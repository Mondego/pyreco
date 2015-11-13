__FILENAME__ = block
"""Vimdoc blocks: encapsulated chunks of documentation."""
from collections import OrderedDict
import warnings

import vimdoc
from vimdoc import error
from vimdoc import paragraph
from vimdoc import regex


class Block(object):
  """Blocks are encapsulated chunks of documentation.

  They consist of a number of paragraphs and an optional header. The paragraphs
  can come in many types, including text, lists, or code. The block may also
  contain metadata statements specifying things like the plugin author, etc.
  """

  def __init__(self, is_secondary=False):
    # May include:
    # deprecated (boolean)
    # dict (name)
    # private (boolean, in function)
    # name (of section)
    # type (constant, e.g. vimdoc.FUNCTION)
    # id (of section, in section or backmatter)
    # namespace (of function)
    # attribute (of function in dict)
    self.locals = {}
    # Merged into module. May include:
    # author (string)
    # library (boolean)
    # order (list of strings)
    # standalone (boolean)
    # stylization (string)
    # tagline (string)
    self.globals = {}
    self.header = None
    self.paragraphs = paragraph.Paragraphs()
    self._required_args = []
    self._optional_args = []
    self._closed = False
    self._is_secondary = is_secondary

  def AddLine(self, line):
    """Adds a line of text to the block. Paragraph type is auto-determined."""
    # Code blocks are treated differently:
    # Newlines aren't joined and blanklines aren't special.
    # See :help help-writing for specification.
    if self.paragraphs.IsType(paragraph.CodeBlock):
      # '<' exits code blocks.
      if line.startswith('<'):
        self.paragraphs.Close()
        line = line[1:].lstrip()
        if line:
          self.AddLine(line)
        return
      # Lines starting in column 0 exit code lines.
      if line[:1] not in ' \t':
        self.paragraphs.Close()
        self.AddLine(line)
        return
      self.paragraphs.AddLine(line)
      return
    # Always grab the required/optional args.
    self._ParseArgs(line)
    # Blank lines divide paragraphs.
    if not line.strip():
      self.paragraphs.SetType(paragraph.BlankLine)
      return
    # Start lists if you get a list item.
    match = regex.list_item.match(line or '')
    if match:
      leader = match.group(1)
      self.paragraphs.Close()
      line = regex.list_item.sub('', line)
      self.paragraphs.SetType(paragraph.ListItem, leader)
      self.paragraphs.AddLine(line)
      return
    if line and line[:1] in ' \t':
      # Continue lists by indenting.
      if self.paragraphs.IsType(paragraph.ListItem):
        self.paragraphs.AddLine(line.lstrip())
        return
    elif self.paragraphs.IsType(paragraph.ListItem):
      self.paragraphs.Close()
    # Everything else is text.
    self.paragraphs.SetType(paragraph.TextParagraph)
    # Lines ending in '>' enter code blocks.
    if line.endswith('>'):
      line = line[:-1].rstrip()
      if line:
        self.paragraphs.AddLine(line)
      self.paragraphs.SetType(paragraph.CodeBlock)
      return
    # Normal paragraph handling.
    self.paragraphs.AddLine(line)

  def Global(self, **kwargs):
    """Sets global metadata, like plugin author."""
    self.SetType(True)
    for key, value in kwargs.items():
      if key in self.globals:
        raise error.RedundantControl(key)
      self.globals[key] = value

  def Local(self, **kwargs):
    """Sets local metadata, like private/public scope."""
    self.SetType(True)
    for key, value in kwargs.items():
      if key in self.locals and self.locals[key] != value:
        raise error.InconsistentControl(key, self.locals[key], value)
      self.locals[key] = value

  def SetType(self, newtype):
    """Sets the block type (function, command, etc.)."""
    ourtype = self.locals.get('type')
    # 'True' means "I'm definitely vimdoc but I don't have a type yet".
    if newtype is True or newtype == ourtype:
      self.locals['type'] = ourtype or newtype
      return
    # 'None' means "I don't know one way or the other".
    if ourtype is None or ourtype is True:
      self.locals['type'] = newtype
    else:
      raise error.TypeConflict(ourtype, newtype)

  def SetHeader(self, directive):
    """Sets the header handler."""
    if self.header:
      raise error.MultipleErrors
    self.header = directive
    self.paragraphs.Close()

  def AddSubHeader(self, name):
    """Adds a subheader line."""
    self.paragraphs.SetType(paragraph.SubHeaderLine, name)

  def Default(self, arg, value):
    """Adds a line which sets the default value for an optional arg."""
    # If you do "@default foo=[bar]" it's implied that [bar] preceeds [foo] in
    # the argument list -- hence, we parse value before arg.
    self._ParseArgs(value)
    # The arg is assumed optional, since it can default to things.
    if arg not in self._optional_args:
      self._optional_args.append(arg)
    self.paragraphs.SetType(paragraph.DefaultLine, arg, value)

  def Except(self, typ, description):
    """Adds a line specifying that the code can throw a specific exception."""
    description = description or ''
    self._ParseArgs(description)
    self.paragraphs.SetType(paragraph.ExceptionLine, typ, description)

  def Close(self):
    """Closes the block against further text.

    This triggers expansion of the header, if it exists. This must be done
    before the header can be used.

    Returns:
      The block itself, for easy chaining. (So you can yield block.Close())
    """
    if self._closed:
      return
    self._closed = True
    if self.locals.get('type') is True and 'dict' in self.locals:
      self.SetType(vimdoc.DICTIONARY)
    if (self.locals.get('type') in [vimdoc.FUNCTION, vimdoc.COMMAND]
        and 'exception' not in self.locals):
      if not self.header:
        # We import here to avoid a circular dependency.
        # pylint:disable-msg=g-import-not-at-top
        from vimdoc.docline import Usage
        self.header = Usage('{]')
      self.locals['usage'] = self.header.GenerateUsage(self)
    if 'private' in self.locals and self.locals.get('type') != vimdoc.FUNCTION:
      raise error.InvalidBlock('Only functions may be marked as private.')
    return self

  def RequiredArgs(self):
    """Gets a list of arguments required by the block."""
    if self.locals.get('type') == vimdoc.FUNCTION:
      sigargs = [a for a in self.locals.get('args') if a != '...']
      # They didn't mention any args. Use the args from the function signature.
      if not self._required_args:
        return sigargs
      # The args they did mention are all in the signature. Use the argument
      # order from the function signature.
      if not set(self._required_args).difference(sigargs):
        return sigargs
      # Looks like they're renaming the signature's args. Use the arguments that
      # they named in the order they named them.
      if len(self._required_args) == len(sigargs):
        return self._required_args
      # We have no idea what they're doing. The function signature doesn't match
      # the argumenst mentioned in the documentation.
      warnings.warn(
          'Arguments do not match function signature. '
          'Function signature arguments are {}. '
          'Documentation arguments are {}.'
          .format(sigargs, self._required_args),
          error.ArgumentMismatch)
    return self._required_args

  def OptionalArgs(self):
    """Gets a list of optional arguments accepted by the doc'd code."""
    if (self.locals.get('type') == vimdoc.FUNCTION
        and self._optional_args
        and '...' not in self.locals.get('args')):
      # The function accepts no optional parameters. Warn and return nothing.
      warnings.warn(
          'Documentation claims optional parameters '
          'that function {} does not accept.'.format(self.FullName()),
          error.DocumentationWarning)
      return ()
    return self._optional_args

  def LocalName(self):
    """The (file-)local name of the doc'd code element."""
    if self.locals.get('type') == vimdoc.DICTIONARY:
      return self.locals['dict']
    if 'name' not in self.locals:
      raise KeyError('Unnamed block.')
    return self.locals['name']

  def FullName(self):
    """The global (namespaced as necessary) name of the code element."""
    typ = self.locals.get('type')
    if typ == vimdoc.FUNCTION:
      if 'dict' in self.locals:
        attribute = self.locals.get('attribute', self.LocalName())
        return '{}.{}'.format(self.locals['dict'], attribute)
      if 'exception' in self.locals:
        return 'ERROR({})'.format(self.locals['exception'] or self.LocalName())
      return self.locals.get('namespace', '') + self.LocalName()
    if typ == vimdoc.SETTING:
      return 'g:{}'.format(self.LocalName())
    return self.LocalName()

  def TagName(self):
    """The tag string to use for links to the code element."""
    if self._is_secondary:
      return None
    typ = self.locals.get('type')
    if typ == vimdoc.FUNCTION:
      # Function tags end with (), except for the special case of ERROR() tags.
      if 'exception' not in self.locals:
        return '{}()'.format(self.FullName())
    if typ == vimdoc.COMMAND:
      return ':{}'.format(self.FullName())
    return self.FullName()

  def _ParseArgs(self, args):
    # Removes duplicates but retains order:
    self._required_args = list(OrderedDict.fromkeys(
        self._required_args + regex.required_arg.findall(args)))
    self._optional_args = list(OrderedDict.fromkeys(
        self._optional_args + regex.optional_arg.findall(args)))

  def __repr__(self):
    try:
      name = self.FullName()
    except KeyError:
      name = '?'
    return '{}({})'.format(self.__class__.__name__, name)

  def __lt__(self, other):
    return self.FullName() < other.FullName()

