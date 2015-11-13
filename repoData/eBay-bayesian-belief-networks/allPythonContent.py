__FILENAME__ = bbn
from __future__ import division
'''Data Structures to represent a BBN as a DAG.'''
import sys
import copy
import heapq

from StringIO import StringIO
from itertools import combinations, product
from collections import defaultdict

from prettytable import PrettyTable

from bayesian import GREEN, NORMAL
from bayesian.graph import Node, UndirectedNode, connect
from bayesian.graph import Graph, UndirectedGraph
from bayesian.utils import get_args, named_base_type_factory
from bayesian.utils import get_original_factors


class BBNNode(Node):

    def __init__(self, factor):
        super(BBNNode, self).__init__(factor.__name__)
        self.func = factor
        self.argspec = get_args(factor)

    def __repr__(self):
        return '<BBNNode %s (%s)>' % (
            self.name,
            self.argspec)


class BBN(Graph):
    '''A Directed Acyclic Graph'''

    def __init__(self, nodes_dict, name=None, domains={}):
        self.nodes = nodes_dict.values()
        self.vars_to_nodes = nodes_dict
        self.domains = domains
        # For each node we want
        # to explicitly record which
        # variable it 'introduced'.
        # Note that we cannot record
        # this duing Node instantiation
        # becuase at that point we do
        # not yet know *which* of the
        # variables in the argument
        # list is the one being modeled
        # by the function. (Unless there
        # is only one argument)
        for variable_name, node in nodes_dict.items():
            node.variable_name = variable_name

    def get_graphviz_source(self):
        fh = StringIO()
        fh.write('digraph G {\n')
        fh.write('  graph [ dpi = 300 bgcolor="transparent" rankdir="LR"];\n')
        edges = set()
        for node in sorted(self.nodes, key=lambda x:x.name):
            fh.write('  %s [ shape="ellipse" color="blue"];\n' % node.name)
            for child in node.children:
                edge = (node.name, child.name)
                edges.add(edge)
        for source, target in sorted(edges, key=lambda x:(x[0], x[1])):
            fh.write('  %s -> %s;\n' % (source, target))
        fh.write('}\n')
        return fh.getvalue()

    def build_join_tree(self):
        jt = build_join_tree(self)
        return jt

    def query(self, **kwds):
        jt = self.build_join_tree()
        assignments = jt.assign_clusters(self)
        jt.initialize_potentials(assignments, self, kwds)

        jt.propagate()
        marginals = dict()
        normalizers = defaultdict(float)

        for node in self.nodes:
            for k, v in jt.marginal(node).items():
                # For a single node the
                # key for the marginal tt always
                # has just one argument so we
                # will unpack it here
                marginals[k[0]] = v
                # If we had any evidence then we
                # need to normalize all the variables
                # not evidenced.
                if kwds:
                    normalizers[k[0][0]] += v

        if kwds:
            for k, v in marginals.iteritems():
                if normalizers[k[0]] != 0:
                    marginals[k] /= normalizers[k[0]]

        return marginals

    def q(self, **kwds):
        '''Interactive user friendly wrapper
        around query()
        '''
        result = self.query(**kwds)
        tab = PrettyTable(['Node', 'Value', 'Marginal'], sortby='Node')
        tab.align = 'l'
        tab.align['Marginal'] = 'r'
        tab.float_format = '%8.6f'
        for (node, value), prob in result.items():
            if kwds.get(node, '') == value:
                tab.add_row(['%s*' % node,
                             '%s%s*%s' % (GREEN, value, NORMAL),
                             '%8.6f' % prob])
            else:
                tab.add_row([node, value, '%8.6f' % prob])
        print tab


class JoinTree(UndirectedGraph):

    def __init__(self, nodes, name=None):
        super(JoinTree, self).__init__(
            nodes, name)

    @property
    def sepset_nodes(self):
        return [n for n in self.nodes if isinstance(n, JoinTreeSepSetNode)]

    @property
    def clique_nodes(self):
        return [n for n in self.nodes if isinstance(n, JoinTreeCliqueNode)]

    def get_graphviz_source(self):
        fh = StringIO()
        fh.write('graph G {\n')
        fh.write('  graph [ dpi = 300 bgcolor="transparent" rankdir="LR"];\n')
        edges = set()
        for node in self.nodes:
            if isinstance(node, JoinTreeSepSetNode):
                fh.write('  %s [ shape="box" color="blue"];\n' % node.name)
            else:
                fh.write('  %s [ shape="ellipse" color="red"];\n' % node.name)
            for neighbour in node.neighbours:
                edge = [node.name, neighbour.name]
                edges.add(tuple(sorted(edge)))
        for source, target in edges:
            fh.write('  %s -- %s;\n' % (source, target))
        fh.write('}\n')
        return fh.getvalue()

    def initialize_potentials(self, assignments, bbn, evidence={}):
        # Step 1, assign 1 to each cluster and sepset
        for node in self.nodes:
            tt = dict()
            vals = []
            variables = node.variable_names
            # Lets sort the variables here so that
            # the variable names in the keys in
            # the tt are always sorted.
            variables.sort()
            for variable in variables:
                domain = bbn.domains.get(variable, [True, False])
                vals.append(list(product([variable], domain)))
            permutations = product(*vals)
            for permutation in permutations:
                tt[permutation] = 1
            node.potential_tt = tt

        # Step 2: Note that in H&D the assignments are
        # done as part of step 2 however we have
        # seperated the assignment algorithm out and
        # done these prior to step 1.
        # Now for each assignment we want to
        # generate a truth-table from the
        # values of the bbn truth-tables that are
        # assigned to the clusters...

        for clique, bbn_nodes in assignments.iteritems():

            tt = dict()
            vals = []
            variables = list(clique.variable_names)
            variables.sort()
            for variable in variables:
                domain = bbn.domains.get(variable, [True, False])
                vals.append(list(product([variable], domain)))
            permutations = product(*vals)
            for permutation in permutations:
                argvals = dict(permutation)
                potential = 1
                for bbn_node in bbn_nodes:
                    bbn_node.clique = clique
                    # We could handle evidence here
                    # by altering the potential_tt.
                    # This is slightly different to
                    # the way that H&D do it.

                    arg_list = []
                    for arg_name in get_args(bbn_node.func):
                        arg_list.append(argvals[arg_name])

                    potential *= bbn_node.func(*arg_list)
                tt[permutation] = potential
            clique.potential_tt = tt

        if not evidence:
            # We dont need to deal with likelihoods
            # if we dont have any evidence.
            return

        # Step 2b: Set each liklihood element ^V(v) to 1
        likelihoods = self.initial_likelihoods(assignments, bbn)
        for clique, bbn_nodes in assignments.iteritems():
            for node in bbn_nodes:
                if node.variable_name in evidence:
                    for k, v in clique.potential_tt.items():
                        # Encode the evidence in
                        # the clique potential...
                        for variable, value in k:
                            if (variable == node.variable_name):
                                if value != evidence[variable]:
                                    clique.potential_tt[k] = 0


    def initial_likelihoods(self, assignments, bbn):
        # TODO: Since this is the same every time we should probably
        # cache it.
        l = defaultdict(dict)
        for clique, bbn_nodes in assignments.iteritems():
            for node in bbn_nodes:
                for value in bbn.domains.get(node.variable_name, [True, False]):
                    l[(node.variable_name, value)] = 1
        return l


    def assign_clusters(self, bbn):
        assignments_by_family = dict()
        assignments_by_clique = defaultdict(list)
        assigned = set()
        for node in bbn.nodes:
            args = get_args(node.func)
            if len(args) == 1:
                # If the func has only 1 arg
                # it means that it does not
                # specify a conditional probability
                # This is where H&D is a bit vague
                # but it seems to imply that we
                # do not assign it to any
                # clique.
                # Revising this for now as I dont
                # think its correct, I think
                # all CPTs need to be assigned
                # once and once only. The example
                # in H&D just happens to be a clique
                # that f_a could have been assigned
                # to but wasnt presumably because
                # it got assigned somewhere else.
                pass
                #continue
            # Now we need to find a cluster that
            # is a superset of the Family(v)
            # Family(v) is defined by D&H to
            # be the union of v and parents(v)
            family = set(args)
            # At this point we need to know which *variable*
            # a BBN node represents. Up to now we have
            # not *explicitely* specified this, however
            # we have been following some conventions
            # so we could just use this convention for
            # now. Need to come back to this to
            # perhaps establish the variable at
            # build bbn time...
            containing_cliques = [clique_node for clique_node in
                                  self.clique_nodes if
                                  (set(clique_node.variable_names).
                                   issuperset(family))]
            assert len(containing_cliques) >= 1
            for clique in containing_cliques:
                if node in assigned:
                    # Make sure we assign all original
                    # PMFs only once each
                    continue
                assignments_by_clique[clique].append(node)
                assigned.add(node)
            assignments_by_family[tuple(family)] = containing_cliques
        return assignments_by_clique

    def propagate(self, starting_clique=None):
        '''Refer to H&D pg. 20'''

        # Step 1 is to choose an arbitrary clique cluster
        # as starting cluster
        if starting_clique is None:
            starting_clique = self.clique_nodes[0]

        # Step 2: Unmark all clusters, call collect_evidence(X)
        for node in self.clique_nodes:
            node.marked = False
        self.collect_evidence(sender=starting_clique)

        # Step 3: Unmark all clusters, call distribute_evidence(X)
        for node in self.clique_nodes:
            node.marked = False

        self.distribute_evidence(starting_clique)

    def collect_evidence(self, sender=None, receiver=None):

        # Step 1, Mark X
        sender.marked = True

        # Step 2, call collect_evidence on Xs unmarked
        # neighbouring clusters.
        for neighbouring_clique in sender.neighbouring_cliques:
            if not neighbouring_clique.marked:
                self.collect_evidence(
                    sender=neighbouring_clique,
                    receiver=sender)
        # Step 3, pass message from sender to receiver
        if receiver is not None:
            sender.pass_message(receiver)

    def distribute_evidence(self, sender=None, receiver=None):

        # Step 1, Mark X
        sender.marked = True

        # Step 2, pass a messagee from X to each of its
        # unmarked neighbouring clusters
        for neighbouring_clique in sender.neighbouring_cliques:
            if not neighbouring_clique.marked:
                sender.pass_message(neighbouring_clique)

        # Step 3, call distribute_evidence on Xs unmarked neighbours
        for neighbouring_clique in sender.neighbouring_cliques:
            if not neighbouring_clique.marked:
                self.distribute_evidence(
                    sender=neighbouring_clique,
                    receiver=sender)

    def marginal(self, bbn_node):
        '''Remember that the original
        variables that we are interested in
        are actually in the bbn. However
        when we constructed the JT we did
        it out of the moralized graph.
        This means the cliques refer to
        the nodes in the moralized graph
        and not the nodes in the BBN.
        For efficiency we should come back
        to this and add some pointers
        or an index.
        '''

        # First we will find the JT nodes that
        # contain the bbn_node ie all the nodes
        # that are either cliques or sepsets
        # that contain the bbn_node
        # Note that for efficiency we
        # should probably have an index
        # cached in the bbn and/or the jt.
        containing_nodes = []

        for node in self.clique_nodes:
            if bbn_node.name in [n.name for n in node.clique.nodes]:
                containing_nodes.append(node)
                # In theory it doesnt matter which one we
                # use so we could bale out after we
                # find the first one
                # TODO: With some better indexing we could
                # avoid searching for this node every time...

        clique_node = containing_nodes[0]
        tt = defaultdict(float)
        for k, v in clique_node.potential_tt.items():
            entry = transform(
                k,
                clique_node.variable_names,
                [bbn_node.variable_name]) # XXXXXX
            tt[entry] += v

        # Now if this node was evidenced we need to normalize
        # over the values...
        # TODO: It will be safer to copy the defaultdict to a regular dict
        return tt


class Clique(object):

    def __init__(self, cluster):
        self.nodes = cluster


    def __repr__(self):
        vars = sorted([n.variable_name for n in self.nodes])
        return 'Clique_%s' % ''.join([v.upper() for v in vars])


def transform(x, X, R):
    '''Transform a Potential Truth Table
    Entry into a different variable space.
    For example if we have the
    entry [True, True, False] representing
    values of variable [A, B, C] in X
    and we want to transform into
    R which has variables [C, A] we
    will return the entry [False, True].
    Here X represents the argument list
    for the clique set X and R represents
    the argument list for the sepset.
    This implies that R is always a subset
    of X'''
    entry = []
    for r in R:
        pos = X.index(r)
        entry.append(x[pos])
    return tuple(entry)


class JoinTreeCliqueNode(UndirectedNode):

    def __init__(self, clique):
        super(JoinTreeCliqueNode, self).__init__(
            clique.__repr__())
        self.clique = clique
        # Now we create a pointer to
        # this clique node as the "parent" clique
        # node of each node in the cluster.
        #for node in self.clique.nodes:
        #    node.parent_clique = self
        # This is not quite correct, the
        # parent cluster as defined by H&D
        # is *a* cluster than is a superset
        # of Family(v)

    @property
    def variable_names(self):
        '''Return the set of variable names
        that this clique represents'''
        var_names = []
        for node in self.clique.nodes:
            var_names.append(node.variable_name)
        return sorted(var_names)

    @property
    def neighbouring_cliques(self):
        '''Return the neighbouring cliques
        this is used during the propagation algorithm.

        '''
        neighbours = set()
        for sepset_node in self.neighbours:
            # All *immediate* neighbours will
            # be sepset nodes, its the neighbours of
            # these sepsets that form the nodes
            # clique neighbours (excluding itself)
            for clique_node in sepset_node.neighbours:
                if clique_node is not self:
                    neighbours.add(clique_node)
        return neighbours

    def pass_message(self, target):
        '''Pass a message from this node to the
        recipient node during propagation.

        NB: It may turnout at this point that
        after initializing the potential
        Truth table on the JT we could quite
        simply construct a factor graph
        from the JT and use the factor
        graph sum product propagation.
        In theory this should be the same
        and since the semantics are already
        worked out it would be easier.'''

        # Find the sepset node between the
        # source and target nodes.
        sepset_node = list(set(self.neighbours).intersection(
            target.neighbours))[0]

        # Step 1: projection
        self.project(sepset_node)

        # Step 2 absorbtion
        self.absorb(sepset_node, target)

    def project(self, sepset_node):
        '''See page 20 of PPTC.
        We assign a new potential tt to
        the sepset which consists of the
        potential of the source node
        with all variables not in R marginalized.
        '''
        assert sepset_node in self.neighbours
        # First we make a copy of the
        # old potential tt
        sepset_node.potential_tt_old = copy.deepcopy(
            sepset_node.potential_tt)

        # Now we assign a new potential tt
        # to the sepset by marginalizing
        # out the variables from X that are not
        # in the sepset
        tt = defaultdict(float)
        for k, v in self.potential_tt.items():
            entry = transform(k, self.variable_names,
                              sepset_node.variable_names)
            tt[entry] += v
        sepset_node.potential_tt = tt

    def absorb(self, sepset, target):
        # Assign a new potential tt to
        # Y (the target)
        tt = dict()

        for k, v in target.potential_tt.items():
            # For each entry we multiply by
            # sepsets new value and divide
            # by sepsets old value...
            # Note that nowhere in H&D is
            # division on potentials defined.
            # However in Barber page 12
            # an equation implies that
            # the the division is equivalent
            # to the original assignment.
            # For now we will assume entry-wise
            # division which seems logical.
            entry = transform(k, target.variable_names,
                              sepset.variable_names)
            if target.potential_tt[k] == 0:
                tt[k] = 0
            else:
                tt[k] = target.potential_tt[k] * (sepset.potential_tt[entry] /
                                                  sepset.potential_tt_old[entry])
        target.potential_tt = tt

    def __repr__(self):
        return '<JoinTreeCliqueNode: %s>' % self.clique


class SepSet(object):

    def __init__(self, X, Y):
        '''X and Y are cliques represented as sets.'''
        self.X = X
        self.Y = Y
        self.label = list(X.nodes.intersection(Y.nodes))

    @property
    def mass(self):
        return len(self.label)

    @property
    def cost(self):
        '''Since cost is used as a tie-breaker
        and is an optimization for inference time
        we will punt on it for now. Instead we
        will just use the assumption that all
        variables in X and Y are binary and thus
        use a weight of 2.
        TODO: come back to this and compute
        actual weights
        '''
        return 2 ** len(self.X.nodes) + 2 ** len(self.Y.nodes)

    def insertable(self, forest):
        '''A sepset can only be inserted
        into the JT if the cliques it
        separates are NOT already on
        the same tree.
        NOTE: For efficiency we should
        add an index that indexes cliques
        into the trees in the forest.'''
        X_trees = [t for t in forest if self.X in
                   [n.clique for n in t.clique_nodes]]
        Y_trees = [t for t in forest if self.Y in
                   [n.clique for n in t.clique_nodes]]
        assert len(X_trees) == 1
        assert len(Y_trees) == 1
        if X_trees[0] is not Y_trees[0]:
            return True
        return False

    def insert(self, forest):
        '''Inserting this sepset into
        a forest, providing the two
        cliques are in different trees,
        means that effectively we are
        collapsing the two trees into
        one. We will explicitely perform
        this collapse by adding the
        sepset node into the tree
        and adding edges between itself
        and its clique node neighbours.
        Finally we must remove the
        second tree from the forest
        as it is now joined to the
        first.
        '''
        X_tree = [t for t in forest if self.X in
                  [n.clique for n in t.clique_nodes]][0]
        Y_tree = [t for t in forest if self.Y in
                  [n.clique for n in t.clique_nodes]][0]

        # Now create and insert a sepset node into the Xtree
        ss_node = JoinTreeSepSetNode(self, self)
        X_tree.nodes.append(ss_node)

        # And connect them
        self.X.node.neighbours.append(ss_node)
        ss_node.neighbours.append(self.X.node)

        # Now lets keep the X_tree and drop the Y_tree
        # this means we need to copy all the nodes
        # in the Y_tree that are not already in the X_tree
        for node in Y_tree.nodes:
            if node in X_tree.nodes:
                continue
            X_tree.nodes.append(node)

        # Now connect the sepset node to the
        # Y_node (now residing in the X_tree)
        self.Y.node.neighbours.append(ss_node)
        ss_node.neighbours.append(self.Y.node)

        # And finally we must remove the Y_tree from
        # the forest...
        forest.remove(Y_tree)

    def __repr__(self):
        return 'SepSet_%s' % ''.join(
            #[x.name[2:].upper() for x in list(self.label)])
            [x.variable_name.upper() for x in list(self.label)])


class JoinTreeSepSetNode(UndirectedNode):

    def __init__(self, name, sepset):
        super(JoinTreeSepSetNode, self).__init__(name)
        self.sepset = sepset

    @property
    def variable_names(self):
        '''Return the set of variable names
        that this sepset represents'''
        # TODO: we are assuming here
        # that X and Y are each separate
        # variables from the BBN which means
        # we are assuming that the sepsets
        # always contain only 2 nodes.
        # Need to check whether this is
        # the case.
        return sorted([x.variable_name for x in self.sepset.label])

    def __repr__(self):
        return '<JoinTreeSepSetNode: %s>' % self.sepset


def build_bbn(*args, **kwds):
    '''Builds a BBN Graph from
    a list of functions and domains'''
    variables = set()
    domains = kwds.get('domains', {})
    name = kwds.get('name')
    variable_nodes = dict()
    factor_nodes = dict()

    if isinstance(args[0], list):
        # Assume the functions were all
        # passed in a list in the first
        # argument. This makes it possible
        # to build very large graphs with
        # more than 255 functions, since
        # Python functions are limited to
        # 255 arguments.
        args = args[0]

    for factor in args:
        factor_args = get_args(factor)
        variables.update(factor_args)
        bbn_node = BBNNode(factor)
        factor_nodes[factor.__name__] = bbn_node

    # Now lets create the connections
    # To do this we need to find the
    # factor node representing the variables
    # in a child factors argument and connect
    # it to the child node.

    # Note that calling original_factors
    # here can break build_bbn if the
    # factors do not correctly represent
    # a BBN.
    original_factors = get_original_factors(factor_nodes.values())
    for factor_node in factor_nodes.values():
        factor_args = get_args(factor_node)
        parents = [original_factors[arg] for arg in
                   factor_args if original_factors[arg] != factor_node]
        for parent in parents:
            connect(parent, factor_node)
    bbn = BBN(original_factors, name=name)
    bbn.domains = domains

    return bbn


def make_undirected_copy(dag):
    '''Returns an exact copy of the dag
    except that direction of edges are dropped.'''
    nodes = dict()
    for node in dag.nodes:
        undirected_node = UndirectedNode(
            name=node.name)
        undirected_node.func = node.func
        undirected_node.argspec = node.argspec
        undirected_node.variable_name = node.variable_name
        nodes[node.name] = undirected_node
    # Now we need to traverse the original
    # nodes once more and add any parents
    # or children as neighbours.
    for node in dag.nodes:
        for parent in node.parents:
            nodes[node.name].neighbours.append(
                nodes[parent.name])
            nodes[parent.name].neighbours.append(
                nodes[node.name])

    g = UndirectedGraph(nodes.values())
    return g


def make_moralized_copy(gu, dag):
    '''gu is an undirected graph being
    a copy of dag.'''
    gm = copy.deepcopy(gu)
    gm_nodes = dict(
        [(node.name, node) for node in gm.nodes])
    for node in dag.nodes:
        for parent_1, parent_2 in combinations(
                node.parents, 2):
            if gm_nodes[parent_1.name] not in \
               gm_nodes[parent_2.name].neighbours:
                gm_nodes[parent_2.name].neighbours.append(
                    gm_nodes[parent_1.name])
            if gm_nodes[parent_2.name] not in \
               gm_nodes[parent_1.name].neighbours:
                gm_nodes[parent_1.name].neighbours.append(
                    gm_nodes[parent_2.name])
    return gm


def priority_func(node):
    '''Specify the rules for computing
    priority of a node. See Harwiche and Wang pg 12.
    '''
    # We need to calculate the number of edges
    # that would be added.
    # For each node, we need to connect all
    # of the nodes in itself and its neighbours
    # (the "cluster") which are not already
    # connected. This will be the primary
    # key value in the heap.
    # We need to fix the secondary key, right
    # now its just 2 (because mostly the variables
    # will be discrete binary)
    introduced_arcs = 0
    cluster = [node] + node.neighbours
    for node_a, node_b in combinations(cluster, 2):
        if node_a not in node_b.neighbours:
            assert node_b not in node_a.neighbours
            introduced_arcs += 1
    return [introduced_arcs, 2]  # TODO: Fix this to look at domains


def construct_priority_queue(nodes, priority_func=priority_func):
    pq = []
    for node_name, node in nodes.iteritems():
        entry = priority_func(node) + [node.name]
        heapq.heappush(pq, entry)
    return pq


def record_cliques(cliques, cluster):
    '''We only want to save the cluster
    if it is not a subset of any clique
    already saved.
    Argument cluster must be a set'''
    if any([cluster.issubset(c.nodes) for c in cliques]):
        return
    cliques.append(Clique(cluster))


def triangulate(gm, priority_func=priority_func):
    '''Triangulate the moralized Graph. (in Place)
    and return the cliques of the triangulated
    graph as well as the elimination ordering.'''

    # First we will make a copy of gm...
    gm_ = copy.deepcopy(gm)

    # Now we will construct a priority q using
    # the standard library heapq module.
    # See docs for example of priority q tie
    # breaking. We will use a 3 element list
    # with entries as follows:
    #   - Number of edges added if V were selected
    #   - Weight of V (or cluster)
    #   - Pointer to node in gm_
    # Note that its unclear from Huang and Darwiche
    # what is meant by the "number of values of V"
    gmnodes = dict([(node.name, node) for node in gm.nodes])
    elimination_ordering = []
    cliques = []
    while True:
        gm_nodes = dict([(node.name, node) for node in gm_.nodes])
        if not gm_nodes:
            break
        pq = construct_priority_queue(gm_nodes, priority_func)
        # Now we select the first node in
        # the priority q and any arcs that
        # should be added in order to fully connect
        # the cluster should be added to both
        # gm and gm_
        v = gm_nodes[pq[0][2]]
        cluster = [v] + v.neighbours
        for node_a, node_b in combinations(cluster, 2):
            if node_a not in node_b.neighbours:
                node_b.neighbours.append(node_a)
                node_a.neighbours.append(node_b)
                # Now also add this new arc to gm...
                gmnodes[node_b.name].neighbours.append(
                    gmnodes[node_a.name])
                gmnodes[node_a.name].neighbours.append(
                    gmnodes[node_b.name])
        gmcluster = set([gmnodes[c.name] for c in cluster])
        record_cliques(cliques, gmcluster)
        # Now we need to remove v from gm_...
        # This means we also have to remove it from all
        # of its neighbours that reference it...
        for neighbour in v.neighbours:
            neighbour.neighbours.remove(v)
        gm_.nodes.remove(v)
        elimination_ordering.append(v.name)
    return cliques, elimination_ordering


def build_join_tree(dag, clique_priority_func=priority_func):

    # First we will create an undirected copy
    # of the dag
    gu = make_undirected_copy(dag)

    # Now we create a copy of the undirected graph
    # and connect all pairs of parents that are
    # not already parents called the 'moralized' graph.
    gm = make_moralized_copy(gu, dag)

    # Now we triangulate the moralized graph...
    cliques, elimination_ordering = triangulate(gm, clique_priority_func)

    # Now we initialize the forest and sepsets
    # Its unclear from Darwiche Huang whether we
    # track a sepset for each tree or whether its
    # a global list????
    # We will implement the Join Tree as an undirected
    # graph for now...

    # First initialize a set of graphs where
    # each graph initially consists of just one
    # node for the clique. As these graphs get
    # populated with sepsets connecting them
    # they should collapse into a single tree.
    forest = set()
    for clique in cliques:
        jt_node = JoinTreeCliqueNode(clique)
        # Track a reference from the clique
        # itself to the node, this will be
        # handy later... (alternately we
        # could just collapse clique and clique
        # node into one class...
        clique.node = jt_node
        tree = JoinTree([jt_node])
        forest.add(tree)

    # Initialize the SepSets
    S = set()  # track the sepsets
    for X, Y in combinations(cliques, 2):
        if X.nodes.intersection(Y.nodes):
            S.add(SepSet(X, Y))
    sepsets_inserted = 0
    while sepsets_inserted < (len(cliques) - 1):
        # Adding in name to make this sort deterministic
        deco = [(s, -1 * s.mass, s.cost, s.__repr__()) for s in S]
        deco.sort(key=lambda x: x[1:])
        candidate_sepset = deco[0][0]
        for candidate_sepset, _, _, _ in deco:
            if candidate_sepset.insertable(forest):
                # Insert into forest and remove the sepset
                candidate_sepset.insert(forest)
                S.remove(candidate_sepset)
                sepsets_inserted += 1
                break

    assert len(forest) == 1
    jt = list(forest)[0]
    return jt

########NEW FILE########
__FILENAME__ = cancer
'''This is the example from Chapter 2 BAI'''
from bayesian.bbn import *


def fP(P):
    '''Pollution'''
    if P == 'high':
        return 0.1
    elif P == 'low':
        return 0.9


def fS(S):
    '''Smoker'''
    if S is True:
        return 0.3
    elif S is False:
        return 0.7


def fC(P, S, C):
    '''Cancer'''
    table = dict()
    table['ttt'] = 0.05
    table['ttf'] = 0.95
    table['tft'] = 0.02
    table['tff'] = 0.98
    table['ftt'] = 0.03
    table['ftf'] = 0.97
    table['fft'] = 0.001
    table['fff'] = 0.999
    key = ''
    key = key + 't' if P == 'high' else key + 'f'
    key = key + 't' if S else key + 'f'
    key = key + 't' if C else key + 'f'
    return table[key]


def fX(C, X):
    '''X-ray'''
    table = dict()
    table['tt'] = 0.9
    table['tf'] = 0.1
    table['ft'] = 0.2
    table['ff'] = 0.8
    key = ''
    key = key + 't' if C else key + 'f'
    key = key + 't' if X else key + 'f'
    return table[key]


def fD(C, D):
    '''Dyspnoeia'''
    table = dict()
    table['tt'] = 0.65
    table['tf'] = 0.35
    table['ft'] = 0.3
    table['ff'] = 0.7
    key = ''
    key = key + 't' if C else key + 'f'
    key = key + 't' if D else key + 'f'
    return table[key]


if __name__ == '__main__':
    g = build_bbn(
        fP, fS, fC, fX, fD,
        domains={
            'P': ['low', 'high']})
    g.q()
    g.q(P='high')
    g.q(D=True)
    g.q(S=True)
    g.q(C=True, S=True)
    g.q(D=True, S=True)

