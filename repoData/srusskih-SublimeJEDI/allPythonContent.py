__FILENAME__ = classes
"""
The :mod:`jedi.api.classes` module contains the return classes of the API.
These classes are the much bigger part of the whole API, because they contain
the interesting information about completion and goto operations.
"""
import warnings
from itertools import chain

from jedi._compatibility import next, unicode, use_metaclass
from jedi import settings
from jedi import common
from jedi.parser import representation as pr
from jedi.cache import underscore_memoization
from jedi.evaluate.cache import memoize_default, CachedMetaClass
from jedi.evaluate import representation as er
from jedi.evaluate import iterable
from jedi.evaluate import imports
from jedi.evaluate import compiled
from jedi.api import keywords
from jedi.evaluate.finder import get_names_of_scope


def defined_names(evaluator, scope):
    """
    List sub-definitions (e.g., methods in class).

    :type scope: Scope
    :rtype: list of Definition
    """
    pair = next(get_names_of_scope(evaluator, scope, star_search=False,
                                   include_builtin=False), None)
    names = pair[1] if pair else []
    names = [n for n in names if isinstance(n, pr.Import) or (len(n) == 1)]
    return [Definition(evaluator, d) for d in sorted(names, key=lambda s: s.start_pos)]


class BaseDefinition(object):
    _mapping = {
        'posixpath': 'os.path',
        'riscospath': 'os.path',
        'ntpath': 'os.path',
        'os2emxpath': 'os.path',
        'macpath': 'os.path',
        'genericpath': 'os.path',
        'posix': 'os',
        '_io': 'io',
        '_functools': 'functools',
        '_sqlite3': 'sqlite3',
        '__builtin__': '',
        'builtins': '',
    }

    _tuple_mapping = dict((tuple(k.split('.')), v) for (k, v) in {
        'argparse._ActionsContainer': 'argparse.ArgumentParser',
        '_sre.SRE_Match': 're.MatchObject',
        '_sre.SRE_Pattern': 're.RegexObject',
    }.items())

    def __init__(self, evaluator, definition, start_pos):
        self._evaluator = evaluator
        self._start_pos = start_pos
        self._definition = definition
        """
        An instance of :class:`jedi.parsing_representation.Base` subclass.
        """
        self.is_keyword = isinstance(definition, keywords.Keyword)

        # generate a path to the definition
        self._module = definition.get_parent_until()
        if self.in_builtin_module():
            self.module_path = None
        else:
            self.module_path = self._module.path
            """Shows the file path of a module. e.g. ``/usr/lib/python2.7/os.py``"""

    @property
    def start_pos(self):
        """
        .. deprecated:: 0.7.0
           Use :attr:`.line` and :attr:`.column` instead.
        .. todo:: Remove!
        """
        warnings.warn("Use line/column instead.", DeprecationWarning)
        return self._start_pos

    @property
    def type(self):
        """
        The type of the definition.

        Here is an example of the value of this attribute.  Let's consider
        the following source.  As what is in ``variable`` is unambiguous
        to Jedi, :meth:`jedi.Script.goto_definitions` should return a list of
        definition for ``sys``, ``f``, ``C`` and ``x``.

        >>> from jedi import Script
        >>> source = '''
        ... import keyword
        ...
        ... class C:
        ...     pass
        ...
        ... class D:
        ...     pass
        ...
        ... x = D()
        ...
        ... def f():
        ...     pass
        ...
        ... variable = keyword or f or C or x'''
        >>> script = Script(source, len(source.splitlines()), 3, 'example.py')
        >>> defs = script.goto_definitions()

        Before showing what is in ``defs``, let's sort it by :attr:`line`
        so that it is easy to relate the result to the source code.

        >>> defs = sorted(defs, key=lambda d: d.line)
        >>> defs                           # doctest: +NORMALIZE_WHITESPACE
        [<Definition module keyword>, <Definition class C>,
         <Definition class D>, <Definition def f>]

        Finally, here is what you can get from :attr:`type`:

        >>> defs[0].type
        'module'
        >>> defs[1].type
        'class'
        >>> defs[2].type
        'instance'
        >>> defs[3].type
        'function'

        """
        # generate the type
        stripped = self._definition
        if isinstance(stripped, compiled.CompiledObject):
            return stripped.type()
        if isinstance(stripped, er.InstanceElement):
            stripped = stripped.var
        if isinstance(stripped, pr.NamePart):
            stripped = stripped.parent
        if isinstance(stripped, pr.Name):
            stripped = stripped.parent
        return type(stripped).__name__.lower()

    def _path(self):
        """The module path."""
        path = []

        def insert_nonnone(x):
            if x:
                path.insert(0, x)

        if not isinstance(self._definition, keywords.Keyword):
            par = self._definition
            while par is not None:
                if isinstance(par, pr.Import):
                    insert_nonnone(par.namespace)
                    insert_nonnone(par.from_ns)
                    if par.relative_count == 0:
                        break
                with common.ignored(AttributeError):
                    path.insert(0, par.name)
                par = par.parent
        return path

    @property
    def module_name(self):
        """
        The module name.

        >>> from jedi import Script
        >>> source = 'import json'
        >>> script = Script(source, path='example.py')
        >>> d = script.goto_definitions()[0]
        >>> print(d.module_name)                       # doctest: +ELLIPSIS
        json
        """
        return str(self._module.name)

    def in_builtin_module(self):
        """Whether this is a builtin module."""
        return isinstance(self._module, compiled.CompiledObject)

    @property
    def line_nr(self):
        """
        .. deprecated:: 0.5.0
           Use :attr:`.line` instead.
        .. todo:: Remove!
        """
        warnings.warn("Use line instead.", DeprecationWarning)
        return self.line

    @property
    def line(self):
        """The line where the definition occurs (starting with 1)."""
        if self.in_builtin_module():
            return None
        return self._start_pos[0]

    @property
    def column(self):
        """The column where the definition occurs (starting with 0)."""
        if self.in_builtin_module():
            return None
        return self._start_pos[1]

    def docstring(self, raw=False):
        r"""
        Return a document string for this completion object.

        Example:

        >>> from jedi import Script
        >>> source = '''\
        ... def f(a, b=1):
        ...     "Document for function f."
        ... '''
        >>> script = Script(source, 1, len('def f'), 'example.py')
        >>> doc = script.goto_definitions()[0].docstring()
        >>> print(doc)
        f(a, b = 1)
        <BLANKLINE>
        Document for function f.

        Notice that useful extra information is added to the actual
        docstring.  For function, it is call signature.  If you need
        actual docstring, use ``raw=True`` instead.

        >>> print(script.goto_definitions()[0].docstring(raw=True))
        Document for function f.

        """
        if raw:
            return _Help(self._definition).raw()
        else:
            return _Help(self._definition).full()

    @property
    def doc(self):
        """
        .. deprecated:: 0.8.0
           Use :meth:`.docstring` instead.
        .. todo:: Remove!
        """
        warnings.warn("Use documentation() instead.", DeprecationWarning)
        return self.docstring()

    @property
    def raw_doc(self):
        """
        .. deprecated:: 0.8.0
           Use :meth:`.docstring` instead.
        .. todo:: Remove!
        """
        warnings.warn("Use documentation() instead.", DeprecationWarning)
        return self.docstring(raw=True)

    @property
    def description(self):
        """A textual description of the object."""
        return unicode(self._definition)

    @property
    def full_name(self):
        """
        Dot-separated path of this object.

        It is in the form of ``<module>[.<submodule>[...]][.<object>]``.
        It is useful when you want to look up Python manual of the
        object at hand.

        Example:

        >>> from jedi import Script
        >>> source = '''
        ... import os
        ... os.path.join'''
        >>> script = Script(source, 3, len('os.path.join'), 'example.py')
        >>> print(script.goto_definitions()[0].full_name)
        os.path.join

        Notice that it correctly returns ``'os.path.join'`` instead of
        (for example) ``'posixpath.join'``.

        """
        path = [unicode(p) for p in self._path()]
        # TODO add further checks, the mapping should only occur on stdlib.
        if not path:
            return None  # for keywords the path is empty

        with common.ignored(KeyError):
            path[0] = self._mapping[path[0]]
        for key, repl in self._tuple_mapping.items():
            if tuple(path[:len(key)]) == key:
                path = [repl] + path[len(key):]

        return '.'.join(path if path[0] else path[1:])

    @memoize_default()
    def _follow_statements_imports(self):
        """
        Follow both statements and imports, as far as possible.
        """
        stripped = self._definition
        if isinstance(stripped, pr.Name):
            stripped = stripped.parent
            # We should probably work in `Finder._names_to_types` here.
            if isinstance(stripped, pr.Function):
                stripped = er.Function(self._evaluator, stripped)
            elif isinstance(stripped, pr.Class):
                stripped = er.Class(self._evaluator, stripped)

        if stripped.isinstance(pr.Statement):
            return self._evaluator.eval_statement(stripped)
        elif stripped.isinstance(pr.Import):
            return imports.strip_imports(self._evaluator, [stripped])
        else:
            return [stripped]

    @property
    @memoize_default()
    def params(self):
        """
        Raises an ``AttributeError``if the definition is not callable.
        Otherwise returns a list of `Definition` that represents the params.
        """
        followed = self._follow_statements_imports()
        if not followed or not followed[0].is_callable():
            raise AttributeError()
        followed = followed[0]  # only check the first one.

        if followed.isinstance(er.Function):
            if isinstance(followed, er.InstanceElement):
                params = followed.params[1:]
            else:
                params = followed.params
        elif followed.isinstance(er.compiled.CompiledObject):
            params = followed.params
        else:
            try:
                sub = followed.get_subscope_by_name('__init__')
                params = sub.params[1:]  # ignore self
            except KeyError:
                return []
        return [_Param(self._evaluator, p) for p in params]

    def parent(self):
        if isinstance(self._definition, compiled.CompiledObject):
            non_flow = self._definition.parent
        else:
            scope = self._definition.get_parent_until(pr.IsScope, include_current=False)
            non_flow = scope.get_parent_until(pr.Flow, reverse=True)
        return Definition(self._evaluator, non_flow)

    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, self.description)


class Completion(BaseDefinition):
    """
    `Completion` objects are returned from :meth:`api.Script.completions`. They
    provide additional information about a completion.
    """
    def __init__(self, evaluator, name, needs_dot, like_name_length, base):
        super(Completion, self).__init__(evaluator, name.parent, name.start_pos)

        self._name = name
        self._needs_dot = needs_dot
        self._like_name_length = like_name_length
        self._base = base

        # Completion objects with the same Completion name (which means
        # duplicate items in the completion)
        self._same_name_completions = []

    def _complete(self, like_name):
        dot = '.' if self._needs_dot else ''
        append = ''
        if settings.add_bracket_after_function \
                and self.type == 'Function':
            append = '('

        if settings.add_dot_after_module:
            if isinstance(self._base, pr.Module):
                append += '.'
        if isinstance(self._base, pr.Param):
            append += '='

        name = str(self._name.names[-1])
        if like_name:
            name = name[self._like_name_length:]
        return dot + name + append

    @property
    def complete(self):
        """
        Return the rest of the word, e.g. completing ``isinstance``::

            isinstan# <-- Cursor is here

        would return the string 'ce'. It also adds additional stuff, depending
        on your `settings.py`.
        """
        return self._complete(True)

    @property
    def name(self):
        """
        Similar to :attr:`complete`, but return the whole word, for
        example::

            isinstan

        would return `isinstance`.
        """
        return unicode(self._name.names[-1])

    @property
    def name_with_symbols(self):
        """
        Similar to :attr:`name`, but like :attr:`name`
        returns also the symbols, for example::

            list()

        would return ``.append`` and others (which means it adds a dot).
        """
        return self._complete(False)

    @property
    def word(self):
        """
        .. deprecated:: 0.6.0
           Use :attr:`.name` instead.
        .. todo:: Remove!
        """
        warnings.warn("Use name instead.", DeprecationWarning)
        return self.name

    @property
    def description(self):
        """Provide a description of the completion object."""
        parent = self._name.parent
        if parent is None:
            return ''
        t = self.type
        if t == 'statement' or t == 'import':
            desc = self._definition.get_code(False)
        else:
            desc = '.'.join(unicode(p) for p in self._path())

        line = '' if self.in_builtin_module else '@%s' % self.line
        return '%s: %s%s' % (t, desc, line)

    def __repr__(self):
        return '<%s: %s>' % (type(self).__name__, self._name)

    def docstring(self, raw=False, fast=True):
        """
        :param fast: Don't follow imports that are only one level deep like
            ``import foo``, but follow ``from foo import bar``. This makes
            sense for speed reasons. Completing `import a` is slow if you use
            the ``foo.documentation(fast=False)`` on every object, because it
            parses all libraries starting with ``a``.
        """
        definition = self._definition
        if isinstance(self._definition, pr.Import):
            i = imports.ImportWrapper(self._evaluator, self._definition)
            if len(i.import_path) > 1 or not fast:
                followed = self._follow_statements_imports()
                if followed:
                    # TODO: Use all of the followed objects as input to Documentation.
                    definition = followed[0]

        if raw:
            return _Help(definition).raw()
        else:
            return _Help(definition).full()

    @property
    def type(self):
        """
        The type of the completion objects. Follows imports. For a further
        description, look at :attr:`jedi.api.classes.BaseDefinition.type`.
        """
        if isinstance(self._definition, pr.Import):
            i = imports.ImportWrapper(self._evaluator, self._definition)
            if len(i.import_path) <= 1:
                return 'module'

            followed = self.follow_definition()
            if followed:
                # Caveat: Only follows the first one, ignore the other ones.
                # This is ok, since people are almost never interested in
                # variations.
                return followed[0].type
        return super(Completion, self).type

    @memoize_default()
    def _follow_statements_imports(self):
        # imports completion is very complicated and needs to be treated
        # separately in Completion.
        if self._definition.isinstance(pr.Import) and self._definition.alias is None:
            i = imports.ImportWrapper(self._evaluator, self._definition, True)
            import_path = i.import_path + (unicode(self._name),)
            try:
                return imports.get_importer(self._evaluator, import_path,
                                            i._importer.module).follow(self._evaluator)
            except imports.ModuleNotFound:
                pass
        return super(Completion, self)._follow_statements_imports()

    @memoize_default()
    def follow_definition(self):
        """
        Return the original definitions. I strongly recommend not using it for
        your completions, because it might slow down |jedi|. If you want to
        read only a few objects (<=20), it might be useful, especially to get
        the original docstrings. The basic problem of this function is that it
        follows all results. This means with 1000 completions (e.g.  numpy),
        it's just PITA-slow.
        """
        defs = self._follow_statements_imports()
        return [Definition(self._evaluator, d) for d in defs]


class Definition(use_metaclass(CachedMetaClass, BaseDefinition)):
    """
    *Definition* objects are returned from :meth:`api.Script.goto_assignments`
    or :meth:`api.Script.goto_definitions`.
    """
    def __init__(self, evaluator, definition):
        super(Definition, self).__init__(evaluator, definition, definition.start_pos)

    @property
    @underscore_memoization
    def name(self):
        """
        Name of variable/function/class/module.

        For example, for ``x = None`` it returns ``'x'``.

        :rtype: str or None
        """
        d = self._definition
        if isinstance(d, er.InstanceElement):
            d = d.var

        if isinstance(d, (compiled.CompiledObject, compiled.CompiledName)):
            name = d.name
        elif isinstance(d, pr.Name):
            name = d.names[-1]
        elif isinstance(d, iterable.Array):
            name = d.type
        elif isinstance(d, (pr.Class, er.Class, er.Instance,
                            er.Function, pr.Function)):
            name = d.name
        elif isinstance(d, pr.Module):
            name = self.module_name
        elif isinstance(d, pr.Import):
            try:
                name = d.get_defined_names()[0].names[-1]
            except (AttributeError, IndexError):
                return None
        elif isinstance(d, pr.Statement):
            try:
                expression_list = d.assignment_details[0][0]
                name = expression_list[0].name.names[-1]
            except IndexError:
                if isinstance(d, pr.Param):
                    try:
                        return unicode(d.expression_list()[0].name)
                    except (IndexError, AttributeError):
                        # IndexError for syntax error params
                        # AttributeError for *args/**kwargs
                        pass
                return None
        elif isinstance(d, iterable.Generator):
            return None
        elif isinstance(d, pr.NamePart):
            name = d
        return unicode(name)

    @property
    def description(self):
        """
        A description of the :class:`.Definition` object, which is heavily used
        in testing. e.g. for ``isinstance`` it returns ``def isinstance``.

        Example:

        >>> from jedi import Script
        >>> source = '''
        ... def f():
        ...     pass
        ...
        ... class C:
        ...     pass
        ...
        ... variable = f or C'''
        >>> script = Script(source, column=3)  # line is maximum by default
        >>> defs = script.goto_definitions()
        >>> defs = sorted(defs, key=lambda d: d.line)
        >>> defs
        [<Definition def f>, <Definition class C>]
        >>> str(defs[0].description)  # strip literals in python2
        'def f'
        >>> str(defs[1].description)
        'class C'

        """
        d = self._definition
        if isinstance(d, er.InstanceElement):
            d = d.var
        if isinstance(d, pr.Name):
            d = d.parent

        if isinstance(d, compiled.CompiledObject):
            d = d.type() + ' ' + d.name
        elif isinstance(d, iterable.Array):
            d = 'class ' + d.type
        elif isinstance(d, (pr.Class, er.Class, er.Instance)):
            d = 'class ' + unicode(d.name)
        elif isinstance(d, (er.Function, pr.Function)):
            d = 'def ' + unicode(d.name)
        elif isinstance(d, pr.Module):
            # only show module name
            d = 'module %s' % self.module_name
        elif self.is_keyword:
            d = 'keyword %s' % d.name
        else:
            d = d.get_code().replace('\n', '').replace('\r', '')
        return d

    @property
    def desc_with_module(self):
        """
        In addition to the definition, also return the module.

        .. warning:: Don't use this function yet, its behaviour may change. If
            you really need it, talk to me.

        .. todo:: Add full path. This function is should return a
            `module.class.function` path.
        """
        position = '' if self.in_builtin_module else '@%s' % (self.line)
        return "%s:%s%s" % (self.module_name, self.description, position)

    @memoize_default()
    def defined_names(self):
        """
        List sub-definitions (e.g., methods in class).

        :rtype: list of Definition
        """
        defs = self._follow_statements_imports()
        # For now we don't want base classes or evaluate decorators.
        defs = [d.base if isinstance(d, (er.Class, er.Function)) else d for d in defs]
        iterable = (defined_names(self._evaluator, d) for d in defs)
        iterable = list(iterable)
        return list(chain.from_iterable(iterable))

    def __eq__(self, other):
        return self._start_pos == other._start_pos \
            and self.module_path == other.module_path \
            and self.name == other.name \
            and self._evaluator == other._evaluator

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._start_pos, self.module_path, self.name, self._evaluator))


class CallSignature(Definition):
    """
    `CallSignature` objects is the return value of `Script.function_definition`.
    It knows what functions you are currently in. e.g. `isinstance(` would
    return the `isinstance` function. without `(` it would return nothing.
    """
    def __init__(self, evaluator, executable, call, index, key_name):
        super(CallSignature, self).__init__(evaluator, executable)
        self._index = index
        self._key_name = key_name
        self._call = call

    @property
    def index(self):
        """
        The Param index of the current call.
        Returns None if the index doesn't is not defined.
        """
        if self._key_name is not None:
            for i, param in enumerate(self.params):
                if self._key_name == param.name:
                    return i
            if self.params and self.params[-1]._definition.stars == 2:
                return i
            else:
                return None

        if self._index >= len(self.params):

            for i, param in enumerate(self.params):
                # *args case
                if param._definition.stars == 1:
                    return i
            return None
        return self._index

    @property
    def bracket_start(self):
        """
        The indent of the bracket that is responsible for the last function
        call.
        """
        c = self._call
        while c.next is not None:
            c = c.next
        return c.name.end_pos

    @property
    def call_name(self):
        """
        .. deprecated:: 0.8.0
           Use :attr:`.name` instead.
        .. todo:: Remove!

        The name (e.g. 'isinstance') as a string.
        """
        warnings.warn("Use name instead.", DeprecationWarning)
        return unicode(self._definition.name)

    @property
    def module(self):
        """
        .. deprecated:: 0.8.0
           Use :attr:`.module_name` for the module name.
        .. todo:: Remove!
        """
        return self._executable.get_parent_until()

    def __repr__(self):
        return '<%s: %s index %s>' % (type(self).__name__, self._definition,
                                      self.index)


class _Param(Definition):
    """
    Just here for backwards compatibility.
    """
    def get_code(self):
        """
        .. deprecated:: 0.8.0
           Use :attr:`.description` and :attr:`.name` instead.
        .. todo:: Remove!

        A function to get the whole code of the param.
        """
        warnings.warn("Use description instead.", DeprecationWarning)
        return self.description


class _Help(object):
    """
    Temporary implementation, will be used as `Script.help() or something in
    the future.
    """
    def __init__(self, definition):
        self._definition = definition

    def full(self):
        try:
            return self._definition.doc
        except AttributeError:
            return self.raw()

    def raw(self):
        """
        The raw docstring ``__doc__`` for any object.

        See :attr:`doc` for example.
        """
        try:
            return self._definition.raw_doc
        except AttributeError:
            return ''

########NEW FILE########
__FILENAME__ = helpers
"""
Helpers for the API
"""
import re

from jedi.evaluate import imports


def completion_parts(path_until_cursor):
    """
    Returns the parts for the completion
    :return: tuple - (path, dot, like)
    """
    match = re.match(r'^(.*?)(\.|)(\w?[\w\d]*)$', path_until_cursor, flags=re.S)
    return match.groups()


def sorted_definitions(defs):
    # Note: `or ''` below is required because `module_path` could be
    return sorted(defs, key=lambda x: (x.module_path or '', x.line or 0, x.column or 0))


def get_on_import_stmt(evaluator, user_context, user_stmt, is_like_search=False):
    """
    Resolve the user statement, if it is an import. Only resolve the
    parts until the user position.
    """
    import_names = user_stmt.get_all_import_names()
    kill_count = -1
    cur_name_part = None
    for i in import_names:
        if user_stmt.alias == i:
            continue
        for name_part in i.names:
            if name_part.end_pos >= user_context.position:
                if not cur_name_part:
                    cur_name_part = name_part
                kill_count += 1

    context = user_context.get_context()
    just_from = next(context) == 'from'

    i = imports.ImportWrapper(evaluator, user_stmt, is_like_search,
                              kill_count=kill_count, direct_resolve=True,
                              is_just_from=just_from)
    return i, cur_name_part

########NEW FILE########
__FILENAME__ = interpreter
import inspect
import re

from jedi._compatibility import builtins
from jedi import debug
from jedi.common import source_to_unicode
from jedi.cache import underscore_memoization
from jedi.evaluate import compiled
from jedi.evaluate.compiled.fake import get_module
from jedi.parser import representation as pr
from jedi.parser.fast import FastParser
from jedi.evaluate import helpers


class InterpreterNamespace(pr.Module):
    def __init__(self, evaluator, namespace, parser_module):
        self.namespace = namespace
        self.parser_module = parser_module
        self._evaluator = evaluator

    def get_defined_names(self):
        for name in self.parser_module.get_defined_names():
            yield name
        for key, value in self.namespace.items():
            yield LazyName(self._evaluator, key, value)

    def __getattr__(self, name):
        return getattr(self.parser_module, name)


class LazyName(helpers.FakeName):
    def __init__(self, evaluator, name, value):
        super(LazyName, self).__init__(name)
        self._evaluator = evaluator
        self._value = value
        self._name = name

    @property
    @underscore_memoization
    def parent(self):
        parser_path = []
        obj = self._value
        if inspect.ismodule(obj):
            module = obj
        else:
            try:
                o = obj.__objclass__
                parser_path.append(pr.NamePart(obj.__name__, None, (None, None)))
                obj = o
            except AttributeError:
                pass

            try:
                module_name = obj.__module__
                parser_path.insert(0, pr.NamePart(obj.__name__, None, (None, None)))
            except AttributeError:
                # Unfortunately in some cases like `int` there's no __module__
                module = builtins
            else:
                module = __import__(module_name)
        raw_module = get_module(self._value)

        try:
            path = module.__file__
        except AttributeError:
            pass
        else:
            path = re.sub('c$', '', path)
            if path.endswith('.py'):
                # cut the `c` from `.pyc`
                with open(path) as f:
                    source = source_to_unicode(f.read())
                mod = FastParser(source, path[:-1]).module
                if not parser_path:
                    return mod
                found = self._evaluator.eval_call_path(iter(parser_path), mod, None)
                if found:
                    return found[0]
                debug.warning('Interpreter lookup for Python code failed %s',
                              mod)

        module = compiled.CompiledObject(raw_module)
        if raw_module == builtins:
            # The builtins module is special and always cached.
            module = compiled.builtin
        return compiled.create(self._evaluator, self._value, module, module)

    @parent.setter
    def parent(self, value):
        """Needed because of the ``representation.Simple`` super class."""


def create(evaluator, namespace, parser_module):
    ns = InterpreterNamespace(evaluator, namespace, parser_module)
    for attr_name in pr.SCOPE_CONTENTS:
        for something in getattr(parser_module, attr_name):
            something.parent = ns

########NEW FILE########
__FILENAME__ = keywords
import pydoc
import keyword

from jedi._compatibility import is_py3
from jedi import common
from jedi.evaluate import compiled

try:
    from pydoc_data import topics as pydoc_topics
except ImportError:
    # Python 2.6
    import pydoc_topics

if is_py3:
    keys = keyword.kwlist
else:
    keys = keyword.kwlist + ['None', 'False', 'True']


def keywords(string='', pos=(0, 0), all=False):
    if all:
        return set([Keyword(k, pos) for k in keys])
    if string in keys:
        return set([Keyword(string, pos)])
    return set()


def keyword_names(*args, **kwargs):
    kwds = []
    for k in keywords(*args, **kwargs):
        start = k.start_pos
        kwds.append(KeywordName(k, k.name, start))
    return kwds


def get_operator(string, pos):
    return Keyword(string, pos)


class KeywordName(object):
    def __init__(self, parent, name, start_pos):
        self.parent = parent
        self.names = [name]
        self.start_pos = start_pos

    @property
    def end_pos(self):
        return self.start_pos[0], self.start_pos[1] + len(self.name)


class Keyword(object):
    def __init__(self, name, pos):
        self.name = name
        self.start_pos = pos
        self.parent = compiled.builtin

    def get_parent_until(self):
        return self.parent

    @property
    def names(self):
        """ For a `parsing.Name` like comparision """
        return [self.name]

    @property
    def docstr(self):
        return imitate_pydoc(self.name)

    def __repr__(self):
        return '<%s: %s>' % (type(self).__name__, self.name)


def imitate_pydoc(string):
    """
    It's not possible to get the pydoc's without starting the annoying pager
    stuff.
    """
    # str needed because of possible unicode stuff in py2k (pydoc doesn't work
    # with unicode strings)
    string = str(string)
    h = pydoc.help
    with common.ignored(KeyError):
        # try to access symbols
        string = h.symbols[string]
        string, _, related = string.partition(' ')

    get_target = lambda s: h.topics.get(s, h.keywords.get(s))
    while isinstance(string, str):
        string = get_target(string)

    try:
        # is a tuple now
        label, related = string
    except TypeError:
        return ''

    try:
        return pydoc_topics.topics[label] if pydoc_topics else ''
    except KeyError:
        return ''

########NEW FILE########
__FILENAME__ = replstartup
"""
To use Jedi completion in Python interpreter, add the following in your shell
setup (e.g., ``.bashrc``)::

    export PYTHONSTARTUP="$(python -m jedi repl)"

Then you will be able to use Jedi completer in your Python interpreter::

    $ python
    Python 2.7.2+ (default, Jul 20 2012, 22:15:08)
    [GCC 4.6.1] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> import os
    >>> os.path.join().split().in<TAB>                     # doctest: +SKIP
    os.path.join().split().index   os.path.join().split().insert

"""

import jedi.utils
jedi.utils.setup_readline()
del jedi
# Note: try not to do many things here, as it will contaminate global
# namespace of the interpreter.

########NEW FILE########
__FILENAME__ = usages
from jedi._compatibility import u, unicode
from jedi import common
from jedi.api import classes
from jedi.parser import representation as pr
from jedi.evaluate import imports
from jedi.evaluate import helpers


def usages(evaluator, definitions, search_name, mods):
    def compare_array(definitions):
        """ `definitions` are being compared by module/start_pos, because
        sometimes the id's of the objects change (e.g. executions).
        """
        result = []
        for d in definitions:
            module = d.get_parent_until()
            result.append((module, d.start_pos))
        return result

    def check_call_for_usage(call):
        stmt = call.parent
        while not isinstance(stmt.parent, pr.IsScope):
            stmt = stmt.parent
        # New definition, call cannot be a part of stmt
        if len(call.name) == 1 and call.execution is None \
                and call.name in stmt.get_defined_names():
            # Class params are not definitions (like function params). They
            # are super classes, that need to be resolved.
            if not (isinstance(stmt, pr.Param) and isinstance(stmt.parent, pr.Class)):
                return

        follow = []  # There might be multiple search_name's in one call_path
        call_path = list(call.generate_call_path())
        for i, name in enumerate(call_path):
            # name is `pr.NamePart`.
            if u(name) == search_name:
                follow.append(call_path[:i + 1])

        for call_path in follow:
            follow_res, search = evaluator.goto(call.parent, call_path)
            # names can change (getattr stuff), therefore filter names that
            # don't match `search`.

            # TODO add something like that in the future - for now usages are
            # completely broken anyway.
            #follow_res = [r for r in follow_res if str(r) == search]
            #print search.start_pos,search_name.start_pos
            #print follow_res, search, search_name, [(r, r.start_pos) for r in follow_res]
            follow_res = usages_add_import_modules(evaluator, follow_res, search)

            compare_follow_res = compare_array(follow_res)
            # compare to see if they match
            if any(r in compare_definitions for r in compare_follow_res):
                yield classes.Definition(evaluator, search)

    if not definitions:
        return set()

    compare_definitions = compare_array(definitions)
    mods |= set([d.get_parent_until() for d in definitions])
    names = []
    for m in imports.get_modules_containing_name(mods, search_name):
        try:
            stmts = m.used_names[search_name]
        except KeyError:
            continue
        for stmt in stmts:
            if isinstance(stmt, pr.Import):
                count = 0
                imps = []
                for i in stmt.get_all_import_names():
                    for name_part in i.names:
                        count += 1
                        if unicode(name_part) == search_name:
                            imps.append((count, name_part))

                for used_count, name_part in imps:
                    i = imports.ImportWrapper(evaluator, stmt, kill_count=count - used_count,
                                              direct_resolve=True)
                    f = i.follow(is_goto=True)
                    if set(f) & set(definitions):
                        names.append(classes.Definition(evaluator, name_part))
            else:
                for call in helpers.scan_statement_for_calls(stmt, search_name, assignment_details=True):
                    names += check_call_for_usage(call)
    return names


def usages_add_import_modules(evaluator, definitions, search_name):
    """ Adds the modules of the imports """
    new = set()
    for d in definitions:
        if isinstance(d.parent, pr.Import):
            s = imports.ImportWrapper(evaluator, d.parent, direct_resolve=True)
            with common.ignored(IndexError):
                new.add(s.follow(is_goto=True)[0])
    return set(definitions) | new

########NEW FILE########
__FILENAME__ = cache
"""
This caching is very important for speed and memory optimizations. There's
nothing really spectacular, just some decorators. The following cache types are
available:

- module caching (`load_parser` and `save_parser`), which uses pickle and is
  really important to assure low load times of modules like ``numpy``.
- ``time_cache`` can be used to cache something for just a limited time span,
  which can be useful if there's user interaction and the user cannot react
  faster than a certain time.

This module is one of the reasons why |jedi| is not thread-safe. As you can see
there are global variables, which are holding the cache information. Some of
these variables are being cleaned after every API usage.
"""
import time
import os
import sys
import json
import hashlib
import gc
import inspect
import shutil
import re
try:
    import cPickle as pickle
except ImportError:
    import pickle

from jedi import settings
from jedi import common
from jedi import debug

_time_caches = []

_star_import_cache = {}

# for fast_parser, should not be deleted
parser_cache = {}


class ParserCacheItem(object):
    def __init__(self, parser, change_time=None):
        self.parser = parser
        if change_time is None:
            change_time = time.time()
        self.change_time = change_time


def clear_caches(delete_all=False):
    """ Jedi caches many things, that should be completed after each completion
    finishes.

    :param delete_all: Deletes also the cache that is normally not deleted,
        like parser cache, which is important for faster parsing.
    """
    global _time_caches

    if delete_all:
        _time_caches = []
        _star_import_cache.clear()
        parser_cache.clear()
    else:
        # normally just kill the expired entries, not all
        for tc in _time_caches:
            # check time_cache for expired entries
            for key, (t, value) in list(tc.items()):
                if t < time.time():
                    # delete expired entries
                    del tc[key]


def time_cache(time_add_setting):
    """ This decorator works as follows: Call it with a setting and after that
    use the function with a callable that returns the key.
    But: This function is only called if the key is not available. After a
    certain amount of time (`time_add_setting`) the cache is invalid.
    """
    def _temp(key_func):
        dct = {}
        _time_caches.append(dct)

        def wrapper(optional_callable, *args, **kwargs):
            key = key_func(*args, **kwargs)
            value = None
            if key in dct:
                expiry, value = dct[key]
                if expiry > time.time():
                    return value
            value = optional_callable()
            time_add = getattr(settings, time_add_setting)
            if key is not None:
                dct[key] = time.time() + time_add, value
            return value
        return wrapper
    return _temp


