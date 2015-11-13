__FILENAME__ = abstract_classes
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from tie_breaker import TieBreaker
from abc import ABCMeta, abstractmethod
from copy import copy, deepcopy
import types

# This class provides methods that most electoral systems make use of.


class VotingSystem(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, ballots, tie_breaker=None):
        self.ballots = ballots
        for ballot in self.ballots:
            if "count" not in ballot:
                ballot["count"] = 1
        self.tie_breaker = tie_breaker
        if isinstance(self.tie_breaker, types.ListType):
            self.tie_breaker = TieBreaker(self.tie_breaker)
        self.calculate_results()

    @abstractmethod
    def as_dict(self):
        data = dict()
        data["candidates"] = self.candidates
        if self.tie_breaker and self.tie_breaker.ties_broken:
            data["tie_breaker"] = self.tie_breaker.as_list()
        return data

    def break_ties(self, tied_objects, reverse_order=False):
        if self.tie_breaker is None:
            self.tie_breaker = TieBreaker(self.candidates)
        return self.tie_breaker.break_ties(tied_objects, reverse_order)

# Given a set of candidates, return a fixed number of winners


class FixedWinnerVotingSystem(VotingSystem):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, ballots, tie_breaker=None):
        super(FixedWinnerVotingSystem, self).__init__(ballots, tie_breaker)

    def as_dict(self):
        data = super(FixedWinnerVotingSystem, self).as_dict()
        if hasattr(self, 'tied_winners'):
            data["tied_winners"] = self.tied_winners
        return data

# Given a set of candidates, return a fixed number of winners


class MultipleWinnerVotingSystem(FixedWinnerVotingSystem):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, ballots, tie_breaker=None, required_winners=1):
        self.required_winners = required_winners
        super(MultipleWinnerVotingSystem, self).__init__(ballots, tie_breaker)

    def calculate_results(self):
        if self.required_winners == len(self.candidates):
            self.winners = self.candidates

    def as_dict(self):
        data = super(MultipleWinnerVotingSystem, self).as_dict()
        data["winners"] = self.winners
        return data

# Given a set of candidates, return a fixed number of winners


class SingleWinnerVotingSystem(FixedWinnerVotingSystem):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, ballots, tie_breaker=None):
        super(SingleWinnerVotingSystem, self).__init__(ballots, tie_breaker)

    def as_dict(self):
        data = super(SingleWinnerVotingSystem, self).as_dict()
        data["winner"] = self.winner
        return data

# Given a set of candidates, return a fixed number of winners


class AbstractSingleWinnerVotingSystem(SingleWinnerVotingSystem):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, ballots, multiple_winner_class, tie_breaker=None):
        self.multiple_winner_class = multiple_winner_class
        super(AbstractSingleWinnerVotingSystem, self).__init__(ballots, tie_breaker=tie_breaker)

    def calculate_results(self):
        self.multiple_winner_instance = self.multiple_winner_class(self.ballots, tie_breaker=self.tie_breaker, required_winners=1)
        self.__dict__.update(self.multiple_winner_instance.__dict__)
        self.winner = list(self.winners)[0]
        del self.winners

    def as_dict(self):
        data = super(AbstractSingleWinnerVotingSystem, self).as_dict()
        data.update(self.multiple_winner_instance.as_dict())
        del data["winners"]
        return data

# Given a set of candidates, return an ordering


class OrderingVotingSystem(VotingSystem):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, ballots, tie_breaker=None, winner_threshold=None):
        self.winner_threshold = winner_threshold
        super(OrderingVotingSystem, self).__init__(ballots, tie_breaker=tie_breaker)

    def as_dict(self):
        data = super(OrderingVotingSystem, self).as_dict()
        data["order"] = self.order
        return data

# Given a single winner system, generate a non-proportional ordering by sequentially removing the winner


class AbstractOrderingVotingSystem(OrderingVotingSystem):
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, ballots, single_winner_class, winner_threshold=None, tie_breaker=None):
        self.single_winner_class = single_winner_class
        super(AbstractOrderingVotingSystem, self).__init__(ballots, winner_threshold=winner_threshold, tie_breaker=tie_breaker)

    def calculate_results(self):
        self.order = []
        self.rounds = []
        remaining_ballots = deepcopy(self.ballots)
        remaining_candidates = True
        while (
            (remaining_candidates is True or len(remaining_candidates) > 1)
            and (self.winner_threshold is None or len(self.order) < self.winner_threshold)
        ):

            # Given the remaining ballots, who should win?
            result = self.single_winner_class(deepcopy(remaining_ballots), tie_breaker=self.tie_breaker)

            # Mark the candidate that won
            r = {'winner': result.winner}
            self.order.append(r['winner'])

            # Mark any ties that might have occurred
            if hasattr(result, 'tie_breaker'):
                self.tie_breaker = result.tie_breaker
                if hasattr(result, 'tied_winners'):
                    r['tied_winners'] = result.tied_winners
            self.rounds.append(r)

            # Remove the candidate from the remaining candidates and ballots
            if remaining_candidates is True:
                self.candidates = result.candidates
                remaining_candidates = copy(self.candidates)
            remaining_candidates.remove(result.winner)
            remaining_ballots = self.ballots_without_candidate(result.ballots, result.winner)

        # Note the last remaining candidate
        if (self.winner_threshold is None or len(self.order) < self.winner_threshold):
            r = {'winner': list(remaining_candidates)[0]}
            self.order.append(r['winner'])
            self.rounds.append(r)

    def as_dict(self):
        data = super(AbstractOrderingVotingSystem, self).as_dict()
        data["rounds"] = self.rounds
        return data

########NEW FILE########
__FILENAME__ = common_functions
def matching_keys(dict, target_value):
    return set([
        key
        for key, value in dict.iteritems()
        if value == target_value
    ])


def unique_permutations(xs):
    if len(xs) < 2:
        yield xs
    else:
        h = []
        for x in xs:
            h.append(x)
            if x in h[:-1]:
                continue
            ts = xs[:]
            ts.remove(x)
            for ps in unique_permutations(ts):
                yield [x] + ps

########NEW FILE########
__FILENAME__ = condorcet
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from abc import ABCMeta, abstractmethod
from abstract_classes import SingleWinnerVotingSystem
from pygraph.classes.digraph import digraph
import itertools


class CondorcetHelper(object):

    def standardize_ballots(self, ballots, ballot_notation):

        self.ballots = ballots
        if ballot_notation == "grouping":
            for ballot in self.ballots:
                ballot["ballot"].reverse()
                new_ballot = {}
                r = 0
                for rank in ballot["ballot"]:
                    r += 1
                    for candidate in rank:
                        new_ballot[candidate] = r
                ballot["ballot"] = new_ballot
        elif ballot_notation == "ranking":
            for ballot in self.ballots:
                for candidate, rating in ballot["ballot"].iteritems():
                    ballot["ballot"][candidate] = -float(rating)
        elif ballot_notation == "rating" or ballot_notation is None:
            for ballot in self.ballots:
                for candidate, rating in ballot["ballot"].iteritems():
                    ballot["ballot"][candidate] = float(rating)
        else:
            print ballot_notation
            raise Exception("Unknown notation specified")

        self.candidates = set()
        for ballot in self.ballots:
            self.candidates |= set(ballot["ballot"].keys())

        for ballot in self.ballots:
            lowest_preference = min(ballot["ballot"].values()) - 1
            for candidate in self.candidates - set(ballot["ballot"].keys()):
                ballot["ballot"][candidate] = lowest_preference

    def graph_winner(self):
        losing_candidates = set([edge[1] for edge in self.graph.edges()])
        winning_candidates = set(self.graph.nodes()) - losing_candidates
        if len(winning_candidates) == 1:
            self.winner = list(winning_candidates)[0]
        elif len(winning_candidates) > 1:
            self.tied_winners = winning_candidates
            self.winner = self.break_ties(winning_candidates)
        else:
            self.condorcet_completion_method()

    @staticmethod
    def ballots_into_graph(candidates, ballots):
        graph = digraph()
        graph.add_nodes(candidates)
        for pair in itertools.permutations(candidates, 2):
            graph.add_edge(pair, sum([
                ballot["count"]
                for ballot in ballots
                if ballot["ballot"][pair[0]] > ballot["ballot"][pair[1]]
            ]))
        return graph

    @staticmethod
    def edge_weights(graph):
        return dict([
            (edge, graph.edge_weight(edge))
            for edge in graph.edges()
        ])

    @staticmethod
    def remove_weak_edges(graph):
        for pair in itertools.combinations(graph.nodes(), 2):
            pairs = (pair, (pair[1], pair[0]))
            weights = (graph.edge_weight(pairs[0]), graph.edge_weight(pairs[1]))
            if weights[0] >= weights[1]:
                graph.del_edge(pairs[1])
            if weights[1] >= weights[0]:
                graph.del_edge(pairs[0])

# This class determines the Condorcet winner if one exists.


class CondorcetSystem(SingleWinnerVotingSystem, CondorcetHelper):

    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, ballots, tie_breaker=None, ballot_notation=None):
        self.standardize_ballots(ballots, ballot_notation)
        super(CondorcetSystem, self).__init__(self.ballots, tie_breaker=tie_breaker)

    def calculate_results(self):
        self.graph = self.ballots_into_graph(self.candidates, self.ballots)
        self.pairs = self.edge_weights(self.graph)
        self.remove_weak_edges(self.graph)
        self.strong_pairs = self.edge_weights(self.graph)
        self.graph_winner()

    def as_dict(self):
        data = super(CondorcetSystem, self).as_dict()
        if hasattr(self, 'pairs'):
            data["pairs"] = self.pairs
        if hasattr(self, 'strong_pairs'):
            data["strong_pairs"] = self.strong_pairs
        if hasattr(self, 'tied_winners'):
            data["tied_winners"] = self.tied_winners
        return data