########NEW FILE########
__FILENAME__ = earthquake
'''This is the earthquake example from 2.5.1 in BAI'''
from bayesian.bbn import build_bbn


def f_burglary(burglary):
    if burglary is True:
        return 0.01
    return 0.99


def f_earthquake(earthquake):
    if earthquake is True:
        return 0.02
    return 0.98


def f_alarm(burglary, earthquake, alarm):
    table = dict()
    table['ttt'] = 0.95
    table['ttf'] = 0.05
    table['tft'] = 0.94
    table['tff'] = 0.06
    table['ftt'] = 0.29
    table['ftf'] = 0.71
    table['fft'] = 0.001
    table['fff'] = 0.999
    key = ''
    key = key + 't' if burglary else key + 'f'
    key = key + 't' if earthquake else key + 'f'
    key = key + 't' if alarm else key + 'f'
    return table[key]


def f_johncalls(alarm, johncalls):
    table = dict()
    table['tt'] = 0.9
    table['tf'] = 0.1
    table['ft'] = 0.05
    table['ff'] = 0.95
    key = ''
    key = key + 't' if alarm else key + 'f'
    key = key + 't' if johncalls else key + 'f'
    return table[key]


def f_marycalls(alarm, marycalls):
    table = dict()
    table['tt'] = 0.7
    table['tf'] = 0.3
    table['ft'] = 0.01
    table['ff'] = 0.99
    key = ''
    key = key + 't' if alarm else key + 'f'
    key = key + 't' if marycalls else key + 'f'
    return table[key]


if __name__ == '__main__':
    g = build_bbn(
        f_burglary,
        f_earthquake,
        f_alarm,
        f_johncalls,
        f_marycalls)
    g.q()

########NEW FILE########
__FILENAME__ = family_out_problem
'''This example is from http://www.cs.ubc.ca/~murphyk/Bayes/Charniak_91.pdf'''
from bayesian.bbn import build_bbn
from bayesian.utils import make_key

'''
This problem is also sometimes referred to
as "the Dog Problem"
'''


def family_out(fo):
    if fo:
        return 0.15
    return 0.85


def bowel_problem(bp):
    if bp:
        return 0.01
    return 0.99


def light_on(fo, lo):
    tt = dict(
        tt=0.6,
        tf=0.4,
        ft=0.05,
        ff=0.96)
    return tt[make_key(fo, lo)]


def dog_out(fo, bp, do):
    tt = dict(
        ttt=0.99,
        tft=0.9,
        ftt=0.97,
        fft=0.3)   # Note typo in article!
    key = make_key(fo, bp, do)
    if key in tt:
        return tt[key]
    key = make_key(fo, bp, not do)
    return 1 - tt[key]


def hear_bark(do, hb):
    tt = dict(
        tt=0.7,
        ft=0.01)
    key = make_key(do, hb)
    if key in tt:
        return tt[key]
    key = make_key(do, not hb)
    return 1 - tt[key]


if __name__ == '__main__':
    g = build_bbn(
        family_out,
        bowel_problem,
        light_on,
        dog_out,
        hear_bark)
    g.q()

########NEW FILE########
__FILENAME__ = huang_darwiche
'''The Example from Huang and Darwiche's Procedural Guide'''
from __future__ import division
from bayesian.bbn import *
from bayesian.utils import make_key


def f_a(a):
    return 1 / 2


def f_b(a, b):
    tt = dict(
        tt=0.5,
        ft=0.4,
        tf=0.5,
        ff=0.6)
    return tt[make_key(a, b)]


def f_c(a, c):
    tt = dict(
        tt=0.7,
        ft=0.2,
        tf=0.3,
        ff=0.8)
    return tt[make_key(a, c)]


def f_d(b, d):
    tt = dict(
        tt=0.9,
        ft=0.5,
        tf=0.1,
        ff=0.5)
    return tt[make_key(b, d)]


def f_e(c, e):
    tt = dict(
        tt=0.3,
        ft=0.6,
        tf=0.7,
        ff=0.4)
    return tt[make_key(c, e)]


def f_f(d, e, f):
    tt = dict(
        ttt=0.01,
        ttf=0.99,
        tft=0.01,
        tff=0.99,
        ftt=0.01,
        ftf=0.99,
        fft=0.99,
        fff=0.01)
    return tt[make_key(d, e, f)]


def f_g(c, g):
    tt = dict(
        tt=0.8, tf=0.2,
        ft=0.1, ff=0.9)
    return tt[make_key(c, g)]


def f_h(e, g, h):
    tt = dict(
        ttt=0.05, ttf=0.95,
        tft=0.95, tff=0.05,
        ftt=0.95, ftf=0.05,
        fft=0.95, fff=0.05)
    return tt[make_key(e, g, h)]


if __name__ == '__main__':
    g = build_bbn(
        f_a, f_b, f_c, f_d,
        f_e, f_f, f_g, f_h)
    g.q()

########NEW FILE########
__FILENAME__ = monty_hall
'''The Monty Hall Problem Modelled as a Bayesian Belief Network'''
from bayesian.bbn import *

'''
As BBN:


         GuestDoor     ActualDoor
               \         /
                MontyDoor
                p(M|G,A)


As Factor Graph:

        fGuestDoor               fActualDoor
             |                        |
         GuestDoor                ActualDoor
             |                        |
             +------fMontyDoor--------+
                         |
                     MontyDoor

Now Query: Given Guest chooses door A
and Monty chooses door B, should guest
switch to C or stay with A?

'''


def f_prize_door(prize_door):
    return 1.0 / 3


def f_guest_door(guest_door):
    return 1.0 / 3


def f_monty_door(prize_door, guest_door, monty_door):
    if prize_door == guest_door:
        if prize_door == monty_door:
            return 0
        else:
            return 0.5
    elif prize_door == monty_door:
        return 0
    elif guest_door == monty_door:
        return 0
    return 1


if __name__ == '__main__':

    g = build_bbn(
        f_prize_door,
        f_guest_door,
        f_monty_door,
        domains=dict(
            prize_door=['A', 'B', 'C'],
            guest_door=['A', 'B', 'C'],
            monty_door=['A', 'B', 'C']))
    # Initial Marginals without any knowledge.
    # Observe that the likelihood for
    # all three doors is 1/3.
    print 'Initial Marginal Probabilities:'
    g.q()
    # Now suppose the guest chooses
    # door A and Monty chooses door B.
    # Should we switch our choice from
    # A to C or not?
    # To answer this we "query" the
    # graph with instantiation of the
    # observed variables as "evidence".
    # The likelihood for door C has
    # indeed increased to 2/3 therefore
    # we should switch to door C.
    #print 'Marginals after knowing Guest chose A and Monty chose B.'
    #g.q(guest_door='A', monty_door='B')

########NEW FILE########
__FILENAME__ = pleasanton_weather
'''Simple Model of Pleasanton Weather'''
from __future__ import division

from bayesian.bbn import build_bbn

'''
This is an extremely simple five
variable model of the weather in
Pleasanton, California.
Any real weather model would have
orders of magnitude more parameters.
However the weather in this area
is remarkably consistent.
All probabilities are simple guesses
based on having lived in the area
for several years.

Here I am rather loosely defining
temp approximately as:

'hot' - above 90' F
'medium' - 55 to 90' F
'cold' - below 55' F

Rain is a binary value, so even
though in Autumn/Fall, if it does
rain, it may be only a few drops.
The value for rain would in this
case still be True.
'''

# Temp today conditioned on yesterday

spring_temp = {
    ('hot', 'hot'): 0.6,
    ('hot', 'medium'): 0.3,
    ('hot', 'cold'): 0.1,
    ('medium', 'hot'): 0.2,
    ('medium', 'medium'): 0.6,
    ('medium', 'cold'): 0.2,
    ('cold', 'hot'): 0.05,
    ('cold', 'medium'): 0.4,
    ('cold', 'cold'): 0.55}


summer_temp = {
    ('hot', 'hot'): 0.9,
    ('hot', 'medium'): 0.099,
    ('hot', 'cold'): 0.001,
    ('medium', 'hot'): 0.4,
    ('medium', 'medium'): 0.59,
    ('medium', 'cold'): 0.01,
    ('cold', 'hot'): 0.1,
    ('cold', 'medium'): 0.89,
    ('cold', 'cold'): 0.01}


autumn_temp = {
    ('hot', 'hot'): 0.6,
    ('hot', 'medium'): 0.3,
    ('hot', 'cold'): 0.1,
    ('medium', 'hot'): 0.2,
    ('medium', 'medium'): 0.6,
    ('medium', 'cold'): 0.2,
    ('cold', 'hot'): 0.05,
    ('cold', 'medium'): 0.4,
    ('cold', 'cold'): 0.55}


winter_temp = {
    ('hot', 'hot'): 0.2,
    ('hot', 'medium'): 0.6,
    ('hot', 'cold'): 0.2,
    ('medium', 'hot'): 0.05,
    ('medium', 'medium'): 0.5,
    ('medium', 'cold'): 0.45,
    ('cold', 'hot'): 0.01,
    ('cold', 'medium'): 0.19,
    ('cold', 'cold'): 0.80}


season_temp = dict(
    spring=spring_temp,
    summer=summer_temp,
    autumn=autumn_temp,
    winter=winter_temp)


# Rain today conditioned on yesterday

spring_rain = {
    (False, False): 0.35,
    (False, True): 0.65,
    (True, False): 0.35,
    (True, True): 0.65}


summer_rain = {
    (False, False): 0.95,
    (False, True): 0.05,
    (True, False): 0.8,
    (True, True): 0.2}


autumn_rain = {
    (False, False): 0.8,
    (False, True): 0.2,
    (True, False): 0.7,
    (True, True): 0.3}


winter_rain = {
    (False, False): 0.2,
    (False, True): 0.8,
    (True, False): 0.2,
    (True, True): 0.8}


season_rain = dict(
    spring=spring_rain,
    summer=summer_rain,
    autumn=autumn_rain,
    winter=winter_rain)


def f_season(season):
    return 0.25


def f_temp_yesterday(temp_yesterday):
    if temp_yesterday == 'hot':
        return 0.5
    elif temp_yesterday == 'medium':
        return 0.25
    elif temp_yesterday == 'cold':
        return 0.25


def f_rain_yesterday(rain_yesterday):
    return 0.5


def f_temp(season, temp_yesterday, temp):
    return season_temp[season][(temp_yesterday, temp)]


def f_rain(season, rain_yesterday, rain):
    return season_rain[season][(rain_yesterday, rain)]


if __name__ == '__main__':
    g = build_bbn(
        f_temp_yesterday,
        f_rain_yesterday,
        f_season,
        f_temp,
        f_rain,
        domains=dict(
            temp_yesterday=('hot', 'medium', 'cold'),
            temp=('hot', 'medium', 'cold'),
            season=('spring', 'summer', 'autumn', 'winter')))
    g.q()

########NEW FILE########
__FILENAME__ = sprinkler
'''Example from Wikipedia: http://en.wikipedia.org/wiki/Bayesian_network'''

from bayesian.bbn import *
from bayesian.utils import make_key


def f_rain(rain):
    if rain is True:
        return 0.2
    return 0.8


def f_sprinkler(rain, sprinkler):
    if rain is False and sprinkler is True:
        return 0.4
    if rain is False and sprinkler is False:
        return 0.6
    if rain is True and sprinkler is True:
        return 0.01
    if rain is True and sprinkler is False:
        return 0.99


def f_grass_wet(sprinkler, rain, grass_wet):
    table = dict()
    table['fft'] = 0.0
    table['fff'] = 1.0
    table['ftt'] = 0.8
    table['ftf'] = 0.2
    table['tft'] = 0.9
    table['tff'] = 0.1
    table['ttt'] = 0.99
    table['ttf'] = 0.01
    return table[make_key(sprinkler, rain, grass_wet)]


if __name__ == '__main__':
    g = build_bbn(
        f_rain,
        f_sprinkler,
        f_grass_wet)

########NEW FILE########
__FILENAME__ = walk
'''Simple Example Containing A Cycle'''
from __future__ import division

from bayesian.bbn import *
from bayesian.utils import make_key

'''

                          Rain Forecast
                              |
                 +------------+
                 |            |
               Rain           |
                 |            |
                 +---------+  |
                           |  |
                           Walk


Our decision to go for a walk is based on two factors,
the forecast for rain and on actual rain observed.

'''


def f_forecast(forecast):
    if forecast is True:
        return 0.6
    return 0.4


def f_rain(forecast, rain):
    table = dict()
    table['tt'] = 0.95
    table['tf'] = 0.05
    table['ft'] = 0.1
    table['ff'] = 0.9
    return table[make_key(forecast, rain)]


def f_walk(forecast, rain, walk):
    table = dict()
    table['fff'] = 0.01
    table['fft'] = 0.99
    table['ftf'] = 0.99
    table['ftt'] = 0.01
    table['tff'] = 0.8
    table['tft'] = 0.2
    table['ttf'] = 0.999
    table['ttt'] = 0.001
    return table[make_key(forecast, rain, walk)]


if __name__ == '__main__':
    g = build_bbn(
        f_forecast,
        f_rain,
        f_walk)
    g.q()

########NEW FILE########
__FILENAME__ = bif_inference_tester
import bif_parser
from time import time
from prettytable import *

# Perform exact and/or persistent sampling
# inference on a given .bif file,
# showing the time taken and the convergence
# of probability in the case of increasing samples

if __name__ == '__main__':

    # Name of .bif file
    name = 'insurance'

    # (Variable, Value) pair in marginals table to focus on
    key = ('RuggedAuto', 'Football')

    start = time()
    module_name = bif_parser.parse(name)
    print str(time()-start) + "s to parse .bif file into python module"
    start = time()
    module = __import__(module_name)
    print str(time()-start) + "s to import the module"
    start = time()
    fg = module.create_graph()
    print str(time()-start) + "s to create factor graph"
    start = time()
    bg = module.create_bbn()
    print str(time()-start) + "s to create bayesian network"

    # Methods of inference to demonstrate
    exact = True
    sampling = True

    if exact:
        start = time()
        if not sampling:

            # Set exact=True, sampling=False to
            # just show the exact marginals table
            # and select a key of interest
            bg.q()
        else:
            print 'Exact probability:', bg.query()[key]
        print 'Time taken for exact query:', time()-start

    if sampling:
        fg.inference_method = 'sample_db'

        table = PrettyTable(["Number of samples",
                             "Time to generate samples",
                             "Time to query", "Probability",
                             "Difference from previous"])

        for power in range(10):
            n = 2**power
            fg.n_samples = n
            start = time()
            fg.generate_samples(n)
            generate_time = time() - start
            start = time()
            q = fg.query()
            query_time = time() - start
            p = q[key]
            diff = "" if power == 0 else abs(p-prev_p)
            prev_p = p
            table.add_row([n, generate_time, query_time, p, diff])

        print table

########NEW FILE########
__FILENAME__ = bif_parser
import re


def parse(filename):
    """Parses the .bif file with the
    given name (exclude the extension from the argument)
    and produces a python file with create_graph() and create_bbn() functions
    to return the network. The name of the module is returned.
    The bbn/factor_graph objects will have the filename as their model name."""

    # Setting up I/O
    module_name = filename+'_bn'
    outfile = open(module_name + '.py', 'w')

    def write(s):
        outfile.write(s+"\n")
    infile = open(filename+'.bif')
    infile.readline()
    infile.readline()

    # Import statements in the produced module
    write("""from bayesian.factor_graph import *
from bayesian.bbn import *
""")

    # Regex patterns for parsing
    variable_pattern = re.compile(r"  type discrete \[ \d+ \] \{ (.+) \};\s*")
    prior_probability_pattern_1 = re.compile(
        r"probability \( ([^|]+) \) \{\s*")
    prior_probability_pattern_2 = re.compile(r"  table (.+);\s*")
    conditional_probability_pattern_1 = (
        re.compile(r"probability \( (.+) \| (.+) \) \{\s*"))
    conditional_probability_pattern_2 = re.compile(r"  \((.+)\) (.+);\s*")

    variables = {}  # domains
    functions = []  # function names (nodes/variables)

    # For every line in the file
    while True:
        line = infile.readline()

        # End of file
        if not line:
            break

        # Variable declaration
        if line.startswith("variable"):
            match = variable_pattern.match(infile.readline())

            # Extract domain and place into dictionary
            if match:
                variables[line[9:-3]] = match.group(1).split(", ")
            else:
                raise Exception("Unrecognised variable declaration:\n" + line)
            infile.readline()

        # Probability distribution
        elif line.startswith("probability"):

            match = prior_probability_pattern_1.match(line)
            if match:

                # Prior probabilities
                variable = match.group(1)
                function_name = "f_" + variable
                functions.append(function_name)
                line = infile.readline()
                match = prior_probability_pattern_2.match(line)
                write("""dictionary_%(var)s = %(dict)s

def %(function)s(%(var)s):
    return dictionary_%(var)s[%(var)s]
"""
                      % {
                          'function': function_name,
                          'var': variable,
                          'dict': str(dict(
                              zip(variables[variable],
                                  map(float, match.group(1).split(", ")))))
                      }
                )
                infile.readline()  # }

            else:
                match = conditional_probability_pattern_1.match(line)
                if match:

                    # Conditional probabilities
                    variable = match.group(1)
                    function_name = "f_" + variable
                    functions.append(function_name)
                    given = match.group(2)
                    dictionary = {}

                    # Iterate through the conditional probability table
                    while True:
                        line = infile.readline()  # line of the CPT
                        if line == '}\n':
                            break
                        match = conditional_probability_pattern_2.match(line)
                        given_values = match.group(1).split(", ")
                        for value, prob in zip(
                                variables[variable],
                                map(float, match.group(2).split(", "))):
                            dictionary[tuple(given_values + [value])] = prob
                    write("""dictionary_%(var)s = %(dict)s
def %(function)s(%(given)s, %(var)s):
    return dictionary_%(var)s[(%(given)s, %(var)s)]
"""
                          % {'function': function_name,
                             'given': given,
                             'var': variable,
                             'dict': str(dictionary)})
                else:
                    raise Exception(
                        "Unrecognised probability declaration:\n" + line)

    write("""functions = %(funcs)s
domains_dict = %(vars)s

def create_graph():
    g = build_graph(
        *functions,
        domains = domains_dict)
    g.name = '%(name)s'
    return g

def create_bbn():
    g = build_bbn(
        *functions,
        domains = domains_dict)
    g.name = '%(name)s'
    return g
"""
          % {
              'funcs': ''.join(c for c in str(functions) if c not in "'\""),
              'vars': str(variables), 'name': filename})
    outfile.close()
    return module_name

########NEW FILE########
__FILENAME__ = cancer
'''This is the example from Chapter 2 BAI'''
from bayesian.factor_graph import *


def fP(P):
    '''Pollution'''
    if P == 'high':
        return 0.1
    elif P == 'low':
        return 0.9


def fS(S):
    '''Smoker'''
    if S is True:
        return 0.3
    elif S is False:
        return 0.7


def fC(P, S, C):
    '''Cancer'''
    table = dict()
    table['ttt'] = 0.05
    table['ttf'] = 0.95
    table['tft'] = 0.02
    table['tff'] = 0.98
    table['ftt'] = 0.03
    table['ftf'] = 0.97
    table['fft'] = 0.001
    table['fff'] = 0.999
    key = ''
    key = key + 't' if P == 'high' else key + 'f'
    key = key + 't' if S else key + 'f'
    key = key + 't' if C else key + 'f'
    return table[key]


def fX(C, X):
    '''X-ray'''
    table = dict()
    table['tt'] = 0.9
    table['tf'] = 0.1
    table['ft'] = 0.2
    table['ff'] = 0.8
    key = ''
    key = key + 't' if C else key + 'f'
    key = key + 't' if X else key + 'f'
    return table[key]


def fD(C, D):
    '''Dyspnoeia'''
    table = dict()
    table['tt'] = 0.65
    table['tf'] = 0.35
    table['ft'] = 0.3
    table['ff'] = 0.7
    key = ''
    key = key + 't' if C else key + 'f'
    key = key + 't' if D else key + 'f'
    return table[key]


if __name__ == '__main__':
    g = build_graph(
        fP, fS, fC, fX, fD,
        domains={
            'P': ['low', 'high']})
    g.q()
    g.q(P='high')
    g.q(D=True)
    g.q(S=True)
    g.q(C=True, S=True)
    g.q(D=True, S=True)

########NEW FILE########
__FILENAME__ = earthquake
'''This is the earthquake example from 2.5.1 in BAI'''
from bayesian.factor_graph import *


def f_burglary(burglary):
    if burglary is True:
        return 0.01
    return 0.99


def f_earthquake(earthquake):
    if earthquake is True:
        return 0.02
    return 0.98


def f_alarm(burglary, earthquake, alarm):
    table = dict()
    table['ttt'] = 0.95
    table['ttf'] = 0.05
    table['tft'] = 0.94
    table['tff'] = 0.06
    table['ftt'] = 0.29
    table['ftf'] = 0.71
    table['fft'] = 0.001
    table['fff'] = 0.999
    key = ''
    key = key + 't' if burglary else key + 'f'
    key = key + 't' if earthquake else key + 'f'
    key = key + 't' if alarm else key + 'f'
    return table[key]


def f_johncalls(alarm, johncalls):
    table = dict()
    table['tt'] = 0.9
    table['tf'] = 0.1
    table['ft'] = 0.05
    table['ff'] = 0.95
    key = ''
    key = key + 't' if alarm else key + 'f'
    key = key + 't' if johncalls else key + 'f'
    return table[key]


def f_marycalls(alarm, marycalls):
    table = dict()
    table['tt'] = 0.7
    table['tf'] = 0.3
    table['ft'] = 0.01
    table['ff'] = 0.99
    key = ''
    key = key + 't' if alarm else key + 'f'
    key = key + 't' if marycalls else key + 'f'
    return table[key]


if __name__ == '__main__':
    g = build_graph(
        f_burglary,
        f_earthquake,
        f_alarm,
        f_johncalls,
        f_marycalls)
    g.q()

########NEW FILE########
__FILENAME__ = huang_darwiche
'''The Example from Huang and Darwiche's Procedural Guide'''
from __future__ import division
from bayesian.factor_graph import *
from bayesian.utils import make_key


def f_a(a):
    return 1 / 2


def f_b(a, b):
    tt = dict(
        tt=0.5,
        ft=0.4,
        tf=0.5,
        ff=0.6)
    return tt[make_key(a, b)]


def f_c(a, c):
    tt = dict(
        tt=0.7,
        ft=0.2,
        tf=0.3,
        ff=0.8)
    return tt[make_key(a, c)]


def f_d(b, d):
    tt = dict(
        tt=0.9,
        ft=0.5,
        tf=0.1,
        ff=0.5)
    return tt[make_key(b, d)]


def f_e(c, e):
    tt = dict(
        tt=0.3,
        ft=0.6,
        tf=0.7,
        ff=0.4)
    return tt[make_key(c, e)]


def f_f(d, e, f):
    tt = dict(
        ttt=0.01,
        ttf=0.99,
        tft=0.01,
        tff=0.99,
        ftt=0.01,
        ftf=0.99,
        fft=0.99,
        fff=0.01)
    return tt[make_key(d, e, f)]


def f_g(c, g):
    tt = dict(
        tt=0.8, tf=0.2,
        ft=0.1, ff=0.9)
    return tt[make_key(c, g)]


def f_h(e, g, h):
    tt = dict(
        ttt=0.05, ttf=0.95,
        tft=0.95, tff=0.05,
        ftt=0.95, ftf=0.05,
        fft=0.95, fff=0.05)
    return tt[make_key(e, g, h)]


if __name__ == '__main__':
    g = build_graph(
        f_a, f_b, f_c, f_d,
        f_e, f_f, f_g, f_h)
    g.n_samples = 1000
    g.q()

########NEW FILE########
__FILENAME__ = monty_hall
'''The Monty Hall Problem Modelled as a Bayesian Belief Network'''
from bayesian.factor_graph import *

'''
As BBN:


         GuestDoor     ActualDoor
               \         /
                MontyDoor
                p(M|G,A)


As Factor Graph:

        fGuestDoor               fActualDoor
             |                        |
         GuestDoor                ActualDoor
             |                        |
             +------fMontyDoor--------+
                         |
                     MontyDoor

Now Query: Given Guest chooses door A
and Monty chooses door B, should guest
switch to C or stay with A?

'''


def f_prize_door(prize_door):
    return 1.0 / 3


def f_guest_door(guest_door):
    return 1.0 / 3


def f_monty_door(prize_door, guest_door, monty_door):
    if prize_door == guest_door:
        if prize_door == monty_door:
            return 0
        else:
            return 0.5
    elif prize_door == monty_door:
        return 0
    elif guest_door == monty_door:
        return 0
    return 1


if __name__ == '__main__':

    g = build_graph(
        f_prize_door,
        f_guest_door,
        f_monty_door,
        domains=dict(
            prize_door=['A', 'B', 'C'],
            guest_door=['A', 'B', 'C'],
            monty_door=['A', 'B', 'C']))
    # Initial Marginals without any knowledge.
    # Observe that the likelihood for
    # all three doors is 1/3.
    print 'Initial Marginal Probabilities:'
    g.q()
    # Now suppose the guest chooses
    # door A and Monty chooses door B.
    # Should we switch our choice from
    # A to C or not?
    # To answer this we "query" the
    # graph with instantiation of the
    # observed variables as "evidence".
    # The likelihood for door C has
    # indeed increased to 2/3 therefore
    # we should switch to door C.
    print 'Marginals after knowing Guest chose A and Monty chose B.'
    g.q(guest_door='A', monty_door='B')

########NEW FILE########
__FILENAME__ = monty_hall_sampled
'''The Monty Hall Problem Modelled as a Bayesian Belief Network'''
from bayesian.factor_graph import *

'''
As BBN:


         GuestDoor     ActualDoor
               \         /
                MontyDoor
                p(M|G,A)


As Factor Graph:

        fGuestDoor               fActualDoor
             |                        |
         GuestDoor                ActualDoor
             |                        |
             +------fMontyDoor--------+
                         |
                     MontyDoor

Now Query: Given Guest chooses door A
and Monty chooses door B, should guest
switch to C or stay with A?

'''


def f_prize_door(prize_door):
    return 1.0 / 3


def f_guest_door(guest_door):
    return 1.0 / 3


def f_monty_door(prize_door, guest_door, monty_door):
    if prize_door == guest_door:
        if prize_door == monty_door:
            return 0
        else:
            return 0.5
    elif prize_door == monty_door:
        return 0
    elif guest_door == monty_door:
        return 0
    return 1


if __name__ == '__main__':

    g = build_graph(
        f_prize_door,
        f_guest_door,
        f_monty_door,
        domains=dict(
            prize_door=['A', 'B', 'C'],
            guest_door=['A', 'B', 'C'],
            monty_door=['A', 'B', 'C']),
        name='Monty_Hall')
    g.inference_method = 'sample_db'

    # Initial Marginals without any knowledge.
    # Observe that the likelihood for
    # all three doors is 1/3.
    #print 'Initial Marginal Probabilities:'
    #g.q()
    # Now suppose the guest chooses
    # door A and Monty chooses door B.
    # Should we switch our choice from
    # A to C or not?
    # To answer this we "query" the
    # graph with instantiation of the
    # observed variables as "evidence".
    # The likelihood for door C has
    # indeed increased to 2/3 therefore
    # we should switch to door C.
    #print 'Marginals after knowing Guest chose A and Monty chose B.'
    #g.q(guest_door='A', monty_door='B')

########NEW FILE########
__FILENAME__ = walk
from __future__ import division
'''Simple Example Containing A Cycle'''

from bayesian.factor_graph import *


'''

                          Rain Forecast
                              |
                 +------------+
                 |            |
               Rain           |
                 |            |
                 +---------+  |
                           |  |
                           Walk


Our decision to go for a walk is based on two factors,
the forecast for rain and on actual rain observed.

'''


def little_bool(var):
    return str(var).lower()[0]


def f_forecast(forecast):
    if forecast is True:
        return 0.6
    return 0.4


def f_rain(forecast, rain):
    table = dict()
    table['tt'] = 0.95
    table['tf'] = 0.05
    table['ft'] = 0.1
    table['ff'] = 0.9
    key = ''
    key = key + little_bool(forecast)
    key = key + little_bool(rain)
    return table[key]


def f_walk(forecast, rain, walk):
    table = dict()
    table['fff'] = 0.01
    table['fft'] = 0.99
    table['ftf'] = 0.99
    table['ftt'] = 0.01
    table['tff'] = 0.8
    table['tft'] = 0.2
    table['ttf'] = 0.999
    table['ttt'] = 0.001
    key = ''
    key = key + little_bool(forecast)
    key = key + little_bool(rain)
    key = key + little_bool(walk)
    return table[key]


forecast = VariableNode('forecast')
rain = VariableNode('rain')
walk = VariableNode('walk')

