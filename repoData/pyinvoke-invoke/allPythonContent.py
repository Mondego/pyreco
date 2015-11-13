__FILENAME__ = conf
from datetime import datetime
import os
import sys

exts = ('autodoc', 'intersphinx')# 'viewcode')
extensions = list(map(lambda x: 'sphinx.ext.%s' % x, exts))
templates_path = ['_templates']
source_suffix = '.rst'
master_doc = 'index'

project = u'Invoke'
year = datetime.now().year
copyright = u'%d Jeff Forcier' % year

# Ensure `links` try hitting API endpoints by default.
default_role = 'py:obj'
# And that we can talk to Python stdlib docs
intersphinx_mapping = {
    'python': ('http://docs.python.org/2.6', None),
}

# Ensure project directory is on PYTHONPATH for version, autodoc access
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '..')))

exclude_trees = ['_build']
pygments_style = 'sphinx'
html_theme = 'default'

# RTD stylesheet
html_style = 'rtd.css'
html_static_path = ['_static']

latex_documents = [
  ('index', 'invoke.tex', u'Invoke Documentation',
   u'Jeff Forcier', 'manual'),
]

# Autodoc settings
autodoc_default_flags = ['members']
autoclass_content = 'both'

# Releases for nice changelog, + settings
extensions.append('releases')
releases_release_uri = "https://github.com/pyinvoke/invoke/tree/%s"
releases_issue_uri = "https://github.com/pyinvoke/invoke/issues/%s"

########NEW FILE########
__FILENAME__ = main
import os

from spec import Spec, trap, eq_

from invoke import run


def _output_eq(cmd, expected):
    return eq_(run(cmd).stdout, expected)


class Main(Spec):
    def setup(self):
        # Enter integration/ so Invoke loads its local tasks.py
        os.chdir(os.path.dirname(__file__))

    @trap
    def basic_invocation(self):
        _output_eq("invoke print_foo", "foo\n")

    @trap
    def shorthand_binary_name(self):
        _output_eq("inv print_foo", "foo\n")

    @trap
    def explicit_task_module(self):
        _output_eq("inv --collection _explicit foo", "Yup\n")

    @trap
    def invocation_with_args(self):
        _output_eq(
            "inv print_name --name whatevs",
            "whatevs\n"
        )

########NEW FILE########
__FILENAME__ = tasks
"""
Tasks module for use within the integration tests.
"""

from invoke import task, run


@task
def print_foo():
    print("foo")

@task
def print_name(name):
    print(name)

########NEW FILE########
__FILENAME__ = _explicit
from invoke import task, run


@task
def foo():
    print("Yup")

########NEW FILE########
__FILENAME__ = cli
from functools import partial
import os
import sys
import textwrap

from .vendor import six

from .context import Context
from .loader import FilesystemLoader
from .parser import Parser, Context as ParserContext, Argument
from .executor import Executor
from .exceptions import Failure, CollectionNotFound, ParseError
from .util import debug, pty_size, enable_logging
from ._version import __version__


def task_name_to_key(x):
    return (x.count('.'), x)

sort_names = partial(sorted, key=task_name_to_key)

indent_num = 2
indent = " " * indent_num


def print_help(tuples):
    """
    Print tabbed columns from (name, help) tuples.

    Useful for listing tasks + docstrings, flags + help strings, etc.
    """
    padding = 3
    # Calculate column sizes: don't wrap flag specs, give what's left over
    # to the descriptions.
    name_width = max(len(x[0]) for x in tuples)
    desc_width = pty_size()[0] - name_width - indent_num - padding - 1
    wrapper = textwrap.TextWrapper(width=desc_width)
    for name, help_str in tuples:
        # Wrap descriptions/help text
        help_chunks = wrapper.wrap(help_str)
        # Print flag spec + padding
        name_padding = name_width - len(name)
        spec = ''.join((
            indent,
            name,
            name_padding * ' ',
            padding * ' '
        ))
        # Print help text as needed
        if help_chunks:
            print(spec + help_chunks[0])
            for chunk in help_chunks[1:]:
                print((' ' * len(spec)) + chunk)
        else:
            print(spec.rstrip())
    print('')



def parse_gracefully(parser, argv):
    """
    Run ``parser.parse_argv(argv)`` & gracefully handle ``ParseError``.

    'Gracefully' meaning to print a useful human-facing error message instead
    of a traceback; the program will still exit if an error is raised.

    If no error is raised, returns the result of the ``parse_argv`` call.
    """
    try:
        return parser.parse_argv(argv)
    except ParseError as e:
        sys.exit(str(e))


def parse(argv, collection=None, version=None):
    """
    Parse ``argv`` list-of-strings into useful core & per-task structures.

    :returns:
        Three-tuple of ``args`` (core, non-task `.Argument` objects),
        ``collection`` (compiled `.Collection` of tasks, using defaults or core
        arguments affecting collection generation) and ``tasks`` (a list of
        `~.parser.context.Context` objects representing the requested task
        executions).
    """
    # Initial/core parsing (core options can affect the rest of the parsing)
    initial_context = ParserContext(args=(
        # TODO: make '--collection' a list-building arg, not a string
        Argument(
            names=('collection', 'c'),
            help="Specify collection name to load. May be given >1 time."
        ),
        Argument(
            names=('root', 'r'),
            help="Change root directory used for finding task modules."
        ),
        Argument(
            names=('help', 'h'),
            optional=True,
            help="Show core or per-task help and exit."
        ),
        Argument(
            names=('version', 'V'),
            kind=bool,
            default=False,
            help="Show version and exit."
        ),
        Argument(
            names=('list', 'l'),
            kind=bool,
            default=False,
            help="List available tasks."
        ),
        Argument(
            names=('no-dedupe',),
            kind=bool,
            default=False,
            help="Disable task deduplication."
        ),
        Argument(
            names=('echo', 'e'),
            kind=bool,
            default=False,
            help="Echo executed commands before running.",
        ),
        Argument(
            names=('warn-only', 'w'),
            kind=bool,
            default=False,
            help="Warn, instead of failing, when shell commands fail.",
        ),
        Argument(
            names=('pty', 'p'),
            kind=bool,
            default=False,
            help="Use a pty when executing shell commands.",
        ),
        Argument(
            names=('hide', 'H'),
            help="Set default value of run()'s 'hide' kwarg.",
        ),
        Argument(
            names=('debug', 'd'),
            kind=bool,
            default=False,
            help="Enable debug output.",
        ),
    ))
    # 'core' will result an .unparsed attribute with what was left over.
    debug("Parsing initial context (core args)")
    parser = Parser(initial=initial_context, ignore_unknown=True)
    core = parse_gracefully(parser, argv[1:])
    debug("After core-args pass, leftover argv: %r" % (core.unparsed,))
    args = core[0].args

    # Enable debugging from here on out, if debug flag was given.
    if args.debug.value:
        enable_logging()

    # Print version & exit if necessary
    if args.version.value:
        if version:
            print(version)
        else:
            print("Invoke %s" % __version__)
        sys.exit(0)

    # Core (no value given) --help output
    # TODO: if this wants to display context sensitive help (e.g. a combo help
    # and available tasks listing; or core flags modified by plugins/task
    # modules) it will have to move farther down.
    if args.help.value == True:
        program_name = os.path.basename(argv[0])
        if program_name == 'invoke' or program_name == 'inv':
            program_name = 'inv[oke]'
        print("Usage: {0} [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]".format(program_name))
        print("")
        print("Core options:")
        print_help(initial_context.help_tuples())
        sys.exit(0)

    # Load collection (default or specified) and parse leftovers
    # (Skip loading if somebody gave us an explicit task collection.)
    if not collection:
        debug("No collection given, loading from %r" % args.root.value)
        loader = FilesystemLoader(start=args.root.value)
        start = args.collection.value
        collection = loader.load(start) if start else loader.load()
    parser = Parser(contexts=collection.to_contexts())
    debug("Parsing actual tasks against collection %r" % collection)
    tasks = parse_gracefully(parser, core.unparsed)

    # Per-task help. Use the parser's contexts dict as that's the easiest way
    # to obtain Context objects here - which are what help output needs.
    name = args.help.value
    if name in parser.contexts:
        # Setup
        ctx = parser.contexts[name]
        tuples = ctx.help_tuples()
        docstring = collection[name].__doc__
        header = "Usage: inv[oke] [--core-opts] %s %%s[other tasks here ...]" % name
        print(header % ("[--options] " if tuples else ""))
        print("")
        print("Docstring:")
        if docstring:
            # Really wish textwrap worked better for this.
            doclines = textwrap.dedent(docstring.lstrip('\n').rstrip()+'\n').splitlines()
            for line in doclines:
                if line.strip():
                    print(indent + line)
                else:
                    print("")
            print("")
        else:
            print(indent + "none")
            print("")
        print("Options:")
        if tuples:
            print_help(tuples)
        else:
            print(indent + "none")
            print("")
        sys.exit(0)

    # Print discovered tasks if necessary
    if args.list.value:
        print("Available tasks:\n")
        # Sort in depth, then alpha, order
        task_names = collection.task_names
        pairs = []
        for primary in sort_names(task_names.keys()):
            # Add aliases
            aliases = sort_names(task_names[primary])
            name = primary
            if aliases:
                name += " (%s)" % ', '.join(aliases)
            # Add docstring 1st lines
            task = collection[primary]
            help_ = ""
            if task.__doc__:
                help_ = task.__doc__.lstrip().splitlines()[0]
            pairs.append((name, help_))

        # Print
        print_help(pairs)
        sys.exit(0)

    # Return to caller so they can handle the results
    return args, collection, tasks


def derive_opts(args):
    run = {}
    if args['warn-only'].value:
        run['warn'] = True
    if args.pty.value:
        run['pty'] = True
    if args.hide.value:
        run['hide'] = args.hide.value
    if args.echo.value:
        run['echo'] = True
    return {'run': run}

def dispatch(argv, version=None):
    args, collection, tasks = parse(argv, version=version)
    results = []
    executor = Executor(collection, Context(**derive_opts(args)))
    # Take action based on 'core' options and the 'tasks' found
    for context in tasks:
        kwargs = {}
        # Take CLI arguments out of parser context, create func-kwarg dict.
        for _, arg in six.iteritems(context.args):
            # Use the arg obj's internal name - not what was necessarily given
            # on the CLI. (E.g. --my-option vs --my_option for
            # mytask(my_option=xxx) requires this.)
            # TODO: store 'given' name somewhere in case somebody wants to see
            # it when handling args.
            kwargs[arg.name] = arg.value
        try:
            # TODO: allow swapping out of Executor subclasses based on core
            # config options
            results.append(executor.execute(
                # Task name given on CLI
                name=context.name,
                # Flags/other args given to this task specifically
                kwargs=kwargs,
                # Was the core dedupe flag given?
                dedupe=not args['no-dedupe']
            ))
        except Failure as f:
            sys.exit(f.result.exited)
    return results


def main():
    # Parse command line
    debug("Base argv from sys: %r" % (sys.argv[1:],))
    dispatch(sys.argv)

########NEW FILE########
__FILENAME__ = collection
import copy
from operator import add
import types

from .vendor import six
from .vendor.lexicon import Lexicon

from .parser import Context, Argument
from .tasks import Task


class Collection(object):
    """
    A collection of executable tasks.
    """
    def __init__(self, *args, **kwargs):
        """
        Create a new task collection/namespace.

        `.Collection` offers a set of methods for building a collection of
        tasks from scratch, plus a convenient constructor wrapping said API.

        **The method approach**

        May initialize with no arguments and use methods (e.g.
        `.add_task`/`.add_collection`) to insert objects::

            c = Collection()
            c.add_task(some_task)

        If an initial string argument is given, it is used as the default name
        for this collection, should it be inserted into another collection as a
        sub-namespace::

            docs = Collection('docs')
            docs.add_task(doc_task)
            ns = Collection()
            ns.add_task(top_level_task)
            ns.add_collection(docs)
            # Valid identifiers are now 'top_level_task' and 'docs.doc_task'
            # (assuming the task objects were actually named the same as the
            # variables we're using :))

        For details, see the API docs for the rest of the class.

        **The constructor approach**

        All ``*args`` given to `.Collection` (besides the optional first 'name'
        argument) are expected to be `.Task` or `.Collection` instances which
        will be passed to `.add_task`/`.add_collection` as appropriate. Module
        objects are also valid (as they are for `.add_collection`). For
        example, the below snippet results in the same two task identifiers as
        the one above::

            ns = Collection(top_level_task, Collection('docs', doc_task))

        If any ``**kwargs`` are given, the keywords are used as the initial
        name arguments for the respective values::

            ns = Collection(
                top_level_task=some_other_task,
                docs=Collection(doc_task)
            )

        That's exactly equivalent to::

            docs = Collection(doc_task)
            ns = Collection()
            ns.add_task(some_other_task, 'top_level_task')
            ns.add_collection(docs, 'docs')

        See individual methods' API docs for details.
        """
        # Initialize
        self.tasks = Lexicon()
        self.collections = Lexicon()
        self.default = None
        self.name = None
        self._configuration = {}
        # Name if applicable
        args = list(args)
        if args and isinstance(args[0], six.string_types):
            self.name = args.pop(0)
        # Dispatch args/kwargs
        for arg in args:
            self._add_object(arg)
        # Dispatch kwargs
        for name, obj in six.iteritems(kwargs):
            self._add_object(obj, name)

    def _add_object(self, obj, name=None):
        if isinstance(obj, Task):
            method = self.add_task
        elif isinstance(obj, (Collection, types.ModuleType)):
            method = self.add_collection
        else:
            raise TypeError("No idea how to insert %r!" % type(obj))
        return method(obj, name=name)

    def __str__(self):
        return "<Collection {0!r}: {1}>".format(
            self.name, ", ".join(sorted(self.tasks.keys())))

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.name == other.name and self.tasks == other.tasks

    @classmethod
    def from_module(self, module, name=None, config=None):
        """
        Return a new `.Collection` created from ``module``.

        Inspects ``module`` for any `.Task` instances and adds them to a new
        `.Collection`, returning it. If any explicit namespace collections
        exist (named ``ns`` or ``namespace``) a copy of that collection object
        is preferentially loaded instead.

        When the implicit/default collection is generated, it will be named
        after the module's ``__name__`` attribute, or its last dotted section
        if it's a submodule. (I.e. it should usually map to the actual ``.py``
        filename.)

        Explicitly given collections will only be given that module-derived
        name if they don't already have a valid ``.name`` attribute.

        :param name:
            A string, which if given will override any automatically derived
            collection name (or name set on the module's root namespace, if it
            has one.)

        :param config:
            A dict, used to set config options on the newly created
            `.Collection` before returning it (saving you a call to
            `.configure`.)
            
            If the imported module had a root namespace object, ``config`` is
            merged on top of it (i.e. overriding any conflicts.)
        """
        module_name = module.__name__.split('.')[-1]
        # See if the module provides a default NS to use in lieu of creating
        # our own collection.
        for candidate in ('ns', 'namespace'):
            obj = getattr(module, candidate, None)
            if obj and isinstance(obj, Collection):
                # Explicitly given name wins over root ns name which wins over
                # actual module name.
                ret = Collection(name or obj.name or module_name)
                ret.tasks = copy.deepcopy(obj.tasks)
                ret.collections = copy.deepcopy(obj.collections)
                ret.default = copy.deepcopy(obj.default)
                # Explicitly given config wins over root ns config
                obj_config = copy.deepcopy(obj._configuration)
                if config:
                    obj_config.update(config)
                ret._configuration = obj_config
                return ret
        # Failing that, make our own collection from the module's tasks.
        tasks = filter(
            lambda x: isinstance(x, Task),
            vars(module).values()
        )
        # Again, explicit name wins over implicit one from module path
        collection = Collection(name or module_name)
        for task in tasks:
            collection.add_task(task)
        if config:
            collection.configure(config)
        return collection

    def add_task(self, task, name=None, default=None):
        """
        Add `.Task` ``task`` to this collection.

        :param task: The `.Task` object to add to this collection.

        :param name:
            Optional string name to bind to (overrides the task's own
            self-defined ``name`` attribute and/or any Python identifier (i.e.
            ``.func_name``.)

        :param default: Whether this task should be the collection default.
        """
        if name is None:
            if task.name:
                name = task.name
            elif hasattr(task.body, 'func_name'):
                name = task.body.func_name
            elif hasattr(task.body, '__name__'):
                name = task.__name__
            else:
                raise ValueError("Could not obtain a name for this task!")
        if name in self.collections:
            raise ValueError("Name conflict: this collection has a sub-collection named %r already" % name)
        self.tasks[name] = task
        for alias in task.aliases:
            self.tasks.alias(alias, to=name)
        if default is True or (default is None and task.is_default):
            if self.default:
                msg = "'%s' cannot be the default because '%s' already is!"
                raise ValueError(msg % (name, self.default))
            self.default = name

    def add_collection(self, coll, name=None):
        # Handle module-as-collection
        if isinstance(coll, types.ModuleType):
            coll = Collection.from_module(coll)
        # Ensure we have a name, or die trying
        name = name or coll.name
        if not name:
            raise ValueError("Non-root collections must have a name!")
        # Test for conflict
        if name in self.tasks:
            raise ValueError("Name conflict: this collection has a task named %r already" % name)
        # Insert
        self.collections[name] = coll

    def split_path(self, path):
        """
        Obtain first collection + remainder, of a task path.

        E.g. for ``"subcollection.taskname"``, return ``("subcollection",
        "taskname")``; for ``"subcollection.nested.taskname"`` return
        ``("subcollection", "nested.taskname")``, etc.

        An empty path becomes simply ``('', '')``.
        """
        parts = path.split('.')
        coll = parts.pop(0)
        rest = '.'.join(parts)
        return coll, rest

    def __getitem__(self, name=None):
        """
        Returns task named ``name``. Honors aliases and subcollections.

        If this collection has a default task, it is returned when ``name`` is
        empty or ``None``. If empty input is given and no task has been
        selected as the default, ValueError will be raised.

        Tasks within subcollections should be given in dotted form, e.g.
        'foo.bar'. Subcollection default tasks will be returned on the
        subcollection's name.
        """
        return self.task_with_config(name)[0]

    def _task_with_merged_config(self, coll, rest, ours):
        task, config = self.collections[coll].task_with_config(rest)
        return task, dict(config, **ours)

    def task_with_config(self, name):
        """
        Return task named ``name`` plus its configuration dict.

        E.g. in a deeply nested tree, this method returns the `.Task`, and a
        configuration dict created by merging that of this `.Collection` and
        any nested `.Collections`, up through the one actually holding the
        `.Task`.

        See `__getitem__` for semantics of the ``name`` argument.

        :return: Two-tuple of (`.Task`, `dict`).
        """
        # Our top level configuration
        ours = self.configuration()
        # Default task for this collection itself
        if not name:
            if self.default:
                return self[self.default], ours
            else:
                raise ValueError("This collection has no default task.")
        # Non-default tasks within subcollections -> recurse (sorta)
        if '.' in name:
            coll, rest = self.split_path(name)
            return self._task_with_merged_config(coll, rest, ours)
        # Default task for subcollections (via empty-name lookup)
        if name in self.collections:
            return self._task_with_merged_config(name, '', ours)
        # Regular task lookup
        return self.tasks[name], ours

    def __contains__(self, name):
        try:
            task = self[name]
            return True
        except KeyError:
            return False

    def to_contexts(self):
        """
        Returns all contained tasks and subtasks as a list of parser contexts.
        """
        result = []
        for primary, aliases in six.iteritems(self.task_names):
            task = self[primary]
            result.append(Context(
                name=primary, aliases=aliases, args=task.get_arguments()
            ))
        return result

    def subtask_name(self, collection_name, task_name):
        return "%s.%s" % (collection_name, task_name)

    @property
    def task_names(self):
        """
        Return all task identifiers for this collection as a dict.

        Specifically, a dict with the primary/"real" task names as the key, and
        any aliases as a list value.
        """
        ret = {}
        # Our own tasks get no prefix, just go in as-is: {name: [aliases]}
        for name, task in six.iteritems(self.tasks):
            ret[name] = task.aliases
        # Subcollection tasks get both name + aliases prefixed
        for coll_name, coll in six.iteritems(self.collections):
            for task_name, aliases in six.iteritems(coll.task_names):
                # Cast to list to handle Py3 map() 'map' return value,
                # so we can add to it down below if necessary.
                aliases = list(map(
                    lambda x: self.subtask_name(coll_name, x),
                    aliases
                ))
                # Tack on collection name to alias list if this task is the
                # collection's default.
                if coll.default and coll.default == task_name:
                    aliases += (coll_name,)
                ret[self.subtask_name(coll_name, task_name)] = aliases
        return ret

    def configuration(self, taskpath=None):
        """
        Obtain merged configuration values from collection & children.

        .. note::
            Merging uses ``copy.deepcopy`` to prevent state bleed.

        :param taskpath:
            (Optional) Task name/path, identical to that used for `__getitem__`
            (e.g. may be dotted for nested tasks, etc.) Used to decide which
            path to follow in the collection tree when merging config values.

        :returns: A `dict` containing configuration values.
        """
        if taskpath is None:
            return copy.deepcopy(self._configuration)
        return self.task_with_config(taskpath)[1]

    def configure(self, options):
        """
        Merge ``options`` dict into this collection's `.configuration`.

        Options configured this way will be available to all
        :doc:`contextualized tasks </concepts/context>`. It is recommended to
        use unique keys to avoid potential clashes with other config options

        For example, if you were configuring a Sphinx docs build target
        directory, it's better to use a key like ``'sphinx.target'`` than
        simply ``'target'``.

        :param options: An object implementing the dictionary protocol.
        :returns: ``None``.
        """
        self._configuration.update(options)

########NEW FILE########
__FILENAME__ = context
from copy import deepcopy

from .runner import run


class Context(object):
    """
    Context-aware API wrapper & state-passing object.

    `.Context` objects are created during command-line parsing (or, if desired,
    by hand) and used to share parser and configuration state with executed
    tasks (see :doc:`/concepts/context`).

    Specifically, the class offers wrappers for core API calls (such as `.run`)
    which take into account CLI parser flags, configuration files, and/or
    changes made at runtime. It also acts as a dict-like object proxying to its
    ``config`` attribute (for e.g. ``__getitem__``, ``get`` and ``update``.)

    Instances of `.Context` may be shared between tasks when executing
    sub-tasks - either the same context the caller was given, or an altered
    copy thereof (or, theoretically, a brand new one).

    .. note::
        Transmitting a copy (using e.g. `.clone`) instead of mutating a
        ``Context`` in-place is a nice way to limit unwanted or hard-to-track
        state mutation, and/or to enable safer concurrency.
    """
    def __init__(self, run=None, config=None):
        """
        :param run:
            A dict acting as default ``**kwargs`` for `.run`. E.g. to create a
            `.Context` whose `Context.run` method defaults to ``echo=True``,
            say::

                ctx = Context(run={'echo': True})

        :param config:
            General (non-``run``-oriented) configuration options dict.
            Optional.
        """
        self.config = {
            'run': run or {},
            'general': config or {},
        }

    def clone(self):
        """
        Return a new Context instance resembling this one.

        Simple syntactic sugar for a handful of ``deepcopy`` calls, which
        generally work fine because config values are simple data structures.
        """
        return Context(
            run=deepcopy(self.config['run']),
            config=deepcopy(self.config['general']),
        )

    def run(self, *args, **kwargs):
        """
        Wrapper for `.run`.

        To set default `.run` keyword argument values, instantiate `.Context`
        with the ``run`` kwarg set to a dict.

        E.g. to create a `.Context` whose `.Context.run` method always defaults
        to ``warn=True``::

            ctx = Context(run={'warn': True})
            ctx.run('command') # behaves like invoke.run('command', warn=True)

        """
        options = dict(self.config['run'])
        options.update(kwargs)
        return run(*args, **options)

    def __getitem__(self, *args, **kwargs):
        return self.config['general'].__getitem__(*args, **kwargs)

    def get(self, *args, **kwargs):
        return self.config['general'].get(*args, **kwargs)

    def update(self, *args, **kwargs):
        return self.config['general'].update(*args, **kwargs)

########NEW FILE########
__FILENAME__ = exceptions
class CollectionNotFound(Exception):
    def __init__(self, name, start):
        self.name = name
        self.start = start


class Failure(Exception):
    """
    Exception subclass representing failure of a command execution.

    It exhibits a ``result`` attribute containing the related `Result` object,
    whose attributes may be inspected to determine why the command failed.
    """
    def __init__(self, result):
        self.result = result

    def __str__(self):
        return """Command execution failure!

Exit code: {0}

Stderr:

{1}

""".format(self.result.exited, self.result.stderr)

    def __repr__(self):
        return str(self)


class ParseError(Exception):
    def __init__(self, msg, context=None):
        super(ParseError, self).__init__(msg)
        self.context = context

########NEW FILE########
__FILENAME__ = executor
from .context import Context
from .util import debug
from .tasks import Call


class Executor(object):
    """
    An execution strategy for Task objects.

    Subclasses may override various extension points to change, add or remove
    behavior.
    """
    def __init__(self, collection, context=None):
        """
        Initialize executor with handles to a task collection & config context.

        The collection is used for looking up tasks by name and
        storing/retrieving state, e.g. how many times a given task has been
        run this session and so on. It is optional; if not given a blank
        `~invoke.context.Context` is used.

        A copy of the context is passed into any tasks that mark themselves as
        requiring one for operation.
        """
        self.collection = collection
        self.context = context or Context()

    def _execute(self, task, name, args, kwargs):
        # Need task + possible name when invoking CLI-given tasks, so we can
        # pass a dotted path to Collection.configuration()
        debug("Executing %r%s" % (task, (" as %s" % name) if name else ""))
        if task.contextualized:
            context = self.context.clone()
            context.update(self.collection.configuration(name))
            args = (context,) + args
        return task(*args, **kwargs)


    def execute(self, name, kwargs=None, dedupe=True):
        """
        Execute a named task, honoring pre- or post-tasks and so forth.

        :param name:
            A string naming which task from the Executor's `.Collection` is to
            be executed. May contain dotted syntax appropriate for calling
            namespaced tasks, e.g. ``subcollection.taskname``.

        :param kwargs:
            A keyword argument dict expanded when calling the requested task.
            E.g.::

                executor.execute('mytask', {'myarg': 'foo'})

            is (roughly) equivalent to::

                mytask(myarg='foo')

        :param dedupe:
            Ensures any given task within ``self.collection`` is only run once
            per session. Set to ``False`` to disable this behavior.

        :returns:
            The return value of the named task -- regardless of whether pre- or
            post-tasks are executed.
        """
        # Expand task list
        task = self.collection[name]
        debug("Executor is examining top level task %r (name given: %r)" % (
            task, name
        ))
        # TODO: post-tasks
        pre = list(task.pre)
        debug("Pre-tasks: %r" % (pre,))
        # Dedupe if requested
        if dedupe:
            debug("Deduplication is enabled")
            # Compact (preserving order, so not using list+set)
            compact_pre = []
            for t in pre:
                if t not in compact_pre:
                    compact_pre.append(t)
            debug("Pre-tasks, obvious dupes removed: %r" % (compact_pre,))
            # Remove tasks already called
            pre = []
            for t in compact_pre:
                if not t.called:
                    pre.append(t)
            debug("Pre-tasks, already-called tasks removed: %r" % (pre,))
        else:
            debug("Deduplication is DISABLED, above pre-task list will run")
        # Execute
        results = {}
        kwargs = kwargs or {}
        for t in pre:
            # TODO: intelligent result capture
            # Execute task w/o a given name since it's a pre-task.
            # TODO: figure out if that's quite right (may not play well with
            # nested config junk)
            pre_args, pre_kwargs = tuple(), {}
            if isinstance(t, Call):
                c = t
                t = c.task
                pre_args, pre_kwargs = c.args, c.kwargs
            self._execute(task=t, name=None, args=pre_args, kwargs=pre_kwargs)
        return self._execute(task=task, name=name, args=tuple(), kwargs=kwargs)

########NEW FILE########
__FILENAME__ = loader
import os
import sys
import imp

from .collection import Collection
from .exceptions import CollectionNotFound
from .tasks import Task


class Loader(object):
    """
    Abstract class defining how to load a session's base `.Collection`.
    """
    def find(self, name):
        """
        Implementation-specific finder method seeking collection ``name``.

        Must return a 4-tuple valid for use by `imp.load_module`, which is
        typically a name string followed by the contents of the 3-tuple
        returned by `imp.find_module` (``file``, ``pathname``,
        ``description``.)

        For a sample implementation, see `FilesystemLoader`.
        """
        raise NotImplementedError

    def load(self, name='tasks'):
        """
        Load and return collection identified by ``name``.

        This method requires a working implementation of `.find` in order to
        function.

        In addition to importing the named module, it will add the module's
        parent directory to the front of `sys.path` to provide normal Python
        import behavior (i.e. so the loaded module may load local-to-it modules
        or packages.)
        """
        # Find the named tasks module, depending on implementation.
        # Will raise an exception if not found.
        fd, path, desc = self.find(name)
        try:
            # Ensure containing directory is on sys.path in case the module
            # being imported is trying to load local-to-it names.
            sys.path.insert(0, os.path.dirname(path))
            # Actual import
            module = imp.load_module(name, fd, path, desc)
            # Make a collection from it, and done
            return Collection.from_module(module)
        finally:
            # Ensure we clean up the opened file object returned by find()
            fd.close()


class FilesystemLoader(Loader):
    """
    Loads Python files from the filesystem (e.g. ``tasks.py``.)

    Searches recursively towards filesystem root from a given start point.
    """
    def __init__(self, start=None):
        self._start = start

    @property
    def start(self):
        # Lazily determine default CWD
        return self._start or os.getcwd()

    def find(self, name):
        # Accumulate all parent directories
        start = self.start
        parents = [os.path.abspath(start)]
        parents.append(os.path.dirname(parents[-1]))
        while parents[-1] != parents[-2]:
            parents.append(os.path.dirname(parents[-1]))
        # Make sure we haven't got duplicates on the end
        if parents[-1] == parents[-2]:
            parents = parents[:-1]
        # Use find_module with our list of parents. ImportError from
        # find_module means "couldn't find" not "found and couldn't import" so
        # we turn it into a more obvious exception class.
        try:
            return imp.find_module(name, parents)
        except ImportError:
            raise CollectionNotFound(name=name, start=start)

########NEW FILE########
__FILENAME__ = monkey
# Fuckin' A.

import select, errno, os, sys
from subprocess import Popen as OriginalPopen, mswindows, PIPE

from .vendor import six


def read_byte(file_no):
    return os.read(file_no, 1)