########NEW FILE########
__FILENAME__ = irv
from abstract_classes import AbstractSingleWinnerVotingSystem
from stv import STV


class IRV(AbstractSingleWinnerVotingSystem):

    def __init__(self, ballots, tie_breaker=None):
        super(IRV, self).__init__(ballots, STV, tie_breaker=tie_breaker)

    def calculate_results(self):
        super(IRV, self).calculate_results()
        IRV.singularize(self.rounds)

    def as_dict(self):
        data = super(IRV, self).as_dict()
        IRV.singularize(data["rounds"])
        return data

    @staticmethod
    def singularize(rounds):
        for r in rounds:
            if "winners" in r:
                r["winner"] = list(r["winners"])[0]
                del r["winners"]

########NEW FILE########
__FILENAME__ = plurality
from abstract_classes import AbstractSingleWinnerVotingSystem
from plurality_at_large import PluralityAtLarge


class Plurality(AbstractSingleWinnerVotingSystem):

    def __init__(self, ballots, tie_breaker=None):
        super(Plurality, self).__init__(ballots, PluralityAtLarge, tie_breaker=tie_breaker)

########NEW FILE########
__FILENAME__ = plurality_at_large
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from abstract_classes import MultipleWinnerVotingSystem
from common_functions import matching_keys
import types
import copy


class PluralityAtLarge(MultipleWinnerVotingSystem):

    def __init__(self, ballots, tie_breaker=None, required_winners=1):
        super(PluralityAtLarge, self).__init__(ballots, tie_breaker=tie_breaker, required_winners=required_winners)

    def calculate_results(self):

        # Standardize the ballot format and extract the candidates
        self.candidates = set()
        for ballot in self.ballots:

            # Convert single candidate ballots into ballot lists
            if not isinstance(ballot["ballot"], types.ListType):
                ballot["ballot"] = [ballot["ballot"]]

            # Ensure no ballot has an excess of votes
            if len(ballot["ballot"]) > self.required_winners:
                raise Exception("A ballot contained too many candidates")

            # Add all candidates on the ballot to the set
            self.candidates.update(set(ballot["ballot"]))

        # Sum up all votes for each candidate
        self.tallies = dict.fromkeys(self.candidates, 0)
        for ballot in self.ballots:
            for candidate in ballot["ballot"]:
                self.tallies[candidate] += ballot["count"]
        tallies = copy.deepcopy(self.tallies)

        # Determine which candidates win
        winning_candidates = set()
        while len(winning_candidates) < self.required_winners:

            # Find the remaining candidates with the most votes
            largest_tally = max(tallies.values())
            top_candidates = matching_keys(tallies, largest_tally)

            # Reduce the found candidates if there are too many
            if len(top_candidates | winning_candidates) > self.required_winners:
                self.tied_winners = top_candidates.copy()
                while len(top_candidates | winning_candidates) > self.required_winners:
                    top_candidates.remove(self.break_ties(top_candidates, True))

            # Move the top candidates into the winning pile
            winning_candidates |= top_candidates
            for candidate in top_candidates:
                del tallies[candidate]

        self.winners = winning_candidates

    def as_dict(self):
        data = super(PluralityAtLarge, self).as_dict()
        data["tallies"] = self.tallies
        return data

########NEW FILE########
__FILENAME__ = ranked_pairs
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from condorcet import CondorcetSystem, CondorcetHelper
from pygraph.classes.digraph import digraph
from pygraph.algorithms.cycles import find_cycle
from common_functions import matching_keys
from copy import deepcopy


# This class implements the Schulze Method (aka the beatpath method)
class RankedPairs(CondorcetSystem, CondorcetHelper):

    def __init__(self, ballots, tie_breaker=None, ballot_notation=None):
        super(RankedPairs, self).__init__(ballots, tie_breaker=tie_breaker, ballot_notation=ballot_notation)

    def condorcet_completion_method(self):

        # Initialize the candidate graph
        self.rounds = []
        graph = digraph()
        graph.add_nodes(self.candidates)

        # Loop until we've considered all possible pairs
        remaining_strong_pairs = deepcopy(self.strong_pairs)
        while len(remaining_strong_pairs) > 0:
            r = {}

            # Find the strongest pair
            largest_strength = max(remaining_strong_pairs.values())
            strongest_pairs = matching_keys(remaining_strong_pairs, largest_strength)
            if len(strongest_pairs) > 1:
                r["tied_pairs"] = strongest_pairs
                strongest_pair = self.break_ties(strongest_pairs)
            else:
                strongest_pair = list(strongest_pairs)[0]
            r["pair"] = strongest_pair

            # If the pair would add a cycle, skip it
            graph.add_edge(strongest_pair)
            if len(find_cycle(graph)) > 0:
                r["action"] = "skipped"
                graph.del_edge(strongest_pair)
            else:
                r["action"] = "added"
            del remaining_strong_pairs[strongest_pair]
            self.rounds.append(r)

        self.old_graph = self.graph
        self.graph = graph
        self.graph_winner()

    def as_dict(self):
        data = super(RankedPairs, self).as_dict()
        if hasattr(self, 'rounds'):
            data["rounds"] = self.rounds
        return data

########NEW FILE########
__FILENAME__ = schulze_by_graph
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from schulze_method import SchulzeMethod
from schulze_helper import SchulzeHelper
from abstract_classes import AbstractOrderingVotingSystem
from pygraph.classes.digraph import digraph


# This class provides Schulze Method results, but bypasses ballots and uses preference tallies instead.
class SchulzeMethodByGraph(SchulzeMethod):

    def __init__(self, edges, tie_breaker=None, ballot_notation=None):
        self.edges = edges
        super(SchulzeMethodByGraph, self).__init__([], tie_breaker=tie_breaker, ballot_notation=ballot_notation)

    def standardize_ballots(self, ballots, ballot_notation):
        self.ballots = []
        self.candidates = set([edge[0] for edge, weight in self.edges.iteritems()]) | set([edge[1] for edge, weight in self.edges.iteritems()])

    def ballots_into_graph(self, candidates, ballots):
        graph = digraph()
        graph.add_nodes(candidates)
        for edge in self.edges.iteritems():
            graph.add_edge(edge[0], edge[1])
        return graph

# This class provides Schulze NPR results, but bypasses ballots and uses preference tallies instead.


class SchulzeNPRByGraph(AbstractOrderingVotingSystem, SchulzeHelper):

    def __init__(self, edges, winner_threshold=None, tie_breaker=None, ballot_notation=None):
        self.edges = edges
        self.candidates = set([edge[0] for edge, weight in edges.iteritems()]) | set([edge[1] for edge, weight in edges.iteritems()])
        super(SchulzeNPRByGraph, self).__init__(
            [],
            single_winner_class=SchulzeMethodByGraph,
            winner_threshold=winner_threshold,
            tie_breaker=tie_breaker,
        )

    def ballots_without_candidate(self, ballots, candidate):
        self.edges = dict([(edge, weight) for edge, weight in self.edges.iteritems() if edge[0] != candidate and edge[1] != candidate])
        return self.edges

    def calculate_results(self):
        self.ballots = self.edges
        super(SchulzeNPRByGraph, self).calculate_results()

########NEW FILE########
__FILENAME__ = schulze_helper
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pygraph.algorithms.accessibility import accessibility, mutual_accessibility
from pygraph.classes.digraph import digraph
from pygraph.algorithms.minmax import maximum_flow
from condorcet import CondorcetHelper
from common_functions import matching_keys, unique_permutations

PREFERRED_LESS = 1
PREFERRED_SAME = 2
PREFERRED_MORE = 3
STRENGTH_TOLERANCE = 0.0000000001
STRENGTH_THRESHOLD = 0.1

# This class implements the Schulze Method (aka the beatpath method)


