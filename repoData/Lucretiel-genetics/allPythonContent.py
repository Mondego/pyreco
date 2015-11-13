__FILENAME__ = cross
import itertools
import random


def one_point_crossover(length):
    point = random.randint(0, length)
    yield from itertools.repeat(True, point)
    yield from itertools.repeat(False, length - point)


def two_point_crossover(length):
    points = sorted(random.randint(0, length) for _ in range(2))
    yield from itertools.repeat(True, points[0])
    yield from itertools.repeat(False, points[1] - points[0])
    yield from itertools.repeat(True, length - points[1])


def uniform_point_crossover(length):
    return (random.choice((False, True)) for i in range(length))

########NEW FILE########
__FILENAME__ = base
import abc


class DNABase(metaclass=abc.ABCMeta):
    '''
    DNABase is the base class for all dna. It defines the abstract methods that
    all DNA should have, as well as an __lt__ method for sorting.
    '''
    @abc.abstractmethod
    def total_length(self):
        '''
        This method returns the total length of this DNA. For dna with
        subcomponents, it should return the sum of the lengths of those
        components. See DNASegment for an example
        '''
        pass

    @abc.abstractmethod
    def mutate(self, mask):
        '''
        This method should return a DNA object that is the result of applying
        the mutation mask to each component of this DNA. It is allowed to
        return self if and only if the mask application doesn't change the dna
        at all.
        '''
        pass

    @abc.abstractmethod
    def combine(self, other, mask):
        '''
        Return a tuple of two new DNAs that are the result of combining this
        DNA with other, using the mask.
        '''
        pass

    def __lt__(self, other):
        return self.score < other.score

    def has_score(self):
        return hasattr(self, 'score')


def combine_element_pairs(pairs):
    '''
    When given an iterable that returns pairs- such as
    [(1, 2), (3, 4), (5, 6)] combine them into a pair of iterables, such as
    ((1, 3, 5), (2, 4, 6))
    '''

    return tuple(zip(*pairs))

########NEW FILE########
__FILENAME__ = binary
import random
from .base import DNABase, combine_element_pairs


class DNABinary(DNABase):
    '''
    DNABinary is a relatively efficient implementation of DNA in which each
    component is only a bit.
    '''
    def __init__(self, bits):
        #Allows for initializers of the form '1000101'
        if isinstance(bits, str):
            bits = map(int, bits)

        #Allows for length initializers
        if isinstance(bits, int):
            bits = (random.choice((True, False)) for _ in range(bits))
        self.components = tuple(map(bool, bits))

    def total_length(self):
        return len(self.components)

    def mutate(self, mutate_mask):
        return DNABinary(random.choice((True, False)) if mask else c
                         for c, mask in zip(self.components, mutate_mask))

    def combine(self, other, combine_mask):
        def combine_generator():
            for c1, c2, mask in zip(self, other, combine_mask):
                yield (c1, c2) if mask else (c2, c1)

        child1, child2 = combine_element_pairs(combine_generator())

        return DNABinary(child1), DNABinary(child2)

    #iteration
    def __iter__(self):
        return iter(self.components)

    def __len__(self):
        return len(self.components)

    def __getitem__(self, index):
        return self.components[index]

########NEW FILE########
__FILENAME__ = component
from .base import DNABase


class DNAComponent(DNABase):
    '''
    A dna component is a single, indivisible value in the dna. Subclasses
    should provide a mutate_value() for mutation and an initial_value()
    function for argument-free initialization. If no initial_value function
    exists, mutate_value will be used
    '''
    def __init__(self, initial_value=None):
        if initial_value is None:
            try:
                self.value = self.initial_value()
            except AttributeError:
                self.value = self.mutate_value()
        else:
            self.value = initial_value

    def total_length(self):
        return 1

    def mutate(self, mutate_mask):
        if next(iter(mutate_mask)):
            return type(self)(self.mutate_value())
        else:
            return self

    def combine(self, other, cross_mask):
        if next(iter(cross_mask)):
            return (self, other)
        else:
            return (other, self)

