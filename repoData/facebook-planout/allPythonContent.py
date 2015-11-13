__FILENAME__ = anchoring_demo
import random
from uuid import uuid4
from flask import (
  Flask,
  session,
  request,
  redirect,
  url_for,
  render_template_string
)
app = Flask(__name__)

app.config.update(dict(
  DEBUG=True,
  SECRET_KEY='3.14159', # shhhhh
))

from planout.experiment import SimpleExperiment
from planout.ops.random import *

class AnchoringExperiment(SimpleExperiment):
  def setup(self):
    self.set_log_file('anchoring_webapp.log')

  def assign(self, params, userid):
    params.use_round_number = BernoulliTrial(p=0.5, unit=userid)
    if params.use_round_number:
      params.price = UniformChoice(choices=[240000, 250000, 260000],
        unit=userid)
    else:
      params.price = RandomInteger(min=240000, max=260000, unit=userid)

def money_format(number):
  return "${:,.2f}".format(number)

@app.route('/')
def main():
    # if no userid is defined make one up
    if 'userid' not in session:
        session['userid'] = str(uuid4())

    anchoring_exp = AnchoringExperiment(userid=session['userid'])
    price = anchoring_exp.get('price')

    return render_template_string("""
    <html>
      <head>
        <title>Let's buy a house!</title>
      </head>
      <body>
        <h3>
          A lovely new home is going on the market for {{ price }}. <br>
        </h3>
        <p>
          What will be your first offer?
        </p>
        <form action="/bid" method="GET">
          $<input type="text" length="10" name="bid"></input>
          <input type="submit"></input>
        </form>
      <br>
      <p><a href="/">Reload without resetting my session ID. I'll get the same offer when I come back.</a></p>
      <p><a href="/reset">Reset my session ID so I get re-randomized into a new treatment.</a></p>
      </body>
    </html>
    """, price=money_format(price))

@app.route('/reset')
def reset():
  session.clear()
  return redirect(url_for('main'))

@app.route('/bid')
def bid():
  bid_string = request.args.get('bid')
  bid_string = bid_string.replace(',', '') # get rid of commas
  try:
    bid_amount = int(bid_string)

    anchoring_exp = AnchoringExperiment(userid=session['userid'])
    anchoring_exp.log_event('bid', {'bid_amount': bid_amount})

    return render_template_string("""
      <html>
        <head>
          <title>Nice bid!</title>
        </head>
        <body>
          <p>You bid {{ bid }}. We'll be in touch if they accept your offer!</p>
          <p><a href="/">Back</a></p>
        </body>
      </html>
      """, bid=money_format(bid_amount))
  except ValueError:
    return render_template_string("""
      <html>
        <head>
          <title>Bad bid!</title>
        </head>
        <body>
          <p>You bid {{ bid }}. That's not a number, so we probably won't be accepting your bid.</p>
          <p><a href="/">Back</a></p>
        </body>
      </html>
      """, bid=bid_string)


if __name__ == '__main__':
    app.run()

########NEW FILE########
__FILENAME__ = demo_experiments
import interpreter_experiment_examples as interpreter
import simple_experiment_examples as simple_experiment

def demo_experiment1(module):
  print 'using %s...' % module.__name__
  exp1_runs = [module.Exp1(userid=i) for i in xrange(10)]
  print [(e.get('group_size'), e.get('ratings_goal')) for e in exp1_runs]

def demo_experiment2(module):
  print 'using %s...' % module.__name__
  # number of cues and selection of cues depends on userid and pageid
  for u in xrange(1,4):
    for p in xrange(1, 4):
      print module.Exp2(userid=u, pageid=p, liking_friends=['a','b','c','d'])

def demo_experiment3(module):
  print 'using %s...' % module.__name__
  for i in xrange(5):
    print module.Exp3(userid=i)

def demo_experiment4(module):
  print 'using %s...' % module.__name__
  for i in xrange(5):
    # probability of collapsing is deterministic on sourceid
    e = module.Exp4(sourceid=i, storyid=1, viewerid=1)
    # whether or not the story is collapsed depends on the sourceid
    exps = [module.Exp4(sourceid=i, storyid=1, viewerid=v) for v in xrange(10)]
    print e.get('prob_collapse'), [exp.get('collapse') for exp in exps]

if __name__ == '__main__':
  # run each experiment implemented using SimpleExperiment (simple_experiment)
  # or using the interpreter
  print '\nDemoing experiment 1...'
  demo_experiment1(simple_experiment)
  demo_experiment1(interpreter)

  print '\nDemoing experiment 2...'
  demo_experiment2(simple_experiment)
  demo_experiment2(interpreter)

  print '\nDemoing experiment 3...'
  demo_experiment3(simple_experiment)
  demo_experiment3(interpreter)

  print '\nDemoing experiment 4...'
  demo_experiment4(simple_experiment)
  demo_experiment4(interpreter)

########NEW FILE########
__FILENAME__ = demo_namespaces
from planout.namespace import SimpleNamespace
from planout.experiment import SimpleExperiment, DefaultExperiment
from planout.ops.random import *


class V1(SimpleExperiment):
  def assign(self, params, userid):
    params.banner_text = UniformChoice(
      choices=['Hello there!', 'Welcome!'],
      unit=userid)

class V2(SimpleExperiment):
  def assign(self, params, userid):
    params.banner_text = WeightedChoice(
      choices=['Hello there!', 'Welcome!'],
      weights=[0.8, 0.2],
      unit=userid)

class V3(SimpleExperiment):
  def assign(self, params, userid):
    params.banner_text = WeightedChoice(
      choices=['Nice to see you!', 'Welcome back!'],
      weights=[0.8, 0.2],
      unit=userid)


class DefaultButtonExperiment(DefaultExperiment):
  def get_default_params(self):
    return {'banner_text': 'Generic greetings!'}

class ButtonNamespace(SimpleNamespace):
  def setup(self):
    self.name = 'my_demo'
    self.primary_unit = 'userid'
    self.num_segments = 100
    self.default_experiment_class = DefaultButtonExperiment

  def setup_experiments(self):
    self.add_experiment('first version phase 1', V1, 10)
    self.add_experiment('first version phase 2', V1, 30)
    self.add_experiment('second version phase 1', V2, 40)
    self.remove_experiment('second version phase 1')
    self.add_experiment('third version phase 1', V3, 30)

if __name__ == '__main__':
  for i in xrange(100):
    e = ButtonNamespace(userid=i)
    print 'user %s: %s' % (i, e.get('banner_text'))

########NEW FILE########
__FILENAME__ = interpreter_experiment_examples
from planout.interpreter import *
from planout.experiment import SimpleExperiment
import json
import hashlib
from abc import ABCMeta, abstractmethod

class SimpleInterpretedExperiment(SimpleExperiment):
  """Simple class for loading a file-based PlanOut interpreter experiment"""
  __metaclass__ = ABCMeta

  filename = None

  def assign(self, params, **kwargs):
    procedure = Interpreter(
      json.load(open(self.filename)),
      self.salt,
      kwargs
      )
    params.update(procedure.get_params())

  def checksum(self):
    # src doesn't count first line of code, which includes function name
    src = open(self.filename).read()
    return hashlib.sha1(src).hexdigest()[:8]

class Exp1(SimpleInterpretedExperiment):
  filename = "sample_scripts/exp1.json"

class Exp2(SimpleInterpretedExperiment):
  filename = "sample_scripts/exp2.json"

class Exp3(SimpleInterpretedExperiment):
  filename = "sample_scripts/exp3.json"