class SchulzeHelper(CondorcetHelper):

    def condorcet_completion_method(self):
        self.schwartz_set_heuristic()

    def schwartz_set_heuristic(self):

        # Iterate through using the Schwartz set heuristic
        self.actions = []
        while len(self.graph.edges()) > 0:
            access = accessibility(self.graph)
            mutual_access = mutual_accessibility(self.graph)
            candidates_to_remove = set()
            for candidate in self.graph.nodes():
                candidates_to_remove |= (set(access[candidate]) - set(mutual_access[candidate]))

            # Remove nodes at the end of non-cycle paths
            if len(candidates_to_remove) > 0:
                self.actions.append({'nodes': candidates_to_remove})
                for candidate in candidates_to_remove:
                    self.graph.del_node(candidate)

            # If none exist, remove the weakest edges
            else:
                edge_weights = self.edge_weights(self.graph)
                self.actions.append({'edges': matching_keys(edge_weights, min(edge_weights.values()))})
                for edge in self.actions[-1]["edges"]:
                    self.graph.del_edge(edge)

        self.graph_winner()

    def generate_vote_management_graph(self):
        self.vote_management_graph = digraph()
        self.vote_management_graph.add_nodes(self.completed_patterns)
        self.vote_management_graph.del_node(tuple([PREFERRED_MORE] * self.required_winners))
        self.pattern_nodes = self.vote_management_graph.nodes()
        self.vote_management_graph.add_nodes(["source", "sink"])
        for pattern_node in self.pattern_nodes:
            self.vote_management_graph.add_edge(("source", pattern_node))
        for i in range(self.required_winners):
            self.vote_management_graph.add_node(i)
        for pattern_node in self.pattern_nodes:
            for i in range(self.required_winners):
                if pattern_node[i] == 1:
                    self.vote_management_graph.add_edge((pattern_node, i))
        for i in range(self.required_winners):
            self.vote_management_graph.add_edge((i, "sink"))

    # Generates a list of all patterns that do not contain indifference
    def generate_completed_patterns(self):
        self.completed_patterns = []
        for i in range(0, self.required_winners + 1):
            for pattern in unique_permutations(
                    [PREFERRED_LESS] * (self.required_winners - i)
                    + [PREFERRED_MORE] * (i)
            ):
                self.completed_patterns.append(tuple(pattern))

    def proportional_completion(self, candidate, other_candidates):
        profile = dict(zip(self.completed_patterns, [0] * len(self.completed_patterns)))

        # Obtain an initial tally from the ballots
        for ballot in self.ballots:
            pattern = []
            for other_candidate in other_candidates:
                if ballot["ballot"][candidate] < ballot["ballot"][other_candidate]:
                    pattern.append(PREFERRED_LESS)
                elif ballot["ballot"][candidate] == ballot["ballot"][other_candidate]:
                    pattern.append(PREFERRED_SAME)
                else:
                    pattern.append(PREFERRED_MORE)
            pattern = tuple(pattern)
            if pattern not in profile:
                profile[pattern] = 0.0
            profile[pattern] += ballot["count"]
        weight_sum = sum(profile.values())

        # Peel off patterns with indifference (from the most to the least) and apply proportional completion to them
        for pattern in sorted(profile.keys(), key=lambda pattern: pattern.count(PREFERRED_SAME), reverse=True):
            if pattern.count(PREFERRED_SAME) == 0:
                break
            self.proportional_completion_round(pattern, profile)

        try:
            assert round(weight_sum, 5) == round(sum(profile.values()), 5)
        except:
            print "Proportional completion broke (went from %s to %s)" % (weight_sum, sum(profile.values()))

        return profile

    def proportional_completion_round(self, completion_pattern, profile):

        # Remove pattern that contains indifference
        weight_sum = sum(profile.values())
        completion_pattern_weight = profile[completion_pattern]
        del profile[completion_pattern]

        patterns_to_consider = {}
        for pattern in profile.keys():
            append = False
            append_target = []
            for i in range(len(completion_pattern)):
                if completion_pattern[i] == PREFERRED_SAME:
                    append_target.append(pattern[i])
                    if pattern[i] != PREFERRED_SAME:
                        append = True
                else:
                    append_target.append(completion_pattern[i])
            append_target = tuple(append_target)

            if append is True and append_target in profile:
                append_target = tuple(append_target)
                if append_target not in patterns_to_consider:
                    patterns_to_consider[append_target] = set()
                patterns_to_consider[append_target].add(pattern)

        denominator = 0
        for (append_target, patterns) in patterns_to_consider.items():
            for pattern in patterns:
                denominator += profile[pattern]

        # Reweight the remaining items
        for pattern in patterns_to_consider.keys():
            if denominator == 0:
                profile[pattern] += completion_pattern_weight / len(patterns_to_consider)
            else:
                if pattern not in profile:
                    profile[pattern] = 0
                profile[pattern] += sum(profile[considered_pattern] for considered_pattern in patterns_to_consider[pattern]) * completion_pattern_weight / denominator

        try:
            assert round(weight_sum, 5) == round(sum(profile.values()), 5)
        except:
            print "Proportional completion round broke (went from %s to %s)" % (weight_sum, sum(profile.values()))

        return profile

    # This method converts the voter profile into a capacity graph and iterates
    # on the maximum flow using the Edmonds Karp algorithm. The end result is
    # the limit of the strength of the voter management as per Markus Schulze's
    # Calcul02.pdf (draft, 28 March 2008, abstract: "In this paper we illustrate
    # the calculation of the strengths of the vote managements.").
    def strength_of_vote_management(self, voter_profile):

        # Initialize the graph weights
        for pattern in self.pattern_nodes:
            self.vote_management_graph.set_edge_weight(("source", pattern), voter_profile[pattern])
            for i in range(self.required_winners):
                if pattern[i] == 1:
                    self.vote_management_graph.set_edge_weight((pattern, i), voter_profile[pattern])

        # Iterate towards the limit
        r = [(float(sum(voter_profile.values())) - voter_profile[tuple([PREFERRED_MORE] * self.required_winners)]) / self.required_winners]
        while len(r) < 2 or r[-2] - r[-1] > STRENGTH_TOLERANCE:
            for i in range(self.required_winners):
                self.vote_management_graph.set_edge_weight((i, "sink"), r[-1])
            max_flow = maximum_flow(self.vote_management_graph, "source", "sink")
            sink_sum = sum(v for k, v in max_flow[0].iteritems() if k[1] == "sink")
            r.append(sink_sum / self.required_winners)

            # We expect strengths to be above a specified threshold
            if sink_sum < STRENGTH_THRESHOLD:
                return 0

        # Return the final max flow
        return round(r[-1], 9)

########NEW FILE########
__FILENAME__ = schulze_method
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from schulze_helper import SchulzeHelper
from condorcet import CondorcetSystem

# This class implements the Schulze Method (aka the beatpath method)


class SchulzeMethod(CondorcetSystem, SchulzeHelper):

    def __init__(self, ballots, tie_breaker=None, ballot_notation=None):
        super(SchulzeMethod, self).__init__(ballots, tie_breaker=tie_breaker, ballot_notation=ballot_notation)

    def as_dict(self):
        data = super(SchulzeMethod, self).as_dict()
        if hasattr(self, 'actions'):
            data["actions"] = self.actions
        return data

########NEW FILE########
__FILENAME__ = schulze_npr
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from abstract_classes import AbstractOrderingVotingSystem
from schulze_helper import SchulzeHelper
from schulze_method import SchulzeMethod

#


class SchulzeNPR(AbstractOrderingVotingSystem, SchulzeHelper):

    def __init__(self, ballots, winner_threshold=None, tie_breaker=None, ballot_notation=None):
        self.standardize_ballots(ballots, ballot_notation)
        super(SchulzeNPR, self).__init__(
            self.ballots,
            single_winner_class=SchulzeMethod,
            winner_threshold=winner_threshold,
            tie_breaker=tie_breaker,
        )

    @staticmethod
    def ballots_without_candidate(ballots, candidate):
        for ballot in ballots:
            if candidate in ballot['ballot']:
                del ballot['ballot'][candidate]
        return ballots

########NEW FILE########
__FILENAME__ = schulze_pr
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# This class implements the Schulze Proportional Ranking Method as defined
# in schulze2.pdf
from schulze_helper import SchulzeHelper
from abstract_classes import OrderingVotingSystem
from pygraph.classes.digraph import digraph


class SchulzePR(OrderingVotingSystem, SchulzeHelper):

    def __init__(self, ballots, tie_breaker=None, winner_threshold=None, ballot_notation=None):
        self.standardize_ballots(ballots, ballot_notation)
        super(SchulzePR, self).__init__(
            self.ballots,
            tie_breaker=tie_breaker,
            winner_threshold=winner_threshold,
        )

    def calculate_results(self):

        remaining_candidates = self.candidates.copy()
        self.order = []
        self.rounds = []

        if self.winner_threshold is None:
            winner_threshold = len(self.candidates)
        else:
            winner_threshold = min(len(self.candidates), self.winner_threshold + 1)

        for self.required_winners in range(1, winner_threshold):

            # Generate the list of patterns we need to complete
            self.generate_completed_patterns()
            self.generate_vote_management_graph()

            # Generate the edges between nodes
            self.graph = digraph()
            self.graph.add_nodes(remaining_candidates)
            self.winners = set([])
            self.tied_winners = set([])

            # Generate the edges between nodes
            for candidate_from in remaining_candidates:
                other_candidates = sorted(list(remaining_candidates - set([candidate_from])))
                for candidate_to in other_candidates:
                    completed = self.proportional_completion(candidate_from, set([candidate_to]) | set(self.order))
                    weight = self.strength_of_vote_management(completed)
                    if weight > 0:
                        self.graph.add_edge((candidate_to, candidate_from), weight)

            # Determine the round winner through the Schwartz set heuristic
            self.schwartz_set_heuristic()

            # Extract the winner and adjust the remaining candidates list
            self.order.append(self.winner)
            round = {"winner": self.winner}
            if len(self.tied_winners) > 0:
                round["tied_winners"] = self.tied_winners
            self.rounds.append(round)
            remaining_candidates -= set([self.winner])
            del self.winner
            del self.actions
            if hasattr(self, 'tied_winners'):
                del self.tied_winners

        # Attach the last candidate as the sole winner if necessary
        if self.winner_threshold is None or self.winner_threshold == len(self.candidates):
            self.rounds.append({"winner": list(remaining_candidates)[0]})
            self.order.append(list(remaining_candidates)[0])

        del self.winner_threshold

    def as_dict(self):
        data = super(SchulzePR, self).as_dict()
        data["rounds"] = self.rounds
        return data

########NEW FILE########
__FILENAME__ = schulze_stv
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# This class implements Schulze STV, a proportional representation system
from abstract_classes import MultipleWinnerVotingSystem
from schulze_helper import SchulzeHelper
from pygraph.classes.digraph import digraph
import itertools


class SchulzeSTV(MultipleWinnerVotingSystem, SchulzeHelper):

    def __init__(self, ballots, tie_breaker=None, required_winners=1, ballot_notation=None):
        self.standardize_ballots(ballots, ballot_notation)
        super(SchulzeSTV, self).__init__(self.ballots, tie_breaker=tie_breaker, required_winners=required_winners)

    def calculate_results(self):

        # Don't bother if everyone's going to win
        super(SchulzeSTV, self).calculate_results()
        if hasattr(self, 'winners'):
            return

        # Generate the list of patterns we need to complete
        self.generate_completed_patterns()
        self.generate_vote_management_graph()

        # Build the graph of possible winners
        self.graph = digraph()
        for candidate_set in itertools.combinations(self.candidates, self.required_winners):
            self.graph.add_nodes([tuple(sorted(list(candidate_set)))])

        # Generate the edges between nodes
        for candidate_set in itertools.combinations(self.candidates, self.required_winners + 1):
            for candidate in candidate_set:
                other_candidates = sorted(set(candidate_set) - set([candidate]))
                completed = self.proportional_completion(candidate, other_candidates)
                weight = self.strength_of_vote_management(completed)
                if weight > 0:
                    for subset in itertools.combinations(other_candidates, len(other_candidates) - 1):
                        self.graph.add_edge((tuple(other_candidates), tuple(sorted(list(subset) + [candidate]))), weight)

        # Determine the winner through the Schwartz set heuristic
        self.graph_winner()

        # Split the "winner" into its candidate components
        self.winners = set(self.winner)
        del self.winner

    def as_dict(self):
        data = super(SchulzeSTV, self).as_dict()
        if hasattr(self, 'actions'):
            data['actions'] = self.actions
        return data