########NEW FILE########
__FILENAME__ = segment
from .base import DNABase, combine_element_pairs


class DNASegment(DNABase):
    def __init__(self, components=None):
        '''
        If no initializer is given, there should be an initial_components()
        '''
        if components is None:
            components = self.initial_components()
        self.components = tuple(components)

    def total_length(self):
        return sum(c.total_length() for c in self.components)

    def mutate(self, mutate_mask):
        iter_mutate_mask = iter(mutate_mask)
        return type(self)(c.mutate(iter_mutate_mask) for c in self.components)

    def combine(self, other, cross_mask):
        iter_cross_mask = iter(cross_mask)

        def combine_generator():
            for c1, c2 in zip(self, other):
                yield c1.combine(c2, iter_cross_mask)

        child1, child2 = combine_element_pairs(combine_generator())

        return type(self)(child1), type(self)(child2)

    # Iteration protocol
    def __iter__(self):
        return iter(self.components)

    def __len__(self):
        return len(self.components)

    def __getitem__(self, index):
        return self.components[index]

########NEW FILE########
__FILENAME__ = structured
'''
Created on Aug 4, 2013

@author: nathan
'''

from .segment import DNASegment


def structured_segment(*ordered_types):
    types_table = {cls.__name__: i for i, cls in enumerate(ordered_types)}

    class StructuredSegment(DNASegment):
        def initial_components(self):
            return (Type() for Type in ordered_types)

        def __getattr__(self, name):
            return self.components[types_table[name]]

    return StructuredSegment


def arrayed_segment(length, repeated_type):
    class ArrayedSegment(DNASegment):
        def initial_components(self):
            return (repeated_type() for _ in range(length))

    return ArrayedSegment

# TODO: add binary dna

########NEW FILE########
__FILENAME__ = mutation
import random


def mutation_rate(rate):
    def mutation_mask(length):
        return (True if random.random() < rate else False for _ in range(length))
    return mutation_mask

########NEW FILE########
__FILENAME__ = selectors
import random
import bisect
import itertools


def tournament(tournament_size):
    def tournament_selector(population, num_parents):
        for _ in range(num_parents):
            yield max(random.sample(population, tournament_size))
    return tournament_selector


def _accumulate_scores(population):
    scores = list(itertools.accumulate(member.score for member in population))
    return scores, scores[-1]


def roulette(population, num_parents):
    #Uses code taken from
    #http://stackoverflow.com/questions/3679694/a-weighted-version-of-random-choice

    cumulative_scores, total = _accumulate_scores(population)

    for _ in range(num_parents):
        rand = random.random() * total
        yield population[bisect.bisect(cumulative_scores, rand)]


def stochastic(population, num_parents):
    cumulative_scores, total = _accumulate_scores(population)
    average = total / num_parents

    rand = random.random() * average

    for float_index, in itertools.islice(itertools.count(rand, average), num_parents):
        yield population[bisect.bisect(cumulative_scores, float_index)]

########NEW FILE########
__FILENAME__ = discrete
def pairwise(iterable):
    x = iter(iterable)
    return zip(x, x)


class DiscreteSimulation:
    def __init__(self, population_size, mutation_mask, crossover_mask,
            selection_function, elite_size,
            initial_generator, fitness_function=None):
        self.population_size = population_size
        self.mutation_mask = mutation_mask
        self.crossover_mask = crossover_mask
        self.selection_function = selection_function
        self.elite_size = elite_size
        self.initial_generator = initial_generator
        self.fitness_function = fitness_function

        self.parents_per_selection = population_size - elite_size

    def parents(self, scored_population):
        '''
        Given a scored population, yield pairs of parents
        '''
        selected = self.selection_function(scored_population,
                                           self.parents_per_selection)
        return pairwise(selected)

    def find_scores(self, population):
        if self.fitness_function is not None:
            for member in population:
                member.score = self.fitness_function(member)
        return population

    def initial_population(self):
        '''Create an initial populaton'''
        return list(self.initial_generator() for _ in
                    range(self.population_size))

    def step_generator(self, population):
        '''Run a whole genetic step on a scored population'''
        # Sort population and score if nessesary
        scored_population = sorted(self.find_scores(population), reverse=True)

        # Yield the elite elements
        yield from scored_population[:self.elite_size]
        # Generate parents
        for parent1, parent2 in self.parents(scored_population):
            # crossover parents
            mask = self.crossover_mask(parent1.total_length())
            for child in parent1.combine(parent2, mask):
                # mutate
                yield child.mutate(self.mutation_mask(child.total_length()))

    def step(self, population):
        return list(self.step_generator(population))