########NEW FILE########
__FILENAME__ = codeline
"""Parse vim code to mutate vimdoc blocks."""
import abc

import vimdoc


class CodeLine(object):
  """A line of code that affects the block above it.

  For example, the documentation above a function line will be modified to set
  type=FUNCTION.
  """
  __metaclass__ = abc.ABCMeta

  def Update(self, block):
    """Updates a single block."""

  def Affect(self, blocks, selection):
    """Affects all blocks above the code line.

    There can be multiple blocks above the code line, for example:

    " @usage item index list
    " Insert {item} at {list} after {index}
    " @usage value key dict
    " Insert {value} in {dict} under {key}
    function ...

    All blocks will be affected, regardless of selection. Then all blocks will
    be unselected: once the documentation hits the codeline, the blocks are
    done.

    Args:
      blocks: The blocks above this codeline.
      selection: the selected blocks.

    Yields:
        Each block after updating it.
    """
    for block in blocks:
      self.Update(block)
      yield block
    blocks[:] = []
    selection[:] = []


class Blank(CodeLine):
  """A blank line."""


class EndOfFile(CodeLine):
  """The end of the file."""


class Unrecognized(CodeLine):
  """A code line that doesn't deserve decoration."""

  def __init__(self, line):
    self.line = line

  def Affect(self, blocks, selection):
    """Documentation above unrecognized lines is ignored."""
    blocks[:] = []
    selection[:] = []
    return ()


class Definition(CodeLine):
  """An abstract definition line."""

  __metaclass__ = abc.ABCMeta

  def __init__(self, typ, name):
    self.name = name
    self.type = typ

  def Update(self, block):
    block.SetType(self.type)
    block.Local(name=self.name)


class Function(Definition):
  """Function definition."""

  def __init__(self, name, namespace, args):
    self.name = name
    self.namespace = namespace
    self.args = args
    super(Function, self).__init__(vimdoc.FUNCTION, name)

  def Update(self, block):
    super(Function, self).Update(block)
    if self.namespace:
      block.Local(namespace=self.namespace, local=True, args=self.args)
    else:
      block.Local(local=False, args=self.args)


class Command(Definition):
  """Command definition."""

  def __init__(self, name, **flags):
    self.flags = flags
    super(Command, self).__init__(vimdoc.COMMAND, name)

  def Update(self, block):
    """Updates one block above the command line."""
    super(Command, self).Update(block)
    # Usage is like:
    # [range][count]["x][N]MyCommand[!] {req1} {req2} [optional1] [optional2]
    head = ''
    if self.flags.get('range'):
      head += '[range]'
    if self.flags.get('count'):
      head += '[count]'
    if self.flags.get('register'):
      head += '["x]'
    if self.flags.get('buffer'):
      head += '[N]'
    head += '<>'
    if self.flags.get('bang'):
      head += '[!]'
    block.Local(head=head)


class Setting(Definition):
  def __init__(self, name):
    super(Setting, self).__init__(vimdoc.SETTING, name)


class Flag(Definition):
  def __init__(self, name):
    super(Flag, self).__init__(vimdoc.FLAG, name)

########NEW FILE########
__FILENAME__ = docline
"""Vimfile documentation lines, the stuff of vimdoc blocks."""
import abc

import vimdoc
from vimdoc import error
from vimdoc import regex
from vimdoc.block import Block


class DocLine(object):
  """One line of vim documentation."""

  __metaclass__ = abc.ABCMeta

  def Each(self, blocks, selection):
    """Iterates the selected blocks."""
    for i in selection:
      if i >= len(blocks):
        raise error.InvalidBlockNumber(i, blocks, selection)
      yield blocks[i]

  def Affect(self, blocks, selection):
    """Updates each selected block.

    Args:
      blocks: The different blocks defined so far.
      selection: The blocks being operated upon.
    Returns:
      The blocks ready to be closed (which is an empty list -- codelines are the
      ones who close blocks, not doclines.)
    """
    if not blocks:
      blocks.append(Block())
      selection.append(0)
    for block in self.Each(blocks, selection):
      self.Update(block)
    return ()

  @abc.abstractmethod
  def Update(self, block):
    """Update one block."""


class Text(DocLine):
  def __init__(self, line):
    self.line = line

  def Update(self, block):
    block.AddLine(self.line)


class BlockDirective(DocLine):
  """A line-spanning directive, like @usage."""

  __metaclass__ = abc.ABCMeta

  REGEX = regex.no_args

  def __init__(self, args):
    match = self.REGEX.match(args)
    if not match:
      raise error.InvalidBlockArgs(self.__class__.__name__, args)
    self.Assign(*match.groups())

  def Assign(self):
    pass


class All(BlockDirective):
  REGEX = regex.numbers_args

  def Assign(self, numbers):
    # @all blocks are one-indexed.
    numbers = numbers or ''
    self.blocks = [int(i) - 1 for i in regex.number_arg.findall(numbers)]

  def Affect(self, blocks, selection):
    if not self.blocks:
      selection[:] = range(len(blocks))
    else:
      selection[:] = self.blocks
    for i in selection:
      if i >= len(blocks):
        raise error.InvalidBlockNumber(i)
      blocks[i].SetType(True)
    return ()


class Author(BlockDirective):
  REGEX = regex.any_args

  def Assign(self, author):
    self.author = author

  def Update(self, block):
    block.Global(author=self.author)


class Backmatter(BlockDirective):
  REGEX = regex.backmatter_args

  def Assign(self, ident):
    self.id = ident

  def Update(self, block):
    block.SetType(vimdoc.BACKMATTER)
    block.Local(id=self.id)


class Default(BlockDirective):
  REGEX = regex.default_args

  def Assign(self, arg, value):
    self.arg = arg
    self.value = value

  def Update(self, block):
    block.Default(self.arg, self.value)


class Deprecated(BlockDirective):
  REGEX = regex.one_arg

  def Assign(self, reason):
    self.reason = reason

  def Update(self, block):
    block.Local(deprecated=self.reason)


# pylint: disable=g-bad-name
class Exception_(BlockDirective):
  REGEX = regex.maybe_word

  def Assign(self, word):
    self.word = word

  def Update(self, block):
    block.Local(exception=self.word)


class Dict(BlockDirective):
  REGEX = regex.dict_args

  def Assign(self, name, attribute=None):
    self.name = name
    self.attribute = attribute

  def Update(self, block):
    block.SetType(True)
    block.Local(dict=self.name)
    if self.attribute:
      block.SetType(vimdoc.FUNCTION)
      block.Local(attribute=self.attribute)
    # We can't set the dict type here because it may be set to Funtion type
    # later, and we don't want a type mismatch.


class Library(BlockDirective):
  def Update(self, block):
    block.Global(library=True)


class Order(BlockDirective):
  REGEX = regex.order_args

  def Assign(self, args):
    self.order = regex.order_arg.findall(args)

  def Update(self, block):
    block.Global(order=self.order)


class Private(BlockDirective):
  def Update(self, block):
    block.Local(private=True)


class Public(BlockDirective):
  def Update(self, block):
    block.Local(private=False)


class Section(BlockDirective):
  REGEX = regex.section_args

  def Assign(self, name, ident):
    self.name = name.replace('\\,', ',').replace('\\\\', '\\')
    self.id = ident

  def Update(self, block):
    block.SetType(vimdoc.SECTION)
    block.Local(name=self.name, id=self.id)


class Standalone(BlockDirective):
  def Update(self, block):
    block.Global(standalone=True)


