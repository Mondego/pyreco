__FILENAME__ = exceptions
from parsimonious.utils import StrAndRepr


class ParseError(StrAndRepr, Exception):
    """A call to ``Expression.parse()`` or ``match()`` didn't match."""

    def __init__(self, text, pos=-1, expr=None):
        # It would be nice to use self.args, but I don't want to pay a penalty
        # to call descriptors or have the confusion of numerical indices in
        # Expression._match().
        self.text = text
        self.pos = pos
        self.expr = expr

    def __unicode__(self):
        rule_name = ((u"'%s'" % self.expr.name) if self.expr.name else
                     unicode(self.expr))
        return u"Rule %s didn't match at '%s' (line %s, column %s)." % (
                rule_name,
                self.text[self.pos:self.pos + 20],
                self.line(),
                self.column())

    # TODO: Add line, col, and separated-out error message so callers can build
    # their own presentation.

    def line(self):
        """Return the 1-based line number where the expression ceased to
        match."""
        # This is a method rather than a property in case we ever wanted to
        # pass in which line endings we want to use.
        return self.text.count('\n', 0, self.pos) + 1

    def column(self):
        """Return the 1-based column where the expression ceased to match."""
        # We choose 1-based because that's what Python does with SyntaxErrors.
        try:
            return self.pos - self.text.rindex('\n', 0, self.pos)
        except ValueError:
            return self.pos + 1


class IncompleteParseError(ParseError):
    """A call to ``parse()`` matched a whole Expression but did not consume the
    entire text."""

    def __unicode__(self):
        return u"Rule '%s' matched in its entirety, but it didn't consume all the text. The non-matching portion of the text begins with '%s' (line %s, column %s)." % (
                self.expr.name,
                self.text[self.pos:self.pos + 20],
                self.line(),
                self.column())


class VisitationError(Exception):
    """Something went wrong while traversing a parse tree.

    This exception exists to augment an underlying exception with information
    about where in the parse tree the error occurred. Otherwise, it could be
    tiresome to figure out what went wrong; you'd have to play back the whole
    tree traversal in your head.

    """
    # TODO: Make sure this is pickleable. Probably use @property pattern. Make
    # the original exc and node available on it if they don't cause a whole
    # raft of stack frames to be retained.
    def __init__(self, exc, exc_class, node):
        """Construct.

        :arg exc: What went wrong. We wrap this and add more info.
        :arg node: The node at which the error occurred

        """
        self.original_class = exc_class
        super(VisitationError, self).__init__(
            '%s: %s\n\n'
            'Parse tree:\n'
            '%s' %
            (exc_class.__name__,
             exc,
             node.prettily(error=node)))


class UndefinedLabel(StrAndRepr, VisitationError):
    """A rule referenced in a grammar was never defined.

    Circular references and forward references are okay, but you have to define
    stuff at some point.

    """
    def __init__(self, label):
        self.label = label

    def __unicode__(self):
        return u'The label "%s" was never defined.' % self.label

########NEW FILE########
__FILENAME__ = expressions
"""Subexpressions that make up a parsed grammar

These do the parsing.

"""
# TODO: Make sure all symbol refs are local--not class lookups or
# anything--for speed. And kill all the dots.

import re

from parsimonious.exceptions import ParseError, IncompleteParseError
from parsimonious.nodes import Node, RegexNode
from parsimonious.utils import StrAndRepr


__all__ = ['Expression', 'Literal', 'Regex', 'Sequence', 'OneOf', 'Lookahead',
           'Not', 'Optional', 'ZeroOrMore', 'OneOrMore']


class Expression(StrAndRepr):
    """A thing that can be matched against a piece of text"""

    # Slots are about twice as fast as __dict__-based attributes:
    # http://stackoverflow.com/questions/1336791/dictionary-vs-object-which-is-more-efficient-and-why

    # Top-level expressions--rules--have names. Subexpressions are named ''.
    __slots__ = ['name']

    def __init__(self, name=''):
        self.name = name

    def parse(self, text, pos=0):
        """Return a parse tree of ``text``.

        Raise ``ParseError`` if the expression wasn't satisfied. Raise
        ``IncompleteParseError`` if the expression was satisfied but didn't
        consume the full string.

        """
        node = self.match(text, pos=pos)
        if node.end < len(text):
            raise IncompleteParseError(text, node.end, self)
        return node

    def match(self, text, pos=0):
        """Return the parse tree matching this expression at the given
        position, not necessarily extending all the way to the end of ``text``.

        Raise ``ParseError`` if there is no match there.

        :arg pos: The index at which to start matching

        """
        error = ParseError(text)
        node = self._match(text, pos, {}, error)
        if node is None:
            raise error
        return node

    def _match(self, text, pos, cache, error):
        """Internal-only guts of ``match()``

        :arg cache: The packrat cache::

            {(oid, pos): Node tree matched by object `oid` at index `pos` ...}

        :arg error: A ParseError instance with ``text`` already filled in but
            otherwise blank. We update the error reporting info on this object
            as we go. (Sticking references on an existing instance is faster
            than allocating a new one for each expression that fails.) We
            return None rather than raising and catching ParseErrors because
            catching is slow.
        """
        # TODO: Optimize. Probably a hot spot.
        #
        # Is there a way of looking up cached stuff that's faster than hashing
        # this id-pos pair?
        #
        # If this is slow, think about the array module. It might (or might
        # not!) use more RAM, but it'll likely be faster than hashing things
        # all the time. Also, can we move all the allocs up front?
        #
        # To save space, we have lots of choices: (0) Quit caching whole Node
        # objects. Cache just what you need to reconstitute them. (1) Cache
        # only the results of entire rules, not subexpressions (probably a
        # horrible idea for rules that need to backtrack internally a lot). (2)
        # Age stuff out of the cache somehow. LRU? (3) Cuts.
        expr_id = id(self)
        node = cache.get((expr_id, pos), ())  # TODO: Change to setdefault to prevent infinite recursion in left-recursive rules.
        if node is ():
            node = cache[(expr_id, pos)] = self._uncached_match(text,
                                                                pos,
                                                                cache,
                                                                error)

        # Record progress for error reporting:
        if node is None and pos >= error.pos and (
                self.name or getattr(error.expr, 'name', None) is None):
            # Don't bother reporting on unnamed expressions (unless that's all
            # we've seen so far), as they're hard to track down for a human.
            # Perhaps we could include the unnamed subexpressions later as
            # auxilliary info.
            error.expr = self
            error.pos = pos

        return node

    def __unicode__(self):
        return u'<%s %s at 0x%s>' % (
            self.__class__.__name__,
            self.as_rule(),
            id(self))

    def as_rule(self):
        """Return the left- and right-hand sides of a rule that represents me.

        Return unicode. If I have no ``name``, omit the left-hand side.

        """
        return ((u'%s = %s' % (self.name, self._as_rhs())) if self.name else
                self._as_rhs())

    def _unicode_members(self):
        """Return an iterable of my unicode-represented children, stopping
        descent when we hit a named node so the returned value resembles the
        input rule."""
        return [(m.name or m._as_rhs()) for m in self.members]

    def _as_rhs(self):
        """Return the right-hand side of a rule that represents me.

        Implemented by subclasses.

        """
        raise NotImplementedError


class Literal(Expression):
    """A string literal

    Use these if you can; they're the fastest.

    """
    __slots__ = ['literal']

    def __init__(self, literal, name=''):
        super(Literal, self).__init__(name)
        self.literal = literal

    def _uncached_match(self, text, pos, cache, error):
        if text.startswith(self.literal, pos):
            return Node(self.name, text, pos, pos + len(self.literal))

    def _as_rhs(self):
        # TODO: Get backslash escaping right.
        return '"%s"' % self.literal