class Exp4(SimpleInterpretedExperiment):
  filename = "sample_scripts/exp4.json"

########NEW FILE########
__FILENAME__ = simple_experiment_examples
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from planout.experiment import SimpleExperiment
from planout.ops.random import *

class Exp1(SimpleExperiment):
  def assign(self, e, userid):
    e.group_size = UniformChoice(choices=[1, 10], unit=userid);
    e.specific_goal = BernoulliTrial(p=0.8, unit=userid);
    if e.specific_goal:
      e.ratings_per_user_goal = UniformChoice(
        choices=[8, 16, 32, 64], unit=userid)
      e.ratings_goal = e.group_size * e.ratings_per_user_goal
    return e

class Exp2(SimpleExperiment):
  def assign(self, params, userid, pageid, liking_friends):
    params.num_cues = RandomInteger(
      min=1,
      max=min(len(liking_friends), 3),
      unit=[userid, pageid]
    )
    params.friends_shown = Sample(
      choices=liking_friends,
      draws=params.num_cues,
      unit=[userid, pageid]
    )

class Exp3(SimpleExperiment):
  def assign(self, e, userid):
    e.has_banner = BernoulliTrial(p=0.97, unit=userid)
    cond_probs = [0.5, 0.95]
    e.has_feed_stories = BernoulliTrial(p=cond_probs[e.has_banner], unit=userid)
    e.button_text = UniformChoice(
      choices=["I'm a voter", "I'm voting"], unit=userid)


class Exp4(SimpleExperiment):
  def assign(self, e, sourceid, storyid, viewerid):
    e.prob_collapse = RandomFloat(min=0.0, max=1.0, unit=sourceid)
    e.collapse = BernoulliTrial(p=e.prob_collapse, unit=[storyid, viewerid])
    return e

########NEW FILE########
__FILENAME__ = assignment
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from .ops.random import *
from collections import MutableMapping

# The Assignment class is the main work horse that lets you to execute
# random operators using the names of variables being assigned as salts.
# It is a MutableMapping, which means it plays nice with things like Flask
# template renders.
class Assignment(MutableMapping):
  """
  A mutable mapping that contains the result of an assign call.
  """
  def __init__(self, experiment_salt):
    self.experiment_salt = experiment_salt
    self._data = {}

  def evaluate(self, value):
    return value

  def __setitem__(self, name, value):
    if name in ('_data', 'experiment_salt'):
      self.__dict__[name] = value
      return

    if isinstance(value, PlanOutOpRandom):
      if 'salt' not in value.args:
        value.args['salt'] = name
      self._data[name] = value.execute(self)
    else:
      self._data[name] = value

  __setattr__ = __setitem__

  def __getitem__(self, name):
    if name in ('_data', 'experiment_salt'):
      return self.__dict__[name]
    else:
      return self._data[name]

  __getattr__ = __getitem__

  def __delitem__(self, name):
    del self._data[name]

  def __iter__(self):
    return iter(self._data)

  def __len__(self):
    return len(self._data)

  def __str__(self):
    return str(self._data)

########NEW FILE########
__FILENAME__ = experiment
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import logging
import time
import re
import json
import inspect
import hashlib
from abc import ABCMeta, abstractmethod
import __main__ as main

from .assignment import Assignment


# decorator for methods that assume assignments have been made
def requires_assignment(f):
  def wrapped_f(self, *args, **kwargs):
    if not self._assigned:
      self._assign()
    return f(self, *args, **kwargs)
  return wrapped_f

# decorator for methods that should be exposure logged
def requires_exposure_logging(f):
  def wrapped_f(self, *args, **kwargs):
    if self._auto_exposure_log and self.in_experiment and not self.exposure_logged:
      self.log_exposure()
    return f(self, *args, **kwargs)
  return wrapped_f

class Experiment(object):
  """Abstract base class for PlanOut experiments"""
  __metaclass__ = ABCMeta

  logger_configured = False

  def __init__(self, **inputs):
    self.inputs = inputs           # input data
    self._exposure_logged = False  # True when assignments have been exposure logged
    self._salt = None              # Experiment-level salt
    self.in_experiment = True

    # use the name of the class as the default name
    self._name = self.__class__.__name__

    # auto-exposure logging is enabled by default
    self._auto_exposure_log = True

    self.setup()                   # sets name, salt, etc.

    self._assignment = self.get_assignment()
    self._checksum = self.checksum()
    self._assigned = False

  def _assign(self):
    """Assignment and setup that only happens when we need to log data"""
    self.configure_logger() # sets up loggers
    self.assign(self._assignment, **self.inputs)
    self.in_experiment = \
      self._assignment.get('in_experiment', self.in_experiment)
    # check if inputs+params were previously logged
    self._logged = self.previously_logged()

  def setup(self):
    """Set experiment attributes, e.g., experiment name and salt."""
    # If the experiment name is not specified, just use the class name
    pass

  def get_assignment(self):
    return Assignment(self.salt)

  @property
  def salt(self):
    # use the experiment name as the salt if the salt is not set
    return self._salt if self._salt else self.name

  @salt.setter
  def salt(self, value):
    self._salt = value

  @property
  def name(self):
    return self._name

  @name.setter
  def name(self, value):
    self._name = re.sub(r'\s+', '-', value)

  @abstractmethod
  def assign(params, **kwargs):
    """Returns evaluated PlanOut mapper with experiment assignment"""
    pass

  @requires_assignment
  def __asBlob(self, extras={}):
    """Dictionary representation of experiment data"""
    d = {
      'name': self.name,
      'time': int(time.time()),
      'salt': self.salt,
      'inputs': self.inputs,
      'params': dict(self._assignment),
    }
    for k in extras:
      d[k] = extras[k]
    if self._checksum:
      d['checksum'] = self._checksum
    return d

  def checksum(self):
    # if we're running from a file and want to detect if the experiment file has changed
    if hasattr(main, '__file__'):
      # src doesn't count first line of code, which includes function name
      src = ''.join(inspect.getsourcelines(self.assign)[0][1:])
      return hashlib.sha1(src).hexdigest()[:8]
    # if we're running in an interpreter, don't worry about it
    else:
      return None

  @property
  def exposure_logged(self):
    return self._exposure_logged

  @exposure_logged.setter
  def exposure_logged(self, value):
    self._exposure_logged = value

  def set_auto_exposure_logging(self, value):
    """
    Disables / enables auto exposure logging (enabled by default).
    """
    self._auto_exposure_log = value

  @requires_assignment
  @requires_exposure_logging
  def get_params(self):
    """
    Get all PlanOut parameters. Triggers exposure log.
    """
    # In general, this should only be used by custom loggers.
    return dict(self._assignment)

  @requires_assignment
  @requires_exposure_logging
  def get(self, name, default=None):
    """
    Get PlanOut parameter (returns default if undefined). Triggers exposure log.
    """
    return self._assignment.get(name, default)

  @requires_assignment
  @requires_exposure_logging
  def __str__(self):
    """
    String representation of exposure log data. Triggers exposure log.
    """
    return str(self.__asBlob())

  def log_exposure(self, extras=None):
    """Logs exposure to treatment"""
    self.exposure_logged = True
    self.log_event('exposure', extras)

  def log_event(self, event_type, extras=None):
    """Log an arbitrary event"""
    if extras:
      extra_payload = {'event': event_type, 'extra_data': extras.copy()}
    else:
      extra_payload = {'event': event_type}
    self.log(self.__asBlob(extra_payload))

  @abstractmethod
  def configure_logger(self):
    """Set up files, database connections, sockets, etc for logging."""
    pass

  @abstractmethod
  def log(self, data):
    """Log experimental data"""
    pass

  @abstractmethod
  def previously_logged(self):
    """Check if the input has already been logged.
       Gets called once during in the constructor."""
    # For high-use applications, one might have this method to check if
    # there is a memcache key associated with the checksum of the inputs+params
    pass