f_forecast_node = FactorNode('f_forecast', f_forecast)
f_rain_node = FactorNode('f_rain', f_rain)
f_walk_node = FactorNode('f_walk', f_walk)


connect(f_forecast_node, forecast)
connect(f_rain_node, [forecast, rain])
connect(f_walk_node, [forecast, rain, walk])

graph = FactorGraph([
                    forecast,
                    rain,
                    walk,
                    f_forecast_node,
                    f_rain_node,
                    f_walk_node])


def tabulate(counts, normalizer):
    table = PrettyTable(['Variable', 'Value', 'p'])
    table.align = 'l'
    deco = [(k, v) for k, v in counts.items()]
    deco.sort()
    for k, v in deco:
        if k[1] is not False:
            table.add_row(list(k) + [v / normalizer])
    print table


if __name__ == '__main__':
    graph.verify()
    print graph.get_sample()

    n = 10000
    counts = defaultdict(int)
    for i in range(0, n):
        table = PrettyTable(['Variable', 'Value'])
        table.align = 'l'
        sample = graph.get_sample()
        for var in sample:
            key = (var.name, var)
            counts[key] += 1

    from pprint import pprint
    pprint(counts)
    print 'Sampled:'
    tabulate(counts, n)

########NEW FILE########
__FILENAME__ = koller
'''This example is from Koller & Friedman example 7.3 page 252'''
from bayesian.gaussian_bayesian_network import *

'''
This is a simple example with 3 variables:

         +----+    +----+    +----+
         | X1 |--->| X2 |--->| X3 |
         +----+    +----+    +----+

With parameters:

p(X1) ~ N(1; 4)
p(X2|X1) ~ N(0.5X1 - 3.5; 4)
p(X3|X2) ~ N(-X2 + 1; 3)

Remember that in our gaussian decorators
we are using Standard Deviation while the
Koller example uses Variance.

'''


@gaussian(1, 2)
def f_x1(x1):
    pass


@conditional_gaussian(-3.5, 2, 0.5)
def f_x2(x1, x2):
    pass


@conditional_gaussian(1, 3 ** 0.5, -1)
def f_x3(x2, x3):
    pass


if __name__ == '__main__':
    g = build_graph(f_x1, f_x2, f_x3)
    g.q()

########NEW FILE########
__FILENAME__ = river
from __future__ import division
'''Simple Example Using Gaussian Variables'''
from bayesian.gaussian_bayesian_network import gaussian, conditional_gaussian
from bayesian.gaussian_bayesian_network import build_graph
from bayesian.utils import shrink_matrix

'''
This example comes from page 3 of
http://people.cs.aau.dk/~uk/papers/castillo-kjaerulff-03.pdf

Note that to create a Guassian Node
we supply mean and standard deviation,
this differs from the example in the
above paper which uses variance (=std. dev.) ** 2

Note in the paper they specify variance,
wheres as this example we are  using std. dev.
instead hence for A the variance is 4 and std_dev is 2.
'''


@gaussian(3, 2)
def f_a(a):
    '''represents point A in the river system'''
    pass


@conditional_gaussian(1, 1, 1)
def f_b(a, b):
    '''Point b is a conditional Guassian
    with parent a.
    '''
    pass


@conditional_gaussian(3, 2, 2)
def f_c(a, c):
    '''Point c is a conditional Guassian
    with parent a'''
    pass


@conditional_gaussian(1, 1, betas=dict(b=1, c=1))
def f_d(b, c, d):
    pass


if __name__ == '__main__':

    g = build_graph(
        f_a,
        f_b,
        f_c,
        f_d)
    g.q()

########NEW FILE########
__FILENAME__ = exceptions
class InvalidGraphException(Exception):
    '''
    Raised if the graph verification
    method fails.
    '''
    pass


class InvalidSampleException(Exception):
    '''Should be raised if a
    sample is invalid.'''
    pass


class InvalidInferenceMethod(Exception):
    '''Raise if the user tries to set
    the inference method to an unknown string.'''
    pass


class InsufficientSamplesException(Exception):
    '''Raised when the inference method
    is 'sample_db' and there are less
    pre-generated samples than the
    graphs n_samples attribute.'''
    pass


class NoSamplesInDB(Warning):
    pass


class VariableNotInGraphError(Exception):
    """Exception raised when
    a graph is queried with
    a variable that is not part of
    the graph.
    """
    pass


class IncorrectInferenceMethodError(Exception):
    '''Raise when attempt is made to
    generate samples when the inference
    method is not 'sample_db'
    '''
    pass

########NEW FILE########
__FILENAME__ = factor_graph
from __future__ import division
'''Implements Sum-Product Algorithm and Sampling over Factor Graphs'''
import os
import csv
import sys
import copy
import inspect
import random

from collections import defaultdict
from itertools import product as iter_product
from Queue import Queue

import sqlite3
from prettytable import PrettyTable

from bayesian.persistance import SampleDB, ensure_data_dir_exists
from bayesian.exceptions import *
from bayesian.utils import get_args

DEBUG = False
GREEN = '\033[92m'
NORMAL = '\033[0m'

class Node(object):

    def is_leaf(self):
        if len(self.neighbours) == 1:
            return True
        return False

    def send(self, message):
        recipient = message.destination
        if DEBUG:
            print '%s ---> %s' % (
                self.name, recipient.name), message
        recipient.received_messages[
            self.name] = message

    def get_sent_messages(self):
        sent_messages = {}
        for neighbour in self.neighbours:
            if neighbour.received_messages.get(self.name):
                sent_messages[neighbour.name] = \
                    neighbour.received_messages.get(self.name)
        return sent_messages

    def message_report(self):
        '''
        List out all messages Node
        currently has received.
        '''
        print '------------------------------'
        print 'Messages at Node %s' % self.name
        print '------------------------------'
        for k, v in self.received_messages.iteritems():
            print '%s <-- Argspec:%s' % (v.source.name, v.argspec)
            v.list_factors()
        print '--'

    def get_target(self):
        '''
        A node can only send to a neighbour if
        it has not already sent to that neighbour
        and it has received messages from all other
        neighbours.
        '''
        neighbours = self.neighbours
        #if len(neighbours) - len(self.received_messages) > 1:
        #    return None
        needed_to_send = defaultdict(int)
        for target in neighbours:
            needed_to_send[target] = len(neighbours) - 1
        for _, message in self.received_messages.items():
            for target in neighbours:
                if message.source != target:
                    needed_to_send[target] -= 1
        for k, v in needed_to_send.items():
            if v == 0 and not self.name in k.received_messages:
                return k

    def get_neighbour_by_name(self, name):
        for node in self.neighbours:
            if node.name == name:
                return node


class VariableNode(Node):

    def __init__(self, name, domain=[True, False]):
        self.name = name
        self.domain = domain
        self.neighbours = []
        self.received_messages = {}
        self.value = None

    def construct_message(self):
        target = self.get_target()
        message = make_variable_node_message(self, target)
        return message

    def __repr__(self):
        return '<VariableNode: %s:%s>' % (self.name, self.value)

    def marginal(self, val, normalizer=1.0):
        '''
        The marginal function in a Variable
        Node is the product of all incoming
        messages. These should all be functions
        of this nodes variable.
        When any of the variables in the
        network are constrained we need to
        normalize.
        '''
        product = 1
        for _, message in self.received_messages.iteritems():
            product *= message(val)
        return product / normalizer

    def reset(self):
        self.received_messages = {}
        self.value = None

    def verify_neighbour_types(self):
        '''
        Check that all neighbours are of VariableNode type.
        '''
        for node in self.neighbours:
            if not isinstance(node, FactorNode):
                return False
        return True


class FactorNode(Node):

    def __init__(self, name, func, neighbours=[]):
        self.name = name
        self.func = func
        self.neighbours = neighbours[:]
        self.received_messages = {}
        self.func.value = None
        self.cached_functions = []

    def construct_message(self):
        target = self.get_target()
        message = make_factor_node_message(self, target)
        return message

    def verify_neighbour_types(self):
        '''
        Check that all neighbours are of VariableNode type.
        '''
        for node in self.neighbours:
            if not isinstance(node, VariableNode):
                return False
        return True

    def __repr__(self):
        return '<FactorNode %s %s(%s)>' % \
            (self.name,
             self.func.__name__,
             get_args(self.func))

    def marginal(self, val_dict):
        # The Joint marginal of the
        # neighbour variables of a factor
        # node is given by the product
        # of the incoming messages and the factor
        product = 1
        neighbours = self.neighbours
        for neighbour in neighbours:
            message = self.received_messages[neighbour.name]
            call_args = []
            for arg in get_args(message):
                call_args.append(val_dict[arg])
            if not call_args:
                call_args.append('dummy')
            product *= message(*call_args)
        # Finally we also need to multiply
        # by the factor itself
        call_args = []
        for arg in get_args(self.func):
            call_args.append(val_dict[arg])
        if not call_args:
            call_args.append('dummy')
        product *= self.func(*call_args)
        return product

    def add_evidence(self, node, value):
        '''
        Here we modify the factor function
        to return 0 whenever it is called
        with the observed variable having
        a value other than the observed value.
        '''
        args = get_args(self.func)
        pos = args.index(node.name)
        # Save the old func so that we
        # can remove the evidence later
        old_func = self.func
        self.cached_functions.insert(0, old_func)

        def evidence_func(*args):
            if args[pos] != value:
                return 0
            return old_func(*args)

        evidence_func.argspec = args
        evidence_func.domains = old_func.domains
        self.func = evidence_func

    def reset(self):
        self.received_messages = {}
        if self.cached_functions:
            self.func = self.cached_functions[-1]
            self.cached_functions = []


class Message(object):

    def list_factors(self):
        print '---------------------------'
        print 'Factors in message %s -> %s' % \
            (self.source.name, self.destination.name)
        print '---------------------------'
        for factor in self.factors:
            print factor

    def __call__(self, var):
        '''
        Evaluate the message as a function
        '''
        if getattr(self.func, '__name__', None) == 'unity':
            return 1
        assert not isinstance(var, VariableNode)
        # Now check that the name of the
        # variable matches the argspec...
        #assert var.name == self.argspec[0]
        return self.func(var)


class VariableMessage(Message):

    def __init__(self, source, destination, factors, func):
        self.source = source
        self.destination = destination
        self.factors = factors
        self.argspec = get_args(func)
        self.func = func

    def __repr__(self):
        return '<V-Message from %s -> %s: %s factors (%s)>' % \
            (self.source.name, self.destination.name,
             len(self.factors), self.argspec)


class FactorMessage(Message):

    def __init__(self, source, destination, factors, func):
        self.source = source
        self.destination = destination
        self.factors = factors
        self.func = func
        self.argspec = get_args(func)
        self.domains = func.domains

    def __repr__(self):
        return '<F-Message %s -> %s: ~(%s) %s factors.>' % \
            (self.source.name, self.destination.name,
             self.argspec,
             len(self.factors))


def connect(a, b):
    '''
    Make an edge between two nodes
    or between a source and several
    neighbours.
    '''
    if not isinstance(b, list):
        b = [b]
    for b_ in b:
        a.neighbours.append(b_)
        b_.neighbours.append(a)



def eliminate_var(f, var):
    '''
    Given a function f return a new
    function which sums over the variable
    we want to eliminate

    This may be where we have the opportunity
    to remove the use of .value....

    '''
    arg_spec = get_args(f)
    pos = arg_spec.index(var)
    new_spec = arg_spec[:]
    new_spec.remove(var)
    # Lets say the orginal argspec is
    # ('a', 'b', 'c', 'd') and they
    # are all Booleans
    # Now lets say we want to eliminate c
    # This means we want to sum over
    # f(a, b, True, d) and f(a, b, False, d)
    # Seems like all we have to do is know
    # the positionn of c and thats it???
    # Ok so its not as simple as that...
    # this is because when the *call* is made
    # to the eliminated function, as opposed
    # to when its built then its only
    # called with ('a', 'b', 'd')
    eliminated_pos = arg_spec.index(var)

    def eliminated(*args):
        template = arg_spec[:]
        total = 0
        call_args = template[:]
        i = 0
        for arg in args:
            # To be able to remove .value we
            # first need to also be able to
            # remove .name in fact .value is
            # just a side effect of having to
            # rely on .name. This means we
            # probably need to construct a
            # a list containing the names
            # of the args based on the position
            # they are being called.
            if i == eliminated_pos:
                # We need to increment i
                # once more to skip over
                # the variable being marginalized
                call_args[i] = 'marginalize me!'
                i += 1
            call_args[i] = arg
            i += 1

        for val in f.domains[var]:
            #v = VariableNode(name=var)
            #v.value = val
            #call_args[pos] = v
            call_args[pos] = val
            total += f(*call_args)
        return total

    eliminated.argspec = new_spec
    eliminated.domains = f.domains
    #eliminated.__name__ = f.__name__
    return eliminated


def memoize(f):
    '''
    The goal of message passing
    is to re-use results. This
    memoise is slightly modified from
    usual examples in that it caches
    the values of variables rather than
    the variables themselves.
    '''
    cache = {}

    def memoized(*args):
        #arg_vals = tuple([arg.value for arg in args])
        arg_vals = tuple(args)
        if not arg_vals in cache:
            cache[arg_vals] = f(*args)
        return cache[arg_vals]

    if hasattr(f, 'domains'):
        memoized.domains = f.domains
    if hasattr(f, 'argspec'):
        memoized.argspec = f.argspec
    return memoized


def make_not_sum_func(product_func, keep_var):
    '''
    Given a function with some set of
    arguments, and a single argument to keep,
    construct a new function only of the
    keep_var, summarized over all the other
    variables.

    For this branch we are trying to
    get rid of the requirement to have
    to use .value on arguments....
    Looks like its actually in the
    eliminate var...
    '''
    args = get_args(product_func)
    new_func = copy.deepcopy(product_func)
    for arg in args:
        if arg != keep_var:
            new_func = eliminate_var(new_func, arg)
            new_func = memoize(new_func)
    return new_func


def make_factor_node_message(node, target_node):
    '''
    The rules for a factor node are:
    take the product of all the incoming
    messages (except for the destination
    node) and then take the sum over
    all the variables except for the
    destination variable.
    >>> def f(x1, x2, x3): pass
    >>> node = object()
    >>> node.func = f
    >>> target_node = object()
    >>> target_node.name = 'x2'
    >>> make_factor_node_message(node, target_node)
    '''

    if node.is_leaf():
        not_sum_func = make_not_sum_func(node.func, target_node.name)
        message = FactorMessage(node, target_node, [node.func], not_sum_func)
        return message

    args = set(get_args(node.func))

    # Compile list of factors for message
    factors = [node.func]

    # Now add the message that came from each
    # of the non-destination neighbours...
    neighbours = node.neighbours
    for neighbour in neighbours:
        if neighbour == target_node:
            continue
        # When we pass on a message, we unwrap
        # the original payload and wrap it
        # in new headers, this is purely
        # to verify the procedure is correct
        # according to usual nomenclature
        in_message = node.received_messages[neighbour.name]
        if in_message.destination != node:
            out_message = VariableMessage(
                neighbour, node, in_message.factors,
                in_message.func)
            out_message.argspec = in_message.argspec
        else:
            out_message = in_message
        factors.append(out_message)

    product_func = make_product_func(factors)
    not_sum_func = make_not_sum_func(product_func, target_node.name)
    message = FactorMessage(node, target_node, factors, not_sum_func)
    return message


def make_variable_node_message(node, target_node):
    '''
    To construct the message from
    a variable node to a factor
    node we take the product of
    all messages received from
    neighbours except for any
    message received from the target.
    If the source node is a leaf node
    then send the unity function.
    '''
    if node.is_leaf():
        message = VariableMessage(
            node, target_node, [1], unity)
        return message
    factors = []
    neighbours = node.neighbours
    for neighbour in neighbours:
        if neighbour == target_node:
            continue
        factors.append(
            node.received_messages[neighbour.name])

    product_func = make_product_func(factors)
    message = VariableMessage(
        node, target_node, factors, product_func)
    return message


def make_product_func(factors):
    '''
    Return a single callable from
    a list of factors which correctly
    applies the arguments to each
    individual factor.

    The challenge here is to return a function
    whose argument list we know and ensure that
    when this function is called, its always
    called with the correct arguments.
    Since the correct argspec is attached
    to the built function it seems that
    it should be up to the caller to
    get the argument list correct.
    So we need to determine when and where its called...

    '''
    args_map = {}
    all_args = []
    domains = {}
    for factor in factors:
        #if factor == 1:
        #    continue
        args_map[factor] = get_args(factor)
        all_args += args_map[factor]
        if hasattr(factor, 'domains'):
            domains.update(factor.domains)
    args = list(set(all_args))
    # Perhaps if we sort the


    def product_func(*product_func_args):
        #import pytest; pytest.set_trace()
        #arg_dict = dict([(a.name, a) for a in product_func_args])
        arg_dict = dict(zip(args, product_func_args))
        #import pytest; pytest.set_trace()
        result = 1
        for factor in factors:
            #domains.update(factor.domains)
            # We need to build the correct argument
            # list to call this factor with.
            factor_args = []
            for arg in get_args(factor):
                if arg in arg_dict:
                    factor_args.append(arg_dict[arg])
            if not factor_args:
                # Since we always require
                # at least one argument we
                # insert a dummy argument
                # so that the unity function works.
                factor_args.append('dummy')
            result *= factor(*factor_args)

        return result

    product_func.argspec = args
    product_func.factors = factors
    product_func.domains = domains
    return memoize(product_func)


def make_unity(argspec):
    def unity(x):
        return 1
    unity.argspec = argspec
    unity.__name__ = '1'
    return unity


def unity():
    return 1


def expand_args(args):
    if not args:
        return []
    return


def dict_to_tuples(d):
    '''
    Convert a dict whose values
    are lists to a list of
    tuples of the key with
    each of the values
    '''
    retval = []
    for k, vals in d.iteritems():
        retval.append([(k, v) for v in vals])
    return retval


def expand_parameters(arg_vals):
    '''
    Given a list of args and values
    return a list of tuples
    containing all possible sequences
    of length n.
    '''
    arg_tuples = dict_to_tuples(arg_vals)
    return [dict(args) for args in iter_product(*arg_tuples)]


def add_evidence(node, value):
    '''
    Set a variable node to an observed value.
    Note that for now this is achieved
    by modifying the factor functions
    which this node is connected to.
    After updating the factor nodes
    we need to re-run the sum-product
    algorithm. We also need to normalize
    all marginal outcomes.
    '''
    node.value = value
    neighbours = node.neighbours
    for factor_node in neighbours:
        if node.name in get_args(factor_node.func):
            factor_node.add_evidence(node, value)


def discover_sample_ordering(graph):
    '''
    Try to get the order of variable nodes
    for sampling. This would be easier in
    the underlying BBN but lets try on
    the factor graph.
    '''
    iterations = 0
    ordering = []
    pmf_ordering = []
    accounted_for = set()
    variable_nodes = [n for n in graph.nodes if isinstance(n, VariableNode)]
    factor_nodes = [n for n in graph.nodes if isinstance(n, FactorNode)]
    required = len([n for n in graph.nodes if isinstance(n, VariableNode)])
    # Firstly any leaf factor nodes will
    # by definition only have one variable
    # node connection, therefore these
    # variables can be set first.
    for node in graph.get_leaves():
        if isinstance(node, FactorNode):
            ordering.append(node.neighbours[0])
            accounted_for.add(node.neighbours[0].name)
            pmf_ordering.append(node.func)

    # Now for each factor node whose variables
    # all but one are already in the ordering,
    # we can add that one variable. This is
    # actuall
    while len(ordering) < required:
        for node in factor_nodes:
            args = set(get_args(node.func))
            new_args = args.difference(accounted_for)
            if len(new_args) == 1:
                arg_name = list(new_args)[0]
                var_node = node.get_neighbour_by_name(arg_name)
                ordering.append(var_node)
                accounted_for.add(var_node.name)
                pmf_ordering.append(node.func)
    return zip(ordering, pmf_ordering)


def get_sample(ordering, evidence={}):
    '''
    Given a valid ordering, sample the network.
    '''
    sample = []
    sample_dict = dict()
    for var, func in ordering:
        r = random.random()
        total = 0
        for val in var.domain:
            test_var = VariableNode(var.name)
            test_var.value = val
            # Now we need to build the
            # argument list out of any
            # variables already in the sample
            # and this new test value in
            # the order required by the function.
            args = []
            for arg in get_args(func):
                if arg == var.name:
                    #args.append(test_var)
                    args.append(val)
                else:
                    args.append(sample_dict[arg].value)

            total += func(*args)
            if total > r:
                # We only want to use this sample
                # if it corresponds to the evidence value...
                if var.name in evidence:
                    if test_var.value == evidence[var.name]:
                        sample.append(test_var)
                        sample_dict[var.name] = test_var
                else:
                    sample.append(test_var)
                    sample_dict[var.name] = test_var
                break
        if not var.name in sample_dict:
            print 'Iterated through all values for %s and %s but no go...' \
                % (var.name, func.__name__)
            # This seems to mean that we have never seen this combination
            # of variables before, we can either discard it as irrelevant or
            # use some type of +1 smoothing???
            # What if we just randomly select some value for var????
            # lets try that as it seems the easiest....
            raise InvalidSampleException
    return sample


class FactorGraph(object):

    def __init__(self, nodes, name=None, n_samples=100):
        self.nodes = nodes
        self._inference_method = 'sumproduct'
        # We need to divine the domains for Factor nodes here...
        # First compile a mapping of factors to variables
        # from the arg spec...
        function_args = dict()
        arg_domains = dict()
        for node in self.nodes:
            if isinstance(node, VariableNode):
                #if not hasattr(node, 'domain'):
                #    node.domain = [True, False]
                arg_domains[node.name] = node.domain
            elif isinstance(node, FactorNode):
                function_args[node.func.__name__] = get_args(node.func)
        # Now if the domains for the
        # factor functions have not been explicitely
        # set we create them based on the variable
        # values it can take.
        for node in self.nodes:
            if isinstance(node, FactorNode):
                if hasattr(node.func, 'domains'):
                    continue
                domains = dict()
                for arg in get_args(node.func):
                    if not arg in arg_domains:
                        print 'WARNING: missing variable for arg:%s' % arg
                    else:
                        domains.update({arg: arg_domains[arg]})
                node.func.domains = domains
        self.name = name
        self.n_samples = n_samples
        # Now try to set the mode of inference..
        try:
            if self.has_cycles():
                # Currently only sampling
                # is supported for cyclic graphs
                self.inference_method = 'sample'
            else:
                # The sumproduct method will
                # give exact likelihoods but
                # only of the graph contains
                # no cycles.
                self.inference_method = 'sumproduct'
        except:
            print 'Failed to determine if graph has cycles, '
            'setting inference to sample.'
            self.inference_method = 'sample'
        self.enforce_minimum_samples = False

    @property
    def inference_method(self):
        return self._inference_method

    @inference_method.setter
    def inference_method(self, value):
        # If the value is being set to 'sample_db'
        # we need to make sure that the sqlite file
        # exists.
        if value == 'sample_db':
            ensure_data_dir_exists(self.sample_db_filename)
            sample_ordering = self.discover_sample_ordering()
            domains = dict([(var, var.domain) for var, _ in sample_ordering])
            if not os.path.isfile(self.sample_db_filename):
                # This is a new file so we need to
                # initialize the db...
                self.sample_db = SampleDB(
                    self.sample_db_filename,
                    domains,
                    initialize=True)
            else:
                self.sample_db = SampleDB(
                    self.sample_db_filename,
                    domains,
                    initialize=False)
        self._inference_method = value

    @property
    def sample_db_filename(self):
        '''
        Get the name of the sqlite sample
        database for external sample
        generation and querying.
        The default location for now
        will be in the users home
        directory under ~/.pypgm/data/[name].sqlite
        where [name] is the name of the
        model. If the model has
        not been given an explict name
        it will be "default".

        '''
        home = os.path.expanduser('~')
        return os.path.join(
            home, '.pypgm',
            'data',
            '%s.sqlite' % (self.name or 'default'))

    def reset(self):
        '''
        Reset all nodes back to their initial state.
        We should do this before or after adding
        or removing evidence.
        '''
        for node in self.nodes:
            node.reset()

    def has_cycles(self):
        '''
        Check if the graph has cycles or not.
        We will do this by traversing starting
        from any leaf node and recording
        both the edges traversed and the nodes
        discovered. From stackoverflow, if
        an unexplored edge leads to a
        previously found node then it has
        cycles.
        '''
        discovered_nodes = set()
        traversed_edges = set()
        q = Queue()
        for node in self.nodes:
            if node.is_leaf():
                start_node = node
                break
        q.put(start_node)
        while not q.empty():
            current_node = q.get()
            if DEBUG:
                print "Current Node: ", current_node
                print "Discovered Nodes before adding Current Node: ", \
                    discovered_nodes
            if current_node.name in discovered_nodes:
                # We have a cycle!
                if DEBUG:
                    print 'Dequeued node already processed: %s', current_node
                return True
            discovered_nodes.add(current_node.name)
            if DEBUG:
                print "Discovered Nodes after adding Current Node: ", \
                    discovered_nodes
            for neighbour in current_node.neighbours:
                edge = [current_node.name, neighbour.name]
                # Since this is undirected and we want
                # to record the edges we have traversed
                # we will sort the edge alphabetically
                edge.sort()
                edge = tuple(edge)
                if edge not in traversed_edges:
                    # This is a new edge...
                    if neighbour.name in discovered_nodes:
                        return True
                # Now place all neighbour nodes on the q
                # and record this edge as traversed
                if neighbour.name not in discovered_nodes:
                    if DEBUG:
                        print 'Enqueuing: %s' % neighbour
                    q.put(neighbour)
                traversed_edges.add(edge)
        return False

    def verify(self):
        '''
        Check several properties of the Factor Graph
        that should hold.
        '''
        # Check that all nodes are either
        # instances of classes derived from
        # VariableNode or FactorNode.
        # It is a very common error to instantiate
        # the graph with the factor function
        # instead of the corresponding factor
        # node.
        for node in self.nodes:
            if not isinstance(node, VariableNode) and \
                    not isinstance(node, FactorNode):
                bases = node.__class__.__bases__
                if not VariableNode in bases and not FactorNode in bases:
                    print ('Factor Graph does not '
                           'support nodes of type: %s' % node.__class__)
                    raise InvalidGraphException
        # First check that for each node
        # only connects to nodes of the
        # other type.
        print 'Checking neighbour node types...'
        for node in self.nodes:
            if not node.verify_neighbour_types():
                print '%s has invalid neighbour type.' % node
                return False
        print 'Checking that all factor functions have domains...'
        for node in self.nodes:
            if isinstance(node, FactorNode):
                if not hasattr(node.func, 'domains'):
                    print '%s has no domains.' % node
                    raise InvalidGraphException
                elif not node.func.domains:
                    # Also check for an empty domain dict!
                    print '%s has empty domains.' % node
                    raise InvalidGraphException
        print 'Checking that all variables are accounted for' + \
            ' by at least one function...'
        variables = set([vn.name for vn in self.nodes
                         if isinstance(vn, VariableNode)])

        largs = [get_args(fn.func) for fn in
                 self.nodes if isinstance(fn, FactorNode)]

        args = set(reduce(lambda x, y: x + y, largs))

        if not variables.issubset(args):
            print 'These variables are not used in any factors nodes: '
            print variables.difference(args)
            return False
        print 'Checking that all arguments have matching variable nodes...'
        if not args.issubset(variables):
            print 'These arguments have missing variables:'
            print args.difference(variables)
            return False
        print 'Checking that graph has at least one leaf node...'
        leaf_nodes = filter(
            lambda x: x.is_leaf(),
            self.nodes)
        if not leaf_nodes:
            print 'Graph has no leaf nodes.'
            raise InvalidGraphException
        return True

    def get_leaves(self):
        return [node for node in self.nodes if node.is_leaf()]

    def get_eligible_senders(self):
        '''
        Return a list of nodes that are
        eligible to send messages at this
        round. Only nodes that have received
        messages from all but one neighbour
        may send at any round.
        '''
        eligible = []
        for node in self.nodes:
            if node.get_target():
                eligible.append(node)
        return eligible

    def propagate(self):
        '''
        This is the heart of the sum-product
        Message Passing Algorithm.
        '''
        step = 1
        while True:
            eligible_senders = self.get_eligible_senders()
            #print 'Step: %s %s nodes can send.' \
            # % (step, len(eligible_senders))
            #print [x.name for x in eligible_senders]
            if not eligible_senders:
                break
            for node in eligible_senders:
                message = node.construct_message()
                node.send(message)
            step += 1

    def variable_nodes(self):
        return [n for n in self.nodes if isinstance(n, VariableNode)]

    def factor_nodes(self):
        return [n for n in self.nodes if isinstance(n, FactorNode)]

    def get_normalizer(self):
        for node in self.variable_nodes():
            if node.value is not None:
                normalizer = node.marginal(node.value)
                return normalizer
        return 1

    def status(self, omit=[False, 0]):
        normalizer = self.get_normalizer()
        retval = dict()
        for node in self.variable_nodes():
            for value in node.domain:
                m = node.marginal(value, normalizer)
                retval[(node.name, value)] = m
        return retval

    def query_by_propagation(self, **kwds):
        self.reset()
        for k, v in kwds.items():
            for node in self.variable_nodes():
                if node.name == k:
                    add_evidence(node, v)
        self.propagate()
        return self.status()

    def query(self, **kwds):
        if self.inference_method == 'sample_db':
            return self.query_by_external_samples(**kwds)
        elif self.inference_method == 'sample':
            return self.query_by_sampling(**kwds)
        elif self.inference_method == 'sumproduct':
            return self.query_by_propagation(**kwds)
        raise InvalidInferenceMethod

    def q(self, **kwds):
        '''Wrapper around query

        This method formats the query
        result in a nice human readable format
        for interactive use.
        '''
        result = self.query(**kwds)
        tab = PrettyTable(['Node', 'Value', 'Marginal'], sortby='Node')
        tab.align = 'l'
        tab.align['Marginal'] = 'r'
        tab.float_format = '%8.6f'
        for (node, value), prob in result.items():
            if kwds.get(node, '') == value:
                tab.add_row(['%s*' % node,
                             '%s%s*%s' % (GREEN, value, NORMAL),
                             '%8.6f' % prob])
            else:
                tab.add_row([node, value, '%8.6f' % prob])
        print tab

    def discover_sample_ordering(self):
        return discover_sample_ordering(self)

    def get_sample(self, evidence={}):
        '''
        We need to allow for setting
        certain observed variables and
        discarding mismatching
        samples as we generate them.
        '''
        if not hasattr(self, 'sample_ordering'):
            self.sample_ordering = self.discover_sample_ordering()
        return get_sample(self.sample_ordering, evidence)

    def query_by_sampling(self, **kwds):
        counts = defaultdict(int)
        valid_samples = 0
        while valid_samples < self.n_samples:
            print "%s of %s" % (valid_samples, self.n_samples)
            try:
                sample = self.get_sample(kwds)
                valid_samples += 1
            except:
                print 'Failed to get a valid sample...'
                print 'continuing...'
                continue
            for var in sample:
                key = (var.name, var.value)
                counts[key] += 1
        # Now normalize
        normalized = dict(
            [(k, v / valid_samples) for k, v in counts.items()])
        return normalized

    def generate_samples(self, n):
        '''
        Generate and save samples to
        the SQLite sample db for this
        model.
        '''
        if self.inference_method != 'sample_db':
            raise IncorrectInferenceMethodError(
                'generate_samples() not support for inference method: %s' % \
                self.inference_method)
        valid_samples = 0
        if not hasattr(self, 'sample_ordering'):
            self.sample_ordering = self.discover_sample_ordering()
        fn = [x[0].name for x in self.sample_ordering]
        sdb = self.sample_db
        while valid_samples < n:
            try:
                sample = self.get_sample()
            except InvalidSampleException:
                # TODO: Need to figure
                # out why we get invalid
                # samples.
                continue
            sdb.save_sample([(v.name, v.value) for v in sample])
            valid_samples += 1
        sdb.commit()
        print '%s samples stored in %s' % (n, self.sample_db_filename)

    def query_by_external_samples(self, **kwds):
        counts = defaultdict(int)
        samples = self.sample_db.get_samples(self.n_samples, **kwds)
        if len(samples) == 0:
            raise NoSamplesInDB(
                'There are no samples in the database. '
                'Generate some with graph.generate_samples(N).')
        if len(samples) < self.n_samples and self.enforce_minimum_samples:
            raise InsufficientSamplesException(
                'There are less samples in the sampling '
                'database than are required by this graph. '
                'Either generate more samples '
                '(graph.generate_samples(N) or '
                'decrease the number of samples '
                'required for querying (graph.n_samples). ')
        for sample in samples:
            for name, val in sample.items():
                key = (name, val)
                counts[key] += 1
        normalized = dict(
            [(k, v / len(samples)) for k, v in counts.items()])
        return normalized


    def export(self, filename=None, format='graphviz'):
        '''Export the graph in GraphViz dot language.'''
        if filename:
            fh = open(filename, 'w')
        else:
            fh = sys.stdout
        if format != 'graphviz':
            raise 'Unsupported Export Format.'
        fh.write('graph G {\n')
        fh.write('  graph [ dpi = 300 bgcolor="transparent" rankdir="LR"];\n')
        edges = set()
        for node in self.nodes:
            if isinstance(node, FactorNode):
                fh.write('  %s [ shape="rectangle" color="red"];\n' % node.name)
            else:
                fh.write('  %s [ shape="ellipse" color="blue"];\n' % node.name)
        for node in self.nodes:
            for neighbour in node.neighbours:
                edge = [node.name, neighbour.name]
                edge = tuple(sorted(edge))
                edges.add(edge)
        for source, target in edges:
            fh.write('  %s -- %s;\n' % (source, target))
        fh.write('}\n')