########NEW FILE########
__FILENAME__ = stv
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from abstract_classes import MultipleWinnerVotingSystem
import math
import copy
from common_functions import matching_keys

# This class implements the Single Transferable vote (aka STV) in its most
# classic form (see http://en.wikipedia.org/wiki/Single_transferable_vote).
# Alternate counting methods such as Meek's and Warren's would be nice, but
# would need to be covered in a separate class.


class STV(MultipleWinnerVotingSystem):

    def __init__(self, ballots, tie_breaker=None, required_winners=1):
        super(STV, self).__init__(ballots, tie_breaker=tie_breaker, required_winners=required_winners)

    def calculate_results(self):

        self.candidates = set()
        for ballot in self.ballots:
            ballot["count"] = float(ballot["count"])
            self.candidates.update(set(ballot['ballot']))

        self.quota = STV.droop_quota(self.ballots, self.required_winners)
        self.rounds = []
        self.winners = set()
        quota = self.quota
        remaining_candidates = copy.deepcopy(self.candidates)
        ballots = copy.deepcopy(self.ballots)

        # Loop until we have enough candidates
        while len(self.winners) < self.required_winners and len(remaining_candidates) + len(self.winners) > self.required_winners:

            # If all the votes have been used up, start from scratch for the remaining candidates
            round = {}
            if len(filter(lambda ballot: ballot["count"] > 0, ballots)) == 0:
                round["note"] = "reset"
                ballots = copy.deepcopy(self.ballots)
                for ballot in ballots:
                    ballot["ballot"] = filter(lambda x: x in remaining_candidates, ballot["ballot"])
                quota = STV.droop_quota(ballots, self.required_winners - len(self.winners))

            # If any candidates meet or exceeds the quota, they're a winner
            round["tallies"] = STV.tallies(ballots)
            if max(round["tallies"].values()) >= quota:

                # Collect candidates as winners
                round["winners"] = set([
                    candidate
                    for candidate, tally in round["tallies"].items()
                    if tally >= self.quota
                ])
                self.winners |= round["winners"]
                remaining_candidates -= round["winners"]

                # Redistribute excess votes
                for ballot in ballots:
                    if ballot["ballot"][0] in round["winners"]:
                        ballot["count"] *= (round["tallies"][ballot["ballot"][0]] - self.quota) / round["tallies"][ballot["ballot"][0]]

                # Remove candidates from remaining ballots
                ballots = self.remove_candidates_from_ballots(round["winners"], ballots)

            # If no candidate exceeds the quota, elimiate the least preferred
            else:
                round.update(self.loser(round["tallies"]))
                remaining_candidates.remove(round["loser"])
                ballots = self.remove_candidates_from_ballots([round["loser"]], ballots)

            # Record this round's actions
            self.rounds.append(round)

        # Append the final winner and return
        if len(self.winners) < self.required_winners:
            self.remaining_candidates = remaining_candidates
            self.winners |= self.remaining_candidates

    def as_dict(self):
        data = super(STV, self).as_dict()
        data["quota"] = self.quota
        data["rounds"] = self.rounds
        if hasattr(self, 'remaining_candidates'):
            data["remaining_candidates"] = self.remaining_candidates
        return data

    def loser(self, tallies):
        losers = matching_keys(tallies, min(tallies.values()))
        if len(losers) == 1:
            return {"loser": list(losers)[0]}
        else:
            return {
                "tied_losers": losers,
                "loser": self.break_ties(losers, True)
            }

    @staticmethod
    def remove_candidates_from_ballots(candidates, ballots):
        for ballot in ballots:
            for candidate in candidates:
                if candidate in ballot["ballot"]:
                    ballot["ballot"].remove(candidate)
        return ballots

    @staticmethod
    def tallies(ballots):
        tallies = dict.fromkeys(STV.viable_candidates(ballots), 0)
        for ballot in ballots:
            if len(ballot["ballot"]) > 0:
                tallies[ballot["ballot"][0]] += ballot["count"]
        return dict((candidate, votes) for (candidate, votes) in tallies.iteritems() if votes > 0)

    @staticmethod
    def viable_candidates(ballots):
        candidates = set([])
        for ballot in ballots:
            candidates |= set(ballot["ballot"])
        return candidates

    @staticmethod
    def droop_quota(ballots, seats=1):
        voters = 0
        for ballot in ballots:
            voters += ballot["count"]
        return int(math.floor(voters / (seats + 1)) + 1)

########NEW FILE########
__FILENAME__ = tie_breaker
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import random
import types
from copy import copy

# This class provides tie breaking methods


class TieBreaker(object):

    #
    def __init__(self, candidate_range):
        self.ties_broken = False
        self.random_ordering = list(candidate_range)
        if not isinstance(candidate_range, types.ListType):
            random.shuffle(self.random_ordering)

    #
    def break_ties(self, tied_candidates, reverse=False):
        self.ties_broken = True
        random_ordering = copy(self.random_ordering)
        if reverse:
            random_ordering.reverse()
        if getattr(list(tied_candidates)[0], '__iter__', False):
            result = self.break_complex_ties(tied_candidates, random_ordering)
        else:
            result = self.break_simple_ties(tied_candidates, random_ordering)
        return result

    #
    @staticmethod
    def break_simple_ties(tied_candidates, random_ordering):
        for candidate in random_ordering:
            if candidate in tied_candidates:
                return candidate

    #
    @staticmethod
    def break_complex_ties(tied_candidates, random_ordering):
        max_columns = len(list(tied_candidates)[0])
        column = 0
        while len(tied_candidates) > 1 and column < max_columns:
            min_index = min(random_ordering.index(list(candidate)[column]) for candidate in tied_candidates)
            tied_candidates = set([candidate for candidate in tied_candidates if candidate[column] == random_ordering[min_index]])
            column += 1
        return list(tied_candidates)[0]

    #
    def as_list(self):
        return self.random_ordering

    #
    def __str__(self):
        return "[%s]" % ">".join(self.random_ordering)

########NEW FILE########
__FILENAME__ = test_condorcet
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.schulze_method import SchulzeMethod
import unittest


class TestCondorcet(unittest.TestCase):

    def test_grouping_format(self):

        # Generate data
        input = [
            {"count": 12, "ballot": [["Andrea"], ["Brad"], ["Carter"]]},
            {"count": 26, "ballot": [["Andrea"], ["Carter"], ["Brad"]]},
            {"count": 12, "ballot": [["Andrea"], ["Carter"], ["Brad"]]},
            {"count": 13, "ballot": [["Carter"], ["Andrea"], ["Brad"]]},
            {"count": 27, "ballot": [["Brad"]]},
        ]
        output = SchulzeMethod(input, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output, {
            "candidates": set(['Carter', 'Brad', 'Andrea']),
            "pairs": {
                ('Andrea', 'Brad'): 63,
                ('Brad', 'Carter'): 39,
                ('Carter', 'Andrea'): 13,
                ('Andrea', 'Carter'): 50,
                ('Brad', 'Andrea'): 27,
                ('Carter', 'Brad'): 51
            },
            "strong_pairs": {
                ('Andrea', 'Brad'): 63,
                ('Carter', 'Brad'): 51,
                ('Andrea', 'Carter'): 50
            },
            "winner": 'Andrea'
        })

    def test_ranking_format(self):

        # Generate data
        input = [
            {"count": 12, "ballot": {"Andrea": 1, "Brad": 2, "Carter": 3}},
            {"count": 26, "ballot": {"Andrea": 1, "Carter": 2, "Brad": 3}},
            {"count": 12, "ballot": {"Andrea": 1, "Carter": 2, "Brad": 3}},
            {"count": 13, "ballot": {"Carter": 1, "Andrea": 2, "Brad": 3}},
            {"count": 27, "ballot": {"Brad": 1}}
        ]
        output = SchulzeMethod(input, ballot_notation="ranking").as_dict()

        # Run tests
        self.assertEqual(output, {
            "candidates": set(['Carter', 'Brad', 'Andrea']),
            "pairs": {
                ('Andrea', 'Brad'): 63,
                ('Brad', 'Carter'): 39,
                ('Carter', 'Andrea'): 13,
                ('Andrea', 'Carter'): 50,
                ('Brad', 'Andrea'): 27,
                ('Carter', 'Brad'): 51
            },
            "strong_pairs": {
                ('Andrea', 'Brad'): 63,
                ('Carter', 'Brad'): 51,
                ('Andrea', 'Carter'): 50
            },
            "winner": 'Andrea'
        })

    def test_rating_format(self):

        # Generate data
        input = [
            {"count": 12, "ballot": {"Andrea": 10, "Brad": 5, "Carter": 3}},
            {"count": 26, "ballot": {"Andrea": 10, "Carter": 5, "Brad": 3}},
            {"count": 12, "ballot": {"Andrea": 10, "Carter": 5, "Brad": 3}},
            {"count": 13, "ballot": {"Carter": 10, "Andrea": 5, "Brad": 3}},
            {"count": 27, "ballot": {"Brad": 10}}
        ]
        output = SchulzeMethod(input, ballot_notation="rating").as_dict()

        # Run tests
        self.assertEqual(output, {
            "candidates": set(['Carter', 'Brad', 'Andrea']),
            "pairs": {
                ('Andrea', 'Brad'): 63,
                ('Brad', 'Carter'): 39,
                ('Carter', 'Andrea'): 13,
                ('Andrea', 'Carter'): 50,
                ('Brad', 'Andrea'): 27,
                ('Carter', 'Brad'): 51
            },
            "strong_pairs": {
                ('Andrea', 'Brad'): 63,
                ('Carter', 'Brad'): 51,
                ('Andrea', 'Carter'): 50
            },
            "winner": 'Andrea'
        })

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_irv
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.irv import IRV
import unittest