class DefaultExperiment(Experiment):
  """
  Dummy experiment which has no logging. Default experiments used by namespaces
  should inherent from this class.
  """
  def configure_logger(self):
    pass  # we don't log anything when there is no experiment

  def log(self, data):
    pass

  def previously_logged(self):
    return True

  def assign(self, params, **kwargs):
    # more complex default experiments can override this method
    params.update(self.get_default_params())

  def get_default_params(self):
    """
    Default experiments that are just key-value stores should
    override this method."""
    return {}

class SimpleExperiment(Experiment):
  """Simple experiment base class which exposure logs to a file"""

  __metaclass__ = ABCMeta
  # We only want to set up the logger once, the first time the object is
  # instantiated. We do this by maintaining this class variable.
  logger = {}
  log_file = {}

  def configure_logger(self):
    """Sets up logger to log to a file"""
    my_logger = self.__class__.logger
    # only want to set logging handler once for each experiment (name)
    if self.name not in self.__class__.logger:
      if self.name not in self.__class__.log_file:
        self.__class__.log_file[self.name] = '%s.log' % self.name
      file_name = self.__class__.log_file[self.name]
      my_logger[self.name] = logging.getLogger(self.name)
      my_logger[self.name].setLevel(logging.INFO)
      my_logger[self.name].addHandler(logging.FileHandler(file_name))
      my_logger[self.name].propagate = False

  def log(self, data):
    """Logs data to a file"""
    self.__class__.logger[self.name].info(json.dumps(data))

  def set_log_file(self, path):
    self.__class__.log_file[self.name] = path

  def previously_logged(self):
    """Check if the input has already been logged.
       Gets called once during in the constructor."""
    # SimpleExperiment doesn't connect with any services, so we just assume
    # that if the object is a new instance, this is the first time we are
    # seeing the inputs/outputs given.
    return False

########NEW FILE########
__FILENAME__ = interpreter
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from copy import deepcopy
from .ops.utils import Operators


Operators.initFactory()

class Interpreter(object):
  """PlanOut interpreter"""

  def __init__(self, serialization, experiment_salt='global_salt', inputs={}):
    self._serialization = serialization
    self._env = {}
    self._overrides = {}
    self.experiment_salt = self._experiment_salt = experiment_salt
    self._evaluated = False
    self._inputs = inputs.copy()


  def get_params(self):
    """Get all assigned parameter values from an executed interpreter script"""
    # evaluate code if it hasn't already been evaluated
    if not self._evaluated:
      self.evaluate(self._serialization)
      self._evaluated = True
    return self._env

  def set_env(self, new_env):
    """Replace the current environment with a dictionary"""
    self._env = deepcopy(new_env)
    # apply overrides
    for v in self._overrides:
      self._env[v] = self._overrides[v]
    return self

  def has(self, name):
    """Check if a variable exists in the PlanOut environment"""
    return name in self._env

  def get(self, name, default=None):
    """Get a variable from the PlanOut environment"""
    return self._env.get(name, self._inputs.get(name, default))

  def set(self, name, value):
    """Set a variable in the PlanOut environment"""
    self._env[name] = value
    return self

  def set_overrides(self, overrides):
    """
    Sets variables to maintain a frozen state during the interpreter's
    execution. This is useful for debugging PlanOut scripts.
    """
    Operators.enable_overrides()
    self._overrides = overrides
    self.set_env(self._env)  # this will reset overrides
    return self

  def has_override(self, name):
    """Check to see if a variable has an override."""
    return name in self._overrides

  def get_overrides(self):
    """Get a dictionary of all overrided values"""
    return self._overrides

  def evaluate(self, planout_code):
    """Recursively evaluate PlanOut interpreter code"""
    # if the object is a PlanOut operator, execute it it.
    if Operators.isOperator(planout_code):
      return Operators.operatorInstance(planout_code).execute(self)
    # if the object is a list, iterate over the list and evaluate each element
    elif type(planout_code) is list:
      return [self.evaluate(i) for i in planout_code]
    else:
      return planout_code  # data is a literal


class Validator():
  """
  Inspects and validates serialized PlanOut experiment definitions.
  This can be used by management systems for validating JSON scripts
  and printing them in human readable "pretty" format.
  """
  def __init__(self, serialization):
    self._serialization = serialization

  def validate(self):
    """validate PlanOut serialization"""
    config = self._serialization
    return Operators.validateOperator(config)

  def pretty(self):
    """pretty print PlanOut serialization as PlanOut language code"""
    config = self._serialization
    return Operators.operatorInstance(config).pretty()

  def get_variables(self):
    """get all variables set by PlanOut script"""
    pass

  def get_input_variables(self):
    """get all variables used not defined by the PlanOut script"""
    pass

########NEW FILE########
__FILENAME__ = namespace
from abc import ABCMeta, abstractmethod, abstractproperty
from operator import itemgetter

from .experiment import Experiment, DefaultExperiment
from .ops.random import Sample, RandomInteger
from .assignment import Assignment

# decorator for methods that assume assignments have been made
def requires_experiment(f):
  def wrapped_f(self, *args, **kwargs):
    if not self._experiment:
      self._assign_experiment()
    return f(self, *args, **kwargs)
  return wrapped_f


def requires_default_experiment(f):
  def wrapped_f(self, *args, **kwargs):
    if not self._default_experiment:
      self._assign_default_experiment()
    return f(self, *args, **kwargs)
  return wrapped_f


class Namespace(object):
  __metaclass__ = ABCMeta
  def __init__(self, **kwargs):
    pass

  @abstractmethod
  def add_experiment(self, name, exp_object, num_segments, **kwargs):
    pass

  @abstractmethod
  def remove_experiment(self, name):
    pass

  @abstractmethod
  def set_auto_exposure_logging(self, value):
    pass

  @abstractproperty
  def in_experiment(self):
    pass

  @abstractmethod
  def get(self, name, default):
    pass

  @abstractmethod
  def log_exposure(self, extras=None):
    pass

  @abstractmethod
  def log_event(self, event_type, extras=None):
    pass