class Popen(OriginalPopen):
    #
    # Custom code
    #
    def __init__(self, *args, **kwargs):
        hide = kwargs.pop('hide', [])
        super(Popen, self).__init__(*args, **kwargs)
        self.hide = hide


    #
    # Copy/modified code from upstream
    #
    if mswindows:
        def _readerthread(self, fh, buffer):
            # TODO: How to determine which sys.std(out|err) to use?
            buffer.append(fh.read())
    else: # Sane operating systems
        # endtime + timeout are new for py3; we don't currently use them but
        # they must exist to be compatible.
        def _communicate(self, input, endtime=None, timeout=None):
            read_set = []
            write_set = []
            stdout = None # Return
            stderr = None # Return

            if self.stdin:
                # Flush stdio buffer.  This might block, if the user has
                # been writing to .stdin in an uncontrolled fashion.
                self.stdin.flush()
                if input:
                    write_set.append(self.stdin)
                else:
                    self.stdin.close()
            if self.stdout:
                read_set.append(self.stdout)
                stdout = []
            if self.stderr:
                read_set.append(self.stderr)
                stderr = []

            input_offset = 0
            empty_str = b''
            while read_set or write_set:
                try:
                    rlist, wlist, xlist = select.select(read_set, write_set, [])
                except select.error as e:
                    if e.args[0] == errno.EINTR:
                        continue
                    raise

                if self.stdin in wlist:
                    # When select has indicated that the file is writable,
                    # we can write up to PIPE_BUF bytes without risk
                    # blocking.  POSIX defines PIPE_BUF >= 512
                    chunk = input[input_offset : input_offset + 512]
                    bytes_written = os.write(self.stdin.fileno(), chunk)
                    input_offset += bytes_written
                    if input_offset >= len(input):
                        self.stdin.close()
                        write_set.remove(self.stdin)

                if self.stdout in rlist:
                    data = read_byte(self.stdout.fileno())
                    if data == empty_str:
                        self.stdout.close()
                        read_set.remove(self.stdout)
                    if 'out' not in self.hide:
                        stream = sys.stdout
                        if six.PY3:
                            stream = stream.buffer
                        stream.write(data)
                    stdout.append(data)

                if self.stderr in rlist:
                    data = read_byte(self.stderr.fileno())
                    if data == empty_str:
                        self.stderr.close()
                        read_set.remove(self.stderr)
                    if 'err' not in self.hide:
                        stream = sys.stderr
                        if six.PY3:
                            stream = stream.buffer
                        stream.write(data)
                    stderr.append(data)

            # All data exchanged.  Translate lists into strings.
            if stdout is not None:
                stdout = empty_str.join(stdout).decode('utf-8', 'replace')
            if stderr is not None:
                stderr = empty_str.join(stderr).decode('utf-8', 'replace')

            # Translate newlines, if requested.  We cannot let the file
            # object do the translation: It is based on stdio, which is
            # impossible to combine with select (unless forcing no
            # buffering).
            if self.universal_newlines and hasattr(file, 'newlines'):
                if stdout:
                    stdout = self._translate_newlines(stdout)
                if stderr:
                    stderr = self._translate_newlines(stderr)

            self.wait()
            return (stdout, stderr)

########NEW FILE########
__FILENAME__ = argument
class Argument(object):
    """
    A command-line argument/flag.

    :param name:
        Syntactic sugar for ``names=[<name>]``. Giving both ``name`` and
        ``names`` is invalid.
    :param names:
        List of valid identifiers for this argument. For example, a "help"
        argument may be defined with a name list of ``['-h', '--help']``.
    :param kind:
        Type factory & parser hint. E.g. ``int`` will turn the default text
        value parsed, into a Python integer; and ``bool`` will tell the
        parser not to expect an actual value but to treat the argument as a
        toggle/flag.
    :param default:
        Default value made available to the parser if no value is given on the
        command line.
    :param help:
        Help text, intended for use with ``--help``.
    :param positional:
        Whether or not this argument's value may be given positionally. When
        ``False`` (default) arguments must be explicitly named.
    :param optional:
        Whether or not this (non-``bool``) argument requires a value.
    """
    def __init__(self, name=None, names=(), kind=str, default=None, help=None,
        positional=False, optional=False, attr_name=None):
        if name and names:
            msg = "Cannot give both 'name' and 'names' arguments! Pick one."
            raise TypeError(msg)
        if not (name or names):
            raise TypeError("An Argument must have at least one name.")
        self.names = tuple(names if names else (name,))
        self.kind = kind
        self.raw_value = self._value = None
        self.default = default
        self.help = help
        self.positional = positional
        self.optional = optional
        self.attr_name = attr_name

    def __str__(self):
        return "<%s: %s%s%s>" % (
            self.__class__.__name__,
            self.name,
            " (%s)" % (", ".join(self.nicknames)) if self.nicknames else "",
            "*" if self.positional else ""
        )

    def __repr__(self):
        return str(self)

    @property
    def name(self):
        return self.attr_name or self.names[0]

    @property
    def nicknames(self):
        return self.names[1:]

    @property
    def takes_value(self):
        return self.kind is not bool

    @property
    def value(self):
        return self._value if self._value is not None else self.default

    @value.setter
    def value(self, arg):
        self.set_value(arg, cast=True)

    def set_value(self, value, cast=True):
        """
        Actual explicit value-setting API call.

        Sets ``self.raw_value`` to ``value`` directly.

        Sets ``self.value`` to ``self.kind(value)``, unless ``cast=False`` in
        which case the raw value is also used.
        """
        self.raw_value = value
        self._value = (self.kind if cast else lambda x: x)(value)

########NEW FILE########
__FILENAME__ = context
from ..vendor.lexicon import Lexicon

from .argument import Argument


def to_flag(name):
    name = name.replace('_', '-')
    if len(name) == 1:
        return '-' + name
    return '--' + name

def sort_candidate(arg):
    names = arg.names
    # TODO: is there no "split into two buckets on predicate" builtin?
    shorts = set(x for x in names if len(x.strip('-')) == 1)
    longs = set(x for x in names if x not in shorts)
    return sorted(shorts if shorts else longs)[0]

def flag_key(x):
    """
    Obtain useful key list-of-ints for sorting CLI flags.
    """
    # Setup
    ret = []
    x = sort_candidate(x)
    # Long-style flags win over short-style ones, so the first item of
    # comparison is simply whether the flag is a single character long (with
    # non-length-1 flags coming "first" [lower number])
    ret.append(1 if len(x) == 1 else 0)
    # Next item of comparison is simply the strings themselves,
    # case-insensitive. They will compare alphabetically if compared at this
    # stage.
    ret.append(x.lower())
    # Finally, if the case-insensitive test also matched, compare
    # case-sensitive, but inverse (with lowercase letters coming first)
    inversed = ''
    for char in x:
        inversed += char.lower() if char.isupper() else char.upper()
    ret.append(inversed)
    return ret


class Context(object):
    """
    Parsing context with knowledge of flags & their format.

    Generally associated with the core program or a task.

    When run through a parser, will also hold runtime values filled in by the
    parser.
    """
    def __init__(self, name=None, aliases=(), args=()):
        """
        Create a new ``Context`` named ``name``, with ``aliases``.

        ``name`` is optional, and should be a string if given. It's used to
        tell Context objects apart, and for use in a Parser when determining
        what chunk of input might belong to a given Context.

        ``aliases`` is also optional and should be an iterable containing
        strings. Parsing will honor any aliases when trying to "find" a given
        context in its input.

        May give one or more ``args``, which is a quick alternative to calling
        ``for arg in args: self.add_arg(arg)`` after initialization.
        """
        self.args = Lexicon()
        self.positional_args = []
        self.flags = Lexicon()
        self.inverse_flags = {} # No need for Lexicon here
        self.name = name
        self.aliases = aliases
        for arg in args:
            self.add_arg(arg)

    def __str__(self):
        aliases = (" (%s)" % ', '.join(self.aliases)) if self.aliases else ""
        name = (" %r%s" % (self.name, aliases)) if self.name else ""
        args = (": %r" % (self.args,)) if self.args else ""
        return "<parser/Context%s%s>" % (name, args)

    def __repr__(self):
        return str(self)

    def add_arg(self, *args, **kwargs):
        """
        Adds given ``Argument`` (or constructor args for one) to this context.

        The Argument in question is added to the following dict attributes:

        * ``args``: "normal" access, i.e. the given names are directly exposed
          as keys.
        * ``flags``: "flaglike" access, i.e. the given names are translated
          into CLI flags, e.g. ``"foo"`` is accessible via ``flags['--foo']``.
        * ``inverse_flags``: similar to ``flags`` but containing only the
          "inverse" versions of boolean flags which default to True. This
          allows the parser to track e.g. ``--no-myflag`` and turn it into a
          False value for the ``myflag`` Argument.
        """
        # Normalize
        if len(args) == 1 and isinstance(args[0], Argument):
            arg = args[0]
        else:
            arg = Argument(*args, **kwargs)
        # Uniqueness constraint: no name collisions
        for name in arg.names:
            if name in self.args:
                msg = "Tried to add an argument named %r but one already exists!"
                raise ValueError(msg % name)
        # First name used as "main" name for purposes of aliasing
        main = arg.names[0] # NOT arg.name
        self.args[main] = arg
        # Note positionals in distinct, ordered list attribute
        if arg.positional:
            self.positional_args.append(arg)
        # Add names & nicknames to flags, args
        self.flags[to_flag(main)] = arg
        for name in arg.nicknames:
            self.args.alias(name, to=main)
            self.flags.alias(to_flag(name), to=to_flag(main))
        # Add attr_name to args, but not flags
        if arg.attr_name:
            self.args.alias(arg.attr_name, to=main)
        # Add to inverse_flags if required
        if arg.kind == bool and arg.default == True:
            # Invert the 'main' flag name here, which will be a dashed version
            # of the primary argument name if underscore-to-dash transformation
            # occurred.
            inverse_name = to_flag("no-%s" % main)
            self.inverse_flags[inverse_name] = to_flag(main)

    @property
    def needs_positional_arg(self):
        return any(x.value is None for x in self.positional_args)

    def help_for(self, flag):
        """
        Return 2-tuple of ``(flag-spec, help-string)`` for given ``flag``.
        """
        # Obtain arg obj
        if flag not in self.flags:
            raise ValueError("%r is not a valid flag for this context! Valid flags are: %r" % (flag, self.flags.keys()))
        arg = self.flags[flag]
        # Show all potential names for this flag in the output
        names = list(set([flag] + self.flags.aliases_of(flag)))
        # Determine expected value type, if any
        value = {
            str: 'STRING',
        }.get(arg.kind)
        # Format & go
        full_names = []
        for name in names:
            if value:
                # Short flags are -f VAL, long are --foo=VAL
                # When optional, also, -f [VAL] and --foo[=VAL]
                if len(name.strip('-')) == 1:
                    value_ = ("[%s]" % value) if arg.optional else value
                    valuestr = " %s" % value_
                else:
                    valuestr = "=%s" % value
                    if arg.optional:
                        valuestr = "[%s]" % valuestr
            else:
                # no value => boolean
                # check for inverse
                if name in self.inverse_flags.values():
                    name = "--[no-]%s" % name[2:]

                valuestr = ""
            # Tack together
            full_names.append(name + valuestr)
        namestr = ", ".join(sorted(full_names, key=len))
        helpstr = arg.help or ""
        return namestr, helpstr

    def help_tuples(self):
        """
        Return sorted iterable of help tuples for all member Arguments.

        Sorts like so:

        * General sort is alphanumerically
        * Short flags win over long flags
        * Arguments with *only* long flags and *no* short flags will come
          first.
        * When an Argument has multiple long or short flags, it will sort using
          the most favorable (lowest alphabetically) candidate.

        This will result in a help list like so::

            --alpha, --zeta # 'alpha' wins
            --beta
            -a, --query # short flag wins
            -b, --argh
            -c
        """
        # TODO: argument/flag API must change :(
        # having to call to_flag on 1st name of an Argument is just dumb.
        # To pass in an Argument object to help_for may require moderate
        # changes?
        # Cast to list to ensure non-generator on Python 3.
        return list(map(
            lambda x: self.help_for(to_flag(x.name)),
            sorted(self.flags.values(), key=flag_key)
        ))

########NEW FILE########
__FILENAME__ = parser
import copy

from ..vendor.lexicon import Lexicon
from ..vendor.fluidity import StateMachine, state, transition
from ..vendor import six

from .context import Context
from .argument import Argument # Mostly for importing via invoke.parser.<x>
from ..util import debug
from ..exceptions import ParseError


def is_flag(value):
    return value.startswith('-')

def is_long_flag(value):
    return value.startswith('--')


class Parser(object):
    """
    Create parser conscious of ``contexts`` and optional ``initial`` context.

    ``contexts`` should be an iterable of ``Context`` instances which will be
    searched when new context names are encountered during a parse. These
    Contexts determine what flags may follow them, as well as whether given
    flags take values.

    ``initial`` is optional and will be used to determine validity of "core"
    options/flags at the start of the parse run, if any are encountered.

    ``ignore_unknown`` determines what to do when contexts are found which do
    not map to any members of ``contexts``. By default it is ``False``, meaning
    any unknown contexts result in a parse error exception. If ``True``,
    encountering an unknown context halts parsing and populates the return
    value's ``.unparsed`` attribute with the remaining parse tokens.
    """
    def __init__(self, contexts=(), initial=None, ignore_unknown=False):
        self.initial = initial
        self.contexts = Lexicon()
        self.ignore_unknown = ignore_unknown
        for context in contexts:
            debug("Adding %s" % context)
            if not context.name:
                raise ValueError("Non-initial contexts must have names.")
            exists = "A context named/aliased %r is already in this parser!"
            if context.name in self.contexts:
                raise ValueError(exists % context.name)
            self.contexts[context.name] = context
            for alias in context.aliases:
                if alias in self.contexts:
                    raise ValueError(exists % alias)
                self.contexts.alias(alias, to=context.name)

    def parse_argv(self, argv):
        """
        Parse an argv-style token list ``argv``.

        Returns a list of ``Context`` objects matching the order they were
        found in the ``argv`` and containing ``Argument`` objects with updated
        values based on any flags given.

        Assumes any program name has already been stripped out. Good::

            Parser(...).parse_argv(['--core-opt', 'task', '--task-opt'])

        Bad::

            Parser(...).parse_argv(['invoke', '--core-opt', ...])
        """
        machine = ParseMachine(initial=self.initial, contexts=self.contexts,
            ignore_unknown=self.ignore_unknown)
        # FIXME: Why isn't there str.partition for lists? There must be a
        # better way to do this. Split argv around the double-dash remainder
        # sentinel.
        debug("Starting argv: %r" % (argv,))
        try:
            ddash = argv.index('--')
        except ValueError:
            ddash = len(argv) # No remainder == body gets all
        body = argv[:ddash]
        remainder = argv[ddash:][1:] # [1:] to strip off remainder itself
        if remainder:
            debug("Remainder: argv[%r:][1:] => %r" % (ddash, remainder))
        for index, token in enumerate(body):
            # Handle non-space-delimited forms, if not currently expecting a
            # flag value and still in valid parsing territory (i.e. not in
            # "unknown" state which implies store-only)
            if not machine.waiting_for_flag_value and is_flag(token) \
                and not machine.result.unparsed:
                orig = token
                # Equals-sign-delimited flags, eg --foo=bar or -f=bar
                if '=' in token:
                    token, _, value = token.partition('=')
                    debug("Splitting x=y expr %r into tokens %r and %r" % (
                        orig, token, value))
                    body.insert(index + 1, value)
                # Contiguous boolean short flags, e.g. -qv
                elif not is_long_flag(token) and len(token) > 2:
                    full_token = token[:]
                    rest, token = token[2:], token[:2]
                    debug("Splitting %r into token %r and rest %r" % (full_token, token, rest))
                    # Handle boolean flag block vs short-flag + value. Make
                    # sure not to test the token as a context flag if we've
                    # passed into 'storing unknown stuff' territory (e.g. on a
                    # core-args pass, handling what are going to be task args)
                    have_flag = (token in machine.context.flags
                        and machine.current_state != 'unknown')
                    if have_flag and machine.context.flags[token].takes_value:
                        debug("%r is a flag for current context & it takes a value, giving it %r" % (token, rest))
                        body.insert(index + 1, rest)
                    else:
                        rest = ['-%s' % x for x in rest]
                        debug("Splitting multi-flag glob %r into %r and %r" % (
                            orig, token, rest))
                        for item in reversed(rest):
                            body.insert(index + 1, item)
            machine.handle(token)
        machine.finish()
        result = machine.result
        result.remainder = ' '.join(remainder)
        return result


class ParseMachine(StateMachine):
    initial_state = 'context'

    state('context', enter=['complete_flag', 'complete_context'])
    state('unknown', enter=['complete_flag', 'complete_context'])
    state('end', enter=['complete_flag', 'complete_context'])

    transition(from_=('context', 'unknown'), event='finish', to='end')
    transition(from_='context', event='see_context', action='switch_to_context', to='context')
    transition(from_=('context', 'unknown'), event='see_unknown', action='store_only', to='unknown')

    def changing_state(self, from_, to):
        debug("ParseMachine: %r => %r" % (from_, to))

    def __init__(self, initial, contexts, ignore_unknown):
        # Initialize
        self.ignore_unknown = ignore_unknown
        self.context = copy.deepcopy(initial)
        debug("Initialized with context: %r" % self.context)
        self.flag = None
        self.result = ParseResult()
        self.contexts = copy.deepcopy(contexts)
        debug("Available contexts: %r" % self.contexts)
        # In case StateMachine does anything in __init__
        super(ParseMachine, self).__init__()

    @property
    def waiting_for_flag_value(self):
        return self.flag and self.flag.takes_value and self.flag.raw_value is None

    def handle(self, token):
        debug("Handling token: %r" % token)
        # Handle unknown state at the top: we don't care about even
        # possibly-valid input if we've encountered unknown input.
        if self.current_state == 'unknown':
            debug("Top-of-handle() see_unknown(%r)" % token)
            self.see_unknown(token)
            return
        # Flag
        if self.context and token in self.context.flags:
            debug("Saw flag %r" % token)
            self.switch_to_flag(token)
        elif self.context and token in self.context.inverse_flags:
            debug("Saw inverse flag %r" % token)
            self.switch_to_flag(token, inverse=True)
        # Value for current flag
        elif self.waiting_for_flag_value:
            self.see_value(token)
        # Positional args (must come above context-name check in case we still
        # need a posarg and the user legitimately wants to give it a value that
        # just happens to be a valid context name.)
        elif self.context and self.context.needs_positional_arg:
            debug("Context %r requires positional args, eating %r" % (
                self.context, token))
            self.see_positional_arg(token)
        # New context
        elif token in self.contexts:
            self.see_context(token)
        # Unknown
        else:
            if not self.ignore_unknown:
                self.error("No idea what %r is!" % token)
            else:
                debug("Bottom-of-handle() see_unknown(%r)" % token)
                self.see_unknown(token)

    def store_only(self, token):
        # Start off the unparsed list
        debug("Storing unknown token %r" % token)
        self.result.unparsed.append(token)

    def complete_context(self):
        debug("Wrapping up context %r" % (self.context.name if self.context else self.context))
        # Ensure all of context's positional args have been given.
        if self.context and self.context.needs_positional_arg:
            self.error("'%s' did not receive all required positional arguments!" % self.context.name)
        if self.context and self.context not in self.result:
            self.result.append(self.context)

    def switch_to_context(self, name):
        self.context = self.contexts[name]
        debug("Moving to context %r" % name)
        debug("Context args: %r" % self.context.args)
        debug("Context flags: %r" % self.context.flags)
        debug("Context inverse_flags: %r" % self.context.inverse_flags)

    def complete_flag(self):
        # Barf if we needed a value and didn't get one
        if (
            self.flag
            and self.flag.takes_value
            and self.flag.raw_value is None
            and not self.flag.optional
        ):
            self.error("Flag %r needed value and was not given one!" % self.flag)
        # Handle optional-value flags; at this point they were not given an
        # explicit value, but they were seen, ergo they should get treated like
        # bools.
        if self.flag and self.flag.raw_value is None and self.flag.optional:
            msg = "Saw optional flag %r go by w/ no value; setting to True"
            debug(msg % self.flag.name)
            # Skip casting so the bool gets preserved
            self.flag.set_value(True, cast=False)

    def check_ambiguity(self, value):
        """
        Guard against ambiguity when currently flag takes an optional value.
        """
        if not (self.flag and self.flag.optional):
            return False
        tests = []
        # unfilled posargs still exist
        tests.append(self.context and self.context.needs_positional_arg)
        # * value looks like it's supposed to be a flag itself.
        # (Doesn't have to even actually be valid - chances are if it looks
        # like a flag, the user was trying to give one.)
        tests.append(is_flag(value))
        # * value matches another valid task/context name
        tests.append(value in self.contexts)
        if any(tests):
            msg = "%r is ambiguous when given after an optional-value flag"
            raise ParseError(msg % value)

    def switch_to_flag(self, flag, inverse=False):
        # Sanity check for ambiguity w/ prior optional-value flag
        self.check_ambiguity(flag)
        # Set flag/arg obj
        flag = self.context.inverse_flags[flag] if inverse else flag
        # Update state
        self.flag = self.context.flags[flag]
        debug("Moving to flag %r" % self.flag)
        # Handle boolean flags (which can immediately be updated)
        if not self.flag.takes_value:
            val = not inverse
            debug("Marking seen flag %r as %s" % (self.flag, val))
            self.flag.value = val

    def see_value(self, value):
        self.check_ambiguity(value)
        if self.flag.takes_value:
            debug("Setting flag %r to value %r" % (self.flag, value))
            self.flag.value = value
        else:
            self.error("Flag %r doesn't take any value!" % self.flag)

    def see_positional_arg(self, value):
        for arg in self.context.positional_args:
            if arg.value is None:
                arg.value = value
                break

    def error(self, msg):
        raise ParseError(msg, self.context)


class ParseResult(list):
    """
    List-like object with some extra parse-related attributes.

    Specifically, a ``.remainder`` attribute, which is the string found after a
    ``--`` in any parsed argv list; and an ``.unparsed`` attribute, a list of
    tokens that were unable to be parsed.
    """
    def __init__(self, *args, **kwargs):
        super(ParseResult, self).__init__(*args, **kwargs)
        self.remainder = ""
        self.unparsed = []

########NEW FILE########
__FILENAME__ = runner
import os
import pty
import select
import sys

from .vendor import pexpect

from .monkey import Popen, PIPE
from .exceptions import Failure


def normalize_hide(val):
    hide_vals = (None, False, 'out', 'stdout', 'err', 'stderr', 'both', True)
    if val not in hide_vals:
        raise ValueError("'hide' got %r which is not in %r" % (val, hide_vals,))
    if val in (None, False):
        hide = ()
    elif val in ('both', True):
        hide = ('out', 'err')
    elif val == 'stdout':
        hide = ('out',)
    elif val == 'stderr':
        hide = ('err',)
    else:
        hide = (val,)
    return hide


class Runner(object):
    """
    Abstract core command-running API.

    Actual command runners should subclass & implement the following:

    * ``run``: Command execution hooking directly into the subprocess'
      stdout/stderr pipes and returning their eventual values as distinct
      strings. Specifically, have a signature of ``def run(self, command, warn,
      hide):`` (see `.runner.run` for semantics of these) and return a 4-tuple
      of ``(stdout, stderr, exitcode, exception)``.
    * ``run_pty``: Execution utilizing a pseudo-terminal, which is then
      expected to only return a useful stdout (with stderr usually empty.) Has
      same signature and return value as ``run``.

    For an implementation example, see the source code for `.Local`.
    """
    def run(self, command, warn, hide):
        raise NotImplementedError

    def run_pty(self, command, warn, hide):
        raise NotImplementedError


class Local(Runner):
    """
    Execute a command on the local system in a subprocess.
    """
    def run(self, command, warn, hide):
        process = Popen(
            command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            hide=hide,
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode, None

    def run_pty(self, command, warn, hide):
        out = []
        def out_filter(text):
            out.append(text.decode("utf-8", 'replace'))
            if 'out' not in hide:
                return text
            else:
                return b""
        wrapped_cmd = "/bin/bash -c \"%s\"" % command
        p = pexpect.spawn(wrapped_cmd)
        # Ensure pexpect doesn't barf with OSError if we fall off the end of
        # the child's input on some platforms (e.g. Linux).
        exception = None
        try:
            p.interact(output_filter=out_filter)
        except OSError as e:
            # Only capture the OSError we expect
            if "Input/output error" not in str(e):
                raise
            # Ensure it ties off the child, sets exitstatus, etc
            p.close()
            # Capture the exception in case it's NOT the OSError we think it
            # is and folks need to debug
            exception = e
        return "".join(out), "", p.exitstatus, exception


def run(command, warn=False, hide=None, pty=False, echo=False, runner=Local):
    """
    Execute ``command`` (via ``runner``) returning a `Result` object.

    A `Failure` exception (containing a reference to the `Result` that would
    otherwise have been returned) is raised if the command terminates with a
    nonzero return code. This behavior may be disabled by setting
    ``warn=True``.

    To disable copying the command's stdout and/or stderr to the controlling
    terminal, specify ``hide='out'`` (or ``'stdout'``), ``hide='err'`` (or
    ``'stderr'``) or ``hide='both'`` (or ``True``). The default value is
    ``None``, meaning to print everything; ``False`` will also disable hiding.

    .. note::
        Stdout and stderr are always captured and stored in the ``Result``
        object, regardless of ``hide``'s value.

    By default, ``run`` connects directly to the invoked process and reads
    its stdout/stderr streams. Some programs will buffer differently (or even
    behave differently) in this situation compared to using an actual terminal
    or pty. To use a pty, specify ``pty=True``.

    .. warning::
        Due to their nature, ptys have a single output stream, so the ability
        to tell stdout apart from stderr is **not possible** when ``pty=True``.
        As such, all output will appear on your local stdout and be captured
        into the ``stdout`` result attribute. Stderr and ``stderr`` will always
        be empty when ``pty=True``.

    `.run` does not echo the commands it runs by default; to make it do so, say
    ``echo=True``.

    The ``runner`` argument allows overriding the actual execution mechanism,
    and must be a class exposing two methods, ``run`` and ``run_pty``, whose
    signatures must match ``function(command, warn, hide)`` - all of which
    match the above descriptions, re: types and default values.
    
    These methods must return a tuple of ``(stdout, stderr, exited,
    exception)``, where ``stdout`` and ``stderr`` are strings, ``exited`` is
    an integer, and ``exception`` is an exception object or ``None``.
    """
    hide = normalize_hide(hide)
    exception = False
    if echo:
        print("\033[1;37m%s\033[0m" % command)
    runner_ = runner()
    func = runner_.run_pty if pty else runner_.run
    stdout, stderr, exited, exception = func(command, warn, hide)
    result = Result(
        stdout=stdout,
        stderr=stderr,
        exited=exited,
        pty=pty,
        exception=exception,
    )
    if not (result or warn):
        raise Failure(result)
    return result


class Result(object):
    """
    A container for information about the result of a command execution.

    `Result` instances have the following attributes:

    * ``stdout``: The subprocess' standard output, as a multiline string.
    * ``stderr``: Same as ``stdout`` but containing standard error (unless
      the process was invoked via a pty; see `run`.)
    * ``exited``: An integer representing the subprocess' exit/return code.
    * ``return_code``: An alias to ``exited``.
    * ``ok``: A boolean equivalent to ``exited == 0``.
    * ``failed``: The inverse of ``ok``: ``True`` if the program exited with a
      nonzero return code.
    * ``pty``: A boolean describing whether the subprocess was invoked with a
      pty or not; see `run`.
    * ``exception``: Typically ``None``, but may be an exception object if
      ``pty`` was ``True`` and ``run()`` had to swallow an apparently-spurious
      ``OSError``. Solely for sanity checking/debugging purposes.

    `Result` objects' truth evaluation is equivalent to their ``ok``
    attribute's value.
    """
    # TODO: inherit from namedtuple instead? heh
    def __init__(self, stdout, stderr, exited, pty, exception=None):
        self.exited = self.return_code = exited
        self.stdout = stdout
        self.stderr = stderr
        self.pty = pty
        self.exception = exception

    def __nonzero__(self):
        # Holy mismatch between name and implementation, Batman!
        return self.exited == 0

    # Python 3 ahoy
    def __bool__(self):
        return self.__nonzero__()

    def __str__(self):
        ret = ["Command exited with status %s." % self.exited]
        for x in ('stdout', 'stderr'):
            val = getattr(self, x)
            ret.append("""=== %s ===
%s
""" % (x, val.rstrip()) if val else "(no %s)" % x)
        return "\n".join(ret)

    @property
    def ok(self):
        return self.exited == 0

    @property
    def failed(self):
        return not self.ok

########NEW FILE########
__FILENAME__ = tasks
"""
This module contains the core `.Task` class & convenience decorators used to
generate new tasks.
"""
import inspect
import types

from .vendor import six
from .vendor.lexicon import Lexicon

from .context import Context
from .parser import Argument

if six.PY3:
    from itertools import zip_longest
else:
    from itertools import izip_longest as zip_longest


# Non-None sentinel
NO_DEFAULT = object()


class Task(object):
    """
    Core object representing an executable task & its argument specification.
    """
    # TODO: store these kwarg defaults central, refer to those values both here
    # and in @task.
    # TODO: allow central per-session / per-taskmodule control over some of
    # them, e.g. (auto_)positional, auto_shortflags.
    # NOTE: we shadow __builtins__.help here. It's purposeful. :(
    def __init__(self,
        body,
        name=None,
        contextualized=False,
        aliases=(),
        positional=None,
        optional=(),
        default=False,
        auto_shortflags=True,
        help=None,
        pre=None,
    ):
        # Real callable
        self.body = body
        # Must copy doc/name here because Sphinx is stupid about properties.
        self.__doc__ = getattr(body, '__doc__', '')
        self.__name__ = getattr(body, '__name__', '')
        # Is this a contextualized task?
        self.contextualized = contextualized
        # Default name, alternate names, and whether it should act as the
        # default for its parent collection
        self._name = name
        self.aliases = aliases
        self.is_default = default
        # Arg/flag/parser hints
        self.positional = self.fill_implicit_positionals(positional)
        self.optional = optional
        self.auto_shortflags = auto_shortflags
        self.help = help or {}
        # Call chain bidness
        self.pre = pre or []
        self.times_called = 0

    @property
    def name(self):
        return self._name or self.__name__

    def __str__(self):
        aliases = ""
        if self.aliases:
            aliases = " ({0})".format(', '.join(self.aliases))
        return "<Task {0!r}{1}>".format(self.name, aliases)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        if self.name != other.name:
            return False
        # Functions do not define __eq__ but func_code objects apparently do.
        # (If we're wrapping some other callable, they will be responsible for
        # defining equality on their end.)
        if self.body == other.body:
            return True
        else:
            try:
                return (
                    six.get_function_code(self.body) ==
                    six.get_function_code(other.body)
                )
            except AttributeError:
                return False

    def __hash__(self):
        # Presumes name and body will never be changed. Hrm.
        # Potentially cleaner to just not use Tasks as hash keys, but let's do
        # this for now.
        return hash(self.name) + hash(self.body)

    def __call__(self, *args, **kwargs):
        # Guard against calling contextualized tasks with no context.
        if self.contextualized and not isinstance(args[0], Context):
            raise TypeError("Contextualized task expected a Context, got %s instead!" % type(args[0]))
        result = self.body(*args, **kwargs)
        self.times_called += 1
        return result

    @property
    def called(self):
        return self.times_called > 0

    def argspec(self, body):
        """
        Returns two-tuple:

        * First item is list of arg names, in order defined.

            * I.e. we *cannot* simply use a dict's ``keys()`` method here.

        * Second item is dict mapping arg names to default values or
          task.NO_DEFAULT (i.e. an 'empty' value distinct from None).
        """
        # Handle callable-but-not-function objects
        # TODO: __call__ exhibits the 'self' arg; do we manually nix 1st result
        # in argspec, or is there a way to get the "really callable" spec?
        func = body if isinstance(body, types.FunctionType) else body.__call__
        spec = inspect.getargspec(func)
        arg_names = spec.args[:]
        matched_args = [reversed(x) for x in [spec.args, spec.defaults or []]]
        spec_dict = dict(zip_longest(*matched_args, fillvalue=NO_DEFAULT))
        # Remove context argument, if applicable
        if self.contextualized:
            context_arg = arg_names.pop(0)
            del spec_dict[context_arg]
        return arg_names, spec_dict

    def fill_implicit_positionals(self, positional):
        args, spec_dict = self.argspec(self.body)
        # If positionals is None, everything lacking a default
        # value will be automatically considered positional.
        if positional is None:
            positional = []
            for name in args: # Go in defined order, not dict "order"
                default = spec_dict[name]
                if default is NO_DEFAULT:
                    positional.append(name)
        return positional

    def arg_opts(self, name, default, taken_names):
        opts = {}
        # Whether it's positional or not
        opts['positional'] = name in self.positional
        # Whether it is a value-optional flag
        opts['optional'] = name in self.optional
        # Argument name(s) (replace w/ dashed version if underscores present,
        # and move the underscored version to be the attr_name instead.)
        if '_' in name:
            opts['attr_name'] = name
            name = name.replace('_', '-')
        names = [name]
        if self.auto_shortflags:
            # Must know what short names are available
            for char in name:
                if not (char == name or char in taken_names):
                    names.append(char)
                    break
        opts['names'] = names
        # Handle default value & kind if possible
        if default not in (None, NO_DEFAULT):
            # TODO: allow setting 'kind' explicitly.
            opts['kind'] = type(default)
            opts['default'] = default
        # Help
        if name in self.help:
            opts['help'] = self.help[name]
        return opts

    def get_arguments(self):
        """
        Return a list of Argument objects representing this task's signature.
        """
        # Core argspec
        arg_names, spec_dict = self.argspec(self.body)
        # Obtain list of args + their default values (if any) in
        # declaration/definition order (i.e. based on getargspec())
        tuples = [(x, spec_dict[x]) for x in arg_names]
        # Prime the list of all already-taken names (mostly for help in
        # choosing auto shortflags)
        taken_names = set(x[0] for x in tuples)
        # Build arg list (arg_opts will take care of setting up shortnames,
        # etc)
        args = []
        for name, default in tuples:
            new_arg = Argument(**self.arg_opts(name, default, taken_names))
            args.append(new_arg)
            # Update taken_names list with new argument's full name list
            # (which may include new shortflags) so subsequent Argument
            # creation knows what's taken.
            taken_names.update(set(new_arg.names))
        # Now we need to ensure positionals end up in the front of the list, in
        # order given in self.positionals, so that when Context consumes them,
        # this order is preserved.
        for posarg in reversed(self.positional):
            for i, arg in enumerate(args):
                if arg.name == posarg:
                    args.insert(0, args.pop(i))
                    break
        return args


def task(*args, **kwargs):
    """
    Marks wrapped callable object as a valid Invoke task.

    May be called without any parentheses if no extra options need to be
    specified. Otherwise, the following keyword arguments are allowed in the
    parenthese'd form:

    * ``name``: Default name to use when binding to a `.Collection`. Useful for
      avoiding Python namespace issues (i.e. when the desired CLI level name
      can't or shouldn't be used as the Python level name.)
    * ``contextualized``: Hints to callers (especially the CLI) that this task
      expects to be given a `~invoke.context.Context` object as its first
      argument when called.
    * ``aliases``: Specify one or more aliases for this task, allowing it to be
      invoked as multiple different names. For example, a task named ``mytask``
      with a simple ``@task`` wrapper may only be invoked as ``"mytask"``.
      Changing the decorator to be ``@task(aliases=['myothertask'])`` allows
      invocation as ``"mytask"`` *or* ``"myothertask"``.
    * ``positional``: Iterable overriding the parser's automatic "args with no
      default value are considered positional" behavior. If a list of arg
      names, no args besides those named in this iterable will be considered
      positional. (This means that an empty list will force all arguments to be
      given as explicit flags.)
    * ``optional``: Iterable of argument names, declaring those args to
      have :ref:`optional values <optional-values>`. Such arguments may be
      given as value-taking options (e.g. ``--my-arg=myvalue``, wherein the
      task is given ``"myvalue"``) or as Boolean flags (``--my-arg``, resulting
      in ``True``).
    * ``default``: Boolean option specifying whether this task should be its
      collection's default task (i.e. called if the collection's own name is
      given.)
    * ``auto_shortflags``: Whether or not to automatically create short
      flags from task options; defaults to True.
    * ``help``: Dict mapping argument names to their help strings. Will be
      displayed in ``--help`` output.
    * ``pre``: List of task objects to execute prior to the
      wrapped task whenever it is executed.

    If any non-keyword arguments are given, they are taken as the value of the
    ``pre`` kwarg for convenience's sake. (It is an error to give both
    ``*args`` and ``pre`` at the same time.)
    """
    # @task -- no options were (probably) given.
    # Also handles ctask's use case when given as @ctask, equivalent to
    # @task(obj, contextualized=True).
    if len(args) == 1 and callable(args[0]) and not isinstance(args[0], Task):
        return Task(args[0], **kwargs)
    # @task(pre, tasks, here)
    if args:
        if 'pre' in kwargs:
            raise TypeError("May not give *args and 'pre' kwarg simultaneously!")
        kwargs['pre'] = args
    # @task(options)
    # TODO: pull in centrally defined defaults here (see Task)
    name = kwargs.pop('name', None)
    contextualized = kwargs.pop('contextualized', False)
    aliases = kwargs.pop('aliases', ())
    positional = kwargs.pop('positional', None)
    optional = tuple(kwargs.pop('optional', ()))
    default = kwargs.pop('default', False)
    auto_shortflags = kwargs.pop('auto_shortflags', True)
    help = kwargs.pop('help', {})
    pre = kwargs.pop('pre', [])
    # Handle unknown kwargs
    if kwargs:
        kwarg = (" unknown kwargs %r" % (kwargs,)) if kwargs else ""
        raise TypeError("@task was called with" + kwarg)
    def inner(obj):
        obj = Task(
            obj,
            name=name,
            contextualized=contextualized,
            aliases=aliases,
            positional=positional,
            optional=optional,
            default=default,
            auto_shortflags=auto_shortflags,
            help=help,
            pre=pre
        )
        return obj
    return inner


def ctask(*args, **kwargs):
    """
    Wrapper for `.task` which sets ``contextualized=True`` by default.

    Please see `.task` for documentation.
    """
    kwargs.setdefault('contextualized', True)
    return task(*args, **kwargs)


class Call(object):
    """
    Represents a call/execution of a `.Task` with some arguments.

    Wraps its `.Task` so it can be treated as one by `.Executor`.

    Similar to `~functools.partial` with some added functionality.
    """
    def __init__(self, task, *args, **kwargs):
        self.task = task
        self.args = args
        self.kwargs = kwargs

    @property
    def called(self):
        return self.task.called

# Convenience/aesthetically pleasing-ish alias
call = Call

########NEW FILE########
__FILENAME__ = util
import fcntl
import logging
import os
import struct
import sys
import termios


def enable_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(module)s: %(message)s",
    )