class TestInstantRunoff(unittest.TestCase):

    # IRV, no ties
    def test_irv_no_ties(self):

        # Generate data
        input = [
            {"count": 26, "ballot": ["c1", "c2", "c3"]},
            {"count": 20, "ballot": ["c2", "c3", "c1"]},
            {"count": 23, "ballot": ["c3", "c1", "c2"]}
        ]
        output = IRV(input).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3']),
            'quota': 35,
            'winner': 'c3',
            'rounds': [
                {'tallies': {'c3': 23.0, 'c2': 20.0, 'c1': 26.0}, 'loser': 'c2'},
                {'tallies': {'c3': 43.0, 'c1': 26.0}, 'winner': 'c3'}
            ]
        })

    # IRV, ties
    def test_irv_ties(self):

        # Generate data
        input = [
            {"count": 26, "ballot": ["c1", "c2", "c3"]},
            {"count": 20, "ballot": ["c2", "c3", "c1"]},
            {"count": 20, "ballot": ["c3", "c1", "c2"]}
        ]
        output = IRV(input).as_dict()

        # Run tests
        self.assertEqual(output["quota"], 34)
        self.assertEqual(len(output["rounds"]), 2)
        self.assertEqual(len(output["rounds"][0]), 3)
        self.assertEqual(output["rounds"][0]["tallies"], {'c1': 26, 'c2': 20, 'c3': 20})
        self.assertEqual(output["rounds"][0]["tied_losers"], set(['c2', 'c3']))
        self.assert_(output["rounds"][0]["loser"] in output["rounds"][0]["tied_losers"])
        self.assertEqual(len(output["rounds"][1]["tallies"]), 2)
        self.assert_("winner" in output["rounds"][1])
        self.assertEqual(len(output["tie_breaker"]), 3)

    # IRV, no rounds
    def test_irv_landslide(self):

        # Generate data
        input = [
            {"count": 56, "ballot": ["c1", "c2", "c3"]},
            {"count": 20, "ballot": ["c2", "c3", "c1"]},
            {"count": 20, "ballot": ["c3", "c1", "c2"]}
        ]
        output = IRV(input).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3']),
            'quota': 49,
            'winner': 'c1',
            'rounds': [
                {'tallies': {'c3': 20.0, 'c2': 20.0, 'c1': 56.0}, 'winner': 'c1'}
            ]
        })

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_plurality
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.plurality import Plurality
import unittest


class TestPlurality(unittest.TestCase):

    # Plurality, no ties
    def test_no_ties(self):

        # Generate data
        input = [
            {"count": 26, "ballot": "c1"},
            {"count": 22, "ballot": "c2"},
            {"count": 23, "ballot": "c3"}
        ]
        output = Plurality(input).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3']),
            'tallies': {'c3': 23, 'c2': 22, 'c1': 26},
            'winner': 'c1'
        })

    # Plurality, alternate ballot format
    def test_plurality_alternate_ballot_format(self):

        # Generate data
        input = [
            {"count": 26, "ballot": ["c1"]},
            {"count": 22, "ballot": ["c2"]},
            {"count": 23, "ballot": ["c3"]}
        ]
        output = Plurality(input).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3']),
            'tallies': {'c3': 23, 'c2': 22, 'c1': 26},
            'winner': 'c1'
        })

    # Plurality, irrelevant ties
    def test_irrelevant_ties(self):

        # Generate data
        input = [
            {"count": 26, "ballot": "c1"},
            {"count": 23, "ballot": "c2"},
            {"count": 23, "ballot": "c3"}
        ]
        output = Plurality(input).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3']),
            'tallies': {'c3': 23, 'c2': 23, 'c1': 26},
            'winner': 'c1'
        })

    # Plurality, relevant ties
    def test_relevant_ties(self):

        # Generate data
        input = [
            {"count": 26, "ballot": "c1"},
            {"count": 26, "ballot": "c2"},
            {"count": 23, "ballot": "c3"}
        ]
        output = Plurality(input).as_dict()

        # Run tests
        self.assertEqual(output["tallies"], {'c1': 26, 'c2': 26, 'c3': 23})
        self.assertEqual(output["tied_winners"], set(['c1', 'c2']))
        self.assert_(output["winner"] in output["tied_winners"])
        self.assertEqual(len(output["tie_breaker"]), 3)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_plurality_at_large
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.plurality_at_large import PluralityAtLarge
import unittest


class TestPluralityAtLarge(unittest.TestCase):

    # Plurality at Large, no ties
    def test_plurality_at_large_no_ties(self):

        # Generate data
        output = PluralityAtLarge([
            {"count": 26, "ballot": ["c1", "c2"]},
            {"count": 22, "ballot": ["c1", "c3"]},
            {"count": 23, "ballot": ["c2", "c3"]}
        ], required_winners=2).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3']),
            'tallies': {'c3': 45, 'c2': 49, 'c1': 48},
            'winners': set(['c2', 'c1'])
        })

    # Plurality at Large, irrelevant ties
    def test_plurality_at_large_irrelevant_ties(self):

        # Generate data
        output = PluralityAtLarge([
            {"count": 26, "ballot": ["c1", "c2"]},
            {"count": 22, "ballot": ["c1", "c3"]},
            {"count": 22, "ballot": ["c2", "c3"]},
            {"count": 11, "ballot": ["c4", "c5"]}
        ], required_winners=2).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3', 'c4', 'c5']),
            'tallies': {'c3': 44, 'c2': 48, 'c1': 48, 'c5': 11, 'c4': 11},
            'winners': set(['c2', 'c1'])
        })

    # Plurality at Large, irrelevant ties
    def test_plurality_at_large_relevant_ties(self):

        # Generate data
        output = PluralityAtLarge([
            {"count": 30, "ballot": ["c1", "c2"]},
            {"count": 22, "ballot": ["c3", "c1"]},
            {"count": 22, "ballot": ["c2", "c3"]},
            {"count": 4, "ballot": ["c4", "c1"]},
            {"count": 8, "ballot": ["c3", "c4"]},
        ], required_winners=2).as_dict()

        # Run tests
        self.assertEqual(output["tallies"], {'c3': 52, 'c2': 52, 'c1': 56, 'c4': 12})
        self.assertEqual(len(output["tie_breaker"]), 4)
        self.assertEqual(output["tied_winners"], set(['c2', 'c3']))
        self.assert_("c1" in output["winners"] and ("c2" in output["winners"] or "c3" in output["winners"]))
        self.assertEqual(len(output), 5)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_ranked_pairs
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.ranked_pairs import RankedPairs
import unittest


class TestRankedPairs(unittest.TestCase):

    # Ranked Pairs, cycle
    def test_no_cycle(self):

        # Generate data
        input = [
            {"count": 80, "ballot": [["c1", "c2"], ["c3"]]},
            {"count": 50, "ballot": [["c2"], ["c3", "c1"]]},
            {"count": 40, "ballot": [["c3"], ["c1"], ["c2"]]}
        ]
        output = RankedPairs(input, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c3', 'c2', 'c1']),
            'pairs': {
                ('c1', 'c2'): 40,
                ('c1', 'c3'): 80,
                ('c2', 'c1'): 50,
                ('c2', 'c3'): 130,
                ('c3', 'c1'): 40,
                ('c3', 'c2'): 40
            },
            'strong_pairs': {
                ('c2', 'c3'): 130,
                ('c1', 'c3'): 80,
                ('c2', 'c1'): 50
            },
            'winner': 'c2'
        })

    # Ranked Pairs, cycle
    def test_cycle(self):

        # Generate data
        input = [
            {"count": 80, "ballot": [["c1"], ["c2"], ["c3"]]},
            {"count": 50, "ballot": [["c2"], ["c3"], ["c1"]]},
            {"count": 40, "ballot": [["c3"], ["c1"], ["c2"]]}
        ]
        output = RankedPairs(input, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c3', 'c2', 'c1']),
            'pairs': {
                ('c1', 'c3'): 80,
                ('c1', 'c2'): 120,
                ('c2', 'c1'): 50,
                ('c2', 'c3'): 130,
                ('c3', 'c1'): 90,
                ('c3', 'c2'): 40
            },
            'strong_pairs': {
                ('c2', 'c3'): 130,
                ('c1', 'c2'): 120,
                ('c3', 'c1'): 90
            },
            'rounds': [
                {'pair': ('c2', 'c3'), 'action': 'added'},
                {'pair': ('c1', 'c2'), 'action': 'added'},
                {'pair': ('c3', 'c1'), 'action': 'skipped'}
            ],
            'winner': 'c1'
        })

    # Strongest pairs tie
    def test_tied_pairs(self):

        # Generate data
        input = [
            {"count": 100, "ballot": [["chocolate"], ["vanilla"]]},
            {"count": 100, "ballot": [["vanilla"], ["strawberry"]]},
            {"count": 1, "ballot": [["strawberry"], ["chocolate"]]}
        ]
        output = RankedPairs(input, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output["pairs"], {
            ('vanilla', 'strawberry'): 200,
            ('strawberry', 'vanilla'): 1,
            ('chocolate', 'vanilla'): 101,
            ('vanilla', 'chocolate'): 100,
            ('strawberry', 'chocolate'): 101,
            ('chocolate', 'strawberry'): 100
        })

        self.assertEqual(output["strong_pairs"], {
            ('chocolate', 'vanilla'): 101,
            ('vanilla', 'strawberry'): 200,
            ('strawberry', 'chocolate'): 101
        })

        self.assertEqual(
            output["rounds"][1]["tied_pairs"],
            set([('chocolate', 'vanilla'), ('strawberry', 'chocolate')])
        )

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_schulze_by_graph
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.schulze_by_graph import SchulzeMethodByGraph, SchulzeNPRByGraph
import unittest