########NEW FILE########
__FILENAME__ = test_cross
from genetics import cross
import itertools


def mask_run(mask, b):
    for m in mask:
        if m is (not b):
            break
        assert m is b


def test_one_point_crossover():
    mask = list(cross.one_point_crossover(100))
    assert len(mask) == 100
    mask_iter = iter(mask)

    mask_run(mask_iter, True)

    for m in mask_iter:
        assert m is False


def test_two_point_crossover():
    mask = list(cross.two_point_crossover(100))
    assert len(mask) == 100
    mask_iter = iter(mask)

    mask_run(mask_iter, True)
    mask_run(mask_iter, False)

    for m in mask_iter:
        assert m is True


def test_uniform_point_crossover():
    mask = list(cross.uniform_point_crossover(100))
    assert len(mask) == 100

    values = set()
    for m in mask:
        values.add(m)
    assert True in values and False in values
########NEW FILE########
__FILENAME__ = test_binary
import random
from genetics.dna.binary import DNABinary


def test_basic_init():
    init = (True, False, True, True, False, False, False, True, True, False)
    x = DNABinary(init)

    for component, b in zip(x, init):
        assert component == b


def test_string_init():
    init = '1000101011110101010010100101001010101110101010000000111'
    x = DNABinary(init)

    def convert_ones_zeroes(c):
        if c == '1':
            return True
        elif c == '0':
            return False
        return None

    init_bools = [convert_ones_zeroes(c) for c in init]

    for component, b in zip(x, init_bools):
        assert component == b


def test_length_init():
    x = DNABinary(100)

    assert len(x) == 100

    for component in x:
        assert component is True or component is False


def test_total_length():
    x = DNABinary(100)
    assert x.total_length() == 100


def test_deterministic_combine():
    dna1 = DNABinary(True for _ in range(100))
    dna2 = DNABinary(False for _ in range(100))

    combine_mask = [True if i < 25 else False for i in range(100)]

    dna3, dna4 = dna1.combine(dna2, combine_mask)

    for component1, component2, mask in zip(dna3, dna4, combine_mask):
        if mask:
            assert component1 is True
            assert component2 is False
        else:
            assert component1 is False
            assert component2 is True


def test_random_combine():
    dna1 = DNABinary(100)
    dna2 = DNABinary(100)

    combine_mask = [random.choice((True, False)) for _ in range(100)]

    dna3, dna4 = dna1.combine(dna2, combine_mask)

    for parent1, parent2, child1, child2, mask in zip(dna1, dna2, dna3, dna4, combine_mask):
        if mask:
            assert child1 == parent1
            assert child2 == parent2
        else:
            assert child1 == parent2
            assert child2 == parent1


def test_mutation():
    dna = DNABinary(False for _ in range(100))

    mask = [True if i % 2 == 0 else False for i in range(100)]

    mutated = dna.mutate(mask)

    # Test that the original DNA is untouched
    for b in dna:
        assert b is False

    for b, mask in zip(mutated, mask):
        if not mask:
            assert b is False


def test_element_access():
    x = [True, False, False, True]

    dna = DNABinary(x)

    for i in range(4):
        assert dna[i] == x[i]

