__FILENAME__ = contain
#!/usr/bin/env python
# encoding: utf-8

from collections import namedtuple
from gevent import Greenlet
from json import dumps, loads
from os.path import abspath
from service import UnitOfWork
from uow import UnitOfWorkFactory
import logging
import sys


######################################################################
## class definitions

class Container (object):
    """Container for a distrib Py UnitOfWork"""

    def __init__ (self):
        """constructor"""
        self.param_space = []

        ## NB: override to specify the data source
        self.file_name = abspath('dat/foo.tsv')
        ## NB: override to define the fields of a result tuple
        self.Result = namedtuple('Foo', ['bar', 'ugh'])


    def data_load (self, file_name):
        """load the specified data file"""
        ## NB: override to load the data file
        self.param_space.append(23)


    def run_calc (self, params):
        """run calculations based on the given param space element"""
        ## NB: override to calculate a job
        return self.Result(93, 11)


class ContainerUOWFactory (UnitOfWorkFactory):
    """UnitOfWorkFactory definition for distrib Py jobs"""

    def __init__ (self):
        #super(UnitOfWorkFactory, self).__init__()
        pass

    def instantiate_uow (self, uow_name, prefix):
        return ContainerUOW(uow_name, prefix, Container())


class ContainerUOW (UnitOfWork):
    """UnitOfWork definition for distrib Py jobs"""
    def __init__ (self, uow_name, prefix, container):
        super(ContainerUOW, self).__init__(uow_name, prefix)
        self._shard = {}

        self._container = container
        self.results = []


    def perform_task (self, payload):
        """perform a task consumed from the Worker.task_queue"""
        logging.debug(payload)

        if "job" in payload:
            result = self._container.run_calc(payload["job"])
            self.results.append(result)
            logging.debug(result)
        elif "nop" in payload:
            pass


    def orchestrate (self, framework):
        """initialize shards, then iterate until all percentiles are trained"""
        framework.send_ring_rest("shard/init", {})
        framework.send_ring_rest("data/load", { "file": self._container.file_name })

        self._container.data_load(self._container.file_name)
        framework.phase_barrier()

        while len(self._container.param_space) > 0:
            for shard_id, shard_uri in framework.get_worker_list():
                if len(self._container.param_space) > 0:
                    params = self._container.param_space.pop(0)
                    framework.send_worker_rest(shard_id, shard_uri, "calc/run", { "params": params })

        framework.phase_barrier()

        # report the results
        needs_header = True

        for shard_msg in framework.send_ring_rest("shard/dump", {}):
            payload = loads(shard_msg)

            if needs_header:
                print "\t".join(payload["fields"])
                needs_header = False

            for result in payload["results"]:
                print "\t".join(map(lambda x: str(x), result))


    def handle_endpoints (self, worker, uri_path, env, start_response, body):
        """UnitOfWork REST endpoints, delegated from the Worker"""
        if uri_path == '/shard/init':
            # initialize the shard
            Greenlet(self.shard_init, worker, env, start_response, body).start()
            return True
        elif uri_path == '/data/load':
            # load the data
            Greenlet(self.data_load, worker, env, start_response, body).start()
            return True
        elif uri_path == '/calc/run':
            # run the calculations
            Greenlet(self.calc_run, worker, env, start_response, body).start()
            return True
        elif uri_path == '/shard/dump':
            # dump the results
            Greenlet(self.shard_dump, worker, env, start_response, body).start()
            return True
        else:
            return False


    ######################################################################
    ## job-specific REST endpoints implemented as gevent coroutines

    def shard_init (self, *args, **kwargs):
        """initialize a shard"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            self.set_ring(worker.shard_id, worker.ring)
            worker.prep_task_queue()

            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)


    def data_load (self, *args, **kwargs):
        """prepare for calculations"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            with worker.wrap_task_event():
                # HTTP response first, then initiate long-running task
                start_response('200 OK', [('Content-Type', 'text/plain')])
                body.put("Bokay\r\n")
                body.put(StopIteration)

                # load the data file
                logging.debug(payload["file"])
                self._container.data_load(payload["file"])

                # put a NOP into the queue, so we'll have something to join on
                worker.put_task_queue({ "nop": True })


    def calc_run (self, *args, **kwargs):
        """enqueue one calculation"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            with worker.wrap_task_event():
                # caller expects JSON response
                start_response('200 OK', [('Content-Type', 'application/json')])
                body.put(dumps({ "ok": 1 }))
                body.put("\r\n")
                body.put(StopIteration)

                # put the params into the queue
                worker.put_task_queue({ "job": payload["params"] })


    def shard_dump (self, *args, **kwargs):
        """dump the results"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            start_response('200 OK', [('Content-Type', 'application/json')])
            body.put(dumps({ "fields": self.results[0]._fields, "results": self.results }))
            body.put("\r\n")
            body.put(StopIteration)


if __name__=='__main__':
    ## test GA in standalone-mode, without distributed services
    pass

########NEW FILE########
__FILENAME__ = exelixi
#!/usr/bin/env python
# encoding: utf-8

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# author: Paco Nathan
# https://github.com/ceteri/exelixi


from argparse import ArgumentParser
from os.path import abspath
from service import Framework, Worker
from util import get_master_leader, get_master_state, pipe_slave_list
import logging
import sys


######################################################################
## globals

APP_NAME = "Exelixi"


######################################################################
## command line arguments

def parse_cli_args ():
    parser = ArgumentParser(prog="Exelixi", usage="one of the operational modes shown below...", add_help=True,
                            description="Exelixi, a distributed framework for genetic algorithms, based on Apache Mesos")

    group1 = parser.add_argument_group("Mesos Framework", "run as a distributed framework on an Apache Mesos cluster")
    group1.add_argument("-m", "--master", metavar="HOST:PORT", nargs=1,
                        help="location for one of the masters")
    group1.add_argument("-w", "--workers", nargs=1, type=int, default=[1],
                        help="number of workers to be launched")

    group1.add_argument("--cpu", nargs=1, type=int, default=[1],
                        help="CPU allocation per worker, as CPU count")
    group1.add_argument("--mem", nargs=1, type=int, default=[32],
                        help="MEM allocation per worker, as MB/shard")

    group2 = parser.add_argument_group("Mesos Executor", "run as an Apache Mesos executor (using no arguments)")

    group3 = parser.add_argument_group("Standalone Framework", "run as a test framework in standalone mode")
    group3.add_argument("-s", "--slaves", nargs="+", metavar="HOST:PORT",
                        help="list of slaves (HOST:PORT) on which to run workers")

    group4 = parser.add_argument_group("Standalone Worker", "run as a test worker in standalone mode")
    group4.add_argument("-p", "--port", nargs=1, metavar="PORT",
                        help="port number to use for this service")

    group5 = parser.add_argument_group("Nodes", "enumerate the slave nodes in an Apache Mesos cluster")
    group5.add_argument("-n", "--nodes", nargs="?", metavar="HOST:PORT",
                        help="location for one of the Apache Mesos masters")

    parser.add_argument("--uow", nargs=1, metavar="PKG.CLASS", default=["uow.UnitOfWorkFactory"],
                        help="subclassed UnitOfWork definition")

    parser.add_argument("--prefix", nargs=1, default=["hdfs://exelixi"],
                        help="path prefix for durable storage")

    parser.add_argument("--log", nargs=1, default=["DEBUG"],
                        help="logging level: INFO, DEBUG, WARNING, ERROR, CRITICAL")

    return parser.parse_args()