class Regex(Expression):
    """An expression that matches what a regex does.

    Use these as much as you can and jam as much into each one as you can;
    they're fast.

    """
    __slots__ = ['re']

    def __init__(self, pattern, name='', ignore_case=False, locale=False,
                 multiline=False, dot_all=False, unicode=False, verbose=False):
        super(Regex, self).__init__(name)
        self.re = re.compile(pattern, (ignore_case and re.I) |
                                      (locale and re.L) |
                                      (multiline and re.M) |
                                      (dot_all and re.S) |
                                      (unicode and re.U) |
                                      (verbose and re.X))

    def _uncached_match(self, text, pos, cache, error):
        """Return length of match, ``None`` if no match."""
        m = self.re.match(text, pos)
        if m is not None:
            span = m.span()
            node = RegexNode(self.name, text, pos, pos + span[1] - span[0])
            node.match = m  # TODO: A terrible idea for cache size?
            return node

    def _regex_flags_from_bits(self, bits):
        """Return the textual equivalent of numerically encoded regex flags."""
        flags = 'tilmsux'
        return ''.join(flags[i] if (1 << i) & bits else '' for i in xrange(6))

    def _as_rhs(self):
        # TODO: Get backslash escaping right.
        return '~"%s"%s' % (self.re.pattern,
                            self._regex_flags_from_bits(self.re.flags))


class _Compound(Expression):
    """An abstract expression which contains other expressions"""

    __slots__ = ['members']

    def __init__(self, *members, **kwargs):
        """``members`` is a sequence of expressions."""
        super(_Compound, self).__init__(kwargs.get('name', ''))
        self.members = members


class Sequence(_Compound):
    """A series of expressions that must match contiguous, ordered pieces of
    the text

    In other words, it's a concatenation operator: each piece has to match, one
    after another.

    """
    def _uncached_match(self, text, pos, cache, error):
        new_pos = pos
        length_of_sequence = 0
        children = []
        for m in self.members:
            node = m._match(text, new_pos, cache, error)
            if node is None:
                return None
            children.append(node)
            length = node.end - node.start
            new_pos += length
            length_of_sequence += length
        # Hooray! We got through all the members!
        return Node(self.name, text, pos, pos + length_of_sequence, children)

    def _as_rhs(self):
        return u' '.join(self._unicode_members())

class OneOf(_Compound):
    """A series of expressions, one of which must match

    Expressions are tested in order from first to last. The first to succeed
    wins.

    """
    def _uncached_match(self, text, pos, cache, error):
        for m in self.members:
            node = m._match(text, pos, cache, error)
            if node is not None:
                # Wrap the succeeding child in a node representing the OneOf:
                return Node(self.name, text, pos, node.end, children=[node])

    def _as_rhs(self):
        return u' / '.join(self._unicode_members())


class Lookahead(_Compound):
    """An expression which consumes nothing, even if its contained expression
    succeeds"""

    # TODO: Merge this and Not for better cache hit ratios and less code.
    # Downside: pretty-printed grammars might be spelled differently than what
    # went in. That doesn't bother me.

    def _uncached_match(self, text, pos, cache, error):
        node = self.members[0]._match(text, pos, cache, error)
        if node is not None:
            return Node(self.name, text, pos, pos)

    def _as_rhs(self):
        return u'&%s' % self._unicode_members()[0]


class Not(_Compound):
    """An expression that succeeds only if the expression within it doesn't

    In any case, it never consumes any characters; it's a negative lookahead.

    """
    def _uncached_match(self, text, pos, cache, error):
        # FWIW, the implementation in Parsing Techniques in Figure 15.29 does
        # not bother to cache NOTs directly.
        node = self.members[0]._match(text, pos, cache, error)
        if node is None:
            return Node(self.name, text, pos, pos)

    def _as_rhs(self):
        # TODO: Make sure this parenthesizes the member properly if it's an OR
        # or AND.
        return u'!%s' % self._unicode_members()[0]


# Quantifiers. None of these is strictly necessary, but they're darn handy.

class Optional(_Compound):
    """An expression that succeeds whether or not the contained one does

    If the contained expression succeeds, it goes ahead and consumes what it
    consumes. Otherwise, it consumes nothing.

    """
    def _uncached_match(self, text, pos, cache, error):
        node = self.members[0]._match(text, pos, cache, error)
        return (Node(self.name, text, pos, pos) if node is None else
                Node(self.name, text, pos, node.end, children=[node]))

    def _as_rhs(self):
        return u'%s?' % self._unicode_members()[0]


# TODO: Merge with OneOrMore.
class ZeroOrMore(_Compound):
    """An expression wrapper like the * quantifier in regexes."""
    def _uncached_match(self, text, pos, cache, error):
        new_pos = pos
        children = []
        while True:
            node = self.members[0]._match(text, new_pos, cache, error)
            if node is None or not (node.end - node.start):
                # Node was None or 0 length. 0 would otherwise loop infinitely.
                return Node(self.name, text, pos, new_pos, children)
            children.append(node)
            new_pos += node.end - node.start

    def _as_rhs(self):
        return u'%s*' % self._unicode_members()[0]


class OneOrMore(_Compound):
    """An expression wrapper like the + quantifier in regexes.

    You can also pass in an alternate minimum to make this behave like "2 or
    more", "3 or more", etc.

    """
    __slots__ = ['min']

    # TODO: Add max. It should probably succeed if there are more than the max
    # --just not consume them.

    def __init__(self, member, name='', min=1):
        super(OneOrMore, self).__init__(member, name=name)
        self.min = min

    def _uncached_match(self, text, pos, cache, error):
        new_pos = pos
        children = []
        while True:
            node = self.members[0]._match(text, new_pos, cache, error)
            if node is None:
                break
            children.append(node)
            length = node.end - node.start
            if length == 0:  # Don't loop infinitely.
                break
            new_pos += length
        if len(children) >= self.min:
            return Node(self.name, text, pos, new_pos, children)

    def _as_rhs(self):
        return u'%s+' % self._unicode_members()[0]

########NEW FILE########
__FILENAME__ = grammar
"""A convenience which constructs expression trees from an easy-to-read syntax

Use this unless you have a compelling reason not to; it performs some
optimizations that would be tedious to do when constructing an expression tree
by hand.

"""
import ast

from parsimonious.exceptions import UndefinedLabel
from parsimonious.expressions import (Literal, Regex, Sequence, OneOf,
    Lookahead, Optional, ZeroOrMore, OneOrMore, Not)
from parsimonious.nodes import NodeVisitor
from parsimonious.utils import StrAndRepr


__all__ = ['Grammar']


class Grammar(StrAndRepr, dict):
    """A collection of expressions that describe a language

    You can start parsing from the default expression by calling ``parse()``
    directly on the ``Grammar`` object::

        g = Grammar('''
                    polite_greeting = greeting ", my good " title
                    greeting        = "Hi" / "Hello"
                    title           = "madam" / "sir"
                    ''')
        g.parse('Hello, my good sir')

    Or start parsing from any of the other expressions; you can pull them out
    of the grammar as if it were a dictionary::

        g['greeting'].parse('Hi')

    You could also just construct a bunch of ``Expression`` objects yourself
    and stitch them together into a language, but using a ``Grammar`` has some
    important advantages:

    * Languages are much easier to define in the nice syntax it provides.
    * Circular references aren't a pain.
    * It does all kinds of whizzy space- and time-saving optimizations, like
      factoring up repeated subexpressions into a single object, which should
      increase cache hit ratio. [Is this implemented yet?]

    """
    def __init__(self, rules, default_rule=None):
        """Construct a grammar.

        :arg rules: A string of production rules, one per line. There must be
            at least one rule.
        :arg default_rule: The name of the rule invoked when you call
            ``parse()`` on the grammar. Defaults to the first rule.

        """
        # We can either have extending callers pull the rule text out of repr,
        # or we could get fancy and define __add__ on Grammars and strings. Or
        # maybe, if you want to extend a grammar, just prepend (or append?)
        # your string to its, and yours will take precedence. Or use the OMeta
        # delegation syntax.
        exprs, first = self._expressions_from_rules(rules)

        self.update(exprs)
        self.default_rule = exprs[default_rule] if default_rule else first

    def _expressions_from_rules(self, rules):
        """Return a 2-tuple: a dict of rule names pointing to their
        expressions, and then the first rule.

        It's a web of expressions, all referencing each other. Typically,
        there's a single root to the web of references, and that root is the
        starting symbol for parsing, but there's nothing saying you can't have
        multiple roots.

        """
        tree = rule_grammar.parse(rules)
        return RuleVisitor().visit(tree)

    def parse(self, text, pos=0):
        """Parse some text with the default rule."""
        return self.default_rule.parse(text, pos=pos)

    def match(self, text, pos=0):
        """Parse some text with the default rule but not necessarily all the
        way to the end.

        :arg pos: The index at which to start parsing

        """
        return self.default_rule.match(text, pos=pos)

    def __unicode__(self):
        """Return a rule string that, when passed to the constructor, would
        reconstitute the grammar."""
        exprs = [self.default_rule]
        exprs.extend(expr for expr in self.itervalues() if
                     expr is not self.default_rule)
        return '\n'.join(expr.as_rule() for expr in exprs)

    def __repr__(self):
        """Return an expression that will reconstitute the grammar."""
        return "Grammar('%s')" % str(self).encode('string_escape')


