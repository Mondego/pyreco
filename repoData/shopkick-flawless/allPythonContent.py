__FILENAME__ = decorator_example
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import flawless.client
import flawless.client.decorators
import flawless.lib.config


# You can wrap a function using the flawless decorator and any exceptions that
# get thrown will be reported to the flawless backend & then re-raised
@flawless.client.decorators.wrap_function
def example1():
  raise Exception()



# You can also control behavior of the decorator. For instance you can set the
# number of times an error must occur before an email gets sent. You can also
# prevent the exception from being re-raised
@flawless.client.decorators.wrap_function(error_threshold=1, reraise_exception=False)
def example2():
  raise Exception()



# Finally, you can decorate an entire class. The class decorator wraps any instance
# method or classmethod in the class with the function decorator.
@flawless.client.decorators.wrap_class
class ExampleClass(object):

  def func1(self):
    raise Exception()

  @classmethod
  def func2(cls):
    raise Exception()



if __name__ == '__main__':
  # The client has three options to configure the flawless client
  # Option 1: Set flawless_hostport in the config file and call flawless.lib.config.init_config
  flawless.lib.config.init_config("../config/flawless.cfg")

  # Option 2: Manually edit flawless/client/default.py and hardcode the value for hostport

  # Option 3: Call set_hostport
  flawless.client.set_hostport("localhost:9028")



  # example1 will re-raise the exception
  try:
    example1()
  except:
    pass

  # example 2 will not
  example2()

  # The class methods will re-raise the exception
  obj = ExampleClass()
  try:
    obj.func1()
  except:
    pass

########NEW FILE########
__FILENAME__ = middleware_example
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import os

import flawless.client
from flawless.client.middleware import FlawlessMiddleware
import flawless.lib.config

# Django: Put the following in wsgi.py
# Pylons: Put the following in the make_app function in middleware.py
flawless.client.set_hostport("localhost:9028")
application = FlawlessMiddleware(application)



# There are three options for configuring the flawless client
# Option 1: Set flawless_hostport in the config file and call flawless.lib.config.init_config
flawless.lib.config.init_config("../config/flawless.cfg")

# Option 2: Manually edit flawless/client/default.py and hardcode the value for hostport

# Option 3: Call set_hostport
flawless.client.set_hostport("localhost:9028")

########NEW FILE########
__FILENAME__ = decorators
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import functools
import inspect

import flawless.client


def wrap_function(func=None, error_threshold=None, reraise_exception=True):
  ''' Wraps a function with reporting to errors backend '''
  # This if/else allows wrap_function to behave like a normal decorator when
  # used like:
  #     @wrap_function
  #     def some_func():
  #
  # However, it also allows wrap_function to also be passed keyword arguments
  # like the following:
  #     @wrap_function(error_threshold=3, reraise_exception=False)
  #     def some_func():
  if func:
    return flawless.client._wrap_function_with_error_decorator(
        func=func, error_threshold=error_threshold, reraise_exception=reraise_exception)
  else:
    return functools.partial(flawless.client._wrap_function_with_error_decorator,
                             error_threshold=error_threshold,
                             reraise_exception=reraise_exception)


def wrap_class(cls, error_threshold=None):
  ''' Wraps a class with reporting to errors backend by decorating each function of the class.
      Decorators are injected under the classmethod decorator if they exist.
  '''
  for method_name, method in inspect.getmembers(cls, inspect.ismethod):
    wrapped_method = flawless.client._wrap_function_with_error_decorator(
      method if not method.im_self else method.im_func,
      save_current_stack_trace=False,
      error_threshold=error_threshold,
    )
    if method.im_self:
      wrapped_method = classmethod(wrapped_method)
    setattr(cls, method_name, wrapped_method)
  return cls


########NEW FILE########
__FILENAME__ = default
hostport=None

########NEW FILE########
__FILENAME__ = middleware
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import os
import traceback
import socket
import sys
import StringIO

try:
  import webob
except:
  pass

import flawless.client

class FlawlessMiddleware(object):
  """Middleware records errors to the error backend"""
  def __init__(self, app):
    self.app = app
    self.hostname = socket.gethostname()

  def __call__(self, environ, start_response):
    try:
      return self.app(environ, start_response)
    except:
      type, value, tb = sys.exc_info()
      reconstructed_req = self._reconstruct_request(environ)
      flawless.client.record_error(hostname=self.hostname, tb=tb, exception_message=repr(value),
                                   additional_info=reconstructed_req)
      raise value, None, tb

  def _reconstruct_request(self, environ):
    request_str = ""
    if "webob" in globals():
      request_str = str(webob.Request(environ))[:2000]
    else:
      req_parts = []
      method = environ.get("REQUEST_METHOD", "")
      path = environ.get("PATH_INFO", "")
      path += ("?" * bool(environ.get("QUERY_STRING"))) + environ.get("QUERY_STRING", "")

      req_parts.append("%s %s %s" % (method, path, environ.get("SERVER_PROTOCOL", "")))
      req_parts.append("Host: %s" % environ.get("HTTP_HOST", ""))
      req_parts.append("Referer: %s" % environ.get("HTTP_REFERER", ""))
      req_parts.append("Cookie: %s" % environ.get("HTTP_COOKIE", ""))
      req_parts.append("Content-Length: %s" % environ.get("CONTENT_LENGTH", ""))
      req_parts.append("User-Agent: %s" % environ.get("HTTP_USER_AGENT", ""))
      request_str = "\n".join(req_parts)

    return request_str

########NEW FILE########
__FILENAME__ = persistent_dictionary
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import os
import os.path
import pickle
import shutil
import threading

from flawless.lib.data_structures import ProxyContainerMethodsMetaClass

class PersistentDictionary(object):
  ''' Provides a persistent thread-safe dictionary that is backed by a file on disk '''
  __metaclass__ = ProxyContainerMethodsMetaClass
  def _proxyfunc_(attr, self, *args, **kwargs):
    with self.lock:
      return getattr(self.dict, attr)(*args, **kwargs)

  def __init__(self, file_path):
    self.lock = threading.RLock()
    self.file_path = file_path
    self.dict = None

  def open(self):
    with self.lock:
      if os.path.isfile(self.file_path):
        fh = open(self.file_path, "rb+")
        self.dict = pickle.load(fh)
        fh.close()
      else:
        self.dict = dict()

  def sync(self):
    with self.lock:
      fh = open(self.file_path + ".tmp", "wb+")
      pickle.dump(self.dict, fh, pickle.HIGHEST_PROTOCOL)
      fh.close()
      shutil.move(self.file_path + ".tmp", self.file_path)

  def close(self):
    self.sync()

  def get_path(self):
    return self.file_path


########NEW FILE########
__FILENAME__ = prefix_tree
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import os

from flawless.lib.data_structures import ProxyContainerMethodsMetaClass


class PrefixTree(object):
  __metaclass__ = ProxyContainerMethodsMetaClass
  _proxyfunc_ = lambda attr, self, *args, **kwargs: getattr(self.root, attr)(*args, **kwargs)

  def __init__(self, split_key_func, join_key_func, accumulator_func=None,
               accumulator_intializer=None):
    self.split_key_func = split_key_func
    self.join_key_func = join_key_func
    self.accumulator_func = accumulator_func or (lambda x, y: x)
    self.accumulator_intializer = accumulator_intializer
    self.root = Branch(self)
    self.length = 0

  def set_accumulator(self, accumulator_func, accumulator_intializer):
    self.accumulator_func = accumulator_func
    self.accumulator_intializer = accumulator_intializer


class StringPrefixTree(PrefixTree):

  def __init__(self, accumulator_func=None, accumulator_intializer=None):
    split_key_func = lambda s: (s[0], s[1:])
    join_key_func = lambda *args: "".join(args)
    super(StringPrefixTree, self).__init__(
      split_key_func=split_key_func,
      join_key_func=join_key_func,
      accumulator_func=accumulator_func,
      accumulator_intializer=accumulator_intializer,
    )


class FilePathTree(PrefixTree):

  def __init__(self, accumulator_func=None, accumulator_intializer=None, sep=os.sep):
    split_key_func = lambda s: (s, None) if sep not in s else s.split(sep, 1)
    join_key_func = lambda *args: sep.join(*args)
    super(FilePathTree, self).__init__(
      split_key_func=split_key_func,
      join_key_func=join_key_func,
      accumulator_func=accumulator_func,
      accumulator_intializer=accumulator_intializer,
    )


class Branch(object):

  def __init__(self, trunk):
    self.trunk = trunk
    self.branches = dict()
    self.size = 0
    self.value = None
    self.is_set = False

  def __str__(self):
    retval = []
    if self.is_set:
      retval.append("(%s)" % str(self.value))

    for index, (key, subbranch) in enumerate(self.branches.items()):
      pad = "|   " if index != (len(self.branches) - 1) else "    "
      subbranch_str = "\n".join([pad + s for s in str(subbranch).split("\n")])
      retval.append("|-- " + str(key))
      retval.append(subbranch_str)
    return "\n".join(retval)

  def __setitem__(self, key, value):
    if not key:
      retval = not self.is_set
      self.value = value
      self.is_set = True
      self.size += 1
      return retval

    head, remaining = self.trunk.split_key_func(key)
    if head not in self.branches:
      self.branches[head] = Branch(self.trunk)
    retval = self.branches[head].__setitem__(remaining, value)
    self.size += int(retval)
    return retval

  def __getitem__(self, key):
    if not key:
      if self.trunk.accumulator_intializer is None:
        return self.value
      else:
        return self.trunk.accumulator_func(self.trunk.accumulator_intializer, self.value)

    head, remaining = self.trunk.split_key_func(key)
    if head not in self.branches:
      retval = self.trunk.accumulator_intializer
    else:
      retval = self.branches[head][remaining]
    return self.trunk.accumulator_func(retval, self.value)

  def __delitem__(self, key):
    head, remaining = self.trunk.split_key_func(key)
    if not remaining and head in self.branches:
      del_size = self.branches[head].size
      self.size -= del_size
      del self.branches[head]
      return del_size
    if not remaining and head not in self.branches:
      return 0
    elif remaining:
      num_deleted = self.branches[head].__delitem__(remaining)
      self.size -= num_deleted
      return num_deleted

  def __contains__(self, key):
    if not key:
      return True

    head, remaining = self.trunk.split_key_func(key)
    if head not in self.branches:
      return False
    else:
      return self.branches[head][remaining]

  def __iter__(self):
    for key in self.branches:
      if self.is_set or self.branches[key].size == 1:
        yield self.trunk.join_key_func(key)
      for sub_result in self.branches[key]:
        yield self.trunk.join_key_func(key, sub_result)

  def __len__(self):
    return self.size

