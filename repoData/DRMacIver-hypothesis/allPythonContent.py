__FILENAME__ = flags
class Flags(object):
    def __init__(self, flags=None):
        self.flags = frozenset(flags or {})

    def __repr__(self):
        return "Flags(%s)" % ', '.join(map(str,self.flags))

    def __hash__(self):
        return hash(self.flags)

    def __eq__(self, other):
        return isinstance(other, Flags) and self.flags == other.flags

    def __ne__(self, other):
        return not (self == other)

    def enabled(self, flag):
        return flag in self.flags

    def with_enabled(self, *flags):
        x = set(self.flags)
        for f in flags:
            x.add(f)
        return Flags(x)

    def with_disabled(self, *flags):
        x = set(self.flags)
        for f in flags:
            x.remove(f)
        return Flags(x)

########NEW FILE########
__FILENAME__ = hashitanyway
def hash_everything(l):
    try:
        return hash(l)
    except TypeError:
        h = hash(l.__class__)
        try:
            xs = iter(l)
        except TypeError:
            return h

        for x in xs:
            h = h ^ hash_everything(x)
        return h


class HashItAnyway(object):
    def __init__(self, wrapped):
        self.wrapped = wrapped
        self.h = hash_everything(wrapped)

    def __eq__(self, other):
        return (isinstance(other, HashItAnyway) and
                self.wrapped.__class__ == other.wrapped.__class__ and
                self.h == other.h and
                self.wrapped == other.wrapped)

    def __ne__(self, other):
        return not(self == other)

    def __hash__(self):
        return self.h

    def __repr__(self):
        return "HashItAnyway(%s)" % repr(self.wrapped)

########NEW FILE########
__FILENAME__ = searchstrategy
from hypothesis.specmapper import SpecificationMapper
from hypothesis.tracker import Tracker
from hypothesis.flags import Flags

from inspect import isclass
from collections import namedtuple
from abc import abstractmethod
from math import log, log1p
import math

from random import random as rand, choice
import random


def strategy_for(typ):
    def accept_function(fn):
        SearchStrategies.default().define_specification_for(typ, fn)
        return fn
    return accept_function


def strategy_for_instances(typ):
    def accept_function(fn):
        SearchStrategies.default().define_specification_for_instances(typ, fn)
        return fn
    return accept_function


class SearchStrategies(SpecificationMapper):
    def strategy(self, descriptor, **kwargs):
        return self.specification_for(descriptor, **kwargs)

    def missing_specification(self, descriptor):
        if isinstance(descriptor, SearchStrategy):
            return descriptor
        else:
            return SpecificationMapper.missing_specification(self, descriptor)


def nice_string(xs, history=None):
    history = history or []
    if xs in history:
        return '(...)'
    history = history + [xs]
    recurse = lambda t: nice_string(t, history)
    if isinstance(xs, list):
        return '[' + ', '.join(map(recurse, xs)) + ']'
    if isinstance(xs, tuple):
        return '(' + ', '.join(map(recurse, xs)) + ')'
    if isinstance(xs, dict):
        return '{' + ', '.join(
            repr(k1) + ':' + recurse(v1)
            for k1, v1 in xs.items()
        ) + '}'
    try:
        return xs.__name__
    except AttributeError:
        pass

    try:
        d = xs.__dict__
    except AttributeError:
        return repr(xs)

    return "%s(%s)" % (
        xs.__class__.__name__,
        ', '.join(
            "%s=%s" % (k2, nice_string(v2, history)) for k2, v2 in d.items()
        )
    )


class SearchStrategy(object):
    def __init__(self,
                 strategies,
                 descriptor):
        self.descriptor = descriptor
        strategies.cache_specification_for_descriptor(descriptor, self)

    def __repr__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            nice_string(self.descriptor)
        )

    def may_call_self_recursively(self):
        if not hasattr(self, '__may_call_self_recursively'):
            self.__may_call_self_recursively = any(
                self is x for x in self.all_child_strategies()
            )
        return self.__may_call_self_recursively

    def all_child_strategies(self):
        stack = [self]
        seen = []

        while stack:
            head = stack.pop()
            for c in head.child_strategies():
                if any((s is c for s in seen)):
                    continue
                yield c
                stack.append(c)
                seen.append(c)

    def flags(self):
        r = set()
        self.add_flags_to(r)
        return Flags(r)

    def personal_flag(self, flag):
        return (self, str(flag))

    def add_flags_to(self, s, history=None):
        history = history or []
        if self in history:
            return
        history.append(self)
        for f in self.own_flags():
            s.add(f)
        for c in self.child_strategies():
            c.add_flags_to(s, history)

    def own_flags(self):
        return ()

    def child_strategies(self):
        return ()

    @abstractmethod
    def produce(self, size, flags):
        pass  # pragma: no coverass  # pragma: no cover

    def complexity(self, value):
        return 0

    def simplify(self, value):
        return iter(())

    def simplify_such_that(self, t, f):
        tracker = Tracker()
        yield t

        while True:
            for s in self.simplify(t):
                if tracker.track(s) > 1:
                    continue
                if f(s):
                    yield s
                    t = s
                    break
            else:
                break

    def could_have_produced(self, x):
        d = self.descriptor
        c = d if isclass(d) else d.__class__
        return isinstance(x, c)

entropy_to_geom_cache = {}


def geometric_probability_for_entropy(desired_entropy):
    if desired_entropy <= 1e-8:
        return 0.0

    if desired_entropy in entropy_to_geom_cache:
        return entropy_to_geom_cache[desired_entropy]

    def h(p):
        q = 1 - p
        return -(q * log1p(-p) + p * log(p))/(log(2) * p)

    lower = 0.0
    upper = 1.0
    for _ in xrange(max(int(desired_entropy * 2), 64)):
        mid = (lower + upper) / 2
        if h(mid) > desired_entropy:
            lower = mid
        else:
            upper = mid

    entropy_to_geom_cache[desired_entropy] = mid
    return mid


def arbitrary_int():
    return random.randint(-2**32, 2**32)


def geometric_int(p):
    if p <= 0:
        return arbitrary_int()
    elif p >= 1:
        return 0
    denom = log1p(- p)
    return int(log(rand()) / denom)


@strategy_for(int)
class IntStrategy(SearchStrategy):
    def own_flags(self):
        return ("allow_negative_ints",)

    def complexity(self, value):
        if value >= 0:
            return value
        else:
            return 1 - value

    def produce(self, size, flags):
        can_be_negative = flags.enabled("allow_negative_ints") and size > 1

        if size <= 1e-8:
            return 0

        if size >= 32:
            return arbitrary_int()

        if can_be_negative:
            size -= 1

        p = geometric_probability_for_entropy(size)
        n = geometric_int(p)
        if can_be_negative and rand() <= 0.5:
            n = -n
        return n

    def simplify(self, x):
        if x < 0:
            yield -x
            for y in self.simplify(-x):
                yield -y
        elif x > 0:
            #FIXME: This is a stupid way to do it
            seen = {0}
            yield 0
            max_not_seen = x - 1
            while max_not_seen > 0:
                n = random.randint(0, max_not_seen)
                if n not in seen:
                    seen.add(n)
                    if n == max_not_seen:
                        while max_not_seen in seen:
                            max_not_seen -= 1
                    yield n