########NEW FILE########
__FILENAME__ = test_component
from nose.tools import assert_raises
from genetics.dna.component import DNAComponent

# Classes for test cases
class BasicComponent1(DNAComponent):
    def initial_value(self):
        return 1


class BasicComponent2(DNAComponent):
    def initial_value(self):
        return 2


class ComponentWithIterable(DNAComponent):
    def initial_value(self):
        return (1, 2, 3, 4)


class IncrementingComponent(DNAComponent):
    def initial_value(self):
        return 0

    def mutate_value(self):
        return self.value + 1


class ComponentNoInitial(DNAComponent):
    def mutate_value(self):
        return 1


def test_initial_value():
    x = DNAComponent(5)
    assert x.value == 5


def test_initial_value_from_function():
    x = BasicComponent1()
    assert x.value == 1


def test_initial_value_from_mutation():
    x = ComponentNoInitial()
    assert x.value == 1


def test_initial_value_no_arg_fails():
    with assert_raises(AttributeError):
        DNAComponent()


def test_total_length_basic():
    basic = BasicComponent1()
    assert basic.total_length() == 1


def test_total_length_iterable():
    iterable = ComponentWithIterable()
    assert iterable.total_length() == 1


def test_mutation():
    original_component = IncrementingComponent()
    component = original_component
    assert component.value == 0
    component = component.mutate([1])
    assert component.value == 1
    component = component.mutate([0])
    assert component.value == 1
    component = component.mutate([1, 0])
    assert component.value == 2
    component = component.mutate([0, 1])
    assert component.value == 2
    assert original_component.value == 0


def test_mask_consumption():
    component = IncrementingComponent()

    mask = iter((True, False, True, False))
    assert component.value == 0
    component = component.mutate(mask)
    assert component.value == 1
    assert next(mask) == False


def test_combine():
    def combine_check(mask, did_swap):
        child1, child2 = parent1.combine(parent2, mask)
        if did_swap:
            assert child1.value == parent1.value
            assert child2.value == parent2.value
        else:
            assert child1.value == parent2.value
            assert child2.value == parent1.value

    parent1 = BasicComponent1()
    parent2 = BasicComponent2()

    combine_check([True], True)
    combine_check([False], False)
    combine_check([True, False], True)
    combine_check([False, True], False)

########NEW FILE########
__FILENAME__ = test_segment
from genetics.dna.segment import DNASegment
from genetics.dna.component import DNAComponent


class MutatingComponent(DNAComponent):
    def initial_value(self):
        return 0

    def mutate_value(self):
        return 1


class MutatingSegment(DNASegment):
    def initial_components(self):
        return (MutatingComponent() for _ in range(20))


class NestedMutatingSegment(DNASegment):
    def initial_components(self):
        return (MutatingSegment() for _ in range(5))


def test_total_length():
    x = MutatingSegment()
    assert x.total_length() == 20


def test_nested_total_length():
    x = NestedMutatingSegment()
    assert x.total_length() == 100


def test_length():
    x = MutatingSegment()
    assert len(x) == 20


def test_nested_length():
    x = NestedMutatingSegment()
    assert len(x) == 5


def test_iteration():
    x = MutatingSegment()

    for a, b in zip(x, x.components):
        assert a is b


def test_item_access():
    x = MutatingSegment()

    for i in range(20):
        assert x[i] is x.components[i]

########NEW FILE########
__FILENAME__ = test_mutate
from genetics import mutation
import itertools


def test_no_mutation():
    mask = list(mutation.mutation_rate(0)(100))
    assert len(mask) == 100
    for m in mask:
        assert m is False


def test_all_mutation():
    mask = list(mutation.mutation_rate(1)(100))
    assert len(mask) == 100
    for m in mask:
        assert m is True


def test_some_mutation():
    for rate in (.25, .5, .75):
        mask = list(mutation.mutation_rate(rate)(100))
        assert len(mask) == 100
        values = set()
        for m in mask:
            values.add(m)
        assert True in values and False in values

########NEW FILE########