########NEW FILE########
__FILENAME__ = stubs
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

from flawless.lib.data_structures import ProxyContainerMethodsMetaClass


class PersistentDictionaryStub(object):
  __metaclass__ = ProxyContainerMethodsMetaClass
  _proxyfunc_ = lambda attr, self, *args, **kwargs: getattr(self.dict, attr)(*args, **kwargs)

  def __init__(self, file_path):
    self.file_path = file_path

  def open(self):
    self.dict = dict()

  def sync(self):
    pass

  def close(self):
    pass

  def get_path(self):
    return self.file_path

########NEW FILE########
__FILENAME__ = repo
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import abc
import logging
import os
import os.path
import re
import subprocess

import flawless.lib.config


log = logging.getLogger(__name__)
config = flawless.lib.config.get()


def get_repository(open_process_func=subprocess.Popen):
  if config.repo_type == "git":
    return GitRepository(open_process_func=open_process_func)


class Repository(object):
  __metaclass__ = abc.ABCMeta

  def __init__(self, local_path=None, remote_url=None, branch_pattern=None,
               open_process_func=subprocess.Popen):
    self.local_path = local_path or config.repo_dir
    self.remote_url = remote_url or config.repo_url
    self.open_process_func = open_process_func
    self.branch_pattern = re.compile(config.repo_branch_pattern) if config.repo_branch_pattern else None

  @abc.abstractmethod
  def blame(self, filename, line_number):
    pass

  @abc.abstractmethod
  def update(self):
    pass

  @abc.abstractmethod
  def create(self):
    pass