def build_graph(*args, **kwds):
    '''
    Automatically create all the
    variable and factor nodes
    using only function definitions.
    Since its cumbersome to supply
    the domains for variable nodes
    via the factor domains perhaps
    we should allow a domains dict?
    '''
    # Lets start off identifying all the
    # variables by introspecting the
    # functions.
    variables = set()
    domains = kwds.get('domains', {})
    name = kwds.get('name')
    variable_nodes = dict()
    factor_nodes = []
    if isinstance(args[0], list):
        # Assume the functions were all
        # passed in a list in the first
        # argument. This makes it possible
        # to build very large graphs with
        # more than 255 functions.
        args = args[0]
    for factor in args:
        factor_args = get_args(factor)
        variables.update(factor_args)
        factor_node = FactorNode(factor.__name__, factor)
        #factor_node.func.domains = domains
        # Bit of a hack for now we should actually exclude variables that
        # are not parameters of this function
        factor_nodes.append(factor_node)
    for variable in variables:
        node = VariableNode(
            variable,
            domain=domains.get(variable, [True, False]))
        variable_nodes[variable] = node
    # Now we have to connect each factor node
    # to its variable nodes
    for factor_node in factor_nodes:
        factor_args = get_args(factor_node.func)
        connect(factor_node, [variable_nodes[x] for x in factor_args])
    graph = FactorGraph(variable_nodes.values() + factor_nodes, name=name)
    #print domains
    return graph

########NEW FILE########
__FILENAME__ = gaussian
from __future__ import division

import math
from collections import defaultdict
from itertools import combinations, product

from prettytable import PrettyTable

from bayesian.linear_algebra import Matrix, zeros


'''
Provides Gaussian Density functions and
approximation to Gaussian CDF.
see https://en.wikipedia.org/wiki/Normal_distribution#Cumulative_distribution
"Numerical approximations for the normal CDF"
For the multivariate case we use the statsmodels module.
'''

b0 = 0.2316419
b1 = 0.319381530
b2 = -0.356563782
b3 = 1.781477937
b4 = -1.821255978
b5 = 1.330274429


def std_gaussian_cdf(x):
    '''Zelen & Severo approximation'''
    g = make_gaussian(0, 1)
    t = 1 / (1 + b0 * x)
    return 1 - g(x) * (
        b1 * t +
        b2 * t ** 2 +
        b3 * t ** 3 +
        b4 * t ** 4 +
        b5 * t ** 5)


def make_gaussian(mean, std_dev):

    def gaussian(x):
        return 1 / (std_dev * (2 * math.pi) ** 0.5) * \
            math.exp((-(x - mean) ** 2) / (2 * std_dev ** 2))

    gaussian.mean = mean
    gaussian.std_dev = std_dev
    gaussian.cdf = make_gaussian_cdf(mean, std_dev)

    return gaussian


def make_gaussian_cdf(mean, std_dev):

    def gaussian_cdf(x):
        t = (x - mean) / std_dev
        if t > 0:
            return std_gaussian_cdf(t)
        elif t == 0:
            return 0.5
        else:
            return 1 - std_gaussian_cdf(abs(t))

    return gaussian_cdf


def make_log_normal(mean, std_dev, base=math.e):
    '''
    Example of approximate log normal distribution:
    In [13]: t = [5, 5, 5, 5, 6, 10, 10, 20, 50]

    In [14]: [math.log(x) for x in t]
    Out[14]:
    [1.6094379124341003,
    1.6094379124341003,
    1.6094379124341003,
    1.6094379124341003,
    1.791759469228055,
    2.302585092994046,
    2.302585092994046,
    2.995732273553991,
    3.912023005428146]

    When constructing the log-normal,
    keep in mind that the mean parameter is the
    mean of the log of the values.

    '''
    def log_normal(x):

        return 1 / (x * (2 * math.pi * std_dev * std_dev) ** 0.5) * \
            base ** (-((math.log(x, base) - mean) ** 2) / (2 * std_dev ** 2))

    log_normal.cdf = make_log_normal_cdf(mean, std_dev)

    return log_normal


def make_log_normal_cdf(mean, std_dev, base=math.e):

    def log_normal_cdf(x):
        gaussian_cdf = make_gaussian_cdf(0, 1)
        return gaussian_cdf((math.log(x, base) - mean) / std_dev)

    return log_normal_cdf


def discretize_gaussian(mu, stddev, buckets,
                        func_name='f_output_var', var_name='output_var'):
    '''Given gaussian distribution parameters
    generate python code that specifies
    a discretized function suitable for
    use in a bayesian belief network.
    buckets should be a list of values
    designating the endpoints of each
    discretized bin, for example if you
    have a variable in the domain [0; 1000]
    and you want 3 discrete intervals
    say [0-400], [400-600], [600-1000]
    then you supply n-1 values where n
    is the number of buckets as follows:
    buckets = [400, 600]
    The code that is generated will thus
    have three values and the prior for
    each value will be computed from
    the cdf function.

    In addition when the function is
    called with a numeric value it will
    automatically convert the numeric
    value into the correct discrete
    value.
    '''
    result = []

    cdf = make_gaussian_cdf(mu, stddev)
    cutoffs = [cdf(b) for b in buckets]
    probs = dict()

    # First the -infinity to the first cutoff....
    probs['%s_LT_%s' % (var_name, buckets[0])] = cutoffs[0]

    # Now the middle buckets
    for i, (b, c) in enumerate(zip(buckets, cutoffs)):
        if i == 0:
            continue
        probs['%s_GE_%s_LT_%s' % (
            var_name, buckets[i-1], b)] = c - cutoffs[i-1]

    # And the final bucket...
    probs['%s_GE_%s' % (
        var_name, buckets[-1])] = 1 - cutoffs[-1]

    # Check that the values = approx 1
    assert round(sum(probs.values()), 5) == 1

    # Now build the python fuction
    result.append('def %s(%s):' % (func_name, var_name))
    result.append('    probs = dict()')
    for k, v in probs.iteritems():
        result.append("    probs['%s'] = %s" % (k, v))
    result.append('    return probs[%s]' % var_name)

    # We will store the buckets as well as the arg_name
    # as attributes
    # of the function to make conversion to discrete
    # values easier.
    result.append('%s.buckets = %s' % (
        func_name, [buckets]))  # Since the argspec is a list of vars
                                # we will make the buckets a list of
                                # buckets one per arg for easy zip.


    return '\n'.join(result), probs.keys()


def discretize_multivariate_guassian(
        means, cov, buckets, parent_vars, cdf,
        func_name='f_output_var', var_name='output_var'):
    '''buckets should be an iterable of iterables
    where each element represnts the buckets into
    which the corresponding variable should be
    discretized.
    cov is the covariance matrix.
    cdf is a callable'''
    assert len(means) == len(stddevs)
    assert len(stddevs) == len(buckets)
    assert len(buckets) == len(parent_vars)

    inf = float("inf")
    result = []
    tt = dict()

    # First we will build the discrete value domains
    # for each of the parent variables.
    domains = defaultdict(list)
    for parent_var, bins in zip(parent_vars, buckets):
        for start, end in zip([-float("inf")] + bins, bins + [float("inf")]):
            if start == -inf:
                domains[parent_var].append(
                '%s_LT_%s' % (parent_var, end))
            elif end == inf:
                domains[parent_var].append(
                    '%s_GE_%s' % (parent_var, start))
            else:

                domains[parent_var].append(
                    '%s_GE_%s_LT_%s' % (
                        parent_var, start, end))

    # TODO Complete this possibly using statsmodels or scipy
    # to integrate over the pdfs.

    # We store the integrations in a dict with
    # n dimentional keys e.g.
    # probs[('A_LT_10', 'B_GT_10')] = 0.001 etc
    probs = dict()
    return domains


def marginalize_joint(x, mu, sigma):
    '''Given joint parameters we want to
    marginilize out the xth one.
    Assume that sigma is represented as a
    list of lists.'''
    new_mu = mu[:]
    del new_mu[x]
    new_sigma = []
    for i, row in enumerate(sigma):
        if i == x:
            continue
        new_row = row[:]
        del new_row[x]
        new_sigma.append(new_row)
    return new_mu, new_sigma


def joint_to_conditional(
        mu_x, mu_y, sigma_xx, sigma_xy, sigma_yx, sigma_yy):
    '''
    See Page 22 from MB08.
    p(X, Y) = N ([mu_x]; [sigma_xx sigma_xy])
                 [mu_y]; [sigma_yx sigma_yy]

    We will be returning the conditional
    distribution of p(Y|X)
    therefore we will always assume
    the shape of mu_y and sigma_yy to be (1, 1)
    Remember that the results of applying
    a single evidence variable in the
    iterative update procedure
    returns the *joint* distribution
    of the full graph given the evidence.
    However what we are actually interested in
    is reading off the individual factors
    of the graph given their dependancies.
    From a joint P(x1,x2...,y)
    return distribution of p(y|x1,x2...)
    mu and sigma should both be instances
    of some Matrix class which can
    invert matrices and do matrix
    arithemetic.
    size(sigma) = (len(mu), len(mu))
    len(mu) = len(x) + 1
    '''
    beta_0 = (mu_y - sigma_yx * sigma_xx.I * mu_x)[0, 0]
    beta = sigma_yx * sigma_xx.I
    sigma = sigma_yy - sigma_yx * sigma_xx.I * sigma_xy
    return beta_0, beta, sigma


def conditional_to_joint(
        mu_x, sigma_x, beta_0, beta, sigma_c):
    '''
    This is from page 19 of
    http://webdocs.cs.ualberta.ca/~greiner/C-651/SLIDES/MB08_GaussianNetworks.pdf
    We are given the parameters of a conditional
    gaussian p(Y|x) = N(beta_0 + beta'x; sigma)
    and also the unconditional means and sigma
    of the joint of the parents: mu_x and sigma_x
    Lets assume Y is always shape(1, 1)
    mu_x has shape(1, len(betas)) and
    sigma_x has shape(len(mu_x), len(mu_x))
    [[mu_X1],
     [mu_X2],
     .....
     [mu_Xn]]

    '''
    mu = MeansVector.zeros((len(beta.rows) + 1, 1))
    for i in range(len(mu_x.rows)):
        mu[i, 0] = mu_x[i, 0]
    assert (beta.T * mu_x).shape == (1, 1)
    mu_y = beta_0 + (beta.T * mu_x)[0, 0]
    mu[len(mu_x), 0] = mu_y
    sigma = CovarianceMatrix.zeros((mu.shape[0], mu.shape[0]))
    # Now the top left block
    # of the covariance matrix is
    # just a copy of the sigma_x matrix
    for i in range(0, len(sigma_x.rows)):
        for j in range(0, len(sigma_x.rows[0])):
            sigma[i, j] = sigma_x[i, j]
    # Now for the top-right and bottom-left corners
    for i in range(0, len(sigma_x)):
        total = 0
        for j in range(0, len(sigma_x)):
            total += beta[j, 0] * sigma_x[i, j]
        sigma[i, len(mu_x)] = total
        sigma[len(mu_x), i] = total
    # And finally for the bottom right corner
    sigma_y = sigma_c + (beta.T * sigma_x * beta)[0, 0]
    sigma[len(sigma_x), len(sigma_x)] = (
        sigma_y)
    return mu, sigma


class NamedMatrix(Matrix):
    '''Wrapper allowing referencing
    of columns and rows by variable
    name'''

    def __init__(self, rows=[], names=[]):
        super(NamedMatrix, self).__init__(rows)
        if not names:
            # Default to x1, x2....
            names = ['x%s' % x for x in range(1, len(rows) + 1)]
        self.set_names(names)

    @classmethod
    def zeros(cls, shape, names=[]):
        '''Alternate constructor that
        creates a zero based matrix'''
        rows, cols = shape
        matrix_rows = []
        for i in range(0, rows):
            matrix_rows.append([0] * cols)
        if not names:
            names = ['x%s' % x for x in range(1, rows + 1)]
        cov = cls(matrix_rows, names)
        return cov

    def set_name(self, col, name):
        self.names[name] = col
        self.index_to_name[col] = name
        self.name_ordering.append(name)

    def set_names(self, names):
        assert len(names) in self.shape
        self.names = dict(zip(names, range(len(names))))
        self.name_ordering = names
        self.index_to_name = dict([(v, k) for k, v in self.names.items()])

    def __getitem__(self, item):
        if isinstance(item, str):
            assert item in self.names
            item = self.names[item]
            return super(NamedMatrix, self).__getitem__(item)
        elif isinstance(item, tuple):
            row, col = item
            if isinstance(row, str):
                assert row in self.names
                row = self.names[row]
            if isinstance(col, str):
                assert col in self.names
                col = self.names[col]
            return super(NamedMatrix, self).__getitem__((row, col))
        else:
            return super(NamedMatrix, self).__getitem__(item)

    def __setitem__(self, item, value):
        if isinstance(item, tuple):
            row, col = item
            if isinstance(row, str):
                assert row in self.names
                row = self.names[row]
            if isinstance(col, str):
                assert col in self.names
                col = self.names[col]
            return super(NamedMatrix, self).__setitem__((row, col), value)
        else:
            return super(NamedMatrix, self).__setitem__(item, value)

    def col(self, j):
        if isinstance(j, str):
            assert j in self.names
            j = self.names[j]
        return [row[j] for row in self.rows]

    def __repr__(self):
        cols = self.name_ordering[:self.shape[1]]
        tab = PrettyTable([''] + cols)
        tab.align = 'r'
        for row in self.name_ordering:
            table_row = [row]
            for col in cols:
                table_row.append('%s' % self[row, col])
            tab.add_row(table_row)
        return tab.get_string()


class CovarianceMatrix(NamedMatrix):
    '''Wrapper allowing referencing
    of columns and rows by variable
    name'''

    def __init__(self, rows=[], names=[]):
        super(CovarianceMatrix, self).__init__(rows)
        if not names:
            # Default to x1, x2....
            names = ['x%s' % x for x in range(1, len(rows) + 1)]
        self.set_names(names)

    def split(self, name):
        '''Split into sigma_xx, sigma_yy etc...'''
        assert name in self.names
        x_names = [n for n in self.name_ordering if n != name]
        sigma_xx = CovarianceMatrix.zeros(
            (len(self) - 1, len(self) - 1),
            names=x_names)
        sigma_yy = CovarianceMatrix.zeros((1, 1), names=[name])
        #sigma_xy = zeros((len(sigma_xx), 1))
        sigma_xy = NamedMatrix.zeros((len(sigma_xx), 1), names=x_names)
        #sigma_yx = zeros((1, len(sigma_xx)))
        sigma_yx = NamedMatrix.zeros((1, len(sigma_xx)), names=x_names)

        for row, col in product(
                self.name_ordering,
                self.name_ordering):
            v = self[row, col]
            if row == name and col == name:
                sigma_yy[0, 0] = v
            elif row != name and col != name:
                sigma_xx[row, col] = v
            elif row == name:
                sigma_xy[col, 0] = v
            else:
                sigma_yx[0, row] = v
        return sigma_xx, sigma_xy, sigma_yx, sigma_yy


class MeansVector(NamedMatrix):
    '''Wrapper allowing referencing
    of rows by variable name.
    In this implementation we will
    always consider a vector of means
    to be a vertical matrix with
    a shape of n rows and 1 col.
    The rows will be named.
    '''


    def __init__(self, rows=[], names=[]):
        super(MeansVector, self).__init__(rows)
        if not names:
            # Default to x1, x2....
            names = ['x%s' % x for x in range(1, len(rows) + 1)]
        self.set_names(names)

    def __getitem__(self, item):
        if isinstance(item, str):
            assert item in self.names
            item = self.names[item]
            return super(MeansVector, self).__getitem__(item)
        elif isinstance(item, tuple):
            row, col = item
            if isinstance(row, str):
                assert row in self.names
                row = self.names[row]
            if isinstance(col, str):
                assert col in self.names
                col = self.names[col]
            return super(MeansVector, self).__getitem__((row, col))
        else:
            return super(MeansVector, self).__getitem__(item)

    def __setitem__(self, item, value):
        if isinstance(item, tuple):
            row, col = item
            assert col == 0 # means vector is always one col
            if isinstance(row, str):
                assert row in self.names
                row = self.names[row]
            return super(MeansVector, self).__setitem__((row, col), value)
        elif isinstance(item, str):
            # Since a MeansVector is always a n x 1
            # matrix we will allow setitem by row only
            # and infer col 0 always
            assert item in self.names
            row = self.names[item]
            return super(MeansVector, self).__setitem__((row, 0), value)
        else:
            return super(MeansVector, self).__setitem__(item, value)

    def __repr__(self):
        tab = PrettyTable(['', 'mu'])
        tab.align = 'r'
        rows = []
        for row in self.name_ordering:
            table_row = [row, '%s' % self[row, 0]]
            tab.add_row(table_row)
        return tab.get_string()

    def split(self, name):
        '''Split into mu_x and mu_y'''
        assert name in self.names
        x_names = [n for n in self.name_ordering if n != name]
        mu_x = MeansVector.zeros((len(self) - 1, 1),
                         names=x_names)
        mu_y = MeansVector.zeros((1, 1), names=[name])

        for row in self.name_ordering:
            v = self[row, 0]
            if row == name:
                mu_y[name, 0] = v
            else:
                mu_x[row, 0] = v
        return mu_x, mu_y

########NEW FILE########
__FILENAME__ = gaussian_bayesian_network
'''Classes for pure Gaussian Bayesian Networks'''
import math
import types
from functools import wraps
from numbers import Number
from collections import Counter
from itertools import product as xproduct
from StringIO import StringIO

from bayesian.graph import Graph, Node, connect
from bayesian.gaussian import make_gaussian_cdf
from bayesian.gaussian import marginalize_joint
from bayesian.gaussian import joint_to_conditional, conditional_to_joint
from bayesian.gaussian import CovarianceMatrix, MeansVector
from bayesian.linear_algebra import zeros, Matrix
from bayesian.utils import get_args
from bayesian.utils import get_original_factors
from bayesian.exceptions import VariableNotInGraphError
from bayesian.linear_algebra import Matrix

def gaussian(mu, sigma):
    # This is the gaussian decorator
    # which is a decorator with parameters
    # This means it should return a
    # 'normal' decorated ie twice wrapped...

    def gaussianize(f):

        @wraps(f)
        def gaussianized(*args):
            x = args[0]
            return 1 / (sigma * (2 * math.pi) ** 0.5) * \
                math.exp((-(x - mu) ** 2) / (2 * sigma ** 2))

        gaussianized.mean = mu
        gaussianized.std_dev = sigma
        gaussianized.variance = sigma ** 2
        gaussianized.cdf = make_gaussian_cdf(mu, sigma)
        gaussianized.argspec = get_args(f)
        gaussianized.entropy = types.MethodType(
            lambda x: 0.5 * math.log(2 * math.pi * math.e * x.variance),
            gaussianized)

        return gaussianized
    return gaussianize


def conditional_gaussian(mu, sigma, betas):

    def conditional_gaussianize(f):

        @wraps(f)
        def conditional_gaussianized(*args, **kwds):
            '''Since this function will never
            be called directly we dont need anything here.
            '''
            # First we need to construct a vector
            # out of the args...
            x = zeros((len(args), 1))
            for i, a in enumerate(args):
                x[i, 0] = a
            sigma = conditional_gaussianized.covariance_matrix
            mu = conditional_gaussianized.joint_mu
            return 1 / (2 * math.pi * sigma.det()) ** 0.5 \
                * math.exp(-0.5 * ((x - mu).T * sigma.I * (x - mu))[0, 0])

        conditional_gaussianized.mean = mu
        conditional_gaussianized.std_dev = sigma
        conditional_gaussianized.variance = sigma ** 2
        conditional_gaussianized.raw_betas = betas
        conditional_gaussianized.argspec = get_args(f)
        conditional_gaussianized.entropy = types.MethodType(
            lambda x: len(x.joint_mu) / 2 * \
            (1 + math.log(2 * math.pi)) + \
            0.5 * math.log(x.covariance_matrix.det()), conditional_gaussianized)

        # NOTE: the joint parameters are
        # add to this function at the time of the
        # graph construction

        return conditional_gaussianized

    return conditional_gaussianize


class GBNNode(Node):

    def __init__(self, factor):
        super(GBNNode, self).__init__(factor.__name__)
        self.func = factor
        self.argspec = get_args(factor)

    def __repr__(self):
        return '<GuassianNode %s (%s)>' % (
            self.name,
            self.argspec)

    @property
    def variance(self):
        return self.func.variance


class GaussianBayesianGraph(Graph):

    def __init__(self, nodes, name=None):
        self.nodes = nodes
        self.name = name
        # Assign integer indices
        # to the nodes to trace
        # matrix rows and cols
        # back to the nodes.
        # The indices must be in
        # topological order.
        ordered = self.get_topological_sort()
        for i, node in enumerate(ordered):
            node.index = i

    def get_joint_parameters(self):
        '''Return the vector of means
        and the covariance matrix
        for the full joint distribution.
        For now, by definition, all
        the variables in a Gaussian
        Bayesian Network are either
        univariate gaussian or
        conditional guassians.
        '''
        ordered = self.get_topological_sort()
        mu_x = Matrix([[ordered[0].func.mean]])
        sigma_x = Matrix([[ordered[0].func.variance]])
        # Iteratively build up the mu and sigma matrices
        for node in ordered[1:]:
            beta_0 = node.func.mean
            beta = zeros((node.index, 1))
            total = 0
            for parent in node.parents:
                #beta_0 -= node.func.betas[parent.variable_name] * \
                #          parent.func.mean
                beta[parent.index, 0] = node.func.betas[parent.variable_name]
            sigma_c = node.func.variance
            mu_x, sigma_x = conditional_to_joint(
                mu_x, sigma_x, beta_0, beta, sigma_c)
        # Now set the names on the covariance matrix to
        # the graphs variabe names
        names = [n.variable_name for n in ordered]
        mu_x.set_names(names)
        sigma_x.set_names(names)
        return mu_x, sigma_x

    def query(self, **kwds):

        # Ensure the evidence variables are actually
        # present
        invalid_vars = [v for v in kwds.keys() if v not in self.nodes]
        if invalid_vars:
            raise VariableNotInGraphError(invalid_vars)

        mu, sigma = self.get_joint_parameters()

        # Iteratively apply the evidence...
        result = dict()
        result['evidence'] = kwds

        for k, v in kwds.items():
            x = MeansVector([[v]], names=[k])
            sigma_yy, sigma_yx, sigma_xy, sigma_xx = (
                sigma.split(k))
            mu_y, mu_x = mu.split(k)
            # See equations (6) and (7) of CK
            mu_y_given_x = MeansVector(
                (mu_y + sigma_yx * sigma_xx.I * (x - mu_x)).rows,
                names = mu_y.name_ordering)
            sigma_y_given_x = CovarianceMatrix(
                (sigma_yy - sigma_yx * sigma_xx.I * sigma_xy).rows,
                names=sigma_yy.name_ordering)
            sigma = sigma_y_given_x
            mu = mu_y_given_x

        result['joint'] = dict(mu=mu, sigma=sigma)
        return result

    def q(self, **kwds):
        '''Wrapper around query

        This method formats the query
        result in a nice human readable format
        for interactive use.
        '''
        result = self.query(**kwds)
        mu = result['joint']['mu']
        sigma = result['joint']['sigma']
        evidence = result['evidence']
        print 'Evidence: %s' % str(evidence)
        print 'Covariance Matrix:'
        print sigma
        print 'Means:'
        print mu


    def discover_sample_ordering(self):
        return discover_sample_ordering(self)


    def get_graphviz_source(self):
        fh = StringIO()
        fh.write('digraph G {\n')
        fh.write('  graph [ dpi = 300 bgcolor="transparent" rankdir="LR"];\n')
        edges = set()
        for node in sorted(self.nodes.values(), key=lambda x:x.name):
            fh.write('  %s [ shape="ellipse" color="blue"];\n' % node.name)
            for child in node.children:
                edge = (node.name, child.name)
                edges.add(edge)
        for source, target in sorted(edges, key=lambda x:(x[0], x[1])):
            fh.write('  %s -> %s;\n' % (source, target))
        fh.write('}\n')
        return fh.getvalue()