class SimpleNamespace(Namespace):
  __metaclass__ = ABCMeta
  def __init__(self, **kwargs):
    self.name = self.__class__  # default name is the class name
    self.inputs = kwargs
    self.num_segments = None

    # dictionary mapping segments to experiment names
    self.segment_allocations = {}

    # dictionary mapping experiment names to experiment objects
    self.current_experiments = {}

    self._experiment = None          # memoized experiment object
    self._default_experiment = None  # memoized default experiment object
    self.default_experiment_class = DefaultExperiment

    # setup name, primary key, number of segments, etc
    self.setup()
    self.available_segments = set(range(self.num_segments))

    # load namespace with experiments
    self.setup_experiments()


  @abstractmethod
  def setup(self):
    """Sets up experiment"""
    # Developers extending this class should set the following variables
    # self.name = 'sample namespace'
    # self.primary_unit = 'userid'
    # self.num_segments = 10000
    pass

  @abstractmethod
  def setup_experiments():
    # e.g.,
    # self.add_experiment('first experiment', Exp1, 100)
    pass

  @property
  def primary_unit(self):
    return self._primary_unit

  @primary_unit.setter
  def primary_unit(self, value):
    # later on we require that the primary key is a list, so we use
    # a setter to convert strings to a single element list
    if type(value) is list:
      self._primary_unit = value
    else:
      self._primary_unit = [value]


  def add_experiment(self, name, exp_object, segments):
    num_avail = len(self.available_segments)
    if num_avail < segments:
      print 'error: %s segments requested, only %s available.' % \
        (segments, num_avail)
      return False
    if name in self.current_experiments:
      print 'error: there is already an experiment called %s.' %  name
      return False

    # randomly select the given number of segments from all available segments
    a = Assignment(self.name)
    a.sampled_segments = \
      Sample(choices=list(self.available_segments), draws=segments, unit=name)

    # assign each segment to the experiment name
    for segment in a.sampled_segments:
      self.segment_allocations[segment] = name
      self.available_segments.remove(segment)

    # associate the experiment name with an object
    self.current_experiments[name] = exp_object


  def remove_experiment(self, name):
    if name not in self.current_experiments:
      print 'error: there is no experiment called %s.' %  name
      return False

    segments_to_free = \
      [s for s, n in self.segment_allocations.iteritems() if n == name]

    for segment in segments_to_free:
      del self.segment_allocations[segment]
      self.available_segments.add(segment)
    del self.current_experiments[name]

    return True

  def get_segment(self):
    # randomly assign primary unit to a segment
    a = Assignment(self.name)
    a.segment = RandomInteger(min=0, max=self.num_segments,
      unit=itemgetter(*self.primary_unit)(self.inputs))
    return a.segment


  def _assign_experiment(self):
    "assign primary unit to an experiment"

    segment = self.get_segment()
    # is the unit allocated to an experiment?
    if segment in self.segment_allocations:
      experiment_name = self.segment_allocations[segment]
      experiment = self.current_experiments[experiment_name](**self.inputs)
      experiment.name = '%s-%s' % (self.name, experiment_name)
      experiment.salt = '%s.%s' % (self.name, experiment_name)
      self._experiment = experiment
      self._in_experiment = experiment.in_experiment
    else:
      self._assign_default_experiment()
      self._in_experiment = False


  def _assign_default_experiment(self):
    self._default_experiment = self.default_experiment_class(**self.inputs)


  @requires_default_experiment
  def default_get(self, name, default=None):
    return self._default_experiment.get(name, default)


  @property
  @requires_experiment
  def in_experiment(self):
    return self._in_experiment


  @in_experiment.setter
  def in_experiment(self, value):
    # in_experiment cannot be externally modified
    pass


  @requires_experiment
  def set_auto_exposure_logging(self, value):
    self._experiment.set_auto_exposure_logging(value)

  @requires_experiment
  def get(self, name, default=None):
    if self._experiment is None:
      return self.default_get(name, default)
    else:
      return self._experiment.get(name, self.default_get(name, default))

  @requires_experiment
  def log_exposure(self, extras=None):
    """Logs exposure to treatment"""
    if self._experiment is None:
      pass
    self._experiment.log_exposure(extras)

  @requires_experiment
  def log_event(self, event_type, extras=None):
    """Log an arbitrary event"""
    if self._experiment is None:
      pass
    self._experiment.log_event(event_type, extras)

########NEW FILE########
__FILENAME__ = base
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import logging
from abc import ABCMeta, abstractmethod

from .utils import Operators

class PlanOutOp(object):
  """Abstract base class for PlanOut Operators"""
  __metaclass__ = ABCMeta
  # all PlanOut operator have some set of parameters that act as required and
  # optional arguments
  def __init__(self, **parameters):
    self.args = parameters

  # all PlanOut operators must implement execute
  @abstractmethod
  def execute(self, mapper):
    pass

  # all PlanOut operators must specify required and optional parameters
  # that get used in execute() by defining options():
  #   def options(self):
  #     return {
  #       'p': {'required': 1, 'description': 'probability of success'},
  #       'n': {'required': 0, 'description': 'number of samples'}
  #     }
  #
  def options(self):
    return {}

  # if custom operators needs to perform additional, custom validation,
  # override this method (see the Cond operator in core as an example)
  def validate(self):
    return True

  def prettyArgs(self):
    return Operators.prettyParamFormat(self.args)

  def pretty(self):
    return '%s(%s)' % (self.args['op'], self.prettyArgs())

  # validates the presence of operator parameters.
  # this only gets called from Operators.validateOperator()
  def _validate(self):
    parameters = self.args
    is_valid = True
    # any operator can safely use these parameters
    # in particular, salt is automatically appended to variables
    # which don't have salt specified.
    safe_params = set(['op', 'salt'])
    # verify that all parameters are legit parameters
    instance_opts = self._options()
    for param in parameters:
      if param not in safe_params and param not in instance_opts:
        logging.error("'%s' is not a valid parameter for %s" \
            % (param, Operators.pretty(parameters)))
        is_valid = False
    # verify that all required parameters are present
    for param in instance_opts:
      if self.getOptionRequired(param) and param not in parameters:
        logging.error("required parameter '%s' not found in %s" \
            % (param, Operators.pretty(parameters)))
        is_valid = False
    # perform additional validation, if necessary
    return is_valid and self.validate()

  # recursively appends parents' options() with instance's options()
  # this only gets called by the PlanOutOp base class.
  def _options(self):
    if type(self) is PlanOutOp:
      return {}
    else:
      parent_opts = super(type(self), self).options()  # init with parent opts
      instance_opts = self.options()
      for option_name in parent_opts:
        instance_opts[option_name] = parent_opts[option_name]
      return instance_opts

  # methods that can be used by the QE to generate UI elements for operators
  def getOptionDescription(self, option_name):
    return self._options()[option_name].get('description', option_name)

  def getOptionRequired(self, option_name):
    return self._options()[option_name].get('required', 1)

  def getOptions(self):
    return [p for p in self._options()]


# PlanOutOpSimple is the easiest way to implement simple operators.
# The class automatically evaluates the values of all parameters passed in via
# execute(), and stores the PlanOut mapper object and evaluated
# parameters as instance variables.  The user can then extend PlanOutOpSimple
# and implement simpleExecute().

class PlanOutOpSimple(PlanOutOp):
  __metaclass__ = ABCMeta

  def execute(self, mapper):
    self.mapper = mapper
    self.parameters = {}    # evaluated parameters
    for param in self.args:
      self.parameters[param] = mapper.evaluate(self.args[param])
    return self.simpleExecute()

  def validate(self):
    is_valid = True
    for param_name in self.args:
      if not Operators.validateOperator(self.args[param_name]):
        is_valid = False
    return is_valid

class PlanOutOpBinary(PlanOutOpSimple):
  __metaclass__ = ABCMeta

  def options(self):
    return {
      'left': {'required': 1, 'description': 'left side of binary operator'},
      'right': {'required': 1, 'description': 'right side of binary operator'}}

  def simpleExecute(self):
    return self.binaryExecute(self.parameters['left'], self.parameters['right'])

  def pretty(self):
    return '%s %s %s' % (
      Operators.pretty(self.args['left']),
      self.getInfixString(),
      Operators.pretty(self.args['right']))

  def getInfixString(self):
    return self.args['op']

  @abstractmethod
  def binaryExecute(self, left, right):
    pass


class PlanOutOpUnary(PlanOutOpSimple):
  __metaclass__ = ABCMeta
  def options(self):
    return {
      'value': {'required': 1, 'description': 'input value to commutative operator'}}

  def simpleExecute(self):
    return self.unaryExecute(self.parameters['value'])

  def pretty(self):
    return self.getUnaryString + Operators.pretty(self.args['value'])

  def getUnaryString(self):
    return self.args['op']

  @abstractmethod
  def unaryExecute(self, value):
    pass