@time_cache("call_signatures_validity")
def cache_call_signatures(source, user_pos, stmt):
    """This function calculates the cache key."""
    index = user_pos[0] - 1
    lines = source.splitlines() or ['']
    if source and source[-1] == '\n':
        lines.append('')

    before_cursor = lines[index][:user_pos[1]]
    other_lines = lines[stmt.start_pos[0]:index]
    whole = '\n'.join(other_lines + [before_cursor])
    before_bracket = re.match(r'.*\(', whole, re.DOTALL)

    module_path = stmt.get_parent_until().path
    return None if module_path is None else (module_path, before_bracket, stmt.start_pos)


def underscore_memoization(func):
    """
    Decorator for methods::

        class A(object):
            def x(self):
                if self._x:
                    self._x = 10
                return self._x

    Becomes::

        class A(object):
            @underscore_memoization
            def x(self):
                return 10

    A now has an attribute ``_x`` written by this decorator.
    """
    name = '_' + func.__name__

    def wrapper(self):
        try:
            return getattr(self, name)
        except AttributeError:
            result = func(self)
            if inspect.isgenerator(result):
                result = list(result)
            setattr(self, name, result)
            return result

    return wrapper


def memoize(func):
    """A normal memoize function."""
    dct = {}

    def wrapper(*args, **kwargs):
        key = (args, frozenset(kwargs.items()))
        try:
            return dct[key]
        except KeyError:
            result = func(*args, **kwargs)
            dct[key] = result
            return result
    return wrapper


def cache_star_import(func):
    def wrapper(evaluator, scope, *args, **kwargs):
        with common.ignored(KeyError):
            mods = _star_import_cache[scope]
            if mods[0] + settings.star_import_cache_validity > time.time():
                return mods[1]
        # cache is too old and therefore invalid or not available
        _invalidate_star_import_cache_module(scope)
        mods = func(evaluator, scope, *args, **kwargs)
        _star_import_cache[scope] = time.time(), mods

        return mods
    return wrapper


def _invalidate_star_import_cache_module(module, only_main=False):
    """ Important if some new modules are being reparsed """
    with common.ignored(KeyError):
        t, mods = _star_import_cache[module]

        del _star_import_cache[module]

        for m in mods:
            _invalidate_star_import_cache_module(m, only_main=True)

    if not only_main:
        # We need a list here because otherwise the list is being changed
        # during the iteration in py3k: iteritems -> items.
        for key, (t, mods) in list(_star_import_cache.items()):
            if module in mods:
                _invalidate_star_import_cache_module(key)


def invalidate_star_import_cache(path):
    """On success returns True."""
    try:
        parser_cache_item = parser_cache[path]
    except KeyError:
        return False
    else:
        _invalidate_star_import_cache_module(parser_cache_item.parser.module)
        return True


def load_parser(path, name):
    """
    Returns the module or None, if it fails.
    """
    if path is None and name is None:
        return None

    p_time = os.path.getmtime(path) if path else None
    n = name if path is None else path
    try:
        parser_cache_item = parser_cache[n]
        if not path or p_time <= parser_cache_item.change_time:
            return parser_cache_item.parser
        else:
            # In case there is already a module cached and this module
            # has to be reparsed, we also need to invalidate the import
            # caches.
            _invalidate_star_import_cache_module(parser_cache_item.parser.module)
    except KeyError:
        if settings.use_filesystem_cache:
            return ParserPickling.load_parser(n, p_time)


def save_parser(path, name, parser, pickling=True):
    try:
        p_time = None if not path else os.path.getmtime(path)
    except OSError:
        p_time = None
        pickling = False

    n = name if path is None else path
    item = ParserCacheItem(parser, p_time)
    parser_cache[n] = item
    if settings.use_filesystem_cache and pickling:
        ParserPickling.save_parser(n, item)


class ParserPickling(object):

    version = 10
    """
    Version number (integer) for file system cache.

    Increment this number when there are any incompatible changes in
    parser representation classes.  For example, the following changes
    are regarded as incompatible.

    - Class name is changed.
    - Class is moved to another module.
    - Defined slot of the class is changed.
    """

    def __init__(self):
        self.__index = None
        self.py_tag = 'cpython-%s%s' % sys.version_info[:2]
        """
        Short name for distinguish Python implementations and versions.

        It's like `sys.implementation.cache_tag` but for Python < 3.3
        we generate something similar.  See:
        http://docs.python.org/3/library/sys.html#sys.implementation

        .. todo:: Detect interpreter (e.g., PyPy).
        """

    def load_parser(self, path, original_changed_time):
        try:
            pickle_changed_time = self._index[path]
        except KeyError:
            return None
        if original_changed_time is not None \
                and pickle_changed_time < original_changed_time:
            # the pickle file is outdated
            return None

        with open(self._get_hashed_path(path), 'rb') as f:
            try:
                gc.disable()
                parser_cache_item = pickle.load(f)
            finally:
                gc.enable()

        debug.dbg('pickle loaded: %s', path)
        parser_cache[path] = parser_cache_item
        return parser_cache_item.parser

    def save_parser(self, path, parser_cache_item):
        self.__index = None
        try:
            files = self._index
        except KeyError:
            files = {}
            self._index = files

        with open(self._get_hashed_path(path), 'wb') as f:
            pickle.dump(parser_cache_item, f, pickle.HIGHEST_PROTOCOL)
            files[path] = parser_cache_item.change_time

        self._flush_index()

    @property
    def _index(self):
        if self.__index is None:
            try:
                with open(self._get_path('index.json')) as f:
                    data = json.load(f)
            except (IOError, ValueError):
                self.__index = {}
            else:
                # 0 means version is not defined (= always delete cache):
                if data.get('version', 0) != self.version:
                    self.clear_cache()
                    self.__index = {}
                else:
                    self.__index = data['index']
        return self.__index

    def _remove_old_modules(self):
        # TODO use
        change = False
        if change:
            self._flush_index(self)
            self._index  # reload index

    def _flush_index(self):
        data = {'version': self.version, 'index': self._index}
        with open(self._get_path('index.json'), 'w') as f:
            json.dump(data, f)
        self.__index = None

    def clear_cache(self):
        shutil.rmtree(self._cache_directory())

    def _get_hashed_path(self, path):
        return self._get_path('%s.pkl' % hashlib.md5(path.encode("utf-8")).hexdigest())

    def _get_path(self, file):
        dir = self._cache_directory()
        if not os.path.exists(dir):
            os.makedirs(dir)
        return os.path.join(dir, file)

    def _cache_directory(self):
        return os.path.join(settings.cache_directory, self.py_tag)


# is a singleton
ParserPickling = ParserPickling()

########NEW FILE########
__FILENAME__ = common
""" A universal module with functions / classes without dependencies. """
import sys
import contextlib
import functools
import re
from ast import literal_eval

from jedi._compatibility import unicode, next, reraise
from jedi import settings


class MultiLevelStopIteration(Exception):
    """
    StopIteration's get catched pretty easy by for loops, let errors propagate.
    """


class UncaughtAttributeError(Exception):
    """
    Important, because `__getattr__` and `hasattr` catch AttributeErrors
    implicitly. This is really evil (mainly because of `__getattr__`).
    `hasattr` in Python 2 is even more evil, because it catches ALL exceptions.
    Therefore this class originally had to be derived from `BaseException`
    instead of `Exception`.  But because I removed relevant `hasattr` from
    the code base, we can now switch back to `Exception`.

    :param base: return values of sys.exc_info().
    """


def safe_property(func):
    return property(reraise_uncaught(func))


def reraise_uncaught(func):
    """
    Re-throw uncaught `AttributeError`.

    Usage:  Put ``@rethrow_uncaught`` in front of the function
    which does **not** suppose to raise `AttributeError`.

    AttributeError is easily get caught by `hasattr` and another
    ``except AttributeError`` clause.  This becomes problem when you use
    a lot of "dynamic" attributes (e.g., using ``@property``) because you
    can't distinguish if the property does not exist for real or some code
    inside of the "dynamic" attribute through that error.  In a well
    written code, such error should not exist but getting there is very
    difficult.  This decorator is to help us getting there by changing
    `AttributeError` to `UncaughtAttributeError` to avoid unexpected catch.
    This helps us noticing bugs earlier and facilitates debugging.

    .. note:: Treating StopIteration here is easy.
              Add that feature when needed.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwds):
        try:
            return func(*args, **kwds)
        except AttributeError:
            exc_info = sys.exc_info()
            reraise(UncaughtAttributeError(exc_info[1]), exc_info[2])
    return wrapper


class PushBackIterator(object):
    def __init__(self, iterator):
        self.pushes = []
        self.iterator = iterator
        self.current = None

    def push_back(self, value):
        self.pushes.append(value)

    def __iter__(self):
        return self

    def next(self):
        """ Python 2 Compatibility """
        return self.__next__()

    def __next__(self):
        if self.pushes:
            self.current = self.pushes.pop()
        else:
            self.current = next(self.iterator)
        return self.current


@contextlib.contextmanager
def scale_speed_settings(factor):
    a = settings.max_executions
    b = settings.max_until_execution_unique
    settings.max_executions *= factor
    settings.max_until_execution_unique *= factor
    yield
    settings.max_executions = a
    settings.max_until_execution_unique = b


def indent_block(text, indention='    '):
    """This function indents a text block with a default of four spaces."""
    temp = ''
    while text and text[-1] == '\n':
        temp += text[-1]
        text = text[:-1]
    lines = text.split('\n')
    return '\n'.join(map(lambda s: indention + s, lines)) + temp


@contextlib.contextmanager
def ignored(*exceptions):
    """
    Context manager that ignores all of the specified exceptions. This will
    be in the standard library starting with Python 3.4.
    """
    try:
        yield
    except exceptions:
        pass


def source_to_unicode(source, encoding=None):
    def detect_encoding():
        """
        For the implementation of encoding definitions in Python, look at:
        - http://www.python.org/dev/peps/pep-0263/
        - http://docs.python.org/2/reference/lexical_analysis.html#encoding-declarations
        """
        byte_mark = literal_eval(r"b'\xef\xbb\xbf'")
        if source.startswith(byte_mark):
            # UTF-8 byte-order mark
            return 'utf-8'

        first_two_lines = re.match(r'(?:[^\n]*\n){0,2}', str(source)).group(0)
        possible_encoding = re.search(r"coding[=:]\s*([-\w.]+)",
                                      first_two_lines)
        if possible_encoding:
            return possible_encoding.group(1)
        else:
            # the default if nothing else has been set -> PEP 263
            return encoding if encoding is not None else 'iso-8859-1'

    if isinstance(source, unicode):
        # only cast str/bytes
        return source

    # cast to unicode by default
    return unicode(source, detect_encoding(), 'replace')

########NEW FILE########
__FILENAME__ = debug
from jedi._compatibility import encoding, is_py3
import inspect
import os
import time

try:
    if os.name == 'nt':
        # does not work on Windows, as pyreadline and colorama interfere
        raise ImportError
    else:
        # Use colorama for nicer console output.
        from colorama import Fore, init
        from colorama import initialise
        # pytest resets the stream at the end - causes troubles. Since after
        # every output the stream is reset automatically we don't need this.
        initialise.atexit_done = True
        init()
except ImportError:
    class Fore(object):
        RED = ''
        GREEN = ''
        YELLOW = ''
        RESET = ''

NOTICE = object()
WARNING = object()
SPEED = object()

enable_speed = False
enable_warning = False
enable_notice = False

# callback, interface: level, str
debug_function = None
ignored_modules = ['jedi.evaluate.builtin', 'jedi.parser']
_debug_indent = -1
_start_time = time.time()


def reset_time():
    global _start_time, _debug_indent
    _start_time = time.time()
    _debug_indent = -1


def increase_indent(func):
    """Decorator for makin """
    def wrapper(*args, **kwargs):
        global _debug_indent
        _debug_indent += 1
        result = func(*args, **kwargs)
        _debug_indent -= 1
        return result
    return wrapper


def dbg(message, *args):
    """ Looks at the stack, to see if a debug message should be printed. """
    if debug_function and enable_notice:
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        if not (mod.__name__ in ignored_modules):
            i = ' ' * _debug_indent
            debug_function(NOTICE, i + 'dbg: ' + message % args)


def warning(message, *args):
    if debug_function and enable_warning:
        i = ' ' * _debug_indent
        debug_function(WARNING, i + 'warning: ' + message % args)


def speed(name):
    if debug_function and enable_speed:
        now = time.time()
        i = ' ' * _debug_indent
        debug_function(SPEED, i + 'speed: ' + '%s %s' % (name, now - _start_time))


def print_to_stdout(level, str_out):
    """ The default debug function """
    if level == NOTICE:
        col = Fore.GREEN
    elif level == WARNING:
        col = Fore.RED
    else:
        col = Fore.YELLOW
    if not is_py3:
        str_out = str_out.encode(encoding, 'replace')
    print(col + str_out + Fore.RESET)


# debug_function = print_to_stdout

########NEW FILE########
__FILENAME__ = cache
"""
- the popular ``memoize_default`` works like a typical memoize and returns the
  default otherwise.
- ``CachedMetaClass`` uses ``memoize_default`` to do the same with classes.
"""

NO_DEFAULT = object()


def memoize_default(default=None, evaluator_is_first_arg=False, second_arg_is_evaluator=False):
    """ This is a typical memoization decorator, BUT there is one difference:
    To prevent recursion it sets defaults.

    Preventing recursion is in this case the much bigger use than speed. I
    don't think, that there is a big speed difference, but there are many cases
    where recursion could happen (think about a = b; b = a).
    """
    def func(function):
        def wrapper(obj, *args, **kwargs):
            if evaluator_is_first_arg:
                cache = obj.memoize_cache
            elif second_arg_is_evaluator:  # needed for meta classes
                cache = args[0].memoize_cache
            else:
                cache = obj._evaluator.memoize_cache

            try:
                memo = cache[function]
            except KeyError:
                memo = {}
                cache[function] = memo

            key = (obj, args, frozenset(kwargs.items()))
            if key in memo:
                return memo[key]
            else:
                if default is not NO_DEFAULT:
                    memo[key] = default
                rv = function(obj, *args, **kwargs)
                memo[key] = rv
                return rv
        return wrapper
    return func


class CachedMetaClass(type):
    """
    This is basically almost the same than the decorator above, it just caches
    class initializations. I haven't found any other way, so I'm doing it with
    meta classes.
    """
    @memoize_default(None, second_arg_is_evaluator=True)
    def __call__(self, *args, **kwargs):
        return super(CachedMetaClass, self).__call__(*args, **kwargs)

########NEW FILE########
__FILENAME__ = fake
"""
Loads functions that are mixed in to the standard library. E.g. builtins are
written in C (binaries), but my autocompletion only understands Python code. By
mixing in Python code, the autocompletion should work much better for builtins.
"""

import os
import inspect

from jedi._compatibility import is_py3, builtins, unicode
from jedi.parser import Parser
from jedi.parser import tokenize
from jedi.parser.representation import Class
from jedi.evaluate.helpers import FakeName

modules = {}


def _load_faked_module(module):
    module_name = module.__name__
    if module_name == '__builtin__' and not is_py3:
        module_name = 'builtins'

    try:
        return modules[module_name]
    except KeyError:
        path = os.path.dirname(os.path.abspath(__file__))
        try:
            with open(os.path.join(path, 'fake', module_name) + '.pym') as f:
                source = f.read()
        except IOError:
            modules[module_name] = None
            return
        module = Parser(unicode(source), module_name).module
        modules[module_name] = module

        if module_name == 'builtins' and not is_py3:
            # There are two implementations of `open` for either python 2/3.
            # -> Rename the python2 version (`look at fake/builtins.pym`).
            open_func = search_scope(module, 'open')
            open_func.name = FakeName('open_python3')
            open_func = search_scope(module, 'open_python2')
            open_func.name = FakeName('open')
        return module


def search_scope(scope, obj_name):
    for s in scope.subscopes:
        if str(s.name) == obj_name:
            return s


def get_module(obj):
    if inspect.ismodule(obj):
        return obj
    try:
        obj = obj.__objclass__
    except AttributeError:
        pass

    try:
        imp_plz = obj.__module__
    except AttributeError:
        # Unfortunately in some cases like `int` there's no __module__
        return builtins
    else:
        return __import__(imp_plz)


def _faked(module, obj, name):
    # Crazy underscore actions to try to escape all the internal madness.
    if module is None:
        module = get_module(obj)

    faked_mod = _load_faked_module(module)
    if faked_mod is None:
        return

    # Having the module as a `parser.representation.module`, we need to scan
    # for methods.
    if name is None:
        if inspect.isbuiltin(obj):
            return search_scope(faked_mod, obj.__name__)
        elif not inspect.isclass(obj):
            # object is a method or descriptor
            cls = search_scope(faked_mod, obj.__objclass__.__name__)
            if cls is None:
                return
            return search_scope(cls, obj.__name__)
    else:
        if obj == module:
            return search_scope(faked_mod, name)
        else:
            cls = search_scope(faked_mod, obj.__name__)
            if cls is None:
                return
            return search_scope(cls, name)


def get_faked(module, obj, name=None):
    obj = obj.__class__ if is_class_instance(obj) else obj
    result = _faked(module, obj, name)
    if not isinstance(result, Class) and result is not None:
        # Set the docstr which was previously not set (faked modules don't
        # contain it).
        doc = '''"""%s"""''' % obj.__doc__  # TODO need escapes.
        result.add_docstr(tokenize.Token(tokenize.STRING, doc, (0, 0)))
        return result


def is_class_instance(obj):
    """Like inspect.* methods."""
    return not (inspect.isclass(obj) or inspect.ismodule(obj)
                or inspect.isbuiltin(obj) or inspect.ismethod(obj)
                or inspect.ismethoddescriptor(obj) or inspect.iscode(obj)
                or inspect.isgenerator(obj))

########NEW FILE########
__FILENAME__ = docstrings
"""
Docstrings are another source of information for functions and classes.
:mod:`jedi.evaluate.dynamic` tries to find all executions of functions, while
the docstring parsing is much easier. There are two different types of
docstrings that |jedi| understands:

- `Sphinx <http://sphinx-doc.org/markup/desc.html#info-field-lists>`_
- `Epydoc <http://epydoc.sourceforge.net/manual-fields.html>`_

For example, the sphinx annotation ``:type foo: str`` clearly states that the
type of ``foo`` is ``str``.

As an addition to parameter searching, this module also provides return
annotations.
"""

import re
from itertools import chain
from textwrap import dedent

from jedi.evaluate.cache import memoize_default
from jedi.parser import Parser
from jedi.common import indent_block

DOCSTRING_PARAM_PATTERNS = [
    r'\s*:type\s+%s:\s*([^\n]+)',  # Sphinx
    r'\s*@type\s+%s:\s*([^\n]+)',  # Epydoc
]

DOCSTRING_RETURN_PATTERNS = [
    re.compile(r'\s*:rtype:\s*([^\n]+)', re.M),  # Sphinx
    re.compile(r'\s*@rtype:\s*([^\n]+)', re.M),  # Epydoc
]

REST_ROLE_PATTERN = re.compile(r':[^`]+:`([^`]+)`')


@memoize_default(None, evaluator_is_first_arg=True)
def follow_param(evaluator, param):
    func = param.parent_function
    param_str = _search_param_in_docstr(func.raw_doc, str(param.get_name()))
    return _evaluate_for_statement_string(evaluator, param_str, param.get_parent_until())


def _search_param_in_docstr(docstr, param_str):
    """
    Search `docstr` for a type of `param_str`.

    >>> _search_param_in_docstr(':type param: int', 'param')
    'int'
    >>> _search_param_in_docstr('@type param: int', 'param')
    'int'
    >>> _search_param_in_docstr(
    ...   ':type param: :class:`threading.Thread`', 'param')
    'threading.Thread'
    >>> _search_param_in_docstr('no document', 'param') is None
    True

    """
    # look at #40 to see definitions of those params
    patterns = [re.compile(p % re.escape(param_str))
                for p in DOCSTRING_PARAM_PATTERNS]
    for pattern in patterns:
        match = pattern.search(docstr)
        if match:
            return _strip_rst_role(match.group(1))

    return None


def _strip_rst_role(type_str):
    """
    Strip off the part looks like a ReST role in `type_str`.

    >>> _strip_rst_role(':class:`ClassName`')  # strip off :class:
    'ClassName'
    >>> _strip_rst_role(':py:obj:`module.Object`')  # works with domain
    'module.Object'
    >>> _strip_rst_role('ClassName')  # do nothing when not ReST role
    'ClassName'

    See also:
    http://sphinx-doc.org/domains.html#cross-referencing-python-objects

    """
    match = REST_ROLE_PATTERN.match(type_str)
    if match:
        return match.group(1)
    else:
        return type_str


def _evaluate_for_statement_string(evaluator, string, module):
    code = dedent("""
    def pseudo_docstring_stuff():
        '''Create a pseudo function for docstring statements.'''
    %s
    """)
    if string is None:
        return []

    for element in re.findall('((?:\w+\.)*\w+)\.', string):
        # Try to import module part in dotted name.
        # (e.g., 'threading' in 'threading.Thread').
        string = 'import %s\n' % element + string

    p = Parser(code % indent_block(string), no_docstr=True)
    pseudo_cls = p.module.subscopes[0]
    try:
        stmt = pseudo_cls.statements[-1]
    except IndexError:
        return []

    # Use the module of the param.
    # TODO this module is not the module of the param in case of a function
    # call. In that case it's the module of the function call.
    # stuffed with content from a function call.
    pseudo_cls.parent = module
    definitions = evaluator.eval_statement(stmt)
    it = (evaluator.execute(d) for d in definitions)
    # TODO Executing tuples does not make sense, people tend to say
    # `(str, int)` in a type annotation, which means that it returns a tuple
    # with both types.
    # At this point we just return the classes if executing wasn't possible,
    # i.e. is a tuple.
    return list(chain.from_iterable(it)) or definitions


@memoize_default(None, evaluator_is_first_arg=True)
def find_return_types(evaluator, func):
    def search_return_in_docstr(code):
        for p in DOCSTRING_RETURN_PATTERNS:
            match = p.search(code)
            if match:
                return _strip_rst_role(match.group(1))

    type_str = search_return_in_docstr(func.raw_doc)
    return _evaluate_for_statement_string(evaluator, type_str, func.get_parent_until())

########NEW FILE########
__FILENAME__ = dynamic
"""
One of the really important features of |jedi| is to have an option to
understand code like this::

    def foo(bar):
        bar. # completion here
    foo(1)

There's no doubt wheter bar is an ``int`` or not, but if there's also a call
like ``foo('str')``, what would happen? Well, we'll just show both. Because
that's what a human would expect.

It works as follows:

- |Jedi| sees a param
- search for function calls named ``foo``
- execute these calls and check the input. This work with a ``ParamListener``.
"""

from jedi._compatibility import unicode
from jedi.parser import representation as pr
from jedi import settings
from jedi.evaluate import helpers
from jedi.evaluate.cache import memoize_default
from jedi.evaluate import imports

# This is something like the sys.path, but only for searching params. It means
# that this is the order in which Jedi searches params.
search_param_modules = ['.']


class ParamListener(object):
    """
    This listener is used to get the params for a function.
    """
    def __init__(self):
        self.param_possibilities = []

    def execute(self, params):
        self.param_possibilities.append(params)


@memoize_default([], evaluator_is_first_arg=True)
def search_params(evaluator, param):
    """
    This is a dynamic search for params. If you try to complete a type:

    >>> def func(foo):
    ...     foo
    >>> func(1)
    >>> func("")

    It is not known what the type is, because it cannot be guessed with
    recursive madness. Therefore one has to analyse the statements that are
    calling the function, as well as analyzing the incoming params.
    """
    if not settings.dynamic_params:
        return []

    def get_params_for_module(module):
        """
        Returns the values of a param, or an empty array.
        """
        @memoize_default([], evaluator_is_first_arg=True)
        def get_posibilities(evaluator, module, func_name):
            try:
                possible_stmts = module.used_names[func_name]
            except KeyError:
                return []

            for stmt in possible_stmts:
                if isinstance(stmt, pr.Import):
                    continue
                calls = helpers.scan_statement_for_calls(stmt, func_name)
                for c in calls:
                    # no execution means that params cannot be set
                    call_path = list(c.generate_call_path())
                    pos = c.start_pos
                    scope = stmt.parent

                    # this whole stuff is just to not execute certain parts
                    # (speed improvement), basically we could just call
                    # ``eval_call_path`` on the call_path and it would
                    # also work.
                    def listRightIndex(lst, value):
                        return len(lst) - lst[-1::-1].index(value) - 1

                    # Need to take right index, because there could be a
                    # func usage before.
                    call_path_simple = [unicode(d) if isinstance(d, pr.NamePart)
                                        else d for d in call_path]
                    i = listRightIndex(call_path_simple, func_name)
                    first, last = call_path[:i], call_path[i + 1:]
                    if not last and not call_path_simple.index(func_name) != i:
                        continue
                    scopes = [scope]
                    if first:
                        scopes = evaluator.eval_call_path(iter(first), scope, pos)
                        pos = None
                    from jedi.evaluate import representation as er
                    for scope in scopes:
                        s = evaluator.find_types(scope, func_name, position=pos,
                                                 search_global=not first,
                                                 resolve_decorator=False)

                        c = [getattr(escope, 'base_func', None) or escope.base
                             for escope in s
                             if escope.isinstance(er.Function, er.Class)]
                        if compare in c:
                            # only if we have the correct function we execute
                            # it, otherwise just ignore it.
                            evaluator.follow_path(iter(last), s, scope)

            return listener.param_possibilities

        result = []
        for params in get_posibilities(evaluator, module, func_name):
            for p in params:
                if str(p) == param_name:
                    result += evaluator.eval_statement(p.parent)
        return result

    func = param.get_parent_until(pr.Function)
    current_module = param.get_parent_until()
    func_name = unicode(func.name)
    compare = func
    if func_name == '__init__' and isinstance(func.parent, pr.Class):
        func_name = unicode(func.parent.name)
        compare = func.parent

    # get the param name
    if param.assignment_details:
        # first assignment details, others would be a syntax error
        expression_list, op = param.assignment_details[0]
    else:
        expression_list = param.expression_list()
    offset = 1 if expression_list[0] in ['*', '**'] else 0
    param_name = str(expression_list[offset].name)

    # add the listener
    listener = ParamListener()
    func.listeners.add(listener)

    result = []
    # This is like backtracking: Get the first possible result.
    for mod in imports.get_modules_containing_name([current_module], func_name):
        result = get_params_for_module(mod)
        if result:
            break

    # cleanup: remove the listener; important: should not stick.
    func.listeners.remove(listener)

    return result

########NEW FILE########
__FILENAME__ = finder
"""
Searcjing for names with given scope and name. This is very central in Jedi and
Python. The name resolution is quite complicated with descripter,
``__getattribute__``, ``__getattr__``, ``global``, etc.

Flow checks
+++++++++++