def build_gbn(*args, **kwds):
    '''Builds a Gaussian Bayesian Graph from
    a list of functions'''
    variables = set()
    name = kwds.get('name')
    variable_nodes = dict()
    factor_nodes = dict()

    if isinstance(args[0], list):
        # Assume the functions were all
        # passed in a list in the first
        # argument. This makes it possible
        # to build very large graphs with
        # more than 255 functions, since
        # Python functions are limited to
        # 255 arguments.
        args = args[0]

    for factor in args:
        factor_args = get_args(factor)
        variables.update(factor_args)
        node = GBNNode(factor)
        factor_nodes[factor.__name__] = node

    # Now lets create the connections
    # To do this we need to find the
    # factor node representing the variables
    # in a child factors argument and connect
    # it to the child node.
    # Note that calling original_factors
    # here can break build_gbn if the
    # factors do not correctly represent
    # a valid network. This will be fixed
    # in next release
    original_factors = get_original_factors(factor_nodes.values())
    for var_name, factor in original_factors.items():
        factor.variable_name = var_name
    for factor_node in factor_nodes.values():
        factor_args = get_args(factor_node)
        parents = [original_factors[arg] for arg in
                   factor_args if original_factors[arg] != factor_node]
        for parent in parents:
            connect(parent, factor_node)
    # Now process the raw_betas to create a dict
    for factor_node in factor_nodes.values():
        # Now we want betas to always be a dict
        # but in the case that the node only
        # has one parent we will allow the user to specify
        # the single beta for that parent simply
        # as a number and not a dict.
        if hasattr(factor_node.func, 'raw_betas'):
            if isinstance(factor_node.func.raw_betas, Number):
                # Make sure that if they supply a number
                # there is only one parent
                assert len(get_args(factor_node)) == 2
                betas = dict()
                for arg in get_args(factor_node):
                    if arg != factor_node.variable_name:
                        betas[arg] = factor_node.func.raw_betas
                factor_node.func.betas = betas
            else:
                factor_node.func.betas = factor_node.func.raw_betas
    gbn = GaussianBayesianGraph(original_factors, name=name)
    # Now for any conditional gaussian nodes
    # we need to tell the node function what the
    # parent parameters are so that the pdf can
    # be computed.
    sorted = gbn.get_topological_sort()
    joint_mu, joint_sigma = gbn.get_joint_parameters()
    for node in sorted:
        if hasattr(node.func, 'betas'):
            # This means its multivariate gaussian
            names = [n.variable_name for n in node.parents] + [node.variable_name]
            node.func.joint_mu = MeansVector.zeros((len(names), 1), names=names)
            for name in names:
                node.func.joint_mu[name] = joint_mu[name][0, 0]
            node.func.covariance_matrix = CovarianceMatrix.zeros(
                (len(names), len(names)), names)
            for row, col in xproduct(names, names):
                node.func.covariance_matrix[row, col] = joint_sigma[row, col]
    return gbn


def build_graph(*args, **kwds):
    '''For compatibility, this is
    just a wrapper around build_gbn'''
    return build_gbn(*args, **kwds)

########NEW FILE########
__FILENAME__ = gaussian_node
import math
from itertools import product
from functools import wraps
import numpy as np

from bayesian.factor_graph import Node
from bayesian.gaussian import make_gaussian_cdf
from bayesian.utils import get_args



def conditional_covariance_matrix(sigma_11, sigma_12, sigma_22, sigma_21):
    return sigma_11 - sigma_12 * (sigma_22 ** -1) * sigma_21


def split(means, sigma):
    ''' Split the means and covariance matrix
    into 'parts' as in wikipedia article ie

    mu = | mu_1 |
         | mu_2 |

    sigma = | sigma_11 sigma_12 |
            | sigma_21 sigma_22 |

    We will assume that we always combine
    one variable at a time and thus we
    will always split by mu_2 ie mu_2 will
    always have dim(1,1) so that it can
    be subtracted from the scalar a
    Also we will make sim(sigma_22)
    always (1,1)


    '''
    mu_1 = means[0:-1]
    mu_2 = means[-1:]
    sigma_11 = sigma[0:len(means) -1, 0:len(means) -1]
    sigma_12 = sigma[:-1,-1:]
    sigma_21 = sigma_12.T
    sigma_22 = sigma[len(means) -1:, len(means) - 1:]
    return mu_1, mu_2, sigma_11, sigma_12, sigma_21, sigma_22


def conditional_mean(mu_1, mu_2, a, sigma_12, sigma_22):
    '''These arg names are from the Wikipedia article'''
    mean = mu_1 + sigma_12 * sigma_22 ** -1 * (a - mu_2)
    return mean


def build_sigma_from_std_devs(std_devs):
    retval = []
    for sd_i, sd_j in product(std_devs, std_devs):
        retval.append(sd_i * sd_j)
    return np.matrix(retval).reshape(len(std_devs), len(std_devs))


def get_parent_from_betas(betas, child):
    '''Return all betas ending at child'''
    return [k for k, v in betas.items() if k[0] == child]


def conditional_to_joint_sigma_2(s, C, variances, betas):
    '''
    This is derived from the psuedo code
    on page 538, Schachter and Kenley.
    http://www.stanford.edu/dept/MSandE/cgi-bin/people/faculty/shachter/pdfs/gaussid.pdf
    s is an ordering of the nodes in which no
    dependent variable occurs before its parents.
    To make this work we have to make sure we
    are using the same notation that they use.
    See beginning of chapter 2.
    For the example we have X1, X2 and X3
    Thus n = [1, 2, 3]
    s = [1, 2, 3] (This is the ordered sequence)
    for now C is a dict with the vals being
    the list of parents so
    C[1] = []
    C[2] = [1]
    C[3] = [2]
    betas is a dict of the betas keyed
    by a tuple representing the node
    indices.
    Ok I can verify that this one works!
    for the example in Koller and in the presentation page 19
    it gets correct results...
    Now to check for the river example.

    Woohoo, this works for the river example!!!!
    Now I will write an _3 version that
    uses more sensible arguments...

    '''

    sigma = np.zeros((len(s), len(s)))
    for j in s:
        for i in range(1, j-1+1):
            total = 0
            for k in C[j]:
                total += sigma[i - 1, k - 1] * betas[(j, k)]
            sigma[j-1, i-1] = total
            sigma[i-1, j-1] = total
        total = 0
        for k in C[j]:
            total += sigma[j-1, k-1] * betas[(j, k)]
        sigma[j-1, j-1] = variances[j-1] + total
    return sigma

########NEW FILE########
__FILENAME__ = graph
'''Generic Graph Classes'''
from StringIO import StringIO

class Node(object):

    def __init__(self, name, parents=[], children=[]):
        self.name = name
        self.parents = parents[:]
        self.children = children[:]

    def __repr__(self):
        return '<Node %s>' % self.name


class UndirectedNode(object):

    def __init__(self, name, neighbours=[]):
        self.name = name
        self.neighbours = neighbours[:]

    def __repr__(self):
        return '<UndirectedNode %s>' % self.name


class Graph(object):

    def export(self, filename=None, format='graphviz'):
        '''Export the graph in GraphViz dot language.'''
        if format != 'graphviz':
            raise 'Unsupported Export Format.'
        if filename:
            fh = open(filename, 'w')
        else:
            fh = sys.stdout
        fh.write(self.get_graphviz_source())

    def get_topological_sort(self):
        '''In order to make this sort
        deterministic we will use the
        variable name as a secondary sort'''
        l = []
        l_set = set() # For speed
        s = [n for n in self.nodes.values() if not n.parents]
        s.sort(reverse=True, key=lambda x:x.variable_name)
        while s:
            n = s.pop()
            l.append(n)
            l_set.add(n)
            # Now some of n's children may be
            # added to s if all their parents
            # are already accounted for.
            for m in n.children:
                if set(m.parents).issubset(l_set):
                    s.append(m)
                    s.sort(reverse=True, key=lambda x:x.variable_name)
        if len(l) == len(self.nodes):
            return l
        raise "Graph Has Cycles"


class UndirectedGraph(object):

    def __init__(self, nodes, name=None):
        self.nodes = nodes
        self.name = name

    def get_graphviz_source(self):
        fh = StringIO()
        fh.write('graph G {\n')
        fh.write('  graph [ dpi = 300 bgcolor="transparent" rankdir="LR"];\n')
        edges = set()
        for node in self.nodes:
            fh.write('  %s [ shape="ellipse" color="blue"];\n' % node.name)
            for neighbour in node.neighbours:
                edge = [node.name, neighbour.name]
                edges.add(tuple(sorted(edge)))
        for source, target in edges:
            fh.write('  %s -- %s;\n' % (source, target))
        fh.write('}\n')
        return fh.getvalue()

    def export(self, filename=None, format='graphviz'):
        '''Export the graph in GraphViz dot language.'''
        if format != 'graphviz':
            raise 'Unsupported Export Format.'
        if filename:
            fh = open(filename, 'w')
        else:
            fh = sys.stdout
        fh.write(self.get_graphviz_source())


def connect(parent, child):
    '''
    Make an edge between a parent
    node and a child node.
    a - parent
    b - child
    '''
    parent.children.append(child)
    child.parents.append(parent)

########NEW FILE########
__FILENAME__ = linear_algebra
'''Very Basic backup Matrix ops for non-Numpy installs'''
from copy import deepcopy

class Matrix(object):

    def __init__(self, rows=[]):
        if not rows:
            self.rows = []
        else:
            assert isinstance(rows, list)
            self.rows = rows

    def append(self, row):
        '''Like list.append but must be a tuple.'''
        self.rows.append(row)

    def __len__(self):
        return len(self.rows)

    @property
    def shape(self):
        return (len(self.rows), len(self.rows[0]))

    def __getitem__(self, item):
        if isinstance(item, int):
            # Since Numpy Matrices return
            # a Matrix for row gets
            # we will do the same...
            return Matrix([self.rows[item][:]])
        if isinstance(item, tuple):
            row, col = item
            return self.rows[row][col]


    def __setitem__(self, item, val):
        row, col = item
        assert row >= 0
        assert col >= 0
        assert row < len(self.rows)
        assert col < len(self.rows[0])
        self.rows[row][col] = val

    def __add__(self, other):
        assert self.shape == other.shape
        retval = zeros(self.shape)
        for i in range(len(self.rows)):
            for j in range(len(self.rows[0])):
                retval[i, j] = self[i, j] + other[i, j]
        return retval

    def __sub__(self, other):
        assert self.shape == other.shape
        retval = zeros(self.shape)
        for i in range(len(self.rows)):
            for j in range(len(self.rows[0])):
                retval[i, j] = self[i, j] - other[i, j]
        return retval

    def __mul__(self, other):
        assert len(self.rows[0]) == len(other.rows)
        rows = len(self.rows)
        cols = len(other.rows[0])
        result = zeros((rows, cols))
        for new_i in range(0, len(self.rows)):
            for new_j in range(0, len(other.rows[0])):
                total = 0
                for k in range(0, len(self.rows[0])):
                    total += self[new_i, k] * other[k, new_j]
                result[new_i, new_j] = total
        return result

    def __div__(self, other):
        return self * other.I

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def col(self, j):
        return [row[j] for row in self.rows]

    @property
    def T(self):
        '''Transpose'''
        result = zeros((len(self.rows[0]), len(self.rows)))
        for i in range(0, len(self.rows)):
            for j in range(0, len(self.rows[0])):
                result[j, i] = self[i, j]
        return result

    @property
    def I(self):
        '''Inverse named I to emulate numpy API'''
        assert len(self.rows) == len(self.rows[0])
        if len(self.rows) == 1:
            return Matrix([[1.0 / self[0, 0]]])
        inverse = make_identity(len(self.rows))
        m = Matrix()
        m.rows = deepcopy(self.rows)
        for col in range(len(self.rows)):
            diag_row = col
            k = 1.0 / m[diag_row, col]
            for j in range(0, len(m.rows)):
                m[diag_row, j] *= k
            for j in range(0, len(inverse.rows)):
                inverse[diag_row, j] *= k
            source_row = diag_row
            for target_row in range(len(self.rows)):
                if source_row != target_row:
                    k = -m[target_row, col]
                    ones = make_identity(len(self.rows))
                    ones[source_row, target_row] = k
                    source_vals = ones.col(target_row)
                    for j in range(0, len(self.rows[0])):
                        target_vals = m.col(j)
                        m[target_row, j] = inner_product(
                            source_vals, target_vals)
                    for j in range(0, len(self.rows[0])):
                        target_vals = inverse.col(j)
                        inverse[target_row, j] = inner_product(
                            source_vals, target_vals)
        return inverse

    def det(self):
        return _det(self.rows)

    def __repr__(self):
        rows = []
        for i in range(0, len(self.rows)):
            row = ['%s' % j for j in self.rows[i]]
            rows.append(str('\t'.join(row)))
        return '\n'.join(rows)


def inner_product(x, y):
    assert len(x) == len(y)
    return sum(map(lambda (x, y): x * y, zip(x, y)))


def zeros(size):
    '''Emulate the Numpy np.zeros factory'''
    rows, cols = size
    m = Matrix()
    for i in range(0, rows):
        m.rows.append([0] * cols)
    return m


def make_identity(j):
    m = zeros((j, j))
    for i in range(0, j):
        m[i, i] = 1
    return m

def split(means, sigma):
    ''' Split the means and covariance matrix
    into 'parts' as in wikipedia article ie

    mu = | mu_x |
         | mu_y |

    sigma = | sigma_xx sigma_xy |
            | sigma_yx sigma_yy |

    We will assume that we always combine
    one variable at a time and thus we
    will always split by mu_y ie mu_y will
    always have dim(1,1) so that it can
    be subtracted from the scalar a
    Also we will make dim(sigma_yy)
    always (1,1)


    '''
    mu_x = means[0:-1]
    mu_2 = means[-1:]
    sigma_11 = sigma[0:len(means) -1, 0:len(means) -1]
    sigma_12 = sigma[:-1,-1:]
    sigma_21 = sigma_12.T
    sigma_22 = sigma[len(means) -1:, len(means) - 1:]
    return mu_1, mu_2, sigma_11, sigma_12, sigma_21, sigma_22


def _det(l):
    n = len(l)
    if (n > 2):
        i = 1
        t = 0
        sum = 0
        while t <= n - 1:
            d = {}
            t1 = 1
            while t1 <= n - 1:
                m = 0
                d[t1] = []
                while m <= n - 1:
                    if (m == t):
                        u = 0
                    else:
                        d[t1].append(l[t1][m])
                    m += 1
                t1 += 1
            l1 = [d[x] for x in d]
            sum = sum + i * (l[0][t]) * (_det(l1))
            i = i * (-1)
            t += 1
        return sum
    else:
        return (l[0][0]*l[1][1]-l[0][1]*l[1][0])


if __name__ == '__main__':
    my_a = Matrix()
    my_b = Matrix()
    my_a.rows.append([0, 1, 2])
    my_a.rows.append([3, 4, 5])
    my_b.rows.append([0, 1])
    my_b.rows.append([2, 3])
    my_b.rows.append([4, 5])
    m = my_a * my_b
    print my_a * my_b
    import ipdb; ipdb.set_trace()
    mi = m.I
    print m
    print mi

########NEW FILE########
__FILENAME__ = persistance
'''Handle Persistance of Pre-generated Samples'''
import os
import sqlite3


class UnsupportedTypeException(Exception):
    pass


class SampleDBNotFoundException(Exception):
    pass


COMMIT_THRESHOLD = 1000

# Python data type to SQLite data type mapping
# NOTE: Technically SQLite does not support
# boolean types, they are internally stored
# as 0 and 1, however you can still issue
# a create statement with a type of 'bool'.
# We will use this to distinguish between
# boolean and integer data types.
P2S_MAPPING = {
    bool: 'bool',
    str: 'varchar',
    unicode: 'varchar',
    int: 'integer'}


S2P_MAPPING = {
    'bool': bool,
    'varchar': unicode,
    'integer': int}


def domains_to_metadata(domains):
    '''Construct a metadata dict
    out of the domains dict.
    The domains dict has the following
    form:
    keys: variable names from a factor graph
    vals: list of possible values the variable can have
    The metadata dict has the following form:
    keys: (same as above)
    vals: A string representing the sqlite data type
    (i.e 'integer' for bool and 'varchar' for str)'''
    metadata = dict()
    for k, v in domains.items():
        # Assume that all values in the domain
        # are of the same type. TODO: verify this!
        try:
            metadata[k.name] = P2S_MAPPING[type(v[0])]
        except KeyError:
            print k, v
            raise UnsupportedTypeException
    return metadata


def ensure_data_dir_exists(filename):
    data_dir = os.path.dirname(filename)
    if not os.path.exists(data_dir):
        # Create the data directory...
        os.makedirs(data_dir)


def initialize_sample_db(conn, metadata):
    '''Create a new SQLite sample database
    with the appropriate column names.
    metadata should be a dict of column
    names with a type. Currently if
    the Variable is a boolean variable
    we map it to integers 1 and 0.
    All other variables are considered
    to be categorical and are mapped
    to varchar'''
    type_specs = []
    for column, sqlite_type in metadata.items():
        type_specs.append((column, sqlite_type))
    SQL = '''
        CREATE TABLE samples (%s);
    ''' % ','.join(['%s %s' % (col, type_) for col, type_ in type_specs])
    cur = conn.cursor()
    print SQL
    cur.execute(SQL)


def build_row_factory(conn):
    '''
    Introspect the samples table
    to build the row_factory
    function. We will assume that
    numeric values are Boolean
    and all other values are Strings.
    Should we encounter a numeric
    value not in (0, 1) we will
    raise an error.
    '''
    cur = conn.cursor()
    cur.execute("pragma table_info('samples')")
    cols = cur.fetchall()
    column_metadata = dict([(col[1], col[2]) for col in cols])

    def row_factory(cursor, row):
        row_dict = dict()
        for idx, desc in enumerate(cursor.description):
            col_name = desc[0]
            col_val = row[idx]
            try:
                row_dict[col_name] = \
                    S2P_MAPPING[column_metadata[col_name]](col_val)
            except KeyError:
                raise UnsupportedTypeException(
                    'A column in the SQLite samples '
                    'database has an unsupported type. '
                    'Supported types are %s. ' % str(S2P_MAPPING.keys()))
        return row_dict

    return row_factory


class SampleDB(object):

    def __init__(self, filename, domains, initialize=False):
        self.conn = sqlite3.connect(filename)
        self.metadata = domains_to_metadata(domains)
        if initialize:
            initialize_sample_db(self.conn, self.metadata)
        self.conn.row_factory = build_row_factory(self.conn)
        self.insert_count = 0

    def get_samples(self, n, **kwds):
        cur = self.conn.cursor()
        sql = '''
            SELECT * FROM samples
        '''
        evidence_cols = []
        evidence_vals = []
        for k, v in kwds.items():
            evidence_cols.append('%s=?' % k)
            if isinstance(v, bool):
                # Cast booleans to integers
                evidence_vals.append(int(v))
            else:
                evidence_vals.append(v)
        if evidence_vals:
            sql += '''
                WHERE %s
            ''' % ' AND '.join(evidence_cols)
        sql += ' LIMIT %s' % n
        cur.execute(sql, evidence_vals)
        return cur.fetchall()

    def save_sample(self, sample):
        '''
        Given a list of tuples
        (col, val) representing
        a sample save it to the sqlite db
        with default type mapping.
        The sqlite3 module automatically
        converts booleans to integers.
        '''
        #keys, vals = zip(*sample.items())
        keys = [x[0] for x in sample]
        vals = [x[1] for x in sample]
        sql = '''
            INSERT INTO SAMPLES
            (%(columns)s)
            VALUES
            (%(values)s)
        ''' % dict(
            columns=', '.join(keys),
            values=', '.join(['?'] * len(vals)))
        cur = self.conn.cursor()
        cur.execute(sql, vals)
        self.insert_count += 1
        if self.insert_count >= COMMIT_THRESHOLD:
            self.commit()

    def commit(self):
        print 'Committing....'
        try:
            self.conn.commit()
            self.insert_count = 1
        except:
            print 'Commit to db file failed...'
            raise

########NEW FILE########
__FILENAME__ = stats
from __future__ import division
'''Basic Stats functionality'''

import math
from collections import defaultdict

from prettytable import PrettyTable


class Vector(object):

    def __init__(self, l):
        self.l = l

    @property
    def mean(self):
        return sum(self.l) / len(self.l)

    @property
    def median(self):
        l = self.l[:]
        l.sort()
        mid = int(float(len(l)) / 2)
        if len(l) % 2 == 1:
            return l[mid]
        else:
            v = Vector(l[mid - 1:mid])
            return v.mean

    @property
    def mode(self):
        '''
        NB: For now we are always
        returning only one mode
        so if the sample is multimodal
        this is not reliable
        '''
        l = self.l[:]
        counts = defaultdict(int)
        for x in l:
            counts[x] += 1
        deco = [(k, v) for k, v in counts.items()]
        deco.sort(reverse=True, key=lambda x: x[1])
        return deco[0][0]

    @property
    def population_std_dev(self):
        return math.sqrt(self.population_variance)

    @property
    def std_dev(self):
        '''Corrected sample standard deviation.'''
        return math.sqrt(self.variance)

    @property
    def population_variance(self):
        mu = self.mean
        sumsq = sum([math.pow(x - mu, 2) for x in self.l])
        return sumsq / len(self.l)

    @property
    def variance(self):
        '''Corrected (unbiased) sample variance'''
        mu = self.mean
        sumsq = sum([math.pow(x - mu, 2) for x in self.l])
        return sumsq / (len(self.l) - 1)

    @property
    def mean_absolute_deviation(self):
        '''Mean of absolute differences to mean'''
        mu = self.mean
        return sum([abs(x - mu) for x in self.l]) / len(self.l)

    @property
    def median_absolute_deviation(self):
        '''Mean of absolute differences to median'''
        mu = self.median
        return sum([abs(x - mu) for x in self.l]) / len(self.l)

    @property
    def mode_absolute_deviation(self):
        '''Mean of absolute differences to a mode*'''
        mu = self.mode
        return sum([abs(x - mu) for x in self.l]) / len(self.l)

    def describe(self):
        tab = PrettyTable(['Property', 'value'])
        tab.align['Property'] = 'l'
        tab.align['value'] = 'r'
        tab.add_row(['Total Numbers', len(self.l)])
        tab.add_row(['Mean', self.mean])
        tab.add_row(['Median', self.median])
        tab.add_row(['Mode*', self.mode])
        tab.add_row(['Sample Standard Deviation', self.std_dev])
        tab.add_row(['Sample Variance', self.variance])
        tab.add_row(['Populatoin Standard Deviation',
                     self.population_std_dev])
        tab.add_row(['Population Variance',
                     self.population_variance])
        tab.add_row(['Mean Absolute Deviation',
                     self.mean_absolute_deviation])
        tab.add_row(['Median Absolute Deviation',
                     self.median_absolute_deviation])
        tab.add_row(['Mode Absolute Deviation',
                     self.mode_absolute_deviation])
        print tab

########NEW FILE########
__FILENAME__ = test_cancer
'''Test the cancer example as a BBN.'''
from bayesian.bbn import build_bbn
from bayesian.examples.bbns.cancer import fP, fS, fC, fX, fD


def pytest_funcarg__cancer_graph(request):
    g = build_bbn(
        fP, fS, fC, fX, fD,
        domains={
            'P': ['low', 'high']})
    return g


def close_enough(x, y, r=3):
    return round(x, r) == round(y, r)


class TestCancerGraph():

    '''
    See table 2.2 of BAI_Chapter2.pdf
    For verification of results.
    (Note typo in some values)
    '''

    def test_no_evidence(self, cancer_graph):
        '''Column 2 of upper half of table'''

        result = cancer_graph.query()
        assert close_enough(result[('P', 'high')], 0.1)
        assert close_enough(result[('P', 'low')], 0.9)
        assert close_enough(result[('S', True)], 0.3)
        assert close_enough(result[('S', False)], 0.7)
        assert close_enough(result[('C', True)], 0.012)
        assert close_enough(result[('C', False)], 0.988)
        assert close_enough(result[('X', True)], 0.208)
        assert close_enough(result[('X', False)], 0.792)
        assert close_enough(result[('D', True)], 0.304)
        assert close_enough(result[('D', False)], 0.696)

    def test_D_True(self, cancer_graph):
        '''Column 3 of upper half of table'''
        result = cancer_graph.query(D=True)
        assert close_enough(result[('P', 'high')], 0.102)
        assert close_enough(result[('P', 'low')], 0.898)
        assert close_enough(result[('S', True)], 0.307)
        assert close_enough(result[('S', False)], 0.693)
        assert close_enough(result[('C', True)], 0.025)
        assert close_enough(result[('C', False)], 0.975)
        assert close_enough(result[('X', True)], 0.217)
        assert close_enough(result[('X', False)], 0.783)
        assert close_enough(result[('D', True)], 1)
        assert close_enough(result[('D', False)], 0)

    def test_S_True(self, cancer_graph):
        '''Column 4 of upper half of table'''
        result = cancer_graph.query(S=True)
        assert close_enough(result[('P', 'high')], 0.1)
        assert close_enough(result[('P', 'low')], 0.9)
        assert close_enough(result[('S', True)], 1)
        assert close_enough(result[('S', False)], 0)
        assert close_enough(result[('C', True)], 0.032)
        assert close_enough(result[('C', False)], 0.968)
        assert close_enough(result[('X', True)], 0.222)
        assert close_enough(result[('X', False)], 0.778)
        assert close_enough(result[('D', True)], 0.311)
        assert close_enough(result[('D', False)], 0.689)

    def test_C_True(self, cancer_graph):
        '''Column 5 of upper half of table'''
        result = cancer_graph.query(C=True)
        assert close_enough(result[('P', 'high')], 0.249)
        assert close_enough(result[('P', 'low')], 0.751)
        assert close_enough(result[('S', True)], 0.825)
        assert close_enough(result[('S', False)], 0.175)
        assert close_enough(result[('C', True)], 1)
        assert close_enough(result[('C', False)], 0)
        assert close_enough(result[('X', True)], 0.9)
        assert close_enough(result[('X', False)], 0.1)
        assert close_enough(result[('D', True)], 0.650)
        assert close_enough(result[('D', False)], 0.350)

    def test_C_True_S_True(self, cancer_graph):
        '''Column 6 of upper half of table'''
        result = cancer_graph.query(C=True, S=True)
        assert close_enough(result[('P', 'high')], 0.156)
        assert close_enough(result[('P', 'low')], 0.844)
        assert close_enough(result[('S', True)], 1)
        assert close_enough(result[('S', False)], 0)
        assert close_enough(result[('C', True)], 1)
        assert close_enough(result[('C', False)], 0)
        assert close_enough(result[('X', True)], 0.9)
        assert close_enough(result[('X', False)], 0.1)
        assert close_enough(result[('D', True)], 0.650)
        assert close_enough(result[('D', False)], 0.350)

    def test_D_True_S_True(self, cancer_graph):
        '''Column 7 of upper half of table'''
        result = cancer_graph.query(D=True, S=True)
        assert close_enough(result[('P', 'high')], 0.102)
        assert close_enough(result[('P', 'low')], 0.898)
        assert close_enough(result[('S', True)], 1)
        assert close_enough(result[('S', False)], 0)
        assert close_enough(result[('C', True)], 0.067)
        assert close_enough(result[('C', False)], 0.933)
        assert close_enough(result[('X', True)], 0.247)
        assert close_enough(result[('X', False)], 0.753)
        assert close_enough(result[('D', True)], 1)
        assert close_enough(result[('D', False)], 0)

########NEW FILE########
__FILENAME__ = test_earthquake
'''Test the Earthquake Example BBN.'''
from bayesian.bbn import build_bbn
from bayesian.examples.bbns.earthquake import *


def pytest_funcarg__earthquake_bbn(request):
    g = build_bbn(
        f_burglary, f_earthquake, f_alarm,
        f_johncalls, f_marycalls)
    return g


def close_enough(x, y, r=6):
    return round(x, r) == round(y, r)