class TestSchulzeMethodByGraph(unittest.TestCase):

    def test_simple_example(self):

        # Generate data
        input = {
            ('a', 'b'): 4,
            ('b', 'a'): 3,
            ('a', 'c'): 4,
            ('c', 'a'): 3,
            ('b', 'c'): 4,
            ('c', 'b'): 3,
        }
        output = SchulzeMethodByGraph(input).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['a', 'b', 'c']),
            'pairs': input,
            'strong_pairs': {
                ('a', 'b'): 4,
                ('a', 'c'): 4,
                ('b', 'c'): 4,
            },
            'winner': 'a',
        })


class TestSchulzeNPRByGraph(unittest.TestCase):

    def test_simple_example(self):

        # Generate data
        input = {
            ('a', 'b'): 8,
            ('b', 'a'): 3,
            ('a', 'c'): 3,
            ('c', 'a'): 4,
            ('b', 'c'): 6,
            ('c', 'b'): 3,
        }
        output = SchulzeNPRByGraph(input, winner_threshold=3).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['a', 'b', 'c']),
            'rounds': [{'winner': 'a'}, {'winner': 'b'}, {'winner': 'c'}],
            'order': ['a', 'b', 'c']
        })

    def test_complex_example(self):

        # Generate data
        input = {
            ('a', 'b'): 4,
            ('b', 'a'): 3,
            ('a', 'c'): 4,
            ('c', 'a'): 3,
            ('b', 'c'): 4,
            ('c', 'b'): 3,
            ('a', 'd'): 4,
            ('d', 'a'): 4,
            ('b', 'd'): 4,
            ('d', 'b'): 4,
            ('c', 'd'): 4,
            ('d', 'c'): 4

        }
        output = SchulzeNPRByGraph(input, winner_threshold=3, tie_breaker=['a', 'd', 'c', 'b']).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['a', 'b', 'c', 'd']),
            'tie_breaker': ['a', 'd', 'c', 'b'],
            'rounds': [
                {'winner': 'a', 'tied_winners': set(['a', 'd'])},
                {'winner': 'd', 'tied_winners': set(['b', 'd'])},
                {'winner': 'b'},
            ],
            'order': ['a', 'd', 'b'],
        })

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_schulze_method
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.schulze_method import SchulzeMethod
import unittest


class TestSchulzeMethod(unittest.TestCase):

    # Schulze Method, example from Wikipedia
    # http://en.wikipedia.org/wiki/Schulze_method#The_Schwartz_set_heuristic
    def test_wiki_example(self):

        # Generate data
        input = [
            {"count": 3, "ballot": [["A"], ["C"], ["D"], ["B"]]},
            {"count": 9, "ballot": [["B"], ["A"], ["C"], ["D"]]},
            {"count": 8, "ballot": [["C"], ["D"], ["A"], ["B"]]},
            {"count": 5, "ballot": [["D"], ["A"], ["B"], ["C"]]},
            {"count": 5, "ballot": [["D"], ["B"], ["C"], ["A"]]}
        ]
        output = SchulzeMethod(input, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['A', 'C', 'B', 'D']),
            'pairs': {
                ('A', 'B'): 16,
                ('A', 'C'): 17,
                ('A', 'D'): 12,
                ('B', 'A'): 14,
                ('B', 'C'): 19,
                ('B', 'D'): 9,
                ('C', 'A'): 13,
                ('C', 'B'): 11,
                ('C', 'D'): 20,
                ('D', 'A'): 18,
                ('D', 'B'): 21,
                ('D', 'C'): 10
            },
            'strong_pairs': {
                ('D', 'B'): 21,
                ('C', 'D'): 20,
                ('B', 'C'): 19,
                ('D', 'A'): 18,
                ('A', 'C'): 17,
                ('A', 'B'): 16,
            },
            'actions': [
                {'edges': set([('A', 'B')])},
                {'edges': set([('A', 'C')])},
                {'nodes': set(['A'])},
                {'edges': set([('B', 'C')])},
                {'nodes': set(['B', 'D'])}
            ],
            'winner': 'C'
        })

    # http://en.wikipedia.org/wiki/Schulze_method#Example
    def test_wiki_example2(self):

        # Generate data
        input = [
            {"count": 5, "ballot": [["A"], ["C"], ["B"], ["E"], ["D"]]},
            {"count": 5, "ballot": [["A"], ["D"], ["E"], ["C"], ["B"]]},
            {"count": 8, "ballot": [["B"], ["E"], ["D"], ["A"], ["C"]]},
            {"count": 3, "ballot": [["C"], ["A"], ["B"], ["E"], ["D"]]},
            {"count": 7, "ballot": [["C"], ["A"], ["E"], ["B"], ["D"]]},
            {"count": 2, "ballot": [["C"], ["B"], ["A"], ["D"], ["E"]]},
            {"count": 7, "ballot": [["D"], ["C"], ["E"], ["B"], ["A"]]},
            {"count": 8, "ballot": [["E"], ["B"], ["A"], ["D"], ["C"]]}
        ]
        output = SchulzeMethod(input, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['A', 'C', 'B', 'E', 'D']),
            'pairs': {
                ('A', 'B'): 20,
                ('A', 'C'): 26,
                ('A', 'D'): 30,
                ('A', 'E'): 22,
                ('B', 'A'): 25,
                ('B', 'C'): 16,
                ('B', 'D'): 33,
                ('B', 'E'): 18,
                ('C', 'A'): 19,
                ('C', 'B'): 29,
                ('C', 'D'): 17,
                ('C', 'E'): 24,
                ('D', 'A'): 15,
                ('D', 'B'): 12,
                ('D', 'C'): 28,
                ('D', 'E'): 14,
                ('E', 'A'): 23,
                ('E', 'B'): 27,
                ('E', 'C'): 21,
                ('E', 'D'): 31
            },
            'strong_pairs': {
                ('B', 'D'): 33,
                ('E', 'D'): 31,
                ('A', 'D'): 30,
                ('C', 'B'): 29,
                ('D', 'C'): 28,
                ('E', 'B'): 27,
                ('A', 'C'): 26,
                ('B', 'A'): 25,
                ('C', 'E'): 24,
                ('E', 'A'): 23
            },
            'actions': [
                {'edges': set([('E', 'A')])},
                {'edges': set([('C', 'E')])},
                {'nodes': set(['A', 'C', 'B', 'D'])}
            ],
            'winner': 'E'
        })

    def test_tiebreaker_bug(self):

        # Generate data
        input = [
            {"count": 1, "ballot": [["A"], ["B", "C"]]},
            {"count": 1, "ballot": [["B"], ["A"], ["C"]]},
        ]
        output = SchulzeMethod(input, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output['candidates'], set(['A', 'B', 'C']))
        self.assertEqual(output['pairs'], {
            ('A', 'B'): 1,
            ('A', 'C'): 2,
            ('B', 'A'): 1,
            ('B', 'C'): 1,
            ('C', 'A'): 0,
            ('C', 'B'): 0,
        })
        self.assertEqual(output['strong_pairs'], {
            ('A', 'C'): 2,
            ('B', 'C'): 1,
        })
        self.assertEqual(output['tied_winners'], set(['A', 'B']))

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_schulze_npr
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.schulze_npr import SchulzeNPR
import unittest


class TestSchulzeNPR(unittest.TestCase):

    def test_single_voter(self):

        # Generate data
        input = [
            {"count": 1, "ballot": {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}},
        ]
        output = SchulzeNPR(input, winner_threshold=5, ballot_notation="ranking").as_dict()

        # Run tests
        self.assertEqual(output, {
            'order': ['A', 'B', 'C', 'D', 'E'],
            'candidates': set(['A', 'B', 'C', 'D', 'E']),
            'rounds': [
                {'winner': 'A'},
                {'winner': 'B'},
                {'winner': 'C'},
                {'winner': 'D'},
                {'winner': 'E'}
            ]
        })

    def test_nonproportionality(self):

        # Generate data
        input = [
            {"count": 2, "ballot": {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}},
            {"count": 1, "ballot": {"A": 5, "B": 4, "C": 3, "D": 2, "E": 1}},
        ]
        output = SchulzeNPR(input, winner_threshold=5, ballot_notation="ranking").as_dict()

        # Run tests
        self.assertEqual(output, {
            'order': ['A', 'B', 'C', 'D', 'E'],
            'candidates': set(['A', 'B', 'C', 'D', 'E']),
            'rounds': [
                {'winner': 'A'},
                {'winner': 'B'},
                {'winner': 'C'},
                {'winner': 'D'},
                {'winner': 'E'}
            ]
        })


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_schulze_pr
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.schulze_pr import SchulzePR
import unittest