class Stylized(BlockDirective):
  REGEX = regex.stylizing_args

  def Assign(self, stylization):
    self.stylization = stylization

  def Update(self, block):
    block.Global(stylization=self.stylization)


class SubSection(BlockDirective):
  REGEX = regex.any_args

  def Assign(self, name):
    self.name = name

  def Update(self, block):
    block.AddSubHeader(self.name)


class Tagline(BlockDirective):
  REGEX = regex.any_args

  def Assign(self, tagline):
    self.tagline = tagline

  def Update(self, block):
    block.Global(tagline=self.tagline)


class Throws(BlockDirective):
  REGEX = regex.throw_args

  def Assign(self, typ, description):
    if not regex.vim_error.match(typ):
      typ = 'ERROR({})'.format(typ)
    self.error = typ
    self.description = description

  def Update(self, block):
    block.Except(self.error, self.description)


class Header(BlockDirective):
  """A header directive, like @usage @function or @command."""

  __metaclass__ = abc.ABCMeta

  def Affect(self, blocks, selection):
    """Updates the block selection.

    If this block is already split into multiple sections, or if it already has
    a header, then a new section is created with this header. Otherwise, this
    header is set as the header for the single block.

    Args:
      blocks: The blocks defined in the documentation so far.
      selection: The blocks currently being acted on.
    Returns:
      The blocks ready to be closed (which is none).
    """
    if (len(blocks) != 1) or (blocks[0].header):
      # Mark this as a secondary block if there are other blocks above it that
      # are describing the same block. (This allows us to, for example, only add
      # the function tag to the FIRST block that describes the function and not
      # to subsequent blocks showing other ways to use the same function.)
      is_secondary = len(blocks) > 0
      newblock = Block(is_secondary=is_secondary)
      # If the first block has no header, copy its locals.
      if blocks and blocks[0].header is None:
        newblock.locals = dict(blocks[0].locals)
      blocks.append(newblock)
      selection[:] = [len(blocks) - 1]
    else:
      # There is only one block. Assert that it's selected.
      assert selection == [0], 'Singleton blocks must be selected.'
    for block in self.Each(blocks, selection):
      block.SetHeader(self)
      self.Update(block)
    return ()

  def Assign(self, usage):
    self.usage = usage
    self.reqs = regex.required_arg.findall(usage)
    self.opts = regex.optional_arg.findall(usage)

  def Update(self, block):
    pass

  def GenerateUsage(self, block):
    isfunc = block.locals.get('type') == vimdoc.FUNCTION
    sep = ', ' if isfunc else ' '
    extra_reqs = sep.join('{%s}' % r
                          for r in block.RequiredArgs()
                          if r not in self.reqs)
    extra_opts = sep.join('[%s]' % o
                          for o in block.OptionalArgs()
                          if o not in self.opts)
    return self.FillOut(block.FullName(), sep, extra_reqs, extra_opts)

  def FillOut(self, name, sep, extra_reqs, extra_opts):
    """Expands the usage line with the given arguments."""
    # The user may use the {] hole to place both required and optional args,
    # appropriately separated.
    if extra_reqs and extra_opts:
      extra_args = extra_reqs + sep + extra_opts
    else:
      extra_args = extra_reqs + extra_opts
    # Expand the argument holes.
    # Presumably, the user won't use both the arg hole and the required/optional
    # holes. If they do, then we'll dutifully replicate the args.
    usage = regex.arg_hole.sub(extra_args, self.usage)
    usage = regex.required_hole.sub(extra_reqs, usage)
    usage = regex.optional_hole.sub(extra_opts, usage)
    # Remove bad separators.
    usage = regex.bad_separator.sub('', usage)
    # Expand the name holes.
    usage = regex.name_hole.sub(name, usage)
    # Expand the hole escape sequences.
    usage = regex.namehole_escape.sub(r'<\1>', usage)
    usage = regex.requiredhole_escape.sub(r'{\1}', usage)
    usage = regex.optionalhole_escape.sub(r'[\1]', usage)
    return usage


class Command(Header):
  REGEX = regex.any_args

  def Update(self, block):
    block.SetType(vimdoc.COMMAND)


class Function(Header):
  REGEX = regex.any_args

  def Update(self, block):
    block.SetType(vimdoc.FUNCTION)


class Usage(Header):
  REGEX = regex.usage_args

  def GenerateUsage(self, block):
    """Generates the usage line. Syntax depends upon the block type."""
    normalize = lambda arg: arg if arg[0] in '[{' else ('{%s}' % arg)
    args = [normalize(arg) for arg in regex.usage_arg.findall(self.usage)]
    if block.locals.get('type') == vimdoc.FUNCTION:
      # Functions are like MyFunction({req1}, {req2}, [opt1])
      self.usage = '<>(%s)' % ', '.join(args)
    else:
      assert block.locals.get('type') == vimdoc.COMMAND
      # Commands are like :[range]MyCommand[!] {req1} {req2} [opt1]
      self.usage = ':%s %s' % (block.locals.get('head', '<>'), ' '.join(args))
    return super(Usage, self).GenerateUsage(block)


BLOCK_DIRECTIVES = {
    'all': All,
    'author': Author,
    'backmatter': Backmatter,
    'command': Command,
    'default': Default,
    'deprecated': Deprecated,
    'dict': Dict,
    'exception': Exception_,
    'function': Function,
    'library': Library,
    'order': Order,
    'private': Private,
    'public': Public,
    'section': Section,
    'standalone': Standalone,
    'stylized': Stylized,
    'subsection': SubSection,
    'tagline': Tagline,
    'throws': Throws,
    'usage': Usage,
}

########NEW FILE########
__FILENAME__ = error
"""Vimdoc error classes."""


class Error(Exception):
  pass


class DocumentationWarning(Warning):
  pass


class InvalidAddonInfo(Warning):
  pass


class ParseError(Error):
  def __init__(self, message, filename=None, lineno=None):
    self.filename = filename
    self.lineno = lineno
    super(ParseError, self).__init__(message)

  def __str__(self):
    parent = super(ParseError, self).__str__()
    if self.lineno is not None or self.filename is not None:
      lineno = '???' if self.lineno is None else ('%03d' % self.lineno)
      filename = '???' if self.filename is None else self.filename
      prefix = '{}.{}: '.format(filename, lineno)
    else:
      prefix = ''
    return prefix + parent


class ArgumentMismatch(Warning):
  pass


class TypeConflict(ParseError):
  def __init__(self, t1, t2, *args, **kwargs):
    super(TypeConflict, self).__init__(
        'Type {} is incompatible with type {}'.format(t1, t2),
        *args, **kwargs)


class InvalidBlockNumber(ParseError):
  def __init__(self, number, blocks, selection, *args, **kwargs):
    super(InvalidBlockNumber, self).__init__(
        'There is no block number {}. '
        'There are {} blocks. '
        'Current selection is {}'
        .format(number, len(blocks), selection),
        *args, **kwargs)


class InvalidBlockArgs(ParseError):
  def __init__(self, block, params, *args, **kwargs):
    super(InvalidBlockArgs, self).__init__(
        'Invalid args for block {}: "{}"'.format(block, params),
        *args, **kwargs)


class UnrecognizedBlockDirective(ParseError):
  def __init__(self, block, *args, **kwargs):
    super(UnrecognizedBlockDirective, self).__init__(
        'Unrecognized block directive "{}"'.format(block), *args, **kwargs)


class UnrecognizedInlineDirective(ParseError):
  def __init__(self, inline, *args, **kwargs):
    super(UnrecognizedInlineDirective, self).__init__(
        'Unrecognized inline directive "%s"' % inline, *args, **kwargs)


class CannotContinue(ParseError):
  pass


class RedundantControl(ParseError):
  def __init__(self, control, *args, **kwargs):
    super(RedundantControl, self).__init__(
        'Redundant control "{}"'.format(control),
        *args, **kwargs)


class InconsistentControl(ParseError):
  def __init__(self, control, old, new, *args, **kwargs):
    super(InconsistentControl, self).__init__(
        'Inconsistent control "{}" ({} vs {})'.format(control, old, new),
        *args, **kwargs)


class MultipleHeaders(ParseError):
  def __init__(self, *args, **kwargs):
    super(MultipleHeaders, self).__init__(
        'Block given multiple headers.',
        *args, **kwargs)


class InvalidBlock(ParseError):
  pass