class TestEarthQuakeBBN():

    def test_no_evidence(self, earthquake_bbn):
        result = earthquake_bbn.query()

        assert close_enough(result[('alarm', True)], 0.016114)
        assert close_enough(result[('alarm', False)], 0.983886)
        assert close_enough(result[('burglary', True)], 0.010000)
        assert close_enough(result[('burglary', False)], 0.990000)
        assert close_enough(result[('earthquake', True)], 0.020000)
        assert close_enough(result[('earthquake', False)], 0.980000)
        assert close_enough(result[('johncalls', True)], 0.063697)
        assert close_enough(result[('johncalls', False)], 0.936303)
        assert close_enough(result[('marycalls', True)], 0.021119)
        assert close_enough(result[('marycalls', False)], 0.978881)

########NEW FILE########
__FILENAME__ = test_huang_darwiche
'''Test the Huang-Darwiche example as a BBN.'''
from bayesian.bbn import build_bbn
from bayesian.examples.bbns.huang_darwiche import *


def pytest_funcarg__huang_darwiche_bbn(request):
    g = build_bbn(
        f_a, f_b, f_c, f_d,
        f_e, f_f, f_g, f_h)
    return g


def close_enough(x, y, r=3):
    return round(x, r) == round(y, r)


class TestHuangeDarwicheBBN():

    def test_no_evidence(self, huang_darwiche_bbn):
        result = huang_darwiche_bbn.query()
        assert close_enough(result[('a', True)], 0.5)
        assert close_enough(result[('a', False)], 0.5)
        assert close_enough(result[('d', True)], 0.68)
        assert close_enough(result[('d', False)], 0.32)
        assert close_enough(result[('b', True)], 0.45)
        assert close_enough(result[('b', False)], 0.55)
        assert close_enough(result[('c', True)], 0.45)
        assert close_enough(result[('c', False)], 0.55)
        assert close_enough(result[('e', True)], 0.465)
        assert close_enough(result[('e', False)], 0.535)
        assert close_enough(result[('f', True)], 0.176)
        assert close_enough(result[('f', False)], 0.824)
        assert close_enough(result[('g', True)], 0.415)
        assert close_enough(result[('g', False)], 0.585)
        assert close_enough(result[('h', True)], 0.823)
        assert close_enough(result[('h', False)], 0.177)

########NEW FILE########
__FILENAME__ = test_monty_hall
'''Test the Monty Hall example as a BBN.'''
from bayesian.bbn import build_bbn
from bayesian.examples.bbns.monty_hall import (
    f_guest_door, f_prize_door, f_monty_door)


def pytest_funcarg__monty_hall_graph(request):
    g = build_bbn(
        f_guest_door, f_prize_door, f_monty_door,
        domains={
            'guest_door': ['A', 'B', 'C'],
            'monty_door': ['A', 'B', 'C'],
            'prize_door': ['A', 'B', 'C']})
    return g


def close_enough(x, y, r=3):
    return round(x, r) == round(y, r)


class TestMontyGraph():

    def test_no_evidence(self, monty_hall_graph):
        result = monty_hall_graph.query()
        assert close_enough(result[('guest_door', 'A')], 0.333)
        assert close_enough(result[('guest_door', 'B')], 0.333)
        assert close_enough(result[('guest_door', 'C')], 0.333)
        assert close_enough(result[('monty_door', 'A')], 0.333)
        assert close_enough(result[('monty_door', 'B')], 0.333)
        assert close_enough(result[('monty_door', 'C')], 0.333)
        assert close_enough(result[('prize_door', 'A')], 0.333)
        assert close_enough(result[('prize_door', 'B')], 0.333)
        assert close_enough(result[('prize_door', 'C')], 0.333)

    def test_guest_A_monty_B(self, monty_hall_graph):
        result = monty_hall_graph.query(guest_door='A', monty_door='B')
        assert close_enough(result[('guest_door', 'A')], 1)
        assert close_enough(result[('guest_door', 'B')], 0)
        assert close_enough(result[('guest_door', 'C')], 0)
        assert close_enough(result[('monty_door', 'A')], 0)
        assert close_enough(result[('monty_door', 'B')], 1)
        assert close_enough(result[('monty_door', 'C')], 0)
        assert close_enough(result[('prize_door', 'A')], 0.333)
        assert close_enough(result[('prize_door', 'B')], 0)
        assert close_enough(result[('prize_door', 'C')], 0.667)

########NEW FILE########
__FILENAME__ = test_earthquake_fg
'''Test the Earthquake Example as a Factor Graph.'''
from bayesian.factor_graph import build_graph
from bayesian.examples.factor_graphs.earthquake import *


def pytest_funcarg__earthquake_factor_graph(request):
    g = build_graph(
        f_burglary, f_earthquake, f_alarm,
        f_johncalls, f_marycalls)
    return g


def close_enough(x, y, r=6):
    return round(x, r) == round(y, r)


class TestEarthQuakeBBN():

    def test_no_evidence(self, earthquake_factor_graph):
        result = earthquake_factor_graph.query()

        assert close_enough(result[('alarm', True)], 0.016114)
        assert close_enough(result[('alarm', False)], 0.983886)
        assert close_enough(result[('burglary', True)], 0.010000)
        assert close_enough(result[('burglary', False)], 0.990000)
        assert close_enough(result[('earthquake', True)], 0.020000)
        assert close_enough(result[('earthquake', False)], 0.980000)
        assert close_enough(result[('johncalls', True)], 0.063697)
        assert close_enough(result[('johncalls', False)], 0.936303)
        assert close_enough(result[('marycalls', True)], 0.021119)
        assert close_enough(result[('marycalls', False)], 0.978881)

########NEW FILE########
__FILENAME__ = test_bbn
from __future__ import division
import pytest

import os

from bayesian.bbn import *
from bayesian.utils import make_key


def r3(x):
    return round(x, 3)


def r5(x):
    return round(x, 5)


def pytest_funcarg__sprinkler_graph(request):
    '''The Sprinkler Example as a BBN
    to be used in tests.
    '''
    cloudy = Node('Cloudy')
    sprinkler = Node('Sprinkler')
    rain = Node('Rain')
    wet_grass = Node('WetGrass')
    cloudy.children = [sprinkler, rain]
    sprinkler.parents = [cloudy]
    sprinkler.children = [wet_grass]
    rain.parents = [cloudy]
    rain.children = [wet_grass]
    wet_grass.parents = [
        sprinkler,
        rain]
    bbn = BBN(
        dict(
            cloudy=cloudy,
            sprinkler=sprinkler,
            rain=rain,
            wet_grass=wet_grass)
        )
    return bbn


def pytest_funcarg__huang_darwiche_nodes(request):
    '''The nodes for the Huang Darwich example'''
    def f_a(a):
        return 1 / 2

    def f_b(a, b):
        tt = dict(
            tt=0.5,
            ft=0.4,
            tf=0.5,
            ff=0.6)
        return tt[make_key(a, b)]

    def f_c(a, c):
        tt = dict(
            tt=0.7,
            ft=0.2,
            tf=0.3,
            ff=0.8)
        return tt[make_key(a, c)]

    def f_d(b, d):
        tt = dict(
            tt=0.9,
            ft=0.5,
            tf=0.1,
            ff=0.5)
        return tt[make_key(b, d)]

    def f_e(c, e):
        tt = dict(
            tt=0.3,
            ft=0.6,
            tf=0.7,
            ff=0.4)
        return tt[make_key(c, e)]

    def f_f(d, e, f):
        tt = dict(
            ttt=0.01,
            ttf=0.99,
            tft=0.01,
            tff=0.99,
            ftt=0.01,
            ftf=0.99,
            fft=0.99,
            fff=0.01)
        return tt[make_key(d, e, f)]

    def f_g(c, g):
        tt = dict(
            tt=0.8, tf=0.2,
            ft=0.1, ff=0.9)
        return tt[make_key(c, g)]

    def f_h(e, g, h):
        tt = dict(
            ttt=0.05, ttf=0.95,
            tft=0.95, tff=0.05,
            ftt=0.95, ftf=0.05,
            fft=0.95, fff=0.05)
        return tt[make_key(e, g, h)]

    return [f_a, f_b, f_c, f_d,
            f_e, f_f, f_g, f_h]


def pytest_funcarg__huang_darwiche_dag(request):

    nodes = pytest_funcarg__huang_darwiche_nodes(request)
    return build_bbn(nodes)


def pytest_funcarg__huang_darwiche_moralized(request):

    dag = pytest_funcarg__huang_darwiche_dag(request)
    gu = make_undirected_copy(dag)
    gm = make_moralized_copy(gu, dag)

    return gm


def pytest_funcarg__huang_darwiche_jt(request):
    def priority_func_override(node):
        introduced_arcs = 0
        cluster = [node] + node.neighbours
        for node_a, node_b in combinations(cluster, 2):
            if node_a not in node_b.neighbours:
                assert node_b not in node_a.neighbours
                introduced_arcs += 1
        if node.name == 'f_h':
            return [introduced_arcs, 0]  # Force f_h tie breaker
        if node.name == 'f_g':
            return [introduced_arcs, 1]  # Force f_g tie breaker
        if node.name == 'f_c':
            return [introduced_arcs, 2]  # Force f_c tie breaker
        if node.name == 'f_b':
            return [introduced_arcs, 3]
        if node.name == 'f_d':
            return [introduced_arcs, 4]
        if node.name == 'f_e':
            return [introduced_arcs, 5]
        return [introduced_arcs, 10]
    dag = pytest_funcarg__huang_darwiche_dag(request)
    jt = build_join_tree(dag, priority_func_override)
    return jt


class TestBBN():

    def test_get_graphviz_source(self, sprinkler_graph):
        gv_src = '''digraph G {
  graph [ dpi = 300 bgcolor="transparent" rankdir="LR"];
  Cloudy [ shape="ellipse" color="blue"];
  Rain [ shape="ellipse" color="blue"];
  Sprinkler [ shape="ellipse" color="blue"];
  WetGrass [ shape="ellipse" color="blue"];
  Cloudy -> Rain;
  Cloudy -> Sprinkler;
  Rain -> WetGrass;
  Sprinkler -> WetGrass;
}
'''
        assert sprinkler_graph.get_graphviz_source() == gv_src

    def test_get_original_factors(self, huang_darwiche_nodes):
        original_factors = get_original_factors(
            huang_darwiche_nodes)
        assert original_factors['a'] == huang_darwiche_nodes[0]
        assert original_factors['b'] == huang_darwiche_nodes[1]
        assert original_factors['c'] == huang_darwiche_nodes[2]
        assert original_factors['d'] == huang_darwiche_nodes[3]
        assert original_factors['e'] == huang_darwiche_nodes[4]
        assert original_factors['f'] == huang_darwiche_nodes[5]
        assert original_factors['g'] == huang_darwiche_nodes[6]
        assert original_factors['h'] == huang_darwiche_nodes[7]

    def test_build_graph(self, huang_darwiche_nodes):
        bbn = build_bbn(huang_darwiche_nodes)
        nodes = dict([(node.name, node) for node in bbn.nodes])
        assert nodes['f_a'].parents == []
        assert nodes['f_b'].parents == [nodes['f_a']]
        assert nodes['f_c'].parents == [nodes['f_a']]
        assert nodes['f_d'].parents == [nodes['f_b']]
        assert nodes['f_e'].parents == [nodes['f_c']]
        assert nodes['f_f'].parents == [nodes['f_d'], nodes['f_e']]
        assert nodes['f_g'].parents == [nodes['f_c']]
        assert nodes['f_h'].parents == [nodes['f_e'], nodes['f_g']]

    def test_make_undirecred_copy(self, huang_darwiche_dag):
        ug = make_undirected_copy(huang_darwiche_dag)
        nodes = dict([(node.name, node) for node in ug.nodes])
        assert set(nodes['f_a'].neighbours) == set([
            nodes['f_b'], nodes['f_c']])
        assert set(nodes['f_b'].neighbours) == set([
            nodes['f_a'], nodes['f_d']])
        assert set(nodes['f_c'].neighbours) == set([
            nodes['f_a'], nodes['f_e'], nodes['f_g']])
        assert set(nodes['f_d'].neighbours) == set([
            nodes['f_b'], nodes['f_f']])
        assert set(nodes['f_e'].neighbours) == set([
            nodes['f_c'], nodes['f_f'], nodes['f_h']])
        assert set(nodes['f_f'].neighbours) == set([
            nodes['f_d'], nodes['f_e']])
        assert set(nodes['f_g'].neighbours) == set([
            nodes['f_c'], nodes['f_h']])
        assert set(nodes['f_h'].neighbours) == set([
            nodes['f_e'], nodes['f_g']])

    def test_make_moralized_copy(self, huang_darwiche_dag):
        gu = make_undirected_copy(huang_darwiche_dag)
        gm = make_moralized_copy(gu, huang_darwiche_dag)
        nodes = dict([(node.name, node) for node in gm.nodes])
        assert set(nodes['f_a'].neighbours) == set([
            nodes['f_b'], nodes['f_c']])
        assert set(nodes['f_b'].neighbours) == set([
            nodes['f_a'], nodes['f_d']])
        assert set(nodes['f_c'].neighbours) == set([
            nodes['f_a'], nodes['f_e'], nodes['f_g']])
        assert set(nodes['f_d'].neighbours) == set([
            nodes['f_b'], nodes['f_f'], nodes['f_e']])
        assert set(nodes['f_e'].neighbours) == set([
            nodes['f_c'], nodes['f_f'], nodes['f_h'],
            nodes['f_d'], nodes['f_g']])
        assert set(nodes['f_f'].neighbours) == set([
            nodes['f_d'], nodes['f_e']])
        assert set(nodes['f_g'].neighbours) == set([
            nodes['f_c'], nodes['f_h'], nodes['f_e']])
        assert set(nodes['f_h'].neighbours) == set([
            nodes['f_e'], nodes['f_g']])

    def test_construct_priority_queue(self, huang_darwiche_moralized):
        nodes = dict(
            [(node.name, node) for node in
             huang_darwiche_moralized.nodes])
        pq = construct_priority_queue(nodes, priority_func)
        assert pq == [[0, 2, 'f_f'], [0, 2, 'f_h'],
                      [1, 2, 'f_b'], [1, 2, 'f_a'],
                      [1, 2, 'f_g'], [2, 2, 'f_d'],
                      [2, 2, 'f_c'], [7, 2, 'f_e']]

        # Note that for this test we want to ensure
        # the same elimination ordering as on page 13
        # of Darwiche and Wang. The first two entries
        # in the priority queue are actually a tie
        # so we will manually manipulate them here
        # by specifying an alternative priority func:
        def priority_func_override(node):
            introduced_arcs = 0
            cluster = [node] + node.neighbours
            for node_a, node_b in combinations(cluster, 2):
                if node_a not in node_b.neighbours:
                    assert node_b not in node_a.neighbours
                    introduced_arcs += 1
            if node.name == 'f_h':
                return [introduced_arcs, 0]  # Force f_h tie breaker
            return [introduced_arcs, 2]
        pq = construct_priority_queue(
            nodes,
            priority_func_override)
        assert pq[0] == [0, 0, 'f_h']

    def test_triangulate(self, huang_darwiche_moralized):

        # Because of ties in the priority q we will
        # override the priority function here to
        # insert tie breakers to ensure the same
        # elimination ordering as Darwich Huang.
        def priority_func_override(node):
            introduced_arcs = 0
            cluster = [node] + node.neighbours
            for node_a, node_b in combinations(cluster, 2):
                if node_a not in node_b.neighbours:
                    assert node_b not in node_a.neighbours
                    introduced_arcs += 1
            if node.name == 'f_h':
                return [introduced_arcs, 0]  # Force f_h tie breaker
            if node.name == 'f_g':
                return [introduced_arcs, 1]  # Force f_g tie breaker
            if node.name == 'f_c':
                return [introduced_arcs, 2]  # Force f_c tie breaker
            if node.name == 'f_b':
                return [introduced_arcs, 3]
            if node.name == 'f_d':
                return [introduced_arcs, 4]
            if node.name == 'f_e':
                return [introduced_arcs, 5]
            return [introduced_arcs, 10]
        cliques, elimination_ordering = triangulate(
            huang_darwiche_moralized, priority_func_override)
        nodes = dict([(node.name, node) for node in
                      huang_darwiche_moralized.nodes])
        assert len(cliques) == 6
        assert cliques[0].nodes == set(
            [nodes['f_e'], nodes['f_g'], nodes['f_h']])
        assert cliques[1].nodes == set(
            [nodes['f_c'], nodes['f_e'], nodes['f_g']])
        assert cliques[2].nodes == set(
            [nodes['f_d'], nodes['f_e'], nodes['f_f']])
        assert cliques[3].nodes == set(
            [nodes['f_a'], nodes['f_c'], nodes['f_e']])
        assert cliques[4].nodes == set(
            [nodes['f_a'], nodes['f_b'], nodes['f_d']])
        assert cliques[5].nodes == set(
            [nodes['f_a'], nodes['f_d'], nodes['f_e']])

        assert elimination_ordering == [
            'f_h',
            'f_g',
            'f_f',
            'f_c',
            'f_b',
            'f_d',
            'f_e',
            'f_a']
        # Now lets ensure the triangulated graph is
        # the same as Darwiche Huang fig. 2 pg. 13
        nodes = dict([(node.name, node) for node in
                      huang_darwiche_moralized.nodes])
        assert set(nodes['f_a'].neighbours) == set([
            nodes['f_b'], nodes['f_c'],
            nodes['f_d'], nodes['f_e']])
        assert set(nodes['f_b'].neighbours) == set([
            nodes['f_a'], nodes['f_d']])
        assert set(nodes['f_c'].neighbours) == set([
            nodes['f_a'], nodes['f_e'], nodes['f_g']])
        assert set(nodes['f_d'].neighbours) == set([
            nodes['f_b'], nodes['f_f'], nodes['f_e'],
            nodes['f_a']])
        assert set(nodes['f_e'].neighbours) == set([
            nodes['f_c'], nodes['f_f'], nodes['f_h'],
            nodes['f_d'], nodes['f_g'], nodes['f_a']])
        assert set(nodes['f_f'].neighbours) == set([
            nodes['f_d'], nodes['f_e']])
        assert set(nodes['f_g'].neighbours) == set([
            nodes['f_c'], nodes['f_h'], nodes['f_e']])
        assert set(nodes['f_h'].neighbours) == set([
            nodes['f_e'], nodes['f_g']])

    def test_triangulate_no_tie_break(self, huang_darwiche_moralized):
        # Now lets see what happens if
        # we dont enforce the tie-breakers...
        # It seems the triangulated graph is
        # different adding edges from d to c
        # and b to c
        # Will be interesting to see whether
        # inference will still be correct.
        cliques, elimination_ordering = triangulate(
            huang_darwiche_moralized)
        nodes = dict([(node.name, node) for node in
                      huang_darwiche_moralized.nodes])
        assert set(nodes['f_a'].neighbours) == set([
            nodes['f_b'], nodes['f_c']])
        assert set(nodes['f_b'].neighbours) == set([
            nodes['f_a'], nodes['f_d'], nodes['f_c']])
        assert set(nodes['f_c'].neighbours) == set([
            nodes['f_a'], nodes['f_e'], nodes['f_g'],
            nodes['f_b'], nodes['f_d']])
        assert set(nodes['f_d'].neighbours) == set([
            nodes['f_b'], nodes['f_f'], nodes['f_e'],
            nodes['f_c']])
        assert set(nodes['f_e'].neighbours) == set([
            nodes['f_c'], nodes['f_f'], nodes['f_h'],
            nodes['f_d'], nodes['f_g']])
        assert set(nodes['f_f'].neighbours) == set([
            nodes['f_d'], nodes['f_e']])
        assert set(nodes['f_g'].neighbours) == set([
            nodes['f_c'], nodes['f_h'], nodes['f_e']])
        assert set(nodes['f_h'].neighbours) == set([
            nodes['f_e'], nodes['f_g']])

    def test_build_join_tree(self, huang_darwiche_dag):
        def priority_func_override(node):
            introduced_arcs = 0
            cluster = [node] + node.neighbours
            for node_a, node_b in combinations(cluster, 2):
                if node_a not in node_b.neighbours:
                    assert node_b not in node_a.neighbours
                    introduced_arcs += 1
            if node.name == 'f_h':
                return [introduced_arcs, 0]  # Force f_h tie breaker
            if node.name == 'f_g':
                return [introduced_arcs, 1]  # Force f_g tie breaker
            if node.name == 'f_c':
                return [introduced_arcs, 2]  # Force f_c tie breaker
            if node.name == 'f_b':
                return [introduced_arcs, 3]
            if node.name == 'f_d':
                return [introduced_arcs, 4]
            if node.name == 'f_e':
                return [introduced_arcs, 5]
            return [introduced_arcs, 10]

        jt = build_join_tree(huang_darwiche_dag, priority_func_override)
        for node in jt.sepset_nodes:
            assert set([n.clique for n in node.neighbours]) == \
                set([node.sepset.X, node.sepset.Y])
        # TODO: Need additional tests here especially for
        # clique nodes.

    def test_initialize_potentials(
            self, huang_darwiche_jt, huang_darwiche_dag):
        # Seems like there can be multiple assignments so
        # for this test we will set the assignments explicitely
        cliques = dict([(node.name, node) for node in
                        huang_darwiche_jt.clique_nodes])
        bbn_nodes = dict([(node.name, node) for node in
                          huang_darwiche_dag.nodes])
        assignments = {
            cliques['Clique_ACE']: [bbn_nodes['f_c'], bbn_nodes['f_e']],
            cliques['Clique_ABD']: [
                bbn_nodes['f_a'], bbn_nodes['f_b'],  bbn_nodes['f_d']]}
        huang_darwiche_jt.initialize_potentials(
            assignments, huang_darwiche_dag)
        for node in huang_darwiche_jt.sepset_nodes:
            for v in node.potential_tt.values():
                assert v == 1

        # Note that in H&D there are two places that show
        # initial potentials, one is for ABD and AD
        # and the second is for ACE and CE
        # We should test both here but we must enforce
        # the assignments above because alternate and
        # equally correct Junction Trees will give
        # different potentials.
        def r(x):
            return round(x, 3)

        tt = cliques['Clique_ACE'].potential_tt
        assert r(tt[('a', True), ('c', True), ('e', True)]) == 0.21
        assert r(tt[('a', True), ('c', True), ('e', False)]) == 0.49
        assert r(tt[('a', True), ('c', False), ('e', True)]) == 0.18
        assert r(tt[('a', True), ('c', False), ('e', False)]) == 0.12
        assert r(tt[('a', False), ('c', True), ('e', True)]) == 0.06
        assert r(tt[('a', False), ('c', True), ('e', False)]) == 0.14
        assert r(tt[('a', False), ('c', False), ('e', True)]) == 0.48
        assert r(tt[('a', False), ('c', False), ('e', False)]) == 0.32

        tt = cliques['Clique_ABD'].potential_tt
        assert r(tt[('a', True), ('b', True), ('d', True)]) == 0.225
        assert r(tt[('a', True), ('b', True), ('d', False)]) == 0.025
        assert r(tt[('a', True), ('b', False), ('d', True)]) == 0.125
        assert r(tt[('a', True), ('b', False), ('d', False)]) == 0.125
        assert r(tt[('a', False), ('b', True), ('d', True)]) == 0.180
        assert r(tt[('a', False), ('b', True), ('d', False)]) == 0.020
        assert r(tt[('a', False), ('b', False), ('d', True)]) == 0.150
        assert r(tt[('a', False), ('b', False), ('d', False)]) == 0.150

        # TODO: We should add all the other potentials here too.

    def test_jtclique_node_variable_names(self, huang_darwiche_jt):
        for node in huang_darwiche_jt.clique_nodes:
            if 'ADE' in node.name:
                assert set(node.variable_names) == set(['a', 'd', 'e'])

    def test_assign_clusters(self, huang_darwiche_jt, huang_darwiche_dag):

        # NOTE: This test will fail sometimes as assign_clusters
        # is currently non-deterministic, we should fix this.

        bbn_nodes = dict([(node.name, node) for node in
                          huang_darwiche_dag.nodes])
        assignments = huang_darwiche_jt.assign_clusters(huang_darwiche_dag)
        jt_cliques = dict([(node.name, node) for node
                           in huang_darwiche_jt.clique_nodes])
        # Note that these assignments are slightly different
        # to the ones in H&D. In their paper they never
        # give a full list of assignments so we will use
        # these default deterministic assignments for the
        # test. These are assumed to be a valid assignment
        # as all other tests pass.
        assert [] == assignments[jt_cliques['Clique_ADE']]
        assert [bbn_nodes['f_f']] == assignments[jt_cliques['Clique_DEF']]
        assert [bbn_nodes['f_h']] == assignments[jt_cliques['Clique_EGH']]
        assert [bbn_nodes['f_a'], bbn_nodes['f_c']] == \
            assignments[jt_cliques['Clique_ACE']]
        assert [bbn_nodes['f_b'], bbn_nodes['f_d']] == \
            assignments[jt_cliques['Clique_ABD']]
        assert [bbn_nodes['f_e'], bbn_nodes['f_g']] == \
            assignments[jt_cliques['Clique_CEG']]

        # Now we also need to ensure that every original
        # factor from the BBN has been assigned once
        # and only once to some cluster.
        assert set(
            [node for assignment in
             assignments.values() for node in assignment]) == \
            set(
                [node for node in huang_darwiche_dag.nodes])

    def test_propagate(self, huang_darwiche_jt, huang_darwiche_dag):
        jt_cliques = dict([(node.name, node) for node in
                           huang_darwiche_jt.clique_nodes])
        assignments = huang_darwiche_jt.assign_clusters(huang_darwiche_dag)
        huang_darwiche_jt.initialize_potentials(
            assignments, huang_darwiche_dag)

        huang_darwiche_jt.propagate(starting_clique=jt_cliques['Clique_ACE'])
        tt = jt_cliques['Clique_DEF'].potential_tt
        assert r5(tt[(('d', False), ('e', True), ('f', True))]) == 0.00150
        assert r5(tt[(('d', True), ('e', False), ('f', True))]) == 0.00365
        assert r5(tt[(('d', False), ('e', False), ('f', True))]) == 0.16800
        assert r5(tt[(('d', True), ('e', True), ('f', True))]) == 0.00315
        assert r5(tt[(('d', False), ('e', False), ('f', False))]) == 0.00170
        assert r5(tt[(('d', True), ('e', True), ('f', False))]) == 0.31155
        assert r5(tt[(('d', False), ('e', True), ('f', False))]) == 0.14880
        assert r5(tt[(('d', True), ('e', False), ('f', False))]) == 0.36165

        # TODO: Add more potential truth tables from other nodes.

    def test_marginal(self,  huang_darwiche_jt, huang_darwiche_dag):
        bbn_nodes = dict([(node.name, node) for node in
                          huang_darwiche_dag.nodes])
        assignments = huang_darwiche_jt.assign_clusters(huang_darwiche_dag)
        huang_darwiche_jt.initialize_potentials(
            assignments, huang_darwiche_dag)
        huang_darwiche_jt.propagate()

        # These test values come directly from
        # pg. 22 of H & D
        p_A = huang_darwiche_jt.marginal(bbn_nodes['f_a'])
        assert r3(p_A[(('a', True), )]) == 0.5
        assert r3(p_A[(('a', False), )]) == 0.5

        p_D = huang_darwiche_jt.marginal(bbn_nodes['f_d'])
        assert r3(p_D[(('d', True), )]) == 0.68
        assert r3(p_D[(('d', False), )]) == 0.32

        # The remaining marginals here come
        # from the module itself, however they
        # have been corrobarted by running
        # inference using the sampling inference
        # engine and the same results are
        # achieved.
        '''
        +------+-------+----------+
        | Node | Value | Marginal |
        +------+-------+----------+
        | a    | False | 0.500000 |
        | a    | True  | 0.500000 |
        | b    | False | 0.550000 |
        | b    | True  | 0.450000 |
        | c    | False | 0.550000 |
        | c    | True  | 0.450000 |
        | d    | False | 0.320000 |
        | d    | True  | 0.680000 |
        | e    | False | 0.535000 |
        | e    | True  | 0.465000 |
        | f    | False | 0.823694 |
        | f    | True  | 0.176306 |
        | g    | False | 0.585000 |
        | g    | True  | 0.415000 |
        | h    | False | 0.176900 |
        | h    | True  | 0.823100 |
        +------+-------+----------+
        '''
        p_B = huang_darwiche_jt.marginal(bbn_nodes['f_b'])
        assert r3(p_B[(('b', True), )]) == 0.45
        assert r3(p_B[(('b', False), )]) == 0.55

        p_C = huang_darwiche_jt.marginal(bbn_nodes['f_c'])
        assert r3(p_C[(('c', True), )]) == 0.45
        assert r3(p_C[(('c', False), )]) == 0.55

        p_E = huang_darwiche_jt.marginal(bbn_nodes['f_e'])
        assert r3(p_E[(('e', True), )]) == 0.465
        assert r3(p_E[(('e', False), )]) == 0.535

        p_F = huang_darwiche_jt.marginal(bbn_nodes['f_f'])
        assert r3(p_F[(('f', True), )]) == 0.176
        assert r3(p_F[(('f', False), )]) == 0.824

        p_G = huang_darwiche_jt.marginal(bbn_nodes['f_g'])
        assert r3(p_G[(('g', True), )]) == 0.415
        assert r3(p_G[(('g', False), )]) == 0.585

        p_H = huang_darwiche_jt.marginal(bbn_nodes['f_h'])
        assert r3(p_H[(('h', True), )]) == 0.823
        assert r3(p_H[(('h', False), )]) == 0.177