class GitRepository(Repository):

  def __init__(self, *args, **kwargs):
    super(GitRepository, self).__init__(*args, **kwargs)
    self.extract_email_pattern = re.compile(r"^author-mail <([^>]+)+>$")
    self.extract_modified_pattern = re.compile(r"^author-time (\d+)$")
    self.digit_tokenizer_pattern = re.compile(r'(\d+)|(\D+)').findall
    self.natural_sort_func = \
      lambda s: tuple(int(num) if num else alpha for num, alpha in self.digit_tokenizer_pattern(s))

  def _raw_run(self, args, log_output=False):
    p = self.open_process_func(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    err = p.stderr.read()
    out = p.stdout.read()
    if log_output and out:
      log.info(out)
    if log_output and err:
      log.error(err)
    return out

  def _run_git_command(self, args, log_output=False):
    base_args = [
      config.git_cli_path,
      "--git-dir=%s" % os.path.join(self.local_path, ".git"),
      "--work-tree=%s" % self.local_path,
    ]
    base_args.extend(args)
    return self._raw_run(base_args, log_output=log_output)

  def blame(self, filename, line_number):
    args = [
      "blame",
      "-p",
      os.path.join(self.local_path, filename),
      "-L",
      "%d,+1" % line_number,
    ]
    output = self._run_git_command(args)
    email, modified = None, None
    for line in output.split("\n"):
      if email and modified:
        break

      match = self.extract_email_pattern.match(line)
      if match:
        email = match.group(1)
      match = self.extract_modified_pattern.match(line)
      if match:
        modified = int(match.group(1))

    return email, modified

  def update(self, log_output=False):
    if not self.remote_url:
      return

    branch_names = self._run_git_command(["fetch"], log_output=log_output)
    all_branches = self._run_git_command(["branch", "-r"], log_output=log_output).split("\n")
    all_branches = [s.strip() for s in all_branches if "->" not in s and s.strip()]
    all_branches = sorted(all_branches, key=self.natural_sort_func)
    if self.branch_pattern:
      all_branches = [s for s in all_branches if self.branch_pattern.match(s)]

    self._run_git_command(["reset", "--hard", all_branches[-1]], log_output=log_output)

  def create(self):
    if not os.path.exists(self.local_path):
      os.makedirs(self.local_path)
    self._raw_run(
      [config.git_cli_path, "clone", self.remote_url, self.local_path],
      log_output=True,
    )
    self.update(log_output=True)


########NEW FILE########
__FILENAME__ = api
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import pickle


class ApiObject(object):
  _api_attributes = []

  def __init__(self, *args, **kwargs):
    values = dict((k, None) for k, _ in self._api_attributes)
    values.update(zip([k for k, _ in self._api_attributes], args))
    values.update(kwargs)
    primitives = [int, str, bool, unicode, float, list, dict, set]
    values = dict((k, t(values[k]) if values[k] and t in primitives else values[k])
                  for k, t in self._api_attributes)
    self.__dict__.update(values)

  def dumps(self):
    return pickle.dumps(self, pickle.HIGHEST_PROTOCOL)

  @staticmethod
  def loads(strval):
    return pickle.loads(strval)

  def __hash__(self):
    return reduce(lambda x, y: x ^ hash(y), self.__dict__.iteritems(), 1)

  def __str__(self):
    return repr(self)

  def __repr__(self):
    return "%s(%s)" % (
        self.__class__.__name__,
        ", ".join("%s=%s" % (k,repr(v)) for k,v in self.__dict__.items())
    )

  def __eq__(self, other):
    return type(self) == type(other) and self.__dict__ == other.__dict__


class ErrorKey(ApiObject):
  _api_attributes = [
    ('filename', str),
    ('line_number', int),
    ('function_name', str),
    ('text', str),
  ]


class StackLine(ApiObject):
  _api_attributes = [
    ('filename', str),
    ('line_number', int),
    ('function_name', str),
    ('text', str),
    ('frame_locals', dict),
  ]


class RecordErrorRequest(ApiObject):
  _api_attributes = [
    ('traceback', list),
    ('exception_message', str),
    ('hostname', str),
    ('error_threshold', int),
    ('additional_info', str),
  ]


class ErrorInfo(ApiObject):
  _api_attributes = [
    ('error_count', int),
    ('developer_email', str),
    ('date', str),
    ('email_sent', bool),
    ('last_occurrence', str),
    ('is_known_error', bool),
    ('last_error_data', RecordErrorRequest),
  ]

########NEW FILE########
__FILENAME__ = configure_server
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import ConfigParser
import os
import os.path
import readline
import subprocess
import threading
import sys
import socket
import shutil

import flawless.lib.config
from flawless.lib.version_control import repo

def interview(conf_path):
  options = dict(
    log_level="WARNING",
    port="9028",
  )

  print "Configure server host & port"
  print   "----------------------------"
  options["port"] = raw_input("What port should the server listen on (suggested: 9028): ")
  options["hostname"] = raw_input("Internet browser accessible hostname to access this server "
                                  "(ex: http://%s): " % socket.gethostname())

  print "\nConfigure Email"
  print   "---------------"
  options["smtp_host"] = raw_input("What is host:port for your smtp server (ex: smtphost:25): ").strip()
  smtp_user = raw_input("What is the username should flawless use to access your smtp "
                        "server (leave blank if username not required)? ").strip()
  if smtp_user:
    options["smtp_user"] = smtp_user
    options["smtp_password"] = raw_input("What is %s's password? " % smtp_user).strip()
  options["email_domain_name"] = raw_input("What is your email domain (ex: example.com): ").strip()
  options["ignore_vcs_email_domain"] = raw_input("Are all developer emails on %s (y/n): " %
                                               options["email_domain_name"])[0] in ['y', 'Y']
  options["default_contact"] = raw_input("If Flawless can't figure out which developer to email, "
                                         "what should be the default email address that Flawless "
                                         "sends to? ").strip()

  print "\nConfigure Directory Paths"
  print   "-------------------------"
  conf_dir_path = os.path.dirname(conf_path)
  if (raw_input("Use %s as the directory to store configuration information (y/n)? " %
      conf_dir_path).strip()[0] in ['n', 'N']):
    conf_dir_path = raw_input("Enter desired configuration directory path: ").strip()
    if not os.path.exists(conf_dir_path):
      os.makedirs(conf_dir_path)
      copy_files = True
    else:
      copy_files = raw_input("Overwrite existing files in %s (y/n)? " % conf_dir_path).strip()[0] in ['y', 'Y']

    if copy_files:
      default_dir = os.path.dirname(flawless.lib.config.default_path)
      files_to_copy = [f for f in os.listdir(default_dir)
                       if not f.startswith('.')]
      for filename in files_to_copy:
        shutil.copy2(os.path.join(default_dir, filename), conf_dir_path)
  options["data_dir_path"] = raw_input("Enter path to directory were Flawless can persist "
                                       "error data to disk (ex: /tmp/flawless/): ").strip()

  print "\nConfigure Repository Access"
  print   "---------------------------"

  if subprocess.call(["which", "git"], stdout=open(os.devnull)):
    print "Could not detect git. Please enter path to git executable"
    git_cli_path = raw_input("path to git binary: ")
    options["git_cli_path"] = git_cli_path

  print "Flawless needs access to a regularly updated copy of your repo in order to run git-blame"
  print "and determine which developer caused an error. Flawless can either checkout"
  print "and manage the repo iteself, or you can just provide the directory path to"
  print "the repo and mange keeping the repo up to date yourself\n"
  repo_url = repo_dir = branch_pattern = None
  if raw_input("Should Flawless checkout a copy of your repo (y/n): ")[0] in ['y', 'Y']:
    print "Please enter the URI for the repo, including username & password if necessary"
    print "Examples: https://username:password@example.com/path/repo.git or"
    print "git://username@example.com/repo.git"
    repo_url = raw_input("Git remote URI: ").strip()
    repo_dir = raw_input("Where should the repo live (ex: /tmp/flawless_repo): ").strip()

    if raw_input("Do you cut release branches for the code flawless will monitor (y/n)? ")[0] in ['y', 'Y']:
      print "Flawless will regularly check for new branches and always work off the latest branch"
      print "Latest branch is determined by sorting branch names by name"
      print "Please enter a Python regular expression that identifies your release branch names"
      print "Example: example-server-release"
      branch_pattern = raw_input("regexp: ").strip()
  else:
    repo_dir = raw_input("What is the filepath to your git repo (ex: /tmp/repo): ").strip()

  options["repo_dir"] = repo_dir
  options["repo_url"] = repo_url
  options["repo_branch_pattern"] = branch_pattern
  options["repo_type"] = "git"

  print "\nBasic configuration done"
  if raw_input("Overwrite flawless.cfg (y/n)? ")[0] in ['y', 'Y']:
    parser = ConfigParser.SafeConfigParser()
    config_path = os.path.join(conf_dir_path, "flawless.cfg")
    parser.read(config_path)
    if not parser.has_section("flawless"):
      parser.add_section("flawless")
    for option, value in options.items():
      if value is not None:
        parser.set("flawless", str(option), str(value))
    with open(config_path, "w") as fh:
      parser.write(fh)

  if repo_url:
    print "\nYou elected to have flawless manage a copy of your git repo. Flawless will now attempt to"
    print "clone your repo"
    new_repo = repo.GitRepository(local_path=repo_dir,
                                  remote_url=repo_url,
                                  branch_pattern=branch_pattern)
    new_repo.create()

  print "\n\nSetup complete!"
  print "Start the server by running:"
  print "flawless start -conf %s" % os.path.join(conf_dir_path, "flawless.cfg")
  print ("Check server is running by visiting http://%s:%s/check_health" %
         (options["hostname"], options["port"]))




if __name__ == '__main__':
  interview(flawless.lib.config.default_path)

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import os.path
import sys

import flawless.lib.config
import flawless.server.server
import flawless.server.configure_server



def show_options():
  for option in flawless.lib.config.OPTIONS:
    print option.name
    print "  default value: %s" % repr(option.default)
    print "  type: %s" % str(option.type)
    print "  description: %s\n" % option.description

def usage():
  print "Usage: flawless [start|configure|options|help] [-conf path]"
  print "  Commands:"
  print "    start - Start the server"
  print "    configure - Run server setup script"
  print "    options - Display list of server configuration options for flawless.cfg"
  print "    help - Display this description"
  print "  Options:"
  print "    -conf path: Path to flawless.cfg"


def main():
  conf_path = flawless.lib.config.default_path

  command = None if len(sys.argv) > 1 else usage
  args_list = list(reversed(sys.argv[1:]))
  while args_list:
    arg = args_list.pop()
    if arg == "start" and not command:
      command = lambda: flawless.server.server.serve(conf_path)
    elif arg == "configure" and not command:
      command = lambda: flawless.server.configure_server.interview(conf_path)
    elif arg == "options" and not command:
      command = show_options
    elif arg == "help" and not command:
      command = usage
    elif arg == "-conf":
      if not args_list:
        command = usage
        break
      conf_path = args_list.pop()
    else:
      command = usage
      break

  command()


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import functools
import logging
import os.path
from SocketServer import ThreadingMixIn
import sys
import urlparse

import flawless.lib.config
from flawless.server.service import FlawlessService

log = logging.getLogger(__name__)
config = flawless.lib.config.get()

class SimpleThreadedHTTPServer(ThreadingMixIn, HTTPServer):
  def attach_service(self, service):
    self.service = service

  def server_close(self):
    HTTPServer.server_close(self)
    self.service.errors_seen.sync()


class SimpleRequestHTTPHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    parts = urlparse.urlparse(self.path)
    kwargs = dict(urlparse.parse_qsl(parts.query))
    ret = None

    try:
      if hasattr(self.server.service, parts.path[1:] or "index"):
        ret = getattr(self.server.service, parts.path[1:]  or "index")(**kwargs)
        self.send_response(200)
        self.send_header('Content-Length', len(ret or ""))
        self.send_header('Content-Type', 'text/html')
      else:
        self.send_response(404)
    except Exception as e:
      log.exception(e)
      self.send_response(500)
    finally:
      self.end_headers()
    if ret:
      self.wfile.write(ret)

  def do_POST(self):
    # Read in POST body
    parts = urlparse.urlparse(self.path)
    content_length = int(self.headers.getheader("Content-Length"))
    req_str = self.rfile.read(content_length)

    ret = None
    try:
      ret = getattr(self.server.service, parts.path[1:])(req_str)
      self.send_response(200)
      if ret:
        self.send_header('Content-Length', len(ret))
        self.send_header('Content-Type', 'text/html')
    except Exception as e:
      log.exception(e)
      self.send_response(500)
    finally:
      self.end_headers()

    if ret:
      self.wfile.write(ret)


def serve(conf_path):
  flawless.lib.config.init_config(conf_path)
  # Try and create datadir if it doesn't exist. For instance it might be in /tmp
  if not os.path.exists(config.data_dir_path):
    os.makedirs(config.data_dir_path)

  logging.basicConfig(level=getattr(logging, config.log_level), filename=config.log_file,
                      stream=sys.stderr)
  flawless_service = FlawlessService()
  server = SimpleThreadedHTTPServer(('', config.port), SimpleRequestHTTPHandler)
  server.attach_service(flawless_service)
  server.request_queue_size = 50
  try:
    server.serve_forever()
  except KeyboardInterrupt:
    server.server_close()

def main():
  conf_path = flawless.lib.config.default_path
  if len(sys.argv) > 1:
    conf_path = sys.argv[1]
  serve(conf_path)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = service
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

from __future__ import absolute_import
import __main__

import cgi
import copy
import email
import collections
import datetime
import inspect
import logging
import os
import os.path
import pickle
import re
import shutil
import smtplib
import subprocess
import sys
import threading
import time
import traceback
import urllib
import urlparse

import flawless.lib.config
from flawless.lib.data_structures.persistent_dictionary import PersistentDictionary
from flawless.lib.data_structures import prefix_tree
from flawless.lib.version_control.repo import get_repository
from flawless.server import api

try:
  import simplejson as json
except:
  import json


log = logging.getLogger(__name__)
config = flawless.lib.config.get()

def dump_json(obj):
  return json.dumps(
      obj,
      indent=2,
      separators=(',', ': '),
      default=lambda o: dict((k,v) for k,v in o.__dict__.items() if v is not None),
  )


class CodeIdentifierBaseClass(object):
  def __init__(self, filename, function_name=None, code_fragment=None, min_alert_threshold=None,
               max_alert_threshold=None, email_recipients=None, email_header=None,
               alert_every_n_occurences=None):
    if not filename:
      raise ValueError("filename is required")
    self.filename = filename
    self.function_name = function_name
    # Condense whitespace to make comparissions more forgiving
    self.code_fragment = None if not code_fragment else re.sub("\s+", " ", code_fragment)

    # Optional fields
    self.min_alert_threshold = min_alert_threshold
    self.max_alert_threshold = max_alert_threshold
    self.email_recipients = email_recipients
    self.email_header = email_header
    self.alert_every_n_occurences = alert_every_n_occurences

  def to_json(self):
    return dump_json(dict((k,v) for k,v in self.__dict__.items() if v))

  def __str__(self):
    return repr(self)

  def __repr__(self):
    return "%s(%s)" % (
        self.__class__.__name__,
        ", ".join("%s=%s" % (k,repr(v)) for k,v in self.__dict__.items())
    )

  def __eq__(self, other):
    # We allow people to whitelist entire files, or functions by setting function_name to None or
    # code-fragment to None
    if not isinstance(other, CodeIdentifierBaseClass):
      return False
    if self.filename != other.filename:
      return False
    if self.function_name and other.function_name and self.function_name != other.function_name:
      return False
    if (self.code_fragment and other.code_fragment and self.code_fragment not in other.code_fragment
        and other.code_fragment not in self.code_fragment):
      return False

    return True


class KnownError(CodeIdentifierBaseClass):
  def __init__(self, *args, **kwargs):
    super(KnownError, self).__init__(*args, **kwargs)
    if (self.min_alert_threshold == self.max_alert_threshold == self.alert_every_n_occurences == None):
      raise ValueError("One of the following must be set: min_alert_threshold, "
                       "max_alert_threshold, or alert_every_n_occurences")

class StackTraceEntry(CodeIdentifierBaseClass):
  def __init__(self, filename, function_name, code_fragment):
    if not (filename and function_name and code_fragment):
      raise ValueError("filename, function_name, and code_fragment are required")
    super(StackTraceEntry, self).__init__(filename, function_name, code_fragment)


class BuildingBlock(CodeIdentifierBaseClass):
  def __init__(self, filename, function_name=None, code_fragment=None):
    super(BuildingBlock, self).__init__(filename, function_name, code_fragment)


class ThirdPartyWhitelistEntry(CodeIdentifierBaseClass):
  def __init__(self, filename, function_name=None, code_fragment=None):
    super(ThirdPartyWhitelistEntry, self).__init__(filename, function_name, code_fragment)


class LineTypeEnum(object):
  DEFAULT = 1
  KNOWN_ERROR = 2
  BUILDING_BLOCK = 3
  THIRDPARTY_WHITELIST = 4
  IGNORED_FILEPATH = 5
  BAD_FILEPATH = 6

class FlawlessService(object):
  ############################## CONSTANTS ##############################

  # Validates that email address is valid. Does not attempt to be RFC compliant
  #   local part: any alphanumeric or ., %, +, \, -, _
  #   domain part: any alphanumeric. Dashes or periods allowed as long as they are not followed
  #                by a period
  #   top level domain: between 2 to 4 alpha chracters
  VALIDATE_EMAIL_PATTERN = \
    re.compile(r"^[A-Za-z0-9.%+\-_]+@(?:(?:[a-zA-Z0-9]+-?)*[a-zA-Z0-9]\.)+[A-Za-z]{2,4}$")

  ############################## Init ##############################

  def __init__(self, persistent_dict_cls=PersistentDictionary,
               thread_cls=threading.Thread,
               open_file_func=open, open_process_func=subprocess.Popen,
               smtp_client_cls=smtplib.SMTP, time_func=time.time):
    self.open_file_func = open_file_func
    self.open_process_func = open_process_func
    self.smtp_client_cls = smtp_client_cls
    self.persistent_dict_cls = persistent_dict_cls
    self.time_func = time_func
    self.thread_cls = thread_cls
    self.number_of_git_blames_running = 0

    self.building_blocks = self._parse_whitelist_file("building_blocks", BuildingBlock)
    self.third_party_whitelist = self._parse_whitelist_file("third_party_whitelist",
                                                            ThirdPartyWhitelistEntry)
    self.known_errors = self._parse_whitelist_file("known_errors", KnownError)
    self.email_remapping = dict((e["remap"], e["to"]) for e in self._read_json_file("email_remapping"))
    self.watch_all_errors, self.watch_only_if_blamed = self._parse_watchers_file("watched_files")

    self.repository = get_repository(open_process_func=open_process_func)

    self.extract_base_path_pattern = re.compile('^.*/%s/?(.*)$' %
                                                config.report_runtime_package_directory_name)
    self.only_blame_patterns = [re.compile(p) for p in config.only_blame_filepaths_matching]

    self.lock = threading.RLock()
    self.errors_seen = None
    self._refresh_errors_seen()

    self.persist_thread = self.thread_cls(target=self._run_background_update_thread)
    self.persist_thread.daemon = True
    self.persist_thread.start()

  ############################## Parse Config Files ##############################

  def _read_json_file(self, filename):
    # All configuration files are stored a json lists. The convention in this package
    # is to treats all strings in the top level list as comments
    with self.open_file_func(os.path.join(config.config_dir_path, filename), "r") as fh:
       return [o for o in json.loads(fh.read().strip()) if not isinstance(o, basestring)]

  def _parse_whitelist_file(self, filename, parsed_cls):
    parsed_objs = collections.defaultdict(list)
    for json_entry in self._read_json_file(filename):
      py_entry = parsed_cls(**json_entry)
      parsed_objs[py_entry.filename].append(py_entry)
    return parsed_objs

  def _parse_watchers_file(self, filename):
    all_error_tree = prefix_tree.FilePathTree()
    blame_only_tree = prefix_tree.FilePathTree()

    for watch in self._read_json_file(filename):
      tree = all_error_tree if watch.get("watch_all_errors") else blame_only_tree
      if watch["filepath"] not in tree:
        tree[watch["filepath"]] = list()
      tree[watch["filepath"]].append(watch["email"])

    # Set all_error_tree to have accumulator that will allow us to find everyone who was watching
    # the file or a parent of the file
    all_error_tree.set_accumulator(
      accumulator_intializer=list(),
      accumulator_func=lambda x, y: x + y if y else x,
    )

    return all_error_tree, blame_only_tree


  ############################## Update Thread ##############################

  def _file_path_for_ms(self, epoch_ms):
    timestamp_date = self._convert_epoch_ms(cls=datetime.date, epoch_ms=epoch_ms)
    timestamp_date = timestamp_date - datetime.timedelta(days=timestamp_date.isoweekday() % 7)
    file_path = os.path.join(config.data_dir_path,
                             "flawless-errors-" + timestamp_date.strftime("%Y-%m-%d"))
    return file_path

  def _refresh_errors_seen(self, epoch_ms=None):
    file_path = self._file_path_for_ms(epoch_ms)
    with self.lock:
      if self.errors_seen is None:
        self.errors_seen = self.persistent_dict_cls(file_path)
        self.errors_seen.open()
      elif file_path != self.errors_seen.get_path():
        # Order matters here since there can be a race condition if not done correctly
        old_errors_seen = self.errors_seen
        new_errors_seen = self.persistent_dict_cls(file_path)
        new_errors_seen.open()
        self.errors_seen = new_errors_seen
        old_errors_seen.close()

  def _run_background_update_thread(self):
    while True:
      time.sleep(300)
      tasks_to_run = [
        lambda: self.errors_seen.sync(),
        lambda: self._refresh_errors_seen(),
        lambda: self.repository.update(),
      ]
      # Run all items in try/except block because we don't want our background thread
      # to die.
      for task in tasks_to_run:
        try:
          task()
        except Exception as e:
          self._handle_flawless_issue("<br />".join(traceback.format_exception(*sys.exc_info())))

  ############################## Misc Helper Funcs ##############################

  def _sendmail(self, to_addresses, subject, body):
    host, port = config.smtp_host.split(":")
    smtp_client = self.smtp_client_cls(host, int(port))

    invalid_addresses = [e for e in to_addresses if
                         not bool(self.VALIDATE_EMAIL_PATTERN.match(e))]
    if invalid_addresses:
      to_addresses = [e for e in to_addresses if e not in invalid_addresses]
      self._handle_flawless_issue(
        "Invalid email address found. Not sending to: %s" % ", ".join(invalid_addresses),
        log_func=log.warning,
      )

    msg = email.MIMEText.MIMEText(body.encode("UTF-8"), "html", "UTF-8")
    msg["From"] = "error_report@%s" % config.email_domain_name
    msg["To"] = ", ".join(to_addresses)
    msg["Subject"] = subject

    if config.smtp_user and config.smtp_password:
      smtp_client.login(config.smtp_user, config.smtp_password)
    smtp_client.sendmail(msg["From"], to_addresses, msg.as_string())
    smtp_client.quit()

  def _get_email(self, email):
    '''Given an email address, check the email_remapping table to see if the email
    should be sent to a different address. This function also handles overriding
    the email domain if ignore_vcs_email_domain is set or the domain was missing'''
    if not email or "@" not in email:
      return None

    if email in self.email_remapping:
      return self.email_remapping[email]
    prefix, domain = email.split("@", 2)
    if prefix in self.email_remapping:
      return self.email_remapping[prefix]
    if "." not in domain or config.ignore_vcs_email_domain:
      return "%s@%s" % (prefix, config.email_domain_name)
    return email

  def _convert_epoch_ms(self, cls, epoch_ms=None):
    if not epoch_ms:
      epoch_ms = int(self.time_func() * 1000)
    return cls.fromtimestamp(epoch_ms / 1000.)

  def _matches_filepath_pattern(self, filepath):
    '''Given a filepath, and a list of regex patterns, this function returns true
    if filepath matches any one of those patterns'''
    if not self.only_blame_patterns:
      return True

    for pattern in self.only_blame_patterns:
      if pattern.match(filepath):
        return True
    return False

  def _get_entry(self, entry, entry_tree):
    '''Helper function for retrieving a particular entry from the prefix trees'''
    for e in entry_tree[entry.filename]:
      if entry == e:
        return e

  def _handle_flawless_issue(self, message, log_func=log.error):
    log_func(message)
    if config.default_contact:
      self._sendmail([config.default_contact], "Unexpected problem on Flawless Server", message)

  def _get_line_type(self, line):
    match = self.extract_base_path_pattern.match(line.filename)
    if not match:
      return LineTypeEnum.BAD_FILEPATH

    filepath = match.group(1)
    entry = StackTraceEntry(filepath, line.function_name, line.text)
    if entry in self.third_party_whitelist[filepath]:
      return LineTypeEnum.THIRDPARTY_WHITELIST
    elif not self._matches_filepath_pattern(filepath):
      return LineTypeEnum.IGNORED_FILEPATH
    elif entry in self.building_blocks[filepath]:
      return LineTypeEnum.BUILDING_BLOCK
    elif entry in self.known_errors[filepath]:
      return LineTypeEnum.KNOWN_ERROR
    else:
      return LineTypeEnum.DEFAULT

  def _format_traceback(self, request, append_locals=True, show_full_stack=False,
                        linebreak="<br />", spacer="&nbsp;", start_bold="<strong>",
                        end_bold="</strong>", escape_func=cgi.escape):
    # Traceback
    parts = []
    parts.append("{b}Traceback (most recent call last):{xb}".format(b=start_bold, xb=end_bold))
    formatted_stack = [
      '{sp}{sp}File "{filename}", line {line}, in {function}{lb}{sp}{sp}{sp}{sp}{code}'.format(
        sp=spacer, lb=linebreak, filename=l.filename, line=l.line_number,
        function=l.function_name, code=escape_func(l.text),
      )
      for l in request.traceback
    ]
    parts.extend(formatted_stack)
    parts.append(escape_func(request.exception_message))

    # Frame Locals
    parts.append(linebreak * 2 + "{b}Stack Frame:{xb}".format(b=start_bold, xb=end_bold))
    frames_to_show = [l for l in request.traceback if l.frame_locals is not None and
                      (self._get_line_type(l) in [LineTypeEnum.KNOWN_ERROR, LineTypeEnum.DEFAULT]
                       or show_full_stack)]
    for l in frames_to_show:
      line_info = '{sp}{sp}{b}File "{filename}", line {line}, in {function}{xb}'.format(
        sp=spacer, filename=l.filename, line=l.line_number, function=l.function_name,
        b=start_bold, xb=end_bold,
      )
      local_vals = ['{sp}{sp}{sp}{sp}{name}={value}'.format(
                        sp=spacer, name=name, value=escape_func(value.decode("UTF-8", "replace")))
                    for name, value in sorted(l.frame_locals.items())]
      parts.append(line_info)
      parts.extend(local_vals or [spacer * 4 + "No variables in this frame"])

    # Additional Information
    if request.additional_info:
      parts.append(linebreak * 2 + "{b}Additional Information:{xb}".format(b=start_bold, xb=end_bold))
      parts.append(
          escape_func(request.additional_info.decode("UTF-8", "replace")).replace("\n", linebreak)
      )

    return linebreak.join(parts)

  ############################## Record Error ##############################

  def record_error(self, request):
      t = self.thread_cls(target=self._record_error, args=[request])
      t.start()

  def _blame_line(self, traceback):
    '''Figures out which line in traceback is to blame for the error.
    Returns a 3-tuple of (api.ErrorKey, StackTraceEntry, [email recipients])'''
    key = None
    blamed_entry = None
    email_recipients = []
    for stack_line in traceback:
      line_type = self._get_line_type(stack_line)
      if line_type == LineTypeEnum.THIRDPARTY_WHITELIST:
        return None, None, None
      elif line_type in [LineTypeEnum.DEFAULT, LineTypeEnum.KNOWN_ERROR]:
        filepath = self.extract_base_path_pattern.match(stack_line.filename).group(1)
        entry = StackTraceEntry(filepath, stack_line.function_name, stack_line.text)
        blamed_entry = entry
        key = api.ErrorKey(filepath, stack_line.line_number,
                           stack_line.function_name, stack_line.text)
        if filepath in self.watch_all_errors:
          email_recipients.extend(self.watch_all_errors[filepath])
    return (key, blamed_entry, email_recipients)


  def _record_error(self, request):
    # Parse request
    request = api.RecordErrorRequest.loads(request)

    # Figure out which line in the stack trace is to blame for the error
    key, blamed_entry, email_recipients = self._blame_line(request.traceback)
    if not key:
      return

    # If this error hasn't been reported before, then find the dev responsible
    err_info = None
    if key not in self.errors_seen:
      # If flawless is being flooded wih errors, limit the number of git blames so the
      # service doesn't fall over. We don't use a thread safe counter, because 10
      # git blames is just a soft limit
      if self.number_of_git_blames_running > config.max_concurrent_git_blames:
        log.error("Unable to process %s because %d git blames already running" %
                  (str(key), self.number_of_git_blames_running))
        return
      try:
        self.number_of_git_blames_running += 1
        email, last_touched_ts = self.repository.blame(key.filename, key.line_number)
      finally:
        self.number_of_git_blames_running -= 1
      dev_email = self._get_email(email)
      last_touched_ts = last_touched_ts or 0

      cur_time = self._convert_epoch_ms(datetime.datetime).strftime("%Y-%m-%d %H:%M:%S")
      mod_time = self._convert_epoch_ms(datetime.datetime, epoch_ms=last_touched_ts * 1000)
      mod_time = mod_time.strftime("%Y-%m-%d %H:%M:%S")
      known_entry = self._get_entry(blamed_entry, self.known_errors)
      err_info = api.ErrorInfo(error_count=1,
                               developer_email=dev_email or "unknown",
                               date=mod_time,
                               email_sent=False,
                               last_occurrence=cur_time,
                               is_known_error=bool(known_entry),
                               last_error_data=request)
      self.errors_seen[key] = err_info
      log.info("Error %s caused by %s on %s" % (str(key), dev_email, mod_time))

      if not dev_email:
        self._handle_flawless_issue("Unable to do blame for %s. You may want to consider setting "
                                    "only_blame_filepaths_matching in your flawless.cfg " % str(key))
        err_info.email_sent = True
        return
    # If we've already seen this error then update the error count
    elif key in self.errors_seen:
      err_info = self.errors_seen[key]
      err_info.error_count += 1
      err_info.last_error_data = request
      cur_dt = self._convert_epoch_ms(datetime.datetime)
      err_info.last_occurrence = cur_dt.strftime("%Y-%m-%d %H:%M:%S")
      self.errors_seen[key] = err_info

    # Figure out if we should send an email or not
    send_email = False
    known_entry = None
    if blamed_entry not in self.known_errors[blamed_entry.filename]:
      # If it is an unknown error, then it must meet certain criteria. The code must have been
      # touched after report_only_after_minimum_date so errors in old code can be ignored. It
      # also has to have occurred at least report_error_threshold times (although the client
      # is allowed to override that value).
      if (not err_info.email_sent and err_info.date >= config.report_only_after_minimum_date and
          err_info.error_count >= (request.error_threshold or config.report_error_threshold)):
        send_email = True
    else:
      # If it is a known error, we allow fine grainted control of how frequently emails will
      # be sent. An email will be sent if it has passed the min_alert_threshold, and/or this
      # is the Nth occurrence as defined alert_every_n_occurences. If it has passed
      # max_alert_threshold then no emails will be sent.
      known_entry = self._get_entry(blamed_entry, self.known_errors)
      if (known_entry.min_alert_threshold and err_info.error_count >= known_entry.min_alert_threshold
          and not err_info.email_sent):
        send_email = True
      if (known_entry.alert_every_n_occurences and
            err_info.error_count % known_entry.alert_every_n_occurences == 0):
        send_email = True
      if (known_entry.max_alert_threshold is not None
          and err_info.error_count > known_entry.max_alert_threshold):
        send_email = False

    # Send email if applicable
    if send_email:
      email_body = []
      dev_email = self._get_email(err_info.developer_email)
      if dev_email:
        email_recipients.append(dev_email)

      # Add additional recipients that have registered for this error
      if blamed_entry.filename in self.watch_only_if_blamed:
        email_recipients.extend(self.watch_only_if_blamed[blamed_entry.filename])
      if known_entry:
        email_recipients.extend(known_entry.email_recipients or [])
        email_body.append(known_entry.email_header or "")

      email_body.append(self._format_traceback(request))
      email_body.append(
        "<br /><br /><a href='http://%s/add_known_error?%s'>Add to whitelist</a>" %
        (config.hostname + ":" + str(config.port),
         urllib.urlencode(
           dict(filename=key.filename, function_name=key.function_name, code_fragment=key.text)
         )
        )
      )

      # Send the email
      log.info("Sending email for %s to %s" % (str(key), ", ".join(email_recipients)))
      self._sendmail(
          to_addresses=email_recipients,
          subject="Error on %s in %s" % (request.hostname, key.filename),
          body="<br />".join([s for s in email_body if s]),
      )
      err_info.email_sent = True
      self.errors_seen[key] = err_info

  ############################## Summarize Errors ##############################

  def index(self, *args, **kwargs):
    return self.get_weekly_error_report(*args, **kwargs)

  def get_weekly_error_report(self, timestamp=None, include_known_errors=False,
                              include_modified_before_min_date=False):
    file_path = self._file_path_for_ms(int(timestamp) * 1000) if timestamp else None
    retdict = dict()
    if timestamp is None or self.errors_seen.get_path() == file_path:
      retdict = self.errors_seen.dict
    else:
      report = self.persistent_dict_cls(file_path)
      report.open()
      retdict = report.dict
    html_parts = ["<html><head><title>Error Report</title></head><body>"]

    grouped_errors = collections.defaultdict(list)
    developer_score = collections.defaultdict(int)
    for key, value in retdict.items():
      if ((not value.is_known_error or include_known_errors) and
          (value.date >= config.report_only_after_minimum_date or include_modified_before_min_date)):
        grouped_errors[value.developer_email].append((key, value))
        developer_score[value.developer_email] += value.error_count

    for developer, score in sorted(developer_score.items(), key=lambda t: t[1], reverse=True):
      html_parts.append("<strong>%s (score: %d)</strong>" % (developer, score))
      for err_key, err_info in grouped_errors[developer]:
        html_parts.append("Number of Occurrences: " + str(err_info.error_count))
        html_parts.append("Last Occurred: " + err_info.last_occurrence)
        html_parts.append("Filename: " + err_key.filename)
        html_parts.append("Function Name: " + err_key.function_name)
        html_parts.append("Line Number: " + str(err_key.line_number))
        html_parts.append("Date Committed: " + err_info.date)
        html_parts.append("Email Sent: " + str(err_info.email_sent))
        params = copy.copy(err_key.__dict__)
        if timestamp:
          params["timestamp"] = timestamp
        view_url = "http://%s/view_traceback?%s" % (config.hostname + ":" + str(config.port),
                                                    urllib.urlencode(params))
        html_parts.append("<a href='%s'>view traceback</a>" % view_url)
        html_parts.append("<br />")
      html_parts.append("<br />")

    if not grouped_errors:
      html_parts.append("Wow, no errors. Great job!")
    return "<br />".join(html_parts)

  def view_traceback(self, filename="", function_name="", text="", line_number="", timestamp=None):
    file_path = self._file_path_for_ms(int(timestamp) * 1000) if timestamp else None
    errdict = dict()
    if timestamp is None or self.errors_seen.get_path() == file_path:
      errdict = self.errors_seen.dict
    else:
      report = self.persistent_dict_cls(file_path)
      report.open()
      errdict = report.dict

    err_key = api.ErrorKey(filename=filename, function_name=function_name,
                           text=text, line_number=line_number)
    err_info = errdict.get(err_key)
    datastr = "Not Found"
    if err_info:
      datastr = self._format_traceback(err_info.last_error_data)
    return """
      <html>
        <head>
          <title>Flawless Traceback</title>
        </head>
        <body style='font-family: courier; font-size: 10pt'>
          {data}
        </body>
      </html>
    """.format(data=datastr)

  ############################## Add New Known Error ##############################

  def add_known_error(self, filename="", function_name="", code_fragment=""):
    code_fragment = cgi.escape(code_fragment)
    return """
      <html>
        <head>
          <title>Add Known Error</title>
        </head>
        <body>
        <div>
          Instructions: Fill out the file path, function name and code fragment for the known error.
          If function name or code fragment are left empty, then they are treated as wildcards.<br />
          Just entering file path, function name and code fragment will whitelist the error and stop
          all emails about it. If you want to continue emails, but at a lower (or higher)
          frequency or threshold you can use the optional fields.
        </div><br /><br />
        <form action='save_known_error' method='POST'>
          <table>
            <tr><td>* = Required</td></tr>
            <tr>
              <td>* File Path:</td>
              <td><input name='filename' type='text' value='{filename}' size='50'/></td>
            </tr>
            <tr>
              <td>* Function Name:</td>
              <td><input name='function_name' type='text'value='{function_name}' size='50'/></td>
            </tr>
            <tr>
              <td>* Code Fragment:</td>
              <td><textarea name='code_fragment' rows='1' cols='50'/>{code_fragment}</textarea></td>
            </tr>
            <tr>
              <td>* Error Type:</td>
              <td>
                <select name='type'>
                  <option value='known_errors' selected>Add to Known Errors</option>
                  <option value='building_blocks'>Mark as Library Code</option>
                  <option value='third_party_whitelist'>Add to Ignored Thirdparty Errors</option>
                </select>
              </td>
            </tr>
            <tr><td>&nbsp</td></tr>
            <tr><td><strong>Following section is only for known errors</strong></td></tr>
            <tr><td>Must set one of the following **</td></tr>
            <tr>
              <td>** Minimum Alert Threshold:</td>
              <td><input name='min_alert_threshold' type='text' /></td>
            </tr>
            <tr>
              <td>** Maximum Alert Threshold:</td>
              <td><input name='max_alert_threshold' type='text' /></td>
            </tr>
            <tr>
              <td>** Alert Every N Occurrences:</td>
              <td><input name='alert_every_n_occurences' type='text' /></td>
            </tr>
            <tr>
              <td>Email Recipients CSV:</td>
              <td><input name='email_recipients' type='text' size='50'/></td>
            </tr>
            <tr>
              <td>Email Header:</td>
              <td><textarea name='email_header' rows='5' cols='50'></textarea></td>
            </tr>
          </table>
          <input type='submit'></input>
        </form>
       </body>
      </html>
    """.format(**dict(locals().items()))

  def save_known_error(self, request):
    params = dict(urlparse.parse_qsl(request))
    class_map = dict(known_errors=KnownError, building_blocks=BuildingBlock,
                     third_party_whitelist=ThirdPartyWhitelistEntry)
    cls = class_map[params['type']]
    init_args = inspect.getargspec(CodeIdentifierBaseClass.__init__ if cls == KnownError
                                   else cls.__init__).args

    whitelist_attrs = [s for s in init_args if s != 'self']
    new_entry = cls(**dict((k,params.get(k)) for k in whitelist_attrs))
    filename = os.path.join(config.config_dir_path, params['type'])

    with self.open_file_func(filename, "r") as fh:
      contents = json.load(fh)
    with self.open_file_func(filename + ".tmp", "w") as fh:
      contents.append(new_entry)
      fh.write(dump_json(contents))
    shutil.move(filename + ".tmp", filename)

    getattr(self, params['type'])[new_entry.filename].append(new_entry)
    return "<html><body>SUCCESS</body></html>"

  def check_health(self):
    parts = ["<html><body>OK<br/>"]
    for option in flawless.lib.config.OPTIONS:
      parts.append("%s: %s" % (option.name, str(getattr(config, option.name))))
    parts.append("</body></html>")
    return "<br />".join(parts)


########NEW FILE########
__FILENAME__ = stub
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import inspect

import flawless.server.thrift.errors.ttypes as errors_ttypes
from flawless.server.thrift.errors import ErrorsService

class ErrorsServiceStub(object):
  def __init__(self):
    for func in [f for f in dir(self) if not f.startswith("_")]:
      getattr(self, func).__dict__["result"] = None
      getattr(self, func).__dict__["last_args"] = None
      getattr(self, func).__dict__["args_list"] = list()

  def _handle_stub(self, func, args):
   last_args = dict((k,v) for k,v in args.items() if k != "self")
   getattr(self, func).__dict__["last_args"] = last_args
   getattr(self, func).__dict__["args_list"].append(last_args)
   return getattr(self, func).__dict__["result"]

  def record_error(self, error_request):
    return self._handle_stub("record_error", locals())

  def get_weekly_error_report(self, timestamp):
    return self._handle_stub("get_weekly_error_report", locals())

  def open(self):
    pass

  def close(self):
    return True


########NEW FILE########
__FILENAME__ = flawless_daemon
# Disable relative imports, and remove magical current directory sys.path entry
from __future__ import absolute_import
import sys
if __name__ == "__main__": sys.path.pop(0)

import daemon
import daemon.pidlockfile
import lockfile
import os.path
import os

import flawless.server.server

def main(argv):
  # Process argv
  if len(argv) <= 1:
    print "\nUsage: python flawless_daemon.py FLAWLESS_CONFIG_PATH [PID_FILE_PATH]"
    print "  FLAWLESS_CONFIG_PATH - The path to the flawless.cfg config you want to use"
    print "  PID_FILE_PATH - (optional) The path you want to for the PID lock file\n"
    return
  flawless_cfg_path = os.path.abspath(argv[1])
  pid_file_path = os.path.abspath(argv[2]) if len(argv) == 3 else None

  # Initialize context
  context = daemon.DaemonContext()
  context.detach_process = True
  context.working_directory = '.'

  # Setup logging of output
  pid = os.getpid()
  filename = "flawless-%d.ERROR" % pid
  error_log = open(filename, "w+", 1)
  context.stdout = error_log
  context.stderr = error_log

  # Setup PID file
  if pid_file_path:
    context.pidfile = daemon.pidlockfile.TimeoutPIDLockFile(pid_file_path, acquire_timeout=2)

  try:
    with context:
      os.setpgid(0, os.getpid())
      flawless.server.server.serve(flawless_cfg_path)
  except lockfile.LockTimeout:
    sys.stderr.write("Error: Couldn't acquire lock on %s. Exiting.\n" % pid_file_path)
    sys.exit(1)


if __name__ == '__main__':
  main(sys.argv)

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import copy
import unittest


import flawless.client
import flawless.client.decorators
import flawless.server.api as api



@flawless.client.decorators.wrap_class
class ThriftTestHandler(object):

  def __init__(self):
    self.instancevar = 98

  def method(self, fail=False, result=42):
    return self._simulate_call(fail, result)

  @classmethod
  def classmeth(cls, fail=False, result=43):
    return cls._simulate_call(fail, result)

  @classmethod
  def _simulate_call(cls, fail=False, result=42):
    if fail:
      raise Exception()

    return result

  def check_health(self, fail=False, result=42, delay=0):
    return self._simulate_call(fail=fail, result=result, delay=delay)


class BaseErrorsTestCase(unittest.TestCase):

  def setUp(self):
    self.saved_send_func = flawless.client._send_request
    setattr(flawless.client, "_send_request", self._send_request_stub_func)
    self.saved_config = copy.deepcopy(flawless.lib.config.get().__dict__)
    self.test_config = flawless.lib.config.get()
    self.test_config.__dict__ = dict((o.name, o.default) for o in flawless.lib.config.OPTIONS)
    flawless.client.set_hostport("localhost")
    self.last_req = None
    self.req_list = []

  def tearDown(self):
    setattr(flawless.client, "_send_request", self.saved_send_func)
    flawless.lib.config.get().__dict__ = self.saved_config

  def _send_request_stub_func(self, req):
    self.last_req = req
    self.req_list.append(req)


class ClassDecoratorTestCase(BaseErrorsTestCase):
  def setUp(self):
    super(ClassDecoratorTestCase, self).setUp()
    self.handler = ThriftTestHandler()

  def test_returns_correct_result(self):
    self.assertEquals(56, self.handler.method(result=56))

  def test_returns_correct_result_for_classmethod(self):
    self.assertEquals(91, ThriftTestHandler.classmeth(result=91))

  def test_should_call_flawless_backend_on_exception(self):
    self.assertRaises(Exception, self.handler.method, fail=True)
    self.assertEquals(1, len(self.req_list))
    errorFound = False
    req_obj = api.RecordErrorRequest.loads(self.last_req.get_data())
    for row in req_obj.traceback:
      if row.function_name == "_simulate_call":
        errorFound = True
      if row.function_name == "method":
        self.assertEquals('98', row.frame_locals['self.instancevar'])
    self.assertTrue(errorFound)
    self.assertEqual(None, req_obj.error_threshold)

  def test_logs_classvars(self):
    self.assertRaises(Exception, self.handler.method, fail=True)
    self.assertEquals(1, len(self.req_list))
    errorFound = False
    req_obj = api.RecordErrorRequest.loads(self.last_req.get_data())
    for row in req_obj.traceback:
      if row.function_name == "_simulate_call":
        errorFound = True
    self.assertTrue(errorFound)
    self.assertEqual(None, req_obj.error_threshold)


class FunctionDecoratorTestCase(BaseErrorsTestCase):
  def setUp(self):
    super(FunctionDecoratorTestCase, self).setUp()

  @flawless.client.decorators.wrap_function
  def example_func(self, fail=False, retval=None):
    myvar = 7
    if fail:
      raise Exception(":(")
    return  retval

  @flawless.client.decorators.wrap_function(error_threshold=7, reraise_exception=False)
  def second_example_func(self, fail=False, retval=None):
    if fail:
      raise Exception("woohoo")
    return  retval

  def test_returns_correct_result(self):
    self.assertEquals(7, self.example_func(fail=False, retval=7))

  def test_should_call_flawless_backend_on_exception(self):
    self.assertRaises(Exception, self.example_func, fail=True)
    errorFound = False
    req_obj = api.RecordErrorRequest.loads(self.last_req.get_data())
    for row in req_obj.traceback:
      if row.function_name == "example_func":
        errorFound = True
    self.assertTrue(errorFound)
    self.assertEqual(None, req_obj.error_threshold)

  def test_decorator_with_kwargs(self):
    self.second_example_func(fail=True)
    errorFound = False
    req_obj = api.RecordErrorRequest.loads(self.last_req.get_data())
    for row in req_obj.traceback:
      if row.function_name == "second_example_func":
        errorFound = True
    self.assertTrue(errorFound)
    self.assertEqual(7, req_obj.error_threshold)

  def test_logs_locals(self):
    self.assertRaises(Exception, self.example_func, fail=True)
    errorFound = False
    req_obj = api.RecordErrorRequest.loads(self.last_req.get_data())
    for row in req_obj.traceback:
      if row.function_name == "example_func":
        errorFound = True
        self.assertEquals('7', row.frame_locals['myvar'])
    self.assertTrue(errorFound)
    self.assertEqual(None, req_obj.error_threshold)


class FuncThreadStub(object):
  def __init__(self, target):
    self.target = target

  def start(self):
    self.target()


if __name__ == '__main__':
  unittest.main()


########NEW FILE########
__FILENAME__ = prefix_tree_test
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import unittest

from flawless.lib.data_structures import prefix_tree

class PrefixTreeTestCase(unittest.TestCase):

  def setUp(self):
    super(PrefixTreeTestCase, self).setUp()

  def _flatten_branch(self, key, tree):
    head, tail = None, key
    node_chain = [tree.root]
    cur_node = tree.root
    while tail:
      head, tail = tree.split_key_func(tail)
      self.assertTrue(head in cur_node.branches)
      node_chain.append(cur_node.branches[head])
      cur_node = cur_node.branches[head]
    return node_chain

  def test_setting_value(self):
    tree = prefix_tree.StringPrefixTree()
    tree["abcd"] = 7
    expected_keys = ['a', 'b', 'c', 'd']
    node_chain = self._flatten_branch("abcd", tree)
    self.assertEquals(5, len(node_chain))
    for node in node_chain[1:-1]:
      self.assertEquals(node.value, None)
      self.assertEquals(node.is_set, False)
      self.assertEquals(1, node.size)

    self.assertEquals(True, node_chain[4].is_set)
    self.assertEquals(7, node_chain[4].value)
    self.assertEquals(1, node_chain[4].size)

  def test_getting_value(self):
    tree = prefix_tree.StringPrefixTree()
    tree["abcd"] = 7
    self.assertEquals(7, tree["abcd"])

  def test_len(self):
    tree = prefix_tree.StringPrefixTree()
    tree["abcd"] = 4
    tree["ab"] = 2
    node_chain = self._flatten_branch("abcd", tree)
    self.assertEquals(5, len(node_chain))
    self.assertEquals(2, len(tree))
    for index, node in enumerate(node_chain):
      if index in [2,4]:
        self.assertEquals(True, node.is_set)
        self.assertEquals(index, node.value)
      else:
        self.assertEquals(False, node.is_set)
        self.assertEquals(None, node.value)
      self.assertEquals(2 if index <= 2 else 1, node.size)

if __name__ == '__main__':
  unittest.main()

########NEW FILE########
__FILENAME__ = run
import os
import os.path
import unittest


def run():
  test_files = list()
  for base, _, files in os.walk('.'):
    for filename in files:
      if filename.endswith(".py") and "test" in filename:
        test_files.append(os.path.normpath(os.path.join(base, filename)))

  module_strings = [path[0:-3].replace('/', '.') for path in test_files]
  suites = [unittest.defaultTestLoader.loadTestsFromName(modpath) for modpath
            in module_strings]
  testSuite = unittest.TestSuite(suites)
  text_runner = unittest.TextTestRunner().run(testSuite)


if __name__ == '__main__':
  run()

########NEW FILE########
__FILENAME__ = service_test
#!/usr/bin/env python
#
# Copyright (c) 2011-2013, Shopkick Inc.
# All rights reserved.
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# ---
# Author: John Egan <john@shopkick.com>

import copy
import datetime
import email
import json
import time
import unittest
import StringIO

from flawless.lib.data_structures.stubs import PersistentDictionaryStub
import flawless.lib.config
from flawless.server import api
from flawless.server.service import *
import flawless.server.server



class BaseTestCase(unittest.TestCase):

  def setUp(self):
    super(BaseTestCase, self).setUp()
    self.popen_stub = POpenStub()
    self.popen_stub.stdout = StringIO.StringIO(
      "75563df6e9d1efe44b48f6643fde9ebbd822b0c5 25 25 1\n"
      "author John Egan\n"
      "author-mail <wishbone@shopkick.com>\n"
      "author-time %d\n"
      "author-tz -0800\n"
      "committer John Egan\n"
      "committer-mail <repo_master@shopkick.com>\n"
      "committer-time 1356245776\n"
      "committer-tz -0800\n"
      "summary Add more robust support for string keys\n"
      "previous 3491c7b8e298ec81dc7583163a118e7c2250999f safe_access.py\n"
      "filename safe_access.py\n"
      "               ex: a.b.[myvar] where myvar is passed in as a kwarg\n"
      % int(time.mktime(datetime.datetime(2017, 7, 30).timetuple()))
    )

    self._set_stub_time(datetime.datetime(2020, 1, 1))
    self.smtp_stub = SMTPClientStub()
    self.file_open_stub = OpenFileStub()

    self.watchers = [
      "TEST COMMENT",
      {
        "email": "wilfred@shopkick.com",
        "filepath": "tools/furminator.py",
        "watch_all_errors": True,
      },
      {
        "email": "lassie@shopkick.com",
        "filepath": "tools/furminator.py",
        "watch_all_errors": True,
      },
      "TEST COMMENT",
      {
        "email": "wishbone@shopkick.com",
        "filepath": "lib/no/such/path/for/testing.py",
        "watch_all_errors": True,
      },
    ]

    self.third_party_whitelist = [
      "TEST COMMENT",
      ThirdPartyWhitelistEntry('facebook.py', 'post_treat_to_facebook',
                     'urllib.urlencode(args), post_data)'),
      "TEST COMMENT",
      ThirdPartyWhitelistEntry(
          'SQLAlchemy-0.5.6-py2.6.egg/sqlalchemy/pool.py',
          'do_get',
          'raise exc.TimeoutError("QueuePool limit of size %d overflow %d ',
      ),
    ]

    self.known_errors = [
      KnownError(
        'lib/doghouse/authentication.py',
        'check_auth',
        'raise errors.BadAuthenticationError("Something smells off...")',
        max_alert_threshold=0,
      ),
      "TEST COMMENT",
      KnownError(
        filename='coreservices/waterbowl/rewards/water.py',
        function_name='make_external_api_request',
        code_fragment='raise api.WaterbowlError(error_code='
                      'api.WaterbowlErrorCode.OUT_OF_WATER, message=str(e))',
        email_recipients=["wilfred@shopkick.com", "snoopy@shopkick.com"],
        email_header = 'NOTE: This error typically does not require dev team involvement.',
        alert_every_n_occurences=1,
      ),
    ]

    self.building_blocks = [
      "TEST COMMENT",
      BuildingBlock('apps/shopkick/doghouse/lib/base.py',
                     '_get_request_param',
                     'raise errors.BadRequestError("Missing param %s" % name)'),
    ]

    self.file_open_stub.set_file('../config/building_blocks', dump_json(self.building_blocks))

    self.file_open_stub.set_file('../config/third_party_whitelist',
                                 dump_json(self.third_party_whitelist))
    self.file_open_stub.set_file('../config/known_errors', dump_json(self.known_errors))
    self.file_open_stub.set_file('../config/email_remapping', dump_json([]))
    self.file_open_stub.set_file('../config/watched_files', dump_json(self.watchers))

    self.saved_config = copy.deepcopy(flawless.lib.config.get().__dict__)
    self.test_config = flawless.lib.config.get()
    self.test_config.__dict__ = dict((o.name, o.default) for o in flawless.lib.config.OPTIONS)
    self.test_config.repo_dir = "/tmp"
    self.test_config.report_only_after_minimum_date = "2010-01-01"
    self.test_config.report_error_threshold = 1
    self.test_config.only_blame_filepaths_matching = [
      r"^coreservices(?!.*/thrift/).*$",
      r"lib/.*",
      r"tools/.*",
    ]
    self.test_config.report_runtime_package_directory_name = "site-packages"
    self.test_config.config_dir_path = "../config"

    self.handler = FlawlessService(
      open_process_func=self.popen_stub,
      persistent_dict_cls=PersistentDictionaryStub,
      smtp_client_cls=self.smtp_stub,
      time_func=lambda: self.stub_time,
      open_file_func=self.file_open_stub,
      thread_cls=ThreadStub,
    )

  def tearDown(self):
    super(BaseTestCase, self).tearDown()
    flawless.lib.config.get().__dict__ = self.saved_config

  def _set_stub_time(self, dt):
    self.stub_time = int(time.mktime(dt.timetuple()))

  def assertDictEquals(self, expected, actual):
    if expected == actual:
      return

    bad_keys = set(expected.keys()) ^ set(actual.keys())
    if bad_keys:
      keys_str = [str(key) for key in (set(expected.keys()) - set(actual.keys()))]
      errstr = "Keys not in second dict: %s" % "\n".join(keys_str)
      keys_str = [str(key) for key in (set(actual.keys()) - set(expected.keys()))]
      errstr += "\nKeys not in first dict:  %s" % "\n".join(keys_str)
      raise AssertionError("Missing/Extraneous keys:\n%s" % errstr)
    for key in expected.keys():
      if expected[key] != actual[key]:
        raise AssertionError("Value mismatch for key %s:\n%s\n%s" %
                             (key, str(expected[key]), str(actual[key])))

  def assertEmailEquals(self, expected, actual):
    self.assertEquals(expected["from_address"], actual["from_address"])
    self.assertEquals(set(expected["to_addresses"]), set(actual["to_addresses"]))
    parsed_email = email.message_from_string(actual["body"])
    self.assertEquals(expected["from_address"], parsed_email["From"])
    self.assertEquals(set(expected["to_addresses"]), set(parsed_email["To"].split(", ")))
    self.assertEquals(expected["subject"], parsed_email["Subject"])
    self.assertTrue(expected["body"] in parsed_email.get_payload(decode=True))


class RecordErrorTestCase(BaseTestCase):

  def setUp(self):
    super(RecordErrorTestCase, self).setUp()

  def test_records_error(self):
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/coreservices/service.py", 7, "serve", "..."),
                   api.StackLine("/site-packages/thirdparty/3rdparty_lib.py", 9, "call", "x")],
        exception_message="email text",
        hostname="localhost",
    )

    self.handler.record_error(req.dumps())
    self.assertDictEquals({api.ErrorKey("coreservices/service.py", 7, "serve", "..."):
                      api.ErrorInfo(1, "wishbone@shopkick.com", "2017-07-30 00:00:00", True, "2020-01-01 00:00:00",
                                    is_known_error=False, last_error_data=req)},
                     self.handler.errors_seen.dict)
    self.assertEqual(["git", "--git-dir=/tmp/.git", "--work-tree=/tmp", "blame",
                      "-p", "/tmp/coreservices/service.py", "-L", "7,+1"],
                     self.popen_stub.last_args)
    self.assertEmailEquals(dict(to_addresses=["wishbone@shopkick.com"],
                          from_address="error_report@example.com",
                          subject="Error on localhost in coreservices/service.py",
                          body="email text",
                          smtp_server_host_port=None),
                     self.smtp_stub.last_args)

  def test_records_error_with_thrift_in_file_name(self):
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/coreservices/thrift_file.py", 7, "serve", "..."),
                   api.StackLine("/site-packages/thirdparty/3rdparty_lib.py", 9, "call", "x")],
        exception_message="email text",
        hostname="localhost",
    )

    self.handler.record_error(req.dumps())
    self.assertDictEquals({api.ErrorKey("coreservices/thrift_file.py", 7, "serve", "..."):
                      api.ErrorInfo(1, "wishbone@shopkick.com", "2017-07-30 00:00:00", True, "2020-01-01 00:00:00",
                                    is_known_error=False, last_error_data=req)},
                     self.handler.errors_seen.dict)

  def test_ignores_error_in_thrift_directory(self):
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/thirdparty/3rdparty_lib.py", 9, "call", "x"),
                   api.StackLine("/site-packages/coreservices/thrift/file.py", 7, "serve", "...")],
        exception_message="email text",
        hostname="localhost",
    )

    self.handler.record_error(req.dumps())
    self.assertDictEquals({}, self.handler.errors_seen.dict)

  def test_doesnt_report_errors_under_threshold(self):
    self.test_config.report_error_threshold = 2
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/coreservices/service.py", 7, "serve", "..."),
                   api.StackLine("/site-packages/thirdparty/3rdparty_lib.py", 9, "call", "x")],
        exception_message="email text",
        hostname="localhost",
    )

    self.handler.record_error(req.dumps())
    self.assertDictEquals({api.ErrorKey("coreservices/service.py", 7, "serve", "..."):
                      api.ErrorInfo(1, "wishbone@shopkick.com", "2017-07-30 00:00:00", False, "2020-01-01 00:00:00",
                                    is_known_error=False, last_error_data=req)},
                     self.handler.errors_seen.dict)
    self.assertEquals(None, self.smtp_stub.last_args)

  def test_uses_threshold_specified_in_request(self):
    self.test_config.report_error_threshold = 2
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/coreservices/service.py", 7, "serve", "..."),
                   api.StackLine("/site-packages/thirdparty/3rdparty_lib.py", 9, "call", "x")],
        exception_message="email text",
        hostname="localhost",
        error_threshold=1,
    )

    self.handler.record_error(req.dumps())

    self.assertEmailEquals(dict(to_addresses=["wishbone@shopkick.com"],
                          from_address="error_report@example.com",
                          cc_address=None,
                          bcc_address=None,
                          subject="Error on localhost in coreservices/service.py",
                          body="email text",
                          smtp_server_host_port=None),
                     self.smtp_stub.last_args)

  def test_always_alerts_on_red_alert_errors(self):
    self.test_config.report_error_threshold = 3
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/coreservices/service.py", 7, "serve", "..."),
                   api.StackLine('/site-packages/coreservices/service/utils.py',
                                   9, "check_water_levels", '% (waterbowl_id, min_required_level))'),
                   api.StackLine("/site-packages/coreservices/waterbowl/rewards/water.py",
                                   5,
                                   "make_external_api_request",
                                   "raise api.WaterbowlError(error_code=api.WaterbowlErrorCode."
                                   "OUT_OF_WATER, message=str(e))"),
        ],
        exception_message="email text",
        hostname="localhost",
    )

    self.handler.record_error(req.dumps())

    # The 2 red alert recipients plus the developer responsible
    self.assertEmailEquals(dict(to_addresses=["wilfred@shopkick.com", "wishbone@shopkick.com",
                                              "snoopy@shopkick.com"],
                          from_address="error_report@example.com",
                          cc_address=None,
                          bcc_address=None,
                          subject="Error on localhost in coreservices/waterbowl/rewards/water.py",
                          body="email text",
                          smtp_server_host_port=None),
                     self.smtp_stub.last_args)

  def test_email_includes_watchers(self):
    # Almost the same setup as test_uses_threshold_specified_in_request except the traceback includes
    # a path that Yen is watching
    self.test_config.report_error_threshold = 2
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/tools/furminator.py", 7, "fubar", "..."),
                   api.StackLine("/site-packages/thirdparty/3rdparty_lib.py", 9, "call", "x")],
        exception_message="email text",
        hostname="localhost",
        error_threshold=1,
    )

    self.handler.record_error(req.dumps())
    self.assertEmailEquals(dict(to_addresses=["wilfred@shopkick.com", "wishbone@shopkick.com", "lassie@shopkick.com"],
                          from_address="error_report@example.com",
                          cc_address=None,
                          bcc_address=None,
                          subject="Error on localhost in tools/furminator.py",
                          body="email text",
                          smtp_server_host_port=None),
                     self.smtp_stub.last_args)

  def test_email_includes_extra_information(self):
    # Traceback includes a path that has extra_information tagged on it
    self.test_config.report_error_threshold = 2
    req = api.RecordErrorRequest(
        traceback=[
            api.StackLine(
                "/site-packages/coreservices/waterbowl/rewards/water.py",
                5,
                "make_external_api_request",
                "raise api.WaterbowlError(error_code=api.WaterbowlErrorCode."
                "OUT_OF_WATER, message=str(e))"
            ),
        ],
        exception_message="email text",
        hostname="localhost",
        error_threshold=1,
        additional_info="extra stuff",
    )

    self.handler.record_error(req.dumps())

    self.assertEmailEquals(dict(to_addresses=["snoopy@shopkick.com",
                                      "wilfred@shopkick.com",
                                      "wishbone@shopkick.com"],
                          from_address="error_report@example.com",
                          cc_address=None,
                          bcc_address=None,
                          subject="Error on localhost in coreservices/waterbowl/rewards/water.py",
                          body='NOTE: This error typically does not require dev team involvement.',
                          smtp_server_host_port=None),
                     self.smtp_stub.last_args)
    body = email.message_from_string(self.smtp_stub.last_args["body"]).get_payload(decode=True)
    self.assertTrue("email text" in body)
    self.assertTrue("extra stuff" in body)

  def test_removes_duplicate_emails(self):
    # Almost the same setup as test_uses_threshold_specified_in_request except the traceback includes
    # a path that John is watching. Since he's also the developer who committed the buggy code, he is
    # the one and only email recipient.
    self.test_config.report_error_threshold = 2
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/lib/no/such/path/for/testing.py", 7, "fubar", "..."),
                   api.StackLine("/site-packages/thirdparty/3rdparty_lib.py", 9, "call", "x")],
        exception_message="email text",
        hostname="localhost",
        error_threshold=1,
    )

    self.handler.record_error(req.dumps())

    self.assertEmailEquals(dict(to_addresses=["wishbone@shopkick.com"],
                          from_address="error_report@example.com",
                          cc_address=None,
                          bcc_address=None,
                          subject="Error on localhost in lib/no/such/path/for/testing.py",
                          body="email text",
                          smtp_server_host_port=None),
                     self.smtp_stub.last_args)



  def test_doesnt_email_on_errors_before_cutoff_date(self):
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/coreservices/service.py", 7, "serve", "..."),
                   api.StackLine("/site-packages/thirdparty/3rdparty_lib.py", 9, "call", "x")],
        exception_message="email text",
        hostname="localhost",
    )
    self.popen_stub.stdout = StringIO.StringIO(
      "75563df6e9d1efe44b48f6643fde9ebbd822b0c5 25 25 1\n"
      "author John Egan\n"
      "author-mail <wishbone@shopkick.com>\n"
      "author-time %d\n"
      "author-tz -0800\n"
      % int(time.mktime(datetime.datetime(2009, 7, 30).timetuple()))
    )

    self.handler.record_error(req.dumps())
    self.assertDictEquals({api.ErrorKey("coreservices/service.py", 7, "serve", "..."):
                      api.ErrorInfo(1, "wishbone@shopkick.com", "2009-07-30 00:00:00", False,
                                    "2020-01-01 00:00:00", is_known_error=False, last_error_data=req)},
                     self.handler.errors_seen.dict)
    self.assertEqual(None, self.smtp_stub.last_args)

  def test_records_error_only_once(self):
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/coreservices/service.py", 7, "serve", "..."),
                   api.StackLine("/site-packages/thirdparty/3rdparty_lib.py", 9, "call", "x")],
        exception_message="email text",
        hostname="localhost",
    )
    self.handler.record_error(req.dumps())
    self._set_stub_time(datetime.datetime(2020, 1, 2))
    self.handler.record_error(req.dumps())

    self.assertDictEquals({api.ErrorKey("coreservices/service.py", 7, "serve", "..."):
                      api.ErrorInfo(2, "wishbone@shopkick.com", "2017-07-30 00:00:00", True, "2020-01-02 00:00:00",
                                    is_known_error=False, last_error_data=req)},
                     self.handler.errors_seen.dict)
    self.assertEqual(1, len(self.smtp_stub.args_list))

  def test_does_not_email_for_whitelisted_errors(self):
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/lib/doghouse/authentication.py", 7, "check_auth",
                                   'raise errors.BadAuthenticationError("Something smells off...")')],
        exception_message="email text",
        hostname="localhost",
    )
    self.handler.record_error(req.dumps())

    self.assertDictEquals({api.ErrorKey("lib/doghouse/authentication.py", 7, "check_auth",
                                    'raise errors.BadAuthenticationError("Something smells off...")'):
                      api.ErrorInfo(1, "wishbone@shopkick.com", "2017-07-30 00:00:00", False, "2020-01-01 00:00:00",
                                    is_known_error=True, last_error_data=req)},
                     self.handler.errors_seen.dict)
    self.assertEquals(None, self.smtp_stub.last_args)

  def test_ignores_third_party_whitelisted_errors(self):
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/SQLAlchemy-0.5.6-py2.6.egg/sqlalchemy/pool.py",
                                   7,
                                   "do_get",
                                   'raise exc.TimeoutError("QueuePool limit of size %d overflow %d '
                                   'reached, connection timed out, timeout %d" % (self.size(),'
                                   'self.overflow(), self._timeout))')],
        exception_message="email text",
        hostname="localhost",
    )
    self.handler.record_error(req.dumps())
    self.assertDictEquals({}, self.handler.errors_seen.dict)

  def test_ignores_third_party_whitelisted_errors_for_facebook(self):
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/facebook.py",
                                   7,
                                   "post_treat_to_facebook",
                                   'urllib.urlencode(args), post_data)')],
        exception_message="email text",
        hostname="localhost",
    )
    self.handler.record_error(req.dumps())
    self.assertDictEquals({}, self.handler.errors_seen.dict)

  def test_traces_up_stack_trace_for_errors_originating_from_building_blocks(self):
    req = api.RecordErrorRequest(
        traceback=[api.StackLine("/site-packages/lib/test.py", 5, "test_func", "code"),
                   api.StackLine("/site-packages/coreservices/service.py", 7, "serve", "..."),
                   api.StackLine("/site-packages/apps/shopkick/doghouse/lib/base.py", 9,
                                       "_get_request_param",
                                       'raise errors.BadRequestError("Missing param %s" % name)')],
        exception_message="email text",
        hostname="localhost",
    )
    self.handler.record_error(req.dumps())

    self.assertDictEquals({api.ErrorKey("coreservices/service.py", 7, "serve", "..."):
                      api.ErrorInfo(1, "wishbone@shopkick.com", "2017-07-30 00:00:00", True, "2020-01-01 00:00:00",
                                    is_known_error=False, last_error_data=req)},
                     self.handler.errors_seen.dict)