class BootstrappingGrammar(Grammar):
    """The grammar used to recognize the textual rules that describe other
    grammars

    This grammar gets its start from some hard-coded Expressions and claws its
    way from there to an expression tree that describes how to parse the
    grammar description syntax.

    """
    def _expressions_from_rules(self, rule_syntax):
        """Return the rules for parsing the grammar definition syntax.

        Return a 2-tuple: a dict of rule names pointing to their expressions,
        and then the top-level expression for the first rule.

        """
        # Hard-code enough of the rules to parse the grammar that describes the
        # grammar description language, to bootstrap:
        comment = Regex(r'#[^\r\n]*', name='comment')
        meaninglessness = OneOf(Regex(r'\s+'), comment, name='meaninglessness')
        _ = ZeroOrMore(meaninglessness, name='_')
        equals = Sequence(Literal('='), _, name='equals')
        label = Sequence(Regex(r'[a-zA-Z_][a-zA-Z_0-9]*'), _, name='label')
        reference = Sequence(label, Not(equals), name='reference')
        quantifier = Sequence(Regex(r'[*+?]'), _, name='quantifier')
        # This pattern supports empty literals. TODO: A problem?
        spaceless_literal = Regex(r'u?r?"[^"\\]*(?:\\.[^"\\]*)*"',
                                  ignore_case=True,
                                  dot_all=True,
                                  name='spaceless_literal')
        literal = Sequence(spaceless_literal, _, name='literal')
        regex = Sequence(Literal('~'),
                         literal,
                         Regex('[ilmsux]*', ignore_case=True),
                         _,
                         name='regex')
        atom = OneOf(reference, literal, regex, name='atom')
        quantified = Sequence(atom, quantifier, name='quantified')

        term = OneOf(quantified, atom, name='term')
        not_term = Sequence(Literal('!'), term, _, name='not_term')
        term.members = (not_term,) + term.members

        sequence = Sequence(term, OneOrMore(term), name='sequence')
        or_term = Sequence(Literal('/'), _, term, name='or_term')
        ored = Sequence(term, OneOrMore(or_term), name='ored')
        expression = OneOf(ored, sequence, term, name='expression')
        rule = Sequence(label, equals, expression, name='rule')
        rules = Sequence(_, OneOrMore(rule), name='rules')

        # Use those hard-coded rules to parse the (more extensive) rule syntax.
        # (For example, unless I start using parentheses in the rule language
        # definition itself, I should never have to hard-code expressions for
        # those above.)

        rule_tree = rules.parse(rule_syntax)

        # Turn the parse tree into a map of expressions:
        return RuleVisitor().visit(rule_tree)

# The grammar for parsing PEG grammar definitions:
# This is a nice, simple grammar. We may someday add to it, but it's a safe bet
# that the future will always be a superset of this.
rule_syntax = (r'''
    # Ignored things (represented by _) are typically hung off the end of the
    # leafmost kinds of nodes. Literals like "/" count as leaves.

    rules = _ rule+
    rule = label equals expression
    equals = "=" _
    literal = spaceless_literal _

    # So you can't spell a regex like `~"..." ilm`:
    spaceless_literal = ~"u?r?\"[^\"\\\\]*(?:\\\\.[^\"\\\\]*)*\""is /
                        ~"u?r?'[^'\\\\]*(?:\\\\.[^'\\\\]*)*'"is

    expression = ored / sequence / term
    or_term = "/" _ term
    ored = term or_term+
    sequence = term term+
    not_term = "!" term _
    lookahead_term = "&" term _
    term = not_term / lookahead_term / quantified / atom
    quantified = atom quantifier
    atom = reference / literal / regex / parenthesized
    regex = "~" spaceless_literal ~"[ilmsux]*"i _
    parenthesized = "(" _ expression ")" _
    quantifier = ~"[*+?]" _
    reference = label !equals

    # A subsequent equal sign is the only thing that distinguishes a label
    # (which begins a new rule) from a reference (which is just a pointer to a
    # rule defined somewhere else):
    label = ~"[a-zA-Z_][a-zA-Z_0-9]*" _

    # _ = ~r"\s*(?:#[^\r\n]*)?\s*"
    _ = meaninglessness*
    meaninglessness = ~r"\s+" / comment
    comment = ~r"#[^\r\n]*"
    ''')


class LazyReference(unicode):
    """A lazy reference to a rule, which we resolve after grokking all the
    rules"""

    name = u''

    # Just for debugging:
    def _as_rhs(self):
        return u'<LazyReference to %s>' % self