########NEW FILE########
__FILENAME__ = test_examples
'''Unit tests for the examples in the examples dir.'''
from bayesian.factor_graph import build_graph
from bayesian.examples.factor_graphs.cancer import fP, fS, fC, fX, fD


'''
Since one of the goals of this package
are to have many working examples its
very important that the examples work
correctly "out of the box".
Please add unit tests for all examples
and give references to their sources.

Note that the identical graph also
appears in test_graph where many more
lower level tests are run. These tests
however import the code directly from
the examples directory.
'''


def pytest_funcarg__cancer_graph(request):
    g = build_graph(
        fP, fS, fC, fX, fD,
        domains={
            'P': ['low', 'high']})
    return g


class TestCancerGraph():

    '''
    See table 2.2 of BAI_Chapter2.pdf
    For verification of results.
    (Note typo in some values)
    '''

    def test_no_evidence(self, cancer_graph):
        '''Column 2 of upper half of table'''
        result = cancer_graph.query()
        assert round(result[('P', 'high')], 3) == 0.1
        assert round(result[('P', 'low')], 3) == 0.9
        assert round(result[('S', True)], 3) == 0.3
        assert round(result[('S', False)], 3) == 0.7
        assert round(result[('C', True)], 3) == 0.012
        assert round(result[('C', False)], 3) == 0.988
        assert round(result[('X', True)], 3) == 0.208
        assert round(result[('X', False)], 3) == 0.792
        assert round(result[('D', True)], 3) == 0.304
        assert round(result[('D', False)], 3) == 0.696

    def test_D_True(self, cancer_graph):
        '''Column 3 of upper half of table'''
        result = cancer_graph.query(D=True)
        assert round(result[('P', 'high')], 3) == 0.102
        assert round(result[('P', 'low')], 3) == 0.898
        assert round(result[('S', True)], 3) == 0.307
        assert round(result[('S', False)], 3) == 0.693
        assert round(result[('C', True)], 3) == 0.025
        assert round(result[('C', False)], 3) == 0.975
        assert round(result[('X', True)], 3) == 0.217
        assert round(result[('X', False)], 3) == 0.783
        assert round(result[('D', True)], 3) == 1
        assert round(result[('D', False)], 3) == 0

    def test_S_True(self, cancer_graph):
        '''Column 4 of upper half of table'''
        result = cancer_graph.query(S=True)
        assert round(result[('P', 'high')], 3) == 0.1
        assert round(result[('P', 'low')], 3) == 0.9
        assert round(result[('S', True)], 3) == 1
        assert round(result[('S', False)], 3) == 0
        assert round(result[('C', True)], 3) == 0.032
        assert round(result[('C', False)], 3) == 0.968
        assert round(result[('X', True)], 3) == 0.222
        assert round(result[('X', False)], 3) == 0.778
        assert round(result[('D', True)], 3) == 0.311
        assert round(result[('D', False)], 3) == 0.689

    def test_C_True(self, cancer_graph):
        '''Column 5 of upper half of table'''
        result = cancer_graph.query(C=True)
        assert round(result[('P', 'high')], 3) == 0.249
        assert round(result[('P', 'low')], 3) == 0.751
        assert round(result[('S', True)], 3) == 0.825
        assert round(result[('S', False)], 3) == 0.175
        assert round(result[('C', True)], 3) == 1
        assert round(result[('C', False)], 3) == 0
        assert round(result[('X', True)], 3) == 0.9
        assert round(result[('X', False)], 3) == 0.1
        assert round(result[('D', True)], 3) == 0.650
        assert round(result[('D', False)], 3) == 0.350

    def test_C_True_S_True(self, cancer_graph):
        '''Column 6 of upper half of table'''
        result = cancer_graph.query(C=True, S=True)
        assert round(result[('P', 'high')], 3) == 0.156
        assert round(result[('P', 'low')], 3) == 0.844
        assert round(result[('S', True)], 3) == 1
        assert round(result[('S', False)], 3) == 0
        assert round(result[('C', True)], 3) == 1
        assert round(result[('C', False)], 3) == 0
        assert round(result[('X', True)], 3) == 0.9
        assert round(result[('X', False)], 3) == 0.1
        assert round(result[('D', True)], 3) == 0.650
        assert round(result[('D', False)], 3) == 0.350

    def test_D_True_S_True(self, cancer_graph):
        '''Column 7 of upper half of table'''
        result = cancer_graph.query(D=True, S=True)
        assert round(result[('P', 'high')], 3) == 0.102
        assert round(result[('P', 'low')], 3) == 0.898
        assert round(result[('S', True)], 3) == 1
        assert round(result[('S', False)], 3) == 0
        assert round(result[('C', True)], 3) == 0.067
        assert round(result[('C', False)], 3) == 0.933
        assert round(result[('X', True)], 3) == 0.247
        assert round(result[('X', False)], 3) == 0.753
        assert round(result[('D', True)], 3) == 1
        assert round(result[('D', False)], 3) == 0

########NEW FILE########
__FILENAME__ = test_factor_graph_verify
import pytest
from bayesian.factor_graph import *


def pytest_funcarg__x1(request):
    x1 = VariableNode('x1')
    return x1


def pytest_funcarg__x2(request):
    x2 = VariableNode('x2')
    return x2


def pytest_funcarg__fA_node(request):

    def fA(x1):
        return 0.5

    fA_node = FactorNode('fA', fA)
    return fA_node


def pytest_funcarg__simple_valid_graph(request):

    def fA(x1):
        return 0.5

    fA_node = FactorNode('fA', fA)
    x1 = VariableNode('x1')
    connect(fA_node, x1)
    graph = FactorGraph([fA_node, x1])
    return graph


def pytest_funcarg__graph_with_function_as_node(request):
    '''
    A common error is to instantiate the
    graph with the function instead of
    the function node wrapper.
    '''
    def fA(x1):
        return 0.5

    fA_node = FactorNode('fA', fA)
    x1 = VariableNode('x1')

    connect(fA_node, x1)
    graph = FactorGraph([fA, x1])
    return graph


def pytest_funcarg__graph_with_empty_func_domains(request):

    def fA(x1):
        return 0.5

    fA_node = FactorNode('fA', fA)
    x1 = VariableNode('x1')
    connect(fA_node, x1)
    graph = FactorGraph([fA_node, x1])
    fA_node.func.domains = {}
    return graph


def pytest_funcarg__graph_with_missing_func_domains(request):

    def fA(x1):
        return 0.5

    fA_node = FactorNode('fA', fA)
    x1 = VariableNode('x1')
    connect(fA_node, x1)
    graph = FactorGraph([fA_node, x1])
    delattr(fA_node.func, 'domains')
    return graph


def pytest_funcarg__graph_with_cycle(request):
    '''
    This graph looks like this BBN:

    x1        x2----+
    |         |     |
    +----+----+     |
         |          |
         x3         |
         |          |
         +-----+----+
               |
               x4
    '''

    def fA(x1):
        return 0.5

    def fB(x2):
        return 0.5

    def fC(x1, x2, x3):
        return 0.5

    def fD(x2, x3, x4):
        return 0.5

    graph = build_graph(fA, fB, fC, fD)
    return graph


class TestVerify():

    def test_verify_variable_node_neighbour_type(self, x1, fA_node):
        connect(fA_node, x1)
        assert fA_node.verify_neighbour_types() is True
        assert x1.verify_neighbour_types() is True

    def test_verify_variable_node_neighbour_type_symmetry(self, x1, fA_node):
        connect(x1, fA_node)
        assert fA_node.verify_neighbour_types() is True
        assert x1.verify_neighbour_types() is True

    def test_verify_variable_node_wrong_neighbour_type(self, x1, x2):
        connect(x1, x2)
        assert x1.verify_neighbour_types() is False
        assert x2.verify_neighbour_types() is False

    def test_nodes_of_correct_type(self, simple_valid_graph):
        assert simple_valid_graph.verify() is True

    def test_broken_graph_bad_factor_node(self, graph_with_function_as_node):
        '''
        Make sure exception is raised for
        broken graph.
        '''
        with pytest.raises(InvalidGraphException):
            graph_with_function_as_node.verify()

    def test_broken_graph_empty_factor_domains(
            self, graph_with_empty_func_domains):
        """Ensure exception is raised for broken graph."""
        with pytest.raises(InvalidGraphException):
            graph_with_empty_func_domains.verify()

    def test_broken_graph_missing_factor_domains(
            self, graph_with_missing_func_domains):
        """Ensureexception is raised for broken graph."""
        with pytest.raises(InvalidGraphException):
            graph_with_missing_func_domains.verify()

    def test_graph_has_no_cycles(self, simple_valid_graph):
        assert simple_valid_graph.has_cycles() is False

    def test_graph_has_cycles(self, graph_with_cycle):
        assert graph_with_cycle.has_cycles() is True

########NEW FILE########
__FILENAME__ = test_gaussian
import pytest

from itertools import product as xproduct
from bayesian.gaussian import *


def pytest_funcarg__means_vector_a(request):
    m = MeansVector([[0], [1], [2]], names=('a', 'b', 'c'))
    return m


def pytest_funcarg__means_vector_b(request):
    m = MeansVector([[0], [1], [2]], names=('a', 'b', 'c'))
    return m


def pytest_funcarg__means_vector_c(request):
    m = MeansVector([[0], [1], [2]], names=('a', 'b', 'd'))
    return m


def pytest_funcarg__means_vector_d(request):
    m = MeansVector([[0], [1], [3]], names=('a', 'b', 'c'))
    return m


class TestGaussian():

    def test_joint_to_conditional_1(self):
        '''This is from the example
        on page 22
        '''
        mu_x = MeansVector([[1]])
        mu_y = MeansVector([[-4.5]])
        sigma_xx = CovarianceMatrix([[4]])
        sigma_xy = CovarianceMatrix([[2]])
        sigma_yx = CovarianceMatrix([[2]])
        sigma_yy = CovarianceMatrix([[5]])
        beta_0, beta, sigma = joint_to_conditional(
            mu_x, mu_y, sigma_xx, sigma_xy, sigma_yx, sigma_yy)
        assert beta_0 == -5
        assert beta == Matrix([[0.5]])
        assert sigma == Matrix([[4]])

    def test_joint_to_conditional_2(self):
        # Now do the same for P(X2|X3)
        mu_x = MeansVector([[-4.5]])
        mu_y = MeansVector([[8.5]])
        sigma_xx = CovarianceMatrix([[5]])
        sigma_xy = CovarianceMatrix([[-5]])
        sigma_yx = CovarianceMatrix([[-5]])
        sigma_yy = CovarianceMatrix([[8]])
        beta_0, beta, sigma = joint_to_conditional(
            mu_x, mu_y, sigma_xx, sigma_xy, sigma_yx, sigma_yy)
        assert beta_0 == 4
        assert beta == Matrix([[-1]])
        assert sigma == Matrix([[3]])

    def test_joint_to_conditional_3(self):
        # Now for the river example...
        # These values can be confirmed from page 4
        # First for p(B|A)
        mu_x = MeansVector([[3]])
        mu_y = MeansVector([[4]])
        sigma_xx = CovarianceMatrix([[4]])
        sigma_xy = CovarianceMatrix([[4]])
        sigma_yx = CovarianceMatrix([[4]])
        sigma_yy = CovarianceMatrix([[5]])
        beta_0, beta, sigma = joint_to_conditional(
            mu_x, mu_y, sigma_xx, sigma_xy, sigma_yx, sigma_yy)
        assert beta_0 == 1
        # On page 3, the conditional for the factor f(b|a):
        # N(mu_B + beta_BA(a - mu_A), v_B)
        #
        #        mu_B + beta_BA(a - mu_A)
        #    ==  mu_B + (beta_BA * a) - beta_BA * mu_A
        #    ==     4 + 1 * a - 1 * 3
        #    ==     4 + a - 3
        #    ==     1 + a
        #    ==> beta_0 should be 1
        assert beta == Matrix([[1]])
        assert sigma == Matrix([[1]])

    def test_joint_to_conditional_4(self):
        # p(C|A)
        mu_x = MeansVector([[3]])
        mu_y = MeansVector([[9]])
        sigma_xx = CovarianceMatrix([[4]])
        sigma_xy = CovarianceMatrix([[8]])
        sigma_yx = CovarianceMatrix([[8]])
        sigma_yy = CovarianceMatrix([[20]])
        beta_0, beta, sigma = joint_to_conditional(
            mu_x, mu_y, sigma_xx, sigma_xy, sigma_yx, sigma_yy)
        # from page 3: f(c|a) ~ N(mu_C + beta_CA(a - mu_A), v_C)
        #        mu_C + beta_CA(a - mu_A)
        #    ==  mu_C + beta_CA * a - beta_CA * mu_A
        #    ==     9 + 2 * a - 2 * 3
        #    ==     9 + 2a - 6
        #    ==     3 + 2a
        #    ==> beta_0 = 3 and beta_1 = 2
        assert beta_0 == 3
        assert beta == Matrix([[2]])
        assert sigma == Matrix([[4]])

    def test_joint_to_conditional_5(self):
        # Now the more complicated example
        # where we have multiple parent nodes
        # p(D|B, C)
        mu_x = MeansVector([
            [4],
            [9]])
        mu_y = MeansVector([[14]])
        sigma_xx = CovarianceMatrix([
            [5, 8],
            [8, 20]])
        sigma_xy = CovarianceMatrix([
            [13],
            [28]])
        sigma_yx = CovarianceMatrix([
            [13, 28]])
        sigma_yy = CovarianceMatrix([[42]])
        beta_0, beta, sigma = joint_to_conditional(
            mu_x, mu_y, sigma_xx, sigma_xy, sigma_yx, sigma_yy)
        # From page 3 :
        # f(d|b,c) ~ N(mu_D + beta_DB(b - mu_B) + beta_DC(c - mu_C), v_D)
        #              mu_D + beta_DB(b - mu_B) + beta_DC(c - mu_C
        #          ==  mu_D + beta_DB * b - beta_DB * mu_B + \
        #                 beta_DC * c - beta_DC * mu_C
        #          ==  14   + 1 * b - 1 * 4 + 1 * c - 1 * 9
        #          ==  14 + 1b - 4 + 1c -9
        #          ==  1 + 1b + 1c
        #          ==> beta_0 = 1, beta = (1  1)'
        assert beta_0 == 1
        assert beta == Matrix([[1, 1]])
        assert sigma == Matrix([[1]])

    def test_conditional_to_joint_1(self):
        # For the example in http://webdocs.cs.ualberta.ca/
        # ~greiner/C-651/SLIDES/MB08_GaussianNetworks.pdf
        # we will build up the joint parameters one by one to test...
        mu_x = MeansVector([[1]])
        sigma_x = CovarianceMatrix([[4]])
        beta_0 = -5
        beta = MeansVector([[0.5]])
        sigma_c = 4
        mu, sigma = conditional_to_joint(
            mu_x, sigma_x, beta_0, beta, sigma_c)
        assert mu == MeansVector([
            [1],
            [-4.5]])
        assert sigma == CovarianceMatrix([
            [4, 2],
            [2, 5]])

    def test_conditional_to_joint_2(self):
        # Now we want to build up the second step of the process...
        mu_x = MeansVector([
            [1],
            [-4.5]])
        sigma_x = CovarianceMatrix([
            [4, 2],
            [2, 5]])
        beta_0 = 4
        beta = MeansVector([
            [0],  # Represents no edge from x1 to x3
            [-1]])
        sigma_c = 3
        mu, sigma = conditional_to_joint(
            mu_x, sigma_x, beta_0, beta, sigma_c)
        assert mu == MeansVector([
            [1],
            [-4.5],
            [8.5]])
        assert sigma == CovarianceMatrix([
            [4, 2, -2],
            [2, 5, -5],
            [-2, -5, 8]])

    def test_conditional_to_joint_3(self):
        # Now lets do the river example...
        mu_x = MeansVector([        # This is mean(A)
            [3]])
        sigma_x = CovarianceMatrix([     # variance(A)
            [4]])
        beta_0 = 1  # See above test for joint_to_conditional mean(B|A)
        beta = MeansVector([
            [1]])   # beta_BA
        sigma_c = 1            # variance(B|A)
        # now mu and sigma will get the joint parameters for A,B
        mu, sigma = conditional_to_joint(
            mu_x, sigma_x, beta_0, beta, sigma_c)
        assert mu == MeansVector([
            [3],
            [4]])
        assert sigma == CovarianceMatrix([
            [4, 4],
            [4, 5]])

    def test_conditional_to_joint_4(self):
        # Now add Node C
        mu_x = MeansVector([
            [3],
            [4]])
        sigma_x = CovarianceMatrix([
            [4, 4],
            [4, 5]])
        beta_0 = 3
        beta = MeansVector([
            [2],  # c->a
            [0],  # c-> Not connected so 0
        ])
        sigma_c = 4       # variance(C) == variance(CA)
        # now mu and sigma will get the joint parameters for A,B
        mu, sigma = conditional_to_joint(
            mu_x, sigma_x, beta_0, beta, sigma_c)
        assert mu == MeansVector([
            [3],
            [4],
            [9]])
        assert sigma == CovarianceMatrix([
            [4, 4, 8],
            [4, 5, 8],
            [8, 8, 20]])

    def test_conditional_to_joint_5(self):
        # Test adding the d variable from the river example
        mu_x = MeansVector([
            [3],
            [4],
            [9]])
        sigma_x = CovarianceMatrix([
            [4, 4, 8],
            [4, 5, 8],
            [8, 8, 20]])
        beta_0 = 1  # See above test for joint_to_conditional
        beta = MeansVector([
            [0],    # No edge from a->c
            [1],    # beta_DB Taken directly from page 4
            [1]])   # beta_DC Taken from page 4
        sigma_c = 1
        mu, sigma = conditional_to_joint(
            mu_x, sigma_x, beta_0, beta, sigma_c)
        assert mu == MeansVector([
            [3],
            [4],
            [9],
            [14]])
        assert sigma == CovarianceMatrix([
            [4, 4, 8, 12],
            [4, 5, 8, 13],
            [8, 8, 20, 28],
            [12, 13, 28, 42]])

        # Now we will test a graph which
        # has more than 1 parentless node.
        mu_x = MeansVector([
            [3]])
        sigma_x = CovarianceMatrix([
            [4]])
        beta_0 = 5
        beta = MeansVector([[0]])
        sigma_c = 1
        mu, sigma = conditional_to_joint(
            mu_x, sigma_x, beta_0, beta, sigma_c)
        assert mu == MeansVector([[3], [5]])
        assert sigma == CovarianceMatrix([[4, 0], [0, 1]])

    def test_split(self):
        sigma = CovarianceMatrix(
            [
                [4, 4, 8, 12],
                [4, 5, 8, 13],
                [8, 8, 20, 28],
                [12, 13, 28, 42]],
            names=['a', 'b', 'c', 'd'])
        sigma_xx, sigma_xy, sigma_yx, sigma_yy = sigma.split('a')
        print sigma_xx
        print sigma_xy
        for name in ['b', 'c', 'd']:
            assert name in sigma_xx.names
            assert name in sigma_xy.names
            assert name in sigma_yx.names
            assert name not in sigma_yy.names
        assert 'a' in sigma_yy.names
        assert 'a' not in sigma_xx.names
        assert 'a' not in sigma_xy.names
        assert 'a' not in sigma_yx.names
        for row, col in xproduct(['b', 'c', 'd'], ['b', 'c', 'd']):
            assert sigma_xx[row, col] == sigma[row, col]

        # Now lets test joint to conditional...
        # Since above we already took 'a' out of sigma_xx
        # we can now just re-split and remove 'd'
        sigma_xx, sigma_xy, sigma_yx, sigma_yy = sigma_xx.split('d')
        mu_x = MeansVector([
            [4],
            [9]])
        mu_y = MeansVector([
            [14]])
        beta_0, beta, sigma = joint_to_conditional(
            mu_x, mu_y, sigma_xx, sigma_xy, sigma_yx, sigma_yy)
        assert beta_0 == 1
        assert beta == Matrix([[1, 1]])
        assert sigma == Matrix([[1]])

    def test_means_vector_equality(
            self, means_vector_a, means_vector_b,
            means_vector_c, means_vector_d):
        assert means_vector_a == means_vector_b
        assert means_vector_a != means_vector_c
        assert means_vector_a != means_vector_d

########NEW FILE########
__FILENAME__ = test_gaussian_bayesian_network
from __future__ import division
import pytest

import os

from bayesian.gaussian import MeansVector, CovarianceMatrix
from bayesian.gaussian_bayesian_network import *
from bayesian.examples.gaussian_bayesian_networks.river import (
    f_a, f_b, f_c, f_d)


def pytest_funcarg__river_graph(request):
    g = build_graph(f_a, f_b, f_c, f_d)
    return g


class TestGBN():

    def test_get_joint_parameters(self, river_graph):
        mu, sigma = river_graph.get_joint_parameters()
        assert mu == MeansVector(
            [[3],
             [4],
             [9],
             [14]],
            names=['a', 'b', 'c', 'd'])
        assert sigma == CovarianceMatrix(
            [[4, 4, 8, 12],
             [4, 5, 8, 13],
             [8, 8, 20, 28],
             [12, 13, 28, 42]],
            names=['a', 'b', 'c', 'd'])

    def test_query(self, river_graph):
        result = river_graph.query(a=7)
        mu = result['joint']['mu']
        sigma = result['joint']['sigma']
        assert mu == MeansVector([
            [8],
            [17],
            [26]], names=['b', 'c', 'd'])
        assert sigma == CovarianceMatrix(
            [[1, 0, 1],
             [0, 4, 4],
             [1, 4, 6]],
            names=['b', 'c', 'd'])

        result = river_graph.query(a=7, c=17)
        mu = result['joint']['mu']
        sigma = result['joint']['sigma']
        assert mu == MeansVector([
            [8],
            [26]], names=['b', 'd'])
        assert sigma == CovarianceMatrix(
            [[1, 1],
             [1, 2]],
            names=['b', 'd'])

        result = river_graph.query(a=7, c=17, b=8)
        mu = result['joint']['mu']
        sigma = result['joint']['sigma']
        assert mu == MeansVector([
            [26]], names=['d'])
        assert sigma == CovarianceMatrix(
            [[1]],
            names=['d'])

    def test_assignment_of_joint_parameters(self, river_graph):
        assert river_graph.nodes['b'].func.joint_mu == MeansVector([
            [3],
            [4]], names=['a', 'b'])
        assert river_graph.nodes['b'].func.covariance_matrix == CovarianceMatrix([
            [4, 4],
            [4, 5]], names=['a', 'b'])


    def test_gaussian_pdf(self, river_graph):
        assert round(river_graph.nodes['a'].func(3), 4) == 0.1995
        assert round(river_graph.nodes['a'].func(10), 4) == 0.0002

    def test_multivariate_gaussian_pdf(self, river_graph):
        assert round(river_graph.nodes['d'].func(3, 1, 3), 4) == 0.0005

########NEW FILE########
__FILENAME__ = test_gbn_examples
'''Tests for the examples in examples/gaussian_bayesian_networks'''
from bayesian.gaussian_bayesian_network import build_graph
from bayesian.examples.gaussian_bayesian_networks.river import (
    f_a, f_b, f_c, f_d)
from bayesian.linear_algebra import zeros, Matrix
from bayesian.gaussian import MeansVector, CovarianceMatrix


def pytest_funcarg__river_graph(request):
    g = build_graph(f_a, f_b, f_c, f_d)
    return g


class TestRiverExample():

    def test_get_joint_parameters(self, river_graph):
        mu, sigma = river_graph.get_joint_parameters()
        assert mu == MeansVector([
            [3],
            [4],
            [9],
            [14]], names=['a', 'b', 'c', 'd'])
        assert sigma == CovarianceMatrix([
            [4, 4, 8, 12],
            [4, 5, 8, 13],
            [8, 8, 20, 28],
            [12, 13, 28, 42]], names=['a', 'b', 'c', 'd'])

    def test_query(self, river_graph):
        r = river_graph.query(a=7)
        print r

########NEW FILE########
__FILENAME__ = test_graph
import pytest

import os

from bayesian.factor_graph import *
from bayesian.gaussian_bayesian_network import build_gbn
from bayesian.examples.gaussian_bayesian_networks.river import (
    f_a, f_b, f_c, f_d)


def pytest_funcarg__river_graph(request):
    g = build_gbn(f_a, f_b, f_c, f_d)
    return g


def fA(x1):
    if x1 is True:
        return 0.1
    elif not x1:
        return 0.9

fA.domains = dict(x1=[True, False])


def fB(x2):
    if x2 is True:
        return 0.3
    elif not x2:
        return 0.7

fB.domains = dict(x2=[True, False])


def pytest_funcarg__eliminate_var_factor(request):
    '''Get a factor to test variable elimination'''

    def factor(x1, x2, x3):
        table = dict()
        table['ttt'] = 0.05
        table['ttf'] = 0.95
        table['tft'] = 0.02
        table['tff'] = 0.98
        table['ftt'] = 0.03
        table['ftf'] = 0.97
        table['fft'] = 0.001
        table['fff'] = 0.999
        key = ''
        key = key + 't' if x1 else key + 'f'
        key = key + 't' if x2 else key + 'f'
        key = key + 't' if x3 else key + 'f'
        return table[key]

    factor.domains = dict(
        x1=[True, False],
        x2=[True, False],
        x3=[True, False])

    return factor


def fC(x1, x2, x3):
    '''
    This needs to be a joint probability distribution
    over the inputs and the node itself
    '''
    table = dict()
    table['ttt'] = 0.05
    table['ttf'] = 0.95
    table['tft'] = 0.02
    table['tff'] = 0.98
    table['ftt'] = 0.03
    table['ftf'] = 0.97
    table['fft'] = 0.001
    table['fff'] = 0.999
    key = ''
    key = key + 't' if x1 else key + 'f'
    key = key + 't' if x2 else key + 'f'
    key = key + 't' if x3 else key + 'f'
    return table[key]


fC.domains = dict(
    x1=[True, False],
    x2=[True, False],
    x3=[True, False])


def fD(x3, x4):
    table = dict()
    table['tt'] = 0.9
    table['tf'] = 0.1
    table['ft'] = 0.2
    table['ff'] = 0.8
    key = ''
    key = key + 't' if x3 else key + 'f'
    key = key + 't' if x4 else key + 'f'
    return table[key]

fD.domains = dict(
    x3=[True, False],
    x4=[True, False])


def fE(x3, x5):
    table = dict()
    table['tt'] = 0.65
    table['tf'] = 0.35
    table['ft'] = 0.3
    table['ff'] = 0.7
    key = ''
    key = key + 't' if x3 else key + 'f'
    key = key + 't' if x5 else key + 'f'
    return table[key]

fE.domains = dict(
    x3=[True, False],
    x5=[True, False])

# Build the network

fA_node = FactorNode('fA', fA)
fB_node = FactorNode('fB', fB)
fC_node = FactorNode('fC', fC)
fD_node = FactorNode('fD', fD)
fE_node = FactorNode('fE', fE)

x1 = VariableNode('x1')
x2 = VariableNode('x2')
x3 = VariableNode('x3')
x4 = VariableNode('x4')
x5 = VariableNode('x5')

connect(fA_node, x1)
connect(fB_node, x2)
connect(fC_node, [x1, x2, x3])
connect(fD_node, [x3, x4])
connect(fE_node, [x3, x5])


def test_connect():
    assert fA_node.neighbours == [x1]
    assert fB_node.neighbours == [x2]
    assert fC_node.neighbours == [x1, x2, x3]
    assert fD_node.neighbours == [x3, x4]
    assert fE_node.neighbours == [x3, x5]
    assert x1.neighbours == [fA_node, fC_node]
    assert x2.neighbours == [fB_node, fC_node]
    assert x3.neighbours == [fC_node, fD_node, fE_node]
    assert x4.neighbours == [fD_node]
    assert x5.neighbours == [fE_node]


graph = FactorGraph([x1, x2, x3, x4, x5,
                     fA_node, fB_node, fC_node, fD_node, fE_node])