# Allow from-the-start debugging (vs toggled during load of tasks module) via
# shell env var.
if os.environ.get('INVOKE_DEBUG'):
    enable_logging()

# Add top level logger functions to global namespace. Meh.
log = logging.getLogger('invoke')
for x in ('debug',):
    globals()[x] = getattr(log, x)


def pty_size():
    """
    Return local (stdout-based) pty size as ``(num_cols, num_rows)`` tuple.

    If unable to determine (e.g. ``sys.stdout`` has been monkeypatched, or
    ``termios`` lacking ``TIOCGWINSZ``) defaults to 80x24.
    """
    default_cols, default_rows = 80, 24
    cols, rows = default_cols, default_rows
    if sys.stdout.isatty():
        # We want two short unsigned integers (rows, cols)
        fmt = 'HH'
        # Create an empty (zeroed) buffer for ioctl to map onto. Yay for C!
        buffer = struct.pack(fmt, 0, 0)
        # Call TIOCGWINSZ to get window size of stdout, returns our filled
        # buffer
        try:
            result = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ,
                buffer)
            # Unpack buffer back into Python data types
            # NOTE: this unpack gives us rows x cols, but we return the
            # inverse.
            rows, cols = struct.unpack(fmt, result)
            # Fall back to defaults if TIOCGWINSZ returns unreasonable values
            if rows == 0:
                rows = default_rows
            if cols == 0:
                cols = default_cols
        # Deal with e.g. sys.stdout being monkeypatched, such as in testing.
        # Or termios not having a TIOCGWINSZ.
        except AttributeError:
            pass
    return cols, rows

########NEW FILE########
__FILENAME__ = backwardscompat
import sys

if sys.version_info >= (3,):
    def callable(obj):
        return hasattr(obj, '__call__')
else:
    callable = callable


########NEW FILE########
__FILENAME__ = machine
import re
import inspect
from .backwardscompat import callable

# metaclass implementation idea from
# http://blog.ianbicking.org/more-on-python-metaprogramming-comment-14.html
_transition_gatherer = []

def transition(event, from_, to, action=None, guard=None):
    _transition_gatherer.append([event, from_, to, action, guard])

_state_gatherer = []

def state(name, enter=None, exit=None):
    _state_gatherer.append([name, enter, exit])


class MetaStateMachine(type):

    def __new__(cls, name, bases, dictionary):
        global _transition_gatherer, _state_gatherer
        Machine = super(MetaStateMachine, cls).__new__(cls, name, bases, dictionary)
        Machine._class_transitions = []
        Machine._class_states = {}
        for s in _state_gatherer:
            Machine._add_class_state(*s)
        for i in _transition_gatherer:
            Machine._add_class_transition(*i)
        _transition_gatherer = []
        _state_gatherer = []
        return Machine


StateMachineBase = MetaStateMachine('StateMachineBase', (object, ), {})


class StateMachine(StateMachineBase):

    def __init__(self):
        self._bring_definitions_to_object_level()
        self._inject_into_parts()
        self._validate_machine_definitions()
        if callable(self.initial_state):
            self.initial_state = self.initial_state()
        self._current_state_object = self._state_by_name(self.initial_state)
        self._current_state_object.run_enter(self)
        self._create_state_getters()

    def __new__(cls, *args, **kwargs):
        obj = super(StateMachine, cls).__new__(cls)
        obj._states = {}
        obj._transitions = []
        return obj

    def _bring_definitions_to_object_level(self):
        self._states.update(self.__class__._class_states)
        self._transitions.extend(self.__class__._class_transitions)

    def _inject_into_parts(self):
        for collection in [self._states.values(), self._transitions]:
            for component in collection:
                component.machine = self

    def _validate_machine_definitions(self):
        if len(self._states) < 2:
            raise InvalidConfiguration('There must be at least two states')
        if not getattr(self, 'initial_state', None):
            raise InvalidConfiguration('There must exist an initial state')

    @classmethod
    def _add_class_state(cls, name, enter, exit):
        cls._class_states[name] = _State(name, enter, exit)

    def add_state(self, name, enter=None, exit=None):
        state = _State(name, enter, exit)
        setattr(self, state.getter_name(), state.getter_method().__get__(self, self.__class__))
        self._states[name] = state

    def _current_state_name(self):
        return self._current_state_object.name

    current_state = property(_current_state_name)

    def changing_state(self, from_, to):
        """
        This method is called whenever a state change is executed
        """
        pass

    def _new_state(self, state):
        self.changing_state(self._current_state_object.name, state.name)
        self._current_state_object = state

    def _state_objects(self):
        return list(self._states.values())

    def states(self):
        return [s.name for s in self._state_objects()]

    @classmethod
    def _add_class_transition(cls, event, from_, to, action, guard):
        transition = _Transition(event, [cls._class_states[s] for s in _listize(from_)],
            cls._class_states[to], action, guard)
        cls._class_transitions.append(transition)
        setattr(cls, event, transition.event_method())

    def add_transition(self, event, from_, to, action=None, guard=None):
        transition = _Transition(event, [self._state_by_name(s) for s in _listize(from_)],
            self._state_by_name(to), action, guard)
        self._transitions.append(transition)
        setattr(self, event, transition.event_method().__get__(self, self.__class__))

    def _process_transitions(self, event_name, *args, **kwargs):
        transitions = self._transitions_by_name(event_name)
        transitions = self._ensure_from_validity(transitions)
        this_transition = self._check_guards(transitions)
        this_transition.run(self, *args, **kwargs)

    def _create_state_getters(self):
        for state in self._state_objects():
            setattr(self, state.getter_name(), state.getter_method().__get__(self, self.__class__))

    def _state_by_name(self, name):
        for state in self._state_objects():
            if state.name == name:
                return state

    def _transitions_by_name(self, name):
        return list(filter(lambda transition: transition.event == name, self._transitions))

    def _ensure_from_validity(self, transitions):
        valid_transitions = list(filter(
          lambda transition: transition.is_valid_from(self._current_state_object),
          transitions))
        if len(valid_transitions) == 0:
            raise InvalidTransition("Cannot %s from %s" % (
                transitions[0].event, self.current_state))
        return valid_transitions

    def _check_guards(self, transitions):
        allowed_transitions = []
        for transition in transitions:
            if transition.check_guard(self):
                allowed_transitions.append(transition)
        if len(allowed_transitions) == 0:
            raise GuardNotSatisfied("Guard is not satisfied for this transition")
        elif len(allowed_transitions) > 1:
            raise ForkedTransition("More than one transition was allowed for this event")
        return allowed_transitions[0]


class _Transition(object):

    def __init__(self, event, from_, to, action, guard):
        self.event = event
        self.from_ = from_
        self.to = to
        self.action = action
        self.guard = _Guard(guard)

    def event_method(self):
        def generated_event(machine, *args, **kwargs):
            these_transitions = machine._process_transitions(self.event, *args, **kwargs)
        generated_event.__doc__ = 'event %s' % self.event
        generated_event.__name__ = self.event
        return generated_event

    def is_valid_from(self, from_):
        return from_ in _listize(self.from_)

    def check_guard(self, machine):
        return self.guard.check(machine)

    def run(self, machine, *args, **kwargs):
        machine._current_state_object.run_exit(machine)
        machine._new_state(self.to)
        self.to.run_enter(machine)
        _ActionRunner(machine).run(self.action, *args, **kwargs)


class _Guard(object):

    def __init__(self, action):
        self.action = action

    def check(self, machine):
        if self.action is None:
            return True
        items = _listize(self.action)
        result = True
        for item in items:
            result = result and self._evaluate(machine, item)
        return result

    def _evaluate(self, machine, item):
        if callable(item):
            return item(machine)
        else:
            guard = getattr(machine, item)
            if callable(guard):
                guard = guard()
            return guard


class _State(object):

    def __init__(self, name, enter, exit):
        self.name = name
        self.enter = enter
        self.exit = exit

    def getter_name(self):
        return 'is_%s' % self.name

    def getter_method(self):
        def state_getter(self_machine):
            return self_machine.current_state == self.name
        return state_getter

    def run_enter(self, machine):
        _ActionRunner(machine).run(self.enter)

    def run_exit(self, machine):
        _ActionRunner(machine).run(self.exit)


class _ActionRunner(object):

    def __init__(self, machine):
        self.machine = machine

    def run(self, action_param, *args, **kwargs):
        if not action_param:
            return
        action_items = _listize(action_param)
        for action_item in action_items:
            self._run_action(action_item, *args, **kwargs)

    def _run_action(self, action, *args, **kwargs):
        if callable(action):
            self._try_to_run_with_args(action, self.machine, *args, **kwargs)
        else:
            self._try_to_run_with_args(getattr(self.machine, action), *args, **kwargs)

    def _try_to_run_with_args(self, action, *args, **kwargs):
        try:
            action(*args, **kwargs)
        except TypeError:
            action()


class InvalidConfiguration(Exception):
    pass


class InvalidTransition(Exception):
    pass


class GuardNotSatisfied(Exception):
    pass


class ForkedTransition(Exception):
    pass


def _listize(value):
    return type(value) in [list, tuple] and value or [value]


########NEW FILE########
__FILENAME__ = alias_dict
# Normal import
try:
    import six
# Horrible, awful hack to work when vendorized
except ImportError:
    from .. import six


class AliasDict(dict):
    def __init__(self, *args, **kwargs):
        super(AliasDict, self).__init__(*args, **kwargs)
        self.aliases = {}

    def alias(self, from_, to):
        self.aliases[from_] = to

    def unalias(self, from_):
        del self.aliases[from_]

    def aliases_of(self, name):
        """
        Returns other names for given real key or alias ``name``.

        If given a real key, returns its aliases.

        If given an alias, returns the real key it points to, plus any other
        aliases of that real key. (The given alias itself is not included in
        the return value.)
        """
        names = []
        key = name
        # self.aliases keys are aliases, not realkeys. Easy test to see if we
        # should flip around to the POV of a realkey when given an alias.
        if name in self.aliases:
            key = self.aliases[name]
            # Ensure the real key shows up in output.
            names.append(key)
        # 'key' is now a realkey, whose aliases are all keys whose value is
        # itself. Filter out the original name given.
        names.extend([
            k for k,v
            in six.iteritems(self.aliases)
            if v == key and k != name
        ])
        return names

    def _handle(self, key, value, single, multi, unaliased):
        # Attribute existence test required to not blow up when deepcopy'd
        if key in getattr(self, 'aliases', {}):
            target = self.aliases[key]
            # Single-string targets
            if isinstance(target, six.string_types):
                return single(self, target, value)
            # Multi-string targets
            else:
                if multi:
                    return multi(self, target, value)
                else:
                    for subkey in target:
                        single(self, subkey, value)
        else:
            return unaliased(self, key, value)

    def _single(self, target):
        return isinstance(target, six.string_types)

    def __setitem__(self, key, value):
        def single(d, target, value): d[target] = value
        def unaliased(d, key, value): super(AliasDict, d).__setitem__(key, value)
        return self._handle(key, value, single, None, unaliased)

    def __getitem__(self, key):
        def single(d, target, value): return d[target]
        def unaliased(d, key, value): return super(AliasDict, d).__getitem__(key)

        def multi(d, target, value):
            msg = "Multi-target aliases have no well-defined value and can't be read."
            raise ValueError(msg)

        return self._handle(key, None, single, multi, unaliased)

    def __contains__(self, key):
        def single(d, target, value): return target in d

        def multi(d, target, value):
            return all(subkey in self for subkey in self.aliases[key])

        def unaliased(d, key, value):
            return super(AliasDict, d).__contains__(key)

        return self._handle(key, None, single, multi, unaliased)

    def __delitem__(self, key):
        def single(d, target, value): del d[target]

        def unaliased(d, key, value):
            return super(AliasDict, d).__delitem__(key)

        return self._handle(key, None, single, None, unaliased)