Flow checks are not really mature. There's only a check for ``isinstance``.  It
would check whether a flow has the form of ``if isinstance(a, type_or_tuple)``.
Unfortunately every other thing is being ignored (e.g. a == '' would be easy to
check for -> a is a string). There's big potential in these checks.
"""
import sys

from jedi._compatibility import hasattr, unicode, u, reraise
from jedi.parser import representation as pr, tokenize
from jedi import debug
from jedi import common
from jedi import settings
from jedi.evaluate import representation as er
from jedi.evaluate import dynamic
from jedi.evaluate import compiled
from jedi.evaluate import docstrings
from jedi.evaluate import iterable
from jedi.evaluate import imports


class NameFinder(object):
    def __init__(self, evaluator, scope, name_str, position=None):
        self._evaluator = evaluator
        self.scope = scope
        self.name_str = name_str
        self.position = position

    def find(self, scopes, resolve_decorator=True):
        names = self.filter_name(scopes)
        types = self._names_to_types(names, resolve_decorator)
        debug.dbg('finder._names_to_types: %s, old: %s', names, types)
        return self._resolve_descriptors(types)

    def scopes(self, search_global=False):
        if search_global:
            return get_names_of_scope(self._evaluator, self.scope, self.position)
        else:
            if isinstance(self.scope, er.Instance):
                return self.scope.scope_generator()
            else:
                if isinstance(self.scope, er.Class):
                    # classes are only available directly via chaining?
                    # strange stuff...
                    names = self.scope.get_defined_names()
                else:
                    names = _get_defined_names_for_position(self.scope, self.position)
                return iter([(self.scope, names)])

    def filter_name(self, scope_generator):
        """
        Filters all variables of a scope (which are defined in the
        `scope_generator`), until the name fits.
        """
        result = []
        for nscope, name_list in scope_generator:
            break_scopes = []
            if not isinstance(nscope, compiled.CompiledObject):
                # Here is the position stuff happening (sorting of variables).
                # Compiled objects don't need that, because there's only one
                # reference.
                name_list = sorted(name_list, key=lambda n: n.start_pos, reverse=True)
            for name in name_list:
                if unicode(self.name_str) != name.get_code():
                    continue

                parpar = name.parent.parent
                if name.parent.parent in break_scopes:
                    continue

                if not self._name_is_array_assignment(name):
                    result.append(name)  # `arr[1] =` is not the definition
                # for comparison we need the raw class
                # this means that a definition was found and is not e.g.
                # in if/else.
                if result and self._name_is_break_scope(name):
                    #print result, name.parent, parpar, s
                    if isinstance(parpar, pr.Flow) \
                            or isinstance(parpar, pr.KeywordStatement) \
                            and parpar.name == 'global':
                        s = nscope.base if isinstance(nscope, er.Class) else nscope
                        if parpar == s:
                            break
                    else:
                        break
                    break_scopes.append(parpar)
            if result:
                break

        debug.dbg('finder.filter_name "%s" in (%s-%s): %s@%s', self.name_str,
                  self.scope, nscope, u(result), self.position)
        return result

    def _check_getattr(self, inst):
        """Checks for both __getattr__ and __getattribute__ methods"""
        result = []
        # str is important to lose the NamePart!
        name = compiled.create(self._evaluator, str(self.name_str))
        with common.ignored(KeyError):
            result = inst.execute_subscope_by_name('__getattr__', [name])
        if not result:
            # this is a little bit special. `__getattribute__` is executed
            # before anything else. But: I know no use case, where this
            # could be practical and the jedi would return wrong types. If
            # you ever have something, let me know!
            with common.ignored(KeyError):
                result = inst.execute_subscope_by_name('__getattribute__', [name])
        return result

    def _name_is_break_scope(self, name):
        """
        Returns the parent of a name, which means the element which stands
        behind a name.
        """
        par = name.parent
        if par.isinstance(pr.Statement):
            if isinstance(name, er.InstanceElement) and not name.is_class_var:
                return False
        elif isinstance(par, pr.Import) and len(par.namespace) > 1:
            # TODO multi-level import non-breakable
            return False
        return True

    def _name_is_array_assignment(self, name):
        if name.parent.isinstance(pr.Statement):
            def is_execution(calls):
                for c in calls:
                    if isinstance(c, (unicode, str, tokenize.Token)):
                        continue
                    if c.isinstance(pr.Array):
                        if is_execution(c):
                            return True
                    elif c.isinstance(pr.Call):
                        # Compare start_pos, because names may be different
                        # because of executions.
                        if c.name.start_pos == name.start_pos \
                                and c.execution:
                            return True
                return False

            is_exe = False
            for assignee, op in name.parent.assignment_details:
                is_exe |= is_execution(assignee)

            if is_exe:
                # filter array[3] = ...
                # TODO check executions for dict contents
                return True
        return False

    def _names_to_types(self, names, resolve_decorator):
        types = []
        # Add isinstance and other if/assert knowledge.
        flow_scope = self.scope
        evaluator = self._evaluator
        while flow_scope:
            # TODO check if result is in scope -> no evaluation necessary
            n = check_flow_information(evaluator, flow_scope,
                                       self.name_str, self.position)
            if n:
                return n
            flow_scope = flow_scope.parent

        for name in names:
            typ = name.parent
            if typ.isinstance(pr.ForFlow):
                types += self._handle_for_loops(typ)
            elif isinstance(typ, pr.Param):
                types += self._eval_param(typ)
            elif typ.isinstance(pr.Statement):
                if typ.is_global():
                    # global keyword handling.
                    types += evaluator.find_types(typ.parent.parent, str(name))
                else:
                    types += self._remove_statements(typ)
            else:
                if isinstance(typ, pr.Class):
                    typ = er.Class(evaluator, typ)
                elif isinstance(typ, pr.Function):
                    typ = er.Function(evaluator, typ)
                if typ.isinstance(er.Function) and resolve_decorator:
                    typ = typ.get_decorated_func()
                types.append(typ)

        if not names and isinstance(self.scope, er.Instance):
            # handling __getattr__ / __getattribute__
            types = self._check_getattr(self.scope)

        return types

    def _remove_statements(self, stmt):
        """
        This is the part where statements are being stripped.

        Due to lazy evaluation, statements like a = func; b = a; b() have to be
        evaluated.
        """
        evaluator = self._evaluator
        types = []
        # Remove the statement docstr stuff for now, that has to be
        # implemented with the evaluator class.
        #if stmt.docstr:
            #res_new.append(stmt)

        check_instance = None
        if isinstance(stmt, er.InstanceElement) and stmt.is_class_var:
            check_instance = stmt.instance
            stmt = stmt.var

        types += evaluator.eval_statement(stmt, seek_name=unicode(self.name_str))

        if check_instance is not None:
            # class renames
            types = [er.InstanceElement(evaluator, check_instance, a, True)
                     if isinstance(a, (er.Function, pr.Function))
                     else a for a in types]
        return types

    def _eval_param(self, param):
        evaluator = self._evaluator
        res_new = []
        func = param.parent

        cls = func.parent.get_parent_until((pr.Class, pr.Function))

        if isinstance(cls, pr.Class) and param.position_nr == 0:
            # This is where we add self - if it has never been
            # instantiated.
            if isinstance(self.scope, er.InstanceElement):
                res_new.append(self.scope.instance)
            else:
                for inst in evaluator.execute(er.Class(evaluator, cls)):
                    inst.is_generated = True
                    res_new.append(inst)
            return res_new

        # Instances are typically faked, if the instance is not called from
        # outside. Here we check it for __init__ functions and return.
        if isinstance(func, er.InstanceElement) \
                and func.instance.is_generated and str(func.name) == '__init__':
            param = func.var.params[param.position_nr]

        # Add docstring knowledge.
        doc_params = docstrings.follow_param(evaluator, param)
        if doc_params:
            return doc_params

        if not param.is_generated:
            # Param owns no information itself.
            res_new += dynamic.search_params(evaluator, param)
            if not res_new:
                if param.stars:
                    t = 'tuple' if param.stars == 1 else 'dict'
                    typ = evaluator.find_types(compiled.builtin, t)[0]
                    res_new = evaluator.execute(typ)
            if not param.assignment_details:
                # this means that there are no default params,
                # so just ignore it.
                return res_new
        return res_new + evaluator.eval_statement(param, seek_name=unicode(self.name_str))

    def _handle_for_loops(self, loop):
        # Take the first statement (for has always only
        # one, remember `in`). And follow it.
        if not loop.inputs:
            return []
        result = iterable.get_iterator_types(self._evaluator.eval_statement(loop.inputs[0]))
        if len(loop.set_vars) > 1:
            expression_list = loop.set_stmt.expression_list()
            # loops with loop.set_vars > 0 only have one command
            result = _assign_tuples(expression_list[0], result, unicode(self.name_str))
        return result

    def _resolve_descriptors(self, types):
        """Processes descriptors"""
        result = []
        for r in types:
            if isinstance(self.scope, (er.Instance, er.Class)) \
                    and hasattr(r, 'get_descriptor_return'):
                # handle descriptors
                with common.ignored(KeyError):
                    result += r.get_descriptor_return(self.scope)
                    continue
            result.append(r)
        return result


def check_flow_information(evaluator, flow, search_name_part, pos):
    """ Try to find out the type of a variable just with the information that
    is given by the flows: e.g. It is also responsible for assert checks.::

        if isinstance(k, str):
            k.  # <- completion here

    ensures that `k` is a string.
    """
    if not settings.dynamic_flow_information:
        return None

    result = []
    if isinstance(flow, pr.IsScope) and not result:
        for ass in reversed(flow.asserts):
            if pos is None or ass.start_pos > pos:
                continue
            result = _check_isinstance_type(evaluator, ass, search_name_part)
            if result:
                break

    if isinstance(flow, pr.Flow) and not result:
        if flow.command in ['if', 'while'] and len(flow.inputs) == 1:
            result = _check_isinstance_type(evaluator, flow.inputs[0], search_name_part)
    return result


def _check_isinstance_type(evaluator, stmt, search_name_part):
    try:
        expression_list = stmt.expression_list()
        # this might be removed if we analyze and, etc
        assert len(expression_list) == 1
        call = expression_list[0]
        assert isinstance(call, pr.Call) and str(call.name) == 'isinstance'
        assert bool(call.execution)

        # isinstance check
        isinst = call.execution.values
        assert len(isinst) == 2  # has two params
        obj, classes = [statement.expression_list() for statement in isinst]
        assert len(obj) == 1
        assert len(classes) == 1
        assert isinstance(obj[0], pr.Call)

        # names fit?
        assert unicode(obj[0].name) == unicode(search_name_part)
        assert isinstance(classes[0], pr.StatementElement)  # can be type or tuple
    except AssertionError:
        return []

    result = []
    for c in evaluator.eval_call(classes[0]):
        for typ in (c.get_index_types() if isinstance(c, iterable.Array) else [c]):
            result += evaluator.execute(typ)
    return result


def _get_defined_names_for_position(scope, position=None, start_scope=None):
    """
    Return filtered version of ``scope.get_defined_names()``.

    This function basically does what :meth:`scope.get_defined_names
    <parsing_representation.Scope.get_defined_names>` does.

    - If `position` is given, delete all names defined after `position`.
    - For special objects like instances, `position` is ignored and all
      names are returned.

    :type     scope: :class:`parsing_representation.IsScope`
    :param    scope: Scope in which names are searched.
    :param position: The position as a line/column tuple, default is infinity.
    """
    names = scope.get_defined_names()
    # Instances have special rules, always return all the possible completions,
    # because class variables are always valid and the `self.` variables, too.
    if not position or isinstance(scope, (iterable.Array, er.Instance, compiled.CompiledObject)) \
            or start_scope != scope \
            and isinstance(start_scope, (pr.Function, er.FunctionExecution)):
        return names
    names_new = []
    for n in names:
        if n.start_pos[0] is not None and n.start_pos < position:
            names_new.append(n)
    return names_new


def get_names_of_scope(evaluator, scope, position=None, star_search=True, include_builtin=True):
    """
    Get all completions (names) possible for the current scope. The star search
    option is only here to provide an optimization. Otherwise the whole thing
    would probably start a little recursive madness.

    This function is used to include names from outer scopes. For example, when
    the current scope is function:

    >>> from jedi._compatibility import u
    >>> from jedi.parser import Parser
    >>> parser = Parser(u('''
    ... x = ['a', 'b', 'c']
    ... def func():
    ...     y = None
    ... '''))
    >>> scope = parser.module.subscopes[0]
    >>> scope
    <Function: func@3-5>

    `get_names_of_scope` is a generator.  First it yields names from most inner
    scope.

    >>> from jedi.evaluate import Evaluator
    >>> pairs = list(get_names_of_scope(Evaluator(), scope))
    >>> pairs[0]
    (<Function: func@3-5>, [<Name: y@4,4>])

    Then it yield the names from one level outer scope. For this example, this
    is the most outer scope.

    >>> pairs[1]
    (<SubModule: None@1-5>, [<Name: x@2,0>, <Name: func@3,4>])

    Finally, it yields names from builtin, if `include_builtin` is
    true (default).

    >>> pairs[2]                                        #doctest: +ELLIPSIS
    (<Builtin: ...builtin...>, [<CompiledName: ...>, ...])

    :rtype: [(pr.Scope, [pr.Name])]
    :return: Return an generator that yields a pair of scope and names.
    """
    in_func_scope = scope
    non_flow = scope.get_parent_until(pr.Flow, reverse=True)
    while scope:
        if isinstance(scope, pr.SubModule) and scope.parent:
            # we don't want submodules to report if we have modules.
            scope = scope.parent
            continue
        # `pr.Class` is used, because the parent is never `Class`.
        # Ignore the Flows, because the classes and functions care for that.
        # InstanceElement of Class is ignored, if it is not the start scope.
        if not (scope != non_flow and scope.isinstance(pr.Class)
                or scope.isinstance(pr.Flow)
                or scope.isinstance(er.Instance)
                and non_flow.isinstance(er.Function)
                or isinstance(scope, compiled.CompiledObject)
                and scope.type() == 'class' and in_func_scope != scope):
            try:
                if isinstance(scope, er.Instance):
                    for g in scope.scope_generator():
                        yield g
                else:
                    yield scope, _get_defined_names_for_position(scope, position, in_func_scope)
            except StopIteration:
                reraise(common.MultiLevelStopIteration, sys.exc_info()[2])
        if scope.isinstance(pr.ForFlow) and scope.is_list_comp:
            # is a list comprehension
            yield scope, scope.get_defined_names(is_internal_call=True)

        scope = scope.parent
        # This is used, because subscopes (Flow scopes) would distort the
        # results.
        if scope and scope.isinstance(er.Function, pr.Function, er.FunctionExecution):
            in_func_scope = scope

    # Add star imports.
    if star_search:
        for s in imports.remove_star_imports(evaluator, non_flow.get_parent_until()):
            for g in get_names_of_scope(evaluator, s, star_search=False):
                yield g

        # Add builtins to the global scope.
        if include_builtin:
            yield compiled.builtin, compiled.builtin.get_defined_names()


def _assign_tuples(tup, results, seek_name):
    """
    This is a normal assignment checker. In python functions and other things
    can return tuples:
    >>> a, b = 1, ""
    >>> a, (b, c) = 1, ("", 1.0)

    Here, if `seek_name` is "a", the number type will be returned.
    The first part (before `=`) is the param tuples, the second one result.

    :type tup: pr.Array
    """
    def eval_results(index):
        types = []
        for r in results:
            try:
                func = r.get_exact_index_types
            except AttributeError:
                debug.warning("invalid tuple lookup %s of result %s in %s",
                              tup, results, seek_name)
            else:
                with common.ignored(IndexError):
                    types += func(index)
        return types

    result = []
    for i, stmt in enumerate(tup):
        # Used in assignments. There is just one call and no other things,
        # therefore we can just assume, that the first part is important.
        command = stmt.expression_list()[0]

        if tup.type == pr.Array.NOARRAY:

                # unnessecary braces -> just remove.
            r = results
        else:
            r = eval_results(i)

        # LHS of tuples can be nested, so resolve it recursively
        result += find_assignments(command, r, seek_name)
    return result


def find_assignments(lhs, results, seek_name):
    """
    Check if `seek_name` is in the left hand side `lhs` of assignment.

    `lhs` can simply be a variable (`pr.Call`) or a tuple/list (`pr.Array`)
    representing the following cases::

        a = 1        # lhs is pr.Call
        (a, b) = 2   # lhs is pr.Array

    :type lhs: pr.Call
    :type results: list
    :type seek_name: str
    """
    if isinstance(lhs, pr.Array):
        return _assign_tuples(lhs, results, seek_name)
    elif unicode(lhs.name.names[-1]) == seek_name:
        return results
    else:
        return []

########NEW FILE########
__FILENAME__ = helpers
import copy

from jedi import common
from jedi.parser import representation as pr
from jedi import debug


def fast_parent_copy(obj):
    """
    Much, much faster than copy.deepcopy, but just for certain elements.
    """
    new_elements = {}

    def recursion(obj):
        if isinstance(obj, pr.Statement):
            # Need to set _set_vars, otherwise the cache is not working
            # correctly, don't know why.
            obj.get_defined_names()

        new_obj = copy.copy(obj)
        new_elements[obj] = new_obj

        try:
            items = list(new_obj.__dict__.items())
        except AttributeError:
            # __dict__ not available, because of __slots__
            items = []

        before = ()
        for cls in new_obj.__class__.__mro__:
            with common.ignored(AttributeError):
                if before == cls.__slots__:
                    continue
                before = cls.__slots__
                items += [(n, getattr(new_obj, n)) for n in before]

        for key, value in items:
            # replace parent (first try _parent and then parent)
            if key in ['parent', '_parent'] and value is not None:
                if key == 'parent' and '_parent' in items:
                    # parent can be a property
                    continue
                with common.ignored(KeyError):
                    setattr(new_obj, key, new_elements[value])
            elif key in ['parent_function', 'use_as_parent', '_sub_module']:
                continue
            elif isinstance(value, list):
                setattr(new_obj, key, list_rec(value))
            elif isinstance(value, pr.Simple):
                setattr(new_obj, key, recursion(value))
        return new_obj

    def list_rec(list_obj):
        copied_list = list_obj[:]   # lists, tuples, strings, unicode
        for i, el in enumerate(copied_list):
            if isinstance(el, pr.Simple):
                copied_list[i] = recursion(el)
            elif isinstance(el, list):
                copied_list[i] = list_rec(el)
        return copied_list
    return recursion(obj)


def call_signature_array_for_pos(stmt, pos):
    """
    Searches for the array and position of a tuple.
    """
    def search_array(arr, pos):
        accepted_types = pr.Array.TUPLE, pr.Array.NOARRAY
        if arr.type == 'dict':
            for stmt in arr.values + arr.keys:
                new_arr, index = call_signature_array_for_pos(stmt, pos)
                if new_arr is not None:
                    return new_arr, index
        else:
            for i, stmt in enumerate(arr):
                new_arr, index = call_signature_array_for_pos(stmt, pos)
                if new_arr is not None:
                    return new_arr, index

                if arr.start_pos < pos <= stmt.end_pos:
                    if arr.type in accepted_types and isinstance(arr.parent, pr.Call):
                        return arr, i
        if len(arr) == 0 and arr.start_pos < pos < arr.end_pos:
            if arr.type in accepted_types and isinstance(arr.parent, pr.Call):
                return arr, 0
        return None, 0

    def search_call(call, pos):
        arr, index = None, 0
        if call.next is not None:
            if isinstance(call.next, pr.Array):
                arr, index = search_array(call.next, pos)
            else:
                arr, index = search_call(call.next, pos)
        if not arr and call.execution is not None:
            arr, index = search_array(call.execution, pos)
        return arr, index

    if stmt.start_pos >= pos >= stmt.end_pos:
        return None, 0

    for command in stmt.expression_list():
        arr = None
        if isinstance(command, pr.Array):
            arr, index = search_array(command, pos)
        elif isinstance(command, pr.StatementElement):
            arr, index = search_call(command, pos)
        if arr is not None:
            return arr, index
    return None, 0


def search_call_signatures(user_stmt, position):
    """
    Returns the function Call that matches the position before.
    """
    debug.speed('func_call start')
    call, index = None, 0
    if user_stmt is not None and isinstance(user_stmt, pr.Statement):
        # some parts will of the statement will be removed
        user_stmt = fast_parent_copy(user_stmt)
        arr, index = call_signature_array_for_pos(user_stmt, position)
        if arr is not None:
            call = arr.parent

    debug.speed('func_call parsed')
    return call, index


def scan_statement_for_calls(stmt, search_name, assignment_details=False):
    """ Returns the function Calls that match search_name in an Array. """
    def scan_array(arr, search_name):
        result = []
        if arr.type == pr.Array.DICT:
            for key_stmt, value_stmt in arr.items():
                result += scan_statement_for_calls(key_stmt, search_name)
                result += scan_statement_for_calls(value_stmt, search_name)
        else:
            for stmt in arr:
                result += scan_statement_for_calls(stmt, search_name)
        return result

    check = list(stmt.expression_list())
    if assignment_details:
        for expression_list, op in stmt.assignment_details:
            check += expression_list

    result = []
    for c in check:
        if isinstance(c, pr.Array):
            result += scan_array(c, search_name)
        elif isinstance(c, pr.Call):
            s_new = c
            while s_new is not None:
                n = s_new.name
                if isinstance(n, pr.Name) \
                        and search_name in [str(x) for x in n.names]:
                    result.append(c)

                if s_new.execution is not None:
                    result += scan_array(s_new.execution, search_name)
                s_new = s_new.next

    return result


class FakeSubModule():
    line_offset = 0


class FakeArray(pr.Array):
    def __init__(self, values, parent, arr_type=pr.Array.LIST):
        p = (0, 0)
        super(FakeArray, self).__init__(FakeSubModule, p, arr_type, parent)
        self.values = values


class FakeStatement(pr.Statement):
    def __init__(self, expression_list, start_pos=(0, 0)):
        p = start_pos
        super(FakeStatement, self).__init__(FakeSubModule, expression_list, p, p)
        self.set_expression_list(expression_list)


class FakeName(pr.Name):
    def __init__(self, name, parent=None):
        p = 0, 0
        super(FakeName, self).__init__(FakeSubModule, [(name, p)], p, p, parent)

########NEW FILE########
__FILENAME__ = imports
"""
:mod:`jedi.evaluate.imports` is here to resolve import statements and return
the modules/classes/functions/whatever, which they stand for. However there's
not any actual importing done. This module is about finding modules in the
filesystem. This can be quite tricky sometimes, because Python imports are not
always that simple.

This module uses imp for python up to 3.2 and importlib for python 3.3 on; the
correct implementation is delegated to _compatibility.

This module also supports import autocompletion, which means to complete
statements like ``from datetim`` (curser at the end would return ``datetime``).
"""
import os
import pkgutil
import sys
from itertools import chain

from jedi._compatibility import find_module, unicode
from jedi import common
from jedi import debug
from jedi import cache
from jedi.parser import fast
from jedi.parser import representation as pr
from jedi.evaluate import sys_path
from jedi.evaluate import helpers
from jedi import settings
from jedi.common import source_to_unicode
from jedi.evaluate import compiled
from jedi.evaluate.cache import memoize_default, NO_DEFAULT


class ModuleNotFound(Exception):
    pass


class ImportWrapper(pr.Base):
    """
    An ImportWrapper is the path of a `pr.Import` object.
    """
    class GlobalNamespace(object):
        def __init__(self):
            self.line_offset = 0

    GlobalNamespace = GlobalNamespace()

    def __init__(self, evaluator, import_stmt, is_like_search=False, kill_count=0,
                 direct_resolve=False, is_just_from=False):
        self._evaluator = evaluator
        self.import_stmt = import_stmt
        self.is_like_search = is_like_search
        self.direct_resolve = direct_resolve
        self.is_just_from = is_just_from

        self.is_partial_import = bool(max(0, kill_count))

        # rest is import_path resolution
        import_path = []
        if import_stmt.from_ns:
            import_path += import_stmt.from_ns.names
        if import_stmt.namespace:
            if self._is_nested_import() and not direct_resolve:
                import_path.append(import_stmt.namespace.names[0])
            else:
                import_path += import_stmt.namespace.names
        import_path = [str(name_part) for name_part in import_path]

        for i in range(kill_count + int(is_like_search)):
            if import_path:
                import_path.pop()

        module = import_stmt.get_parent_until()
        self._importer = get_importer(self._evaluator, tuple(import_path), module,
                                      import_stmt.relative_count)

    def __repr__(self):
        return '<%s: %s>' % (type(self).__name__, self.import_stmt)

    @property
    def import_path(self):
        return self._importer.import_path

    def get_defined_names(self, on_import_stmt=False):
        names = []
        for scope in self.follow():
            if scope is ImportWrapper.GlobalNamespace:
                if not self._is_relative_import():
                    names += self._get_module_names()

                if self._importer.file_path is not None:
                    path = os.path.abspath(self._importer.file_path)
                    for i in range(self.import_stmt.relative_count - 1):
                        path = os.path.dirname(path)
                    names += self._get_module_names([path])

                    if self._is_relative_import():
                        rel_path = self._importer.get_relative_path() + '/__init__.py'
                        if os.path.exists(rel_path):
                            m = load_module(rel_path)
                            names += m.get_defined_names()
            else:
                if on_import_stmt and isinstance(scope, pr.Module) \
                        and scope.path.endswith('__init__.py'):
                    pkg_path = os.path.dirname(scope.path)
                    paths = self._importer.namespace_packages(pkg_path, self.import_path)
                    names += self._get_module_names([pkg_path] + paths)
                if self.is_just_from:
                    # In the case of an import like `from x.` we don't need to
                    # add all the variables.
                    if ('os',) == self.import_path and not self._is_relative_import():
                        # os.path is a hardcoded exception, because it's a
                        # ``sys.modules`` modification.
                        names.append(self._generate_name('path'))
                    continue
                from jedi.evaluate import finder
                for s, scope_names in finder.get_names_of_scope(self._evaluator,
                                                                scope, include_builtin=False):
                    for n in scope_names:
                        if self.import_stmt.from_ns is None \
                                or self.is_partial_import:
                                # from_ns must be defined to access module
                                # values plus a partial import means that there
                                # is something after the import, which
                                # automatically implies that there must not be
                                # any non-module scope.
                                continue
                        names.append(n)
        return names

    def _generate_name(self, name):
        return helpers.FakeName(name, parent=self.import_stmt)

    def _get_module_names(self, search_path=None):
        """
        Get the names of all modules in the search_path. This means file names
        and not names defined in the files.
        """

        names = []
        # add builtin module names
        if search_path is None:
            names += [self._generate_name(name) for name in sys.builtin_module_names]

        if search_path is None:
            search_path = self._importer.sys_path_with_modifications()
        for module_loader, name, is_pkg in pkgutil.iter_modules(search_path):
            names.append(self._generate_name(name))
        return names

    def _is_nested_import(self):
        """
        This checks for the special case of nested imports, without aliases and
        from statement::

            import foo.bar
        """
        return not self.import_stmt.alias and not self.import_stmt.from_ns \
            and len(self.import_stmt.namespace.names) > 1 \
            and not self.direct_resolve

    def _get_nested_import(self, parent):
        """
        See documentation of `self._is_nested_import`.
        Generates an Import statement, that can be used to fake nested imports.
        """
        i = self.import_stmt
        # This is not an existing Import statement. Therefore, set position to
        # 0 (0 is not a valid line number).
        zero = (0, 0)
        names = [(unicode(name_part), name_part.start_pos)
                 for name_part in i.namespace.names[1:]]
        n = pr.Name(i._sub_module, names, zero, zero, self.import_stmt)
        new = pr.Import(i._sub_module, zero, zero, n)
        new.parent = parent
        debug.dbg('Generated a nested import: %s', new)
        return new

    def _is_relative_import(self):
        return bool(self.import_stmt.relative_count)

    def follow(self, is_goto=False):
        if self._evaluator.recursion_detector.push_stmt(self.import_stmt):
            # check recursion
            return []

        if self.import_path:
            try:
                scope, rest = self._importer.follow_file_system()
            except ModuleNotFound:
                debug.warning('Module not found: %s', self.import_stmt)
                return []

            scopes = [scope]
            scopes += remove_star_imports(self._evaluator, scope)

            # follow the rest of the import (not FS -> classes, functions)
            if len(rest) > 1 or rest and self.is_like_search:
                scopes = []
                if ('os', 'path') == self.import_path[:2] \
                        and not self._is_relative_import():
                    # This is a huge exception, we follow a nested import
                    # ``os.path``, because it's a very important one in Python
                    # that is being achieved by messing with ``sys.modules`` in
                    # ``os``.
                    scopes = self._evaluator.follow_path(iter(rest), [scope], scope)
            elif rest:
                if is_goto:
                    scopes = list(chain.from_iterable(
                        self._evaluator.find_types(s, rest[0], is_goto=True)
                        for s in scopes))
                else:
                    scopes = list(chain.from_iterable(
                        self._evaluator.follow_path(iter(rest), [s], s)
                        for s in scopes))

            if self._is_nested_import():
                scopes.append(self._get_nested_import(scope))
        else:
            scopes = [ImportWrapper.GlobalNamespace]
        debug.dbg('after import: %s', scopes)
        self._evaluator.recursion_detector.pop_stmt()
        return scopes


def get_importer(evaluator, import_path, module, level=0):
    """
    Checks the evaluator caches first, which resembles the ``sys.modules``
    cache and speeds up libraries like ``numpy``.
    """
    if level != 0:
        # Only absolute imports should be cached. Otherwise we have a mess.
        # TODO Maybe calculate the absolute import and save it here?
        return _Importer(evaluator, import_path, module, level)
    try:
        return evaluator.import_cache[import_path]
    except KeyError:
        importer = _Importer(evaluator, import_path, module, level)
        evaluator.import_cache[import_path] = importer
        return importer


class _Importer(object):
    def __init__(self, evaluator, import_path, module, level=0):
        """
        An implementation similar to ``__import__``. Use `follow_file_system`
        to actually follow the imports.

        *level* specifies whether to use absolute or relative imports. 0 (the
        default) means only perform absolute imports. Positive values for level
        indicate the number of parent directories to search relative to the
        directory of the module calling ``__import__()`` (see PEP 328 for the
        details).

        :param import_path: List of namespaces (strings).
        """
        debug.speed('import %s' % (import_path,))
        self._evaluator = evaluator
        self.import_path = import_path
        self.level = level
        self.module = module
        path = module.path
        # TODO abspath
        self.file_path = os.path.dirname(path) if path is not None else None

    def get_relative_path(self):
        path = self.file_path
        for i in range(self.level - 1):
            path = os.path.dirname(path)
        return path

    @memoize_default()
    def sys_path_with_modifications(self):
        # If you edit e.g. gunicorn, there will be imports like this:
        # `from gunicorn import something`. But gunicorn is not in the
        # sys.path. Therefore look if gunicorn is a parent directory, #56.
        in_path = []
        if self.import_path:
            parts = self.file_path.split(os.path.sep)
            for i, p in enumerate(parts):
                if p == self.import_path[0]:
                    new = os.path.sep.join(parts[:i])
                    in_path.append(new)

        return in_path + sys_path.sys_path_with_modifications(self.module)

    def follow(self, evaluator):
        scope, rest = self.follow_file_system()
        if rest:
            # follow the rest of the import (not FS -> classes, functions)
            return evaluator.follow_path(iter(rest), [scope], scope)
        return [scope]

    @memoize_default(NO_DEFAULT)
    def follow_file_system(self):
        if self.file_path:
            sys_path_mod = list(self.sys_path_with_modifications())
            if not self.module.has_explicit_absolute_import:
                # If the module explicitly asks for absolute imports,
                # there's probably a bogus local one.
                sys_path_mod.insert(0, self.file_path)

            # First the sys path is searched normally and if that doesn't
            # succeed, try to search the parent directories, because sometimes
            # Jedi doesn't recognize sys.path modifications (like py.test
            # stuff).
            old_path, temp_path = self.file_path, os.path.dirname(self.file_path)
            while old_path != temp_path:
                sys_path_mod.append(temp_path)
                old_path, temp_path = temp_path, os.path.dirname(temp_path)
        else:
            sys_path_mod = list(sys_path.get_sys_path())

        return self._follow_sys_path(sys_path_mod)

    def namespace_packages(self, found_path, import_path):
        """
        Returns a list of paths of possible ``pkgutil``/``pkg_resources``
        namespaces. If the package is no "namespace package", an empty list is
        returned.
        """
        def follow_path(directories, paths):
            try:
                directory = next(directories)
            except StopIteration:
                return paths
            else:
                deeper_paths = []
                for p in paths:
                    new = os.path.join(p, directory)
                    if os.path.isdir(new) and new != found_path:
                        deeper_paths.append(new)
                return follow_path(directories, deeper_paths)

        with open(os.path.join(found_path, '__init__.py'), 'rb') as f:
            content = common.source_to_unicode(f.read())
            # these are strings that need to be used for namespace packages,
            # the first one is ``pkgutil``, the second ``pkg_resources``.
            options = ('declare_namespace(__name__)', 'extend_path(__path__')
            if options[0] in content or options[1] in content:
                # It is a namespace, now try to find the rest of the modules.
                return follow_path(iter(import_path), sys.path)
        return []

    def _follow_sys_path(self, sys_path):
        """
        Find a module with a path (of the module, like usb.backend.libusb10).
        """
        def follow_str(ns_path, string):
            debug.dbg('follow_module %s %s', ns_path, string)
            path = None
            if ns_path:
                path = ns_path
            elif self.level > 0:  # is a relative import
                path = self.get_relative_path()

            if path is not None:
                importing = find_module(string, [path])
            else:
                debug.dbg('search_module %s %s', string, self.file_path)
                # Override the sys.path. It works only good that way.
                # Injecting the path directly into `find_module` did not work.
                sys.path, temp = sys_path, sys.path
                try:
                    importing = find_module(string)
                finally:
                    sys.path = temp

            return importing

        current_namespace = (None, None, None)
        # now execute those paths
        rest = []
        for i, s in enumerate(self.import_path):
            try:
                current_namespace = follow_str(current_namespace[1], s)
            except ImportError:
                _continue = False
                if self.level >= 1 and len(self.import_path) == 1:
                    # follow `from . import some_variable`
                    rel_path = self.get_relative_path()
                    with common.ignored(ImportError):
                        current_namespace = follow_str(rel_path, '__init__')
                elif current_namespace[2]:  # is a package
                    for n in self.namespace_packages(current_namespace[1],
                                                     self.import_path[:i]):
                        try:
                            current_namespace = follow_str(n, s)
                            if current_namespace[1]:
                                _continue = True
                                break
                        except ImportError:
                            pass

                if not _continue:
                    if current_namespace[1]:
                        rest = self.import_path[i:]
                        break
                    else:
                        raise ModuleNotFound('The module you searched has not been found')

        path = current_namespace[1]
        is_package_directory = current_namespace[2]

        f = None
        if is_package_directory or current_namespace[0]:
            # is a directory module
            if is_package_directory:
                path += '/__init__.py'
                with open(path, 'rb') as f:
                    source = f.read()
            else:
                source = current_namespace[0].read()
                current_namespace[0].close()
            return load_module(path, source), rest
        else:
            return load_module(name=path), rest


def strip_imports(evaluator, scopes):
    """
    Here we strip the imports - they don't get resolved necessarily.
    Really used anymore? Merge with remove_star_imports?
    """
    result = []
    for s in scopes:
        if isinstance(s, pr.Import):
            result += ImportWrapper(evaluator, s).follow()
        else:
            result.append(s)
    return result


@cache.cache_star_import
def remove_star_imports(evaluator, scope, ignored_modules=()):
    """
    Check a module for star imports::

        from module import *

    and follow these modules.
    """
    modules = strip_imports(evaluator, (i for i in scope.get_imports() if i.star))
    new = []
    for m in modules:
        if m not in ignored_modules:
            new += remove_star_imports(evaluator, m, modules)
    modules += new

    # Filter duplicate modules.
    return set(modules)


def load_module(path=None, source=None, name=None):
    def load(source):
        if path is not None and path.endswith('.py'):
            if source is None:
                with open(path, 'rb') as f:
                    source = f.read()
        else:
            return compiled.load_module(path, name)
        p = path or name
        p = fast.FastParser(common.source_to_unicode(source), p)
        cache.save_parser(path, name, p)
        return p.module

    cached = cache.load_parser(path, name)
    return load(source) if cached is None else cached.module


def get_modules_containing_name(mods, name):
    """
    Search a name in the directories of modules.
    """
    def check_python_file(path):
        try:
            return cache.parser_cache[path].parser.module
        except KeyError:
            try:
                return check_fs(path)
            except IOError:
                return None

    def check_fs(path):
        with open(path, 'rb') as f:
            source = source_to_unicode(f.read())
            if name in source:
                return load_module(path, source)

    # skip non python modules
    mods = set(m for m in mods if not isinstance(m, compiled.CompiledObject))
    mod_paths = set()
    for m in mods:
        mod_paths.add(m.path)
        yield m

    if settings.dynamic_params_for_other_modules:
        paths = set(settings.additional_dynamic_modules)
        for p in mod_paths:
            if p is not None:
                d = os.path.dirname(p)
                for entry in os.listdir(d):
                    if entry not in mod_paths:
                        if entry.endswith('.py'):
                            paths.add(d + os.path.sep + entry)

        for p in sorted(paths):
            # make testing easier, sort it - same results on every interpreter
            c = check_python_file(p)
            if c is not None and c not in mods:
                yield c

########NEW FILE########
__FILENAME__ = iterable
"""
Contains all classes and functions to deal with lists, dicts, generators and
iterators in general.

Array modifications
*******************

If the content of an array (``set``/``list``) is requested somewhere, the
current module will be checked for appearances of ``arr.append``,
``arr.insert``, etc.  If the ``arr`` name points to an actual array, the
content will be added

This can be really cpu intensive, as you can imagine. Because |jedi| has to
follow **every** ``append`` and check wheter it's the right array. However this
works pretty good, because in *slow* cases, the recursion detector and other
settings will stop this process.

It is important to note that:

1. Array modfications work only in the current module.
2. Jedi only checks Array additions; ``list.pop``, etc are ignored.
"""
from itertools import chain

from jedi import common
from jedi import debug
from jedi import settings
from jedi._compatibility import use_metaclass, is_py3, unicode
from jedi.parser import representation as pr
from jedi.evaluate import compiled
from jedi.evaluate import helpers
from jedi.evaluate import precedence
from jedi.evaluate.cache import CachedMetaClass, memoize_default, NO_DEFAULT
from jedi.cache import underscore_memoization


class Generator(use_metaclass(CachedMetaClass, pr.Base)):
    """Handling of `yield` functions."""
    def __init__(self, evaluator, func, var_args):
        super(Generator, self).__init__()
        self._evaluator = evaluator
        self.func = func
        self.var_args = var_args

    @underscore_memoization
    def get_defined_names(self):
        """
        Returns a list of names that define a generator, which can return the
        content of a generator.
        """
        executes_generator = '__next__', 'send', 'next'
        for name in compiled.generator_obj.get_defined_names():
            if name.name in executes_generator:
                parent = GeneratorMethod(self, name.parent)
                yield helpers.FakeName(name.name, parent)
            else:
                yield name

    def iter_content(self):
        """ returns the content of __iter__ """
        return self._evaluator.execute(self.func, self.var_args, True)

    def get_index_types(self, index=None):
        debug.warning('Tried to get array access on a generator: %s', self)
        return []

    def __getattr__(self, name):
        if name not in ['start_pos', 'end_pos', 'parent', 'get_imports',
                        'asserts', 'doc', 'docstr', 'get_parent_until',
                        'get_code', 'subscopes']:
            raise AttributeError("Accessing %s of %s is not allowed."
                                 % (self, name))
        return getattr(self.func, name)

    def __repr__(self):
        return "<%s of %s>" % (type(self).__name__, self.func)


class GeneratorMethod(object):
    """``__next__`` and ``send`` methods."""
    def __init__(self, generator, builtin_func):
        self._builtin_func = builtin_func
        self._generator = generator

    def execute(self):
        return self._generator.iter_content()

    def __getattr__(self, name):
        return getattr(self._builtin_func, name)


class Array(use_metaclass(CachedMetaClass, pr.Base)):
    """
    Used as a mirror to pr.Array, if needed. It defines some getter
    methods which are important in this module.
    """
    def __init__(self, evaluator, array):
        self._evaluator = evaluator
        self._array = array

    @memoize_default(NO_DEFAULT)
    def get_index_types(self, indexes=()):
        """
        Get the types of a specific index or all, if not given.

        :param indexes: The index input types.
        """
        result = []
        if [index for index in indexes if isinstance(index, Slice)]:
            return [self]

        if len(indexes) == 1:
            # This is indexing only one element, with a fixed index number,
            # otherwise it just ignores the index (e.g. [1+1]).
            index = indexes[0]
            if isinstance(index, compiled.CompiledObject) \
                    and isinstance(index.obj, (int, str, unicode)):
                with common.ignored(KeyError, IndexError, TypeError):
                    return self.get_exact_index_types(index.obj)

        result = list(_follow_values(self._evaluator, self._array.values))
        result += check_array_additions(self._evaluator, self)
        return result

    def get_exact_index_types(self, mixed_index):
        """ Here the index is an int/str. Raises IndexError/KeyError """
        index = mixed_index
        if self.type == pr.Array.DICT:
            index = None
            for i, key_statement in enumerate(self._array.keys):
                # Because we only want the key to be a string.
                key_expression_list = key_statement.expression_list()
                if len(key_expression_list) != 1:  # cannot deal with complex strings
                    continue
                key = key_expression_list[0]
                if isinstance(key, pr.Literal):
                    key = key.value
                elif isinstance(key, pr.Name):
                    key = str(key)
                else:
                    continue

                if mixed_index == key:
                    index = i
                    break
            if index is None:
                raise KeyError('No key found in dictionary')

        # Can raise an IndexError
        values = [self._array.values[index]]
        return _follow_values(self._evaluator, values)

    def get_defined_names(self):
        """
        This method generates all `ArrayMethod` for one pr.Array.
        It returns e.g. for a list: append, pop, ...
        """
        # `array.type` is a string with the type, e.g. 'list'.
        scope = self._evaluator.find_types(compiled.builtin, self._array.type)[0]
        scope = self._evaluator.execute(scope)[0]  # builtins only have one class
        names = scope.get_defined_names()
        return [ArrayMethod(n) for n in names]

    @common.safe_property
    def parent(self):
        return compiled.builtin

    def get_parent_until(self):
        return compiled.builtin

    def __getattr__(self, name):
        if name not in ['type', 'start_pos', 'get_only_subelement', 'parent',
                        'get_parent_until', 'items']:
            raise AttributeError('Strange access on %s: %s.' % (self, name))
        return getattr(self._array, name)

    def __getitem__(self):
        return self._array.__getitem__()

    def __iter__(self):
        return self._array.__iter__()

    def __len__(self):
        return self._array.__len__()

    def __repr__(self):
        return "<e%s of %s>" % (type(self).__name__, self._array)


class ArrayMethod(object):
    """
    A name, e.g. `list.append`, it is used to access the original array
    methods.
    """
    def __init__(self, name):
        super(ArrayMethod, self).__init__()
        self.name = name

    def __getattr__(self, name):
        # Set access privileges:
        if name not in ['parent', 'names', 'start_pos', 'end_pos', 'get_code']:
            raise AttributeError('Strange accesson %s: %s.' % (self, name))
        return getattr(self.name, name)

    def get_parent_until(self):
        return compiled.builtin

    def __repr__(self):
        return "<%s of %s>" % (type(self).__name__, self.name)


def get_iterator_types(inputs):
    """Returns the types of any iterator (arrays, yields, __iter__, etc)."""
    iterators = []
    # Take the first statement (for has always only
    # one, remember `in`). And follow it.
    for it in inputs:
        if isinstance(it, (Generator, Array, ArrayInstance)):
            iterators.append(it)
        else:
            if not hasattr(it, 'execute_subscope_by_name'):
                debug.warning('iterator/for loop input wrong: %s', it)
                continue
            try:
                iterators += it.execute_subscope_by_name('__iter__')
            except KeyError:
                debug.warning('iterators: No __iter__ method found.')

    result = []
    from jedi.evaluate.representation import Instance
    for gen in iterators:
        if isinstance(gen, Array):
            # Array is a little bit special, since this is an internal
            # array, but there's also the list builtin, which is
            # another thing.
            result += gen.get_index_types()
        elif isinstance(gen, Instance):
            # __iter__ returned an instance.
            name = '__next__' if is_py3 else 'next'
            try:
                result += gen.execute_subscope_by_name(name)
            except KeyError:
                debug.warning('Instance has no __next__ function in %s.', gen)
        else:
            # is a generator
            result += gen.iter_content()
    return result


def check_array_additions(evaluator, array):
    """ Just a mapper function for the internal _check_array_additions """
    if not pr.Array.is_type(array._array, pr.Array.LIST, pr.Array.SET):
        # TODO also check for dict updates
        return []

    is_list = array._array.type == 'list'
    current_module = array._array.get_parent_until()
    res = _check_array_additions(evaluator, array, current_module, is_list)
    return res


@memoize_default([], evaluator_is_first_arg=True)
def _check_array_additions(evaluator, compare_array, module, is_list):
    """
    Checks if a `pr.Array` has "add" statements:
    >>> a = [""]
    >>> a.append(1)
    """
    if not settings.dynamic_array_additions or isinstance(module, compiled.CompiledObject):
        return []

    def check_calls(calls, add_name):
        """
        Calls are processed here. The part before the call is searched and
        compared with the original Array.
        """
        result = []
        for c in calls:
            call_path = list(c.generate_call_path())
            call_path_simple = [unicode(n) if isinstance(n, pr.NamePart) else n
                                for n in call_path]
            separate_index = call_path_simple.index(add_name)
            if add_name == call_path_simple[-1] or separate_index == 0:
                # this means that there is no execution -> [].append
                # or the keyword is at the start -> append()
                continue
            backtrack_path = iter(call_path[:separate_index])

            position = c.start_pos
            scope = c.get_parent_until(pr.IsScope)

            found = evaluator.eval_call_path(backtrack_path, scope, position)
            if not compare_array in found:
                continue

            params = call_path[separate_index + 1]
            if not params.values:
                continue  # no params: just ignore it
            if add_name in ['append', 'add']:
                for param in params:
                    result += evaluator.eval_statement(param)
            elif add_name in ['insert']:
                try:
                    second_param = params[1]
                except IndexError:
                    continue
                else:
                    result += evaluator.eval_statement(second_param)
            elif add_name in ['extend', 'update']:
                for param in params:
                    iterators = evaluator.eval_statement(param)
                result += get_iterator_types(iterators)
        return result

    from jedi.evaluate import representation as er

    def get_execution_parent(element, *stop_classes):
        """ Used to get an Instance/FunctionExecution parent """
        if isinstance(element, Array):
            stmt = element._array.parent
        else:
            # is an Instance with an ArrayInstance inside
            stmt = element.var_args[0].var_args.parent
        if isinstance(stmt, er.InstanceElement):
            stop_classes = list(stop_classes) + [er.Function]
        return stmt.get_parent_until(stop_classes)

    temp_param_add = settings.dynamic_params_for_other_modules
    settings.dynamic_params_for_other_modules = False

    search_names = ['append', 'extend', 'insert'] if is_list else \
        ['add', 'update']
    comp_arr_parent = get_execution_parent(compare_array, er.FunctionExecution)

    possible_stmts = []
    res = []
    for n in search_names:
        try:
            possible_stmts += module.used_names[n]
        except KeyError:
            continue
        for stmt in possible_stmts:
            # Check if the original scope is an execution. If it is, one
            # can search for the same statement, that is in the module
            # dict. Executions are somewhat special in jedi, since they
            # literally copy the contents of a function.
            if isinstance(comp_arr_parent, er.FunctionExecution):
                stmt = comp_arr_parent. \
                    get_statement_for_position(stmt.start_pos)
                if stmt is None:
                    continue
            # InstanceElements are special, because they don't get copied,
            # but have this wrapper around them.
            if isinstance(comp_arr_parent, er.InstanceElement):
                stmt = er.InstanceElement(comp_arr_parent.instance, stmt)

            if evaluator.recursion_detector.push_stmt(stmt):
                # check recursion
                continue

            res += check_calls(helpers.scan_statement_for_calls(stmt, n), n)
            evaluator.recursion_detector.pop_stmt()
    # reset settings
    settings.dynamic_params_for_other_modules = temp_param_add
    return res


def check_array_instances(evaluator, instance):
    """Used for set() and list() instances."""
    if not settings.dynamic_arrays_instances:
        return instance.var_args
    ai = ArrayInstance(evaluator, instance)
    return [ai]


class ArrayInstance(pr.Base):
    """
    Used for the usage of set() and list().
    This is definitely a hack, but a good one :-)
    It makes it possible to use set/list conversions.
    """
    def __init__(self, evaluator, instance):
        self._evaluator = evaluator
        self.instance = instance
        self.var_args = instance.var_args

    def iter_content(self):
        """
        The index is here just ignored, because of all the appends, etc.
        lists/sets are too complicated too handle that.
        """
        items = []
        from jedi.evaluate.representation import Instance
        for stmt in self.var_args:
            for typ in self._evaluator.eval_statement(stmt):
                if isinstance(typ, Instance) and len(typ.var_args):
                    array = typ.var_args[0]
                    if isinstance(array, ArrayInstance):
                        # Certain combinations can cause recursions, see tests.
                        if not self._evaluator.recursion_detector.push_stmt(self.var_args):
                            items += array.iter_content()
                            self._evaluator.recursion_detector.pop_stmt()
                items += get_iterator_types([typ])

        # TODO check if exclusion of tuple is a problem here.
        if isinstance(self.var_args, tuple) or self.var_args.parent is None:
            return []  # generated var_args should not be checked for arrays

        module = self.var_args.get_parent_until()
        is_list = str(self.instance.name) == 'list'
        items += _check_array_additions(self._evaluator, self.instance, module, is_list)
        return items


def _follow_values(evaluator, values):
    """ helper function for the index getters """
    return list(chain.from_iterable(evaluator.eval_statement(v) for v in values))


class Slice(object):
    def __init__(self, evaluator, start, stop, step):
        self._evaluator = evaluator
        # all of them are either a Precedence or None.
        self._start = start
        self._stop = stop
        self._step = step

    @property
    def obj(self):
        """
        Imitate CompiledObject.obj behavior and return a ``builtin.slice()``
        object.
        """
        def get(element):
            if element is None:
                return None

            result = self._evaluator.process_precedence_element(element)
            if len(result) != 1:
                # We want slices to be clear defined with just one type.
                # Otherwise we will return an empty slice object.
                raise IndexError
            try:
                return result[0].obj
            except AttributeError:
                return None

        try:
            return slice(get(self._start), get(self._stop), get(self._step))
        except IndexError:
            return slice(None, None, None)


def create_indexes_or_slices(evaluator, index_array):
    if not index_array:
        return ()

    # Just take the first part of the "array", because this is Python stdlib
    # behavior. Numpy et al. perform differently, but Jedi won't understand
    # that anyway.
    expression_list = index_array[0].expression_list()
    prec = precedence.create_precedence(expression_list)

    # check for slices
    if isinstance(prec, precedence.Precedence) and prec.operator == ':':
        start = prec.left
        if isinstance(start, precedence.Precedence) and start.operator == ':':
            stop = start.right
            start = start.left
            step = prec.right
        else:
            stop = prec.right
            step = None
        return (Slice(evaluator, start, stop, step),)
    else:
        return tuple(evaluator.process_precedence_element(prec))

########NEW FILE########
__FILENAME__ = param
import copy

from jedi.parser import representation as pr
from jedi.evaluate import iterable
from jedi import common
from jedi.evaluate import helpers


def get_params(evaluator, func, var_args):
    def gen_param_name_copy(param, keys=(), values=(), array_type=None):
        """
        Create a param with the original scope (of varargs) as parent.
        """
        if isinstance(var_args, pr.Array):
            parent = var_args.parent
            start_pos = var_args.start_pos
        else:
            parent = func
            start_pos = 0, 0

        new_param = copy.copy(param)
        new_param.is_generated = True
        if parent is not None:
            new_param.parent = parent

        # create an Array (-> needed for *args/**kwargs tuples/dicts)
        arr = pr.Array(helpers.FakeSubModule, start_pos, array_type, parent)
        arr.values = values
        key_stmts = []
        for key in keys:
            key_stmts.append(helpers.FakeStatement([key], start_pos))
        arr.keys = key_stmts
        arr.type = array_type

        new_param.set_expression_list([arr])

        name = copy.copy(param.get_name())
        name.parent = new_param
        return name

    result = []
    start_offset = 0
    from jedi.evaluate.representation import InstanceElement
    if isinstance(func, InstanceElement):
        # Care for self -> just exclude it and add the instance
        start_offset = 1
        self_name = copy.copy(func.params[0].get_name())
        self_name.parent = func.instance
        result.append(self_name)

    param_dict = {}
    for param in func.params:
        param_dict[str(param.get_name())] = param
    # There may be calls, which don't fit all the params, this just ignores it.
    var_arg_iterator = common.PushBackIterator(_var_args_iterator(evaluator, var_args))

    non_matching_keys = []
    keys_used = set()
    keys_only = False
    for param in func.params[start_offset:]:
        # The value and key can both be null. There, the defaults apply.
        # args / kwargs will just be empty arrays / dicts, respectively.
        # Wrong value count is just ignored. If you try to test cases that are
        # not allowed in Python, Jedi will maybe not show any completions.
        key, value = next(var_arg_iterator, (None, None))
        while key:
            keys_only = True
            try:
                key_param = param_dict[str(key)]
            except KeyError:
                non_matching_keys.append((key, value))
            else:
                keys_used.add(str(key))
                result.append(gen_param_name_copy(key_param, values=[value]))
            key, value = next(var_arg_iterator, (None, None))

        expression_list = param.expression_list()
        keys = []
        values = []
        array_type = None
        ignore_creation = False
        if param.stars == 1:
            # *args param
            array_type = pr.Array.TUPLE
            if value:
                values.append(value)
            for key, value in var_arg_iterator:
                # Iterate until a key argument is found.
                if key:
                    var_arg_iterator.push_back((key, value))
                    break
                values.append(value)
        elif param.stars == 2:
            # **kwargs param
            array_type = pr.Array.DICT
            if non_matching_keys:
                keys, values = zip(*non_matching_keys)
        elif not keys_only:
            # normal param
            if value is not None:
                values = [value]
            else:
                if param.assignment_details:
                    # No value: return the default values.
                    ignore_creation = True
                    result.append(param.get_name())
                    param.is_generated = True
                else:
                    # If there is no assignment detail, that means there is no
                    # assignment, just the result. Therefore nothing has to be
                    # returned.
                    values = []

        # Just ignore all the params that are without a key, after one keyword
        # argument was set.
        if not ignore_creation and (not keys_only or expression_list[0] == '**'):
            keys_used.add(str(key))
            result.append(gen_param_name_copy(param, keys=keys, values=values,
                                              array_type=array_type))

    if keys_only:
        # sometimes param arguments are not completely written (which would
        # create an Exception, but we have to handle that).
        for k in set(param_dict) - keys_used:
            result.append(gen_param_name_copy(param_dict[k]))
    return result


def _var_args_iterator(evaluator, var_args):
    """
    Yields a key/value pair, the key is None, if its not a named arg.
    """
    # `var_args` is typically an Array, and not a list.
    for stmt in var_args:
        if not isinstance(stmt, pr.Statement):
            if stmt is None:
                yield None, None
                continue
            old = stmt
            # generate a statement if it's not already one.
            stmt = helpers.FakeStatement([old])

        # *args
        expression_list = stmt.expression_list()
        if not len(expression_list):
            continue
        if expression_list[0] == '*':
            # *args must be some sort of an array, otherwise -> ignore
            for array in evaluator.eval_expression_list(expression_list[1:]):
                if isinstance(array, iterable.Array):
                    for field_stmt in array:  # yield from plz!
                        yield None, field_stmt
                elif isinstance(array, iterable.Generator):
                    for field_stmt in array.iter_content():
                        yield None, helpers.FakeStatement([field_stmt])
        # **kwargs
        elif expression_list[0] == '**':
            for array in evaluator.eval_expression_list(expression_list[1:]):
                if isinstance(array, iterable.Array):
                    for key_stmt, value_stmt in array.items():
                        # first index, is the key if syntactically correct
                        call = key_stmt.expression_list()[0]
                        if isinstance(call, pr.Name):
                            yield call, value_stmt
                        elif isinstance(call, pr.Call):
                            yield call.name, value_stmt
        # Normal arguments (including key arguments).
        else:
            if stmt.assignment_details:
                key_arr, op = stmt.assignment_details[0]
                # named parameter
                if key_arr and isinstance(key_arr[0], pr.Call):
                    yield key_arr[0].name, stmt
            else:
                yield None, stmt

########NEW FILE########
__FILENAME__ = precedence
"""
Handles operator precedence.
"""

from jedi._compatibility import unicode
from jedi.parser import representation as pr
from jedi import debug
from jedi.common import PushBackIterator
from jedi.evaluate.compiled import CompiledObject, create, builtin


class PythonGrammar(object):
    """
    Some kind of mirror of http://docs.python.org/3/reference/grammar.html.
    """

    class MultiPart(str):
        def __new__(cls, first, second):
            self = str.__new__(cls, first)
            self.second = second
            return self

        def __str__(self):
            return str.__str__(self) + ' ' + self.second

    FACTOR = '+', '-', '~'
    POWER = '**',
    TERM = '*', '/', '%', '//'
    ARITH_EXPR = '+', '-'

    SHIFT_EXPR = '<<', '>>'
    AND_EXPR = '&',
    XOR_EXPR = '^',
    EXPR = '|',

    COMPARISON = ('<', '>', '==', '>=', '<=', '!=', 'in',
                  MultiPart('not', 'in'), MultiPart('is', 'not'), 'is')

    NOT_TEST = 'not',
    AND_TEST = 'and',
    OR_TEST = 'or',

    #TEST = or_test ['if' or_test 'else' test] | lambdef

    TERNARY = 'if',
    SLICE = ':',

    ORDER = (POWER, TERM, ARITH_EXPR, SHIFT_EXPR, AND_EXPR, XOR_EXPR,
             EXPR, COMPARISON, AND_TEST, OR_TEST, TERNARY, SLICE)

    FACTOR_PRIORITY = 0  # highest priority
    LOWEST_PRIORITY = len(ORDER)
    NOT_TEST_PRIORITY = LOWEST_PRIORITY - 4  # priority only lower for `and`/`or`
    SLICE_PRIORITY = LOWEST_PRIORITY - 1  # priority only lower for `and`/`or`


class Precedence(object):
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

    def parse_tree(self, strip_literals=False):
        def process(which):
            try:
                which = which.parse_tree(strip_literals)
            except AttributeError:
                pass
            if strip_literals and isinstance(which, pr.Literal):
                which = which.value
            return which

        return (process(self.left), self.operator, process(self.right))

    def __repr__(self):
        return '(%s %s %s)' % (self.left, self.operator, self.right)


class TernaryPrecedence(Precedence):
    def __init__(self, left, operator, right, check):
        super(TernaryPrecedence, self).__init__(left, operator, right)
        self.check = check


def create_precedence(expression_list):
    iterator = PushBackIterator(iter(expression_list))
    return _check_operator(iterator)


def _syntax_error(element, msg='SyntaxError in precedence'):
    debug.warning('%s: %s, %s' % (msg, element, element.start_pos))


def _get_number(iterator, priority=PythonGrammar.LOWEST_PRIORITY):
    el = next(iterator)
    if isinstance(el, pr.Operator):
        if el in PythonGrammar.FACTOR:
            right = _get_number(iterator, PythonGrammar.FACTOR_PRIORITY)
        elif el in PythonGrammar.NOT_TEST \
                and priority >= PythonGrammar.NOT_TEST_PRIORITY:
            right = _get_number(iterator, PythonGrammar.NOT_TEST_PRIORITY)
        elif el in PythonGrammar.SLICE \
                and priority >= PythonGrammar.SLICE_PRIORITY:
            iterator.push_back(el)
            return None
        else:
            _syntax_error(el)
            return _get_number(iterator, priority)
        return Precedence(None, el, right)
    else:
        return el


def _check_operator(iterator, priority=PythonGrammar.LOWEST_PRIORITY):
    try:
        left = _get_number(iterator, priority)
    except StopIteration:
        return None

    for el in iterator:
        if not isinstance(el, pr.Operator):
            _syntax_error(el)
            continue

        operator = None
        for check_prio, check in enumerate(PythonGrammar.ORDER):
            if check_prio >= priority:
                # respect priorities.
                iterator.push_back(el)
                return left

            try:
                match_index = check.index(el)
            except ValueError:
                continue

            match = check[match_index]
            if isinstance(match, PythonGrammar.MultiPart):
                next_tok = next(iterator)
                if next_tok != match.second:
                    iterator.push_back(next_tok)
                    if el == 'is':  # `is not` special case
                        match = 'is'
                    else:
                        continue

            operator = match
            break

        if operator is None:
            _syntax_error(el)
            continue

        if operator in PythonGrammar.POWER:
            check_prio += 1  # to the power of is right-associative
        elif operator in PythonGrammar.TERNARY:
            try:
                middle = []
                for each in iterator:
                    if each == 'else':
                        break
                    middle.append(each)
                middle = create_precedence(middle)
            except StopIteration:
                _syntax_error(operator, 'SyntaxError ternary incomplete')
        right = _check_operator(iterator, check_prio)
        if right is None and not operator in PythonGrammar.SLICE:
            _syntax_error(iterator.current, 'SyntaxError operand missing')
        else:
            if operator in PythonGrammar.TERNARY:
                left = TernaryPrecedence(left, str(operator), right, middle)
            else:
                left = Precedence(left, str(operator), right)
    return left


def _literals_to_types(evaluator, result):
    # Changes literals ('a', 1, 1.0, etc) to its type instances (str(),
    # int(), float(), etc).
    for i, r in enumerate(result):
        if is_literal(r):
            # Literals are only valid as long as the operations are
            # correct. Otherwise add a value-free instance.
            cls = builtin.get_by_name(r.name)
            result[i] = evaluator.execute(cls)[0]
    return list(set(result))


def calculate(evaluator, left_result, operator, right_result):
    result = []
    if left_result is None and right_result:
        # cases like `-1` or `1 + ~1`
        for right in right_result:
            result.append(_factor_calculate(evaluator, operator, right))
        return result
    else:
        if not left_result or not right_result:
            # illegal slices e.g. cause left/right_result to be None
            result = (left_result or []) + (right_result or [])
            result = _literals_to_types(evaluator, result)
        else:
            # I don't think there's a reasonable chance that a string
            # operation is still correct, once we pass something like six
            # objects.
            if len(left_result) * len(right_result) > 6:
                result = _literals_to_types(evaluator, left_result + right_result)
            else:
                for left in left_result:
                    for right in right_result:
                        result += _element_calculate(evaluator, left, operator, right)
    return result


def _factor_calculate(evaluator, operator, right):
    if _is_number(right):
        if operator == '-':
            return create(evaluator, -right.obj)
    return right


def _is_number(obj):
    return isinstance(obj, CompiledObject) \
        and isinstance(obj.obj, (int, float))


def _is_string(obj):
    return isinstance(obj, CompiledObject) \
        and isinstance(obj.obj, (str, unicode))


def is_literal(obj):
    return _is_number(obj) or _is_string(obj)


def _element_calculate(evaluator, left, operator, right):
    if operator == '*':
        # for iterables, ignore * operations
        from jedi.evaluate import iterable
        if isinstance(left, iterable.Array) or _is_string(left):
            return [left]
    elif operator == '+':
        if _is_number(left) and _is_number(right) or _is_string(left) and _is_string(right):
            return [create(evaluator, left.obj + right.obj)]
    elif operator == '-':
        if _is_number(left) and _is_number(right):
            return [create(evaluator, left.obj - right.obj)]
    return [left, right]

########NEW FILE########
__FILENAME__ = recursion
"""
Recursions are the recipe of |jedi| to conquer Python code. However, someone
must stop recursions going mad. Some settings are here to make |jedi| stop at
the right time. You can read more about them :ref:`here <settings-recursion>`.

Next to :mod:`jedi.evaluate.cache` this module also makes |jedi| not
thread-safe. Why?  ``ExecutionRecursionDecorator`` uses class variables to
count the function calls.
"""
from jedi.parser import representation as pr
from jedi import debug
from jedi import settings
from jedi.evaluate import compiled
from jedi.evaluate import iterable


def recursion_decorator(func):
    def run(evaluator, stmt, *args, **kwargs):
        rec_detect = evaluator.recursion_detector
        # print stmt, len(self.node_statements())
        if rec_detect.push_stmt(stmt):
            return []
        else:
            result = func(evaluator, stmt, *args, **kwargs)
            rec_detect.pop_stmt()
        return result
    return run


class RecursionDetector(object):
    """
    A decorator to detect recursions in statements. In a recursion a statement
    at the same place, in the same module may not be executed two times.
    """
    def __init__(self):
        self.top = None
        self.current = None

    def push_stmt(self, stmt):
        self.current = _RecursionNode(stmt, self.current)
        check = self._check_recursion()
        if check:  # TODO remove False!!!!
            debug.warning('catched stmt recursion: %s against %s @%s', stmt,
                          check.stmt, stmt.start_pos)
            self.pop_stmt()
            return True
        return False

    def pop_stmt(self):
        if self.current is not None:
            # I don't know how current can be None, but sometimes it happens
            # with Python3.
            self.current = self.current.parent

    def _check_recursion(self):
        test = self.current
        while True:
            test = test.parent
            if self.current == test:
                return test
            if not test:
                return False

    def node_statements(self):
        result = []
        n = self.current
        while n:
            result.insert(0, n.stmt)
            n = n.parent
        return result


class _RecursionNode(object):
    """ A node of the RecursionDecorator. """
    def __init__(self, stmt, parent):
        self.script = stmt.get_parent_until()
        self.position = stmt.start_pos
        self.parent = parent
        self.stmt = stmt

        # Don't check param instances, they are not causing recursions
        # The same's true for the builtins, because the builtins are really
        # simple.
        self.is_ignored = isinstance(stmt, pr.Param) \
            or (self.script == compiled.builtin)

    def __eq__(self, other):
        if not other:
            return None

        is_list_comp = lambda x: isinstance(x, pr.ForFlow) and x.is_list_comp
        return self.script == other.script \
            and self.position == other.position \
            and not is_list_comp(self.stmt.parent) \
            and not is_list_comp(other.parent) \
            and not self.is_ignored and not other.is_ignored


def execution_recursion_decorator(func):
    def run(execution, evaluate_generator=False):
        detector = execution._evaluator.execution_recursion_detector
        if detector.push_execution(execution, evaluate_generator):
            result = []
        else:
            result = func(execution, evaluate_generator)
        detector.pop_execution()
        return result

    return run


class ExecutionRecursionDetector(object):
    """
    Catches recursions of executions.
    It is designed like a Singelton. Only one instance should exist.
    """
    def __init__(self):
        self.recursion_level = 0
        self.parent_execution_funcs = []
        self.execution_funcs = set()
        self.execution_count = 0

    def __call__(self, execution, evaluate_generator=False):
        debug.dbg('Execution recursions: %s', execution, self.recursion_level,
                  self.execution_count, len(self.execution_funcs))
        if self.check_recursion(execution, evaluate_generator):
            result = []
        else:
            result = self.func(execution, evaluate_generator)
        self.pop_execution()
        return result

    def pop_execution(cls):
        cls.parent_execution_funcs.pop()
        cls.recursion_level -= 1

    def push_execution(cls, execution, evaluate_generator):
        in_par_execution_funcs = execution.base in cls.parent_execution_funcs
        in_execution_funcs = execution.base in cls.execution_funcs
        cls.recursion_level += 1
        cls.execution_count += 1
        cls.execution_funcs.add(execution.base)
        cls.parent_execution_funcs.append(execution.base)

        if cls.execution_count > settings.max_executions:
            return True

        if isinstance(execution.base, (iterable.Array, iterable.Generator)):
            return False
        module = execution.get_parent_until()
        if evaluate_generator or module == compiled.builtin:
            return False

        if in_par_execution_funcs:
            if cls.recursion_level > settings.max_function_recursion_level:
                return True
        if in_execution_funcs and \
                len(cls.execution_funcs) > settings.max_until_execution_unique:
            return True
        if cls.execution_count > settings.max_executions_without_builtins:
            return True
        return False

########NEW FILE########
__FILENAME__ = representation
"""
Like described in the :mod:`jedi.evaluate.parsing_representation` module,
there's a need for an ast like module to represent the states of parsed
modules.

But now there are also structures in Python that need a little bit more than
that. An ``Instance`` for example is only a ``Class`` before it is
instantiated. This class represents these cases.