def test_variable_node_is_leaf():
    assert not x1.is_leaf()
    assert not x2.is_leaf()
    assert not x3.is_leaf()
    assert x4.is_leaf()
    assert x5.is_leaf()


def test_factor_node_is_leaf():
    assert fA_node.is_leaf()
    assert fB_node.is_leaf()
    assert not fC_node.is_leaf()
    assert not fD_node.is_leaf()
    assert not fE_node.is_leaf()


def test_graph_get_leaves():
    assert graph.get_leaves() == [x4, x5, fA_node, fB_node]


# Tests at step 1
def test_graph_get_step_1_eligible_senders():
    eligible_senders = graph.get_eligible_senders()
    assert eligible_senders == [x4, x5, fA_node, fB_node]


def test_node_get_step_1_target():
    assert x1.get_target() is None
    assert x2.get_target() is None
    assert x3.get_target() is None
    assert x4.get_target() == fD_node
    assert x5.get_target() == fE_node
    assert fA_node.get_target() == x1
    assert fB_node.get_target() == x2
    assert fC_node.get_target() is None
    assert fD_node.get_target() is None
    assert fE_node.get_target() is None


def test_construct_message():
    message = x4.construct_message()
    assert message.source.name == 'x4'
    assert message.destination.name == 'fD'
    assert message.argspec == []
    assert message.factors == [1]
    message = x5.construct_message()
    assert message.source.name == 'x5'
    assert message.destination.name == 'fE'
    assert message.argspec == []
    assert message.factors == [1]
    message = fA_node.construct_message()
    assert message.source.name == 'fA'
    assert message.destination.name == 'x1'
    assert message.argspec == ['x1']
    assert message.factors == [fA_node.func]
    message = fB_node.construct_message()
    assert message.source.name == 'fB'
    assert message.destination.name == 'x2'
    assert message.argspec == ['x2']
    assert message.factors == [fB_node.func]


def test_send_message():
    message = x4.construct_message()
    x4.send(message)
    assert message.destination.received_messages['x4'] == message
    message = x5.construct_message()
    x5.send(message)
    assert message.destination.received_messages['x5'] == message
    message = fA_node.construct_message()
    fA_node.send(message)
    assert message.destination.received_messages['fA'] == message
    message = fB_node.construct_message()
    fB_node.send(message)
    assert message.destination.received_messages['fB'] == message


def test_sent_messages():
    sent = x4.get_sent_messages()
    assert sent['fD'] == fD_node.received_messages['x4']
    sent = x5.get_sent_messages()
    assert sent['fE'] == fE_node.received_messages['x5']
    sent = fA_node.get_sent_messages()
    assert sent['x1'] == x1.received_messages['fA']
    sent = fB_node.get_sent_messages()
    assert sent['x2'] == x2.received_messages['fB']


# Step 2
def test_node_get_step_2_target():
    assert x1.get_target() == fC_node
    assert x2.get_target() == fC_node


def test_graph_reset():
    graph.reset()
    for node in graph.nodes:
        assert node.received_messages == {}


def test_propagate():
    graph.reset()
    graph.propagate()
    for node in graph.nodes:
        node.message_report()


def marg(x, val, normalizer=1.0):
    return round(x.marginal(val, normalizer), 3)


def test_marginals():
    m = marg(x1, True)
    assert m == 0.1
    m = marg(x1, False)
    assert m == 0.9
    m = marg(x2, True)
    assert m == 0.3
    m = marg(x2, False)
    assert m == 0.7
    m = marg(x3, True)
    assert m == 0.012  # Note slight rounding difference to BAI
    m = marg(x3, False)
    assert m == 0.988
    m = marg(x4, True)
    assert m == 0.208
    m = marg(x4, False)
    assert m == 0.792
    m = marg(x5, True)
    assert m == 0.304
    m = marg(x5, False)
    assert m == 0.696


def test_add_evidence():
    '''
    We will set x5=True, this
    corresponds to variable D in BAI
    '''
    graph.reset()
    add_evidence(x5, True)
    graph.propagate()
    normalizer = marg(x5, True)
    assert normalizer == 0.304
    m = marg(x1, True, normalizer)
    assert m == 0.102
    m = marg(x1, False, normalizer)
    assert m == 0.898
    m = marg(x2, True, normalizer)
    assert m == 0.307
    m = marg(x2, False, normalizer)
    assert m == 0.693
    m = marg(x3, True, normalizer)
    assert m == 0.025
    m = marg(x3, False, normalizer)
    assert m == 0.975
    m = marg(x4, True, normalizer)
    assert m == 0.217
    m = marg(x4, False, normalizer)
    assert m == 0.783
    m = marg(x5, True, normalizer)
    assert m == 1.0
    m = marg(x5, False, normalizer)
    assert m == 0.0


def test_add_evidence_x2_true():
    '''
    x2 = S in BAI
    '''
    graph.reset()
    add_evidence(x2, True)
    graph.propagate()
    normalizer = marg(x2, True)
    m = marg(x1, True, normalizer)
    assert m == 0.1
    m = marg(x1, False, normalizer)
    assert m == 0.9
    m = marg(x2, True, normalizer)
    assert m == 1.0
    m = marg(x2, False, normalizer)
    assert m == 0.0
    m = marg(x3, True, normalizer)
    assert m == 0.032
    m = marg(x3, False, normalizer)
    assert m == 0.968
    m = marg(x4, True, normalizer)
    assert m == 0.222
    m = marg(x4, False, normalizer)
    assert m == 0.778
    m = marg(x5, True, normalizer)
    assert m == 0.311
    m = marg(x5, False, normalizer)
    assert m == 0.689


def test_add_evidence_x3_true():
    '''
    x3 = True in BAI this is Cancer = True
    '''
    graph.reset()
    add_evidence(x3, True)
    graph.propagate()
    normalizer = x3.marginal(True)
    m = marg(x1, True, normalizer)
    assert m == 0.249
    m = marg(x1, False, normalizer)
    assert m == 0.751
    m = marg(x2, True, normalizer)
    assert m == 0.825
    m = marg(x2, False, normalizer)
    assert m == 0.175
    m = marg(x3, True, normalizer)
    assert m == 1.0
    m = marg(x3, False, normalizer)
    assert m == 0.0
    m = marg(x4, True, normalizer)
    assert m == 0.9
    m = marg(x4, False, normalizer)
    assert m == 0.1
    m = marg(x5, True, normalizer)
    assert m == 0.650
    m = marg(x5, False, normalizer)
    assert m == 0.350


def test_add_evidence_x2_true_and_x3_true():
    '''
    x2 = True in BAI this is Smoker = True
    x3 = True in BAI this is Cancer = True
    '''
    graph.reset()
    add_evidence(x2, True)
    add_evidence(x3, True)
    graph.propagate()
    normalizer = x3.marginal(True)
    m = marg(x1, True, normalizer)
    assert m == 0.156
    m = marg(x1, False, normalizer)
    assert m == 0.844
    m = marg(x2, True, normalizer)
    assert m == 1.0
    m = marg(x2, False, normalizer)
    assert m == 0.0
    m = marg(x3, True, normalizer)
    assert m == 1.0
    m = marg(x3, False, normalizer)
    assert m == 0.0
    m = marg(x4, True, normalizer)
    assert m == 0.9
    m = marg(x4, False, normalizer)
    assert m == 0.1
    m = marg(x5, True, normalizer)
    assert m == 0.650
    m = marg(x5, False, normalizer)
    assert m == 0.350


def test_add_evidence_x5_true_x2_true():
    graph.reset()
    add_evidence(x5, True)
    add_evidence(x2, True)
    graph.propagate()
    normalizer = x5.marginal(True)
    m = marg(x1, True, normalizer)
    assert m == 0.102
    m = marg(x1, False, normalizer)
    assert m == 0.898
    m = marg(x2, True, normalizer)
    assert m == 1.0
    m = marg(x2, False, normalizer)
    assert m == 0.0
    m = marg(x3, True, normalizer)
    assert m == 0.067
    m = marg(x3, False, normalizer)
    assert m == 0.933
    m = marg(x4, True, normalizer)
    assert m == 0.247
    m = marg(x4, False, normalizer)
    assert m == 0.753
    m = marg(x5, True, normalizer)
    assert m == 1.0
    m = marg(x5, False, normalizer)
    assert m == 0.0


# Now we are going to test based on the second
# half of table 2.2 where the prior for prior
# for the Smoking parameter (x2=True) is
# set to 0.5. We start by redefining the
# PMF for fB and then rebuilding the factor
# graph


def test_marginals_table_22_part_2_x2_prior_change():
    def fB(x2):
        if x2 is True:
            return 0.5
        elif not x2:
            return 0.5
    fB.domains = dict(x2=[True, False])

    # Build the network
    fA_node = FactorNode('fA', fA)
    fB_node = FactorNode('fB', fB)
    fC_node = FactorNode('fC', fC)
    fD_node = FactorNode('fD', fD)
    fE_node = FactorNode('fE', fE)

    x1 = VariableNode('x1')
    x2 = VariableNode('x2')
    x3 = VariableNode('x3')
    x4 = VariableNode('x4')
    x5 = VariableNode('x5')

    connect(x1, [fA_node, fC_node])
    connect(x2, [fB_node, fC_node])
    connect(x3, [fC_node, fD_node, fE_node])
    connect(x4, fD_node)
    connect(x5, fE_node)

    nodes = [x1, x2, x3, x4, x5, fA_node, fB_node, fC_node, fD_node, fE_node]

    graph = FactorGraph(nodes)
    graph.propagate()
    m = marg(x1, True)
    assert m == 0.1
    m = marg(x1, False)
    assert m == 0.9
    m = marg(x2, True)
    assert m == 0.5
    m = marg(x2, False)
    assert m == 0.5
    m = marg(x3, True)
    assert m == 0.017
    m = marg(x3, False)
    assert m == 0.983
    m = marg(x4, True)
    assert m == 0.212
    m = marg(x4, False)
    assert m == 0.788
    m = marg(x5, True)
    assert m == 0.306
    m = marg(x5, False)
    assert m == 0.694

    # Now set D=T (x5=True)
    graph.reset()
    add_evidence(x5, True)
    graph.propagate()
    normalizer = marg(x5, True)
    assert normalizer == 0.306
    m = marg(x1, True, normalizer)
    assert m == 0.102
    m = marg(x1, False, normalizer)
    assert m == 0.898
    m = marg(x2, True, normalizer)
    assert m == 0.508
    m = marg(x2, False, normalizer)
    assert m == 0.492
    m = marg(x3, True, normalizer)
    assert m == 0.037
    m = marg(x3, False, normalizer)
    assert m == 0.963
    m = marg(x4, True, normalizer)
    assert m == 0.226
    m = marg(x4, False, normalizer)
    assert m == 0.774
    m = marg(x5, True, normalizer)
    assert m == 1.0
    m = marg(x5, False, normalizer)
    assert m == 0.0

    graph.reset()
    add_evidence(x2, True)
    graph.propagate()
    normalizer = marg(x2, True)
    m = marg(x1, True, normalizer)
    assert m == 0.1
    m = marg(x1, False, normalizer)
    assert m == 0.9
    m = marg(x2, True, normalizer)
    assert m == 1.0
    m = marg(x2, False, normalizer)
    assert m == 0.0
    m = marg(x3, True, normalizer)
    assert m == 0.032
    m = marg(x3, False, normalizer)
    assert m == 0.968
    m = marg(x4, True, normalizer)
    # Note that in Table 2.2 x4 and x5 marginals are reversed:
    assert m == 0.222
    m = marg(x4, False, normalizer)
    assert m == 0.778
    m = marg(x5, True, normalizer)
    assert m == 0.311
    m = marg(x5, False, normalizer)
    assert m == 0.689

    '''
    x3 = True in BAI this is Cancer = True
    '''
    graph.reset()
    add_evidence(x3, True)
    graph.propagate()
    normalizer = x3.marginal(True)
    m = marg(x1, True, normalizer)
    assert m == 0.201
    m = marg(x1, False, normalizer)
    assert m == 0.799
    m = marg(x2, True, normalizer)
    assert m == 0.917
    m = marg(x2, False, normalizer)
    assert m == 0.083
    m = marg(x3, True, normalizer)
    assert m == 1.0
    m = marg(x3, False, normalizer)
    assert m == 0.0
    m = marg(x4, True, normalizer)
    assert m == 0.9
    m = marg(x4, False, normalizer)
    assert m == 0.1
    m = marg(x5, True, normalizer)
    assert m == 0.650
    m = marg(x5, False, normalizer)
    assert m == 0.350

    '''
    x2 = True in BAI this is Smoker = True
    x3 = True in BAI this is Cancer = True
    '''
    graph.reset()
    add_evidence(x2, True)
    add_evidence(x3, True)
    graph.propagate()
    normalizer = x3.marginal(True)
    m = marg(x1, True, normalizer)
    assert m == 0.156
    m = marg(x1, False, normalizer)
    assert m == 0.844
    m = marg(x2, True, normalizer)
    assert m == 1.0
    m = marg(x2, False, normalizer)
    assert m == 0.0
    m = marg(x3, True, normalizer)
    assert m == 1.0
    m = marg(x3, False, normalizer)
    assert m == 0.0
    m = marg(x4, True, normalizer)
    assert m == 0.9
    m = marg(x4, False, normalizer)
    assert m == 0.1
    m = marg(x5, True, normalizer)
    assert m == 0.650
    m = marg(x5, False, normalizer)
    assert m == 0.350

    graph.reset()
    add_evidence(x5, True)
    add_evidence(x2, True)
    graph.propagate()
    normalizer = x5.marginal(True)
    m = marg(x1, True, normalizer)
    assert m == 0.102
    m = marg(x1, False, normalizer)
    assert m == 0.898
    m = marg(x2, True, normalizer)
    assert m == 1.0
    m = marg(x2, False, normalizer)
    assert m == 0.0
    m = marg(x3, True, normalizer)
    assert m == 0.067
    m = marg(x3, False, normalizer)
    assert m == 0.933
    m = marg(x4, True, normalizer)
    assert m == 0.247
    m = marg(x4, False, normalizer)
    assert m == 0.753
    m = marg(x5, True, normalizer)
    assert m == 1.0
    m = marg(x5, False, normalizer)
    assert m == 0.0


def test_verify_node_neighbour_type():

    def fA(x1):
        return 0.5

    fA_node = FactorNode('fA', fA)

    x1 = VariableNode('x1')

    connect(fA_node, x1)
    assert fA_node.verify_neighbour_types() is True
    assert x1.verify_neighbour_types() is True

    x2 = VariableNode('x2')
    x3 = VariableNode('x3')
    connect(x2, x3)
    assert x2.verify_neighbour_types() is False
    assert x3.verify_neighbour_types() is False


def test_verify_graph():
    def fA(x1):
        return 0.5

    def fB(x2):
        return 0.5

    fA_node = FactorNode('fA', fA)
    fB_node = FactorNode('fB', fB)

    x1 = VariableNode('x1')
    x2 = VariableNode('x2')

    connect(fA_node, x1)
    graph = FactorGraph([fA_node, x1])
    assert graph.verify() is True

    connect(fA_node, fB_node)
    graph = FactorGraph([fA_node, fB_node])
    assert graph.verify() is False

    connect(x1, x2)
    graph = FactorGraph([x1, x2])
    assert graph.verify() is False


def test_set_func_domains_from_variable_domains():
    def fA(x1):
        return 0.5

    def fB(x2):
        return 0.5

    x1 = VariableNode('x1', domain=['high', 'low'])
    fA_node = FactorNode('fA', fA)
    connect(x1, fA_node)
    graph = FactorGraph([x1, fA_node])
    assert fA_node.func.domains == dict(x1=['high', 'low'])

    x2 = VariableNode('x2')
    fB_node = FactorNode('fB', fB)
    connect(x2, fB_node)
    graph = FactorGraph([x2, fB_node])
    assert fB_node.func.domains == dict(x2=[True, False])


def test_discover_sample_ordering():

    def fActualDoor(ActualDoor):
        return 1.0 / 3

    def fGuestDoor(GuestDoor):
        return 1.0 / 3

    def fMontyDoor(ActualDoor, GuestDoor, MontyDoor):
        if ActualDoor == GuestDoor:
            if GuestDoor == MontyDoor:
                return 0
            else:
                return 0.5
        if GuestDoor == MontyDoor:
            return 0
        if ActualDoor == MontyDoor:
            return 0
        return 1

    # Build the network
    fActualDoor_node = FactorNode('fActualDoor', fActualDoor)
    fGuestDoor_node = FactorNode('fGuestDoor', fGuestDoor)
    fMontyDoor_node = FactorNode('fMontyDoor', fMontyDoor)

    ActualDoor = VariableNode('ActualDoor', ['A', 'B', 'C'])
    GuestDoor = VariableNode('GuestDoor', ['A', 'B', 'C'])
    MontyDoor = VariableNode('MontyDoor', ['A', 'B', 'C'])

    connect(fActualDoor_node, ActualDoor)
    connect(fGuestDoor_node, GuestDoor)
    connect(fMontyDoor_node, [ActualDoor, GuestDoor, MontyDoor])

    graph = FactorGraph(
        [ActualDoor,
         GuestDoor,
         MontyDoor,
         fActualDoor_node,
         fGuestDoor_node,
         fMontyDoor_node])

    assert graph.verify() is True
    ordering = graph.discover_sample_ordering()
    assert len(ordering) == 3
    assert ordering[0][0].name == 'ActualDoor'
    assert ordering[0][1].__name__ == 'fActualDoor'
    assert ordering[1][0].name == 'GuestDoor'
    assert ordering[1][1].__name__ == 'fGuestDoor'
    assert ordering[2][0].name == 'MontyDoor'
    assert ordering[2][1].__name__ == 'fMontyDoor'


def test_sample_db_filename():
    graph = FactorGraph([], name='model_1')
    home = os.path.expanduser('~')
    expected_filename = os.path.join(
        home,
        '.pypgm',
        'data',
        'model_1.sqlite')
    assert graph.sample_db_filename == expected_filename


def test_eliminate_var(eliminate_var_factor):

    eliminated = eliminate_var(eliminate_var_factor, 'x2')
    assert eliminated.argspec == ['x1', 'x3']
    assert eliminated(True, True) == 0.07


class TestGraphModule(object):

    def test_get_topological_sort(self, river_graph):
        ordering = river_graph.get_topological_sort()
        assert len(ordering) == 4
        assert ordering[0].name == 'f_a'
        assert ordering[1].name == 'f_b'
        assert ordering[2].name == 'f_c'
        assert ordering[3].name == 'f_d'

########NEW FILE########
__FILENAME__ = test_linear_algebra
'''Tests for the small backup linera algebra module'''
import pytest

from bayesian.linear_algebra import *


def pytest_funcarg__matrix_a(request):
    m = Matrix([
        [1, 2, 3],
        [4, 5, 6]
        ])
    return m


def pytest_funcarg__matrix_b(request):
    m = Matrix([
        [1, 2],
        [3, 4],
        [5, 6]
        ])
    return m


def pytest_funcarg__matrix_c(request):
    m = Matrix([
        [4, 4, 8, 12],
        [4, 5, 8, 13],
        [8, 8, 20, 28],
        [12, 13, 28, 42]
        ])
    return m

def pytest_funcarg__matrix_e(request):
    m = Matrix([
        [4, 4, 8, 12],
        [4, 5, 8, 13],
        [8, 8, 20, 28],
        [12, 13, 28, 42]
        ])
    return m

def pytest_funcarg__matrix_f(request):
    '''differs in one cell to matrix_e'''
    m = Matrix([
        [4, 4, 8, 12],
        [4, 5, 88, 13],
        [8, 8, 20, 28],
        [12, 13, 28, 42]
        ])
    return m


def pytest_funcarg__matrix_d(request):
    m = Matrix([
        [0],
        [1],
        [2],
        [3],
        [4]
        ])
    return m


def pytest_funcarg__matrix_g(request):
    m = Matrix([[-2, 2, -3],
                [-1, 1, 3],
                [2, 0, -1]])
    return m


def close_enough(a, b):
    if abs(a - b) < 0.000001:
        return True
    return False


class TestLinearAlgebra():

    def test_zeros(self):
        m = zeros((4, 4))
        assert len(m.rows) == 4
        for i in range(4):
            assert len(m.rows[i]) == 4
        for i in range(4):
            for j in range(4):
                assert m[i, j] == 0

    def test_make_identity(self):
        m = make_identity(4)
        assert len(m.rows) == 4
        for i in range(4):
            assert len(m.rows[i]) == 4
        for i in range(4):
            for j in range(4):
                if i == j:
                    assert m[i, j] == 1
                else:
                    assert m[i, j] == 0

    def test_multiply(self, matrix_a, matrix_b):
        m = matrix_a * matrix_b
        assert len(m.rows) == 2
        for i in range(2):
            assert len(m.rows[i]) == 2
        assert m[0, 0] == 22
        assert m[0, 1] == 28
        assert m[1, 0] == 49
        assert m[1, 1] == 64

        sigma_YZ = Matrix([
            [8],
            [4],
            [12]])
        sigma_ZZ = Matrix([
            [4]])
        t = sigma_YZ * sigma_ZZ.I
        assert t == Matrix([
            [2],
            [1],
            [3]])

    def test_invert(self, matrix_c):
        c_inv = matrix_c.I
        assert c_inv[0, 0] == 2.25
        assert c_inv[0, 1] == -1.0
        assert c_inv[0, 2] == -0.5
        assert close_enough(c_inv[0, 3], -2.96059473e-16)

        assert c_inv[1, 0] == -1.0
        assert c_inv[1, 1] == 2
        assert c_inv[1, 2] == 1
        assert c_inv[1, 3] == -1

        assert c_inv[2, 0] == -0.5
        assert c_inv[2, 1] == 1
        assert c_inv[2, 2] == 1.25
        assert c_inv[2, 3] == -1

        assert close_enough(c_inv[3, 0], -2.66453526e-15)
        assert c_inv[3, 1] == -1
        assert c_inv[3, 2] == -1
        assert c_inv[3, 3] == 1

    def test_slicing(self, matrix_d):
        # Note slicing is NOT YET IMPLEMENTED
        pass

    def test_equality(self, matrix_c, matrix_d,
                      matrix_e, matrix_f):
        assert matrix_c == matrix_e
        assert matrix_c != matrix_d
        assert matrix_e != matrix_f

    def test_matrix_determinant(self, matrix_g):
        d = matrix_g.det()
        assert d == 18

########NEW FILE########
__FILENAME__ = test_persistance
import pytest
from bayesian.factor_graph import *


def f_prize_door(prize_door):
    return 1.0 / 3


def f_guest_door(guest_door):
    return 1.0 / 3


def f_monty_door(prize_door, guest_door, monty_door):
    if prize_door == guest_door:
        if prize_door == monty_door:
            return 0
        else:
            return 0.5
    elif prize_door == monty_door:
        return 0
    elif guest_door == monty_door:
        return 0
    return 1


def pytest_funcarg__monty_graph(request):
    g = build_graph(
        f_prize_door,
        f_guest_door,
        f_monty_door,
        domains=dict(
            prize_door=['A', 'B', 'C'],
            guest_door=['A', 'B', 'C'],
            monty_door=['A', 'B', 'C']))
    return g


class TestPersistance():

    def test_create_sqlite_db_when_inference_method_changed(self, monty_graph):
        assert monty_graph.inference_method == 'sumproduct'
        # Now switch the inference_method to sample_db...
        monty_graph.inference_method = 'sample_db'
        assert monty_graph.inference_method == 'sample_db'

########NEW FILE########
__FILENAME__ = test_undirected_graph
import pytest

import os

from bayesian.bbn import *


def pytest_funcarg__sprinkler_graph(request):
    '''The Sprinkler Example as a moralized undirected graph
    to be used in tests.
    '''
    cloudy = Node('Cloudy')
    sprinkler = Node('Sprinkler')
    rain = Node('Rain')
    wet_grass = Node('WetGrass')
    cloudy.neighbours = [
        sprinkler, rain]
    sprinkler.neighbours = [cloudy, wet_grass]
    rain.neighbours = [cloudy, wet_grass]
    wet_grass.neighbours = [
        sprinkler,
        rain]
    graph = UndirectedGraph([
        cloudy,
        sprinkler,
        rain,
        wet_grass])
    return graph


class TestUndirectedGraph():

    def test_get_graphviz_source(self, sprinkler_graph):
        gv_src = '''graph G {
  graph [ dpi = 300 bgcolor="transparent" rankdir="LR"];
  Cloudy [ shape="ellipse" color="blue"];
  Sprinkler [ shape="ellipse" color="blue"];
  Rain [ shape="ellipse" color="blue"];
  WetGrass [ shape="ellipse" color="blue"];
  Rain -- WetGrass;
  Sprinkler -- WetGrass;
  Cloudy -- Sprinkler;
  Cloudy -- Rain;
}
'''
        assert sprinkler_graph.get_graphviz_source() == gv_src

########NEW FILE########
__FILENAME__ = utils
'''Some Useful Helper Functions'''
import inspect

from prettytable import PrettyTable

# TODO: Find a better location for get_args
def get_args(func):
    '''
    Return the names of the arguments
    of a function as a list of strings.
    This is so that we can omit certain
    variables when we marginalize.
    Note that functions created by
    make_product_func do not return
    an argspec, so we add a argspec
    attribute at creation time.
    '''
    if hasattr(func, 'argspec'):
        return func.argspec
    return inspect.getargspec(func).args


def make_key(*args):
    '''Handy for short truth table keys'''
    key = ''
    for a in args:
        if hasattr(a, 'value'):
            raise "value attribute deprecated"
        else:
            key += str(a).lower()[0]
    return key


def named_base_type_factory(v, l):
    '''Note this does not work
    for bool since bool is not
    subclassable'''
    return type(
        'labeled_{}'.format(type(v).__name__),
        (type(v), ),
        {'label': l, 'value': v})(v)


def get_original_factors(factors):
    '''
    For a set of factors, we want to
    get a mapping of the variables to
    the factor which first introduces the
    variable to the set.
    To do this without enforcing a special
    naming convention such as 'f_' for factors,
    or a special ordering, such as the last
    argument is always the new variable,
    we will have to discover the 'original'
    factor that introduces the variable
    iteratively.
    '''
    original_factors = dict()
    while len(original_factors) < len(factors):
        for factor in factors:
            args = get_args(factor)
            unaccounted_args = [a for a in args if a not in original_factors]
            if len(unaccounted_args) == 1:
                original_factors[unaccounted_args[0]] = factor
    return original_factors


def shrink_matrix(x):
    '''Remove Nulls'''
    while True:
        if len([x for x in m[0] if x is None]) == x.cols:
            x.pop()
            x = x.tr()
            continue
    return x

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Bayesian documentation build configuration file, created by
# sphinx-quickstart on Mon Jul  8 22:49:16 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.pngmath', 'sphinx.ext.mathjax', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Bayesian Belief Networks in Python Tutorial'
copyright = u'2013, Neville Newey'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1.5'
# The full version, including alpha/beta/rc tags.
release = '0.1.5'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

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

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'agogo_nn'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}
html_theme_options = {
    "textalign": "false",
}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
html_title = 'Bayesian Belief Networks in Python Tutorial'

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
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'Bayesiandoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'Bayesian.tex', u'Bayesian Documentation',
   u'Neville Newey', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'bayesian', u'Bayesian Documentation',
     [u'Neville Newey'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Bayesian', u'Bayesian Documentation',
   u'Neville Newey', 'Bayesian', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False


# -- Options for Epub output ---------------------------------------------------

# Bibliographic Dublin Core info.
epub_title = u'Bayesian'
epub_author = u'Neville Newey'
epub_publisher = u'Neville Newey'
epub_copyright = u'2013, Neville Newey'

# The language of the text. It defaults to the language option
# or en if the language is not set.
#epub_language = ''

# The scheme of the identifier. Typical schemes are ISBN or URL.
#epub_scheme = ''

# The unique identifier of the text. This can be a ISBN number
# or the project homepage.
#epub_identifier = ''

# A unique identification for the text.
#epub_uid = ''

# A tuple containing the cover image and cover page html template filenames.
#epub_cover = ()

# A sequence of (type, uri, title) tuples for the guide element of content.opf.
#epub_guide = ()

# HTML files that should be inserted before the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_pre_files = []

# HTML files shat should be inserted after the pages created by sphinx.
# The format is a list of tuples containing the path and title.
#epub_post_files = []

# A list of files that should not be packed into the epub file.
#epub_exclude_files = []

# The depth of the table of contents in toc.ncx.
#epub_tocdepth = 3

# Allow duplicate toc entries.
#epub_tocdup = True

# Fix unsupported image types using the PIL.
#epub_fix_images = False

# Scale large images.
#epub_max_image_width = 0

# If 'no', URL addresses will not be shown.
#epub_show_urls = 'inline'

# If false, no index is generated.
#epub_use_index = True

########NEW FILE########