class AmbiguousBlock(ParseError):
  def __init__(self, *args, **kwargs):
    super(AmbiguousBlock, self).__init__(
        'Block type is ambiguous.',
        *args, **kwargs)


class BadStructure(Error):
  pass


class NoSuchSection(BadStructure):
  def __init__(self, section):
    super(NoSuchSection, self).__init__(
        'Section {} never defined.'.format(section))


class NeglectedSections(BadStructure):
  def __init__(self, sections):
    super(NeglectedSections, self).__init__(
        'Sections {} not included in ordering.'.format(sections))

########NEW FILE########
__FILENAME__ = module
"""Vimdoc plugin management."""
from collections import OrderedDict
import itertools
import json
import os
import warnings

import vimdoc
from vimdoc import error
from vimdoc import parser
from vimdoc.block import Block

# Plugin subdirectories that should be crawled by vimdoc.
DOC_SUBDIRS = [
    'plugin',
    'instant',
    'autoload',
    'syntax',
    'indent',
    'ftdetect',
    'ftplugin',
]


class Module(object):
  """Manages a set of source files that all output to the same help file."""

  def __init__(self, name, plugin):
    self.name = name
    self.plugin = plugin
    self.sections = OrderedDict()
    self.backmatters = {}
    self.collections = {}
    self.order = None

  def Merge(self, block, namespace=None):
    """Merges a block with the module."""
    typ = block.locals.get('type')

    # This block doesn't want to be spoken to.
    if not typ:
      return
    # If the type still hasn't been set, it never will be.
    if typ is True:
      raise error.AmbiguousBlock

    block.Local(namespace=namespace)
    # Consume module-level metadata
    if 'order' in block.globals:
      if self.order is not None:
        raise error.RedundantControl('order')
      self.order = block.globals['order']
    self.plugin.Merge(block)

    # Sections and Backmatter are specially treated.
    if typ == vimdoc.SECTION:
      self.sections[block.locals.get('id')] = block
    elif typ == vimdoc.BACKMATTER:
      self.backmatters[block.locals.get('id')] = block
    else:
      collection_type = self.plugin.GetCollectionType(block)
      if collection_type is not None:
        self.collections.setdefault(collection_type, []).append(block)

  def LookupTag(self, typ, name):
    return self.plugin.LookupTag(typ, name)

  def Close(self):
    """Closes the module.

    All default sections that have not been overridden will be created.
    """
    if vimdoc.FUNCTION in self.collections and 'functions' not in self.sections:
      functions = Block()
      functions.SetType(vimdoc.SECTION)
      functions.Local(id='functions', name='Functions')
      self.Merge(functions)
    if (vimdoc.EXCEPTION in self.collections
        and 'exceptions' not in self.sections):
      exceptions = Block()
      exceptions.SetType(vimdoc.SECTION)
      exceptions.Local(id='exceptions', name='Exceptions')
      self.Merge(exceptions)
    if vimdoc.COMMAND in self.collections and 'commands' not in self.sections:
      commands = Block()
      commands.SetType(vimdoc.SECTION)
      commands.Local(id='commands', name='Commands')
      self.Merge(commands)
    if vimdoc.DICTIONARY in self.collections and 'dicts' not in self.sections:
      dicts = Block()
      dicts.SetType(vimdoc.SECTION)
      dicts.Local(id='dicts', name='Dictionaries')
      self.Merge(dicts)
    if ((vimdoc.FLAG in self.collections or
         vimdoc.SETTING in self.collections) and
        'config' not in self.sections):
      config = Block()
      config.SetType(vimdoc.SECTION)
      config.Local(id='config', name='Configuration')
      self.Merge(config)
    if not self.order:
      self.order = []
      for builtin in [
          'intro',
          'config',
          'commands',
          'autocmds',
          'settings',
          'dicts',
          'functions',
          'exceptions',
          'mappings',
          'about']:
        if builtin in self.sections or builtin in self.backmatters:
          self.order.append(builtin)
    for backmatter in self.backmatters:
      if backmatter not in self.sections:
        raise error.NoSuchSection(backmatter)
    known = set(itertools.chain(self.sections, self.backmatters))
    if known.difference(self.order):
      raise error.NeglectedSections(known)
    # Sections are now in order.
    for key in self.order:
      if key in self.sections:
        # Move to end.
        self.sections[key] = self.sections.pop(key)

  def Chunks(self):
    for ident, section in self.sections.items():
      yield section
      if ident == 'functions':
        # Sort by namespace, but preserve order within the same namespace. This
        # lets us avoid variability in the order files are traversed without
        # losing all useful order information.
        collection = sorted(
            self.collections.get(vimdoc.FUNCTION, ()),
            key=lambda x: x.locals.get('namespace', ''))
        for block in collection:
          if 'dict' not in block.locals and 'exception' not in block.locals:
            yield block
      if ident == 'commands':
        for block in self.collections.get(vimdoc.COMMAND, ()):
          yield block
      if ident == 'dicts':
        for block in sorted(self.collections.get(vimdoc.DICTIONARY, ())):
          yield block
          collection = sorted(
              self.collections.get(vimdoc.FUNCTION, ()),
              key=lambda x: x.locals.get('namespace', ''))
          for func in collection:
            if func.locals.get('dict') == block.locals['dict']:
              yield func
      if ident == 'exceptions':
        for block in self.collections.get(vimdoc.EXCEPTION, ()):
          yield block
      if ident == 'config':
        for block in self.collections.get(vimdoc.FLAG, ()):
          yield block
        for block in self.collections.get(vimdoc.SETTING, ()):
          yield block
      if ident in self.backmatters:
        yield self.backmatters[ident]


class VimPlugin(object):
  """State for entire plugin (potentially multiple modules)."""

  def __init__(self, name):
    self.name = name
    self.collections = {}
    self.tagline = None
    self.author = None
    self.stylization = None
    self.library = None

  def ConsumeMetadata(self, block):
    assert block.locals.get('type') in [vimdoc.SECTION, vimdoc.BACKMATTER]
    # Error out for deprecated controls.
    if 'author' in block.globals:
      raise error.InvalidBlock(
          'Invalid directive @author.'
          ' Specify author field in addon-info.json instead.')
    if 'tagline' in block.globals:
      raise error.InvalidBlock(
          'Invalid directive @tagline.'
          ' Specify description field in addon-info.json instead.')
    for control in ['stylization', 'library']:
      if control in block.globals:
        if getattr(self, control) is not None:
          raise error.RedundantControl(control)
        setattr(self, control, block.globals[control])

  def LookupTag(self, typ, name):
    """Returns the tag name for the given type and name."""
    # Support both @command(Name) and @command(:Name).
    fullname = (
        typ == vimdoc.COMMAND and name.lstrip(':') or name)
    block = None
    if typ in self.collections:
      collection = self.collections[typ]
      candidates = [x for x in collection if x.FullName() == fullname]
      if len(candidates) > 1:
        raise KeyError('Found multiple %ss named %s' % (typ, name))
      if candidates:
        block = candidates[0]
    if block is None:
      # Create a dummy block to get default tag.
      block = Block()
      block.SetType(typ)
      block.Local(name=fullname)
    return block.TagName()

  def GetCollectionType(self, block):
    typ = block.locals.get('type')

    # The inclusion of function docs depends upon the module type.
    if typ == vimdoc.FUNCTION:
      # Exclude deprecated functions
      if block.locals.get('deprecated'):
        return None
      # If this is a library module, exclude private functions.
      if self.library and block.locals.get('private'):
        return None
      # If this is a non-library, exclude non-explicitly-public functions.
      if not self.library and block.locals.get('private', True):
        return None
      if 'exception' in block.locals:
        return vimdoc.EXCEPTION

    return typ

  def Merge(self, block):
    typ = block.locals.get('type')
    if typ in [vimdoc.SECTION, vimdoc.BACKMATTER]:
      self.ConsumeMetadata(block)
    else:
      collection_type = self.GetCollectionType(block)
      if collection_type is not None:
        self.collections.setdefault(collection_type, []).append(block)