########NEW FILE########
__FILENAME__ = attribute_dict
class AttributeDict(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            # to conform with __getattr__ spec
            raise AttributeError(key)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        del self[key]

########NEW FILE########
__FILENAME__ = pexpect
"""Pexpect is a Python module for spawning child applications and controlling
them automatically. Pexpect can be used for automating interactive applications
such as ssh, ftp, passwd, telnet, etc. It can be used to a automate setup
scripts for duplicating software package installations on different servers. It
can be used for automated software testing. Pexpect is in the spirit of Don
Libes' Expect, but Pexpect is pure Python. Other Expect-like modules for Python
require TCL and Expect or require C extensions to be compiled. Pexpect does not
use C, Expect, or TCL extensions. It should work on any platform that supports
the standard Python pty module. The Pexpect interface focuses on ease of use so
that simple tasks are easy.

There are two main interfaces to the Pexpect system; these are the function,
run() and the class, spawn. The spawn class is more powerful. The run()
function is simpler than spawn, and is good for quickly calling program. When
you call the run() function it executes a given program and then returns the
output. This is a handy replacement for os.system().

For example::

    pexpect.run('ls -la')

The spawn class is the more powerful interface to the Pexpect system. You can
use this to spawn a child program then interact with it by sending input and
expecting responses (waiting for patterns in the child's output).

For example::

    child = pexpect.spawn('scp foo myname@host.example.com:.')
    child.expect ('Password:')
    child.sendline (mypassword)

This works even for commands that ask for passwords or other input outside of
the normal stdio streams. For example, ssh reads input directly from the TTY
device which bypasses stdin.

Credits: Noah Spurrier, Richard Holden, Marco Molteni, Kimberley Burchett,
Robert Stone, Hartmut Goebel, Chad Schroeder, Erick Tryzelaar, Dave Kirby, Ids
vander Molen, George Todd, Noel Taylor, Nicolas D. Cesar, Alexander Gattin,
Jacques-Etienne Baudoux, Geoffrey Marshall, Francisco Lourenco, Glen Mabey,
Karthik Gurusamy, Fernando Perez, Corey Minyard, Jon Cohen, Guillaume
Chazarain, Andrew Ryan, Nick Craig-Wood, Andrew Stone, Jorgen Grahn, John
Spiegel, Jan Grant, Shane Kerr and Thomas Kluyver. Let me know if I forgot anyone.

Pexpect is free, open source, and all that good stuff.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Pexpect Copyright (c) 2010 Noah Spurrier
http://pexpect.sourceforge.net/
"""

try:
    import os, sys, time
    import select
    import re
    import struct
    import resource
    import types
    import pty
    import tty
    import termios
    import fcntl
    import errno
    import traceback
    import signal
except ImportError as e:
    raise ImportError (str(e) + """

A critical module was not found. Probably this operating system does not
support it. Pexpect is intended for UNIX-like operating systems.""")

# Python 3 support - vendorized
from . import six

__version__ = '2.5.2'
version = __version__
version_info = (2,5,2)
__all__ = ['ExceptionPexpect', 'EOF', 'TIMEOUT', 'spawn', 'spawnb', 'run', 'which',
    'split_command_line', '__version__']

# Exception classes used by this module.
class ExceptionPexpect(Exception):

    """Base class for all exceptions raised by this module.
    """

    def __init__(self, value):

        self.value = value

    def __str__(self):

        return str(self.value)

    def get_trace(self):

        """This returns an abbreviated stack trace with lines that only concern
        the caller. In other words, the stack trace inside the Pexpect module
        is not included. """

        tblist = traceback.extract_tb(sys.exc_info()[2])
        #tblist = filter(self.__filter_not_pexpect, tblist)
        tblist = [item for item in tblist if self.__filter_not_pexpect(item)]
        tblist = traceback.format_list(tblist)
        return ''.join(tblist)

    def __filter_not_pexpect(self, trace_list_item):

        """This returns True if list item 0 the string 'pexpect.py' in it. """

        if trace_list_item[0].find('pexpect.py') == -1:
            return True
        else:
            return False

class EOF(ExceptionPexpect):

    """Raised when EOF is read from a child. This usually means the child has exited."""

class TIMEOUT(ExceptionPexpect):

    """Raised when a read time exceeds the timeout. """

##class TIMEOUT_PATTERN(TIMEOUT):
##    """Raised when the pattern match time exceeds the timeout.
##    This is different than a read TIMEOUT because the child process may
##    give output, thus never give a TIMEOUT, but the output
##    may never match a pattern.
##    """
##class MAXBUFFER(ExceptionPexpect):
##    """Raised when a scan buffer fills before matching an expected pattern."""

PY3 = six.PY3

def _cast_bytes(s, enc):
    if isinstance(s, unicode):
        return s.encode(enc)
    return s

def _cast_unicode(s, enc):
    if isinstance(s, bytes):
        return s.decode(enc)
    return s

re_type = type(re.compile(''))

def run (command, timeout=-1, withexitstatus=False, events=None, extra_args=None,
         logfile=None, cwd=None, env=None, encoding='utf-8'):

    """
    This function runs the given command; waits for it to finish; then
    returns all output as a string. STDERR is included in output. If the full
    path to the command is not given then the path is searched.

    Note that lines are terminated by CR/LF (\\r\\n) combination even on
    UNIX-like systems because this is the standard for pseudo ttys. If you set
    'withexitstatus' to true, then run will return a tuple of (command_output,
    exitstatus). If 'withexitstatus' is false then this returns just
    command_output.

    The run() function can often be used instead of creating a spawn instance.
    For example, the following code uses spawn::

        from pexpect import *
        child = spawn('scp foo myname@host.example.com:.')
        child.expect ('(?i)password')
        child.sendline (mypassword)

    The previous code can be replace with the following::

        from pexpect import *
        run ('scp foo myname@host.example.com:.', events={'(?i)password': mypassword})

    Examples
    ========

    Start the apache daemon on the local machine::

        from pexpect import *
        run ("/usr/local/apache/bin/apachectl start")

    Check in a file using SVN::

        from pexpect import *
        run ("svn ci -m 'automatic commit' my_file.py")

    Run a command and capture exit status::

        from pexpect import *
        (command_output, exitstatus) = run ('ls -l /bin', withexitstatus=1)

    Tricky Examples
    ===============

    The following will run SSH and execute 'ls -l' on the remote machine. The
    password 'secret' will be sent if the '(?i)password' pattern is ever seen::

        run ("ssh username@machine.example.com 'ls -l'", events={'(?i)password':'secret\\n'})

    This will start mencoder to rip a video from DVD. This will also display
    progress ticks every 5 seconds as it runs. For example::

        from pexpect import *
        def print_ticks(d):
            print d['event_count'],
        run ("mencoder dvd://1 -o video.avi -oac copy -ovc copy", events={TIMEOUT:print_ticks}, timeout=5)

    The 'events' argument should be a dictionary of patterns and responses.
    Whenever one of the patterns is seen in the command out run() will send the
    associated response string. Note that you should put newlines in your
    string if Enter is necessary. The responses may also contain callback
    functions. Any callback is function that takes a dictionary as an argument.
    The dictionary contains all the locals from the run() function, so you can
    access the child spawn object or any other variable defined in run()
    (event_count, child, and extra_args are the most useful). A callback may
    return True to stop the current run process otherwise run() continues until
    the next event. A callback may also return a string which will be sent to
    the child. 'extra_args' is not used by directly run(). It provides a way to
    pass data to a callback function through run() through the locals
    dictionary passed to a callback."""

    if timeout == -1:
        child = spawn(command, maxread=2000, logfile=logfile, cwd=cwd, env=env,
                      encoding=encoding)
    else:
        child = spawn(command, timeout=timeout, maxread=2000, logfile=logfile,
                      cwd=cwd, env=env, encoding=encoding)
    if events is not None:
        patterns = events.keys()
        responses = events.values()
    else:
        patterns=None # We assume that EOF or TIMEOUT will save us.
        responses=None
    child_result_list = []
    event_count = 0
    while 1:
        try:
            index = child.expect (patterns)
            if isinstance(child.after, basestring):
                child_result_list.append(child.before + child.after)
            else: # child.after may have been a TIMEOUT or EOF, so don't cat those.
                child_result_list.append(child.before)
            if isinstance(responses[index], basestring):
                child.send(responses[index])
            elif type(responses[index]) is types.FunctionType:
                callback_result = responses[index](locals())
                sys.stdout.flush()
                if isinstance(callback_result, basestring):
                    child.send(callback_result)
                elif callback_result:
                    break
            else:
                raise TypeError ('The callback must be a string or function type.')
            event_count = event_count + 1
        except TIMEOUT as e:
            child_result_list.append(child.before)
            break
        except EOF as e:
            child_result_list.append(child.before)
            break
    child_result = child._empty_buffer.join(child_result_list)
    if withexitstatus:
        child.close()
        return (child_result, child.exitstatus)
    else:
        return child_result

class spawnb(object):
    """Use this class to start and control child applications with a pure-bytes
    interface."""
    
    _buffer_type = bytes
    def _cast_buffer_type(self, s):
        return _cast_bytes(s, self.encoding)
    _empty_buffer = b''
    _pty_newline = b'\r\n'
    
    # Some code needs this to exist, but it's mainly for the spawn subclass.
    encoding = 'utf-8'

    def __init__(self, command, args=[], timeout=30, maxread=2000, searchwindowsize=None,
                 logfile=None, cwd=None, env=None):

        """This is the constructor. The command parameter may be a string that
        includes a command and any arguments to the command. For example::

            child = pexpect.spawn ('/usr/bin/ftp')
            child = pexpect.spawn ('/usr/bin/ssh user@example.com')
            child = pexpect.spawn ('ls -latr /tmp')

        You may also construct it with a list of arguments like so::

            child = pexpect.spawn ('/usr/bin/ftp', [])
            child = pexpect.spawn ('/usr/bin/ssh', ['user@example.com'])
            child = pexpect.spawn ('ls', ['-latr', '/tmp'])

        After this the child application will be created and will be ready to
        talk to. For normal use, see expect() and send() and sendline().

        Remember that Pexpect does NOT interpret shell meta characters such as
        redirect, pipe, or wild cards (>, |, or *). This is a common mistake.
        If you want to run a command and pipe it through another command then
        you must also start a shell. For example::

            child = pexpect.spawn('/bin/bash -c "ls -l | grep LOG > log_list.txt"')
            child.expect(pexpect.EOF)

        The second form of spawn (where you pass a list of arguments) is useful
        in situations where you wish to spawn a command and pass it its own
        argument list. This can make syntax more clear. For example, the
        following is equivalent to the previous example::

            shell_cmd = 'ls -l | grep LOG > log_list.txt'
            child = pexpect.spawn('/bin/bash', ['-c', shell_cmd])
            child.expect(pexpect.EOF)

        The maxread attribute sets the read buffer size. This is maximum number
        of bytes that Pexpect will try to read from a TTY at one time. Setting
        the maxread size to 1 will turn off buffering. Setting the maxread
        value higher may help performance in cases where large amounts of
        output are read back from the child. This feature is useful in
        conjunction with searchwindowsize.

        The searchwindowsize attribute sets the how far back in the incomming
        seach buffer Pexpect will search for pattern matches. Every time
        Pexpect reads some data from the child it will append the data to the
        incomming buffer. The default is to search from the beginning of the
        imcomming buffer each time new data is read from the child. But this is
        very inefficient if you are running a command that generates a large
        amount of data where you want to match The searchwindowsize does not
        effect the size of the incomming data buffer. You will still have
        access to the full buffer after expect() returns.

        The logfile member turns on or off logging. All input and output will
        be copied to the given file object. Set logfile to None to stop
        logging. This is the default. Set logfile to sys.stdout to echo
        everything to standard output. The logfile is flushed after each write.

        Example log input and output to a file::

            child = pexpect.spawn('some_command')
            fout = open('mylog.txt','w')
            child.logfile = fout

        Example log to stdout::

            child = pexpect.spawn('some_command')
            child.logfile = sys.stdout

        The logfile_read and logfile_send members can be used to separately log
        the input from the child and output sent to the child. Sometimes you
        don't want to see everything you write to the child. You only want to
        log what the child sends back. For example::

            child = pexpect.spawn('some_command')
            child.logfile_read = sys.stdout

        To separately log output sent to the child use logfile_send::

            self.logfile_send = fout

        The delaybeforesend helps overcome a weird behavior that many users
        were experiencing. The typical problem was that a user would expect() a
        "Password:" prompt and then immediately call sendline() to send the
        password. The user would then see that their password was echoed back
        to them. Passwords don't normally echo. The problem is caused by the
        fact that most applications print out the "Password" prompt and then
        turn off stdin echo, but if you send your password before the
        application turned off echo, then you get your password echoed.
        Normally this wouldn't be a problem when interacting with a human at a
        real keyboard. If you introduce a slight delay just before writing then
        this seems to clear up the problem. This was such a common problem for
        many users that I decided that the default pexpect behavior should be
        to sleep just before writing to the child application. 1/20th of a
        second (50 ms) seems to be enough to clear up the problem. You can set
        delaybeforesend to 0 to return to the old behavior. Most Linux machines
        don't like this to be below 0.03. I don't know why.

        Note that spawn is clever about finding commands on your path.
        It uses the same logic that "which" uses to find executables.

        If you wish to get the exit status of the child you must call the
        close() method. The exit or signal status of the child will be stored
        in self.exitstatus or self.signalstatus. If the child exited normally
        then exitstatus will store the exit return code and signalstatus will
        be None. If the child was terminated abnormally with a signal then
        signalstatus will store the signal value and exitstatus will be None.
        If you need more detail you can also read the self.status member which
        stores the status returned by os.waitpid. You can interpret this using
        os.WIFEXITED/os.WEXITSTATUS or os.WIFSIGNALED/os.TERMSIG. """

        self.STDIN_FILENO = pty.STDIN_FILENO
        self.STDOUT_FILENO = pty.STDOUT_FILENO
        self.STDERR_FILENO = pty.STDERR_FILENO
        self.stdin = sys.stdin
        self.stdout = sys.stdout
        self.stderr = sys.stderr

        self.searcher = None
        self.ignorecase = False
        self.before = None
        self.after = None
        self.match = None
        self.match_index = None
        self.terminated = True
        self.exitstatus = None
        self.signalstatus = None
        self.status = None # status returned by os.waitpid
        self.flag_eof = False
        self.pid = None
        self.child_fd = -1 # initially closed
        self.timeout = timeout
        self.delimiter = EOF
        self.logfile = logfile
        self.logfile_read = None # input from child (read_nonblocking)
        self.logfile_send = None # output to send (send, sendline)
        self.maxread = maxread # max bytes to read at one time into buffer
        self.buffer = self._empty_buffer # This is the read buffer. See maxread.
        self.searchwindowsize = searchwindowsize # Anything before searchwindowsize point is preserved, but not searched.
        # Most Linux machines don't like delaybeforesend to be below 0.03 (30 ms).
        self.delaybeforesend = 0.05 # Sets sleep time used just before sending data to child. Time in seconds.
        self.delayafterclose = 0.1 # Sets delay in close() method to allow kernel time to update process status. Time in seconds.
        self.delayafterterminate = 0.1 # Sets delay in terminate() method to allow kernel time to update process status. Time in seconds.
        self.softspace = False # File-like object.
        self.name = '<' + repr(self) + '>' # File-like object.
        self.closed = True # File-like object.
        self.cwd = cwd
        self.env = env
        self.__irix_hack = (sys.platform.lower().find('irix')>=0) # This flags if we are running on irix
        # Solaris uses internal __fork_pty(). All others use pty.fork().
        if 'solaris' in sys.platform.lower() or 'sunos5' in sys.platform.lower():
            self.use_native_pty_fork = False
        else:
            self.use_native_pty_fork = True


        # allow dummy instances for subclasses that may not use command or args.
        if command is None:
            self.command = None
            self.args = None
            self.name = '<pexpect factory incomplete>'
        else:
            self._spawn (command, args)

    def __del__(self):

        """This makes sure that no system resources are left open. Python only
        garbage collects Python objects. OS file descriptors are not Python
        objects, so they must be handled explicitly. If the child file
        descriptor was opened outside of this class (passed to the constructor)
        then this does not close it. """

        if not self.closed:
            # It is possible for __del__ methods to execute during the
            # teardown of the Python VM itself. Thus self.close() may
            # trigger an exception because os.close may be None.
            # -- Fernando Perez
            try:
                self.close()
            except:
                pass

    def __str__(self):

        """This returns a human-readable string that represents the state of
        the object. """

        s = []
        s.append(repr(self))
        s.append('version: ' + __version__)
        s.append('command: ' + str(self.command))
        s.append('args: ' + str(self.args))
        s.append('searcher: ' + str(self.searcher))
        s.append('buffer (last 100 chars): ' + str(self.buffer)[-100:])
        s.append('before (last 100 chars): ' + str(self.before)[-100:])
        s.append('after: ' + str(self.after))
        s.append('match: ' + str(self.match))
        s.append('match_index: ' + str(self.match_index))
        s.append('exitstatus: ' + str(self.exitstatus))
        s.append('flag_eof: ' + str(self.flag_eof))
        s.append('pid: ' + str(self.pid))
        s.append('child_fd: ' + str(self.child_fd))
        s.append('closed: ' + str(self.closed))
        s.append('timeout: ' + str(self.timeout))
        s.append('delimiter: ' + str(self.delimiter))
        s.append('logfile: ' + str(self.logfile))
        s.append('logfile_read: ' + str(self.logfile_read))
        s.append('logfile_send: ' + str(self.logfile_send))
        s.append('maxread: ' + str(self.maxread))
        s.append('ignorecase: ' + str(self.ignorecase))
        s.append('searchwindowsize: ' + str(self.searchwindowsize))
        s.append('delaybeforesend: ' + str(self.delaybeforesend))
        s.append('delayafterclose: ' + str(self.delayafterclose))
        s.append('delayafterterminate: ' + str(self.delayafterterminate))
        return '\n'.join(s)

    def _spawn(self,command,args=[]):

        """This starts the given command in a child process. This does all the
        fork/exec type of stuff for a pty. This is called by __init__. If args
        is empty then command will be parsed (split on spaces) and args will be
        set to parsed arguments. """

        # The pid and child_fd of this object get set by this method.
        # Note that it is difficult for this method to fail.
        # You cannot detect if the child process cannot start.
        # So the only way you can tell if the child process started
        # or not is to try to read from the file descriptor. If you get
        # EOF immediately then it means that the child is already dead.
        # That may not necessarily be bad because you may haved spawned a child
        # that performs some task; creates no stdout output; and then dies.

        # If command is an int type then it may represent a file descriptor.
        if type(command) == type(0):
            raise ExceptionPexpect ('Command is an int type. If this is a file descriptor then maybe you want to use fdpexpect.fdspawn which takes an existing file descriptor instead of a command string.')

        if type (args) != type([]):
            raise TypeError ('The argument, args, must be a list.')

        if args == []:
            self.args = split_command_line(command)
            self.command = self.args[0]
        else:
            self.args = args[:] # work with a copy
            self.args.insert (0, command)
            self.command = command

        command_with_path = which(self.command)
        if command_with_path is None:
            raise ExceptionPexpect ('The command was not found or was not executable: %s.' % self.command)
        self.command = command_with_path
        self.args[0] = self.command

        self.name = '<' + ' '.join (self.args) + '>'

        assert self.pid is None, 'The pid member should be None.'
        assert self.command is not None, 'The command member should not be None.'

        if self.use_native_pty_fork:
            try:
                self.pid, self.child_fd = pty.fork()
            except OSError as e:
                raise ExceptionPexpect('Error! pty.fork() failed: ' + str(e))
        else: # Use internal __fork_pty
            self.pid, self.child_fd = self.__fork_pty()

        if self.pid == 0: # Child
            try:
                self.child_fd = sys.stdout.fileno() # used by setwinsize()
                self.setwinsize(24, 80)
            except:
                # Some platforms do not like setwinsize (Cygwin).
                # This will cause problem when running applications that
                # are very picky about window size.
                # This is a serious limitation, but not a show stopper.
                pass
            # Do not allow child to inherit open file descriptors from parent.
            max_fd = resource.getrlimit(resource.RLIMIT_NOFILE)[0]
            for i in range (3, max_fd):
                try:
                    os.close (i)
                except OSError:
                    pass

            # I don't know why this works, but ignoring SIGHUP fixes a
            # problem when trying to start a Java daemon with sudo
            # (specifically, Tomcat).
            signal.signal(signal.SIGHUP, signal.SIG_IGN)

            if self.cwd is not None:
                os.chdir(self.cwd)
            if self.env is None:
                os.execv(self.command, self.args)
            else:
                os.execvpe(self.command, self.args, self.env)

        # Parent
        self.terminated = False
        self.closed = False

    def __fork_pty(self):

        """This implements a substitute for the forkpty system call. This
        should be more portable than the pty.fork() function. Specifically,
        this should work on Solaris.

        Modified 10.06.05 by Geoff Marshall: Implemented __fork_pty() method to
        resolve the issue with Python's pty.fork() not supporting Solaris,
        particularly ssh. Based on patch to posixmodule.c authored by Noah
        Spurrier::

            http://mail.python.org/pipermail/python-dev/2003-May/035281.html

        """

        parent_fd, child_fd = os.openpty()
        if parent_fd < 0 or child_fd < 0:
            raise ExceptionPexpect("Error! Could not open pty with os.openpty().")

        pid = os.fork()
        if pid < 0:
            raise ExceptionPexpect("Error! Failed os.fork().")
        elif pid == 0:
            # Child.
            os.close(parent_fd)
            self.__pty_make_controlling_tty(child_fd)

            os.dup2(child_fd, 0)
            os.dup2(child_fd, 1)
            os.dup2(child_fd, 2)

            if child_fd > 2:
                os.close(child_fd)
        else:
            # Parent.
            os.close(child_fd)

        return pid, parent_fd

    def __pty_make_controlling_tty(self, tty_fd):

        """This makes the pseudo-terminal the controlling tty. This should be
        more portable than the pty.fork() function. Specifically, this should
        work on Solaris. """

        child_name = os.ttyname(tty_fd)

        # Disconnect from controlling tty. Harmless if not already connected.
        try:
            fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY);
            if fd >= 0:
                os.close(fd)
        except:
            # Already disconnected. This happens if running inside cron.
            pass

        os.setsid()

        # Verify we are disconnected from controlling tty
        # by attempting to open it again.
        try:
            fd = os.open("/dev/tty", os.O_RDWR | os.O_NOCTTY);
            if fd >= 0:
                os.close(fd)
                raise ExceptionPexpect("Error! Failed to disconnect from controlling tty. It is still possible to open /dev/tty.")
        except:
            # Good! We are disconnected from a controlling tty.
            pass

        # Verify we can open child pty.
        fd = os.open(child_name, os.O_RDWR);
        if fd < 0:
            raise ExceptionPexpect("Error! Could not open child pty, " + child_name)
        else:
            os.close(fd)

        # Verify we now have a controlling tty.
        fd = os.open("/dev/tty", os.O_WRONLY)
        if fd < 0:
            raise ExceptionPexpect("Error! Could not open controlling tty, /dev/tty")
        else:
            os.close(fd)

    def fileno (self):   # File-like object.

        """This returns the file descriptor of the pty for the child.
        """

        return self.child_fd

    def close (self, force=True):   # File-like object.

        """This closes the connection with the child application. Note that
        calling close() more than once is valid. This emulates standard Python
        behavior with files. Set force to True if you want to make sure that
        the child is terminated (SIGKILL is sent if the child ignores SIGHUP
        and SIGINT). """

        if not self.closed:
            self.flush()
            os.close (self.child_fd)
            time.sleep(self.delayafterclose) # Give kernel time to update process status.
            if self.isalive():
                if not self.terminate(force):
                    raise ExceptionPexpect ('close() could not terminate the child using terminate()')
            self.child_fd = -1
            self.closed = True
            #self.pid = None

    def flush (self):   # File-like object.

        """This does nothing. It is here to support the interface for a
        File-like object. """

        pass

    def isatty (self):   # File-like object.

        """This returns True if the file descriptor is open and connected to a
        tty(-like) device, else False. """

        return os.isatty(self.child_fd)

    def waitnoecho (self, timeout=-1):

        """This waits until the terminal ECHO flag is set False. This returns
        True if the echo mode is off. This returns False if the ECHO flag was
        not set False before the timeout. This can be used to detect when the
        child is waiting for a password. Usually a child application will turn
        off echo mode when it is waiting for the user to enter a password. For
        example, instead of expecting the "password:" prompt you can wait for
        the child to set ECHO off::

            p = pexpect.spawn ('ssh user@example.com')
            p.waitnoecho()
            p.sendline(mypassword)

        If timeout==-1 then this method will use the value in self.timeout.
        If timeout==None then this method to block until ECHO flag is False.
        """

        if timeout == -1:
            timeout = self.timeout
        if timeout is not None:
            end_time = time.time() + timeout
        while True:
            if not self.getecho():
                return True
            if timeout < 0 and timeout is not None:
                return False
            if timeout is not None:
                timeout = end_time - time.time()
            time.sleep(0.1)

    def getecho (self):

        """This returns the terminal echo mode. This returns True if echo is
        on or False if echo is off. Child applications that are expecting you
        to enter a password often set ECHO False. See waitnoecho(). """

        attr = termios.tcgetattr(self.child_fd)
        if attr[3] & termios.ECHO:
            return True
        return False

    def setecho (self, state):

        """This sets the terminal echo mode on or off. Note that anything the
        child sent before the echo will be lost, so you should be sure that
        your input buffer is empty before you call setecho(). For example, the
        following will work as expected::

            p = pexpect.spawn('cat')
            p.sendline ('1234') # We will see this twice (once from tty echo and again from cat).
            p.expect (['1234'])
            p.expect (['1234'])
            p.setecho(False) # Turn off tty echo
            p.sendline ('abcd') # We will set this only once (echoed by cat).
            p.sendline ('wxyz') # We will set this only once (echoed by cat)
            p.expect (['abcd'])
            p.expect (['wxyz'])

        The following WILL NOT WORK because the lines sent before the setecho
        will be lost::

            p = pexpect.spawn('cat')
            p.sendline ('1234') # We will see this twice (once from tty echo and again from cat).
            p.setecho(False) # Turn off tty echo
            p.sendline ('abcd') # We will set this only once (echoed by cat).
            p.sendline ('wxyz') # We will set this only once (echoed by cat)
            p.expect (['1234'])
            p.expect (['1234'])
            p.expect (['abcd'])
            p.expect (['wxyz'])
        """

        self.child_fd
        attr = termios.tcgetattr(self.child_fd)
        if state:
            attr[3] = attr[3] | termios.ECHO
        else:
            attr[3] = attr[3] & ~termios.ECHO
        # I tried TCSADRAIN and TCSAFLUSH, but these were inconsistent
        # and blocked on some platforms. TCSADRAIN is probably ideal if it worked.
        termios.tcsetattr(self.child_fd, termios.TCSANOW, attr)

    def read_nonblocking (self, size = 1, timeout = -1):

        """This reads at most size bytes from the child application. It
        includes a timeout. If the read does not complete within the timeout
        period then a TIMEOUT exception is raised. If the end of file is read
        then an EOF exception will be raised. If a log file was set using
        setlog() then all data will also be written to the log file.

        If timeout is None then the read may block indefinitely. If timeout is -1
        then the self.timeout value is used. If timeout is 0 then the child is
        polled and if there was no data immediately ready then this will raise
        a TIMEOUT exception.

        The timeout refers only to the amount of time to read at least one
        character. This is not effected by the 'size' parameter, so if you call
        read_nonblocking(size=100, timeout=30) and only one character is
        available right away then one character will be returned immediately.
        It will not wait for 30 seconds for another 99 characters to come in.

        This is a wrapper around os.read(). It uses select.select() to
        implement the timeout. """

        if self.closed:
            raise ValueError ('I/O operation on closed file in read_nonblocking().')

        if timeout == -1:
            timeout = self.timeout

        # Note that some systems such as Solaris do not give an EOF when
        # the child dies. In fact, you can still try to read
        # from the child_fd -- it will block forever or until TIMEOUT.
        # For this case, I test isalive() before doing any reading.
        # If isalive() is false, then I pretend that this is the same as EOF.
        if not self.isalive():
            r,w,e = self.__select([self.child_fd], [], [], 0) # timeout of 0 means "poll"
            if not r:
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Braindead platform.')
        elif self.__irix_hack:
            # This is a hack for Irix. It seems that Irix requires a long delay before checking isalive.
            # This adds a 2 second delay, but only when the child is terminated.
            r, w, e = self.__select([self.child_fd], [], [], 2)
            if not r and not self.isalive():
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Pokey platform.')

        r,w,e = self.__select([self.child_fd], [], [], timeout)

        if not r:
            if not self.isalive():
                # Some platforms, such as Irix, will claim that their processes are alive;
                # then timeout on the select; and then finally admit that they are not alive.
                self.flag_eof = True
                raise EOF ('End of File (EOF) in read_nonblocking(). Very pokey platform.')
            else:
                raise TIMEOUT ('Timeout exceeded in read_nonblocking().')

        if self.child_fd in r:
            try:
                s = os.read(self.child_fd, size)
            except OSError as e: # Linux does this
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Exception style platform.')
            if s == b'': # BSD style
                self.flag_eof = True
                raise EOF ('End Of File (EOF) in read_nonblocking(). Empty string style platform.')

            s2 = self._cast_buffer_type(s)
            if self.logfile is not None:
                self.logfile.write(s2)
                self.logfile.flush()
            if self.logfile_read is not None:
                self.logfile_read.write(s2)
                self.logfile_read.flush()

            return s

        raise ExceptionPexpect ('Reached an unexpected state in read_nonblocking().')

    def read (self, size = -1):         # File-like object.
        """This reads at most "size" bytes from the file (less if the read hits
        EOF before obtaining size bytes). If the size argument is negative or
        omitted, read all data until EOF is reached. The bytes are returned as
        a string object. An empty string is returned when EOF is encountered
        immediately. """

        if size == 0:
            return self._empty_buffer
        if size < 0:
            self.expect (self.delimiter) # delimiter default is EOF
            return self.before

        # I could have done this more directly by not using expect(), but
        # I deliberately decided to couple read() to expect() so that
        # I would catch any bugs early and ensure consistant behavior.
        # It's a little less efficient, but there is less for me to
        # worry about if I have to later modify read() or expect().
        # Note, it's OK if size==-1 in the regex. That just means it
        # will never match anything in which case we stop only on EOF.
        if self._buffer_type is bytes:
            pat = (six.u('.{%d}' % size)).encode('ascii')
        else:
            pat = six.u('.{%d}' % size)
        cre = re.compile(pat, re.DOTALL)
        index = self.expect ([cre, self.delimiter]) # delimiter default is EOF
        if index == 0:
            return self.after ### self.before should be ''. Should I assert this?
        return self.before

    def readline(self, size = -1):
        """This reads and returns one entire line. A trailing newline is kept
        in the string, but may be absent when a file ends with an incomplete
        line. Note: This readline() looks for a \\r\\n pair even on UNIX
        because this is what the pseudo tty device returns. So contrary to what
        you may expect you will receive the newline as \\r\\n. An empty string
        is returned when EOF is hit immediately. Currently, the size argument is
        mostly ignored, so this behavior is not standard for a file-like
        object. If size is 0 then an empty string is returned. """

        if size == 0:
            return self._empty_buffer
        index = self.expect ([self._pty_newline, self.delimiter]) # delimiter default is EOF
        if index == 0:
            return self.before + self._pty_newline
        return self.before

    def __iter__ (self):    # File-like object.

        """This is to support iterators over a file-like object.
        """

        return self

    def next (self):    # File-like object.

        """This is to support iterators over a file-like object.
        """

        result = self.readline()
        if result == self._empty_buffer:
            raise StopIteration
        return result

    def readlines (self, sizehint = -1):    # File-like object.

        """This reads until EOF using readline() and returns a list containing
        the lines thus read. The optional "sizehint" argument is ignored. """

        lines = []
        while True:
            line = self.readline()
            if not line:
                break
            lines.append(line)
        return lines

    def write(self, s):   # File-like object.

        """This is similar to send() except that there is no return value.
        """

        self.send (s)

    def writelines (self, sequence):   # File-like object.

        """This calls write() for each element in the sequence. The sequence
        can be any iterable object producing strings, typically a list of
        strings. This does not add line separators There is no return value.
        """

        for s in sequence:
            self.write (s)

    def send(self, s):

        """This sends a string to the child process. This returns the number of
        bytes written. If a log file was set then the data is also written to
        the log. """

        time.sleep(self.delaybeforesend)
        
        s2 = self._cast_buffer_type(s)
        if self.logfile is not None:
            self.logfile.write(s2)
            self.logfile.flush()
        if self.logfile_send is not None:
            self.logfile_send.write(s2)
            self.logfile_send.flush()
        c = os.write (self.child_fd, _cast_bytes(s, self.encoding))
        return c

    def sendline(self, s=''):

        """This is like send(), but it adds a line feed (os.linesep). This
        returns the number of bytes written. """

        n = self.send (s)
        n = n + self.send (os.linesep)
        return n

    def sendcontrol(self, char):

        """This sends a control character to the child such as Ctrl-C or
        Ctrl-D. For example, to send a Ctrl-G (ASCII 7)::

            child.sendcontrol('g')

        See also, sendintr() and sendeof().
        """

        char = char.lower()
        a = ord(char)
        if a>=97 and a<=122:
            a = a - ord('a') + 1
            return self.send (chr(a))
        d = {'@':0, '`':0,
            '[':27, '{':27,
            '\\':28, '|':28,
            ']':29, '}': 29,
            '^':30, '~':30,
            '_':31,
            '?':127}
        if char not in d:
            return 0
        return self.send (chr(d[char]))

    def sendeof(self):

        """This sends an EOF to the child. This sends a character which causes
        the pending parent output buffer to be sent to the waiting child
        program without waiting for end-of-line. If it is the first character
        of the line, the read() in the user program returns 0, which signifies
        end-of-file. This means to work as expected a sendeof() has to be
        called at the beginning of a line. This method does not send a newline.
        It is the responsibility of the caller to ensure the eof is sent at the
        beginning of a line. """

        ### Hmmm... how do I send an EOF?
        ###C  if ((m = write(pty, *buf, p - *buf)) < 0)
        ###C      return (errno == EWOULDBLOCK) ? n : -1;
        #fd = sys.stdin.fileno()
        #old = termios.tcgetattr(fd) # remember current state
        #attr = termios.tcgetattr(fd)
        #attr[3] = attr[3] | termios.ICANON # ICANON must be set to recognize EOF
        #try: # use try/finally to ensure state gets restored
        #    termios.tcsetattr(fd, termios.TCSADRAIN, attr)
        #    if hasattr(termios, 'CEOF'):
        #        os.write (self.child_fd, '%c' % termios.CEOF)
        #    else:
        #        # Silly platform does not define CEOF so assume CTRL-D
        #        os.write (self.child_fd, '%c' % 4)
        #finally: # restore state
        #    termios.tcsetattr(fd, termios.TCSADRAIN, old)
        if hasattr(termios, 'VEOF'):
            char = termios.tcgetattr(self.child_fd)[6][termios.VEOF]
        else:
            # platform does not define VEOF so assume CTRL-D
            char = chr(4)
        self.send(char)

    def sendintr(self):

        """This sends a SIGINT to the child. It does not require
        the SIGINT to be the first character on a line. """

        if hasattr(termios, 'VINTR'):
            char = termios.tcgetattr(self.child_fd)[6][termios.VINTR]
        else:
            # platform does not define VINTR so assume CTRL-C
            char = chr(3)
        self.send (char)

    def eof (self):

        """This returns True if the EOF exception was ever raised.
        """

        return self.flag_eof

    def terminate(self, force=False):

        """This forces a child process to terminate. It starts nicely with
        SIGHUP and SIGINT. If "force" is True then moves onto SIGKILL. This
        returns True if the child was terminated. This returns False if the
        child could not be terminated. """

        if not self.isalive():
            return True
        try:
            self.kill(signal.SIGHUP)
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            self.kill(signal.SIGCONT)
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            self.kill(signal.SIGINT)
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            if force:
                self.kill(signal.SIGKILL)
                time.sleep(self.delayafterterminate)
                if not self.isalive():
                    return True
                else:
                    return False
            return False
        except OSError as e:
            # I think there are kernel timing issues that sometimes cause
            # this to happen. I think isalive() reports True, but the
            # process is dead to the kernel.
            # Make one last attempt to see if the kernel is up to date.
            time.sleep(self.delayafterterminate)
            if not self.isalive():
                return True
            else:
                return False

    def wait(self):

        """This waits until the child exits. This is a blocking call. This will
        not read any data from the child, so this will block forever if the
        child has unread output and has terminated. In other words, the child
        may have printed output then called exit(); but, technically, the child
        is still alive until its output is read. """

        if self.isalive():
            pid, status = os.waitpid(self.pid, 0)
        else:
            raise ExceptionPexpect ('Cannot wait for dead child process.')
        self.exitstatus = os.WEXITSTATUS(status)
        if os.WIFEXITED (status):
            self.status = status
            self.exitstatus = os.WEXITSTATUS(status)
            self.signalstatus = None
            self.terminated = True
        elif os.WIFSIGNALED (status):
            self.status = status
            self.exitstatus = None
            self.signalstatus = os.WTERMSIG(status)
            self.terminated = True
        elif os.WIFSTOPPED (status):
            raise ExceptionPexpect ('Wait was called for a child process that is stopped. This is not supported. Is some other process attempting job control with our child pid?')
        return self.exitstatus

    def isalive(self):

        """This tests if the child process is running or not. This is
        non-blocking. If the child was terminated then this will read the
        exitstatus or signalstatus of the child. This returns True if the child
        process appears to be running or False if not. It can take literally
        SECONDS for Solaris to return the right status. """

        if self.terminated:
            return False

        if self.flag_eof:
            # This is for Linux, which requires the blocking form of waitpid to get
            # status of a defunct process. This is super-lame. The flag_eof would have
            # been set in read_nonblocking(), so this should be safe.
            waitpid_options = 0
        else:
            waitpid_options = os.WNOHANG

        try:
            pid, status = os.waitpid(self.pid, waitpid_options)
        except OSError as e: # No child processes
            if e.errno == errno.ECHILD:
                raise ExceptionPexpect ('isalive() encountered condition where "terminated" is 0, but there was no child process. Did someone else call waitpid() on our process?')
            else:
                raise e

        # I have to do this twice for Solaris. I can't even believe that I figured this out...
        # If waitpid() returns 0 it means that no child process wishes to
        # report, and the value of status is undefined.
        if pid == 0:
            try:
                pid, status = os.waitpid(self.pid, waitpid_options) ### os.WNOHANG) # Solaris!
            except OSError as e: # This should never happen...
                if e[0] == errno.ECHILD:
                    raise ExceptionPexpect ('isalive() encountered condition that should never happen. There was no child process. Did someone else call waitpid() on our process?')
                else:
                    raise e

            # If pid is still 0 after two calls to waitpid() then
            # the process really is alive. This seems to work on all platforms, except
            # for Irix which seems to require a blocking call on waitpid or select, so I let read_nonblocking
            # take care of this situation (unfortunately, this requires waiting through the timeout).
            if pid == 0:
                return True

        if pid == 0:
            return True

        if os.WIFEXITED (status):
            self.status = status
            self.exitstatus = os.WEXITSTATUS(status)
            self.signalstatus = None
            self.terminated = True
        elif os.WIFSIGNALED (status):
            self.status = status
            self.exitstatus = None
            self.signalstatus = os.WTERMSIG(status)
            self.terminated = True
        elif os.WIFSTOPPED (status):
            raise ExceptionPexpect ('isalive() encountered condition where child process is stopped. This is not supported. Is some other process attempting job control with our child pid?')
        return False

    def kill(self, sig):

        """This sends the given signal to the child application. In keeping
        with UNIX tradition it has a misleading name. It does not necessarily
        kill the child unless you send the right signal. """

        # Same as os.kill, but the pid is given for you.
        if self.isalive():
            os.kill(self.pid, sig)

    def compile_pattern_list(self, patterns):

        """This compiles a pattern-string or a list of pattern-strings.
        Patterns must be a StringType, EOF, TIMEOUT, SRE_Pattern, or a list of
        those. Patterns may also be None which results in an empty list (you
        might do this if waiting for an EOF or TIMEOUT condition without
        expecting any pattern).

        This is used by expect() when calling expect_list(). Thus expect() is
        nothing more than::

             cpl = self.compile_pattern_list(pl)
             return self.expect_list(cpl, timeout)

        If you are using expect() within a loop it may be more
        efficient to compile the patterns first and then call expect_list().
        This avoid calls in a loop to compile_pattern_list()::

             cpl = self.compile_pattern_list(my_pattern)
             while some_condition:
                ...
                i = self.expect_list(clp, timeout)
                ...
        """

        if patterns is None:
            return []
        if not isinstance(patterns, list):
            patterns = [patterns]

        compile_flags = re.DOTALL # Allow dot to match \n
        if self.ignorecase:
            compile_flags = compile_flags | re.IGNORECASE
        compiled_pattern_list = []
        for p in patterns:
            if isinstance(p, six.string_types):
                p = self._cast_buffer_type(p)
                compiled_pattern_list.append(re.compile(p, compile_flags))
            elif p is EOF:
                compiled_pattern_list.append(EOF)
            elif p is TIMEOUT:
                compiled_pattern_list.append(TIMEOUT)
            elif type(p) is re_type:
                p = self._prepare_regex_pattern(p)
                compiled_pattern_list.append(p)
            else:
                raise TypeError ('Argument must be one of StringTypes, EOF, TIMEOUT, SRE_Pattern, or a list of those type. %s' % str(type(p)))

        return compiled_pattern_list
    
    def _prepare_regex_pattern(self, p):
        "Recompile unicode regexes as bytes regexes. Overridden in subclass."
        if isinstance(p.pattern, six.text_type):
            p = re.compile(p.pattern.encode('utf-8'), p.flags &~ re.UNICODE)
        return p

    def expect(self, pattern, timeout = -1, searchwindowsize=-1):

        """This seeks through the stream until a pattern is matched. The
        pattern is overloaded and may take several types. The pattern can be a
        StringType, EOF, a compiled re, or a list of any of those types.
        Strings will be compiled to re types. This returns the index into the
        pattern list. If the pattern was not a list this returns index 0 on a
        successful match. This may raise exceptions for EOF or TIMEOUT. To
        avoid the EOF or TIMEOUT exceptions add EOF or TIMEOUT to the pattern
        list. That will cause expect to match an EOF or TIMEOUT condition
        instead of raising an exception.

        If you pass a list of patterns and more than one matches, the first match
        in the stream is chosen. If more than one pattern matches at that point,
        the leftmost in the pattern list is chosen. For example::

            # the input is 'foobar'
            index = p.expect (['bar', 'foo', 'foobar'])
            # returns 1 ('foo') even though 'foobar' is a "better" match

        Please note, however, that buffering can affect this behavior, since
        input arrives in unpredictable chunks. For example::

            # the input is 'foobar'
            index = p.expect (['foobar', 'foo'])
            # returns 0 ('foobar') if all input is available at once,
            # but returs 1 ('foo') if parts of the final 'bar' arrive late

        After a match is found the instance attributes 'before', 'after' and
        'match' will be set. You can see all the data read before the match in
        'before'. You can see the data that was matched in 'after'. The
        re.MatchObject used in the re match will be in 'match'. If an error
        occurred then 'before' will be set to all the data read so far and
        'after' and 'match' will be None.

        If timeout is -1 then timeout will be set to the self.timeout value.

        A list entry may be EOF or TIMEOUT instead of a string. This will
        catch these exceptions and return the index of the list entry instead
        of raising the exception. The attribute 'after' will be set to the
        exception type. The attribute 'match' will be None. This allows you to
        write code like this::

                index = p.expect (['good', 'bad', pexpect.EOF, pexpect.TIMEOUT])
                if index == 0:
                    do_something()
                elif index == 1:
                    do_something_else()
                elif index == 2:
                    do_some_other_thing()
                elif index == 3:
                    do_something_completely_different()

        instead of code like this::

                try:
                    index = p.expect (['good', 'bad'])
                    if index == 0:
                        do_something()
                    elif index == 1:
                        do_something_else()
                except EOF:
                    do_some_other_thing()
                except TIMEOUT:
                    do_something_completely_different()

        These two forms are equivalent. It all depends on what you want. You
        can also just expect the EOF if you are waiting for all output of a
        child to finish. For example::

                p = pexpect.spawn('/bin/ls')
                p.expect (pexpect.EOF)
                print p.before

        If you are trying to optimize for speed then see expect_list().
        """

        compiled_pattern_list = self.compile_pattern_list(pattern)
        return self.expect_list(compiled_pattern_list, timeout, searchwindowsize)

    def expect_list(self, pattern_list, timeout = -1, searchwindowsize = -1):

        """This takes a list of compiled regular expressions and returns the
        index into the pattern_list that matched the child output. The list may
        also contain EOF or TIMEOUT (which are not compiled regular
        expressions). This method is similar to the expect() method except that
        expect_list() does not recompile the pattern list on every call. This
        may help if you are trying to optimize for speed, otherwise just use
        the expect() method.  This is called by expect(). If timeout==-1 then
        the self.timeout value is used. If searchwindowsize==-1 then the
        self.searchwindowsize value is used. """

        return self.expect_loop(searcher_re(pattern_list), timeout, searchwindowsize)

    def expect_exact(self, pattern_list, timeout = -1, searchwindowsize = -1):

        """This is similar to expect(), but uses plain string matching instead
        of compiled regular expressions in 'pattern_list'. The 'pattern_list'
        may be a string; a list or other sequence of strings; or TIMEOUT and
        EOF.

        This call might be faster than expect() for two reasons: string
        searching is faster than RE matching and it is possible to limit the
        search to just the end of the input buffer.

        This method is also useful when you don't want to have to worry about
        escaping regular expression characters that you want to match."""

        if isinstance(pattern_list, (bytes, unicode)) or pattern_list in (TIMEOUT, EOF):
            pattern_list = [pattern_list]
        return self.expect_loop(searcher_string(pattern_list), timeout, searchwindowsize)

    def expect_loop(self, searcher, timeout = -1, searchwindowsize = -1):

        """This is the common loop used inside expect. The 'searcher' should be
        an instance of searcher_re or searcher_string, which describes how and what
        to search for in the input.

        See expect() for other arguments, return value and exceptions. """

        self.searcher = searcher

        if timeout == -1:
            timeout = self.timeout
        if timeout is not None:
            end_time = time.time() + timeout
        if searchwindowsize == -1:
            searchwindowsize = self.searchwindowsize

        try:
            incoming = self.buffer
            freshlen = len(incoming)
            while True: # Keep reading until exception or return.
                index = searcher.search(incoming, freshlen, searchwindowsize)
                if index >= 0:
                    self.buffer = incoming[searcher.end : ]
                    self.before = incoming[ : searcher.start]
                    self.after = incoming[searcher.start : searcher.end]
                    self.match = searcher.match
                    self.match_index = index
                    return self.match_index
                # No match at this point
                if timeout is not None and timeout < 0:
                    raise TIMEOUT ('Timeout exceeded in expect_any().')
                # Still have time left, so read more data
                c = self.read_nonblocking (self.maxread, timeout)
                freshlen = len(c)
                time.sleep (0.0001)
                incoming = incoming + c
                if timeout is not None:
                    timeout = end_time - time.time()
        except EOF as e:
            self.buffer = self._empty_buffer
            self.before = incoming
            self.after = EOF
            index = searcher.eof_index
            if index >= 0:
                self.match = EOF
                self.match_index = index
                return self.match_index
            else:
                self.match = None
                self.match_index = None
                raise EOF (str(e) + '\n' + str(self))
        except TIMEOUT as e:
            self.buffer = incoming
            self.before = incoming
            self.after = TIMEOUT
            index = searcher.timeout_index
            if index >= 0:
                self.match = TIMEOUT
                self.match_index = index
                return self.match_index
            else:
                self.match = None
                self.match_index = None
                raise TIMEOUT (str(e) + '\n' + str(self))
        except:
            self.before = incoming
            self.after = None
            self.match = None
            self.match_index = None
            raise

    def getwinsize(self):

        """This returns the terminal window size of the child tty. The return
        value is a tuple of (rows, cols). """

        TIOCGWINSZ = getattr(termios, 'TIOCGWINSZ', 1074295912)
        s = struct.pack('HHHH', 0, 0, 0, 0)
        x = fcntl.ioctl(self.fileno(), TIOCGWINSZ, s)
        return struct.unpack('HHHH', x)[0:2]

    def setwinsize(self, r, c):

        """This sets the terminal window size of the child tty. This will cause
        a SIGWINCH signal to be sent to the child. This does not change the
        physical window size. It changes the size reported to TTY-aware
        applications like vi or curses -- applications that respond to the
        SIGWINCH signal. """

        # Check for buggy platforms. Some Python versions on some platforms
        # (notably OSF1 Alpha and RedHat 7.1) truncate the value for
        # termios.TIOCSWINSZ. It is not clear why this happens.
        # These platforms don't seem to handle the signed int very well;
        # yet other platforms like OpenBSD have a large negative value for
        # TIOCSWINSZ and they don't have a truncate problem.
        # Newer versions of Linux have totally different values for TIOCSWINSZ.
        # Note that this fix is a hack.
        TIOCSWINSZ = getattr(termios, 'TIOCSWINSZ', -2146929561)
        if TIOCSWINSZ == 2148037735:
            TIOCSWINSZ = -2146929561 # Same bits, but with sign.
        # Note, assume ws_xpixel and ws_ypixel are zero.
        s = struct.pack('HHHH', r, c, 0, 0)
        fcntl.ioctl(self.fileno(), TIOCSWINSZ, s)

    def interact(self, escape_character = b'\x1d', input_filter = None, output_filter = None):

        """This gives control of the child process to the interactive user (the
        human at the keyboard). Keystrokes are sent to the child process, and
        the stdout and stderr output of the child process is printed. This
        simply echos the child stdout and child stderr to the real stdout and
        it echos the real stdin to the child stdin. When the user types the
        escape_character this method will stop. The default for
        escape_character is ^]. This should not be confused with ASCII 27 --
        the ESC character. ASCII 29 was chosen for historical merit because
        this is the character used by 'telnet' as the escape character. The
        escape_character will not be sent to the child process.

        You may pass in optional input and output filter functions. These
        functions should take a string and return a string. The output_filter
        will be passed all the output from the child process. The input_filter
        will be passed all the keyboard input from the user. The input_filter
        is run BEFORE the check for the escape_character.

        Note that if you change the window size of the parent the SIGWINCH
        signal will not be passed through to the child. If you want the child
        window size to change when the parent's window size changes then do
        something like the following example::

            import pexpect, struct, fcntl, termios, signal, sys
            def sigwinch_passthrough (sig, data):
                s = struct.pack("HHHH", 0, 0, 0, 0)
                a = struct.unpack('hhhh', fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ , s))
                global p
                p.setwinsize(a[0],a[1])
            p = pexpect.spawn('/bin/bash') # Note this is global and used in sigwinch_passthrough.
            signal.signal(signal.SIGWINCH, sigwinch_passthrough)
            p.interact()
        """

        # Flush the buffer.
        if PY3: self.stdout.write(_cast_unicode(self.buffer, self.encoding))
        else:   self.stdout.write(self.buffer)
        self.stdout.flush()
        self.buffer = self._empty_buffer
        mode = tty.tcgetattr(self.STDIN_FILENO)
        tty.setraw(self.STDIN_FILENO)
        try:
            self.__interact_copy(escape_character, input_filter, output_filter)
        finally:
            tty.tcsetattr(self.STDIN_FILENO, tty.TCSAFLUSH, mode)

    def __interact_writen(self, fd, data):

        """This is used by the interact() method.
        """

        while data != b'' and self.isalive():
            n = os.write(fd, data)
            data = data[n:]

    def __interact_read(self, fd):

        """This is used by the interact() method.
        """

        return os.read(fd, 1000)

    def __interact_copy(self, escape_character = None, input_filter = None, output_filter = None):

        """This is used by the interact() method.
        """

        while self.isalive():
            r,w,e = self.__select([self.child_fd, self.STDIN_FILENO], [], [])
            if self.child_fd in r:
                data = self.__interact_read(self.child_fd)
                if output_filter: data = output_filter(data)
                if self.logfile is not None:
                    self.logfile.write (data)
                    self.logfile.flush()
                os.write(self.STDOUT_FILENO, data)
            if self.STDIN_FILENO in r:
                data = self.__interact_read(self.STDIN_FILENO)
                if input_filter: data = input_filter(data)
                i = data.rfind(escape_character)
                if i != -1:
                    data = data[:i]
                    self.__interact_writen(self.child_fd, data)
                    break
                self.__interact_writen(self.child_fd, data)

    def __select (self, iwtd, owtd, ewtd, timeout=None):

        """This is a wrapper around select.select() that ignores signals. If
        select.select raises a select.error exception and errno is an EINTR
        error then it is ignored. Mainly this is used to ignore sigwinch
        (terminal resize). """

        # if select() is interrupted by a signal (errno==EINTR) then
        # we loop back and enter the select() again.
        if timeout is not None:
            end_time = time.time() + timeout
        while True:
            try:
                return select.select (iwtd, owtd, ewtd, timeout)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    # if we loop back we have to subtract the amount of time we already waited.
                    if timeout is not None:
                        timeout = end_time - time.time()
                        if timeout < 0:
                            return ([],[],[])
                else: # something else caused the select.error, so this really is an exception
                    raise