class RuleVisitor(NodeVisitor):
    """Turns a parse tree of a grammar definition into a map of ``Expression``
    objects

    This is the magic piece that breathes life into a parsed bunch of parse
    rules, allowing them to go forth and parse other things.

    """
    quantifier_classes = {'?': Optional, '*': ZeroOrMore, '+': OneOrMore}

    visit_expression = visit_term = visit_atom = NodeVisitor.lift_child

    def visit_parenthesized(self, parenthesized, (left_paren, _1,
                                                  expression,
                                                  right_paren, _2)):
        """Treat a parenthesized subexpression as just its contents.

        Its position in the tree suffices to maintain its grouping semantics.

        """
        return expression

    def visit_quantifier(self, quantifier, (symbol, _)):
        """Turn a quantifier into just its symbol-matching node."""
        return symbol

    def visit_quantified(self, quantified, (atom, quantifier)):
        return self.quantifier_classes[quantifier.text](atom)

    def visit_lookahead_term(self, lookahead_term, (ampersand, term, _)):
        return Lookahead(term)

    def visit_not_term(self, not_term, (exclamation, term, _)):
        return Not(term)

    def visit_rule(self, rule, (label, equals, expression)):
        """Assign a name to the Expression and return it."""
        expression.name = label  # Assign a name to the expr.
        return expression

    def visit_sequence(self, sequence, (term, other_terms)):
        """A parsed Sequence looks like [term node, OneOrMore node of
        ``another_term``s]. Flatten it out."""
        return Sequence(term, *other_terms)

    def visit_ored(self, ored, (first_term, other_terms)):
        return OneOf(first_term, *other_terms)

    def visit_or_term(self, or_term, (slash, _, term)):
        """Return just the term from an ``or_term``.

        We already know it's going to be ored, from the containing ``ored``.

        """
        return term

    def visit_label(self, label, (name, _)):
        """Turn a label into a unicode string."""
        return name.text

    def visit_reference(self, reference, (label, not_equals)):
        """Stick a :class:`LazyReference` in the tree as a placeholder.

        We resolve them all later.

        """
        return LazyReference(label)

    def visit_regex(self, regex, (tilde, literal, flags, _)):
        """Return a ``Regex`` expression."""
        flags = flags.text.upper()
        pattern = literal.literal  # Pull the string back out of the Literal
                                   # object.
        return Regex(pattern, ignore_case='I' in flags,
                              locale='L' in flags,
                              multiline='M' in flags,
                              dot_all='S' in flags,
                              unicode='U' in flags,
                              verbose='X' in flags)

    def visit_spaceless_literal(self, spaceless_literal, visited_children):
        """Turn a string literal into a ``Literal`` that recognizes it."""
        # Piggyback on Python's string support so we can have backslash
        # escaping and niceties like \n, \t, etc.
        # string.decode('string_escape') would have been a lower-level
        # possibility.
        return Literal(ast.literal_eval(spaceless_literal.text))

    def visit_literal(self, literal, (spaceless_literal, _)):
        """Pick just the literal out of a literal-and-junk combo."""
        return spaceless_literal

    def generic_visit(self, node, visited_children):
        """Replace childbearing nodes with a list of their children; keep
        others untouched.

        For our case, if a node has children, only the children are important.
        Otherwise, keep the node around for (for example) the flags of the
        regex rule. Most of these kept-around nodes are subsequently thrown
        away by the other visitor methods.

        We can't simply hang the visited children off the original node; that
        would be disastrous if the node occurred in more than one place in the
        tree.

        """
        return visited_children or node  # should semantically be a tuple

    def _resolve_refs(self, rule_map, expr, unwalked_names, walking_names):
        """Return an expression with all its lazy references recursively
        resolved.

        Resolve any lazy references in the expression ``expr``, recursing into
        all subexpressions. Populate ``rule_map`` with any other rules (named
        expressions) resolved along the way. Remove from ``unwalked_names`` any
        which were resolved.

        :arg walking_names: The stack of labels we are currently recursing
            through. This prevents infinite recursion for circular refs.

        """
        # If it's a top-level (named) expression and we've already walked it,
        # don't walk it again:
        if expr.name and expr.name not in unwalked_names:
            # unwalked_names started out with all the rule names in it, so, if
            # this is a named expr and it isn't in there, it must have been
            # resolved.
            return rule_map[expr.name]

        # If not, resolve it:
        elif isinstance(expr, LazyReference):
            label = unicode(expr)
            if label not in walking_names:
                # We aren't already working on traversing this label:
                try:
                    reffed_expr = rule_map[label]
                except KeyError:
                    raise UndefinedLabel(expr)
                rule_map[label] = self._resolve_refs(
                        rule_map,
                        reffed_expr,
                        unwalked_names,
                        walking_names + (label,))

                # If we recurse into a compound expression, the remove()
                # happens in there. But if this label points to a non-compound
                # expression like a literal or a regex or another lazy
                # reference, we need to do this here:
                unwalked_names.discard(label)
            return rule_map[label]
        else:
            members = getattr(expr, 'members', [])
            if members:
                expr.members = [self._resolve_refs(rule_map,
                                                   m,
                                                   unwalked_names,
                                                   walking_names)
                                for m in members]
            if expr.name:
                unwalked_names.remove(expr.name)
            return expr

    def visit_rules(self, node, (_, rules)):
        """Collate all the rules into a map. Return (map, default rule).

        The default rule is the first one. Or, if you have more than one rule
        of that name, it's the last-occurring rule of that name. (This lets you
        override the default rule when you extend a grammar.)

        """
        # Map each rule's name to its Expression. Later rules of the same name
        # override earlier ones. This lets us define rules multiple times and
        # have the last declarations win, so you can extend grammars by
        # concatenation.
        rule_map = dict((expr.name, expr) for expr in rules)

        # Resolve references. This tolerates forward references.
        unwalked_names = set(rule_map.iterkeys())
        while unwalked_names:
            rule_name = next(iter(unwalked_names))  # any arbitrary item
            rule_map[rule_name] = self._resolve_refs(rule_map,
                                                     rule_map[rule_name],
                                                     unwalked_names,
                                                     (rule_name,))
            unwalked_names.discard(rule_name)
        return rule_map, rules[0]


# Bootstrap to level 1...
rule_grammar = BootstrappingGrammar(rule_syntax)
# ...and then to level 2. This establishes that the node tree of our rule
# syntax is built by the same machinery that will build trees of our users'
# grammars. And the correctness of that tree is tested, indirectly, in
# test_grammar.
rule_grammar = Grammar(rule_syntax)

# TODO: Teach Expression trees how to spit out Python representations of
# themselves. Then we can just paste that in above, and we won't have to
# bootstrap on import. Though it'll be a little less DRY. [Ah, but this is not
# so clean, because it would have to output multiple statements to get multiple
# refs to a single expression hooked up.]

########NEW FILE########
__FILENAME__ = nodes
"""Nodes that make up parse trees

Parsing spits out a tree of these, which you can then tell to walk itself and
spit out a useful value. Or you can walk it yourself; the structural attributes
are public.

"""
# TODO: If this is slow, think about using cElementTree or something.
import sys

from parsimonious.exceptions import VisitationError
from parsimonious.utils import StrAndRepr


class Node(StrAndRepr):
    """A parse tree node

    Consider these immutable once constructed. As a side effect of a
    memory-saving strategy in the cache, multiple references to a single
    ``Node`` might be returned in a single parse tree. So, if you start
    messing with one, you'll see surprising parallel changes pop up elsewhere.

    My philosophy is that parse trees (and their nodes) should be
    representation-agnostic. That is, they shouldn't get all mixed up with what
    the final rendered form of a wiki page (or the intermediate representation
    of a programming language, or whatever) is going to be: you should be able
    to parse once and render several representations from the tree, one after
    another.

    """
    # I tried making this subclass list, but it got ugly. I had to construct
    # invalid ones and patch them up later, and there were other problems.
    __slots__ = ['expr_name',  # The name of the expression that generated me
                 'full_text',  # The full text fed to the parser
                 'start', # The position in the text where that expr started matching
                 'end',   # The position after start where the expr first didn't
                          # match. [start:end] follow Python slice conventions.
                 'children']  # List of child parse tree nodes

    def __init__(self, expr_name, full_text, start, end, children=None):
        self.expr_name = expr_name
        self.full_text = full_text
        self.start = start
        self.end = end
        self.children = children or []

    def __iter__(self):
        """Support looping over my children and doing tuple unpacks on me.

        It can be very handy to unpack nodes in arg lists; see
        :class:`PegVisitor` for an example.

        """
        return iter(self.children)

    @property
    def text(self):
        """Return the text this node matched."""
        return self.full_text[self.start:self.end]

    # From here down is just stuff for testing and debugging.

    def prettily(self, error=None):
        """Return a unicode, pretty-printed representation of me.

        :arg error: The node to highlight because an error occurred there

        """
        # TODO: If a Node appears multiple times in the tree, we'll point to
        # them all. Whoops.
        def indent(text):
            return '\n'.join(('    ' + line) for line in text.splitlines())
        ret = [u'<%s%s matching "%s">%s' % (
            self.__class__.__name__,
            (' called "%s"' % self.expr_name) if self.expr_name else '',
            self.text,
            '  <-- *** We were here. ***' if error is self else '')]
        for n in self:
            ret.append(indent(n.prettily(error=error)))
        return '\n'.join(ret)

    def __unicode__(self):
        """Return a compact, human-readable representation of me."""
        return self.prettily()

    def __eq__(self, other):
        """Support by-value deep comparison with other nodes for testing."""
        return (other is not None and
                self.expr_name == other.expr_name and
                self.full_text == other.full_text and
                self.start == other.start and
                self.end == other.end and
                self.children == other.children)

    def __ne__(self, other):
        return not self == other

    def __repr__(self, top_level=True):
        """Return a bit of code (though not an expression) that will recreate
        me."""
        # repr() of unicode flattens everything out to ASCII, so we don't need
        # to explicitly encode things afterward.
        ret = ["s = %r" % self.full_text] if top_level else []
        ret.append("%s(%r, s, %s, %s%s)" % (
            self.__class__.__name__,
            self.expr_name,
            self.start,
            self.end,
            (', children=[%s]' %
             ', '.join([c.__repr__(top_level=False) for c in self.children]))
            if self.children else ''))
        return '\n'.join(ret)