def Modules(directory):
  """Creates modules from a plugin directory.

  Note that there can be many, if a plugin has standalone parts that merit their
  own helpfiles.

  Args:
    directory: The plugin directory.
  Yields:
    Module objects as necessary.
  """
  directory = directory.rstrip(os.path.sep)
  addon_info = None
  # Check for module metadata in addon-info.json (if it exists).
  addon_info_path = os.path.join(directory, 'addon-info.json')
  if os.path.isfile(addon_info_path):
    try:
      with open(addon_info_path, 'r') as addon_info_file:
        addon_info = json.loads(addon_info_file.read())
    except (IOError, ValueError) as e:
      warnings.warn(
          'Failed to read file {}. Error was: {}'.format(addon_info_path, e),
          error.InvalidAddonInfo)
  plugin_name = None
  # Use plugin name from addon-info.json if available. Fall back to dir name.
  addon_info = addon_info or {}
  plugin_name = addon_info.get(
      'name', os.path.basename(os.path.abspath(directory)))
  plugin = VimPlugin(plugin_name)

  # Set module metadata from addon-info.json.
  if addon_info is not None:
    # Valid addon-info.json. Apply addon metadata.
    if 'author' in addon_info:
      plugin.author = addon_info['author']
    if 'description' in addon_info:
      plugin.tagline = addon_info['description']

  # Crawl plugin dir and collect parsed blocks for each file path.
  paths_and_blocks = []
  standalone_paths = []
  autoloaddir = os.path.join(directory, 'autoload')
  for (root, dirs, files) in os.walk(directory):
    # Prune non-standard top-level dirs like 'test'.
    if root == directory:
      dirs[:] = [x for x in dirs if x in DOC_SUBDIRS + ['after']]
    if root == os.path.join(directory, 'after'):
      dirs[:] = [x for x in dirs if x in DOC_SUBDIRS]
    for f in files:
      filename = os.path.join(root, f)
      if os.path.splitext(filename)[1] == '.vim':
        with open(filename) as filehandle:
          blocks = list(parser.ParseBlocks(filehandle, filename))
        relative_path = os.path.relpath(filename, directory)
        paths_and_blocks.append((relative_path, blocks))
        if filename.startswith(autoloaddir):
          if blocks and blocks[0].globals.get('standalone'):
            standalone_paths.append(relative_path)

  docdir = os.path.join(directory, 'doc')
  if not os.path.isdir(docdir):
    os.mkdir(docdir)

  modules = []

  main_module = Module(plugin_name, plugin)
  for (path, blocks) in paths_and_blocks:
    # Skip standalone paths.
    if GetMatchingStandalonePath(path, standalone_paths) is not None:
      continue
    namespace = None
    if path.startswith('autoload' + os.path.sep):
      namespace = GetAutoloadNamespace(os.path.relpath(path, 'autoload'))
    for block in blocks:
      main_module.Merge(block, namespace=namespace)
  modules.append(main_module)

  # Process standalone modules.
  standalone_modules = {}
  for (path, blocks) in paths_and_blocks:
    standalone_path = GetMatchingStandalonePath(path, standalone_paths)
    # Skip all but standalone paths.
    if standalone_path is None:
      continue
    assert path.startswith('autoload' + os.path.sep)
    namespace = GetAutoloadNamespace(os.path.relpath(path, 'autoload'))
    standalone_module = standalone_modules.get(standalone_path)
    # Initialize module if this is the first file processed from it.
    if standalone_module is None:
      standalone_module = Module(namespace.rstrip('#'), plugin)
      standalone_modules[standalone_path] = standalone_module
      modules.append(standalone_module)
    for block in blocks:
      standalone_module.Merge(block, namespace=namespace)

  for module in modules:
    module.Close()
    yield module


def GetAutoloadNamespace(filepath):
  return (os.path.splitext(filepath)[0]).replace('/', '#') + '#'


def GetMatchingStandalonePath(path, standalones):
  for standalone in standalones:
    # Check for filename match.
    if path == standalone:
      return standalone
    # Strip off '.vim' and check for directory match.
    if path.startswith(os.path.splitext(standalone)[0] + os.path.sep):
      return standalone
  return None

########NEW FILE########
__FILENAME__ = output
"""Vim helpfile outputter."""
import os
import textwrap
import warnings

import vimdoc
from vimdoc import error
from vimdoc import paragraph
from vimdoc import regex


