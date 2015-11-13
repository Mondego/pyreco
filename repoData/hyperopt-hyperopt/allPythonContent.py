__FILENAME__ = algobase
""" Support code for new-style search algorithms.
"""

__authors__ = "James Bergstra"
__license__ = "3-clause BSD License"
__contact__ = "github.com/hyperopt/hyperopt"

import copy
from collections import deque

import numpy as np

from . import pyll
from .base import (
    miscs_update_idxs_vals,
    )


class ExprEvaluator(object):
    def __init__(self, expr,
                 deepcopy_inputs=False,
                 max_program_len=None,
                 memo_gc=True):
        """
        Parameters
        ----------

        expr - pyll Apply instance to be evaluated

        deepcopy_inputs - deepcopy inputs to every node prior to calling that
            node's function on those inputs. If this leads to a different
            return value, then some function (XXX add more complete DebugMode
            functionality) in your graph is modifying its inputs and causing
            mis-calculation. XXX: This is not a fully-functional DebugMode
            because if the offender happens on account of the toposort order
            to be the last user of said input, then it will not be detected as
            a potential problem.

        max_program_len : int (default pyll.base.DEFAULT_MAX_PROGRAM_LEN)
            If more than this many nodes are evaluated in the course of
            evaluating `expr`, then evaluation is aborted under the assumption
            that an infinite recursion is underway.

        memo_gc : bool
            If True, values computed for apply nodes within `expr` may be
            cleared during computation. The bookkeeping required to do this
            takes a bit of extra time, but usually no big deal.

        """
        self.expr = pyll.as_apply(expr)
        if deepcopy_inputs not in (0, 1, False, True):
            # -- I've been calling rec_eval(expr, memo) by accident a few times
            #    this error would have been appreciated.
            #
            # TODO: Good candidate for Py3K keyword-only argument
            raise ValueError('deepcopy_inputs should be bool', deepcopy_inputs)
        self.deepcopy_inputs = deepcopy_inputs
        if max_program_len is None:
            self.max_program_len = pyll.base.DEFAULT_MAX_PROGRAM_LEN
        else:
            self.max_program_len = max_program_len
        self.memo_gc = memo_gc

    def eval_nodes(self, memo=None):
        if memo is None:
            memo = {}
        else:
            memo = dict(memo)

        # TODO: optimize dfs to not recurse past the items in memo
        #       this is especially important for evaluating Lambdas
        #       which cause rec_eval to recurse
        #
        # N.B. that Lambdas may expand the graph during the evaluation
        #      so that this iteration may be an incomplete
        if self.memo_gc:
            clients = self.clients = {}
            for aa in pyll.dfs(self.expr):
                clients.setdefault(aa, set())
                for ii in aa.inputs():
                    clients.setdefault(ii, set()).add(aa)

        todo = deque([self.expr])
        while todo:
            if len(todo) > self.max_program_len:
                raise RuntimeError('Probably infinite loop in document')
            node = todo.pop()

            if node in memo:
                # -- we've already computed this, move on.
                continue

            # -- different kinds of nodes are treated differently:
            if node.name == 'switch':
                waiting_on = self.on_switch(memo, node)
                if waiting_on is None:
                    continue
            elif isinstance(node, pyll.Literal):
                # -- constants go straight into the memo
                self.set_in_memo(memo, node, node.obj)
                continue
            else:
                # -- normal instruction-type nodes have inputs
                waiting_on = [v for v in node.inputs() if v not in memo]

            if waiting_on:
                # -- Necessary inputs have yet to be evaluated.
                #    push the node back in the queue, along with the
                #    inputs it still needs
                todo.append(node)
                todo.extend(waiting_on)
            else:
                rval = self.on_node(memo, node)
                if isinstance(rval, pyll.Apply):
                    # -- if an instruction returns a Pyll apply node
                    # it means evaluate that too. Lambdas do this.
                    #
                    # XXX: consider if it is desirable, efficient, buggy
                    #      etc. to keep using the same memo dictionary.
                    #      I think it is OK because by using the same
                    #      dictionary all of the nodes are stored in the memo
                    #      so all keys are preserved until the entire outer
                    #      function returns
                    evaluator = self.__class__(rval,
                                               self.deep_copy_inputs,
                                               self.max_program_len,
                                               self.memo_gc)
                    foo = evaluator(memo)
                    self.set_in_memo(memo, node, foo)
                else:
                    self.set_in_memo(memo, node, rval)
        return memo

    def set_in_memo(self, memo, k, v):
        """Assign memo[k] = v

        This is implementation optionally drops references to the arguments
        "clients" required to compute apply-node `k`, which allows those
        objects to be garbage-collected. This feature is enabled by
        `self.memo_gc`.

        """
        if self.memo_gc:
            assert v is not pyll.base.GarbageCollected
            memo[k] = v
            for ii in k.inputs():
                # -- if all clients of ii are already in the memo
                #    then we can free memo[ii] by replacing it
                #    with a dummy symbol
                if all(iic in memo for iic in self.clients[ii]):
                    #print 'collecting', ii
                    memo[ii] = pyll.base.GarbageCollected
        else:
            memo[k] = v

    def on_switch(self, memo, node):
        # -- pyll.base.switch is a control-flow expression.
        #
        #    It's signature is
        #       int, option0, option1, option2, ..., optionN
        #
        #    The semantics of a switch node are to only evaluate the option
        #    corresponding to the value of the leading integer. (Think of
        #    a switch block in the C language.)
        #
        #    This is a helper-function to self.eval_nodes.  It returns None,
        #    or a list of apply-nodes required to evaluate the given switch
        #    node.
        #
        #    When it returns None, the memo has been updated so that
        #    memo[`node`] has been assigned the computed value for the given
        #    switch node.
        #
        switch_i_var = node.pos_args[0]
        if switch_i_var in memo:
            switch_i = memo[switch_i_var]
            try:
                int(switch_i)
            except:
                raise TypeError('switch argument was', switch_i)
            if switch_i != int(switch_i) or switch_i < 0:
                raise ValueError('switch pos must be positive int',
                                 switch_i)
            rval_var = node.pos_args[switch_i + 1]
            if rval_var in memo:
                self.set_in_memo(memo, node, memo[rval_var])
                return
            else:
                return [rval_var]
        else:
            return [switch_i_var]

    def on_node(self, memo, node):
        # -- Retrieve computed arguments of apply node
        args = _args = [memo[v] for v in node.pos_args]
        kwargs = _kwargs = dict([(k, memo[v])
                                 for (k, v) in node.named_args])

        if self.memo_gc:
            # -- Ensure no computed argument has been (accidentally) freed for
            #    garbage-collection.
            for aa in args + kwargs.values():
                assert aa is not pyll.base.GarbageCollected

        if self.deepcopy_inputs:
            # -- I think this is supposed to be skipped if node.pure == True
            #    because that attribute is supposed to mark the node as having
            #    no side-effects that affect expression-evaluation.
            #
            #    HOWEVER That has not been tested in a while, and it's hard to
            #    verify (with e.g. unit tests) that a node marked "pure" isn't
            #    lying. So we hereby ignore the `pure` attribute and copy
            #    everything to be on the safe side.
            args = copy.deepcopy(_args)
            kwargs = copy.deepcopy(_kwargs)

        return pyll.scope._impls[node.name](*args, **kwargs)


class SuggestAlgo(ExprEvaluator):
    """Add constructor and call signature to match suggest()

    Also, detect when on_node is handling a hyperparameter, and
    delegate that to an `on_node_hyperparameter` method. This method
    must be implemented by a derived class.
    """
    def __init__(self, domain, trials, seed):
        ExprEvaluator.__init__(self, domain.s_idxs_vals)
        self.domain = domain
        self.trials = trials
        self.label_by_node = dict([
            (n, l) for l, n in self.domain.vh.vals_by_label().items()])
        self._seed = seed
        self.rng = np.random.RandomState(seed)

    def __call__(self, new_id):
        self.rng.seed(self._seed + new_id)
        memo = self.eval_nodes(
            memo={
                self.domain.s_new_ids: [new_id],
                self.domain.s_rng: self.rng,
            })
        idxs, vals = memo[self.expr]
        new_result = self.domain.new_result()
        new_misc = dict(
            tid=new_id,
            cmd=self.domain.cmd,
            workdir=self.domain.workdir)
        miscs_update_idxs_vals([new_misc], idxs, vals)
        rval = self.trials.new_trial_docs(
            [new_id], [None], [new_result], [new_misc])
        return rval

    def on_node(self, memo, node):
        if node in self.label_by_node:
            label = self.label_by_node[node]
            return self.on_node_hyperparameter(memo, node, label)
        else:
            return ExprEvaluator.on_node(self, memo, node)

    def batch(self, new_ids):
        new_ids = list(new_ids)
        self.rng.seed([self._seed] + new_ids)
        memo = self.eval_nodes(
            memo={
                self.domain.s_new_ids: new_ids,
                self.domain.s_rng: self.rng,
            })
        idxs, vals = memo[self.expr]
        return idxs, vals

# -- flake-8 abhors blank line EOF

########NEW FILE########
__FILENAME__ = anneal
"""
Annealing algorithm for hyperopt

Annealing is a simple but effective variant on random search that
takes some advantage of a smooth response surface.

The simple (but not overly simple) code of simulated annealing makes this file
a good starting point for implementing new search algorithms.

"""

__authors__ = "James Bergstra"
__license__ = "3-clause BSD License"
__contact__ = "github.com/hyperopt/hyperopt"

import logging

import numpy as np
from pyll.stochastic import (
    # -- integer
    categorical,
    # randint, -- unneeded
    # -- normal
    normal,
    lognormal,
    qnormal,
    qlognormal,
    # -- uniform
    uniform,
    loguniform,
    quniform,
    qloguniform,
    )
from .base import miscs_to_idxs_vals
from .algobase import (
    SuggestAlgo,
    ExprEvaluator,
    )

logger = logging.getLogger(__name__)


class AnnealingAlgo(SuggestAlgo):
    """
    This simple annealing algorithm begins by sampling from the prior,
    but tends over time to sample from points closer and closer to the best
    ones observed.

    In addition to the value of this algorithm as a baseline optimization
    strategy, it is a simple starting point for implementing new algorithms.

    # The Annealing Algorithm

    The annealing algorithm is to choose one of the previous trial points
    as a starting point, and then to sample each hyperparameter from a similar
    distribution to the one specified in the prior, but whose density is more
    concentrated around the trial point we selected.

    This algorithm is a simple variation on random search that leverages
    smoothness in the response surface.  The annealing rate is not adaptive.

    ## Choosing a Best Trial

    The algorithm formalizes the notion of "one of the best trials" by
    sampling a position from a geometric distribution whose mean is the
    `avg_best_idx` parameter.  The "best trial" is the trial thus selected
    from the set of all trials (`self.trials`).

    It may happen that in the process of ancestral sampling, we may find that
    the best trial at some ancestral point did not use the hyperparameter we
    need to draw.  In such a case, this algorithm will draw a new "runner up"
    best trial, and use that one as if it had been chosen as the best trial.

    The set of best trials, and runner-up best trials obtained during the
    process of choosing all hyperparameters is kept sorted by the validation
    loss, and at each point where the best trial does not define a
    required hyperparameter value, we actually go through all the list of
    runners-up too, before giving up and adding a new runner-up trial.


    ## Concentrating Prior Distributions

    To sample a hyperparameter X within a search space, we look at
    what kind of hyperparameter it is (what kind of distribution it's from)
    and the previous successful values of that hyperparameter, and make
    a new proposal for that hyperparameter independently of other
    hyperparameters (except technically any choice nodes that led us to use
    this current hyperparameter in the first place).

    For example, if X is a uniform-distributed hyperparameters drawn from
    `U(l, h)`, we look at the value `x` of the hyperparameter in the selected
    trial, and draw from a new uniform density `U(x - w/2, x + w/2)`, where w
    is related to the initial range, and the number of observations we have for
    X so far. If W is the initial range, and T is the number of observations
    we have, then w = W / (1 + T * shrink_coef).  If the resulting range would
    extend either below l or above h, we shift it to fit into the original
    bounds.

    """

    def __init__(self, domain, trials, seed,
                 avg_best_idx=2.0,
                 shrink_coef=0.1):
        """
        Parameters
        ----------
        avg_best_idx: float
            Mean of geometric distribution over which trial to explore around,
            selecting from trials sorted by score (0 is best)

        shrink_coef: float
            Rate of reduction in the size of sampling neighborhood as more
            points have been explored.
        """
        SuggestAlgo.__init__(self, domain, trials, seed=seed)
        self.avg_best_idx = avg_best_idx
        self.shrink_coef = shrink_coef
        doc_by_tid = {}
        for doc in trials.trials:
            # get either this docs own tid or the one that it's from
            tid = doc['tid']
            loss = domain.loss(doc['result'], doc['spec'])
            if loss is None:
                # -- associate infinite loss to new/running/failed jobs
                loss = float('inf')
            else:
                loss = float(loss)
            doc_by_tid[tid] = (doc, loss)
        self.tid_docs_losses = sorted(doc_by_tid.items())
        self.tids = np.asarray([t for (t, (d, l)) in self.tid_docs_losses])
        self.losses = np.asarray([l for (t, (d, l)) in self.tid_docs_losses])
        self.tid_losses_dct = dict(zip(self.tids, self.losses))
        # node_tids: dict from hp label -> trial ids (tids) using that hyperparam
        # node_vals: dict from hp label -> values taken by that hyperparam
        self.node_tids, self.node_vals = miscs_to_idxs_vals(
            [d['misc'] for (tid, (d, l)) in self.tid_docs_losses],
            keys=domain.params.keys())
        self.best_tids = []

    def shrinking(self, label):
        """Return fraction of original search width

        Parameters
        ----------
        label: string
            the name of a hyperparameter
        """
        T = len(self.node_vals[label])
        return 1.0 / (1.0 + T * self.shrink_coef)

    def choose_ltv(self, label, size):
        """Returns (loss, tid, val) of best/runner-up trial
        """
        tids = self.node_tids[label]
        vals = self.node_vals[label]
        losses = [self.tid_losses_dct[tid] for tid in tids]

        if size == 1:
            # -- try to return the value corresponding to one of the
            #    trials that was previously chosen (non-independence
            #    of hyperparameter values)
            # This doesn't really make sense if we're sampling a lot of
            # points at a time.
            tid_set = set(tids)
            for tid in self.best_tids:
                if tid in tid_set:
                    idx = tids.index(tid)
                    rval = losses[idx], tid, vals[idx]
                    return rval

        # -- choose a new good seed point
        good_idx = self.rng.geometric(1.0 / self.avg_best_idx, size=size) - 1
        good_idx = np.clip(good_idx, 0, len(tids) - 1).astype('int32')

        picks = np.argsort(losses)[good_idx]
        picks_loss = np.asarray(losses)[picks]
        picks_tids = np.asarray(tids)[picks]
        picks_vals = np.asarray(vals)[picks]

        #ltvs = np.asarray(sorted(zip(losses, tids, vals)))
        #best_loss, best_tid, best_val = ltvs[best_idx]
        if size == 1:
            self.best_tids.append(int(picks_tids))
        return picks_loss, picks_tids, picks_vals

    def on_node_hyperparameter(self, memo, node, label):
        """
        Return a new value for one hyperparameter.

        Parameters:
        -----------

        memo - a partially-filled dictionary of node -> list-of-values
               for the nodes in a vectorized representation of the
               original search space.

        node - an Apply instance in the vectorized search space,
               which corresponds to a hyperparameter

        label - a string, the name of the hyperparameter


        Returns: a list with one value in it: the suggested value for this
        hyperparameter


        Notes
        -----

        This function works by delegating to self.hp_HPTYPE functions to
        handle each of the kinds of hyperparameters in hyperopt.pyll_utils.

        Other search algorithms can implement this function without
        delegating based on the hyperparameter type, but it's a pattern
        I've used a few times so I show it here.

        """
        n_observations = len(self.node_vals[label])
        if n_observations > 0:
            # -- Pick a previous trial on which to base the new sample
            size = memo[node.arg['size']]
            loss, tid, val = self.choose_ltv(label, size=size)
            try:
                handler = getattr(self, 'hp_%s' % node.name)
            except AttributeError:
                raise NotImplementedError('Annealing', node.name)
            return handler(memo, node, label, tid, val)
        else:
            # -- Draw the new sample from the prior
            return ExprEvaluator.on_node(self, memo, node)

    def hp_uniform(self, memo, node, label, tid, val,
                   log_scale=False,
                   pass_q=False,
                   uniform_like=uniform):
        """
        Return a new value for a uniform hyperparameter.

        Parameters:
        -----------

        memo - (see on_node_hyperparameter)

        node - (see on_node_hyperparameter)

        label - (see on_node_hyperparameter)

        tid - trial-identifier of the model trial on which to base a new sample

        val - the value of this hyperparameter on the model trial

        Returns: a list with one value in it: the suggested value for this
        hyperparameter
        """
        if log_scale:
            midpt = np.log(val)
        else:
            midpt = val
        high = memo[node.arg['high']]
        low = memo[node.arg['low']]
        width = (high - low) * self.shrinking(label)
        half = .5 * width
        min_midpt = low + half
        max_midpt = high - half
        clipped_midpt = np.clip(midpt, min_midpt, max_midpt)

        #if pass_q:
        #    assert low <= val <= high, (low, val, high)
        #else:
        #    val = min(high, max(val, low))
        #new_high = min(high, val + width / 2)
        #if new_high == high:
        #    new_low = new_high - width
        #else:
        #    new_low = max(low, val - width / 2)
        #    if new_low == low:
        #        new_high = min(high, new_low + width)
        #assert low <= new_low <= new_high <= high
        if pass_q:
            return uniform_like(
                low=clipped_midpt - half,
                high=clipped_midpt + half,
                rng=self.rng,
                q=memo[node.arg['q']],
                size=memo[node.arg['size']])
        else:
            return uniform_like(
                low=clipped_midpt - half,
                high=clipped_midpt + half,
                rng=self.rng,
                size=memo[node.arg['size']])

    def hp_quniform(self, *args, **kwargs):
        return self.hp_uniform(
            pass_q=True,
            uniform_like=quniform,
            *args,
            **kwargs)

    def hp_loguniform(self, *args, **kwargs):
        return self.hp_uniform(
            log_scale=True,
            pass_q=False,
            uniform_like=loguniform,
            *args,
            **kwargs)

    def hp_qloguniform(self, *args, **kwargs):
        return self.hp_uniform(
            log_scale=True,
            pass_q=True,
            uniform_like=qloguniform,
            *args,
            **kwargs)

    def hp_randint(self, memo, node, label, tid, val):
        """
        Parameters: See `hp_uniform`
        """
        upper = memo[node.arg['upper']]
        val1 = np.atleast_1d(val)
        if val1.size:
            counts = np.bincount(val1, minlength=upper) / float(val1.size)
        else:
            counts = np.zeros(upper)
            prior = 1.0
        prior = self.shrinking(label)
        p = (1 - prior) * counts + prior * (1.0 / upper)
        rval = categorical(p=p, upper=upper, rng=self.rng,
                           size=memo[node.arg['size']])
        return rval

    def hp_categorical(self, memo, node, label, tid, val):
        """
        Parameters: See `hp_uniform`
        """
        size = memo[node.arg['size']]
        if size == 0:
            return []
        val1 = np.atleast_1d(val)
        p = p_orig = np.asarray(memo[node.arg['p']])
        if p.ndim == 2:
            if len(p) not in (1, len(val1)):
                print node
                print p
                print np.asarray(p).shape
            assert len(p) in (1, len(val1))
        else:
            assert p.ndim == 1
            p = p[np.newaxis, :]
        upper = memo[node.arg['upper']]
        if val1.size:
            counts = np.bincount(val1, minlength=upper) / float(val1.size)
            prior = self.shrinking(label)
        else:
            counts = np.zeros(upper)
            prior = 1.0
        new_p = (1 - prior) * counts + prior * p
        assert new_p.ndim == 2
        rval = categorical(p=new_p, rng=self.rng, size=size)
        if p_orig.ndim == 1:
            assert len(rval) == 1
            return rval[0]
        else:
            return rval

    def hp_normal(self, memo, node, label, tid, val):
        """
        Parameters: See `hp_uniform`
        """
        return normal(
            mu=val,
            sigma=memo[node.arg['sigma']] * self.shrinking(label),
            rng=self.rng,
            size=memo[node.arg['size']])

    def hp_lognormal(self, memo, node, label, tid, val):
        """
        Parameters: See `hp_uniform`
        """
        return lognormal(
            mu=np.log(val),
            sigma=memo[node.arg['sigma']] * self.shrinking(label),
            rng=self.rng,
            size=memo[node.arg['size']])

    def hp_qlognormal(self, memo, node, label, tid, val):
        """
        Parameters: See `hp_uniform`
        """
        return qlognormal(
            # -- prevent log(0) without messing up algo
            mu=np.log(1e-16 + val),
            sigma=memo[node.arg['sigma']] * self.shrinking(label),
            q=memo[node.arg['q']],
            rng=self.rng,
            size=memo[node.arg['size']])

    def hp_qnormal(self, memo, node, label, tid, val):
        """
        Parameters: See `hp_uniform`
        """
        return qnormal(
            mu=val,
            sigma=memo[node.arg['sigma']] * self.shrinking(label),
            q=memo[node.arg['q']],
            rng=self.rng,
            size=memo[node.arg['size']])


def suggest(new_ids, domain, trials, seed, *args, **kwargs):
    new_id, = new_ids
    return AnnealingAlgo(domain, trials, seed, *args, **kwargs)(new_id)


def suggest_batch(new_ids, domain, trials, seed, *args, **kwargs):
    return AnnealingAlgo(domain, trials, seed, *args, **kwargs).batch(new_ids)

# -- flake-8 abhors blank line EOF

########NEW FILE########
__FILENAME__ = base
"""Base classes / Design

The design is that there are three components fitting together in this project:

- Trials - a list of documents including at least sub-documents:
    ['spec'] - the specification of hyper-parameters for a job
    ['result'] - the result of Domain.evaluate(). Typically includes:
        ['status'] - one of the STATUS_STRINGS
        ['loss'] - real-valued scalar that hyperopt is trying to minimize
    ['idxs'] - compressed representation of spec
    ['vals'] - compressed representation of spec
    ['tid'] - trial id (unique in Trials list)

- Domain - specifies a search problem

- Ctrl - a channel for two-way communication
         between an Experiment and Domain.evaluate.
         Experiment subclasses may subclass Ctrl to match. For example, if an
         experiment is going to dispatch jobs in other threads, then an
         appropriate thread-aware Ctrl subclass should go with it.

"""

__authors__ = "James Bergstra"
__license__ = "3-clause BSD License"
__contact__ = "github.com/hyperopt/hyperopt"

import logging
import datetime
import os
import sys

import numpy as np

import bson  # -- comes with pymongo
from bson.objectid import ObjectId

import pyll
#from pyll import scope  # looks unused but
from pyll.stochastic import recursive_set_rng_kwarg

from .exceptions import (
    DuplicateLabel, InvalidTrial, InvalidResultStatus, InvalidLoss)
from .utils import pmin_sampled
from .utils import use_obj_for_literal_in_memo
from .vectorize import VectorizeHelper

logger = logging.getLogger(__name__)


# -- STATUS values
#    An eval_fn returning a dictionary must have a status key with
#    one of these values. They are used by optimization routines
#    and plotting functions.

STATUS_NEW = 'new'
STATUS_RUNNING = 'running'
STATUS_SUSPENDED = 'suspended'
STATUS_OK = 'ok'
STATUS_FAIL = 'fail'
STATUS_STRINGS = (
    'new',        # computations have not started
    'running',    # computations are in prog
    'suspended',  # computations have been suspended, job is not finished
    'ok',         # computations are finished, terminated normally
    'fail')       # computations are finished, terminated with error
                  #   - result['status_fail'] should contain more info


# -- JOBSTATE values
# These are used internally by the scheduler.
# These values are used to communicate between an Experiment
# and a worker process. Consider moving them to mongoexp.

# -- named constants for job execution pipeline
JOB_STATE_NEW = 0
JOB_STATE_RUNNING = 1
JOB_STATE_DONE = 2
JOB_STATE_ERROR = 3
JOB_STATES = [
    JOB_STATE_NEW,
    JOB_STATE_RUNNING,
    JOB_STATE_DONE,
    JOB_STATE_ERROR]


TRIAL_KEYS = [
    'tid',
    'spec',
    'result',
    'misc',
    'state',
    'owner',
    'book_time',
    'refresh_time',
    'exp_key']

TRIAL_MISC_KEYS = [
    'tid',
    'cmd',
    'idxs',
    'vals']


def _all_same(*args):
    return 1 == len(set(args))


def SONify(arg, memo=None):
    add_arg_to_raise = True
    try:
        if memo is None:
            memo = {}
        if id(arg) in memo:
            rval = memo[id(arg)]
        if isinstance(arg, ObjectId):
            rval = arg
        elif isinstance(arg, datetime.datetime):
            rval = arg
        elif isinstance(arg, np.floating):
            rval = float(arg)
        elif isinstance(arg, np.integer):
            rval = int(arg)
        elif isinstance(arg, (list, tuple)):
            rval = type(arg)([SONify(ai, memo) for ai in arg])
        elif isinstance(arg, dict):
            rval = dict(
                [(SONify(k, memo), SONify(v, memo)) for k, v in arg.items()])
        elif isinstance(arg, (basestring, float, int, long, type(None))):
            rval = arg
        elif isinstance(arg, np.ndarray):
            if arg.ndim == 0:
                rval = SONify(arg.sum())
            else:
                rval = map(SONify, arg)  # N.B. memo None
        # -- put this after ndarray because ndarray not hashable
        elif arg in (True, False):
            rval = int(arg)
        else:
            add_arg_to_raise = False
            raise TypeError('SONify', arg)
    except Exception, e:
        if add_arg_to_raise:
            e.args = e.args + (arg,)
        raise
    memo[id(rval)] = rval
    return rval


def miscs_update_idxs_vals(miscs, idxs, vals,
                           assert_all_vals_used=True,
                           idxs_map=None):
    """
    Unpack the idxs-vals format into the list of dictionaries that is
    `misc`.

    idxs_map: a dictionary of id->id mappings so that the misc['idxs'] can
        contain different numbers than the idxs argument. XXX CLARIFY
    """
    if idxs_map is None:
        idxs_map = {}

    assert set(idxs.keys()) == set(vals.keys())

    misc_by_id = dict([(m['tid'], m) for m in miscs])
    for m in miscs:
        m['idxs'] = dict([(key, []) for key in idxs])
        m['vals'] = dict([(key, []) for key in idxs])

    for key in idxs:
        assert len(idxs[key]) == len(vals[key])
        for tid, val in zip(idxs[key], vals[key]):
            tid = idxs_map.get(tid, tid)
            if assert_all_vals_used or tid in misc_by_id:
                misc_by_id[tid]['idxs'][key] = [tid]
                misc_by_id[tid]['vals'][key] = [val]

    return miscs


def miscs_to_idxs_vals(miscs, keys=None):
    if keys is None:
        if len(miscs) == 0:
            raise ValueError('cannot infer keys from empty miscs')
        keys = miscs[0]['idxs'].keys()
    idxs = dict([(k, []) for k in keys])
    vals = dict([(k, []) for k in keys])
    for misc in miscs:
        for node_id in idxs:
            t_idxs = misc['idxs'][node_id]
            t_vals = misc['vals'][node_id]
            assert len(t_idxs) == len(t_vals)
            assert t_idxs == [] or t_idxs == [misc['tid']]
            idxs[node_id].extend(t_idxs)
            vals[node_id].extend(t_vals)
    return idxs, vals


def spec_from_misc(misc):
    spec = {}
    for k, v in misc['vals'].items():
        if len(v) == 0:
            pass
        elif len(v) == 1:
            spec[k] = v[0]
        else:
            raise NotImplementedError('multiple values', (k, v))
    return spec


class Trials(object):
    """Database interface supporting data-driven model-based optimization.

    The model-based optimization algorithms used by hyperopt's fmin function
    work by analyzing samples of a response surface--a history of what points
    in the search space were tested, and what was discovered by those tests.
    A Trials instance stores that history and makes it available to fmin and
    to the various optimization algorithms.

    This class (`base.Trials`) is a pure-Python implementation of the database
    in terms of lists of dictionaries.  Subclass `mongoexp.MongoTrials`
    implements the same API in terms of a mongodb database running in another
    process. Other subclasses may be implemented in future.

    The elements of `self.trials` represent all of the completed, in-progress,
    and scheduled evaluation points from an e.g. `fmin` call.

    Each element of `self.trials` is a dictionary with *at least* the following
    keys:

    * **tid**: a unique trial identification object within this Trials instance
      usually it is an integer, but it isn't obvious that other sortable,
      hashable objects couldn't be used at some point.

    * **result**: a sub-dictionary representing what was returned by the fmin
      evaluation function. This sub-dictionary has a key 'status' with a value
      from `STATUS_STRINGS` and the status is `STATUS_OK`, then there should be
      a 'loss' key as well with a floating-point value.  Other special keys in
      this sub-dictionary may be used by optimization algorithms  (see them
      for details). Other keys in this sub-dictionary can be used by the
      evaluation function to store miscelaneous diagnostics and debugging
      information.

    * **misc**: despite generic name, this is currently where the trial's
      hyperparameter assigments are stored. This sub-dictionary has two
      elements: `'idxs'` and `'vals'`. The `vals` dictionary is
      a sub-sub-dictionary mapping each hyperparameter to either `[]` (if the
      hyperparameter is inactive in this trial), or `[<val>]` (if the
      hyperparameter is active). The `idxs` dictionary is technically
      redundant -- it is the same as `vals` but it maps hyperparameter names
      to either `[]` or `[<tid>]`.

    """

    async = False

    def __init__(self, exp_key=None, refresh=True):
        self._ids = set()
        self._dynamic_trials = []
        self._exp_key = exp_key
        self.attachments = {}
        if refresh:
            self.refresh()

    def view(self, exp_key=None, refresh=True):
        rval = object.__new__(self.__class__)
        rval._exp_key = exp_key
        rval._ids = self._ids
        rval._dynamic_trials = self._dynamic_trials
        rval.attachments = self.attachments
        if refresh:
            rval.refresh()
        return rval

    def aname(self, trial, name):
        return 'ATTACH::%s::%s' % (trial['tid'], name)

    def trial_attachments(self, trial):
        """
        Support syntax for load:  self.trial_attachments(doc)[name]
        # -- does this work syntactically?
        #    (In any event a 2-stage store will work)
        Support syntax for store: self.trial_attachments(doc)[name] = value
        """

        # don't offer more here than in MongoCtrl
        class Attachments(object):
            def __contains__(_self, name):
                return self.aname(trial, name) in self.attachments

            def __getitem__(_self, name):
                return self.attachments[self.aname(trial, name)]

            def __setitem__(_self, name, value):
                self.attachments[self.aname(trial, name)] = value

            def __delitem__(_self, name):
                del self.attachments[self.aname(trial, name)]

        return Attachments()

    def __iter__(self):
        try:
            return iter(self._trials)
        except AttributeError:
            print >> sys.stderr, "You have to refresh before you iterate"
            raise

    def __len__(self):
        try:
            return len(self._trials)
        except AttributeError:
            print >> sys.stderr, "You have to refresh before you compute len"
            raise

    def __getitem__(self, item):
        # -- how to make it obvious whether indexing is by _trials position
        #    or by tid if both are integers?
        raise NotImplementedError('')

    def refresh(self):
        # In MongoTrials, this method fetches from database
        if self._exp_key is None:
            self._trials = [
                tt for tt in self._dynamic_trials
                if tt['state'] != JOB_STATE_ERROR]
        else:
            self._trials = [tt
                            for tt in self._dynamic_trials
                            if (tt['state'] != JOB_STATE_ERROR
                                and tt['exp_key'] == self._exp_key)]
        self._ids.update([tt['tid'] for tt in self._trials])

    @property
    def trials(self):
        return self._trials

    @property
    def tids(self):
        return [tt['tid'] for tt in self._trials]

    @property
    def specs(self):
        return [tt['spec'] for tt in self._trials]

    @property
    def results(self):
        return [tt['result'] for tt in self._trials]

    @property
    def miscs(self):
        return [tt['misc'] for tt in self._trials]

    @property
    def idxs_vals(self):
        return miscs_to_idxs_vals(self.miscs)

    @property
    def idxs(self):
        return self.idxs_vals[0]

    @property
    def vals(self):
        return self.idxs_vals[1]

    def assert_valid_trial(self, trial):
        if not (hasattr(trial, 'keys') and hasattr(trial, 'values')):
            raise InvalidTrial('trial should be dict-like', trial)
        for key in TRIAL_KEYS:
            if key not in trial:
                raise InvalidTrial('trial missing key %s', key)
        for key in TRIAL_MISC_KEYS:
            if key not in trial['misc']:
                raise InvalidTrial('trial["misc"] missing key', key)
        if trial['tid'] != trial['misc']['tid']:
            raise InvalidTrial(
                'tid mismatch between root and misc',
                trial)
        # -- check for SON-encodable
        try:
            bson.BSON.encode(trial)
        except:
            # TODO: save the trial object somewhere to inspect, fix, re-insert
            #       so that precious data is not simply deallocated and lost.
            print '-' * 80
            print "CANT ENCODE"
            print '-' * 80
            raise
        if trial['exp_key'] != self._exp_key:
            raise InvalidTrial('wrong exp_key',
                               (trial['exp_key'], self._exp_key))
        # XXX how to assert that tids are unique?
        return trial

    def _insert_trial_docs(self, docs):
        """insert with no error checking
        """
        rval = [doc['tid'] for doc in docs]
        self._dynamic_trials.extend(docs)
        return rval

    def insert_trial_doc(self, doc):
        """insert trial after error checking

        Does not refresh. Call self.refresh() for the trial to appear in
        self.specs, self.results, etc.
        """
        doc = self.assert_valid_trial(SONify(doc))
        return self._insert_trial_docs([doc])[0]
        # refreshing could be done fast in this base implementation, but with
        # a real DB the steps should be separated.

    def insert_trial_docs(self, docs):
        """ trials - something like is returned by self.new_trial_docs()
        """
        docs = [self.assert_valid_trial(SONify(doc))
                for doc in docs]
        return self._insert_trial_docs(docs)

    def new_trial_ids(self, N):
        aa = len(self._ids)
        rval = range(aa, aa + N)
        self._ids.update(rval)
        return rval

    def new_trial_docs(self, tids, specs, results, miscs):
        assert len(tids) == len(specs) == len(results) == len(miscs)
        rval = []
        for tid, spec, result, misc in zip(tids, specs, results, miscs):
            doc = dict(
                state=JOB_STATE_NEW,
                tid=tid,
                spec=spec,
                result=result,
                misc=misc)
            doc['exp_key'] = self._exp_key
            doc['owner'] = None
            doc['version'] = 0
            doc['book_time'] = None
            doc['refresh_time'] = None
            rval.append(doc)
        return rval

    def source_trial_docs(self, tids, specs, results, miscs, sources):
        assert _all_same(map(len, [tids, specs, results, miscs, sources]))
        rval = []
        for tid, spec, result, misc, source in zip(tids, specs, results, miscs,
                                                   sources):
            doc = dict(
                version=0,
                tid=tid,
                spec=spec,
                result=result,
                misc=misc,
                state=source['state'],
                exp_key=source['exp_key'],
                owner=source['owner'],
                book_time=source['book_time'],
                refresh_time=source['refresh_time'],
                )
            # -- ensure that misc has the following fields,
            #    some of which may already by set correctly.
            assign = ('tid', tid), ('cmd', None), ('from_tid', source['tid'])
            for k, v in assign:
                assert doc['misc'].setdefault(k, v) == v
            rval.append(doc)
        return rval

    def delete_all(self):
        self._dynamic_trials = []
        self.attachments = {}
        self.refresh()

    def count_by_state_synced(self, arg, trials=None):
        """
        Return trial counts by looking at self._trials
        """
        if trials is None:
            trials = self._trials
        if arg in JOB_STATES:
            queue = [doc for doc in trials if doc['state'] == arg]
        elif hasattr(arg, '__iter__'):
            states = set(arg)
            assert all([x in JOB_STATES for x in states])
            queue = [doc for doc in trials if doc['state'] in states]
        else:
            raise TypeError(arg)
        rval = len(queue)
        return rval

    def count_by_state_unsynced(self, arg):
        """
        Return trial counts that count_by_state_synced would return if we
        called refresh() first.
        """
        if self._exp_key is not None:
            exp_trials = [tt
                          for tt in self._dynamic_trials
                          if tt['exp_key'] == self._exp_key]
        else:
            exp_trials = self._dynamic_trials
        return self.count_by_state_synced(arg, trials=exp_trials)

    def losses(self, bandit=None):
        if bandit is None:
            return [r.get('loss') for r in self.results]
        else:
            return map(bandit.loss, self.results, self.specs)

    def statuses(self, bandit=None):
        if bandit is None:
            return [r.get('status') for r in self.results]
        else:
            return map(bandit.status, self.results, self.specs)

    def average_best_error(self, bandit=None):
        """Return the average best error of the experiment

        Average best error is defined as the average of bandit.true_loss,
        weighted by the probability that the corresponding bandit.loss is best.

        For domains with loss measurement variance of 0, this function simply
        returns the true_loss corresponding to the result with the lowest loss.
        """

        if bandit is None:
            results = self.results
            loss = [r['loss']
                    for r in results if r['status'] == STATUS_OK]
            loss_v = [r.get('loss_variance', 0)
                      for r in results if r['status'] == STATUS_OK]
            true_loss = [r.get('true_loss', r['loss'])
                         for r in results if r['status'] == STATUS_OK]
        else:
            def fmap(f):
                rval = np.asarray([
                    f(r, s)
                    for (r, s) in zip(self.results, self.specs)
                    if bandit.status(r) == STATUS_OK]).astype('float')
                if not np.all(np.isfinite(rval)):
                    raise ValueError()
                return rval
            loss = fmap(bandit.loss)
            loss_v = fmap(bandit.loss_variance)
            true_loss = fmap(bandit.true_loss)
        loss3 = zip(loss, loss_v, true_loss)
        if not loss3:
            raise ValueError('Empty loss vector')
        loss3.sort()
        loss3 = np.asarray(loss3)
        if np.all(loss3[:, 1] == 0):
            best_idx = np.argmin(loss3[:, 0])
            return loss3[best_idx, 2]
        else:
            cutoff = 0
            sigma = np.sqrt(loss3[0][1])
            while (cutoff < len(loss3)
                    and loss3[cutoff][0] < loss3[0][0] + 3 * sigma):
                cutoff += 1
            pmin = pmin_sampled(loss3[:cutoff, 0], loss3[:cutoff, 1])
            #print pmin
            #print loss3[:cutoff, 0]
            #print loss3[:cutoff, 1]
            #print loss3[:cutoff, 2]
            avg_true_loss = (pmin * loss3[:cutoff, 2]).sum()
            return avg_true_loss

    @property
    def best_trial(self):
        """Trial with lowest loss and status=STATUS_OK
        """
        candidates = [t for t in self.trials
                      if t['result']['status'] == STATUS_OK]
        losses = [float(t['result']['loss']) for t in candidates]
        assert not np.any(np.isnan(losses))
        best = np.argmin(losses)
        return candidates[best]

    @property
    def argmin(self):
        best_trial = self.best_trial
        vals = best_trial['misc']['vals']
        # unpack the one-element lists to values
        # and skip over the 0-element lists
        rval = {}
        for k, v in vals.items():
            if v:
                rval[k] = v[0]
        return rval

    def fmin(self, fn, space, algo, max_evals,
             rstate=None,
             verbose=0,
             pass_expr_memo_ctrl=None,
             catch_eval_exceptions=False,
             return_argmin=True,
             ):
        """Minimize a function over a hyperparameter space.

        For most parameters, see `hyperopt.fmin.fmin`.

        Parameters
        ----------

        catch_eval_exceptions : bool, default False
            If set to True, exceptions raised by either the evaluation of the
            configuration space from hyperparameters or the execution of `fn`
            , will be caught by fmin, and recorded in self._dynamic_trials as
            error jobs (JOB_STATE_ERROR).  If set to False, such exceptions
            will not be caught, and so they will propagate to calling code.


        """
        # -- Stop-gap implementation!
        #    fmin should have been a Trials method in the first place
        #    but for now it's still sitting in another file.
        import fmin as fmin_module
        return fmin_module.fmin(
            fn, space, algo, max_evals,
            trials=self,
            rstate=rstate,
            verbose=verbose,
            allow_trials_fmin=False,  # -- prevent recursion
            pass_expr_memo_ctrl=pass_expr_memo_ctrl,
            catch_eval_exceptions=catch_eval_exceptions,
            return_argmin=return_argmin)


def trials_from_docs(docs, validate=True, **kwargs):
    """Construct a Trials base class instance from a list of trials documents
    """
    rval = Trials(**kwargs)
    if validate:
        rval.insert_trial_docs(docs)
    else:
        rval._insert_trial_docs(docs)
    rval.refresh()
    return rval


class Ctrl(object):
    """Control object for interruptible, checkpoint-able evaluation
    """
    info = logger.info
    warn = logger.warn
    error = logger.error
    debug = logger.debug

    def __init__(self, trials, current_trial=None):
        # -- attachments should be used like
        #      attachments[key]
        #      attachments[key] = value
        #    where key and value are strings. Client code should not
        #    expect any dictionary-like behaviour beyond that (no update)
        if trials is None:
            self.trials = Trials()
        else:
            self.trials = trials
        self.current_trial = current_trial

    def checkpoint(self, r=None):
        assert self.current_trial in self.trials._trials
        if r is not None:
            self.current_trial['result'] = r

    @property
    def attachments(self):
        """
        Support syntax for load:  self.attachments[name]
        Support syntax for store: self.attachments[name] = value
        """
        return self.trials.trial_attachments(trial=self.current_trial)

    def inject_results(self, specs, results, miscs, new_tids=None):
        """Inject new results into self.trials

        Returns ??? XXX

        new_tids can be None, in which case new tids will be generated
        automatically

        """
        trial = self.current_trial
        assert trial is not None
        num_news = len(specs)
        assert len(specs) == len(results) == len(miscs)
        if new_tids is None:
            new_tids = self.trials.new_trial_ids(num_news)
        new_trials = self.trials.source_trial_docs(tids=new_tids,
                                                   specs=specs,
                                                   results=results,
                                                   miscs=miscs,
                                                   sources=[trial])
        for t in new_trials:
            t['state'] = JOB_STATE_DONE
        return self.trials.insert_trial_docs(new_trials)


class Domain(object):
    """Picklable representation of search space and evaluation function.

    """
    rec_eval_print_node_on_error = False

    # -- the Ctrl object is not used directly, but rather
    #    a live Ctrl instance is inserted for the pyll_ctrl
    #    in self.evaluate so that it can be accessed from within
    #    the pyll graph describing the search space.
    pyll_ctrl = pyll.as_apply(Ctrl)

    def __init__(self, fn, expr,
                 workdir=None,
                 pass_expr_memo_ctrl=None,
                 name=None,
                 loss_target=None,
                 ):
        """
        Paramaters
        ----------

        fn : callable
            This stores the `fn` argument to `fmin`. (See `hyperopt.fmin.fmin`)

        expr : hyperopt.pyll.Apply
            This is the `space` argument to `fmin`. (See `hyperopt.fmin.fmin`)

        workdir : string (or None)
            If non-None, the current working directory will be `workdir`while
            `expr` and `fn` are evaluated. (XXX Currently only respected by
            jobs run via MongoWorker)

        pass_expr_memo_ctrl : bool
            If True, `fn` will be called like this:
            `fn(self.expr, memo, ctrl)`,
            where `memo` is a dictionary mapping `Apply` nodes to their
            computed values, and `ctrl` is a `Ctrl` instance for communicating
            with a Trials database.  This lower-level calling convention is
            useful if you want to call e.g. `hyperopt.pyll.rec_eval` yourself
            in some customized way.

        name : string (or None)
            Label, used for pretty-printing.

        loss_target : float (or None)
            The actual or estimated minimum of `fn`.
            Some optimization algorithms may behave differently if their first
            objective is to find an input that achieves a certain value,
            rather than the more open-ended objective of pure minimization.
            XXX: Move this from Domain to be an fmin arg.

        """
        self.fn = fn
        if pass_expr_memo_ctrl is None:
            self.pass_expr_memo_ctrl = getattr(fn,
                                               'fmin_pass_expr_memo_ctrl',
                                               False)
        else:
            self.pass_expr_memo_ctrl = pass_expr_memo_ctrl

        self.expr = pyll.as_apply(expr)

        self.params = {}
        for node in pyll.dfs(self.expr):
            if node.name == 'hyperopt_param':
                label = node.arg['label'].obj
                if label in self.params:
                    raise DuplicateLabel(label)
                self.params[label] = node.arg['obj']

        self.loss_target = loss_target
        self.name = name

        self.workdir = workdir
        self.s_new_ids = pyll.Literal('new_ids')  # -- list at eval-time
        before = pyll.dfs(self.expr)
        # -- raises exception if expr contains cycles
        pyll.toposort(self.expr)
        vh = self.vh = VectorizeHelper(self.expr, self.s_new_ids)
        # -- raises exception if v_expr contains cycles
        pyll.toposort(vh.v_expr)

        idxs_by_label = vh.idxs_by_label()
        vals_by_label = vh.vals_by_label()
        after = pyll.dfs(self.expr)
        # -- try to detect if VectorizeHelper screwed up anything inplace
        assert before == after
        assert set(idxs_by_label.keys()) == set(vals_by_label.keys())
        assert set(idxs_by_label.keys()) == set(self.params.keys())

        self.s_rng = pyll.Literal('rng-placeholder')
        # -- N.B. operates inplace:
        self.s_idxs_vals = recursive_set_rng_kwarg(
            pyll.scope.pos_args(idxs_by_label, vals_by_label),
            self.s_rng)

        # -- raises an exception if no topological ordering exists
        pyll.toposort(self.s_idxs_vals)

        # -- Protocol for serialization.
        #    self.cmd indicates to e.g. MongoWorker how this domain
        #    should be [un]serialized.
        #    XXX This mechanism deserves review as support for ipython
        #        workers improves.
        self.cmd = ('domain_attachment', 'FMinIter_Domain')

    def memo_from_config(self, config):
        memo = {}
        for node in pyll.dfs(self.expr):
            if node.name == 'hyperopt_param':
                label = node.arg['label'].obj
                # -- hack because it's not really garbagecollected
                #    this does have the desired effect of crashing the
                #    function if rec_eval actually needs a value that
                #    the the optimization algorithm thought to be unnecessary
                memo[node] = config.get(label, pyll.base.GarbageCollected)
        return memo

    def evaluate(self, config, ctrl, attach_attachments=True):
        memo = self.memo_from_config(config)
        use_obj_for_literal_in_memo(self.expr, ctrl, Ctrl, memo)
        if self.pass_expr_memo_ctrl:
            rval = self.fn(expr=self.expr, memo=memo, ctrl=ctrl)
        else:
            # -- the "work" of evaluating `config` can be written
            #    either into the pyll part (self.expr)
            #    or the normal Python part (self.fn)
            pyll_rval = pyll.rec_eval(
                self.expr,
                memo=memo,
                print_node_on_error=self.rec_eval_print_node_on_error)
            rval = self.fn(pyll_rval)

        if isinstance(rval, (float, int, np.number)):
            dict_rval = {'loss': float(rval), 'status': STATUS_OK}
        else:
            dict_rval = dict(rval)
            status = dict_rval['status']
            if status not in STATUS_STRINGS:
                raise InvalidResultStatus(dict_rval)

            if status == STATUS_OK:
                # -- make sure that the loss is present and valid
                try:
                    dict_rval['loss'] = float(dict_rval['loss'])
                except (TypeError, KeyError):
                    raise InvalidLoss(dict_rval)

        if attach_attachments:
            attachments = dict_rval.pop('attachments', {})
            for key, val in attachments.items():
                ctrl.attachments[key] = val

        # -- don't do this here because SON-compatibility is only a requirement
        #    for trials destined for a mongodb. In-memory rvals can contain
        #    anything.
        #return base.SONify(dict_rval)
        return dict_rval

    def short_str(self):
        return 'Domain{%s}' % str(self.fn)

    def loss(self, result, config=None):
        """Extract the scalar-valued loss from a result document
        """
        return result.get('loss', None)

    def loss_variance(self, result, config=None):
        """Return the variance in the estimate of the loss"""
        return result.get('loss_variance', 0.0)

    def true_loss(self, result, config=None):
        """Return a true loss, in the case that the `loss` is a surrogate"""
        # N.B. don't use get() here, it evaluates self.loss un-necessarily
        try:
            return result['true_loss']
        except KeyError:
            return self.loss(result, config=config)

    def true_loss_variance(self, config=None):
        """Return the variance in  true loss,
        in the case that the `loss` is a surrogate.
        """
        raise NotImplementedError()

    def status(self, result, config=None):
        """Extract the job status from a result document
        """
        return result['status']

    def new_result(self):
        """Return a JSON-encodable object
        to serve as the 'result' for new jobs.
        """
        return {'status': STATUS_NEW}


# -- flake8 doesn't like blank last line

########NEW FILE########
__FILENAME__ = criteria
"""Criteria for Bayesian optimization
"""
import numpy as np
import scipy.stats


def EI_empirical(samples, thresh):
    """Expected Improvement over threshold from samples

    (See example usage in EI_gaussian_empirical)
    """
    improvement = np.maximum(samples - thresh, 0)
    return improvement.mean()


def EI_gaussian_empirical(mean, var, thresh, rng, N):
    """Expected Improvement of Gaussian over threshold

    (estimated empirically)
    """
    return EI_empirical(rng.randn(N) * np.sqrt(var) + mean, thresh)


def EI_gaussian(mean, var, thresh):
    """Expected Improvement of Gaussian over threshold

    (estimated analytically)
    """
    sigma = np.sqrt(var)
    score = (mean - thresh) / sigma
    n = scipy.stats.norm
    return sigma * (score * n.cdf(score) + n.pdf(score))


def logEI_gaussian(mean, var, thresh):
    """Return log(EI(mean, var, thresh))

    This formula avoids underflow in cdf for
        thresh >= mean + 37 * sqrt(var)

    """
    assert np.asarray(var).min() >= 0
    sigma = np.sqrt(var)
    score = (mean - thresh) / sigma
    n = scipy.stats.norm
    try:
        float(mean)
        is_scalar = True
    except TypeError:
        is_scalar = False

    if is_scalar:
        if score < 0:
            pdf = n.logpdf(score)
            r = np.exp(np.log(-score) + n.logcdf(score) - pdf)
            rval = np.log(sigma) + pdf + np.log1p(-r)
            if not np.isfinite(rval):
                return -np.inf
            else:
                return rval
        else:
            return np.log(sigma) + np.log(score * n.cdf(score) + n.pdf(score))
    else:
        score = np.asarray(score)
        rval = np.zeros_like(score)

        olderr = np.seterr(all='ignore')
        try:
            negs = score < 0
            nonnegs = np.logical_not(negs)
            negs_score = score[negs]
            negs_pdf = n.logpdf(negs_score)
            r = np.exp(np.log(-negs_score)
                       + n.logcdf(negs_score)
                       - negs_pdf)
            rval[negs] = np.log(sigma[negs]) + negs_pdf + np.log1p(-r)
            nonnegs_score = score[nonnegs]
            rval[nonnegs] = np.log(sigma[nonnegs]) + np.log(
                nonnegs_score * n.cdf(nonnegs_score) + n.pdf(nonnegs_score))
            rval[np.logical_not(np.isfinite(rval))] = -np.inf
        finally:
            np.seterr(**olderr)
        return rval


def UCB(mean, var, zscore):
    """Upper Confidence Bound

    For a model which predicts a Gaussian-distributed outcome, the UCB is

        mean + zscore * sqrt(var)
    """
    return mean + np.sqrt(var) * zscore


# -- flake8

########NEW FILE########
__FILENAME__ = exceptions
"""
"""

class BadSearchSpace(Exception):
    """Something is wrong in the description of the search space"""


class DuplicateLabel(BadSearchSpace):
    """A search space included a duplicate label """


class InvalidTrial(ValueError):
    """Non trial-like object used as Trial"""
    def __init__(self, msg, obj):
        ValueError.__init__(self, msg + ' ' + str(obj))
        self.obj = obj


class InvalidResultStatus(ValueError):
    """Status of fmin evaluation was not in base.STATUS_STRINGS"""
    def __init__(self, result):
        ValueError.__init__(self)
        self.result = result


class InvalidLoss(ValueError):
    """fmin evaluation returned invalid loss value"""
    def __init__(self, result):
        ValueError.__init__(self)
        self.result = result

# -- flake8 doesn't like blank last line

########NEW FILE########
__FILENAME__ = fmin
try:
    import dill as cPickle
except ImportError:
    import cPickle

import functools
import logging
import os
import sys
import time

import numpy as np

import pyll
from .utils import coarse_utcnow
from . import base

logger = logging.getLogger(__name__)


def fmin_pass_expr_memo_ctrl(f):
    """
    Mark a function as expecting kwargs 'expr', 'memo' and 'ctrl' from
    hyperopt.fmin.

    expr - the pyll expression of the search space
    memo - a partially-filled memo dictionary such that
           `rec_eval(expr, memo=memo)` will build the proposed trial point.
    ctrl - the Experiment control object (see base.Ctrl)

    """
    f.fmin_pass_expr_memo_ctrl = True
    return f


def partial(fn, **kwargs):
    """functools.partial work-alike for functions decorated with
    fmin_pass_expr_memo_ctrl
    """
    rval = functools.partial(fn, **kwargs)
    if hasattr(fn, 'fmin_pass_expr_memo_ctrl'):
        rval.fmin_pass_expr_memo_ctrl = fn.fmin_pass_expr_memo_ctrl
    return rval


class FMinIter(object):
    """Object for conducting search experiments.
    """
    catch_eval_exceptions = False
    cPickle_protocol = -1

    def __init__(self, algo, domain, trials, rstate, async=None,
            max_queue_len=1,
            poll_interval_secs=1.0,
            max_evals=sys.maxint,
            verbose=0,
            ):
        self.algo = algo
        self.domain = domain
        self.trials = trials
        if async is None:
            self.async = trials.async
        else:
            self.async = async
        self.poll_interval_secs = poll_interval_secs
        self.max_queue_len = max_queue_len
        self.max_evals = max_evals
        self.rstate = rstate

        if self.async:
            if 'FMinIter_Domain' in trials.attachments:
                logger.warn('over-writing old domain trials attachment')
            msg = cPickle.dumps(
                    domain, protocol=self.cPickle_protocol)
            # -- sanity check for unpickling
            cPickle.loads(msg)
            trials.attachments['FMinIter_Domain'] = msg

    def serial_evaluate(self, N=-1):
        for trial in self.trials._dynamic_trials:
            if trial['state'] == base.JOB_STATE_NEW:
                trial['state'] == base.JOB_STATE_RUNNING
                now = coarse_utcnow()
                trial['book_time'] = now
                trial['refresh_time'] = now
                spec = base.spec_from_misc(trial['misc'])
                ctrl = base.Ctrl(self.trials, current_trial=trial)
                try:
                    result = self.domain.evaluate(spec, ctrl)
                except Exception, e:
                    logger.info('job exception: %s' % str(e))
                    trial['state'] = base.JOB_STATE_ERROR
                    trial['misc']['error'] = (str(type(e)), str(e))
                    trial['refresh_time'] = coarse_utcnow()
                    if not self.catch_eval_exceptions:
                        # -- JOB_STATE_ERROR means this trial
                        #    will be removed from self.trials.trials
                        #    by this refresh call.
                        self.trials.refresh()
                        raise
                else:
                    #logger.debug('job returned status: %s' % result['status'])
                    #logger.debug('job returned loss: %s' % result.get('loss'))
                    trial['state'] = base.JOB_STATE_DONE
                    trial['result'] = result
                    trial['refresh_time'] = coarse_utcnow()
                N -= 1
                if N == 0:
                    break
        self.trials.refresh()

    def block_until_done(self):
        already_printed = False
        if self.async:
            unfinished_states = [base.JOB_STATE_NEW, base.JOB_STATE_RUNNING]

            def get_queue_len():
                return self.trials.count_by_state_unsynced(unfinished_states)

            qlen = get_queue_len()
            while qlen > 0:
                if not already_printed:
                    logger.info('Waiting for %d jobs to finish ...' % qlen)
                    already_printed = True
                time.sleep(self.poll_interval_secs)
                qlen = get_queue_len()
            self.trials.refresh()
        else:
            self.serial_evaluate()

    def run(self, N, block_until_done=True):
        """
        block_until_done  means that the process blocks until ALL jobs in
        trials are not in running or new state

        """
        trials = self.trials
        algo = self.algo
        n_queued = 0

        def get_queue_len():
            return self.trials.count_by_state_unsynced(base.JOB_STATE_NEW)

        stopped = False
        while n_queued < N:
            qlen = get_queue_len()
            while qlen < self.max_queue_len and n_queued < N:
                n_to_enqueue = min(self.max_queue_len - qlen, N - n_queued)
                new_ids = trials.new_trial_ids(n_to_enqueue)
                self.trials.refresh()
                if 0:
                    for d in self.trials.trials:
                        print 'trial %i %s %s' % (d['tid'], d['state'],
                            d['result'].get('status'))
                new_trials = algo(new_ids, self.domain, trials,
                                  self.rstate.randint(2 ** 31 - 1))
                assert len(new_ids) >= len(new_trials)
                if len(new_trials):
                    self.trials.insert_trial_docs(new_trials)
                    self.trials.refresh()
                    n_queued += len(new_trials)
                    qlen = get_queue_len()
                else:
                    stopped = True
                    break

            if self.async:
                # -- wait for workers to fill in the trials
                time.sleep(self.poll_interval_secs)
            else:
                # -- loop over trials and do the jobs directly
                self.serial_evaluate()

            if stopped:
                break

        if block_until_done:
            self.block_until_done()
            self.trials.refresh()
            logger.info('Queue empty, exiting run.')
        else:
            qlen = get_queue_len()
            if qlen:
                msg = 'Exiting run, not waiting for %d jobs.' % qlen
                logger.info(msg)

    def __iter__(self):
        return self

    def next(self):
        self.run(1, block_until_done=self.async)
        if len(self.trials) >= self.max_evals:
            raise StopIteration()
        return self.trials

    def exhaust(self):
        n_done = len(self.trials)
        self.run(self.max_evals - n_done, block_until_done=self.async)
        self.trials.refresh()
        return self


def fmin(fn, space, algo, max_evals, trials=None, rstate=None,
         allow_trials_fmin=True, pass_expr_memo_ctrl=None,
         catch_eval_exceptions=False,
         verbose=0,
         return_argmin=True,
        ):
    """Minimize a function over a hyperparameter space.

    More realistically: *explore* a function over a hyperparameter space
    according to a given algorithm, allowing up to a certain number of
    function evaluations.  As points are explored, they are accumulated in
    `trials`


    Parameters
    ----------

    fn : callable (trial point -> loss)
        This function will be called with a value generated from `space`
        as the first and possibly only argument.  It can return either
        a scalar-valued loss, or a dictionary.  A returned dictionary must
        contain a 'status' key with a value from `STATUS_STRINGS`, must
        contain a 'loss' key if the status is `STATUS_OK`. Particular
        optimization algorithms may look for other keys as well.  An
        optional sub-dictionary associated with an 'attachments' key will
        be removed by fmin its contents will be available via
        `trials.trial_attachments`. The rest (usually all) of the returned
        dictionary will be stored and available later as some 'result'
        sub-dictionary within `trials.trials`.

    space : hyperopt.pyll.Apply node
        The set of possible arguments to `fn` is the set of objects
        that could be created with non-zero probability by drawing randomly
        from this stochastic program involving involving hp_<xxx> nodes
        (see `hyperopt.hp` and `hyperopt.pyll_utils`).

    algo : search algorithm
        This object, such as `hyperopt.rand.suggest` and
        `hyperopt.tpe.suggest` provides logic for sequential search of the
        hyperparameter space.

    max_evals : int
        Allow up to this many function evaluations before returning.

    trials : None or base.Trials (or subclass)
        Storage for completed, ongoing, and scheduled evaluation points.  If
        None, then a temporary `base.Trials` instance will be created.  If
        a trials object, then that trials object will be affected by
        side-effect of this call.

    rstate : numpy.RandomState, default numpy.random or `$HYPEROPT_FMIN_SEED`
        Each call to `algo` requires a seed value, which should be different
        on each call. This object is used to draw these seeds via `randint`.
        The default rstate is
        `numpy.random.RandomState(int(env['HYPEROPT_FMIN_SEED']))`
        if the `HYPEROPT_FMIN_SEED` environment variable is set to a non-empty
        string, otherwise np.random is used in whatever state it is in.

    verbose : int
        Print out some information to stdout during search.

    allow_trials_fmin : bool, default True
        If the `trials` argument

    pass_expr_memo_ctrl : bool, default False
        If set to True, `fn` will be called in a different more low-level
        way: it will receive raw hyperparameters, a partially-populated
        `memo`, and a Ctrl object for communication with this Trials
        object.

    return_argmin : bool, default True
        If set to False, this function returns nothing, which can be useful
        for example if it is expected that `len(trials)` may be zero after
        fmin, and therefore `trials.argmin` would be undefined.


    Returns
    -------

    argmin : None or dictionary
        If `return_argmin` is False, this function returns nothing.
        Otherwise, it returns `trials.argmin`.  This argmin can be converted
        to a point in the configuration space by calling
        `hyperopt.space_eval(space, best_vals)`.


    """
    if rstate is None:
        env_rseed = os.environ.get('HYPEROPT_FMIN_SEED', '')
        if env_rseed:
            rstate = np.random.RandomState(int(env_rseed))
        else:
            rstate = np.random.RandomState()

    if allow_trials_fmin and hasattr(trials, 'fmin'):
        return trials.fmin(
            fn, space,
            algo=algo,
            max_evals=max_evals,
            rstate=rstate,
            pass_expr_memo_ctrl=pass_expr_memo_ctrl,
            verbose=verbose,
            catch_eval_exceptions=catch_eval_exceptions,
            return_argmin=return_argmin,
            )

    if trials is None:
        trials = base.Trials()

    domain = base.Domain(fn, space,
        pass_expr_memo_ctrl=pass_expr_memo_ctrl)

    rval = FMinIter(algo, domain, trials, max_evals=max_evals,
                    rstate=rstate,
                    verbose=verbose)
    rval.catch_eval_exceptions = catch_eval_exceptions
    rval.exhaust()
    if return_argmin:
        return trials.argmin


def space_eval(space, hp_assignment):
    """Compute a point in a search space from a hyperparameter assignment.

    Parameters:
    -----------
    space - a pyll graph involving hp nodes (see `pyll_utils`).

    hp_assignment - a dictionary mapping hp node labels to values.
    """
    space = pyll.as_apply(space)
    nodes = pyll.toposort(space)
    memo = {}
    for node in nodes:
        if node.name == 'hyperopt_param':
            label = node.arg['label'].eval()
            if label in hp_assignment:
                memo[node] = hp_assignment[label]
    rval = pyll.rec_eval(space, memo=memo)
    return rval

# -- flake8 doesn't like blank last line

########NEW FILE########
__FILENAME__ = graphviz
"""
Use graphviz's dot language to express the relationship between hyperparamters
in a search space.

"""

import StringIO
from pyll_utils import expr_to_config


def dot_hyperparameters(expr):
    """
    Return a dot language specification of a graph which describes the
    relationship between hyperparameters. Each hyperparameter within the
    pyll expression `expr` is represented by a rectangular node, and
    each value of each choice node that creates a conditional variable
    in the search space is represented by an elliptical node.

    The direction of the arrows corresponds to the sequence of events
    in an ancestral sampling process.

    E.g.:
    >>> open('foo.dot', 'wb').write(dot_hyperparameters(search_space()))

    Then later from the shell, type e.g.
    dot -Tpng foo.dot > foo.png && eog foo.png

    Graphviz has other tools too: http://www.graphviz.org

    """
    conditions = ()
    hps = {}
    expr_to_config(expr, conditions, hps)
    rval = StringIO.StringIO()
    print >> rval, "digraph {"
    edges = set()

    def var_node(a):
        print >> rval, '"%s" [ shape=box];' % a

    def cond_node(a):
        print >> rval, '"%s" [ shape=ellipse];' % a

    def edge(a, b):
        text = '"%s" -> "%s";' % (a, b)
        if text not in edges:
            print >> rval, text
            edges.add(text)

    for hp, dct in hps.items():
        # create the node
        var_node(hp)

        # create an edge from anything it depends on
        for and_conds in dct['conditions']:
            if len(and_conds) > 1:
                parent_label = ' & '.join([
                    '%(name)s%(op)s%(val)s' % cond.__dict__
                    for cond in and_conds])
                cond_node(parent_label)
                edge(parent_label, hp)
                for cond in and_conds:
                    sub_parent_label = '%s%s%s' % (
                        cond.name, cond.op, cond.val)
                    cond_node(sub_parent_label)
                    edge(cond.name, sub_parent_label)
                    edge(sub_parent_label, parent_label)
            elif len(and_conds) == 1:
                parent_label = '%s%s%s' % (
                    and_conds[0].name, and_conds[0].op, and_conds[0].val)
                edge(and_conds[0].name, parent_label)
                cond_node(parent_label)
                edge(parent_label, hp)
    print >> rval, "}"
    return rval.getvalue()


########NEW FILE########
__FILENAME__ = hp
"""
Support nicer user syntax:
    from hyperopt import hp
    hp.uniform('x', 0, 1)
"""
from pyll_utils import hp_choice as choice
from pyll_utils import hp_randint as randint
from pyll_utils import hp_pchoice as pchoice

from pyll_utils import hp_uniform as uniform
from pyll_utils import hp_quniform as quniform
from pyll_utils import hp_loguniform as loguniform
from pyll_utils import hp_qloguniform as qloguniform

from pyll_utils import hp_normal as normal
from pyll_utils import hp_qnormal as qnormal
from pyll_utils import hp_lognormal as lognormal
from pyll_utils import hp_qlognormal as qlognormal

########NEW FILE########
__FILENAME__ = ipy
"""Utilities for Parallel Model Selection with IPython

Author: James Bergstra <james.bergstra@gmail.com>
Licensed: MIT
"""
from time import sleep, time

import numpy as np
from IPython.parallel import interactive
#from IPython.parallel import TaskAborted
#from IPython.display import clear_output

from .base import Trials
from .base import Domain
from .base import JOB_STATE_NEW
from .base import JOB_STATE_RUNNING
from .base import JOB_STATE_DONE
from .base import JOB_STATE_ERROR
from .base import spec_from_misc
from .utils import coarse_utcnow

import sys
print >> sys.stderr, "WARNING: IPythonTrials is not as complete, stable"
print >> sys.stderr, "         or well tested as Trials or MongoTrials."


class LostEngineError(RuntimeError):
    """An IPEngine disappeared during computation, and a job with it."""


class IPythonTrials(Trials):

    def __init__(self, client,
            job_error_reaction='raise',
            save_ipy_metadata=True):
        self._client = client
        self.job_map = {}
        self.job_error_reaction = job_error_reaction
        self.save_ipy_metadata = save_ipy_metadata
        Trials.__init__(self)
        self._testing_fmin_was_called = False

    def _insert_trial_docs(self, docs):
        rval = [doc['tid'] for doc in docs]
        self._dynamic_trials.extend(docs)
        return rval

    def refresh(self):
        job_map = {}

        # -- carry over state for active engines
        for eid in self._client.ids:
            job_map[eid] = self.job_map.pop(eid, (None, None))

        # -- deal with lost engines, abandoned promises
        for eid, (p, tt) in self.job_map.items():
            if self.job_error_reaction == 'raise':
                raise LostEngineError(p)
            elif self.job_error_reaction == 'log':
                tt['error'] = 'LostEngineError (%s)' % str(p)
                tt['state'] = JOB_STATE_ERROR
            else:
                raise ValueError(self.job_error_reaction)

        # -- remove completed jobs from job_map
        for eid, (p, tt) in job_map.items():
            if p is None:
                continue
            #print p
            #assert eid == p.engine_id
            if p.ready():
                try:
                    tt['result'] = p.get()
                    tt['state'] = JOB_STATE_DONE
                except Exception, e:
                    if self.job_error_reaction == 'raise':
                        raise
                    elif self.job_error_reaction == 'log':
                        tt['error'] = str(e)
                        tt['state'] = JOB_STATE_ERROR
                    else:
                        raise ValueError(self.job_error_reaction)
                if self.save_ipy_metadata:
                    tt['ipy_metadata'] = p.metadata
                tt['refresh_time'] = coarse_utcnow()
                job_map[eid] = (None, None)

        self.job_map = job_map

        Trials.refresh(self)

    def fmin(self, fn, space, algo, max_evals,
        rstate=None,
        verbose=0,
        wait=True,
        pass_expr_memo_ctrl=None,
        ):

        if rstate is None:
            rstate = np.random

        # -- used in test_ipy
        self._testing_fmin_was_called = True

        if pass_expr_memo_ctrl is None:
            try:
                pass_expr_memo_ctrl = fn.pass_expr_memo_ctrl
            except AttributeError:
                pass_expr_memo_ctrl = False

        domain = Domain(fn, space, rseed=rstate.randint(2 ** 31 - 1),
                pass_expr_memo_ctrl=pass_expr_memo_ctrl)

        last_print_time = 0

        while len(self._dynamic_trials) < max_evals:
            self.refresh()

            if verbose and last_print_time + 1 < time():
                print 'fmin: %4i/%4i/%4i/%4i  %f' % (
                    self.count_by_state_unsynced(JOB_STATE_NEW),
                    self.count_by_state_unsynced(JOB_STATE_RUNNING),
                    self.count_by_state_unsynced(JOB_STATE_DONE),
                    self.count_by_state_unsynced(JOB_STATE_ERROR),
                    min([float('inf')] + [l for l in self.losses() if l is not None])
                    )
                last_print_time = time()

            idles = [eid for (eid, (p, tt)) in self.job_map.items() if p is None]

            if idles:
                new_ids = self.new_trial_ids(len(idles))
                new_trials = algo(new_ids, domain, self)
                if len(new_trials) == 0:
                    break
                else:
                    assert len(idles) == len(new_trials)
                    for eid, new_trial in zip(idles, new_trials):
                        now = coarse_utcnow()
                        new_trial['book_time'] = now
                        new_trial['refresh_time'] = now
                        promise = self._client[eid].apply_async(
                            call_domain,
                            domain,
                            config=spec_from_misc(new_trial['misc']),
                            )

                        # -- XXX bypassing checks because 'ar'
                        # is not ok for SONify... but should check
                        # for all else being SONify
                        tid, = self.insert_trial_docs([new_trial])
                        tt = self._dynamic_trials[-1]
                        assert tt['tid'] == tid
                        self.job_map[eid] = (promise, tt)
                        tt['state'] = JOB_STATE_RUNNING

        if wait:
            if verbose:
                print 'fmin: Waiting on remaining jobs...'
            self.wait(verbose=verbose)

        return self.argmin

    def wait(self, verbose=False, verbose_print_interval=1.0):
        last_print_time = 0
        while True:
            self.refresh()
            if verbose and last_print_time + verbose_print_interval < time():
                print 'fmin: %4i/%4i/%4i/%4i  %f' % (
                    self.count_by_state_unsynced(JOB_STATE_NEW),
                    self.count_by_state_unsynced(JOB_STATE_RUNNING),
                    self.count_by_state_unsynced(JOB_STATE_DONE),
                    self.count_by_state_unsynced(JOB_STATE_ERROR),
                    min([float('inf')]
                        + [l for l in self.losses() if l is not None])
                    )
                last_print_time = time()
            if self.count_by_state_unsynced(JOB_STATE_NEW):
                sleep(1e-1)
                continue
            if self.count_by_state_unsynced(JOB_STATE_RUNNING):
                sleep(1e-1)
                continue
            break

    def __getstate__(self):
        rval = dict(self.__dict__)
        del rval['_client']
        del rval['_trials']
        del rval['job_map']
        #print rval.keys()
        return rval

    def __setstate__(self, dct):
        self.__dict__ = dct
        self.job_map = {}
        Trials.refresh(self)


@interactive
def call_domain(domain, config):
    ctrl = None # -- not implemented yet
    return domain.evaluate(
            config=config,
            ctrl=ctrl,
            attach_attachments=False, # -- Not implemented yet
            )

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python

"""
Entry point for bin/* scripts
"""

__authors__   = "James Bergstra"
__license__   = "3-clause BSD License"
__contact__   = "github.com/hyperopt/hyperopt"

import cPickle
import logging
import os

import base
import utils

logger = logging.getLogger(__name__)

from .base import SerialExperiment
import sys
import logging
logger = logging.getLogger(__name__)

def main_search():
    from optparse import OptionParser
    parser = OptionParser(
            usage="%prog [options] [<bandit> <bandit_algo>]")
    parser.add_option('--load',
            default='',
            dest="load",
            metavar='FILE',
            help="unpickle experiment from here on startup")
    parser.add_option('--save',
            default='experiment.pkl',
            dest="save",
            metavar='FILE',
            help="pickle experiment to here on exit")
    parser.add_option("--steps",
            dest='steps',
            default='100',
            metavar='N',
            help="exit after queuing this many jobs (default: 100)")
    parser.add_option("--workdir",
            dest="workdir",
            default=os.path.expanduser('~/.hyperopt.workdir'),
            help="create workdirs here",
            metavar="DIR")
    parser.add_option("--bandit-argfile",
            dest="bandit_argfile",
            default=None,
            help="path to file containing arguments bandit constructor \
                  file format: pickle of dictionary containing two keys,\
                  {'args' : tuple of positional arguments, \
                   'kwargs' : dictionary of keyword arguments}")
    parser.add_option("--bandit-algo-argfile",
            dest="bandit_algo_argfile",
            default=None,
            help="path to file containing arguments for bandit_algo "
                  "constructor.  File format is pickled dictionary containing "
                  "two keys: 'args', a tuple of positional arguments, and "
                  "'kwargs', a dictionary of keyword arguments. "
                  "NOTE: bandit is pre-pended as first element of arg tuple.")

    (options, args) = parser.parse_args()
    try:
        bandit_json, bandit_algo_json = args
    except:
        parser.print_help()
        return -1

    try:
        if not options.load:
            raise IOError()
        handle = open(options.load, 'rb')
        self = cPickle.load(handle)
        handle.close()
    except IOError:
        bandit = utils.get_obj(bandit_json, argfile=options.bandit_argfile)
        bandit_algo = utils.get_obj(bandit_algo_json,
                                    argfile=options.bandit_algo_argfile,
                                    args=(bandit,))
        self = SerialExperiment(bandit_algo)

    try:
        self.run(int(options.steps))
    finally:
        if options.save:
            cPickle.dump(self, open(options.save, 'wb'))


def main(cmd, fn_pos = 1):
    """
    Entry point for bin/* scripts
    XXX
    """
    logging.basicConfig(
            stream=sys.stderr,
            level=logging.INFO)
    try:
        runner = dict(
                search='main_search',
                dryrun='main_dryrun',
                plot_history='main_plot_history',
                )[cmd]
    except KeyError:
        logger.error("Command not recognized: %s" % cmd)
        # XXX: Usage message
        sys.exit(1)
    try:
        argv1 = sys.argv[fn_pos]
    except IndexError:
        logger.error('Module name required (XXX: print Usage)')
        return 1

    fn = datasets.main.load_tokens(sys.argv[fn_pos].split('.') + [runner])
    sys.exit(fn(sys.argv[fn_pos+1:]))

if __name__ == '__main__':
    cmd = sys.argv[1]
    sys.exit(main(cmd, 2))

########NEW FILE########
__FILENAME__ = mix
import numpy as np

def suggest(new_ids, domain, trials, seed, p_suggest):
    """Return the result of a randomly-chosen suggest function

    For exampl to search by sometimes using random search, sometimes anneal,
    and sometimes tpe, type:

        fmin(...,
            algo=partial(mix.suggest,
                p_suggest=[
                    (.1, rand.suggest),
                    (.2, anneal.suggest),
                    (.7, tpe.suggest),]),
            )


    Parameters
    ----------

    p_suggest: list of (probability, suggest) pairs
        Make a suggestion from one of the suggest functions,
        in proportion to its corresponding probability.
        sum(probabilities) must be [close to] 1.0
        
    """
    rng = np.random.RandomState(seed)
    ps, suggests = zip(*p_suggest)
    assert len(ps) == len(suggests) == len(p_suggest)
    if not np.isclose(sum(ps), 1.0):
        raise ValueError('Probabilities should sum to 1', ps)
    idx = rng.multinomial(n=1, pvals=ps).argmax()
    return suggests[idx](new_ids, domain, trials,
                         seed=int(rng.randint(2 ** 31)))


########NEW FILE########
__FILENAME__ = mongoexp
"""
Mongodb-based Trials Object
===========================

Components involved:

- mongo
    e.g. mongod ...

- driver
    e.g. hyperopt-mongo-search mongo://address bandit_json bandit_algo_json

- worker
    e.g. hyperopt-mongo-worker --loop mongo://address


Mongo
=====

Mongo (daemon process mongod) is used for IPC between the driver and worker.
Configure it as you like, so that hyperopt-mongo-search can communicate with it.
I think there is some support in this file for an ssh+mongo connection type.

The experiment uses the following collections for IPC:

* jobs - documents of a standard form used to store suggested trials and their
    results.  These documents have keys:
    * spec : subdocument returned by bandit_algo.suggest
    * exp_key: an identifier of which driver suggested this trial
    * cmd: a tuple (protocol, ...) identifying bandit.evaluate
    * state: 0, 1, 2, 3 for job state (new, running, ok, fail)
    * owner: None for new jobs, (hostname, pid) for started jobs
    * book_time: time a job was reserved
    * refresh_time: last time the process running the job checked in
    * result: the subdocument returned by bandit.evaluate
    * error: for jobs of state 3, a reason for failure.
    * logs: a dict of sequences of strings received by ctrl object
        * info: info messages
        * warn: warning messages
        * error: error messages

* fs - a gridfs storage collection (used for pickling)

* drivers - documents describing drivers. These are used to prevent two drivers
    from using the same exp_key simultaneously, and to attach saved states.
    * exp_key
    * workdir: [optional] path where workers should chdir to
    Attachments:
        * pkl: [optional] saved state of experiment class
        * bandit_args_kwargs: [optional] pickled (clsname, args, kwargs) to
             reconstruct bandit in worker processes

The MongoJobs, and CtrlObj classes as well as the main_worker
method form the abstraction barrier around this database layout.


Worker
======

A worker looks up a job in a mongo database, maps that job document to a
runnable python object, calls that object, and writes the return value back to
the database.

A worker *reserves* a job by atomically identifying a document in the jobs
collection whose owner is None and whose state is 0, and setting the state to
1.  If it fails to identify such a job, it loops with a random sleep interval
of a few seconds and polls the database.

If hyperopt-mongo-worker is called with a --loop argument then it goes back to
the database after finishing a job to identify and perform another one.

CtrlObj
-------

The worker allocates a CtrlObj and passes it to bandit.evaluate in addition to
the subdocument found at job['spec'].  A bandit can use ctrl.info, ctrl.warn,
ctrl.error and so on like logger methods, and those messages will be written
to the mongo database (to job['logs']).  They are not written synchronously
though, they are written when the bandit.evaluate function calls
ctrl.checkpoint().

Ctrl.checkpoint does several things:
* flushes logging messages to the database
* updates the refresh_time
* optionally updates the result subdocument

The main_worker routine calls Ctrl.checkpoint(rval) once after the
bandit.evalute function has returned before setting the state to 2 or 3 to
finalize the job in the database.

"""

__authors__ = ["James Bergstra", "Dan Yamins"]
__license__ = "3-clause BSD License"
__contact__ = "github.com/hyperopt/hyperopt"

import copy
try:
    import dill as cPickle
except ImportError:
    import cPickle
import hashlib
import logging
import optparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urlparse
import warnings

import numpy
import pymongo
import gridfs
from bson import SON


logger = logging.getLogger(__name__)

from .base import JOB_STATES
from .base import (JOB_STATE_NEW, JOB_STATE_RUNNING, JOB_STATE_DONE,
        JOB_STATE_ERROR)
from .base import Trials
from .base import trials_from_docs
from .base import InvalidTrial
from .base import Ctrl
from .base import SONify
from .base import spec_from_misc
from .utils import coarse_utcnow
from .utils import fast_isin
from .utils import get_most_recent_inds
from .utils import json_call
import plotting


class OperationFailure(Exception):
    """Proxy that could be factored out if we also want to use CouchDB and
    JobmanDB classes with this interface
    """


class Shutdown(Exception):
    """
    Exception for telling mongo_worker loop to quit
    """


class WaitQuit(Exception):
    """
    Exception for telling mongo_worker loop to quit
    """


class InvalidMongoTrial(InvalidTrial):
    pass


class DomainSwapError(Exception):
    """Raised when the search program tries to change the bandit attached to
    an experiment.
    """


class ReserveTimeout(Exception):
    """No job was reserved in the alotted time
    """


def read_pw():
    username = 'hyperopt'
    password = open(os.path.join(os.getenv('HOME'), ".hyperopt")).read()[:-1]
    return dict(
            username=username,
            password=password)


def authenticate_for_db(db):
    d = read_pw()
    db.authenticate(d['username'], d['password'])


def parse_url(url, pwfile=None):
    """Unpacks a url of the form
        protocol://[username[:pw]]@hostname[:port]/db/collection

    :rtype: tuple of strings
    :returns: protocol, username, password, hostname, port, dbname, collection

    :note:
    If the password is not given in the url but the username is, then
    this function will read the password from file by calling
    ``open(pwfile).read()[:-1]``

    """

    protocol=url[:url.find(':')]
    ftp_url='ftp'+url[url.find(':'):]

    # -- parse the string as if it were an ftp address
    tmp = urlparse.urlparse(ftp_url)

    logger.info( 'PROTOCOL %s'% protocol)
    logger.info( 'USERNAME %s'% tmp.username)
    logger.info( 'HOSTNAME %s'% tmp.hostname)
    logger.info( 'PORT %s'% tmp.port)
    logger.info( 'PATH %s'% tmp.path)
    try:
        _, dbname, collection = tmp.path.split('/')
    except:
        print >> sys.stderr, "Failed to parse '%s'"%(str(tmp.path))
        raise
    logger.info( 'DB %s'% dbname)
    logger.info( 'COLLECTION %s'% collection)

    if tmp.password is None:
        if (tmp.username is not None) and pwfile:
            password = open(pwfile).read()[:-1]
        else:
            password = None
    else:
        password = tmp.password
    logger.info( 'PASS %s'% password)

    return (protocol, tmp.username, password, tmp.hostname, tmp.port, dbname,
            collection)


def connection_with_tunnel(host='localhost',
            auth_dbname='admin', port=27017,
            ssh=False, user='hyperopt', pw=None):
        if ssh:
            local_port=numpy.random.randint(low=27500, high=28000)
            # -- forward from local to remote machine
            ssh_tunnel = subprocess.Popen(
                    ['ssh', '-NTf', '-L',
                        '%i:%s:%i'%(local_port, '127.0.0.1', port),
                        host],
                    #stdin=subprocess.PIPE,
                    #stdout=subprocess.PIPE,
                    #stderr=subprocess.PIPE,
                    )
            # -- give the subprocess time to set up
            time.sleep(.5)
            connection = pymongo.Connection('127.0.0.1', local_port,
                    document_class=SON)
        else:
            connection = pymongo.Connection(host, port, document_class=SON)
            if user:
                if user == 'hyperopt':
                    authenticate_for_db(connection[auth_dbname])
                else:
                    raise NotImplementedError()
            ssh_tunnel=None

        # -- Ensure that changes are written to at least once server.
        connection.write_concern['w'] = 1
        # -- Ensure that changes are written to the journal if there is one.
        connection.write_concern['j'] = True

        return connection, ssh_tunnel


def connection_from_string(s):
    protocol, user, pw, host, port, db, collection = parse_url(s)
    if protocol == 'mongo':
        ssh=False
    elif protocol in ('mongo+ssh', 'ssh+mongo'):
        ssh=True
    else:
        raise ValueError('unrecognized protocol for MongoJobs', protocol)
    connection, tunnel = connection_with_tunnel(
            ssh=ssh,
            user=user,
            pw=pw,
            host=host,
            port=port,
            )
    return connection, tunnel, connection[db], connection[db][collection]


class MongoJobs(object):
    """
    # Interface to a Jobs database structured like this
    #
    # Collections:
    #
    # db.jobs - structured {config_name, 'cmd', 'owner', 'book_time',
    #                  'refresh_time', 'state', 'exp_key', 'owner', 'result'}
    #    This is the collection that the worker nodes write to
    #
    # db.gfs - file storage via gridFS for all collections
    #
    """
    def __init__(self, db, jobs, gfs, conn, tunnel, config_name):
        """
        Parameters
        ----------

        db - Mongo Database (e.g. `Connection()[dbname]`)
            database in which all job-related info is stored

        jobs - Mongo Collection handle
            collection within `db` to use for job arguments, return vals,
            and various bookkeeping stuff and meta-data. Typically this is
            `db['jobs']`

        gfs - Mongo GridFS handle
            GridFS is used to store attachments - binary blobs that don't fit
            or are awkward to store in the `jobs` collection directly.

        conn - Mongo Connection
            Why we need to keep this, I'm not sure.

        tunnel - something for ssh tunneling if you're doing that
            See `connection_with_tunnel` for more info.

        config_name - string
            XXX: No idea what this is for, seems unimportant.

        """
        self.db = db
        self.jobs = jobs
        assert jobs.write_concern['w'] >= 1
        self.gfs = gfs
        self.conn = conn
        self.tunnel = tunnel
        self.config_name = config_name

    # TODO: rename jobs -> coll throughout
    coll = property(lambda s : s.jobs)

    @classmethod
    def alloc(cls, dbname, host='localhost',
            auth_dbname='admin', port=27017,
            jobs_coll='jobs', gfs_coll='fs', ssh=False, user=None, pw=None):
        connection, tunnel = connection_with_tunnel(
                host, auth_dbname, port, ssh, user, pw)
        db = connection[dbname]
        gfs = gridfs.GridFS(db, collection=gfs_coll)
        return cls(db, db[jobs_coll], gfs, connection, tunnel)

    @classmethod
    def new_from_connection_str(cls, conn_str, gfs_coll='fs', config_name='spec'):
        connection, tunnel, db, coll = connection_from_string(conn_str)
        gfs = gridfs.GridFS(db, collection=gfs_coll)
        return cls(db, coll, gfs, connection, tunnel, config_name)

    def __iter__(self):
        return self.jobs.find()

    def __len__(self):
        try:
            return self.jobs.count()
        except:
            return 0

    def create_jobs_indexes(self):
        jobs = self.db.jobs
        for k in ['exp_key', 'result.loss', 'book_time']:
            jobs.create_index(k)

    def create_drivers_indexes(self):
        drivers = self.db.drivers
        drivers.create_index('exp_key', unique=True)

    def create_indexes(self):
        self.create_jobs_indexes()
        self.create_drivers_indexes()

    def jobs_complete(self, cursor=False):
        c = self.jobs.find(spec=dict(state=JOB_STATE_DONE))
        return c if cursor else list(c)

    def jobs_error(self, cursor=False):
        c = self.jobs.find(spec=dict(state=JOB_STATE_ERROR))
        return c if cursor else list(c)

    def jobs_running(self, cursor=False):
        if cursor:
            raise NotImplementedError()
        rval = list(self.jobs.find(spec=dict(state=JOB_STATE_RUNNING)))
        #TODO: mark some as MIA
        rval = [r for r in rval if not r.get('MIA', False)]
        return rval

    def jobs_dead(self, cursor=False):
        if cursor:
            raise NotImplementedError()
        rval = list(self.jobs.find(spec=dict(state=JOB_STATE_RUNNING)))
        #TODO: mark some as MIA
        rval = [r for r in rval if r.get('MIA', False)]
        return rval

    def jobs_queued(self, cursor=False):
        c = self.jobs.find(spec=dict(state=JOB_STATE_NEW))
        return c if cursor else list(c)

    def insert(self, job):
        """Return a job dictionary by inserting the job dict into the database"""
        try:
            cpy = copy.deepcopy(job)
            # -- this call adds an _id field to cpy
            _id = self.jobs.insert(cpy, check_keys=True)
            # -- so now we return the dict with the _id field
            assert _id == cpy['_id']
            return cpy
        except pymongo.errors.OperationFailure, e:
            # -- translate pymongo error class into hyperopt error class
            #    This was meant to make it easier to catch insertion errors
            #    in a generic way even if different databases were used.
            #    ... but there's just MongoDB so far, so kinda goofy.
            raise OperationFailure(e)

    def delete(self, job):
        """Delete job[s]"""
        try:
            self.jobs.remove(job)
        except pymongo.errors.OperationFailure, e:
            # -- translate pymongo error class into hyperopt error class
            #    see insert() code for rationale.
            raise OperationFailure(e)

    def delete_all(self, cond=None):
        """Delete all jobs and attachments"""
        if cond is None:
            cond = {}
        try:
            for d in self.jobs.find(spec=cond, fields=['_id', '_attachments']):
                logger.info('deleting job %s' % d['_id'])
                for name, file_id in d.get('_attachments', []):
                    try:
                        self.gfs.delete(file_id)
                    except gridfs.errors.NoFile:
                        logger.error('failed to remove attachment %s:%s' % (
                            name, file_id))
                self.jobs.remove(d)
        except pymongo.errors.OperationFailure, e:
            # -- translate pymongo error class into hyperopt error class
            #    see insert() code for rationale.
            raise OperationFailure(e)

    def delete_all_error_jobs(self):
        return self.delete_all(cond={'state': JOB_STATE_ERROR})

    def reserve(self, host_id, cond=None, exp_key=None):
        now = coarse_utcnow()
        if cond is None:
            cond = {}
        else:
            cond = copy.copy(cond) #copy is important, will be modified, but only the top-level

        if exp_key is not None:
            cond['exp_key'] = exp_key

        #having an owner of None implies state==JOB_STATE_NEW, so this effectively
        #acts as a filter to make sure that only new jobs get reserved.
        if cond.get('owner') is not None:
            raise ValueError('refusing to reserve owned job')
        else:
            cond['owner'] = None
            cond['state'] = JOB_STATE_NEW #theoretically this is redundant, theoretically

        try:
            rval = self.jobs.find_and_modify(
                cond,
                {'$set':
                    {'owner': host_id,
                     'book_time': now,
                     'state': JOB_STATE_RUNNING,
                     'refresh_time': now,
                     }
                 },
                new=True,
                upsert=False)
        except pymongo.errors.OperationFailure, e:
            logger.error('Error during reserve_job: %s'%str(e))
            rval = None
        return rval

    def refresh(self, doc):
        self.update(doc, dict(refresh_time=coarse_utcnow()))

    def update(self, doc, dct, collection=None, do_sanity_checks=True):
        """Return union of doc and dct, after making sure that dct has been
        added to doc in `collection`.

        This function does not modify either `doc` or `dct`.

        """
        if collection is None:
            collection = self.coll

        dct = copy.deepcopy(dct)
        if '_id' not in doc:
            raise ValueError('doc must have an "_id" key to be updated')

        if '_id' in dct:
            if dct['_id'] != doc['_id']:
                raise ValueError('cannot update the _id field')
            del dct['_id']

        if 'version' in dct:
            if dct['version'] != doc['version']:
                warnings.warn('Ignoring "version" field in update dictionary')

        if 'version' in doc:
            doc_query = dict(_id=doc['_id'], version=doc['version'])
            dct['version'] = doc['version']+1
        else:
            doc_query = dict(_id=doc['_id'])
            dct['version'] = 1
        try:
            # warning - if doc matches nothing then this function succeeds
            # N.B. this matches *at most* one entry, and possibly zero
            collection.update(
                    doc_query,
                    {'$set': dct},
                    upsert=False,
                    multi=False,)
        except pymongo.errors.OperationFailure, e:
            # -- translate pymongo error class into hyperopt error class
            #    see insert() code for rationale.
            raise OperationFailure(e)

        # update doc in-place to match what happened on the server side
        doc.update(dct)

        if do_sanity_checks:
            server_doc = collection.find_one(
                    dict(_id=doc['_id'], version=doc['version']))
            if server_doc is None:
                raise OperationFailure('updated doc not found : %s'
                        % str(doc))
            elif server_doc != doc:
                if 0:# This is all commented out because it is tripping on the fact that
                    # str('a') != unicode('a').
                    # TODO: eliminate false alarms and catch real ones
                    mismatching_keys = []
                    for k, v in server_doc.items():
                        if k in doc:
                            if doc[k] != v:
                                mismatching_keys.append((k, v, doc[k]))
                        else:
                            mismatching_keys.append((k, v, '<missing>'))
                    for k,v in doc.items():
                        if k not in server_doc:
                            mismatching_keys.append((k, '<missing>', v))

                    raise OperationFailure('local and server doc documents are out of sync: %s'%
                            repr((doc, server_doc, mismatching_keys)))
        return doc

    def attachment_names(self, doc):
        def as_str(name_id):
            assert isinstance(name_id[0], basestring), name_id
            return str(name_id[0])
        return map(as_str, doc.get('_attachments', []))

    def set_attachment(self, doc, blob, name, collection=None):
        """Attach potentially large data string `blob` to `doc` by name `name`

        blob must be a string

        doc must have been saved in some collection (must have an _id), but not
        necessarily the jobs collection.

        name must be a string

        Returns None
        """

        # If there is already a file with the given name for this doc, then we will delete it
        # after writing the new file
        attachments = doc.get('_attachments', [])
        name_matches = [a for a in attachments if a[0] == name]

        # the filename is set to something so that fs.list() will display the file
        new_file_id = self.gfs.put(blob, filename='%s_%s' % (doc['_id'], name))
        logger.info('stored blob of %i bytes with id=%s and filename %s_%s' % (
            len(blob), str(new_file_id), doc['_id'], name))

        new_attachments = ([a for a in attachments if a[0] != name]
                + [(name, new_file_id)])

        try:
            ii = 0
            doc = self.update(doc, {'_attachments': new_attachments},
                    collection=collection)
            # there is a database leak until we actually delete the files that
            # are no longer pointed to by new_attachments
            while ii < len(name_matches):
                self.gfs.delete(name_matches[ii][1])
                ii += 1
        except:
            while ii < len(name_matches):
                logger.warning("Leak during set_attachment: old_file_id=%s" % (
                    name_matches[ii][1]))
                ii += 1
            raise
        assert len([n for n in self.attachment_names(doc) if n == name]) == 1
        #return new_file_id

    def get_attachment(self, doc, name):
        """Retrieve data attached to `doc` by `attach_blob`.

        Raises OperationFailure if `name` does not correspond to an attached blob.

        Returns the blob as a string.
        """
        attachments = doc.get('_attachments', [])
        file_ids = [a[1] for a in attachments if a[0] == name]
        if not file_ids:
            raise OperationFailure('Attachment not found: %s' % name)
        if len(file_ids) > 1:
            raise OperationFailure('multiple name matches', (name, file_ids))
        return self.gfs.get(file_ids[0]).read()

    def delete_attachment(self, doc, name, collection=None):
        attachments = doc.get('_attachments', [])
        file_id = None
        for i,a in enumerate(attachments):
            if a[0] == name:
                file_id = a[1]
                break
        if file_id is None:
            raise OperationFailure('Attachment not found: %s' % name)
        #print "Deleting", file_id
        del attachments[i]
        self.update(doc, {'_attachments':attachments}, collection=collection)
        self.gfs.delete(file_id)


class MongoTrials(Trials):
    """Trials maps on to an entire mongo collection. It's basically a wrapper
    around MongoJobs for now.

    As a concession to performance, this object permits trial filtering based
    on the exp_key, but I feel that's a hack. The case of `cmd` is similar--
    the exp_key and cmd are semantically coupled.

    WRITING TO THE DATABASE
    -----------------------
    The trials object is meant for *reading* a trials database. Writing
    to a database is different enough from writing to an in-memory
    collection that no attempt has been made to abstract away that
    difference.  If you want to update the documents within
    a MongoTrials collection, then retrieve the `.handle` attribute (a
    MongoJobs instance) and use lower-level methods, or pymongo's
    interface directly.  When you are done writing, call refresh() or
    refresh_tids() to bring the MongoTrials up to date.
    """
    async = True

    def __init__(self, arg, exp_key=None, cmd=None, workdir=None,
            refresh=True):
        if isinstance(arg, MongoJobs):
            self.handle = arg
        else:
            connection_string = arg
            self.handle = MongoJobs.new_from_connection_str(connection_string)
        self.handle.create_indexes()
        self._exp_key = exp_key
        self.cmd = cmd
        self.workdir = workdir
        if refresh:
            self.refresh()

    def view(self, exp_key=None, cmd=None, workdir=None, refresh=True):
        rval = self.__class__(self.handle,
                exp_key=self._exp_key if exp_key is None else exp_key,
                cmd=self.cmd if cmd is None else cmd,
                workdir=self.workdir if workdir is None else workdir,
                refresh=refresh)
        return rval

    def refresh_tids(self, tids):
        """ Sync documents with `['tid']` in the list of `tids` from the
        database (not *to* the database).

        Local trial documents whose tid is not in `tids` are not
        affected by this call.  Local trial documents whose tid is in `tids` may
        be:

        * *deleted* (if db no longer has corresponding document), or
        * *updated* (if db has an updated document) or,
        * *left alone* (if db document matches local one).

        Additionally, if the db has a matching document, but there is no
        local trial with a matching tid, then the db document will be
        *inserted* into the local collection.

        """
        exp_key = self._exp_key
        if exp_key != None:
            query = {'exp_key' : exp_key}
        else:
            query = {}
        t0 = time.time()
        query['state'] = {'$ne': JOB_STATE_ERROR}
        if tids is not None:
            query['tid'] = {'$in': list(tids)}
        orig_trials = getattr(self, '_trials', [])
        _trials = orig_trials[:] #copy to make sure it doesn't get screwed up
        if _trials:
            db_data = list(self.handle.jobs.find(query,
                                            fields=['_id', 'version']))
            # -- pull down a fresh list of ids from mongo
            if db_data:
                #make numpy data arrays
                db_data = numpy.rec.array([(x['_id'], int(x['version']))
                                        for x in db_data],
                                        names=['_id', 'version'])
                db_data.sort(order=['_id', 'version'])
                db_data = db_data[get_most_recent_inds(db_data)]

                existing_data = numpy.rec.array([(x['_id'],
                                              int(x['version'])) for x in _trials],
                                              names=['_id', 'version'])
                existing_data.sort(order=['_id', 'version'])

                #which records are in db but not in existing, and vice versa
                db_in_existing = fast_isin(db_data['_id'], existing_data['_id'])
                existing_in_db = fast_isin(existing_data['_id'], db_data['_id'])

                #filtering out out-of-date records
                _trials = [_trials[_ind] for _ind in existing_in_db.nonzero()[0]]

                #new data is what's in db that's not in existing
                new_data = db_data[numpy.invert(db_in_existing)]

                #having removed the new and out of data data,
                #concentrating on data in db and existing for state changes
                db_data = db_data[db_in_existing]
                existing_data = existing_data[existing_in_db]
                try:
                    assert len(db_data) == len(existing_data)
                    assert (existing_data['_id'] == db_data['_id']).all()
                    assert (existing_data['version'] <= db_data['version']).all()
                except:
                    reportpath = os.path.join(os.getcwd(),
                             'hyperopt_refresh_crash_report_' + \
                                      str(numpy.random.randint(1e8)) + '.pkl')
                    logger.error('HYPEROPT REFRESH ERROR: writing error file to %s' % reportpath)
                    _file = open(reportpath, 'w')
                    cPickle.dump({'db_data': db_data,
                                  'existing_data': existing_data},
                                _file)
                    _file.close()
                    raise

                same_version = existing_data['version'] == db_data['version']
                _trials = [_trials[_ind] for _ind in same_version.nonzero()[0]]
                version_changes = existing_data[numpy.invert(same_version)]

                #actually get the updated records
                update_ids = new_data['_id'].tolist() + version_changes['_id'].tolist()
                num_new = len(update_ids)
                update_query = copy.deepcopy(query)
                update_query['_id'] = {'$in': update_ids}
                updated_trials = list(self.handle.jobs.find(update_query))
                _trials.extend(updated_trials)
            else:
                num_new = 0
                _trials = []
        else:
            #this case is for performance, though should be able to be removed
            #without breaking correctness.
            _trials = list(self.handle.jobs.find(query))
            if _trials:
                _trials = [_trials[_i] for _i in get_most_recent_inds(_trials)]
            num_new = len(_trials)

        logger.debug('Refresh data download took %f seconds for %d ids' %
                         (time.time() - t0, num_new))

        if tids is not None:
            # -- If tids were given, then _trials only contains
            #    documents with matching tids. Here we augment these
            #    fresh matching documents, with our current ones whose
            #    tids don't match.
            new_trials = _trials
            tids_set = set(tids)
            assert all(t['tid'] in tids_set for t in new_trials)
            old_trials = [t for t in orig_trials if t['tid'] not in tids_set]
            _trials = new_trials + old_trials

        # -- reassign new trials to self, in order of increasing tid
        jarray = numpy.array([j['_id'] for j in _trials])
        jobsort = jarray.argsort()
        self._trials = [_trials[_idx] for _idx in jobsort]
        self._specs = [_trials[_idx]['spec'] for _idx in jobsort]
        self._results = [_trials[_idx]['result'] for _idx in jobsort]
        self._miscs = [_trials[_idx]['misc'] for _idx in jobsort]

    def refresh(self):
        self.refresh_tids(None)

    def _insert_trial_docs(self, docs):
        rval = []
        for doc in docs:
            rval.append(self.handle.jobs.insert(doc))
        return rval

    def count_by_state_unsynced(self, arg):
        exp_key = self._exp_key
        # TODO: consider searching by SON rather than dict
        if isinstance(arg, int):
            if arg not in JOB_STATES:
                raise ValueError('invalid state', arg)
            query = dict(state=arg)
        else:
            assert hasattr(arg, '__iter__')
            states = list(arg)
            assert all([x in JOB_STATES for x in states])
            query = dict(state={'$in': states})
        if exp_key != None:
            query['exp_key'] = exp_key
        rval = self.handle.jobs.find(query).count()
        return rval

    def delete_all(self, cond=None):
        if cond is None:
            cond = {}
        else:
            cond = dict(cond)

        if self._exp_key:
            cond['exp_key'] = self._exp_key
        # -- remove all documents matching condition
        self.handle.delete_all(cond)
        gfs = self.handle.gfs
        for filename in gfs.list():
            try:
                fdoc = gfs.get_last_version(filename=filename, **cond)
            except gridfs.errors.NoFile:
                continue
            gfs.delete(fdoc._id)
        self.refresh()

    def new_trial_ids(self, N):
        db = self.handle.db
        # N.B. that the exp key is *not* used here. It was once, but it caused
        # a nasty bug: tids were generated by a global experiment
        # with exp_key=None, running a suggest() that introduced sub-experiments
        # with exp_keys, which ran jobs that did result injection.  The tids of
        # injected jobs were sometimes unique within an experiment, and
        # sometimes not. Hilarious!
        #
        # Solution: tids are generated to be unique across the db, not just
        # within an exp_key.
        #

        # -- mongo docs say you can't upsert an empty document
        query = {'a': 0}

        doc = None
        while doc is None:
            doc = db.job_ids.find_and_modify(
                    query,
                    {'$inc' : {'last_id': N}},
                    upsert=True)
            if doc is None:
                logger.warning('no last_id found, re-trying')
                time.sleep(1.0)
        lid = doc.get('last_id', 0)
        return range(lid, lid + N)

    def trial_attachments(self, trial):
        """
        Attachments to a single trial (e.g. learned weights)

        Returns a dictionary interface to the attachments.
        """

        # don't offer more here than in MongoCtrl
        class Attachments(object):
            def __contains__(_self, name):
                return name in self.handle.attachment_names(doc=trial)

            def __len__(_self):
                return len(self.handle.attachment_names(doc=trial))

            def __iter__(_self):
                return iter(self.handle.attachment_names(doc=trial))

            def __getitem__(_self, name):
                try:
                    return self.handle.get_attachment(
                        doc=trial,
                        name=name)
                except OperationFailure:
                    raise KeyError(name)

            def __setitem__(_self, name, value):
                self.handle.set_attachment(
                    doc=trial,
                    blob=value,
                    name=name,
                    collection=self.handle.db.jobs)

            def __delitem__(_self, name):
                raise NotImplementedError('delete trial_attachment')

            def keys(self):
                return [k for k in self]

            def values(self):
                return [self[k] for k in self]

            def items(self):
                return [(k, self[k]) for k in self]

        return Attachments()

    @property
    def attachments(self):
        """
        Attachments to a Trials set (such as bandit args).

        Support syntax for load:  self.attachments[name]
        Support syntax for store: self.attachments[name] = value
        """
        gfs = self.handle.gfs

        query = {}
        if self._exp_key:
            query['exp_key'] = self._exp_key

        class Attachments(object):
            def __iter__(_self):
                if query:
                    # -- gfs.list does not accept query kwargs
                    #    (at least, as of pymongo 2.4)
                    filenames = [fname
                                 for fname in gfs.list()
                                 if fname in _self]
                else:
                    filenames = gfs.list()
                return iter(filenames)

            def __contains__(_self, name):
                return gfs.exists(filename=name, **query)

            def __getitem__(_self, name):
                try:
                    rval = gfs.get_version(filename=name, **query).read()
                    return rval
                except gridfs.NoFile:
                    raise KeyError(name)

            def __setitem__(_self, name, value):
                if gfs.exists(filename=name, **query):
                    gout = gfs.get_last_version(filename=name, **query)
                    gfs.delete(gout._id)
                gfs.put(value, filename=name, **query)

            def __delitem__(_self, name):
                gout = gfs.get_last_version(filename=name, **query)
                gfs.delete(gout._id)

        return Attachments()


class MongoWorker(object):
    poll_interval = 3.0  # -- seconds
    workdir = None

    def __init__(self, mj,
            poll_interval=poll_interval,
            workdir=workdir,
            exp_key=None,
            logfilename='logfile.txt',
            ):
        """
        mj - MongoJobs interface to jobs collection
        poll_interval - seconds
        workdir - string
        exp_key - restrict reservations to this key
        """
        self.mj = mj
        self.poll_interval = poll_interval
        self.workdir = workdir
        self.exp_key = exp_key
        self.logfilename = logfilename

    def make_log_handler(self):
        self.log_handler = logging.FileHandler(self.logfilename)
        self.log_handler.setFormatter(
            logging.Formatter(
                fmt='%(levelname)s (%(name)s): %(message)s'))
        self.log_handler.setLevel(logging.INFO)

    def run_one(self,
        host_id=None,
        reserve_timeout=None,
        erase_created_workdir=False,
        ):
        if host_id == None:
            host_id = '%s:%i'%(socket.gethostname(), os.getpid()),
        job = None
        start_time = time.time()
        mj = self.mj
        while job is None:
            if (reserve_timeout
                    and (time.time() - start_time) > reserve_timeout):
                raise ReserveTimeout()
            job = mj.reserve(host_id, exp_key=self.exp_key)
            if not job:
                interval = (1 +
                        numpy.random.rand()
                        * (float(self.poll_interval) - 1.0))
                logger.info('no job found, sleeping for %.1fs' % interval)
                time.sleep(interval)

        logger.debug('job found: %s' % str(job))

        # -- don't let the cmd mess up our trial object
        spec = spec_from_misc(job['misc'])

        ctrl = MongoCtrl(
                trials=MongoTrials(mj, exp_key=job['exp_key'], refresh=False),
                read_only=False,
                current_trial=job)
        if self.workdir is None:
            workdir = job['misc'].get('workdir', os.getcwd())
            if workdir is None:
                workdir = ''
            workdir = os.path.join(workdir, str(job['_id']))
        else:
            workdir = self.workdir
        workdir = os.path.abspath(os.path.expanduser(workdir))
        cwd = os.getcwd()
        sentinal = None
        if not os.path.isdir(workdir):
            # -- figure out the closest point to the workdir in the filesystem
            closest_dir = ''
            for wdi in os.path.split(workdir):
                if os.path.isdir(os.path.join(closest_dir, wdi)):
                    closest_dir = os.path.join(closest_dir, wdi)
                else:
                    break
            assert closest_dir != workdir

            # -- touch a sentinal file so that recursive directory
            #    removal stops at the right place
            sentinal = os.path.join(closest_dir, wdi + '.inuse')
            logger.debug("touching sentinal file: %s" % sentinal)
            open(sentinal, 'w').close()
            # -- now just make the rest of the folders
            logger.debug("making workdir: %s" % workdir)
            os.makedirs(workdir)
        try:
            root_logger = logging.getLogger()
            if self.logfilename:
                self.make_log_handler()
                root_logger.addHandler(self.log_handler)

            cmd = job['misc']['cmd']
            cmd_protocol = cmd[0]
            try:
                if cmd_protocol == 'cpickled fn':
                    worker_fn = cPickle.loads(cmd[1])
                elif cmd_protocol == 'call evaluate':
                    bandit = cPickle.loads(cmd[1])
                    worker_fn = bandit.evaluate
                elif cmd_protocol == 'token_load':
                    cmd_toks = cmd[1].split('.')
                    cmd_module = '.'.join(cmd_toks[:-1])
                    worker_fn = exec_import(cmd_module, cmd[1])
                elif cmd_protocol == 'bandit_json evaluate':
                    bandit = json_call(cmd[1])
                    worker_fn = bandit.evaluate
                elif cmd_protocol == 'driver_attachment':
                    #name = 'driver_attachment_%s' % job['exp_key']
                    blob = ctrl.trials.attachments[cmd[1]]
                    bandit_name, bandit_args, bandit_kwargs = cPickle.loads(blob)
                    worker_fn = json_call(bandit_name,
                            args=bandit_args,
                            kwargs=bandit_kwargs).evaluate
                elif cmd_protocol == 'domain_attachment':
                    blob = ctrl.trials.attachments[cmd[1]]
                    try:
                        domain = cPickle.loads(blob)
                    except BaseException, e:
                        logger.info('Error while unpickling. Try installing dill via "pip install dill" for enhanced pickling support.')
                        raise
                    worker_fn = domain.evaluate
                else:
                    raise ValueError('Unrecognized cmd protocol', cmd_protocol)

                result = worker_fn(spec, ctrl)
                result = SONify(result)
            except BaseException, e:
                #XXX: save exception to database, but if this fails, then
                #      at least raise the original traceback properly
                logger.info('job exception: %s' % str(e))
                ctrl.checkpoint()
                mj.update(job,
                        {'state': JOB_STATE_ERROR,
                        'error': (str(type(e)), str(e))})
                raise
        finally:
            if self.logfilename:
                root_logger.removeHandler(self.log_handler)
            os.chdir(cwd)

        logger.info('job finished: %s' % str(job['_id']))
        attachments = result.pop('attachments', {})
        for aname, aval in attachments.items():
            logger.info(
                'mongoexp: saving attachment name=%s (%i bytes)' % (
                    aname, len(aval)))
            ctrl.attachments[aname] = aval
        ctrl.checkpoint(result)
        mj.update(job, {'state': JOB_STATE_DONE})

        if sentinal:
            if erase_created_workdir:
                logger.debug('MongoWorker.run_one: rmtree %s' % workdir)
                shutil.rmtree(workdir)
                # -- put it back so that recursive removedirs works
                os.mkdir(workdir)
                # -- recursive backtrack to sentinal
                logger.debug('MongoWorker.run_one: removedirs %s'
                             % workdir)
                os.removedirs(workdir)
            # -- remove sentinal
            logger.debug('MongoWorker.run_one: rm %s' % sentinal)
            os.remove(sentinal)


class MongoCtrl(Ctrl):
    """
    Attributes:

    current_trial - current job document
    jobs - MongoJobs object in which current_trial resides
    read_only - True means don't change the db

    """
    def __init__(self, trials, current_trial, read_only):
        self.trials = trials
        self.current_trial = current_trial
        self.read_only = read_only

    def debug(self, *args, **kwargs):
        # XXX: This is supposed to log to db
        return logger.debug(*args, **kwargs)

    def info(self, *args, **kwargs):
        # XXX: This is supposed to log to db
        return logger.info(*args, **kwargs)

    def warn(self, *args, **kwargs):
        # XXX: This is supposed to log to db
        return logger.warn(*args, **kwargs)

    def error(self, *args, **kwargs):
        # XXX: This is supposed to log to db
        return logger.error(*args, **kwargs)

    def checkpoint(self, result=None):
        if not self.read_only:
            handle = self.trials.handle
            handle.refresh(self.current_trial)
            if result is not None:
                return handle.update(self.current_trial, dict(result=result))

    @property
    def attachments(self):
        """
        Support syntax for load:  self.attachments[name]
        Support syntax for store: self.attachments[name] = value
        """
        return self.trials.trial_attachments(trial=self.current_trial)

    @property
    def set_attachment(self):
        # XXX: Is there a better deprecation error?
        raise RuntimeError(
            'set_attachment deprecated. Use `self.attachments[name] = value`')


def exec_import(cmd_module, cmd):
    worker_fn = None
    exec('import %s; worker_fn = %s' % (cmd_module, cmd))
    return worker_fn


def as_mongo_str(s):
    if s.startswith('mongo://'):
        return s
    else:
        return 'mongo://%s' % s


def main_worker_helper(options, args):
    N = int(options.max_jobs)
    if options.last_job_timeout is not None:
        last_job_timeout = time.time() + float(options.last_job_timeout)
    else:
        last_job_timeout = None

    def sighandler_shutdown(signum, frame):
        logger.info('Caught signal %i, shutting down.' % signum)
        raise Shutdown(signum)

    def sighandler_wait_quit(signum, frame):
        logger.info('Caught signal %i, shutting down.' % signum)
        raise WaitQuit(signum)

    signal.signal(signal.SIGINT, sighandler_shutdown)
    signal.signal(signal.SIGHUP, sighandler_shutdown)
    signal.signal(signal.SIGTERM, sighandler_shutdown)
    signal.signal(signal.SIGUSR1, sighandler_wait_quit)

    if N > 1:
        proc = None
        cons_errs = 0
        if last_job_timeout and time.time() > last_job_timeout:
            logger.info("Exiting due to last_job_timeout")
            return

        while N and cons_errs < int(options.max_consecutive_failures):
            try:
                # recursive Popen, dropping N from the argv
                # By using another process to run this job
                # we protect ourselves from memory leaks, bad cleanup
                # and other annoying details.
                # The tradeoff is that a large dataset must be reloaded once for
                # each subprocess.
                sub_argv = [sys.argv[0],
                        '--poll-interval=%s' % options.poll_interval,
                        '--max-jobs=1',
                        '--mongo=%s' % options.mongo,
                        '--reserve-timeout=%s' % options.reserve_timeout]
                if options.workdir is not None:
                    sub_argv.append('--workdir=%s' % options.workdir)
                if options.exp_key is not None:
                    sub_argv.append('--exp-key=%s' % options.exp_key)
                proc = subprocess.Popen(sub_argv)
                retcode = proc.wait()
                proc = None

            except Shutdown:
                #this is the normal way to stop the infinite loop (if originally N=-1)
                if proc:
                    #proc.terminate() is only available as of 2.6
                    os.kill(proc.pid, signal.SIGTERM)
                    return proc.wait()
                else:
                    return 0

            except WaitQuit:
                # -- sending SIGUSR1 to a looping process will cause it to
                # break out of the loop after the current subprocess finishes
                # normally.
                if proc:
                    return proc.wait()
                else:
                    return 0

            if retcode != 0:
                cons_errs += 1
            else:
                cons_errs = 0
            N -= 1
        logger.info("exiting with N=%i after %i consecutive exceptions" %(
            N, cons_errs))
    elif N == 1:
        # XXX: the name of the jobs collection is a parameter elsewhere,
        #      so '/jobs' should not be hard-coded here
        mj = MongoJobs.new_from_connection_str(
                as_mongo_str(options.mongo) + '/jobs')

        mworker = MongoWorker(mj,
                float(options.poll_interval),
                workdir=options.workdir,
                exp_key=options.exp_key)
        mworker.run_one(reserve_timeout=float(options.reserve_timeout))
    else:
        raise ValueError("N <= 0")


def main_worker():
    parser = optparse.OptionParser(usage="%prog [options]")

    parser.add_option("--exp-key",
            dest='exp_key',
            default = None,
            metavar='str',
            help="identifier for this workers's jobs")
    parser.add_option("--last-job-timeout",
            dest='last_job_timeout',
            metavar='T',
            default=None,
            help="Do not reserve a job after T seconds have passed")
    parser.add_option("--max-consecutive-failures",
            dest="max_consecutive_failures",
            metavar='N',
            default=4,
            help="stop if N consecutive jobs fail (default: 4)")
    parser.add_option("--max-jobs",
            dest='max_jobs',
            default=sys.maxint,
            help="stop after running this many jobs (default: inf)")
    parser.add_option("--mongo",
            dest='mongo',
            default='localhost/hyperopt',
            help="<host>[:port]/<db> for IPC and job storage")
    parser.add_option("--poll-interval",
            dest='poll_interval',
            metavar='N',
            default=5,
            help="check work queue every 1 < T < N seconds (default: 5")
    parser.add_option("--reserve-timeout",
            dest='reserve_timeout',
            metavar='T',
            default=120.0,
            help="poll database for up to T seconds to reserve a job")
    parser.add_option("--workdir",
            dest="workdir",
            default=None,
            help="root workdir (default: load from mongo)",
            metavar="DIR")

    (options, args) = parser.parse_args()

    if args:
        parser.print_help()
        return -1

    return main_worker_helper(options, args)


########NEW FILE########
__FILENAME__ = plotting
"""
Functions to visualize an Experiment.

"""

__authors__   = "James Bergstra"
__license__   = "3-clause BSD License"
__contact__   = "github.com/hyperopt/hyperopt"

import math
import sys

# -- don't import this here because it locks in the backend
#    and we want the unittests to be able to set the backend
##import matplotlib.pyplot as plt

import numpy as np
from . import base
from .base import miscs_to_idxs_vals

default_status_colors = {
    base.STATUS_NEW: 'k',
    base.STATUS_RUNNING: 'g',
    base.STATUS_OK:'b',
    base.STATUS_FAIL:'r'}

def algo_as_str(algo):
    if isinstance(algo, basestring):
        return algo
    return str(algo)


def main_plot_history(trials, bandit=None, algo=None, do_show=True,
        status_colors=None):
    # -- import here because file-level import is too early
    import matplotlib.pyplot as plt

    # self is an Experiment
    if status_colors is None:
        status_colors = default_status_colors

    # XXX: show the un-finished or error trials
    Ys, colors = zip(*[(y, status_colors[s])
        for y, s in zip(trials.losses(bandit), trials.statuses(bandit))
        if y is not None])
    plt.scatter(range(len(Ys)), Ys, c=colors)
    plt.xlabel('time')
    plt.ylabel('loss')

    if bandit is not None and bandit.loss_target is not None:
        plt.axhline(bandit.loss_target)
        ymin = min(np.min(Ys), bandit.loss_target)
        ymax = max(np.max(Ys), bandit.loss_target)
        yrange = ymax - ymin
        ymean = (ymax + ymin) / 2.0
        plt.ylim(
                ymean - 0.53 * yrange,
                ymean + 0.53 * yrange,
                )
    best_err = trials.average_best_error(bandit)
    print "avg best error:", best_err
    plt.axhline(best_err, c='g')

    plt.title('bandit: %s algo: %s' % (
        bandit.short_str() if bandit else '-',
        algo_as_str(algo)))
    if do_show:
        plt.show()


def main_plot_histogram(trials, bandit=None, algo=None, do_show=True):
    # -- import here because file-level import is too early
    import matplotlib.pyplot as plt

    status_colors = default_status_colors
    Xs, Ys, Ss, Cs= zip(*[(x, y, s, status_colors[s])
        for (x, y, s) in zip(trials.specs, trials.losses(bandit),
            trials.statuses(bandit))
        if y is not None ])


    # XXX: deal with ok vs. un-finished vs. error trials
    print 'Showing Histogram of %i jobs' % len(Ys)
    plt.hist(Ys)
    plt.xlabel('loss')
    plt.ylabel('frequency')

    plt.title('bandit: %s algo: %s' % (
        bandit.short_str() if bandit else '-',
        algo_as_str(algo)))
    if do_show:
        plt.show()


def main_plot_vars(trials, bandit=None, do_show=True, fontsize=10,
        colorize_best=None,
        columns=5,
        ):
    # -- import here because file-level import is too early
    import matplotlib.pyplot as plt

    idxs, vals = miscs_to_idxs_vals(trials.miscs)
    losses = trials.losses()
    finite_losses = [y for y in losses if y not in (None, float('inf'))]
    asrt = np.argsort(finite_losses)
    if colorize_best != None:
        colorize_thresh = finite_losses[asrt[colorize_best + 1]]
    else:
        # -- set to lower than best (disabled)
        colorize_thresh = finite_losses[asrt[0]] - 1

    loss_min = min(finite_losses)
    loss_max = max(finite_losses)
    print 'finite loss range', loss_min, loss_max, colorize_thresh

    loss_by_tid = dict(zip(trials.tids, losses))

    def color_fn(lossval):
        if lossval is None:
            return (1, 1, 1)
        else:
            t = 4 * (lossval - loss_min) / (loss_max - loss_min + .0001)
            if t < 1:
                return t, 0, 0
            if t < 2:
                return 2-t, t-1, 0
            if t < 3:
                return 0, 3-t, t-2
            return 0, 0, 4-t

    def color_fn_bw(lossval):
        if lossval in (None, float('inf')):
            return (1, 1, 1)
        else:
            t = (lossval - loss_min) / (loss_max - loss_min + .0001)
            if lossval < colorize_thresh:
                return (0., 1. - t, 0.)  # -- red best black worst
            else:
                return (t, t, t)    # -- white=worst, black=best

    all_labels = list(idxs.keys())
    titles = ['%s (%s)' % (label, bandit.params[label].name)
            for label in all_labels]
    order = np.argsort(titles)

    C = columns
    R = int(np.ceil(len(all_labels) / float(C)))

    for plotnum, varnum in enumerate(order):
        #print varnum, titles[varnum]
        label = all_labels[varnum]
        plt.subplot(R, C, plotnum + 1)
        #print '-' * 80
        #print 'Node', label

        # hide x ticks
        ticks_num, ticks_txt = plt.xticks()
        plt.xticks(ticks_num, ['' for i in xrange(len(ticks_num))])

        dist_name = bandit.params[label].name
        x = idxs[label]
        if 'log' in dist_name:
            y = np.log(vals[label])
        else:
            y = vals[label]
        plt.title(titles[varnum], fontsize=fontsize)
        c = map(color_fn_bw, [loss_by_tid[ii] for ii in idxs[label]])
        if len(y):
            plt.scatter(x, y, c=c)
        if 'log' in dist_name:
            nums, texts = plt.yticks()
            plt.yticks(nums, ['%.2e' % np.exp(t) for t in nums])

    if do_show:
        plt.show()



if 0:
    def erf(x):
        """Erf impl that doesn't require scipy.
        """
        # from http://www.math.sfu.ca/~cbm/aands/frameindex.htm
        # via
        # http://stackoverflow.com/questions/457408/
        #      is-there-an-easily-available-implementation-of-erf-for-python
        #
        #

        # save the sign of x
        sign = 1
        if x < 0:
            sign = -1
        x = abs(x)

        # constants
        a1 =  0.254829592
        a2 = -0.284496736
        a3 =  1.421413741
        a4 = -1.453152027
        a5 =  1.061405429
        p  =  0.3275911

        # A&S formula 7.1.26
        t = 1.0/(1.0 + p*x)
        y = 1.0 - (((((a5*t + a4)*t) + a3)*t + a2)*t + a1)*t*math.exp(-x*x)
        return sign*y # erf(-x) = -erf(x)

    def mixed_max_erf(scores, n_valid):
        scores = list(scores) # shallow copy
        scores.sort()         # sort the copy
        scores.reverse()      # reverse the order

        #this is valid for classification
        # where the scores are the means of Bernoulli variables.
        best_mean = scores[0][0]
        best_variance = best_mean * (1.0 - best_mean) / (n_valid - 1)

        rval = 0.0
        rval_denom = 0.0

        for i, (vscore,tscore) in enumerate(scores):
            mean = vscore
            variance = mean * (1.0 - mean) / (n_valid - 1)
            diff_mean = mean - best_mean
            diff_variance = variance + best_variance
            # for scores, which should approach 1, the diff here will be negative (or zero).
            # so the probability of the current point being the best is the probability that
            # the current gaussian puts on positive values.
            assert diff_mean <= 0.0
            p_current_is_best = 0.5 - 0.5 * erf(-diff_mean / math.sqrt(diff_variance))
            rval += p_current_is_best * tscore
            rval_denom += p_current_is_best
            if p_current_is_best < 0.001:
                #print 'breaking after',i, 'examples'
                break
        return rval / rval_denom
    def mixed_max_sampled(scores, n_valid, n_samples=100, rng=None):
        scores = list(scores) # shallow copy
        scores.sort()         # sort the copy
        scores.reverse()      # reverse the order

        # this is valid for classification
        # where the scores are the means of Bernoulli variables.
        best_mean = scores[0][0]
        best_variance = best_mean * (1.0 - best_mean) / (n_valid - 1)
        mu = []
        sigma = []
        tscores = []
        for i, (vscore,tscore) in enumerate(scores):
            mean = vscore
            variance = mean * (1.0 - mean) / (n_valid - 1)
            diff_mean = mean - best_mean
            diff_variance = variance + best_variance
            # for scores, which should approach 1, the diff here will be negative (or zero).
            # so the probability of the current point being the best is the probability that
            # the current gaussian puts on positive values.

            if -diff_mean / np.sqrt(diff_variance) > 3:
                #print 'breaking after', len(tscores), len(scores)
                break
            else:
                mu.append(diff_mean)
                sigma.append(np.sqrt(diff_variance))
                tscores.append(tscore)

        if rng is None:
            rng = np.random.RandomState(232342)

        mu = np.asarray(mu)
        sigma = np.asarray(sigma)
        tscores = np.asarray(tscores)

        nrml = rng.randn(n_samples, len(mu)) * sigma + mu
        winners = (nrml.T == nrml.max(axis=1))
        p_best_ = winners.sum(axis=0)
        p_best = p_best_ / p_best_.sum()

        return np.dot(p_best, t_scores), p_best


if 0:
    def rexp_plot_acc(scores, n_valid, n_test, pbest_n_samples=100, rng=None):
        """
        Uses the current pyplot figure to show efficiency of random experiment.

        :type scores: a list of (validation accuracy, test accuracy)  pairs
        :param scores: results from the trials of a random experiment

        :type n_valid: integer
        :param n_valid: size of the validation set

        :type n_test: integer
        :param n_test: size of the test set

        :type mixed_max: function like mixed_max_erf or mixed_max_sampled
        :param mixed_max: the function to estimate the maximum of a validation sample

        """
        if rng is None:
            rng = np.random.RandomState(232342)
        K = 1
        scatter_x = []
        scatter_y = []
        scatter_c = []
        box_x = []
        log_K = 0
        while K < len(scores):
            n_batches_of_K = len(scores)//K
            if n_batches_of_K < 2:
                break

            def best_score(i):
                scores_i = scores[i*K:(i+1)*K]
                rval= np.dot(
                        [tscore for (vscore,tscore) in scores_i],
                        pbest_sampled(
                            [vscore for (vscore,tscore) in scores_i],
                            n_valid,
                            n_samples=pbest_n_samples,
                            rng=rng))
                #print rval
                return rval

            if n_batches_of_K < 10:
                # use scatter plot
                for i in xrange(n_batches_of_K):
                    scatter_x.append(log_K+1)
                    scatter_y.append(best_score(i))
                    scatter_c.append((0,0,0))
                box_x.append([])
            else:
                # use box plot
                box_x.append([best_score(i) for i in xrange(n_batches_of_K)])
            K *= 2
            log_K += 1
        plt.scatter( scatter_x, scatter_y, c=scatter_c, marker='+', linewidths=0.2,
                edgecolors=scatter_c)
        boxplot_lines = plt.boxplot(box_x)
        for key in boxplot_lines:
            plt.setp(boxplot_lines[key], color='black')
        #plt.setp(boxplot_lines['medians'], color=(.5,.5,.5))

        # draw the spans
        #
        # the 'test performance of the best model' is a mixture of gaussian-distributed quantity
        # with components comp_mean, and comp_var and weights w
        #
        # w[i] is prob. of i'th model being best in validation
        w = pbest_sampled([vs for (vs,ts) in scores], n_valid, n_samples=pbest_n_samples, rng=rng)
        comp_mean = np.asarray([ts for (vs,ts) in scores])
        comp_var = (comp_mean * (1-comp_mean)) / (n_test-1)

        # the mean of the mixture is
        mean = np.dot(w, comp_mean)

        #the variance of the mixture is
        var = np.dot(w, comp_mean**2 + comp_var) - mean**2

        # test average is distributed according to a mixture of gaussians, so we have to use the following fo
        std = math.sqrt(var)
        #plt.axhline(mean, color=(1.0,1.0,1.0), linestyle='--', linewidth=0.1)
        #plt.axhspan(mean-1.96*std, mean+1.96*std, color=(0.5,0.5,0.5))
        plt.axhline(mean-1.96*std, color=(0.0,0.0,0.0))
        plt.axhline(mean+1.96*std, color=(0.0,0.0,0.0))

        # get margin:
        if 0:
            margin = 1.0 - mean
            plt.ylim(0.5-margin, 1.0 )

        # set ticks
        ticks_num, ticks_txt = plt.xticks()
        plt.xticks(ticks_num, ['%i'%(2**i) for i in xrange(len(ticks_num))])


    def rexp_pairs_raw(x, y, vscores):
        if len(x) != len(y): raise ValueError()
        if len(x) != len(vscores): raise ValueError()

        vxy = zip(vscores, x, y)
        vxy.sort()
        vscores, x, y = zip(*vxy)

        vscores = np.asarray(vscores)

        max_score = vscores.max()
        min_score = vscores.min()
        colors = np.outer(0.9 - 0.89*(vscores - min_score)/(max_score- min_score), [1,1,1])
        plt.scatter( x, y, c=colors, marker='o', linewidths=0.1)

        #remove ticks labels
        nums, texts = plt.xticks()
        plt.xticks(nums, ['']*len(nums))
        nums, texts = plt.yticks()
        plt.yticks(nums, ['']*len(nums))

    class CoordType(object):pass
    class RealCoord(CoordType):
        @staticmethod
        def preimage(x): return np.asarray(x)
    class LogCoord(CoordType):
        @staticmethod
        def preimage(x): return np.log(x)
    class Log0Coord(CoordType):
        @staticmethod
        def preimage(x):
            x = np.asarray(x)
            return np.log(x+(x==0)*x.min()/2)
    IntCoord = RealCoord
    LogIntCoord = LogCoord
    class CategoryCoord(CoordType):
        def __init__(self, categories=None):
            self.categories = categories
        def preimage(self, x):
            if self.categories:
                return np.asarray([self.categories.index(xi) for xi in x])
            else:
                return x

    def rexp_pairs(x, y, vscores, xtype, ytype):
        return rexp_pairs_raw(xtype.preimage(x), ytype.preimage(y), vscores)

    class MultiHistory(object):
        """
        Show the history of multiple optimization algorithms.
        """
        def __init__(self):
            self.histories = []

        def add_experiment(self, mj, y_fn, start=0, stop=sys.maxint,
                color=None,
                label=None):
            trials = [(job['book_time'], job, y_fn(job))
                    for job in mj if ('book_time' in job
                        and y_fn(job) is not None
                        and np.isfinite(y_fn(job)))]
            trials.sort()
            trials = trials[start:stop]
            if trials:
                self.histories.append((
                    [t[1] for t in trials],
                    [t[2] for t in trials],
                    color, label))
            else:
                print 'NO TRIALS'

        def add_scatters(self):
            for t, y, c, l in self.histories:
                print 'setting label', l
                plt.scatter(
                        np.arange(len(y)),
                        y,
                        c=c,
                        label=l,
                        s=12)

        def main_show(self, title=None):
            self.add_scatters()
            if title:
                plt.title(title)
            #plt.axvline(25) # make a parameter
            #plt.axhline(.2)
            #plt.axhline(.3)
            plt.show()

    def main_plot_histories(cls):
        import plotting
        conn_str_template = sys.argv[2]
        algos = sys.argv[3].split(',')
        dataset_name = sys.argv[4]
        start = int(sys.argv[5]) if len(sys.argv)>5 else 0
        stop = int(sys.argv[6]) if len(sys.argv)>6 else sys.maxint
        mh = plotting.MultiHistory()
        colors = ['r', 'y', 'b', 'g', 'c', 'k']


        def custom_err_fn(trial):
            if 2 == trial['status']:
                rval = 1.0 - trial['result']['best_epoch_valid']
                if rval > dict(
                        convex=.4,
                        mnist_rotated_background_images=2)[dataset_name]:
                    return None
                else:
                    return rval

        for c, algo in zip(colors, algos):
            conn_str = conn_str_template % (algo, dataset_name)
            print 'algo', algo
            mh.add_experiment(
                    mj=MongoJobs.new_from_connection_str(conn_str),
                    y_fn=custom_err_fn,
                    color=c,
                    label=algo,
                    start=start,
                    stop=stop)
        plt = plotting.plt
        plt.axhline(
                1.0 - icml07.dbn3_scores[dataset_name],
                c='k',label='manual+grid')#, dashes=[0,1])
        mh.add_scatters()
        plt.legend()
        plt.title(dataset_name)
        plt.show()

    class ScatterByConf(object):
        trial_color_dict = {0:'k', 1:'g', 2:'b', 3:'r'}
        def __init__(self, conf_template, confs, status, y):
            self.conf_template = conf_template
            self.confs = confs
            self.y = np.asarray(y)
            assert self.y.ndim == 1
            self.status = status

            self.colors = np.asarray(
                [self.trial_color_dict.get(s, None) for s in self.status])

            self.a_choices = np.array([[e['choice']
                for e in t.flatten()]
                for t in confs])
            self.nones = np.array([[None
                for e in t.flatten()]
                for t in confs])
            self.a_names = conf_template.flatten_names()
            self.a_vars = [not np.all(self.a_choices[:,i]==self.nones[:,i])
                    for i,name in enumerate(self.a_names)]

            assert len(self.y) == len(self.a_choices)
            assert len(self.y) == len(self.colors)

        def trial_color(self, t):
            return self.trial_color_dict.get(t['status'], None)

        def scatter_one(self, column):
            assert self.a_vars[column]

            non_missing = self.a_choices[:,column] != self.nones[:,column]
            x = self.a_choices[non_missing, column]
            y = self.y[non_missing]
            c = self.colors[non_missing]
            plt.xlabel(self.a_names[column])
            plt.scatter(x, y, c=c)

        def main_show_one(self, column):
            # show all conf effects in a grid of scatter-plots
            self.scatter_one(column)
            plt.show()
        def main_show_all(self, columns=None):
            if columns == None:
                columns = range(len(self.a_vars))

            columns = [c for c in columns if c < len(self.a_vars)]

            n_vars = np.sum(self.a_vars[c] for c in columns)
            print n_vars
            n_rows = 1
            n_cols = 10000
            n_vars -= 1
            while n_cols > 5 and n_cols > 3 * n_rows: # while "is ugly"
                n_vars += 1  # leave one more space at the end...
                n_rows = int(np.sqrt(n_vars))
                while n_vars % n_rows:
                    n_rows -= 1
                n_cols = n_vars / n_rows
            print n_rows, n_cols

            subplot_idx = 0
            for var_idx in columns:
                if self.a_vars[var_idx]:
                    plt.subplot(n_rows, n_cols, subplot_idx+1)
                    self.scatter_one(var_idx)
                    subplot_idx += 1
            plt.show()

    def main_plot_scatter(self, argv):
        low_col = int(argv[0])
        high_col = int(argv[1])
        # upgrade jobs in db to ht_dist2-compatible things
        scatter_by_conf = ScatterByConf(
                self.bandit.template,
                self.trials,
                status = self.statuses(),
                y = self.losses())
        return scatter_by_conf.main_show_all(range(low_col, high_col))


########NEW FILE########
__FILENAME__ = base
# file is called AST to not collide with std lib module 'ast'
#
# It provides types to build ASTs in a simple lambda-notation style
#

import copy
import logging; logger = logging.getLogger(__name__)
import operator
import time

from StringIO import StringIO
from collections import deque

import networkx as nx

# TODO: move things depending on numpy (among others too) to a library file
import numpy as np
np_versions = map(int, np.__version__.split('.')[:2])


DEFAULT_MAX_PROGRAM_LEN = 100000


class PyllImportError(ImportError):
    """A pyll symbol was not defined in the scope """


class MissingArgument(object):
    """Object to represent a missing argument to a function application
    """


class SymbolTable(object):
    """
    An object whose methods generally allocate Apply nodes.

    _impls is a dictionary containing implementations for those nodes.

    >>> self.add(a, b)          # -- creates a new 'add' Apply node
    >>> self._impl['add'](a, b) # -- this computes a + b
    """

    def __init__(self):
        # -- list and dict are special because they are Python builtins
        self._impls = {
                'list': list,
                'dict': dict,
                'range': range,
                'len': len,
                'int': int,
                'float': float,
                'map': map,
                'max': max,
                'min': min,
                'getattr': getattr,
                }

    def _new_apply(self, name, args, kwargs, o_len, pure):
        pos_args = [as_apply(a) for a in args]
        named_args = [(k, as_apply(v)) for (k, v) in kwargs.items()]
        named_args.sort()
        return Apply(name,
                pos_args=pos_args,
                named_args=named_args,
                o_len=o_len,
                pure=pure)

    # ----

    def dict(self, *args, **kwargs):
        # XXX: figure out len
        return self._new_apply('dict', args, kwargs, o_len=None,
                pure=True)

    def int(self, arg):
        return self._new_apply('int', [as_apply(arg)], {}, o_len=None,
                pure=True)

    def float(self, arg):
        return self._new_apply('float', [as_apply(arg)], {}, o_len=None,
                pure=True)

    def len(self, obj):
        return self._new_apply('len', [obj], {}, o_len=None,
                pure=True)

    def list(self, init):
        return self._new_apply('list', [as_apply(init)], {}, o_len=None,
                pure=True)

    def map(self, fn, seq, pure=False):
        """
        pure - True is assertion that fn does not modify seq[i]
        """
        return self._new_apply('map', [as_apply(fn), as_apply(seq)], {},
                               o_len=seq.o_len,
                               pure=pure
                               )

    def range(self, *args):
        return self._new_apply('range', args, {}, o_len=None, pure=True)

    def max(self, *args):
        """ return max of args """
        return self._new_apply('max', map(as_apply, args), {},
                o_len=None, pure=True)

    def min(self, *args):
        """ return min of args """
        return self._new_apply('min', map(as_apply, args), {},
                o_len=None, pure=True)

    def getattr(self, obj, attr, *args):
        return self._new_apply('getattr',
                [as_apply(obj), as_apply(attr)] + map(as_apply, args),
                {},
                o_len=None,
                pure=True)

    # ----


    def _define(self, f, o_len, pure):
        name = f.__name__
        entry = SymbolTableEntry(self, name, o_len, pure)
        setattr(self, name, entry)
        self._impls[name] = f
        return f

    def define(self, f, o_len=None, pure=False):
        """Decorator for adding python functions to self
        """
        name = f.__name__
        if hasattr(self, name):
            raise ValueError('Cannot override existing symbol', name)
        return self._define(f, o_len, pure)

    def define_if_new(self, f, o_len=None, pure=False):
        """Pass silently if f matches the current implementation
        for f.__name__"""
        name = f.__name__
        if hasattr(self, name) and self._impls[name] is not f:
            raise ValueError('Cannot redefine existing symbol', name)
        return self._define(f, o_len, pure)

    def undefine(self, f):
        if isinstance(f, basestring):
            name = f
        else:
            name = f.__name__
        del self._impls[name]
        delattr(self, name)

    def define_pure(self, f):
        return self.define(f, o_len=None, pure=True)

    def define_info(self, o_len=None, pure=False):
        def wrapper(f):
            return self.define(f, o_len=o_len, pure=pure)
        return wrapper

    def inject(self, *args, **kwargs):
        """
        Add symbols from self into a dictionary and return the dict.

        This is used for import-like syntax: see `import_`.
        """
        rval = {}
        for k in args:
            try:
                rval[k] = getattr(self, k)
            except AttributeError:
                raise PyllImportError(k)
        for k, origk in kwargs.items():
            try:
                rval[k] = getattr(self, origk)
            except AttributeError:
                raise PyllImportError(origk)
        return rval

    def import_(self, _globals, *args, **kwargs):
        _globals.update(self.inject(*args, **kwargs))

class SymbolTableEntry(object):
    """A functools.partial-like class for adding symbol table entries.
    """
    def __init__(self, symbol_table, apply_name, o_len, pure):
        self.symbol_table = symbol_table
        self.apply_name = apply_name
        self.o_len = o_len
        self.pure = pure

    def __call__(self, *args, **kwargs):
        return self.symbol_table._new_apply(
                self.apply_name,
                args,
                kwargs,
                self.o_len,
                self.pure)

scope = SymbolTable()


def as_apply(obj):
    """Smart way of turning object into an Apply
    """
    if isinstance(obj, Apply):
        rval = obj
    elif isinstance(obj, tuple):
        rval = Apply('pos_args', [as_apply(a) for a in obj], {}, len(obj))
    elif isinstance(obj, list):
        rval = Apply('pos_args', [as_apply(a) for a in obj], {}, None)
    elif isinstance(obj, dict):
        items = obj.items()
        # -- should be fine to allow numbers and simple things
        #    but think about if it's ok to allow Applys
        #    it messes up sorting at the very least.
        items.sort()
        if all(isinstance(k, basestring) for k in obj):
            named_args = [(k, as_apply(v)) for (k, v) in items]
            rval = Apply('dict', [], named_args, len(named_args))
        else:
            new_items = [(k, as_apply(v)) for (k, v) in items]
            rval = Apply('dict', [as_apply(new_items)], {}, o_len=None)
    else:
        rval = Literal(obj)
    assert isinstance(rval, Apply)
    return rval


class Apply(object):
    """
    Represent a symbolic application of a symbol to arguments.

    o_len - None or int if the function is guaranteed to return a fixed number
        `o_len` of outputs if it returns successfully
    pure - True only if the function has no relevant side-effects
    """

    def __init__(self, name, pos_args, named_args,
            o_len=None,
            pure=False,
            define_params=None):
        self.name = name
        # -- tuples or arrays -> lists
        self.pos_args = list(pos_args)
        self.named_args = [[kw, arg] for (kw, arg) in named_args]
        # -- o_len is attached this early to support tuple unpacking and
        #    list coersion.
        self.o_len = o_len
        self.pure = pure
        # -- define_params lets us cope with stuff that may be in the
        #    SymbolTable on the master but not on the worker.
        self.define_params = define_params
        assert all(isinstance(v, Apply) for v in pos_args)
        assert all(isinstance(v, Apply) for k, v in named_args)
        assert all(isinstance(k, basestring) for k, v in named_args)

    def __setstate__(self, state):
        self.__dict__.update(state)
        # -- On deserialization, update scope if need be.
        if self.define_params:
            scope.define_if_new(**self.define_params)

    def eval(self, memo=None):
        """
        Recursively evaluate an expression graph.

        This method operates directly on the graph of extended inputs to this
        node, making no attempt to modify or optimize the expression graph.

        Caveats:

          * If there are nodes in the graph that do not represent expressions,
            (e.g. nodes that correspond to statement blocks or assertions)
            then it's not clear what this routine should do, and you should
            probably not call it.

          * If there are Lambdas in the graph, this procedure will not evluate
            them -- see rec_eval for that.

        However, for many cases that are pure expression graphs, this
        offers a quick and simple way to evaluate them.
        """
        if memo is None:
            memo = {}
        if id(self) in memo:
            return memo[id(self)]
        else:
            args = [a.eval() for a in self.pos_args]
            kwargs = dict([(n, a.eval()) for (n, a) in self.named_args])
            f = scope._impls[self.name]
            memo[id(self)] = rval = f(*args, **kwargs)
            return rval

    def inputs(self):
        # -- this function gets called a lot and it's not 100% safe to cache
        #    so the if/else is a small optimization
        if self.named_args:
            rval = self.pos_args + [v for (k, v) in self.named_args]
        else:
            rval = self.pos_args
        #assert all(isinstance(arg, Apply) for arg in rval)
        return rval

    @property
    def arg(self):
        # XXX: move this introspection to __init__, and change
        #      the basic data-structure to not use pos_args and named_args.
        # XXX: think though... we want the binding to be updated if pos_args
        # and named_args is modified... so maybe this is an ok way to do it?
        #
        # XXX: extend something to deal with Lambda objects instead of
        # decorated python functions.
        #
        # http://docs.python.org/reference/expressions.html#calls
        #
        binding = {}

        fn = scope._impls[self.name]
        # XXX does not work for builtin functions
        defaults = fn.__defaults__  # right-aligned default values for params
        code = fn.__code__

        extra_args_ok = bool(code.co_flags & 0x04)
        extra_kwargs_ok = bool(code.co_flags & 0x08)

        # -- assert that my understanding of calling protocol is correct
        try:
            if extra_args_ok and extra_kwargs_ok:
                assert len(code.co_varnames) >= code.co_argcount + 2
                param_names = code.co_varnames[:code.co_argcount + 2]
                args_param = param_names[code.co_argcount]
                kwargs_param = param_names[code.co_argcount + 1]
                pos_params = param_names[:code.co_argcount]
            elif extra_kwargs_ok:
                assert len(code.co_varnames) >= code.co_argcount + 1
                param_names = code.co_varnames[:code.co_argcount + 1]
                kwargs_param = param_names[code.co_argcount]
                pos_params = param_names[:code.co_argcount]
            elif extra_args_ok:
                assert len(code.co_varnames) >= code.co_argcount + 1
                param_names = code.co_varnames[:code.co_argcount + 1]
                args_param = param_names[code.co_argcount]
                pos_params = param_names[:code.co_argcount]
            else:
                assert len(code.co_varnames) >= code.co_argcount
                param_names = code.co_varnames[:code.co_argcount]
                pos_params = param_names[:code.co_argcount]
        except AssertionError:
            print 'YIKES: MISUNDERSTANDING OF CALL PROTOCOL:',
            print code.co_argcount,
            print code.co_varnames,
            print '%x' % code.co_flags
            raise

        if extra_args_ok:
            binding[args_param] == []

        if extra_kwargs_ok:
            binding[kwargs_param] == {}

        if len(self.pos_args) > code.co_argcount and not extra_args_ok:
            raise TypeError('Argument count exceeds number of positional params')

        # -- bind positional arguments
        for param_i, arg_i in zip(param_names, self.pos_args):
            binding[param_i] = arg_i

        if extra_args_ok:
            # XXX: THIS IS NOT BEING TESTED AND IS OBVIOUSLY BROKEN
            binding[args_param].extend(args[code.co_argcount:])

        # -- bind keyword arguments
        for aname, aval in self.named_args:
            try:
                pos = pos_params.index(aname)
            except ValueError:
                if extra_kwargs_ok:
                    binding[kwargs_param][aname] = aval
                    continue
                else:
                    raise TypeError('Unrecognized keyword argument', aname)
            param = param_names[pos]
            if param in binding:
                raise TypeError('Duplicate argument for parameter', param)
            binding[param] = aval

        assert len(binding) <= len(param_names)

        if len(binding) < len(param_names):
            for p in param_names:
                if p not in binding:
                    binding[p] = MissingArgument

        return binding

    def set_kwarg(self, name, value):
        for ii, (key, val) in enumerate(self.named_args):
            if key == name:
                self.named_args[ii][1] = as_apply(value)
                return
        arg = self.arg
        if name in arg and arg[name] != MissingArgument:
            raise NotImplementedError('change pos arg to kw arg')
        else:
            self.named_args.append([name, as_apply(value)])
            self.named_args.sort()

    def clone_from_inputs(self, inputs, o_len='same'):
        if len(inputs) != len(self.inputs()):
            raise TypeError()
        L = len(self.pos_args)
        pos_args = list(inputs[:L])
        named_args = [[kw, inputs[L + ii]]
                for ii, (kw, arg) in enumerate(self.named_args)]
        # -- danger cloning with new inputs can change the o_len
        if o_len == 'same':
            o_len = self.o_len
        return self.__class__(self.name, pos_args, named_args, o_len)

    def replace_input(self, old_node, new_node):
        rval = []
        for ii, aa in enumerate(self.pos_args):
            if aa is old_node:
                self.pos_args[ii] = new_node
                rval.append(ii)
        for ii, (nn, aa) in enumerate(self.named_args):
            if aa is old_node:
                self.named_args[ii][1] = new_node
                rval.append(ii + len(self.pos_args))
        return rval

    def pprint(self, ofile, lineno=None, indent=0, memo=None):
        if memo is None:
            memo = {}
        if lineno is None:
            lineno = [0]

        if self in memo:
            print >> ofile, lineno[0], ' ' * indent + memo[self]
            lineno[0] += 1
        else:
            memo[self] = self.name + ('  [line:%i]' % lineno[0])
            print >> ofile, lineno[0], ' ' * indent + self.name
            lineno[0] += 1
            for arg in self.pos_args:
                arg.pprint(ofile, lineno, indent + 2, memo)
            for name, arg in self.named_args:
                print >> ofile, lineno[0], ' ' * indent + ' ' + name + ' ='
                lineno[0] += 1
                arg.pprint(ofile, lineno, indent + 2, memo)

    def __str__(self):
        sio = StringIO()
        self.pprint(sio)
        return sio.getvalue()[:-1]  # remove trailing '\n'

    def __add__(self, other):
        return scope.add(self, other)

    def __radd__(self, other):
        return scope.add(other, self)

    def __sub__(self, other):
        return scope.sub(self, other)

    def __rsub__(self, other):
        return scope.sub(other, self)

    def __neg__(self):
        return scope.neg(self)

    def __mul__(self, other):
        return scope.mul(self, other)

    def __rmul__(self, other):
        return scope.mul(other, self)

    def __div__(self, other):
        return scope.div(self, other)

    def __rdiv__(self, other):
        return scope.div(other, self)

    def __floordiv__(self, other):
        return scope.floordiv(self, other)

    def __rfloordiv__(self, other):
        return scope.floordiv(other, self)

    def __pow__(self, other):
        return scope.pow(self, other)

    def __rpow__(self, other):
        return scope.pow(other, self)

    def __gt__(self, other):
        return scope.gt(self, other)

    def __ge__(self, other):
        return scope.ge(self, other)

    def __lt__(self, other):
        return scope.lt(self, other)

    def __le__(self, other):
        return scope.le(self, other)

    def __getitem__(self, idx):
        if self.o_len is not None and isinstance(idx, int):
            if idx >= self.o_len:
                #  -- this IndexError is essential for supporting
                #     tuple-unpacking syntax or list coersion of self.
                raise IndexError()
        return scope.getitem(self, idx)

    def __len__(self):
        if self.o_len is None:
            raise TypeError('len of pyll.Apply either undefined or unknown')
        return self.o_len

    def __call__(self, *args, **kwargs):
        return scope.call(self, args, kwargs)


def apply(name, *args, **kwargs):
    pos_args = [as_apply(a) for a in args]
    named_args = [(k, as_apply(v)) for (k, v) in kwargs.items()]
    named_args.sort()
    return Apply(name,
            pos_args=pos_args,
            named_args=named_args,
            o_len=None)


class Literal(Apply):
    def __init__(self, obj=None):
        try:
            o_len = len(obj)
        except TypeError:
            o_len = None
        Apply.__init__(self, 'literal', [], {}, o_len, pure=True)
        self._obj = obj

    def eval(self, memo=None):
        if memo is None:
            memo = {}
        return memo.setdefault(id(self), self._obj)

    @property
    def obj(self):
        return self._obj

    @property
    def arg(self):
        return {}

    def pprint(self, ofile, lineno=None, indent=0, memo=None):
        if lineno is None:
            lineno = [0]
        if memo is None:
            memo = {}
        if self in memo:
            print >> ofile, lineno[0], ' ' * indent + memo[self]
        else:
            # TODO: set up a registry for this
            if isinstance(self._obj, np.ndarray):
                msg = 'Literal{np.ndarray,shape=%s,min=%f,max=%f}' % (
                        self._obj.shape, self._obj.min(), self._obj.max())
            else:
                msg = 'Literal{%s}' % str(self._obj)
            memo[self] = '%s  [line:%i]' % (msg, lineno[0])
            print >> ofile, lineno[0], ' ' * indent + msg
        lineno[0] += 1

    def replace_input(self, old_node, new_node):
        return []

    def clone_from_inputs(self, inputs, o_len='same'):
        return self.__class__(self._obj)


class Lambda(object):

    # XXX: Extend Lambda objects to have a list of exception clauses.
    #      If the code of the expr() throws an error, these clauses convert
    #      that error to a return value.

    def __init__(self, name, params, expr):
        self.__name__ = name  # like a python function
        self.params = params  # list of (name, symbol[, default_value]) tuples
        self.expr = expr      # pyll graph defining this Lambda

    def __call__(self, *args, **kwargs):
        # -- return `expr` cloned from given args and kwargs
        if len(args) > len(self.params):
            raise TypeError('too many arguments')
        memo = {}
        for arg, param in zip(args, self.params):
            #print 'applying with arg', param, arg
            memo[param[1]] = as_apply(arg)
        if len(args) != len(self.params) or kwargs:
            raise NotImplementedError('named / default arguments',
                    (args, self.params))
        rval = clone(self.expr, memo)
        #print 'BEFORE'
        #print self.expr
        #print 'AFTER'
        #print rval
        return rval


class UndefinedValue(object):
    pass


# -- set up some convenience symbols to use as parameters in Lambda definitions
p0 = Literal(UndefinedValue)
p1 = Literal(UndefinedValue)
p2 = Literal(UndefinedValue)
p3 = Literal(UndefinedValue)
p4 = Literal(UndefinedValue)


@scope.define
def call(fn, args=(), kwargs={}):
    """ call fn with given args and kwargs.

    This is used to represent Apply.__call__
    """
    return fn(*args, **kwargs)


@scope.define
def callpipe1(fn_list, arg):
    """

    fn_list: a list lambdas  that return either pyll expressions or python
        values

    arg: the argument to the first function in the list

    return: `fn_list[-1]( ... (fn_list[1](fn_list[0](arg))))`

    """
    # XXX: in current implementation, if fs are `partial`, then
    #      this loop will expand all functions f at once, so that they
    #      will all be evaluated in the same scope/memo by rec_eval.
    #      Normally programming languages would evaluate each f in a private
    #      scope
    for f in fn_list:
        arg = f(arg)
    return arg


@scope.define
def partial(name, *args, **kwargs):
    # TODO: introspect the named instruction, to retrieve the
    #       list of parameters *not* accounted for by args and kwargs
    # then delete these stupid functions and just have one `partial`
    try:
        name = name.apply_name  # to retrieve name from scope.foo methods
    except AttributeError:
        pass

    my_id = len(scope._impls)
    # -- create a function with this name
    #    the name is the string used index into scope._impls
    temp_name = 'partial_%s_id%i' % (name, my_id)
    l = Lambda(temp_name, [('x', p0)],
            expr=apply(name, *(args + (p0,)), **kwargs))
    scope.define(l)
    # assert that the next partial will get a different id
    # XXX; THIS ASSUMES THAT SCOPE ONLY GROWS
    assert my_id < len(scope._impls)
    rval = getattr(scope, temp_name)
    return rval


def dfs(aa, seq=None, seqset=None):
    if seq is None:
        assert seqset is None
        seq = []
        seqset = {}
    # -- seqset is the set of all nodes we have seen (which may be still on
    #    the stack)
    #    N.B. it used to be a stack, but now it's a dict mapping to inputs
    #    because that's an optimization saving us from having to call inputs
    #    so often.
    if aa in seqset:
        return
    assert isinstance(aa, Apply)
    seqset[aa] = aa.inputs()
    for ii in seqset[aa]:
        dfs(ii, seq, seqset)
    seq.append(aa)
    return seq


def toposort(expr):
    """
    Return apply nodes of `expr` sub-tree in topological order.

    Raises networkx.NetworkXUnfeasible if subtree contains cycle.

    """
    G = nx.DiGraph()
    for node in dfs(expr):
        G.add_edges_from([(n_in, node) for n_in in node.inputs()])
    order = nx.topological_sort(G)
    assert order[-1] == expr
    return order


def clone(expr, memo=None):
    if memo is None:
        memo = {}
    nodes = dfs(expr)
    for node in nodes:
        if node not in memo:
            new_inputs = [memo[arg] for arg in node.inputs()]
            new_node = node.clone_from_inputs(new_inputs)
            memo[node] = new_node
    return memo[expr]


def clone_merge(expr, memo=None, merge_literals=False):
    nodes = dfs(expr)
    if memo is None:
        memo = {}
    # -- args are somewhat slow to construct, so cache them out front
    #    XXX node.arg does not always work (builtins, weird co_flags)
    node_args = [(node.pos_args, node.named_args) for node in nodes]
    del node
    for ii, node_ii in enumerate(nodes):
        if node_ii in memo:
            continue
        new_ii = None
        if node_ii.pure:
            for jj in range(ii):
                node_jj = nodes[jj]
                if node_ii.name != node_jj.name:
                    continue
                if node_ii.name == 'literal':
                    if not merge_literals:
                        continue
                    if node_ii._obj != node_jj._obj:
                        continue
                else:
                    if node_args[ii] != node_args[jj]:
                        continue
                logger.debug('clone_merge %s %i <- %i' % (
                    node_ii.name, jj, ii))
                new_ii = node_jj
                break
        if new_ii is None:
            new_inputs = [memo[arg] for arg in node_ii.inputs()]
            new_ii = node_ii.clone_from_inputs(new_inputs)
        memo[node_ii] = new_ii

    return memo[expr]


##############################################################################
##############################################################################


class GarbageCollected(object):
    '''Placeholder representing a garbage-collected value '''


def rec_eval(expr, deepcopy_inputs=False, memo=None,
        max_program_len=None,
        memo_gc=True,
        print_trace=False,
        print_node_on_error=True,
        ):
    """
    expr - pyll Apply instance to be evaluated

    memo - optional dictionary of values to use for particular nodes

    deepcopy_inputs - deepcopy inputs to every node prior to calling that
        node's function on those inputs. If this leads to a different return
        value, then some function (XXX add more complete DebugMode
        functionality) in your graph is modifying its inputs and causing
        mis-calculation. XXX: This is not a fully-functional DebugMode because
        if the offender happens on account of the toposort order to be the last
        user of said input, then it will not be detected as a potential
        problem.

    """
    if max_program_len == None:
        max_program_len = DEFAULT_MAX_PROGRAM_LEN

    if deepcopy_inputs not in (0, 1, False, True):
        # -- I've been calling rec_eval(expr, memo) by accident a few times
        #    this error would have been appreciated.
        raise ValueError('deepcopy_inputs should be bool', deepcopy_inputs)

    node = as_apply(expr)
    topnode = node

    if memo is None:
        memo = {}
    else:
        memo = dict(memo)

    # -- hack for speed
    #    since the inputs are constant during rec_eval
    #    but not constant in general
    node_inputs = {}
    node_list = []
    dfs(node, node_list, seqset=node_inputs)

    # TODO: optimize dfs to not recurse past the items in memo
    #       this is especially important for evaluating Lambdas
    #       which cause rec_eval to recurse
    #
    # N.B. that Lambdas may expand the graph during the evaluation
    #      so that this iteration may be an incomplete
    if memo_gc:
        clients = {}
        for aa in node_list:
            clients.setdefault(aa, set())
            for ii in node_inputs[aa]:
                clients.setdefault(ii, set()).add(aa)
        def set_memo(k, v):
            assert v is not GarbageCollected
            memo[k] = v
            for ii in node_inputs[k]:
                # -- if all clients of ii are already in the memo
                #    then we can free memo[ii] by replacing it
                #    with a dummy symbol
                if all(iic in memo for iic in clients[ii]):
                    #print 'collecting', ii
                    memo[ii] = GarbageCollected
    else:
        def set_memo(k, v):
            memo[k] = v

    todo = deque([topnode])
    while todo:
        if len(todo) > max_program_len:
            raise RuntimeError('Probably infinite loop in document')
        node = todo.pop()
        if print_trace:
            print 'rec_eval:print_trace', len(todo), node.name

        if node in memo:
            # -- we've already computed this, move on.
            continue

        # -- different kinds of nodes are treated differently:
        if node.name == 'switch':
            # -- switch is the conditional evaluation node
            switch_i_var = node.pos_args[0]
            if switch_i_var in memo:
                switch_i = memo[switch_i_var]
                try:
                    int(switch_i)
                except:
                    raise TypeError('switch argument was', switch_i)
                if switch_i != int(switch_i) or switch_i < 0:
                    raise ValueError('switch pos must be positive int',
                            switch_i)
                rval_var = node.pos_args[switch_i + 1]
                if rval_var in memo:
                    set_memo(node, memo[rval_var])
                    continue
                else:
                    waiting_on = [rval_var]
            else:
                waiting_on = [switch_i_var]
        elif isinstance(node, Literal):
            # -- constants go straight into the memo
            set_memo(node, node.obj)
            continue
        else:
            # -- normal instruction-type nodes have inputs
            waiting_on = [v for v in node_inputs[node] if v not in memo]

        if waiting_on:
            # -- Necessary inputs have yet to be evaluated.
            #    push the node back in the queue, along with the
            #    inputs it still needs
            todo.append(node)
            todo.extend(waiting_on)
        else:
            # -- not waiting on anything;
            #    this instruction can be evaluated.
            args = _args = [memo[v] for v in node.pos_args]
            kwargs = _kwargs = dict([(k, memo[v])
                for (k, v) in node.named_args])

            if memo_gc:
                for aa in args + kwargs.values():
                    assert aa is not GarbageCollected

            if deepcopy_inputs:
                args = copy.deepcopy(_args)
                kwargs = copy.deepcopy(_kwargs)

            try:
                rval = scope._impls[node.name](*args, **kwargs)

            except Exception, e:
                if print_node_on_error:
                    print '=' * 80
                    print 'ERROR in rec_eval'
                    print 'EXCEPTION', type(e), str(e)
                    print 'NODE'
                    print node  # -- typically a multi-line string
                    print '=' * 80
                raise

            if isinstance(rval, Apply):
                # -- if an instruction returns a Pyll apply node
                # it means evaluate that too. Lambdas do this.
                #
                # XXX: consider if it is desirable, efficient, buggy
                #      etc. to keep using the same memo dictionary
                foo = rec_eval(rval, deepcopy_inputs, memo,
                        memo_gc=memo_gc)
                set_memo(node, foo)
            else:
                set_memo(node, rval)

    return memo[topnode]


############################################################################
############################################################################

@scope.define_pure
def pos_args(*args):
    return args



@scope.define_pure
def identity(obj):
    return obj


# -- We used to define these as Python functions in this file, but the operator
#    module already provides them, is slightly more efficient about it. Since
#    searchspaces uses the same convention, we can more easily map graphs back
#    and forth and reduce the amount of code in both codebases.
scope.define_pure(operator.getitem)
scope.define_pure(operator.add)
scope.define_pure(operator.sub)
scope.define_pure(operator.mul)
scope.define_pure(operator.div)
scope.define_pure(operator.floordiv)
scope.define_pure(operator.neg)
scope.define_pure(operator.eq)
scope.define_pure(operator.lt)
scope.define_pure(operator.le)
scope.define_pure(operator.gt)
scope.define_pure(operator.ge)


@scope.define_pure
def exp(a):
    return np.exp(a)


@scope.define_pure
def log(a):
    return np.log(a)


@scope.define_pure
def pow(a, b):
    return a ** b


@scope.define_pure
def sin(a):
    return np.sin(a)


@scope.define_pure
def cos(a):
    return np.cos(a)


@scope.define_pure
def tan(a):
    return np.tan(a)


@scope.define_pure
def sum(x, axis=None):
    if axis is None:
        return np.sum(x)
    else:
        return np.sum(x, axis=axis)


@scope.define_pure
def sqrt(x):
    return np.sqrt(x)


@scope.define_pure
def minimum(x, y):
    return np.minimum(x, y)


@scope.define_pure
def maximum(x, y):
    return np.maximum(x, y)


@scope.define_pure
def array_union1(args):
    s = set()
    for a in args:
        s.update(a)
    return np.asarray(sorted(s))


@scope.define_pure
def array_union(*args):
    return array_union1(args)


@scope.define_pure
def asarray(a, dtype=None):
    if dtype is None:
        return np.asarray(a)
    else:
        return np.asarray(a, dtype=dtype)


@scope.define_pure
def str_join(s, seq):
    return s.join(seq)


def _bincount_slow(x, weights=None, minlength=None):
    """backport of np.bincount post numpy 1.6
    """
    if weights is not None:
        raise NotImplementedError()
    if minlength is None:
        rlen = np.max(x) + 1
    else:
        rlen = max(np.max(x) + 1, minlength)
    rval = np.zeros(rlen, dtype='int')
    for xi in np.asarray(x).flatten():
        rval[xi] += 1
    return rval


@scope.define_pure
def bincount(x, weights=None, minlength=None):
    if np_versions[0] == 1 and np_versions[1] < 6:
        # -- np.bincount doesn't have minlength arg
        return _bincount_slow(x, weights, minlength)
    else:
        if np.asarray(x).size:
            return np.bincount(x, weights, minlength)
        else:
            # -- currently numpy rejects this case,
            #    but it seems sensible enough to me.
            return np.zeros(minlength, dtype='int')


@scope.define_pure
def repeat(n_times, obj):
    return [obj] * n_times


@scope.define
def call_method(obj, methodname, *args, **kwargs):
    method = getattr(obj, methodname)
    return method(*args, **kwargs)


@scope.define_pure
def call_method_pure(obj, methodname, *args, **kwargs):
    method = getattr(obj, methodname)
    return method(*args, **kwargs)


@scope.define_pure
def copy_call_method_pure(obj, methodname, *args, **kwargs):
    # -- this method copies object before calling the method
    #    so that in the case where args and kwargs are not modified
    #    the call_method can be done in a no-side-effect way.
    #
    #    It is a mistake to use this method when args or kwargs are modified
    #    by the call to method.
    method = getattr(copy.copy(obj), methodname)
    return method(*args, **kwargs)


@scope.define_pure
def switch(pos, *args):
    # switch is an unusual expression, in that it affects control flow
    # when executed with rec_eval. args are not all evaluated, only
    # args[pos] is evaluated.
    ##raise RuntimeError('switch is not meant to be evaluated')
    #
    # .. However, in quick-evaluation schemes it is handy that this be defined
    # as follows:
    return args[pos]


def _kwswitch(kw, **kwargs):
    """conditional evaluation according to string value"""
    # Get the index of the string in kwargs to use switch
    keys, values = zip(*sorted(kwargs.iteritems()))
    match_idx = scope.call_method_pure(keys, 'index', kw)
    return scope.switch(match_idx, *values)

scope.kwswitch = _kwswitch


@scope.define_pure
def Raise(etype, *args, **kwargs):
    raise etype(*args, **kwargs)


@scope.define_info(o_len=2)
def curtime(obj):
    return time.time(), obj


@scope.define
def pdb_settrace(obj):
    import pdb; pdb.set_trace()
    return obj


########NEW FILE########
__FILENAME__ = stochastic
"""
Constructs for annotating base graphs.
"""
import sys
import numpy as np

from .base import scope, as_apply, dfs, Apply, rec_eval, clone

################################################################################
################################################################################
def ERR(msg):
    print >> sys.stderr, msg


implicit_stochastic_symbols = set()


def implicit_stochastic(f):
    implicit_stochastic_symbols.add(f.__name__)
    return f


@scope.define
def rng_from_seed(seed):
    return np.random.RandomState(seed)


# -- UNIFORM

@implicit_stochastic
@scope.define
def uniform(low, high, rng=None, size=()):
    return rng.uniform(low, high, size=size)


@implicit_stochastic
@scope.define
def loguniform(low, high, rng=None, size=()):
    draw = rng.uniform(low, high, size=size)
    return np.exp(draw)


@implicit_stochastic
@scope.define
def quniform(low, high, q, rng=None, size=()):
    draw = rng.uniform(low, high, size=size)
    return np.round(draw/q) * q


@implicit_stochastic
@scope.define
def qloguniform(low, high, q, rng=None, size=()):
    draw = np.exp(rng.uniform(low, high, size=size))
    return np.round(draw/q) * q


# -- NORMAL

@implicit_stochastic
@scope.define
def normal(mu, sigma, rng=None, size=()):
    return rng.normal(mu, sigma, size=size)


@implicit_stochastic
@scope.define
def qnormal(mu, sigma, q, rng=None, size=()):
    draw = rng.normal(mu, sigma, size=size)
    return np.round(draw/q) * q


@implicit_stochastic
@scope.define
def lognormal(mu, sigma, rng=None, size=()):
    draw = rng.normal(mu, sigma, size=size)
    return np.exp(draw)


@implicit_stochastic
@scope.define
def qlognormal(mu, sigma, q, rng=None, size=()):
    draw = np.exp(rng.normal(mu, sigma, size=size))
    return np.round(draw/q) * q


# -- CATEGORICAL


@implicit_stochastic
@scope.define
def randint(upper, rng=None, size=()):
    # this is tricky because numpy doesn't support
    # upper being a list of len size[0]
    if isinstance(upper, (list, tuple)):
        if isinstance(size, int):
            assert len(upper) == size
            return np.asarray([rng.randint(uu) for uu in upper])
        elif len(size) == 1:
            assert len(upper) == size[0]
            return np.asarray([rng.randint(uu) for uu in upper])
    return rng.randint(upper, size=size)


@implicit_stochastic
@scope.define
def categorical(p, upper=None, rng=None, size=()):
    """Draws i with probability p[i]"""
    if len(p) == 1 and isinstance(p[0], np.ndarray):
        p = p[0]
    p = np.asarray(p)

    if size == ():
        size = (1,)
    elif isinstance(size, (int, np.number)):
        size = (size,)
    else:
        size = tuple(size)

    if size == (0,):
        return np.asarray([])
    assert len(size)

    if p.ndim == 0:
        raise NotImplementedError()
    elif p.ndim == 1:
        n_draws = int(np.prod(size))
        sample = rng.multinomial(n=1, pvals=p, size=int(n_draws))
        assert sample.shape == size + (len(p),)
        rval = np.dot(sample, np.arange(len(p)))
        rval.shape = size
        return rval
    elif p.ndim == 2:
        n_draws_, n_choices = p.shape
        n_draws, = size
        assert n_draws == n_draws_
        rval = [np.where(rng.multinomial(pvals=p[ii], n=1))[0][0]
                                for ii in xrange(n_draws)]
        rval = np.asarray(rval)
        rval.shape = size
        return rval
    else:
        raise NotImplementedError()


def choice(args):
    return scope.one_of(*args)
scope.choice = choice


def one_of(*args):
    ii = scope.randint(len(args))
    return scope.switch(ii, *args)
scope.one_of = one_of


def recursive_set_rng_kwarg(expr, rng=None):
    """
    Make all of the stochastic nodes in expr use the rng

    uniform(0, 1) -> uniform(0, 1, rng=rng)
    """
    if rng is None:
        rng = np.random.RandomState()
    lrng = as_apply(rng)
    for node in dfs(expr):
        if node.name in implicit_stochastic_symbols:
            for ii, (name, arg) in enumerate(list(node.named_args)):
                if name == 'rng':
                    node.named_args[ii] = ('rng', lrng)
                    break
            else:
                node.named_args.append(('rng', lrng))
    return expr


def sample(expr, rng=None, **kwargs):
    """
    Parameters:
    expr - a pyll expression to be evaluated

    rng - a np.random.RandomState instance
          default: `np.random.RandomState()`
          
    **kwargs - optional arguments passed along to
               `hyperopt.pyll.rec_eval`

    """
    if rng is None:
        rng = np.random.RandomState()
    foo = recursive_set_rng_kwarg(clone(as_apply(expr)), as_apply(rng))
    return rec_eval(foo, **kwargs)

########NEW FILE########
__FILENAME__ = test_base
from hyperopt.pyll.base import *

from nose import SkipTest
from nose.tools import assert_raises
import numpy as np

from hyperopt.pyll import base

def test_literal_pprint():
    l = Literal(5)
    print str(l)
    assert str(l) == '0 Literal{5}'


def test_literal_apply():
    l0 = Literal([1, 2, 3])
    print str(l0)
    assert str(l0) == '0 Literal{[1, 2, 3]}'


def test_literal_unpacking():
    l0 = Literal([1, 2, 3])
    a, b, c = l0
    print a
    assert c.name == 'getitem'
    assert c.pos_args[0] is l0
    assert isinstance(c.pos_args[1], Literal)
    assert c.pos_args[1]._obj == 2


def test_as_apply_passthrough():
    a4 = as_apply(4)
    assert a4 is as_apply(a4)


def test_as_apply_literal():
    assert isinstance(as_apply(7), Literal)


def test_as_apply_list_of_literals():
    l = [9, 3]
    al = as_apply(l)
    assert isinstance(al, Apply)
    assert al.name == 'pos_args'
    assert isinstance(al.pos_args[0], Literal)
    assert isinstance(al.pos_args[1], Literal)
    al.pos_args[0]._obj == 9
    al.pos_args[1]._obj == 3


def test_as_apply_tuple_of_literals():
    l = (9, 3)
    al = as_apply(l)
    assert isinstance(al, Apply)
    assert al.name == 'pos_args'
    assert isinstance(al.pos_args[0], Literal)
    assert isinstance(al.pos_args[1], Literal)
    al.pos_args[0]._obj == 9
    al.pos_args[1]._obj == 3
    assert len(al) == 2


def test_as_apply_list_of_applies():
    alist = [as_apply(i) for i in range(5)]

    al = as_apply(alist)
    assert isinstance(al, Apply)
    assert al.name == 'pos_args'
    # -- have to come back to this if Literal copies args
    assert al.pos_args == alist


def test_as_apply_dict_of_literals():
    d = {'a': 9, 'b': 10}
    ad = as_apply(d)
    assert isinstance(ad, Apply)
    assert ad.name == 'dict'
    assert len(ad) == 2
    assert ad.named_args[0][0] == 'a'
    assert ad.named_args[0][1]._obj == 9
    assert ad.named_args[1][0] == 'b'
    assert ad.named_args[1][1]._obj == 10


def test_as_apply_dict_of_applies():
    d = {'a': as_apply(9), 'b': as_apply(10)}
    ad = as_apply(d)
    assert isinstance(ad, Apply)
    assert ad.name == 'dict'
    assert len(ad) == 2
    assert ad.named_args[0][0] == 'a'
    assert ad.named_args[0][1]._obj == 9
    assert ad.named_args[1][0] == 'b'
    assert ad.named_args[1][1]._obj == 10


def test_as_apply_nested_dict():
    d = {'a': 9, 'b': {'c':11, 'd':12}}
    ad = as_apply(d)
    assert isinstance(ad, Apply)
    assert ad.name == 'dict'
    assert len(ad) == 2
    assert ad.named_args[0][0] == 'a'
    assert ad.named_args[0][1]._obj == 9
    assert ad.named_args[1][0] == 'b'
    assert ad.named_args[1][1].name == 'dict'
    assert ad.named_args[1][1].named_args[0][0] == 'c'
    assert ad.named_args[1][1].named_args[0][1]._obj == 11
    assert ad.named_args[1][1].named_args[1][0] == 'd'
    assert ad.named_args[1][1].named_args[1][1]._obj == 12


def test_dfs():
    dd = as_apply({'c':11, 'd':12})

    d = {'a': 9, 'b': dd, 'y': dd, 'z': dd + 1}
    ad = as_apply(d)
    order = dfs(ad)
    print [str(o) for o in order]
    assert order[0]._obj == 9
    assert order[1]._obj == 11
    assert order[2]._obj == 12
    assert order[3].named_args[0][0] == 'c'
    assert order[4]._obj == 1
    assert order[5].name == 'add'
    assert order[6].named_args[0][0] == 'a'
    assert len(order) == 7


@scope.define_info(o_len=2)
def _test_foo():
    return 1, 2

def test_o_len():
    obj = scope._test_foo()
    x, y = obj
    assert x.name == 'getitem'
    assert x.pos_args[1]._obj == 0
    assert y.pos_args[1]._obj == 1


def test_eval_arithmetic():
    a, b, c = as_apply((2, 3, 4))

    assert (a + b).eval() == 5
    assert (a + b + c).eval() == 9
    assert (a + b + 1 + c).eval() == 10

    assert (a * b).eval() == 6
    assert (a * b * c * (-1)).eval() == -24

    assert (a - b).eval() == -1
    assert (a - b * c).eval() == -10

    assert (a / b).eval() == 0   # int div
    assert (b / a).eval() == 1   # int div
    assert (c / a ).eval() == 2
    assert (4 / a).eval() == 2
    assert (a / 4.0).eval() == 0.5


def test_bincount():
    def test_f(f):
        r = np.arange(10)
        counts = f(r)
        assert isinstance(counts, np.ndarray)
        assert len(counts) == 10
        assert np.all(counts == 1)

        r = np.arange(10) + 3
        counts = f(r)
        assert isinstance(counts, np.ndarray)
        assert len(counts) == 13
        assert np.all(counts[3:] == 1)
        assert np.all(counts[:3] == 0)

        r = np.arange(10) + 3
        counts = f(r, minlength=5) # -- ignore minlength
        assert isinstance(counts, np.ndarray)
        assert len(counts) == 13
        assert np.all(counts[3:] == 1)
        assert np.all(counts[:3] == 0)

        r = np.arange(10) + 3
        counts = f(r, minlength=15) # -- pad to minlength
        assert isinstance(counts, np.ndarray)
        assert len(counts) == 15
        assert np.all(counts[:3] == 0)
        assert np.all(counts[3:13] == 1)
        assert np.all(counts[13:] == 0)

        r = np.arange(10) % 3 + 3
        counts = f(r, minlength=7) # -- pad to minlength
        assert list(counts) == [0, 0, 0, 4, 3, 3, 0]

    try:
        test_f(base._bincount_slow)
        test_f(base.bincount)
    except TypeError, e:
        if 'function takes at most 2 arguments' in str(e):
            raise SkipTest()
        raise

def test_switch_and_Raise():
    i = Literal()
    ab = scope.switch(i, 'a', 'b', scope.Raise(Exception))
    assert rec_eval(ab, memo={i: 0}) == 'a'
    assert rec_eval(ab, memo={i: 1}) == 'b'
    assert_raises(Exception, rec_eval, ab, memo={i:2})


def test_kwswitch():
    i = Literal()
    ab = scope.kwswitch(i, k1='a', k2='b', err=scope.Raise(Exception))
    assert rec_eval(ab, memo={i: 'k1'}) == 'a'
    assert rec_eval(ab, memo={i: 'k2'}) == 'b'
    assert_raises(Exception, rec_eval, ab, memo={i: 'err'})


def test_recursion():
    scope.define(Lambda('Fact', [('x', p0)],
            expr=scope.switch(
                p0 > 1,
                1,
                p0 * apply('Fact', p0 - 1))))
    print scope.Fact(3)
    #print rec_eval(scope.Fact(3))
    assert rec_eval(scope.Fact(3)) == 6


def test_partial():
    add2 = scope.partial('add', 2)
    print add2
    assert len(str(add2).split('\n')) == 3

    # add2 evaluates to a scope method
    thing = rec_eval(add2)
    print thing
    assert 'SymbolTableEntry' in str(thing)

    # add2() evaluates to a failure because it's only a partial application
    assert_raises(NotImplementedError, rec_eval, add2())

    # add2(3) evaluates to 5 because we've filled in all the blanks
    thing = rec_eval(add2(3))
    print thing
    assert thing == 5


def test_callpipe():

    # -- set up some 1-variable functions
    a2 = scope.partial('add', 2)
    a3 = scope.partial('add', 3)

    def s9(a):
        return scope.sub(a, 9)

    # x + 2 + 3 - 9 == x - 4
    r = scope.callpipe1([a2, a3, s9], 5)
    thing = rec_eval(r)
    assert thing == 1


def test_clone_merge():
    a, b, c = as_apply((2, 3, 2))
    d = (a + b) * (c + b)
    len_d = len(dfs(d))

    e = clone_merge(d, merge_literals=True)
    assert len_d == len(dfs(d))
    assert len_d > len(dfs(e))
    assert e.eval() == d.eval()

def test_clone_merge_no_merge_literals():
    a, b, c = as_apply((2, 3, 2))
    d = (a + b) * (c + b)
    len_d = len(dfs(d))
    e = clone_merge(d, merge_literals=False)
    assert len_d == len(dfs(d))
    assert len_d == len(dfs(e))
    assert e.eval() == d.eval()

def test_len():
    assert_raises(TypeError, len, scope.uniform(0, 1))



########NEW FILE########
__FILENAME__ = test_stochastic
import numpy as np
from hyperopt.pyll import scope, as_apply, dfs, rec_eval
from hyperopt.pyll.stochastic import *

def test_recursive_set_rng_kwarg():
    uniform = scope.uniform
    a = as_apply([uniform(0, 1), uniform(2, 3)])
    rng = np.random.RandomState(234)
    recursive_set_rng_kwarg(a, rng)
    print a
    val_a = rec_eval(a)
    assert 0 < val_a[0] < 1
    assert 2 < val_a[1] < 3


def test_lnorm():
    G = scope
    choice = G.choice
    uniform = G.uniform
    quantized_uniform = G.quniform

    inker_size = quantized_uniform(low=0, high=7.99, q=2) + 3
    # -- test that it runs
    lnorm = as_apply({'kwargs': {'inker_shape' : (inker_size, inker_size),
             'outker_shape' : (inker_size, inker_size),
             'remove_mean' : choice([0, 1]),
             'stretch' : uniform(low=0, high=10),
             'threshold' : uniform(
                 low=.1 / np.sqrt(10.),
                 high=10 * np.sqrt(10))
             }})
    print lnorm
    print 'len', len(str(lnorm))
    # not sure what to assert
    # ... this is too fagile
    # assert len(str(lnorm)) == 980


def test_sample_deterministic():
    aa = as_apply([0, 1])
    print aa
    dd = sample(aa, np.random.RandomState(3))
    assert dd == (0, 1)


def test_repeatable():
    u = scope.uniform(0, 1)
    aa = as_apply(dict(
                u = u,
                n = scope.normal(5, 0.1),
                l = [0, 1, scope.one_of(2, 3), u]))
    dd1 = sample(aa, np.random.RandomState(3))
    dd2 = sample(aa, np.random.RandomState(3))
    dd3 = sample(aa, np.random.RandomState(4))
    assert dd1 == dd2
    assert dd1 != dd3


def test_sample():
    u = scope.uniform(0, 1)
    aa = as_apply(dict(
                u = u,
                n = scope.normal(5, 0.1),
                l = [0, 1, scope.one_of(2, 3), u]))
    print aa
    dd = sample(aa, np.random.RandomState(3))
    assert 0 < dd['u'] < 1
    assert 4 < dd['n'] < 6
    assert dd['u'] == dd['l'][3]
    assert dd['l'][:2] == (0, 1)
    assert dd['l'][2] in (2, 3)


########NEW FILE########
__FILENAME__ = pyll_utils
from functools import partial
from base import DuplicateLabel
from pyll.base import Apply
from pyll import scope
from pyll import as_apply

#
# Hyperparameter Types
#

@scope.define
def hyperopt_param(label, obj):
    """ A graph node primarily for annotating - VectorizeHelper looks out
    for these guys, and optimizes subgraphs of the form:

        hyperopt_param(<stochastic_expression>(...))

    """
    return obj


def hp_pchoice(label, p_options):
    """
    label: string
    p_options: list of (probability, option) pairs
    """
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    p, options = zip(*p_options)
    n_options = len(options)
    ch = scope.hyperopt_param(label,
                              scope.categorical(
                                  p,
                                  upper=n_options))
    return scope.switch(ch, *options)


def hp_choice(label, options):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    ch = scope.hyperopt_param(label,
        scope.randint(len(options)))
    return scope.switch(ch, *options)


def hp_randint(label, *args, **kwargs):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    return scope.hyperopt_param(label,
        scope.randint(*args, **kwargs))


def hp_uniform(label, *args, **kwargs):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    return scope.float(
            scope.hyperopt_param(label,
                scope.uniform(*args, **kwargs)))


def hp_quniform(label, *args, **kwargs):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    return scope.float(
            scope.hyperopt_param(label,
                scope.quniform(*args, **kwargs)))


def hp_loguniform(label, *args, **kwargs):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    return scope.float(
            scope.hyperopt_param(label,
                scope.loguniform(*args, **kwargs)))


def hp_qloguniform(label, *args, **kwargs):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    return scope.float(
            scope.hyperopt_param(label,
                scope.qloguniform(*args, **kwargs)))


def hp_normal(label, *args, **kwargs):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    return scope.float(
            scope.hyperopt_param(label,
                scope.normal(*args, **kwargs)))


def hp_qnormal(label, *args, **kwargs):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    return scope.float(
            scope.hyperopt_param(label,
                scope.qnormal(*args, **kwargs)))


def hp_lognormal(label, *args, **kwargs):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    return scope.float(
            scope.hyperopt_param(label,
                scope.lognormal(*args, **kwargs)))


def hp_qlognormal(label, *args, **kwargs):
    if not isinstance(label, basestring):
        raise TypeError('require string label')
    return scope.float(
            scope.hyperopt_param(label,
                scope.qlognormal(*args, **kwargs)))


#
# Tools for extracting a search space from a Pyll graph
#


class Cond(object):
    def __init__(self, name, val, op):
        self.op = op
        self.name = name
        self.val = val

    def __str__(self):
        return 'Cond{%s %s %s}' %  (self.name, self.op, self.val)

    def __eq__(self, other):
        return self.op == other.op and self.name == other.name and self.val == other.val

    def __hash__(self):
        return hash((self.op, self.name, self.val))

    def __repr__(self):
        return str(self)

EQ = partial(Cond, op='=')

def _expr_to_config(expr, conditions, hps):
    if expr.name == 'switch':
        idx = expr.inputs()[0]
        options = expr.inputs()[1:]
        assert idx.name == 'hyperopt_param'
        assert idx.arg['obj'].name in (
                'randint',     # -- in case of hp.choice
                'categorical', # -- in case of hp.pchoice
                )
        _expr_to_config(idx, conditions, hps)
        for ii, opt in enumerate(options):
            _expr_to_config(opt,
                           conditions + (EQ(idx.arg['label'].obj, ii),),
                           hps)
    elif expr.name == 'hyperopt_param':
        label = expr.arg['label'].obj
        if label in hps:
            if hps[label]['node'] != expr.arg['obj']:
                raise DuplicateLabel(label)
            hps[label]['conditions'].add(conditions)
        else:
            hps[label] = {'node': expr.arg['obj'],
                          'conditions': set((conditions,)),
                          'label': label,
                          }
    else:
        for ii in expr.inputs():
            _expr_to_config(ii, conditions, hps)

def expr_to_config(expr, conditions, hps):
    """
    Populate dictionary `hps` with the hyperparameters in pyll graph `expr`
    and conditions for participation in the evaluation of `expr`.

    Arguments:
    expr       - a pyll expression root.
    conditions - a tuple of conditions (`Cond`) that must be True for
                 `expr` to be evaluated.
    hps        - dictionary to populate

    Creates `hps` dictionary:
        label -> { 'node': apply node of hyperparameter distribution,
                   'conditions': `conditions` + tuple,
                   'label': label
                   }
    """
    expr = as_apply(expr)
    if conditions is None:
        conditions = ()
    assert isinstance(expr, Apply)
    _expr_to_config(expr, conditions, hps)
    _remove_allpaths(hps, conditions)

    
def _remove_allpaths(hps, conditions):
    """Hacky way to recognize some kinds of false dependencies
    Better would be logic programming.
    """
    potential_conds = {}
    for k, v in hps.items():
        if v['node'].name in ('randint', 'categorical'):
            upper = v['node'].arg['upper'].obj
            potential_conds[k] = frozenset([EQ(k, ii) for ii in range(upper)])

    for k, v in hps.items():
        if len(v['conditions']) > 1:
            all_conds = [[c for c in cond if c is not True]
                         for cond in v['conditions']]
            all_conds = [cond for cond in all_conds if len(cond) >= 1]
            if len(all_conds) == 0:
                v['conditions'] = set([conditions])
                continue

            depvar = all_conds[0][0].name

            all_one_var = all(len(cond) == 1 and cond[0].name == depvar
                              for cond in all_conds)
            if all_one_var:
                conds = [cond[0] for cond in all_conds]
                if frozenset(conds) == potential_conds[depvar]:
                    v['conditions'] = set([conditions])
                    continue


# -- eof

########NEW FILE########
__FILENAME__ = rand
"""
Random search - presented as hyperopt.fmin_random
"""
import logging
import numpy as np

import pyll

from .base import miscs_update_idxs_vals

logger = logging.getLogger(__name__)


def suggest(new_ids, domain, trials, seed):
    #logger.debug("in suggest with seed: %s" % (str(seed)))
    #logger.debug('generating trials for new_ids: %s' % str(new_ids))

    rng = np.random.RandomState(seed)
    rval = []
    for ii, new_id in enumerate(new_ids):
        # -- sample new specs, idxs, vals
        idxs, vals = pyll.rec_eval(
            domain.s_idxs_vals,
            memo={
                domain.s_new_ids: [new_id],
                domain.s_rng: rng,
            })
        new_result = domain.new_result()
        new_misc = dict(tid=new_id, cmd=domain.cmd, workdir=domain.workdir)
        miscs_update_idxs_vals([new_misc], idxs, vals)
        rval.extend(trials.new_trial_docs([new_id],
                    [None], [new_result], [new_misc]))
    return rval


def suggest_batch(new_ids, domain, trials, seed):

    rng = np.random.RandomState(seed)
    # -- sample new specs, idxs, vals
    idxs, vals = pyll.rec_eval(
        domain.s_idxs_vals,
        memo={
            domain.s_new_ids: new_ids,
            domain.s_rng: rng,
        })
    return idxs, vals


# flake8 likes no trailing blank line

########NEW FILE########
__FILENAME__ = rdists
"""
Extra distributions to complement scipy.stats

"""
import numpy as np
import numpy.random as mtrand
import scipy.stats
from scipy.stats import rv_continuous, rv_discrete
from scipy.stats.distributions import rv_generic


class uniform_gen(scipy.stats.distributions.uniform_gen):
    # -- included for completeness
    pass


class norm_gen(scipy.stats.distributions.norm_gen):
    # -- included for completeness
    pass


class loguniform_gen(rv_continuous):
    """ Stats for Y = e^X where X ~ U(low, high).

    """
    def __init__(self, low=0, high=1):
        rv_continuous.__init__(self,
                a=np.exp(low),
                b=np.exp(high))
        self._low = low
        self._high = high

    def _rvs(self):
        rval = np.exp(mtrand.uniform(
            self._low,
            self._high,
            self._size))
        return rval

    def _pdf(self, x):
        return 1.0 / (x * (self._high - self._low))

    def _logpdf(self, x):
        return - np.log(x) - np.log(self._high - self._low)

    def _cdf(self, x):
        return (np.log(x) - self._low) / (self._high - self._low)


# -- cut and paste from scipy.stats
#    because the way s is passed to these functions makes it impossible
#    to construct this class. insane
class lognorm_gen(rv_continuous):
    """A lognormal continuous random variable.

    %(before_notes)s

    Notes
    -----
    The probability density function for `lognorm` is::

        lognorm.pdf(x, s) = 1 / (s*x*sqrt(2*pi)) * exp(-1/2*(log(x)/s)**2)

    for ``x > 0``, ``s > 0``.

    If log x is normally distributed with mean mu and variance sigma**2,
    then x is log-normally distributed with shape paramter sigma and scale
    parameter exp(mu).

    %(example)s

    """
    def __init__(self, mu, sigma):
        self.mu_ = mu
        self.s_ = sigma
        self.norm_ = scipy.stats.norm
        rv_continuous.__init__(self, a=0.0, name='loguniform', shapes='s')

    def _rvs(self):
        s = self.s_
        return np.exp(self.mu_ + s * self.norm_.rvs(size=self._size))

    def _pdf(self, x):
        s = self.s_
        Px = np.exp(-(np.log(x) - self.mu_ ) ** 2 / (2 * s ** 2))
        return Px / (s * x * np.sqrt(2 * np.pi))

    def _cdf(self, x):
        s = self.s_
        return self.norm_.cdf((np.log(x) - self.mu_) / s)

    def _ppf(self, q):
        s = self.s_
        return np.exp(s*self.norm_._ppf(q) + self.mu_)

    def _stats(self):
        if self.mu_ != 0.0:
            raise NotImplementedError()
        s = self.s_
        p = np.exp(s*s)
        mu = np.sqrt(p)
        mu2 = p*(p-1)
        g1 = np.sqrt((p-1))*(2+p)
        g2 = np.polyval([1,2,3,0,-6.0],p)
        return mu, mu2, g1, g2

    def _entropy(self):
        if self.mu_ != 0.0:
            raise NotImplementedError()
        s = self.s_
        return 0.5 * (1 + np.log(2 * np.pi) + 2 * np.log(s))


def qtable_pmf(x, q, qlow, xs, ps):
    qx = np.round(np.atleast_1d(x).astype(np.float) / q) * q
    is_multiple = np.isclose(qx, x)
    ix = np.round((qx - qlow) / q).astype(np.int)
    is_inbounds = np.logical_and(ix >= 0, ix < len(ps))
    oks = np.logical_and(is_multiple, is_inbounds)
    rval = np.zeros_like(qx)
    rval[oks] = np.asarray(ps)[ix[oks]]
    if isinstance(x, np.ndarray):
        return rval.reshape(x.shape)
    else:
        return float(rval)


def qtable_logpmf(x, q, qlow, xs, ps):
    p = qtable_pmf(np.atleast_1d(x), q, qlow, xs, ps)
    # -- this if/else avoids np warning about underflow
    rval = np.zeros_like(p)
    rval[p == 0] = -np.inf
    rval[p != 0] = np.log(p[p != 0])
    if isinstance(x, np.ndarray):
        return rval
    else:
        return float(rval)


class quniform_gen(object):
    # -- not inheriting from scipy.stats.rv_discrete
    #    because I don't understand the design of those rv classes
    """ Stats for Y = q * round(X / q) where X ~ U(low, high).

    """
    def __init__(self, low, high, q):
        low, high, q = map(float, (low, high, q))
        qlow = np.round(low / q) * q
        qhigh = np.round(high / q) * q
        if qlow == qhigh:
            xs = [qlow]
            ps = [1.0]
        else:
            lowmass = 1 - ((low - qlow + .5 * q) / q)
            assert 0 <= lowmass <= 1.0, (lowmass, low, qlow, q)
            highmass = (high - qhigh + .5 * q) / q
            assert 0 <= highmass <= 1.0, (highmass, high, qhigh, q)
            # -- xs: qlow to qhigh inclusive
            xs = np.arange(qlow, qhigh + .5 * q, q)
            ps = np.ones(len(xs))
            ps[0] = lowmass
            ps[-1] = highmass
            ps /= ps.sum()

        self.low = low
        self.high = high
        self.q = q
        self.qlow = qlow
        self.qhigh = qhigh
        self.xs = np.asarray(xs)
        self.ps = np.asarray(ps)

    def pmf(self, x):
        return qtable_pmf(x, self.q, self.qlow, self.xs, self.ps)

    def logpmf(self, x):
        return qtable_logpmf(x, self.q, self.qlow, self.xs, self.ps)

    def rvs(self, size=()):
        rval = mtrand.uniform(low=self.low, high=self.high, size=size)
        rval = np.round(rval / self.q) * self.q
        return rval


class qloguniform_gen(quniform_gen):
    """ Stats for Y = q * round(e^X / q) where X ~ U(low, high).

    """
    # -- not inheriting from scipy.stats.rv_discrete
    #    because I don't understand the design of those rv classes

    def __init__(self, low, high, q):
        low, high, q = map(float, (low, high, q))
        elow = np.exp(low)
        ehigh = np.exp(high)
        qlow = np.round(elow / q) * q
        qhigh = np.round(ehigh / q) * q

        # -- loguniform for using the CDF
        lu = loguniform_gen(low=low, high=high)

        cut_low = np.exp(low) # -- lowest possible pre-round value
        cut_high = min(qlow + .5 * q, # -- highest value that would ...
                       ehigh)         # -- round to qlow
        xs = [qlow]
        ps = [lu.cdf(cut_high)]
        ii = 0
        cdf_high = ps[0]

        while cut_high < (ehigh - 1e-10):
            cut_high, cut_low = min(cut_high + q, ehigh), cut_high
            cdf_high, cdf_low = lu.cdf(cut_high), cdf_high
            ii += 1
            xs.append(qlow + ii * q)
            ps.append(cdf_high - cdf_low)

        ps = np.asarray(ps)
        ps /= ps.sum()

        self.low = low
        self.high = high
        self.q = q
        self.qlow = qlow
        self.qhigh = qhigh
        self.xs = np.asarray(xs)
        self.ps = ps

    def pmf(self, x):
        return qtable_pmf(x, self.q, self.qlow, self.xs, self.ps)

    def logpmf(self, x):
        return qtable_logpmf(x, self.q, self.qlow, self.xs, self.ps)

    def rvs(self, size=()):
        x = mtrand.uniform(low=self.low, high=self.high, size=size)
        rval = np.round(np.exp(x) / self.q) * self.q
        return rval


class qnormal_gen(object):
    """Stats for Y = q * round(X / q) where X ~ N(mu, sigma)
    """
    def __init__(self, mu, sigma, q):
        self.mu, self.sigma, self.q = map(float, (mu, sigma, q))
        # -- distfn for using the CDF
        self._norm_logcdf = scipy.stats.norm(loc=mu, scale=sigma).logcdf

    def in_domain(self, x):
        return np.isclose(x, np.round(x / self.q) * self.q)

    def pmf(self, x):
        return np.exp(self.logpmf(x))

    def logpmf(self, x):
        x1 = np.atleast_1d(x)
        in_domain = self.in_domain(x1)
        rval = np.zeros_like(x1, dtype=np.float) - np.inf
        x_in_domain = x1[in_domain]

        ubound = x_in_domain + self.q * 0.5
        lbound = x_in_domain - self.q * 0.5
        # -- reflect intervals right of mu to other side
        #    for more accurate calculation
        flip = (lbound > self.mu)
        tmp = lbound[flip].copy()
        lbound[flip] = self.mu - (ubound[flip] - self.mu)
        ubound[flip] = self.mu - (tmp - self.mu)

        #if lbound > self.mu:
            #lbound, ubound = (self.mu - (ubound - self.mu),
                              #self.mu - (lbound - self.mu))
        assert np.all(ubound > lbound)
        a = self._norm_logcdf(ubound)
        b = self._norm_logcdf(lbound)
        rval[in_domain] = a + np.log1p(- np.exp(b - a))
        if isinstance(x, np.ndarray):
            return rval
        else:
            return float(rval)

    def rvs(self, size=()):
        x = mtrand.normal(loc=self.mu, scale=self.sigma, size=size)
        rval = np.round(x / self.q) * self.q
        return rval


class qlognormal_gen(object):
    """Stats for Y = q * round(exp(X) / q) where X ~ N(mu, sigma)
    """
    def __init__(self, mu, sigma, q):
        self.mu, self.sigma, self.q = map(float, (mu, sigma, q))
        # -- distfn for using the CDF
        self._norm_cdf = scipy.stats.norm(loc=mu, scale=sigma).cdf

    def in_domain(self, x):
        return np.logical_and((x >= 0),
                              np.isclose(x, np.round(x / self.q) * self.q))

    def pmf(self, x):
        x1 = np.atleast_1d(x)
        in_domain = self.in_domain(x1)
        x1_in_domain = x1[in_domain]
        rval = np.zeros_like(x1, dtype=np.float)
        rval_in_domain = self._norm_cdf(np.log(x1_in_domain + 0.5 * self.q))
        rval_in_domain[x1_in_domain != 0] -= self._norm_cdf(
            np.log(x1_in_domain[x1_in_domain != 0] - 0.5 * self.q))
        rval[in_domain] = rval_in_domain
        if isinstance(x, np.ndarray):
            return rval
        else:
            return float(rval)


    def logpmf(self, x):
        pmf = self.pmf(np.atleast_1d(x))
        assert np.all(pmf >= 0)
        pmf[pmf == 0] = -np.inf
        pmf[pmf > 0] = np.log(pmf[pmf > 0])
        if isinstance(x, np.ndarray):
            return pmf
        else:
            return float(pmf)

    def rvs(self, size=()):
        x = mtrand.normal(loc=self.mu, scale=self.sigma, size=size)
        rval = np.round(np.exp(x) / self.q) * self.q
        return rval


# -- non-empty last line for flake8

########NEW FILE########
__FILENAME__ = test_anneal
from functools import partial
import unittest
import numpy as np
from hyperopt import anneal
from hyperopt import rand
from hyperopt import Trials, fmin

from test_domains import CasePerDomain

def passthrough(x):
    return x

class TestItJustRuns(unittest.TestCase, CasePerDomain):
    def work(self):
        trials = Trials()
        space = self.bandit.expr
        fmin(
            fn=passthrough,
            space=space,
            trials=trials,
            algo=anneal.suggest,
            max_evals=10)


class TestItAtLeastSortOfWorks(unittest.TestCase, CasePerDomain):
    thresholds = dict(
            quadratic1=1e-5,
            q1_lognormal=0.01,
            distractor=-0.96, #-- anneal is a strategy that can really
                              #   get tricked by the distractor.
            gauss_wave=-2.0,
            gauss_wave2=-2.0,
            n_arms=-2.5,
            many_dists=.0005,
            branin=0.7,
            )

    LEN = dict(
            # -- running a long way out tests overflow/underflow
            #    to some extent
            quadratic1=1000,
            many_dists=200,
            # -- anneal is pretty bad at this kind of function
            distractor=150,
            #q1_lognormal=100,
            branin=200,
            )

    def setUp(self):
        self.olderr = np.seterr('raise')
        np.seterr(under='ignore')

    def tearDown(self, *args):
        np.seterr(**self.olderr)

    def work(self):
        bandit = self.bandit
        assert bandit.name is not None
        algo = partial(
            anneal.suggest,
                )
        LEN = self.LEN.get(bandit.name, 50)

        trials = Trials()
        fmin(fn=passthrough,
            space=self.bandit.expr,
            trials=trials,
            algo=algo,
            max_evals=LEN)
        assert len(trials) == LEN

        if 1:
            rtrials = Trials()
            fmin(fn=passthrough,
                space=self.bandit.expr,
                trials=rtrials,
                algo=rand.suggest,
                max_evals=LEN)
            print 'RANDOM BEST 6:', list(sorted(rtrials.losses()))[:6]

        if 0:
            plt.subplot(2, 2, 1)
            plt.scatter(range(LEN), trials.losses())
            plt.title('TPE losses')
            plt.subplot(2, 2, 2)
            plt.scatter(range(LEN), ([s['x'] for s in trials.specs]))
            plt.title('TPE x')
            plt.subplot(2, 2, 3)
            plt.title('RND losses')
            plt.scatter(range(LEN), rtrials.losses())
            plt.subplot(2, 2, 4)
            plt.title('RND x')
            plt.scatter(range(LEN), ([s['x'] for s in rtrials.specs]))
            plt.show()
        if 0:
            plt.hist(
                    [t['x'] for t in self.experiment.trials],
                    bins=20)

        #print trials.losses()
        print 'ANNEAL BEST 6:', list(sorted(trials.losses()))[:6]
        #logx = np.log([s['x'] for s in trials.specs])
        #print 'TPE MEAN', np.mean(logx)
        #print 'TPE STD ', np.std(logx)
        thresh = self.thresholds[bandit.name]
        print 'Thresh', thresh
        assert min(trials.losses()) < thresh



########NEW FILE########
__FILENAME__ = test_base
import copy
import unittest
import numpy as np
import bson

from hyperopt.pyll import scope
uniform = scope.uniform
normal = scope.normal
one_of = scope.one_of

from hyperopt.base import JOB_STATE_NEW
from hyperopt.base import TRIAL_KEYS
from hyperopt.base import TRIAL_MISC_KEYS
from hyperopt.base import InvalidTrial
from hyperopt.base import miscs_to_idxs_vals
from hyperopt.base import SONify
from hyperopt.base import Trials
from hyperopt.base import trials_from_docs


def ok_trial(tid, *args, **kwargs):
    return dict(
        tid=tid,
        result={'status': 'algo, ok'},
        spec={'a':1, 'foo': (args, kwargs)},
        misc={
            'tid':tid,
            'cmd':("some cmd",),
            'idxs':{'z':[tid]},
            'vals':{'z':[1]}},
        extra='extra', # -- more stuff here is ok
        owner=None,
        state=JOB_STATE_NEW,
        version=0,
        book_time=None,
        refresh_time=None,
        exp_key=None,
        )


class Suggest_API(object):
    """
    Run some generic sanity-checks of a suggest algorithm to make sure that
    it respects the semantics expected by e.g. fmin.

    Use it like this:

        TestRand = Suggest_API.make_test_class(rand.suggest, 'TestRand')

    """

    @classmethod
    def make_tst_class(cls, suggest, domain, name):
        class Tester(unittest.TestCase, cls):
            def suggest(self, *args, **kwargs):
                print args, kwargs
                return suggest(*args, **kwargs)

            def setUp(self):
                self.domain = domain
        Tester.__name__ = name
        return Tester


    seed_randomizes = True

    def idxs_vals_from_ids(self, ids, seed):
        docs = self.suggest(ids, self.domain, Trials(), seed)
        trials = trials_from_docs(docs)
        idxs, vals = miscs_to_idxs_vals(trials.miscs)
        return idxs, vals

    def test_arbitrary_ids(self):
        # -- suggest implementations should work for arbitrary ID
        #    values (possibly assuming they are hashable), and the
        #    ID values should have no effect on the return values.
        ids_1 = [-2, 0, 7, 'a', '007', 66, 'a3', '899', 23, 2333]
        ids_2 = ['a', 'b', 'c', 'd', 1, 2, 3, 0.1, 0.2, 0.3]
        idxs_1, vals_1 = self.idxs_vals_from_ids(ids=ids_1, seed=45)
        idxs_2, vals_2 = self.idxs_vals_from_ids(ids=ids_2, seed=45)
        all_ids_1 = set()
        for var, ids in idxs_1.items():
            all_ids_1.update(ids)
        all_ids_2 = set()
        for var, ids in idxs_2.items():
            all_ids_2.update(ids)
        self.assertEqual(all_ids_1, set(ids_1))
        self.assertEqual(all_ids_2, set(ids_2))
        self.assertEqual(vals_1, vals_2)

    def test_seed_randomizes(self):
        #
        # suggest() algorithms can be either stochastic (e.g. random search)
        # or deterministic (e.g. grid search).  If an suggest implementation
        # is stochastic, then changing the seed argument should change the
        # return value.
        #
        if not self.seed_randomizes:
            return

        # -- sample 20 points to make sure we get some differences even
        #    for small search spaces (chance of false failure is 1/million).
        idxs_1, vals_1 = self.idxs_vals_from_ids(ids=range(20), seed=45)
        idxs_2, vals_2 = self.idxs_vals_from_ids(ids=range(20), seed=46)
        self.assertNotEqual((idxs_1, vals_1), (idxs_2, vals_2))


class TestTrials(unittest.TestCase):
    def setUp(self):
        self.trials = Trials()

    def test_valid(self):
        trials = self.trials
        f = trials.insert_trial_doc
        fine = ok_trial('ID', 1, 2, 3)

        # --original runs fine
        f(fine)

        # -- take out each mandatory root key
        def knockout(key):
            rval = copy.deepcopy(fine)
            del rval[key]
            return rval
        for key in TRIAL_KEYS:
            self.assertRaises(InvalidTrial, f, knockout(key))

        # -- take out each mandatory misc key
        def knockout2(key):
            rval = copy.deepcopy(fine)
            del rval['misc'][key]
            return rval
        for key in TRIAL_MISC_KEYS:
            self.assertRaises(InvalidTrial, f, knockout2(key))

    def test_insert_sync(self):
        trials = self.trials
        assert len(trials) == 0
        trials.insert_trial_doc(ok_trial('a', 8))
        assert len(trials) == 0
        trials.insert_trial_doc(ok_trial(5, a=1, b=3))
        assert len(trials) == 0
        trials.insert_trial_docs(
                [ok_trial(tid=4, a=2, b=3), ok_trial(tid=9, a=4, b=3)])
        assert len(trials) == 0
        trials.refresh()

        assert len(trials) == 4, len(trials)
        assert len(trials) == len(trials.specs)
        assert len(trials) == len(trials.results)
        assert len(trials) == len(trials.miscs)

        trials.insert_trial_docs(
                trials.new_trial_docs(
                    ['id0', 'id1'],
                    [dict(a=1), dict(a=2)],
                    [dict(status='new'), dict(status='new')],
                    [dict(tid='id0', idxs={}, vals={}, cmd=None),
                        dict(tid='id1', idxs={}, vals={}, cmd=None)],))

        assert len(trials) == 4
        assert len(trials) == len(trials.specs)
        assert len(trials) == len(trials.results)
        assert len(trials) == len(trials.miscs)

        trials.refresh()
        assert len(trials) == 6
        assert len(trials) == len(trials.specs)
        assert len(trials) == len(trials.results)
        assert len(trials) == len(trials.miscs)


class TestSONify(unittest.TestCase):

    def SONify(self, foo):
        rval = SONify(foo)
        assert bson.BSON.encode(dict(a=rval))
        return rval

    def test_int(self):
        assert self.SONify(1) == 1

    def test_float(self):
        assert self.SONify(1.1) == 1.1

    def test_np_int(self):
        assert self.SONify(np.int(1)) == 1

    def test_np_float(self):
        assert self.SONify(np.float(1.1)) == 1.1

    def test_np_1d_int(self):
        assert np.all(self.SONify(np.asarray([1, 2, 3]))
                == [1, 2, 3])

    def test_np_1d_float(self):
        assert np.all(self.SONify(np.asarray([1, 2, 3.4]))
                == [1, 2, 3.4])

    def test_np_1d_str(self):
        assert np.all(self.SONify(np.asarray(['a', 'b', 'ccc']))
                == ['a', 'b', 'ccc'])

    def test_np_2d_int(self):
        assert np.all(self.SONify(np.asarray([[1, 2], [3, 4]]))
                == [[1, 2], [3, 4]])

    def test_np_2d_float(self):
        assert np.all(self.SONify(np.asarray([[1, 2], [3, 4.5]]))
                == [[1, 2], [3, 4.5]])

    def test_nested_w_bool(self):
        thing = dict(a=1, b='2', c=True, d=False, e=np.int(3), f=[1l])
        assert thing == SONify(thing)





########NEW FILE########
__FILENAME__ = test_criteria
import numpy as np
import hyperopt.criteria as crit


def test_ei():
    rng = np.random.RandomState(123)
    for mean, var in [(0, 1), (-4, 9)]:
        thresholds = np.arange(-5, 5, .25) * np.sqrt(var) + mean

        v_n = [crit.EI_gaussian_empirical(mean, var, thresh, rng, 10000)
               for thresh in thresholds]
        v_a = [crit.EI_gaussian(mean, var, thresh)
               for thresh in thresholds]

        #import matplotlib.pyplot as plt
        #plt.plot(thresholds, v_n)
        #plt.plot(thresholds, v_a)
        #plt.show()

        if not np.allclose(v_n, v_a, atol=0.03, rtol=0.03):
            for t, n, a in zip(thresholds, v_n, v_a):
                print t, n, a, abs(n - a), abs(n - a) / (abs(n) + abs(a))
            assert 0
            #mean, var, thresh, v_n, v_a)


def test_log_ei():
    for mean, var in [(0, 1), (-4, 9)]:
        thresholds = np.arange(-5, 30, .25) * np.sqrt(var) + mean

        ei = np.asarray(
            [crit.EI_gaussian(mean, var, thresh)
             for thresh in thresholds])
        nlei = np.asarray(
            [crit.logEI_gaussian(mean, var, thresh)
             for thresh in thresholds])
        naive = np.log(ei)
        #import matplotlib.pyplot as plt
        #plt.plot(thresholds, ei, label='ei')
        #plt.plot(thresholds, nlei, label='nlei')
        #plt.plot(thresholds, naive, label='naive')
        #plt.legend()
        #plt.show()

        # -- assert that they match when the threshold isn't too high
        assert np.allclose(nlei, naive)


def test_log_ei_range():
    assert np.all(
        np.isfinite(
            [crit.logEI_gaussian(0, 1, thresh)
             for thresh in [-500, 0, 50, 100, 500, 5000]]))


def test_ucb():
    assert np.allclose(crit.UCB(0, 1, 1), 1)
    assert np.allclose(crit.UCB(0, 1, 2), 2)
    assert np.allclose(crit.UCB(0, 4, 1), 2)
    assert np.allclose(crit.UCB(1, 4, 1), 3)

# -- flake8

########NEW FILE########
__FILENAME__ = test_domains
import unittest

import numpy as np

from hyperopt import Trials, Domain, fmin, hp, base
from hyperopt.rand import suggest
from hyperopt.pyll import as_apply
from hyperopt.pyll import scope


# -- define this bandit here too for completeness' sake
def domain_constructor(**b_kwargs):
    """
    Decorate a function that returns a pyll expressions so that
    it becomes a Domain instance instead of a function

    Example:

    @domain_constructor(loss_target=0)
    def f(low, high):
        return {'loss': hp.uniform('x', low, high) ** 2 }

    """
    def deco(f):
        def wrapper(*args, **kwargs):
            if 'name' in b_kwargs:
                _b_kwargs = b_kwargs
            else:
                _b_kwargs = dict(b_kwargs, name=f.__name__)
            f_rval = f(*args, **kwargs)
            domain = Domain(lambda x: x, f_rval, **_b_kwargs)
            return domain
        wrapper.__name__ = f.__name__
        return wrapper
    return deco


@domain_constructor()
def coin_flip():
    """ Possibly the simplest possible Bandit implementation
    """
    return {'loss': hp.choice('flip', [0.0, 1.0]), 'status': base.STATUS_OK}



@domain_constructor(loss_target=0)
def quadratic1():
    """
    About the simplest problem you could ask for:
    optimize a one-variable quadratic function.
    """
    return {'loss': (hp.uniform('x', -5, 5) - 3) ** 2, 'status': base.STATUS_OK}


@domain_constructor(loss_target=0)
def q1_choice():
    o_x = hp.choice('o_x', [
        (-3, hp.uniform('x_neg', -5, 5)),
        ( 3, hp.uniform('x_pos', -5, 5)),
        ])
    return {'loss': (o_x[0] - o_x[1])  ** 2, 'status': base.STATUS_OK}


@domain_constructor(loss_target=0)
def q1_lognormal():
    """
    About the simplest problem you could ask for:
    optimize a one-variable quadratic function.
    """
    return {'loss': scope.min(0.1 * (hp.lognormal('x', 0, 2) - 10) ** 2,
                              10),
            'status': base.STATUS_OK }


@domain_constructor(loss_target=-2)
def n_arms(N=2):
    """
    Each arm yields a reward from a different Gaussian.

    The correct arm is arm 0.

    """
    rng = np.random.RandomState(123)
    x = hp.choice('x', [0, 1])
    reward_mus = as_apply([-1] + [0] * (N - 1))
    reward_sigmas = as_apply([1] * N)
    return {'loss': scope.normal(reward_mus[x], reward_sigmas[x], rng=rng),
            'loss_variance': 1.0,
            'status': base.STATUS_OK}


@domain_constructor(loss_target=-2)
def distractor():
    """
    This is a nasty function: it has a max in a spike near -10, and a long
    asymptote that is easy to find, but guides hill-climbing approaches away
    from the true max.

    The second peak is at x=-10.
    The prior mean is 0.
    """

    x = hp.uniform('x', -15, 15)
    f1 = 1.0 / (1.0 + scope.exp(-x))    # climbs rightward from 0.0 to 1.0
    f2 = 2 * scope.exp(-(x + 10) ** 2)  # bump with height 2 at (x=-10)
    return {'loss': -f1 - f2, 'status': base.STATUS_OK}


@domain_constructor(loss_target=-1)
def gauss_wave():
    """
    Essentially, this is a high-frequency sinusoidal function plus a broad quadratic.
    One variable controls the position along the curve.
    The binary variable determines whether the sinusoidal is shifted by pi.

    So there are actually two maxima in this problem, it's just one is more
    probable.  The tricky thing here is dealing with the fact that there are two
    variables and one is discrete.

    """

    x = hp.uniform('x', -20, 20)
    t = hp.choice('curve', [x, x + np.pi])
    f1 = scope.sin(t)
    f2 = 2 * scope.exp(-(t / 5.0) ** 2)
    return {'loss': - (f1 + f2), 'status': base.STATUS_OK}


@domain_constructor(loss_target=-2.5)
def gauss_wave2():
    """
    Variant of the GaussWave problem in which noise is added to the score
    function, and there is an option to either have no sinusoidal variation, or
    a negative cosine with variable amplitude.

    Immediate local max is to sample x from spec and turn off the neg cos.
    Better solution is to move x a bit to the side, turn on the neg cos and turn
    up the amp to 1.
    """

    rng = np.random.RandomState(123)
    var = .1
    x = hp.uniform('x', -20, 20)
    amp = hp.uniform('amp', 0, 1)
    t = (scope.normal(0, var, rng=rng) + 2 * scope.exp(-(x / 5.0) ** 2))
    return {'loss': - hp.choice('hf', [t, t + scope.sin(x) * amp]),
            'loss_variance': var, 'status': base.STATUS_OK}


@domain_constructor(loss_target=0)
def many_dists():
    a=hp.choice('a', [0, 1, 2])
    b=hp.randint('b', 10)
    c=hp.uniform('c', 4, 7)
    d=hp.loguniform('d', -2, 0)
    e=hp.quniform('e', 0, 10, 3)
    f=hp.qloguniform('f', 0, 3, 2)
    g=hp.normal('g', 4, 7)
    h=hp.lognormal('h', -2, 2)
    i=hp.qnormal('i', 0, 10, 2)
    j=hp.qlognormal('j', 0, 2, 1)
    k=hp.pchoice('k', [(.1, 0), (.9, 1)])
    z = a + b + c + d + e + f + g + h + i + j + k
    return {'loss': scope.float(scope.log(1e-12 + z ** 2)),
            'status': base.STATUS_OK}


@domain_constructor(loss_target=0.398)
def branin():
    """
    The Branin, or Branin-Hoo, function has three global minima,
    and is roughly an angular trough across a 2D input space.

        f(x, y) = a (y - b x ** 2 + c x - r ) ** 2 + s (1 - t) cos(x) + s
    
    The recommended values of a, b, c, r, s and t are:
        a = 1
        b = 5.1 / (4 pi ** 2)
        c = 5 / pi
        r = 6
        s = 10
        t = 1 / (8 * pi)

    Global Minima:
      [(-pi, 12.275),
       (pi, 2.275),
       (9.42478, 2.475)]

    Source: http://www.sfu.ca/~ssurjano/branin.html
    """
    x = hp.uniform('x', -5., 10.)
    y = hp.uniform('y', 0., 15.)
    pi = float(np.pi)
    loss = ((y - (5.1 / (4 * pi ** 2)) * x ** 2 + 5 * x / pi - 6) ** 2
             + 10 * (1 - 1 / (8 * pi)) * scope.cos(x) + 10)
    return {'loss': loss,
            'loss_variance': 0,
            'status': base.STATUS_OK}


class DomainExperimentMixin(object):
    def test_basic(self):
        domain = self._domain_cls()
        #print 'domain params', domain.params, domain
        #print 'algo params', algo.vh.params
        trials = Trials()
        fmin(lambda x: x, domain.expr,
             trials=trials,
             algo=suggest,
             max_evals=self._n_steps)
        assert trials.average_best_error(domain) - domain.loss_target  < .2

    @classmethod
    def make(cls, domain_cls, n_steps=500):
        class Tester(unittest.TestCase, cls):
            def setUp(self):
                self._n_steps = n_steps
                self._domain_cls = domain_cls
        Tester.__name__ = domain_cls.__name__ + 'Tester'
        return Tester


quadratic1Tester = DomainExperimentMixin.make(quadratic1)
q1_lognormalTester = DomainExperimentMixin.make(q1_lognormal)
q1_choiceTester = DomainExperimentMixin.make(q1_choice)
n_armsTester = DomainExperimentMixin.make(n_arms)
distractorTester = DomainExperimentMixin.make(distractor)
gauss_waveTester = DomainExperimentMixin.make(gauss_wave)
gauss_wave2Tester = DomainExperimentMixin.make(gauss_wave2,
        n_steps=5000)
many_distsTester = DomainExperimentMixin.make(many_dists)
braninTester = DomainExperimentMixin.make(branin)


class CasePerDomain(object):
    # -- this is a mixin
    # -- Override self.work to execute a test for each kind of self.bandit

    def test_quadratic1(self):
        self.bandit = quadratic1()
        self.work()

    def test_q1lognormal(self):
        self.bandit = q1_lognormal()
        self.work()

    def test_twoarms(self):
        self.bandit = n_arms()
        self.work()

    def test_distractor(self):
        self.bandit = distractor()
        self.work()

    def test_gausswave(self):
        self.bandit = gauss_wave()
        self.work()

    def test_gausswave2(self):
        self.bandit = gauss_wave2()
        self.work()

    def test_many_dists(self):
        self.bandit = many_dists()
        self.work()

    def test_branin(self):
        self.bandit = branin()
        self.work()

# -- non-blank last line for flake8

########NEW FILE########
__FILENAME__ = test_fmin
import unittest
import numpy as np
import nose.tools

from hyperopt import fmin, rand, tpe, hp, Trials, exceptions, space_eval, STATUS_FAIL, STATUS_OK
from hyperopt.base import JOB_STATE_ERROR


def test_quadratic1_rand():
    trials = Trials()

    argmin = fmin(
            fn=lambda x: (x - 3) ** 2,
            space=hp.uniform('x', -5, 5),
            algo=rand.suggest,
            max_evals=500,
            trials=trials)

    assert len(trials) == 500
    assert abs(argmin['x'] - 3.0) < .25


def test_quadratic1_tpe():
    trials = Trials()

    argmin = fmin(
            fn=lambda x: (x - 3) ** 2,
            space=hp.uniform('x', -5, 5),
            algo=tpe.suggest,
            max_evals=50,
            trials=trials)

    assert len(trials) == 50, len(trials)
    assert abs(argmin['x'] - 3.0) < .25, argmin


def test_quadratic1_anneal():
    trials = Trials()
    import hyperopt.anneal

    N = 30
    def fn(x):
        return (x - 3) ** 2

    argmin = fmin(
            fn=fn,
            space=hp.uniform('x', -5, 5),
            algo=hyperopt.anneal.suggest,
            max_evals=N,
            trials=trials)

    print argmin

    assert len(trials) == N
    assert abs(argmin['x'] - 3.0) < .25


@nose.tools.raises(exceptions.DuplicateLabel)
def test_duplicate_label_is_error():
    trials = Trials()

    def fn(xy):
        x, y = xy
        return x ** 2 + y ** 2

    fmin(fn=fn,
            space=[
                hp.uniform('x', -5, 5),
                hp.uniform('x', -5, 5),
                ],
            algo=rand.suggest,
            max_evals=500,
            trials=trials)


def test_space_eval():
    space = hp.choice('a',
        [
            ('case 1', 1 + hp.lognormal('c1', 0, 1)),
            ('case 2', hp.uniform('c2', -10, 10))
        ])

    assert space_eval(space, {'a': 0, 'c1': 1.0}) == ('case 1', 2.0)
    assert space_eval(space, {'a': 1, 'c2': 3.5}) == ('case 2', 3.5)

def test_set_fmin_rstate():
    lossfn = lambda x: (x - 3) ** 2
    trials_seed0 = Trials()
    argmin_seed0 = fmin(
            fn=lossfn,
            space=hp.uniform('x', -5, 5),
            algo=rand.suggest,
            max_evals=1,
            trials=trials_seed0,
            rstate=np.random.RandomState(0))
    assert len(trials_seed0) == 1
    trials_seed1 = Trials()
    argmin_seed1 = fmin(
            fn=lossfn,
            space=hp.uniform('x', -5, 5),
            algo=rand.suggest,
            max_evals=1,
            trials=trials_seed1,
            rstate=np.random.RandomState(1))
    assert len(trials_seed1) == 1
    assert argmin_seed0 != argmin_seed1


class TestFmin(unittest.TestCase):
    class SomeError(Exception):
        #XXX also test domain.exceptions mechanism that actually catches this
        pass

    def eval_fn(self, space):
        raise TestFmin.SomeError()

    def setUp(self):
        self.trials = Trials()

    def test_catch_eval_exceptions_True(self):

        # -- should go to max_evals, catching all exceptions, so all jobs
        #    should have JOB_STATE_ERROR
        fmin(self.eval_fn,
             space=hp.uniform('x', 0, 1),
             algo=rand.suggest,
             trials=self.trials,
             max_evals=2,
             catch_eval_exceptions=True,
             return_argmin=False,)
        trials = self.trials
        assert len(trials) == 0
        assert len(trials._dynamic_trials) == 2
        assert trials._dynamic_trials[0]['state'] == JOB_STATE_ERROR
        assert trials._dynamic_trials[0]['misc']['error'] != None
        assert trials._dynamic_trials[1]['state'] == JOB_STATE_ERROR
        assert trials._dynamic_trials[1]['misc']['error'] != None

    def test_catch_eval_exceptions_False(self):
        with self.assertRaises(TestFmin.SomeError):
            fmin(self.eval_fn,
                 space=hp.uniform('x', 0, 1),
                 algo=rand.suggest,
                 trials=self.trials,
                 max_evals=2,
                 catch_eval_exceptions=False)
        print len(self.trials)
        assert len(self.trials) == 0
        assert len(self.trials._dynamic_trials) == 1

def test_status_fail_tpe():
    trials = Trials()

    argmin = fmin(
            fn=lambda x: ( {'loss': (x - 3) ** 2, 'status': STATUS_OK} if (x < 0) else
                           {'status': STATUS_FAIL}),
            space=hp.uniform('x', -5, 5),
            algo=tpe.suggest,
            max_evals=50,
            trials=trials)

    assert len(trials) == 50, len(trials)
    assert argmin['x'] < 0, argmin
    assert trials.best_trial['result'].has_key('loss'), trials.best_trial['result'].has_key('loss')
    assert trials.best_trial['result']['loss'] >= 9, trials.best_trial['result']['loss']


########NEW FILE########
__FILENAME__ = test_ipy
import sys
from nose import SkipTest
try:
    from IPython.parallel import Client
except ImportError:
    print >> sys.stderr, "Skipping IPython Tests (IPython not found)"
    raise SkipTest('IPython not present')

from hyperopt.ipy import IPythonTrials
import hyperopt.hp
import hyperopt.tpe
import hyperopt


def simple_objective(args):
    # -- why are these imports here !?
    # -- is it because they need to be imported on the client?
    import time
    import random
    return args ** 2

space = hyperopt.hp.uniform('x', 0, 1)


def test0():
    try:
        client = Client()
    except IOError:
        raise SkipTest()
    trials = IPythonTrials(client)

    minval = trials.fmin(simple_objective, space, hyperopt.tpe.suggest, 25)
    print minval
    assert minval['x'] < .2


def test_fmin_fn():
    try:
        client = Client()
    except IOError:
        raise SkipTest()
    trials = IPythonTrials(client)
    assert not trials._testing_fmin_was_called
    minval = hyperopt.fmin(simple_objective, space,
            algo=hyperopt.tpe.suggest,
            max_evals=25,
            trials=trials)

    assert minval['x'] < .2
    assert trials._testing_fmin_was_called


########NEW FILE########
__FILENAME__ = test_mongoexp
import cPickle
import os
import signal
import subprocess
import sys
import threading
import time
import unittest

import numpy as np
import nose
import nose.plugins.skip

from hyperopt.base import JOB_STATE_DONE
from hyperopt.mongoexp import MongoTrials
from hyperopt.mongoexp import MongoWorker
from hyperopt.mongoexp import ReserveTimeout
from hyperopt.mongoexp import as_mongo_str
from hyperopt.mongoexp import main_worker_helper
from hyperopt.mongoexp import MongoJobs
from hyperopt.fmin import fmin
from hyperopt import rand
import hyperopt.tests.test_base
from test_domains import gauss_wave2

def skiptest(f):
    def wrapper(*args, **kwargs):
        raise nose.plugins.skip.SkipTest()
    wrapper.__name__ = f.__name__
    return wrapper


class TempMongo(object):
    """
    Context manager for tests requiring a live database.

    with TempMongo() as foo:
        mj = foo.mongo_jobs('test1')
    """
    def __init__(self, workdir="/tmp/hyperopt_test"):
        self.workdir = workdir

    def __enter__(self):
        try:
            open(self.workdir)
            assert 0
        except IOError:
            subprocess.call(["mkdir", "-p", '%s/db' % self.workdir])
            proc_args = [ "mongod",
                        "--dbpath=%s/db" % self.workdir,
                        "--nojournal",
                         "--noprealloc",
                        "--port=22334"]
            #print "starting mongod", proc_args
            self.mongo_proc = subprocess.Popen(
                    proc_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.workdir, # this prevented mongod assertion fail 
                    )
            try:
                interval = .125
                while interval <= 2:
                    if interval > .125:
                        print "Waiting for mongo to come up"
                    time.sleep(interval)
                    interval *= 2
                    if  self.db_up():
                        break
                if self.db_up():
                    return self
                else:
                    try:
                        os.kill(self.mongo_proc.pid, signal.SIGTERM)
                    except OSError:
                        pass # if it crashed there is no such process
                    out, err = self.mongo_proc.communicate()
                    print >> sys.stderr, out
                    print >> sys.stderr, err
                    raise RuntimeError('No database connection', proc_args)
            except Exception, e:
                try:
                    os.kill(self.mongo_proc.pid, signal.SIGTERM)
                except OSError:
                    pass # if it crashed there is no such process
                raise e

    def __exit__(self, *args):
        #print 'CLEANING UP MONGO ...'
        os.kill(self.mongo_proc.pid, signal.SIGTERM)
        self.mongo_proc.wait()
        subprocess.call(["rm", "-Rf", self.workdir])
        #print 'CLEANING UP MONGO DONE'

    @staticmethod
    def connection_string(dbname):
        return as_mongo_str('localhost:22334/%s' % dbname) + '/jobs'

    @staticmethod
    def mongo_jobs(dbname):
        return MongoJobs.new_from_connection_str(
                TempMongo.connection_string(dbname))

    def db_up(self):
        try:
            self.mongo_jobs('__test_db')
            return True
        except:  # XXX: don't know what exceptions to put here
            return False

# -- If we can't create a TempMongo instance, then
#    simply print what happened, 
try:
    with TempMongo() as temp_mongo:
        pass
except OSError, e:
    print >> sys.stderr, e
    print >> sys.stderr, ("Failed to create a TempMongo context,"
        " skipping all mongo tests.")
    if "such file" in str(e):
        print >> sys.stderr, "Hint: is mongod executable on path?"
    raise nose.SkipTest()


class TestMongoTrials(hyperopt.tests.test_base.TestTrials):
    def setUp(self):
        self.temp_mongo = TempMongo()
        self.temp_mongo.__enter__()
        self.trials = MongoTrials(
                self.temp_mongo.connection_string('foo'),
                exp_key=None)

    def tearDown(self, *args):
        self.temp_mongo.__exit__(*args)


def with_mongo_trials(f, exp_key=None):
    def wrapper():
        with TempMongo() as temp_mongo:
            trials = MongoTrials(temp_mongo.connection_string('foo'),
                    exp_key=exp_key)
            print(len(trials.results))
            f(trials)
    wrapper.__name__ = f.__name__
    return wrapper


def _worker_thread_fn(host_id, n_jobs, timeout, dbname='foo', logfilename=None):
    mw = MongoWorker(
        mj=TempMongo.mongo_jobs(dbname),
        logfilename=logfilename)
    try:
        while n_jobs:
            mw.run_one(host_id, timeout, erase_created_workdir=True)
            print 'worker: %s ran job' % str(host_id)
            n_jobs -= 1
    except ReserveTimeout:
        print 'worker timed out:', host_id
        pass


def with_worker_threads(n_threads, dbname='foo',
        n_jobs=sys.maxint, timeout=10.0):
    """
    Decorator that will run a test with some MongoWorker threads in flight
    """
    def newth(ii):
        return threading.Thread(
                target=_worker_thread_fn,
                args=(('hostname', ii), n_jobs, timeout, dbname))
    def deco(f):
        def wrapper(*args, **kwargs):
            # --start some threads
            threads = map(newth, range(n_threads))
            [th.start() for th in threads]
            try:
                return f(*args, **kwargs)
            finally:
                [th.join() for th in threads]
        wrapper.__name__ = f.__name__ # -- nose requires test in name
        return wrapper
    return deco


@with_mongo_trials
def test_with_temp_mongo(trials):
    pass # -- just verify that the decorator can run


@with_mongo_trials
def test_new_trial_ids(trials):
    a = trials.new_trial_ids(1)
    b = trials.new_trial_ids(2)
    c = trials.new_trial_ids(3)

    assert len(a) == 1
    assert len(b) == 2
    assert len(c) == 3
    s = set()
    s.update(a)
    s.update(b)
    s.update(c)
    assert len(s) == 6


@with_mongo_trials
def test_attachments(trials):
    blob = 'abcde'
    assert 'aname' not in trials.attachments
    trials.attachments['aname'] = blob
    assert 'aname' in trials.attachments
    assert trials.attachments[u'aname'] == blob
    assert trials.attachments['aname'] == blob

    blob2 = 'zzz'
    trials.attachments['aname'] = blob2
    assert 'aname' in trials.attachments
    assert trials.attachments['aname'] == blob2
    assert trials.attachments[u'aname'] == blob2

    del trials.attachments['aname']
    assert 'aname' not in trials.attachments


@with_mongo_trials
def test_delete_all_on_attachments(trials):
    trials.attachments['aname'] = 'a'
    trials.attachments['aname2'] = 'b'
    assert 'aname2' in trials.attachments
    trials.delete_all()
    assert 'aname' not in trials.attachments
    assert 'aname2' not in trials.attachments


def test_handles_are_independent():
    with TempMongo() as tm:
        t1 = tm.mongo_jobs('t1')
        t2 = tm.mongo_jobs('t2')
        assert len(t1) == 0
        assert len(t2) == 0

        # test that inserting into t1 doesn't affect t2
        t1.insert({'a': 7})
        assert len(t1) == 1
        assert len(t2) == 0


def passthrough(x):
    return x


class TestExperimentWithThreads(unittest.TestCase):

    @staticmethod
    def worker_thread_fn(host_id, n_jobs, timeout):
        mw = MongoWorker(
            mj=TempMongo.mongo_jobs('foodb'),
            logfilename=None)
        while n_jobs:
            mw.run_one(host_id, timeout, erase_created_workdir=True)
            print('worker: %s ran job' % str(host_id))
            n_jobs -= 1

    @staticmethod
    def fmin_thread_fn(space, trials, max_evals, seed):
        fmin(
            fn=passthrough,
            space=space,
            algo=rand.suggest,
            trials=trials,
            rstate=np.random.RandomState(seed),
            max_evals=max_evals,
            return_argmin=False)

    def test_seeds_AAB(self):
        # launch 3 simultaneous experiments with seeds A, A, B.
        # Verify all experiments run to completion.
        # Verify first two experiments run identically.
        # Verify third experiment runs differently.

        exp_keys = ['A0', 'A1', 'B']
        seeds = [1, 1, 2]
        n_workers = 2
        jobs_per_thread = 6
        # -- total jobs = 2 * 6 = 12
        # -- divided by 3 experiments: 4 jobs per fmin
        max_evals = (n_workers * jobs_per_thread) // len(exp_keys)

        # -- should not matter which domain is used here
        domain = gauss_wave2()

        cPickle.dumps(domain.expr)
        cPickle.dumps(passthrough)


        worker_threads = [
            threading.Thread(
                target=TestExperimentWithThreads.worker_thread_fn,
                args=(('hostname', ii), jobs_per_thread, 30.0))
            for ii in range(n_workers)]

        with TempMongo() as tm:
            mj = tm.mongo_jobs('foodb')
            trials_list = [
                MongoTrials(tm.connection_string('foodb'), key)
                for key in exp_keys]

            fmin_threads = [
                threading.Thread(
                    target=TestExperimentWithThreads.fmin_thread_fn,
                    args=(domain.expr, trials, max_evals, seed))
                for seed, trials in zip(seeds, trials_list)]

            try:
                [th.start() for th in worker_threads + fmin_threads]
            finally:
                print('joining worker threads...')
                [th.join() for th in worker_threads + fmin_threads]

            # -- not using an exp_key gives a handle to all the trials
            #    in foodb
            all_trials = MongoTrials(tm.connection_string('foodb'))
            self.assertEqual(len(all_trials), n_workers * jobs_per_thread)

            # Verify that the fmin calls terminated correctly:
            for trials in trials_list:
                self.assertEqual(
                    trials.count_by_state_synced(JOB_STATE_DONE),
                    max_evals)
                self.assertEqual(
                    trials.count_by_state_unsynced(JOB_STATE_DONE),
                    max_evals)
                self.assertEqual(len(trials), max_evals)


            # Verify that the first two experiments match.
            # (Do these need sorting by trial id?)
            trials_A0, trials_A1, trials_B0 = trials_list
            self.assertEqual(
                [t['misc']['vals'] for t in trials_A0.trials],
                [t['misc']['vals'] for t in trials_A1.trials])

            # Verify that the last experiment does not match.
            # (Do these need sorting by trial id?)
            self.assertNotEqual(
                [t['misc']['vals'] for t in trials_A0.trials],
                [t['misc']['vals'] for t in trials_B0.trials])


class FakeOptions(object):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


# -- assert that the test raises a ReserveTimeout within 5 seconds
@nose.tools.timed(10.0)  #XXX:  this needs a suspiciously long timeout
@nose.tools.raises(ReserveTimeout)
@with_mongo_trials
def test_main_worker(trials):
    options = FakeOptions(
            max_jobs=1,
            # XXX: sync this with TempMongo
            mongo=as_mongo_str('localhost:22334/foodb'),
            reserve_timeout=1,
            poll_interval=.5,
            workdir=None,
            exp_key='foo',
            last_job_timeout=None,
            )
    # -- check that it runs
    #    and that the reserve timeout is respected
    main_worker_helper(options, ())


########NEW FILE########
__FILENAME__ = test_pchoice
from functools import partial
import numpy as np
import unittest
from hyperopt import hp, Trials, fmin, tpe, anneal, rand
import hyperopt.pyll.stochastic


class TestPChoice(unittest.TestCase):
    def test_basic(self):

        space = hp.pchoice('naive_type',
                [(.14, 'gaussian'),
                 (.02, 'multinomial'),
                 (.84, 'bernoulli')])
        a, b, c = 0, 0, 0
        rng = np.random.RandomState(123)
        for i in range(0, 1000):
            nesto = hyperopt.pyll.stochastic.sample(space, rng=rng)
            if nesto == 'gaussian':
                a += 1
            elif nesto == 'multinomial':
                b += 1
            elif nesto == 'bernoulli':
                c += 1
        print(a, b, c)
        assert a + b + c == 1000
        assert 120 < a < 160
        assert 0 < b < 40
        assert 800 < c < 900

    def test_basic2(self):
        space = hp.choice('normal_choice', [
            hp.pchoice('fsd',
                [(.1, 'first'),
                 (.8, 'second'),
                 (.1, 2)]),
            hp.choice('something_else', [10, 20])
        ])
        a, b, c = 0, 0, 0
        rng=np.random.RandomState(123)
        for i in range(0, 1000):
            nesto = hyperopt.pyll.stochastic.sample(space, rng=rng)
            if nesto == 'first':
                a += 1
            elif nesto == 'second':
                b += 1
            elif nesto == 2:
                c += 1
            elif nesto in (10, 20):
                pass
            else:
                assert 0, nesto
        print(a, b, c)
        assert b > 2 * a
        assert b > 2 * c

    def test_basic3(self):
        space = hp.pchoice('something', [
            (.2, hp.pchoice('number', [(.8, 2), (.2, 1)])),
            (.8, hp.pchoice('number1', [(.7, 5), (.3, 6)]))
        ])
        a, b, c, d = 0, 0, 0, 0
        rng = np.random.RandomState(123)
        for i in range(0, 2000):
            nesto = hyperopt.pyll.stochastic.sample(space, rng=rng)
            if nesto == 2:
                a += 1
            elif nesto == 1:
                b += 1
            elif nesto == 5:
                c += 1
            elif nesto == 6:
                d += 1
            else:
                assert 0, nesto
        print(a, b, c, d)
        assert a + b + c + d == 2000
        assert 300 < a + b < 500
        assert 1500 < c + d < 1700
        assert a * .3 > b  # a * 1.2 > 4 * b
        assert c * 3 * 1.2 > d * 7


class TestSimpleFMin(unittest.TestCase):
    # test that that a space with a pchoice in it is
    # (a) accepted by various algos and
    # (b) handled correctly.
    #
    def setUp(self):
        self.space = hp.pchoice('a', [
            (.1, 0), 
            (.2, 1),
            (.3, 2),
            (.4, 3)])
        self.trials = Trials()

    def objective(self, a):
        return [1, 1, 1, 0 ][a]

    def test_random(self):
        # test that that a space with a pchoice in it is
        # (a) accepted by tpe.suggest and
        # (b) handled correctly.
        N = 150
        fmin(self.objective,
            space=self.space,
            trials=self.trials,
            algo=rand.suggest,
            max_evals=N)

        a_vals = [t['misc']['vals']['a'][0] for t in self.trials.trials]
        counts = np.bincount(a_vals)
        print counts
        assert counts[3] > N * .35
        assert counts[3] < N * .60

    def test_tpe(self):
        N = 100
        fmin(self.objective,
            space=self.space,
            trials=self.trials,
            algo=partial(tpe.suggest, n_startup_jobs=10),
            max_evals=N)

        a_vals = [t['misc']['vals']['a'][0] for t in self.trials.trials]
        counts = np.bincount(a_vals)
        print counts
        assert counts[3] > N * .6

    def test_anneal(self):
        N = 100
        fmin(self.objective,
            space=self.space,
            trials=self.trials,
            algo=partial(anneal.suggest),
            max_evals=N)

        a_vals = [t['misc']['vals']['a'][0] for t in self.trials.trials]
        counts = np.bincount(a_vals)
        print counts
        assert counts[3] > N * .6

def test_bug1_rand():
    space = hp.choice('preprocess_choice', [
        {'pwhiten': hp.pchoice('whiten_randomPCA',
                               [(.3, False), (.7, True)])},
        {'palgo': False},
        {'pthree': 7}])
    best = fmin(fn=lambda x: 1,
                space=space,
                algo=rand.suggest,
                max_evals=50)

def test_bug1_tpe():
    space = hp.choice('preprocess_choice', [
        {'pwhiten': hp.pchoice('whiten_randomPCA',
                               [(.3, False), (.7, True)])},
        {'palgo': False},
        {'pthree': 7}])
    best = fmin(fn=lambda x: 1,
                space=space,
                algo=tpe.suggest,
                max_evals=50)

def test_bug1_anneal():
    space = hp.choice('preprocess_choice', [
        {'pwhiten': hp.pchoice('whiten_randomPCA',
                               [(.3, False), (.7, True)])},
        {'palgo': False},
        {'pthree': 7}])
    best = fmin(fn=lambda x: 1,
                space=space,
                algo=anneal.suggest,
                max_evals=50)


########NEW FILE########
__FILENAME__ = test_plotting
"""
Verify that the plotting routines can at least run.

If environment variable HYPEROPT_SHOW is defined and true,
then the plots actually appear.

"""
import unittest
import os

try:
    import matplotlib
    matplotlib.use('svg')  # -- prevents trying to connect to X server
except ImportError:
    import nose
    raise nose.SkipTest()

from hyperopt import Trials
import hyperopt.plotting
from hyperopt import rand, fmin
from test_domains import many_dists

def get_do_show():
    rval = int(os.getenv('HYPEROPT_SHOW', '0'))
    print 'do_show =', rval
    return rval

class TestPlotting(unittest.TestCase):
    def setUp(self):
        domain = self.domain = many_dists()
        trials = self.trials = Trials()
        fmin(lambda x: x,
            space=domain.expr,
            trials=trials,
            algo=rand.suggest,
            max_evals=200)

    def test_plot_history(self):
        hyperopt.plotting.main_plot_history(
                self.trials,
                do_show=get_do_show())

    def test_plot_histogram(self):
        hyperopt.plotting.main_plot_histogram(
                self.trials,
                do_show=get_do_show())

    def test_plot_vars(self):
        hyperopt.plotting.main_plot_vars(
                self.trials,
                self.domain,
                do_show=get_do_show())


########NEW FILE########
__FILENAME__ = test_pyll_utils

from hyperopt.pyll_utils import EQ
from hyperopt.pyll_utils import expr_to_config
from hyperopt import hp
from hyperopt.pyll import as_apply


def test_expr_to_config():

    z = hp.randint('z', 10)
    a = hp.choice('a',
                  [
                      hp.uniform('b', -1, 1) + z,
                      {'c': 1, 'd': hp.choice('d',
                                              [3 + hp.loguniform('c', 0, 1),
                                               1 + hp.loguniform('e', 0, 1)])
                      }])

    expr = as_apply((a, z))

    hps = {}
    expr_to_config(expr, (True,), hps)

    for label, dct in hps.items():
        print label
        print '  dist: %s(%s)' % (
            dct['node'].name,
            ', '.join(map(str, [ii.eval() for ii in dct['node'].inputs()])))
        if len(dct['conditions']) > 1:
            print '  conditions (OR):'
            for condseq in dct['conditions']:
                print '    ', ' AND '.join(map(str, condseq))
        elif dct['conditions']:
            for condseq in dct['conditions']:
                print '  conditions :', ' AND '.join(map(str, condseq))


    assert hps['a']['node'].name == 'randint'
    assert hps['b']['node'].name == 'uniform'
    assert hps['c']['node'].name == 'loguniform'
    assert hps['d']['node'].name == 'randint'
    assert hps['e']['node'].name == 'loguniform'
    assert hps['z']['node'].name == 'randint'

    assert set([(True, EQ('a', 0))]) == set([(True, EQ('a', 0))])
    assert hps['a']['conditions'] == set([(True,)])
    assert hps['b']['conditions'] == set([
        (True, EQ('a', 0))]), hps['b']['conditions']
    assert hps['c']['conditions'] == set([
        (True, EQ('a', 1), EQ('d', 0))])
    assert hps['d']['conditions'] == set([
        (True, EQ('a', 1))])
    assert hps['e']['conditions'] == set([
        (True, EQ('a', 1), EQ('d', 1))])
    assert hps['z']['conditions'] == set([
        (True,),
        (True, EQ('a', 0))])


def test_remove_allpaths():
    z = hp.uniform('z', 0, 10)
    a = hp.choice('a', [ z + 1, z - 1])
    hps = {}
    expr_to_config(a, (True,), hps)
    aconds = hps['a']['conditions']
    zconds = hps['z']['conditions']
    assert aconds == set([(True,)]), aconds
    assert zconds == set([(True,)]), zconds


########NEW FILE########
__FILENAME__ = test_rand
import unittest
from hyperopt.base import Trials, trials_from_docs, miscs_to_idxs_vals
from hyperopt import rand
from hyperopt.tests.test_base import Suggest_API
from test_domains import gauss_wave2, coin_flip

TestRand = Suggest_API.make_tst_class(rand.suggest, gauss_wave2(), 'TestRand')


class TestRand(unittest.TestCase):

    def test_seeding(self):
        # -- assert that the seeding works a particular way

        domain = coin_flip()
        docs = rand.suggest(range(10), domain, Trials(), seed=123)
        trials = trials_from_docs(docs)
        idxs, vals = miscs_to_idxs_vals(trials.miscs)

        # Passes Nov 8 / 2013 
        self.assertEqual(list(idxs['flip']), range(10))
        self.assertEqual(list(vals['flip']), [0, 1, 0, 0, 0, 0, 0, 1, 1, 0])

    # -- TODO: put in a test that guarantees that
    #          stochastic nodes are sampled in a paricular order.

########NEW FILE########
__FILENAME__ = test_rdists
from collections import defaultdict
import unittest
import numpy as np
import numpy.testing as npt
from hyperopt.rdists import (
    loguniform_gen,
    lognorm_gen,
    quniform_gen,
    qloguniform_gen,
    qnormal_gen,
    qlognormal_gen,
    )
from scipy import stats
try:
    from scipy.stats.tests.test_continuous_basic import (
        check_cdf_logcdf,
        check_pdf_logpdf,
        check_pdf,
        check_cdf_ppf,
        )
    from scipy.stats.tests import test_discrete_basic as tdb
except ImportError:

    def check_cdf_logcdf(*args):
        pass

    def check_pdf_logpdf(*args):
        pass

    def check_pdf(*args):
        pass
    
    def check_cdf_ppf(*args):
        pass


class TestLogUniform(unittest.TestCase):
    def test_cdf_logcdf(self):
        check_cdf_logcdf(loguniform_gen(0, 1), (0, 1), '')
        check_cdf_logcdf(loguniform_gen(0, 1), (-5, 5), '')

    def test_cdf_ppf(self):
        check_cdf_ppf(loguniform_gen(0, 1), (0, 1), '')
        check_cdf_ppf(loguniform_gen(-2, 1), (-5, 5), '')

    def test_pdf_logpdf(self):
        check_pdf_logpdf(loguniform_gen(0, 1), (0, 1), '')
        check_pdf_logpdf(loguniform_gen(low=-4, high=-0.5), (-2, 1), '')

    def test_pdf(self):
        check_pdf(loguniform_gen(0, 1), (0, 1), '')
        check_pdf(loguniform_gen(low=-4, high=-2), (-3, 2), '')

    def test_distribution_rvs(self):
        alpha = 0.01
        loc = 0
        scale = 1
        arg = (loc, scale)
        distfn = loguniform_gen(0, 1)
        D,pval = stats.kstest(distfn.rvs, distfn.cdf, args=arg, N=1000)
        if (pval < alpha):
            npt.assert_(pval > alpha,
                        "D = %f; pval = %f; alpha = %f; args=%s" % (
                            D, pval, alpha, arg))


class TestLogNormal(unittest.TestCase):
    def test_cdf_logcdf(self):
        check_cdf_logcdf(lognorm_gen(0, 1), (0, 1), '')
        check_cdf_logcdf(lognorm_gen(0, 1), (-5, 5), '')

    def test_cdf_ppf(self):
        check_cdf_ppf(lognorm_gen(0, 1), (0, 1), '')
        check_cdf_ppf(lognorm_gen(-2, 1), (-5, 5), '')

    def test_pdf_logpdf(self):
        check_pdf_logpdf(lognorm_gen(0, 1), (0, 1), '')
        check_pdf_logpdf(lognorm_gen(mu=-4, sigma=0.5), (-2, 1), '')

    def test_pdf(self):
        check_pdf(lognorm_gen(0, 1), (0, 1), '')
        check_pdf(lognorm_gen(mu=-4, sigma=2), (-3, 2), '')

    def test_distribution_rvs(self):
        return
        alpha = 0.01
        loc = 0
        scale = 1
        arg = (loc, scale)
        distfn = lognorm_gen(0, 1)
        D,pval = stats.kstest(distfn.rvs, distfn.cdf, args=arg, N=1000)
        if (pval < alpha):
            npt.assert_(pval > alpha,
                        "D = %f; pval = %f; alpha = %f; args=%s" % (
                            D, pval, alpha, arg))



def check_d_samples(dfn, n, rtol=1e-2, atol=1e-2):
    counts = defaultdict(lambda: 0)
    #print 'sample', dfn.rvs(size=n)
    inc = 1.0 / n
    for s in dfn.rvs(size=n):
        counts[s] += inc
    for ii, p in sorted(counts.items()):
        t = np.allclose(dfn.pmf(ii), p, rtol=rtol, atol=atol)
        if not t:
            print 'Error in sampling frequencies', ii
            print 'value\tpmf\tfreq'
            for jj in sorted(counts):
                print ('%.2f\t%.3f\t%.4f' % (
                    jj, dfn.pmf(jj), counts[jj]))
            npt.assert_(t,
                "n = %i; pmf = %f; p = %f" % (
                    n, dfn.pmf(ii), p))



class TestQUniform(unittest.TestCase):
    def test_smallq(self):
        low, high, q = (0, 1, .1)
        qu = quniform_gen(low, high, q)
        check_d_samples(qu, n=10000)

    def test_bigq(self):
        low, high, q = (-20, -1, 3)
        qu = quniform_gen(low, high, q)
        check_d_samples(qu, n=10000)

    def test_offgrid_int(self):
        qn = quniform_gen(0, 2, 2)
        assert qn.pmf(0) > 0.0
        assert qn.pmf(1) == 0.0
        assert qn.pmf(2) > 0.0
        assert qn.pmf(3) == 0.0
        assert qn.pmf(-1) == 0.0

    def test_offgrid_float(self):
        qn = quniform_gen(0, 1, .2)
        assert qn.pmf(0) > 0.0
        assert qn.pmf(.1) == 0.0
        assert qn.pmf(.2) > 0.0
        assert qn.pmf(.4) > 0.0
        assert qn.pmf(.8) > 0.0
        assert qn.pmf(-.2) == 0.0
        assert qn.pmf(.99) == 0.0
        assert qn.pmf(-.99) == 0.0


class TestQLogUniform(unittest.TestCase):
    def logp(self, x, low, high, q):
        return qloguniform_gen(low, high, q).logpmf(x)

    def test_smallq(self):
        low, high, q = (0, 1, .1)
        qlu = qloguniform_gen(low, high, q)
        check_d_samples(qlu, n=10000)

    def test_bigq(self):
        low, high, q = (-20, 4, 3)
        qlu = qloguniform_gen(low, high, q)
        check_d_samples(qlu, n=10000)

    def test_point(self):
        low, high, q = (np.log(.05), np.log(.15), 0.5)
        qlu = qloguniform_gen(low, high, q)
        check_d_samples(qlu, n=10000)

    def test_2points(self):
        low, high, q = (np.log(.05), np.log(.75), 0.5)
        qlu = qloguniform_gen(low, high, q)
        check_d_samples(qlu, n=10000)

    def test_point_logpmf(self):
        assert np.allclose(self.logp(0, np.log(.25), np.log(.5), 1), 0.0)

    def test_rounding_logpmf(self):
        assert (self.logp(0, np.log(.25), np.log(.75), 1)
                > self.logp(1, np.log(.25), np.log(.75), 1))
        assert (self.logp(-1, np.log(.25), np.log(.75), 1)
                == self.logp(2, np.log(.25), np.log(.75), 1)
                == -np.inf)

    def test_smallq_logpmf(self):
        assert (self.logp(0.2, np.log(.16), np.log(.55), .1)
                > self.logp(0.3, np.log(.16), np.log(.55), .1)
                > self.logp(0.4, np.log(.16), np.log(.55), .1)
                > self.logp(0.5, np.log(.16), np.log(.55), .1)
                > -10)

        assert (self.logp(0.1, np.log(.16), np.log(.55), 1)
                == self.logp(0.6, np.log(.16), np.log(.55), 1)
                == -np.inf)


class TestQNormal(unittest.TestCase):
    def test_smallq(self):
        mu, sigma, q = (0, 1, .1)
        qn = qnormal_gen(mu, sigma, q)
        check_d_samples(qn, n=10000)

    def test_bigq(self):
        mu, sigma, q = (-20, 4, 3)
        qn = qnormal_gen(mu, sigma, q)
        check_d_samples(qn, n=10000)

    def test_offgrid_int(self):
        qn = qnormal_gen(0, 1, 2)
        assert qn.pmf(0) > 0.0
        assert qn.pmf(1) == 0.0
        assert qn.pmf(2) > 0.0

    def test_offgrid_float(self):
        qn = qnormal_gen(0, 1, .2)
        assert qn.pmf(0) > 0.0
        assert qn.pmf(.1) == 0.0
        assert qn.pmf(.2) > 0.0
        assert qn.pmf(.4) > 0.0
        assert qn.pmf(-.2) > 0.0
        assert qn.pmf(-.4) > 0.0
        assert qn.pmf(.99) == 0.0
        assert qn.pmf(-.99) == 0.0

    def test_numeric(self):
        qn = qnormal_gen(0, 1, 1)
        assert qn.pmf(500) > -np.inf


class TestQLogNormal(unittest.TestCase):
    def test_smallq(self):
        mu, sigma, q = (0, 1, .1)
        qn = qlognormal_gen(mu, sigma, q)
        check_d_samples(qn, n=10000)

    def test_bigq(self):
        mu, sigma, q = (-20, 4, 3)
        qn = qlognormal_gen(mu, sigma, q)
        check_d_samples(qn, n=10000)

    def test_offgrid_int(self):
        mu, sigma, q = (1, 2, 2)
        qn = qlognormal_gen(mu, sigma, q)
        assert qn.pmf(0) > qn.pmf(2) > qn.pmf(20) > 0
        assert qn.pmf(1) == qn.pmf(2-.001) == qn.pmf(-1) == 0

    def test_offgrid_float(self):
        mu, sigma, q = (-.5, 2, .2)
        qn = qlognormal_gen(mu, sigma, q)
        assert qn.pmf(0) > qn.pmf(.2) > qn.pmf(2) > 0
        assert qn.pmf(.1) == qn.pmf(.2-.001) == qn.pmf(-.2) == 0

    def test_numeric(self):
        # XXX we don't have a numerically accurate computation for this guy
        #qn = qlognormal_gen(0, 1, 1)
        #assert -np.inf < qn.logpmf(1e-20) < -50
        #assert -np.inf < qn.logpmf(1e20) < -50
        pass
# -- non-empty last line for flake8

########NEW FILE########
__FILENAME__ = test_tpe
from functools import partial
import os
import unittest

import nose

import numpy as np
try:
    import matplotlib.pyplot as plt
except ImportError:
    pass

from hyperopt import pyll
from hyperopt.pyll import scope

from hyperopt import Trials

from hyperopt.base import miscs_to_idxs_vals, STATUS_OK

from hyperopt import hp

from hyperopt.tpe import adaptive_parzen_normal_orig
from hyperopt.tpe import GMM1
from hyperopt.tpe import GMM1_lpdf
from hyperopt.tpe import LGMM1
from hyperopt.tpe import LGMM1_lpdf

import hyperopt.rand as rand
import hyperopt.tpe as tpe
from hyperopt import fmin

from test_domains import (
    domain_constructor,
    CasePerDomain)

DO_SHOW = int(os.getenv('HYPEROPT_SHOW', '0'))


def passthrough(x):
    return x


def test_adaptive_parzen_normal_orig():
    rng = np.random.RandomState(123)

    prior_mu = 7
    prior_sigma = 2
    mus = rng.randn(10) + 5

    weights2, mus2, sigmas2 = adaptive_parzen_normal_orig(
            mus, 3.3, prior_mu, prior_sigma)

    print weights2
    print mus2
    print sigmas2

    assert len(weights2) == len(mus2) == len(sigmas2) == 11
    assert np.all(weights2[0] > weights2[1:])
    assert mus2[0] == 7
    assert np.all(mus2[1:] == mus)
    assert sigmas2[0] == 2


class TestGMM1(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.RandomState(234)

    def test_mu_is_used_correctly(self):
        assert np.allclose(10,
                GMM1([1], [10.0], [0.0000001], rng=self.rng))

    def test_sigma_is_used_correctly(self):
        samples = GMM1([1], [0.0], [10.0], size=[1000], rng=self.rng)
        assert 9 < np.std(samples) < 11

    def test_mus_make_variance(self):
        samples = GMM1([.5, .5], [0.0, 1.0], [0.000001, 0.000001],
                rng=self.rng, size=[1000])
        print samples.shape
        #import matplotlib.pyplot as plt
        #plt.hist(samples)
        #plt.show()
        assert .45 < np.mean(samples) < .55, np.mean(samples)
        assert .2 < np.var(samples) < .3, np.var(samples)

    def test_weights(self):
        samples = GMM1([.9999, .0001], [0.0, 1.0], [0.000001, 0.000001],
                rng=self.rng,
                size=[1000])
        assert samples.shape == (1000,)
        #import matplotlib.pyplot as plt
        #plt.hist(samples)
        #plt.show()
        assert -.001 < np.mean(samples) < .001, np.mean(samples)
        assert np.var(samples) < .0001, np.var(samples)

    def test_mat_output(self):
        samples = GMM1([.9999, .0001], [0.0, 1.0], [0.000001, 0.000001],
                rng=self.rng,
                size=[40, 20])
        assert samples.shape == (40, 20)
        assert -.001 < np.mean(samples) < .001, np.mean(samples)
        assert np.var(samples) < .0001, np.var(samples)

    def test_lpdf_scalar_one_component(self):
        llval = GMM1_lpdf(1.0,  # x
                [1.],           # weights
                [1.0],          # mu
                [2.0],          # sigma
                )
        assert llval.shape == ()
        assert np.allclose(llval,
                np.log(1.0 / np.sqrt(2 * np.pi * 2.0 ** 2)))

    def test_lpdf_scalar_N_components(self):
        llval = GMM1_lpdf(1.0,     # x
                [0.25, 0.25, .5],  # weights
                [0.0, 1.0, 2.0],   # mu
                [1.0, 2.0, 5.0],   # sigma
                )

        a = (.25 / np.sqrt(2 * np.pi * 1.0 ** 2)
                * np.exp(-.5 * (1.0) ** 2))
        a += (.25 / np.sqrt(2 * np.pi * 2.0 ** 2))
        a += (.5 / np.sqrt(2 * np.pi * 5.0 ** 2)
                * np.exp(-.5 * (1.0 / 5.0) ** 2))

    def test_lpdf_vector_N_components(self):
        llval = GMM1_lpdf([1.0, 0.0],     # x
                [0.25, 0.25, .5],         # weights
                [0.0, 1.0, 2.0],          # mu
                [1.0, 2.0, 5.0],          # sigma
                )

        # case x = 1.0
        a = (.25 / np.sqrt(2 * np.pi * 1.0 ** 2)
                * np.exp(-.5 * (1.0) ** 2))
        a += (.25 / np.sqrt(2 * np.pi * 2.0 ** 2))
        a += (.5 / np.sqrt(2 * np.pi * 5.0 ** 2)
                * np.exp(-.5 * (1.0 / 5.0) ** 2))

        assert llval.shape == (2,)
        assert np.allclose(llval[0], np.log(a))

        # case x = 0.0
        a = (.25 / np.sqrt(2 * np.pi * 1.0 ** 2))
        a += (.25 / np.sqrt(2 * np.pi * 2.0 ** 2)
                * np.exp(-.5 * (1.0 / 2.0) ** 2))
        a += (.5 / np.sqrt(2 * np.pi * 5.0 ** 2)
                * np.exp(-.5 * (2.0 / 5.0) ** 2))
        assert np.allclose(llval[1], np.log(a))

    def test_lpdf_matrix_N_components(self):
        llval = GMM1_lpdf(
                [
                    [1.0, 0.0, 0.0],
                    [0, 0, 1],
                    [0, 0, 1000],
                ],
                [0.25, 0.25, .5],  # weights
                [0.0, 1.0, 2.0],   # mu
                [1.0, 2.0, 5.0],   # sigma
                )
        print llval
        assert llval.shape == (3, 3)

        a = (.25 / np.sqrt(2 * np.pi * 1.0 ** 2)
                * np.exp(-.5 * (1.0) ** 2))
        a += (.25 / np.sqrt(2 * np.pi * 2.0 ** 2))
        a += (.5 / np.sqrt(2 * np.pi * 5.0 ** 2)
                * np.exp(-.5 * (1.0 / 5.0) ** 2))

        assert np.allclose(llval[0, 0], np.log(a))
        assert np.allclose(llval[1, 2], np.log(a))

        # case x = 0.0
        a = (.25 / np.sqrt(2 * np.pi * 1.0 ** 2))
        a += (.25 / np.sqrt(2 * np.pi * 2.0 ** 2)
                * np.exp(-.5 * (1.0 / 2.0) ** 2))
        a += (.5 / np.sqrt(2 * np.pi * 5.0 ** 2)
                * np.exp(-.5 * (2.0 / 5.0) ** 2))

        assert np.allclose(llval[0, 1], np.log(a))
        assert np.allclose(llval[0, 2], np.log(a))
        assert np.allclose(llval[1, 0], np.log(a))
        assert np.allclose(llval[1, 1], np.log(a))
        assert np.allclose(llval[2, 0], np.log(a))
        assert np.allclose(llval[2, 1], np.log(a))

        assert np.isfinite(llval[2, 2])


class TestGMM1Math(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.RandomState(234)
        self.weights = [.1, .3, .4, .2]
        self.mus = [1.0, 2.0, 3.0, 4.0]
        self.sigmas = [.1, .4, .8, 2.0]
        self.q = None
        self.low = None
        self.high = None
        self.n_samples = 10001
        self.samples_per_bin = 500
        self.show = False
        # -- triggers error if test case forgets to call work()
        self.worked = False

    def tearDown(self):
        assert self.worked

    def work(self):
        self.worked = True
        kwargs = dict(
                weights=self.weights,
                mus=self.mus,
                sigmas=self.sigmas,
                low=self.low,
                high=self.high,
                q=self.q,
                )
        samples = GMM1(rng=self.rng,
                size=(self.n_samples,),
                **kwargs)
        samples = np.sort(samples)
        edges = samples[::self.samples_per_bin]
        #print samples

        pdf = np.exp(GMM1_lpdf(edges[:-1], **kwargs))
        dx = edges[1:] - edges[:-1]
        y = 1 / dx / len(dx)

        if self.show:
            plt.scatter(edges[:-1], y)
            plt.plot(edges[:-1], pdf)
            plt.show()
        err = (pdf - y) ** 2
        print np.max(err)
        print np.mean(err)
        print np.median(err)
        if not self.show:
            assert np.max(err) < .1
            assert np.mean(err) < .01
            assert np.median(err) < .01

    def test_basic(self):
        self.work()

    def test_bounded(self):
        self.low = 2.5
        self.high = 3.5
        self.work()


class TestQGMM1Math(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.RandomState(234)
        self.weights = [.1, .3, .4, .2]
        self.mus = [1.0, 2.0, 3.0, 4.0]
        self.sigmas = [.1, .4, .8, 2.0]
        self.low = None
        self.high = None
        self.n_samples = 1001
        self.show = DO_SHOW  # or put a string
        # -- triggers error if test case forgets to call work()
        self.worked = False

    def tearDown(self):
        assert self.worked

    def work(self, **kwargs):
        self.__dict__.update(kwargs)
        del kwargs
        self.worked = True
        gkwargs = dict(
                weights=self.weights,
                mus=self.mus,
                sigmas=self.sigmas,
                low=self.low,
                high=self.high,
                q=self.q,
                )
        samples = GMM1(rng=self.rng,
                size=(self.n_samples,),
                **gkwargs) / self.q
        print 'drew', len(samples), 'samples'
        assert np.all(samples == samples.astype('int'))
        min_max = int(samples.min()), int(samples.max())
        counts = np.bincount(samples.astype('int') - min_max[0])

        print counts
        xcoords = np.arange(min_max[0], min_max[1] + 1) * self.q
        prob = np.exp(GMM1_lpdf(xcoords, **gkwargs))
        assert counts.sum() == self.n_samples
        y = counts / float(self.n_samples)

        if self.show:
            plt.scatter(xcoords, y, c='r', label='empirical')
            plt.scatter(xcoords, prob, c='b', label='predicted')
            plt.legend()
            plt.title(str(self.show))
            plt.show()
        err = (prob - y) ** 2
        print np.max(err)
        print np.mean(err)
        print np.median(err)
        if self.show:
            raise nose.SkipTest()
        else:
            assert np.max(err) < .1
            assert np.mean(err) < .01
            assert np.median(err) < .01

    def test_basic_1(self):
        self.work(q=1)

    def test_basic_2(self):
        self.work(q=2)

    def test_basic_pt5(self):
        self.work(q=0.5)

    def test_bounded_1(self):
        self.work(q=1, low=2, high=4)

    def test_bounded_2(self):
        self.work(q=2, low=2, high=4)

    def test_bounded_1b(self):
        self.work(q=1, low=1, high=4.1)

    def test_bounded_2b(self):
        self.work(q=2, low=1, high=4.1)

    def test_bounded_3(self):
        self.work(
                weights=[0.14285714, 0.28571429, 0.28571429, 0.28571429],
                mus=[5.505, 7., 2., 10.],
                sigmas=[8.99, 5., 8., 8.],
                q=1,
                low=1.01,
                high=10,
                n_samples=10000,
                #show='bounded_3',
                )

    def test_bounded_3b(self):
        self.work(
                weights=[0.33333333,  0.66666667],
                mus=[5.505, 5.],
                sigmas=[8.99, 5.19],
                q=1,
                low=1.01,
                high=10,
                n_samples=10000,
                #show='bounded_3b',
                )


class TestLGMM1Math(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.RandomState(234)
        self.weights = [.1, .3, .4, .2]
        self.mus = [-2.0, 1.0, 0.0, 3.0]
        self.sigmas = [.1, .4, .8, 2.0]
        self.low = None
        self.high = None
        self.n_samples = 10001
        self.samples_per_bin = 200
        self.show = False
        # -- triggers error if test case forgets to call work()
        self.worked = False

    def tearDown(self):
        assert self.worked

    @property
    def LGMM1_kwargs(self):
        return dict(
                weights=self.weights,
                mus=self.mus,
                sigmas=self.sigmas,
                low=self.low,
                high=self.high,
                )

    def LGMM1_lpdf(self, samples):
        return self.LGMM1(samples, **self.LGMM1_kwargs)

    def work(self, **kwargs):
        self.__dict__.update(kwargs)
        self.worked = True
        samples = LGMM1(rng=self.rng,
                size=(self.n_samples,),
                **self.LGMM1_kwargs)
        samples = np.sort(samples)
        edges = samples[::self.samples_per_bin]
        centers = .5 * edges[:-1] + .5 * edges[1:]
        print edges

        pdf = np.exp(LGMM1_lpdf(centers, **self.LGMM1_kwargs))
        dx = edges[1:] - edges[:-1]
        y = 1 / dx / len(dx)

        if self.show:
            plt.scatter(centers, y)
            plt.plot(centers, pdf)
            plt.show()
        err = (pdf - y) ** 2
        print np.max(err)
        print np.mean(err)
        print np.median(err)
        if not self.show:
            assert np.max(err) < .1
            assert np.mean(err) < .01
            assert np.median(err) < .01

    def test_basic(self):
        self.work()

    def test_bounded(self):
        self.work(low=2, high=4)


class TestQLGMM1Math(unittest.TestCase):
    def setUp(self):
        self.rng = np.random.RandomState(234)
        self.weights = [.1, .3, .4, .2]
        self.mus = [-2, 0.0, -3.0, 1.0]
        self.sigmas = [2.1, .4, .8, 2.1]
        self.low = None
        self.high = None
        self.n_samples = 1001
        self.show = DO_SHOW
        # -- triggers error if test case forgets to call work()
        self.worked = False

    def tearDown(self):
        assert self.worked

    @property
    def kwargs(self):
        return dict(
                weights=self.weights,
                mus=self.mus,
                sigmas=self.sigmas,
                low=self.low,
                high=self.high,
                q=self.q)

    def QLGMM1_lpdf(self, samples):
        return self.LGMM1(samples, **self.kwargs)

    def work(self, **kwargs):
        self.__dict__.update(kwargs)
        self.worked = True
        samples = LGMM1(rng=self.rng,
                size=(self.n_samples,),
                **self.kwargs) / self.q
        # -- we've divided the LGMM1 by self.q to get ints here
        assert np.all(samples == samples.astype('int'))
        min_max = int(samples.min()), int(samples.max())
        print 'SAMPLES RANGE', min_max
        counts = np.bincount(samples.astype('int') - min_max[0])

        #print samples
        #print counts
        xcoords = np.arange(min_max[0], min_max[1] + 0.5) * self.q
        prob = np.exp(LGMM1_lpdf(xcoords, **self.kwargs))
        print xcoords
        print prob
        assert counts.sum() == self.n_samples
        y = counts / float(self.n_samples)

        if self.show:
            plt.scatter(xcoords, y, c='r', label='empirical')
            plt.scatter(xcoords, prob, c='b', label='predicted')
            plt.legend()
            plt.show()
        # -- calculate errors on the low end, don't take a mean
        #    over all the range spanned by a few outliers.
        err = ((prob - y) ** 2)[:20]
        print np.max(err)
        print np.mean(err)
        print np.median(err)
        if self.show:
            raise nose.SkipTest()
        else:
            assert np.max(err) < .1
            assert np.mean(err) < .01
            assert np.median(err) < .01

    def test_basic_1(self):
        self.work(q=1)

    def test_basic_2(self):
        self.work(q=2)

    def test_basic_pt5(self):
        self.work(q=0.5)

    def test_basic_pt125(self):
        self.work(q=0.125)

    def test_bounded_1(self):
        self.work(q=1, low=2, high=4)

    def test_bounded_2(self):
        self.work(q=2, low=2, high=4)

    def test_bounded_1b(self):
        self.work(q=1, low=1, high=4.1)

    def test_bounded_2b(self):
        self.work(q=2, low=1, high=4.1)


class TestSuggest(unittest.TestCase, CasePerDomain):
    def work(self):
        # -- smoke test that things simply run,
        #    for each type of several search spaces.
        trials = Trials()
        fmin(passthrough,
            space=self.bandit.expr,
            algo=partial(tpe.suggest, n_EI_candidates=3),
            trials=trials,
            max_evals=10)


class TestOpt(unittest.TestCase, CasePerDomain):
    thresholds = dict(
            quadratic1=1e-5,
            q1_lognormal=0.01,
            distractor=-1.96,
            gauss_wave=-2.0,
            gauss_wave2=-2.0,
            n_arms=-2.5,
            many_dists=.0005,
            branin=0.7,
            )

    LEN = dict(
            # -- running a long way out tests overflow/underflow
            #    to some extent
            quadratic1=1000,
            many_dists=200,
            distractor=100,
            #XXX
            q1_lognormal=250,
            gauss_wave2=75, # -- boosted from 50 on Nov/2013 after new
                            #  sampling order made thresh test fail.
            branin=200,
            )

    gammas = dict(
            distractor=.05,
            )

    prior_weights = dict(
            distractor=.01,
            )

    n_EIs = dict(
            #XXX
            # -- this can be low in a few dimensions
            quadratic1=5,
            # -- lower number encourages exploration
            # XXX: this is a damned finicky way to get TPE
            #      to solve the Distractor problem
            distractor=15,
            )

    def setUp(self):
        self.olderr = np.seterr('raise')
        np.seterr(under='ignore')

    def tearDown(self, *args):
        np.seterr(**self.olderr)

    def work(self):

        bandit = self.bandit
        assert bandit.name is not None
        algo = partial(tpe.suggest,
                gamma=self.gammas.get(bandit.name,
                    tpe._default_gamma),
                prior_weight=self.prior_weights.get(bandit.name,
                    tpe._default_prior_weight),
                n_EI_candidates=self.n_EIs.get(bandit.name,
                    tpe._default_n_EI_candidates),
                )
        LEN = self.LEN.get(bandit.name, 50)

        trials = Trials()
        fmin(passthrough,
            space=bandit.expr,
            algo=algo,
            trials=trials,
            max_evals=LEN,
            rstate=np.random.RandomState(123),
            catch_eval_exceptions=False)
        assert len(trials) == LEN

        if 1:
            rtrials = Trials()
            fmin(passthrough,
                space=bandit.expr,
                algo=rand.suggest,
                trials=rtrials,
                max_evals=LEN)
            print 'RANDOM MINS', list(sorted(rtrials.losses()))[:6]
            #logx = np.log([s['x'] for s in rtrials.specs])
            #print 'RND MEAN', np.mean(logx)
            #print 'RND STD ', np.std(logx)

        if 0:
            plt.subplot(2, 2, 1)
            plt.scatter(range(LEN), trials.losses())
            plt.title('TPE losses')
            plt.subplot(2, 2, 2)
            plt.scatter(range(LEN), ([s['x'] for s in trials.specs]))
            plt.title('TPE x')
            plt.subplot(2, 2, 3)
            plt.title('RND losses')
            plt.scatter(range(LEN), rtrials.losses())
            plt.subplot(2, 2, 4)
            plt.title('RND x')
            plt.scatter(range(LEN), ([s['x'] for s in rtrials.specs]))
            plt.show()
        if 0:
            plt.hist(
                    [t['x'] for t in self.experiment.trials],
                    bins=20)

        #print trials.losses()
        print 'TPE    MINS', list(sorted(trials.losses()))[:6]
        #logx = np.log([s['x'] for s in trials.specs])
        #print 'TPE MEAN', np.mean(logx)
        #print 'TPE STD ', np.std(logx)
        thresh = self.thresholds[bandit.name]
        print 'Thresh', thresh
        assert min(trials.losses()) < thresh


@domain_constructor(loss_target=0)
def opt_q_uniform(target):
    rng = np.random.RandomState(123)
    x = hp.quniform('x', 1.01, 10, 1)
    return {'loss': (x - target) ** 2 + scope.normal(0, 1, rng=rng),
            'status': STATUS_OK}


class TestOptQUniform():

    show_steps = False
    show_vars = DO_SHOW
    LEN = 25

    def work(self, **kwargs):
        self.__dict__.update(kwargs)
        bandit = opt_q_uniform(self.target)
        prior_weight = 2.5
        gamma = 0.20
        algo = partial(tpe.suggest,
                prior_weight=prior_weight,
                n_startup_jobs=2,
                n_EI_candidates=128,
                gamma=gamma)
        #print algo.opt_idxs['x']
        #print algo.opt_vals['x']

        trials = Trials()
        fmin(passthrough,
            space=bandit.expr,
            algo=algo,
            trials=trials,
            max_evals=self.LEN)
        if self.show_vars:
            import hyperopt.plotting
            hyperopt.plotting.main_plot_vars(trials, bandit, do_show=1)

        idxs, vals = miscs_to_idxs_vals(trials.miscs)
        idxs = idxs['x']
        vals = vals['x']

        losses = trials.losses()

        from hyperopt.tpe import ap_filter_trials
        from hyperopt.tpe import adaptive_parzen_samplers

        qu = scope.quniform(1.01, 10, 1)
        fn = adaptive_parzen_samplers['quniform']
        fn_kwargs = dict(size=(4,), rng=np.random)
        s_below = pyll.Literal()
        s_above = pyll.Literal()
        b_args = [s_below, prior_weight] + qu.pos_args
        b_post = fn(*b_args, **fn_kwargs)
        a_args = [s_above, prior_weight] + qu.pos_args
        a_post = fn(*a_args, **fn_kwargs)

        #print b_post
        #print a_post
        fn_lpdf = getattr(scope, a_post.name + '_lpdf')
        print fn_lpdf
        # calculate the llik of b_post under both distributions
        a_kwargs = dict([(n, a) for n, a in a_post.named_args
                    if n not in ('rng', 'size')])
        b_kwargs = dict([(n, a) for n, a in b_post.named_args
                    if n not in ('rng', 'size')])
        below_llik = fn_lpdf(*([b_post] + b_post.pos_args), **b_kwargs)
        above_llik = fn_lpdf(*([b_post] + a_post.pos_args), **a_kwargs)
        new_node = scope.broadcast_best(b_post, below_llik, above_llik)

        print '=' * 80

        do_show = self.show_steps

        for ii in range(2, 9):
            if ii > len(idxs):
                break
            print '-' * 80
            print 'ROUND', ii
            print '-' * 80
            all_vals = [2, 3, 4, 5, 6, 7, 8, 9, 10]
            below, above = ap_filter_trials(idxs[:ii],
                    vals[:ii], idxs[:ii], losses[:ii], gamma)
            below = below.astype('int')
            above = above.astype('int')
            print 'BB0', below
            print 'BB1', above
            #print 'BELOW',  zip(range(100), np.bincount(below, minlength=11))
            #print 'ABOVE',  zip(range(100), np.bincount(above, minlength=11))
            memo = {b_post: all_vals, s_below: below, s_above: above}
            bl, al, nv = pyll.rec_eval([below_llik, above_llik, new_node],
                    memo=memo)
            #print bl - al
            print 'BB2', dict(zip(all_vals, bl - al))
            print 'BB3', dict(zip(all_vals, bl))
            print 'BB4', dict(zip(all_vals, al))
            print 'ORIG PICKED', vals[ii]
            print 'PROPER OPT PICKS:', nv

            #assert np.allclose(below, [3, 3, 9])
            #assert len(below) + len(above) == len(vals)

            if do_show:
                plt.subplot(8, 1, ii)
                #plt.scatter(all_vals,
                #    np.bincount(below, minlength=11)[2:], c='b')
                #plt.scatter(all_vals,
                #    np.bincount(above, minlength=11)[2:], c='c')
                plt.scatter(all_vals, bl, c='g')
                plt.scatter(all_vals, al, c='r')
        if do_show:
            plt.show()

    def test4(self):
        self.work(target=4, LEN=100)

    def test2(self):
        self.work(target=2, LEN=100)

    def test6(self):
        self.work(target=6, LEN=100)

    def test10(self):
        self.work(target=10, LEN=100)


########NEW FILE########
__FILENAME__ = test_utils
import numpy as np
from hyperopt.utils import fast_isin
from hyperopt.utils import get_most_recent_inds


def test_fast_isin():
    Y = np.random.randint(0, 10000, size=(100, ))
    X = np.arange(10000)
    Z = fast_isin(X, Y)
    D = np.unique(Y)
    D.sort()
    T1 = (X[Z] == D).all()

    X = np.array(range(10000) + range(10000))
    Z = fast_isin(X, Y)
    T2 = (X[Z] == np.append(D, D.copy())).all()

    X = np.random.randint(0, 100, size = (40, ))
    X.sort()
    Y = np.random.randint(0, 100, size = (60, ))
    Y.sort()

    XinY = np.array([ind for ind in range(len(X)) if X[ind] in Y])
    YinX = np.array([ind for ind in range(len(Y)) if Y[ind] in X])

    T3 = (fast_isin(X, Y).nonzero()[0] == XinY).all()
    T4 = (fast_isin(Y, X).nonzero()[0] == YinX).all()

    assert T1 & T2 & T3 & T4


def test_get_most_recent_inds():
    test_data = []
    most_recent_data = []
    for ind in range(300):
        k = np.random.randint(1,6)
        for _ind in range(k):
            test_data.append({'_id': ind, 'version':_ind})
        most_recent_data.append({'_id': ind, 'version': _ind})
    rng = np.random.RandomState(0)
    p = rng.permutation(len(test_data))
    test_data_rearranged = [test_data[_p] for _p in p]
    rind = get_most_recent_inds(test_data_rearranged)
    test_data_rearranged_most_recent = [test_data_rearranged[idx] for idx in rind]
    assert all([t in most_recent_data for t in test_data_rearranged_most_recent])
    assert len(test_data_rearranged_most_recent) == len(most_recent_data)

    test_data = [{'_id':0, 'version':1}]
    
    assert get_most_recent_inds(test_data).tolist() == [0]
    
    test_data = [{'_id':0, 'version':1}, {'_id':0, 'version':2}]
    assert get_most_recent_inds(test_data).tolist() == [1]
    
    test_data = [{'_id':0, 'version':1}, {'_id':0, 'version':2},
                 {'_id':1, 'version':1}]
    
    assert get_most_recent_inds(test_data).tolist() == [1, 2]
    
    test_data = [{'_id': -1, 'version':1}, {'_id':0, 'version':1},
                 {'_id':0, 'version':2}, {'_id':1, 'version':1}]
    
    assert get_most_recent_inds(test_data).tolist() == [0, 2, 3]
    
    test_data = [{'_id': -1, 'version':1}, {'_id':0, 'version':1},
                 {'_id':0, 'version':2}, {'_id':0, 'version':2}]
    
    assert get_most_recent_inds(test_data).tolist() == [0, 3]
########NEW FILE########
__FILENAME__ = test_vectorize
import numpy as np

from hyperopt.pyll import as_apply, scope, rec_eval, clone, dfs
from hyperopt.pyll.stochastic import recursive_set_rng_kwarg

from hyperopt import base, fmin, rand
from hyperopt.vectorize import VectorizeHelper
from hyperopt.vectorize import replace_repeat_stochastic
from hyperopt.pyll_utils import hp_choice
from hyperopt.pyll_utils import hp_uniform
from hyperopt.pyll_utils import hp_quniform
from hyperopt.pyll_utils import hp_loguniform
from hyperopt.pyll_utils import hp_qloguniform


def config0():
    p0 = scope.uniform(0, 1)
    p1 = scope.uniform(2, 3)
    p2 = scope.one_of(-1, p0)
    p3 = scope.one_of(-2, p1)
    p4 = 1
    p5 = [3, 4, p0]
    p6 = scope.one_of(-3, p1)
    d = locals()
    d['p1'] = None # -- don't sample p1 all the time, only if p3 says so
    s = as_apply(d)
    return s


def test_clone():
    config = config0()
    config2 = clone(config)

    nodeset = set(dfs(config))
    assert not any(n in nodeset for n in dfs(config2))

    foo = recursive_set_rng_kwarg(
                config,
                scope.rng_from_seed(5))
    r = rec_eval(foo)
    print r
    r2 = rec_eval(
            recursive_set_rng_kwarg(
                config2,
                scope.rng_from_seed(5)))

    print r2
    assert r == r2


def test_vectorize_trivial():
    N = as_apply(15)

    p0 = hp_uniform('p0', 0, 1)
    loss = p0
    print loss
    expr_idxs = scope.range(N)
    vh = VectorizeHelper(loss, expr_idxs, build=True)
    vloss = vh.v_expr

    full_output = as_apply([vloss,
        vh.idxs_by_label(),
        vh.vals_by_label()])
    fo2 = replace_repeat_stochastic(full_output)

    new_vc = recursive_set_rng_kwarg(
            fo2,
            as_apply(np.random.RandomState(1)),
            )

    #print new_vc
    losses, idxs, vals = rec_eval(new_vc)
    print 'losses', losses
    print 'idxs p0', idxs['p0']
    print 'vals p0', vals['p0']
    p0dct = dict(zip(idxs['p0'], vals['p0']))
    for ii, li in enumerate(losses):
        assert p0dct[ii] == li


def test_vectorize_simple():
    N = as_apply(15)

    p0 = hp_uniform('p0', 0, 1)
    loss = p0 ** 2
    print loss
    expr_idxs = scope.range(N)
    vh = VectorizeHelper(loss, expr_idxs, build=True)
    vloss = vh.v_expr

    full_output = as_apply([vloss,
        vh.idxs_by_label(),
        vh.vals_by_label()])
    fo2 = replace_repeat_stochastic(full_output)

    new_vc = recursive_set_rng_kwarg(
            fo2,
            as_apply(np.random.RandomState(1)),
            )

    #print new_vc
    losses, idxs, vals = rec_eval(new_vc)
    print 'losses', losses
    print 'idxs p0', idxs['p0']
    print 'vals p0', vals['p0']
    p0dct = dict(zip(idxs['p0'], vals['p0']))
    for ii, li in enumerate(losses):
        assert p0dct[ii] ** 2 == li


def test_vectorize_multipath():
    N = as_apply(15)

    p0 = hp_uniform('p0', 0, 1)
    loss = hp_choice('p1', [1, p0, -p0]) ** 2
    expr_idxs = scope.range(N)
    vh = VectorizeHelper(loss, expr_idxs, build=True)

    vloss = vh.v_expr
    print vloss

    full_output = as_apply([vloss,
        vh.idxs_by_label(),
        vh.vals_by_label()])

    new_vc = recursive_set_rng_kwarg(
            full_output,
            as_apply(np.random.RandomState(1)),
            )

    losses, idxs, vals = rec_eval(new_vc)
    print 'losses', losses
    print 'idxs p0', idxs['p0']
    print 'vals p0', vals['p0']
    print 'idxs p1', idxs['p1']
    print 'vals p1', vals['p1']
    p0dct = dict(zip(idxs['p0'], vals['p0']))
    p1dct = dict(zip(idxs['p1'], vals['p1']))
    for ii, li in enumerate(losses):
        print ii, li
        if p1dct[ii] != 0:
            assert li == p0dct[ii] ** 2
        else:
            assert li == 1


def test_vectorize_config0():
    p0 = hp_uniform('p0', 0, 1)
    p1 = hp_loguniform('p1', 2, 3)
    p2 = hp_choice('p2', [-1, p0])
    p3 = hp_choice('p3', [-2, p1])
    p4 = 1
    p5 = [3, 4, p0]
    p6 = hp_choice('p6', [-3, p1])
    d = locals()
    d['p1'] = None # -- don't sample p1 all the time, only if p3 says so
    config = as_apply(d)

    N = as_apply('N:TBA')
    expr = config
    expr_idxs = scope.range(N)
    vh = VectorizeHelper(expr, expr_idxs, build=True)
    vconfig = vh.v_expr

    full_output = as_apply([vconfig, vh.idxs_by_label(), vh.vals_by_label()])

    if 1:
        print '=' * 80
        print 'VECTORIZED'
        print full_output
        print '\n' * 1

    fo2 = replace_repeat_stochastic(full_output)
    if 0:
        print '=' * 80
        print 'VECTORIZED STOCHASTIC'
        print fo2
        print '\n' * 1

    new_vc = recursive_set_rng_kwarg(
            fo2,
            as_apply(np.random.RandomState(1))
            )
    if 0:
        print '=' * 80
        print 'VECTORIZED STOCHASTIC WITH RNGS'
        print new_vc

    Nval = 10
    foo, idxs, vals = rec_eval(new_vc, memo={N: Nval})

    print 'foo[0]', foo[0]
    print 'foo[1]', foo[1]
    assert len(foo) == Nval
    if 0:  # XXX refresh these values to lock down sampler
        assert foo[0] == {
            'p0': 0.39676747423066994,
            'p1': None,
            'p2': 0.39676747423066994,
            'p3': 2.1281244479293568,
            'p4': 1,
            'p5': (3, 4, 0.39676747423066994) }
    assert foo[1] != foo[2]

    print idxs
    print vals['p3']
    print vals['p6']
    print idxs['p1']
    print vals['p1']
    assert len(vals['p3']) == Nval
    assert len(vals['p6']) == Nval
    assert len(idxs['p1']) < Nval
    p1d = dict(zip(idxs['p1'], vals['p1']))
    for ii, (p3v, p6v) in enumerate(zip(vals['p3'], vals['p6'])):
        if p3v == p6v == 0:
            assert ii not in idxs['p1']
        if p3v:
            assert foo[ii]['p3'] == p1d[ii]
        if p6v:
            print 'p6', foo[ii]['p6'], p1d[ii]
            assert foo[ii]['p6'] == p1d[ii]


def test_distributions():
    # test that the distributions come out right

    # XXX: test more distributions
    space = {
        'loss': (
            hp_loguniform('lu', -2, 2) +
            hp_qloguniform('qlu', np.log(1 + 0.01), np.log(20), 2) +
            hp_quniform('qu', -4.999, 5, 1) +
            hp_uniform('u', 0, 10)),
        'status': 'ok'}
    trials = base.Trials()
    N = 1000
    fmin(lambda x: x,
        space=space,
        algo=rand.suggest,
        trials=trials,
        max_evals=N,
        rstate=np.random.RandomState(124),
        catch_eval_exceptions=False)
    assert len(trials) == N
    idxs, vals = base.miscs_to_idxs_vals(trials.miscs)
    print idxs.keys()

    COUNTMAX = 130
    COUNTMIN = 70

    # -- loguniform
    log_lu = np.log(vals['lu'])
    assert len(log_lu) == N
    assert -2 < np.min(log_lu)
    assert np.max(log_lu) < 2
    h = np.histogram(log_lu)[0]
    print h
    assert np.all(COUNTMIN < h)
    assert np.all(h < COUNTMAX)

    # -- quantized log uniform
    qlu = vals['qlu']
    assert np.all(np.fmod(qlu, 2) == 0)
    assert np.min(qlu) == 2
    assert np.max(qlu) == 20
    bc_qlu = np.bincount(qlu)
    assert bc_qlu[2] > bc_qlu[4] > bc_qlu[6] > bc_qlu[8]

    # -- quantized uniform
    qu = vals['qu']
    assert np.min(qu) == -5
    assert np.max(qu) == 5
    assert np.all(np.fmod(qu, 1) == 0)
    bc_qu = np.bincount(np.asarray(qu).astype('int') + 5)
    assert np.all(40 < bc_qu), bc_qu  # XXX: how to get the distribution flat
    # with new rounding rule?
    assert np.all(bc_qu < 125), bc_qu
    assert np.all(bc_qu < COUNTMAX)

    # -- uniform
    u = vals['u']
    assert np.min(u) > 0
    assert np.max(u) < 10
    h = np.histogram(u)[0]
    print h
    assert np.all(COUNTMIN < h)
    assert np.all(h < COUNTMAX)

    #import matplotlib.pyplot as plt
    #plt.hist(np.log(vals['node_2']))
    #plt.show()




########NEW FILE########
__FILENAME__ = test_webpage

def test_landing_screen():

    # define an objective function
    def objective(args):
        case, val = args
        if case == 'case 1':
            return val
        else:
            return val ** 2

    # define a search space
    from hyperopt import hp
    space = hp.choice('a',
        [
            ('case 1', 1 + hp.lognormal('c1', 0, 1)),
            ('case 2', hp.uniform('c2', -10, 10))
        ])

    # minimize the objective over the space
    import hyperopt
    best = hyperopt.fmin(objective, space,
        algo=hyperopt.tpe.suggest,
        max_evals=100)

    print best
    # -> {'a': 1, 'c2': 0.01420615366247227}

    print hyperopt.space_eval(space, best)
    # -> ('case 2', 0.01420615366247227}

########NEW FILE########
__FILENAME__ = tpe
"""
Graphical model (GM)-based optimization algorithm using Theano
"""

__authors__ = "James Bergstra"
__license__ = "3-clause BSD License"
__contact__ = "github.com/jaberg/hyperopt"

import logging
import time

import numpy as np
from scipy.special import erf
import pyll
from pyll import scope
from pyll.stochastic import implicit_stochastic

from .base import miscs_to_idxs_vals
from .base import miscs_update_idxs_vals
from .base import Trials
import rand

logger = logging.getLogger(__name__)

EPS = 1e-12

# -- default linear forgetting. don't try to change by writing this variable
# because it's captured in function default args when this file is read
DEFAULT_LF = 25


adaptive_parzen_samplers = {}


def adaptive_parzen_sampler(name):
    def wrapper(f):
        assert name not in adaptive_parzen_samplers
        adaptive_parzen_samplers[name] = f
        return f
    return wrapper


#
# These are some custom distributions
# that are used to represent posterior distributions.
#

# -- Categorical

@scope.define
def categorical_lpdf(sample, p, upper):
    """
    """
    if sample.size:
        return np.log(np.asarray(p)[sample])
    else:
        return np.asarray([])


# -- Bounded Gaussian Mixture Model (BGMM)

@implicit_stochastic
@scope.define
def GMM1(weights, mus, sigmas, low=None, high=None, q=None, rng=None,
        size=()):
    """Sample from truncated 1-D Gaussian Mixture Model"""
    weights, mus, sigmas = map(np.asarray, (weights, mus, sigmas))
    assert len(weights) == len(mus) == len(sigmas)
    n_samples = np.prod(size)
    #n_components = len(weights)
    if low is None and high is None:
        # -- draw from a standard GMM
        active = np.argmax(rng.multinomial(1, weights, (n_samples,)), axis=1)
        samples = rng.normal(loc=mus[active], scale=sigmas[active])
    else:
        # -- draw from truncated components
        # TODO: one-sided-truncation
        low = float(low)
        high = float(high)
        if low >= high:
            raise ValueError('low >= high', (low, high))
        samples = []
        while len(samples) < n_samples:
            active = np.argmax(rng.multinomial(1, weights))
            draw = rng.normal(loc=mus[active], scale=sigmas[active])
            if low <= draw < high:
                samples.append(draw)
    samples = np.reshape(np.asarray(samples), size)
    #print 'SAMPLES', samples
    if q is None:
        return samples
    else:
        return np.round(samples / q) * q


@scope.define
def normal_cdf(x, mu, sigma):
    top = (x - mu)
    bottom = np.maximum(np.sqrt(2) * sigma, EPS)
    z = top / bottom
    return 0.5 * (1 + erf(z))


@scope.define
def GMM1_lpdf(samples, weights, mus, sigmas, low=None, high=None, q=None):
    verbose = 0
    samples, weights, mus, sigmas = map(np.asarray,
            (samples, weights, mus, sigmas))
    if samples.size == 0:
        return np.asarray([])
    if weights.ndim != 1:
        raise TypeError('need vector of weights', weights.shape)
    if mus.ndim != 1:
        raise TypeError('need vector of mus', mus.shape)
    if sigmas.ndim != 1:
        raise TypeError('need vector of sigmas', sigmas.shape)
    assert len(weights) == len(mus) == len(sigmas)
    _samples = samples
    samples = _samples.flatten()

    if verbose:
        print 'GMM1_lpdf:samples', set(samples)
        print 'GMM1_lpdf:weights', weights
        print 'GMM1_lpdf:mus', mus
        print 'GMM1_lpdf:sigmas', sigmas
        print 'GMM1_lpdf:low', low
        print 'GMM1_lpdf:high', high
        print 'GMM1_lpdf:q', q

    if low is None and high is None:
        p_accept = 1
    else:
        p_accept = np.sum(
                weights * (
                    normal_cdf(high, mus, sigmas)
                    - normal_cdf(low, mus, sigmas)))

    if q is None:
        dist = samples[:, None] - mus
        mahal = (dist / np.maximum(sigmas, EPS)) ** 2
        # mahal shape is (n_samples, n_components)
        Z = np.sqrt(2 * np.pi * sigmas ** 2)
        coef = weights / Z / p_accept
        rval = logsum_rows(- 0.5 * mahal + np.log(coef))
    else:
        prob = np.zeros(samples.shape, dtype='float64')
        for w, mu, sigma in zip(weights, mus, sigmas):
            if high is None:
                ubound = samples + q / 2.0
            else:
                ubound = np.minimum(samples + q / 2.0, high)
            if low is None:
                lbound = samples - q / 2.0
            else:
                lbound = np.maximum(samples - q / 2.0, low)
            # -- two-stage addition is slightly more numerically accurate
            inc_amt = w * normal_cdf(ubound, mu, sigma)
            inc_amt -= w * normal_cdf(lbound, mu, sigma)
            prob += inc_amt
        rval = np.log(prob) - np.log(p_accept)

    if verbose:
        print 'GMM1_lpdf:rval:', dict(zip(samples, rval))

    rval.shape = _samples.shape
    return rval


# -- Mixture of Log-Normals

@scope.define
def lognormal_cdf(x, mu, sigma):
    # wikipedia claims cdf is
    # .5 + .5 erf( log(x) - mu / sqrt(2 sigma^2))
    #
    # the maximum is used to move negative values and 0 up to a point
    # where they do not cause nan or inf, but also don't contribute much
    # to the cdf.
    if len(x) == 0:
        return np.asarray([])
    if x.min() < 0:
        raise ValueError('negative arg to lognormal_cdf', x)
    olderr = np.seterr(divide='ignore')
    try:
        top = np.log(np.maximum(x, EPS)) - mu
        bottom = np.maximum(np.sqrt(2) * sigma, EPS)
        z = top / bottom
        return .5 + .5 * erf(z)
    finally:
        np.seterr(**olderr)


@scope.define
def lognormal_lpdf(x, mu, sigma):
    # formula copied from wikipedia
    # http://en.wikipedia.org/wiki/Log-normal_distribution
    assert np.all(sigma >= 0)
    sigma = np.maximum(sigma, EPS)
    Z = sigma * x * np.sqrt(2 * np.pi)
    E = 0.5 * ((np.log(x) - mu) / sigma) ** 2
    rval = -E - np.log(Z)
    return rval


@scope.define
def qlognormal_lpdf(x, mu, sigma, q):
    # casting rounds up to nearest step multiple.
    # so lpdf is log of integral from x-step to x+1 of P(x)

    # XXX: subtracting two numbers potentially very close together.
    return np.log(
            lognormal_cdf(x, mu, sigma)
            - lognormal_cdf(x - q, mu, sigma))


@implicit_stochastic
@scope.define
def LGMM1(weights, mus, sigmas, low=None, high=None, q=None,
        rng=None, size=()):
    weights, mus, sigmas = map(np.asarray, (weights, mus, sigmas))
    n_samples = np.prod(size)
    #n_components = len(weights)
    if low is None and high is None:
        active = np.argmax(
                rng.multinomial(1, weights, (n_samples,)),
                axis=1)
        assert len(active) == n_samples
        samples = np.exp(
                rng.normal(
                    loc=mus[active],
                    scale=sigmas[active]))
    else:
        # -- draw from truncated components
        # TODO: one-sided-truncation
        low = float(low)
        high = float(high)
        if low >= high:
            raise ValueError('low >= high', (low, high))
        samples = []
        while len(samples) < n_samples:
            active = np.argmax(rng.multinomial(1, weights))
            draw = rng.normal(loc=mus[active], scale=sigmas[active])
            if low <= draw < high:
                samples.append(np.exp(draw))
        samples = np.asarray(samples)

    samples = np.reshape(np.asarray(samples), size)
    if q is not None:
        samples = np.round(samples / q) * q
    return samples


def logsum_rows(x):
    R, C = x.shape
    m = x.max(axis=1)
    return np.log(np.exp(x - m[:, None]).sum(axis=1)) + m


@scope.define
def LGMM1_lpdf(samples, weights, mus, sigmas, low=None, high=None, q=None):
    samples, weights, mus, sigmas = map(np.asarray,
            (samples, weights, mus, sigmas))
    assert weights.ndim == 1
    assert mus.ndim == 1
    assert sigmas.ndim == 1
    _samples = samples
    if samples.ndim != 1:
        samples = samples.flatten()

    if low is None and high is None:
        p_accept = 1
    else:
        p_accept = np.sum(
                weights * (
                    normal_cdf(high, mus, sigmas)
                    - normal_cdf(low, mus, sigmas)))

    if q is None:
        # compute the lpdf of each sample under each component
        lpdfs = lognormal_lpdf(samples[:, None], mus, sigmas)
        rval = logsum_rows(lpdfs + np.log(weights))
    else:
        # compute the lpdf of each sample under each component
        prob = np.zeros(samples.shape, dtype='float64')
        for w, mu, sigma in zip(weights, mus, sigmas):
            if high is None:
                ubound = samples + q / 2.0
            else:
                ubound = np.minimum(samples + q / 2.0, np.exp(high))
            if low is None:
                lbound = samples - q / 2.0
            else:
                lbound = np.maximum(samples - q / 2.0, np.exp(low))
            lbound = np.maximum(0, lbound)
            # -- two-stage addition is slightly more numerically accurate
            inc_amt = w * lognormal_cdf(ubound, mu, sigma)
            inc_amt -= w * lognormal_cdf(lbound, mu, sigma)
            prob += inc_amt
        rval = np.log(prob) - np.log(p_accept)
    rval.shape = _samples.shape
    return rval


#
# This is the weird heuristic ParzenWindow estimator used for continuous
# distributions in various ways.
#

@scope.define_info(o_len=3)
def adaptive_parzen_normal_orig(mus, prior_weight, prior_mu, prior_sigma):
    """
    A heuristic estimator for the mu and sigma values of a GMM
    TODO: try to find this heuristic in the literature, and cite it - Yoshua
    mentioned the term 'elastic' I think?

    mus - matrix (N, M) of M, N-dimensional component centers
    """
    mus_orig = np.array(mus)
    mus = np.array(mus)
    assert str(mus.dtype) != 'object'

    if mus.ndim != 1:
        raise TypeError('mus must be vector', mus)
    if len(mus) == 0:
        mus = np.asarray([prior_mu])
        sigma = np.asarray([prior_sigma])
    elif len(mus) == 1:
        mus = np.asarray([prior_mu] + [mus[0]])
        sigma = np.asarray([prior_sigma, prior_sigma * .5])
    elif len(mus) >= 2:
        order = np.argsort(mus)
        mus = mus[order]
        sigma = np.zeros_like(mus)
        sigma[1:-1] = np.maximum(
                mus[1:-1] - mus[0:-2],
                mus[2:] - mus[1:-1])
        if len(mus) > 2:
            lsigma = mus[2] - mus[0]
            usigma = mus[-1] - mus[-3]
        else:
            lsigma = mus[1] - mus[0]
            usigma = mus[-1] - mus[-2]

        sigma[0] = lsigma
        sigma[-1] = usigma

        # XXX: is sorting them necessary anymore?
        # un-sort the mus and sigma
        mus[order] = mus.copy()
        sigma[order] = sigma.copy()

        if not np.all(mus_orig == mus):
            print 'orig', mus_orig
            print 'mus', mus
        assert np.all(mus_orig == mus)

        # put the prior back in
        mus = np.asarray([prior_mu] + list(mus))
        sigma = np.asarray([prior_sigma] + list(sigma))

    maxsigma = prior_sigma
    # -- magic formula:
    minsigma = prior_sigma / np.sqrt(1 + len(mus))

    #print 'maxsigma, minsigma', maxsigma, minsigma
    sigma = np.clip(sigma, minsigma, maxsigma)

    weights = np.ones(len(mus), dtype=mus.dtype)
    weights[0] = prior_weight

    #print weights.dtype
    weights = weights / weights.sum()
    if 0:
        print 'WEIGHTS', weights
        print 'MUS', mus
        print 'SIGMA', sigma

    return weights, mus, sigma


@scope.define
def linear_forgetting_weights(N, LF):
    assert N >= 0
    assert LF > 0
    if N == 0:
        return np.asarray([])
    elif N < LF:
        return np.ones(N)
    else:
        ramp = np.linspace(1.0 / N, 1.0, num=N - LF)
        flat = np.ones(LF)
        weights = np.concatenate([ramp, flat], axis=0)
        assert weights.shape == (N,), (weights.shape, N)
        return weights

# XXX: make TPE do a post-inference pass over the pyll graph and insert
# non-default LF argument
@scope.define_info(o_len=3)
def adaptive_parzen_normal(mus, prior_weight, prior_mu, prior_sigma,
        LF=DEFAULT_LF):
    """
    mus - matrix (N, M) of M, N-dimensional component centers
    """
    #mus_orig = np.array(mus)
    mus = np.array(mus)
    assert str(mus.dtype) != 'object'

    if mus.ndim != 1:
        raise TypeError('mus must be vector', mus)
    if len(mus) == 0:
        srtd_mus = np.asarray([prior_mu])
        sigma = np.asarray([prior_sigma])
        prior_pos = 0
    elif len(mus) == 1:
        if prior_mu < mus[0]:
            prior_pos = 0
            srtd_mus = np.asarray([prior_mu, mus[0]])
            sigma = np.asarray([prior_sigma, prior_sigma * .5])
        else:
            prior_pos = 1
            srtd_mus = np.asarray([mus[0], prior_mu])
            sigma = np.asarray([prior_sigma * .5, prior_sigma])
    elif len(mus) >= 2:

        # create new_mus, which is sorted, and in which
        # the prior has been inserted
        order = np.argsort(mus)
        prior_pos = np.searchsorted(mus[order], prior_mu)
        srtd_mus = np.zeros(len(mus) + 1)
        srtd_mus[:prior_pos] = mus[order[:prior_pos]]
        srtd_mus[prior_pos] = prior_mu
        srtd_mus[prior_pos + 1:] = mus[order[prior_pos:]]
        sigma = np.zeros_like(srtd_mus)
        sigma[1:-1] = np.maximum(
                srtd_mus[1:-1] - srtd_mus[0:-2],
                srtd_mus[2:] - srtd_mus[1:-1])
        lsigma = srtd_mus[1] - srtd_mus[0]
        usigma = srtd_mus[-1] - srtd_mus[-2]
        sigma[0] = lsigma
        sigma[-1] = usigma

    if LF and LF < len(mus):
        unsrtd_weights = linear_forgetting_weights(len(mus), LF)
        srtd_weights = np.zeros_like(srtd_mus)
        assert len(unsrtd_weights) + 1 == len(srtd_mus)
        srtd_weights[:prior_pos] = unsrtd_weights[order[:prior_pos]]
        srtd_weights[prior_pos] = prior_weight
        srtd_weights[prior_pos + 1:] = unsrtd_weights[order[prior_pos:]]

    else:
        srtd_weights = np.ones(len(srtd_mus))
        srtd_weights[prior_pos] = prior_weight

    # -- magic formula:
    maxsigma = prior_sigma / 1.0
    minsigma = prior_sigma / min(100.0, (1.0 + len(srtd_mus)))

    #print 'maxsigma, minsigma', maxsigma, minsigma
    sigma = np.clip(sigma, minsigma, maxsigma)

    sigma[prior_pos] = prior_sigma
    assert prior_sigma > 0
    assert maxsigma > 0
    assert minsigma > 0
    assert np.all(sigma > 0), (sigma.min(), minsigma, maxsigma)


    #print weights.dtype
    srtd_weights /= srtd_weights.sum()
    if 0:
        print 'WEIGHTS', srtd_weights
        print 'MUS', srtd_mus
        print 'SIGMA', sigma

    return srtd_weights, srtd_mus, sigma

#
# Adaptive Parzen Samplers
# These produce conditional estimators for various prior distributions
#

# -- Uniform


@adaptive_parzen_sampler('uniform')
def ap_uniform_sampler(obs, prior_weight, low, high, size=(), rng=None):
    prior_mu = 0.5 * (high + low)
    prior_sigma = 1.0 * (high - low)
    weights, mus, sigmas = scope.adaptive_parzen_normal(obs,
            prior_weight, prior_mu, prior_sigma)
    return scope.GMM1(weights, mus, sigmas, low=low, high=high, q=None,
            size=size, rng=rng)


@adaptive_parzen_sampler('quniform')
def ap_quniform_sampler(obs, prior_weight, low, high, q, size=(), rng=None):
    prior_mu = 0.5 * (high + low)
    prior_sigma = 1.0 * (high - low)
    weights, mus, sigmas = scope.adaptive_parzen_normal(obs,
            prior_weight, prior_mu, prior_sigma)
    return scope.GMM1(weights, mus, sigmas, low=low, high=high, q=q,
            size=size, rng=rng)


@adaptive_parzen_sampler('loguniform')
def ap_loguniform_sampler(obs, prior_weight, low, high,
        size=(), rng=None):
    prior_mu = 0.5 * (high + low)
    prior_sigma = 1.0 * (high - low)
    weights, mus, sigmas = scope.adaptive_parzen_normal(
            scope.log(obs), prior_weight, prior_mu, prior_sigma)
    rval = scope.LGMM1(weights, mus, sigmas, low=low, high=high,
            size=size, rng=rng)
    return rval


@adaptive_parzen_sampler('qloguniform')
def ap_qloguniform_sampler(obs, prior_weight, low, high, q,
        size=(), rng=None):
    prior_mu = 0.5 * (high + low)
    prior_sigma = 1.0 * (high - low)
    weights, mus, sigmas = scope.adaptive_parzen_normal(
            scope.log(
                # -- map observations that were quantized to be below exp(low)
                #    (particularly 0) back up to exp(low) where they will
                #    interact in a reasonable way with the AdaptiveParzen
                #    thing.
                scope.maximum(
                    obs,
                    scope.maximum(  # -- protect against exp(low) underflow
                        EPS,
                        scope.exp(low)))),
            prior_weight, prior_mu, prior_sigma)
    return scope.LGMM1(weights, mus, sigmas, low, high, q=q,
            size=size, rng=rng)


# -- Normal

@adaptive_parzen_sampler('normal')
def ap_normal_sampler(obs, prior_weight, mu, sigma, size=(), rng=None):
    weights, mus, sigmas = scope.adaptive_parzen_normal(
            obs, prior_weight, mu, sigma)
    return scope.GMM1(weights, mus, sigmas, size=size, rng=rng)


@adaptive_parzen_sampler('qnormal')
def ap_qnormal_sampler(obs, prior_weight, mu, sigma, q, size=(), rng=None):
    weights, mus, sigmas = scope.adaptive_parzen_normal(
            obs, prior_weight, mu, sigma)
    return scope.GMM1(weights, mus, sigmas, q=q, size=size, rng=rng)


@adaptive_parzen_sampler('lognormal')
def ap_loglognormal_sampler(obs, prior_weight, mu, sigma, size=(), rng=None):
    weights, mus, sigmas = scope.adaptive_parzen_normal(
            scope.log(obs), prior_weight, mu, sigma)
    rval = scope.LGMM1(weights, mus, sigmas, size=size, rng=rng)
    return rval


@adaptive_parzen_sampler('qlognormal')
def ap_qlognormal_sampler(obs, prior_weight, mu, sigma, q, size=(), rng=None):
    log_obs = scope.log(scope.maximum(obs, EPS))
    weights, mus, sigmas = scope.adaptive_parzen_normal(
            log_obs, prior_weight, mu, sigma)
    rval = scope.LGMM1(weights, mus, sigmas, q=q, size=size, rng=rng)
    return rval


# -- Categorical

@adaptive_parzen_sampler('randint')
def ap_categorical_sampler(obs, prior_weight, upper,
        size=(), rng=None, LF=DEFAULT_LF):
    weights = scope.linear_forgetting_weights(scope.len(obs), LF=LF)
    counts = scope.bincount(obs, minlength=upper, weights=weights)
    # -- add in some prior pseudocounts
    pseudocounts = counts + prior_weight
    return scope.categorical(pseudocounts / scope.sum(pseudocounts),
            upper=upper, size=size, rng=rng)


# @adaptive_parzen_sampler('categorical')
# def ap_categorical_sampler(obs, prior_weight, p, upper, size=(), rng=None,
#                            LF=DEFAULT_LF):
#     return scope.categorical(p, upper, size=size, rng
#                              =rng)

@scope.define
def tpe_cat_pseudocounts(counts, upper, prior_weight, p, size):
    #print counts
    if size == 0 or np.prod(size) == 0:
        return []
    if p.ndim == 2:
        assert np.all(p == p[0])
        p = p[0]
    pseudocounts = counts + upper * (prior_weight * p)
    return pseudocounts / np.sum(pseudocounts)

@adaptive_parzen_sampler('categorical')
def ap_categorical_sampler(obs, prior_weight, p, upper=None,
        size=(), rng=None, LF=DEFAULT_LF):
    weights = scope.linear_forgetting_weights(scope.len(obs), LF=LF)
    counts = scope.bincount(obs, minlength=upper, weights=weights)
    pseudocounts = scope.tpe_cat_pseudocounts(counts, upper, prior_weight, p, size)
    return scope.categorical(pseudocounts, upper=upper, size=size, rng=rng)

#
# Posterior clone performs symbolic inference on the pyll graph of priors.
#

@scope.define_info(o_len=2)
def ap_filter_trials(o_idxs, o_vals, l_idxs, l_vals, gamma,
        gamma_cap=DEFAULT_LF):
    """Return the elements of o_vals that correspond to trials whose losses
    were above gamma, or below gamma.
    """
    o_idxs, o_vals, l_idxs, l_vals = map(np.asarray, [o_idxs, o_vals, l_idxs,
        l_vals])

    # XXX if this is working, refactor this sort for efficiency

    # Splitting is done this way to cope with duplicate loss values.
    n_below = min(int(np.ceil(gamma * np.sqrt(len(l_vals)))), gamma_cap)
    l_order = np.argsort(l_vals)


    keep_idxs = set(l_idxs[l_order[:n_below]])
    below = [v for i, v in zip(o_idxs, o_vals) if i in keep_idxs]

    if 0:
        print 'DEBUG: thresh', l_vals[l_order[:n_below]]

    keep_idxs = set(l_idxs[l_order[n_below:]])
    above = [v for i, v in zip(o_idxs, o_vals) if i in keep_idxs]

    #print 'AA0', below
    #print 'AA1', above

    return np.asarray(below), np.asarray(above)


def build_posterior(specs, prior_idxs, prior_vals, obs_idxs, obs_vals,
        oloss_idxs, oloss_vals, oloss_gamma, prior_weight):
    """
    This method clones a posterior inference graph by iterating forward in
    topological order, and replacing prior random-variables (prior_vals) with
    new posterior distributions that make use of observations (obs_vals).

    """
    assert all(isinstance(arg, pyll.Apply)
            for arg in [oloss_idxs, oloss_vals, oloss_gamma])

    expr = pyll.as_apply([specs, prior_idxs, prior_vals])
    nodes = pyll.dfs(expr)

    # build the joint posterior distribution as the values in this memo
    memo = {}
    # map prior RVs to observations
    obs_memo = {}

    for nid in prior_vals:
        # construct the leading args for each call to adaptive_parzen_sampler
        # which will permit the "adaptive parzen samplers" to adapt to the
        # correct samples.
        obs_below, obs_above = scope.ap_filter_trials(
                obs_idxs[nid], obs_vals[nid],
                oloss_idxs, oloss_vals, oloss_gamma)
        obs_memo[prior_vals[nid]] = [obs_below, obs_above]
    for node in nodes:
        if node not in memo:
            new_inputs = [memo[arg] for arg in node.inputs()]
            if node in obs_memo:
                # -- this case corresponds to an observed Random Var
                # node.name is a distribution like "normal", "randint", etc.
                obs_below, obs_above = obs_memo[node]
                aa = [memo[a] for a in node.pos_args]
                fn = adaptive_parzen_samplers[node.name]
                b_args = [obs_below, prior_weight] + aa
                named_args = [[kw, memo[arg]]
                        for (kw, arg) in node.named_args]
                b_post = fn(*b_args, **dict(named_args))
                a_args = [obs_above, prior_weight] + aa
                a_post = fn(*a_args, **dict(named_args))

                assert a_post.name == b_post.name
                fn_lpdf = getattr(scope, a_post.name + '_lpdf')
                #print fn_lpdf
                a_kwargs = dict([(n, a) for n, a in a_post.named_args
                            if n not in ('rng', 'size')])
                b_kwargs = dict([(n, a) for n, a in b_post.named_args
                            if n not in ('rng', 'size')])

                # calculate the llik of b_post under both distributions
                below_llik = fn_lpdf(*([b_post] + b_post.pos_args), **b_kwargs)
                above_llik = fn_lpdf(*([b_post] + a_post.pos_args), **a_kwargs)

                #improvement = below_llik - above_llik
                #new_node = scope.broadcast_best(b_post, improvement)
                new_node = scope.broadcast_best(b_post, below_llik, above_llik)
            elif hasattr(node, 'obj'):
                # -- keep same literals in the graph
                new_node = node
            else:
                # -- this case is for all the other stuff in the graph
                new_node = node.clone_from_inputs(new_inputs)
            memo[node] = new_node
    post_specs = memo[specs]
    post_idxs = dict([(nid, memo[idxs])
        for nid, idxs in prior_idxs.items()])
    post_vals = dict([(nid, memo[vals])
        for nid, vals in prior_vals.items()])
    assert set(post_idxs.keys()) == set(post_vals.keys())
    assert set(post_idxs.keys()) == set(prior_idxs.keys())
    return post_specs, post_idxs, post_vals


@scope.define
def idxs_prod(full_idxs, idxs_by_label, llik_by_label):
    """Add all of the  log-likelihoods together by id.

    Example arguments:
    full_idxs = [0, 1, ... N-1]
    idxs_by_label = {'node_a': [1, 3], 'node_b': [3]}
    llik_by_label = {'node_a': [0.1, -3.3], node_b: [1.0]}

    This would return N elements: [0, 0.1, 0, -2.3, 0, 0, ... ]
    """
    #print 'FULL IDXS'
    #print full_idxs
    assert len(set(full_idxs)) == len(full_idxs)
    full_idxs = list(full_idxs)
    rval = np.zeros(len(full_idxs))
    pos_of_tid = dict(zip(full_idxs, range(len(full_idxs))))
    assert set(idxs_by_label.keys()) == set(llik_by_label.keys())
    for nid in idxs_by_label:
        idxs = idxs_by_label[nid]
        llik = llik_by_label[nid]
        assert np.all(np.asarray(idxs) > 1)
        assert len(set(idxs)) == len(idxs)
        assert len(idxs) == len(llik)
        for ii, ll in zip(idxs, llik):
            rval[pos_of_tid[ii]] += ll
            #rval[full_idxs.index(ii)] += ll
    return rval


@scope.define
def broadcast_best(samples, below_llik, above_llik):
    if len(samples):
        #print 'AA2', dict(zip(samples, below_llik - above_llik))
        score = below_llik - above_llik
        if len(samples) != len(score):
            raise ValueError()
        best = np.argmax(score)
        return [samples[best]] * len(samples)
    else:
        return []


_default_prior_weight = 1.0

# -- suggest best of this many draws on every iteration
_default_n_EI_candidates = 24

# -- gamma * sqrt(n_trials) is fraction of to use as good
_default_gamma = 0.25

_default_n_startup_jobs = 20

_default_linear_forgetting = DEFAULT_LF


def tpe_transform(domain, prior_weight, gamma):
    s_prior_weight = pyll.Literal(float(prior_weight))

    # -- these dummy values will be replaced in suggest1() and never used
    observed = dict(
            idxs=pyll.Literal(),
            vals=pyll.Literal())
    observed_loss = dict(
            idxs=pyll.Literal(),
            vals=pyll.Literal())

    specs, idxs, vals = build_posterior(
            # -- vectorized clone of bandit template
            domain.vh.v_expr,
            # -- this dict and next represent prior dists
            domain.vh.idxs_by_label(),
            domain.vh.vals_by_label(),
            observed['idxs'],
            observed['vals'],
            observed_loss['idxs'],
            observed_loss['vals'],
            pyll.Literal(gamma),
            s_prior_weight
            )

    return (s_prior_weight, observed, observed_loss,
            specs, idxs, vals)


def suggest(new_ids, domain, trials, seed,
        prior_weight=_default_prior_weight,
        n_startup_jobs=_default_n_startup_jobs,
        n_EI_candidates=_default_n_EI_candidates,
        gamma=_default_gamma,
        linear_forgetting=_default_linear_forgetting,
        ):

    new_id, = new_ids

    t0 = time.time()
    (s_prior_weight, observed, observed_loss, specs, opt_idxs, opt_vals) \
            = tpe_transform(domain, prior_weight, gamma)
    tt = time.time() - t0
    logger.info('tpe_transform took %f seconds' % tt)

    best_docs = dict()
    best_docs_loss = dict()
    for doc in trials.trials:
        # get either this docs own tid or the one that it's from
        tid = doc['misc'].get('from_tid', doc['tid'])
        loss = domain.loss(doc['result'], doc['spec'])
        if loss is None:
            # -- associate infinite loss to new/running/failed jobs
            loss = float('inf')
        else:
            loss = float(loss)
        best_docs_loss.setdefault(tid, loss)
        if loss <= best_docs_loss[tid]:
            best_docs_loss[tid] = loss
            best_docs[tid] = doc

    tid_docs = best_docs.items()
    # -- sort docs by order of suggestion
    #    so that linear_forgetting removes the oldest ones
    tid_docs.sort()
    losses = [best_docs_loss[k] for k, v in tid_docs]
    tids = [k for k, v in tid_docs]
    docs = [v for k, v in tid_docs]

    if docs:
        logger.info('TPE using %i/%i trials with best loss %f' % (
            len(docs), len(trials), min(best_docs_loss.values())))
    else:
        logger.info('TPE using 0 trials')

    if len(docs) < n_startup_jobs:
        # N.B. THIS SEEDS THE RNG BASED ON THE new_id
        return rand.suggest(new_ids, domain, trials, seed)

    #    Sample and compute log-probability.
    if tids:
        # -- the +2 co-ordinates with an assertion above
        #    to ensure that fake ids are used during sampling
        fake_id_0 = max(max(tids), new_id) + 2
    else:
        # -- weird - we're running the TPE algo from scratch
        assert n_startup_jobs <= 0
        fake_id_0 = new_id + 2

    fake_ids = range(fake_id_0, fake_id_0 + n_EI_candidates)

    # -- this dictionary will map pyll nodes to the values
    #    they should take during the evaluation of the pyll program
    memo = {
        domain.s_new_ids: fake_ids,
        domain.s_rng: np.random.RandomState(seed),
           }

    o_idxs_d, o_vals_d = miscs_to_idxs_vals(
        [d['misc'] for d in docs], keys=domain.params.keys())
    memo[observed['idxs']] = o_idxs_d
    memo[observed['vals']] = o_vals_d

    memo[observed_loss['idxs']] = tids
    memo[observed_loss['vals']] = losses

    idxs, vals = pyll.rec_eval([opt_idxs, opt_vals], memo=memo,
            print_node_on_error=False)

    # -- retrieve the best of the samples and form the return tuple
    # the build_posterior makes all specs the same

    rval_specs = [None]  # -- specs are deprecated
    rval_results = [domain.new_result()]
    rval_miscs = [dict(tid=new_id, cmd=domain.cmd, workdir=domain.workdir)]

    miscs_update_idxs_vals(rval_miscs, idxs, vals,
            idxs_map={fake_ids[0]: new_id},
            assert_all_vals_used=False)
    rval_docs = trials.new_trial_docs([new_id],
            rval_specs, rval_results, rval_miscs)

    return rval_docs



########NEW FILE########
__FILENAME__ = utils
import datetime
import numpy as np
import logging
import cPickle
logger = logging.getLogger(__name__)

import numpy

import pyll

def import_tokens(tokens):
    # XXX Document me
    # import as many as we can
    rval = None
    for i in range(len(tokens)):
        modname = '.'.join(tokens[:i+1])
        # XXX: try using getattr, and then merge with load_tokens
        try:
            logger.info('importing %s' % modname)
            exec "import %s" % modname
            exec "rval = %s" % modname
        except ImportError, e:
            logger.info('failed to import %s' % modname)
            logger.info('reason: %s' % str(e))
            break
    return rval, tokens[i:]

def load_tokens(tokens):
    # XXX: merge with import_tokens
    logger.info('load_tokens: %s' % str(tokens))
    symbol, remainder = import_tokens(tokens)
    for attr in remainder:
        symbol = getattr(symbol, attr)
    return symbol


def json_lookup(json):
    symbol = load_tokens(json.split('.'))
    return symbol


def json_call(json, args=(), kwargs=None):
    """
    Return a dataset class instance based on a string, tuple or dictionary

    .. code-block:: python

        iris = json_call('datasets.toy.Iris')

    This function works by parsing the string, and calling import and getattr a
    lot. (XXX)

    """
    if kwargs is None:
        kwargs = {}
    if isinstance(json, basestring):
        symbol = json_lookup(json)
        return symbol(*args, **kwargs)
    elif isinstance(json, dict):
        raise NotImplementedError('dict calling convention undefined', json)
    elif isinstance(json, (tuple, list)):
        raise NotImplementedError('seq calling convention undefined', json)
    else:
        raise TypeError(json)


def get_obj(f, argfile=None, argstr=None, args=(), kwargs=None):
    """
    XXX: document me
    """
    if kwargs is None:
        kwargs = {}
    if argfile is not None:
        argstr = open(argfile).read()
    if argstr is not None:
        argd = cPickle.loads(argstr)
    else:
        argd = {}
    args = args + argd.get('args',())
    kwargs.update(argd.get('kwargs',{}))
    return json_call(f, args=args, kwargs=kwargs)


def pmin_sampled(mean, var, n_samples=1000, rng=None):
    """Probability that each Gaussian-dist R.V. is less than the others

    :param vscores: mean vector
    :param var: variance vector

    This function works by sampling n_samples from every (gaussian) mean distribution,
    and counting up the number of times each element's sample is the best.

    """
    if rng is None:
        rng = numpy.random.RandomState(232342)

    samples = rng.randn(n_samples, len(mean)) * numpy.sqrt(var) + mean
    winners = (samples.T == samples.min(axis=1)).T
    wincounts = winners.sum(axis=0)
    assert wincounts.shape == mean.shape
    return wincounts.astype('float64') / wincounts.sum()


def fast_isin(X,Y):
    """
    Indices of elements in a numpy array that appear in another.

    Fast routine for determining indices of elements in numpy array `X` that 
    appear in numpy array `Y`, returning a boolean array `Z` such that::

            Z[i] = X[i] in Y

    """
    if len(Y) > 0:
        T = Y.copy()
        T.sort()
        D = T.searchsorted(X)
        T = np.append(T,np.array([0]))
        W = (T[D] == X)
        if isinstance(W,bool):
            return np.zeros((len(X),),bool)
        else:
            return (T[D] == X)
    else:
        return np.zeros((len(X),),bool)


def get_most_recent_inds(obj):
    data = numpy.rec.array([(x['_id'], int(x['version']))
                            for x in obj], 
                            names=['_id', 'version'])
    s = data.argsort(order=['_id', 'version'])
    data = data[s]
    recent = (data['_id'][1:] != data['_id'][:-1]).nonzero()[0]
    recent = numpy.append(recent, [len(data)-1])
    return s[recent]


def use_obj_for_literal_in_memo(expr, obj, lit, memo):
    """
    Set `memo[node] = obj` for all nodes in expr such that `node.obj == lit`

    This is a useful routine for fmin-compatible functions that are searching
    domains that include some leaf nodes that are complicated
    runtime-generated objects. One option is to make such leaf nodes pyll
    functions, but it can be easier to construct those objects the normal
    Python way in the fmin function, and just stick them into the evaluation
    memo.  The experiment ctrl object itself is inserted using this technique.
    """
    for node in pyll.dfs(expr):
        try:
            if node.obj == lit:
                memo[node] = obj
        except AttributeError:
            # -- non-literal nodes don't have node.obj
            pass
    return memo


def coarse_utcnow():
    """
    # MongoDB stores only to the nearest millisecond
    # This is mentioned in a footnote here:
    # http://api.mongodb.org/python/current/api/bson/son.html#dt
    """
    now = datetime.datetime.utcnow()
    microsec = (now.microsecond // 10 ** 3) * (10 ** 3)
    return datetime.datetime(now.year, now.month, now.day, now.hour,
                             now.minute, now.second, microsec)



########NEW FILE########
__FILENAME__ = vectorize
import sys

import numpy as np

from pyll import Apply
from pyll import as_apply
from pyll import dfs
from pyll import toposort
from pyll import scope
from pyll import stochastic
from pyll import clone_merge

stoch = stochastic.implicit_stochastic_symbols


def ERR(msg):
    print >> sys.stderr, 'hyperopt.vectorize.ERR', msg


@scope.define_pure
def vchoice_split(idxs, choices, n_options):
    rval = [[] for ii in range(n_options)]
    if len(idxs) != len(choices):
        raise ValueError('idxs and choices different len',
                (len(idxs), len(choices)))
    for ii, cc in zip(idxs, choices):
        rval[cc].append(ii)
    return rval


@scope.define_pure
def vchoice_merge(idxs, choices, *vals):
    rval = []
    assert len(idxs) == len(choices)
    for idx, ch in zip(idxs, choices):
        vi, vv = vals[ch]
        rval.append(vv[list(vi).index(idx)])
    return rval


@scope.define_pure
def idxs_map(idxs, cmd, *args, **kwargs):
    """
    Return the cmd applied at positions idxs, by retrieving args and kwargs
    from the (idxs, vals) pair elements of `args` and `kwargs`.

    N.B. args and kwargs may generally include information for more idx values
    than are requested by idxs.
    """
    # XXX: consider insisting on sorted idxs
    # XXX: use np.searchsorted instead of dct

    if 0: # these should all be true, but evaluating them is slow
        for ii, (idxs_ii, vals_ii) in enumerate(args):
            for jj in idxs: assert jj in idxs_ii
        for kw, (idxs_kw, vals_kw) in kwargs.items():
            for jj in idxs: assert jj in idxs_kw

    args_imap = []
    for idxs_j, vals_j in args:
        if len(idxs_j):
            args_imap.append(dict(zip(idxs_j, vals_j)))
        else:
            args_imap.append({})

    kwargs_imap = {}
    for kw, (idxs_j, vals_j) in kwargs.items():
        if len(idxs_j):
            kwargs_imap[kw] = dict(zip(idxs_j, vals_j))
        else:
            kwargs_imap[kw] = {}

    f = scope._impls[cmd]
    rval = []
    for ii in idxs:
        try:
            args_nn = [arg_imap[ii] for arg_imap in args_imap]
        except:
            ERR('args_nn %s' % cmd)
            ERR('ii %s' % ii)
            ERR('arg_imap %s' % str(arg_imap))
            ERR('args_imap %s' % str(args_imap))
            raise
        try:
            kwargs_nn = dict([(kw, arg_imap[ii])
                for kw, arg_imap in kwargs_imap.items()])
        except:
            ERR('args_nn %s' % cmd)
            ERR('ii %s' % ii)
            ERR('kw %s' % kw)
            ERR('arg_imap %s' % str(arg_imap))
            raise
        try:
            rval_nn = f(*args_nn, **kwargs_nn)
        except:
            ERR('error calling impl of %s' % cmd)
            raise
        rval.append(rval_nn)
    return rval


@scope.define_pure
def idxs_take(idxs, vals, which):
    """
    Return `vals[which]` where `which` is a subset of `idxs`
    """
    # TODO: consider insisting on sorted idxs
    # TODO: use np.searchsorted instead of dct
    assert len(idxs) == len(vals)
    table = dict(zip(idxs, vals))
    return np.asarray([table[w] for w in which])


@scope.define_pure
def uniq(lst):
    s = set()
    rval = []
    for l in lst:
        if id(l) not in s:
            s.add(id(l))
            rval.append(l)
    return rval


def vectorize_stochastic(orig):
    if orig.name == 'idxs_map' and orig.pos_args[1]._obj in stoch:
        # -- this is an idxs_map of a random draw of distribution `dist`
        idxs = orig.pos_args[0]
        dist = orig.pos_args[1]._obj
        def foo(arg):
            # -- each argument is an idxs, vals pair
            assert arg.name == 'pos_args'
            assert len(arg.pos_args) == 2
            arg_vals = arg.pos_args[1]

            # XXX: write a pattern-substitution rule for this case
            if arg_vals.name == 'idxs_take':
                if arg_vals.arg['vals'].name == 'asarray':
                    if arg_vals.arg['vals'].inputs()[0].name == 'repeat':
                        # -- draws are iid, so forget about
                        #    repeating the distribution parameters
                        repeated_thing = arg_vals.arg['vals'].inputs()[0].inputs()[1]
                        return repeated_thing
            if arg.pos_args[0] is idxs:
                return arg_vals
            else:
                # -- arg.pos_args[0] is a superset of idxs
                #    TODO: slice out correct elements using
                #    idxs_take, but more importantly - test this case.
                raise NotImplementedError()
        new_pos_args = [foo(arg) for arg in orig.pos_args[2:]]
        new_named_args = [[aname, foo(arg)]
                for aname, arg in orig.named_args]
        vnode = Apply(dist, new_pos_args, new_named_args, o_len=None)
        n_times = scope.len(idxs)
        if 'size' in dict(vnode.named_args):
            raise NotImplementedError('random node already has size')
        vnode.named_args.append(['size', n_times])
        return vnode
    else:
        return orig


def replace_repeat_stochastic(expr, return_memo=False):
    nodes = dfs(expr)
    memo = {}
    for ii, orig in enumerate(nodes):
        if orig.name == 'idxs_map' and orig.pos_args[1]._obj in stoch:
            # -- this is an idxs_map of a random draw of distribution `dist`
            idxs = orig.pos_args[0]
            dist = orig.pos_args[1]._obj
            def foo(arg):
                # -- each argument is an idxs, vals pair
                assert arg.name == 'pos_args'
                assert len(arg.pos_args) == 2
                arg_vals = arg.pos_args[1]
                if (arg_vals.name == 'asarray'
                        and arg_vals.inputs()[0].name == 'repeat'):
                    # -- draws are iid, so forget about
                    #    repeating the distribution parameters
                    repeated_thing = arg_vals.inputs()[0].inputs()[1]
                    return repeated_thing
                else:
                    if arg.pos_args[0] is idxs:
                        return arg_vals
                    else:
                        # -- arg.pos_args[0] is a superset of idxs
                        #    TODO: slice out correct elements using
                        #    idxs_take, but more importantly - test this case.
                        raise NotImplementedError()
            new_pos_args = [foo(arg) for arg in orig.pos_args[2:]]
            new_named_args = [[aname, foo(arg)]
                    for aname, arg in orig.named_args]
            vnode = Apply(dist, new_pos_args, new_named_args, None)
            n_times = scope.len(idxs)
            if 'size' in dict(vnode.named_args):
                raise NotImplementedError('random node already has size')
            vnode.named_args.append(['size', n_times])
            # -- loop over all nodes that *use* this one, and change them
            for client in nodes[ii+1:]:
                client.replace_input(orig, vnode)
            if expr is orig:
                expr = vnode
            memo[orig] = vnode
    if return_memo:
        return expr, memo
    else:
        return expr


class VectorizeHelper(object):
    """
    Convert a pyll expression representing a single trial into a pyll
    expression representing multiple trials.

    The resulting multi-trial expression is not meant to be evaluated
    directly. It is meant to serve as the input to a suggest algo.

    idxs_memo - node in expr graph -> all elements we might need for it
    take_memo - node in expr graph -> all exprs retrieving computed elements

    """

    def __init__(self, expr, expr_idxs, build=True):
        self.expr = expr
        self.expr_idxs = expr_idxs
        self.dfs_nodes = dfs(expr)
        self.params = {}
        for ii, node in enumerate(self.dfs_nodes):
            if node.name == 'hyperopt_param':
                label = node.arg['label'].obj
                self.params[label] = node.arg['obj']
        # -- recursive construction
        #    This makes one term in each idxs, vals memo for every
        #    directed path through the switches in the graph.

        self.idxs_memo = {}  # node -> union, all idxs computed
        self.take_memo = {}  # node -> list of idxs_take retrieving node vals
        self.v_expr = self.build_idxs_vals(expr, expr_idxs)

        #TODO: graph-optimization pass to remove cruft:
        #  - unions of 1
        #  - unions of full sets with their subsets
        #  - idxs_take that can be merged

        self.assert_integrity_idxs_take()

    def assert_integrity_idxs_take(self):
        idxs_memo = self.idxs_memo
        take_memo = self.take_memo
        after = dfs(self.expr)
        assert after == self.dfs_nodes
        assert set(idxs_memo.keys()) == set(take_memo.keys())
        for node in idxs_memo:
            idxs = idxs_memo[node]
            assert idxs.name == 'array_union'
            vals = take_memo[node][0].pos_args[1]
            for take in take_memo[node]:
                assert take.name == 'idxs_take'
                assert [idxs, vals] == take.pos_args[:2]


    def build_idxs_vals(self, node, wanted_idxs):
        """
        This recursive procedure should be called on an output-node.
        """
        checkpoint_asserts = False
        def checkpoint():
            if checkpoint_asserts:
                self.assert_integrity_idxs_take()
                if node in self.idxs_memo:
                    toposort(self.idxs_memo[node])
                if node in self.take_memo:
                    for take in self.take_memo[node]:
                        toposort(take)

        checkpoint()

        # wanted_idxs are fixed, whereas idxs_memo
        # is full of unions, that can grow in subsequent recursive
        # calls to build_idxs_vals with node as argument.
        assert wanted_idxs != self.idxs_memo.get(node)

        # -- easy exit case
        if node.name == 'hyperopt_param':
            # -- ignore, not vectorizing
            return self.build_idxs_vals(node.arg['obj'], wanted_idxs)

        # -- easy exit case
        elif node.name == 'hyperopt_result':
            # -- ignore, not vectorizing
            return self.build_idxs_vals(node.arg['obj'], wanted_idxs)

        # -- literal case: always take from universal set
        elif node.name == 'literal':
            if node in self.idxs_memo:
                all_idxs, all_vals = self.take_memo[node][0].pos_args[:2]
                wanted_vals = scope.idxs_take(all_idxs, all_vals, wanted_idxs)
                self.take_memo[node].append(wanted_vals)
                checkpoint()
            else:
                # -- initialize idxs_memo to full set
                all_idxs = self.expr_idxs
                n_times = scope.len(all_idxs)
                # -- put array_union into graph for consistency, though it is
                # not necessary
                all_idxs = scope.array_union(all_idxs)
                self.idxs_memo[node] = all_idxs
                all_vals = scope.asarray(scope.repeat(n_times, node))
                wanted_vals = scope.idxs_take(all_idxs, all_vals, wanted_idxs)
                assert node not in self.take_memo
                self.take_memo[node] = [wanted_vals]
                checkpoint()
            return wanted_vals

        # -- switch case: complicated
        elif node.name == 'switch':
            if (node in self.idxs_memo
                    and wanted_idxs in self.idxs_memo[node].pos_args):
                # -- phew, easy case
                all_idxs, all_vals = self.take_memo[node][0].pos_args[:2]
                wanted_vals = scope.idxs_take(all_idxs, all_vals, wanted_idxs)
                self.take_memo[node].append(wanted_vals)
                checkpoint()
            else:
                # -- we need to add some indexes
                if node in self.idxs_memo:
                    all_idxs = self.idxs_memo[node]
                    assert all_idxs.name == 'array_union'
                    all_idxs.pos_args.append(wanted_idxs)
                else:
                    all_idxs = scope.array_union(wanted_idxs)

                choice = node.pos_args[0]
                all_choices = self.build_idxs_vals(choice, all_idxs)

                options = node.pos_args[1:]
                args_idxs = scope.vchoice_split(all_idxs, all_choices,
                        len(options))
                all_vals = scope.vchoice_merge(all_idxs, all_choices)
                for opt_ii, idxs_ii in zip(options, args_idxs):
                    all_vals.pos_args.append(
                            as_apply([
                                idxs_ii,
                                self.build_idxs_vals(opt_ii, idxs_ii),
                                ]))

                wanted_vals = scope.idxs_take(
                        all_idxs,     # -- may grow in future
                        all_vals,     # -- may be replaced in future
                        wanted_idxs)  # -- fixed.
                if node in self.idxs_memo:
                    assert self.idxs_memo[node].name == 'array_union'
                    self.idxs_memo[node].pos_args.append(wanted_idxs)
                    for take in self.take_memo[node]:
                        assert take.name == 'idxs_take'
                        take.pos_args[1] = all_vals
                    self.take_memo[node].append(wanted_vals)
                else:
                    self.idxs_memo[node] = all_idxs
                    self.take_memo[node] = [wanted_vals]
                checkpoint()

        # -- general case
        else:
            # -- this is a general node.
            #    It is generally handled with idxs_memo,
            #    but vectorize_stochastic may immediately transform it into
            #    a more compact form.
            if (node in self.idxs_memo
                    and wanted_idxs in self.idxs_memo[node].pos_args):
                # -- phew, easy case
                for take in self.take_memo[node]:
                    if take.pos_args[2] == wanted_idxs:
                        return take
                raise NotImplementedError('how did this happen?')
                #all_idxs, all_vals = self.take_memo[node][0].pos_args[:2]
                #wanted_vals = scope.idxs_take(all_idxs, all_vals, wanted_idxs)
                #self.take_memo[node].append(wanted_vals)
                #checkpoint()
            else:
                # XXX
                # -- determine if wanted_idxs is actually a subset of the idxs
                # that we are already computing.  This is not only an
                # optimization, but prevents the creation of cycles, which
                # would otherwise occur if we have a graph of the form
                # switch(f(a), g(a), 0). If there are other switches inside f
                # and g, does this get trickier?

                # -- assume we need to add some indexes
                checkpoint()
                if node in self.idxs_memo:
                    all_idxs = self.idxs_memo[node]

                else:
                    all_idxs = scope.array_union(wanted_idxs)
                checkpoint()

                all_vals = scope.idxs_map(all_idxs, node.name)
                for ii, aa in enumerate(node.pos_args):
                    all_vals.pos_args.append(as_apply([
                        all_idxs, self.build_idxs_vals(aa, all_idxs)]))
                    checkpoint()
                for ii, (nn, aa) in enumerate(node.named_args):
                    all_vals.named_args.append([nn, as_apply([
                        all_idxs, self.build_idxs_vals(aa, all_idxs)])])
                    checkpoint()
                all_vals = vectorize_stochastic(all_vals)

                checkpoint()
                wanted_vals = scope.idxs_take(
                        all_idxs,     # -- may grow in future
                        all_vals,     # -- may be replaced in future
                        wanted_idxs)  # -- fixed.
                if node in self.idxs_memo:
                    assert self.idxs_memo[node].name == 'array_union'
                    self.idxs_memo[node].pos_args.append(wanted_idxs)
                    toposort(self.idxs_memo[node])
                    # -- this catches the cycle bug mentioned above
                    for take in self.take_memo[node]:
                        assert take.name == 'idxs_take'
                        take.pos_args[1] = all_vals
                    self.take_memo[node].append(wanted_vals)
                else:
                    self.idxs_memo[node] = all_idxs
                    self.take_memo[node] = [wanted_vals]
                checkpoint()

        return wanted_vals

    def idxs_by_label(self):
        return dict([(name, self.idxs_memo[node])
                for name, node in self.params.items()])

    def vals_by_label(self):
        return dict([(name, self.take_memo[node][0].pos_args[1])
                for name, node in self.params.items()])



########NEW FILE########