@strategy_for(float)
class FloatStrategy(SearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.int_strategy = strategies.strategy(int)

    def own_flags(self):
        return ("allow_negative_floats",)

    def produce(self, size, flags):
        if flags.enabled("allow_negative_floats"):
            s2 = math.exp(2 * size) / (2 * math.pi * math.e)
            return random.gauss(0, s2)
        else:
            return random.expovariate(math.exp(1 - size))

    def complexity(self, x):
        return x if x >= 0 else 1 - x

    def simplify(self, x):
        if x < 0:
            yield -x

        n = int(x)
        y = float(n)
        if x != y: yield y
        for m in self.int_strategy.simplify(n):
            yield x + (m - n)

def h(p):
    return -(p * log(p) + (1-p) * log1p(-p))

def inverse_h(hd):
    if hd < 0: raise ValueError("Entropy h cannot be negative: %s" % h)
    if hd > 1: raise ValueError("Single bit entropy cannot be > 1: %s" % h)
    low = 0.0
    high = 0.5

    for _ in xrange(10):
        mid = (low + high) * 0.5
        if h(mid) < hd: low = mid
        else: high = mid

    return mid

@strategy_for(bool)
class BoolStrategy(SearchStrategy):
    def complexity(self,x):
        if x: return 1
        else: return 0

    def produce(self, size,flags):
        if size >= 1: p = 0.5
        else: p = inverse_h(size)
        if rand() >= p: return False
        return True

@strategy_for_instances(tuple)
class TupleStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.element_strategies = tuple((strategies.strategy(x) for x in descriptor))

    def child_strategies(self):
        return self.element_strategies

    def could_have_produced(self,xs):
        if not SearchStrategy.could_have_produced(self,xs): return False
        if len(xs) != len(self.element_strategies): return False
        return all((s.could_have_produced(x) for s,x in zip(self.element_strategies, xs)))

    def complexity(self, xs):
        return sum((s.complexity(x) for s,x in zip(self.element_strategies, xs)))

    def newtuple(self, xs):
        if self.descriptor.__class__ == tuple:
            return tuple(xs)
        else:
            return self.descriptor.__class__(*xs)

    def produce(self, size, flags):
        es = self.element_strategies
        return self.newtuple([g.produce(float(size)/len(es),flags) for g in es])

    def simplify(self, x):
        """
        Defined simplification for tuples: We don't change the length of the tuple
        we only try to simplify individual elements of it.
        We first try simplifying each index. We then try pairs of indices.
        After that we stop because it's getting silly.
        """

        for i in xrange(0, len(x)):
            for s in self.element_strategies[i].simplify(x[i]):
                z = list(x)
                z[i] = s
                yield self.newtuple(z)
        for i in xrange(0, len(x)):
            for j in xrange(0, len(x)):
                if i == j: continue
                for s in self.element_strategies[i].simplify(x[i]):
                    for t in self.element_strategies[j].simplify(x[j]):
                        z = list(x)
                        z[i] = s
                        z[j] = t
                        yield self.newtuple(z)


@strategy_for_instances(list)
class ListStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)

        self.element_strategy = strategies.strategy(one_of(descriptor))

    def own_flags(self):
        return ('allow_empty_lists',)

    def child_strategies(self):
        return (self.element_strategy,)

    def entropy_allocated_for_length(self, size):
        if size <= 2: return 0.5 * size;
        else: return min(0.05 * (size - 2.0) + 2.0, 6)

    def produce(self, size, flags):
        le = self.entropy_allocated_for_length(size)
        lp = geometric_probability_for_entropy(le)
        length = geometric_int(lp)
        empty_allowed = self.may_call_self_recursively() or flags.enabled('allow_empty_lists')
        if not empty_allowed:
            length += 1

        if length == 0:
            return []
        multiplier = 1.0/(1.0 - lp) if empty_allowed else 1.0
        element_entropy = multiplier * (size - le) / length
        return [self.element_strategy.produce(element_entropy,flags) for _ in xrange(length)]

    def simplify(self, x):
        indices = xrange(0, len(x))
        for i in indices:
            y = list(x)
            del y[i]
            yield y

        for i in indices:
            for s in self.element_strategy.simplify(x[i]):
                z = list(x)
                z[i] = s
                yield z

        for i in xrange(0,len(x) - 1):
            for j in xrange(i,len(x) - 1):
                y = list(x)
                del y[i]
                del y[j]
                yield y

class MappedSearchStrategy(SearchStrategy):
    @abstractmethod
    def pack(self, x):
        pass  # pragma: no cover

    @abstractmethod
    def unpack(self, x):
        pass  # pragma: no cover

    def child_strategies(self):
        return (self.mapped_strategy,)

    def produce(self, size, flags):
        return self.pack(self.mapped_strategy.produce(size,flags))

    def complexity(self, x):
        return self.mapped_strategy.complexity(self.unpack(x))

    def simplify(self, x):
        for y in self.mapped_strategy.simplify(self.unpack(x)):
            yield self.pack(y)