class RegexNode(Node):
    """Node returned from a ``Regex`` expression

    Grants access to the ``re.Match`` object, in case you want to access
    capturing groups, etc.

    """
    __slots__ = ['match']


class NodeVisitor(object):
    """A shell for writing things that turn parse trees into something useful

    Performs a depth-first traversal of an AST. Subclass this, add methods for
    each expr you care about, instantiate, and call
    ``visit(top_node_of_parse_tree)``. It'll return the useful stuff.

    This API is very similar to that of ``ast.NodeVisitor``.

    We never transform the parse tree in place, because...

    * There are likely multiple references to the same ``Node`` object in a
      parse tree, and changes to one reference would surprise you elsewhere.
    * It makes it impossible to report errors: you'd end up with the "error"
      arrow pointing someplace in a half-transformed mishmash of nodes--and
      that's assuming you're even transforming the tree into another tree.
      Heaven forbid you're making it into a string or something else.

    """
    # These could easily all be static methods, but that adds at least as much
    # user-facing weirdness as the ``()`` chars for instantiation. And this
    # way, we're forward compatible if we or the user ever wants to add any
    # state: options, for instance, or a symbol table constructed from a
    # programming language's AST.

    # TODO: If we need to optimize this, we can go back to putting subclasses
    # in charge of visiting children; they know when not to bother. Or we can
    # mark nodes as not descent-worthy in the grammar.
    def visit(self, node):
        method = getattr(self, 'visit_' + node.expr_name, self.generic_visit)

        # Call that method, and show where in the tree it failed if it blows
        # up.
        try:
            return method(node, [self.visit(n) for n in node])
        except VisitationError:
            # Don't catch and re-wrap already-wrapped exceptions.
            raise
        except Exception as e:
            # Catch any exception, and tack on a parse tree so it's easier to
            # see where it went wrong.
            exc_class, exc, tb = sys.exc_info()
            raise VisitationError, (exc, exc_class, node), tb

    def generic_visit(self, node, visited_children):
        """Default visitor method

        :arg node: The node we're visiting
        :arg visited_children: The results of visiting the children of that
            node, in a list

        I'm not sure there's an implementation of this that makes sense across
        all (or even most) use cases, so we leave it to subclasses to implement
        for now.

        """
        raise NotImplementedError("No visitor method was defined for %s." %
                                  node.expr_name)

    # Convenience methods you can call from your own visitors:

    def lift_child(self, node, (first_child,)):
        """Lift the sole child of ``node`` up to replace the node."""
        return first_child

########NEW FILE########
__FILENAME__ = benchmarks
"""Benchmarks for Parsimonious

Run these with ``nosetests parsimonious/tests/bench.py``. They don't run during
normal test runs because they're not tests--they don't assert anything. Also,
they're a bit slow.

These differ from the ones in test_benchmarks in that these are meant to be
compared from revision to revision of Parsimonious to make sure we're not
getting slower. test_benchmarks simply makes sure our choices among
implementation alternatives remain valid.

"""
# These aren't really tests, as they don't assert anything, but I found myself
# rewriting nose's discovery and selection bits, so why not just use nose?

import gc
from timeit import repeat

from parsimonious.grammar import Grammar


def test_not_really_json_parsing():
    """As a baseline for speed, parse some JSON.

    I have no reason to believe that JSON is a particularly representative or
    revealing grammar to test with. Also, this is a naive, unoptimized,
    incorrect grammar, so don't use it as a basis for comparison with other
    parsers. It's just meant to compare across versions of Parsimonious.

    """
    father = """{
        "id" : 1,
        "married" : true,
        "name" : "Larry Lopez",
        "sons" : null,
        "daughters" : [
          {
            "age" : 26,
            "name" : "Sandra"
            },
          {
            "age" : 25,
            "name" : "Margaret"
            },
          {
            "age" : 6,
            "name" : "Mary"
            }
          ]
        }"""
    more_fathers = ','.join([father] * 60)
    json = '{"fathers" : [' + more_fathers + ']}'
    grammar = Grammar(r"""
        value = space (string / number / object / array / true_false_null)
                space

        object = "{" members "}"
        members = (pair ("," pair)*)?
        pair = string ":" value
        array = "[" elements "]"
        elements = (value ("," value)*)?
        true_false_null = "true" / "false" / "null"

        string = space "\"" chars "\"" space
        chars = ~"[^\"]*"  # TODO implement the real thing
        number = (int frac exp) / (int exp) / (int frac) / int
        int = "-"? ((digit1to9 digits) / digit)
        frac = "." digits
        exp = e digits
        digits = digit+
        e = "e+" / "e-" / "e" / "E+" / "E-" / "E"

        digit1to9 = ~"[1-9]"
        digit = ~"[0-9]"
        space = ~"\s*"
        """)

    # These number and repetition values seem to keep results within 5% of the
    # difference between min and max. We get more consistent results running a
    # bunch of single-parse tests and taking the min rather than upping the
    # NUMBER and trying to stomp out the outliers with averaging.
    NUMBER = 1
    REPEAT = 5
    total_seconds = min(repeat(lambda: grammar.parse(json),
                               lambda: gc.enable(),  # so we take into account how we treat the GC
                               repeat=REPEAT,
                               number=NUMBER))
    seconds_each = total_seconds / NUMBER

    kb = len(json) / 1024.0
    print 'Took %.3fs to parse %.1fKB: %.0fKB/s.' % (seconds_each,
                                                     kb,
                                                     kb / seconds_each)

########NEW FILE########
__FILENAME__ = test_benchmarks
"""Tests to show that the benchmarks we based our speed optimizations on are
still valid"""

from functools import partial
from timeit import timeit

from nose.tools import ok_


timeit = partial(timeit, number=500000)


def test_lists_vs_dicts():
    """See what's faster at int key lookup: dicts or lists."""
    list_time = timeit('item = l[9000]', 'l = [0] * 10000')
    dict_time = timeit('item = d[9000]', 'd = dict((x, 0) for x in range(10000))')

    # Dicts take about 1.6x as long as lists in Python 2.6 and 2.7.
    ok_(list_time < dict_time, '%s < %s' % (list_time, dict_time))


def test_call_vs_inline():
    """How bad is the calling penalty?"""
    no_call = timeit('l[0] += 1', 'l = [0]')
    call = timeit('add(); l[0] += 1', 'l = [0]\n'
                                      'def add():\n'
                                      '    pass')

    # Calling a function is pretty fast; it takes just 1.2x as long as the
    # global var access and addition in l[0] += 1.
    ok_(no_call < call, '%s (no call) < %s (call)' % (no_call, call))


def test_startswith_vs_regex():
    """Can I beat the speed of regexes by special-casing literals?"""
    re_time = timeit(
        'r.match(t, 19)',
        'import re\n'
        "r = re.compile('hello')\n"
        "t = 'this is the finest hello ever'")
    startswith_time = timeit("t.startswith('hello', 19)",
                             "t = 'this is the finest hello ever'")

    # Regexes take 2.24x as long as simple string matching.
    ok_(startswith_time < re_time,
        '%s (startswith) < %s (re)' % (startswith_time, re_time))

########NEW FILE########
__FILENAME__ = test_expressions
#coding=utf-8
from unittest import TestCase

from nose.tools import eq_, ok_, assert_raises

from parsimonious.exceptions import ParseError, IncompleteParseError
from parsimonious.expressions import (Literal, Regex, Sequence, OneOf, Not,
    Optional, ZeroOrMore, OneOrMore, Expression)