class TestSchulzePR(unittest.TestCase):

    # This example was detailed in Markus Schulze's schulze2.pdf (Free Riding
    # and Vote Management under Proportional Representation by the Single
    # Transferable Vote, section 6.2).
    def test_part_2_of_5_example(self):

        # Generate data
        input = [
            {"count": 6, "ballot": [["a"], ["d"], ["b"], ["c"], ["e"]]},
            {"count": 12, "ballot": [["a"], ["d"], ["e"], ["c"], ["b"]]},
            {"count": 72, "ballot": [["a"], ["d"], ["e"], ["b"], ["c"]]},
            {"count": 6, "ballot": [["a"], ["e"], ["b"], ["d"], ["c"]]},
            {"count": 30, "ballot": [["b"], ["d"], ["c"], ["e"], ["a"]]},
            {"count": 48, "ballot": [["b"], ["e"], ["a"], ["d"], ["c"]]},
            {"count": 24, "ballot": [["b"], ["e"], ["d"], ["c"], ["a"]]},
            {"count": 168, "ballot": [["c"], ["a"], ["e"], ["b"], ["d"]]},
            {"count": 108, "ballot": [["d"], ["b"], ["e"], ["c"], ["a"]]},
            {"count": 30, "ballot": [["e"], ["a"], ["b"], ["d"], ["c"]]},
        ]
        output = SchulzePR(input, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output, {
            "candidates": set(["a", "b", "c", "d", "e"]),
            "order": ["e", "c", "a", "b", "d"],
            'rounds': [
                {'winner': 'e'},
                {'winner': 'c'},
                {'winner': 'a'},
                {'winner': 'b'},
                {'winner': 'd'}
            ],
        })

    def test_ties(self):

        # Generate data
        input = [
            {"count": 1, "ballot": [["a"], ["d"], ["b"], ["c"], ["e"]]},
            {"count": 1, "ballot": [["d"], ["a"], ["e"], ["c"], ["b"]]},
        ]
        output = SchulzePR(input, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output["candidates"], set(["a", "b", "c", "d", "e"]))
        self.assertEqual(len(output["tie_breaker"]), 5)
        self.assertEqual(output["rounds"][0]["tied_winners"], set(['a', 'd']))
        self.assertEqual(output["rounds"][2]["tied_winners"], set(['c', 'b', 'e']))
        self.assertEqual(len(output["rounds"][3]["tied_winners"]), 2)

    def test_happenstance_example(self):

        # Generate data
        input = [
            {"count": 23, "ballot": {"A": 9, "B": 1, "C": 1, "D": 9, "E": 9, "F": 2}},
            {"count": 7, "ballot": {"A": 3, "B": 2, "C": 3, "D": 1, "E": 9, "F": 9}},
            {"count": 2, "ballot": {"A": 9, "B": 9, "C": 9, "D": 9, "E": 1, "F": 9}}
        ]
        output = SchulzePR(input, winner_threshold=2, ballot_notation="ranking").as_dict()

        # Run tests
        self.assertEqual(output, {
            "candidates": set(["A", "B", "C", "D", "E", "F"]),
            "order": ["B", "C"],
            "rounds": [
                {'winner': 'B'},
                {'winner': 'C'}
            ],
        })

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_schulze_stv
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.schulze_stv import SchulzeSTV
import unittest


class TestSchulzeSTV(unittest.TestCase):

    # This example was detailed in Markus Schulze's schulze2.pdf (Free Riding
    # and Vote Management under Proportional Representation by the Single
    # Transferable Vote, section 5.5).
    def test_part_2_of_5_example(self):

        # Generate data
        input = [
            {"count": 60, "ballot": [["a"], ["b"], ["c"], ["d"], ["e"]]},
            {"count": 45, "ballot": [["a"], ["c"], ["e"], ["b"], ["d"]]},
            {"count": 30, "ballot": [["a"], ["d"], ["b"], ["e"], ["c"]]},
            {"count": 15, "ballot": [["a"], ["e"], ["d"], ["c"], ["b"]]},
            {"count": 12, "ballot": [["b"], ["a"], ["e"], ["d"], ["c"]]},
            {"count": 48, "ballot": [["b"], ["c"], ["d"], ["e"], ["a"]]},
            {"count": 39, "ballot": [["b"], ["d"], ["a"], ["c"], ["e"]]},
            {"count": 21, "ballot": [["b"], ["e"], ["c"], ["a"], ["d"]]},
            {"count": 27, "ballot": [["c"], ["a"], ["d"], ["b"], ["e"]]},
            {"count": 9, "ballot": [["c"], ["b"], ["a"], ["e"], ["d"]]},
            {"count": 51, "ballot": [["c"], ["d"], ["e"], ["a"], ["b"]]},
            {"count": 33, "ballot": [["c"], ["e"], ["b"], ["d"], ["a"]]},
            {"count": 42, "ballot": [["d"], ["a"], ["c"], ["e"], ["b"]]},
            {"count": 18, "ballot": [["d"], ["b"], ["e"], ["c"], ["a"]]},
            {"count": 6, "ballot": [["d"], ["c"], ["b"], ["a"], ["e"]]},
            {"count": 54, "ballot": [["d"], ["e"], ["a"], ["b"], ["c"]]},
            {"count": 57, "ballot": [["e"], ["a"], ["b"], ["c"], ["d"]]},
            {"count": 36, "ballot": [["e"], ["b"], ["d"], ["a"], ["c"]]},
            {"count": 24, "ballot": [["e"], ["c"], ["a"], ["d"], ["b"]]},
            {"count": 3, "ballot": [["e"], ["d"], ["c"], ["b"], ["a"]]},
        ]
        output = SchulzeSTV(input, required_winners=3, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output['winners'], set(['a', 'd', 'e']))

    # http://en.wikipedia.org/wiki/Schulze_STV#Count_under_Schulze_STV
    def test_wiki_example_1(self):

        # Generate data
        input = [
            {"count": 12, "ballot": [["Andrea"], ["Brad"], ["Carter"]]},
            {"count": 26, "ballot": [["Andrea"], ["Carter"], ["Brad"]]},
            {"count": 12, "ballot": [["Andrea"], ["Carter"], ["Brad"]]},
            {"count": 13, "ballot": [["Carter"], ["Andrea"], ["Brad"]]},
            {"count": 27, "ballot": [["Brad"]]},
        ]
        output = SchulzeSTV(input, required_winners=2, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['Carter', 'Brad', 'Andrea']),
            'actions': [
                {'edges': set([(('Brad', 'Carter'), ('Andrea', 'Carter')), (('Brad', 'Carter'), ('Andrea', 'Brad'))])},
                {'nodes': set([('Brad', 'Carter')])},
                {'edges': set([(('Andrea', 'Carter'), ('Andrea', 'Brad'))])},
                {'nodes': set([('Andrea', 'Carter')])}
            ],
            'winners': set(['Andrea', 'Brad'])
        })

    # http://en.wikipedia.org/wiki/Schulze_STV#Count_under_Schulze_STV_2
    def test_wiki_example_2(self):

        # Generate data
        input = [
            {"count": 12, "ballot": [["Andrea"], ["Brad"], ["Carter"]]},
            {"count": 26, "ballot": [["Andrea"], ["Carter"], ["Brad"]]},
            {"count": 12, "ballot": [["Carter"], ["Andrea"], ["Brad"]]},
            {"count": 13, "ballot": [["Carter"], ["Andrea"], ["Brad"]]},
            {"count": 27, "ballot": [["Brad"]]},
        ]
        output = SchulzeSTV(input, required_winners=2, ballot_notation="grouping").as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['Carter', 'Brad', 'Andrea']),
            'actions': [
                {'edges': set([(('Brad', 'Carter'), ('Andrea', 'Carter')), (('Brad', 'Carter'), ('Andrea', 'Brad'))])},
                {'nodes': set([('Brad', 'Carter')])},
                {'edges': set([(('Andrea', 'Carter'), ('Andrea', 'Brad'))])},
                {'nodes': set([('Andrea', 'Carter')])}
            ],
            'winners': set(['Andrea', 'Brad'])
        })

    #
    def test_one_ballot_one_winner(self):

        # Generate data
        input = [
            {"count": 1, "ballot": {"a": 1, "b": 1, "c": 3}}
        ]
        output = SchulzeSTV(input, required_winners=1, ballot_notation="rating").as_dict()

        # Run tests
        self.assertEqual(output['winners'], set(["c"]))

    # This example ensures that vote management strength calculations are
    # calculated correctly.
    def test_one_ballot_two_winners(self):

        # Generate data
        input = [
            {"count": 1, "ballot": {"Metal": 1, "Paper": 1, "Plastic": 2, "Wood": 2}},
        ]
        output = SchulzeSTV(input, required_winners=2, ballot_notation="ranking").as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['Paper', 'Wood', 'Metal', 'Plastic']),
            'winners': set(['Paper', 'Metal'])
        })

    # This example ensures that the proportional completion round correctly
    # accounts for sparse pattern weights.
    def test_two_ballots_two_winners(self):

        # Generate data
        input = [
            {"count": 1, "ballot": {"Metal": 2, "Paper": 1, "Plastic": 2, "Wood": 2}},
            {"count": 1, "ballot": {"Metal": 2, "Paper": 2, "Plastic": 2, "Wood": 1}}
        ]
        output = SchulzeSTV(input, required_winners=2, ballot_notation="ranking").as_dict()

        # Run tests
        self.assertEqual(output, {
            "candidates": set(['Metal', 'Wood', 'Plastic', 'Paper']),
            "winners": set(['Paper', 'Wood']),
        })

    #
    def test_happenstance_example(self):

        # Generate data
        input = [
            {"count": 1, "ballot": {"A": 9, "B": 1, "C": 1, "D": 9, "E": 9, "F": 2}},
            {"count": 1, "ballot": {"A": 3, "B": 2, "C": 3, "D": 1, "E": 9, "F": 9}},
            {"count": 1, "ballot": {"A": 9, "B": 9, "C": 9, "D": 9, "E": 1, "F": 9}}
        ]
        output = SchulzeSTV(input, required_winners=2, ballot_notation="ranking").as_dict()

        # Run tests
        self.assertEqual(
            output["tied_winners"],
            set([('D', 'E'), ('B', 'E'), ('C', 'E'), ('B', 'D')])
        )

    # Any winner set should include one from each of A, B, and C
    def test_happenstance_example_2(self):

        # Generate data
        input = [
            {"count": 5, "ballot": [["A1", "A2"], ["B1", "B2"], ["C1", "C2"]]},
            {"count": 2, "ballot": [["B1", "B2"], ["A1", "A2", "C1", "C2"]]},
            {"count": 4, "ballot": [["C1", "C2"], ["B1", "B2"], ["A1", "A2"]]},
        ]
        output = SchulzeSTV(input, required_winners=3, ballot_notation="grouping").as_dict()

        # Run tests
        self.assert_(set(["A1", "A2"]) & output["winners"])
        self.assert_(set(["B1", "B2"]) & output["winners"])
        self.assert_(set(["C1", "C2"]) & output["winners"])

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_stv
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.stv import STV
import unittest