class Helpfile(object):
  """Outputs vim help files."""

  WIDTH = 78
  TAB = '  '

  def __init__(self, module, docdir):
    self.module = module
    self.docdir = docdir

  def Filename(self):
    help_filename = self.module.name.replace('#', '-')
    return help_filename + '.txt'

  def Write(self):
    filename = os.path.join(self.docdir, self.Filename())
    with open(filename, 'w') as self.file:
      self.WriteHeader()
      self.WriteTableOfContents()
      for chunk in self.module.Chunks():
        self.WriteChunk(chunk)
      self.WriteFooter()

  def WriteHeader(self):
    """Writes a plugin header."""
    # The first line should conform to ':help write-local-help', with a tag for
    # the filename followed by a tab and the tagline (if present).
    line = self.Tag(self.Filename())
    if self.module.plugin.tagline:
      line = '{}\t{}'.format(line, self.module.plugin.tagline)
    # Use Print directly vs. WriteLine so tab isn't expanded by TextWrapper.
    self.Print(line)
    # Next write a line with the author (if present) and tags.
    tag = self.Tag(self.module.name)
    if self.module.plugin.stylization:
      tag = '{} {}'.format(self.Tag(self.module.plugin.stylization), tag)
    if self.module.plugin.author:
      self.WriteLine(self.module.plugin.author, right=tag)
    else:
      self.WriteLine(right=tag)
    self.WriteLine()

  def WriteTableOfContents(self):
    """Writes the table of contents."""
    self.WriteRow()
    self.WriteLine('CONTENTS', right=self.Tag(self.Slug('contents')))
    for i, block in enumerate(self.module.sections.values()):
      assert 'id' in block.locals
      assert 'name' in block.locals
      line = '%d. %s' % (i + 1, block.locals['name'])
      slug = self.Slug(block.locals['id'])
      self.WriteLine(line, indent=1, right=self.Link(slug), fill='.')
    self.WriteLine()

  def WriteChunk(self, chunk):
    """Writes one vimdoc Block."""
    assert 'type' in chunk.locals
    typ = chunk.locals['type']
    if typ == vimdoc.SECTION:
      self.WriteSection(chunk)
    elif typ == vimdoc.FUNCTION:
      if 'exception' in chunk.locals:
        self.WriteSmallBlock(chunk.FullName(), chunk)
      else:
        self.WriteLargeBlock(chunk)
    elif typ == vimdoc.COMMAND:
      self.WriteLargeBlock(chunk)
    elif typ == vimdoc.SETTING:
      self.WriteSmallBlock(chunk.FullName(), chunk)
    elif typ == vimdoc.FLAG:
      self.WriteSmallBlock(self.Slug(chunk.FullName(), ':'), chunk)
    elif typ == vimdoc.DICTIONARY:
      self.WriteSmallBlock(self.Slug(chunk.FullName(), '.'), chunk)
    elif typ == vimdoc.BACKMATTER:
      self.WriteParagraphs(chunk)

  def WriteSection(self, block):
    """Writes a section-type block."""
    self.WriteRow()
    name = block.locals['name']
    ident = block.locals['id']
    slug = self.Slug(ident)
    self.WriteLine(name.upper(), right=self.Tag(slug))
    if block.paragraphs:
      self.WriteLine()
    self.WriteParagraphs(block)

  def WriteLargeBlock(self, block):
    """Writes a large (function, command, etc.) type block."""
    if not block.paragraphs:
      warnings.warn(
          'Undocumented {} {}'.format(
              block.locals.get('type').lower(),
              block.FullName()),
          error.DocumentationWarning)
      return
    assert 'usage' in block.locals
    self.WriteLine(
        # The leader='' makes it indent once on subsequent lines.
        block.locals['usage'], right=self.Tag(block.TagName()), leader='')
    self.WriteParagraphs(block, indent=1)

  def WriteSmallBlock(self, slug, block):
    """Writes a small (flag, setting, etc.) type block."""
    self.WriteLine(right=self.Tag(slug))
    self.WriteParagraphs(block)

  def WriteFooter(self):
    """Writes a plugin footer."""
    self.WriteLine()
    self.WriteLine('vim:tw={}:ts=8:ft=help:norl:'.format(self.WIDTH))

  def WriteParagraphs(self, block, indent=0):
    """Writes a series of text with optional indents."""
    assert 'namespace' in block.locals
    for p in block.paragraphs:
      self.WriteParagraph(p, block.locals['namespace'], indent=indent)
    self.WriteLine()

  def WriteParagraph(self, p, namespace, indent=0):
    """Writes one paragraph."""
    if isinstance(p, paragraph.ListItem):
      # - indents lines after the first
      if p.leader == '-':
        leader = ''
      # + indents the whole paragraph
      elif p.leader == '+':
        leader = '  '
      # Other leaders (*, 1., etc.) are copied verbatim, indented by one
      # shiftwidth.
      else:
        leader = p.leader + ' '
        indent += 1
      self.WriteLine(self.Expand(
          p.text, namespace), indent=indent, leader=leader)
    elif isinstance(p, paragraph.TextParagraph):
      self.WriteLine(self.Expand(p.text, namespace), indent=indent)
    elif isinstance(p, paragraph.BlankLine):
      self.WriteLine()
    elif isinstance(p, paragraph.CodeBlock):
      self.WriteLine('>')
      for line in p.lines:
        self.WriteCodeLine(line, namespace, indent=indent)
      self.WriteLine('<')
    elif isinstance(p, paragraph.DefaultLine):
      self.WriteLine(self.Default(
          p.arg, p.value, namespace), indent=indent)
    elif isinstance(p, paragraph.ExceptionLine):
      self.WriteLine(self.Throws(
          p.exception, p.description, namespace), indent=indent)
    elif isinstance(p, paragraph.SubHeaderLine):
      self.WriteLine(p.name.upper(), indent=indent)
    else:
      raise ValueError('What kind of paragraph is {}?'.format(p))

  def WriteCodeLine(self, text, namespace, indent=0):
    """Writes one line of code."""
    wrapper = textwrap.TextWrapper(
        width=self.WIDTH,
        initial_indent=(indent * self.TAB),
        subsequent_indent=((indent + 2) * self.TAB))
    for line in wrapper.wrap(self.Expand(text, namespace)):
      self.Print(line)

  def Print(self, line, end='\n'):
    """Outputs a line to the file."""
    assert len(line) <= self.WIDTH
    if self.file is None:
      raise ValueError('Helpfile writer not yet given helpfile to write.')
    self.file.write(line + end)

  def WriteRow(self):
    """Writes a horizontal divider row."""
    self.Print('=' * self.WIDTH)

  def WriteLine(self, text='', right='', indent=0, leader=None, fill=' '):
    """Writes one line ouf output, breaking it up as needed."""
    if leader is not None:
      initial_indent = (indent * self.TAB) + leader
      subsequent_indent = (indent + 1) * self.TAB
    else:
      initial_indent = indent * self.TAB
      subsequent_indent = indent * self.TAB
    wrapper = textwrap.TextWrapper(
        width=self.WIDTH,
        initial_indent=initial_indent,
        subsequent_indent=subsequent_indent,
        break_on_hyphens=False)
    lines = wrapper.wrap(text)
    lines = lines or ['']
    lastlen = len(lines[-1])
    rightlen = len(right)
    assert rightlen <= self.WIDTH
    if right and lastlen + rightlen + 1 > self.WIDTH:
      lines.append('')
      lastlen = 0
    if right:
      padding = self.WIDTH - lastlen - rightlen
      assert padding >= 0
      lines[-1] += (fill * padding) + right
    for line in lines:
      self.Print(line)

  def Slug(self, slug, sep='-'):
    return '{}{}{}'.format(self.module.name, sep, slug)

  def Tag(self, slug):
    return '' if slug is None else '*{}*'.format(slug)

  def Link(self, slug):
    return '|{}|'.format(slug)

  def Throws(self, err, description, namespace):
    return 'Throws {} {}'.format(err, self.Expand(description, namespace))

  def Default(self, arg, value, namespace):
    return '[{}] is {} if omitted.'.format(arg, self.Expand(value, namespace))

  def Expand(self, text, namespace):
    def Expander(match):
      expanded = self.ExpandInline(*match.groups(), namespace=namespace)
      if expanded is None:
        # Leave unrecognized directives unexpanded. Might be false positives.
        return match.group(0)
      return expanded
    return regex.inline_directive.sub(Expander, text)

  def ExpandInline(self, inline, element, namespace):
    """Expands inline directives, like @function()."""
    if inline == 'section':
      return self.Link(self.Slug(element))
    elif inline == 'function':
      # If a user says @function(#Foo) then that points to in#this#file#Foo.
      if element.startswith('#'):
        element = (namespace or '') + element[1:]
      return self.Link(self.module.LookupTag(vimdoc.FUNCTION, element))
    elif inline == 'command':
      return self.Link(self.module.LookupTag(vimdoc.COMMAND, element))
    elif inline == 'flag':
      return self.Link(
          self.Slug(self.module.LookupTag(vimdoc.FLAG, element), ':'))
    elif inline == 'setting':
      setting = element if element.startswith('g:') else 'g:' + element
      return self.Link('g:' + self.module.LookupTag(vimdoc.SETTING, setting))
    elif inline == 'dict':
      return self.Link(self.Slug(self.module.LookupTag(
          vimdoc.DICTIONARY, element), '.'))
    elif inline == 'plugin':
      if element == 'author':
        return self.module.plugin.author
      elif element == 'stylized':
        return self.module.plugin.stylization
      elif element == 'name':
        return self.module.name
      elif element is None:
        return self.module.plugin.stylization
      else:
        raise error.UnrecognizedInlineDirective(
            '{} attribute in {}'.format(element, inline))
    return None

########NEW FILE########
__FILENAME__ = paragraph
"""Docline aggregation handlers."""
import abc


class Paragraph(object):
  """Aggregates doclines into paragraph objects.

  It's necessary to know where paragraphs start and end so that we can reflow
  text without joining too many lines. Consider:

    some text that wraps and should all
    be joined into one line
    1. must be distinguished from list items
       which must not be joined with previous lines.
  """

  __metaclass__ = abc.ABCMeta

  def __init__(self):
    self.open = True

  def Close(self):
    self.open = False

  # It's an abstract base class, pylint.
  # pylint:disable-msg=unused-argument
  def AddLine(self, text):
    if not self.open:
      raise ValueError("Can't add to closed paragraphs.")


class TextParagraph(Paragraph):
  def __init__(self):
    super(TextParagraph, self).__init__()
    self.text = ''

  def AddLine(self, text):
    super(TextParagraph, self).AddLine(text)
    if self.text:
      self.text += ' ' + text
    else:
      self.text = text


class BlankLine(Paragraph):
  def __init__(self):
    super(BlankLine, self).__init__()
    self.Close()


class CodeBlock(Paragraph):
  def __init__(self):
    super(CodeBlock, self).__init__()
    self.lines = []

  def AddLine(self, text):
    super(CodeBlock, self).AddLine(text)
    self.lines.append(text)


class DefaultLine(Paragraph):
  def __init__(self, arg, value):
    super(DefaultLine, self).__init__()
    self.open = False
    self.arg = arg
    self.value = value


class ListItem(TextParagraph):
  def __init__(self, leader='*', level=0):
    super(ListItem, self).__init__()
    self.leader = leader
    self.level = level


class ExceptionLine(Paragraph):
  def __init__(self, exception, description):
    super(ExceptionLine, self).__init__()
    self.open = False
    self.exception = exception
    self.description = description


class SubHeaderLine(Paragraph):
  def __init__(self, name):
    super(SubHeaderLine, self).__init__()
    self.open = False
    self.name = name


class Paragraphs(list):
  """A manager for many paragraphs.

  When given a line of text (with an attached type), the Paragraphs object
  decides whether to append it to the current paragraph or start a new paragraph
  (usually by checking if the types match).
  """

  def __init__(self):
    super(Paragraphs, self).__init__()

  def SetType(self, cls, *args):
    if not self.IsType(cls):
      self.append(cls(*args))

  def IsType(self, cls):
    return self and self[-1].open and isinstance(self[-1], cls)

  def AddLine(self, *args):
    # Lines are text by default.
    if not (self and self[-1].open):
      raise ValueError("Paragraph manager doesn't have an open paragraph.")
    self[-1].AddLine(*args)

  def Close(self):
    if self:
      self[-1].Close()

########NEW FILE########
__FILENAME__ = parser
"""The vimdoc parser."""
from vimdoc import codeline
from vimdoc import docline

from vimdoc import error
from vimdoc import regex