@strategy_for(complex)
class ComplexStrategy(MappedSearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy((float, float))

    def pack(self, x):
        return complex(*x)

    def unpack(self, x):
        return (x.real, x.imag)


@strategy_for_instances(set)
class SetStrategy(MappedSearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy(list(descriptor))

    def pack(self, x):
        return set(x)

    def unpack(self, x):
        return list(x)


class OneCharStringStrategy(SearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.characters = kwargs.get('characters', map(chr, range(0, 127)))
        self.zero_point = ord(kwargs.get('zero_point', '0'))

    def produce(self, size, flags):
        return choice(self.characters)

    def complexity(self, x):
        return abs(ord(x) - self.zero_point)

    def simplify(self, x):
        c = ord(x)
        if c < self.zero_point:
            yield chr(2 * self.zero_point - c)
            for d in xrange(c+1, self.zero_point + 1):
                yield chr(d)
        elif c > self.zero_point:
            for d in xrange(c - 1, self.zero_point - 1, -1):
                yield chr(d)


@strategy_for(str)
class StringStrategy(MappedSearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.length_strategy = strategies.strategy(int)
        char_strategy = kwargs.get("char_strategy",
                                   OneCharStringStrategy)

        cs = strategies.new_child_mapper()
        cs.define_specification_for(str, char_strategy)
        self.mapped_strategy = cs.strategy([str])

    def pack(self, ls):
        return ''.join(ls)

    def unpack(self, s):
        return list(s)


@strategy_for_instances(dict)
class FixedKeysDictStrategy(SearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.strategy_dict = {}
        for k, v in descriptor.items():
            self.strategy_dict[k] = strategies.strategy(v)

    def child_strategies(self):
        return self.strategy_dict.values()

    def produce(self, size, flags):
        result = {}
        for k, g in self.strategy_dict.items():
            result[k] = g.produce(size / len(self.strategy_dict), flags)
        return result

    def complexity(self, x):
        return sum((v.complexity(x[k]) for k, v in self.strategy_dict.items()))

    def simplify(self, x):
        for k, v in x.items():
            for s in self.strategy_dict[k].simplify(v):
                y = dict(x)
                y[k] = s
                yield y

OneOf = namedtuple('OneOf', 'elements')

def one_of(args):
    args = list(args)
    if not args:
        raise ValueError("one_of requires at least one value to choose from")
    if len(args) == 1:
        return args[0]
    return OneOf(args)

@strategy_for_instances(OneOf)
class OneOfStrategy(SearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.element_strategies = [strategies.strategy(x) for x in descriptor.elements]

    def own_flags(self):
        return tuple((self.personal_flag(d) for d in self.descriptor.elements))

    def child_strategies(self):
        return self.element_strategies

    def could_have_produced(self, x):
        return any((s.could_have_produced(x) for s in self.element_strategies))

    def how_many_elements_to_pick(self, size):
        max_entropy_to_use = size / 2
        n = len(self.element_strategies)
        if max_entropy_to_use >= log(n, 2):
            return n
        else:
            return int(2 ** max_entropy_to_use)

    def produce(self, size, flags):
        def enabled(c):
            return flags.enabled(self.personal_flag(c.descriptor))
        enabled_strategies = [
            es for es in self.element_strategies if enabled(es)
        ]
        enabled_strategies = enabled_strategies or self.element_strategies
        m = min(self.how_many_elements_to_pick(size), len(enabled_strategies))
        size -= log(m, 2)
        return choice(enabled_strategies[0:m]).produce(size, flags)

    def find_first_strategy(self, x):
        for s in self.element_strategies:
            if s.could_have_produced(x):
                return s
        else:
            raise ValueError(
                "Value %s could not have been produced from %s" % (x, self)
            )

    def complexity(self, x):
        return self.find_first_strategy(x).complexity(x)

    def simplify(self, x):
        return self.find_first_strategy(x).simplify(x)


Just = namedtuple('Just', 'value')
just = Just

@strategy_for_instances(Just)
class JustStrategy(SearchStrategy):
    def produce(self, size, flags):
        return self.descriptor.value

########NEW FILE########
__FILENAME__ = specmapper
from functools import wraps, total_ordering
from hypothesis.hashitanyway import HashItAnyway

class SpecificationMapper(object):
    """
    Maps descriptions of some type to a type. Has configurable handlers for what a description
    may look like. Handlers for descriptions may take either a specific value or all instances
    of a type and have access to the mapper to look up types.

    Also supports prototype based inheritance, with children being able to override specific handlers
    
    There is a single default() object per subclass of SpecificationMapper which everything has
    as a prototype if it's not assigned any other prototype. This allows you to easily define the
    mappers 
    """

    @classmethod
    def default(cls):
        try:
            if cls.default_mapper:
                return cls.default_mapper
        except AttributeError:
            pass
        cls.default_mapper = cls()
        return cls.default_mapper

    def __init__(self, prototype=None):
        self.value_mappers = {}
        self.instance_mappers = {}
        self.__prototype = prototype
        self.__descriptor_cache = {}

    def prototype(self):
      if self.__prototype: 
        return self.__prototype
      if self is self.default():
        return None
      return self.default()

    def cache_specification_for_descriptor(self, descriptor, spec):
        self.__descriptor_cache[HashItAnyway(descriptor)] = spec
    
    def define_specification_for(self, value, specification):
        self.value_mappers.setdefault(value,[]).append(specification)
        self.__descriptor_cache = {}

    def define_specification_for_instances(self, cls, specification):
        self.instance_mappers.setdefault(cls,[]).append(specification)
        self.__descriptor_cache = {}

    def define_specification_for_classes(self, specification,subclasses_of=None):
        if subclasses_of:
            original_specification = specification
            @wraps(specification)
            def restricted(sms, descriptor):
                if issubclass(descriptor,subclasses_of):
                    return original_specification(sms,descriptor)
                else:
                    return next_in_chain()
            specification = restricted

        self.define_specification_for_instances(typekey(SpecificationMapper), specification)

    def new_child_mapper(self):
      return self.__class__(prototype = self)

    def specification_for(self, descriptor):
        k = HashItAnyway(descriptor)
        if k in self.__descriptor_cache:
            return self.__descriptor_cache[k]
        
        for h in self.__find_specification_handlers_for(descriptor):
            try:
                r = h(self, descriptor)
                break
            except NextInChain:
                pass
        else: 
            r = self.missing_specification(descriptor)

        self.__descriptor_cache[k] = r
        return r

    def __find_specification_handlers_for(self, descriptor):
        if safe_in(descriptor, self.value_mappers):
            for h in reversed(self.value_mappers[descriptor]):
                yield h 
        tk = typekey(descriptor)
        for h in self.__instance_handlers(tk):
            yield h
        if self.prototype():
            for h in self.prototype().__find_specification_handlers_for(descriptor):
                yield h

    def __instance_handlers(self, tk):
        for c, hs in sorted(self.instance_mappers.items(), key = lambda x: ClassSorter(x[0])):
            if issubclass(tk, c):
                for h in reversed(hs):
                    yield h

    def missing_specification(self, descriptor):
        raise MissingSpecification(descriptor)

@total_ordering
class ClassSorter(object):
    def __init__(self, cls):
        self.cls = cls

    def __eq__(self, that):
        return self.cls == that.cls

    def __lt__(self, that):
        if self.cls == that.cls: return False
        elif issubclass(self.cls, that.cls): return True
        elif issubclass(that.cls, self.cls): return False
        else: return self.cls.__name__ < that.cls.__name__ 

def typekey(x):
    try:
        return x.__class__
    except AttributeError:
        return type(x)

def safe_in(x, ys):
    """
    Test if x is present in ys even if x is unhashable.
    """
    try:
        return x in ys
    except TypeError:
        return False

def next_in_chain():
    raise NextInChain()

class NextInChain(Exception):
    def __init__(self):
        Exception.__init__(self, "Not handled. Call next in chain. You shouldn't have seen this exception.")

class MissingSpecification(Exception):
    def __init__(self, descriptor):
        Exception.__init__(self, "Unable to produce specification for descriptor %s" % str(descriptor))

########NEW FILE########
__FILENAME__ = statefultesting
from hypothesis.searchstrategy import (
    SearchStrategy,
    SearchStrategies,
    MappedSearchStrategy,
    one_of,
)
from collections import namedtuple
from inspect import getmembers

import hypothesis


def step(f):
    f.hypothesis_test_step = True

    if not hasattr(f, 'hypothesis_test_requirements'):
        f.hypothesis_test_requirements = ()
    return f


def integrity_test(f):
    f.hypothesis_integrity_tests = True
    return f


def requires(*args):
    def alter_function(f):
        f.hypothesis_test_requirements = args
        return f
    return alter_function


class PreconditionNotMet(Exception):
    def __init__(self):
        Exception.__init__(self, "Precondition not met")


def precondition(t):
    if not t:
        raise PreconditionNotMet()


class TestRun(object):
    def __init__(self, cls, steps):
        self.cls = cls
        self.steps = steps

    def run(self):
        tests = self.cls.integrity_tests()
        value = self.cls()

        def run_integrity_tests():
            for t in tests:
                t(value)
        run_integrity_tests()
        for step, args in self.steps:
            try:
                step(value, *args)
                run_integrity_tests()
            except PreconditionNotMet:
                pass
        return True

    def prune(self):
        results = []
        v = self.cls()
        for s in self.steps:
            try:
                s[0](v, *s[1])
                results.append(s)
            except PreconditionNotMet:
                continue
            except Exception:
                results.append(s)
                break
        if len(results) == len(self):
            return None
        else:
            return TestRun(self.cls, results)

    def __eq__(self, that):
        return (isinstance(that, TestRun) and
                self.cls == that.cls and
                self.steps == that.steps)

    def __hash__(self):
        # Where we want to hash this we want to rely on Tracker's logic for
        # hashing collections anyway
        raise TypeError("unhashable type 'testrun'")

    def __len__(self):
        return len(self.steps)

    def __iter__(self):
        return self.steps.__iter__()

    def __getitem__(self, i):
        return self.steps[i]


class StatefulTest(object):
    @classmethod
    def test_steps(cls):
        return cls.functions_with_attributes('hypothesis_test_step')

    @classmethod
    def integrity_tests(cls):
        return cls.functions_with_attributes('hypothesis_integrity_tests')

    @classmethod
    def functions_with_attributes(cls, attr):
        return [v for _, v in getmembers(cls) if hasattr(v, attr)]

    @classmethod
    def breaking_example(cls):
        test_run = hypothesis.falsify(TestRun.run, cls)[0]
        return [(f.__name__,) + args for f, args in test_run]

Step = namedtuple("Step", ("target", "arguments"))


class StepStrategy(MappedSearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        self.mapped_strategy = strategies.strategy(
            descriptor.hypothesis_test_requirements
        )

    def could_have_produced(self, x):
        if not isinstance(x, Step):
            return False
        if x.target != self.descriptor:
            return False
        return self.mapped_strategy.could_have_produced(x.arguments)

    def pack(self, x):
        return Step(self.descriptor, x)

    def unpack(self, x):
        return x.arguments


class StatefulStrategy(MappedSearchStrategy):
    def __init__(self,
                 strategies,
                 descriptor,
                 **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor, **kwargs)
        step_strategies = [
            StepStrategy(strategies, s)
            for s in descriptor.test_steps()
        ]
        child_mapper = strategies.new_child_mapper()
        child_mapper.define_specification_for(
            Step,
            lambda sgs, _: sgs.strategy(one_of(step_strategies))
        )
        self.mapped_strategy = child_mapper.strategy([Step])

    def pack(self, x):
        return TestRun(self.descriptor, x)

    def unpack(self, x):
        return x.steps

    def simplify(self, x):
        pruned = x.prune()
        if pruned:
            yield pruned

        for y in MappedSearchStrategy.simplify(self, x):
            yield y

SearchStrategies.default().define_specification_for_classes(
    StatefulStrategy,
    subclasses_of=StatefulTest
)

########NEW FILE########
__FILENAME__ = testdecorators
from hypothesis.verifier import Verifier, Unfalsifiable, UnsatisfiedAssumption

def given(*generator_arguments,**kwargs):
    if "verifier" in kwargs:
        verifier = kwargs["verifier"]
        del kwargs["verifier"]
    else:
        verifier = Verifier()

    def run_test_with_generator(test):
        def wrapped_test(*arguments):
            # The only thing we accept in falsifying the test are exceptions 
            # Returning successfully is always a pass.
            def to_falsify(xs):
                testargs, testkwargs = xs
                try:
                    test(*(arguments + testargs), **testkwargs) 
                    return True
                except UnsatisfiedAssumption as e:
                    raise e
                except Exception:
                    return False

            try:
                falsifying_example = verifier.falsify(to_falsify, (generator_arguments, kwargs))[0]
            except Unfalsifiable:
                return
         
            # We run this one final time so we get good errors 
            # Otherwise we would have swallowed all the reports of it actually
            # having gone wrong.
            test(*(arguments + falsifying_example[0]), **falsifying_example[1])
        wrapped_test.__name__ = test.__name__
        wrapped_test.__doc__  = test.__doc__
        return wrapped_test
    return run_test_with_generator

########NEW FILE########
__FILENAME__ = test_falsification
from hypothesis.verifier import (
    falsify, 
    assume, 
    Unfalsifiable, 
    Unsatisfiable, 
    Verifier
)
from hypothesis.specmapper import MissingSpecification
from hypothesis.searchstrategy import (
    SearchStrategy, 
    MappedSearchStrategy,
    one_of,
    SearchStrategies,
    strategy_for
)
from collections import namedtuple
import pytest
import re

def test_can_make_assumptions():
    def is_good(x):
        assume(x > 5)
        return x % 2 == 0
    assert falsify(is_good, int)[0] == 7    

class Foo(object):
    pass

@strategy_for(Foo)
class FooStrategy(SearchStrategy):
    def produce(self, size, flags):
        return Foo()

def test_can_falsify_types_without_minimizers():
    assert isinstance(falsify(lambda x: False, Foo)[0], Foo)

class Bar(object):
    def __init__(self,bar=None):
        self.bar = bar

    def size(self):
        s = 0
        while self:
            self = self.bar
            s += 1
        return s

    def __repr__(self):
        return "Bar(%s)" % self.size()
 
    def __eq__(self,other): 
        return isinstance(other, Bar) and self.size() == other.size()

class BarStrategy(SearchStrategy):
    def __init__(self,strategies,descriptor):
        SearchStrategy.__init__(self,strategies,descriptor)
        self.int_strategy = strategies.strategy(int)

    def produce(self, size, flags):
        x = Bar()
        for _ in xrange(self.int_strategy.produce(size,flags)):
            x = Bar(x)
        return x

    def simplify(self, bar):
        while True:
            bar = bar.bar
            if bar: yield bar
            else: return 
     
def test_can_falsify_types_without_default_productions():
    strategies = SearchStrategies()
    strategies.define_specification_for(Bar, BarStrategy)

    with pytest.raises(MissingSpecification):
        SearchStrategies.default().strategy(Bar)

    verifier = Verifier(search_strategies = strategies)
    assert verifier.falsify(lambda x : False, Bar,)[0] == Bar()
    assert verifier.falsify(lambda x : x.size() < 3, Bar)[0] == Bar(Bar(Bar()))
    

def test_can_falsify_tuples():
    def out_of_order_positive_tuple(x):
        a,b = x
        assume(a > 0 and b > 0)
        assert a >= b
        return True
    assert falsify(out_of_order_positive_tuple, (int,int))[0] == (1,2)

def test_can_falsify_dicts():
    def is_good(x):
        assume("foo" in x)
        assume("bar" in x) 
        return x["foo"] < x["bar"]
    assert falsify(is_good, {"foo": int, "bar" : int})[0] == {"foo" : 0, "bar" : 0}
   

def test_can_falsify_assertions():
    def is_good(x):
        assert x < 3
        return True
    assert falsify(is_good, int)[0] == 3

def test_can_falsify_floats():
    x,y,z = falsify(lambda x,y,z: (x + y) + z == x + (y +z), float,float,float)
    assert (x + y) + z != x + (y + z)

def test_can_falsify_ints():
    assert falsify(lambda x: x != 0, int)[0] == 0

def test_can_find_negative_ints():
    assert falsify(lambda x: x >= 0, int)[0] == -1 

def test_can_find_negative_floats():
    assert falsify(lambda x : x > -1.0, float)[0] == -1.0

def test_can_falsify_int_pairs():
    assert falsify(lambda x,y: x > y, int,int) == (0,0)

def test_can_falsify_string_commutativity():
    assert tuple(sorted(falsify(lambda x,y: x + y == y + x,str,str))) == ('0','1')

def test_can_falsify_sets():
    assert falsify(lambda x: not x, {int})[0] == {0}

def test_can_falsify_list_inclusion():
    assert falsify(lambda x,y: x not in y, int, [int]) == (0,[0])

def test_can_falsify_set_inclusion():
    assert falsify(lambda x,y: x not in y, int, {int}) == (0,{0})

def test_can_falsify_lists():
    assert falsify(lambda x: len(x) < 3, [int])[0] == [0] * 3

def test_can_falsify_long_lists():
    assert falsify(lambda x: len(x) < 20, [int],warming_rate=0.5)[0] == [0] * 20 

def test_can_find_unsorted_lists():
    unsorted = falsify(lambda x: sorted(x) == x, [int])[0] 
    assert unsorted == [1,0] or unsorted == [0,-1]

def is_pure(xs):
    return len(set([a.__class__ for a in xs])) <= 1

def test_can_falsify_mixed_lists():
    xs = falsify(is_pure, [int,str])[0]
    assert len(xs) == 2
    assert 0 in xs
    assert "" in xs

def test_can_produce_long_mixed_lists_with_only_a_subset():
    def is_good(xs):
        if len(xs) < 20: return True 
        if any((isinstance(x, int) for x in xs)): return True
        return False
        
    falsify(is_good, [int,str])

def test_can_falsify_alternating_types():
    falsify(lambda x: isinstance(x, int), one_of([int, str]))[0] == ""

class HeavilyBranchingTree(object):
    def __init__(self, children):
        self.children = children

    def depth(self):
        if not self.children:
            return 1
        else:
            return 1 + max(map(HeavilyBranchingTree.depth, self.children))

@strategy_for(HeavilyBranchingTree)
class HeavilyBranchingTreeStrategy(MappedSearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.mapped_strategy = strategies.strategy([HeavilyBranchingTree])

    def pack(self, x):
        return HeavilyBranchingTree(x)

    def unpack(self, x):
        return x.children

def test_can_go_deep_into_recursive_strategies():
    falsify(lambda x: x.depth() <= 5, HeavilyBranchingTree)

def test_can_falsify_string_matching():
    # Note that just doing a match("foo",x) will never find a good solution
    # because the state space is too large
    assert falsify(lambda x: not re.search("a.*b",x), str)[0] == "ab"

def test_minimizes_strings_to_zeroes():
    assert falsify(lambda x: len(x) < 3, str)[0] == "000"

def test_can_find_short_strings():
    assert falsify(lambda x: len(x) > 0, str)[0] == ""
    assert len(falsify(lambda x: len(x) <= 1, str)[0]) == 2
    assert falsify(lambda x : len(x) < 10, [str])[0] == [""] * 10


def test_stops_loop_pretty_quickly():
    with pytest.raises(Unfalsifiable):
        falsify(lambda x: x == x, int)

def test_good_errors_on_bad_values():
    some_string = "I am the very model of a modern major general"
    with pytest.raises(MissingSpecification) as e:
        falsify(lambda x: False, some_string)

    assert some_string in e.value.args[0]

def test_can_falsify_bools():
    assert falsify(lambda x: x, bool)[0] == False

def test_can_falsify_lists_of_bools():
    falsify(lambda x : len([y for y in x if not y]) <= 5, [bool])

def test_can_falsify_empty_tuples():
    assert falsify(lambda x: False, ())[0] == ()


class BinaryTree(object):
    pass

class Leaf(BinaryTree):
    def __init__(self, label):
        self.label = label

    def depth(self):
        return 0

    def breadth(self):
        return 1

    def __eq__(self, that):
        return isinstance(that, Leaf) and self.label == that.label

    def __hash__(self):
        return hash(self.label)

class Split(BinaryTree):
    def __init__(self,left,right):
        self.left = left
        self.right = right

    def depth(self):
        return 1 + max(self.left.depth(), self.right.depth())

    def breadth(self):
        return self.left.breadth() + self.right.breadth()

    def __eq__(self, that):
        return isinstance(that, Split) and that.left == self.left and that.right == self.right

    def __hash__(self):
        return hash(self.left) ^ hash(self.right)

@strategy_for(Leaf)
class LeafStrategy(MappedSearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.mapped_strategy = strategies.strategy(int)

    def pack(self, x):
        return Leaf(x)
    def unpack(self,x):
        return x.label
    
@strategy_for(Split)
class SplitStrategy(MappedSearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.mapped_strategy = strategies.strategy((BinaryTree, BinaryTree))
                       
    def pack(self, x):
        return Split(*x)
    def unpack(self,x):
        return (x.left, x.right)

@strategy_for(BinaryTree)
class BinaryTreeStrategy(MappedSearchStrategy):
    def __init__(   self,
                    strategies,
                    descriptor,
                    **kwargs):
        SearchStrategy.__init__(self, strategies, descriptor,**kwargs)
        self.mapped_strategy = strategies.strategy(one_of([Leaf, Split]))
       
    def child_strategies(self):
        return ()
 
    def pack(self,x):
        return x

    def unpack(self,x):
        return x

def test_can_produce_deep_binary_trees():
    falsify(lambda x: x.depth() <= 2, BinaryTree)

Litter = namedtuple("Litter", ("kitten1", "kitten2"))
def test_can_falsify_named_tuples():
    pair = falsify(lambda x: x.kitten1 < x.kitten2, Litter(str,str))[0]
    assert isinstance(pair,Litter)
    assert pair == Litter("","")

def test_can_falsify_complex_numbers():
    falsify(lambda x: x == (x ** 2) ** 0.5, complex)

    with pytest.raises(Unfalsifiable):
        falsify(lambda x,y: (x * y).conjugate() == x.conjugate() * y.conjugate(), complex, complex)

def test_raises_on_unsatisfiable_assumption():
    with pytest.raises(Unsatisfiable):
        falsify(lambda x: assume(False), int)

########NEW FILE########
__FILENAME__ = test_flags
import hypothesis.searchstrategy as ss
from hypothesis.flags import Flags

def flags(*args,**kwargs):
    return ss.SearchStrategies().strategy(*args,**kwargs).flags().flags

def test_tuple_contains_all_child_flags():
    assert flags(int).issubset(flags((int, str)))
    assert flags(str).issubset(flags((int, str)))

def test_one_of_contains_all_child_flags():
    assert flags(int).issubset(flags(ss.one_of([int, str])))
    assert flags(str).issubset(flags(ss.one_of([int, str])))

def test_list_contains_all_child_flags():
    assert flags(int).issubset(flags([int]))
    assert flags(int).issubset(flags([int, str]))
    assert flags(str).issubset(flags([int, str]))

def test_flags_not_enabled_by_default():
    flags = Flags()
    assert not flags.enabled("foo")

def test_enabling_flags_leaves_original_unchanged():
    flags = Flags()
    assert not flags.enabled("foo")
    flags2 = flags.with_enabled("foo")
    assert not flags.enabled("foo")
    assert flags2.enabled("foo")

def test_can_disable_flags():
    flags = Flags(["foo"])
    assert flags.enabled("foo")
    flags2 = flags.with_disabled("foo")
    assert not flags2.enabled("foo")

def test_str_contains_flags():
    assert "foo" in str(Flags(["foo"]))
    assert "foo" in str(Flags(["foo", "bar"]))
    assert "bar" in str(Flags(["foo", "bar"]))

########NEW FILE########
__FILENAME__ = test_hashitanyway
from hypothesis.hashitanyway import HashItAnyway
from collections import namedtuple

def hia(x):
    return HashItAnyway(x)

def test_respects_equality_of_ints():
    assert hia(1) == hia(1)
    assert hia(1) != hia(2)

def test_respects_equality_of_lists_of_ints():
    assert hia([1,1]) == hia([1,1])
    assert hia([1,2]) == hia([1,2])

def test_respects_equality_of_types():
    assert hia(int) == hia(int)
    assert hia(int) != hia(str)

def test_respects_equality_of_lists_of_types():
    assert hia([int,str]) == hia([int,str])
    assert hia([str,int]) != hia([int,str])

def test_hashes_lists_deterministically():
    assert hash(hia([int,str])) == hash(hia([int,str]))

class Foo():
    def __hash__(self):
        raise TypeError("Unhashable type Foo")

def test_can_use_non_iterable_non_hashables_as_a_dict_key():
    d = {}
    x = hia(Foo())
    d[x] = 1
    assert d[x] == 1
    y = hia(Foo())
    d[y] = 2
    assert d[x] == 1
    assert d[y] == 2
   
def test_can_use_old_style_class_objects_as_a_dict_key():
    d = {}
    x = hia(Foo)
    d[x] = 1
    assert d[x] == 1 

def test_works_correctly_as_a_dict_key():
    k1 = hia([int,str]) 
    k2 = hia([int,str]) 
    d = {}
    d[k1]  = "hi"
    assert d[k2] == "hi"
    d[k2] = "bye"
    assert d[k1] == "bye"
    assert len(d) == 1

Hi = namedtuple("Hi", ("a", "b"))

def test_should_regard_named_tuples_as_distinct_from_unnamed():
    assert Hi(1,2) == (1,2)
    assert hia(Hi(1,2)) != hia((1,2))

def test_has_a_sensible_string_representation():
    x = str(hia("kittens"))
    assert "HashItAnyway" in x
    assert "kittens" in x

########NEW FILE########
__FILENAME__ = test_searchstrategy
import hypothesis.searchstrategy as ss
from hypothesis.flags import Flags
from hypothesis.tracker import Tracker
from collections import namedtuple

def strategy(*args,**kwargs):
    return ss.SearchStrategies().strategy(*args,**kwargs)

def test_tuples_inspect_component_types_for_production():
    strxint = strategy((str,int))

    assert strxint.could_have_produced(("", 2))
    assert not strxint.could_have_produced((2, 2))

    intxint = strategy((int,int))
    
    assert not intxint.could_have_produced(("", 2))
    assert intxint.could_have_produced((2, 2))

def alternating(*args):
    return strategy(ss.one_of(args))

def minimize(s, x):
    for t in s.simplify_such_that(x, lambda _: True):
        x = t
    return x

def test_can_minimize_component_types():
    ios = alternating(str, int)
    assert 0  == minimize(ios, 10)
    assert "" == minimize(ios, "I like kittens")

def test_can_minimize_nested_component_types():
    ios = alternating((int,str), (int,int))
    assert (0,"") == minimize(ios, (42, "I like kittens"))
    assert (0,0)  == minimize(ios, (42, 666))

def test_can_minimize_tuples():
    ts = strategy((int,int,int))
    assert minimize(ts, (10,10,10)) == (0,0,0)

def assert_no_duplicates_in_simplify(s, x):
    s = strategy(s)
    t = Tracker()
    t.track(x)
    for y in s.simplify(x):
        assert t.track(y) == 1


def test_ints_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify(int, 555)


def test_int_lists_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify([int], [0, 555, 1281])


def test_float_lists_no_duplicates_in_simplify():
    assert_no_duplicates_in_simplify([float], [0.5154278802175156, 555.0, 1281.8556018727038])


def test_just_works():
    s = strategy(ss.just("giving"))
    assert s.produce(10, Flags()) == "giving"
    assert list(s.simplify_such_that("giving", lambda _: True)) == ["giving"]


Litter = namedtuple("Litter", ("kitten1", "kitten2"))
def test_named_tuples_always_produce_named_tuples():
    s = strategy(Litter(int,int))

    for i in xrange(100):
        assert isinstance(s.produce(i, Flags()), Litter)

    for x in s.simplify(Litter(100,100)):
        assert isinstance(x, Litter)

def test_strategy_repr_handles_dicts():
    s = repr(strategy({"foo" : int, "bar": str}))
    assert "foo" in s
    assert "bar" in s
    assert "int" in s
    assert "str" in s

def test_strategy_repr_handles_tuples():
    s = repr(strategy((str, str)))
    assert "(str, str)" in s

def test_strategy_repr_handles_bools():
    s = repr(strategy(bool))
    assert "(bool)" in s

class X(object):
    def __init__(self, x):
        self.x = x

    def __repr__(self):
        return "X(%s)" % str(self.x)

@ss.strategy_for_instances(X)
class XStrategy(ss.MappedSearchStrategy):
    def __init__(self,strategies,descriptor):
        ss.SearchStrategy.__init__(self,strategies,descriptor)
        self.mapped_strategy = strategies.strategy(descriptor.x)

    def pack(self,x):
        return X(x)

    def unpack(self,x):
        return x.x

def test_strategy_repr_handles_custom_types():
    assert "X(x=str)" in repr(ss.SearchStrategies().strategy(X(str)))

class TrivialStrategy(ss.SearchStrategy):
    def produce(size, flags):
        return 0

def test_strategy_repr_handles_instances_without_dicts():
    strats = ss.SearchStrategies()
    strats.define_specification_for_instances(int, TrivialStrategy)
    
    assert repr(strats.strategy(42)) == "TrivialStrategy(42)"
    
def test_returns_all_child_strategies_from_list():
    strat = ss.SearchStrategies().strategy([int,[str,float]])

    children = [s.descriptor for s in strat.all_child_strategies()]
    
    assert int in children
    assert str in children
    assert float in children
    assert [str, float] in children

def test_returns_no_duplicate_child_strategies():
    strat = ss.SearchStrategies().strategy([int,[int,float]])
    children = [s.descriptor for s in strat.all_child_strategies()]
    assert len([x for x in children if x == int]) == 1

########NEW FILE########
__FILENAME__ = test_specmapper
from hypothesis.specmapper import (
    SpecificationMapper,
    MissingSpecification,
    next_in_chain
)
import pytest
from collections import namedtuple


def setup_function(fn):
    SpecificationMapper.default_mapper = None
    fn()


def const(x):
    return lambda *args: x


def test_can_define_specifications():
    sm = SpecificationMapper()
    sm.define_specification_for("foo", const(1))
    assert sm.specification_for("foo") == 1


def test_can_define_specifications_on_the_default():
    sm = SpecificationMapper()
    SpecificationMapper.default().define_specification_for("foo", const(1))
    assert sm.specification_for("foo") == 1


class Bar(object):
    pass


def test_can_define_specifications_for_classes():
    sm = SpecificationMapper()
    sm.define_specification_for(Bar, const(1))
    assert sm.specification_for(Bar) == 1


def test_can_define_specifications_for_built_in_types():
    sm = SpecificationMapper()
    sm.define_specification_for(Bar, const(1))
    assert sm.specification_for(Bar) == 1


def test_can_define_instance_specifications():
    sm = SpecificationMapper()
    sm.define_specification_for_instances(str, lambda _, i: i + "bar")
    assert sm.specification_for("foo") == "foobar"


def test_can_define_instance_specifications_on_the_default():
    sm = SpecificationMapper()
    SpecificationMapper.default().define_specification_for_instances(
        str,
        lambda _, i: i + "bar"
    )
    assert sm.specification_for("foo") == "foobar"


def test_can_define_instance_specifications_for_lists():
    sm = SpecificationMapper()
    sm.define_specification_for_instances(list, lambda _, l: len(l))
    assert sm.specification_for([1, 2]) == 2


def test_raises_missing_specification_with_no_spec():
    sm = SpecificationMapper()
    with pytest.raises(MissingSpecification):
        sm.specification_for("hi")


def test_can_create_children():
    sm = SpecificationMapper()
    child = sm.new_child_mapper()
    sm.define_specification_for("foo", const(1))
    assert child.specification_for("foo") == 1


def test_can_override_in_children():
    sm = SpecificationMapper()
    child = sm.new_child_mapper()
    sm.define_specification_for("foo", const(1))
    child.define_specification_for("foo", const(2))
    assert sm.specification_for("foo") == 1
    assert child.specification_for("foo") == 2


class ChildMapper(SpecificationMapper):
    pass


def test_does_not_inherit_default():
    assert ChildMapper.default() != SpecificationMapper.default()
    SpecificationMapper.default().define_specification_for("foo", const(1))
    with pytest.raises(MissingSpecification):
        ChildMapper.default().specification_for("foo")


def test_can_call_other_specs():
    s = SpecificationMapper()
    s.define_specification_for("foo", const(1))
    s.define_specification_for(
        "bar",
        lambda t, _: t.specification_for("foo") + 1
    )
    assert s.specification_for("bar") == 2


def test_child_can_call_other_specs_on_prototype():
    s = SpecificationMapper()
    s.define_specification_for(
        "bar",
        lambda t, d: t.specification_for("foo") + 1
    )
    s2 = s.new_child_mapper()
    s2.define_specification_for("foo", const(1))
    assert s2.specification_for("bar") == 2


def test_can_override_specifications():
    s = SpecificationMapper()
    s.define_specification_for("foo", const(1))
    s.define_specification_for("foo", const(2))
    assert s.specification_for("foo") == 2


def test_can_override_instance_specifications():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, const(1))
    s.define_specification_for_instances(str, const(2))
    assert s.specification_for("foo") == 2


def test_can_call_previous_in_overridden_specifications():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, lambda _, s: len(s))
    s.define_specification_for_instances(
        str,
        lambda _, s: 5 if len(s) > 5 else next_in_chain()
    )
    assert s.specification_for("foo") == 3
    assert s.specification_for(
        "I am the very model of a modern major general"
    ) == 5


class Foo(object):
    pass


class Fooc(Foo):
    pass


class Baz(object):
    pass


def test_can_define_class_specifications():
    s = SpecificationMapper()
    s.define_specification_for_classes(lambda _, c: c())
    assert s.specification_for(Foo).__class__ == Foo


def test_can_define_class_specifications_for_subclasses():
    s = SpecificationMapper()
    s.define_specification_for_classes(const(1))
    s.define_specification_for_classes(const(2), subclasses_of=Foo)
    assert s.specification_for(Foo) == 2
    assert s.specification_for(Fooc) == 2
    assert s.specification_for(Baz) == 1


def test_multiple_calls_return_same_value():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, lambda *_: Foo())

    assert s.specification_for("foo") is s.specification_for("foo")
    assert s.specification_for("foo") is not s.specification_for("bar")


def test_defining_new_handlers_resets_cache():
    s = SpecificationMapper()
    s.define_specification_for_instances(str, lambda *_: Foo())
    x = s.specification_for("foo")
    s.define_specification_for_instances(str, lambda *_: Fooc())
    y = s.specification_for("foo")
    assert y is not x
    assert isinstance(y, Fooc)


def test_cache_correctly_handles_inheritance():
    s = SpecificationMapper()
    s.define_specification_for_instances(
        list,
        lambda s, d: [s.specification_for(d[0])]
    )
    t = s.new_child_mapper()
    t.define_specification_for_instances(str, lambda *_: Foo())

    x = t.specification_for("foo")
    y = t.specification_for(["foo"])[0]
    assert x is y


Litter = namedtuple("Litter", ("kitten1", "kitten2"))


def test_can_handle_subtypes_of_instances():
    s = SpecificationMapper()
    s.define_specification_for_instances(tuple, lambda s, d: sum(d))

    assert s.specification_for((1, 2)) == 3
    assert s.specification_for(Litter(2, 2)) == 4


def test_can_override_handlers_for_supertypes():
    s = SpecificationMapper()
    s.define_specification_for_instances(tuple, lambda s, d: sum(d))
    s.define_specification_for_instances(Litter, lambda s, d: len(d))

    assert s.specification_for((1, 2)) == 3
    assert s.specification_for(Litter(2, 2)) == 2


def test_can_handle_large_numbers_of_instance_mappers():
    def f(s, x):
        return str(x)

    s = SpecificationMapper()
    s.define_specification_for_instances(tuple, f)
    s.define_specification_for_instances(Litter, f)
    s.define_specification_for_instances(list, f)
    s.define_specification_for_instances(set, f)
    s.define_specification_for_instances(str, f)
    s.define_specification_for_instances(int, f)

    assert s.specification_for((1, 1)) == "(1, 1)"

########NEW FILE########
__FILENAME__ = test_statefultesting
from hypothesis.statefultesting import (
    StatefulTest, 
    step, 
    requires,
    precondition,
    integrity_test
)

class Foo(StatefulTest):
    @integrity_test
    def are_you_still_there(self): 
        assert True

    @step
    def blargh(self): pass

    def bar(self): pass

    @step
    def baz(self): pass

def test_picks_up_only_annotated_methods_as_operations():
    assert len(Foo.test_steps()) == 2
    assert len(Foo.integrity_tests()) == 1

class BrokenCounter(StatefulTest):
    def __init__(self):
        self.value = 0

    @step
    def inc(self):
        start_value = self.value
        self.value += 1
        assert self.value == start_value + 1

    @step
    def dec(self):
        precondition(self.value > 0)
        start_value = self.value
        if(self.value != 5): self.value -= 1
        assert self.value == start_value - 1

def test_finds_broken_example():
    assert [x[0] for x in BrokenCounter.breaking_example()] == ['inc'] * 5 + ['dec']

class AlwaysBroken(StatefulTest):
    @step
    def do_something(self):
        pass

    @integrity_test
    def go_boom(self):
        assert False


def test_runs_integrity_checks_initially():
    assert len(AlwaysBroken.breaking_example()) == 0

class SubclassAlwaysBroken(AlwaysBroken):
    pass

class SubclassBrokenCounter(BrokenCounter):
    pass

def test_subclassing_tests_inherits_steps_and_checks():
    SubclassAlwaysBroken.breaking_example()
    SubclassBrokenCounter.breaking_example()
    


class QuicklyBroken(StatefulTest):
    def __init__(self):
        self.value = 0

    @step
    def inc(self):
        self.value += 1

    @integrity_test
    def is_small(self):
        assert self.value < 2

def test_runs_integrity_checks_after_each_step():
    assert len(QuicklyBroken.breaking_example()) == 2

class FiveHater(StatefulTest):
    @requires(int)
    @step
    def hates_fives(self, n):
        assert n < 5

def test_minimizes_arguments_to_steps():
    steps = FiveHater.breaking_example()
    assert len(steps) == 1
    assert steps[0][1] == 5

class BadSet(object):
    def __init__(self):
        self.data = []

    def add(self, arg):
        self.data.append(arg)

    def remove(self, arg):
        for i in xrange(0, len(self.data)):
            if self.data[i] == arg:
                del self.data[i]
                break

    def contains(self, arg):
        return arg in self.data

    def clear(self):
        self.data = []

class BadSetTester(StatefulTest):
    def __init__(self):
        self.target = BadSet()

    @step
    @requires(int)
    def add(self,i):
        self.target.add(i)
        assert self.target.contains(i)

    @step
    @requires(int)
    def remove(self,i):
        self.target.remove(i)
        assert not self.target.contains(i)

    @step
    def clear(self):
        self.target.clear()

def test_bad_set_finds_minimal_break():
    # Try it a lot to make sure this isn't passing by coincidence
    for _ in xrange(10):
        breaking_example = BadSetTester.breaking_example()
        assert len(breaking_example) == 3
        assert len(set([s[1] for s in breaking_example])) == 1

########NEW FILE########
__FILENAME__ = test_testdecorators
from hypothesis.testdecorators import given
from hypothesis.verifier import Verifier, assume
from functools import wraps
import pytest


def fails(f):
    @wraps(f)
    def inverted_test(*arguments, **kwargs):
        with pytest.raises(AssertionError):
            f(*arguments, **kwargs)
    return inverted_test


@given(int, int)
def test_int_addition_is_commutative(x, y):
    assert x + y == y + x


@fails
@given(str, str)
def test_str_addition_is_commutative(x, y):
    assert x + y == y + x


@given(int, int, int)
def test_int_addition_is_associative(x, y, z):
    assert x + (y + z) == (x + y) + z


@fails
@given(float, float, float)
def test_float_addition_is_associative(x, y, z):
    assert x + (y + z) == (x + y) + z


@given([int])
def test_reversing_preserves_integer_addition(xs):
    assert sum(xs) == sum(reversed(xs))


@fails
@given([float])
def test_reversing_does_not_preserve_float_addition(xs):
    assert sum(xs) == sum(reversed(xs))


def test_still_minimizes_on_non_assertion_failures():
    @given(int, verifier=Verifier(starting_size=500))
    def is_not_too_large(x):
        if x >= 10:
            raise ValueError("No, %s is just too large. Sorry" % x)

    with pytest.raises(ValueError) as exinfo:
        is_not_too_large()

    assert " 10 " in exinfo.value.args[0]


@given(int)
def test_integer_division_shrinks_positive_integers(n):
    assume(n > 0)
    assert n/2 < n


class TestCases(object):
    @given(int)
    def test_abs_non_negative(self, x):
        assert abs(x) >= 0

    @fails
    @given(int)
    def test_int_is_always_negative(self, x):
        assert x < 0

    @fails
    @given(float, float)
    def test_float_addition_cancels(self, x, y):
        assert x + (y - x) == y


@fails
@given(int, name=str)
def test_can_be_given_keyword_args(x, name):
    assume(x > 0)
    assert len(name) < x

########NEW FILE########
__FILENAME__ = test_tracker
from hypothesis.tracker import Tracker


def test_track_ints():
    t = Tracker()
    assert t.track(1) == 1
    assert t.track(1) == 2


def test_track_lists():
    t = Tracker()
    assert t.track([1]) == 1
    assert t.track([1]) == 2


def test_nested_unhashables():
    t = Tracker()
    x = {"foo": [1, 2, {3, 4, 5, 6}], "bar": 10}
    assert t.track(x) == 1
    assert t.track(x) == 2

########NEW FILE########
__FILENAME__ = tracker
from hypothesis.hashitanyway import HashItAnyway

class Tracker(object):
    def __init__(self):
        self.contents = {}

    def track(self,x):
        k = HashItAnyway(x)
        n = self.contents.get(k, 0) + 1 
        self.contents[k] = n
        return n

    def __iter__(self):
        for k,v in self.contents.items():
            yield k.wrapped, v

########NEW FILE########
__FILENAME__ = verifier
from hypothesis.searchstrategy import SearchStrategies
from hypothesis.flags import Flags
from random import random
import time


def assume(condition):
    if not condition:
        raise UnsatisfiedAssumption()


class Verifier(object):
    def __init__(self,
                 search_strategies=None,
                 starting_size=1.0,
                 warming_rate=0.5,
                 cooling_rate=0.1,
                 runs_to_explore_flags=3,
                 min_satisfying_examples=5,
                 max_size=512,
                 max_failed_runs=10,
                 timeout=60):
        self.search_strategies = search_strategies or SearchStrategies()
        self.min_satisfying_examples = min_satisfying_examples
        self.starting_size = starting_size
        self.warming_rate = warming_rate
        self.cooling_rate = cooling_rate
        self.max_size = max_size
        self.max_failed_runs = max_failed_runs
        self.runs_to_explore_flags = runs_to_explore_flags
        self.timeout = timeout
        self.start_time = time.time()

    def time_to_call_it_a_day(self):
        return time.time() > self.start_time + self.timeout

    def falsify(self, hypothesis, *argument_types):
        search_strategy = (self.search_strategies
                               .specification_for(argument_types))
        flags = None
        timed_out = False
        # TODO: This is a sign that I should be pulling some of this out into
        # an object.
        examples_found = [0]

        def falsifies(args):
            try:
                examples_found[0] += 1
                return not hypothesis(*args)
            except AssertionError:
                return True
            except UnsatisfiedAssumption:
                examples_found[0] -= 1
                return False

        temperature = self.starting_size
        falsifying_examples = []

        def look_for_a_falsifying_example(size):
            x = search_strategy.produce(size, flags)
            if falsifies(x):
                falsifying_examples.append(x)
                return True
            else:
                return False

        while temperature < self.max_size:
            if self.time_to_call_it_a_day():
                timed_out = True
                break
            rtf = self.runs_to_explore_flags
            for i in xrange(self.runs_to_explore_flags):
                # Try a number of degrees of turning flags on, spaced evenly
                # but with the lowest probability of a flag being on being > 0
                # and the highest < 1.
                # Note that as soon as we find a falsifying example with a set
                # of flags, those are the flags we'll be using for the rest of
                # the run
                p = float(i + 1)/(rtf + 1)

                def generate_flags():
                    return Flags([
                        x
                        for x in search_strategy.flags().flags
                        if random() <= p])
                flags = generate_flags()
                look_for_a_falsifying_example(temperature)
                if falsifying_examples:
                    break
            if falsifying_examples:
                    break
            temperature += self.warming_rate

        if not falsifying_examples:
            ef = examples_found[0]
            if ef < self.min_satisfying_examples:
                raise Unsatisfiable(hypothesis, ef)
            elif timed_out:
                raise Timeout(hypothesis, self.timeout)
            else:
                raise Unfalsifiable(hypothesis)

        failed_runs = 0
        while temperature > 1 and failed_runs < self.max_failed_runs:
            if not look_for_a_falsifying_example(temperature):
                failed_runs += 1

            temperature -= self.cooling_rate

        best_example = min(falsifying_examples, key=search_strategy.complexity)

        for t in search_strategy.simplify_such_that(best_example, falsifies):
            best_example = t
            if self.time_to_call_it_a_day():
                break

        return best_example


def falsify(*args, **kwargs):
    return Verifier(**kwargs).falsify(*args)


class HypothesisException(Exception):
    pass


class UnsatisfiedAssumption(HypothesisException):
    def __init__(self):
        super(UnsatisfiedAssumption, self).__init__("Unsatisfied assumption")


class Unfalsifiable(HypothesisException):
    def __init__(self, hypothesis, extra=''):
        super(Unfalsifiable, self).__init__(
            "Unable to falsify hypothesis %s%s" % (hypothesis, extra)
        )


class Unsatisfiable(HypothesisException):
    def __init__(self, hypothesis, examples):
        super(Unsatisfiable, self).__init__(
            ("Unable to satisfy assumptions of hypothesis %s. " +
             "Only %s examples found ") % (hypothesis, str(examples)))


class Timeout(Unfalsifiable):
    def __init__(self, hypothesis, timeout):
        super(Timeout, self).__init__(
            hypothesis,
            " after %.2fs" % (timeout,)
        )

########NEW FILE########