class TestSTV(unittest.TestCase):

    # STV, no rounds
    def test_stv_landslide(self):

        # Generate data
        input = [
            {"count": 56, "ballot": ["c1", "c2", "c3"]},
            {"count": 40, "ballot": ["c2", "c3", "c1"]},
            {"count": 20, "ballot": ["c3", "c1", "c2"]}
        ]
        output = STV(input, required_winners=2).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3']),
            'quota': 39,
            'rounds': [{
                'tallies': {'c3': 20.0, 'c2': 40.0, 'c1': 56.0},
                'winners': set(['c2', 'c1'])
            }],
            'winners': set(['c2', 'c1'])
        })

    # STV, no rounds
    def test_stv_everyone_wins(self):

        # Generate data
        input = [
            {"count": 56, "ballot": ["c1", "c2", "c3"]},
            {"count": 40, "ballot": ["c2", "c3", "c1"]},
            {"count": 20, "ballot": ["c3", "c1", "c2"]}
        ]
        output = STV(input, required_winners=3).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3']),
            'quota': 30,
            'rounds': [],
            'remaining_candidates': set(['c1', 'c2', 'c3']),
            'winners': set(['c1', 'c2', 'c3'])
        })

    # STV, example from Wikipedia
    # http://en.wikipedia.org/wiki/Single_transferable_vote#An_example
    def test_stv_wiki_example(self):

        # Generate data
        input = [
            {"count": 4, "ballot": ["orange"]},
            {"count": 2, "ballot": ["pear", "orange"]},
            {"count": 8, "ballot": ["chocolate", "strawberry"]},
            {"count": 4, "ballot": ["chocolate", "sweets"]},
            {"count": 1, "ballot": ["strawberry"]},
            {"count": 1, "ballot": ["sweets"]}
        ]
        output = STV(input, required_winners=3).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['orange', 'pear', 'chocolate', 'strawberry', 'sweets']),
            'quota': 6,
            'rounds': [
                {'tallies': {'orange': 4.0, 'strawberry': 1.0, 'pear': 2.0, 'sweets': 1.0, 'chocolate': 12.0}, 'winners': set(['chocolate'])},
                {'tallies': {'orange': 4.0, 'strawberry': 5.0, 'pear': 2.0, 'sweets': 3.0}, 'loser': 'pear'},
                {'tallies': {'orange': 6.0, 'strawberry': 5.0, 'sweets': 3.0}, 'winners': set(['orange'])},
                {'tallies': {'strawberry': 5.0, 'sweets': 3.0}, 'loser': 'sweets'}
            ],
            'remaining_candidates': set(['strawberry']),
            'winners': set(['orange', 'strawberry', 'chocolate'])
        })

    # STV, no rounds
    def test_stv_single_ballot(self):

        # Generate data
        input = [
            {"count": 1, "ballot": ["c1", "c2", "c3", "c4"]},
        ]
        output = STV(input, required_winners=3).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3', 'c4']),
            'quota': 1,
            'rounds': [
                {'tallies': {'c1': 1.0}, 'winners': set(['c1'])},
                {'note': 'reset', 'tallies': {'c2': 1.0}, 'winners': set(['c2'])},
                {'note': 'reset', 'tallies': {'c3': 1.0}, 'winners': set(['c3'])}
            ],
            'winners': set(['c1', 'c2', 'c3'])
        })

    # STV, no rounds
    def test_stv_fewer_voters_than_winners(self):

        # Generate data
        input = [
            {"count": 1, "ballot": ["c1", "c3", "c4"]},
            {"count": 1, "ballot": ["c2", "c3", "c4"]},
        ]
        output = STV(input, required_winners=3).as_dict()

        # Run tests
        self.assertEqual(output, {
            'candidates': set(['c1', 'c2', 'c3', 'c4']),
            'quota': 1,
            'rounds': [
                {'tallies': {'c2': 1.0, 'c1': 1.0}, 'winners': set(['c2', 'c1'])},
                {'note': 'reset', 'tallies': {'c3': 2.0}, 'winners': set(['c3'])}
            ],
            'winners': set(['c1', 'c2', 'c3'])
        })

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_tie_breaker
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.tie_breaker import TieBreaker
import unittest


class TestTieBreaker(unittest.TestCase):

    def setUp(self):
        self.tieBreaker = TieBreaker(['a', 'b', 'c', 'd'])
        self.tieBreaker.random_ordering = ['a', 'b', 'c', 'd']

    def test_simple_tie(self):
        self.assertEqual(
            self.tieBreaker.break_ties(set(['b', 'c'])),
            'b'
        )

    def test_simple_tie_reverse(self):
        self.assertEqual(
            self.tieBreaker.break_ties(set(['b', 'c']), reverse=True),
            'c'
        )

    def test_tuple_tie(self):
        self.assertEqual(
            self.tieBreaker.break_ties(set([('c', 'a'), ('b', 'd'), ('c', 'b')])),
            ('b', 'd')
        )

    def test_tuple_tie_reverse(self):
        self.assertEqual(
            self.tieBreaker.break_ties(set([('c', 'a'), ('b', 'd'), ('c', 'b')]), reverse=True),
            ('c', 'b')
        )

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_schulze_pr
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.schulze_pr import SchulzePR
import time
import unittest


class TestSchulzePR(unittest.TestCase):

    # This test considers a case that SchulzeSTV starts to choke on due to the
    # potential number of nodes and edges to consider.
    def test_10_candidates_5_winners(self):

        # Generate data
        startTime = time.time()
        input = [
            {"count": 1, "ballot": {"A": 9, "B": 1, "C": 1, "D": 9, "E": 9, "F": 2, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 3, "B": 2, "C": 3, "D": 1, "E": 9, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 9, "B": 9, "C": 9, "D": 9, "E": 1, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}}
        ]
        SchulzePR(input, winner_threshold=5, ballot_notation="ranking").as_dict()

        # Run tests
        self.assert_(time.time() - startTime < 1)

    # This test considers a case that SchulzeSTV starts to choke on due to the
    # potential size of the completion patterns
    def test_10_candidates_9_winners(self):

        # Generate data
        startTime = time.time()
        input = [
            {"count": 1, "ballot": {"A": 9, "B": 1, "C": 1, "D": 9, "E": 9, "F": 2, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 3, "B": 2, "C": 3, "D": 1, "E": 9, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 9, "B": 9, "C": 9, "D": 9, "E": 1, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}}
        ]
        SchulzePR(input, winner_threshold=9, ballot_notation="ranking").as_dict()

        # Run tests
        self.assert_(time.time() - startTime < 2)

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = test_schulze_stv
# Copyright (C) 2009, Brad Beattie
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pyvotecore.schulze_stv import SchulzeSTV
import unittest
import time


class TestSchulzeSTV(unittest.TestCase):

    # This test considers a case in which there are 10 choose 5 (252) possible
    # outcomes and 252 choose 2 (31626) possible edges between them.
    def test_10_candidates_5_winners(self):

        # Generate data
        startTime = time.time()
        input = [
            {"count": 1, "ballot": {"A": 9, "B": 1, "C": 1, "D": 9, "E": 9, "F": 2, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 3, "B": 2, "C": 3, "D": 1, "E": 9, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 9, "B": 9, "C": 9, "D": 9, "E": 1, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}}
        ]
        SchulzeSTV(input, required_winners=5, ballot_notation="ranking").as_dict()

        # Run tests
        self.assert_(time.time() - startTime < 8)

    # This test looks at few graph nodes, but large completion patterns. With
    # 10 candidates and 9 winners, we're looking at 3^9 (19683) patterns to
    # consider.
    def test_10_candidates_9_winners(self):

        # Generate data
        startTime = time.time()
        input = [
            {"count": 1, "ballot": {"A": 9, "B": 1, "C": 1, "D": 9, "E": 9, "F": 2, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 3, "B": 2, "C": 3, "D": 1, "E": 9, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 9, "B": 9, "C": 9, "D": 9, "E": 1, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}}
        ]
        SchulzeSTV(input, required_winners=9, ballot_notation="ranking").as_dict()

        # Run tests
        self.assert_(time.time() - startTime < 2)

    # This test ensures that if you request the same number of winners as there
    # are candidates, the system doesn't take the long route to calculate them.
    def test_10_candidates_10_winners(self):

        # Generate data
        startTime = time.time()
        input = [
            {"count": 1, "ballot": {"A": 9, "B": 1, "C": 1, "D": 9, "E": 9, "F": 2, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 3, "B": 2, "C": 3, "D": 1, "E": 9, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}},
            {"count": 1, "ballot": {"A": 9, "B": 9, "C": 9, "D": 9, "E": 1, "F": 9, "G": 9, "H": 9, "I": 9, "J": 9}}
        ]
        output = SchulzeSTV(input, required_winners=10, ballot_notation="ranking").as_dict()

        # Run tests
        self.assertAlmostEqual(startTime, time.time(), 1)
        self.assertEqual(output, {
            'winners': set(['A', 'C', 'B', 'E', 'D', 'G', 'F', 'I', 'H', 'J']),
            'candidates': set(['A', 'C', 'B', 'E', 'D', 'G', 'F', 'I', 'H', 'J'])
        })

if __name__ == "__main__":
    unittest.main()

########NEW FILE########