class spawn(spawnb):
    """This is the main class interface for Pexpect. Use this class to start
    and control child applications."""
    
    _buffer_type = six.text_type
    def _cast_buffer_type(self, s):
        return _cast_unicode(s, self.encoding)
    _empty_buffer = six.u('')
    _pty_newline = six.u('\r\n')
    
    def __init__(self, command, args=[], timeout=30, maxread=2000, searchwindowsize=None,
                 logfile=None, cwd=None, env=None, encoding='utf-8'):
        super(spawn, self).__init__(command, args, timeout=timeout, maxread=maxread,
                    searchwindowsize=searchwindowsize, logfile=logfile, cwd=cwd, env=env)
        self.encoding = encoding
    
    def _prepare_regex_pattern(self, p):
        "Recompile bytes regexes as unicode regexes."
        if isinstance(p.pattern, bytes):
            p = re.compile(p.pattern.decode(self.encoding), p.flags)
        return p
    
    def read_nonblocking(self, size=1, timeout=-1):
        return super(spawn, self).read_nonblocking(size=size, timeout=timeout)\
                                    .decode(self.encoding)
    
    read_nonblocking.__doc__ = spawnb.read_nonblocking.__doc__
        

##############################################################################
# End of spawn class
##############################################################################

class searcher_string (object):

    """This is a plain string search helper for the spawn.expect_any() method.
    This helper class is for speed. For more powerful regex patterns
    see the helper class, searcher_re.

    Attributes:

        eof_index     - index of EOF, or -1
        timeout_index - index of TIMEOUT, or -1

    After a successful match by the search() method the following attributes
    are available:

        start - index into the buffer, first byte of match
        end   - index into the buffer, first byte after match
        match - the matching string itself

    """

    def __init__(self, strings):

        """This creates an instance of searcher_string. This argument 'strings'
        may be a list; a sequence of strings; or the EOF or TIMEOUT types. """

        self.eof_index = -1
        self.timeout_index = -1
        self._strings = []
        for n, s in enumerate(strings):
            if s is EOF:
                self.eof_index = n
                continue
            if s is TIMEOUT:
                self.timeout_index = n
                continue
            self._strings.append((n, s))

    def __str__(self):

        """This returns a human-readable string that represents the state of
        the object."""

        ss =  [ (ns[0],'    %d: "%s"' % ns) for ns in self._strings ]
        ss.append((-1,'searcher_string:'))
        if self.eof_index >= 0:
            ss.append ((self.eof_index,'    %d: EOF' % self.eof_index))
        if self.timeout_index >= 0:
            ss.append ((self.timeout_index,'    %d: TIMEOUT' % self.timeout_index))
        ss.sort()
        return '\n'.join(a[1] for a in ss)

    def search(self, buffer, freshlen, searchwindowsize=None):

        """This searches 'buffer' for the first occurence of one of the search
        strings.  'freshlen' must indicate the number of bytes at the end of
        'buffer' which have not been searched before. It helps to avoid
        searching the same, possibly big, buffer over and over again.

        See class spawn for the 'searchwindowsize' argument.

        If there is a match this returns the index of that string, and sets
        'start', 'end' and 'match'. Otherwise, this returns -1. """

        absurd_match = len(buffer)
        first_match = absurd_match

        # 'freshlen' helps a lot here. Further optimizations could
        # possibly include:
        #
        # using something like the Boyer-Moore Fast String Searching
        # Algorithm; pre-compiling the search through a list of
        # strings into something that can scan the input once to
        # search for all N strings; realize that if we search for
        # ['bar', 'baz'] and the input is '...foo' we need not bother
        # rescanning until we've read three more bytes.
        #
        # Sadly, I don't know enough about this interesting topic. /grahn

        for index, s in self._strings:
            if searchwindowsize is None:
                # the match, if any, can only be in the fresh data,
                # or at the very end of the old data
                offset = -(freshlen+len(s))
            else:
                # better obey searchwindowsize
                offset = -searchwindowsize
            n = buffer.find(s, offset)
            if n >= 0 and n < first_match:
                first_match = n
                best_index, best_match = index, s
        if first_match == absurd_match:
            return -1
        self.match = best_match
        self.start = first_match
        self.end = self.start + len(self.match)
        return best_index

class searcher_re (object):

    """This is regular expression string search helper for the
    spawn.expect_any() method. This helper class is for powerful
    pattern matching. For speed, see the helper class, searcher_string.

    Attributes:

        eof_index     - index of EOF, or -1
        timeout_index - index of TIMEOUT, or -1

    After a successful match by the search() method the following attributes
    are available:

        start - index into the buffer, first byte of match
        end   - index into the buffer, first byte after match
        match - the re.match object returned by a succesful re.search

    """

    def __init__(self, patterns):

        """This creates an instance that searches for 'patterns' Where
        'patterns' may be a list or other sequence of compiled regular
        expressions, or the EOF or TIMEOUT types."""

        self.eof_index = -1
        self.timeout_index = -1
        self._searches = []
        for n, s in enumerate(patterns):
            if s is EOF:
                self.eof_index = n
                continue
            if s is TIMEOUT:
                self.timeout_index = n
                continue
            self._searches.append((n, s))

    def __str__(self):

        """This returns a human-readable string that represents the state of
        the object."""

        ss =  [ (n,'    %d: re.compile("%s")' % (n,str(s.pattern))) for n,s in self._searches]
        ss.append((-1,'searcher_re:'))
        if self.eof_index >= 0:
            ss.append ((self.eof_index,'    %d: EOF' % self.eof_index))
        if self.timeout_index >= 0:
            ss.append ((self.timeout_index,'    %d: TIMEOUT' % self.timeout_index))
        ss.sort()
        return '\n'.join(a[1] for a in ss)

    def search(self, buffer, freshlen, searchwindowsize=None):

        """This searches 'buffer' for the first occurence of one of the regular
        expressions. 'freshlen' must indicate the number of bytes at the end of
        'buffer' which have not been searched before.

        See class spawn for the 'searchwindowsize' argument.

        If there is a match this returns the index of that string, and sets
        'start', 'end' and 'match'. Otherwise, returns -1."""

        absurd_match = len(buffer)
        first_match = absurd_match
        # 'freshlen' doesn't help here -- we cannot predict the
        # length of a match, and the re module provides no help.
        if searchwindowsize is None:
            searchstart = 0
        else:
            searchstart = max(0, len(buffer)-searchwindowsize)
        for index, s in self._searches:
            match = s.search(buffer, searchstart)
            if match is None:
                continue
            n = match.start()
            if n < first_match:
                first_match = n
                the_match = match
                best_index = index
        if first_match == absurd_match:
            return -1
        self.start = first_match
        self.match = the_match
        self.end = self.match.end()
        return best_index

def which (filename):

    """This takes a given filename; tries to find it in the environment path;
    then checks if it is executable. This returns the full path to the filename
    if found and executable. Otherwise this returns None."""

    # Special case where filename already contains a path.
    if os.path.dirname(filename) != '':
        if os.access (filename, os.X_OK):
            return filename

    if not os.environ.has_key('PATH') or os.environ['PATH'] == '':
        p = os.defpath
    else:
        p = os.environ['PATH']

    pathlist = p.split(os.pathsep)

    for path in pathlist:
        f = os.path.join(path, filename)
        if os.access(f, os.X_OK):
            return f
    return None

def split_command_line(command_line):

    """This splits a command line into a list of arguments. It splits arguments
    on spaces, but handles embedded quotes, doublequotes, and escaped
    characters. It's impossible to do this with a regular expression, so I
    wrote a little state machine to parse the command line. """

    arg_list = []
    arg = ''

    # Constants to name the states we can be in.
    state_basic = 0
    state_esc = 1
    state_singlequote = 2
    state_doublequote = 3
    state_whitespace = 4 # The state of consuming whitespace between commands.
    state = state_basic

    for c in command_line:
        if state == state_basic or state == state_whitespace:
            if c == '\\': # Escape the next character
                state = state_esc
            elif c == r"'": # Handle single quote
                state = state_singlequote
            elif c == r'"': # Handle double quote
                state = state_doublequote
            elif c.isspace():
                # Add arg to arg_list if we aren't in the middle of whitespace.
                if state == state_whitespace:
                    None # Do nothing.
                else:
                    arg_list.append(arg)
                    arg = ''
                    state = state_whitespace
            else:
                arg = arg + c
                state = state_basic
        elif state == state_esc:
            arg = arg + c
            state = state_basic
        elif state == state_singlequote:
            if c == r"'":
                state = state_basic
            else:
                arg = arg + c
        elif state == state_doublequote:
            if c == r'"':
                state = state_basic
            else:
                arg = arg + c

    if arg != '':
        arg_list.append(arg)
    return arg_list

# vi:set sr et ts=4 sw=4 ft=python :

########NEW FILE########
__FILENAME__ = six
"""Utilities for writing code that runs on Python 2 and 3"""

# Copyright (c) 2010-2014 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import operator
import sys
import types

__author__ = "Benjamin Peterson <benjamin@python.org>"
__version__ = "1.5.2"


# Useful for very coarse version differentiation.
PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    class_types = type,
    text_type = str
    binary_type = bytes

    MAXSIZE = sys.maxsize
else:
    string_types = basestring,
    integer_types = (int, long)
    class_types = (type, types.ClassType)
    text_type = unicode
    binary_type = str

    if sys.platform.startswith("java"):
        # Jython always uses 32 bits.
        MAXSIZE = int((1 << 31) - 1)
    else:
        # It's possible to have sizeof(long) != sizeof(Py_ssize_t).
        class X(object):
            def __len__(self):
                return 1 << 31
        try:
            len(X())
        except OverflowError:
            # 32-bit
            MAXSIZE = int((1 << 31) - 1)
        else:
            # 64-bit
            MAXSIZE = int((1 << 63) - 1)
        del X


def _add_doc(func, doc):
    """Add documentation to a function."""
    func.__doc__ = doc


def _import_module(name):
    """Import module, returning the module after the last dot."""
    __import__(name)
    return sys.modules[name]


class _LazyDescr(object):

    def __init__(self, name):
        self.name = name

    def __get__(self, obj, tp):
        result = self._resolve()
        setattr(obj, self.name, result) # Invokes __set__.
        # This is a bit ugly, but it avoids running this again.
        delattr(obj.__class__, self.name)
        return result


class MovedModule(_LazyDescr):

    def __init__(self, name, old, new=None):
        super(MovedModule, self).__init__(name)
        if PY3:
            if new is None:
                new = name
            self.mod = new
        else:
            self.mod = old

    def _resolve(self):
        return _import_module(self.mod)

    def __getattr__(self, attr):
        # Hack around the Django autoreloader. The reloader tries to get
        # __file__ or __name__ of every module in sys.modules. This doesn't work
        # well if this MovedModule is for an module that is unavailable on this
        # machine (like winreg on Unix systems). Thus, we pretend __file__ and
        # __name__ don't exist if the module hasn't been loaded yet. We give
        # __path__ the same treatment for Google AppEngine. See issues #51, #53
        # and #56.
        if (attr in ("__file__", "__name__", "__path__") and
            self.mod not in sys.modules):
            raise AttributeError
        _module = self._resolve()
        value = getattr(_module, attr)
        setattr(self, attr, value)
        return value


class _LazyModule(types.ModuleType):

    def __init__(self, name):
        super(_LazyModule, self).__init__(name)
        self.__doc__ = self.__class__.__doc__

    def __dir__(self):
        attrs = ["__doc__", "__name__"]
        attrs += [attr.name for attr in self._moved_attributes]
        return attrs

    # Subclasses should override this
    _moved_attributes = []


class MovedAttribute(_LazyDescr):

    def __init__(self, name, old_mod, new_mod, old_attr=None, new_attr=None):
        super(MovedAttribute, self).__init__(name)
        if PY3:
            if new_mod is None:
                new_mod = name
            self.mod = new_mod
            if new_attr is None:
                if old_attr is None:
                    new_attr = name
                else:
                    new_attr = old_attr
            self.attr = new_attr
        else:
            self.mod = old_mod
            if old_attr is None:
                old_attr = name
            self.attr = old_attr

    def _resolve(self):
        module = _import_module(self.mod)
        return getattr(module, self.attr)



class _MovedItems(_LazyModule):
    """Lazy loading of moved objects"""