class PlanOutOpCommutative(PlanOutOpSimple):
  __metaclass__ = ABCMeta

  def options(self):
    return {
      'values': {'required': 1, 'description': 'input value to commutative operator'}}

  def simpleExecute(self):
    return self.commutativeExecute(self.parameters['values'])

  def pretty(self):
    values = Operators.strip_array(self.args['values'])
    if type(values) is list:
      pretty_values = ', '.join([Operators.pretty(i) for i in values])
    else:
      pretty_values = Operators.pretty(values)

    return '%s(%s)' % (self.getCommutativeString(), pretty_values)

  def getCommutativeString(self):
    return self.args['op']

  @abstractmethod
  def commutativeExecute(self, values):
    pass

########NEW FILE########
__FILENAME__ = core
from .base import (
  PlanOutOp,
  PlanOutOpSimple,
  PlanOutOpBinary,
  PlanOutOpUnary,
  PlanOutOpCommutative,
  )

import planout.ops.utils as ops

def indent(s, n=1):
  l = [("  " * n) + i for i in s.split('\n')]
  return '\n'.join(l)


class Literal(PlanOutOp):
  def options(self):
    return {'value': {'required': 1}}

  def execute(self, mapper):
    return self.args['value']

  def pretty(self):
    return self.args['value']


class Get(PlanOutOp):
  def options(self):
    return {'var': {'required': 1, 'description': 'variable to get'}}

  def execute(self, mapper):
    return mapper.get(self.args['var'])

  def pretty(self):
    return self.args['var']


class Seq(PlanOutOp):
  def options(self):
    return {
      'seq': {
        'required': 1,
        'description': 'sequence of operators to execute'}}

  def execute(self, mapper):
    for op in self.args['seq']:
      mapper.evaluate(op)

  def validate(self):
    is_valid = True
    for op in self.args['seq']:
      if not ops.Operators.validateOperator(op):
        is_valid = False
    return is_valid

  def pretty(self):
    l = [ops.Operators.pretty(v) for v in self.args['seq']]
    return '\n'.join(l)


class Set(PlanOutOp):
  def options(self):
    return {
      'var': {'required': 1, 'description': 'variable to set'},
      'value': {'required': 1, 'description': 'value of variable being set'}}

  def execute(self, mapper):
    var, value = self.args['var'], self.args['value']
    # if a salt is not specified, use the variable name as the salt
    if ops.Operators.isOperator(value) and 'salt' not in value:
      value['salt'] = var
    mapper.set(var, mapper.evaluate(value))

  def validate(self):
    return ops.Operators.validateOperator(self.args['value'])

  def pretty(self):
    strp = ops.Operators.pretty(self.args['value'])
    return "%s = %s;" % (self.args['var'], strp)


class SetOverride(Set):
  def execute(self, mapper):
    var, value = self.args['var'], self.args['value']
    if not mapper.has_override(var):
      super(SetOverride, self).execute(mapper)


class Array(PlanOutOp):
  def options(self):
    return {'values': {'required': 1, 'description': 'array of values'}}

  def execute(self, mapper):
    return [mapper.evaluate(value) for value in self.args['values']]

  def validate(self):
    is_valid = True
    for value in self.args['values']:
      if not ops.Operators.validateOperator(value):
        is_valid = False
    return is_valid

  def pretty(self):
    l = [ops.Operators.pretty(v) for v in self.args['values']]
    f = "[%s]" % ', '.join(l)
    return f


class Index(PlanOutOpSimple):
  def options(self):
    return {
      'base': {'required': 1, 'description': 'variable being indexed'},
      'index': {'required': 1, 'description': 'index'}}

  def simpleExecute(self):
    return self.parameters['base'][self.parameters['index']]

  def pretty(self):
    b = ops.Operators.pretty(self.args['base'])
    i = ops.Operators.pretty(self.args['index'])
    return "%s[%s]" % (b, i)


class Cond(PlanOutOp):
  def options(self):
    return {
    'cond': {'required': 1, 'description': 'array of if-else tuples'}}

  def execute(self, mapper):
    for i in self.args['cond']:
      if_clause, then_clause = i['if'], i['then']
      if mapper.evaluate(if_clause):
        return mapper.evaluate(then_clause)

  def validate(self):
    is_valid = True
    for ifthen_clause in self.args['cond']:
      if len(ifthen_clause) == 2:
        if_c, then_c = ifthen_clause
        if not (ops.Operators.validateOperator(if_c) and \
            ops.Operators.validateOperator(then_c)):
          is_valid = False
      else:
        logging.error('if-then clause %s must be a tuple' \
          % Operators.pretty(ifthen_clause))
        is_valid = False
      return is_valid

  def pretty(self):
    pretty_str = ""
    first_if = True
    for i in self.args['cond']:
      if_clause, then_clause = i['if'], i['then']
      if if_clause == 'true':
        pretty_str += 'else {\n'
      else:
        prefix = 'if(%s) {\n' if first_if else 'else if(%s) {\n'
        pretty_str += prefix % ops.Operators.pretty(if_clause)
      pretty_str += indent(ops.Operators.pretty(then_clause)) + '\n}'
    return pretty_str


class And(PlanOutOp):
  def options(self):
    return {
      'values': {'required': 1, 'description': 'array of truthy values'}}

  def execute(self, mapper):
    for clause in self.args['values']:
      if not mapper.evaluate(clause):
        return False
    return True

  def validate(self):
    is_valid = True
    for clause in self.args['values']:
      if not ops.Operators.validateOperator(clause):
        is_valid = False
    return is_valid

  def pretty(self):
    pretty_c = [Operators.pretty(i) for i in self.args['values']]
    return '&& '.join(pretty_c)

class Or(PlanOutOp):
  def options(self):
    return {
      'values': {'required': 1, 'description': 'array of truthy values'}}

  def execute(self, mapper):
    for clause in self.args['values']:
      if mapper.evaluate(clause):
        return True
    return False

  def validate(self):
    is_valid = True
    for clause in self.args['values']:
      if not ops.Operators.validateOperator(clause):
        is_valid = False
    return is_valid

  def pretty(self):
    pretty_c = [Operators.pretty(c) for c in self.args['values']]
    return '|| '.join(pretty_c)

class Product(PlanOutOpCommutative):
  def commutativeExecute(self, values):
    return reduce(lambda x,y: x*y, values)

  def pretty(self):
    values = Operators.strip_array(self.args['values'])
    pretty_c = [Operators.pretty(i) for i in values]
    return ' * '.join(pretty_c)

class Sum(PlanOutOpCommutative):
  def commutativeExecute(self, values):
    return sum(values)

  def pretty(self):
    pretty_c = [Operators.pretty(c) for c in self.args['values']]
    return '+ '.join(pretty_c)


class Equals(PlanOutOpBinary):
  def getInfixString(self):
    return "=="

  def binaryExecute(self, left, right):
    return left == right


class GreaterThan(PlanOutOpBinary):
  def binaryExecute(self, left, right):
    return left > right

class LessThan(PlanOutOpBinary):
  def binaryExecute(self, left, right):
    return left < right

class LessThanOrEqualTo(PlanOutOpBinary):
  def binaryExecute(self, left, right):
    return left <= right

class GreaterThanOrEqualTo(PlanOutOpBinary):
  def binaryExecute(self, left, right):
    return left >= right