if __name__=='__main__':
    # interpret CLI arguments
    args = parse_cli_args()

    if args.nodes:
        # query and report the slave list, then exit...
        # NB: one per line, to handle large clusters gracefully
        pipe_slave_list(args.nodes)
        sys.exit(0)

    # set up logging
    numeric_log_level = getattr(logging, args.log[0], None)

    if not isinstance(numeric_log_level, int):
        raise ValueError("Invalid log level: %s" % loglevel)

    logging.basicConfig(format="%(asctime)s\t%(levelname)s\t%(message)s", 
                        filename="exelixi.log", 
                        filemode="w",
                        level=numeric_log_level
                        )
    logging.debug(args)

    # report settings for options
    opts = []

    if args.uow:
        opts.append(" ...using %s for the UnitOfWork definitions" % (args.uow[0]))

    if args.prefix:
        opts.append(" ...using %s for the path prefix in durable storage" % (args.prefix[0]))

    # handle the different operational modes
    if args.master:
        logging.info("%s: running a Framework atop an Apache Mesos cluster", APP_NAME)
        logging.info(" ...with master %s and %d workers(s)", args.master[0], args.workers[0])

        for x in opts:
            logging.info(x)

        try:
            from resource import MesosScheduler

            master_uri = get_master_leader(args.master[0])
            exe_path = abspath(sys.argv[0])

            # run Mesos driver to launch Framework and manage resource offers
            driver = MesosScheduler.start_framework(master_uri, exe_path, args.workers[0], args.uow[0], args.prefix[0], args.cpu[0], args.mem[0])
            MesosScheduler.stop_framework(driver)
        except ImportError as e:
            logging.critical("Python module 'mesos' has not been installed", exc_info=True)
            raise

    elif args.slaves:
        logging.info("%s: running a Framework in standalone mode", APP_NAME)
        logging.info(" ...with slave(s) %s", args.slaves)

        for x in opts:
            logging.info(x)

        # run UnitOfWork orchestration via REST endpoints on the workers
        fra = Framework(args.uow[0], args.prefix[0])
        fra.set_worker_list(args.slaves)
        fra.orchestrate_uow()

    elif args.port:
        logging.info("%s: running a worker service on port %s", APP_NAME, args.port[0])

        try:
            svc = Worker(port=int(args.port[0]))
            svc.shard_start()
        except KeyboardInterrupt:
            pass

    else:
        logging.info("%s: running an Executor on an Apache Mesos slave", APP_NAME)

        try:
            from resource import MesosExecutor
            MesosExecutor.run_executor()
        except ImportError as e:
            logging.critical("Python module 'mesos' has not been installed", exc_info=True)
            raise
        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = ga
#!/usr/bin/env python
# encoding: utf-8

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# author: Paco Nathan
# https://github.com/ceteri/exelixi


from hat_trie import Trie
from collections import Counter
from gevent import Greenlet
from hashlib import sha224
from hashring import HashRing
from json import dumps, loads
from monoids import dictm
from random import random, sample
from service import UnitOfWork
from string import ascii_lowercase
from util import instantiate_class, post_distrib_rest
import logging
import sys


######################################################################
## class definitions