def IsComment(line):
  return regex.comment_leader.match(line)


def IsContinuation(line):
  return regex.line_continuation.match(line)


def StripContinuator(line):
  assert regex.line_continuation.match(line)
  return regex.line_continuation.sub('', line)


def EnumerateStripNewlinesAndJoinContinuations(lines):
  """Preprocesses the lines of a vimscript file.

  Enumerates the lines, strips the newlines from the end, and joins the
  continuations.

  Args:
    lines: The lines of the file.
  Yields:
    Each preprocessed line.
  """
  lineno, cached = (None, None)
  for i, line in enumerate(lines):
    line = line.rstrip('\n')
    if IsContinuation(line):
      if cached is None:
        raise error.CannotContinue('No preceeding line.', i)
      elif IsComment(cached) and not IsComment(line):
        raise error.CannotContinue('No comment to continue.', i)
      else:
        cached += StripContinuator(line)
      continue
    if cached is not None:
      yield lineno, cached
    lineno, cached = (i, line)
  if cached is not None:
    yield lineno, cached


def EnumerateParsedLines(lines):
  vimdoc_mode = False
  for i, line in EnumerateStripNewlinesAndJoinContinuations(lines):
    # The intro chunk doesn't need the double-quote introduction (but leave
    # explicit vimdoc leaders alone to be detected and stripped below).
    if i == 0 and IsComment(line) and not regex.vimdoc_leader.match(line):
      vimdoc_mode = True
    if not vimdoc_mode:
      if regex.vimdoc_leader.match(line):
        vimdoc_mode = True
        # There's no need to yield the blank line if it's an empty starter line.
        # For example, in:
        # ""
        # " @usage whatever
        # " description
        # There's no need to yield the first docline as a blank.
        if not regex.empty_vimdoc_leader.match(line):
          # A starter line starts with two comment leaders.
          # If we strip one of them it's a normal comment line.
          yield i, ParseCommentLine(regex.comment_leader.sub('', line))
    elif IsComment(line):
      yield i, ParseCommentLine(line)
    else:
      vimdoc_mode = False
      yield i, ParseCodeLine(line)


def ParseCodeLine(line):
  """Parses one line of code and creates the appropriate CodeLine."""
  if regex.blank_code_line.match(line):
    return codeline.Blank()
  fmatch = regex.function_line.match(line)
  if fmatch:
    namespace, name, args = fmatch.groups()
    return codeline.Function(name, namespace, regex.function_arg.findall(args))
  cmatch = regex.command_line.match(line)
  if cmatch:
    args, name = cmatch.groups()
    flags = {
        'bang': '-bang' in args,
        'range': '-range' in args,
        'count': '-count' in args,
        'register': '-register' in args,
        'buffer': '-buffer' in args,
        'bar': '-bar' in args,
    }
    return codeline.Command(name, **flags)
  smatch = regex.setting_line.match(line)
  if smatch:
    name, = smatch.groups()
    return codeline.Setting(name)
  flagmatch = regex.flag_line.match(line)
  if flagmatch:
    a, b = flagmatch.groups()
    return codeline.Flag(a or b)
  return codeline.Unrecognized(line)


def ParseCommentLine(line):
  """Parses one line of documentation and creates the appropriate DocLine."""
  block = regex.block_directive.match(line)
  if block:
    return ParseBlockDirective(*block.groups())
  return docline.Text(regex.comment_leader.sub('', line))


def ParseBlockDirective(name, rest):
  if name in docline.BLOCK_DIRECTIVES:
    try:
      return docline.BLOCK_DIRECTIVES[name](rest)
    except ValueError:
      raise error.InvalidBlockArgs(rest)
  raise error.UnrecognizedBlockDirective(name)


def ParseBlocks(lines, filename):
  blocks = []
  selection = []
  lineno = 0
  try:
    for lineno, line in EnumerateParsedLines(lines):
      for block in line.Affect(blocks, selection):
        yield block.Close()
    for block in codeline.EndOfFile().Affect(blocks, selection):
      yield block.Close()
  except error.ParseError as e:
    e.lineno = lineno + 1
    e.filename = filename
    raise

########NEW FILE########
__FILENAME__ = regex
# -*- coding: utf-8 -*-
"""When you gaze into the abyss, the abyss gazes also into you.

>>> comment_leader.match('  echo "string"')
>>> comment_leader.match('  " Woot') is not None
True
>>> comment_leader.match('"') is not None
True
>>> comment_leader.sub('', '" foo')
'foo'
>>> comment_leader.sub('', '"bar')
'bar'

>>> line_continuation.match('  foo')
>>> line_continuation.match(' \\  foo') is not None
True

>>> blank_comment_line.match('')
>>> blank_comment_line.match('" foo')
>>> blank_comment_line.match('"') is not None
True
>>> blank_comment_line.match('      "         ') is not None
True

>>> blank_code_line.match('foo')
>>> blank_code_line.match('"')
>>> blank_code_line.match('    ') is not None
True
>>> blank_code_line.match('') is not None
True

>>> block_directive.match('  foo')
>>> block_directive.match('  " foo')
>>> block_directive.match('  " @foo').groups()
('foo', '')
>>> block_directive.match('  " @foo bar baz').groups()
('foo', 'bar baz')

>>> section_args.match('')
>>> section_args.match('Introduction').groups()
('Introduction', None)
>>> section_args.match('The Beginning, beg').groups()
('The Beginning', 'beg')

>>> backmatter_args.match('123')
>>> backmatter_args.match('foo').groups()
('foo',)

>>> dict_args.match('MyDict attr')
>>> dict_args.match('MyDict').groups()
('MyDict', None)
>>> dict_args.match('MyDict.attr').groups()
('MyDict', 'attr')

>>> usage_args.match('foo - bar - baz')
>>> usage_args.match('{foo} bar [][baz]') is not None
True
>>> usage_args.match('{foo...} bar... [][baz...]') is not None
True
>>> usage_arg.findall('{foo} bar [][baz]')
['{foo}', 'bar', '[]', '[baz]']
>>> usage_arg.match('{one..} two.. [three..]')
>>> usage_arg.findall('{one...} two... [three...]')
['{one...}', 'two...', '[three...]']

>>> no_args.match('foo')
>>> no_args.match('') is not None
True

>>> any_args.match('foo') is not None
True
>>> any_args.match('') is not None
True

>>> one_arg.match('foo') is not None
True
>>> one_arg.match('') is None
True

>>> maybe_word.match('Hello There')
>>> maybe_word.match('HelloThere') is not None
True
>>> maybe_word.match('') is not None
True

>>> throw_args.match('-@!813')
>>> throw_args.match('MyError').groups()
('MyError', None)
>>> throw_args.match('MyError on occasion').groups()
('MyError', 'on occasion')

>>> default_args.match('foo!bar')
>>> default_args.match('{foo}=bar')
>>> default_args.match('[foo]=bar').groups()
('[foo]', 'bar')
>>> default_args.match('foo=bar').groups()
('foo', 'bar')
>>> default_args.match('someVar = Some weird ==symbols==').groups()
('someVar', 'Some weird ==symbols==')

>>> order_args.match('some* weird! id"s')
>>> order_args.match('foo bar baz') is not None
True
>>> order_args.match('foo bar baz +').groups()
('foo bar baz +',)
>>> order_arg.findall('foo bar baz -')
['foo', 'bar', 'baz', '-']

>>> stylizing_args.match('Your Plugin')
>>> stylizing_args.match('MyPlugin').groups()
('MyPlugin',)
>>> stylizing_args.match('っoの').groups()
('\\xe3\\x81\\xa3o\\xe3\\x81\\xae',)

>>> function_line.match('foo bar')
>>> function_line.match('fu MyFunction()').groups()
(None, 'MyFunction', '')
>>> function_line.match('funct namespace#MyFunction(foo, bar)').groups()
('namespace#', 'MyFunction', 'foo, bar')
>>> function_line.match('fu!a#b#c#D(...) abort dict range').groups()
('a#b#c#', 'D', '...')

>>> command_line.match('com -nargs=+ -bang MyCommand call #this').groups()
('-nargs=+ -bang ', 'MyCommand')

>>> setting_line.match('let s:myglobal_var = 1')
>>> setting_line.match('let g:myglobal_var = 1').groups()
('myglobal_var',)

>>> flag_line.match("call s:plugin.Flag('myflag')").groups()
('myflag', None)
>>> flag_line.match('cal g:my["flags"].Flag("myflag")').groups()
(None, 'myflag')
>>> flag_line.match("call s:plugin.Flag('Some weird '' flag')").groups()
("Some weird '' flag", None)
>>> flag_line.match(r'call s:plugin.Flag("Another \\" weird flag")').groups()
(None, 'Another \\\\" weird flag')

>>> numbers_args.match('1 two 3')
>>> numbers_args.match('1 2 3').groups()
('1 2 3',)
>>> number_arg.findall('1 2 3')
['1', '2', '3']

>>> vim_error.match('EVERYTHING')
>>> vim_error.match('E101') is not None
True

>>> inline_directive.match('@function(bar)').groups()
('function', 'bar')
>>> inline_directive.sub(
...      lambda match: '[{}]'.format(match.group(2)),
...      'foo @function(bar) baz @link(quux) @this')
'foo [bar] baz [quux] [None]'

>>> function_arg.findall('foo, bar, baz, ...')
['foo', 'bar', 'baz', '...']

>>> bad_separator.search('foo, bar, baz')
>>> bad_separator.search('foo bar baz')
>>> bad_separator.search('foo, , bar, baz') is not None
True
>>> bad_separator.search('foo  bar  baz') is not None
True
>>> bad_separator.sub('', 'foo  bar, , baz')
'foo bar, baz'

>>> vimdoc_leader.match('"" Foo') is not None
True
>>> vimdoc_leader.match('""') is not None
True
>>> vimdoc_leader.match('" " ')
>>> empty_vimdoc_leader.match('  ""') is not None
True
>>> empty_vimdoc_leader.match('""  ')

"""
import re