class Mod(PlanOutOpBinary):
  def binaryExecute(self, left, right):
    return left % right

class Divide(PlanOutOpBinary):
  def binaryExecute(self, left, right):
    return float(left) / float(right)

class Not(PlanOutOpUnary):
  def unaryExecute(self, value):
    return not value

  def getUnaryString():
    return '!'

class Negative(PlanOutOpUnary):
  def unaryExecute(self, value):
    return 0 - value

  def getUnaryString():
    return '-'

class Min(PlanOutOpCommutative):
  def commutativeExecute(self, values):
    return min(values)

class Max(PlanOutOpCommutative):
  def commutativeExecute(self, values):
    return max(values)

class Length(PlanOutOpCommutative):
  def commutativeExecute(self, values):
    return len(values)

########NEW FILE########
__FILENAME__ = random
import hashlib
import base


class PlanOutOpRandom(base.PlanOutOpSimple):
  LONG_SCALE = float(0xFFFFFFFFFFFFFFF)

  def options(self):
    return {
     'unit': {'required': 1, 'description': 'unit to hash on'},
     'salt': {'required': 0,'description':
       'salt for hash. should generally be unique for each random variable'}}

  def getUnit(self, appended_unit=None):
    unit = self.parameters['unit']
    if type(unit) is not list:
      unit = [unit]
    if appended_unit is not None:
      unit += [appended_unit]
    return unit

  def getHash(self, appended_unit=None):
    salt = self.parameters['salt']
    salty = '%s.%s' % (self.mapper.experiment_salt, salt)
    unit_str = '.'.join(map(str, self.getUnit(appended_unit)))
    return int(hashlib.sha1(salty + unit_str).hexdigest()[:15], 16)

  def getUniform(self, min_val=0.0, max_val=1.0, appended_unit=None):
    zero_to_one = self.getHash(appended_unit)/PlanOutOpRandom.LONG_SCALE
    return min_val + max_val*zero_to_one


class RandomFloat(PlanOutOpRandom):
  def options(self):
    return {
      'min': {'required': 1, 'description': 'min (float) value drawn'},
      'max': {'required': 1, 'description': 'max (float) value being drawn'}}

  def simpleExecute(self):
    min_val = self.parameters.get('min', 0)
    max_val = self.parameters.get('max', 1)
    return self.getUniform(min_val, max_val)


class RandomInteger(PlanOutOpRandom):
  def options(self):
    return {
      'min': {'required': 1, 'description': 'min (int) value drawn'},
      'max': {'required': 1, 'description': 'max (int) value being drawn'}}

  def simpleExecute(self):
    min_val = self.parameters.get('min', 0)
    max_val = self.parameters.get('max', 1)
    return min_val + self.getHash() % (max_val - min_val + 1)


class BernoulliTrial(PlanOutOpRandom):
  def options(self):
    return {'p': {'required': 1, 'description': 'probability of drawing 1'}}

  def simpleExecute(self):
    p = self.parameters['p']
    rand_val = self.getUniform(0.0, 1.0)
    return 1 if rand_val <= p else 0


class BernoulliFilter(PlanOutOpRandom):
  def options(self):
   return {
      'p': {'required': 1, 'description': 'probability of retaining element'},
      'choices': {'required': 1, 'description': 'elements being filtered'}}

  def simpleExecute(self):
    p, values = self.parameters['p'], self.parameters['choices']
    if len(values) == 0:
      return []
    return [i for i in values if self.getUniform(0.0, 1.0, i) <= p]


class UniformChoice(PlanOutOpRandom):
  def options(self):
    return {'choices': {'required': 1, 'description': 'elements to draw from'}}

  def simpleExecute(self):
    choices = self.parameters['choices']
    if len(choices) == 0:
      return []
    rand_index = self.getHash() % len(choices)
    return choices[rand_index]


class WeightedChoice(PlanOutOpRandom):
  def options(self):
    return {
      'choices': {'required': 1, 'description': 'elements to draw from'},
      'weights': {'required': 1, 'description': 'probability of draw'}}
  def simpleExecute(self):
    choices = self.parameters['choices']
    weights = self.parameters['weights']
    # eventually add weighted choice
    if len(choices) == 0:
      return []
    cum_weights = dict(zip(choices, weights))
    cum_sum = 0.0
    for choice in cum_weights:
      cum_sum += cum_weights[choice]
      cum_weights[choice] = cum_sum
    stop_value = self.getUniform(0.0, cum_sum)
    for choice in cum_weights:
      if stop_value <= cum_weights[choice]:
        return choice

class Sample(PlanOutOpRandom):
  def options(self):
    return {
      'choices': {'required': 1, 'description': 'choices to sample'},
      'draws': {'required': 0, 'description': 'number of samples to draw'}}

  # implements Fisher-Yates shuffle
  def simpleExecute(self):
    choices = self.parameters['choices']
    num_draws = self.parameters.get('draws', len(choices))
    for i in xrange(len(choices) - 1, 0, -1):
      j = self.getHash(i) % (i + 1)
      choices[i], choices[j] = choices[j], choices[i]
    return choices[:num_draws]

########NEW FILE########
__FILENAME__ = utils
import json

class Operators():
  @staticmethod
  def initFactory():
    import planout.ops.core as core
    import planout.ops.random as random
    Operators.operators = {
      "literal": core.Literal,
      "get": core.Get,
      "seq": core.Seq,
      "set": core.Set,
      "index": core.Index,
      "array": core.Array,
      "equals": core.Equals,
      "cond": core.Cond,
      "and": core.And,
      "or": core.Or,
      ">": core.GreaterThan,
      "<": core.LessThan,
      ">=": core.GreaterThanOrEqualTo,
      "<=": core.LessThanOrEqualTo,
      "%": core.Mod,
      "/": core.Divide,
      "not": core.Not,
      "negative": core.Negative,
      "min": core.Min,
      "max": core.Max,
      "length": core.Length,
      "product": core.Product,
      "sum": core.Sum,
      "randomFloat": random.RandomFloat,
      "randomInteger": random.RandomInteger,
      "bernoulliTrial": random.BernoulliTrial,
      "bernoulliFilter": random.BernoulliFilter,
      "uniformChoice": random.UniformChoice,
      "weightedChoice": random.WeightedChoice,
      "sample": random.Sample
    }

  @staticmethod
  def enable_overrides():
    import core
    Operators.operators['set'] = core.SetOverride

  @staticmethod
  def isOperator(op):
    return \
      type(op) is dict and "op" in op and op["op"] in Operators.operators

  @staticmethod
  def operatorInstance(params):
    return Operators.operators[params['op']](**params)

  @staticmethod
  def validateOperator(params):
    if type(params) is dict and 'op' in params:
      if params['op'] in Operators.operators:
        return Operators.operatorInstance(params)._validate()
      else:
        # this should probably throw an exception
        print 'invalid operator %s' % params['op']
        return False
    else:
      return True  # literals are always valid

  @staticmethod
  def prettyParamFormat(params):
    ps = [p+'='+Operators.pretty(params[p]) for p in params if p != 'op']
    return ', '.join(ps)

  @staticmethod
  def strip_array(params):
    if type(params) is list:
      return params
    if type(params) is dict and params.get('op', None) == 'array':
      return params['values']
    else:
      return params

  @staticmethod
  def pretty(params):
    if Operators.isOperator(params):
      try:
        # if an op is invalid, we may not be able to pretty print it
        my_pretty = Operators.operatorInstance(params).pretty()
      except:
        my_pretty = params
      return my_pretty
    elif type(params) is list:
      return '[%s]' % ', '.join([Operators.pretty(p) for p in params])
    else:
      return json.dumps(params)