class Population (UnitOfWork):
    def __init__ (self, uow_name, prefix, indiv_instance):
        super(Population, self).__init__(uow_name, prefix)

        logging.debug("INIT POPULATION")

        self.indiv_class = indiv_instance.__class__
        self.total_indiv = 0
        self.current_gen = 0

        self._shard = {}
        self._trie = Trie(ascii_lowercase)


    def perform_task (self, payload):
        """perform a task consumed from the Worker.task_queue"""
        key = payload["key"]
        gen = payload["gen"]
        feature_set = payload["feature_set"]
        self.receive_reify(key, gen, feature_set)


    def orchestrate (self, framework):
        """
        initialize a Population of unique Individuals at generation 0,
        then iterate N times or until a "good enough" solution is found
        """
        framework.send_ring_rest("pop/init", {})
        framework.send_ring_rest("pop/gen", {})

        while True:
            framework.phase_barrier()

            if self.current_gen == self.uow_factory.n_gen:
                break

            # determine the fitness cutoff threshold
            self.total_indiv = 0
            hist = {}

            for shard_msg in framework.send_ring_rest("pop/hist", {}):
                logging.debug(shard_msg)
                payload = loads(shard_msg)
                self.total_indiv += payload["total_indiv"]
                hist = dictm.fold([hist, payload["hist"]])

            # test for the terminating condition
            hist_items = map(lambda x: (float(x[0]), x[1],), sorted(hist.items(), reverse=True))

            if self.test_termination(self.current_gen, hist_items):
                break

            ## NB: TODO save Framework state to Zookeeper

            # apply the fitness cutoff and breed "children" for the
            # next generation
            fitness_cutoff = self.get_fitness_cutoff(hist_items)
            framework.send_ring_rest("pop/next", { "current_gen": self.current_gen, "fitness_cutoff": fitness_cutoff })
            self.current_gen += 1

        # report the best Individuals in the final result
        results = []

        for l in framework.send_ring_rest("pop/enum", { "fitness_cutoff": fitness_cutoff }):
            results.extend(loads(l))

        results.sort(reverse=True)

        for x in results:
            # print results to stdout
            print "\t".join(x)


    def handle_endpoints (self, worker, uri_path, env, start_response, body):
        """UnitOfWork REST endpoints, delegated from the Worker"""
        if uri_path == '/pop/init':
            # initialize the Population subset on this shard
            Greenlet(self.pop_init, worker, env, start_response, body).start()
            return True
        elif uri_path == '/pop/gen':
            # create generation 0 in this shard
            Greenlet(self.pop_gen, worker, env, start_response, body).start()
            return True
        elif uri_path == '/pop/hist':
            # calculate a partial histogram for the fitness distribution
            Greenlet(self.pop_hist, worker, env, start_response, body).start()
            return True
        elif uri_path == '/pop/next':
            # attempt to run another generation
            Greenlet(self.pop_next, worker, env, start_response, body).start()
            return True
        elif uri_path == '/pop/enum':
            # enumerate the Individuals in this shard of the Population
            Greenlet(self.pop_enum, worker, env, start_response, body).start()
            return True
        elif uri_path == '/pop/reify':
            # test/add a new Individual into the Population (birth)
            Greenlet(self.pop_reify, worker, env, start_response, body).start()
            return True
        else:
            return False


    ######################################################################
    ## GA-specific REST endpoints implemented as gevent coroutines

    def pop_init (self, *args, **kwargs):
        """initialize a Population of unique Individuals on this shard"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            self.set_ring(worker.shard_id, worker.ring)
            worker.prep_task_queue()

            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)


    def pop_gen (self, *args, **kwargs):
        """create generation 0 of Individuals in this shard of the Population"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            with worker.wrap_task_event():
                # HTTP response first, then initiate long-running task
                start_response('200 OK', [('Content-Type', 'text/plain')])
                body.put("Bokay\r\n")
                body.put(StopIteration)

                self.populate(0)


    def pop_hist (self, *args, **kwargs):
        """calculate a partial histogram for the fitness distribution"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            start_response('200 OK', [('Content-Type', 'application/json')])
            body.put(dumps({ "total_indiv": self.total_indiv, "hist": self.get_part_hist() }))
            body.put("\r\n")
            body.put(StopIteration)


    def pop_next (self, *args, **kwargs):
        """iterate N times or until a 'good enough' solution is found"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            with worker.wrap_task_event():
                # HTTP response first, then initiate long-running task
                start_response('200 OK', [('Content-Type', 'text/plain')])
                body.put("Bokay\r\n")
                body.put(StopIteration)

                current_gen = payload["current_gen"]
                fitness_cutoff = payload["fitness_cutoff"]
                self.next_generation(current_gen, fitness_cutoff)


    def pop_enum (self, *args, **kwargs):
        """enumerate the Individuals in this shard of the Population"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            fitness_cutoff = payload["fitness_cutoff"]

            start_response('200 OK', [('Content-Type', 'application/json')])
            body.put(dumps(self.enum(fitness_cutoff)))
            body.put("\r\n")
            body.put(StopIteration)


    def pop_reify (self, *args, **kwargs):
        """test/add a newly generated Individual into the Population (birth)"""
        worker = args[0]
        payload, start_response, body = worker.get_response_context(args[1:])

        if worker.auth_request(payload, start_response, body):
            worker.put_task_queue(payload)

            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)


    ######################################################################
    ## Individual lifecycle within the local subset of the Population

    def populate (self, current_gen):
        """initialize the population"""
        for _ in xrange(self.uow_factory.n_pop):
            # constructor pattern
            indiv = self.indiv_class()
            indiv.populate(current_gen, self.uow_factory.generate_features())

            # add the generated Individual to the Population
            # failure semantics: must filter nulls from initial population
            self.reify(indiv)


    def reify (self, indiv):
        """test/add a newly generated Individual into the Population (birth)"""
        neighbor_shard_id = None
        shard_uri = None

        if self._hash_ring:
            neighbor_shard_id = self._hash_ring.get_node(indiv.key)

            if neighbor_shard_id != self._shard_id:
                shard_uri = self._shard_dict[neighbor_shard_id]

        # distribute the tasks in this phase throughout the HashRing,
        # using a remote task_queue with synchronization based on a
        # barrier pattern

        if shard_uri:
            msg = { "key": indiv.key, "gen": indiv.gen, "feature_set": loads(indiv.get_json_feature_set()) }
            lines = post_distrib_rest(self.prefix, neighbor_shard_id, shard_uri, "pop/reify", msg)
            return False
        else:
            return self._reify_locally(indiv)


    def receive_reify (self, key, gen, feature_set):
        """test/add a received reify request """
        indiv = self.indiv_class()
        indiv.populate(gen, feature_set)
        self._reify_locally(indiv)


    def _reify_locally (self, indiv):
        """test/add a newly generated Individual into the Population locally (birth)"""
        if not (indiv.key in self._trie):
            self._trie[indiv.key] = 1
            self.total_indiv += 1

            # potentially an expensive operation, deferred until remote reification
            indiv.get_fitness(self.uow_factory, force=True)
            self._shard[indiv.key] = indiv

            return True
        else:
            return False


    def evict (self, indiv):
        """remove an Individual from the Population (death)"""
        if indiv.key in self._shard:
            # Individual only needs to be removed locally
            del self._shard[indiv.key]

            # NB: serialize to disk (write behinds)
            url = self._get_storage_path(indiv)


    def get_part_hist (self):
        """tally counts for the partial histogram of the fitness distribution"""
        l = [ round(indiv.get_fitness(self.uow_factory, force=False), self.uow_factory.hist_granularity) for indiv in self._shard.values() ]
        return dict(Counter(l))


    def get_fitness_cutoff (self, hist_items):
        """determine fitness cutoff (bin lower bounds) for the parent selection filter"""
        logging.debug("fit: %s", hist_items)

        n_indiv = sum([ count for bin, count in hist_items ])
        part_sum = 0
        break_next = False

        for bin, count in hist_items:
            if break_next:
                break

            part_sum += count
            percentile = part_sum / float(n_indiv)
            break_next = percentile >= self.uow_factory.selection_rate

        logging.debug("fit: percentile %f part_sum %d n_indiv %d bin %f", percentile, part_sum, n_indiv, bin)
        return bin


    def _get_storage_path (self, indiv):
        """create a path for durable storage of an Individual"""
        return self.prefix + "/" + indiv.key


    def _boost_diversity (self, current_gen, indiv):
        """randomly select other individuals and mutate them, to promote genetic diversity"""
        if self.uow_factory.mutation_rate > random():
            indiv.mutate(self, current_gen, self.uow_factory)
        elif len(self._shard.values()) >= 3:
            # NB: ensure that at least three parents remain in each
            # shard per generation
            self.evict(indiv)


    def _select_parents (self, current_gen, fitness_cutoff):
        """select the parents for the next generation"""
        partition = map(lambda x: (round(x.get_fitness(), self.uow_factory.hist_granularity) > fitness_cutoff, x), self._shard.values())
        good_fit = map(lambda x: x[1], filter(lambda x: x[0], partition))
        poor_fit = map(lambda x: x[1], filter(lambda x: not x[0], partition))

        # randomly select other individuals to promote genetic
        # diversity, while removing the remnant
        for indiv in poor_fit:
            self._boost_diversity(current_gen, indiv)

        return self._shard.values()


    def next_generation (self, current_gen, fitness_cutoff):
        """select/mutate/crossover parents to produce a new generation"""
        parents = self._select_parents(current_gen, fitness_cutoff)

        for _ in xrange(self.uow_factory.n_pop - len(parents)):
            f, m = sample(parents, 2) 
            success = f.breed(self, current_gen, m, self.uow_factory)

        # backfill to replenish / avoid the dreaded Population collapse
        new_count = 0

        for _ in xrange(self.uow_factory.n_pop - len(self._shard.values())):
            # constructor pattern
            indiv = self.indiv_class()
            indiv.populate(current_gen, self.uow_factory.generate_features())
            self.reify(indiv)

        logging.info("gen\t%d\tshard\t%s\tsize\t%d\ttotal\t%d", current_gen, self._shard_id, len(self._shard.values()), self.total_indiv)


    def test_termination (self, current_gen, hist):
        """evaluate the terminating condition for this generation and report progress"""
        return self.uow_factory.test_termination(current_gen, hist, self.total_indiv)


    def enum (self, fitness_cutoff):
        """enum all Individuals that exceed the given fitness cutoff"""
        return [[ "indiv", "%0.4f" % indiv.get_fitness(), str(indiv.gen), indiv.get_json_feature_set() ]
                for indiv in filter(lambda x: x.get_fitness() >= fitness_cutoff, self._shard.values()) ]


class Individual (object):
    def __init__ (self):
        """create an Individual member of the Population"""
        self.gen = None
        self.key = None
        self._feature_set = None
        self._fitness = None


    def get_fitness (self, uow_factory=None, force=False):
        """determine the fitness ranging [0.0, 1.0]; higher is better"""
        if uow_factory and uow_factory.use_force(force):
            # potentially the most expensive operation, deferred with careful consideration
            self._fitness = uow_factory.get_fitness(self._feature_set)

        return self._fitness


    def get_json_feature_set (self):
        """dump the feature set as a JSON string"""
        return dumps(tuple(self._feature_set))


    def populate (self, gen, feature_set):
        """populate the instance variables"""
        self.gen = gen
        self._feature_set = feature_set

        # create a unique key using a SHA-3 digest of the JSON representing this feature set
        m = sha224()
        m.update(self.get_json_feature_set())
        self.key = unicode(m.hexdigest())


    def mutate (self, pop, gen, uow_factory):
        """attempt to mutate the feature set"""
        # constructor pattern
        mutant = self.__class__()
        mutant.populate(gen, uow_factory.mutate_features(self._feature_set))

        # add the mutant Individual to the Population, but remove its prior self
        # failure semantics: ignore, mutation rate is approx upper bounds
        if pop.reify(mutant):
            pop.evict(self)
            return True
        else:
            return False


    def breed (self, pop, gen, mate, uow_factory):
        """breed with a mate to produce a child"""
        # constructor pattern
        child = self.__class__()
        child.populate(gen, uow_factory.breed_features(self._feature_set, mate._feature_set))

        # add the child Individual to the Population
        # failure semantics: ignore, the count will rebalance over the hash ring
        return pop.reify(child)


if __name__=='__main__':
    ## test GA in standalone-mode, without distributed services

    # parse command line options
    if len(sys.argv) < 2:
        uow_name = "uow.UnitOfWorkFactory"
    else:
        uow_name = sys.argv[1]

    uow_factory = instantiate_class(uow_name)

    # initialize a Population of unique Individuals at generation 0
    uow = uow_factory.instantiate_uow(uow_name, "/tmp/exelixi")
    uow.populate(uow.current_gen)
    fitness_cutoff = 0

    # iterate N times or until a "good enough" solution is found
    while uow.current_gen < uow_factory.n_gen:
        hist = uow.get_part_hist()
        hist_items = map(lambda x: (float(x[0]), x[1],), sorted(hist.items(), reverse=True))

        if uow.test_termination(uow.current_gen, hist_items):
            break

        fitness_cutoff = uow.get_fitness_cutoff(hist_items)
        uow.next_generation(uow.current_gen, fitness_cutoff)

        uow.current_gen += 1

    # report summary
    for x in sorted(uow.enum(fitness_cutoff), reverse=True):
        print "\t".join(x)

########NEW FILE########
__FILENAME__ = hashring
#!/usr/bin/env python
# encoding: utf-8

# Copyright (c) 2012, Amir Salihefendic
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# 1. Redistributions of source code must retain the above copyright notice, this 
# list of conditions and the following disclaimer.
# 
# 2. Redistributions in binary form must reproduce the above copyright notice, 
# this list of conditions and the following disclaimer in the documentation 
# and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.

# author: Amir Salihefendic
# http://amix.dk/blog/post/19367


import md5


class HashRing(object):

    def __init__(self, nodes=None, replicas=3):
        """Manages a hash ring.

        `nodes` is a list of objects that have a proper __str__ representation.
        `replicas` indicates how many virtual points should be used pr. node,
        replicas are required to improve the distribution.
        """
        self.replicas = replicas

        self.ring = dict()
        self._sorted_keys = []

        if nodes:
            for node in nodes:
                self.add_node(node)

    def add_node(self, node):
        """Adds a `node` to the hash ring (including a number of replicas).
        """
        for i in xrange(0, self.replicas):
            key = self.gen_key('%s:%s' % (node, i))
            self.ring[key] = node
            self._sorted_keys.append(key)

        self._sorted_keys.sort()

    def remove_node(self, node):
        """Removes `node` from the hash ring and its replicas.
        """
        for i in xrange(0, self.replicas):
            key = self.gen_key('%s:%s' % (node, i))
            del self.ring[key]
            self._sorted_keys.remove(key)

    def get_node(self, string_key):
        """Given a string key a corresponding node in the hash ring is returned.

        If the hash ring is empty, `None` is returned.
        """
        return self.get_node_pos(string_key)[0]

    def get_node_pos(self, string_key):
        """Given a string key a corresponding node in the hash ring is returned
        along with it's position in the ring.

        If the hash ring is empty, (`None`, `None`) is returned.
        """
        if not self.ring:
            return None, None

        key = self.gen_key(string_key)

        nodes = self._sorted_keys
        for i in xrange(0, len(nodes)):
            node = nodes[i]
            if key <= node:
                return self.ring[node], i

        return self.ring[nodes[0]], 0

    def get_nodes(self, string_key):
        """Given a string key it returns the nodes as a generator that can hold the key.

        The generator is never ending and iterates through the ring
        starting at the correct position.
        """
        if not self.ring:
            yield None, None

        node, pos = self.get_node_pos(string_key)
        for key in self._sorted_keys[pos:]:
            yield self.ring[key]

        while True:
            for key in self._sorted_keys:
                yield self.ring[key]

    def gen_key(self, key):
        """Given a string key it returns a long value,
        this long value represents a place on the hash ring.

        md5 is currently used because it mixes well.
        """
        m = md5.new()
        m.update(key)
        return long(m.hexdigest(), 16)


if __name__=='__main__':
    import random

    memcache_servers = ['192.168.0.246:11212',
                        '192.168.0.247:11212',
                        '192.168.0.249:11212']

    ring = HashRing(memcache_servers)

    print ring.get_node('my_key')
    print ring.get_node('foo bar')
    print ring.get_node(str(random.random()))

########NEW FILE########
__FILENAME__ = monoids
#!/usr/bin/env python
# encoding: utf-8

# Francisco Mota, 2011-11-09
# http://fmota.eu/blog/monoids-in-python.html
# see also: http://arxiv.org/abs/1304.7544

class Monoid (object):
    def __init__ (self, null, lift, op):
        self.null = null
        self.lift = lift
        self.op   = op
 
    def fold (self, xs):
        if hasattr(xs, "__fold__"):
            return xs.__fold__(self)
        else:
            return reduce(self.op, (self.lift(x) for x in xs), self.null)
 
    def __call__ (self, *args):
        return self.fold(args)
 
    def star (self):
        return Monoid(self.null, self.fold, self.op)


def dict_op (a, b):
    for key, val in b.items():
        if not key in a:
            a[key] = val
        else:
            a[key] += val

    return a


summ   = Monoid(0,  lambda x: x,      lambda a,b: a+b)
joinm  = Monoid('', lambda x: str(x), lambda a,b: a+b)
listm  = Monoid([], lambda x: [x],    lambda a,b: a+b)
tuplem = Monoid((), lambda x: (x,),   lambda a,b: a+b)
lenm   = Monoid(0,  lambda x: 1,      lambda a,b: a+b)
prodm  = Monoid(1,  lambda x: x,      lambda a,b: a*b)
dictm  = Monoid({}, lambda x: x,      lambda a,b: dict_op(a, b))


if __name__=='__main__':
    x1 = { "a": 2, "b": 3 }
    x2 = { "b": 2, "c": 7 }

    print x1, x2
    print dictm.fold([x1, x2])

########NEW FILE########
__FILENAME__ = resource
#!/usr/bin/env python
# encoding: utf-8

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# author: Paco Nathan
# https://github.com/ceteri/exelixi


from json import dumps, loads
from service import Framework, Worker, WorkerInfo
from threading import Thread
from util import get_telemetry
from uuid import uuid1
import logging
import mesos
import mesos_pb2
import os
import subprocess
import sys
import time


######################################################################
## class definitions

class MesosScheduler (mesos.Scheduler):
    # https://github.com/apache/mesos/blob/master/src/python/src/mesos.py

    def __init__ (self, executor, exe_path, n_workers, uow_name, prefix, cpu_alloc, mem_alloc):
        self.executor = executor
        self.taskData = {}
        self.tasksLaunched = 0
        self.tasksFinished = 0
        self.messagesSent = 0
        self.messagesReceived = 0

        # resource requirements
        self._cpu_alloc = cpu_alloc
        self._mem_alloc = mem_alloc

        # protected members to customize for Exelixi needs
        self._executors = {}
        self._exe_path = exe_path
        self._n_workers = n_workers
        self._uow_name = uow_name
        self._prefix = prefix


    def registered (self, driver, frameworkId, masterInfo):
        """
        Invoked when the scheduler successfully registers with a Mesos
        master. It is called with the frameworkId, a unique ID
        generated by the master, and the masterInfo which is
        information about the master itself.
        """

        logging.info("registered with framework ID %s", frameworkId.value)


    def resourceOffers (self, driver, offers):
        """
        Invoked when resources have been offered to this framework. A
        single offer will only contain resources from a single slave.
        Resources associated with an offer will not be re-offered to
        _this_ framework until either (a) this framework has rejected
        those resources (see SchedulerDriver.launchTasks) or (b) those
        resources have been rescinded (see Scheduler.offerRescinded).
        Note that resources may be concurrently offered to more than
        one framework at a time (depending on the allocator being
        used).  In that case, the first framework to launch tasks
        using those resources will be able to use them while the other
        frameworks will have those resources rescinded (or if a
        framework has already launched tasks with those resources then
        those tasks will fail with a TASK_LOST status and a message
        saying as much).
        """

        logging.debug("Mesos Scheduler: received %d resource offers", len(offers))

        for offer in offers:
            tasks = []
            logging.debug("Mesos Scheduler: received resource offer %s", offer.id.value)

            ## NB: currently we force 'offer.hostname' to be unique per Executor...
            ## could be changed, but we'd need to juggle the service port numbers

            if self.tasksLaunched < self._n_workers and offer.hostname not in self._executors:
                tid = self.tasksLaunched
                self.tasksLaunched += 1
                logging.debug("Mesos Scheduler: accepting offer on slave %s to start task %d", offer.hostname, tid)

                task = mesos_pb2.TaskInfo()
                task.task_id.value = str(tid)
                task.slave_id.value = offer.slave_id.value
                task.name = "task %d" % tid
                task.executor.MergeFrom(self.executor)

                cpus = task.resources.add()
                cpus.name = "cpus"
                cpus.type = mesos_pb2.Value.SCALAR
                cpus.scalar.value = self._cpu_alloc

                mem = task.resources.add()
                mem.name = "mem"
                mem.type = mesos_pb2.Value.SCALAR
                mem.scalar.value = self._mem_alloc

                tasks.append(task)
                self.taskData[task.task_id.value] = (offer.slave_id, task.executor.executor_id)

                # record and report the Mesos slave node's telemetry and state
                self._executors[offer.hostname] = WorkerInfo(offer, task)

                for exe in self._executors.values():
                    logging.debug(exe.report())

            # request the driver to launch the task
            driver.launchTasks(offer.id, tasks)


    def statusUpdate (self, driver, update):
        """
        Invoked when the status of a task has changed (e.g., a slave
        is lost and so the task is lost, a task finishes and an
        executor sends a status update saying so, etc.) Note that
        returning from this callback acknowledges receipt of this
        status update.  If for whatever reason the scheduler aborts
        during this callback (or the process exits) another status
        update will be delivered.  Note, however, that this is
        currently not true if the slave sending the status update is
        lost or fails during that time.
        """

        logging.debug("Mesos Scheduler: task %s is in state %d", update.task_id.value, update.state)

        if update.state == mesos_pb2.TASK_FINISHED:
            self.tasksFinished += 1
            slave_id, executor_id = self.taskData[update.task_id.value]

            # update WorkerInfo with telemetry from initial discovery task
            telemetry = loads(str(update.data))
            logging.info("telemetry from slave %s, executor %s\n%s", slave_id.value, executor_id.value, str(update.data))

            exe = self.lookup_executor(slave_id.value, executor_id.value)
            exe.ip_addr = telemetry["ip_addr"]

            ## NB: TODO make the service port a parameter
            exe.port = Worker.DEFAULT_PORT

            if self.tasksFinished == self._n_workers:
                logging.info("Mesos Scheduler: %d init tasks completed", self._n_workers)

            # request to launch service as a child process
            self.messagesSent += 1
            message = str(dumps([ self._exe_path, "-p", exe.port ]))
            driver.sendFrameworkMessage(executor_id, slave_id, message)


    def frameworkMessage (self, driver, executorId, slaveId, message):
        """
        Invoked when an executor sends a message. These messages are
        best effort; do not expect a framework message to be
        retransmitted in any reliable fashion.
        """

        self.messagesReceived += 1
        logging.info("Mesos Scheduler: slave %s executor %s", slaveId.value, executorId.value)
        logging.info("message %d received: %s", self.messagesReceived, str(message))

        if self.messagesReceived == self._n_workers:
            if self.messagesReceived != self.messagesSent:
                logging.critical("Mesos Scheduler: framework messages lost! sent %d received %d", self.messagesSent, self.messagesReceived)
                sys.exit(1)

            for exe in self._executors.values():
                logging.debug(exe.report())

            logging.info("all worker services launched and init tasks completed")
            exe_info = self._executors.values()
            worker_list = [ exe.get_shard_uri() for exe in exe_info ]

            # run UnitOfWork orchestration via REST endpoints on the workers
            fra = Framework(self._uow_name, self._prefix)
            fra.set_worker_list(worker_list, exe_info)

            time.sleep(1)
            fra.orchestrate_uow()

            # shutdown the Executors after the end of an algorithm run
            driver.stop()


    def lookup_executor (self, slave_id, executor_id):
        """lookup the Executor based on IDs"""
        for exe in self._executors.values():
            if exe.slave_id == slave_id:
                return exe


    @staticmethod
    def start_framework (master_uri, exe_path, n_workers, uow_name, prefix, cpu_alloc, mem_alloc):
        # initialize an executor
        executor = mesos_pb2.ExecutorInfo()
        executor.executor_id.value = uuid1().hex
        executor.command.value = exe_path
        executor.name = "Exelixi Executor"
        executor.source = "per-job build"

        ## NB: TODO download tarball/container from HDFS
        #uri = executor.command.uris.add()
        #uri.executable = false
        #uri.value = "hdfs://namenode/exelixi/exelixi.tgz"

        # initialize the framework
        framework = mesos_pb2.FrameworkInfo()
        framework.user = "" # have Mesos fill in the current user
        framework.name = "Exelixi Framework"

        if os.getenv("MESOS_CHECKPOINT"):
            logging.debug("Mesos Scheduler: enabling checkpoint for the framework")
            framework.checkpoint = True
    
        # create a scheduler and capture the command line options
        sched = MesosScheduler(executor, exe_path, n_workers, uow_name, prefix, cpu_alloc, mem_alloc)

        # initialize a driver
        if os.getenv("MESOS_AUTHENTICATE"):
            logging.debug("Mesos Scheduler: enabling authentication for the framework")
    
            if not os.getenv("DEFAULT_PRINCIPAL"):
                logging.critical("Mesos Scheduler: expecting authentication principal in the environment")
                sys.exit(1);

            if not os.getenv("DEFAULT_SECRET"):
                logging.critical("Mesos Scheduler: expecting authentication secret in the environment")
                sys.exit(1);

            credential = mesos_pb2.Credential()
            credential.principal = os.getenv("DEFAULT_PRINCIPAL")
            credential.secret = os.getenv("DEFAULT_SECRET")

            driver = mesos.MesosSchedulerDriver(sched, framework, master_uri, credential)
        else:
            driver = mesos.MesosSchedulerDriver(sched, framework, master_uri)

        return driver


    @staticmethod
    def stop_framework (driver):
        """ensure that the driver process terminates"""
        status = 0 if driver.run() == mesos_pb2.DRIVER_STOPPED else 1
        driver.stop();
        sys.exit(status)


class MesosExecutor (mesos.Executor):
    # https://github.com/apache/mesos/blob/master/src/python/src/mesos.py

    def launchTask (self, driver, task):
        """
        Invoked when a task has been launched on this executor
        (initiated via Scheduler.launchTasks).  Note that this task
        can be realized with a thread, a process, or some simple
        computation, however, no other callbacks will be invoked on
        this executor until this callback has returned.
        """

        ## NB: the following code runs on the Mesos slave (source of the resource offer)

        def run_task():
            logging.debug("Mesos Executor: requested task %s", task.task_id.value)

            update = mesos_pb2.TaskStatus()
            update.task_id.value = task.task_id.value
            update.state = mesos_pb2.TASK_RUNNING
            update.data = str("running discovery task")

            logging.debug(update.data)
            driver.sendStatusUpdate(update)

            update = mesos_pb2.TaskStatus()
            update.task_id.value = task.task_id.value
            update.state = mesos_pb2.TASK_FINISHED

            ## NB: TODO test port availability...
            update.data = str(dumps(get_telemetry(), indent=4))

            ## NB: TODO download tarball/container for service launch

            # notify scheduler: ready to launch service
            logging.debug(update.data)
            driver.sendStatusUpdate(update)

        # now create a thread to run the requested task: run tasks in
        # new threads or processes, rather than inside launchTask...
        # NB: gevent/coroutines/Greenlets conflict here... must run
        # those in a child shell process

        thread = Thread(target=run_task)
        thread.start()


    def frameworkMessage (self, driver, message):
        """
        Invoked when a framework message has arrived for this
        executor. These messages are best effort; do not expect a
        framework message to be retransmitted in any reliable fashion.
        """

        # launch service
        logging.info("Mesos Executor: service launched: %s", message)
        subprocess.Popen(loads(message))

        # notify scheduler: service was successfully launched
        driver.sendFrameworkMessage(str("service launched"))


    @staticmethod
    def run_executor ():
        """run the executor until it is stopped externally by the framework"""
        driver = mesos.MesosExecutorDriver(MesosExecutor())
        sys.exit(0 if driver.run() == mesos_pb2.DRIVER_STOPPED else 1)


if __name__=='__main__':
    print "Starting executor..."
    MesosExecutor.run_executor()

########NEW FILE########
__FILENAME__ = sample_lmd
#!/usr/bin/env python
# encoding: utf-8

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# author: Paco Nathan
# https://github.com/ceteri/exelixi


from collections import namedtuple
from copy import deepcopy
from random import randint, sample
from uow import UnitOfWorkFactory
import logging
import sys


######################################################################
## class definitions

OPS = ( "rend", "turn", "sup", "loop" )

Point = namedtuple('Point', 'x y')

DIR_W = Point(1, 0)	# DIR_N
DIR_S = Point(0, 1)	# DIR_W
DIR_E = Point(-1, 0)	# DIR_S
DIR_N = Point(0, -1)	# DIR_E


class Drone (object):
    def __init__ (self, x, y):
        self.pos = Point(x, y)
        self.dir = Point(1, 0)


    def _mod_math (self, pos, dir, mod):
        result = pos + dir

        if result < 0:
            result += mod
        else:
            result %= mod

        return result


    def exec_op_sup (self, mod, sup):
        x = self._mod_math(self.pos.x, sup.x, mod)
        y = self._mod_math(self.pos.y, sup.y, mod)
        self.pos = Point(x, y)
        return x, y


    def exec_op_move (self, mod):
        x = self._mod_math(self.pos.x, self.dir.x, mod)
        y = self._mod_math(self.pos.y, self.dir.y, mod)
        self.pos = Point(x, y)
        return x, y


    def exec_op_turn (self):
        if self.dir.x == DIR_W.x and self.dir.y == DIR_W.y:
            self.dir = DIR_N
        elif self.dir.x == DIR_S.x and self.dir.y == DIR_W.y:
            self.dir = DIR_W
        elif self.dir.x == DIR_E.x and self.dir.y == DIR_E.y:
            self.dir = DIR_S
        elif self.dir.x == DIR_N.x and self.dir.y == DIR_N.y:
            self.dir = DIR_E


class LMDFactory (UnitOfWorkFactory):
    """UnitOfWork definition for Lawnmower Drone GP"""

    def __init__ (self):
        #super(UnitOfWorkFactory, self).__init__()
        self.n_pop = 300
        self.n_gen = 200
        self.max_indiv = 20000
        self.selection_rate = 0.3
        self.mutation_rate = 0.3
        self.term_limit = 5.0e-02
        self.hist_granularity = 3

        self.grid = [
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            [ 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, ],
            ]

        # sampling parameters
        self.length = len(self.grid) ** 2
        self.min = 0
        self.max = len(OPS) - 1


    def generate_features (self):
        """generate a new feature set for a lawnmower drone"""
        rand_len = randint(1, self.length)
        feature_set = []

        while len(feature_set) < rand_len:
            op = randint(self.min, self.max)

            if op == OPS.index("sup"):
                feature_set.append(op)
                feature_set.append(randint(0, len(self.grid) - 1))
                feature_set.append(randint(0, len(self.grid) - 1))

            elif op == OPS.index("loop"):
                if len(feature_set) > 2:
                    offset = randint(1, len(feature_set) - 1)
                    feature_set.append(op)
                    feature_set.append(offset)

            else:
                feature_set.append(op)

        return feature_set


    def mutate_features (self, feature_set):
        """mutate a copy of the given GP program"""
        pos_to_mutate = randint(0, len(feature_set) - 1)
        mutated_feature_set = list(feature_set)
        mutated_feature_set[pos_to_mutate] = randint(self.min, self.max)
        return mutated_feature_set


    def breed_features (self, f_feature_set, m_feature_set):
        """breed two GP programs to produce a toddler GP program"""
        split = randint(1, min(len(f_feature_set), len(m_feature_set)))
        return f_feature_set[split:] + m_feature_set[:split]


    def _simulate (self, grid, code, drone):
        """simulate the lawnmower grid"""
        sp = 0
        mod = len(self.grid)
        num_ops = 0
        max_ops = self.length
        result = None

        try:
            while sp < len(code) and num_ops < max_ops:
                num_ops += 1
                op = code[sp]

                if op == OPS.index("rend"):
                    x, y = drone.exec_op_move(mod)
                    grid[y][x] = 0

                elif op == OPS.index("turn"):
                    drone.exec_op_turn()

                elif op == OPS.index("sup"):
                    sup = Point(code[sp + 1], code[sp + 2])
                    sp += 2

                    if sup.x == 0 and sup.y == 0:
                        return None

                    x, y = drone.exec_op_sup(mod, sup)
                    grid[y][x] = 0

                elif op == OPS.index("loop"):
                    offset = code[sp + 1]

                    if offset == 0 or offset > sp:
                        return None

                    sp -= offset

                else:
                    return None

                #print num_ops, sp, "pos", drone.pos, "dir", drone.dir
                sp += 1

            result = grid

        finally:
            return result


    def get_fitness (self, feature_set):
        """determine the fitness ranging [0.0, 1.0]; higher is better"""
        drone = Drone(randint(0, len(self.grid)), randint(0, len(self.grid)))
        grid = self._simulate(deepcopy(self.grid), feature_set, drone)
        fitness = 0.0

        if grid:
            terrorists = 0

            for row in grid:
                #print row
                terrorists += sum(row)

            fitness = (self.length - terrorists) / float(self.length)

            if len(feature_set) > 5:
                penalty = len(feature_set) / 10.0
                fitness /= penalty

        #print fitness, feature_set
        return fitness


if __name__=='__main__':
    uow = LMDFactory()

    print uow.grid

########NEW FILE########
__FILENAME__ = sample_tsp
#!/usr/bin/env python
# encoding: utf-8

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# author: Paco Nathan
# https://github.com/ceteri/exelixi


from random import randint, sample
from uow import UnitOfWorkFactory
import logging
import sys


######################################################################
## class definitions

class TSPFactory (UnitOfWorkFactory):
    """UnitOfWork definition for Traveling Salesperson Problem"""

    def __init__ (self):
        #super(UnitOfWorkFactory, self).__init__()
        self.n_pop = 10
        self.n_gen = 23
        self.max_indiv = 2000
        self.selection_rate = 0.2
        self.mutation_rate = 0.02
        self.term_limit = 5.0e-03
        self.hist_granularity = 3

        # cost matrix for an example TSP: optimize the bicycling route
        # for weekend chores in Mountain View for a young Steve Jobs
        # tuple definition: (name, addr, duration)

        self.route_meta = ( ( "Home", "secret", 0 ),
                            ( "Piazzas Fine Foods", "3922 Middlefield Rd, Palo Alto, CA 94303", 45 ),
                            ( "Mountain View Public Library", "585 Franklin St, Mountain View, CA 94041", 30 ),
                            ( "Seascapes Fish & Pets Inc", "298 Castro St, Mountain View, CA 94041", 10 ),
                            ( "Dana Street Roasting Company", "744 W Dana St, Mountain View, CA 94041", 20 ),
                            ( "Supercuts", "2420 Charleston Rd, Mountain View, CA 94043", 60 ),
                            )

        self.route_cost = ( ( 0, 7, 11, 12, 14, 8 ),
                            ( 7, 0, 18, 18, 19, 5 ),
                            ( 14, 19, 0, 2, 3, 19 ),
                            ( 12, 20, 3, 0, 1, 19 ),
                            ( 12, 18, 3, 1, 0, 18 ),
                            ( 8, 5, 18, 18, 19, 0 ),
                            )

        # sampling parameters
        self.length = len(self.route_cost) - 1
        self.min = 1
        self.max = self.length


    def generate_features (self):
        """generate a new feature set for young Steve pedaling"""
        features = []
        expected = list(xrange(self.min, self.max + 1))

        # sample row indices in the cost matrix, without replacement
        for _ in xrange(self.length):
            x = sample(expected, 1)[0]
            features.append(x)
            expected.remove(x)

        return features


    def mutate_features (self, feature_set):
        """mutate a copy of the given feature set"""
        pos_to_mutate = randint(0, len(feature_set) - 1)
        mutated_feature_set = list(feature_set)
        mutated_feature_set[pos_to_mutate] = randint(self.min, self.max)
        return mutated_feature_set


    def breed_features (self, f_feature_set, m_feature_set):
        """breed two feature sets to produce a child"""
        half = len(f_feature_set) / 2
        return f_feature_set[half:] + m_feature_set[:half]


    def get_fitness (self, feature_set):
        """determine the fitness ranging [0.0, 1.0]; higher is better"""
        #print feature_set

        # 1st estimator: all points were visited?
        expected = set(xrange(self.min, self.max + 1))
        observed = set(feature_set)
        cost1 = len(expected - observed) / float(len(expected))
        #print expected, observed, cost1

        # 2nd estimator: travel time was minimized?
        total_cost = 0
        worst_case = float(sum(self.route_cost[0])) * 2.0
        x0 = 0

        for x1 in feature_set:
            total_cost += self.route_cost[x0][x1]
            x0 = x1

        total_cost += self.route_cost[x0][0]
        cost2 = min(1.0, total_cost / worst_case)
        #print total_cost, worst_case, cost2

        # combine the two estimators into a fitness score
        fitness = 1.0 - (cost1 + cost2) / 2.0

        if cost1 > 0.0:
            fitness /= 2.0

        #print cost1, cost2, fitness, feature_set
        return fitness


if __name__=='__main__':
    uow = TSPFactory()

    print uow.route_meta
    print uow.route_cost

########NEW FILE########
__FILENAME__ = service
#!/usr/bin/env python
# encoding: utf-8

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# author: Paco Nathan
# https://github.com/ceteri/exelixi


from contextlib import contextmanager
from gevent import monkey, shutdown, signal, spawn, wsgi, Greenlet
from gevent.event import Event
from gevent.queue import JoinableQueue
from hashring import HashRing
from json import dumps, loads
from signal import SIGQUIT
from util import instantiate_class, post_distrib_rest
from uuid import uuid1
import logging
import sys


######################################################################
## class definitions

class Worker (object):
    # http://www.gevent.org/gevent.wsgi.html
    # http://toastdriven.com/blog/2011/jul/31/gevent-long-polling-you/
    # http://blog.pythonisito.com/2012/07/gevent-and-greenlets.html

    DEFAULT_PORT = "9311"


    def __init__ (self, port=DEFAULT_PORT):
        # REST services
        monkey.patch_all()
        signal(SIGQUIT, shutdown)
        self.is_config = False
        self.server = wsgi.WSGIServer(('', int(port)), self._response_handler, log=None)

        # sharding
        self.prefix = None
        self.shard_id = None
        self.ring = None

        # concurrency based on message passing / barrier pattern
        self._task_event = None
        self._task_queue = None

        # UnitOfWork
        self._uow = None


    def shard_start (self):
        """start the worker service for this shard"""
        self.server.serve_forever()


    def shard_stop (self, *args, **kwargs):
        """stop the worker service for this shard"""
        payload = args[0]

        if (self.prefix == payload["prefix"]) and (self.shard_id == payload["shard_id"]):
            logging.info("worker service stopping... you can safely ignore any exceptions that follow")
            self.server.stop()
        else:
            # returns incorrect response in this case, to avoid exception
            logging.error("incorrect shard %s prefix %s", payload["shard_id"], payload["prefix"])


    ######################################################################
    ## authentication methods

    def auth_request (self, payload, start_response, body):
        """test the authentication credentials for a REST call"""
        if (self.prefix == payload["prefix"]) and (self.shard_id == payload["shard_id"]):
            return True
        else:
            # UoW caller did not provide correct credentials to access shard
            start_response('403 Forbidden', [('Content-Type', 'text/plain')])
            body.put("Forbidden, incorrect credentials for this shard\r\n")
            body.put(StopIteration)

            logging.error("incorrect credentials shard %s prefix %s", payload["shard_id"], payload["prefix"])
            return False


    def shard_config (self, *args, **kwargs):
        """configure the service to run a shard"""
        payload, start_response, body = self.get_response_context(args)

        if self.is_config:
            # hey, somebody call security...
            start_response('403 Forbidden', [('Content-Type', 'text/plain')])
            body.put("Forbidden, shard is already in a configured state\r\n")
            body.put(StopIteration)

            logging.warning("denied configuring shard %s prefix %s", self.shard_id, self.prefix)
        else:
            self.is_config = True
            self.prefix = payload["prefix"]
            self.shard_id = payload["shard_id"]

            # dependency injection for UnitOfWork
            uow_name = payload["uow_name"]
            logging.info("initializing unit of work based on %s", uow_name)

            ff = instantiate_class(uow_name)
            self._uow = ff.instantiate_uow(uow_name, self.prefix)

            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)

            logging.info("configuring shard %s prefix %s", self.shard_id, self.prefix)


    ######################################################################
    ## barrier pattern methods

    @contextmanager
    def wrap_task_event (self):
        """initialize a gevent.Event, to which the UnitOfWork will wait as a listener"""
        self._task_event = Event()
        yield

        # complete the Event, notifying the UnitOfWork which waited
        self._task_event.set()
        self._task_event = None


    def _consume_task_queue (self):
        """consume/serve requests until the task_queue empties"""
        while True:
            payload = self._task_queue.get()

            try:
                self._uow.perform_task(payload)
            finally:
                self._task_queue.task_done()


    def prep_task_queue (self):
        """prepare task_queue for another set of distributed tasks"""
        self._task_queue = JoinableQueue()
        spawn(self._consume_task_queue)


    def put_task_queue (self, payload):
        """put the given task definition into the task_queue"""
        self._task_queue.put_nowait(payload)


    def queue_wait (self, *args, **kwargs):
        """wait until all shards finished sending task_queue requests"""
        payload, start_response, body = self.get_response_context(args)

        if self.auth_request(payload, start_response, body):
            if self._task_event:
                self._task_event.wait()

            # HTTP response first, then initiate long-running task
            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)


    def queue_join (self, *args, **kwargs):
        """join on the task_queue, as a barrier to wait until it empties"""
        payload, start_response, body = self.get_response_context(args)

        if self.auth_request(payload, start_response, body):
            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("join queue...\r\n")

            ## NB: TODO this step of emptying out the task_queue on
            ## shards could take a while on a large run... perhaps use
            ## a long-polling HTTP request or websocket instead?
            self._task_queue.join()

            body.put("done\r\n")
            body.put(StopIteration)


    ######################################################################
    ## hash ring methods

    def ring_init (self, *args, **kwargs):
        """initialize the HashRing"""
        payload, start_response, body = self.get_response_context(args)

        if self.auth_request(payload, start_response, body):
            self.ring = payload["ring"]

            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)

            logging.info("setting hash ring %s", self.ring)


    ######################################################################
    ## WSGI handler for REST endpoints

    def get_response_context (self, args):
        """decode the WSGI response context from the Greenlet args"""
        env = args[0]
        msg = env["wsgi.input"].read()
        payload = loads(msg)
        start_response = args[1]
        body = args[2]

        return payload, start_response, body


    def _response_handler (self, env, start_response):
        """handle HTTP request/response"""
        uri_path = env["PATH_INFO"]
        body = JoinableQueue()

        if self._uow and self._uow.handle_endpoints(self, uri_path, env, start_response, body):
            pass

        ##########################################
        # Worker endpoints

        elif uri_path == '/shard/config':
            # configure the service to run a shard
            Greenlet(self.shard_config, env, start_response, body).start()

        elif uri_path == '/shard/stop':
            # shutdown the service
            ## NB: must parse POST data specially, to avoid exception
            payload = loads(env["wsgi.input"].read())
            Greenlet(self.shard_stop, payload).start_later(1)

            # HTTP response starts first, to avoid error after server stops
            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Goodbye\r\n")
            body.put(StopIteration)

        elif uri_path == '/queue/wait':
            # wait until all shards have finished sending task_queue requests
            Greenlet(self.queue_wait, env, start_response, body).start()

        elif uri_path == '/queue/join':
            # join on the task_queue, as a barrier to wait until it empties
            Greenlet(self.queue_join, env, start_response, body).start()

        elif uri_path == '/check/persist':
            ## NB: TODO checkpoint the service state to durable storage
            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)

        elif uri_path == '/check/recover':
            ## NB: TODO restart the service, recovering from most recent checkpoint
            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)

        ##########################################
        # HashRing endpoints

        elif uri_path == '/ring/init':
            # initialize the HashRing
            Greenlet(self.ring_init, env, start_response, body).start()

        elif uri_path == '/ring/add':
            ## NB: TODO add a node to the HashRing
            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)

        elif uri_path == '/ring/del':
            ## NB: TODO delete a node from the HashRing
            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put("Bokay\r\n")
            body.put(StopIteration)

        ##########################################
        # utility endpoints

        elif uri_path == '/':
            # dump info about the service in general
            start_response('200 OK', [('Content-Type', 'text/plain')])
            body.put(str(env) + "\r\n")
            body.put(StopIteration)

        else:
            # ne znayu
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            body.put('Not Found\r\n')
            body.put(StopIteration)

        return body


class WorkerInfo (object):
    def __init__ (self, offer, task):
        self.host = offer.hostname
        self.slave_id = offer.slave_id.value
        self.task_id = task.task_id.value
        self.executor_id = task.executor.executor_id.value
        self.ip_addr = None
        self.port = None

    def get_shard_uri (self):
        """generate a URI for this worker service"""
        return self.ip_addr + ":" + self.port


    def report (self):
        """report the slave telemetry + state"""
        return "host %s slave %s task %s exe %s ip %s:%s" % (self.host, self.slave_id, str(self.task_id), self.executor_id, self.ip_addr, self.port)


class Framework (object):
    def __init__ (self, uow_name, prefix="/tmp/exelixi"):
        """initialize the system parameters, which represent operational state"""
        self.uuid = uuid1().hex
        self.prefix = prefix + "/" + self.uuid
        logging.info("prefix: %s", self.prefix)

        # dependency injection for UnitOfWork
        self.uow_name = uow_name
        logging.info("initializing unit of work based on %s", uow_name)

        ff = instantiate_class(self.uow_name)
        self._uow = ff.instantiate_uow(self.uow_name, self.prefix)

        self._shard_assoc = None
        self._ring = None


    def _gen_shard_id (self, i, n):
        """generate a shard_id"""
        s = str(i)
        z = ''.join([ '0' for _ in xrange(len(str(n)) - len(s)) ])
        return "shard/" + z + s


    def set_worker_list (self, worker_list, exe_info=None):
        """associate shards with Executors"""
        self._shard_assoc = {}

        for i in xrange(len(worker_list)):
            shard_id = self._gen_shard_id(i, len(worker_list))

            if not exe_info:
                self._shard_assoc[shard_id] = [worker_list[i], None]
            else:
                self._shard_assoc[shard_id] = [worker_list[i], exe_info[i]]

        logging.info("shard list: %s", str(self._shard_assoc))


    def get_worker_list (self):
        """generator for the worker shards"""
        for shard_id, (shard_uri, exe_info) in self._shard_assoc.items():
            yield shard_id, shard_uri


    def get_worker_count (self):
        """count the worker shards"""
        return len(self._shard_assoc)


    def send_worker_rest (self, shard_id, shard_uri, path, base_msg):
        """access a REST endpoint on the specified shard"""
        return post_distrib_rest(self.prefix, shard_id, shard_uri, path, base_msg)


    def send_ring_rest (self, path, base_msg):
        """access a REST endpoint on each of the shards"""
        json_str = []

        for shard_id, (shard_uri, exe_info) in self._shard_assoc.items():
            lines = post_distrib_rest(self.prefix, shard_id, shard_uri, path, base_msg)
            json_str.append(lines[0])

        return json_str


    def phase_barrier (self):
        """
        implements a two-phase barrier to (1) wait until all shards
        have finished sending task_queue requests, then (2) join on
        each task_queue, to wait until it has emptied
        """
        self.send_ring_rest("queue/wait", {})
        self.send_ring_rest("queue/join", {})


    def orchestrate_uow (self):
        """orchestrate a UnitOfWork distributed across the HashRing via REST endpoints"""
        # configure the shards and the hash ring
        self.send_ring_rest("shard/config", { "uow_name": self.uow_name })

        self._ring = { shard_id: shard_uri for shard_id, (shard_uri, exe_info) in self._shard_assoc.items() }
        self.send_ring_rest("ring/init", { "ring": self._ring })

        # distribute the UnitOfWork tasks
        self._uow.orchestrate(self)

        # shutdown
        self.send_ring_rest("shard/stop", {})


class UnitOfWork (object):
    def __init__ (self, uow_name, prefix):
        self.uow_name = uow_name
        self.uow_factory = instantiate_class(uow_name)

        self.prefix = prefix

        self._shard_id = None
        self._shard_dict = None
        self._hash_ring = None


    def set_ring (self, shard_id, shard_dict):
        """initialize the HashRing"""
        self._shard_id = shard_id
        self._shard_dict = shard_dict
        self._hash_ring = HashRing(shard_dict.keys())


    def perform_task (self, payload):
        """perform a task consumed from the Worker.task_queue"""
        pass


    def orchestrate (self, framework):
        """orchestrate Workers via REST endpoints"""
        pass


    def handle_endpoints (self, worker, uri_path, env, start_response, body):
        """UnitOfWork REST endpoints"""
        pass


if __name__=='__main__':
    if len(sys.argv) < 2:
        print "usage:\n  %s <host:port> <factory>" % (sys.argv[0])
        sys.exit(1)

    shard_uri = sys.argv[1]
    uow_name = sys.argv[2]

    fra = Framework(uow_name)
    print "framework launching based on %s stored at %s..." % (fra.uow_name, fra.prefix)

    fra.set_worker_list([ shard_uri ])
    fra.orchestrate_uow()

########NEW FILE########
__FILENAME__ = uow
#!/usr/bin/env python
# encoding: utf-8

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# author: Paco Nathan
# https://github.com/ceteri/exelixi


from ga import Individual, Population
from random import randint
from util import instantiate_class
import logging


######################################################################
## class definitions

class UnitOfWorkFactory (object):
    """encapsulates all of the dependency injection and UnitOfWork definitions"""

    def __init__ (self):
        ## NB: override these GA parameters
        self.n_pop = 23
        self.n_gen = 10
        self.term_limit = 5.0e-03
        self.hist_granularity = 3
        self.selection_rate = 0.2
        self.mutation_rate = 0.02
        self.max_indiv = 2000

        ## NB: override these feature set parameters
        self.length = 5
        self.min = 0
        self.max = 100
        self.target = 231


    def instantiate_uow (self, uow_name, prefix):
        """instantiate a UnitOfWork, to decouple services from the GA problem domain"""
        ## NB: override these class references to customize the GA definition
        return Population(uow_name, prefix, Individual())


    def get_fitness (self, feature_set):
        """determine the fitness ranging [0.0, 1.0]; higher is better"""
        ## NB: override this fitness function
        return 1.0 - abs(sum(feature_set) - self.target) / float(self.target)


    def use_force (self, force):
        """determine whether to force recalculation of a fitness function"""
        # NB: override in some use cases, e.g., when required for evaluating shared resources
        return force


    def generate_features (self):
        """generate a new feature set"""
        ## NB: override this feature set generator
        return sorted([ randint(self.min, self.max) for _ in xrange(self.length) ])


    def mutate_features (self, feature_set):
        """mutate a copy of the given feature set"""
        ## NB: override this feature set mutator
        pos_to_mutate = randint(0, len(feature_set) - 1)
        mutated_feature_set = list(feature_set)
        mutated_feature_set[pos_to_mutate] = randint(self.min, self.max)
        return sorted(mutated_feature_set)


    def breed_features (self, f_feature_set, m_feature_set):
        """breed two feature sets to produce a child"""
        ## NB: override this feature set crossover
        half = len(f_feature_set) / 2
        return sorted(f_feature_set[half:] + m_feature_set[:half])


    def _calc_median_hist (self, hist_items, n_indiv):
        """calculate the median from a fitness histogram"""
        sum_count = 0
        mid_count = float(n_indiv) / 2

        if n_indiv == 1:
            return hist_items[0][0]
        else:
            for i in xrange(len(hist_items)):
                bin, count = hist_items[i]
                sum_count += count

                if sum_count == mid_count:
                    return bin
                elif sum_count > mid_count:
                    bin0, count0 = hist_items[i - 1]
                    return ((bin0 * count0) + (bin * count)) / (count0 + count)


    def test_termination (self, current_gen, hist_items, total_indiv):
        """evaluate the terminating condition for this generation and report progress"""
        ## NB: override this termination test

        # calculate a mean squared error (MSE) of fitness for a Population
        hist_keys = map(lambda x: x[0], hist_items)
        n_indiv = sum([ count for bin, count in hist_items ])
        fit_mse = sum([ count * (1.0 - float(bin)) ** 2.0 for bin, count in hist_items ]) / float(n_indiv)

        # calculate summary stats
        fit_max = max(hist_keys)
        fit_avg = sum(hist_keys) / float(n_indiv)
        fit_med = self._calc_median_hist(hist_items, n_indiv)

        # report the progress for one generation
        gen_report = "gen\t%d\tsize\t%d\ttotal\t%d\tmse\t%.2e\tmax\t%.2e\tmed\t%.2e\tavg\t%.2e" % (current_gen, n_indiv, total_indiv, fit_mse, fit_max, fit_med, fit_avg)
        print gen_report
        logging.info(gen_report)
        logging.debug(filter(lambda x: x[1] > 0, hist_items))

        # stop when a "good enough" solution is found
        return (fit_mse <= self.term_limit) or (total_indiv >= self.max_indiv)


if __name__=='__main__':
    # a simple test
    uow_name = "uow.UnitOfWorkFactory"
    uow = instantiate_class(uow_name)

    print uow

########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python
# encoding: utf-8

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# author: Paco Nathan
# https://github.com/ceteri/exelixi


from collections import OrderedDict
from httplib import BadStatusLine
from importlib import import_module
from json import dumps, loads
from os.path import abspath
from random import random
from urllib2 import urlopen, Request, URLError
import logging
import psutil
import socket


######################################################################
## utilities

def instantiate_class (class_path):
    """instantiate a class from the given package.class name"""
    module_name, class_name = class_path.split(".")
    return getattr(import_module(module_name), class_name)()


def post_distrib_rest (prefix, shard_id, shard_uri, path, base_msg):
    """POST a JSON-based message to a REST endpoint on a shard"""
    msg = base_msg.copy()

    # populate credentials
    msg["prefix"] = prefix
    msg["shard_id"] = shard_id

    # POST the JSON payload to the REST endpoint
    uri = "http://" + shard_uri + "/" + path
    req = Request(uri)
    req.add_header('Content-Type', 'application/json')

    logging.debug("send %s %s", shard_uri, path)
    logging.debug(dumps(msg))

    # read/collect the response
    try:
        f = urlopen(req, dumps(msg))
        return f.readlines()
    except URLError as e:
        logging.critical("could not reach REST endpoint %s error: %s", uri, str(e.reason), exc_info=True)
        raise
    except BadStatusLine as e:
        logging.critical("REST endpoint died %s error: %s", uri, str(e.line), exc_info=True)


def get_telemetry ():
    """get system resource telemetry on a Mesos slave via psutil"""
    telemetry = OrderedDict()

    telemetry["ip_addr"] = socket.gethostbyname(socket.gethostname())

    telemetry["mem_free"] =  psutil.virtual_memory().free

    telemetry["cpu_num"] = psutil.NUM_CPUS

    x = psutil.cpu_times()
    telemetry["cpu_times"] = OrderedDict([ ("user", x.user), ("system", x.system), ("idle", x.idle) ])

    x = psutil.disk_usage("/tmp")
    telemetry["disk_usage"] = OrderedDict([ ("free", x.free), ("percent", x.percent) ])

    x = psutil.disk_io_counters()
    telemetry["disk_io"] = OrderedDict([ ("read_count", x.read_count), ("write_count", x.write_count), ("read_bytes", x.read_bytes), ("write_bytes", x.write_bytes), ("read_time", x.read_time), ("write_time", x.write_time) ])

    x = psutil.network_io_counters()
    telemetry["network_io"] = OrderedDict([ ("bytes_sent", x.bytes_sent), ("bytes_recv", x.bytes_recv), ("packets_sent", x.packets_sent), ("packets_recv", x.packets_recv), ("errin", x.errin), ("errout", x.errout), ("dropin", x.dropin), ("dropout", x.dropout) ])

    return telemetry


def get_master_state (master_uri):
    """get current state, represented as JSON, from the Mesos master"""
    uri = "http://" + master_uri + "/master/state.json"

    try:
        response = urlopen(uri)
        return loads(response.read())
    except URLError as e:
        logging.critical("could not reach REST endpoint %s error: %s", uri, str(e.reason), exc_info=True)
        raise


def get_master_leader (master_uri):
    """get the host:port for the Mesos master leader"""
    state = get_master_state(master_uri)
    return state["leader"].split("@")[1]


def pipe_slave_list (master_uri):
    """report a list of slave IP addr, one per line to stdout -- for building pipes"""
    state = get_master_state(get_master_leader(master_uri))

    for s in state["slaves"]:
        print s["pid"].split("@")[1].split(":")[0] 


if __name__=='__main__':
    pass

########NEW FILE########