############################## Stubs ##############################
class LogStub(object):

  def __init__(self):
    self.last_args = None
    self.args_list = []

  def info(self, args):
    self.last_args = args
    self.args_list.append(args)


class POpenStub(object):

  def __init__(self):
    self.last_args = None
    self.stdout = StringIO.StringIO()
    self.stderr = StringIO.StringIO()

  def __call__(self, args, **kwargs):
    self.last_args = args
    return self


class SMTPClientStub(object):
  def __init__(self):
    self.args_list = []
    self.last_args = None
    self.host = None
    self.port = None

  def __call__(self, host, port):
    self.host = host
    self.port = port
    return self

  def sendmail(self, from_address, to_addresses, body):
    self.last_args = dict((k,v) for k, v in locals().items() if k != 'self')
    self.args_list.append(self.last_args)

  def quit(self):
    pass

  def login(self, user, password):
    pass


class OpenFileStub(object):
  def __init__(self):
    self.files = dict()
    self.current_file = None

  def set_file(self, filename, contents):
    self.files[filename] = StringIO.StringIO(contents)

  def __enter__(self, *args, **kwargs):
    return self.files[self.current_file]

  def __exit__(self, type, value, traceback):
    pass

  def __call__(self, filename, *args, **kwargs):
    self.current_file = filename
    return self


class ThreadStub(object):
  def __init__(self, target=None, args=[]):
    self.target = target
    self.args = args

  def start(self):
    if self.target.__name__ != '_run_background_update_thread':
      self.target(*self.args)


if __name__ == "__main__":
  unittest.main()

########NEW FILE########