########NEW FILE########
__FILENAME__ = test_assignment
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest

from planout.assignment import Assignment
from planout.ops.random import UniformChoice

class AssignmentTest(unittest.TestCase):
  tester_unit = 4
  tester_salt = 'test_salt'

  def test_set_get_constant(self):
    a = Assignment(self.tester_salt)
    a.foo = 12
    self.assertEqual(a.foo, 12)

  def test_set_get_uniform(self):
    a = Assignment(self.tester_salt)
    a.foo = UniformChoice(choices=['a', 'b'], unit=self.tester_unit)
    a.bar = UniformChoice(choices=['a', 'b'], unit=self.tester_unit)
    a.baz = UniformChoice(choices=['a', 'b'], unit=self.tester_unit)
    self.assertEqual(a.foo, 'a')
    self.assertEqual(a.bar, 'b')
    self.assertEqual(a.baz, 'a')


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_core_ops
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import unittest

from planout.interpreter import (
  Interpreter,
  Validator,
  )

class TestBasicOperators(unittest.TestCase):
  def runConfig(self, config, init={}):
    e = None
    e = Interpreter(config, 'test_salt', init)
    is_valid = Validator(config).validate()
    self.assertTrue(is_valid)
    return e.get_params()

  def run_config_single(self, config):
    x_config = {'op': 'set', 'var': 'x', 'value': config}
    return self.runConfig(x_config)['x']

  def test_set(self):
    """Test setter"""
    # returns experiment object with probability p
    c = {'op': 'set', 'value': 'x_val', 'var': 'x'}
    d = self.runConfig(c)
    self.assertEquals({'x': 'x_val'}, d)

  def test_seq(self):
    """Test sequence"""
    config = {'op': 'seq', 'seq': [
      {'op': 'set', 'value': 'x_val', 'var': 'x'},
      {'op': 'set', 'value': 'y_val', 'var': 'y'}
    ]}
    d = self.runConfig(config)
    self.assertEquals({'x': 'x_val', 'y': 'y_val'}, d)

  def test_array(self):
    arr = [4,5,'a']
    a = self.run_config_single({'op': 'array', 'values': arr})
    self.assertEquals(arr, a)

  def test_cond(self):
    getInput = lambda i, r: {'op': 'equals', 'left': i, 'right': r}
    testIf = lambda i: self.runConfig({
      'op': 'cond', 'cond': [
      {'if': getInput(i, 0), 'then': {'op': 'set', 'var': 'x', 'value': 'x_0'}},
      {'if': getInput(i, 1), 'then': {'op': 'set', 'var': 'x', 'value': 'x_1'}}
    ]})
    self.assertEquals({'x': 'x_0'}, testIf(0))
    self.assertEquals({'x': 'x_1'}, testIf(1))

  def test_get(self):
    d = self.runConfig({'op': 'seq', 'seq': [
      {'op': 'set', 'var': 'x', 'value': 'x_val'},
      {'op': 'set', 'var': 'y', 'value':
        {'op': 'get', 'var': 'x'}}
    ]})
    self.assertEquals({'x': 'x_val', 'y': 'x_val'}, d)

  def test_index(self):
    x = self.run_config_single({'op': 'index', 'index': 0, 'base': [1,2,3]})
    self.assertEquals(x, 1)
    x = self.run_config_single({'op': 'index', 'index': 2, 'base': [1,2,3]})
    self.assertEquals(x, 3)
    x = self.run_config_single({'op': 'index', 'index': 2, 'base':
     {'op': 'array', 'values': [1,2,3]}})
    self.assertEquals(x, 3)

  def test_length(self):
    arr = range(5)
    length_test = self.run_config_single({'op': 'length', 'values': arr})
    self.assertEquals(len(arr), length_test)
    length_test = self.run_config_single({'op': 'length', 'values': []})
    self.assertEquals(0, length_test)
    length_test = self.run_config_single({'op': 'length', 'values':
      {'op': 'array', 'values': arr}
    })
    self.assertEquals(length_test, len(arr))

  def test_not(self):
    # test not
    x = self.run_config_single({'op': 'not', 'value': 0})
    self.assertEquals(True, x)
    x = self.run_config_single({'op': 'not', 'value': False})
    self.assertEquals(True, x)

    x = self.run_config_single({'op': 'not', 'value': 1})
    self.assertEquals(False, x)
    x = self.run_config_single({'op': 'not', 'value': True})
    self.assertEquals(False, x)

  def test_or(self):
    x = self.run_config_single({
      'op': 'or',
      'values': [0, 0, 0]})
    self.assertEquals(False, x)

    x = self.run_config_single({
      'op': 'or',
      'values': [0, 0, 1]})
    self.assertEquals(True, x)

    x = self.run_config_single({
      'op': 'or',
      'values': [False, True, False]})
    self.assertEquals(True, x)

  def test_and(self):
    x = self.run_config_single({
      'op': 'and',
      'values': [1, 1, 0]})
    self.assertEquals(False, x)

    x = self.run_config_single({
      'op': 'and',
      'values': [0, 0, 1]})
    self.assertEquals(False, x)

    x = self.run_config_single({
      'op': 'and',
      'values': [True, True, True]})
    self.assertEquals(True, x)

  def test_commutative(self):
    arr = [33, 7, 18, 21, -3]

    min_test = self.run_config_single({'op': 'min', 'values': arr})
    self.assertEquals(min(arr), min_test)
    max_test = self.run_config_single({'op': 'max', 'values': arr})
    self.assertEquals(max(arr), max_test)
    sum_test = self.run_config_single({'op': 'sum', 'values': arr})
    self.assertEquals(sum(arr), sum_test)
    product_test = self.run_config_single({'op': 'product', 'values': arr})
    self.assertEquals(reduce(lambda x,y: x*y, arr), product_test)

  def test_binary_ops(self):
    eq = self.run_config_single({'op': 'equals', 'left': 1, 'right': 2})
    self.assertEquals(1==2, eq)
    eq = self.run_config_single({'op': 'equals', 'left': 2, 'right': 2})
    self.assertEquals(2==2, eq)
    gt = self.run_config_single({'op': '>', 'left': 1, 'right': 2})
    self.assertEquals(1>2, gt)
    lt = self.run_config_single({'op': '<', 'left': 1, 'right': 2})
    self.assertEquals(1<2, lt)
    gte = self.run_config_single({'op': '>=', 'left': 2, 'right': 2})
    self.assertEquals(2>=2, gte)
    gte = self.run_config_single({'op': '>=', 'left': 1, 'right': 2})
    self.assertEquals(1>=2, gte)
    lte = self.run_config_single({'op': '<=', 'left': 2, 'right': 2})
    self.assertEquals(2<=2, lte)
    mod = self.run_config_single({'op': '%', 'left': 11, 'right': 3})
    self.assertEquals(11 % 3, mod)
    div = self.run_config_single({'op': '/', 'left': 3, 'right': 4})
    self.assertEquals(0.75, div)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_experiment
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import json
import unittest

from planout.experiment import Experiment
from planout.interpreter import Interpreter
from planout.ops.random import UniformChoice