_moved_attributes = [
    MovedAttribute("cStringIO", "cStringIO", "io", "StringIO"),
    MovedAttribute("filter", "itertools", "builtins", "ifilter", "filter"),
    MovedAttribute("filterfalse", "itertools", "itertools", "ifilterfalse", "filterfalse"),
    MovedAttribute("input", "__builtin__", "builtins", "raw_input", "input"),
    MovedAttribute("map", "itertools", "builtins", "imap", "map"),
    MovedAttribute("range", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("reload_module", "__builtin__", "imp", "reload"),
    MovedAttribute("reduce", "__builtin__", "functools"),
    MovedAttribute("StringIO", "StringIO", "io"),
    MovedAttribute("UserString", "UserString", "collections"),
    MovedAttribute("xrange", "__builtin__", "builtins", "xrange", "range"),
    MovedAttribute("zip", "itertools", "builtins", "izip", "zip"),
    MovedAttribute("zip_longest", "itertools", "itertools", "izip_longest", "zip_longest"),

    MovedModule("builtins", "__builtin__"),
    MovedModule("configparser", "ConfigParser"),
    MovedModule("copyreg", "copy_reg"),
    MovedModule("dbm_gnu", "gdbm", "dbm.gnu"),
    MovedModule("http_cookiejar", "cookielib", "http.cookiejar"),
    MovedModule("http_cookies", "Cookie", "http.cookies"),
    MovedModule("html_entities", "htmlentitydefs", "html.entities"),
    MovedModule("html_parser", "HTMLParser", "html.parser"),
    MovedModule("http_client", "httplib", "http.client"),
    MovedModule("email_mime_multipart", "email.MIMEMultipart", "email.mime.multipart"),
    MovedModule("email_mime_text", "email.MIMEText", "email.mime.text"),
    MovedModule("email_mime_base", "email.MIMEBase", "email.mime.base"),
    MovedModule("BaseHTTPServer", "BaseHTTPServer", "http.server"),
    MovedModule("CGIHTTPServer", "CGIHTTPServer", "http.server"),
    MovedModule("SimpleHTTPServer", "SimpleHTTPServer", "http.server"),
    MovedModule("cPickle", "cPickle", "pickle"),
    MovedModule("queue", "Queue"),
    MovedModule("reprlib", "repr"),
    MovedModule("socketserver", "SocketServer"),
    MovedModule("_thread", "thread", "_thread"),
    MovedModule("tkinter", "Tkinter"),
    MovedModule("tkinter_dialog", "Dialog", "tkinter.dialog"),
    MovedModule("tkinter_filedialog", "FileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_scrolledtext", "ScrolledText", "tkinter.scrolledtext"),
    MovedModule("tkinter_simpledialog", "SimpleDialog", "tkinter.simpledialog"),
    MovedModule("tkinter_tix", "Tix", "tkinter.tix"),
    MovedModule("tkinter_ttk", "ttk", "tkinter.ttk"),
    MovedModule("tkinter_constants", "Tkconstants", "tkinter.constants"),
    MovedModule("tkinter_dnd", "Tkdnd", "tkinter.dnd"),
    MovedModule("tkinter_colorchooser", "tkColorChooser",
                "tkinter.colorchooser"),
    MovedModule("tkinter_commondialog", "tkCommonDialog",
                "tkinter.commondialog"),
    MovedModule("tkinter_tkfiledialog", "tkFileDialog", "tkinter.filedialog"),
    MovedModule("tkinter_font", "tkFont", "tkinter.font"),
    MovedModule("tkinter_messagebox", "tkMessageBox", "tkinter.messagebox"),
    MovedModule("tkinter_tksimpledialog", "tkSimpleDialog",
                "tkinter.simpledialog"),
    MovedModule("urllib_parse", __name__ + ".moves.urllib_parse", "urllib.parse"),
    MovedModule("urllib_error", __name__ + ".moves.urllib_error", "urllib.error"),
    MovedModule("urllib", __name__ + ".moves.urllib", __name__ + ".moves.urllib"),
    MovedModule("urllib_robotparser", "robotparser", "urllib.robotparser"),
    MovedModule("xmlrpc_client", "xmlrpclib", "xmlrpc.client"),
    MovedModule("xmlrpc_server", "xmlrpclib", "xmlrpc.server"),
    MovedModule("winreg", "_winreg"),
]
for attr in _moved_attributes:
    setattr(_MovedItems, attr.name, attr)
    if isinstance(attr, MovedModule):
        sys.modules[__name__ + ".moves." + attr.name] = attr
del attr

_MovedItems._moved_attributes = _moved_attributes

moves = sys.modules[__name__ + ".moves"] = _MovedItems(__name__ + ".moves")


class Module_six_moves_urllib_parse(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_parse"""


_urllib_parse_moved_attributes = [
    MovedAttribute("ParseResult", "urlparse", "urllib.parse"),
    MovedAttribute("SplitResult", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qs", "urlparse", "urllib.parse"),
    MovedAttribute("parse_qsl", "urlparse", "urllib.parse"),
    MovedAttribute("urldefrag", "urlparse", "urllib.parse"),
    MovedAttribute("urljoin", "urlparse", "urllib.parse"),
    MovedAttribute("urlparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlsplit", "urlparse", "urllib.parse"),
    MovedAttribute("urlunparse", "urlparse", "urllib.parse"),
    MovedAttribute("urlunsplit", "urlparse", "urllib.parse"),
    MovedAttribute("quote", "urllib", "urllib.parse"),
    MovedAttribute("quote_plus", "urllib", "urllib.parse"),
    MovedAttribute("unquote", "urllib", "urllib.parse"),
    MovedAttribute("unquote_plus", "urllib", "urllib.parse"),
    MovedAttribute("urlencode", "urllib", "urllib.parse"),
    MovedAttribute("splitquery", "urllib", "urllib.parse"),
]
for attr in _urllib_parse_moved_attributes:
    setattr(Module_six_moves_urllib_parse, attr.name, attr)
del attr

Module_six_moves_urllib_parse._moved_attributes = _urllib_parse_moved_attributes

sys.modules[__name__ + ".moves.urllib_parse"] = sys.modules[__name__ + ".moves.urllib.parse"] = Module_six_moves_urllib_parse(__name__ + ".moves.urllib_parse")


class Module_six_moves_urllib_error(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_error"""


_urllib_error_moved_attributes = [
    MovedAttribute("URLError", "urllib2", "urllib.error"),
    MovedAttribute("HTTPError", "urllib2", "urllib.error"),
    MovedAttribute("ContentTooShortError", "urllib", "urllib.error"),
]
for attr in _urllib_error_moved_attributes:
    setattr(Module_six_moves_urllib_error, attr.name, attr)
del attr

Module_six_moves_urllib_error._moved_attributes = _urllib_error_moved_attributes

sys.modules[__name__ + ".moves.urllib_error"] = sys.modules[__name__ + ".moves.urllib.error"] = Module_six_moves_urllib_error(__name__ + ".moves.urllib.error")


class Module_six_moves_urllib_request(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_request"""


_urllib_request_moved_attributes = [
    MovedAttribute("urlopen", "urllib2", "urllib.request"),
    MovedAttribute("install_opener", "urllib2", "urllib.request"),
    MovedAttribute("build_opener", "urllib2", "urllib.request"),
    MovedAttribute("pathname2url", "urllib", "urllib.request"),
    MovedAttribute("url2pathname", "urllib", "urllib.request"),
    MovedAttribute("getproxies", "urllib", "urllib.request"),
    MovedAttribute("Request", "urllib2", "urllib.request"),
    MovedAttribute("OpenerDirector", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDefaultErrorHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPRedirectHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPCookieProcessor", "urllib2", "urllib.request"),
    MovedAttribute("ProxyHandler", "urllib2", "urllib.request"),
    MovedAttribute("BaseHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgr", "urllib2", "urllib.request"),
    MovedAttribute("HTTPPasswordMgrWithDefaultRealm", "urllib2", "urllib.request"),
    MovedAttribute("AbstractBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyBasicAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("AbstractDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("ProxyDigestAuthHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPSHandler", "urllib2", "urllib.request"),
    MovedAttribute("FileHandler", "urllib2", "urllib.request"),
    MovedAttribute("FTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("CacheFTPHandler", "urllib2", "urllib.request"),
    MovedAttribute("UnknownHandler", "urllib2", "urllib.request"),
    MovedAttribute("HTTPErrorProcessor", "urllib2", "urllib.request"),
    MovedAttribute("urlretrieve", "urllib", "urllib.request"),
    MovedAttribute("urlcleanup", "urllib", "urllib.request"),
    MovedAttribute("URLopener", "urllib", "urllib.request"),
    MovedAttribute("FancyURLopener", "urllib", "urllib.request"),
    MovedAttribute("proxy_bypass", "urllib", "urllib.request"),
]
for attr in _urllib_request_moved_attributes:
    setattr(Module_six_moves_urllib_request, attr.name, attr)
del attr

Module_six_moves_urllib_request._moved_attributes = _urllib_request_moved_attributes

sys.modules[__name__ + ".moves.urllib_request"] = sys.modules[__name__ + ".moves.urllib.request"] = Module_six_moves_urllib_request(__name__ + ".moves.urllib.request")


class Module_six_moves_urllib_response(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_response"""


_urllib_response_moved_attributes = [
    MovedAttribute("addbase", "urllib", "urllib.response"),
    MovedAttribute("addclosehook", "urllib", "urllib.response"),
    MovedAttribute("addinfo", "urllib", "urllib.response"),
    MovedAttribute("addinfourl", "urllib", "urllib.response"),
]
for attr in _urllib_response_moved_attributes:
    setattr(Module_six_moves_urllib_response, attr.name, attr)
del attr

Module_six_moves_urllib_response._moved_attributes = _urllib_response_moved_attributes

sys.modules[__name__ + ".moves.urllib_response"] = sys.modules[__name__ + ".moves.urllib.response"] = Module_six_moves_urllib_response(__name__ + ".moves.urllib.response")


class Module_six_moves_urllib_robotparser(_LazyModule):
    """Lazy loading of moved objects in six.moves.urllib_robotparser"""


_urllib_robotparser_moved_attributes = [
    MovedAttribute("RobotFileParser", "robotparser", "urllib.robotparser"),
]
for attr in _urllib_robotparser_moved_attributes:
    setattr(Module_six_moves_urllib_robotparser, attr.name, attr)
del attr

Module_six_moves_urllib_robotparser._moved_attributes = _urllib_robotparser_moved_attributes

sys.modules[__name__ + ".moves.urllib_robotparser"] = sys.modules[__name__ + ".moves.urllib.robotparser"] = Module_six_moves_urllib_robotparser(__name__ + ".moves.urllib.robotparser")


class Module_six_moves_urllib(types.ModuleType):
    """Create a six.moves.urllib namespace that resembles the Python 3 namespace"""
    parse = sys.modules[__name__ + ".moves.urllib_parse"]
    error = sys.modules[__name__ + ".moves.urllib_error"]
    request = sys.modules[__name__ + ".moves.urllib_request"]
    response = sys.modules[__name__ + ".moves.urllib_response"]
    robotparser = sys.modules[__name__ + ".moves.urllib_robotparser"]

    def __dir__(self):
        return ['parse', 'error', 'request', 'response', 'robotparser']


sys.modules[__name__ + ".moves.urllib"] = Module_six_moves_urllib(__name__ + ".moves.urllib")


def add_move(move):
    """Add an item to six.moves."""
    setattr(_MovedItems, move.name, move)


def remove_move(name):
    """Remove item from six.moves."""
    try:
        delattr(_MovedItems, name)
    except AttributeError:
        try:
            del moves.__dict__[name]
        except KeyError:
            raise AttributeError("no such move, %r" % (name,))


if PY3:
    _meth_func = "__func__"
    _meth_self = "__self__"

    _func_closure = "__closure__"
    _func_code = "__code__"
    _func_defaults = "__defaults__"
    _func_globals = "__globals__"

    _iterkeys = "keys"
    _itervalues = "values"
    _iteritems = "items"
    _iterlists = "lists"
else:
    _meth_func = "im_func"
    _meth_self = "im_self"

    _func_closure = "func_closure"
    _func_code = "func_code"
    _func_defaults = "func_defaults"
    _func_globals = "func_globals"

    _iterkeys = "iterkeys"
    _itervalues = "itervalues"
    _iteritems = "iteritems"
    _iterlists = "iterlists"


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()
next = advance_iterator


try:
    callable = callable
except NameError:
    def callable(obj):
        return any("__call__" in klass.__dict__ for klass in type(obj).__mro__)


if PY3:
    def get_unbound_function(unbound):
        return unbound

    create_bound_method = types.MethodType

    Iterator = object
else:
    def get_unbound_function(unbound):
        return unbound.im_func

    def create_bound_method(func, obj):
        return types.MethodType(func, obj, obj.__class__)

    class Iterator(object):

        def next(self):
            return type(self).__next__(self)

    callable = callable
_add_doc(get_unbound_function,
         """Get the function out of a possibly unbound function""")


get_method_function = operator.attrgetter(_meth_func)
get_method_self = operator.attrgetter(_meth_self)
get_function_closure = operator.attrgetter(_func_closure)
get_function_code = operator.attrgetter(_func_code)
get_function_defaults = operator.attrgetter(_func_defaults)
get_function_globals = operator.attrgetter(_func_globals)


def iterkeys(d, **kw):
    """Return an iterator over the keys of a dictionary."""
    return iter(getattr(d, _iterkeys)(**kw))

def itervalues(d, **kw):
    """Return an iterator over the values of a dictionary."""
    return iter(getattr(d, _itervalues)(**kw))

def iteritems(d, **kw):
    """Return an iterator over the (key, value) pairs of a dictionary."""
    return iter(getattr(d, _iteritems)(**kw))

def iterlists(d, **kw):
    """Return an iterator over the (key, [values]) pairs of a dictionary."""
    return iter(getattr(d, _iterlists)(**kw))


if PY3:
    def b(s):
        return s.encode("latin-1")
    def u(s):
        return s
    unichr = chr
    if sys.version_info[1] <= 1:
        def int2byte(i):
            return bytes((i,))
    else:
        # This is about 2x faster than the implementation above on 3.2+
        int2byte = operator.methodcaller("to_bytes", 1, "big")
    byte2int = operator.itemgetter(0)
    indexbytes = operator.getitem
    iterbytes = iter
    import io
    StringIO = io.StringIO
    BytesIO = io.BytesIO
else:
    def b(s):
        return s
    # Workaround for standalone backslash
    def u(s):
        return unicode(s.replace(r'\\', r'\\\\'), "unicode_escape")
    unichr = unichr
    int2byte = chr
    def byte2int(bs):
        return ord(bs[0])
    def indexbytes(buf, i):
        return ord(buf[i])
    def iterbytes(buf):
        return (ord(byte) for byte in buf)
    import StringIO
    StringIO = BytesIO = StringIO.StringIO
_add_doc(b, """Byte literal""")
_add_doc(u, """Text literal""")


if PY3:
    exec_ = getattr(moves.builtins, "exec")


    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")


    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")


print_ = getattr(moves.builtins, "print", None)
if print_ is None:
    def print_(*args, **kwargs):
        """The new-style print function for Python 2.4 and 2.5."""
        fp = kwargs.pop("file", sys.stdout)
        if fp is None:
            return
        def write(data):
            if not isinstance(data, basestring):
                data = str(data)
            # If the file has an encoding, encode unicode with it.
            if (isinstance(fp, file) and
                isinstance(data, unicode) and
                fp.encoding is not None):
                errors = getattr(fp, "errors", None)
                if errors is None:
                    errors = "strict"
                data = data.encode(fp.encoding, errors)
            fp.write(data)
        want_unicode = False
        sep = kwargs.pop("sep", None)
        if sep is not None:
            if isinstance(sep, unicode):
                want_unicode = True
            elif not isinstance(sep, str):
                raise TypeError("sep must be None or a string")
        end = kwargs.pop("end", None)
        if end is not None:
            if isinstance(end, unicode):
                want_unicode = True
            elif not isinstance(end, str):
                raise TypeError("end must be None or a string")
        if kwargs:
            raise TypeError("invalid keyword arguments to print()")
        if not want_unicode:
            for arg in args:
                if isinstance(arg, unicode):
                    want_unicode = True
                    break
        if want_unicode:
            newline = unicode("\n")
            space = unicode(" ")
        else:
            newline = "\n"
            space = " "
        if sep is None:
            sep = space
        if end is None:
            end = newline
        for i, arg in enumerate(args):
            if i:
                write(sep)
            write(arg)
        write(end)

_add_doc(reraise, """Reraise an exception.""")


def with_metaclass(meta, *bases):
    """Create a base class with a metaclass."""
    return meta("NewBase", bases, {})

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper

########NEW FILE########
__FILENAME__ = _version
__version_info__ = (0, 7, 0)
__version__ = '.'.join(map(str, __version_info__))

########NEW FILE########
__FILENAME__ = tasks
import os
import shutil

from invocations import docs
from invocations.testing import test
from invocations.packaging import vendorize, release

from invoke import ctask as task, run, Collection


@task(name='tree')
def doctree(ctx):
    ctx.run("tree -Ca -I \".git|*.pyc|*.swp|dist|*.egg-info|_static|_build\" docs")

@task
def vendorize_pexpect(ctx, version):
    target = 'invoke/vendor'
    package = 'pexpect'
    vendorize(
        distribution="pexpect-u",
        package=package,
        version=version,
        vendor_dir=target,
        license='LICENSE', # TODO: autodetect this in vendorize
    )
    # Nuke test dir inside package hrrgh
    shutil.rmtree(os.path.join(target, package, 'tests'))

@task(help=test.help)
def integration(c, module=None, runner=None, opts=None):
    """
    Run the integration test suite. May be slow!
    """
    opts = opts or ""
    opts += " --tests=integration/"
    test(c, module, runner, opts)

docs = Collection.from_module(docs)
docs.add_task(doctree)
ns = Collection(test, integration, vendorize, release, docs, vendorize_pexpect)

########NEW FILE########
__FILENAME__ = cli
import os
import sys

from spec import eq_, skip, Spec, ok_, trap, nottest
from mock import patch

from invoke.cli import parse, dispatch
from invoke.context import Context
from invoke.runner import run
from invoke.parser import Parser
from invoke.collection import Collection
from invoke.tasks import task
from invoke.exceptions import Failure
import invoke

from _utils import support


# Strings are easier to type & read than lists

def _dispatch(argstr, version=None):
    return dispatch(argstr.split(), version)

@trap
def _output_eq(args, stdout=None, stderr=None):
    """
    dispatch() 'args', matching output to 'std(out|err)'.

    Must give either or both of the output-expecting args.
    """
    _dispatch("inv {0}".format(args))
    if stdout:
        eq_(sys.stdout.getvalue(), stdout)
    if stderr:
        eq_(sys.stderr.getvalue(), stderr)


class CLI(Spec):
    "Command-line behavior"
    def setup(self):
        os.chdir(support)
        self.sys_exit = patch('sys.exit').start()

    def teardown(self):
        patch.stopall()

    class basic_invocation:
        @trap
        def vanilla(self):
            os.chdir('implicit')
            _dispatch('inv foo')
            eq_(sys.stdout.getvalue(), "Hm\n")

        @trap
        def vanilla_with_explicit_collection(self):
            # Duplicates _output_eq above, but this way that can change w/o
            # breaking our expectations.
            _dispatch('inv -c integration print_foo')
            eq_(sys.stdout.getvalue(), "foo\n")

        def args(self):
            _output_eq('-c integration print_name --name inigo', "inigo\n")

        def underscored_args(self):
            _output_eq(
                '-c integration print_underscored_arg --my-option whatevs',
                "whatevs\n",
            )

    def contextualized_tasks_are_given_parser_context_arg(self):
        # go() in contextualized.py just returns its initial arg
        retval = _dispatch('invoke -c contextualized go')[0]
        assert isinstance(retval, Context)

    def core_help_option_prints_core_help(self):
        # TODO: change dynamically based on parser contents?
        # e.g. no core args == no [--core-opts],
        # no tasks == no task stuff?
        # NOTE: test will trigger default pty size of 80x24, so the below
        # string is formatted appropriately.
        # TODO: add more unit-y tests for specific behaviors:
        # * fill terminal w/ columns + spacing
        # * line-wrap help text in its own column
        expected = """
Usage: inv[oke] [--core-opts] task1 [--task1-opts] ... taskN [--taskN-opts]

Core options:
  --no-dedupe                      Disable task deduplication.
  -c STRING, --collection=STRING   Specify collection name to load. May be
                                   given >1 time.
  -d, --debug                      Enable debug output.
  -e, --echo                       Echo executed commands before running.
  -h [STRING], --help[=STRING]     Show core or per-task help and exit.
  -H STRING, --hide=STRING         Set default value of run()'s 'hide' kwarg.
  -l, --list                       List available tasks.
  -p, --pty                        Use a pty when executing shell commands.
  -r STRING, --root=STRING         Change root directory used for finding task
                                   modules.
  -V, --version                    Show version and exit.
  -w, --warn-only                  Warn, instead of failing, when shell
                                   commands fail.

""".lstrip()
        for flag in ['-h', '--help']:
            _output_eq(flag, expected)

    def per_task_help_prints_help_for_task_only(self):
        expected = """
Usage: inv[oke] [--core-opts] punch [--options] [other tasks here ...]

Docstring:
  none

Options:
  -h STRING, --why=STRING   Motive
  -w STRING, --who=STRING   Who to punch

""".lstrip()
        for flag in ['-h', '--help']:
            _output_eq('-c decorator {0} punch'.format(flag), expected)

    def per_task_help_works_for_unparameterized_tasks(self):
        expected = """
Usage: inv[oke] [--core-opts] biz [other tasks here ...]

Docstring:
  none

Options:
  none

""".lstrip()
        _output_eq('-c decorator -h biz', expected)

    def per_task_help_displays_docstrings_if_given(self):
        expected = """
Usage: inv[oke] [--core-opts] foo [other tasks here ...]

Docstring:
  Foo the bar.

Options:
  none

""".lstrip()
        _output_eq('-c decorator -h foo', expected)

    def per_task_help_dedents_correctly(self):
        expected = """
Usage: inv[oke] [--core-opts] foo2 [other tasks here ...]

Docstring:
  Foo the bar:

    example code

  Added in 1.0

Options:
  none

""".lstrip()
        _output_eq('-c decorator -h foo2', expected)

    def version_info(self):
        _output_eq('-V', "Invoke %s\n" % invoke.__version__)

    @trap
    def version_override(self):
        _dispatch('notinvoke -V', version="nope 1.0")
        eq_(sys.stdout.getvalue(), "nope 1.0\n")

    class task_list:
        "--list"

        def _listing(self, lines):
            return ("""
Available tasks:

%s

""" % '\n'.join("  " + x for x in lines)).lstrip()

        def _list_eq(self, collection, listing):
            cmd = '-c {0} --list'.format(collection)
            _output_eq(cmd, self._listing(listing))

        def simple_output(self):
            expected = self._listing((
                'bar',
                'foo',
                'print_foo',
                'print_name',
                'print_underscored_arg',
            ))
            for flag in ('-l', '--list'):
                _output_eq('-c integration {0}'.format(flag), expected)

        def namespacing(self):
            self._list_eq('namespacing', (
                'toplevel',
                'module.mytask',
            ))

        def top_level_tasks_listed_first(self):
            self._list_eq('simple_ns_list', (
                'z_toplevel',
                'a.subtask'
            ))

        def subcollections_sorted_in_depth_order(self):
            self._list_eq('deeper_ns_list', (
                'toplevel',
                'a.subtask',
                'a.nother.subtask',
            ))

        def aliases_sorted_alphabetically(self):
            self._list_eq('alias_sorting', (
                'toplevel (a, z)',
            ))

        def default_tasks(self):
            # sub-ns default task display as "real.name (collection name)"
            self._list_eq('explicit_root', (
                'top_level (othertop)',
                'sub.sub_task (sub, sub.othersub)',
            ))

        def docstrings_shown_alongside(self):
            self._list_eq('docstrings', (
                'leading_whitespace    foo',
                'no_docstring',
                'one_line              foo',
                'two_lines             foo',
                'with_aliases (a, b)   foo',
            ))

    def no_deduping(self):
        expected = """
foo
foo
bar
""".lstrip()
        _output_eq('-c integration --no-dedupe foo bar', expected)

    def debug_flag_activates_logging(self):
        # Have to patch our logger to get in before Nose logcapture kicks in.
        with patch('invoke.util.debug') as debug:
            _dispatch('inv -d -c debugging foo')
            debug.assert_called_with('my-sentinel')

    class run_options:
        "run() related CLI flags"
        def _test_flag(self, flag, kwarg, value):
            with patch('invoke.context.run') as run:
                _dispatch('invoke {0} -c contextualized run'.format(flag))
                run.assert_called_with('x', **{kwarg: value})

        def warn_only(self):
            self._test_flag('-w', 'warn', True)

        def pty(self):
            self._test_flag('-p', 'pty', True)

        def hide(self):
            self._test_flag('--hide both', 'hide', 'both')

        def echo(self):
            self._test_flag('-e', 'echo', True)


TB_SENTINEL = 'Traceback (most recent call last)'

class HighLevelFailures(Spec):
    @trap
    def command_failure(self):
        "Command failure doesn't show tracebacks"
        with patch('sys.exit') as exit:
            _dispatch('inv -c fail simple')
            assert TB_SENTINEL not in sys.stderr.getvalue()
            exit.assert_called_with(1)

    class parsing:
        def should_not_show_tracebacks(self):
            result = run("inv -c fail missing_pos", warn=True, hide='both')
            assert TB_SENTINEL not in result.stderr

        def should_show_core_usage_on_core_failures(self):
            skip()

        def should_show_context_usage_on_context_failures(self):
            skip()

    def load_failure(self):
        skip()


class CLIParsing(Spec):
    """
    High level parsing tests
    """
    def setup(self):
        @task(positional=[])
        def mytask(mystring, s, boolean=False, b=False, v=False,
            long_name=False, true_bool=True):
            pass
        @task(aliases=['mytask27'])
        def mytask2():
            pass
        @task
        def mytask3(mystring):
            pass
        @task
        def mytask4(clean=False, browse=False):
            pass
        @task(aliases=['other'], default=True)
        def subtask():
            pass
        subcoll = Collection('sub', subtask)
        self.c = Collection(mytask, mytask2, mytask3, mytask4, subcoll)

    def _parser(self):
        return Parser(self.c.to_contexts())

    def _parse(self, argstr):
        return self._parser().parse_argv(argstr.split())

    def _compare(self, invoke, flagname, value):
        invoke = "mytask " + invoke
        result = self._parse(invoke)
        eq_(result[0].args[flagname].value, value)

    def _compare_names(self, given, real):
        eq_(self._parse(given)[0].name, real)

    def underscored_flags_can_be_given_as_dashed(self):
        self._compare('--long-name', 'long_name', True)

    def inverse_boolean_flags(self):
        self._compare('--no-true-bool', 'true_bool', False)

    def namespaced_task(self):
        self._compare_names("sub.subtask", "sub.subtask")

    def aliases(self):
        self._compare_names("mytask27", "mytask2")

    def subcollection_aliases(self):
        self._compare_names("sub.other", "sub.subtask")

    def subcollection_default_tasks(self):
        self._compare_names("sub", "sub.subtask")

    def boolean_args(self):
        "mytask --boolean"
        self._compare("--boolean", 'boolean', True)

    def flag_then_space_then_value(self):
        "mytask --mystring foo"
        self._compare("--mystring foo", 'mystring', 'foo')

    def flag_then_equals_sign_then_value(self):
        "mytask --mystring=foo"
        self._compare("--mystring=foo", 'mystring', 'foo')

    def short_boolean_flag(self):
        "mytask -b"
        self._compare("-b", 'b', True)

    def short_flag_then_space_then_value(self):
        "mytask -s value"
        self._compare("-s value", 's', 'value')

    def short_flag_then_equals_sign_then_value(self):
        "mytask -s=value"
        self._compare("-s=value", 's', 'value')

    def short_flag_with_adjacent_value(self):
        "mytask -svalue"
        r = self._parse("mytask -svalue")
        eq_(r[0].args.s.value, 'value')

    def _flag_value_task(self, value):
        r = self._parse("mytask -s %s mytask2" % value)
        eq_(len(r), 2)
        eq_(r[0].name, 'mytask')
        eq_(r[0].args.s.value, value)
        eq_(r[1].name, 'mytask2')

    def flag_value_then_task(self):
        "mytask -s value mytask2"
        self._flag_value_task('value')

    def flag_value_same_as_task_name(self):
        "mytask -s mytask2 mytask2"
        self._flag_value_task('mytask2')

    def three_tasks_with_args(self):
        "mytask --boolean mytask3 --mystring foo mytask2"
        r = self._parse("mytask --boolean mytask3 --mystring foo mytask2")
        eq_(len(r), 3)
        eq_([x.name for x in r], ['mytask', 'mytask3', 'mytask2'])
        eq_(r[0].args.boolean.value, True)
        eq_(r[1].args.mystring.value, 'foo')

    def tasks_with_duplicately_named_kwargs(self):
        "mytask --mystring foo mytask3 --mystring bar"
        r = self._parse("mytask --mystring foo mytask3 --mystring bar")
        eq_(r[0].name, 'mytask')
        eq_(r[0].args.mystring.value, 'foo')
        eq_(r[1].name, 'mytask3')
        eq_(r[1].args.mystring.value, 'bar')

    def multiple_short_flags_adjacent(self):
        "mytask -bv (and inverse)"
        for args in ('-bv', '-vb'):
            r = self._parse("mytask %s" % args)
            a = r[0].args
            eq_(a.b.value, True)
            eq_(a.v.value, True)

    def globbed_shortflags_with_multipass_parsing(self):
        "mytask -cb and -bc"
        for args in ('-bc', '-cb'):
            _, _, r = parse(['invoke', 'mytask4', args], self.c)
            a = r[0].args
            eq_(a.clean.value, True)
            eq_(a.browse.value, True)

########NEW FILE########
__FILENAME__ = collection
import operator
import sys

from spec import Spec, skip, eq_, raises, assert_raises

from invoke.collection import Collection
from invoke.tasks import task, Task
from invoke.vendor import six
from invoke.vendor.six.moves import reduce

from _utils import load, support_path


@task
def _mytask():
    six.print_("woo!")

def _func():
    pass


class Collection_(Spec):
    class init:
        "__init__"
        def can_accept_task_varargs(self):
            "can accept tasks as *args"
            @task
            def task1():
                pass
            @task
            def task2():
                pass
            c = Collection(task1, task2)
            assert 'task1' in c
            assert 'task2' in c

        def can_accept_collections_as_varargs_too(self):
            sub = Collection('sub')
            ns = Collection(sub)
            eq_(ns.collections['sub'], sub)

        def kwargs_act_as_name_args_for_given_objects(self):
            sub = Collection()
            @task
            def task1():
                pass
            ns = Collection(loltask=task1, notsub=sub)
            eq_(ns['loltask'], task1)
            eq_(ns.collections['notsub'], sub)

        def initial_string_arg_acts_as_name(self):
            sub = Collection('sub')
            ns = Collection(sub)
            eq_(ns.collections['sub'], sub)

        def initial_string_arg_meshes_with_varargs_and_kwargs(self):
            # Collection('myname', atask, acollection, othertask=taskobj, ...)
            @task
            def task1():
                pass
            @task
            def task2():
                pass
            sub = Collection('sub')
            ns = Collection('root', task1, sub, sometask=task2)
            for x, y in (
                (ns.name, 'root'),
                (ns['task1'], task1),
                (ns.collections['sub'], sub),
                (ns['sometask'], task2),
            ):
                eq_(x, y)

    class useful_special_methods:
        def _meh(self):
            @task
            def task1():
                pass
            @task
            def task2():
                pass
            return Collection('meh', task1=task1, task2=task2)

        def setup(self):
            self.c = self._meh()

        def repr_(self):
            "__repr__"
            eq_(repr(self.c), "<Collection 'meh': task1, task2>")

        def equality_should_be_useful(self):
            eq_(self.c, self._meh())

    class from_module:
        def setup(self):
            self.c = Collection.from_module(load('integration'))

        class parameters:
            def setup(self):
                self.mod = load('integration')
                self.fm = Collection.from_module

            def name_override(self):
                eq_(self.fm(self.mod).name, 'integration')
                eq_(
                    self.fm(self.mod, name='not-integration').name,
                    'not-integration'
                )

            def inline_configuration(self):
                # No configuration given, none gotten
                eq_(self.fm(self.mod).configuration(), {})
                # Config kwarg given is reflected when config obtained
                eq_(
                    self.fm(self.mod, config={'foo': 'bar'}).configuration(),
                    {'foo': 'bar'}
                )

            def name_and_config_simultaneously(self):
                # Test w/ posargs to enforce ordering, just for safety.
                c = self.fm(self.mod, 'the name', {'the': 'config'})
                eq_(c.name, 'the name')
                eq_(c.configuration(), {'the': 'config'})

        def adds_tasks(self):
            assert 'print_foo' in self.c

        def derives_collection_name_from_module_name(self):
            eq_(self.c.name, 'integration')

        def submodule_names_are_stripped_to_last_chunk(self):
            with support_path():
                from package import module
            c = Collection.from_module(module)
            eq_(module.__name__, 'package.module')
            eq_(c.name, 'module')
            assert 'mytask' in c # Sanity

        def honors_explicit_collections(self):
            coll = Collection.from_module(load('explicit_root'))
            assert 'top_level' in coll.tasks
            assert 'sub' in coll.collections
            # The real key test
            assert 'sub_task' not in coll.tasks

        def allows_tasks_with_explicit_names_to_override_bound_name(self):
            coll = Collection.from_module(load('subcollection_task_name'))
            assert 'explicit_name' in coll.tasks # not 'implicit_name'

        def returns_unique_Collection_objects_for_same_input_module(self):
            # Ignoring self.c for now, just in case it changes later.
            # First, a module with no root NS
            mod = load('integration')
            c1 = Collection.from_module(mod)
            c2 = Collection.from_module(mod)
            assert c1 is not c2
            # Now one *with* a root NS (which was previously buggy)
            mod2 = load('explicit_root')
            c3 = Collection.from_module(mod2)
            c4 = Collection.from_module(mod2)
            assert c3 is not c4

        class explicit_root_ns:
            def setup(self):
                mod = load('explicit_root')
                mod.ns.configure({'key': 'builtin', 'otherkey': 'yup'})
                mod.ns.name = 'builtin_name'
                self.unchanged = Collection.from_module(mod)
                self.changed = Collection.from_module(
                    mod,
                    name='override_name',
                    config={'key': 'override'}
                )

            def inline_config_with_root_namespaces_overrides_builtin(self):
                eq_(self.unchanged.configuration()['key'], 'builtin')
                eq_(self.changed.configuration()['key'], 'override')

            def inline_config_overrides_via_merge_not_replacement(self):
                assert 'otherkey' in self.changed.configuration()

            def inline_name_overrides_root_namespace_object_name(self):
                eq_(self.unchanged.name, 'builtin_name')
                eq_(self.changed.name, 'override_name')

            def root_namespace_object_name_overrides_module_name(self):
                # Duplicates part of previous test for explicitness' sake.
                # I.e. proves that the name doesn't end up 'explicit_root'.
                eq_(self.unchanged.name, 'builtin_name')


    class add_task:
        def setup(self):
            self.c = Collection()

        def associates_given_callable_with_given_name(self):
            self.c.add_task(_mytask, 'foo')
            eq_(self.c['foo'], _mytask)

        def uses_function_name_as_implicit_name(self):
            self.c.add_task(_mytask)
            assert '_mytask' in self.c

        def prefers_name_kwarg_over_task_name_attr(self):
            self.c.add_task(Task(_func, name='notfunc'), name='yesfunc')
            assert 'yesfunc' in self.c
            assert 'notfunc' not in self.c

        def prefers_task_name_attr_over_function_name(self):
            self.c.add_task(Task(_func, name='notfunc'))
            assert 'notfunc' in self.c
            assert '_func' not in self.c

        @raises(ValueError)
        def raises_ValueError_if_no_name_found(self):
            # Can't use a lambda here as they are technically real functions.
            class Callable(object):
                def __call__(self):
                    pass
            self.c.add_task(Task(Callable()))

        @raises(ValueError)
        def raises_ValueError_on_multiple_defaults(self):
            t1 = Task(_func, default=True)
            t2 = Task(_func, default=True)
            self.c.add_task(t1, 'foo')
            self.c.add_task(t2, 'bar')

        @raises(ValueError)
        def raises_ValueError_if_task_added_mirrors_subcollection_name(self):
            self.c.add_collection(Collection('sub'))
            self.c.add_task(_mytask, 'sub')

        def allows_specifying_task_defaultness(self):
            self.c.add_task(_mytask, default=True)
            eq_(self.c.default, '_mytask')

        def specifying_default_False_overrides_task_setting(self):
            @task(default=True)
            def its_me():
                pass
            self.c.add_task(its_me, default=False)
            eq_(self.c.default, None)

    class add_collection:
        def setup(self):
            self.c = Collection()

        def adds_collection_as_subcollection_of_self(self):
            c2 = Collection('foo')
            self.c.add_collection(c2)
            assert 'foo' in self.c.collections

        def can_take_module_objects(self):
            self.c.add_collection(load('integration'))
            assert 'integration' in self.c.collections

        @raises(ValueError)
        def raises_ValueError_if_collection_without_name(self):
            # Aka non-root collections must either have an explicit name given
            # via kwarg, have a name attribute set, or be a module with
            # __name__ defined.
            root = Collection()
            sub = Collection()
            root.add_collection(sub)

        @raises(ValueError)
        def raises_ValueError_if_collection_named_same_as_task(self):
            self.c.add_task(_mytask, 'sub')
            self.c.add_collection(Collection('sub'))

    class getitem:
        "__getitem__"
        def setup(self):
            self.c = Collection()

        def finds_own_tasks_by_name(self):
            # TODO: duplicates an add_task test above, fix?
            self.c.add_task(_mytask, 'foo')
            eq_(self.c['foo'], _mytask)

        def finds_subcollection_tasks_by_dotted_name(self):
            sub = Collection('sub')
            sub.add_task(_mytask)
            self.c.add_collection(sub)
            eq_(self.c['sub._mytask'], _mytask)

        def honors_aliases_in_own_tasks(self):
            t = Task(_func, aliases=['bar'])
            self.c.add_task(t, 'foo')
            eq_(self.c['bar'], t)

        def honors_subcollection_task_aliases(self):
            self.c.add_collection(load('decorator'))
            assert 'decorator.bar' in self.c

        def honors_own_default_task_with_no_args(self):
            t = Task(_func, default=True)
            self.c.add_task(t)
            eq_(self.c[''], t)

        def honors_subcollection_default_tasks_on_subcollection_name(self):
            sub = Collection.from_module(load('decorator'))
            self.c.add_collection(sub)
            # Sanity
            assert self.c['decorator.biz'] is sub['biz']
            # Real test
            assert self.c['decorator'] is self.c['decorator.biz']

        @raises(ValueError)
        def raises_ValueError_for_no_name_and_no_default(self):
            self.c['']

        @raises(ValueError)
        def ValueError_for_empty_subcol_task_name_and_no_default(self):
            self.c.add_collection(Collection('whatever'))
            self.c['whatever']

    class to_contexts:
        def setup(self):
            @task
            def mytask(text, boolean=False, number=5):
                six.print_(text)
            @task(aliases=['mytask27'])
            def mytask2():
                pass
            @task(aliases=['othertask'], default=True)
            def subtask():
                pass
            sub = Collection('sub', subtask)
            self.c = Collection(mytask, mytask2, sub)
            self.contexts = self.c.to_contexts()
            alias_tups = [list(x.aliases) for x in self.contexts]
            self.aliases = reduce(operator.add, alias_tups, [])
            # Focus on 'mytask' as it has the more interesting sig
            self.context = [x for x in self.contexts if x.name == 'mytask'][0]

        def returns_iterable_of_Contexts_corresponding_to_tasks(self):
            eq_(self.context.name, 'mytask')
            eq_(len(self.contexts), 3)

        def allows_flaglike_access_via_flags(self):
            assert '--text' in self.context.flags

        def positional_arglist_preserves_order_given(self):
            @task(positional=('second', 'first'))
            def mytask(first, second, third):
                pass
            c = Collection()
            c.add_task(mytask)
            ctx = c.to_contexts()[0]
            eq_(ctx.positional_args, [ctx.args['second'], ctx.args['first']])

        def exposes_namespaced_task_names(self):
            assert 'sub.subtask' in [x.name for x in self.contexts]

        def exposes_namespaced_task_aliases(self):
            assert 'sub.othertask' in self.aliases

        def exposes_subcollection_default_tasks(self):
            assert 'sub' in self.aliases

        def exposes_aliases(self):
            assert 'mytask27' in self.aliases

    class task_names:
        def setup(self):
            self.c = Collection.from_module(load('explicit_root'))

        def returns_all_task_names_including_subtasks(self):
            eq_(set(self.c.task_names.keys()), set(['top_level', 'sub.sub_task']))

        def includes_aliases_and_defaults_as_values(self):
            names = self.c.task_names
            eq_(names['top_level'], ['othertop'])
            eq_(names['sub.sub_task'], ['sub.othersub', 'sub'])

    class configuration:
        "Configuration methods"
        def setup(self):
            self.root = Collection()
            self.task = Task(_func, name='task')

        def basic_set_and_get(self):
            self.root.configure({'foo': 'bar'})
            eq_(self.root.configuration(), {'foo': 'bar'})

        def configure_performs_merging(self):
            self.root.configure({'foo': 'bar'})
            eq_(self.root.configuration()['foo'], 'bar')
            self.root.configure({'biz': 'baz'})
            eq_(set(self.root.configuration().keys()), set(['foo', 'biz']))

        def configure_allows_overwriting(self):
            self.root.configure({'foo': 'one'})
            eq_(self.root.configuration()['foo'], 'one')
            self.root.configure({'foo': 'two'})
            eq_(self.root.configuration()['foo'], 'two')

        def call_returns_dict(self):
            eq_(self.root.configuration(), {})
            self.root.configure({'foo': 'bar'})
            eq_(self.root.configuration(), {'foo': 'bar'})

        def access_merges_from_subcollections(self):
            inner = Collection('inner', self.task)
            inner.configure({'foo': 'bar'})
            self.root.configure({'biz': 'baz'})
            # With no inner collection
            eq_(set(self.root.configuration().keys()), set(['biz']))
            # With inner collection
            self.root.add_collection(inner)
            eq_(
                set(self.root.configuration('inner.task').keys()),
                set(['foo', 'biz'])
            )

        def parents_overwrite_children_in_path(self):
            inner = Collection('inner', self.task)
            inner.configure({'foo': 'inner'})
            self.root.add_collection(inner)
            # Before updating root collection's config, reflects inner
            eq_(self.root.configuration('inner.task')['foo'], 'inner')
            self.root.configure({'foo': 'outer'})
            # After, reflects outer (since that now overrides)
            eq_(self.root.configuration('inner.task')['foo'], 'outer')

        def sibling_subcollections_ignored(self):
            inner = Collection('inner', self.task)
            inner.configure({'foo': 'hi there'})
            inner2 = Collection('inner2', Task(_func, name='task2'))
            inner2.configure({'foo': 'nope'})
            root = Collection(inner, inner2)
            eq_(root.configuration('inner.task')['foo'], 'hi there')
            eq_(root.configuration('inner2.task2')['foo'], 'nope')

        def subcollection_paths_may_be_dotted(self):
            leaf = Collection('leaf', self.task)
            leaf.configure({'key': 'leaf-value'})
            middle = Collection('middle', leaf)
            root = Collection('root', middle)
            eq_(root.configuration('middle.leaf.task'), {'key': 'leaf-value'})

        def invalid_subcollection_paths_result_in_KeyError(self):
            # Straight up invalid
            assert_raises(KeyError,
                Collection('meh').configuration,
                'nope.task'
            )
            # Exists but wrong level (should be 'root.task', not just
            # 'task')
            inner = Collection('inner', self.task)
            assert_raises(KeyError,
                Collection('root', inner).configuration, 'task')

        def keys_dont_have_to_exist_in_full_path(self):
            # Kinda duplicates earlier stuff; meh
            # Key only stored on leaf
            leaf = Collection('leaf', self.task)
            leaf.configure({'key': 'leaf-value'})
            middle = Collection('middle', leaf)
            root = Collection('root', middle)
            eq_(root.configuration('middle.leaf.task'), {'key': 'leaf-value'})
            # Key stored on mid + leaf but not root
            middle.configure({'key': 'whoa'})
            eq_(root.configuration('middle.leaf.task'), {'key': 'whoa'})

########NEW FILE########
__FILENAME__ = context
from spec import Spec, skip, eq_
from mock import patch

from invoke.context import Context


class Context_(Spec):
    class init:
        "__init__"
        def takes_optional_run_and_config_args(self):
            # Meh-tastic doesn't-barf tests. MEH.
            Context()
            Context(run={'foo': 'bar'})
            Context(config={'foo': 'bar'})

    class run_:
        def _honors(self, kwarg, value):
            with patch('invoke.context.run') as run:
                Context(run={kwarg: value}).run('x')
                run.assert_called_with('x', **{kwarg: value})

        def warn(self):
            self._honors('warn', True)

        def hide(self):
            self._honors('hide', 'both')

        def pty(self):
            self._honors('pty', True)

        def echo(self):
            self._honors('echo', True)

    class clone:
        def returns_copy_of_self(self):
            skip()

        def contents_of_dicts_are_distinct(self):
            skip()

    class configuration:
        "Dict-like for config"
        def setup(self):
            self.c = Context(config={'foo': 'bar'})

        def getitem(self):
            "___getitem__"
            eq_(self.c['foo'], 'bar')

        def get(self):
            eq_(self.c.get('foo'), 'bar')
            eq_(self.c.get('biz', 'baz'), 'baz')

        def keys(self):
            skip()

        def update(self):
            self.c.update({'newkey': 'newval'})
            eq_(self.c['newkey'], 'newval')

########NEW FILE########
__FILENAME__ = executor
from spec import Spec, eq_, skip
from mock import Mock, call as mock_call

from invoke.context import Context
from invoke.executor import Executor
from invoke.collection import Collection
from invoke.tasks import Task, ctask, call


class Executor_(Spec):
    def setup(self):
        self.task1 = Task(Mock(return_value=7))
        self.task2 = Task(Mock(return_value=10), pre=[self.task1])
        self.task3 = Task(Mock(), pre=[self.task1])
        coll = Collection()
        coll.add_task(self.task1, name='task1')
        coll.add_task(self.task2, name='task2')
        coll.add_task(self.task3, name='task3')
        self.executor = Executor(collection=coll, context=Context())

    class init:
        "__init__"
        def allows_collection_and_context(self):
            coll = Collection()
            cont = Context()
            e = Executor(collection=coll, context=cont)
            assert e.collection is coll
            assert e.context is cont

        def uses_blank_context_by_default(self):
            e = Executor(collection=Collection())
            assert isinstance(e.context, Context)

    class execute:
        def base_case(self):
            self.executor.execute('task1')
            assert self.task1.body.called

        def kwargs(self):
            k = {'foo': 'bar'}
            self.executor.execute(name='task1', kwargs=k)
            self.task1.body.assert_called_once_with(**k)

        def pre_tasks(self):
            self.executor.execute(name='task2')
            eq_(self.task1.body.call_count, 1)

        def pre_task_calls_default_to_empty_args_regardless_of_main_args(self):
            body = Mock()
            t1 = Task(body)
            t2 = Task(Mock(), pre=[t1])
            e = Executor(
                collection=Collection(t1=t1, t2=t2),
                context=Context()
            )
            e.execute('t2', {'something': 'meh'})
            eq_(body.call_args, tuple())

        def _call_objs(self, contextualized):
            body = Mock()
            t1 = Task(body, contextualized=contextualized)
            t2 = Task(Mock(), pre=[call(t1, 5, foo='bar')])
            c = Collection(t1=t1, t2=t2)
            e = Executor(collection=c, context=Context())
            e.execute('t2')
            args, kwargs = body.call_args
            eq_(kwargs, {'foo': 'bar'})
            if contextualized:
                assert isinstance(args[0], Context)
                eq_(args[1], 5)
            else:
                eq_(args, (5,))

        def pre_tasks_may_be_call_objects_specifying_args(self):
            self._call_objs(False)

        def call_obj_pre_tasks_play_well_with_context_args(self):
            self._call_objs(True)

        def enabled_deduping(self):
            self.executor.execute(name='task2')
            self.executor.execute(name='task3')
            eq_(self.task1.body.call_count, 1)

        def deduping_treats_different_calls_to_same_task_differently(self):
            body = Mock()
            t1 = Task(body)
            pre = [call(t1, 5), call(t1, 7), call(t1, 5)]
            t2 = Task(Mock(), pre=pre)
            c = Collection(t1=t1, t2=t2)
            e = Executor(collection=c, context=Context())
            e.execute('t2')
            # Does not call the second t1(5)
            body.assert_has_calls([mock_call(5), mock_call(7)])

        def disabled_deduping(self):
            self.executor.execute(name='task2', dedupe=False)
            self.executor.execute(name='task3', dedupe=False)
            eq_(self.task1.body.call_count, 2)

        def hands_collection_configuration_to_context(self):
            @ctask
            def mytask(ctx):
                eq_(ctx['my.config.key'], 'value')
            c = Collection(mytask)
            c.configure({'my.config.key': 'value'})
            Executor(collection=c, context=Context()).execute('mytask')

        def hands_task_specific_configuration_to_context(self):
            @ctask
            def mytask(ctx):
                eq_(ctx['my.config.key'], 'value')
            @ctask
            def othertask(ctx):
                eq_(ctx['my.config.key'], 'othervalue')
            inner1 = Collection('inner1', mytask)
            inner1.configure({'my.config.key': 'value'})
            inner2 = Collection('inner2', othertask)
            inner2.configure({'my.config.key': 'othervalue'})
            c = Collection(inner1, inner2)
            e = Executor(collection=c, context=Context())
            e.execute('inner1.mytask')
            e.execute('inner2.othertask')

        def subcollection_config_works_with_default_tasks(self):
            @ctask(default=True)
            def mytask(ctx):
                eq_(ctx['my.config.key'], 'value')
            # Sets up a task "known as" sub.mytask which may be called as just
            # 'sub' due to being default.
            sub = Collection('sub', mytask=mytask)
            sub.configure({'my.config.key': 'value'})
            main = Collection(sub=sub)
            # Execute via collection default 'task' name.
            Executor(collection=main, context=Context()).execute('sub')


    class returns_return_value_of_specified_task:
        def base_case(self):
            eq_(self.executor.execute(name='task1'), 7)

        def with_pre_tasks(self):
            eq_(self.executor.execute(name='task2'), 10)

        def with_post_tasks(self):
            skip()

########NEW FILE########
__FILENAME__ = init
import re

import six
from spec import Spec, eq_

import invoke
import invoke.tasks
import invoke.runner
import invoke.collection


class Init(Spec):
    "__init__"
    def dunder_version_info(self):
        assert hasattr(invoke, '__version_info__')
        ver = invoke.__version_info__
        assert isinstance(ver, tuple)
        assert all(isinstance(x, int) for x in ver)

    def dunder_version(self):
        assert hasattr(invoke, '__version__')
        ver = invoke.__version__
        assert isinstance(ver, six.string_types)
        assert re.match(r'\d+\.\d+\.\d+', ver)
    
    def dunder_version_looks_generated_from_dunder_version_info(self):
        # Meh.
        ver_part = invoke.__version__.split('.')[0]
        ver_info_part = invoke.__version_info__[0]
        eq_(ver_part, str(ver_info_part))

    class exposes_bindings:
        def task_decorator(self):
            assert invoke.task is invoke.tasks.task

        def ctask_decorator(self):
            assert invoke.ctask is invoke.tasks.ctask

        def task_class(self):
            assert invoke.Task is invoke.tasks.Task

        def run_function(self):
            assert invoke.run is invoke.runner.run

        def collection_class(self):
            assert invoke.Collection is invoke.collection.Collection

########NEW FILE########
__FILENAME__ = loader
import imp
import os
import sys

from spec import Spec, skip, eq_, raises

from invoke.loader import Loader, FilesystemLoader as FSLoader
from invoke.collection import Collection
from invoke.exceptions import CollectionNotFound

from _utils import support


class _BasicLoader(Loader):
    """
    Tests top level Loader behavior with basic finder stub.

    Used when we want to make sure we're testing Loader.load and not e.g.
    FilesystemLoader's specific implementation.
    """
    def find(self, name):
        self.fd, self.path, self.desc = t = imp.find_module(name, [support])
        return t


class Loader_(Spec):
    def adds_module_parent_dir_to_sys_path(self):
        # Crummy doesn't-explode test.
        _BasicLoader().load('namespacing')

    def closes_opened_file_object(self):
        loader = _BasicLoader()
        loader.load('foo')
        assert loader.fd.closed


class FilesystemLoader_(Spec):
    def setup(self):
        self.l = FSLoader(start=support)

    def exposes_discovery_start_point(self):
        start = '/tmp/'
        eq_(FSLoader(start=start).start, start)

    def has_a_default_discovery_start_point(self):
        eq_(FSLoader().start, os.getcwd())

    def returns_collection_object_if_name_found(self):
        result = self.l.load('foo')
        eq_(type(result), Collection)

    @raises(CollectionNotFound)
    def raises_CollectionNotFound_if_not_found(self):
        self.l.load('nope')

    @raises(ImportError)
    def raises_ImportError_if_found_collection_cannot_be_imported(self):
        # Instead of masking with a CollectionNotFound
        self.l.load('oops')

    def searches_towards_root_of_filesystem(self):
        # Loaded while root is in same dir as .py
        directly = self.l.load('foo')
        # Loaded while root is multiple dirs deeper than the .py
        deep = os.path.join(support, 'ignoreme', 'ignoremetoo')
        indirectly = FSLoader(start=deep).load('foo')
        eq_(directly, indirectly)

    def defaults_to_tasks_collection(self):
        "defaults to 'tasks' collection"
        result = FSLoader(start=support + '/implicit/').load()
        eq_(type(result), Collection)

########NEW FILE########
__FILENAME__ = argument
from spec import Spec, eq_, skip, ok_, raises

from invoke.parser import Argument


class Argument_(Spec):
    class init:
        "__init__"
        def may_take_names_list(self):
            names = ('--foo', '-f')
            a = Argument(names=names)
            # herp a derp
            for name in names:
                assert name in a.names

        def may_take_name_arg(self):
            assert '-b' in Argument(name='-b').names

        @raises(TypeError)
        def must_get_at_least_one_name(self):
            Argument()

        def default_arg_is_name_not_names(self):
            assert 'b' in Argument('b').names

        def can_declare_positional(self):
            eq_(Argument(name='foo', positional=True).positional, True)

        def positional_is_False_by_default(self):
            eq_(Argument(name='foo').positional, False)

        def can_set_attr_name_to_control_name_attr(self):
            a = Argument('foo', attr_name='bar')
            eq_(a.name, 'bar') # not 'foo'

    class string:
        "__str__"

        def shows_useful_info(self):
            eq_(
                str(Argument(names=('name', 'nick1', 'nick2'))),
                "<Argument: %s (%s)>" % ('name', 'nick1, nick2')
            )

        def does_not_show_nickname_parens_if_no_nicknames(self):
            eq_(
                str(Argument('name')),
                "<Argument: name>"
            )

        def shows_positionalness(self):
            eq_(
                str(Argument('name', positional=True)),
                "<Argument: name*>"
            )

    class repr:
        "__repr__"

        def just_aliases_dunder_str(self):
            a = Argument(names=('name', 'name2'))
            eq_(str(a), repr(a))

    class kind_kwarg:
        "'kind' kwarg"

        def is_optional(self):
            Argument(name='a')
            Argument(name='b', kind=int)

        def defaults_to_str(self):
            eq_(Argument('a').kind, str)

        def non_bool_implies_value_needed(self):
            assert Argument(name='a', kind=int).takes_value

        def bool_implies_no_value_needed(self):
            assert not Argument(name='a', kind=bool).takes_value

        def bool_implies_default_False_not_None(self):
            # Right now, parsing a bool flag not given results in None
            # TODO: may want more nuance here -- False when a --no-XXX flag is
            # given, True if --XXX, None if not seen?
            # Only makes sense if we add automatic --no-XXX stuff (think
            # ./configure)
            skip()

        @raises(ValueError)
        def may_validate_on_set(self):
            Argument('a', kind=int).value = 'five'

    class names:
        def returns_tuple_of_all_names(self):
            eq_(Argument(names=('--foo', '-b')).names, ('--foo', '-b'))
            eq_(Argument(name='--foo').names, ('--foo',))

        def is_normalized_to_a_tuple(self):
            ok_(isinstance(Argument(names=('a', 'b')).names, tuple))

    class name:
        def returns_first_name(self):
            eq_(Argument(names=('a', 'b')).name, 'a')

    class nicknames:
        def returns_rest_of_names(self):
            eq_(Argument(names=('a', 'b')).nicknames, ('b',))

    class takes_value:
        def True_by_default(self):
            assert Argument(name='a').takes_value

        def False_if_kind_is_bool(self):
            assert not Argument(name='-b', kind=bool).takes_value

    class value_set:
        "value="
        def available_as_dot_raw_value(self):
            "available as .raw_value"
            a = Argument('a')
            a.value = 'foo'
            eq_(a.raw_value, 'foo')

        def untransformed_appears_as_dot_value(self):
            "untransformed, appears as .value"
            a = Argument('a', kind=str)
            a.value = 'foo'
            eq_(a.value, 'foo')

        def transformed_appears_as_dot_value_with_original_as_raw_value(self):
            "transformed, modified value is .value, original is .raw_value"
            a = Argument('a', kind=int)
            a.value = '5'
            eq_(a.value, 5)
            eq_(a.raw_value, '5')

    class value:
        def returns_default_if_not_set(self):
            a = Argument('a', default=25)
            eq_(a.value, 25)

    class raw_value:
        def is_None_when_no_value_was_actually_seen(self):
            a = Argument('a', kind=int)
            eq_(a.raw_value, None)

    class set_value:
        def casts_by_default(self):
            a = Argument('a', kind=int)
            a.set_value('5')
            eq_(a.value, 5)

        def allows_setting_value_without_casting(self):
            a = Argument('a', kind=int)
            a.set_value('5', cast=False)
            eq_(a.value, '5')

########NEW FILE########
__FILENAME__ = context
import copy

from spec import Spec, eq_, skip, ok_, raises

from invoke.parser import Argument, Context
from invoke.tasks import task
from invoke.collection import Collection


class Context_(Spec):
    "ParserContext" # meh
    def may_have_a_name(self):
        c = Context(name='taskname')
        eq_(c.name, 'taskname')

    def may_have_aliases(self):
        c = Context(name='realname', aliases=('othername', 'yup'))
        assert 'othername' in c.aliases

    def may_give_arg_list_at_init_time(self):
        a1 = Argument('foo')
        a2 = Argument('bar')
        c = Context(name='name', args=(a1, a2))
        assert c.args['foo'] is a1

    # TODO: reconcile this sort of test organization with the .flags oriented
    # tests within 'add_arg'.  Some of this behavior is technically driven by
    # add_arg.
    class args:
        def setup(self):
            self.c = Context(args=(
                Argument('foo'),
                Argument(names=('bar', 'biz')),
                Argument('baz', attr_name='wat'),
            ))

        def exposed_as_dict(self):
            assert 'foo' in self.c.args.keys()

        def exposed_as_Lexicon(self):
            eq_(self.c.args.bar, self.c.args['bar'])

        def args_dict_includes_all_arg_names(self):
            for x in ('foo', 'bar', 'biz'):
                assert x in self.c.args

        def argument_attr_names_appear_in_args_but_not_flags(self):
            # Both appear as "Python-facing" args
            for x in ('baz', 'wat'):
                assert x in self.c.args
            # But attr_name is for Python access only and isn't shown to the
            # parser.
            assert 'wat' not in self.c.flags

    class add_arg:
        def setup(self):
            self.c = Context()

        def can_take_Argument_instance(self):
            a = Argument(names=('foo',))
            self.c.add_arg(a)
            assert self.c.args['foo'] is a

        def can_take_name_arg(self):
            self.c.add_arg('foo')
            assert 'foo' in self.c.args

        def can_take_kwargs_for_single_Argument(self):
            self.c.add_arg(names=('foo', 'bar'))
            assert 'foo' in self.c.args and 'bar' in self.c.args

        @raises(ValueError)
        def raises_ValueError_on_duplicate(self):
            self.c.add_arg(names=('foo', 'bar'))
            self.c.add_arg(name='bar')

        def adds_flaglike_name_to_dot_flags(self):
            "adds flaglike name to .flags"
            self.c.add_arg('foo')
            assert '--foo' in self.c.flags

        def adds_all_names_to_dot_flags(self):
            "adds all names to .flags"
            self.c.add_arg(names=('foo', 'bar'))
            assert '--foo' in self.c.flags
            assert '--bar' in self.c.flags

        def adds_true_bools_to_inverse_flags(self):
            self.c.add_arg(name='myflag', default=True, kind=bool)
            assert '--myflag' in self.c.flags
            assert '--no-myflag' in self.c.inverse_flags
            eq_(self.c.inverse_flags['--no-myflag'], '--myflag')

        def inverse_flags_works_right_with_task_driven_underscored_names(self):
            # Use a Task here instead of creating a raw argument, we're partly
            # testing Task.get_arguments()' transform of underscored names
            # here. Yes that makes this an integration test, but it's nice to
            # test it here at this level & not just in cli tests.
            @task
            def mytask(underscored_option=True):
                pass
            self.c.add_arg(mytask.get_arguments()[0])
            eq_(
                self.c.inverse_flags['--no-underscored-option'],
                '--underscored-option'
            )

        def turns_single_character_names_into_short_flags(self):
            self.c.add_arg('f')
            assert '-f' in self.c.flags
            assert '--f' not in self.c.flags

        def adds_positional_args_to_positional_args(self):
            self.c.add_arg(name='pos', positional=True)
            eq_(self.c.positional_args[0].name, 'pos')

        def positional_args_empty_when_none_given(self):
            eq_(len(self.c.positional_args), 0)

        def positional_args_filled_in_order(self):
            self.c.add_arg(name='pos1', positional=True)
            eq_(self.c.positional_args[0].name, 'pos1')
            self.c.add_arg(name='abc', positional=True)
            eq_(self.c.positional_args[1].name, 'abc')

        def positional_arg_modifications_affect_args_copy(self):
            self.c.add_arg(name='hrm', positional=True)
            eq_(self.c.args['hrm'].value, self.c.positional_args[0].value)
            self.c.positional_args[0].value = 17
            eq_(self.c.args['hrm'].value, self.c.positional_args[0].value)

    class deepcopy:
        "__deepcopy__"
        def setup(self):
            self.arg = Argument('--boolean')
            self.orig = Context(
                name='mytask',
                args=(self.arg,),
                aliases=('othername',)
            )
            self.new = copy.deepcopy(self.orig)

        def returns_correct_copy(self):
            assert self.new is not self.orig
            eq_(self.new.name, 'mytask')
            assert 'othername' in self.new.aliases

        def includes_arguments(self):
            eq_(len(self.new.args), 1)
            assert self.new.args['--boolean'] is not self.arg

        def modifications_to_copied_arguments_do_not_touch_originals(self):
            new_arg = self.new.args['--boolean']
            new_arg.value = True
            assert new_arg.value
            assert not self.arg.value

    class help_for:
        def setup(self):
            # Normal, non-task/collection related Context
            self.vanilla = Context(args=(
                Argument('foo'),
                Argument('bar', help="bar the baz")
            ))
            # Task/Collection generated Context
            # (will expose flags n such)
            @task(help={'otherarg': 'other help'}, optional=['optval'])
            def mytask(myarg, otherarg, optval):
                pass
            col = Collection(mytask)
            self.tasked = col.to_contexts()[0]

        @raises(ValueError)
        def raises_ValueError_for_non_flag_values(self):
            self.vanilla.help_for('foo')

        def vanilla_no_helpstr(self):
            eq_(
                self.vanilla.help_for('--foo'),
                ("--foo=STRING", "")
            )

        def vanilla_with_helpstr(self):
            eq_(
                self.vanilla.help_for('--bar'),
                ("--bar=STRING", "bar the baz")
            )

        def task_driven_with_helpstr(self):
            eq_(
                self.tasked.help_for('--otherarg'),
                ("-o STRING, --otherarg=STRING", "other help")
            )

        # Yes, the next 3 tests are identical in form, but technically they
        # test different behaviors. HERPIN' AN' DERPIN'
        def task_driven_no_helpstr(self):
            eq_(
                self.tasked.help_for('--myarg'),
                ("-m STRING, --myarg=STRING", "")
            )

        def short_form_before_long_form(self):
            eq_(
                self.tasked.help_for('--myarg'),
                ("-m STRING, --myarg=STRING", "")
            )

        def equals_sign_for_long_form_only(self):
            eq_(
                self.tasked.help_for('--myarg'),
                ("-m STRING, --myarg=STRING", "")
            )

        def kind_to_placeholder_map(self):
            # str=STRING, int=INT, etc etc
            skip()

        def shortflag_inputs_work_too(self):
            eq_(self.tasked.help_for('-m'), self.tasked.help_for('--myarg'))

        def optional_values_use_brackets(self):
            eq_(
                self.tasked.help_for('--optval'),
                ("-p [STRING], --optval[=STRING]", "")
            )

        def underscored_args(self):
            c = Context(args=(Argument('i_have_underscores', help='yup'),))
            eq_(c.help_for('--i-have-underscores'), ('--i-have-underscores=STRING', 'yup'))

        def true_default_args(self):
            c = Context(args=(Argument('truthy', kind=bool, default=True),))
            eq_(c.help_for('--truthy'), ('--[no-]truthy', ''))


    class help_tuples:
        def returns_list_of_help_tuples(self):
            # Walks own list of flags/args, ensures resulting map to help_for()
            # TODO: consider redoing help_for to be more flexible on input --
            # arg value or flag; or even Argument objects. ?
            @task(help={'otherarg': 'other help'})
            def mytask(myarg, otherarg):
                pass
            c = Collection(mytask).to_contexts()[0]
            eq_(
                c.help_tuples(),
                [c.help_for('--myarg'), c.help_for('--otherarg')]
            )

        def _assert_order(self, name_tuples, expected_flag_order):
            ctx = Context(args=[Argument(names=x) for x in name_tuples])
            return eq_(
                ctx.help_tuples(),
                [ctx.help_for(x) for x in expected_flag_order]
            )

        def sorts_alphabetically_by_shortflag_first(self):
            # Where shortflags exist, they take precedence
            self._assert_order(
                [('zarg', 'a'), ('arg', 'z')],
                ['--zarg', '--arg']
            )

        def case_ignored_during_sorting(self):
            self._assert_order(
                [('a',), ('B',)],
                # In raw cmp() uppercase would come before lowercase,
                # and we'd get ['-B', '-a']
                ['-a', '-B']
            )

        def lowercase_wins_when_values_identical_otherwise(self):
            self._assert_order(
                [('V',), ('v',)],
                ['-v', '-V']
            )

        def sorts_alphabetically_by_longflag_when_no_shortflag(self):
            # Where no shortflag, sorts by longflag
            self._assert_order(
                [('otherarg',), ('longarg',)],
                ['--longarg', '--otherarg']
            )

        def sorts_heterogenous_help_output_with_longflag_only_options_first(self):
            # When both of the above mix, long-flag-only options come first.
            # E.g.:
            #   --alpha
            #   --beta
            #   -a, --aaaagh
            #   -b, --bah
            #   -c
            self._assert_order(
                [('c',), ('a', 'aaagh'), ('b', 'bah'), ('beta',), ('alpha',)],
                ['--alpha', '--beta', '-a', '-b', '-c']
            )

        def mixed_corelike_options(self):
            self._assert_order(
                [('V', 'version'), ('c', 'collection'), ('h', 'help'),
                    ('l', 'list'), ('r', 'root')],
                ['-c', '-h', '-l', '-r', '-V']
            )

    class needs_positional_arg:
        def represents_whether_all_positional_args_have_values(self):
            c = Context(name='foo', args=(
                Argument('arg1', positional=True),
                Argument('arg2', positional=False),
                Argument('arg3', positional=True),
            ))
            eq_(c.needs_positional_arg, True)
            c.positional_args[0].value = 'wat'
            eq_(c.needs_positional_arg, True)
            c.positional_args[1].value = 'hrm'
            eq_(c.needs_positional_arg, False)

    class str:
        "__str__"
        def with_no_args_output_is_simple(self):
            eq_(str(Context('foo')), "<parser/Context 'foo'>")

        def args_show_as_repr(self):
            eq_(
                str(Context('bar', args=[Argument('arg1')])),
                "<parser/Context 'bar': {'arg1': <Argument: arg1>}>"
            )

        def repr_is_str(self):
            "__repr__ mirrors __str__"
            c = Context('foo')
            eq_(str(c), repr(c))

########NEW FILE########
__FILENAME__ = parser
from spec import Spec, skip, ok_, eq_, raises, trap

from invoke.parser import Parser, Context, Argument, ParseError
from invoke.collection import Collection


class Parser_(Spec):
    def can_take_initial_context(self):
        c = Context()
        p = Parser(initial=c)
        eq_(p.initial, c)

    def can_take_initial_and_other_contexts(self):
        c1 = Context('foo')
        c2 = Context('bar')
        p = Parser(initial=Context(), contexts=[c1, c2])
        eq_(p.contexts['foo'], c1)
        eq_(p.contexts['bar'], c2)

    def can_take_just_other_contexts(self):
        c = Context('foo')
        p = Parser(contexts=[c])
        eq_(p.contexts['foo'], c)

    def can_take_just_contexts_as_non_keyword_arg(self):
        c = Context('foo')
        p = Parser([c])
        eq_(p.contexts['foo'], c)

    @raises(ValueError)
    def raises_ValueError_for_unnamed_Contexts_in_contexts(self):
        Parser(initial=Context(), contexts=[Context()])

    @raises(ValueError)
    def raises_error_for_context_name_clashes(self):
        Parser(contexts=(Context('foo'), Context('foo')))

    @raises(ValueError)
    def raises_error_for_context_alias_and_name_clashes(self):
        Parser((Context('foo', aliases=('bar',)), Context('bar')))

    @raises(ValueError)
    def raises_error_for_context_name_and_alias_clashes(self):
        # I.e. inverse of the above, which is a different code path.
        Parser((Context('foo'), Context('bar', aliases=('foo',))))

    def takes_ignore_unknown_kwarg(self):
        Parser(ignore_unknown=True)

    def ignore_unknown_defaults_to_False(self):
        eq_(Parser().ignore_unknown, False)

    class parse_argv:
        def parses_sys_argv_style_list_of_strings(self):
            "parses sys.argv-style list of strings"
            # Doesn't-blow-up tests FTL
            mytask = Context(name='mytask')
            mytask.add_arg('arg')
            p = Parser(contexts=[mytask])
            p.parse_argv(['mytask', '--arg', 'value'])

        def returns_only_contexts_mentioned(self):
            task1 = Context('mytask')
            task2 = Context('othertask')
            result = Parser((task1, task2)).parse_argv(['othertask'])
            eq_(len(result), 1)
            eq_(result[0].name, 'othertask')

        @raises(ParseError)
        def raises_error_if_unknown_contexts_found(self):
            Parser().parse_argv(['foo', 'bar'])

        def unparsed_does_not_share_state(self):
            r = Parser(ignore_unknown=True).parse_argv(['self'])
            eq_(r.unparsed, ['self'])
            r2 = Parser(ignore_unknown=True).parse_argv(['contained'])
            eq_(r.unparsed, ['self']) # NOT ['self', 'contained']
            eq_(r2.unparsed, ['contained']) # NOT ['self', 'contained']

        def ignore_unknown_returns_unparsed_argv_instead(self):
            r = Parser(ignore_unknown=True).parse_argv(['foo', 'bar', '--baz'])
            eq_(r.unparsed, ['foo', 'bar', '--baz'])

        def ignore_unknown_does_not_mutate_rest_of_argv(self):
            p = Parser([Context('ugh')], ignore_unknown=True)
            r = p.parse_argv(['ugh', 'what', '-nowai'])
            # NOT: ['what', '-n', '-w', '-a', '-i']
            eq_(r.unparsed, ['what', '-nowai'])

        def always_includes_initial_context_if_one_was_given(self):
            # Even if no core/initial flags were seen
            t1 = Context('t1')
            init = Context()
            result = Parser((t1,), initial=init).parse_argv(['t1'])
            eq_(result[0].name, None)
            eq_(result[1].name, 't1')

        def returned_contexts_are_in_order_given(self):
            t1, t2 = Context('t1'), Context('t2')
            r = Parser((t1, t2)).parse_argv(['t2', 't1'])
            eq_([x.name for x in r], ['t2', 't1'])

        def returned_context_member_arguments_contain_given_values(self):
            c = Context('mytask', args=(Argument('boolean', kind=bool),))
            result = Parser((c,)).parse_argv(['mytask', '--boolean'])
            eq_(result[0].args['boolean'].value, True)

        def inverse_bools_get_set_correctly(self):
            arg = Argument('myarg', kind=bool, default=True)
            c = Context('mytask', args=(arg,))
            r = Parser((c,)).parse_argv(['mytask', '--no-myarg'])
            eq_(r[0].args['myarg'].value, False)

        def arguments_which_take_values_get_defaults_overridden_correctly(self):
            args = (Argument('arg', kind=str), Argument('arg2', kind=int))
            c = Context('mytask', args=args)
            argv = ['mytask', '--arg', 'myval', '--arg2', '25']
            result = Parser((c,)).parse_argv(argv)
            eq_(result[0].args['arg'].value, 'myval')
            eq_(result[0].args['arg2'].value, 25)

        def returned_arguments_not_given_contain_default_values(self):
            # I.e. a Context with args A and B, invoked with no mention of B,
            # should result in B existing in the result, with its default value
            # intact, and not e.g. None, or the arg not existing.
            a = Argument('name', kind=str)
            b = Argument('age', default=7)
            c = Context('mytask', args=(a, b))
            result = Parser((c,)).parse_argv(['mytask', '--name', 'blah'])
            eq_(c.args['age'].value, 7)

        def returns_remainder(self):
            "returns -- style remainder string chunk"
            r = Parser((Context('foo'),)).parse_argv(['foo', '--', 'bar', 'biz'])
            eq_(r.remainder, "bar biz")

        def clones_initial_context(self):
            a = Argument('foo', kind=bool)
            eq_(a.value, None)
            c = Context(args=(a,))
            p = Parser(initial=c)
            assert p.initial is c
            r = p.parse_argv(['--foo'])
            assert p.initial is c
            c2 = r[0]
            assert c2 is not c
            a2 = c2.args['foo']
            assert a2 is not a
            eq_(a.value, None)
            eq_(a2.value, True)

        def clones_noninitial_contexts(self):
            a = Argument('foo')
            eq_(a.value, None)
            c = Context(name='mytask', args=(a,))
            p = Parser(contexts=(c,))
            assert p.contexts['mytask'] is c
            r = p.parse_argv(['mytask', '--foo', 'val'])
            assert p.contexts['mytask'] is c
            c2 = r[0]
            assert c2 is not c
            a2 = c2.args['foo']
            assert a2 is not a
            eq_(a.value, None)
            eq_(a2.value, 'val')

        class parsing_errors:
            def setup(self):
                self.p = Parser([Context(name='foo', args=[Argument('bar')])])

            @raises(ParseError)
            def missing_flag_values_raise_ParseError(self):
                self.p.parse_argv(['foo', '--bar'])

            def attaches_context_to_ParseErrors(self):
                try:
                    self.p.parse_argv(['foo', '--bar'])
                except ParseError as e:
                    assert e.context is not None

            def attached_context_is_None_outside_contexts(self):
                try:
                    Parser().parse_argv(['wat'])
                except ParseError as e:
                    assert e.context is None

        class positional_arguments:
            def _basic(self):
                arg = Argument('pos', positional=True)
                mytask = Context(name='mytask', args=[arg])
                return Parser(contexts=[mytask])

            def single_positional_arg(self):
                r = self._basic().parse_argv(['mytask', 'posval'])
                eq_(r[0].args['pos'].value, 'posval')

            @raises(ParseError)
            def omitted_positional_arg_raises_ParseError(self):
                self._basic().parse_argv(['mytask'])

            def positional_args_eat_otherwise_valid_context_names(self):
                mytask = Context('mytask', args=[
                    Argument('pos', positional=True),
                    Argument('nonpos', default='default')
                ])
                othertask = Context('lolwut')
                result = Parser([mytask]).parse_argv(['mytask', 'lolwut'])
                r = result[0]
                eq_(r.args['pos'].value, 'lolwut')
                eq_(r.args['nonpos'].value, 'default')
                eq_(len(result), 1) # Not 2

            def positional_args_can_still_be_given_as_flags(self):
                # AKA "positional args can come anywhere in the context"
                pos1 = Argument('pos1', positional=True)
                pos2 = Argument('pos2', positional=True)
                nonpos = Argument('nonpos', positional=False, default='lol')
                mytask = Context('mytask', args=[pos1, pos2, nonpos])
                eq_(mytask.positional_args, [pos1, pos2])
                r = Parser([mytask]).parse_argv([
                    'mytask',
                    '--nonpos', 'wut',
                    '--pos2', 'pos2val',
                    'pos1val',
                ])[0]
                eq_(r.args['pos1'].value, 'pos1val')
                eq_(r.args['pos2'].value, 'pos2val')
                eq_(r.args['nonpos'].value, 'wut')

        class equals_signs:
            def _compare(self, argname, invoke, value):
                c = Context('mytask', args=(Argument(argname, kind=str),))
                r = Parser((c,)).parse_argv(['mytask', invoke])
                eq_(r[0].args[argname].value, value)

            def handles_equals_style_long_flags(self):
                self._compare('foo', '--foo=bar', 'bar')

            def handles_equals_style_short_flags(self):
                self._compare('f', '-f=bar', 'bar')

            def does_not_require_escaping_equals_signs_in_value(self):
                self._compare('f', '-f=biz=baz', 'biz=baz')

        def handles_multiple_boolean_flags_per_context(self):
            c = Context('mytask', args=(
                Argument('foo', kind=bool), Argument('bar', kind=bool)
            ))
            r = Parser([c]).parse_argv(['mytask', '--foo', '--bar'])
            a = r[0].args
            eq_(a.foo.value, True)
            eq_(a.bar.value, True)

    class optional_arg_values:
        def setup(self):
            self.parser = self._parser()

        def _parser(self, arguments=None):
            if arguments is None:
                arguments = (
                    Argument(
                        names=('foo', 'f'),
                        optional=True,
                        default='mydefault'
                    ),
                )
            self.context = Context('mytask', args=arguments)
            return Parser([self.context])

        def _parse(self, argstr, parser=None):
            parser = parser or self.parser
            return parser.parse_argv(['mytask'] + argstr.split())

        def _expect(self, argstr, expected, parser=None):
            result = self._parse(argstr, parser)
            eq_(result[0].args.foo.value, expected)

        def no_value_becomes_True_not_default_value(self):
            self._expect('--foo', True)
            self._expect('-f', True)

        def value_given_gets_preserved_normally(self):
            for argstr in (
                '--foo whatever',
                '--foo=whatever',
                '-f whatever',
                '-f=whatever',
            ):
                self._expect(argstr, 'whatever')

        def not_given_at_all_uses_default_value(self):
            self._expect('', 'mydefault')

        def _test_for_ambiguity(self, invoke, parser=None):
            msg = "is ambiguous"
            try:
                self._parse(invoke, parser or self.parser)
            # Expected result
            except ParseError as e:
                assert msg in str(e)
            # No exception occurred at all? Bollocks.
            else:
                assert False
            # Any other exceptions will naturally cause failure here.

        def ambiguity_with_unfilled_posargs(self):
            p = self._parser((
                Argument('foo', optional=True),
                Argument('bar', positional=True)
            ))
            self._test_for_ambiguity("--foo uhoh", p)

        def ambiguity_with_flaglike_value(self):
            self._test_for_ambiguity("--foo --bar")

        def ambiguity_with_actual_other_flag(self):
            p = self._parser((
                Argument('foo', optional=True),
                Argument('bar')
            ))
            self._test_for_ambiguity("--foo --bar")

        def ambiguity_with_task_name(self):
            # mytask --foo myothertask
            c1 = Context('mytask', args=(Argument('foo', optional=True),))
            c2 = Context('othertask')
            p = Parser([c1, c2])
            self._test_for_ambiguity("--foo othertask", p)


class ParseResult_(Spec):
    "ParseResult"
    def setup(self):
        self.context = Context('mytask',
            args=(Argument('foo', kind=str), Argument('bar')))
        argv = ['mytask', '--foo', 'foo-val', '--', 'my', 'remainder']
        self.result = Parser((self.context,)).parse_argv(argv)

    def acts_as_a_list_of_parsed_contexts(self):
        eq_(len(self.result), 1)
        eq_(self.result[0].name, 'mytask')

    def exhibits_remainder_attribute(self):
        eq_(self.result.remainder, 'my remainder')

########NEW FILE########
__FILENAME__ = runner
import sys
import os

from spec import eq_, skip, Spec, raises, ok_, trap

from invoke.runner import Runner, run
from invoke.exceptions import Failure

from _utils import support


def _run(returns=None, **kwargs):
    """
    Create a Runner w/ retval reflecting ``returns`` & call ``run(**kwargs)``.
    """
    # Set up return value tuple for Runner.run
    returns = returns or {}
    returns.setdefault('exited', 0)
    value = map(
        lambda x: returns.get(x, None),
        ('stdout', 'stderr', 'exited', 'exception'),
    )
    class MockRunner(Runner):
        def run(self, command, warn, hide):
            return value
    # Ensure top level run() uses that runner, provide dummy command.
    kwargs['runner'] = MockRunner
    return run("whatever", **kwargs)


class Run(Spec):
    "run()"

    def setup(self):
        os.chdir(support)
        self.both = "echo foo && ./err bar"
        self.out = "echo foo"
        self.err = "./err bar"
        self.sub = "inv -c pty_output hide_%s"

    class return_value:
        def return_code_in_result(self):
            """
            Result has .return_code (and .exited) containing exit code int
            """
            r = run(self.out, hide='both')
            eq_(r.return_code, 0)
            eq_(r.exited, 0)

        def nonzero_return_code_for_failures(self):
            result = run("false", warn=True)
            eq_(result.exited, 1)
            result = run("goobypls", warn=True, hide='both')
            eq_(result.exited, 127)

        def stdout_attribute_contains_stdout(self):
            eq_(run(self.out, hide='both').stdout, 'foo\n')

        def stderr_attribute_contains_stderr(self):
            eq_(run(self.err, hide='both').stderr, 'bar\n')

        def ok_attr_indicates_success(self):
            eq_(_run().ok, True)
            eq_(_run(returns={'exited': 1}, warn=True).ok, False)

        def failed_attr_indicates_failure(self):
            eq_(_run().failed, False)
            eq_(_run(returns={'exited': 1}, warn=True).failed, True)

        def has_exception_attr(self):
            eq_(_run().exception, None)


    class failure_handling:
        @raises(Failure)
        def fast_failures(self):
            run("false")

        def run_acts_as_success_boolean(self):
            ok_(not run("false", warn=True))
            ok_(run("true"))

        def non_one_return_codes_still_act_as_False(self):
            ok_(not run("goobypls", warn=True, hide='both'))

        def warn_kwarg_allows_continuing_past_failures(self):
            eq_(run("false", warn=True).exited, 1)

        def Failure_repr_includes_stderr(self):
            try:
                run("./err ohnoz && exit 1", hide='both')
                assert false # Ensure failure to Failure fails
            except Failure as f:
                r = repr(f)
                assert 'ohnoz' in r, "Sentinel 'ohnoz' not found in %r" % r

    class output_controls:
        @trap
        def _hide_both(self, val):
            run(self.both, hide=val)
            eq_(sys.stdall.getvalue(), "")

        def hide_both_hides_everything(self):
            self._hide_both('both')

        def hide_True_hides_everything(self):
            self._hide_both(True)

        @trap
        def hide_out_only_hides_stdout(self):
            run(self.both, hide='out')
            eq_(sys.stdout.getvalue().strip(), "")
            eq_(sys.stderr.getvalue().strip(), "bar")

        @trap
        def hide_err_only_hides_stderr(self):
            run(self.both, hide='err')
            eq_(sys.stdout.getvalue().strip(), "foo")
            eq_(sys.stderr.getvalue().strip(), "")

        @trap
        def hide_accepts_stderr_alias_for_err(self):
            run(self.both, hide='stderr')
            eq_(sys.stdout.getvalue().strip(), "foo")
            eq_(sys.stderr.getvalue().strip(), "")

        @trap
        def hide_accepts_stdout_alias_for_out(self):
            run(self.both, hide='stdout')
            eq_(sys.stdout.getvalue().strip(), "")
            eq_(sys.stderr.getvalue().strip(), "bar")

        def hide_both_hides_both_under_pty(self):
            r = run(self.sub % 'both', hide='both')
            eq_(r.stdout, "")
            eq_(r.stderr, "")

        def hide_out_hides_both_under_pty(self):
            r = run(self.sub % 'out', hide='both')
            eq_(r.stdout, "")
            eq_(r.stderr, "")

        def hide_err_has_no_effect_under_pty(self):
            r = run(self.sub % 'err', hide='both')
            eq_(r.stdout, "foo\r\nbar\r\n")
            eq_(r.stderr, "")

        @trap
        def _no_hiding(self, val):
            r = run(self.both, hide=val)
            eq_(sys.stdout.getvalue().strip(), "foo")
            eq_(sys.stderr.getvalue().strip(), "bar")

        def hide_None_hides_nothing(self):
            self._no_hiding(None)

        def hide_False_hides_nothing(self):
            self._no_hiding(False)

        @raises(ValueError)
        def hide_unknown_vals_raises_ValueError(self):
            run("command", hide="what")

        def hide_unknown_vals_mention_value_given_in_error(self):
            value = "penguinmints"
            try:
                run("command", hide=value)
            except ValueError as e:
                msg = "Error from run(hide=xxx) did not tell user what the bad value was!"
                msg += "\nException msg: %s" % e
                ok_(value in str(e), msg)
            else:
                assert False, "run() did not raise ValueError for bad hide= value"

        def hide_does_not_affect_capturing(self):
            eq_(run(self.out, hide='both').stdout, 'foo\n')

    class pseudo_terminals:
        def return_value_indicates_whether_pty_was_used(self):
            eq_(run("true").pty, False)
            eq_(run("true", pty=True).pty, True)

        def pty_defaults_to_off(self):
            eq_(run("true").pty, False)

    class command_echo:
        @trap
        def does_not_echo_commands_run_by_default(self):
            run("echo hi")
            eq_(sys.stdout.getvalue().strip(), "hi")

        @trap
        def when_echo_True_commands_echoed_in_bold(self):
            run("echo hi", echo=True)
            expected = "\033[1;37mecho hi\033[0m\nhi"
            eq_(sys.stdout.getvalue().strip(), expected)

    #
    # Random edge/corner case junk
    #

    def non_stupid_OSErrors_get_captured(self):
        # Somehow trigger an OSError saying "Input/output error" within
        # pexpect.spawn().interact() & assert it is in result.exception
        skip()

    def KeyboardInterrupt_on_stdin_doesnt_flake(self):
        # E.g. inv test => Ctrl-C halfway => shouldn't get buffer API errors
        skip()

    class funky_characters_in_stdout:
        def basic_nonstandard_characters(self):
            # Crummy "doesn't explode with decode errors" test
            run("cat tree.out", hide='both')

        def nonprinting_bytes(self):
            # Seriously non-printing characters (i.e. non UTF8) also don't asplode
            # load('funky').derp()
            run("echo '\xff'", hide='both')

        def nonprinting_bytes_pty(self):
            # PTY use adds another utf-8 decode spot which can also fail.
            run("echo '\xff'", pty=True, hide='both')


class Local_(Spec):
    def setup(self):
        os.chdir(support)
        self.both = "echo foo && ./err bar"

    def stdout_contains_both_streams_under_pty(self):
        r = run(self.both, hide='both', pty=True)
        eq_(r.stdout, 'foo\r\nbar\r\n')

    def stderr_is_empty_under_pty(self):
        r = run(self.both, hide='both', pty=True)
        eq_(r.stderr, '')

########NEW FILE########
__FILENAME__ = tasks
from spec import Spec, skip, eq_, raises

from invoke.tasks import task, ctask, Task
from invoke.loader import FilesystemLoader as Loader

from _utils import support


#
# NOTE: Most Task tests use @task as it's the primary interface and is a very
# thin wrapper around Task itself. This way we don't have to write 2x tests for
# both Task and @task. Meh :)
#

def _func():
    pass

class task_(Spec):
    "@task"

    def setup(self):
        self.loader = Loader(start=support)
        self.vanilla = self.loader.load('decorator')

    def allows_access_to_wrapped_object(self):
        def lolcats():
            pass
        eq_(task(lolcats).body, lolcats)

    def allows_alias_specification(self):
        eq_(self.vanilla['foo'], self.vanilla['bar'])

    def allows_multiple_aliases(self):
        eq_(self.vanilla['foo'], self.vanilla['otherbar'])

    def allows_default_specification(self):
        eq_(self.vanilla[''], self.vanilla['biz'])

    @raises(ValueError)
    def raises_ValueError_on_multiple_defaults(self):
        self.loader.load('decorator_multi_default')

    def sets_arg_help(self):
        eq_(self.vanilla['punch'].help['why'], 'Motive')

    def sets_arg_kind(self):
        skip()

    def sets_which_args_are_optional(self):
        eq_(self.vanilla['optional_values'].optional, ('myopt',))

    def allows_annotating_args_as_positional(self):
        eq_(self.vanilla['one_positional'].positional, ['pos'])
        eq_(self.vanilla['two_positionals'].positional, ['pos1', 'pos2'])

    def when_positional_arg_missing_all_non_default_args_are_positional(self):
        eq_(self.vanilla['implicit_positionals'].positional, ['pos1', 'pos2'])

    def context_arguments_should_not_appear_in_implicit_positional_list(self):
        @ctask
        def mytask(ctx):
            pass
        eq_(len(mytask.positional), 0)

    def pre_tasks_stored_directly(self):
        @task
        def whatever():
            pass
        @task(pre=[whatever])
        def func():
            pass
        eq_(func.pre, [whatever])

    def allows_star_args_as_shortcut_for_pre(self):
        @task
        def pre1():
            pass
        @task
        def pre2():
            pass
        @task(pre1, pre2)
        def func():
            pass
        eq_(func.pre, (pre1, pre2))

    @raises(TypeError)
    def disallows_ambiguity_between_star_args_and_pre_kwarg(self):
        @task
        def pre1():
            pass
        @task
        def pre2():
            pass
        @task(pre1, pre=[pre2])
        def func():
            pass

    def passes_in_contextualized_kwarg(self):
        @task
        def task1():
            pass
        @task(contextualized=True)
        def task2(ctx):
            pass
        assert not task1.contextualized
        assert task2.contextualized

    def sets_name(self):
        @task(name='foo')
        def bar():
            pass
        eq_(bar.name, 'foo')


class ctask_(Spec):
    def behaves_like_task_with_contextualized_True(self):
        @ctask
        def mytask(ctx):
            pass
        assert mytask.contextualized


class Task_(Spec):
    def has_useful_repr(self):
        i = repr(Task(_func))
        assert '_func' in i, "'func' not found in {0!r}".format(i)
        e = repr(Task(_func, name='funky'))
        assert 'funky' in e, "'funky' not found in {0!r}".format(e)
        assert '_func' not in e, "'_func' unexpectedly seen in {0!r}".format(e)

    def equality_testing(self):
        t1 = Task(_func, name='foo')
        t2 = Task(_func, name='foo')
        eq_(t1, t2)
        t3 = Task(_func, name='bar')
        assert t1 != t3

    class attributes:
        def has_default_flag(self):
            eq_(Task(_func).is_default, False)

        def has_contextualized_flag(self):
            eq_(Task(_func).contextualized, False)

        def name_defaults_to_body_name(self):
            eq_(Task(_func).name, '_func')

        def can_override_name(self):
            eq_(Task(_func, name='foo').name, 'foo')

    class callability:
        def setup(self):
            @task
            def foo():
                "My docstring"
                return 5
            self.task = foo

        def dunder_call_wraps_body_call(self):
            eq_(self.task(), 5)

        @raises(TypeError)
        def errors_if_contextualized_and_first_arg_not_Context(self):
            @ctask
            def mytask(ctx):
                pass
            mytask(5)

        def tracks_times_called(self):
            eq_(self.task.called, False)
            self.task()
            eq_(self.task.called, True)
            eq_(self.task.times_called, 1)
            self.task()
            eq_(self.task.times_called, 2)

        def wraps_body_docstring(self):
            eq_(self.task.__doc__, "My docstring")

        def wraps_body_name(self):
            eq_(self.task.__name__, "foo")

    class get_arguments:
        def setup(self):
            @task(positional=['arg_3', 'arg1'], optional=['arg1'])
            def mytask(arg1, arg2=False, arg_3=5):
                pass
            self.task = mytask
            self.args = self.task.get_arguments()
            self.argdict = self._arglist_to_dict(self.args)

        def _arglist_to_dict(self, arglist):
            # This kinda duplicates Context.add_arg(x) for x in arglist :(
            ret = {}
            for arg in arglist:
                for name in arg.names:
                    ret[name] = arg
            return ret

        def _task_to_dict(self, task):
            return self._arglist_to_dict(task.get_arguments())

        def positional_args_come_first(self):
            eq_(self.args[0].name, 'arg_3')
            eq_(self.args[1].name, 'arg1')
            eq_(self.args[2].name, 'arg2')

        def kinds_are_preserved(self):
            eq_(
                [x.kind for x in self.args],
                # Remember that the default 'kind' is a string.
                [int, str, bool]
            )

        def positional_flag_is_preserved(self):
            eq_(
                [x.positional for x in self.args],
                [True, True, False]
            )

        def optional_flag_is_preserved(self):
            eq_(
                [x.optional for x in self.args],
                [False, True, False]
            )

        def turns_function_signature_into_Arguments(self):
            eq_(len(self.args), 3, str(self.args))
            assert 'arg2' in self.argdict

        def shortflags_created_by_default(self):
            assert 'a' in self.argdict
            assert self.argdict['a'] is self.argdict['arg1']

        def shortflags_dont_care_about_positionals(self):
            "Positionalness doesn't impact whether shortflags are made"
            for short, long_ in (
                ('a', 'arg1'),
                ('r', 'arg2'),
                ('g', 'arg-3'),
            ):
                assert self.argdict[short] is self.argdict[long_]

        def autocreated_short_flags_can_be_disabled(self):
            @task(auto_shortflags=False)
            def mytask(arg):
                pass
            args = self._task_to_dict(mytask)
            assert 'a' not in args
            assert 'arg' in args

        def autocreated_shortflags_dont_collide(self):
            "auto-created short flags don't collide"
            @task
            def mytask(arg1, arg2, barg):
                pass
            args = self._task_to_dict(mytask)
            assert 'a' in args
            assert args['a'] is args['arg1']
            assert 'r' in args
            assert args['r'] is args['arg2']
            assert 'b' in args
            assert args['b'] is args['barg']

        def early_auto_shortflags_shouldnt_lock_out_real_shortflags(self):
            # I.e. "task --foo -f" => --foo should NOT get to pick '-f' for its
            # shortflag or '-f' is totally fucked.
            @task
            def mytask(longarg, l):
                pass
            args = self._task_to_dict(mytask)
            assert 'longarg' in args
            assert 'o' in args
            assert args['o'] is args['longarg']
            assert 'l' in args

        def context_arguments_are_not_returned(self):
            @ctask
            def mytask(ctx):
                pass
            eq_(len(mytask.get_arguments()), 0)

        def underscores_become_dashes(self):
            @task
            def mytask(longer_arg):
                pass
            arg = mytask.get_arguments()[0]
            eq_(arg.names, ('longer-arg', 'l'))
            eq_(arg.attr_name, 'longer_arg')
            eq_(arg.name, 'longer_arg')

########NEW FILE########
__FILENAME__ = alias_sorting
from invoke import task, Collection

@task(aliases=('z', 'a'))
def toplevel():
    pass

########NEW FILE########
__FILENAME__ = contextualized
from invoke import ctask


@ctask
def go(ctx):
    return ctx


@ctask
def run(ctx):
    ctx.run('x')

########NEW FILE########
__FILENAME__ = debugging
from invoke import task
from invoke.util import debug


@task
def foo():
    debug("my-sentinel")

########NEW FILE########
__FILENAME__ = decorator
from invoke.tasks import task


@task(aliases=('bar', 'otherbar'))
def foo():
    """
    Foo the bar.
    """
    pass

@task
def foo2():
    """
    Foo the bar:

      example code

    Added in 1.0
    """
    pass

@task(default=True)
def biz():
    pass

@task(help={'why': 'Motive', 'who': 'Who to punch'})
def punch(who, why):
    pass

@task(positional=['pos'])
def one_positional(pos, nonpos):
    pass

@task(positional=['pos1', 'pos2'])
def two_positionals(pos1, pos2, nonpos):
    pass

@task
def implicit_positionals(pos1, pos2, nonpos=None):
    pass

@task(optional=['myopt'])
def optional_values(myopt):
    pass

########NEW FILE########
__FILENAME__ = decorator_multi_default
from invoke.tasks import task


@task(default=True)
def foo():
    pass

@task(default=True)
def biz():
    pass

########NEW FILE########
__FILENAME__ = deeper_ns_list
from invoke import task, Collection

@task
def toplevel():
    pass

@task
def subtask():
    pass

ns = Collection(toplevel, Collection('a', subtask, Collection('nother', subtask)))

########NEW FILE########
__FILENAME__ = docstrings
from invoke import task


@task
def no_docstring():
    pass

@task
def one_line():
    """foo
    """
@task
def two_lines():
    """foo
    bar
    """

@task
def leading_whitespace():
    """
    foo
    """

@task(aliases=('a', 'b'))
def with_aliases():
    """foo
    """

########NEW FILE########
__FILENAME__ = explicit_root
from invoke import task, Collection


@task(aliases=['othertop'])
def top_level():
    pass

@task(aliases=['othersub'], default=True)
def sub_task():
    pass

sub = Collection('sub', sub_task)
ns = Collection(top_level, sub)

########NEW FILE########
__FILENAME__ = fail
from invoke.tasks import task
from invoke.runner import run

@task
def simple():
    run("false")

@task(positional=['pos'])
def missing_pos(pos):
    pass

########NEW FILE########
__FILENAME__ = foo
from invoke.tasks import task

@task
def mytask():
    pass

########NEW FILE########
__FILENAME__ = tasks
from invoke.tasks import task


@task
def foo():
    print("Hm")

########NEW FILE########
__FILENAME__ = integration
from invoke.tasks import task


@task
def print_foo():
    print("foo")

@task
def print_name(name):
    print(name)

@task
def print_underscored_arg(my_option):
    print(my_option)

@task
def foo():
    print("foo")

@task(foo)
def bar():
    print("bar")

########NEW FILE########
__FILENAME__ = namespacing
from invoke import Collection, task

from package import module

@task
def toplevel():
    pass

ns = Collection(module, toplevel)

########NEW FILE########
__FILENAME__ = oops
import modulethatdoesnotexistohnoes

########NEW FILE########
__FILENAME__ = module
from invoke import task

@task
def mytask():
    pass

########NEW FILE########
__FILENAME__ = pty_output
from invoke.tasks import task
from invoke.runner import run


cmd = "echo foo && ./err bar"


def _go(hide):
    run(cmd, hide=hide, pty=True)

@task
def hide_out():
    _go('out')

@task
def hide_err():
    _go('err')

@task
def hide_both():
    _go('both')

########NEW FILE########
__FILENAME__ = simple_ns_list
from invoke import task, Collection

@task
def z_toplevel():
    pass

@task
def subtask():
    pass

ns = Collection(z_toplevel, Collection('a', subtask))

########NEW FILE########
__FILENAME__ = subcollection_task_name
from invoke import task


@task(name='explicit_name')
def implicit_name():
    pass

########NEW FILE########
__FILENAME__ = _utils
import os, sys
from contextlib import contextmanager


support = os.path.join(os.path.dirname(__file__), '_support')

@contextmanager
def support_path():
    sys.path.insert(0, support)
    yield
    sys.path.pop(0)

def load(name):
    with support_path():
        return __import__(name)

########NEW FILE########