def _DelimitedRegex(pattern):
  return re.compile(r"""
    # Shouldn't follow any non-whitespace character.
    (?<!\S)
    # pattern
    (?:{})
    # Shouldn't be directly followed by alphanumeric (but "," and "." are okay).
    (?!\w)
  """.format(pattern), re.VERBOSE)


# Regular expression soup!
vimdoc_leader = re.compile(r'^\s*"" ?')
empty_vimdoc_leader = re.compile(r'^\s*""$')
comment_leader = re.compile(r'^\s*" ?')
line_continuation = re.compile(r'^\s*\\')
blank_comment_line = re.compile(r'^\s*"\s*$')
blank_code_line = re.compile(r'^\s*$')
block_directive = re.compile(r'^\s*"\s*@([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+|$)(.*)')
section_args = re.compile(r"""
  ^
  # MATCH GROUP 1: The Name
  (
    # Non-commas or escaped commas or escaped escapes.
    (?:[^\\,]|\\.)+
  )
  # Optional identifier
  (?:
    # Separated by comma and whitespace.
    ,\s*
    # MATCHGROUP 2: The identifier
    ([a-zA-Z_-][a-zA-Z0-9_-]*)
  )?
  $
""", re.VERBOSE)
backmatter_args = re.compile(r'([a-zA-Z_-][a-zA-Z0-9_-]*)')
dict_args = re.compile(r"""
  ^([a-zA-Z_][a-zA-Z0-9]*)(?:\.([a-zA-Z_][a-zA-Z0-9_]*))?$
""", re.VERBOSE)
default_args = re.compile(r"""
  ^( # MATCH GROUP 1: The variable name.
    (?: # Any of:
      # Square brackets with an identifier within.
      \[[a-zA-Z_][a-zA-Z0-9_]*\]
    |
       # An identifier
      [a-zA-Z_][a-zA-Z0-9_]*
    )
  ) # An equals sign, optional spaces.
  \s*=\s*
  # MATCH GROUP 2: The value.
  (.*)$
""", re.VERBOSE)
numbers_args = re.compile(r'^((?:\s|\d)*)$')
number_arg = re.compile(r'\d+')
usage_args = re.compile(r"""
  ^((?:
    # Optional separating whitespace.
    \s*
    (?:
      # Curly braces with an optional identifier within.
      {(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)?}
    |
      # Square brackets with an optional identifier within.
      \[(?:[a-zA-Z_.][a-zA-Z0-9_.]*(?:\.\.\.)?)?\]
    |
      # An identifier
      [a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?
    |
      # A joint argument hole
      {\]
    )
    # Many times.
  )*)$
""", re.VERBOSE)
usage_arg = re.compile(r"""
    # Curly braces with an optional identifier within.
    {(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)?}
  |
    # Square brackets with an optional identifier within.
    \[(?:[a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)?\]
  |
    # The special required-followed-by-optional hole
    {\]
  |
    # An identifier
    [a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?
""", re.VERBOSE)
order_args = re.compile(r'^((?:\s*[a-zA-Z_][a-zA-Z0-9_-]*)+(?:\s*[+-])?)$')
order_arg = re.compile(r'([a-zA-Z_][a-zA-Z0-9_-]*|[+-])')
no_args = re.compile(r'^$')
any_args = re.compile(r'^(.*)$')
one_arg = re.compile(r'^(.+)$')
maybe_word = re.compile(r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)?\s*$')
throw_args = re.compile(r'^([a-zA-Z_][a-zA-Z0-9_]*)(?:\s+(.*))?$')
vim_error = re.compile(r'^E\d+$')
stylizing_args = re.compile(r'^(\S+)$')
function_line = re.compile(r"""
  # Leading whitespace.
  ^\s*
  # fu[nction]
  fu(?:n|nc|nct|ncti|nctio|nction)?
  # Separation (with an optional bang)
  (?:\s*!\s*|\s+)
  # GROUP 1: Autocmd namespace.
  ((?:[a-zA-Z_][a-zA-Z0-9_]*\#)+)?
  # GROUP 2: Function name.
  ([a-zA-Z_][a-zA-Z0-9_]*)
  # Open parens
  \s*\(
  # GROUP 3: Parameters
  # This is more permissive than it has to be. Vimdoc is not a parser.
  ([^\)]*)
  # Close parens
  \)
""", re.VERBOSE)
command_line = re.compile(r"""
  # Leading whitespace.
  ^\s*
  # com[mand]
  com(?:m|ma|man|mand)?
  # Optional bang.
  (?:\s*!\s*|\s+)
  # GROUP 1: Command arguments.
  ((?:-\S+\s*)*)
  # GROUP 2: Command name.
  ([a-zA-Z_][a-zA-Z0-9_]*)
""", re.VERBOSE)
setting_line = re.compile(r"""
  # Definition start.
  ^\s*let\s+g:
  # GROUP 1: Setting name.
  # May include [] (indexing) and {} (interpolation).
  ([a-zA-Z_][a-zA-Z0-9_{}\[\]]*)
""", re.VERBOSE)
flag_line = re.compile(r"""
  # Definition start.
  ^\s*call?\s*
  # A bunch of stuff.
  .*
  # .Flag or ['Flag'] or something.
  (?:\.Flag|\[['"]Flag['"]])\(
  # Shit's about to get real.
  (?:
    # GROUP 1: The flag name in single quotes.
    '(
      # Double single quotes escapes single quotes.
      (?:[^']|'')*
    )'
  | # GROUP 2: The flag name in double quotes.
    "(
      # No escapes or double quotes, or one escaped anything.
      (?:[^\\"]|\\.)*
    )"
  )
""", re.VERBOSE)
inline_directive = re.compile(r'@([a-zA-Z_][a-zA-Z0-9_]*)(?:\(([^\s)]+)\))?')

name_hole = re.compile(r'<>')
arg_hole = re.compile(r'{\]')
required_hole = _DelimitedRegex(r'{}')
optional_hole = _DelimitedRegex(r'\[\]')
required_arg = _DelimitedRegex(r'{([a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)}')
optional_arg = _DelimitedRegex(r'\[([a-zA-Z_][a-zA-Z0-9_]*(?:\.\.\.)?)\]')
namehole_escape = re.compile(r'<\|(\|*)>')
requiredhole_escape = re.compile(r'{\|(\|*)}')
optionalhole_escape = re.compile(r'\[\|(\|*)\]')
bad_separator = re.compile(r"""
  (?:
    # Extra comma-spaces
    (?:,\ )+(?=,\ )
  |
    # Multiple spaces
    \ +(?=\ )
  )
""", re.VERBOSE)

function_arg = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*|\.\.\.)')

list_item = re.compile(r'^\s*([*+-]|\d+\.)\s+')

########NEW FILE########