from parsimonious.grammar import Grammar, rule_grammar
from parsimonious.nodes import Node


def len_eq(node, length):
    """Return whether the match lengths of 2 nodes are equal.

    Makes tests shorter and lets them omit positional stuff they don't care
    about.

    """
    node_length = None if node is None else node.end - node.start
    return node_length == length


class LengthTests(TestCase):
    """Tests for returning the right lengths

    I wrote these before parse tree generation was implemented. They're
    partially redundant with TreeTests.

    """
    def test_regex(self):
        len_eq(Literal('hello').match('ehello', 1), 5)  # simple
        len_eq(Regex('hello*').match('hellooo'), 7)  # *
        assert_raises(ParseError, Regex('hello*').match, 'goodbye')  # no match
        len_eq(Regex('hello', ignore_case=True).match('HELLO'), 5)

    def test_sequence(self):
        len_eq(Sequence(Regex('hi*'), Literal('lo'), Regex('.ingo')).match('hiiiilobingo1234'),
            12)  # succeed
        assert_raises(ParseError, Sequence(Regex('hi*'), Literal('lo'), Regex('.ingo')).match, 'hiiiilobing')  # don't
        len_eq(Sequence(Regex('hi*')).match('>hiiii', 1),
            5)  # non-0 pos

    def test_one_of(self):
        len_eq(OneOf(Literal('aaa'), Literal('bb')).match('aaa'), 3)  # first alternative
        len_eq(OneOf(Literal('aaa'), Literal('bb')).match('bbaaa'), 2)  # second
        assert_raises(ParseError, OneOf(Literal('aaa'), Literal('bb')).match, 'aa')  # no match

    def test_not(self):
        len_eq(Not(Regex('.')).match(''), 0)  # match
        assert_raises(ParseError, Not(Regex('.')).match, 'Hi')  # don't

    def test_optional(self):
        len_eq(Sequence(Optional(Literal('a')), Literal('b')).match('b'), 1)  # contained expr fails
        len_eq(Sequence(Optional(Literal('a')), Literal('b')).match('ab'), 2)  # contained expr succeeds

    def test_zero_or_more(self):
        len_eq(ZeroOrMore(Literal('b')).match(''), 0)  # zero
        len_eq(ZeroOrMore(Literal('b')).match('bbb'), 3)  # more

        len_eq(Regex('^').match(''), 0)  # Validate the next test.

        # Try to make it loop infinitely using a zero-length contained expression:
        len_eq(ZeroOrMore(Regex('^')).match(''), 0)

    def test_one_or_more(self):
        len_eq(OneOrMore(Literal('b')).match('b'), 1)  # one
        len_eq(OneOrMore(Literal('b')).match('bbb'), 3)  # more
        len_eq(OneOrMore(Literal('b'), min=3).match('bbb'), 3)  # with custom min; success
        assert_raises(ParseError, OneOrMore(Literal('b'), min=3).match, 'bb')  # with custom min; failure
        len_eq(OneOrMore(Regex('^')).match('bb'), 0)  # attempt infinite loop


class TreeTests(TestCase):
    """Tests for building the right trees

    We have only to test successes here; failures (None-returning cases) are
    covered above.

    """
    def test_simple_node(self):
        """Test that leaf expressions like ``Literal`` make the right nodes."""
        h = Literal('hello', name='greeting')
        eq_(h.match('hello'), Node('greeting', 'hello', 0, 5))

    def test_sequence_nodes(self):
        """Assert that ``Sequence`` produces nodes with the right children."""
        s = Sequence(Literal('heigh', name='greeting1'),
                     Literal('ho',    name='greeting2'), name='dwarf')
        text = 'heighho'
        eq_(s.match(text), Node('dwarf', text, 0, 7, children=
                                [Node('greeting1', text, 0, 5),
                                 Node('greeting2', text, 5, 7)]))

    def test_one_of(self):
        """``OneOf`` should return its own node, wrapping the child that succeeds."""
        o = OneOf(Literal('a', name='lit'), name='one_of')
        text = 'aa'
        eq_(o.match(text), Node('one_of', text, 0, 1, children=[
                                Node('lit', text, 0, 1)]))

    def test_optional(self):
        """``Optional`` should return its own node wrapping the succeeded child."""
        expr = Optional(Literal('a', name='lit'), name='opt')

        text = 'a'
        eq_(expr.match(text), Node('opt', text, 0, 1, children=[
                                   Node('lit', text, 0, 1)]))

        # Test failure of the Literal inside the Optional; the
        # LengthTests.test_optional is ambiguous for that.
        text = ''
        eq_(expr.match(text), Node('opt', text, 0, 0))

    def test_zero_or_more_zero(self):
        """Test the 0 case of ``ZeroOrMore``; it should still return a node."""
        expr = ZeroOrMore(Literal('a'), name='zero')
        text = ''
        eq_(expr.match(text), Node('zero', text, 0, 0))

    def test_one_or_more_one(self):
        """Test the 1 case of ``OneOrMore``; it should return a node with a child."""
        expr = OneOrMore(Literal('a', name='lit'), name='one')
        text = 'a'
        eq_(expr.match(text), Node('one', text, 0, 1, children=[
                                   Node('lit', text, 0, 1)]))

    # Things added since Grammar got implemented are covered in integration
    # tests in test_grammar.


class ParseTests(TestCase):
    """Tests for the ``parse()`` method"""

    def test_parse_success(self):
        """Make sure ``parse()`` returns the tree on success.

        There's not much more than that to test that we haven't already vetted
        above.

        """
        expr = OneOrMore(Literal('a', name='lit'), name='more')
        text = 'aa'
        eq_(expr.parse(text), Node('more', text, 0, 2, children=[
                                   Node('lit', text, 0, 1),
                                   Node('lit', text, 1, 2)]))


class ErrorReportingTests(TestCase):
    """Tests for reporting parse errors"""

    def test_inner_rule_succeeding(self):
        """Make sure ``parse()`` fails and blames the
        rightward-progressing-most named Expression when an Expression isn't
        satisfied.

        Make sure ParseErrors have nice Unicode representations.

        """
        grammar = Grammar("""
            bold_text = open_parens text close_parens
            open_parens = "(("
            text = ~"[a-zA-Z]+"
            close_parens = "))"
            """)
        text = '((fred!!'
        try:
            grammar.parse(text)
        except ParseError as error:
            eq_(error.pos, 6)
            eq_(error.expr, grammar['close_parens'])
            eq_(error.text, text)
            eq_(unicode(error), u"Rule 'close_parens' didn't match at '!!' (line 1, column 7).")

    def test_rewinding(self):
        """Make sure rewinding the stack and trying an alternative (which
        progresses farther) from a higher-level rule can blame an expression
        within the alternative on failure.

        There's no particular reason I suspect this wouldn't work, but it's a
        more real-world example than the no-alternative cases already tested.

        """
        grammar = Grammar("""
            formatted_text = bold_text / weird_text
            bold_text = open_parens text close_parens
            weird_text = open_parens text "!!" bork
            bork = "bork"
            open_parens = "(("
            text = ~"[a-zA-Z]+"
            close_parens = "))"
            """)
        text = '((fred!!'
        try:
            grammar.parse(text)
        except ParseError as error:
            eq_(error.pos, 8)
            eq_(error.expr, grammar['bork'])
            eq_(error.text, text)

    def test_no_named_rule_succeeding(self):
        """Make sure ParseErrors have sane printable representations even if we
        never succeeded in matching any named expressions."""
        grammar = Grammar('''bork = "bork"''')
        try:
            grammar.parse('snork')
        except ParseError as error:
            eq_(error.pos, 0)
            eq_(error.expr, grammar['bork'])
            eq_(error.text, 'snork')

    def test_parse_with_leftovers(self):
        """Make sure ``parse()`` reports where we started failing to match,
        even if a partial match was successful."""
        grammar = Grammar(r'''sequence = "chitty" (" " "bang")+''')
        try:
            grammar.parse('chitty bangbang')
        except IncompleteParseError as error:
            eq_(unicode(error), u"Rule 'sequence' matched in its entirety, but it didn't consume all the text. The non-matching portion of the text begins with 'bang' (line 1, column 12).")

    def test_favoring_named_rules(self):
        """Named rules should be used in error messages in favor of anonymous
        ones, even if those are rightward-progressing-more, and even if the
        failure starts at position 0."""
        grammar = Grammar(r'''starts_with_a = &"a" ~"[a-z]+"''')
        try:
            grammar.parse('burp')
        except ParseError as error:
            eq_(unicode(error), u"Rule 'starts_with_a' didn't match at 'burp' (line 1, column 1).")

    def test_line_and_column(self):
        """Make sure we got the line and column computation right."""
        grammar = Grammar(r"""
            whee_lah = whee "\n" lah "\n"
            whee = "whee"
            lah = "lah"
            """)
        try:
            grammar.parse('whee\nlahGOO')
        except ParseError as error:
            # TODO: Right now, this says "Rule <Literal "\n" at 0x4368250432>
            # didn't match". That's not the greatest. Fix that, then fix this.
            ok_(unicode(error).endswith(ur"""didn't match at 'GOO' (line 2, column 4)."""))