global_log = []
class ExperimentTest(unittest.TestCase):

  def experiment_tester(self, exp_class):
    global global_log
    global_log = []

    e = exp_class(i=42)
    val = e.get_params()

    self.assertTrue('foo' in val)
    self.assertEqual(val['foo'], 'a')

    self.assertEqual(len(global_log), 1)


  def test_vanilla_experiment(self):
    class TestVanillaExperiment(Experiment):
      def configure_logger(self): pass
      def log(self, stuff): global_log.append(stuff)
      def previously_logged(self): pass

      def setup(self):
        self.name = 'test_name'

      def assign(self, params, i):
        params.foo = UniformChoice(choices=['a', 'b'], unit=i)

    self.experiment_tester(TestVanillaExperiment)


  def test_interpreted_experiment(self):
    class TestInterpretedExperiment(Experiment):
      def configure_logger(self): pass
      def log(self, stuff): global_log.append(stuff)
      def previously_logged(self): pass

      def setup(self):
        self.name = 'test_name'

      def assign(self, params, **kwargs):
        compiled = json.loads("""
            {"op":"set",
             "var":"foo",
             "value":{
               "choices":["a","b"],
               "op":"uniformChoice",
               "unit": {"op": "get", "var": "i"}
               }
            }
            """)
        proc = Interpreter(compiled, self.salt, kwargs)
        params.update(proc.get_params())

    self.experiment_tester(TestInterpretedExperiment)
    
    
if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_interpreter
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

import json
import unittest

from planout.interpreter import Interpreter, Validator

class InterpreterTest(unittest.TestCase):
  compiled = json.loads("""
{"op":"seq","seq":[{"op":"set","var":"group_size","value":{"choices":{"op":"array","values":[1,10]},"unit":{"op":"get","var":"userid"},"op":"uniformChoice"}},{"op":"set","var":"specific_goal","value":{"p":0.8,"unit":{"op":"get","var":"userid"},"op":"bernoulliTrial"}},{"op":"cond","cond":[{"if":{"op":"get","var":"specific_goal"},"then":{"op":"seq","seq":[{"op":"set","var":"ratings_per_user_goal","value":{"choices":{"op":"array","values":[8,16,32,64]},"unit":{"op":"get","var":"userid"},"op":"uniformChoice"}},{"op":"set","var":"ratings_goal","value":{"op":"product","values":[{"op":"get","var":"group_size"},{"op":"get","var":"ratings_per_user_goal"}]}}]}}]}]}
  """)

  def test_validator(self):
    v = Validator(self.compiled)
    self.assertTrue(v.validate())

    # these should print errors and return fail.
    incomplete_op = Validator({'op': 'uniformChoice', 'value': 42})
    self.assertFalse(incomplete_op.validate())

    bogus_op = Validator({'op': 'bogoOp', 'value': 42})
    self.assertFalse(bogus_op.validate())

  def test_interpreter(self):
    proc = Interpreter(self.compiled, 'foo', {'userid': 123456})
    self.assertTrue(proc.get_params())


if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = test_random_ops
# Copyright (c) 2014, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

from collections import Counter
import unittest
from math import sqrt

from planout.ops.random import *
from planout.assignment import Assignment

# decorator for quickly constructing PlanOutKit experiments
def experiment_decorator(name):
  def wrap(f):
    def wrapped_f(**kwargs):
      params = Assignment(name)
      return f(params, **kwargs)
    return wrapped_f
  return wrap


class TestRandomOperators(unittest.TestCase):
  z = 3.29  # z_{\alpha/2} for \alpha=0.001, e.g., 99.9% CI: qnorm(1-(0.001/2))

  @staticmethod
  def valueMassToDensity(value_mass):
    """convert value_mass dictionary to a density"""
    values, ns = zip(*value_mass.items())
    ns_sum = float(sum(ns))
    value_density = dict(zip(values, [i/ns_sum for i in ns]))
    return value_density

  def distributionTester(self, func, value_mass, N=1000):
    """Make sure an experiment object generates the desired frequencies"""
    # run N trials of f() with input i
    xs = [func(i=i).get('x') for i in xrange(N)]
    value_density = TestRandomOperators.valueMassToDensity(value_mass)

    # test outcome frequencies against expected density
    self.assertProbs(xs, value_density, float(N))


  def assertProbs(self, xs, value_density, N):
    """Assert a list of values has the same density as value_density"""
    hist = Counter(xs)

    # do binomial test of proportions for each item
    for i in hist:
      self.assertProp(hist[i]/N, value_density[i], N)


  def assertProp(self, observed_p, expected_p, N):
    """Does a test of proportions"""
    # normal approximation of binomial CI.
    # this should be OK for large N and values of p not too close to 0 or 1.
    se = TestRandomOperators.z*sqrt(expected_p*(1-expected_p)/N)
    self.assertTrue(abs(observed_p-expected_p) <= se)


  def test_bernoulli(self):
    """Test bernoulli trial"""

    # returns experiment function with x = BernoulliTrial(p) draw
    # experiment salt is p
    def bernoulliTrial(p):
      @experiment_decorator(p)
      def exp_func(e, i):
        e.x = BernoulliTrial(p=p, unit=i)
        return e
      return exp_func

    self.distributionTester(bernoulliTrial(0.0), {0:1, 1:0})
    self.distributionTester(bernoulliTrial(0.1), {0:0.9, 1:0.1})
    self.distributionTester(bernoulliTrial(1.0), {0:0, 1:1})

  def test_uniform_choice(self):
    """Test uniform choice"""

    # returns experiment function with x = UniformChoice(c) draw
    # experiment salt is a string version of c
    def uniformChoice(c):
      str_c = ','.join(map(str, c))
      @experiment_decorator(str_c)
      def exp_func(e, i):
        e.x = UniformChoice(choices=c, unit=i)
        return e
      return exp_func

    self.distributionTester(uniformChoice(['a']), {'a':1})
    self.distributionTester(uniformChoice(['a','b']), {'a':1, 'b':1})
    self.distributionTester(uniformChoice([1,2,3,4]), {1:1, 2:1, 3:1, 4:1})


  def test_weighted_choice(self):
    """Test weighted choice"""

    # returns experiment function with x = WeightedChoice(c,w) draw
    # experiment salt is a string version of weighted_dict's keys
    def weightedChoice(weight_dict):
      c, w = zip(*weight_dict.items())
      @experiment_decorator(','.join(map(str, w)))
      def exp_func(e, i):
        e.x = WeightedChoice(choices=c, weights=w, unit=i)
        return e
      return exp_func

    d = {'a':1}
    self.distributionTester(weightedChoice(d), d)
    d = {'a':1, 'b':2}
    self.distributionTester(weightedChoice(d), d)
    d = {'a':0, 'b':2, 'c':0}
    self.distributionTester(weightedChoice(d), d)

  def test_sample(self):
    """Test random sampling without replacement"""

    # returns experiment function with x = sample(c, draws)
    # experiment salt is a string version of c
    def sample(choices, draws):
      @experiment_decorator(','.join(map(str, choices)))
      def exp_func(e, i):
        e.x = Sample(choices=choices, draws=draws, unit=i)
        return e
      return exp_func

    def listDistributionTester(func, value_mass, N=1000):
      value_density = TestRandomOperators.valueMassToDensity(value_mass)

      # compute N trials
      xs_list = [func(i=i).get('x') for i in xrange(N)]

      # each xs is a row of the transpose of xs_list.
      # this is expected to have the same distribution as value_density
      for xs in zip(*xs_list):
        self.assertProbs(xs, value_density, float(N))

    listDistributionTester(sample([1,2,3], draws=3), {1:1,2:1,3:1})
    listDistributionTester(sample([1,2,3], draws=2), {1:1,2:1,3:1})
    listDistributionTester(sample(['a','a','b'], draws=3), {'a':2,'b':1})


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