So, why is there also a ``Class`` class here? Well, there are decorators and
they change classes in Python 3.
"""
import copy

from jedi._compatibility import use_metaclass, unicode
from jedi.parser import representation as pr
from jedi.parser.tokenize import Token
from jedi import debug
from jedi import common
from jedi.evaluate.cache import memoize_default, CachedMetaClass
from jedi.evaluate import compiled
from jedi.evaluate import recursion
from jedi.evaluate import iterable
from jedi.evaluate import docstrings
from jedi.evaluate import helpers
from jedi.evaluate import param


class Executable(pr.IsScope):
    """
    An instance is also an executable - because __init__ is called
    :param var_args: The param input array, consist of `pr.Array` or list.
    """
    def __init__(self, evaluator, base, var_args=()):
        self._evaluator = evaluator
        self.base = base
        self.var_args = var_args

    def get_parent_until(self, *args, **kwargs):
        return self.base.get_parent_until(*args, **kwargs)

    @common.safe_property
    def parent(self):
        return self.base.parent


class Instance(use_metaclass(CachedMetaClass, Executable)):
    """
    This class is used to evaluate instances.
    """
    def __init__(self, evaluator, base, var_args=()):
        super(Instance, self).__init__(evaluator, base, var_args)
        if str(base.name) in ['list', 'set'] \
                and compiled.builtin == base.get_parent_until():
            # compare the module path with the builtin name.
            self.var_args = iterable.check_array_instances(evaluator, self)
        else:
            # need to execute the __init__ function, because the dynamic param
            # searching needs it.
            with common.ignored(KeyError):
                self.execute_subscope_by_name('__init__', self.var_args)
        # Generated instances are classes that are just generated by self
        # (No var_args) used.
        self.is_generated = False

    @memoize_default()
    def _get_method_execution(self, func):
        func = InstanceElement(self._evaluator, self, func, True)
        return FunctionExecution(self._evaluator, func, self.var_args)

    def _get_func_self_name(self, func):
        """
        Returns the name of the first param in a class method (which is
        normally self.
        """
        try:
            return str(func.params[0].get_name())
        except IndexError:
            return None

    @memoize_default([])
    def get_self_attributes(self):
        def add_self_dot_name(name):
            """
            Need to copy and rewrite the name, because names are now
            ``instance_usage.variable`` instead of ``self.variable``.
            """
            n = copy.copy(name)
            n.names = n.names[1:]
            n._get_code = unicode(n.names[-1])
            names.append(InstanceElement(self._evaluator, self, n))

        names = []
        # This loop adds the names of the self object, copies them and removes
        # the self.
        for sub in self.base.subscopes:
            if isinstance(sub, pr.Class):
                continue
            # Get the self name, if there's one.
            self_name = self._get_func_self_name(sub)
            if not self_name:
                continue

            if sub.name.get_code() == '__init__':
                # ``__init__`` is special because the params need are injected
                # this way. Therefore an execution is necessary.
                if not sub.decorators:
                    # __init__ decorators should generally just be ignored,
                    # because to follow them and their self variables is too
                    # complicated.
                    sub = self._get_method_execution(sub)
            for n in sub.get_defined_names():
                # Only names with the selfname are being added.
                # It is also important, that they have a len() of 2,
                # because otherwise, they are just something else
                if unicode(n.names[0]) == self_name and len(n.names) == 2:
                    add_self_dot_name(n)

        if not isinstance(self.base, compiled.CompiledObject):
            for s in self.base.get_super_classes():
                for inst in self._evaluator.execute(s):
                    names += inst.get_self_attributes()
        return names

    def get_subscope_by_name(self, name):
        sub = self.base.get_subscope_by_name(name)
        return InstanceElement(self._evaluator, self, sub, True)

    def execute_subscope_by_name(self, name, args=()):
        method = self.get_subscope_by_name(name)
        return self._evaluator.execute(method, args)

    def get_descriptor_return(self, obj):
        """ Throws a KeyError if there's no method. """
        # Arguments in __get__ descriptors are obj, class.
        # `method` is the new parent of the array, don't know if that's good.
        args = [obj, obj.base] if isinstance(obj, Instance) else [None, obj]
        return self.execute_subscope_by_name('__get__', args)

    @memoize_default([])
    def get_defined_names(self):
        """
        Get the instance vars of a class. This includes the vars of all
        classes
        """
        names = self.get_self_attributes()

        for var in self.base.instance_names():
            names.append(InstanceElement(self._evaluator, self, var, True))
        return names

    def scope_generator(self):
        """
        An Instance has two scopes: The scope with self names and the class
        scope. Instance variables have priority over the class scope.
        """
        yield self, self.get_self_attributes()

        names = []
        for var in self.base.instance_names():
            names.append(InstanceElement(self._evaluator, self, var, True))
        yield self, names

    def is_callable(self):
        try:
            self.get_subscope_by_name('__call__')
            return True
        except KeyError:
            return False

    def get_index_types(self, indexes=[]):
        if any([isinstance(i, iterable.Slice) for i in indexes]):
            # Slice support in Jedi is very marginal, at the moment, so just
            # ignore them in case of __getitem__.
            # TODO support slices in a more general way.
            indexes = []

        try:
            return self.execute_subscope_by_name('__getitem__', indexes)
        except KeyError:
            debug.warning('No __getitem__, cannot access the array.')
            return []

    def __getattr__(self, name):
        if name not in ['start_pos', 'end_pos', 'name', 'get_imports',
                        'doc', 'raw_doc', 'asserts']:
            raise AttributeError("Instance %s: Don't touch this (%s)!"
                                 % (self, name))
        return getattr(self.base, name)

    def __repr__(self):
        return "<e%s of %s (var_args: %s)>" % \
            (type(self).__name__, self.base, len(self.var_args or []))


class InstanceElement(use_metaclass(CachedMetaClass, pr.Base)):
    """
    InstanceElement is a wrapper for any object, that is used as an instance
    variable (e.g. self.variable or class methods).
    """
    def __init__(self, evaluator, instance, var, is_class_var=False):
        self._evaluator = evaluator
        if isinstance(var, pr.Function):
            var = Function(evaluator, var)
        elif isinstance(var, pr.Class):
            var = Class(evaluator, var)
        self.instance = instance
        self.var = var
        self.is_class_var = is_class_var

    @common.safe_property
    @memoize_default()
    def parent(self):
        par = self.var.parent
        if isinstance(par, Class) and par == self.instance.base \
                or isinstance(par, pr.Class) \
                and par == self.instance.base.base:
            par = self.instance
        elif not isinstance(par, (pr.Module, compiled.CompiledObject)):
            par = InstanceElement(self.instance._evaluator, self.instance, par, self.is_class_var)
        return par

    def get_parent_until(self, *args, **kwargs):
        return pr.Simple.get_parent_until(self, *args, **kwargs)

    def get_decorated_func(self):
        """ Needed because the InstanceElement should not be stripped """
        func = self.var.get_decorated_func()
        func = InstanceElement(self._evaluator, self.instance, func)
        return func

    def expression_list(self):
        # Copy and modify the array.
        return [InstanceElement(self.instance._evaluator, self.instance, command, self.is_class_var)
                if not isinstance(command, (pr.Operator, Token)) else command
                for command in self.var.expression_list()]

    def __iter__(self):
        for el in self.var.__iter__():
            yield InstanceElement(self.instance._evaluator, self.instance, el, self.is_class_var)

    def __getattr__(self, name):
        return getattr(self.var, name)

    def isinstance(self, *cls):
        return isinstance(self.var, cls)

    def is_callable(self):
        return self.var.is_callable()

    def __repr__(self):
        return "<%s of %s>" % (type(self).__name__, self.var)


class Class(use_metaclass(CachedMetaClass, pr.IsScope)):
    """
    This class is not only important to extend `pr.Class`, it is also a
    important for descriptors (if the descriptor methods are evaluated or not).
    """
    def __init__(self, evaluator, base):
        self._evaluator = evaluator
        self.base = base

    @memoize_default(default=())
    def get_super_classes(self):
        supers = []
        # TODO care for mro stuff (multiple super classes).
        for s in self.base.supers:
            # Super classes are statements.
            for cls in self._evaluator.eval_statement(s):
                if not isinstance(cls, (Class, compiled.CompiledObject)):
                    debug.warning('Received non class as a super class.')
                    continue  # Just ignore other stuff (user input error).
                supers.append(cls)
        if not supers and self.base.parent != compiled.builtin:
            # add `object` to classes
            supers += self._evaluator.find_types(compiled.builtin, 'object')
        return supers

    @memoize_default(default=())
    def instance_names(self):
        def in_iterable(name, iterable):
            """ checks if the name is in the variable 'iterable'. """
            for i in iterable:
                # Only the last name is important, because these names have a
                # maximal length of 2, with the first one being `self`.
                if unicode(i.names[-1]) == unicode(name.names[-1]):
                    return True
            return False

        result = self.base.get_defined_names()
        super_result = []
        # TODO mro!
        for cls in self.get_super_classes():
            # Get the inherited names.
            if isinstance(cls, compiled.CompiledObject):
                super_result += cls.get_defined_names()
            else:
                for i in cls.instance_names():
                    if not in_iterable(i, result):
                        super_result.append(i)
        result += super_result
        return result

    @memoize_default(default=())
    def get_defined_names(self):
        result = self.instance_names()
        type_cls = self._evaluator.find_types(compiled.builtin, 'type')[0]
        return result + list(type_cls.get_defined_names())

    def get_subscope_by_name(self, name):
        for sub in reversed(self.subscopes):
            if sub.name.get_code() == name:
                return sub
        raise KeyError("Couldn't find subscope.")

    def is_callable(self):
        return True

    @common.safe_property
    def name(self):
        return self.base.name

    def __getattr__(self, name):
        if name not in ['start_pos', 'end_pos', 'parent', 'asserts', 'raw_doc',
                        'doc', 'get_imports', 'get_parent_until', 'get_code',
                        'subscopes']:
            raise AttributeError("Don't touch this: %s of %s !" % (name, self))
        return getattr(self.base, name)

    def __repr__(self):
        return "<e%s of %s>" % (type(self).__name__, self.base)


class Function(use_metaclass(CachedMetaClass, pr.IsScope)):
    """
    Needed because of decorators. Decorators are evaluated here.
    """
    def __init__(self, evaluator, func, is_decorated=False):
        """ This should not be called directly """
        self._evaluator = evaluator
        self.base_func = func
        self.is_decorated = is_decorated

    @memoize_default()
    def _decorated_func(self):
        """
        Returns the function, that is to be executed in the end.
        This is also the places where the decorators are processed.
        """
        f = self.base_func

        # Only enter it, if has not already been processed.
        if not self.is_decorated:
            for dec in reversed(self.base_func.decorators):
                debug.dbg('decorator: %s %s', dec, f)
                dec_results = self._evaluator.eval_statement(dec)
                if not len(dec_results):
                    debug.warning('decorator not found: %s on %s', dec, self.base_func)
                    return None
                decorator = dec_results.pop()
                if dec_results:
                    debug.warning('multiple decorators found %s %s',
                                  self.base_func, dec_results)
                # Create param array.
                old_func = Function(self._evaluator, f, is_decorated=True)

                wrappers = self._evaluator.execute(decorator, (old_func,))
                if not len(wrappers):
                    debug.warning('no wrappers found %s', self.base_func)
                    return None
                if len(wrappers) > 1:
                    # TODO resolve issue with multiple wrappers -> multiple types
                    debug.warning('multiple wrappers found %s %s',
                                  self.base_func, wrappers)
                f = wrappers[0]

                debug.dbg('decorator end %s', f)

        if isinstance(f, pr.Function):
            f = Function(self._evaluator, f, True)
        return f

    def get_decorated_func(self):
        """
        This function exists for the sole purpose of returning itself if the
        decorator doesn't turn out to "work".

        We just ignore the decorator here, because sometimes decorators are
        just really complicated and Jedi cannot understand them.
        """
        return self._decorated_func() \
            or Function(self._evaluator, self.base_func, True)

    def get_magic_function_names(self):
        return compiled.magic_function_class.get_defined_names()

    def get_magic_function_scope(self):
        return compiled.magic_function_class

    def is_callable(self):
        return True

    def __getattr__(self, name):
        return getattr(self.base_func, name)

    def __repr__(self):
        decorated_func = self._decorated_func()
        dec = ''
        if decorated_func is not None and decorated_func != self:
            dec = " is " + repr(decorated_func)
        return "<e%s of %s%s>" % (type(self).__name__, self.base_func, dec)


class FunctionExecution(Executable):
    """
    This class is used to evaluate functions and their returns.

    This is the most complicated class, because it contains the logic to
    transfer parameters. It is even more complicated, because there may be
    multiple calls to functions and recursion has to be avoided. But this is
    responsibility of the decorators.
    """
    @memoize_default(default=())
    @recursion.execution_recursion_decorator
    def get_return_types(self, evaluate_generator=False):
        func = self.base
        # Feed the listeners, with the params.
        for listener in func.listeners:
            listener.execute(self._get_params())
        if func.is_generator and not evaluate_generator:
            return [iterable.Generator(self._evaluator, func, self.var_args)]
        else:
            stmts = docstrings.find_return_types(self._evaluator, func)
            for r in self.returns:
                if r is not None:
                    stmts += self._evaluator.eval_statement(r)
            return stmts

    @memoize_default(default=())
    def _get_params(self):
        """
        This returns the params for an TODO and is injected as a
        'hack' into the pr.Function class.
        This needs to be here, because Instance can have __init__ functions,
        which act the same way as normal functions.
        """
        return param.get_params(self._evaluator, self.base, self.var_args)

    def get_defined_names(self):
        """
        Call the default method with the own instance (self implements all
        the necessary functions). Add also the params.
        """
        return self._get_params() + pr.Scope.get_defined_names(self)

    def _copy_properties(self, prop):
        """
        Literally copies a property of a Function. Copying is very expensive,
        because it is something like `copy.deepcopy`. However, these copied
        objects can be used for the executions, as if they were in the
        execution.
        """
        # Copy all these lists into this local function.
        attr = getattr(self.base, prop)
        objects = []
        for element in attr:
            if element is None:
                copied = element
            else:
                copied = helpers.fast_parent_copy(element)
                copied.parent = self._scope_copy(copied.parent)
                if isinstance(copied, pr.Function):
                    copied = Function(self._evaluator, copied)
            objects.append(copied)
        return objects

    def __getattr__(self, name):
        if name not in ['start_pos', 'end_pos', 'imports', '_sub_module']:
            raise AttributeError('Tried to access %s: %s. Why?' % (name, self))
        return getattr(self.base, name)

    @memoize_default()
    def _scope_copy(self, scope):
        """ Copies a scope (e.g. if) in an execution """
        # TODO method uses different scopes than the subscopes property.

        # just check the start_pos, sometimes it's difficult with closures
        # to compare the scopes directly.
        if scope.start_pos == self.start_pos:
            return self
        else:
            copied = helpers.fast_parent_copy(scope)
            copied.parent = self._scope_copy(copied.parent)
            return copied

    @common.safe_property
    @memoize_default([])
    def returns(self):
        return self._copy_properties('returns')

    @common.safe_property
    @memoize_default([])
    def asserts(self):
        return self._copy_properties('asserts')

    @common.safe_property
    @memoize_default([])
    def statements(self):
        return self._copy_properties('statements')

    @common.safe_property
    @memoize_default([])
    def subscopes(self):
        return self._copy_properties('subscopes')

    def get_statement_for_position(self, pos):
        return pr.Scope.get_statement_for_position(self, pos)

    def __repr__(self):
        return "<%s of %s>" % (type(self).__name__, self.base)

########NEW FILE########
__FILENAME__ = stdlib
"""
Implementations of standard library functions, because it's not possible to
understand them with Jedi.
"""
from jedi._compatibility import unicode
from jedi.evaluate import compiled
from jedi.evaluate import representation as er
from jedi.evaluate import iterable
from jedi.evaluate.helpers import FakeArray, FakeStatement
from jedi.parser import representation as pr
from jedi import debug


class NotInStdLib(LookupError):
    pass


def execute(evaluator, obj, params):
    try:
        obj_name = str(obj.name)
    except AttributeError:
        pass
    else:
        if obj.parent == compiled.builtin:
            # for now we just support builtin functions.
            try:
                return _implemented['builtins'][obj_name](evaluator, obj, params)
            except KeyError:
                pass
    raise NotInStdLib()


def _follow_param(evaluator, params, index):
    try:
        stmt = params[index]
    except IndexError:
        return []
    else:
        if isinstance(stmt, pr.Statement):
            return evaluator.eval_statement(stmt)
        else:
            return [stmt]  # just some arbitrary object


def builtins_getattr(evaluator, obj, params):
    stmts = []
    # follow the first param
    objects = _follow_param(evaluator, params, 0)
    names = _follow_param(evaluator, params, 1)
    for obj in objects:
        if not isinstance(obj, (er.Instance, er.Class, pr.Module, compiled.CompiledObject)):
            debug.warning('getattr called without instance')
            continue

        for name in names:
            s = unicode, str
            if isinstance(name, compiled.CompiledObject) and isinstance(name.obj, s):
                stmts += evaluator.follow_path(iter([name.obj]), [obj], obj)
            else:
                debug.warning('getattr called without str')
                continue
    return stmts


def builtins_type(evaluator, obj, params):
    if len(params) == 1:
        # otherwise it would be a metaclass... maybe someday...
        objects = _follow_param(evaluator, params, 0)
        return [o.base for o in objects if isinstance(o, er.Instance)]
    return []


def builtins_super(evaluator, obj, params):
    # TODO make this able to detect multiple inheritance super
    accept = (pr.Function,)
    func = params.get_parent_until(accept)
    if func.isinstance(*accept):
        cls = func.get_parent_until(accept + (pr.Class,),
                                    include_current=False)
        if isinstance(cls, pr.Class):
            cls = er.Class(evaluator, cls)
            su = cls.get_super_classes()
            if su:
                return evaluator.execute(su[0])
    return []


def builtins_reversed(evaluator, obj, params):
    objects = _follow_param(evaluator, params, 0)
    if objects:
        # unpack the iterator values
        objects = tuple(iterable.get_iterator_types(objects))
        if objects:
            rev = reversed(objects)
            # Repack iterator values and then run it the normal way. This is
            # necessary, because `reversed` is a function and autocompletion
            # would fail in certain cases like `reversed(x).__iter__` if we
            # just returned the result directly.
            stmts = [FakeStatement([r]) for r in rev]
            objects = (FakeArray(stmts, objects[0].parent),)
    return [er.Instance(evaluator, obj, objects)]


_implemented = {
    'builtins': {
        'getattr': builtins_getattr,
        'type': builtins_type,
        'super': builtins_super,
        'reversed': builtins_reversed,
    }
}

########NEW FILE########
__FILENAME__ = sys_path
import os
import sys

from jedi._compatibility import exec_function, unicode
from jedi.parser import representation as pr
from jedi import debug
from jedi import common


def get_sys_path():
    def check_virtual_env(sys_path):
        """ Add virtualenv's site-packages to the `sys.path`."""
        venv = os.getenv('VIRTUAL_ENV')
        if not venv:
            return
        venv = os.path.abspath(venv)
        p = os.path.join(
            venv, 'lib', 'python%d.%d' % sys.version_info[:2], 'site-packages')
        sys_path.insert(0, p)

    check_virtual_env(sys.path)
    return [p for p in sys.path if p != ""]


#@cache.memoize_default([]) TODO add some sort of cache again.
def sys_path_with_modifications(module):
    def execute_code(code):
        c = "import os; from os.path import *; result=%s"
        variables = {'__file__': module.path}
        try:
            exec_function(c % code, variables)
        except Exception:
            debug.warning('sys.path manipulation detected, but failed to evaluate.')
            return None
        try:
            res = variables['result']
            if isinstance(res, str):
                return os.path.abspath(res)
            else:
                return None
        except KeyError:
            return None

    def check_module(module):
        try:
            possible_stmts = module.used_names['path']
        except KeyError:
            return get_sys_path()

        sys_path = list(get_sys_path())  # copy
        for p in possible_stmts:
            if not isinstance(p, pr.Statement):
                continue
            expression_list = p.expression_list()
            # sys.path command is just one thing.
            if len(expression_list) != 1 or not isinstance(expression_list[0], pr.Call):
                continue
            call = expression_list[0]
            n = call.name
            if not isinstance(n, pr.Name) or len(n.names) != 3:
                continue
            if [unicode(x) for x in n.names[:2]] != ['sys', 'path']:
                continue
            array_cmd = unicode(n.names[2])
            if call.execution is None:
                continue
            exe = call.execution
            if not (array_cmd == 'insert' and len(exe) == 2
                    or array_cmd == 'append' and len(exe) == 1):
                continue

            if array_cmd == 'insert':
                exe_type, exe.type = exe.type, pr.Array.NOARRAY
                exe_pop = exe.values.pop(0)
                res = execute_code(exe.get_code())
                if res is not None:
                    sys_path.insert(0, res)
                    debug.dbg('sys path inserted: %s', res)
                exe.type = exe_type
                exe.values.insert(0, exe_pop)
            elif array_cmd == 'append':
                res = execute_code(exe.get_code())
                if res is not None:
                    sys_path.append(res)
                    debug.dbg('sys path added: %s', res)
        return sys_path

    if module.path is None:
        # Support for modules without a path is bad, therefore return the
        # normal path.
        return list(get_sys_path())

    curdir = os.path.abspath(os.curdir)
    with common.ignored(OSError):
        os.chdir(os.path.dirname(module.path))

    result = check_module(module)
    result += _detect_django_path(module.path)

    # cleanup, back to old directory
    os.chdir(curdir)
    return result


def _detect_django_path(module_path):
    """ Detects the path of the very well known Django library (if used) """
    result = []
    while True:
        new = os.path.dirname(module_path)
        # If the module_path doesn't change anymore, we're finished -> /
        if new == module_path:
            break
        else:
            module_path = new

        with common.ignored(IOError):
            with open(module_path + os.path.sep + 'manage.py'):
                debug.dbg('Found django path: %s', module_path)
                result.append(module_path)
    return result

########NEW FILE########
__FILENAME__ = fast
"""
Basically a parser that is faster, because it tries to parse only parts and if
anything changes, it only reparses the changed parts. But because it's not
finished (and still not working as I want), I won't document it any further.
"""
import re

from jedi._compatibility import use_metaclass, unicode
from jedi import settings
from jedi import common
from jedi.parser import Parser
from jedi.parser import representation as pr
from jedi.parser import tokenize
from jedi import cache
from jedi.parser.tokenize import (source_tokens, Token, FLOWS, NEWLINE,
                                  COMMENT, ENDMARKER)


class Module(pr.Simple, pr.Module):
    def __init__(self, parsers):
        super(Module, self).__init__(self, (1, 0))
        self.parsers = parsers
        self.reset_caches()

        self.start_pos = 1, 0
        self.end_pos = None, None

    def reset_caches(self):
        """ This module does a whole lot of caching, because it uses different
        parsers. """
        with common.ignored(AttributeError):
            del self._used_names

    def __getattr__(self, name):
        if name.startswith('__'):
            raise AttributeError('Not available!')
        else:
            return getattr(self.parsers[0].module, name)

    @property
    @cache.underscore_memoization
    def used_names(self):
        used_names = {}
        for p in self.parsers:
            for k, statement_set in p.module.used_names.items():
                if k in used_names:
                    used_names[k] |= statement_set
                else:
                    used_names[k] = set(statement_set)
        return used_names

    def __repr__(self):
        return "<fast.%s: %s@%s-%s>" % (type(self).__name__, self.name,
                                        self.start_pos[0], self.end_pos[0])


class CachedFastParser(type):
    """ This is a metaclass for caching `FastParser`. """
    def __call__(self, source, module_path=None):
        if not settings.fast_parser:
            return Parser(source, module_path)

        pi = cache.parser_cache.get(module_path, None)
        if pi is None or isinstance(pi.parser, Parser):
            p = super(CachedFastParser, self).__call__(source, module_path)
        else:
            p = pi.parser  # pi is a `cache.ParserCacheItem`
            p.update(source)
        return p


class ParserNode(object):
    def __init__(self, parser, code, parent=None):
        self.parent = parent

        self.children = []
        # must be created before new things are added to it.
        self.save_contents(parser, code)

    def save_contents(self, parser, code):
        self.code = code
        self.hash = hash(code)
        self.parser = parser

        try:
            # with fast_parser we have either 1 subscope or only statements.
            self.content_scope = parser.module.subscopes[0]
        except IndexError:
            self.content_scope = parser.module

        scope = self.content_scope
        self._contents = {}
        for c in pr.SCOPE_CONTENTS:
            self._contents[c] = list(getattr(scope, c))
        self._is_generator = scope.is_generator

        self.old_children = self.children
        self.children = []

    def reset_contents(self):
        scope = self.content_scope
        for key, c in self._contents.items():
            setattr(scope, key, list(c))
        scope.is_generator = self._is_generator

        if self.parent is None:
            # Global vars of the first one can be deleted, in the global scope
            # they make no sense.
            self.parser.module.global_vars = []

        for c in self.children:
            c.reset_contents()

    def parent_until_indent(self, indent=None):
        if indent is None or self.indent >= indent and self.parent:
            self.old_children = []
            if self.parent is not None:
                return self.parent.parent_until_indent(indent)
        return self

    @property
    def indent(self):
        if not self.parent:
            return 0
        module = self.parser.module
        try:
            el = module.subscopes[0]
        except IndexError:
            try:
                el = module.statements[0]
            except IndexError:
                try:
                    el = module.imports[0]
                except IndexError:
                    try:
                        el = [r for r in module.returns if r is not None][0]
                    except IndexError:
                        return self.parent.indent + 1
        return el.start_pos[1]

    def _set_items(self, parser, set_parent=False):
        # insert parser objects into current structure
        scope = self.content_scope
        for c in pr.SCOPE_CONTENTS:
            content = getattr(scope, c)
            items = getattr(parser.module, c)
            if set_parent:
                for i in items:
                    if i is None:
                        continue  # happens with empty returns
                    i.parent = scope.use_as_parent
                    if isinstance(i, (pr.Function, pr.Class)):
                        for d in i.decorators:
                            d.parent = scope.use_as_parent
            content += items

        # global_vars
        cur = self
        while cur.parent is not None:
            cur = cur.parent
        cur.parser.module.global_vars += parser.module.global_vars

        scope.is_generator |= parser.module.is_generator

    def add_node(self, node, set_parent=False):
        """Adding a node means adding a node that was already added earlier"""
        self.children.append(node)
        self._set_items(node.parser, set_parent=set_parent)
        node.old_children = node.children  # TODO potential memory leak?
        node.children = []

        scope = self.content_scope
        while scope is not None:
            #print('x',scope)
            if not isinstance(scope, pr.SubModule):
                # TODO This seems like a strange thing. Check again.
                scope.end_pos = node.content_scope.end_pos
            scope = scope.parent
        return node

    def add_parser(self, parser, code):
        return self.add_node(ParserNode(parser, code, self), True)


class FastParser(use_metaclass(CachedFastParser)):
    def __init__(self, code, module_path=None):
        # set values like `pr.Module`.
        self.module_path = module_path

        self.current_node = None
        self.parsers = []
        self.module = Module(self.parsers)
        self.reset_caches()

        try:
            self._parse(code)
        except:
            # FastParser is cached, be careful with exceptions
            self.parsers[:] = []
            raise

    def update(self, code):
        self.reset_caches()

        try:
            self._parse(code)
        except:
            # FastParser is cached, be careful with exceptions
            self.parsers[:] = []
            raise

    def _split_parts(self, code):
        """
        Split the code into different parts. This makes it possible to parse
        each part seperately and therefore cache parts of the file and not
        everything.
        """
        def add_part():
            txt = '\n'.join(current_lines)
            if txt:
                if add_to_last and parts:
                    parts[-1] += '\n' + txt
                else:
                    parts.append(txt)
                current_lines[:] = []

        r_keyword = '^[ \t]*(def|class|@|%s)' % '|'.join(tokenize.FLOWS)

        # Split only new lines. Distinction between \r\n is the tokenizer's
        # job.
        self._lines = code.split('\n')
        current_lines = []
        parts = []
        is_decorator = False
        current_indent = 0
        old_indent = 0
        new_indent = False
        in_flow = False
        add_to_last = False
        # All things within flows are simply being ignored.
        for i, l in enumerate(self._lines):
            # check for dedents
            m = re.match('^([\t ]*)(.?)', l)
            indent = len(m.group(1))
            if m.group(2) in ['', '#']:
                current_lines.append(l)  # just ignore comments and blank lines
                continue

            if indent < current_indent:  # -> dedent
                current_indent = indent
                new_indent = False
                if not in_flow or indent < old_indent:
                    add_part()
                    add_to_last = False
                in_flow = False
            elif new_indent:
                current_indent = indent
                new_indent = False

            # Check lines for functions/classes and split the code there.
            if not in_flow:
                m = re.match(r_keyword, l)
                if m:
                    in_flow = m.group(1) in tokenize.FLOWS
                    if not is_decorator and not in_flow:
                        add_part()
                        add_to_last = False
                    is_decorator = '@' == m.group(1)
                    if not is_decorator:
                        old_indent = current_indent
                        current_indent += 1  # it must be higher
                        new_indent = True
                elif is_decorator:
                    is_decorator = False
                    add_to_last = True

            current_lines.append(l)
        add_part()

        return parts

    def _parse(self, code):
        """ :type code: str """
        def empty_parser():
            new, temp = self._get_parser(unicode(''), unicode(''), 0, [], False)
            return new

        parts = self._split_parts(code)
        self.parsers[:] = []

        line_offset = 0
        start = 0
        p = None
        is_first = True

        for code_part in parts:
            lines = code_part.count('\n') + 1
            if is_first or line_offset >= p.module.end_pos[0]:
                indent = len(re.match(r'[ \t]*', code_part).group(0))
                if is_first and self.current_node is not None:
                    nodes = [self.current_node]
                else:
                    nodes = []
                if self.current_node is not None:

                    self.current_node = \
                        self.current_node.parent_until_indent(indent)
                    nodes += self.current_node.old_children

                # check if code_part has already been parsed
                # print '#'*45,line_offset, p and p.module.end_pos, '\n', code_part
                p, node = self._get_parser(code_part, code[start:],
                                           line_offset, nodes, not is_first)

                # The actual used code_part is different from the given code
                # part, because of docstrings for example there's a chance that
                # splits are wrong.
                used_lines = self._lines[line_offset:p.module.end_pos[0]]
                code_part_actually_used = '\n'.join(used_lines)

                if is_first and p.module.subscopes:
                    # special case, we cannot use a function subscope as a
                    # base scope, subscopes would save all the other contents
                    new = empty_parser()
                    if self.current_node is None:
                        self.current_node = ParserNode(new, '')
                    else:
                        self.current_node.save_contents(new, '')
                    self.parsers.append(new)
                    is_first = False

                if is_first:
                    if self.current_node is None:
                        self.current_node = ParserNode(p, code_part_actually_used)
                    else:
                        self.current_node.save_contents(p, code_part_actually_used)
                else:
                    if node is None:
                        self.current_node = \
                            self.current_node.add_parser(p, code_part_actually_used)
                    else:
                        self.current_node = self.current_node.add_node(node)

                self.parsers.append(p)

                is_first = False
            #else:
                #print '#'*45, line_offset, p.module.end_pos, 'theheck\n', repr(code_part)

            line_offset += lines
            start += len(code_part) + 1  # +1 for newline

        if self.parsers:
            self.current_node = self.current_node.parent_until_indent()
        else:
            self.parsers.append(empty_parser())

        self.module.end_pos = self.parsers[-1].module.end_pos

        # print(self.parsers[0].module.get_code())
        del code

    def _get_parser(self, code, parser_code, line_offset, nodes, no_docstr):
        h = hash(code)
        hashes = [n.hash for n in nodes]
        node = None
        try:
            index = hashes.index(h)
            if nodes[index].code != code:
                raise ValueError()
        except ValueError:
            tokenizer = FastTokenizer(parser_code, line_offset)
            p = Parser(parser_code, self.module_path, tokenizer=tokenizer,
                       top_module=self.module, no_docstr=no_docstr)
            p.module.parent = self.module
        else:
            if nodes[index] != self.current_node:
                offset = int(nodes[0] == self.current_node)
                self.current_node.old_children.pop(index - offset)
            node = nodes.pop(index)
            p = node.parser
            m = p.module
            m.line_offset += line_offset + 1 - m.start_pos[0]

        return p, node

    def reset_caches(self):
        self.module.reset_caches()
        if self.current_node is not None:
            self.current_node.reset_contents()


class FastTokenizer(object):
    """
    Breaks when certain conditions are met, i.e. a new function or class opens.
    """
    def __init__(self, source, line_offset=0):
        self.source = source
        self.gen = source_tokens(source, line_offset)
        self.closed = False

        # fast parser options
        self.current = self.previous = Token(None, '', (0, 0))
        self.in_flow = False
        self.new_indent = False
        self.parser_indent = self.old_parser_indent = 0
        self.is_decorator = False
        self.first_stmt = True

    def next(self):
        """ Python 2 Compatibility """
        return self.__next__()

    def __next__(self):
        if self.closed:
            raise common.MultiLevelStopIteration()

        current = next(self.gen)
        tok_type = current.type
        tok_str = current.string
        if tok_type == ENDMARKER:
            raise common.MultiLevelStopIteration()

        self.previous = self.current
        self.current = current

        # this is exactly the same check as in fast_parser, but this time with
        # tokenize and therefore precise.
        breaks = ['def', 'class', '@']

        def close():
            if not self.first_stmt:
                self.closed = True
                raise common.MultiLevelStopIteration()

        # ignore comments/ newlines
        if self.previous.type in (None, NEWLINE) and tok_type not in (COMMENT, NEWLINE):
            # print c, tok_name[c[0]]
            indent = current.start_pos[1]
            if indent < self.parser_indent:  # -> dedent
                self.parser_indent = indent
                self.new_indent = False
                if not self.in_flow or indent < self.old_parser_indent:
                    close()
                self.in_flow = False
            elif self.new_indent:
                self.parser_indent = indent
                self.new_indent = False

            if not self.in_flow:
                if tok_str in FLOWS or tok_str in breaks:
                    self.in_flow = tok_str in FLOWS
                    if not self.is_decorator and not self.in_flow:
                        close()
                    self.is_decorator = '@' == tok_str
                    if not self.is_decorator:
                        self.old_parser_indent = self.parser_indent
                        self.parser_indent += 1  # new scope: must be higher
                        self.new_indent = True

            if tok_str != '@':
                if self.first_stmt and not self.new_indent:
                    self.parser_indent = indent
                self.first_stmt = False
        return current

########NEW FILE########
__FILENAME__ = representation
"""
If you know what an abstract syntax tree (ast) is, you'll see that this module
is pretty much that. The classes represent syntax elements: ``Import``,
``Function``.

A very central class is ``Scope``. It is not used directly by the parser, but
inherited. It's used by ``Function``, ``Class``, ``Flow``, etc. A ``Scope`` may
have ``subscopes``, ``imports`` and ``statements``. The entire parser is based
on scopes, because they also stand for indentation.

One special thing:

``Array`` values are statements. But if you think about it, this makes sense.
``[1, 2+33]`` for example would be an Array with two ``Statement`` inside. This
is the easiest way to write a parser. The same behaviour applies to ``Param``,
which is being used in a function definition.

The easiest way to play with this module is to use :class:`parsing.Parser`.
:attr:`parsing.Parser.module` holds an instance of :class:`SubModule`:

>>> from jedi._compatibility import u
>>> from jedi.parser import Parser
>>> parser = Parser(u('import os'), 'example.py')
>>> submodule = parser.module
>>> submodule
<SubModule: example.py@1-1>

Any subclasses of :class:`Scope`, including :class:`SubModule` has
attribute :attr:`imports <Scope.imports>`.  This attribute has import
statements in this scope.  Check this out:

>>> submodule.imports
[<Import: import os @1,0>]

See also :attr:`Scope.subscopes` and :attr:`Scope.statements`.
"""
import os
import re
from inspect import cleandoc

from jedi._compatibility import (next, Python3Method, encoding, unicode,
                                 is_py3, u, literal_eval)
from jedi import common
from jedi import debug
from jedi import cache
from jedi.parser import tokenize


SCOPE_CONTENTS = 'asserts', 'subscopes', 'imports', 'statements', 'returns'


class GetCodeState(object):
    """A helper class for passing the state of get_code in a thread-safe
    manner."""
    __slots__ = ("last_pos",)

    def __init__(self):
        self.last_pos = (0, 0)


class DocstringMixin(object):
    __slots__ = ()

    def add_docstr(self, token):
        """ Clean up a docstring """
        self._doc_token = token

    @property
    def raw_doc(self):
        """ Returns a cleaned version of the docstring token. """
        try:
            # Returns a literal cleaned version of the ``Token``.
            return unicode(cleandoc(literal_eval(self._doc_token.string)))
        except AttributeError:
            return u('')


class Base(object):
    """
    This is just here to have an isinstance check, which is also used on
    evaluate classes. But since they have sometimes a special type of
    delegation, it is important for those classes to override this method.

    I know that there is a chance to do such things with __instancecheck__, but
    since Python 2.5 doesn't support it, I decided to do it this way.
    """
    __slots__ = ()

    def isinstance(self, *cls):
        return isinstance(self, cls)

    @property
    def newline(self):
        """Returns the newline type for the current code."""
        #TODO: we need newline detection
        return "\n"

    @property
    def whitespace(self):
        """Returns the whitespace type for the current code: tab or space."""
        #TODO: we need tab detection
        return " "

    @Python3Method
    def get_parent_until(self, classes=(), reverse=False,
                         include_current=True):
        """
        Searches the parent "chain" until the object is an instance of
        classes. If classes is empty return the last parent in the chain
        (is without a parent).
        """
        if type(classes) not in (tuple, list):
            classes = (classes,)
        scope = self if include_current else self.parent
        while scope.parent is not None:
            if classes and reverse != scope.isinstance(*classes):
                break
            scope = scope.parent
        return scope

    def is_callable(self):
        """
        By default parser objects are not callable, we make them callable by
        the ``evaluate.representation`` objects.
        """
        return False

    def space(self, from_pos, to_pos):
        """Return the space between two tokens"""
        linecount = to_pos[0] - from_pos[0]
        if linecount == 0:
            return self.whitespace * (to_pos[1] - from_pos[1])
        else:
            return "%s%s" % (
                self.newline * linecount,
                self.whitespace * to_pos[1],
            )


class Simple(Base):
    """
    The super class for Scope, Import, Name and Statement. Every object in
    the parser tree inherits from this class.
    """
    __slots__ = ('parent', '_sub_module', '_start_pos', 'use_as_parent',
                 '_end_pos')

    def __init__(self, module, start_pos, end_pos=(None, None)):
        """
        Initialize :class:`Simple`.

        :type      module: :class:`SubModule`
        :param     module: The module in which this Python object locates.
        :type   start_pos: 2-tuple of int
        :param  start_pos: Position (line, column) of the Statement.
        :type     end_pos: 2-tuple of int
        :param    end_pos: Same as `start_pos`.
        """
        self._sub_module = module
        self._start_pos = start_pos
        self._end_pos = end_pos

        self.parent = None
        # use this attribute if parent should be something else than self.
        self.use_as_parent = self

    @property
    def start_pos(self):
        return self._sub_module.line_offset + self._start_pos[0], \
            self._start_pos[1]

    @start_pos.setter
    def start_pos(self, value):
        self._start_pos = value

    @property
    def end_pos(self):
        if None in self._end_pos:
            return self._end_pos
        return self._sub_module.line_offset + self._end_pos[0], \
            self._end_pos[1]

    @end_pos.setter
    def end_pos(self, value):
        self._end_pos = value

    def __repr__(self):
        code = self.get_code().replace('\n', ' ')
        if not is_py3:
            code = code.encode(encoding, 'replace')
        return "<%s: %s@%s,%s>" % \
            (type(self).__name__, code, self.start_pos[0], self.start_pos[1])


class IsScope(Base):
    __slots__ = ()


class Scope(Simple, IsScope, DocstringMixin):
    """
    Super class for the parser tree, which represents the state of a python
    text file.
    A Scope manages and owns its subscopes, which are classes and functions, as
    well as variables and imports. It is used to access the structure of python
    files.

    :param start_pos: The position (line and column) of the scope.
    :type start_pos: tuple(int, int)
    """
    __slots__ = ('subscopes', 'imports', 'statements', '_doc_token', 'asserts',
                 'returns', 'is_generator')

    def __init__(self, module, start_pos):
        super(Scope, self).__init__(module, start_pos)
        self.subscopes = []
        self.imports = []
        self.statements = []
        self._doc_token = None
        self.asserts = []
        # Needed here for fast_parser, because the fast_parser splits and
        # returns will be in "normal" modules.
        self.returns = []
        self.is_generator = False

    def add_scope(self, sub, decorators):
        sub.parent = self.use_as_parent
        sub.decorators = decorators
        for d in decorators:
            # the parent is the same, because the decorator has not the scope
            # of the function
            d.parent = self.use_as_parent
        self.subscopes.append(sub)
        return sub

    def add_statement(self, stmt):
        """
        Used to add a Statement or a Scope.
        A statement would be a normal command (Statement) or a Scope (Flow).
        """
        stmt.parent = self.use_as_parent
        self.statements.append(stmt)
        return stmt

    def add_import(self, imp):
        self.imports.append(imp)
        imp.parent = self.use_as_parent

    def get_imports(self):
        """ Gets also the imports within flow statements """
        i = [] + self.imports
        for s in self.statements:
            if isinstance(s, Scope):
                i += s.get_imports()
        return i

    def get_code2(self, state=GetCodeState()):
        string = []
        return "".join(string)

    def get_code(self, first_indent=False, indention='    '):
        """
        :return: Returns the code of the current scope.
        :rtype: str
        """
        string = ""
        if self._doc_token is not None:
            string += '"""' + self.raw_doc + '"""\n'

        objs = self.subscopes + self.imports + self.statements + self.returns
        for obj in sorted(objs, key=lambda x: x.start_pos):
            if isinstance(obj, Scope):
                string += obj.get_code(first_indent=True, indention=indention)
            else:
                if obj in self.returns and not isinstance(self, Lambda):
                    string += 'yield ' if self.is_generator else 'return '
                string += obj.get_code()

        if first_indent:
            string = common.indent_block(string, indention=indention)
        return string

    @Python3Method
    def get_defined_names(self):
        """
        Get all defined names in this scope.

        >>> from jedi._compatibility import u
        >>> from jedi.parser import Parser
        >>> parser = Parser(u('''
        ... a = x
        ... b = y
        ... b.c = z
        ... '''))
        >>> parser.module.get_defined_names()
        [<Name: a@2,0>, <Name: b@3,0>, <Name: b.c@4,0>]
        """
        n = []
        for stmt in self.statements:
            try:
                n += stmt.get_defined_names(True)
            except TypeError:
                n += stmt.get_defined_names()

        # function and class names
        n += [s.name for s in self.subscopes]

        for i in self.imports:
            if not i.star:
                n += i.get_defined_names()
        return n

    @Python3Method
    def get_statement_for_position(self, pos, include_imports=False):
        checks = self.statements + self.asserts
        if include_imports:
            checks += self.imports
        if self.isinstance(Function):
            checks += self.params + self.decorators
            checks += [r for r in self.returns if r is not None]
        if self.isinstance(Flow):
            checks += self.inputs
        if self.isinstance(ForFlow) and self.set_stmt is not None:
            checks.append(self.set_stmt)

        for s in checks:
            if isinstance(s, Flow):
                p = s.get_statement_for_position(pos, include_imports)
                while s.next and not p:
                    s = s.next
                    p = s.get_statement_for_position(pos, include_imports)
                if p:
                    return p
            elif s.start_pos <= pos <= s.end_pos:
                return s

        for s in self.subscopes:
            if s.start_pos <= pos <= s.end_pos:
                p = s.get_statement_for_position(pos, include_imports)
                if p:
                    return p

    def __repr__(self):
        try:
            name = self.path
        except AttributeError:
            try:
                name = self.name
            except AttributeError:
                name = self.command

        return "<%s: %s@%s-%s>" % (type(self).__name__, name,
                                   self.start_pos[0], self.end_pos[0])


class Module(IsScope):
    """
    For isinstance checks. fast_parser.Module also inherits from this.
    """


class SubModule(Scope, Module):
    """
    The top scope, which is always a module.
    Depending on the underlying parser this may be a full module or just a part
    of a module.
    """
    __slots__ = ('path', 'global_vars', 'used_names', 'temp_used_names',
                 'line_offset', 'use_as_parent')

    def __init__(self, path, start_pos=(1, 0), top_module=None):
        """
        Initialize :class:`SubModule`.

        :type path: str
        :arg  path: File path to this module.

        .. todo:: Document `top_module`.
        """
        super(SubModule, self).__init__(self, start_pos)
        self.path = path
        self.global_vars = []
        self.used_names = {}
        self.temp_used_names = []
        # this may be changed depending on fast_parser
        self.line_offset = 0

        self.use_as_parent = top_module or self

    def add_global(self, name):
        """
        Global means in these context a function (subscope) which has a global
        statement.
        This is only relevant for the top scope.

        :param name: The name of the global.
        :type name: Name
        """
        # set no parent here, because globals are not defined in this scope.
        self.global_vars.append(name)

    def get_defined_names(self):
        n = super(SubModule, self).get_defined_names()
        n += self.global_vars
        return n

    @property
    @cache.underscore_memoization
    def name(self):
        """ This is used for the goto functions. """
        if self.path is None:
            string = ''  # no path -> empty name
        else:
            sep = (re.escape(os.path.sep),) * 2
            r = re.search(r'([^%s]*?)(%s__init__)?(\.py|\.so)?$' % sep, self.path)
            # remove PEP 3149 names
            string = re.sub('\.[a-z]+-\d{2}[mud]{0,3}$', '', r.group(1))
        # positions are not real therefore choose (0, 0)
        names = [(string, (0, 0))]
        return Name(self, names, (0, 0), (0, 0), self.use_as_parent)

    @property
    def has_explicit_absolute_import(self):
        """
        Checks if imports in this module are explicitly absolute, i.e. there
        is a ``__future__`` import.
        """
        for imp in self.imports:
            if imp.from_ns is None or imp.namespace is None:
                continue

            namespace, feature = imp.from_ns.names[0], imp.namespace.names[0]
            if unicode(namespace) == "__future__" and unicode(feature) == "absolute_import":
                return True

        return False


class Class(Scope):
    """
    Used to store the parsed contents of a python class.

    :param name: The Class name.
    :type name: str
    :param supers: The super classes of a Class.
    :type supers: list
    :param start_pos: The start position (line, column) of the class.
    :type start_pos: tuple(int, int)
    """
    __slots__ = ('name', 'supers', 'decorators')

    def __init__(self, module, name, supers, start_pos):
        super(Class, self).__init__(module, start_pos)
        self.name = name
        name.parent = self.use_as_parent
        self.supers = supers
        for s in self.supers:
            s.parent = self.use_as_parent
        self.decorators = []

    def get_code(self, first_indent=False, indention='    '):
        string = "\n".join('@' + stmt.get_code() for stmt in self.decorators)
        string += 'class %s' % (self.name)
        if len(self.supers) > 0:
            sup = ', '.join(stmt.get_code(False) for stmt in self.supers)
            string += '(%s)' % sup
        string += ':\n'
        string += super(Class, self).get_code(True, indention)
        return string

    @property
    def doc(self):
        """
        Return a document string including call signature of __init__.
        """
        docstr = ""
        if self._doc_token is not None:
            docstr = self.raw_doc
        for sub in self.subscopes:
            if unicode(sub.name.names[-1]) == '__init__':
                return '%s\n\n%s' % (
                    sub.get_call_signature(funcname=self.name.names[-1]), docstr)
        return docstr


class Function(Scope):
    """
    Used to store the parsed contents of a python function.

    :param name: The Function name.
    :type name: str
    :param params: The parameters (Statement) of a Function.
    :type params: list
    :param start_pos: The start position (line, column) the Function.
    :type start_pos: tuple(int, int)
    """
    __slots__ = ('name', 'params', 'decorators', 'listeners', 'annotation')

    def __init__(self, module, name, params, start_pos, annotation):
        super(Function, self).__init__(module, start_pos)
        self.name = name
        if name is not None:
            name.parent = self.use_as_parent
        self.params = params
        for p in params:
            p.parent = self.use_as_parent
            p.parent_function = self.use_as_parent
        self.decorators = []
        self.listeners = set()  # not used here, but in evaluation.

        if annotation is not None:
            annotation.parent = self.use_as_parent
        self.annotation = annotation

    def get_code(self, first_indent=False, indention='    '):
        string = "\n".join('@' + stmt.get_code() for stmt in self.decorators)
        params = ', '.join([stmt.get_code(False) for stmt in self.params])
        string += "def %s(%s):\n" % (self.name, params)
        string += super(Function, self).get_code(True, indention)
        return string

    def get_defined_names(self):
        n = super(Function, self).get_defined_names()
        for p in self.params:
            try:
                n.append(p.get_name())
            except IndexError:
                debug.warning("multiple names in param %s", n)
        return n

    def get_call_signature(self, width=72, funcname=None):
        """
        Generate call signature of this function.

        :param width: Fold lines if a line is longer than this value.
        :type width: int
        :arg funcname: Override function name when given.
        :type funcname: str

        :rtype: str
        """
        l = unicode(funcname or self.name.names[-1]) + '('
        lines = []
        for (i, p) in enumerate(self.params):
            code = p.get_code(False)
            if i != len(self.params) - 1:
                code += ', '
            if len(l + code) > width:
                lines.append(l[:-1] if l[-1] == ' ' else l)
                l = code
            else:
                l += code
        if l:
            lines.append(l)
        lines[-1] += ')'
        return '\n'.join(lines)

    @property
    def doc(self):
        """ Return a document string including call signature. """
        docstr = ""
        if self._doc_token is not None:
            docstr = self.raw_doc
        return '%s\n\n%s' % (self.get_call_signature(), docstr)


class Lambda(Function):
    def __init__(self, module, params, start_pos, parent):
        super(Lambda, self).__init__(module, None, params, start_pos, None)
        self.parent = parent

    def get_code(self, first_indent=False, indention='    '):
        params = ','.join([stmt.get_code() for stmt in self.params])
        string = "lambda %s: " % params
        return string + super(Function, self).get_code(indention=indention)

    def __repr__(self):
        return "<%s @%s (%s-%s)>" % (type(self).__name__, self.start_pos[0],
                                     self.start_pos[1], self.end_pos[1])


class Flow(Scope):
    """
    Used to describe programming structure - flow statements,
    which indent code, but are not classes or functions:

    - for
    - while
    - if
    - try
    - with

    Therefore statements like else, except and finally are also here,
    they are now saved in the root flow elements, but in the next variable.

    :param command: The flow command, if, while, else, etc.
    :type command: str
    :param inputs: The initializations of a flow -> while 'statement'.
    :type inputs: list(Statement)
    :param start_pos: Position (line, column) of the Flow statement.
    :type start_pos: tuple(int, int)
    """
    __slots__ = ('next', 'command', '_parent', 'inputs', 'set_vars')

    def __init__(self, module, command, inputs, start_pos):
        self.next = None
        self.command = command
        super(Flow, self).__init__(module, start_pos)
        self._parent = None
        # These have to be statements, because of with, which takes multiple.
        self.inputs = inputs
        for s in inputs:
            s.parent = self.use_as_parent
        self.set_vars = []

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value
        try:
            self.next.parent = value
        except AttributeError:
            return

    def get_code(self, first_indent=False, indention='    '):
        stmts = []
        for s in self.inputs:
            stmts.append(s.get_code(new_line=False))
        stmt = ', '.join(stmts)
        string = "%s %s:\n" % (self.command, stmt)
        string += super(Flow, self).get_code(True, indention)
        if self.next:
            string += self.next.get_code()
        return string

    def get_defined_names(self, is_internal_call=False):
        """
        Get the names for the flow. This includes also a call to the super
        class.

        :param is_internal_call: defines an option for internal files to crawl
            through this class. Normally it will just call its superiors, to
            generate the output.
        """
        if is_internal_call:
            n = list(self.set_vars)
            for s in self.inputs:
                n += s.get_defined_names()
            if self.next:
                n += self.next.get_defined_names(is_internal_call)
            n += super(Flow, self).get_defined_names()
            return n
        else:
            return self.get_parent_until((Class, Function)).get_defined_names()

    def get_imports(self):
        i = super(Flow, self).get_imports()
        if self.next:
            i += self.next.get_imports()
        return i

    def set_next(self, next):
        """Set the next element in the flow, those are else, except, etc."""
        if self.next:
            return self.next.set_next(next)
        else:
            self.next = next
            self.next.parent = self.parent
            return next


class ForFlow(Flow):
    """
    Used for the for loop, because there are two statement parts.
    """
    def __init__(self, module, inputs, start_pos, set_stmt, is_list_comp=False):
        super(ForFlow, self).__init__(module, 'for', inputs, start_pos)

        self.set_stmt = set_stmt
        self.is_list_comp = is_list_comp

        if set_stmt is not None:
            set_stmt.parent = self.use_as_parent
            self.set_vars = set_stmt.get_defined_names()

            for s in self.set_vars:
                s.parent.parent = self.use_as_parent
                s.parent = self.use_as_parent

    def get_code(self, first_indent=False, indention=" " * 4):
        vars = ",".join(x.get_code() for x in self.set_vars)
        stmts = []
        for s in self.inputs:
            stmts.append(s.get_code(new_line=False))
        stmt = ', '.join(stmts)
        s = "for %s in %s:\n" % (vars, stmt)
        return s + super(Flow, self).get_code(True, indention)


class Import(Simple):
    """
    Stores the imports of any Scopes.

    :param start_pos: Position (line, column) of the Import.
    :type start_pos: tuple(int, int)
    :param namespace: The import, can be empty if a star is given
    :type namespace: Name
    :param alias: The alias of a namespace(valid in the current namespace).
    :type alias: Name
    :param from_ns: Like the namespace, can be equally used.
    :type from_ns: Name
    :param star: If a star is used -> from time import *.
    :type star: bool
    :param defunct: An Import is valid or not.
    :type defunct: bool
    """
    def __init__(self, module, start_pos, end_pos, namespace, alias=None,
                 from_ns=None, star=False, relative_count=0, defunct=False):
        super(Import, self).__init__(module, start_pos, end_pos)

        self.namespace = namespace
        self.alias = alias
        self.from_ns = from_ns
        for n in namespace, alias, from_ns:
            if n:
                n.parent = self.use_as_parent

        self.star = star
        self.relative_count = relative_count
        self.defunct = defunct

    def get_code(self, new_line=True):
        # in case one of the names is None
        alias = self.alias or ''
        namespace = self.namespace or ''
        from_ns = self.from_ns or ''

        if self.alias:
            ns_str = "%s as %s" % (namespace, alias)
        else:
            ns_str = unicode(namespace)

        nl = '\n' if new_line else ''
        if self.from_ns or self.relative_count:
            if self.star:
                ns_str = '*'
            dots = '.' * self.relative_count
            return "from %s%s import %s%s" % (dots, from_ns, ns_str, nl)
        else:
            return "import %s%s" % (ns_str, nl)

    def get_defined_names(self):
        if self.defunct:
            return []
        if self.star:
            return [self]
        if self.alias:
            return [self.alias]
        if len(self.namespace) > 1:
            o = self.namespace
            n = Name(self._sub_module, [(unicode(o.names[0]), o.start_pos)],
                     o.start_pos, o.end_pos, parent=o.parent)
            return [n]
        else:
            return [self.namespace]

    def get_all_import_names(self):
        n = []
        if self.from_ns:
            n.append(self.from_ns)
        if self.namespace:
            n.append(self.namespace)
        if self.alias:
            n.append(self.alias)
        return n


class KeywordStatement(Base):
    """
    For the following statements: `assert`, `del`, `global`, `nonlocal`,
    `raise`, `return`, `yield`, `pass`, `continue`, `break`, `return`, `yield`.
    """
    __slots__ = ('name', 'start_pos', '_stmt', 'parent')

    def __init__(self, name, start_pos, parent, stmt=None):
        self.name = name
        self.start_pos = start_pos
        self._stmt = stmt
        self.parent = parent

        if stmt is not None:
            stmt.parent = self

    def get_code(self):
        if self._stmt is None:
            return "%s\n" % self.name
        else:
            return '%s %s\n' % (self.name, self._stmt)

    def get_defined_names(self):
        return []

    @property
    def end_pos(self):
        try:
            return self._stmt.end_pos
        except AttributeError:
            return self.start_pos[0], self.start_pos[1] + len(self.name)


class Statement(Simple, DocstringMixin):
    """
    This is the class for all the possible statements. Which means, this class
    stores pretty much all the Python code, except functions, classes, imports,
    and flow functions like if, for, etc.

    :type  token_list: list
    :param token_list:
        List of tokens or names.  Each element is either an instance
        of :class:`Name` or a tuple of token type value (e.g.,
        :data:`tokenize.NUMBER`), token string (e.g., ``'='``), and
        start position (e.g., ``(1, 0)``).
    :type   start_pos: 2-tuple of int
    :param  start_pos: Position (line, column) of the Statement.
    """
    __slots__ = ('_token_list', '_set_vars', 'as_names', '_expression_list',
                 '_assignment_details', '_names_are_set_vars', '_doc_token')

    def __init__(self, module, token_list, start_pos, end_pos, parent=None,
                 as_names=(), names_are_set_vars=False, set_name_parents=True):
        super(Statement, self).__init__(module, start_pos, end_pos)
        self._token_list = token_list
        self._names_are_set_vars = names_are_set_vars
        if set_name_parents:
            for t in token_list:
                if isinstance(t, Name):
                    t.parent = self.use_as_parent
            for n in as_names:
                n.parent = self.use_as_parent
        self.parent = parent
        self._doc_token = None
        self._set_vars = None
        self.as_names = list(as_names)

        # cache
        self._assignment_details = []

    @property
    def end_pos(self):
        return self._token_list[-1].end_pos

    def get_code(self, new_line=True):
        def assemble(command_list, assignment=None):
            pieces = [c.get_code() if isinstance(c, Simple) else c.string if
isinstance(c, (tokenize.Token, Operator)) else unicode(c)
                      for c in command_list]
            if assignment is None:
                return ''.join(pieces)
            return '%s %s ' % (''.join(pieces), assignment)

        code = ''.join(assemble(*a) for a in self.assignment_details)
        code += assemble(self.expression_list())
        if self._doc_token:
            code += '\n"""%s"""' % self.raw_doc

        if new_line:
            return code + '\n'
        else:
            return code

    def get_defined_names(self):
        """ Get the names for the statement. """
        if self._set_vars is None:

            def search_calls(calls):
                for call in calls:
                    if isinstance(call, Array):
                        for stmt in call:
                            search_calls(stmt.expression_list())
                    elif isinstance(call, Call):
                        c = call
                        # Check if there's an execution in it, if so this is
                        # not a set_var.
                        is_execution = False
                        while c:
                            if Array.is_type(c.execution, Array.TUPLE):
                                is_execution = True
                            c = c.next
                        if is_execution:
                            continue
                        self._set_vars.append(call.name)

            self._set_vars = []
            for calls, operation in self.assignment_details:
                search_calls(calls)

            if not self.assignment_details and self._names_are_set_vars:
                # In the case of Param, it's also a defining name without ``=``
                search_calls(self.expression_list())
        return self._set_vars + self.as_names

    def is_global(self):
        p = self.parent
        return isinstance(p, KeywordStatement) and p.name == 'global'

    @property
    def assignment_details(self):
        """
        Returns an array of tuples of the elements before the assignment.

        For example the following code::

            x = (y, z) = 2, ''

        would result in ``[(Name(x), '='), (Array([Name(y), Name(z)]), '=')]``.
        """
        # parse statement which creates the assignment details.
        self.expression_list()
        return self._assignment_details

    @cache.underscore_memoization
    def expression_list(self):
        """
        Parse a statement.

        This is not done in the main parser, because it might be slow and
        most of the statements won't need this data anyway. This is something
        'like' a lazy execution.

        This is not really nice written, sorry for that. If you plan to replace
        it and make it nicer, that would be cool :-)
        """
        def is_assignment(tok):
            return isinstance(tok, Operator) and tok.string.endswith('=') \
                and not tok.string in ('>=', '<=', '==', '!=')

        def parse_array(token_iterator, array_type, start_pos, add_el=None):
            arr = Array(self._sub_module, start_pos, array_type, self)
            if add_el is not None:
                arr.add_statement(add_el)
                old_stmt = add_el

            maybe_dict = array_type == Array.SET
            break_tok = None
            is_array = None
            while True:
                stmt, break_tok = parse_stmt(token_iterator, maybe_dict,
                                             break_on_assignment=bool(add_el))
                if stmt is None:
                    break
                else:
                    if break_tok == ',':
                        is_array = True
                    arr.add_statement(stmt, is_key=maybe_dict and break_tok == ':')
                    if break_tok in closing_brackets \
                            or is_assignment(break_tok):
                        break
                old_stmt = stmt
            if arr.type == Array.TUPLE and len(arr) == 1 and not is_array:
                arr.type = Array.NOARRAY
            if not arr.values and maybe_dict:
                # this is a really special case - empty brackets {} are
                # always dictionaries and not sets.
                arr.type = Array.DICT

            arr.end_pos = (break_tok or stmt or old_stmt).end_pos
            return arr, break_tok

        def parse_stmt(token_iterator, maybe_dict=False, added_breaks=(),
                       break_on_assignment=False, stmt_class=Statement,
                       allow_comma=False):
            token_list = []
            level = 0
            first = True
            end_pos = None, None
            tok = None
            for tok in token_iterator:
                end_pos = tok.end_pos
                if first:
                    start_pos = tok.start_pos
                    first = False

                if isinstance(tok, Base):
                    # the token is a Name, which has already been parsed
                    if isinstance(tok, ListComprehension):
                        # it's not possible to set it earlier
                        tok.parent = self
                    elif tok == 'lambda':
                        lambd, tok = parse_lambda(token_iterator)
                        if lambd is not None:
                            token_list.append(lambd)
                    elif tok == 'for':
                        list_comp, tok = parse_list_comp(token_iterator, token_list,
                                                         start_pos, tok.end_pos)
                        if list_comp is not None:
                            token_list = [list_comp]

                    if tok in closing_brackets:
                        level -= 1
                    elif tok in brackets.keys():
                        level += 1

                    if level == -1 or level == 0 and (
                            tok == ',' and not allow_comma
                            or tok in added_breaks
                            or maybe_dict and tok == ':'
                            or is_assignment(tok) and break_on_assignment):
                        end_pos = end_pos[0], end_pos[1] - 1
                        break

                token_list.append(tok)

            if not token_list:
                return None, tok

            statement = stmt_class(self._sub_module, token_list, start_pos,
                                   end_pos, self.parent, set_name_parents=False)
            return statement, tok

        def parse_lambda(token_iterator):
            params = []
            start_pos = self.start_pos
            while True:
                param, tok = parse_stmt(token_iterator, added_breaks=[':'],
                                        stmt_class=Param)
                if param is None:
                    break
                params.append(param)
                if tok == ':':
                    break
            if tok != ':':
                return None, tok

            # Since Lambda is a Function scope, it needs Scope parents.
            parent = self.get_parent_until(IsScope)
            lambd = Lambda(self._sub_module, params, start_pos, parent)

            ret, tok = parse_stmt(token_iterator)
            if ret is not None:
                ret.parent = lambd
                lambd.returns.append(ret)
            lambd.end_pos = self.end_pos
            return lambd, tok

        def parse_list_comp(token_iterator, token_list, start_pos, end_pos):
            def parse_stmt_or_arr(token_iterator, added_breaks=(),
                                  names_are_set_vars=False):
                stmt, tok = parse_stmt(token_iterator, allow_comma=True,
                                       added_breaks=added_breaks)

                if stmt is not None:
                    for t in stmt._token_list:
                        if isinstance(t, Name):
                            t.parent = stmt
                    stmt._names_are_set_vars = names_are_set_vars
                return stmt, tok

            st = Statement(self._sub_module, token_list, start_pos,
                           end_pos, set_name_parents=False)

            middle, tok = parse_stmt_or_arr(token_iterator, ['in'], True)
            if tok != 'in' or middle is None:
                debug.warning('list comprehension middle %s@%s', tok, start_pos)
                return None, tok

            in_clause, tok = parse_stmt_or_arr(token_iterator)
            if in_clause is None:
                debug.warning('list comprehension in @%s', start_pos)
                return None, tok

            return ListComprehension(st, middle, in_clause, self), tok

        # initializations
        result = []
        is_chain = False
        brackets = {'(': Array.TUPLE, '[': Array.LIST, '{': Array.SET}
        closing_brackets = ')', '}', ']'

        token_iterator = iter(self._token_list)
        for tok in token_iterator:
            if isinstance(tok, tokenize.Token):
                token_type = tok.type
                tok_str = tok.string
                if tok_str == 'as':  # just ignore as, because it sets values
                    next(token_iterator, None)
                    continue
            else:
                # the token is a Name, which has already been parsed
                tok_str = tok
                token_type = None

                if is_assignment(tok):
                    # This means, there is an assignment here.
                    # Add assignments, which can be more than one
                    self._assignment_details.append((result, tok.string))
                    result = []
                    is_chain = False
                    continue

            if tok_str == 'lambda':
                lambd, tok_str = parse_lambda(token_iterator)
                if lambd is not None:
                    result.append(lambd)
                if tok_str not in (')', ','):
                    continue

            is_literal = token_type in (tokenize.STRING, tokenize.NUMBER)
            if isinstance(tok_str, Name) or is_literal:
                cls = Literal if is_literal else Call

                call = cls(self._sub_module, tok_str, tok.start_pos, tok.end_pos, self)
                if is_chain:
                    result[-1].set_next(call)
                else:
                    result.append(call)
                is_chain = False
            elif tok_str in brackets.keys():
                arr, is_ass = parse_array(
                    token_iterator, brackets[tok.string], tok.start_pos
                )
                if result and isinstance(result[-1], StatementElement):
                    result[-1].set_execution(arr)
                else:
                    arr.parent = self
                    result.append(arr)
            elif tok_str == '.':
                if result and isinstance(result[-1], StatementElement):
                    is_chain = True
            elif tok_str == ',' and result:  # implies a tuple
                # expression is now an array not a statement anymore
                stmt = Statement(self._sub_module, result, result[0].start_pos,
                                 tok.end_pos, self.parent, set_name_parents=False)
                stmt._expression_list = result
                arr, break_tok = parse_array(token_iterator, Array.TUPLE,
                                             stmt.start_pos, stmt)
                result = [arr]
                if is_assignment(break_tok):
                    self._assignment_details.append((result, break_tok))
                    result = []
                    is_chain = False
            else:
                # comments, strange tokens (like */**), error tokens to
                # reproduce the string correctly.
                is_chain = False
                result.append(tok)
        return result

    def set_expression_list(self, lst):
        """It's necessary for some "hacks" to change the expression_list."""
        self._expression_list = lst


class Param(Statement):
    """
    The class which shows definitions of params of classes and functions.
    But this is not to define function calls.
    """
    __slots__ = ('position_nr', 'is_generated', 'annotation_stmt',
                 'parent_function')

    def __init__(self, *args, **kwargs):
        kwargs.pop('names_are_set_vars', None)
        super(Param, self).__init__(*args, names_are_set_vars=True, **kwargs)

        # this is defined by the parser later on, not at the initialization
        # it is the position in the call (first argument, second...)
        self.position_nr = None
        self.is_generated = False
        self.annotation_stmt = None
        self.parent_function = None

    def add_annotation(self, annotation_stmt):
        annotation_stmt.parent = self.use_as_parent
        self.annotation_stmt = annotation_stmt

    def get_name(self):
        """ get the name of the param """
        n = self.get_defined_names()
        if len(n) > 1:
            debug.warning("Multiple param names (%s).", n)
        return n[0]

    @property
    def stars(self):
        exp = self.expression_list()
        if exp and isinstance(exp[0], Operator):
            return exp[0].string.count('*')
        return 0


class StatementElement(Simple):
    __slots__ = ('parent', 'next', 'execution')

    def __init__(self, module, start_pos, end_pos, parent):
        super(StatementElement, self).__init__(module, start_pos, end_pos)

        # parent is not the oposite of next. The parent of c: a = [b.c] would
        # be an array.
        self.parent = parent
        self.next = None
        self.execution = None

    def set_next(self, call):
        """ Adds another part of the statement"""
        call.parent = self
        if self.next is not None:
            self.next.set_next(call)
        else:
            self.next = call

    def set_execution(self, call):
        """
        An execution is nothing else than brackets, with params in them, which
        shows access on the internals of this name.
        """
        call.parent = self
        if self.next is not None:
            self.next.set_execution(call)
        elif self.execution is not None:
            self.execution.set_execution(call)
        else:
            self.execution = call

    def generate_call_path(self):
        """ Helps to get the order in which statements are executed. """
        try:
            for name_part in self.name.names:
                yield name_part
        except AttributeError:
            yield self
        if self.execution is not None:
            for y in self.execution.generate_call_path():
                yield y
        if self.next is not None:
            for y in self.next.generate_call_path():
                yield y

    def get_code(self):
        s = ''
        if self.execution is not None:
            s += self.execution.get_code()
        if self.next is not None:
            s += '.' + self.next.get_code()
        return s


class Call(StatementElement):
    __slots__ = ('name',)

    def __init__(self, module, name, start_pos, end_pos, parent=None):
        super(Call, self).__init__(module, start_pos, end_pos, parent)
        self.name = name

    def get_code(self):
        return self.name.get_code() + super(Call, self).get_code()

    def __repr__(self):
        return "<%s: %s>" % (type(self).__name__, self.name)


class Literal(StatementElement):
    __slots__ = ('literal', 'value')

    def __init__(self, module, literal, start_pos, end_pos, parent=None):
        super(Literal, self).__init__(module, start_pos, end_pos, parent)
        self.literal = literal
        self.value = literal_eval(literal)

    def get_code(self):
        return self.literal + super(Literal, self).get_code()

    def __repr__(self):
        if is_py3:
            s = self.literal
        else:
            s = self.literal.encode('ascii', 'replace')
        return "<%s: %s>" % (type(self).__name__, s)


class Array(StatementElement):
    """
    Describes the different python types for an array, but also empty
    statements. In the Python syntax definitions this type is named 'atom'.
    http://docs.python.org/py3k/reference/grammar.html
    Array saves sub-arrays as well as normal operators and calls to methods.

    :param array_type: The type of an array, which can be one of the constants
        below.
    :type array_type: int
    """
    __slots__ = ('type', 'end_pos', 'values', 'keys')
    NOARRAY = None  # just brackets, like `1 * (3 + 2)`
    TUPLE = 'tuple'
    LIST = 'list'
    DICT = 'dict'
    SET = 'set'

    def __init__(self, module, start_pos, arr_type=NOARRAY, parent=None):
        super(Array, self).__init__(module, start_pos, (None, None), parent)
        self.end_pos = None, None
        self.type = arr_type
        self.values = []
        self.keys = []

    def add_statement(self, statement, is_key=False):
        """Just add a new statement"""
        statement.parent = self
        if is_key:
            self.type = self.DICT
            self.keys.append(statement)
        else:
            self.values.append(statement)

    @staticmethod
    def is_type(instance, *types):
        """
        This is not only used for calls on the actual object, but for
        ducktyping, to invoke this function with anything as `self`.
        """
        try:
            if instance.type in types:
                return True
        except AttributeError:
            pass
        return False

    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        if self.type == self.DICT:
            raise TypeError('no dicts allowed')
        return self.values[key]

    def __iter__(self):
        if self.type == self.DICT:
            raise TypeError('no dicts allowed')
        return iter(self.values)

    def items(self):
        if self.type != self.DICT:
            raise TypeError('only dicts allowed')
        return zip(self.keys, self.values)

    def get_code(self):
        map = {
            self.NOARRAY: '(%s)',
            self.TUPLE: '(%s)',
            self.LIST: '[%s]',
            self.DICT: '{%s}',
            self.SET: '{%s}'
        }
        inner = []
        for i, stmt in enumerate(self.values):
            s = ''
            with common.ignored(IndexError):
                key = self.keys[i]
                s += key.get_code(new_line=False) + ': '
            s += stmt.get_code(new_line=False)
            inner.append(s)
        add = ',' if self.type == self.TUPLE and len(self) == 1 else ''
        s = map[self.type] % (', '.join(inner) + add)
        return s + super(Array, self).get_code()

    def __repr__(self):
        if self.type == self.NOARRAY:
            typ = 'noarray'
        else:
            typ = self.type
        return "<%s: %s%s>" % (type(self).__name__, typ, self.values)


class NamePart(object):
    """
    A string. Sometimes it is important to know if the string belongs to a name
    or not.
    """
    # Unfortunately there's no way to use slots for str (non-zero __itemsize__)
    # -> http://utcc.utoronto.ca/~cks/space/blog/python/IntSlotsPython3k
    # Therefore don't subclass `str`.
    __slots__ = ('parent', '_string', '_line', '_column')

    def __init__(self, string, parent, start_pos):
        self._string = string
        self.parent = parent
        self._line = start_pos[0]
        self._column = start_pos[1]

    def __str__(self):
        return self._string

    def __unicode__(self):
        return self._string

    def __repr__(self):
        return "<%s: %s>" % (type(self).__name__, self._string)

    def get_code(self):
        return self._string

    def get_parent_until(self, *args, **kwargs):
        return self.parent.get_parent_until(*args, **kwargs)

    @property
    def start_pos(self):
        offset = self.parent._sub_module.line_offset
        return offset + self._line, self._column

    @property
    def end_pos(self):
        return self.start_pos[0], self.start_pos[1] + len(self._string)


class Name(Simple):
    """
    Used to define names in python.
    Which means the whole namespace/class/function stuff.
    So a name like "module.class.function"
    would result in an array of [module, class, function]
    """
    __slots__ = ('names', '_get_code')

    def __init__(self, module, names, start_pos, end_pos, parent=None):
        super(Name, self).__init__(module, start_pos, end_pos)
        # Cache get_code, because it's used quite often for comparisons
        # (seen by using the profiler).
        self._get_code = ".".join(n[0] for n in names)

        names = tuple(NamePart(n[0], self, n[1]) for n in names)
        self.names = names
        if parent is not None:
            self.parent = parent

    def get_code(self):
        """ Returns the names in a full string format """
        return self._get_code

    @property
    def end_pos(self):
        return self.names[-1].end_pos

    @property
    def docstr(self):
        """Return attribute docstring (PEP 257) if exists."""
        return self.parent.docstr

    def __str__(self):
        return self.get_code()

    def __len__(self):
        return len(self.names)


class ListComprehension(Base):
    """ Helper class for list comprehensions """
    def __init__(self, stmt, middle, input, parent):
        self.stmt = stmt
        self.middle = middle
        self.input = input
        for s in stmt, middle, input:
            s.parent = self
        self.parent = parent

    def get_parent_until(self, *args, **kwargs):
        return Simple.get_parent_until(self, *args, **kwargs)

    @property
    def start_pos(self):
        return self.stmt.start_pos

    @property
    def end_pos(self):
        return self.stmt.end_pos

    def __repr__(self):
        return "<%s: %s>" % (type(self).__name__, self.get_code())

    def get_code(self):
        statements = self.stmt, self.middle, self.input
        code = [s.get_code().replace('\n', '') for s in statements]
        return "%s for %s in %s" % tuple(code)


class Operator(Base):
    __slots__ = ('string', '_line', '_column')

    def __init__(self, string, start_pos):
        # TODO needs module param
        self.string = string
        self._line = start_pos[0]
        self._column = start_pos[1]

    def __repr__(self):
        return "<%s: `%s`>" % (type(self).__name__, self.string)

    @property
    def start_pos(self):
        return self._line, self._column

    @property
    def end_pos(self):
        return self._line, self._column + len(self.string)

    def __eq__(self, other):
        """Make comparisons easy. Improves the readability of the parser."""
        return self.string == other

    def __ne__(self, other):
        """Python 2 compatibility."""
        return self.string != other

    def __hash__(self):
        return hash(self.string)

########NEW FILE########
__FILENAME__ = tokenize
# -*- coding: utf-8 -*-
"""
This tokenizer has been copied from the ``tokenize.py`` standard library
tokenizer. The reason was simple: The standanrd library  tokenizer fails
if the indentation is not right. The fast parser of jedi however requires
"wrong" indentation.

Basically this is a stripped down version of the standard library module, so
you can read the documentation there. Additionally we included some speed and
memory optimizations, here.
"""
from __future__ import absolute_import

import string
import re
from io import StringIO
from token import (tok_name, N_TOKENS, ENDMARKER, STRING, NUMBER, NAME, OP,
                   ERRORTOKEN, NEWLINE)

from jedi._compatibility import u

cookie_re = re.compile("coding[:=]\s*([-\w.]+)")


# From here on we have custom stuff (everything before was originally Python
# internal code).
FLOWS = ['if', 'else', 'elif', 'while', 'with', 'try', 'except', 'finally']


namechars = string.ascii_letters + '_'


COMMENT = N_TOKENS
tok_name[COMMENT] = 'COMMENT'


class Token(object):
    """
    The token object is an efficient representation of the structure
    (type, token, (start_pos_line, start_pos_col)). It has indexer
    methods that maintain compatibility to existing code that expects the above
    structure.

    >>> repr(Token(1, "test", (1, 1)))
    "<Token: ('NAME', 'test', (1, 1))>"
    >>> Token(1, 'bar', (3, 4)).__getstate__()
    (1, 'bar', 3, 4)
    >>> a = Token(0, 'baz', (0, 0))
    >>> a.__setstate__((1, 'foo', 3, 4))
    >>> a
    <Token: ('NAME', 'foo', (3, 4))>
    >>> a.start_pos
    (3, 4)
    >>> a.string
    'foo'
    >>> a._start_pos_col
    4
    >>> Token(1, u("😷"), (1 ,1)).string + "p" == u("😷p")
    True
    """
    __slots__ = ("type", "string", "_start_pos_line", "_start_pos_col")

    def __init__(self, type, string, start_pos):
        self.type = type
        self.string = string
        self._start_pos_line = start_pos[0]
        self._start_pos_col = start_pos[1]

    def __repr__(self):
        typ = tok_name[self.type]
        content = typ, self.string, (self._start_pos_line, self._start_pos_col)
        return "<%s: %s>" % (type(self).__name__, content)

    @property
    def start_pos(self):
        return (self._start_pos_line, self._start_pos_col)

    @property
    def end_pos(self):
        """Returns end position respecting multiline tokens."""
        end_pos_line = self._start_pos_line
        lines = self.string.split('\n')
        if self.string.endswith('\n'):
            lines = lines[:-1]
            lines[-1] += '\n'
        end_pos_line += len(lines) - 1
        end_pos_col = self._start_pos_col
        # Check for multiline token
        if self._start_pos_line == end_pos_line:
            end_pos_col += len(lines[-1])
        else:
            end_pos_col = len(lines[-1])
        return (end_pos_line, end_pos_col)

    # Make cache footprint smaller for faster unpickling
    def __getstate__(self):
        return (self.type, self.string, self._start_pos_line, self._start_pos_col)

    def __setstate__(self, state):
        self.type = state[0]
        self.string = state[1]
        self._start_pos_line = state[2]
        self._start_pos_col = state[3]


def group(*choices):
    return '(' + '|'.join(choices) + ')'


def maybe(*choices):
    return group(*choices) + '?'


# Note: we use unicode matching for names ("\w") but ascii matching for
# number literals.
whitespace = r'[ \f\t]*'
comment = r'#[^\r\n]*'
name = r'\w+'

hex_number = r'0[xX][0-9a-fA-F]+'
bin_number = r'0[bB][01]+'
oct_number = r'0[oO][0-7]+'
dec_number = r'(?:0+|[1-9][0-9]*)'
int_number = group(hex_number, bin_number, oct_number, dec_number)
exponent = r'[eE][-+]?[0-9]+'
point_float = group(r'[0-9]+\.[0-9]*', r'\.[0-9]+') + maybe(exponent)
Expfloat = r'[0-9]+' + exponent
float_number = group(point_float, Expfloat)
imag_number = group(r'[0-9]+[jJ]', float_number + r'[jJ]')
number = group(imag_number, float_number, int_number)

# Tail end of ' string.
single = r"[^'\\]*(?:\\.[^'\\]*)*'"
# Tail end of " string.
double = r'[^"\\]*(?:\\.[^"\\]*)*"'
# Tail end of ''' string.
single3 = r"[^'\\]*(?:(?:\\.|'(?!''))[^'\\]*)*'''"
# Tail end of """ string.
double3 = r'[^"\\]*(?:(?:\\.|"(?!""))[^"\\]*)*"""'
triple = group("[bB]?[rR]?'''", '[bB]?[rR]?"""')
# Single-line ' or " string.

# Because of leftmost-then-longest match semantics, be sure to put the
# longest operators first (e.g., if = came before ==, == would get
# recognized as two instances of =).
operator = group(r"\*\*=?", r">>=?", r"<<=?", r"!=",
                 r"//=?", r"->",
                 r"[+\-*/%&|^=<>]=?",
                 r"~")

bracket = '[][(){}]'
special = group(r'\r?\n', r'\.\.\.', r'[:;.,@]')
funny = group(operator, bracket, special)

# First (or only) line of ' or " string.
cont_str = group(r"[bBuU]?[rR]?'[^\n'\\]*(?:\\.[^\n'\\]*)*" +
                 group("'", r'\\\r?\n'),
                 r'[bBuU]?[rR]?"[^\n"\\]*(?:\\.[^\n"\\]*)*' +
                 group('"', r'\\\r?\n'))
pseudo_extras = group(r'\\\r?\n', comment, triple)
pseudo_token = whitespace + group(pseudo_extras, number, funny, cont_str, name)


def _compile(expr):
    return re.compile(expr, re.UNICODE)


pseudoprog, single3prog, double3prog = map(
    _compile, (pseudo_token, single3, double3))
endprogs = {"'": _compile(single), '"': _compile(double),
            "'''": single3prog, '"""': double3prog,
            "r'''": single3prog, 'r"""': double3prog,
            "b'''": single3prog, 'b"""': double3prog,
            "u'''": single3prog, 'u"""': double3prog,
            "br'''": single3prog, 'br"""': double3prog,
            "R'''": single3prog, 'R"""': double3prog,
            "B'''": single3prog, 'B"""': double3prog,
            "U'''": single3prog, 'U"""': double3prog,
            "bR'''": single3prog, 'bR"""': double3prog,
            "Br'''": single3prog, 'Br"""': double3prog,
            "BR'''": single3prog, 'BR"""': double3prog,
            'r': None, 'R': None, 'b': None, 'B': None}

triple_quoted = {}
for t in ("'''", '"""',
          "r'''", 'r"""', "R'''", 'R"""',
          "b'''", 'b"""', "B'''", 'B"""',
          "u'''", 'u"""', "U'''", 'U"""',
          "br'''", 'br"""', "Br'''", 'Br"""',
          "bR'''", 'bR"""', "BR'''", 'BR"""'):
    triple_quoted[t] = t
single_quoted = {}
for t in ("'", '"',
          "r'", 'r"', "R'", 'R"',
          "b'", 'b"', "B'", 'B"',
          "u'", 'u""', "U'", 'U"',
          "br'", 'br"', "Br'", 'Br"',
          "bR'", 'bR"', "BR'", 'BR"'):
    single_quoted[t] = t

del _compile

tabsize = 8


def source_tokens(source, line_offset=0):
    """Generate tokens from a the source code (string)."""
    source = source + '\n'  # end with \n, because the parser needs it
    readline = StringIO(source).readline
    return generate_tokens(readline, line_offset)


def generate_tokens(readline, line_offset=0):
    """
    The original stdlib Python version with minor modifications.
    Modified to not care about dedents.
    """
    lnum = line_offset
    numchars = '0123456789'
    contstr = ''
    contline = None
    while True:             # loop over lines in stream
        line = readline()  # readline returns empty if it's finished. See StringIO
        if not line:
            if contstr:
                yield Token(ERRORTOKEN, contstr, contstr_start)
            break

        lnum += 1
        pos, max = 0, len(line)

        if contstr:                                         # continued string
            endmatch = endprog.match(line)
            if endmatch:
                pos = endmatch.end(0)
                yield Token(STRING, contstr + line[:pos], contstr_start)
                contstr = ''
                contline = None
            else:
                contstr = contstr + line
                contline = contline + line
                continue

        while pos < max:
            pseudomatch = pseudoprog.match(line, pos)
            if not pseudomatch:                             # scan for tokens
                txt = line[pos]
                if line[pos] in '"\'':
                    # If a literal starts but doesn't end the whole rest of the
                    # line is an error token.
                    txt = txt = line[pos:]
                yield Token(ERRORTOKEN, txt, (lnum, pos))
                pos += 1
                continue

            start, pos = pseudomatch.span(1)
            spos = (lnum, start)
            token, initial = line[start:pos], line[start]

            if (initial in numchars or                      # ordinary number
                    (initial == '.' and token != '.' and token != '...')):
                yield Token(NUMBER, token, spos)
            elif initial in '\r\n':
                yield Token(NEWLINE, token, spos)
            elif initial == '#':
                assert not token.endswith("\n")
                yield Token(COMMENT, token, spos)
            elif token in triple_quoted:
                endprog = endprogs[token]
                endmatch = endprog.match(line, pos)
                if endmatch:                                # all on one line
                    pos = endmatch.end(0)
                    token = line[start:pos]
                    yield Token(STRING, token, spos)
                else:
                    contstr_start = (lnum, start)                # multiple lines
                    contstr = line[start:]
                    contline = line
                    break
            elif initial in single_quoted or \
                    token[:2] in single_quoted or \
                    token[:3] in single_quoted:
                if token[-1] == '\n':                       # continued string
                    contstr_start = lnum, start
                    endprog = (endprogs[initial] or endprogs[token[1]] or
                               endprogs[token[2]])
                    contstr = line[start:]
                    contline = line
                    break
                else:                                       # ordinary string
                    yield Token(STRING, token, spos)
            elif initial in namechars:                      # ordinary name
                yield Token(NAME, token, spos)
            elif initial == '\\' and line[start:] == '\\\n':  # continued stmt
                continue
            else:
                yield Token(OP, token, spos)

    yield Token(ENDMARKER, '', (lnum, 0))

########NEW FILE########
__FILENAME__ = user_context
import re
import os

from jedi import cache
from jedi.parser import tokenize
from jedi._compatibility import u
from jedi.parser.fast import FastParser
from jedi.parser import representation
from jedi import debug
from jedi.common import PushBackIterator


class UserContext(object):
    """
    :param source: The source code of the file.
    :param position: The position, the user is currently in. Only important \
    for the main file.
    """
    def __init__(self, source, position):
        self.source = source
        self.position = position
        self._line_cache = None

        # this two are only used, because there is no nonlocal in Python 2
        self._line_temp = None
        self._relevant_temp = None

    @cache.underscore_memoization
    def get_path_until_cursor(self):
        """ Get the path under the cursor. """
        path, self._start_cursor_pos = self._calc_path_until_cursor(self.position)
        return path

    def _calc_path_until_cursor(self, start_pos=None):
        """
        Something like a reverse tokenizer that tokenizes the reversed strings.
        """
        def fetch_line():
            if self._is_first:
                self._is_first = False
                self._line_length = self._column_temp
                line = first_line
            else:
                line = self.get_line(self._line_temp)
                self._line_length = len(line)
            line = '\n' + line

            # add lines with a backslash at the end
            while True:
                self._line_temp -= 1
                last_line = self.get_line(self._line_temp)
                if last_line and last_line[-1] == '\\':
                    line = last_line[:-1] + ' ' + line
                    self._line_length = len(last_line)
                else:
                    break
            return line[::-1]

        self._is_first = True
        self._line_temp, self._column_temp = start_cursor = start_pos
        first_line = self.get_line(self._line_temp)[:self._column_temp]

        open_brackets = ['(', '[', '{']
        close_brackets = [')', ']', '}']

        gen = PushBackIterator(tokenize.generate_tokens(fetch_line))
        string = u('')
        level = 0
        force_point = False
        last_type = None
        is_first = True
        for tok in gen:
            tok_type = tok.type
            tok_str = tok.string
            end = tok.end_pos
            self._column_temp = self._line_length - end[1]
            if is_first:
                if tok.start_pos != (1, 0):  # whitespace is not a path
                    return u(''), start_cursor
                is_first = False

            # print 'tok', token_type, tok_str, force_point
            if last_type == tok_type == tokenize.NAME:
                string += ' '

            if level > 0:
                if tok_str in close_brackets:
                    level += 1
                if tok_str in open_brackets:
                    level -= 1
            elif tok_str == '.':
                force_point = False
            elif force_point:
                # it is reversed, therefore a number is getting recognized
                # as a floating point number
                if tok_type == tokenize.NUMBER and tok_str[0] == '.':
                    force_point = False
                else:
                    break
            elif tok_str in close_brackets:
                level += 1
            elif tok_type in [tokenize.NAME, tokenize.STRING]:
                force_point = True
            elif tok_type == tokenize.NUMBER:
                pass
            else:
                if tok_str == '-':
                    next_tok = next(gen)
                    if next_tok.string == 'e':
                        gen.push_back(next_tok)
                    else:
                        break
                else:
                    break

            x = start_pos[0] - end[0] + 1
            l = self.get_line(x)
            l = first_line if x == start_pos[0] else l
            start_cursor = x, len(l) - end[1]
            string += tok_str
            last_type = tok_type

        # string can still contain spaces at the end
        return string[::-1].strip(), start_cursor

    def get_path_under_cursor(self):
        """
        Return the path under the cursor. If there is a rest of the path left,
        it will be added to the stuff before it.
        """
        return self.get_path_until_cursor() + self.get_path_after_cursor()

    def get_path_after_cursor(self):
        line = self.get_line(self.position[0])
        return re.search("[\w\d]*", line[self.position[1]:]).group(0)

    def get_operator_under_cursor(self):
        line = self.get_line(self.position[0])
        after = re.match("[^\w\s]+", line[self.position[1]:])
        before = re.match("[^\w\s]+", line[:self.position[1]][::-1])
        return (before.group(0) if before is not None else '') \
            + (after.group(0) if after is not None else '')

    def get_context(self, yield_positions=False):
        self.get_path_until_cursor()  # In case _start_cursor_pos is undefined.
        pos = self._start_cursor_pos
        while True:
            # remove non important white space
            line = self.get_line(pos[0])
            while True:
                if pos[1] == 0:
                    line = self.get_line(pos[0] - 1)
                    if line and line[-1] == '\\':
                        pos = pos[0] - 1, len(line) - 1
                        continue
                    else:
                        break

                if line[pos[1] - 1].isspace():
                    pos = pos[0], pos[1] - 1
                else:
                    break

            try:
                result, pos = self._calc_path_until_cursor(start_pos=pos)
                if yield_positions:
                    yield pos
                else:
                    yield result
            except StopIteration:
                if yield_positions:
                    yield None
                else:
                    yield ''

    def get_line(self, line_nr):
        if not self._line_cache:
            self._line_cache = self.source.splitlines()
            if self.source:
                if self.source[-1] == '\n':
                    self._line_cache.append(u(''))
            else:  # ''.splitlines() == []
                self._line_cache = [u('')]

        if line_nr == 0:
            # This is a fix for the zeroth line. We need a newline there, for
            # the backwards parser.
            return u('')
        if line_nr < 0:
            raise StopIteration()
        try:
            return self._line_cache[line_nr - 1]
        except IndexError:
            raise StopIteration()

    def get_position_line(self):
        return self.get_line(self.position[0])[:self.position[1]]


class UserContextParser(object):
    def __init__(self, source, path, position, user_context):
        self._source = source
        self._path = path and os.path.abspath(path)
        self._position = position
        self._user_context = user_context

    @cache.underscore_memoization
    def _parser(self):
        cache.invalidate_star_import_cache(self._path)
        parser = FastParser(self._source, self._path)
        # Don't pickle that module, because the main module is changing quickly
        cache.save_parser(self._path, None, parser, pickling=False)
        return parser

    @cache.underscore_memoization
    def user_stmt(self):
        module = self.module()
        debug.speed('parsed')
        return module.get_statement_for_position(self._position, include_imports=True)

    @cache.underscore_memoization
    def user_stmt_with_whitespace(self):
        """
        Returns the statement under the cursor even if the statement lies
        before the cursor.
        """
        user_stmt = self.user_stmt()

        if not user_stmt:
            # for statements like `from x import ` (cursor not in statement)
            # or `abs( ` where the cursor is out in the whitespace.
            if self._user_context.get_path_under_cursor():
                # We really should have a user_stmt, but the parser couldn't
                # process it - probably a Syntax Error (or in a comment).
                debug.warning('No statement under the cursor.')
                return
            pos = next(self._user_context.get_context(yield_positions=True))
            user_stmt = self.module().get_statement_for_position(pos, include_imports=True)
        return user_stmt

    @cache.underscore_memoization
    def user_scope(self):
        user_stmt = self.user_stmt()
        if user_stmt is None:
            def scan(scope):
                for s in scope.statements + scope.subscopes:
                    if isinstance(s, representation.Scope):
                        if s.start_pos <= self._position <= s.end_pos:
                            return scan(s) or s

            return scan(self.module()) or self.module()
        else:
            return user_stmt.parent

    def module(self):
        return self._parser().module

########NEW FILE########
__FILENAME__ = refactoring
"""
Introduce some basic refactoring functions to |jedi|. This module is still in a
very early development stage and needs much testing and improvement.

.. warning:: I won't do too much here, but if anyone wants to step in, please
             do. Refactoring is none of my priorities

It uses the |jedi| `API <plugin-api.html>`_ and supports currently the
following functions (sometimes bug-prone):

- rename
- extract variable
- inline variable
"""
import difflib

from jedi import common
from jedi.evaluate import helpers
from jedi.parser import representation as pr


class Refactoring(object):
    def __init__(self, change_dct):
        """
        :param change_dct: dict(old_path=(new_path, old_lines, new_lines))
        """
        self.change_dct = change_dct

    def old_files(self):
        dct = {}
        for old_path, (new_path, old_l, new_l) in self.change_dct.items():
            dct[new_path] = '\n'.join(new_l)
        return dct

    def new_files(self):
        dct = {}
        for old_path, (new_path, old_l, new_l) in self.change_dct.items():
            dct[new_path] = '\n'.join(new_l)
        return dct

    def diff(self):
        texts = []
        for old_path, (new_path, old_l, new_l) in self.change_dct.items():
            if old_path:
                udiff = difflib.unified_diff(old_l, new_l)
            else:
                udiff = difflib.unified_diff(old_l, new_l, old_path, new_path)
            texts.append('\n'.join(udiff))
        return '\n'.join(texts)


def rename(script, new_name):
    """ The `args` / `kwargs` params are the same as in `api.Script`.
    :param operation: The refactoring operation to execute.
    :type operation: str
    :type source: str
    :return: list of changed lines/changed files
    """
    return Refactoring(_rename(script.usages(), new_name))


def _rename(names, replace_str):
    """ For both rename and inline. """
    order = sorted(names, key=lambda x: (x.module_path, x.line, x.column),
                   reverse=True)

    def process(path, old_lines, new_lines):
        if new_lines is not None:  # goto next file, save last
            dct[path] = path, old_lines, new_lines

    dct = {}
    current_path = object()
    new_lines = old_lines = None
    for name in order:
        if name.in_builtin_module():
            continue
        if current_path != name.module_path:
            current_path = name.module_path

            process(current_path, old_lines, new_lines)
            if current_path is not None:
                # None means take the source that is a normal param.
                with open(current_path) as f:
                    source = f.read()

            new_lines = common.source_to_unicode(source).splitlines()
            old_lines = new_lines[:]

        nr, indent = name.line, name.column
        line = new_lines[nr - 1]
        new_lines[nr - 1] = line[:indent] + replace_str + \
            line[indent + len(name.name):]
    process(current_path, old_lines, new_lines)
    return dct


def extract(script, new_name):
    """ The `args` / `kwargs` params are the same as in `api.Script`.
    :param operation: The refactoring operation to execute.
    :type operation: str
    :type source: str
    :return: list of changed lines/changed files
    """
    new_lines = common.source_to_unicode(script.source).splitlines()
    old_lines = new_lines[:]

    user_stmt = script._parser.user_stmt()

    # TODO care for multiline extracts
    dct = {}
    if user_stmt:
        pos = script._pos
        line_index = pos[0] - 1
        arr, index = helpers.array_for_pos(user_stmt, pos)
        if arr is not None:
            start_pos = arr[index].start_pos
            end_pos = arr[index].end_pos

            # take full line if the start line is different from end line
            e = end_pos[1] if end_pos[0] == start_pos[0] else None
            start_line = new_lines[start_pos[0] - 1]
            text = start_line[start_pos[1]:e]
            for l in range(start_pos[0], end_pos[0] - 1):
                text += '\n' + l
            if e is None:
                end_line = new_lines[end_pos[0] - 1]
                text += '\n' + end_line[:end_pos[1]]

            # remove code from new lines
            t = text.lstrip()
            del_start = start_pos[1] + len(text) - len(t)

            text = t.rstrip()
            del_end = len(t) - len(text)
            if e is None:
                new_lines[end_pos[0] - 1] = end_line[end_pos[1] - del_end:]
                e = len(start_line)
            else:
                e = e - del_end
            start_line = start_line[:del_start] + new_name + start_line[e:]
            new_lines[start_pos[0] - 1] = start_line
            new_lines[start_pos[0]:end_pos[0] - 1] = []

            # add parentheses in multiline case
            open_brackets = ['(', '[', '{']
            close_brackets = [')', ']', '}']
            if '\n' in text and not (text[0] in open_brackets and text[-1] ==
                                     close_brackets[open_brackets.index(text[0])]):
                text = '(%s)' % text

            # add new line before statement
            indent = user_stmt.start_pos[1]
            new = "%s%s = %s" % (' ' * indent, new_name, text)
            new_lines.insert(line_index, new)
    dct[script.path] = script.path, old_lines, new_lines
    return Refactoring(dct)


def inline(script):
    """
    :type script: api.Script
    """
    new_lines = common.source_to_unicode(script.source).splitlines()

    dct = {}

    definitions = script.goto_assignments()
    with common.ignored(AssertionError):
        assert len(definitions) == 1
        stmt = definitions[0]._definition
        usages = script.usages()
        inlines = [r for r in usages
                   if not stmt.start_pos <= (r.line, r.column) <= stmt.end_pos]
        inlines = sorted(inlines, key=lambda x: (x.module_path, x.line, x.column),
                         reverse=True)
        expression_list = stmt.expression_list()
        # don't allow multiline refactorings for now.
        assert stmt.start_pos[0] == stmt.end_pos[0]
        index = stmt.start_pos[0] - 1

        line = new_lines[index]
        replace_str = line[expression_list[0].start_pos[1]:stmt.end_pos[1] + 1]
        replace_str = replace_str.strip()
        # tuples need parentheses
        if expression_list and isinstance(expression_list[0], pr.Array):
            arr = expression_list[0]
            if replace_str[0] not in ['(', '[', '{'] and len(arr) > 1:
                replace_str = '(%s)' % replace_str

        # if it's the only assignment, remove the statement
        if len(stmt.get_defined_names()) == 1:
            line = line[:stmt.start_pos[1]] + line[stmt.end_pos[1]:]

        dct = _rename(inlines, replace_str)
        # remove the empty line
        new_lines = dct[script.path][2]
        if line.strip():
            new_lines[index] = line
        else:
            new_lines.pop(index)

    return Refactoring(dct)

########NEW FILE########
__FILENAME__ = settings
"""
This module contains variables with global |jedi| settings. To change the
behavior of |jedi|, change the variables defined in :mod:`jedi.settings`.

Plugins should expose an interface so that the user can adjust the
configuration.


Example usage::

    from jedi import settings
    settings.case_insensitive_completion = True


Completion output
~~~~~~~~~~~~~~~~~

.. autodata:: case_insensitive_completion
.. autodata:: add_dot_after_module
.. autodata:: add_bracket_after_function
.. autodata:: no_completion_duplicates


Filesystem cache
~~~~~~~~~~~~~~~~

.. autodata:: cache_directory
.. autodata:: use_filesystem_cache


Parser
~~~~~~

.. autodata:: fast_parser


Dynamic stuff
~~~~~~~~~~~~~

.. autodata:: dynamic_arrays_instances
.. autodata:: dynamic_array_additions
.. autodata:: dynamic_params
.. autodata:: dynamic_params_for_other_modules
.. autodata:: additional_dynamic_modules


.. _settings-recursion:

Recursions
~~~~~~~~~~

Recursion settings are important if you don't want extremly
recursive python code to go absolutely crazy. First of there is a
global limit :data:`max_executions`. This limit is important, to set
a maximum amount of time, the completion may use.

The default values are based on experiments while completing the |jedi| library
itself (inception!). But I don't think there's any other Python library that
uses recursion in a similarly extreme way. These settings make the completion
definitely worse in some cases. But a completion should also be fast.

.. autodata:: max_until_execution_unique
.. autodata:: max_function_recursion_level
.. autodata:: max_executions_without_builtins
.. autodata:: max_executions
.. autodata:: scale_call_signatures


Caching
~~~~~~~

.. autodata:: star_import_cache_validity
.. autodata:: call_signatures_validity


"""
import os
import platform

# ----------------
# completion output settings
# ----------------

case_insensitive_completion = True
"""
The completion is by default case insensitive.
"""

add_dot_after_module = False
"""
Adds a dot after a module, because a module that is not accessed this way is
definitely not the normal case. However, in VIM this doesn't work, that's why
it isn't used at the moment.
"""

add_bracket_after_function = False
"""
Adds an opening bracket after a function, because that's normal behaviour.
Removed it again, because in VIM that is not very practical.
"""

no_completion_duplicates = True
"""
If set, completions with the same name don't appear in the output anymore,
but are in the `same_name_completions` attribute.
"""

# ----------------
# Filesystem cache
# ----------------

use_filesystem_cache = True
"""
Use filesystem cache to save once parsed files with pickle.
"""

if platform.system().lower() == 'windows':
    _cache_directory = os.path.join(os.getenv('APPDATA') or '~', 'Jedi',
                                    'Jedi')
elif platform.system().lower() == 'darwin':
    _cache_directory = os.path.join('~', 'Library', 'Caches', 'Jedi')
else:
    _cache_directory = os.path.join(os.getenv('XDG_CACHE_HOME') or '~/.cache',
                                    'jedi')
cache_directory = os.path.expanduser(_cache_directory)
"""
The path where all the caches can be found.

On Linux, this defaults to ``~/.cache/jedi/``, on OS X to
``~/Library/Caches/Jedi/`` and on Windows to ``%APPDATA%\\Jedi\\Jedi\\``.
On Linux, if environment variable ``$XDG_CACHE_HOME`` is set,
``$XDG_CACHE_HOME/jedi`` is used instead of the default one.
"""

# ----------------
# parser
# ----------------

fast_parser = True
"""
Use the fast parser. This means that reparsing is only being done if
something has been changed e.g. to a function. If this happens, only the
function is being reparsed.
"""

# ----------------
# dynamic stuff
# ----------------

dynamic_arrays_instances = True
"""
Check for `append`, etc. on array instances like list()
"""

dynamic_array_additions = True
"""
check for `append`, etc. on arrays: [], {}, ()
"""

dynamic_params = True
"""
A dynamic param completion, finds the callees of the function, which define
the params of a function.
"""

dynamic_params_for_other_modules = True
"""
Do the same for other modules.
"""

additional_dynamic_modules = []
"""
Additional modules in which |jedi| checks if statements are to be found. This
is practical for IDEs, that want to administrate their modules themselves.
"""

dynamic_flow_information = True
"""
Check for `isinstance` and other information to infer a type.
"""

# ----------------
# recursions
# ----------------

max_until_execution_unique = 50
"""
This limit is probably the most important one, because if this limit is
exceeded, functions can only be one time executed. So new functions will be
executed, complex recursions with the same functions again and again, are
ignored.
"""

max_function_recursion_level = 5
"""
`max_function_recursion_level` is more about whether the recursions are
stopped in deepth or in width. The ratio beetween this and
`max_until_execution_unique` is important here. It stops a recursion (after
the number of function calls in the recursion), if it was already used
earlier.
"""

max_executions_without_builtins = 200
"""
.. todo:: Document this.
"""

max_executions = 250
"""
A maximum amount of time, the completion may use.
"""

scale_call_signatures = 0.1
"""
Because call_signatures is normally used on every single key hit, it has
to be faster than a normal completion. This is the factor that is used to
scale `max_executions` and `max_until_execution_unique`:
"""

# ----------------
# caching validity (time)
# ----------------

star_import_cache_validity = 60.0
"""
In huge packages like numpy, checking all star imports on every completion
might be slow, therefore we do a star import caching, that lasts a certain
time span (in seconds).
"""

call_signatures_validity = 3.0
"""
Finding function calls might be slow (0.1-0.5s). This is not acceptible for
normal writing. Therefore cache it for a short time.
"""

########NEW FILE########
__FILENAME__ = utils
"""
Utilities for end-users.
"""

from __future__ import absolute_import
import __main__
from collections import namedtuple
import re
import os
import sys

from jedi import Interpreter
from jedi.api.helpers import completion_parts
from jedi.parser.user_context import UserContext


def setup_readline(namespace_module=__main__):
    """
    Install Jedi completer to :mod:`readline`.

    This function setups :mod:`readline` to use Jedi in Python interactive
    shell.  If you want to use a custom ``PYTHONSTARTUP`` file (typically
    ``$HOME/.pythonrc.py``), you can add this piece of code::

        try:
            from jedi.utils import setup_readline
            setup_readline()
        except ImportError:
            # Fallback to the stdlib readline completer if it is installed.
            # Taken from http://docs.python.org/2/library/rlcompleter.html
            print("Jedi is not installed, falling back to readline")
            try:
                import readline
                import rlcompleter
                readline.parse_and_bind("tab: complete")
            except ImportError:
                print("Readline is not installed either. No tab completion is enabled.")

    This will fallback to the readline completer if Jedi is not installed.
    The readline completer will only complete names in the global namespace,
    so for example::

        ran<TAB>

    will complete to ``range``

    with both Jedi and readline, but::

        range(10).cou<TAB>

    will show complete to ``range(10).count`` only with Jedi.

    You'll also need to add ``export PYTHONSTARTUP=$HOME/.pythonrc.py`` to
    your shell profile (usually ``.bash_profile`` or ``.profile`` if you use
    bash).

    """
    class JediRL(object):
        def complete(self, text, state):
            """
            This complete stuff is pretty weird, a generator would make
            a lot more sense, but probably due to backwards compatibility
            this is still the way how it works.

            The only important part is stuff in the ``state == 0`` flow,
            everything else has been copied from the ``rlcompleter`` std.
            library module.
            """
            if state == 0:
                sys.path.insert(0, os.getcwd())
                # Calling python doesn't have a path, so add to sys.path.
                try:
                    interpreter = Interpreter(text, [namespace_module.__dict__])

                    path = UserContext(text, (1, len(text))).get_path_until_cursor()
                    path, dot, like = completion_parts(path)
                    before = text[:len(text) - len(like)]
                    completions = interpreter.completions()
                finally:
                    sys.path.pop(0)

                self.matches = [before + c.name_with_symbols for c in completions]
            try:
                return self.matches[state]
            except IndexError:
                return None

    try:
        import readline
    except ImportError:
        print("Module readline not available.")
    else:
        readline.set_completer(JediRL().complete)
        readline.parse_and_bind("tab: complete")
        # jedi itself does the case matching
        readline.parse_and_bind("set completion-ignore-case on")
        # because it's easier to hit the tab just once
        readline.parse_and_bind("set show-all-if-unmodified")
        readline.parse_and_bind("set show-all-if-ambiguous on")
        # don't repeat all the things written in the readline all the time
        readline.parse_and_bind("set completion-prefix-display-length 2")
        # No delimiters, Jedi handles that.
        readline.set_completer_delims('')


def version_info():
    """
    Returns a namedtuple of Jedi's version, similar to Python's
    ``sys.version_info``.
    """
    Version = namedtuple('Version', 'major, minor, micro, releaselevel, serial')
    from jedi import __version__
    tupl = re.findall('[a-z]+|\d+', __version__)
    return Version(*[x if i == 3 else int(x) for i, x in enumerate(tupl)])

########NEW FILE########
__FILENAME__ = _compatibility
"""
To ensure compatibility from Python ``2.6`` - ``3.3``, a module has been
created. Clearly there is huge need to use conforming syntax.
"""
import sys
import imp
import os
import re
try:
    import importlib
except ImportError:
    pass

is_py3 = sys.version_info[0] >= 3
is_py33 = is_py3 and sys.version_info.minor >= 3
is_py26 = not is_py3 and sys.version_info[1] < 7


def find_module_py33(string, path=None):
    loader = importlib.machinery.PathFinder.find_module(string, path)

    if loader is None and path is None:  # Fallback to find builtins
        loader = importlib.find_loader(string)

    if loader is None:
        raise ImportError("Couldn't find a loader for {0}".format(string))

    try:
        is_package = loader.is_package(string)
        if is_package:
            module_path = os.path.dirname(loader.path)
            module_file = None
        else:
            module_path = loader.get_filename(string)
            module_file = open(module_path, 'rb')
    except AttributeError:
        # ExtensionLoader has not attribute get_filename, instead it has a
        # path attribute that we can use to retrieve the module path
        try:
            module_path = loader.path
            module_file = open(loader.path, 'rb')
        except AttributeError:
            module_path = string
            module_file = None
        finally:
            is_package = False

    return module_file, module_path, is_package


def find_module_pre_py33(string, path=None):
    module_file, module_path, description = imp.find_module(string, path)
    module_type = description[2]
    return module_file, module_path, module_type is imp.PKG_DIRECTORY


find_module = find_module_py33 if is_py33 else find_module_pre_py33
find_module.__doc__ = """
Provides information about a module.

This function isolates the differences in importing libraries introduced with
python 3.3 on; it gets a module name and optionally a path. It will return a
tuple containin an open file for the module (if not builtin), the filename
or the name of the module if it is a builtin one and a boolean indicating
if the module is contained in a package.
"""

# next was defined in python 2.6, in python 3 obj.next won't be possible
# anymore
try:
    next = next
except NameError:
    _raiseStopIteration = object()

    def next(iterator, default=_raiseStopIteration):
        if not hasattr(iterator, 'next'):
            raise TypeError("not an iterator")
        try:
            return iterator.next()
        except StopIteration:
            if default is _raiseStopIteration:
                raise
            else:
                return default

# unicode function
try:
    unicode = unicode
except NameError:
    unicode = str

if is_py3:
    u = lambda s: s
else:
    u = lambda s: s.decode('utf-8')

u.__doc__ = """
Decode a raw string into unicode object.  Do nothing in Python 3.
"""

# exec function
if is_py3:
    def exec_function(source, global_map):
        exec(source, global_map)
else:
    eval(compile("""def exec_function(source, global_map):
                        exec source in global_map """, 'blub', 'exec'))

# re-raise function
if is_py3:
    def reraise(exception, traceback):
        raise exception.with_traceback(traceback)
else:
    eval(compile("""
def reraise(exception, traceback):
    raise exception, None, traceback
""", 'blub', 'exec'))

reraise.__doc__ = """
Re-raise `exception` with a `traceback` object.

Usage::

    reraise(Exception, sys.exc_info()[2])

"""

# hasattr function used because python
if is_py3:
    hasattr = hasattr
else:
    def hasattr(obj, name):
        try:
            getattr(obj, name)
            return True
        except AttributeError:
            return False


class Python3Method(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype):
        if obj is None:
            return lambda *args, **kwargs: self.func(*args, **kwargs)
        else:
            return lambda *args, **kwargs: self.func(obj, *args, **kwargs)


def use_metaclass(meta, *bases):
    """ Create a class with a metaclass. """
    if not bases:
        bases = (object,)
    return meta("HackClass", bases, {})


try:
    encoding = sys.stdout.encoding
    if encoding is None:
        encoding = 'utf-8'
except AttributeError:
    encoding = 'ascii'


def u(string):
    """Cast to unicode DAMMIT!
    Written because Python2 repr always implicitly casts to a string, so we
    have to cast back to a unicode (and we now that we always deal with valid
    unicode, because we check that in the beginning).
    """
    if is_py3:
        return str(string)
    elif not isinstance(string, unicode):
        return unicode(str(string), 'UTF-8')
    return string

try:
    import builtins  # module name in python 3
except ImportError:
    import __builtin__ as builtins


import ast


def literal_eval(string):
    # py3.0, py3.1 and py32 don't support unicode literals. Support those, I
    # don't want to write two versions of the tokenizer.
    if is_py3 and sys.version_info.minor < 3:
        if re.match('[uU][\'"]', string):
            string = string[1:]
    return ast.literal_eval(string)

########NEW FILE########
__FILENAME__ = __main__
from sys import argv
from os.path import join, dirname, abspath


if len(argv) == 2 and argv[1] == 'repl':
    # don't want to use __main__ only for repl yet, maybe we want to use it for
    # something else. So just use the keyword ``repl`` for now.
    print(join(dirname(abspath(__file__)), 'api', 'replstartup.py'))

########NEW FILE########
__FILENAME__ = completion
# -*- coding: utf-8 -*-
import functools

import sublime
import sublime_plugin

from .utils import is_python_scope, ask_daemon, get_settings
from .console_logging import getLogger
from .settings import get_settings_param

logger = getLogger(__name__)
FOLLOWING_CHARS = set(["\r", "\n", "\t", " ", ")", "]", ";", "}", "\x00"])


class SublimeJediParamsAutocomplete(sublime_plugin.TextCommand):
    """
    Function / Class constructor autocompletion command
    """
    def run(self, edit, characters='('):
        """
        Insert completion character, and complete function parameters
        if possible

        :param edit: sublime.Edit
        :param characters: str
        """
        self._insert_characters(edit, characters, ')')

        # Deprecated: scope should be tested in key bindings
        #
        # nothing to do with non-python code
        # if not is_python_scope(self.view, self.view.sel()[0].begin()):
        #     logger.info('no function args completion in strings')
        #     return

        if get_settings(self.view)['complete_funcargs']:
            ask_daemon(self.view, self.show_template, 'funcargs', self.view.sel()[0].end())

    @property
    def auto_match_enabled(self):
        """ check if sublime closes parenthesis automaticly """
        return self.view.settings().get('auto_match_enabled', True)

    def _insert_characters(self, edit, open_pair, close_pair):
        """
        Insert autocomplete character with closed pair
        and update selection regions

        If sublime option `auto_match_enabled` turned on, next behavior have to be:

            when none selection

            `( => (<caret>)`
            `<caret>1 => ( => (<caret>1`

            when text selected

            `text => (text<caret>)`

        In other case:

            when none selection

            `( => (<caret>`

            when text selected

            `text => (<caret>`


        :param edit: sublime.Edit
        :param characters: str
        """
        regions = [a for a in self.view.sel()]
        self.view.sel().clear()

        for region in reversed(regions):

            next_char = self.view.substr(region.begin())
            # replace null byte to prevent error
            next_char = next_char.replace('\x00', '\n')
            logger.debug("Next characters: {0}".format(next_char))

            following_text = next_char not in FOLLOWING_CHARS
            logger.debug("Following text: {0}".format(following_text))

            if self.auto_match_enabled:
                self.view.insert(edit, region.begin(), open_pair)
                position = region.end() + 1

                # IF selection is non-zero
                # OR after cursor no any text and selection size is zero
                # THEN insert closing pair
                if region.size() > 0 or not following_text and region.size() == 0:
                    self.view.insert(edit, region.end() + 1, close_pair)
                    position += (len(open_pair) - 1)
            else:
                self.view.replace(edit, region, open_pair)
                position = region.begin() + len(open_pair)

            self.view.sel().add(sublime.Region(position, position))

    def show_template(self, view, template):
        view.run_command('insert_snippet', {"contents": template})


class Autocomplete(sublime_plugin.EventListener):
    """
    Sublime Text autocompletion integration
    """

    completions = []
    cplns_ready = None
    cplns_mode = None

    def on_load(self, view):
        self.cplns_mode = get_settings_param(
            view,
            'sublime_completions_visibility',
            default='default'
        )

    def on_query_completions(self, view, prefix, locations):
        """ Sublime autocomplete event handler

        Get completions depends on current cursor position and return
        them as list of ('possible completion', 'completion type')

        :param view: `sublime.View` object
        :type view: sublime.View
        :param prefix: string for completions
        :type prefix: basestring
        :param locations: offset from beginning
        :type locations: int

        :return: list of tuple(str, str)
        """
        logger.info('JEDI completion triggered')

        if self.cplns_ready:
            logger.debug(
                'JEDI has completion in daemon response {0}'.format(
                    self.completions
                )
            )

            self.cplns_ready = None
            if self.completions:
                cplns, self.completions = self.completions, []
                if self.cplns_mode in ('default', 'jedi'):
                    return (
                        [tuple(i) for i in cplns],
                        sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
                    )
                return [tuple(i) for i in cplns]
            return

        if view.settings().get("repl", False):
            logger.debug("JEDI does not complete in SublimeREPL views")
            return

        # nothing to do with non-python code
        if not is_python_scope(view, locations[0]):
            logger.debug('JEDI does not complete in strings')
            return

        # get completions list
        if self.cplns_ready is None:
            ask_daemon(view, self.show_completions, 'autocomplete', locations[0])
            self.cplns_ready = False
        if self.cplns_mode == 'jedi':
            view.run_command("hide_auto_complete")
        return

    def show_completions(self, view, completions):
        # XXX check position
        self.cplns_ready = True
        if completions:
            self.completions = completions
            view.run_command("hide_auto_complete")
            sublime.set_timeout(functools.partial(self.show, view), 0)

    def show(self, view):
        logger.debug("command history: " + str([
            view.command_history(-1),
            view.command_history(0),
            view.command_history(1),
        ]))
        command = view.command_history(0)

        # if completion was triggerd by tab, then hide "tab" or "snippet"
        if command[0] == 'insert_best_completion' or\
                (command == (u'insert', {'characters': u'\t'}, 1)):
            view.run_command('undo')

        view.run_command("auto_complete", {
            'disable_auto_insert': True,
            'api_completions_only': False,
            'next_completion_if_showing': False,
            'auto_complete_commit_on_tab': True,
        })

########NEW FILE########
__FILENAME__ = console_logging
from __future__ import print_function
import sys
import functools
import logging
import traceback
import sublime
from .settings import get_plugin_settings


def get_plugin_debug_level():
    default = 'error'
    settings = get_plugin_settings()
    level = settings.get('logging_level', default)
    level = level or default
    return getattr(logging, level.upper())


class Logger:
    """
    Sublime Console Logger that takes plugin settings
    """
    def __init__(self, name):
        self.name = str(name)

    @property
    def level(self):
        return get_plugin_debug_level()

    def _print(self, msg):
        print(': '.join([self.name, str(msg)]))

    def log(self, level, msg, **kwargs):
        """ thread-safe logging """
        if kwargs.pop('exc_info', False):
            kwargs['exc_info'] = sys.exc_info()
        log = functools.partial(self._log, level, msg, **kwargs)
        sublime.set_timeout(log, 0)

    def _log(self, level, msg, **kwargs):
        """
        :param level: logging level value
        :param msg: message that logger should prints out
        :param kwargs: dictionary of additional parameters
        """
        if self.level <= level:
            self._print(msg)
            if level == logging.ERROR:
                exc_info = kwargs.get('exc_info')
                if exc_info:
                    traceback.print_exception(*exc_info)

    def debug(self, msg):
        self.log(logging.DEBUG, msg)

    def info(self, msg):
        self.log(logging.INFO, msg)

    def error(self, msg, exc_info=False):
        self.log(logging.ERROR, msg, exc_info=exc_info)

    def exception(self, msg):
        self.error(msg, exc_info=True)

    def warning(self, msg):
        self.log(logging.WARN, msg)


getLogger = Logger

########NEW FILE########
__FILENAME__ = daemon
# -*- coding: utf-8 -*-
import os
import sys
import json
import logging
from optparse import OptionParser

# add jedi too sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import jedi
from jedi.api import NotFoundError

# remove it. WHY?
sys.path.pop(0)

is_funcargs_complete_enabled = True
auto_complete_function_params = 'required'


class JsonFormatter(logging.Formatter):
    def format(self, record):
        output = logging.Formatter.format(self, record)
        data = {
            'logging': record.levelname.lower(),
            'content': output
        }
        record = json.dumps(data)
        return record


def getLogger():
    """ Build file logger """
    log = logging.getLogger('Sublime Jedi Daemon')
    log.setLevel(logging.DEBUG)
    formatter = JsonFormatter('%(asctime)s: %(levelname)-8s: %(message)s')
    hdlr = logging.StreamHandler(sys.stderr)
    hdlr.setFormatter(formatter)
    log.addHandler(hdlr)
    return log


logger = getLogger()


def write(data):
    """  Write data to STDOUT """
    if not isinstance(data, str):
        data = json.dumps(data)

    sys.stdout.write(data)

    if not data.endswith('\n'):
        sys.stdout.write('\n')

    try:
        sys.stdout.flush()
    except IOError:
        sys.exit()


def format_completion(complete):
    """ Returns a tuple of the string that would be visible in
    the completion dialogue and the completion word

    :type complete: jedi.api_classes.Completion
    :rtype: (str, str)
    """
    display, insert = complete.name + '\t' + complete.type, complete.name
    return display, insert


def get_function_parameters(callDef):
    """  Return list function parameters, prepared for sublime completion.
    Tuple contains parameter name and default value

    Parameters list excludes: self, *args and **kwargs parameters

    :type callDef: jedi.api_classes.CallDef
    :rtype: list of (str, str or None)
    """
    if not callDef:
        return []

    params = []
    for param in callDef.params:
        cleaned_param = param.get_code().strip()
        if '*' in cleaned_param or cleaned_param == 'self':
            continue
        params.append([s.strip() for s in cleaned_param.split('=')])
    return params


class JediFacade:
    """
    Facade to call Jedi API


     Action       | Method
    ===============================
     autocomplete | get_autocomplete
    -------------------------------
     goto         | get_goto
    -------------------------------
     usages       | get_usages
    -------------------------------
     funcargs     | get_funcargs
    --------------------------------


    """
    def __init__(self, source, line, offset, filename='', encoding='utf-8'):
        self.script = jedi.Script(
            source, int(line), int(offset), filename, encoding
        )

    def get(self, action):
        """ Action dispatcher """
        try:
            return getattr(self, 'get_' + action)()
        except:
            logger.exception('`JediFacade.get_{0}` failed'.format(action))

    def get_goto(self):
        """ Jedi "Go To Definition" """
        return self._goto()

    def get_usages(self):
        """ Jedi "Find Usage" """
        return self._usages()

    def get_funcargs(self):
        """ complete callable object parameters with Jedi """
        return self._complete_call_assigments()

    def get_autocomplete(self):
        """ Jedi "completion" """
        data = self._parameters_for_completion() or []
        data.extend(self._completion() or [])
        return data

    def _parameters_for_completion(self):
        """ Get function / class' constructor parameters completions list

        :rtype: list of str
        """
        completions = []
        try:
            in_call = self.script.call_signatures()[0]
        except IndexError:
            in_call = None

        parameters = get_function_parameters(in_call)

        for parameter in parameters:
            try:
                name, value = parameter
            except ValueError:
                name = parameter[0]
                value = None

            if value is None:
                completions.append((name, '${1:%s}' % name))
            else:
                completions.append((name + '\t' + value,
                                   '%s=${1:%s}' % (name, value)))
        return completions

    def _completion(self):
        """ regular completions

        :rtype: list of (str, str)
        """
        completions = self.script.completions()
        return [format_completion(complete) for complete in completions]

    def _goto(self):
        """ Jedi "go to Definitions" functionality

        :rtype: list of (str, int, int) or None
        """
        try:
            definitions = self.script.goto_assignments()
            if all(d.type == 'import' for d in definitions):
                # check if it an import string and if it is get definition
                definitions = self.script.get_definition()
        except NotFoundError:
            return
        else:
            return [(i.module_path, i.line, i.column + 1)
                    for i in definitions if not i.in_builtin_module()]

    def _usages(self):
        """ Jedi "find usages" functionality

        :rtype: list of (str, int, int)
        """
        usages = self.script.usages()
        return [(i.module_path, i.line, i.column + 1)
                for i in usages if not i.in_builtin_module()]

    def _complete_call_assigments(self):
        """ Get function or class parameters and build Sublime Snippet string
        for completion

        :rtype: str
        """
        completions = []
        complete_all = auto_complete_function_params == 'all'

        try:
            call_definition = self.script.call_signatures()[0]
        except IndexError:
            call_definition = None

        parameters = get_function_parameters(call_definition)

        for index, parameter in enumerate(parameters):
            try:
                name, value = parameter
            except ValueError:
                name = parameter[0]
                value = None

            if value is None:
                completions.append('${%d:%s}' % (index + 1, name))
            elif complete_all:
                completions.append('%s=${%d:%s}' % (name, index + 1, value))

        return ", ".join(completions)


def process_line(line):
    data = json.loads(line.strip())
    action_type = data['type']

    script = JediFacade(
        source=data['source'],
        line=data['line'],
        offset=data['offset'],
        filename=data.get('filename', '')
    )

    out_data = {
        'uuid': data.get('uuid'),
        'type': action_type,
        action_type: script.get(action_type)
    }

    write(out_data)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option(
        "-p", "--project",
        dest="project_name",
        default='',
        help="project name to store jedi's cache"
    )
    parser.add_option(
        "-e", "--extra_folder",
        dest="extra_folders",
        default=[],
        action="append",
        help="extra folders to add to sys.path"
    )
    parser.add_option(
        "-f", "--complete_function_params",
        dest="function_params",
        default='all',
        help='function parameters completion type: "all", "required", or ""'
    )

    options, args = parser.parse_args()

    is_funcargs_complete_enabled = bool(options.function_params)
    auto_complete_function_params = options.function_params

    logger.info(
        'Daemon started. '
        'extra folders - %s, '
        'complete_function_params - %s',
        options.extra_folders,
        options.function_params,
    )

    # append extra paths to sys.path
    for extra_folder in options.extra_folders:
        if extra_folder not in sys.path:
            sys.path.insert(0, extra_folder)

    # call the Jedi
    for line in iter(sys.stdin.readline, ''):
        if line:
            try:
                process_line(line)
            except Exception:
                logger.exception('failed to process line')

########NEW FILE########
__FILENAME__ = go_to
# -*- coding: utf-8 -*-
import sublime
import sublime_plugin

from .utils import to_relative_path, ask_daemon, is_python_scope


class BaseLookUpJediCommand(object):

    def is_enabled(self):
        """ command enable only for python source code """
        if not is_python_scope(self.view, self.view.sel()[0].begin()):
            return False
        return True

    def _jump_to_in_window(self, filename, line_number=None, column_number=None):
        """ Opens a new window and jumps to declaration if possible

            :param filename: string or int
            :param line_number: int
            :param column_number: int
        """
        active_window = sublime.active_window()

        # If the file was selected from a drop down list
        if isinstance(filename, int):
            if filename == -1:  # cancelled
                return
            filename, line_number, column_number = self.options[filename]
        active_window.open_file('%s:%s:%s' % (filename, line_number or 0,
                                column_number or 0), sublime.ENCODED_POSITION)

    def _window_quick_panel_open_window(self, view, options):
        """ Shows the active `sublime.Window` quickpanel (dropdown) for
            user selection.

            :param option: list of `jedi.api_classes.BasDefinition`
        """
        active_window = view.window()

        # remember filenames
        self.options = options

        # Show the user a selection of filenames
        active_window.show_quick_panel(
            [self.prepare_option(o) for o in options],
            self._jump_to_in_window
        )

    def prepare_option(self, option):
        """ prepare option to display out in quick panel """
        raise NotImplementedError(
            "{} require `prepare_option` definition".format(self.__class__)
        )


class SublimeJediGoto(BaseLookUpJediCommand, sublime_plugin.TextCommand):
    """
    Go to object definition
    """
    def run(self, edit):
        ask_daemon(self.view, self.handle_definitions, 'goto')

    def handle_definitions(self, view, defns):
        if not defns:
            return False
        if len(defns) == 1:
            defn = defns[0]
            self._jump_to_in_window(*defn)
        else:
            self._window_quick_panel_open_window(view, defns)

    def prepare_option(self, option):
        return to_relative_path(option[0])


class SublimeJediFindUsages(BaseLookUpJediCommand, sublime_plugin.TextCommand):
    """
    Find object usages
    """
    def run(self, edit):
        ask_daemon(self.view, self._window_quick_panel_open_window, 'usages')

    def prepare_option(self, option):
        return [to_relative_path(option[0]),
                "line: %d column: %d" % (option[1], option[2])]

########NEW FILE########
__FILENAME__ = settings
import sublime


def get_plugin_settings():
    setting_name = 'sublime_jedi.sublime-settings'
    plugin_settings = sublime.load_settings(setting_name)
    return plugin_settings


def get_settings_param(view, param_name, default=None):
    plugin_settings = get_plugin_settings()
    project_settings = view.settings()
    return project_settings.get(
        param_name,
        plugin_settings.get(param_name, default)
    )

########NEW FILE########
__FILENAME__ = test_daemon
import json
import unittest
from contextlib import contextmanager


@contextmanager
def mock_stderr():
        from cStringIO import StringIO
        import sys

        _stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            yield sys.stderr
        finally:
            sys.stderr = _stderr


class RegressionIssue109(unittest.TestCase):
    """
    logging prints text and traceback to stderr. Then, code in `utils.py` can
    not parse output from daemon.py and there are a lot of messages in ST
    console with `Non JSON data from daemon`

    SHould be tested:

    1. content in stderr should be JSON valid
    2. content should contains correct data
    """

    def test_json_formatter_works_on_jedi_expections(self):

        with mock_stderr() as stderr_mock:
            from daemon import JediFacade  # load class here to mock stderr

            JediFacade('print "hello"', 1, 1).get('some')
            stderr_content = json.loads(stderr_mock.getvalue())

        self.assertEqual(stderr_content['logging'], 'error')
        self.assertIn('Traceback (most recent call last):',
                      stderr_content['content'])
        self.assertIn('JediFacade instance has no attribute \'get_some\'',
                      stderr_content['content'])


if __name__ == '__main__':
    unittest.main()
########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys
import subprocess
import json
import threading
import warnings
from functools import partial
from collections import defaultdict
from uuid import uuid1
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

import sublime

from .console_logging import getLogger
from .settings import get_settings_param

logger = getLogger(__name__)
CUR_DIR = os.path.dirname(os.path.abspath(__file__))
PY3 = sys.version_info[0] == 3
DAEMONS = defaultdict(dict)  # per window


def run_in_active_view(window_id, callback, response):
    for window in sublime.windows():
        if window.id() == window_id:
            callback(window.active_view(), response)
            break


class BaseThread(threading.Thread):

    def __init__(self, fd, window_id, waiting, lock):
        self.fd = fd
        self.done = False
        self.waiting = waiting
        self.wait_lock = lock
        self.window_id = window_id
        super(BaseThread, self).__init__()
        self.daemon = True
        self.start()


class ThreadReader(BaseThread):

    def run(self):
        while not self.done:
            line = self.fd.readline()
            if line:
                data = None
                try:
                    data = json.loads(line.strip())
                except ValueError:
                    if not isinstance(data, dict):
                        logger.exception(
                            "Non JSON data from daemon: {0}".format(line)
                        )
                else:
                    self.call_callback(data)

    def call_callback(self, data):
        """
        Call callback for response data

        :type data: dict
        """
        if 'logging' in data:
            getattr(logger, data['logging'])(data['content'])
            return

        with self.wait_lock:
            callback = self.waiting.pop(data['uuid'], None)

        if callback is not None:
            delayed_callback = partial(
                run_in_active_view,
                self.window_id,
                callback,
                data[data['type']]
            )
            sublime.set_timeout(delayed_callback, 0)


class ThreadWriter(BaseThread, Queue):

    def __init__(self, *args, **kwargs):
        Queue.__init__(self)
        super(ThreadWriter, self).__init__(*args, **kwargs)

    def run(self):
        while not self.done:
            request_data = self.get()

            if not request_data:
                continue

            callback, data = request_data

            with self.wait_lock:
                self.waiting[data['uuid']] = callback

            if not isinstance(data, str):
                data = json.dumps(data)

            self.fd.write(data)
            if not data.endswith('\n'):
                self.fd.write('\n')
            self.fd.flush()


class Daemon(object):

    def __init__(self, view):
        window_id = view.window().id()
        self.waiting = dict()
        self.wlock = threading.RLock()
        self.process = self._start_process(get_settings(view))
        self.stdin = ThreadWriter(self.process.stdin, window_id,
                                  self.waiting, self.wlock)
        self.stdout = ThreadReader(self.process.stdout, window_id,
                                   self.waiting, self.wlock)
        self.stderr = ThreadReader(self.process.stderr, window_id,
                                   self.waiting, self.wlock)

    def _start_process(self, settings):
        options = {
            'stdin': subprocess.PIPE,
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'universal_newlines': True,
            'cwd': CUR_DIR,
            'bufsize': -1,
        }

        # hide "cmd" window in Windows
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            options['startupinfo'] = startupinfo

        command = [
            settings['python_interpreter'],
            '-B', 'daemon.py',
            '-p', settings['project_name']
        ]
        for folder in settings['extra_packages']:
            command.extend(['-e', folder])
        command.extend(['-f', settings['complete_funcargs']])

        logger.debug(
            'Daemon process starting with parameters: {0} {1}'
            .format(command, options)
        )
        try:
            return subprocess.Popen(command, **options)
        except OSError:
            logger.error(
                'Daemon process failed with next parameters: {0} {1}'
                .format(command, options)
            )
            raise

    def request(self, view, request_type, callback, location=None):
        """
        Send request to daemon process

        :type view: sublime.View
        :type request_type: str
        :type callback: callabel
        :type location: type of (int, int) or None
        """
        logger.info('Sending request to daemon for "{0}"'.format(request_type))

        if location is None:
            location = view.sel()[0].begin()
        current_line, current_column = view.rowcol(location)
        source = view.substr(sublime.Region(0, view.size()))

        if PY3:
            uuid = uuid1().hex
        else:
            uuid = uuid1().get_hex()

        data = {
            'source': source,
            'line': current_line + 1,
            'offset': current_column,
            'filename': view.file_name() or '',
            'type': request_type,
            'uuid': uuid,
        }
        self.stdin.put_nowait((callback, data))


def ask_daemon(view, callback, ask_type, location=None):
    """
    Daemon request shortcut

    :type view: sublime.View
    :type callback: callabel
    :type ask_type: str
    :type location: type of (int, int) or None
    """
    window_id = view.window().id()

    if window_id not in DAEMONS:
        DAEMONS[window_id] = Daemon(view)

    DAEMONS[window_id].request(view, ask_type, callback, location)


def get_settings(view):
    """
    get settings for daemon

    :type view: sublime.View
    :rtype: dict
    """
    python_interpreter = get_settings_param(view, 'python_interpreter_path')

    if not python_interpreter:
        python_interpreter = get_settings_param(view, 'python_interpreter',
                                                'python')
    else:
        warnings.warn('`python_interpreter_path` parameter is deprecated.'
                      'Please, use `python_interpreter` instead.',
                      DeprecationWarning)

    python_interpreter = expand_project_path(view, python_interpreter)

    extra_packages = get_settings_param(view, 'python_package_paths', [])
    extra_packages = [expand_project_path(view, p) for p in extra_packages]

    complete_funcargs = get_settings_param(view,
                                           'auto_complete_function_params',
                                           'all')

    first_folder = ''
    if view.window().folders():
        first_folder = os.path.split(view.window().folders()[0])[-1]
    project_name = get_settings_param(view, 'project_name', first_folder)

    return {
        'python_interpreter': python_interpreter,
        'extra_packages': extra_packages,
        'project_name': project_name,
        'complete_funcargs': complete_funcargs
    }


def is_python_scope(view, location):
    """ (View, Point) -> bool

    Get if this is a python source scope (not a string and not a comment)
    """
    return view.match_selector(location, "source.python - string - comment")


def to_relative_path(path):
    """
    Trim project root pathes from **path** passed as argument

    If no any folders opened, path will be retuned unchanged
    """
    folders = sublime.active_window().folders()
    for folder in folders:
        # close path with separator
        if folder[-1] != os.path.sep:
            folder += os.path.sep

        if path.startswith(folder):
            return path.replace(folder, '')

    return path


def expand_project_path(view, path):
    """
    expand variable `$project_path` in **path** to project's path

    :type view: sublime.View
    :type path: str
    :rtype: str
    """
    if path.startswith('$project_path'):
        project_dir = os.path.dirname(view.window().project_file_name())
        return path.replace('$project_path', project_dir, 1)
    else:
        return path

########NEW FILE########