class RepresentationTests(TestCase):
    """Tests for str(), unicode(), and repr() of expressions"""

    def test_unicode_crash(self):
        """Make sure matched unicode strings don't crash ``__str__``."""
        grammar = Grammar(r'string = ~r"\S+"u')
        str(grammar.parse(u'中文'))

    def test_unicode(self):
        """Smoke-test the conversion of expressions to bits of rules.

        A slightly more comprehensive test of the actual values is in
        ``GrammarTests.test_unicode``.

        """
        unicode(rule_grammar)

########NEW FILE########
__FILENAME__ = test_grammar
from sys import version_info
from unittest import TestCase

from nose import SkipTest
from nose.tools import eq_, assert_raises, ok_

from parsimonious.exceptions import UndefinedLabel, ParseError
from parsimonious.nodes import Node
from parsimonious.grammar import rule_grammar, RuleVisitor, Grammar


class BootstrappingGrammarTests(TestCase):
    """Tests for the expressions in the grammar that parses the grammar
    definition syntax"""

    def test_quantifier(self):
        text = '*'
        eq_(rule_grammar['quantifier'].parse(text),
            Node('quantifier', text, 0, 1, children=[
                Node('', text, 0, 1), Node('_', text, 1, 1)]))
        text = '?'
        eq_(rule_grammar['quantifier'].parse(text),
            Node('quantifier', text, 0, 1, children=[
                Node('', text, 0, 1), Node('_', text, 1, 1)]))
        text = '+'
        eq_(rule_grammar['quantifier'].parse(text),
            Node('quantifier', text, 0, 1, children=[
                Node('', text, 0, 1), Node('_', text, 1, 1)]))

    def test_spaceless_literal(self):
        text = '"anything but quotes#$*&^"'
        eq_(rule_grammar['spaceless_literal'].parse(text),
            Node('spaceless_literal', text, 0, len(text), children=[
                Node('', text, 0, len(text))]))
        text = r'''r"\""'''
        eq_(rule_grammar['spaceless_literal'].parse(text),
            Node('spaceless_literal', text, 0, 5, children=[
                Node('', text, 0, 5)]))

    def test_regex(self):
        text = '~"[a-zA-Z_][a-zA-Z_0-9]*"LI'
        eq_(rule_grammar['regex'].parse(text),
            Node('regex', text, 0, len(text), children=[
                 Node('', text, 0, 1),
                 Node('spaceless_literal', text, 1, 25, children=[
                     Node('', text, 1, 25)]),
                 Node('', text, 25, 27),
                 Node('_', text, 27, 27)]))

    def test_successes(self):
        """Make sure the PEG recognition grammar succeeds on various inputs."""
        ok_(rule_grammar['label'].parse('_'))
        ok_(rule_grammar['label'].parse('jeff'))
        ok_(rule_grammar['label'].parse('_THIS_THING'))

        ok_(rule_grammar['atom'].parse('some_label'))
        ok_(rule_grammar['atom'].parse('"some literal"'))
        ok_(rule_grammar['atom'].parse('~"some regex"i'))

        ok_(rule_grammar['quantified'].parse('~"some regex"i*'))
        ok_(rule_grammar['quantified'].parse('thing+'))
        ok_(rule_grammar['quantified'].parse('"hi"?'))

        ok_(rule_grammar['term'].parse('this'))
        ok_(rule_grammar['term'].parse('that+'))

        ok_(rule_grammar['sequence'].parse('this that? other'))

        ok_(rule_grammar['ored'].parse('this / that+ / "other"'))

        # + is higher precedence than &, so 'anded' should match the whole
        # thing:
        ok_(rule_grammar['lookahead_term'].parse('&this+'))

        ok_(rule_grammar['expression'].parse('this'))
        ok_(rule_grammar['expression'].parse('this? that other*'))
        ok_(rule_grammar['expression'].parse('&this / that+ / "other"'))
        ok_(rule_grammar['expression'].parse('this / that? / "other"+'))
        ok_(rule_grammar['expression'].parse('this? that other*'))

        ok_(rule_grammar['rule'].parse('this = that\r'))
        ok_(rule_grammar['rule'].parse('this = the? that other* \t\r'))
        ok_(rule_grammar['rule'].parse('the=~"hi*"\n'))

        ok_(rule_grammar.parse('''
            this = the? that other*
            that = "thing"
            the=~"hi*"
            other = "ahoy hoy"
            '''))


class RuleVisitorTests(TestCase):
    """Tests for ``RuleVisitor``

    As I write these, Grammar is not yet fully implemented. Normally, there'd
    be no reason to use ``RuleVisitor`` directly.

    """
    def test_round_trip(self):
        """Test a simple round trip.

        Parse a simple grammar, turn the parse tree into a map of expressions,
        and use that to parse another piece of text.

        Not everything was implemented yet, but it was a big milestone and a
        proof of concept.

        """
        tree = rule_grammar.parse('''number = ~"[0-9]+"\n''')
        rules, default_rule = RuleVisitor().visit(tree)

        text = '98'
        eq_(default_rule.parse(text), Node('number', text, 0, 2))

    def test_undefined_rule(self):
        """Make sure we throw the right exception on undefined rules."""
        tree = rule_grammar.parse('boy = howdy\n')
        assert_raises(UndefinedLabel, RuleVisitor().visit, tree)

    def test_optional(self):
        tree = rule_grammar.parse('boy = "howdy"?\n')
        rules, default_rule = RuleVisitor().visit(tree)

        howdy = 'howdy'

        # It should turn into a Node from the Optional and another from the
        # Literal within.
        eq_(default_rule.parse(howdy), Node('boy', howdy, 0, 5, children=[
                                           Node('', howdy, 0, 5)]))


class GrammarTests(TestCase):
    """Integration-test ``Grammar``: feed it a PEG and see if it works."""

    def test_expressions_from_rules(self):
        """Test the ``Grammar`` base class's ability to compile an expression
        tree from rules.

        That the correct ``Expression`` tree is built is already tested in
        ``RuleGrammarTests``. This tests only that the ``Grammar`` base class's
        ``_expressions_from_rules`` works.

        """
        greeting_grammar = Grammar('greeting = "hi" / "howdy"')
        tree = greeting_grammar.parse('hi')
        eq_(tree, Node('greeting', 'hi', 0, 2, children=[
                       Node('', 'hi', 0, 2)]))

    def test_unicode(self):
        """Assert that a ``Grammar`` can convert into a string-formatted series
        of rules."""
        grammar = Grammar(r"""
                          bold_text  = bold_open text bold_close
                          text       = ~"[A-Z 0-9]*"i
                          bold_open  = "(("
                          bold_close = "))"
                          """)
        lines = unicode(grammar).splitlines()
        eq_(lines[0], 'bold_text = bold_open text bold_close')
        ok_('text = ~"[A-Z 0-9]*"i%s' % ('u' if version_info >= (3,) else '')
            in lines)
        ok_('bold_open = "(("' in lines)
        ok_('bold_close = "))"' in lines)
        eq_(len(lines), 4)

    def test_match(self):
        """Make sure partial-matching (with pos) works."""
        grammar = Grammar(r"""
                          bold_text  = bold_open text bold_close
                          text       = ~"[A-Z 0-9]*"i
                          bold_open  = "(("
                          bold_close = "))"
                          """)
        s = ' ((boo))yah'
        eq_(grammar.match(s, pos=1), Node('bold_text', s, 1, 8, children=[
                                         Node('bold_open', s, 1, 3),
                                         Node('text', s, 3, 6),
                                         Node('bold_close', s, 6, 8)]))

    def test_bad_grammar(self):
        """Constructing a Grammar with bad rules should raise ParseError."""
        assert_raises(ParseError, Grammar, 'just a bunch of junk')

    def test_comments(self):
        """Test tolerance of comments and blank lines in and around rules."""
        grammar = Grammar(r"""# This is a grammar.

                          # It sure is.
                          bold_text  = stars text stars  # nice
                          text       = ~"[A-Z 0-9]*"i #dude


                          stars      = "**"
                          # Pretty good
                          #Oh yeah.#""")  # Make sure a comment doesn't need a
                                          # \n or \r to end.
        eq_(list(sorted(str(grammar).splitlines())),
            ['''bold_text = stars text stars''',
             # TODO: Unicode flag is on by default in Python 3. I wonder if we
             # should turn it on all the time in Parsimonious.
             '''stars = "**"''',
             '''text = ~"[A-Z 0-9]*"i%s''' % ('u' if version_info >= (3,)
                                              else '')])

    def test_multi_line(self):
        """Make sure we tolerate all sorts of crazy line breaks and comments in
        the middle of rules."""
        grammar = Grammar("""
            bold_text  = bold_open  # commenty comment
                         text  # more comment
                         bold_close
            text       = ~"[A-Z 0-9]*"i
            bold_open  = "((" bold_close =  "))"
            """)
        ok_(grammar.parse('((booyah))') is not None)

    def test_not(self):
        """Make sure "not" predicates get parsed and work properly."""
        grammar = Grammar(r'''not_arp = !"arp" ~"[a-z]+"''')
        assert_raises(ParseError, grammar.parse, 'arp')
        ok_(grammar.parse('argle') is not None)

    def test_lookahead(self):
        grammar = Grammar(r'''starts_with_a = &"a" ~"[a-z]+"''')
        assert_raises(ParseError, grammar.parse, 'burp')

        s = 'arp'
        eq_(grammar.parse('arp'), Node('starts_with_a', s, 0, 3, children=[
                                      Node('', s, 0, 0),
                                      Node('', s, 0, 3)]))

    def test_parens(self):
        grammar = Grammar(r'''sequence = "chitty" (" " "bang")+''')
        # Make sure it's not as if the parens aren't there:
        assert_raises(ParseError, grammar.parse, 'chitty bangbang')

        s = 'chitty bang bang'
        eq_(str(grammar.parse(s)),
            """<Node called "sequence" matching "chitty bang bang">
    <Node matching "chitty">
    <Node matching " bang bang">
        <Node matching " bang">
            <Node matching " ">
            <Node matching "bang">
        <Node matching " bang">
            <Node matching " ">
            <Node matching "bang">""")

    def test_resolve_refs_order(self):
        """Smoke-test a circumstance where lazy references don't get resolved."""
        grammar = Grammar("""
            expression = "(" terms ")"
            terms = term+
            term = number
            number = ~r"[0-9]+"
            """)
        grammar.parse('(34)')

    def test_infinite_loop(self):
        """Smoke-test a grammar that was causing infinite loops while building.

        This was going awry because the "int" rule was never getting marked as
        resolved, so it would just keep trying to resolve it over and over.

        """
        Grammar("""
            digits = digit+
            int = digits
            digit = ~"[0-9]"
            number = int
            main = number
            """)

    def test_right_recursive(self):
        """Right-recursive refs should resolve."""
        grammar = Grammar("""
            digits = digit digits?
            digit = ~r"[0-9]"
            """)
        ok_(grammar.parse('12') is not None)

    def test_badly_circular(self):
        """Uselessly circular references should be detected by the grammar
        compiler."""
        raise SkipTest('We have yet to make the grammar compiler detect these.')
        grammar = Grammar("""
            foo = bar
            bar = foo
            """)

    def test_parens_with_leading_whitespace(self):
        """Make sure a parenthesized expression is allowed to have leading
        whitespace when nested directly inside another."""
        Grammar("""foo = ( ("c") )""").parse('c')

    def test_single_quoted_literals(self):
        Grammar("""foo = 'a' '"'""").parse('a"')

########NEW FILE########
__FILENAME__ = test_nodes
# -*- coding: utf-8 -*-
from nose.tools import eq_, assert_raises

from parsimonious.nodes import Node, NodeVisitor, VisitationError


class HtmlFormatter(NodeVisitor):
    """Visitor that turns a parse tree into HTML fragments"""

    def visit_bold_open(self, node, visited_children):
        return '<b>'

    def visit_bold_close(self, node, visited_children):
        return '</b>'

    def visit_text(self, node, visited_children):
        """Return the text verbatim."""
        return node.text

    def visit_bold_text(self, node, visited_children):
        return ''.join(visited_children)


class ExplosiveFormatter(NodeVisitor):
    """Visitor which raises exceptions"""

    def visit_boom(self, node, visited_children):
        raise ValueError


def test_visitor():
    """Assert a tree gets visited correctly.

    We start with a tree from applying this grammar... ::

        bold_text  = bold_open text bold_close
        text       = ~'[a-zA-Z 0-9]*'
        bold_open  = '(('
        bold_close = '))'

    ...to this text::

        ((o hai))

    """
    text = '((o hai))'
    tree = Node('bold_text', text, 0, 9,
                [Node('bold_open', text, 0, 2),
                 Node('text', text, 2, 7),
                 Node('bold_close', text, 7, 9)])
    result = HtmlFormatter().visit(tree)
    eq_(result, '<b>o hai</b>')


def test_visitation_exception():
    assert_raises(VisitationError,
                  ExplosiveFormatter().visit,
                  Node('boom', '', 0, 0))


def test_str():
    """Test str and unicode of ``Node``."""
    n = Node('text', 'o hai', 0, 5)
    good = '<Node called "text" matching "o hai">'
    eq_(str(n), good)
    eq_(unicode(n), good)


def test_repr():
    """Test repr of ``Node``."""
    s = u'hai ö'
    boogie = u'böogie'
    n = Node(boogie, s, 0, 3, children=[
            Node('', s, 3, 4), Node('', s, 4, 5)])
    eq_(repr(n), """s = {hai_o}\nNode({boogie}, s, 0, 3, children=[Node('', s, 3, 4), Node('', s, 4, 5)])""".format(hai_o=repr(s), boogie=repr(boogie)))

########NEW FILE########
__FILENAME__ = utils
"""General tools which don't depend on other parts of Parsimonious"""

from sys import version_info


class StrAndRepr(object):
    """Mix-in to add a ``__str__`` and ``__repr__`` which return the
    UTF-8-encoded value of ``__unicode__``"""

    if version_info >= (3,):
        # Don't return the "bytes" type from Python 3's __str__:
        def __str__(self):
            return self.__unicode__()
    else:
        def __str__(self):
            return self.__unicode__().encode('utf-8')

    __repr__ = __str__  # Language spec says must be string, not unicode.

########NEW FILE########
