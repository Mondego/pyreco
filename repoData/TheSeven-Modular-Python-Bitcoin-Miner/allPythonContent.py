__FILENAME__ = actualworksource
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#################################
# Actual work source base class #
#################################



import time
import traceback
from binascii import hexlify
from threading import RLock, Thread
from .baseworksource import BaseWorkSource
from .blockchain import DummyBlockchain



class ActualWorkSource(BaseWorkSource):

  nonce_found_async = True
  settings = dict(BaseWorkSource.settings, **{
    "errorlimit": {"title": "Error limit", "type": "int", "position": 20000},
    "errorlockout_factor": {"title": "Error lockout factor", "type": "int", "position": 20100},
    "errorlockout_max": {"title": "Error lockout maximum", "type": "int", "position": 20200},
    "stalelockout": {"title": "Stale lockout", "type": "int", "position": 20500},
  })

  def __init__(self, core, state = None):
    super(ActualWorkSource, self).__init__(core, state)
    
    # Find block chain
    self.blockchain = None
    if not "blockchain" in self.state: self.state.blockchain = None
    self.set_blockchain(core.get_blockchain_by_name(self.state.blockchain))
    
    
  def _reset(self):
    super(ActualWorkSource, self)._reset()
    self.signals_new_block = None
    self.errors = 0
    self.lockoutend = 0
    self.estimated_jobs = 1
    self.estimated_expiry = 60
    
      
  def _stop(self):
    self._cancel_jobs()
    super(ActualWorkSource, self)._stop()
    
    
  def _get_statistics(self, stats, childstats):
    super(ActualWorkSource, self)._get_statistics(stats, childstats)
    stats.signals_new_block = self.signals_new_block
    lockout = self.lockoutend - time.time()
    stats.locked_out = lockout if lockout > 0 else 0
    stats.consecutive_errors = self.errors
    stats.jobs_per_request = self.estimated_jobs
    stats.job_expiry = self.estimated_expiry
    stats.blockchain = self.blockchain
    stats.blockchain_id = self.blockchain.id
    stats.blockchain_name = "None" if isinstance(self.blockchain, DummyBlockchain) else self.blockchain.settings.name


  def destroy(self):
    super(ActualWorkSource, self).destroy()
    if self.blockchain: self.blockchain.remove_work_source(self)
    
    
  def deflate(self):
    # Save block chain name to state
    blockchain = self.get_blockchain()
    if blockchain: self.state.blockchain = blockchain.settings.name
    else: self.state.blockchain = None
    # Let BaseWorkSource handle own deflation
    return super(ActualWorkSource, self).deflate()


  def apply_settings(self):
    super(ActualWorkSource, self).apply_settings()
    if not "errorlimit" in self.settings or not self.settings.errorlimit:
      self.settings.errorlimit = 3
    if not "errorlockout_factor" in self.settings or not self.settings.errorlockout_factor:
      self.settings.errorlockout_factor = 10
    if not "lockout_max" in self.settings or not self.settings.errorlockout_max:
      self.settings.errorlockout_max = 500
    if not "stalelockout" in self.settings: self.settings.stalelockout = 25
    
  
  def get_blockchain(self):
    if isinstance(self.blockchain, DummyBlockchain): return None
    return self.blockchain
    
  
  def set_blockchain(self, blockchain = None):
    if self.blockchain: self.blockchain.remove_work_source(self)
    self.blockchain = blockchain
    if not self.blockchain: self.blockchain = DummyBlockchain(self.core)
    if self.blockchain: self.blockchain.add_work_source(self)
    
    
  def _is_locked_out(self):
    return time.time() <= self.lockoutend
    
      
  def _handle_success(self, jobs = None):
    with self.statelock:
      self.errors = 0
      if jobs:
        jobcount = len(jobs)
        self.estimated_jobs = jobcount
        self.estimated_expiry = int(jobs[0].expiry - time.time())
        with self.stats.lock: self.stats.jobsreceived += jobcount

    
  def _handle_error(self, upload = False):
    with self.statelock:
      self.errors += 1
      if self.errors >= self.settings.errorlimit:
        lockout = min(self.settings.errorlockout_factor + self.errors, self.settings.errorlockout_max)
        self.lockoutend = max(self.lockoutend, time.time() + lockout)
    with self.stats.lock:
      if upload: self.stats.uploadretries += 1
      else: self.stats.failedjobreqs += 1

    
  def _handle_stale(self):
    with self.statelock:
      self.lockoutend = max(self.lockoutend, time.time() + self.settings.stalelockout)
      
      
  def _push_jobs(self, jobs, source = "unknown source"):
    self._handle_success(jobs)
    if jobs:
      accepted = self.core.workqueue.add_jobs(jobs, self, source)
      if accepted != len(jobs): self._handle_stale()
      return accepted
    else: return 0
      
      
  def get_running_fetcher_count(self):
    if not self.started: return 0, 0
    return self._get_running_fetcher_count()

    
  def start_fetchers(self, count, jobs):
    if not self.started or not self.settings.enabled or self._is_locked_out() or not count: return False, 0
    started = 0
    totaljobs = 0
    try:
      while started < count:
        result, newjobs = self._start_fetcher()
        totaljobs += newjobs
        if result:
          started += result
          with self.stats.lock: self.stats.jobrequests += result
        if not result or totaljobs >= jobs:
          if started: return started, totaljobs
          return result, 0
    except:
      self.core.log(self, "Error while fetching job: %s\n" % (traceback.format_exc()), 200, "y")
      self._handle_error()
    if started: return started, totaljobs
    return False, 0


  def nonce_found(self, job, data, nonce, noncediff):
    if self.nonce_found_async:
      thread = Thread(None, self.nonce_found_thread, self.settings.name + "_nonce_found_" + hexlify(nonce).decode("ascii"), (job, data, nonce, noncediff))
      thread.daemon = True
      thread.start()
    else: self.nonce_found_thread(job, data, nonce, noncediff)

    
  def nonce_found_thread(self, job, data, nonce, noncediff):
    tries = 0
    while True:
      try:
        result = self._nonce_found(job, data, nonce, noncediff)
        self._handle_success()
        return job.nonce_handled_callback(nonce, noncediff, result)
      except:
        self.core.log(self, "Error while sending share %s (difficulty %.5f): %s\n" % (hexlify(nonce).decode("ascii"), noncediff, traceback.format_exc()), 200, "y")
        tries += 1
        self._handle_error(True)
        time.sleep(min(30, tries))
        
########NEW FILE########
__FILENAME__ = basefrontend
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#######################
# Frontend base class #
#######################



from threading import RLock
from .util import Bunch
from .startable import Startable
from .inflatable import Inflatable



class BaseFrontend(Startable, Inflatable):

  can_log = False
  can_show_stats = False
  can_configure = False
  can_handle_events = False
  can_autodetect = False
  settings = dict(Inflatable.settings, **{
    "name": {"title": "Name", "type": "string", "position": 100},
  })


  def __init__(self, core, state = None):
    Inflatable.__init__(self, core, state)
    Startable.__init__(self)
    self.does_log = self.__class__.can_log
    self.does_show_stats = self.__class__.can_show_stats
    self.does_handle_events = self.__class__.can_handle_events
    
    
  def destroy(self):
    Startable.destroy(self)
    Inflatable.destroy(self)


  def apply_settings(self):
    Inflatable.apply_settings(self)
    if not "name" in self.settings or not self.settings.name:
      self.settings.name = getattr(self.__class__, "default_name", "Untitled frontend")


  def _reset(self):
    self.core.event(300, self, "reset", None, "Resetting frontend state")
    Startable._reset(self)

########NEW FILE########
__FILENAME__ = baseworker
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#####################
# Worker base class #
#####################



import time
from threading import RLock, Thread
from .util import Bunch
from .statistics import StatisticsProvider
from .startable import Startable
from .inflatable import Inflatable



class BaseWorker(StatisticsProvider, Startable, Inflatable):

  can_autodetect = False
  settings = dict(Inflatable.settings, **{
    "name": {"title": "Name", "type": "string", "position": 100},
  })


  def __init__(self, core, state = None):
    StatisticsProvider.__init__(self)
    Inflatable.__init__(self, core, state)
    Startable.__init__(self)

    self.children = []
    
    
  def destroy(self):
    Startable.destroy(self)
    Inflatable.destroy(self)


  def apply_settings(self):
    Inflatable.apply_settings(self)
    if not "name" in self.settings or not self.settings.name:
      self.settings.name = getattr(self.__class__, "default_name", "Untitled worker")

      
  def _reset(self):
    self.core.event(300, self, "reset", None, "Resetting worker state", worker = self)
    Startable._reset(self)
    self.job = None
    self.jobs_per_second = 0
    self.parallel_jobs = 0
    self.stats.starttime = time.time()
    self.stats.ghashes = 0
    self.stats.mhps = 0
    self.stats.jobsaccepted = 0
    self.stats.jobscanceled = 0
    self.stats.sharesaccepted = 0
    self.stats.sharesrejected = 0
    self.stats.sharesinvalid = 0
    
    
  def _get_statistics(self, stats, childstats):
    StatisticsProvider._get_statistics(self, stats, childstats)
    stats.starttime = self.stats.starttime
    stats.ghashes = self.stats.ghashes + childstats.calculatefieldsum("ghashes")
    stats.avgmhps = 1000. * stats.ghashes / (time.time() - stats.starttime)
    stats.mhps = self.stats.mhps + childstats.calculatefieldsum("mhps")
    stats.jobsaccepted = self.stats.jobsaccepted + childstats.calculatefieldsum("jobsaccepted")
    stats.jobscanceled = self.stats.jobscanceled + childstats.calculatefieldsum("jobscanceled")
    stats.sharesaccepted = self.stats.sharesaccepted + childstats.calculatefieldsum("sharesaccepted")
    stats.sharesrejected = self.stats.sharesrejected + childstats.calculatefieldsum("sharesrejected")
    stats.sharesinvalid = self.stats.sharesinvalid + childstats.calculatefieldsum("sharesinvalid")
    stats.parallel_jobs = self.parallel_jobs + childstats.calculatefieldsum("parallel_jobs")
    stats.current_job = self.job
    stats.current_work_source = getattr(stats.current_job, "worksource", None) if stats.current_job else None
    stats.current_work_source_id = stats.current_work_source.id if stats.current_work_source else None
    stats.current_work_source_name = stats.current_work_source.settings.name if stats.current_work_source else None
    
    
  def get_jobs_per_second(self):
    result = self.jobs_per_second
    for child in self.children: result += child.get_jobs_per_second()
    return result
      
  def get_parallel_jobs(self):
    result = self.parallel_jobs
    for child in self.children: result += child.get_parallel_jobs()
    return result

########NEW FILE########
__FILENAME__ = baseworksource
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##########################
# Work source base class #
##########################



import time
from threading import RLock
from .util import Bunch
from .statistics import StatisticsProvider
from .startable import Startable
from .inflatable import Inflatable



class BaseWorkSource(StatisticsProvider, Startable, Inflatable):

  is_group = False
  settings = dict(Inflatable.settings, **{
    "name": {"title": "Name", "type": "string", "position": 100},
    "enabled": {"title": "Enabled", "type": "boolean", "position": 200},
    "hashrate": {"title": "Hashrate", "type": "float", "position": 10000},
    "priority": {"title": "Priority", "type": "float", "position": 10100},
  })


  def __init__(self, core, state = None):
    StatisticsProvider.__init__(self)
    Inflatable.__init__(self, core, state)
    Startable.__init__(self)

    self.parent = None
    self.statelock = RLock()
    
    
  def destroy(self):
    Startable.destroy(self)
    Inflatable.destroy(self)
    
    
  def apply_settings(self):
    Inflatable.apply_settings(self)
    if not "name" in self.settings or not self.settings.name:
      self.settings.name = getattr(self.__class__, "default_name", "Untitled work source")
    if not "enabled" in self.settings: self.settings.enabled = True
    if not "hashrate" in self.settings: self.settings.hashrate = 0
    if not "priority" in self.settings: self.settings.priority = 1
    
    
  def _reset(self):
    self.core.event(300, self, "reset", None, "Resetting work source state", worksource = self)
    Startable._reset(self)
    self.mhashes_pending = 0
    self.mhashes_deferred = 0
    self.stats.starttime = time.time()
    self.stats.ghashes = 0
    self.stats.jobrequests = 0
    self.stats.failedjobreqs = 0
    self.stats.uploadretries = 0
    self.stats.jobsreceived = 0
    self.stats.jobsaccepted = 0
    self.stats.jobscanceled = 0
    self.stats.sharesaccepted = 0
    self.stats.sharesrejected = 0
    self.stats.difficulty = 0
    self.jobs = []
    
    
  def _get_statistics(self, stats, childstats):
    StatisticsProvider._get_statistics(self, stats, childstats)
    stats.starttime = self.stats.starttime
    stats.ghashes = self.stats.ghashes + childstats.calculatefieldsum("ghashes")
    stats.avgmhps = 1000. * self.stats.ghashes / (time.time() - stats.starttime) + childstats.calculatefieldsum("avgmhps")
    stats.jobrequests = self.stats.jobrequests + childstats.calculatefieldsum("jobrequests")
    stats.failedjobreqs = self.stats.failedjobreqs + childstats.calculatefieldsum("failedjobreqs")
    stats.uploadretries = self.stats.uploadretries + childstats.calculatefieldsum("uploadretries")
    stats.jobsreceived = self.stats.jobsreceived + childstats.calculatefieldsum("jobsreceived")
    stats.jobsaccepted = self.stats.jobsaccepted + childstats.calculatefieldsum("jobsaccepted")
    stats.jobscanceled = self.stats.jobscanceled + childstats.calculatefieldsum("jobscanceled")
    stats.sharesaccepted = self.stats.sharesaccepted + childstats.calculatefieldsum("sharesaccepted")
    stats.sharesrejected = self.stats.sharesrejected + childstats.calculatefieldsum("sharesrejected")
    stats.difficulty = self.stats.difficulty
    
    
  def set_parent(self, parent = None):
    self.parent = parent
    
    
  def get_parent(self):
    return self.parent

    
  def add_job(self, job):
    if not job in self.jobs: self.jobs.append(job)
  

  def remove_job(self, job):
    while job in self.jobs: self.jobs.remove(job)


  def _cancel_jobs(self, graceful = False):
    cancel = []
    with self.core.workqueue.lock:
      while self.jobs:
        job = self.jobs.pop(0)
        if job.worker: cancel.append(job)
        else: job.destroy()
    if not graceful: self.jobs = []
    self.core.workqueue.cancel_jobs(cancel, graceful)
  

  def add_pending_mhashes(self, mhashes):
    with self.statelock: self.mhashes_pending += mhashes
    if self.parent: self.parent.add_pending_mhashes(mhashes)

    
  def add_deferred_mhashes(self, mhashes):
    with self.statelock: self.mhashes_deferred += mhashes
    if self.parent: self.parent.add_deferred_mhashes(mhashes)

########NEW FILE########
__FILENAME__ = blockchain
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#######################
# Block chain manager #
#######################



import time
from threading import RLock
from .util import Bunch
from .statistics import StatisticsProvider, StatisticsList
from .startable import Startable
from .inflatable import Inflatable



class Blockchain(StatisticsProvider, Startable, Inflatable):

  settings = dict(Inflatable.settings, **{
    "name": {"title": "Name", "type": "string", "position": 100},
    "timeout": {"title": "History timeout", "type": "float", "position": 1000},
  })

  
  def __init__(self, core, state = None):
    StatisticsProvider.__init__(self)
    Inflatable.__init__(self, core, state)
    Startable.__init__(self)
    
    self.worksourcelock = RLock()
    self.blocklock = RLock()


  def destroy(self):
    with self.worksourcelock:
      for worksource in self.children:
        worksource.set_blockchain(None)
    Startable.destroy(self)
    Inflatable.destroy(self)


  def apply_settings(self):
    Inflatable.apply_settings(self)
    if not "name" in self.settings or not self.settings.name:
      self.settings.name = "Untitled blockchain"
    with self.core.blockchainlock:
      origname = self.settings.name
      self.settings.name = None
      name = origname
      i = 1
      while self.core.get_blockchain_by_name(name):
        i += 1
        name = origname + (" (%d)" % i)
      self.settings.name = name
    if not "timeout" in self.settings: self.settings.timeout = 60
    
    
  def _reset(self):    
    self.core.event(300, self, "reset", None, "Resetting blockchain state", blockchain = self)
    Startable._reset(self)
    self.currentprevhash = None
    self.knownprevhashes = []
    self.timeoutend = 0
    self.jobs = []
    self.stats.starttime = time.time()
    self.stats.blocks = 0
    self.stats.lastblock = None

    
  def _get_statistics(self, stats, childstats):
    StatisticsProvider._get_statistics(self, stats, childstats)
    stats.starttime = self.stats.starttime
    stats.blocks = self.stats.blocks
    stats.lastblock = self.stats.lastblock
    stats.ghashes = childstats.calculatefieldsum("ghashes")
    stats.avgmhps = childstats.calculatefieldsum("avgmhps")
    stats.jobsreceived = childstats.calculatefieldsum("jobsreceived")
    stats.jobsaccepted = childstats.calculatefieldsum("jobsaccepted")
    stats.jobscanceled = childstats.calculatefieldsum("jobscanceled")
    stats.sharesaccepted = childstats.calculatefieldsum("sharesaccepted")
    stats.sharesrejected = childstats.calculatefieldsum("sharesrejected")
    stats.children = []
    
    
  def add_job(self, job):
    if not job in self.jobs: self.jobs.append(job)
  

  def remove_job(self, job):
    while job in self.jobs: self.jobs.remove(job)


  def add_work_source(self, worksource):
    with self.worksourcelock:
      if not worksource in self.children: self.children.append(worksource)
  

  def remove_work_source(self, worksource):
    with self.worksourcelock:
      while worksource in self.children: self.children.remove(worksource)


  def check_job(self, job):
    if self.currentprevhash == job.prevhash: return True
    cancel = []
    # Needs to be locked outside of blocklock to prevent race condition
    with self.core.workqueue.lock:
      with self.blocklock:
        now = time.time()
        timeout_expired = now > self.timeoutend
        self.timeoutend = now + self.settings.timeout
        if job.prevhash in self.knownprevhashes: return False
        if timeout_expired: self.knownprevhashes = [self.currentprevhash]
        else: self.knownprevhashes.append(self.currentprevhash)
        self.currentprevhash = job.prevhash
        while self.jobs:
          job = self.jobs.pop(0)
          if job.worker: cancel.append(job)
          else: job.destroy()
        self.jobs = []
        with self.stats.lock:
          self.stats.blocks += 1
          self.stats.lastblock = now
    self.core.log(self, "New block detected\n", 300, "B")
    self.core.workqueue.cancel_jobs(cancel)
    return True
 

 
class DummyBlockchain(object):


  def __init__(self, core):
    self.core = core
    self.id = 0
    self.settings = Bunch(name = "Dummy blockchain")
    
    # Initialize job list (protected by global job queue lock)
    self.jobs = []
    self.currentprevhash = None
    self.knownprevhashes = []
    self.timeoutend = 0
    self.blocklock = RLock()
    
    
  def add_job(self, job):
    if not job in self.jobs: self.jobs.append(job)
  

  def remove_job(self, job):
    while job in self.jobs: self.jobs.remove(job)
    
    
  def add_work_source(self, worksource):
    pass


  def remove_work_source(self, worksource):
    pass

  
  def check_job(self, job):
    if self.currentprevhash == job.prevhash: return True
    cancel = []
    # Needs to be locked outside of blocklock to prevent race condition
    with self.core.workqueue.lock:
      with self.blocklock:
        now = time.time()
        timeout_expired = now > self.timeoutend
        self.timeoutend = now + 10
        if job.prevhash in self.knownprevhashes: return False
        if timeout_expired: self.knownprevhashes = [self.currentprevhash]
        else: self.knownprevhashes.append(self.currentprevhash)
        self.currentprevhash = job.prevhash
        while self.jobs:
          job = self.jobs.pop(0)
          if job.worker: cancel.append(job)
          else: job.destroy()
      self.jobs = []
    self.core.log(self, "New block detected\n", 300, "B")
    self.core.workqueue.cancel_jobs(cancel)
    return True


########NEW FILE########
__FILENAME__ = core
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#####################################
# Modular Python Bitcoin Miner Core #
#####################################



import sys
import os
import time
import pickle
import traceback
from datetime import datetime
from threading import RLock, Thread, current_thread
from .statistics import StatisticsList
from .inflatable import Inflatable
from .startable import Startable
from .util import Bunch
try: from queue import Queue
except ImportError: from Queue import Queue



class Core(Startable):

  version = "Modular Python Bitcoin Miner v0.1.0"

  
  def __init__(self, instance = "default", default_loglevel = 500):
    self.instance = instance
    self.id = -1
    self.settings = Bunch(name = "Core")

    # Initialize log queue and hijack stdout/stderr
    self.default_loglevel = default_loglevel
    self.logger_thread = None
    self.logqueue = Queue()
    self.logbuf = {}
    self.event_thread = None
    self.eventqueue = Queue()
    self.printlock = RLock()
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    from .util import OutputRedirector
    sys.stdout = OutputRedirector(self, Bunch(id = -4, settings = Bunch(name = "stdout")), 500)
    sys.stderr = OutputRedirector(self, Bunch(id = -5, settings = Bunch(name = "stderr")), 100, "rB")
    
    # Initialize parent classes
    super(Core, self).__init__()

    # Log "core initializing" event
    self.event(0, self, "initializing", None, "Core initializing")

    # Print startup message
    self.log(self, "%s, Copyright (C) 2012 Michael Sparmann (TheSeven)\n" % Core.version, 0, "B")
    self.log(self, "Modular Python Bitcoin Miner comes with ABSOLUTELY NO WARRANTY.\n", 0)
    self.log(self, "This is free software, and you are welcome to redistribute it under certain conditions.\n", 0)
    self.log(self, "See included file COPYING_GPLv2.txt for details.\n", 0)
    self.log(self, "Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh or,\n", 0, "y")
    self.log(self, "even better, donating a small share of your hashing power if you want\n", 0, "y")
    self.log(self, "to support further development of the Modular Python Bitcoin Miner.\n", 0, "y")
    
    # Set up object registry
    from .objectregistry import ObjectRegistry
    self.registry = ObjectRegistry(self)
    
    # Initialize class lists
    from .worksourcegroup import WorkSourceGroup
    self.frontendclasses = []
    self.workerclasses = []
    self.worksourceclasses = [WorkSourceGroup]

    # Load modules
    self.log(self, "Loading modules...\n", 500, "B")
    # Grrr. Python is just broken...
    import __main__
    basepath = os.path.dirname(__main__.__file__)
    basepath = (basepath if basepath else ".") + "/modules"
    for maintainer in os.listdir(basepath):
      maintainerpath = basepath + "/" + maintainer
      if os.path.isdir(maintainerpath) and os.path.isfile(maintainerpath + "/__init__.py"):
        for module in os.listdir(maintainerpath):
          modulepath = maintainerpath + "/" + module
          if os.path.isdir(modulepath) and os.path.isfile(modulepath + "/__init__.py"):
            try:
              self.log(self, "Loading modules.%s.%s...\n" % (maintainer, module), 800)
              module = getattr(__import__("modules.%s" % maintainer, globals(), locals(), [module], 0), module)
              self.frontendclasses.extend(getattr(module, "frontendclasses", []))
              self.workerclasses.extend(getattr(module, "workerclasses", []))
              self.worksourceclasses.extend(getattr(module, "worksourceclasses", []))
            except Exception as e:
              self.log(self, "Could not load module %s.%s: %s\n" % (maintainer, module, traceback.format_exc()), 300, "yB")
              
    # Register the detected classes in the global object registry
    for frontendclass in self.frontendclasses: frontendclass.id = self.registry.register(frontendclass)
    for workerclass in self.workerclasses: workerclass.id = self.registry.register(workerclass)
    for worksourceclass in self.worksourceclasses: worksourceclass.id = self.registry.register(worksourceclass)

    # Initialize blockchain list
    self.blockchainlock = RLock()
    self.blockchains = []

    # Initialize frontend list
    self.frontendlock = RLock()
    self.frontends = []

    # Initialize worker list
    self.workerlock = RLock()
    self.workers = []
    
    # Initialize work queue
    from .workqueue import WorkQueue
    self.workqueue = WorkQueue(self)

    # Initialize work fetcher
    from .fetcher import Fetcher
    self.fetcher = Fetcher(self)

    # Read saved instance state
    self.event(100, self, "loading_config", None, "Loading configuration")
    try:
      with open("config/%s.cfg" % instance, "rb") as f:
        data = f.read()
      state = pickle.loads(data)
      self.is_new_instance = False
      with self.frontendlock:
        for frontend in state.frontends:
          self.add_frontend(Inflatable.inflate(self, frontend))
      with self.workerlock:
        for worker in state.workers:
          self.add_worker(Inflatable.inflate(self, worker))
      with self.blockchainlock:
        for blockchain in state.blockchains:
          self.add_blockchain(Inflatable.inflate(self, blockchain))
      self.root_work_source = Inflatable.inflate(self, state.root_work_source)
      self.event(100, self, "loaded_config", None, "Successfully loaded configuration")
    except Exception as e:
      self.event(100, self, "loading_config_failed", None, "Loading configuration failed")
      self.log(self, "Could not load instance configuration: %s\nLoading default configuration...\n" % traceback.format_exc(), 300, "yB")
      self.is_new_instance = True
      self.frontends = []
      self.workers = []
      self.blockchains = []
      self.root_work_source = None
    
    # Create a new root work source group if neccessary
    if not self.root_work_source:
      from .worksourcegroup import WorkSourceGroup
      self.root_work_source = WorkSourceGroup(self)
      self.root_work_source.settings.name = "Work sources"
    pass
    
    
  def save(self):
    self.event(100, self, "saving_config", None, "Saving configuration")
    self.log(self, "Saving instance configuration...\n", 500, "B")
    try:
      state = Bunch()
      state.blockchains = []
      for blockchain in self.blockchains:
        state.blockchains.append(blockchain.deflate())
      state.frontends = []
      for frontend in self.frontends:
        state.frontends.append(frontend.deflate())
      state.workers = []
      for worker in self.workers:
        state.workers.append(worker.deflate())
      if not self.root_work_source: state.root_work_source = None
      else: state.root_work_source = self.root_work_source.deflate()
      data = pickle.dumps(state, pickle.HIGHEST_PROTOCOL)
      if not os.path.exists("config"): os.mkdir("config")
      with open("config/%s.cfg" % self.instance, "wb") as f:
        f.write(data)
      self.event(100, self, "saved_config", None, "Successfully saved configuration")
    except Exception as e:
      self.event(100, self, "saving_config_failed", None, "Saving configuration failed")
      self.log(self, "Could not save instance configuration: %s\n" % traceback.format_exc(), 100, "rB")
    
    
  def _reset(self):
    self.event(100, self, "reset", None, "Resetting core state")
    super(Core, self)._reset()
    
    # Reset total calculated hashes and uptime
    self.stats = Bunch()
    self.stats.starttime = time.time()
    self.stats.ghashes = 0


  def _start(self):
    self.event(100, self, "starting", None, "Starting core")
    self.log(self, "Starting up...\n", 100, "B")
    super(Core, self)._start()

    # Start up frontends
    self.log(self, "Starting up frontends...\n", 700)
    have_logger = False
    have_configurator = False
    for frontend in self.frontends:
      try:
        self.log(self, "Starting up frontend %s...\n" % frontend.settings.name, 800)
        frontend.start()
        if frontend.can_log: have_logger = True
        if frontend.can_configure: have_configurator = True
      except Exception as e:
        self.log(self, "Could not start frontend %s: %s\n" % (frontend.settings.name, traceback.format_exc()), 100, "rB")
      
    # Warn if there is no logger frontend (needs to be fone before enabling logger thread)
    if not have_logger:
      self.log(self, "No working logger frontend module present!\n"
                     "Run with --detect-frontends after ensuring that all neccessary modules are installed.\n", 10, "rB")

    # Start logger thread
    self.log(self, "Starting up logging thread...\n", 700)
    self.logger_thread = Thread(None, self.log_worker_thread, "core_log_worker")
    self.logger_thread.start()
    self.started = True

    # Start up event dispatcher thread
    self.log(self, "Starting up event dispatcher thread...\n", 700)
    self.event_thread = Thread(None, self.event_worker_thread, "core_event_worker")
    self.event_thread.start()

    # Warn if there is no configuration frontend
    if not have_configurator:
      self.log(self, "No working configuration frontend module present!\n"
                     "Run with --detect-frontends after ensuring that all neccessary modules are installed.\n", 100, "yB")

    # Start up work queue
    self.log(self, "Starting up work queue...\n", 700)
    try: self.workqueue.start()
    except Exception as e: self.log(self, "Could not start work queue: %s\n" % traceback.format_exc(), 100, "rB")

    # Start up blockchains
    self.log(self, "Starting up blockchains...\n", 700)
    for blockchain in self.blockchains:
      try:
        self.log(self, "Starting up blockchain %s...\n" % blockchain.settings.name, 800)
        blockchain.start()
      except Exception as e:
        self.log(self, "Could not start blockchain %s: %s\n" % (blockchain.settings.name, traceback.format_exc()), 100, "rB")

    # Start up work source tree
    self.log(self, "Starting up work source tree...\n", 700)
    if self.root_work_source:
      try:
        self.log(self, "Starting up work source %s...\n" % self.root_work_source.settings.name, 800)
        self.root_work_source.start()
      except Exception as e:
        self.log(self, "Could not start root work source %s: %s\n" % (self.root_work_source.settings.name, traceback.format_exc()), 100, "rB")

    # Start up work fetcher
    self.log(self, "Starting up work fetcher...\n", 700)
    try: self.fetcher.start()
    except Exception as e: self.log(self, "Could not start work fetcher: %s\n" % traceback.format_exc(), 100, "rB")
    
    # Start up workers
    self.log(self, "Starting up workers...\n", 700)
    for worker in self.workers:
      try:
        self.log(self, "Starting up worker %s...\n" % worker.settings.name, 800)
        worker.start()
      except Exception as e:
        self.log(self, "Could not start worker %s: %s\n" % (worker.settings.name, traceback.format_exc()), 100, "rB")

    self.log(self, "Startup completed\n", 200, "")
    self.event(100, self, "started", None, "Successfully started core")
  
  
  def _stop(self):
    self.event(100, self, "stopping", None, "Stopping core")
    self.log(self, "Shutting down...\n", 100, "B")
    
    # Shut down workers
    self.log(self, "Shutting down workers...\n", 700)
    for worker in self.workers:
      try:
        self.log(self, "Shutting down worker %s...\n" % worker.settings.name, 800)
        worker.stop()
      except Exception as e:
        self.log(self, "Could not stop worker %s: %s\n" % (worker.settings.name, traceback.format_exc()), 100, "rB")

    # Shut down work fetcher
    self.log(self, "Shutting down work fetcher...\n", 700)
    try: self.fetcher.stop()
    except Exception as e: self.log(self, "Could not stop work fetcher: %s\n" % traceback.format_exc(), 100, "rB")

    # Shut down work source tree
    self.log(self, "Shutting down work source tree...\n", 700)
    if self.root_work_source:
      try:
        self.log(self, "Shutting down work source %s...\n" % self.root_work_source.settings.name, 800)
        self.root_work_source.stop()
      except Exception as e:
        self.log(self, "Could not stop root work source %s: %s\n" % (self.root_work_source.settings.name, traceback.format_exc()), 100, "rB")
    
    # Shut down blockchains
    self.log(self, "Shutting down blockchains...\n", 700)
    for blockchain in self.blockchains:
      try:
        self.log(self, "Shutting down blockchain %s...\n" % blockchain.settings.name, 800)
        blockchain.stop()
      except Exception as e:
        self.log(self, "Could not stop blockchain %s: %s\n" % (blockchain.settings.name, traceback.format_exc()), 100, "rB")

    # Shut down work queue
    self.log(self, "Shutting down work queue...\n", 700)
    try: self.workqueue.stop()
    except Exception as e: self.log(self, "Could not stop work queue: %s\n" % traceback.format_exc(), 100, "rB")

    # Save instance configuration
    self.save()
    
    # Shut down the log worker thread
    self.log(self, "Shutting down event dispatcher thread...\n", 700)
    self.eventqueue.put(None)
    self.event_thread.join(10)
    
    # We are about to shut down the logging infrastructure, so switch back to builtin logging
    self.log(self, "Shutting down logging thread...\n", 700)
    self.started = False
    
    # Shut down the log worker thread
    self.logqueue.put(None)
    self.logger_thread.join(10)
    
    # Shut down the frontends
    self.log(self, "Shutting down frontends...\n", 700)
    for frontend in self.frontends:
      try:
        self.log(self, "Shutting down frontend %s...\n" % frontend.settings.name, 800)
        frontend.stop()
      except Exception as e:
        self.log(self, "Could not stop frontend %s: %s\n" % (frontend.settings.name, traceback.format_exc()), 100, "rB")

    super(Core, self)._stop()
    self.log(self, "Shutdown completed\n", 200, "")
    self.event(100, self, "stopped", None, "Successfully stopped core")
          
  
  def detect_frontends(self):
    self.log(self, "Autodetecting frontends...\n", 500, "B")
    for frontendclass in self.frontendclasses:
      if frontendclass.can_autodetect:
        try: frontendclass.autodetect(self)
        except Exception as e:
          name = "%s.%s" % (frontendclass.__module__, frontendclass.__name__)
          self.log(self, "%s autodetection failed: %s\n" % (name, traceback.format_exc()), 300, "yB")
  
  
  def detect_workers(self):
    self.log(self, "Autodetecting workers...\n", 500, "B")
    for workerclass in self.workerclasses:
      if workerclass.can_autodetect:
        try: workerclass.autodetect(self)
        except Exception as e:
          name = "%s.%s" % (workerclass.__module__, workerclass.__name__)
          self.log(self, "%s autodetection failed: %s\n" % (name, traceback.format_exc()), 300, "yB")

    
  def get_blockchains(self):
    return self.blockchains


  def get_blockchain_by_name(self, name):
    for blockchain in self.blockchains:
      if blockchain.settings.name == name:
        return blockchain
    return None
    
  
  def add_blockchain(self, blockchain):
    with self.blockchainlock:
      if not blockchain in self.blockchains:
        self.blockchains.append(blockchain)


  def remove_blockchain(self, blockchain):
    with self.blockchainlock:
      while blockchain in self.blockchains:
        self.blockchains.remove(blockchain)


  def add_frontend(self, frontend):
    with self.start_stop_lock:
      with self.frontendlock:
        if not frontend in self.frontends:
          if self.started:
            try: frontend.start()
            except Exception as e:
              self.log(self, "Could not start frontend %s: %s\n" % (frontend.settings.name, traceback.format_exc()), 100, "yB")
          self.frontends.append(frontend)


  def remove_frontend(self, frontend):
    with self.start_stop_lock:
      with self.frontendlock:
        while frontend in self.frontends:
          if self.started:
            try: frontend.stop()
            except Exception as e:
              self.log(self, "Could not stop frontend %s: %s\n" % (frontend.settings.name, traceback.format_exc()), 100, "yB")
          self.frontends.remove(frontend)


  def add_worker(self, worker):
    with self.start_stop_lock:
      with self.workerlock:
        if not worker in self.workers:
          if self.started:
            try: worker.start()
            except Exception as e:
              self.log(self, "Could not start worker %s: %s\n" % (worker.settings.name, traceback.format_exc()), 100, "yB")
          self.workers.append(worker)


  def remove_worker(self, worker):
    with self.start_stop_lock:
      with self.workerlock:
        while worker in self.workers:
          if self.started:
            try: worker.stop()
            except Exception as e:
              self.log(self, "Could not stop worker %s: %s\n" % (worker.settings.name, traceback.format_exc()), 100, "yB")
          self.workers.remove(worker)


  def get_root_work_source(self):
    return self.root_work_source


  def set_root_work_source(self, worksource):
    with self.start_stop_lock:
      if self.started and self.root_work_source:
        try: self.root_work_source.stop()
        except Exception as e:
          self.log(self, "Could not stop root work source %s: %s\n" % (self.root_work_source.settings.name, traceback.format_exc()), 100, "yB")
      self.root_work_source = worksource
      worksource.set_parent(None)
      if self.started:
        try: worksource.start()
        except Exception as e:
          self.log(self, "Could not start root work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
          
          
  def get_job(self, worker, expiry_min_ahead, async = False):
    return self.workqueue.get_job(worker, expiry_min_ahead, async)
    
    
  def get_blockchain_statistics(self):
    stats = StatisticsList()
    for blockchain in self.blockchains: stats.append(blockchain.get_statistics())
    return stats
    
    
  def get_work_source_statistics(self):
    stats = StatisticsList()
    if self.root_work_source: stats.append(self.root_work_source.get_statistics())
    return stats
    
    
  def get_worker_statistics(self):
    stats = StatisticsList()
    for worker in self.workers: stats.append(worker.get_statistics())
    return stats
    
    
  def notify_speed_changed(self, worker):
    return self.fetcher.notify_speed_changed(worker)
    
    
  def log(self, source, message, loglevel, format = ""):
    # Concatenate messages until there is a linefeed
    thread = current_thread()
    if not thread in self.logbuf: self.logbuf[thread] = [source, loglevel, [], datetime.now()]
    if self.logbuf[thread][1] > loglevel: self.logbuf[thread][1] = loglevel
    self.logbuf[thread][2].append((message, format))
    if message[-1:] != "\n": return
    self.log_multi(*self.logbuf[thread])
    del self.logbuf[thread]

    
  def log_multi(self, source, loglevel, messages, timestamp = datetime.now()):
    # Put message into the queue, will be pushed to listeners by a worker thread
    self.logqueue.put((source, timestamp, loglevel, messages))
    
    # If the core hasn't fully started up yet, the logging subsystem might not
    # work yet. Print the message to stderr as well just in case.
    if not self.started and loglevel <= self.default_loglevel:
      message = ""
      for string, format in messages: message += string
      prefix = "%s [%3d] %s: " % (timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"), loglevel, source.settings.name)
      with self.printlock:
        for line in message.splitlines(True): self.stderr.write(prefix + line)


  def log_worker_thread(self):
    while True:
      data = self.logqueue.get()
      
      # We'll get a None value in the queue if the core wants us to shut down
      if not data:
        self.logqueue.task_done()
        return
      
      for frontend in self.frontends:
        if frontend.can_log:
          try: frontend.write_log_message(*data)
          except:
            if not hasattr(frontend, "_logging_broken"):
              frontend._logging_broken = True
              self.log(frontend, "Exception while logging message: %s" % traceback.format_exc(), 50, "rB")
          
      self.logqueue.task_done()


  def event(self, level, source, event, arg, message = None, worker = None, worksource = None, blockchain = None, job = None, timestamp = datetime.now()):
    self.eventqueue.put((level, source, event, arg, message, worker, worksource, blockchain, job, timestamp))


  def event_worker_thread(self):
    while True:
      data = self.eventqueue.get()
      
      # We'll get a None value in the queue if the core wants us to shut down
      if not data:
        self.eventqueue.task_done()
        return
      
      for frontend in self.frontends:
        if frontend.can_handle_events:
          try: frontend.handle_stats_event(*data)
          except: self.log(frontend, "Exception while logging event: %s" % traceback.format_exc(), 200, "r")
          
      self.eventqueue.task_done()

########NEW FILE########
__FILENAME__ = fetcher
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



################
# Work fetcher #
################



import time
import traceback
from threading import RLock, Condition, Thread, current_thread
from .startable import Startable
from .util import Bunch



class Fetcher(Startable):

  
  def __init__(self, core):
    self.core = core
    self.id = -2
    self.settings = Bunch(name = "Fetcher controller")
    super(Fetcher, self).__init__()
    # Initialize global fetcher lock and wakeup condition
    self.lock = Condition()
    # Fetcher controller thread
    self.controllerthread = None
    
    
  def _reset(self):
    self.core.event(300, self, "reset", None, "Resetting fetcher state")
    super(Fetcher, self)._reset()
    self.speedchanged = True
    self.queuetarget = 5
    

  def _start(self):
    super(Fetcher, self)._start()
    self.shutdown = False
    self.controllerthread = Thread(None, self.controllerloop, "fetcher_controller")
    self.controllerthread.daemon = True
    self.controllerthread.start()
  
  
  def _stop(self):
    self.shutdown = True
    self.wakeup()
    self.controllerthread.join(10)
    super(Fetcher, self)._stop()
      
      
  def wakeup(self):
    with self.lock: self.lock.notify()

    
  def notify_speed_changed(self, worker):
    with self.lock:
      self.speedchanged = True
      self.lock.notify()

    
  def controllerloop(self):
    with self.lock:
      while not self.shutdown:
        if self.speedchanged:
          self.speedchanged = False
          jobspersecond = 0
          paralleljobs = 0
          with self.core.workerlock:
            for worker in self.core.workers:
              jobspersecond += worker.get_jobs_per_second()
              paralleljobs += worker.get_parallel_jobs()
          self.queuetarget = max(5, paralleljobs * 2, jobspersecond * 30)
          self.core.workqueue.target = self.queuetarget
        
        worksource = self.core.get_root_work_source()
        queuecount = self.core.workqueue.count
        fetchercount, jobcount = worksource.get_running_fetcher_count()
        needjobs = self.queuetarget - queuecount - jobcount
        startfetchers = max(0, min(5, (self.queuetarget - queuecount - jobcount // 2) // 2))
        if not startfetchers and queuecount == 0 and fetchercount < 3: startfetchers = 1
        if not startfetchers:
          if self.core.workqueue.count * 2 > self.queuetarget: self.lock.wait()
          else: self.lock.wait(0.1)
          continue
        try:
          if startfetchers:
            started, startedjobs = worksource.start_fetchers(startfetchers if self.core.workqueue.count * 4 < self.queuetarget else 1, needjobs)
            if not started:
              self.lock.wait(0.1)
              continue
          else: self.lock.wait(0.1)
          lockout = time.time() + min(5, 4 * self.core.workqueue.count / self.queuetarget - 1)
          while time.time() < lockout and self.core.workqueue.count > self.queuetarget / 4: self.lock.wait(0.1)
        except:
          self.core.log(self, "Error while starting fetcher thread: %s\n" % traceback.format_exc(), 100, "rB")
          time.sleep(1)

########NEW FILE########
__FILENAME__ = inflatable
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#############################
# In-/Deflatable base class #
#############################



from .util import Bunch



class Inflatable(object):

  settings = {}

  
  def __init__(self, core, state = None):
    self.core = core
    self.started = False
    
    # Create and populate a new state dict if neccessary
    if not state:
      state = Bunch()
      state.settings = Bunch()
      self.is_new_instance = True
    else: self.is_new_instance = False
    self.state = state
      
    # Grab the settings from the state
    self.settings = state.settings
    self.apply_settings()
    
    # Register ourselves in the global object registry
    self.id = core.registry.register(self)
    
    
  def destroy(self):
    # Unregister ourselves from the global object registry
    self.core.registry.unregister(self.id)
    
    
  def apply_settings(self):
    pass
    
        
  def deflate(self):
    return (self.__class__, self.state)
  
  
  @staticmethod
  def inflate(core, state):
    if not state: return None
    return state[0](core, state[1])

########NEW FILE########
__FILENAME__ = job
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#######################
# 4GH nonce range job #
#######################



import struct
import traceback
from binascii import hexlify
from threading import Thread
from .sha256 import SHA256
from hashlib import sha256



class Job(object):

  
  def __init__(self, core, worksource, expiry, data, target, midstate = None, identifier = None):
    self.core = core
    self.worksource = worksource
    self.blockchain = worksource.blockchain
    self.expiry = expiry
    self.data = data
    self.target = target
    self.identifier = identifier
    self.prevhash = data[4:36]
    difficulty_inverse = struct.unpack("<Q", self.target[-12:-4])[0]
    if difficulty_inverse: self.difficulty = 65535. * 2**48 / difficulty_inverse
    else: self.difficulty = 65535. / 65536
    with self.worksource.stats.lock: self.worksource.stats.difficulty = self.difficulty
    if midstate: self.midstate = midstate
    else: self.midstate = Job.calculate_midstate(data)
    self.canceled = False
    self.destroyed = False
    self.worker = None
    self.starttime = None
    self.hashes_remaining = 2**32
    
    
  def register(self):
    self.worksource.add_job(self)
    self.blockchain.add_job(self)
    self.worksource.add_pending_mhashes(-self.hashes_remaining / 1000000.)
    self.core.event(500, self.worksource, "registerjob", None, None, None, self.worksource, self.blockchain, self)
    
    
  def destroy(self):
    if self.destroyed: return
    self.destroyed = True
    self.worksource.remove_job(self)
    self.blockchain.remove_job(self)
    self.core.workqueue.remove_job(self)
    self.worksource.add_pending_mhashes(self.hashes_remaining / 1000000.)
    self.core.event(700, self.worksource, "destroyjob", None, None, self.worker, self.worksource, self.blockchain, self)
    if self.worker:
      hashes = 2**32 - self.hashes_remaining
      self.core.event(400, self.worker, "hashes_calculated", hashes, None, self.worker, self.worksource, self.blockchain, self)
      ghashes = hashes / 1000000000.
      self.core.stats.ghashes += ghashes
      with self.worksource.stats.lock:
        self.worksource.stats.ghashes += ghashes
      with self.worker.stats.lock:
        self.worker.stats.ghashes += ghashes
    
    
  def hashes_processed(self, hashes):
    self.hashes_remaining -= hashes
    
    
  def set_worker(self, worker):
    self.worker = worker
    self.core.log(worker, "Mining %s:%s\n" % (self.worksource.settings.name, hexlify(self.data[:76]).decode("ascii")), 400)
    self.core.event(450, self.worker, "acquirejob", None, None, self.worker, self.worksource, self.blockchain, self)
    with self.worker.stats.lock: self.worker.stats.jobsaccepted += 1
    with self.worksource.stats.lock: self.worksource.stats.jobsaccepted += 1
    
    
  def nonce_found(self, nonce, ignore_invalid = False):
    nonceval = struct.unpack("<I", nonce)[0]
    self.core.event(400, self.worker, "noncefound", nonceval, None, self.worker, self.worksource, self.blockchain, self)
    data = self.data[:76] + nonce + self.data[80:]
    hash = Job.calculate_hash(data)
    if hash[-4:] != b"\0\0\0\0":
      if ignore_invalid: return False
      self.core.log(self.worker, "Got H-not-zero share %s\n" % (hexlify(nonce).decode("ascii")), 200, "yB")
      with self.worker.stats.lock: self.worker.stats.sharesinvalid += 1
      self.core.event(300, self.worker, "nonceinvalid", nonceval, None, self.worker, self.worksource, self.blockchain, self)
      return False
    self.core.log(self.worker, "Found share: %s:%s:%s\n" % (self.worksource.settings.name, hexlify(self.data[:76]).decode("ascii"), hexlify(nonce).decode("ascii")), 350, "g")
    noncediff = 65535. * 2**48 / struct.unpack("<Q", hash[-12:-4])[0]
    self.core.event(450, self.worker, "noncevalid", nonceval, str(noncediff), self.worker, self.worksource, self.blockchain, self)
    if hash[::-1] > self.target[::-1]:
      self.core.event(350, self.worksource, "noncefaileddiff", nonceval, str(self.difficulty), self.worker, self.worksource, self.blockchain, self)
      self.core.log(self.worker, "Share %s (difficulty %.5f) didn't meet difficulty %.5f\n" % (hexlify(nonce).decode("ascii"), noncediff, self.difficulty), 300, "g")
      return True
    self.worksource.nonce_found(self, data, nonce, noncediff)
    return True
    
    
  def nonce_handled_callback(self, nonce, noncediff, result):
    nonceval = struct.unpack("<I", nonce)[0]
    if result == True:
      self.core.log(self.worker, "%s accepted share %s (difficulty %.5f)\n" % (self.worksource.settings.name, hexlify(nonce).decode("ascii"), noncediff), 250, "gB")
      with self.worker.stats.lock: self.worker.stats.sharesaccepted += self.difficulty
      with self.worksource.stats.lock: self.worksource.stats.sharesaccepted += self.difficulty
      self.core.event(350, self.worksource, "nonceaccepted", nonceval, None, self.worker, self.worksource, self.blockchain, self)
    else:
      if result == False or result == None or len(result) == 0: result = "Unknown reason"
      self.core.log(self.worker, "%s rejected share %s (difficulty %.5f): %s\n" % (self.worksource.settings.name, hexlify(nonce).decode("ascii"), noncediff, result), 200, "y")
      with self.worker.stats.lock: self.worker.stats.sharesrejected += self.difficulty
      with self.worksource.stats.lock: self.worksource.stats.sharesrejected += self.difficulty
      self.core.event(300, self.worksource, "noncerejected", nonceval, result, self.worker, self.worksource, self.blockchain, self)


  def cancel(self, graceful = False):
    self.canceled = True
    if not graceful:
      self.worksource.remove_job(self)
      self.blockchain.remove_job(self)
    self.core.workqueue.remove_job(self)
    if self.worker:
      self.core.event(450, self.worksource, "canceljob", None, None, self.worker, self.worksource, self.blockchain, self)
      try: self.worker.notify_canceled(self, graceful)
      except: self.core.log(self.worker, "Exception while canceling job: %s" % (traceback.format_exc()), 100, "r")
      with self.worker.stats.lock: self.worker.stats.jobscanceled += 1
      with self.worksource.stats.lock: self.worksource.stats.jobscanceled += 1
      
      
  @staticmethod
  def calculate_midstate(data):
    return struct.pack("<8I", *struct.unpack(">8I", SHA256.hash(struct.pack("<16I", *struct.unpack(">16I", data[:64])), False)))
      
      
  @staticmethod
  def calculate_hash(data):
    return sha256(sha256(struct.pack("<20I", *struct.unpack(">20I", data[:80]))).digest()).digest()

    
    
class ValidationJob(object):

  
  def __init__(self, core, data, midstate = None):
    self.core = core
    self.data = data
    if midstate: self.midstate = midstate
    else: self.midstate = Job.calculate_midstate(data)
    self.nonce = self.data[76:80]
    self.worker = None
    self.starttime = None
    
    
  def hashes_processed(self, hashes):
    pass
    
    
  def nonce_found(self, nonce, ignore_invalid = False):
    return Job.calculate_hash(self.data[:76] + nonce)[-4:] == b"\0\0\0\0"
   
   
  def destroy(self):
    pass

########NEW FILE########
__FILENAME__ = objectregistry
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



###################
# Object registry #
###################



from threading import RLock



class ObjectRegistry(object):


  def __init__(self, core):
    self.core = core
    self.lock = RLock()
    self.current_id = 0
    self.objects = {}


  def register(self, obj):
    with self.lock:
      self.current_id += 1
      self.objects[self.current_id] = obj
      return self.current_id
      
    
  def unregister(self, id):
    try: del self.objects[id]
    except: pass
  
  
  def get(self, id):
    return self.objects[id]

########NEW FILE########
__FILENAME__ = sha256
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#########################
# SHA256 implementation #
#########################



import struct



class SHA256(object):

  _k = (0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
        0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
        0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
        0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
        0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
        0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
        0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
        0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2)

        
  def __init__(self):        
    self._buffer = b""
    self._length = 0
    self.state = (0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19)
        
        
  def _rotr(self, x, y):
      return ((x >> y) | (x << (32 - y))) & 0xffffffff

      
  def _round(self, data):
    w = [0] * 64
    w[0:15] = struct.unpack("!16L", data)
    
    for i in range(16, 64):
      s0 = self._rotr(w[i - 15], 7) ^ self._rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
      s1 = self._rotr(w[i - 2], 17) ^ self._rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & 0xffffffff
    
    a, b, c, d, e, f, g, h = self.state
    
    for i in range(64):
      t1 = h + (self._rotr(e, 6) ^ self._rotr(e, 11) ^ self._rotr(e, 25)) + ((e & f) ^ ((~e) & g)) + self._k[i] + w[i]
      t2 = (self._rotr(a, 2) ^ self._rotr(a, 13) ^ self._rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))
      h, g, f, e, d, c, b, a = g, f, e, (d + t1) & 0xffffffff, c, b, a, (t1 + t2) & 0xffffffff
        
    self.state = tuple((x + y) & 0xffffffff for x, y in zip(self.state, (a, b, c, d, e, f, g, h)))

    
  def update(self, data):
    self._buffer += data
    self._length += len(data)
    while len(self._buffer) >= 64:
      self._round(self._buffer[:64])
      self._buffer = self._buffer[64:]
      
      
  def finalize(self):
    tailbytes = self._length & 0x3f
    if tailbytes < 56: padding = 55 - tailbytes
    else: padding = 119 - tailbytes
    self.update(b"\x80" + (b"\0" * padding) + struct.pack("!Q", self._length << 3))

      
  def get_bytes(self):
    return struct.pack("!8L", *self.state)

    
  @classmethod
  def hash(cls, data, finalize = True):
    hash = cls()
    hash.update(data)
    if finalize: hash.finalize()
    return hash.get_bytes()
    
########NEW FILE########
__FILENAME__ = startable
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#############################
# In-/Deflatable base class #
#############################



import time
from threading import RLock, Thread



class Startable(object):


  def __init__(self):
    self.start_stop_lock = RLock()
    self.started = False
    self._reset()
    
    
  def destroy(self):
    self.stop()
    super(Startable, self).destroy()
    
    
  def _reset(self):
    pass
    
    
  def _start(self):
    pass


  def _stop(self):
    pass
    
    
  def start(self):
    with self.start_stop_lock:
      if self.started: return
      self._reset()
      self._start()
      self.started = True
  
  
  def stop(self):
    with self.start_stop_lock:
      if not self.started: return
      self._stop()
      self.started = False

        
  def restart(self, delay = 0):
    time.sleep(delay)
    with self.start_stop_lock:
      if not self.started: return
      self.stop()
      self.start()
      
      
  def async_start(self, delay = 0):
    Thread(None, self.start, self.settings.name + "_start", (delay,)).start()

      
  def async_stop(self, delay = 0):
    Thread(None, self.stop, self.settings.name + "_stop", (delay,)).start()
      
      
  def async_restart(self, delay = 0):
    Thread(None, self.restart, self.settings.name + "_restart", (delay,)).start()

########NEW FILE########
__FILENAME__ = statistics
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



###########################
# Statistics base classes #
###########################



from threading import RLock
from .util import Bunch



class Statistics(Bunch):


  def __init__(self, *args, **kwargs):
    super(Statistics, self).__init__(*args, **kwargs)
    

    
class StatisticsList(list):


  def __init__(self, *args, **kwargs):
    super(StatisticsList, self).__init__(*args, **kwargs)
    
    
  def calculatefieldsum(self, field):
    return sum(element[field] for element in self)

    
  def calculatefieldavg(self, field):
    if len(self) == 0: return 0
    return 1. * sum(element[field] in self) / len(self)
    
    
    
class StatisticsProvider(object):


  def __init__(self):
    self.stats = Bunch()
    self.stats.lock = RLock()
    self.children = []
    
    
  def _get_statistics(self, stats, childstats):
    stats.obj = self
    stats.id = self.id
    stats.name = self.settings.name
    stats.children = childstats

    
  def get_statistics(self):
    stats = Statistics()
    childstats = StatisticsList()
    for child in self.children: childstats.append(child.get_statistics())
    with self.stats.lock: self._get_statistics(stats, childstats)
    return stats

########NEW FILE########
__FILENAME__ = util
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#################################
# Utility classes and functions #
#################################



class OutputRedirector(object):


  def __init__(self, core, source, loglevel, flags = ""):
    self.core = core
    self.source = source
    self.loglevel = loglevel
    self.flags = flags

    
  def write(self, data):
    self.core.log(self.source, data, self.loglevel, self.flags)

    
  def flush(self): pass



class Bunch(dict):


  def __init__(self, **kw):
    dict.__init__(self, kw)
    self.__dict__ = self

    
  def __getstate__(self):
    return self

    
  def __setstate__(self, state):
    self.update(state)
    self.__dict__ = self

########NEW FILE########
__FILENAME__ = workqueue
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##############
# Work queue #
##############



import time
from threading import Condition, RLock, Thread
from .startable import Startable
from .util import Bunch
try: from queue import Queue
except: from Queue import Queue



class WorkQueue(Startable):

  
  def __init__(self, core):
    self.core = core
    self.id = -3
    self.settings = Bunch(name = "Work queue")
    super(WorkQueue, self).__init__()
    # Initialize global work queue lock and wakeup condition
    self.lock = Condition()
    self.cancelqueue = Queue()
    
    
  def _reset(self):
    self.core.event(300, self, "reset", None, "Resetting work queue state")
    super(WorkQueue, self)._reset()
    # Initialize job list container and count
    self.lists = {}
    self.target = 5
    self.count = 0
    self.expirycutoff = 0
    # Initialize taken job list container
    self.takenlists = {}
    
    
  def add_job(self, job, source = None, subsource = "unknown source"):
    if not source: source = self
    with self.lock:
      if not job.blockchain.check_job(job):
        mhashes = job.hashes_remaining / 1000000.
        job.worksource.add_pending_mhashes(-mhashes)
        job.worksource.add_deferred_mhashes(mhashes)
        self.core.log(source, "Discarding one job from %s because it is stale\n" % subsource, 500)
        return False
      expiry = int(job.expiry)
      if not expiry in self.lists: self.lists[expiry] = [job]
      else: self.lists[expiry].append(job)
      if expiry > self.expirycutoff: self.count += 1
      job.register()
      self.lock.notify_all()
      self.core.log(source, "Got one job from %s\n" % subsource, 500)
      return True
    
    
  def add_jobs(self, jobs, source = None, subsource = "unknown source"):
    if not source: source = self
    with self.lock:
      seen = {}
      accepted = 0
      dropped = 0
      for job in jobs:
        if not job.blockchain.check_job(job):
          dropped += 1
          if not job.worksource in seen:
            mhashes = 2**32 / 1000000.
            job.worksource.add_pending_mhashes(-mhashes)
            job.worksource.add_deferred_mhashes(mhashes)
            seen[job.worksource] = True
        else:
          expiry = int(job.expiry)
          if not expiry in self.lists: self.lists[expiry] = [job]
          else: self.lists[expiry].append(job)
          if expiry > self.expirycutoff: self.count += 1
          job.register()
          accepted += 1
      self.lock.notify_all()
      if accepted: self.core.log(source, "Got %d jobs from %s\n" % (accepted, subsource), 500)
      if dropped: self.core.log(source, "Discarding %d jobs from %s because they are stale\n" % (dropped, subsource), 500)
      return accepted
    
    
  def cancel_jobs(self, jobs, graceful = False):
    if not jobs: return
    self.cancelqueue.put((jobs, graceful))
    
    
  def remove_job(self, job):
    with self.lock:
      try:
        expiry = int(job.expiry)
        try:
          self.lists[expiry].remove(job)
          if expiry > self.expirycutoff: self.count -= 1
        except: pass
        try: self.takenlists[expiry].remove(job)
        except: pass
      except: pass
      
      
  def get_job(self, worker, expiry_min_ahead, async = False):
    with self.lock:
      while True:
        job = self._get_job_internal(expiry_min_ahead)
        if job:
          job.set_worker(worker)
          expiry = int(job.expiry)
          if int(job.expiry) <= self.expirycutoff: self.count += 1
          if not expiry in self.takenlists: self.takenlists[expiry] = [job]
          else: self.takenlists[expiry].append(job)
          break
        elif async: return None
        self.lock.release()
        with self.core.fetcher.lock:
          self.lock.acquire()
          self.core.fetcher.wakeup()
        self.lock.wait()
    self.core.fetcher.wakeup()
    return job


  def _get_job_internal(self, expiry_min_ahead):
    keys = sorted(self.lists.keys())
    min_expiry = time.time() + expiry_min_ahead
    # Look for a job that meets min_expiry as closely as possible
    for expiry in keys:
      if expiry <= min_expiry: continue
      list = self.lists[expiry]
      if not list: continue
      self.count -= 1
      return list.pop(0)
    # If there was none, look for the job with the latest expiry
    keys.reverse()
    for expiry in keys:
      if expiry > min_expiry: continue
      list = self.lists[expiry]
      if not list: continue
      self.count -= 1
      return list.pop(0)
    # There were no jobs at all
    return None

        
  def _start(self):
    super(WorkQueue, self)._start()
    self.shutdown = False
    self.cleanupthread = Thread(None, self._cleanuploop, "workqueue_cleanup")
    self.cleanupthread.daemon = True
    self.cleanupthread.start()
    self.cancelthread = Thread(None, self._cancelloop, "workqueue_cancelworker")
    self.cancelthread.daemon = True
    self.cancelthread.start()
  
  
  def _stop(self):
    self.shutdown = True
    self.cleanupthread.join(5)
    self.cancelqueue.put(None)
    self.cancelthread.join(5)
    self._reset()
    super(WorkQueue, self)._stop()

    
  def _cleanuploop(self):
    while not self.shutdown:
      now = time.time()
      cancel = []
      with self.lock:
        keys = sorted(self.lists.keys())
        cutoff = now + 10
        for expiry in keys:
          if expiry > cutoff: break
          if expiry > self.expirycutoff and expiry <= cutoff: self.count -= len(self.lists[expiry])
          if expiry <= now:
            while self.lists[expiry]: self.lists[expiry].pop(0).destroy()
            del self.lists[expiry]
        self.expirycutoff = cutoff
        keys = sorted(self.takenlists.keys())
        for expiry in keys:
          if expiry <= now:
            while self.takenlists[expiry]: cancel.append(self.takenlists[expiry].pop(0))
            del self.takenlists[expiry]
      self.core.fetcher.wakeup()
      self.cancel_jobs(cancel)
      time.sleep(1)

  
  def _cancelloop(self):
    while True:
      data = self.cancelqueue.get()
      if not data: return
      jobs, graceful = data
      for job in jobs:
        try: job.cancel(graceful)
        except: self.core.log(self.core, "Error while canceling job: %s\n" % traceback.format_exc(), 100, "r")

########NEW FILE########
__FILENAME__ = worksourcegroup
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



###########################
# Work source group class #
###########################



import time
import traceback
from threading import RLock
from .baseworksource import BaseWorkSource



class WorkSourceGroup(BaseWorkSource):

  version = "core.worksourcegroup v0.1.0"
  default_name = "Untitled work source group"
  is_group = True,
  settings = dict(BaseWorkSource.settings, **{
    "distribution_granularity": {"title": "Distribution granularity", "type": "float", "position": 20000},
  })


  def __init__(self, core, state = None):
    super(WorkSourceGroup, self).__init__(core, state)
    
    # Populate state dict if this is a new instance
    if self.is_new_instance:
      self.state.children = []
      
    # Instantiate child work sources
    self.childlock = RLock()
    self.children = []
    for childstate in self.state.children:
      self.add_work_source(BaseWorkSource.inflate(core, childstate))
      

  def _reset(self):
    super(WorkSourceGroup, self)._reset()
    self.last_index = 0
    self.last_time = time.time()

      
  def apply_settings(self):
    super(WorkSourceGroup, self).apply_settings()
    if not "distribution_granularity" in self.settings or not self.settings.distribution_granularity:
      self.settings.distribution_granularity = 16

      
  def deflate(self):
    # Deflate children first
    self.state.children = []
    for child in self.children:
      self.state.children.append(child.deflate())
    # Let BaseWorkSource handle own deflation
    return super(WorkSourceGroup, self).deflate()


  def add_work_source(self, worksource):
    with self.start_stop_lock:
      w = self
      while w:
        if w == worksource: raise Exception("Trying to move work source %s into itself or one of its descendants!" % worksource.settings.name)
        w = w.get_parent()
      old_parent = worksource.get_parent()
      if old_parent: old_parent.remove_work_source(worksource)
      worksource.set_parent(self)
      with self.childlock:
        if not worksource in self.children:
          if self.started:
            try:
              self.core.log(self, "Starting up work source %s...\n" % (worksource.settings.name), 800)
              worksource.start()
            except Exception as e:
              self.core.log(self, "Could not start work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
          self.children.append(worksource)

    
  def remove_work_source(self, worksource):
    with self.start_stop_lock:
      with self.childlock:
        while worksource in self.children:
          worksource.set_parent()
          if self.started:
            try:
              self.core.log(self, "Shutting down work source %s...\n" % (worksource.settings.name), 800)
              worksource.stop()
            except Exception as e:
              self.core.log(self, "Could not stop work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
          self.children.remove(worksource)
        
        
  def _start(self):
    super(WorkSourceGroup, self)._start()
    with self.childlock:
      for worksource in self.children:
        try:
          self.core.log(self, "Starting up work source %s...\n" % (worksource.settings.name), 800)
          worksource.start()
        except Exception as e:
          self.core.log(self, "Could not start work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
  
  
  def _stop(self):
    with self.childlock:
      for worksource in self.children:
        try:
          self.core.log(self, "Shutting down work source %s...\n" % (worksource.settings.name), 800)
          worksource.stop()
        except Exception as e:
          self.core.log(self, "Could not stop work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
    super(WorkSourceGroup, self)._stop()
      
      
  def _distribute_mhashes(self):
    with self.statelock:
      now = time.time()
      timestep = now - self.last_time
      self.last_time = now
      mhashes_remaining = 2**32 / 1000000. * self.settings.distribution_granularity
      total_priority = 0
      for child in self.children:
        if child.settings.enabled:
          with child.statelock:
            total_priority += child.settings.priority
            mhashes = timestep * child.settings.hashrate
            child.mhashes_pending += mhashes + child.mhashes_deferred * 0.1
            mhashes_remaining -= mhashes
            child.mhashes_deferred *= 0.9
      if mhashes_remaining > 0 and total_priority > 0:
        unit = mhashes_remaining / total_priority
        for child in self.children:
          if child.settings.enabled:
            with child.statelock:
              mhashes = unit * child.settings.priority
              child.mhashes_pending += mhashes
              mhashes_remaining -= mhashes


  def _get_start_index(self):
    with self.statelock:
      self.last_index += 1
      if self.last_index >= len(self.children): self.last_index = 0
      return self.last_index
      
      
  def _start_fetcher(self, jobs, force = False):
    with self.childlock:
      children = [child for child in self.children]
      startindex = self._get_start_index()
    best = False
    found = False
    iteration = 0
    while not found:
      index = startindex
      first = True
      while index != startindex or first:
        worksource = children[index]
        mhashes = 0
        if not worksource.is_group: mhashes = 2**32 / 1000000.
        if force or worksource.mhashes_pending >= mhashes:
          found = True
          if mhashes: worksource.add_pending_mhashes(-mhashes)
          result, gotjobs = worksource.start_fetchers(1, jobs)
          if result is not False:
            if mhashes: worksource.add_pending_mhashes(mhashes)
            if result: return result, gotjobs
            best = result
        index += 1
        if index >= len(children): index = 0
        first = False
      if not found: self._distribute_mhashes()
      iteration += 1
      if iteration > 150: break
      if iteration > 100: force = True
    return best, 0
    
    
  def get_running_fetcher_count(self):
    data = [child.get_running_fetcher_count() for child in self.children]
    return sum(child[0] for child in data), sum(child[1] for child in data)

    
  def start_fetchers(self, count, jobs):
    if not self.started or not self.settings.enabled or not self.children or not count: return False, 0
    started = 0
    result = False
    totaljobs = 0
    while started < count and totaljobs < jobs:
      result, newjobs = self._start_fetcher(jobs)
      if not result: result, newjobs = self._start_fetcher(jobs, True)
      if not result: break
      started += result
      totaljobs += newjobs
    if started: return started, totaljobs
    return result, 0

########NEW FILE########
__FILENAME__ = cursesui
# -*- coding: utf-8 -*-
# Modular Python Bitcoin Miner
# Copyright (C) 2011-2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.


####################
# Curses UI module #
####################

# Module configuration options:
#   updateinterval: Statistics update interval in seconds (default: 1)


import sys
import curses
import threading
import traceback
import atexit
import time
import datetime

class CursesUI(object):
  def __init__(self, miner, dict):
    self.__dict__ = dict
    self.miner = miner
    self.updateinterval = getattr(self, "updateinterval", 1)
    self.ysplit = 10 + len(self.miner.pools) + self.countchildren(self.miner.workers)
    atexit.register(self.shutdown)
    self.mainwin = curses.initscr()
    curses.start_color()
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_RED, 0)
    curses.init_pair(2, curses.COLOR_YELLOW, 0)
    curses.init_pair(3, curses.COLOR_GREEN, 0)
    self.red = curses.color_pair(1)
    self.yellow = curses.color_pair(2)
    self.green = curses.color_pair(3)
    self.mainwin.idlok(True)
    self.mainwin.scrollok(True)
    self.mainwin.erase()
    self.mainwin.refresh()
    self.logwin = curses.newpad(500, 500)
    self.logwin.scrollok(True)
    self.logwin.move(499, 0)
    self.loglf = True
    thread = threading.Thread(None, self.mainloop, "Curses UI")
    thread.daemon = True
    thread.start()
    
  def shutdown(self):
    self.message("", "\n", "")
    self.miner.logqueue.join()
    curses.endwin()
    
  def countchildren(self, children):
    childcount = len(children)
    for child in children:
      childcount = childcount + self.countchildren(child.children)
    return childcount
    
  def calculatemaxfieldlen(self, children, field, indent = 0):
    maxlen = 0
    for child in children:
      length = len(child[field][0])
      if length > maxlen: maxlen = length
    return maxlen
  
  def translatepooldata(self, pools, poolstats, indent = 0):
    for pool in pools:
      bold = "B" if len(pool["children"]) > 0 else ""
      uptime = 1
      try: uptime = (time.time() - pool["starttime"])
      except: pass
      try: failedpercent = 100. * pool["failedreqs"] / pool["requests"]
      except: failedpercent = 0
      try: stalepercent = 100. * pool["rejected"] / (pool["accepted"] + pool["rejected"])
      except: stalepercent = 0
      try: retrypercent = 100. * pool["uploadretries"] / (pool["accepted"] + pool["rejected"])
      except: retrypercent = 0
      try: efficiency = pool["accepted"] * pool["difficulty"] / pool["mhashes"] * 429503.2833
      except: efficiency = 0
      poolstats.append({ \
        "name": (" " * indent + pool["name"], bold, "l"), \
        "longpolling": ("Yes", "g" + bold, "c") if pool["longpolling"] == True else ("No", "r" + bold, "c") if pool["longpolling"] == False else ("Unkn", "y" + bold, "c"), \
        "difficulty": ("%.5f" % pool["difficulty"], bold, "r"), \
        "requests": ("%d" % pool["requests"], bold, "r"), \
        "failedreqs": ("%d (%.1f%%)" % (pool["failedreqs"], failedpercent), "r" + bold if failedpercent > 5 else "g" + bold if failedpercent < 1 else "y" + bold, "r"), \
        "jobsaccepted": ("%d" % pool["jobsaccepted"], bold, "r"), \
        "longpollkilled": ("%d" % pool["longpollkilled"], bold, "r"), \
        "accepted": ("%d" % pool["accepted"], bold, "r"), \
        "rejected": ("%d (%.1f%%)" % (pool["rejected"], stalepercent), "r" + bold if stalepercent > 5 else "g" + bold if stalepercent < 1 else "y" + bold, "r"), \
        "uploadretries": ("%d (%.1f%%)" % (pool["uploadretries"], retrypercent), "r" + bold if retrypercent > 5 else "g" + bold if retrypercent < 1 else "y" + bold, "r"), \
        "avgmhps": ("%.2f" % (pool["mhashes"] / uptime), bold, "r"), \
        "efficiency": ("%.1f%%" % efficiency, "r" + bold if efficiency < 80 else "g" + bold if efficiency > 95 else "y" + bold, "r"), \
        "score": ("%.0f" % pool["score"], bold, "r"), \
      })
      self.translatepooldata(pool["children"], poolstats, indent + 2)
    
  def translateworkerdata(self, workers, workerstats, indent = 0):
    for worker in workers:
      bold = "B" if len(worker["children"]) > 0 else ""
      uptime = 1
      try: uptime = (time.time() - worker["starttime"])
      except: pass
      try: stalepercent = 100. * worker["rejected"] / (worker["accepted"] + worker["rejected"])
      except: stalepercent = 0
      try: invalidpercent = 100. * worker["invalid"] / (worker["accepted"] + worker["rejected"] + worker["invalid"])
      except: invalidpercent = 0
      try: efficiency = worker["accepted"] / worker["mhashes"] * 429503.2833
      except: efficiency = 0
      try: invalidwarning = worker['invalidwarning']
      except: invalidwarning = 1
      try: invalidcritical = worker['invalidcritical']
      except: invalidcritical = 10
      try: tempwarning = worker['tempwarning']
      except: tempwarning = 40
      try: tempcritical = worker['tempcritical']
      except: tempcritical = 50
      if invalidpercent > invalidcritical or ("temperature" in worker and worker['temperature'] != None and worker['temperature'] > tempcritical):
        namecolor = "r" if len(worker["children"]) == 0 else ""
      elif invalidpercent > invalidwarning or ("temperature" in worker and worker['temperature'] != None and worker['temperature'] > tempwarning):
        namecolor = "y" if len(worker["children"]) == 0 else ""
      else:
        namecolor = ""
      workerstats.append({ \
        "name": (" " * indent + worker["name"], namecolor + bold, "l"), \
        "jobsaccepted": ("%d" % worker["jobsaccepted"], bold, "r"), \
        "accepted": ("%.0f" % worker["accepted"], bold, "r"), \
        "rejected": ("%.0f (%.1f%%)" % (worker["rejected"], stalepercent), "r" + bold if stalepercent > 5 else "g" + bold if stalepercent < 1 else "y" + bold, "r"), \
        "invalid": ("%.0f (%.1f%%)" % (worker["invalid"], invalidpercent), "r" + bold if invalidpercent > invalidcritical else "g" + bold if invalidpercent < invalidwarning else "y" + bold, "r"), \
        "mhps": ("%.2f" % worker["mhps"], bold, "r"), \
        "avgmhps": ("%.2f" % (worker["mhashes"] / uptime), bold, "r"), \
        "efficiency": ("%.1f%%" % efficiency, "r" + bold if efficiency < 80 else "g" + bold if efficiency > 95 else "y" + bold, "r"), \
        "temperature": ("%.1f" % worker["temperature"], "r" + bold if worker["temperature"] > tempcritical else "y" + bold if worker["temperature"] > tempwarning else "g" + bold, "c") if "temperature" in worker and worker["temperature"] != None else ("", bold, "c"), \
        "currentpool": (worker["currentpool"] if "currentpool" in worker and worker["currentpool"] != None else "Unknown", bold, "c"), \
      })
      self.translateworkerdata(worker["children"], workerstats, indent + 2)
      
  def drawtable(self, y, columns, stats):
    for column in columns:
      self.mainwin.addstr(y, column["x"], column["title1"].center(column["width"]))
      self.mainwin.addstr(y + 1, column["x"], column["title2"].center(column["width"]), curses.A_UNDERLINE)
      if column["x"] > 0: self.mainwin.vline(y, column["x"] - 1, curses.ACS_VLINE, len(stats) + 2)
      cy = y + 2
      last = cy + len(stats) - 1
      for row in stats:
        data = row[column["field"]]
        if data[2] == "r": text = data[0].rjust(column["width"])
        elif data[2] == "c": text = data[0].center(column["width"])
        else: text = data[0].ljust(column["width"])
        attr = 0 if cy == last else curses.A_UNDERLINE
        if "r" in data[1]: attr = attr | self.red
        elif "y" in data[1]: attr = attr | self.yellow
        elif "g" in data[1]: attr = attr | self.green
        if "B" in data[1]: attr = attr | curses.A_BOLD
        if "U" in data[1]: attr = attr | curses.A_UNDERLINE
        self.mainwin.addstr(cy, column["x"], text, attr)
        cy = cy + 1

  def mainloop(self):
    while True:
      try:
        pooldata = self.miner.collectstatistics(self.miner.pools)
        workerdata = self.miner.collectstatistics(self.miner.workers)
        poolstats = []
        self.translatepooldata(pooldata, poolstats)
        poolcolumns = []
        x = 0
        width = max(4, self.calculatemaxfieldlen(poolstats, "name", 2))
        poolcolumns.append({"title1": "Pool", "title2": "name", "field": "name", "x": x, "width": width})
        x = x + 1 + width
        width = max(4, self.calculatemaxfieldlen(poolstats, "longpolling"))
        poolcolumns.append({"title1": "Long", "title2": "poll", "field": "longpolling", "x": x, "width": width})
        x = x + 1 + width
        width = max(5, self.calculatemaxfieldlen(poolstats, "difficulty"))
        poolcolumns.append({"title1": "", "title2": "Diff.", "field": "difficulty", "x": x, "width": width})
        x = x + 1 + width
        width = max(8, self.calculatemaxfieldlen(poolstats, "requests"))
        poolcolumns.append({"title1": "Job", "title2": "requests", "field": "requests", "x": x, "width": width})
        x = x + 1 + width
        width = max(10, self.calculatemaxfieldlen(poolstats, "failedreqs"))
        poolcolumns.append({"title1": "Failed job", "title2": "requests", "field": "failedreqs", "x": x, "width": width})
        x = x + 1 + width
        width = max(4, self.calculatemaxfieldlen(poolstats, "jobsaccepted"))
        poolcolumns.append({"title1": "Acc.", "title2": "jobs", "field": "jobsaccepted", "x": x, "width": width})
        x = x + 1 + width
        width = max(4, self.calculatemaxfieldlen(poolstats, "longpollkilled"))
        poolcolumns.append({"title1": "Rej.", "title2": "jobs", "field": "longpollkilled", "x": x, "width": width})
        x = x + 1 + width
        width = max(6, self.calculatemaxfieldlen(poolstats, "accepted"))
        poolcolumns.append({"title1": "Acc.", "title2": "shares", "field": "accepted", "x": x, "width": width})
        x = x + 1 + width
        width = max(12, self.calculatemaxfieldlen(poolstats, "rejected"))
        poolcolumns.append({"title1": "Stale shares", "title2": "(rejected)", "field": "rejected", "x": x, "width": width})
        x = x + 1 + width
        width = max(12, self.calculatemaxfieldlen(poolstats, "uploadretries"))
        poolcolumns.append({"title1": "Share upload", "title2": "retries", "field": "uploadretries", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(poolstats, "avgmhps"))
        poolcolumns.append({"title1": "Average", "title2": "MHash/s", "field": "avgmhps", "x": x, "width": width})
        x = x + 1 + width
        width = max(6, self.calculatemaxfieldlen(poolstats, "efficiency"))
        poolcolumns.append({"title1": "Effi-", "title2": "ciency", "field": "efficiency", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(poolstats, "score"))
        poolcolumns.append({"title1": "Current", "title2": "bias", "field": "score", "x": x, "width": width})
        workerstats = []
        self.translateworkerdata(workerdata, workerstats)
        workercolumns = []
        x = 0
        width = max(6, self.calculatemaxfieldlen(workerstats, "name", 2))
        workercolumns.append({"title1": "Worker", "title2": "name", "field": "name", "x": x, "width": width})
        x = x + 1 + width
        width = max(4, self.calculatemaxfieldlen(workerstats, "jobsaccepted"))
        workercolumns.append({"title1": "Acc.", "title2": "jobs", "field": "jobsaccepted", "x": x, "width": width})
        x = x + 1 + width
        width = max(6, self.calculatemaxfieldlen(workerstats, "accepted"))
        workercolumns.append({"title1": "Acc.", "title2": "shares", "field": "accepted", "x": x, "width": width})
        x = x + 1 + width
        width = max(10, self.calculatemaxfieldlen(workerstats, "rejected"))
        workercolumns.append({"title1": "Stales", "title2": "(rejected)", "field": "rejected", "x": x, "width": width})
        x = x + 1 + width
        width = max(12, self.calculatemaxfieldlen(workerstats, "invalid"))
        workercolumns.append({"title1": "Invalids", "title2": "(K not zero)", "field": "invalid", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(workerstats, "mhps"))
        workercolumns.append({"title1": "Current", "title2": "MHash/s", "field": "mhps", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(workerstats, "avgmhps"))
        workercolumns.append({"title1": "Average", "title2": "MHash/s", "field": "avgmhps", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(workerstats, "temperature"))
        workercolumns.append({"title1": "Temp.", "title2": "(deg C)", "field": "temperature", "x": x, "width": width})
        x = x + 1 + width
        width = max(6, self.calculatemaxfieldlen(workerstats, "efficiency"))
        workercolumns.append({"title1": "Effi-", "title2": "ciency", "field": "efficiency", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(workerstats, "currentpool"))
        workercolumns.append({"title1": "Current", "title2": "pool", "field": "currentpool", "x": x, "width": width})
        with self.miner.conlock:
          try:
            self.ysplit = 10 + len(poolstats) + len(workerstats)
            (my, mx) = self.mainwin.getmaxyx()
            self.mainwin.erase()
            self.mainwin.hline(1, 0, curses.ACS_HLINE, mx)
            self.mainwin.hline(self.ysplit - 1, 0, curses.ACS_HLINE, mx)
            self.mainwin.addstr(0, (mx - len(self.miner.useragent)) // 2, self.miner.useragent, curses.A_BOLD)
            inqueue = self.miner.queue.qsize()
            try: queueseconds = (inqueue / self.miner.jobspersecond)
            except: queueseconds = 0
            color = self.red if inqueue <= self.miner.queuelength * 1 / 10 else self.green if inqueue >= self.miner.queuelength * 9 / 10 - 1 else self.yellow
            self.mainwin.addstr(2, 0, "Total speed: ")
            self.mainwin.addstr(("%.1f MH/s" % self.miner.mhps).rjust(11), curses.A_BOLD)
            self.mainwin.addstr(" - Buffer: ")
            self.mainwin.addstr(("%d" % inqueue).ljust(2), color | curses.A_BOLD)
            self.mainwin.addstr("/", color)
            self.mainwin.addstr(("%d" % self.miner.queuelength).rjust(2), color | curses.A_BOLD)
            self.mainwin.addstr(" (", color)
            self.mainwin.addstr(("%.2f" % queueseconds), color | curses.A_BOLD)
            self.mainwin.addstr(" seconds)", color)
            self.drawtable(4, poolcolumns, poolstats)
            self.drawtable(7 + len(poolstats), workercolumns, workerstats)
            self.mainwin.noutrefresh()
            (my, mx) = self.mainwin.getmaxyx()
            (ly, lx) = self.logwin.getmaxyx()
            self.logwin.refresh(ly - my + self.ysplit - 1, 0, self.ysplit, 0, min(my, ly - 1 + self.ysplit) - 1, min(mx, lx) - 1)
          except:
            try:
              self.mainwin.erase()
              self.mainwin.addstr(0, 0, "Failed to display stats!\nWindow is probably too small.", self.red | curses.A_BOLD)
              self.mainwin.refresh()
            except: pass
      except Exception as e:
        self.miner.log("Exception while updating CursesUI stats: %s\n" % traceback.format_exc(), "rB")
      time.sleep(self.updateinterval)

  def message(self, date, str, format):
    attr = 0
    if "r" in format: attr = self.red
    elif "y" in format: attr = self.yellow
    elif "g" in format: attr = self.green
    if "B" in format: attr = attr | curses.A_BOLD
    if "U" in format: attr = attr | curses.A_UNDERLINE
    for i in range(5):
      try:
        self.logwin.addstr(date)
        self.logwin.addstr(str, attr)
        break
      except: pass
    if "\n" in str:
      for i in range(5):
        try:
          (my, mx) = self.mainwin.getmaxyx();
          (ly, lx) = self.logwin.getmaxyx();
          self.logwin.refresh(ly - my + self.ysplit - 1, 0, self.ysplit, 0, min(my, ly - 1 + self.ysplit) - 1, min(mx, lx) - 1)
          break
        except: pass

########NEW FILE########
__FILENAME__ = boardproxy
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#################################################################################
# FPGA Mining LLC X6500 FPGA Miner Board out of process board access dispatcher #
#################################################################################



import time
import signal
import traceback
from threading import Thread, Condition, RLock
from multiprocessing import Process
from .util.ft232r import FT232R, FT232R_PyUSB, FT232R_D2XX, FT232R_PortList
from .util.jtag import JTAG
from .util.fpga import FPGA
from .util.format import formatNumber, formatTime
from .util.BitstreamReader import BitFile



class X6500BoardProxy(Process):
  

  def __init__(self, rxconn, txconn, serial, useftd2xx, takeover, uploadfirmware, firmware, pollinterval):
    super(X6500BoardProxy, self).__init__()
    self.rxconn = rxconn
    self.txconn = txconn
    self.serial = serial
    self.useftd2xx = useftd2xx
    self.takeover = takeover
    self.uploadfirmware = uploadfirmware
    self.firmware = firmware
    self.pollinterval = pollinterval


  def run(self):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    self.lock = RLock()
    self.wakeup = Condition()
    self.error = None
    self.pollingthread = None
    self.shutdown = False
  
    try:

      # Listen for setup commands
      while True:
        data = self.rxconn.recv()
        
        if data[0] == "connect": break
        
        else: raise Exception("Unknown setup message: %s" % str(data))
        
      # Connect to board
      if self.useftd2xx: self.device = FT232R(FT232R_D2XX(self.serial))
      else: self.device = FT232R(FT232R_PyUSB(self.serial, self.takeover))
      self.fpgas = [FPGA(self, "FPGA0", self.device, 0), FPGA(self, "FPGA1", self.device, 1)]
      needupload = False
      
      for id, fpga in enumerate(self.fpgas):
        fpga.id = id
        self.log("Discovering FPGA%d...\n" % id, 600)
        fpga.detect()
        for idcode in fpga.jtag.idcodes:
          self.log("FPGA%d: %s - Firmware: rev %d, build %d\n" % (id, JTAG.decodeIdcode(idcode), fpga.firmware_rev, fpga.firmware_build), 500)
        if fpga.jtag.deviceCount != 1: raise Exception("This module needs two JTAG buses with one FPGA each!")
        if not fpga.jtag.read_ir()[5]: needupload = True

      # Upload firmware if we were asked to
      if self.uploadfirmware or needupload:
        self.log("Programming FPGAs...\n", 200, "B")
        start_time = time.time()
        bitfile = BitFile.read(self.firmware)
        self.log("Firmware file details:\n", 400, "B")
        self.log("  Design Name: %s\n" % bitfile.designname, 400)
        self.log("  Firmware: rev %d, build: %d\n" % (bitfile.rev, bitfile.build), 400)
        self.log("  Part Name: %s\n" % bitfile.part, 400)
        self.log("  Date: %s\n" % bitfile.date, 400)
        self.log("  Time: %s\n" % bitfile.time, 400)
        self.log("  Bitstream Length: %d\n" % len(bitfile.bitstream), 400)
        jtag = JTAG(self.device, 2)
        jtag.deviceCount = 1
        jtag.idcodes = [bitfile.idcode]
        jtag._processIdcodes()
        for fpga in self.fpgas:
          for idcode in fpga.jtag.idcodes:
            if idcode & 0x0FFFFFFF != bitfile.idcode:
              raise Exception("Device IDCode does not match bitfile IDCode! Was this bitstream built for this FPGA?")
        FPGA.programBitstream(self.device, jtag, bitfile.bitstream, self.progresshandler)
        self.log("Programmed FPGAs in %f seconds\n" % (time.time() - start_time), 300)
        bitfile = None  # Free memory
        # Update the FPGA firmware details:
        for fpga in self.fpgas: fpga.detect()

      # Start polling thread
      self.pollingthread = Thread(None, self.polling_thread, "polling_thread")
      self.pollingthread.daemon = True
      self.pollingthread.start()
      
      self.send("started_up", self.fpgas[0].firmware_rev, self.fpgas[1].firmware_rev)

      # Listen for commands
      while True:
        if self.error: raise self.error
      
        data = self.rxconn.recv()
        
        if data[0] == "shutdown": break

        elif data[0] == "ping": self.send("pong")

        elif data[0] == "pong": pass

        elif data[0] == "set_pollinterval":
          self.pollinterval = data[1]
          with self.wakeup: self.wakeup.notify()
        
        elif data[0] == "send_job":
          start = time.time()
          self.fpgas[data[1]].writeJob(data[2])
          end = time.time()
          self.respond(start, end)
        
        elif data[0] == "shutdown_fpga":
          self.fpgas[data[1]].sleep()
        
        elif data[0] == "clear_queue":
          self.fpgas[data[1]].clearQueue()
        
        elif data[0] == "set_speed":
          self.fpgas[data[1]].setClockSpeed(data[2])
        
        elif data[0] == "get_speed":
          self.respond(self.fpgas[data[1]].readClockSpeed())
        
        else: raise Exception("Unknown message: %s" % str(data))
      
    except: self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
    finally:
      self.shutdown = True
      with self.wakeup: self.wakeup.notify()
      try: self.pollingthread.join(2)
      except: pass
      self.send("dying")
      
      
  def send(self, *args):
    with self.lock: self.txconn.send(args)
      
      
  def respond(self, *args):
    self.send("response", *args)
      
      
  def log(self, message, loglevel, format = ""):
    self.send("log", message, loglevel, format)
    
    
  def polling_thread(self):
    try:
      counter = 0
      while not self.shutdown:
        # Poll for nonces
        for i in range(2):
          nonce = self.fpgas[i].readNonce()
          if nonce is not None: self.send("nonce_found", i, time.time(), nonce)
    
        counter += 1
        if counter >= 10:
          counter = 0
          # Read temperatures
          temps = self.device.read_temps()
          self.send("temperature_read", *temps)
        
        with self.wakeup: self.wakeup.wait(self.pollinterval)
        
    except Exception as e:
      self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
      self.error = e
      # Unblock main thread
      self.send("ping")

      
  # Firmware upload progess indicator
  def progresshandler(self, start_time, now_time, written, total):
    try: percent_complete = 100. * written / total
    except ZeroDivisionError: percent_complete = 0
    try: speed = written / (1000 * (now_time - start_time))
    except ZeroDivisionError: speed = 0
    try: remaining_sec = 100 * (now_time - start_time) / percent_complete
    except ZeroDivisionError: remaining_sec = 0
    remaining_sec -= now_time - start_time
    self.log("%.1f%% complete [%sB/s] [%s remaining]\n" % (percent_complete, formatNumber(speed), formatTime(remaining_sec)), 500)
        
########NEW FILE########
__FILENAME__ = BitstreamReader
# Copyright (C) 2011 by fpgaminer <fpgaminer@bitcoin-mining.com>
#                       fizzisist <fizzisist@fpgamining.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Parse a .BIT file generated by Xilinx's bitgen.
# That is the default file generated during ISE's compilation.
#
# FILE FORMAT:
#
# Consists of an initial 11 bytes of unknown content (???)
# Then 5 fields of the format:
#  1 byte key
#  2 byte, Big Endian Length (EXCEPT: The last field, which has a 4 byte length)
#  data (of length specified above ^)
# 
# The 5 fields have keys in the sequence a, b, c, d, e
# The data from the first 4 fields are strings:
# design name, part name, date, time
# The last field is the raw bitstream.
#

import time
import struct

# Dictionary for looking up idcodes from device names:
idcode_lut = {'6slx150fgg484': 0x401d093, '6slx45csg324': 0x4008093, '6slx150tfgg676': 0x403D093}

class BitFileReadError(Exception):
  _corruptFileMessage = "Unable to parse .bit file; header is malformed. Is it really a Xilinx .bit file?"

  def __init__(self, value=None):
    self.parameter = BitFileReadError._corruptFileMessage if value is None else value
  def __str__(self):
    return repr(self.parameter)
    
class BitFileMismatch(Exception):
  _mismatchMessage = "Device IDCode does not match bitfile IDCode! Was this bitstream built for this FPGA?"

  def __init__(self, value=None):
    self.parameter = BitFileReadError._mismatchMessage if value is None else value
  def __str__(self):
    return repr(self.parameter)
    
class BitFileUnknown(Exception):
  _unknownMessage = "Bitfile has an unknown UserID! Was this bitstream built for the X6500?"
  def __init__(self, value=None):
    self.parameter = BitFileReadError._unknownMessage if value is None else value
  def __str__(self):
    return repr(self.parameter)
  
class Object(object):
  pass

class BitFile:
  """Read a .bit file and return a BitFile object."""
  @staticmethod
  def read(name):
    with open(name, 'rb') as f:
      bitfile = BitFile()
      
      # 11 bytes of unknown data
      if BitFile._readLength(f) != 9:
        raise BitFileReadError()
      
      BitFile._readOrDie(f, 11)
      
      bitfile.designname = BitFile._readField(f, b"a").decode("latin1").rstrip('\0')
      bitfile.userid = int(bitfile.designname.split(';')[-1].split('=')[-1], base=16)
      bitfile.part = BitFile._readField(f, b"b").decode("latin1").rstrip('\0')
      bitfile.date = BitFile._readField(f, b"c").decode("latin1").rstrip('\0')
      bitfile.time = BitFile._readField(f, b"d").decode("latin1").rstrip('\0')
      bitfile.idcode = idcode_lut[bitfile.part]
      
      if bitfile.userid == 0xFFFFFFFF:
        bitfile.rev = 0
        bitfile.build = 0
      elif (bitfile.userid >> 16) & 0xFFFF == 0x4224:
        bitfile.rev = (bitfile.userid >> 8) & 0xFF
        bitfile.build = bitfile.userid & 0xFF
      else:
        raise BitFileUnknown()
      
      if BitFile._readOrDie(f, 1) != b"e":
        raise BitFileReadError()
      
      length = BitFile._readLength4(f)
      bitfile.bitstream = BitFile._readOrDie(f, length)
      
      return bitfile
  
  # Read a 2-byte, unsigned, Big Endian length.
  @staticmethod
  def _readLength(filestream):
    return struct.unpack(">H", BitFile._readOrDie(filestream, 2))[0]

  @staticmethod
  def _readLength4(filestream):
    return struct.unpack(">I", BitFile._readOrDie(filestream, 4))[0]

  # Read length bytes, or throw an exception
  @staticmethod
  def _readOrDie(filestream, length):
    data = filestream.read(length)

    if len(data) < length:
      raise BitFileReadError()

    return data

  @staticmethod
  def _readField(filestream, key):
    if BitFile._readOrDie(filestream, 1) != key:
      raise BitFileReadError()

    length = BitFile._readLength(filestream)
    data = BitFile._readOrDie(filestream, length)

    return data
    

  def __init__(self):
    self.designname = None
    self.rev = None
    self.build = None
    self.part = None
    self.date = None
    self.time = None
    self.length = None
    self.idcode = None
    self.bitstream = None


########NEW FILE########
__FILENAME__ = format
# -*- coding: utf-8 -*-

# Copyright (C) 2011 by jedi95 <jedi95@gmail.com> and 
#                CFSworks <CFSworks@gmail.com>
#                fizzisist <fizzisist@fpgamining.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

def formatNumber(n):
  """Format a positive integer in a more readable fashion."""
  if n < 0:
    raise ValueError('can only format positive integers')
  prefixes = 'kMGTP'
  whole = str(int(n))
  decimal = ''
  i = 0
  while len(whole) > 3:
    if i + 1 < len(prefixes):
      decimal = '.%s' % whole[-3:-1]
      whole = whole[:-3]
      i += 1
    else:
      break
  return '%s%s %s' % (whole, decimal, prefixes[i])

def formatTime(seconds):
  """Take a number of seconds and turn it into a string like 32m18s"""
  minutes = int(seconds / 60)
  hours = int(minutes / 60)
  days = int(hours / 24)
  weeks = int(days / 7)
  seconds = seconds % 60
  minutes = minutes % 60
  hours = hours % 24
  days = days % 7
  
  time_string = ''
  if weeks > 0:
    time_string += '%dw' % weeks
  if days > 0:
    time_string += '%dd' % days
  if hours > 0:
    time_string += '%dh' % hours
  if minutes > 0:
    time_string += '%dm' % minutes
  if hours < 1:
    # hide the seconds when we're over an hour
    time_string += '%ds' % seconds
  
  return time_string

########NEW FILE########
__FILENAME__ = fpga
# Copyright (C) 2011 by fizzisist <fizzisist@fpgamining.com>
#                       fpgaminer <fpgaminer@bitcoin-mining.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct
from .jtag import JTAG

class Object(object):
  pass

# JTAG instructions:
USER_INSTRUCTION = 0b000010
JSHUTDOWN        = 0b001101
JSTART           = 0b001100
JPROGRAM         = 0b001011
CFG_IN           = 0b000101
CFG_OUT          = 0b000100
BYPASS           = 0b111111
USERCODE         = 0b001000

def hexstr2array(hexstr):
  """Convert a hex string into an array of bytes"""
  arr = []
  for i in range(len(hexstr)/2):
    arr.append((int(hexstr[i*2], 16) << 4) | int(hexstr[i*2+1], 16))
  return arr

def int2bits(i, bits):
  """Convert an integer to an array of bits, LSB first."""
  result = []
  for n in range(bits):
    result.append(i & 1)
    i = i >> 1
  return result

def bits2int(bits):
  """Convert an array of bits to an integer, LSB first."""
  x = 0
  for i in range(len(bits)):
    x |= bits[i] << i
  return x

def jtagcomm_checksum(bits):
  checksum = 1
  for x in bits:
    checksum ^= x
  return [checksum]


class FPGA:
  def __init__(self, proxy, name, ft232r, chain):
    self.proxy = proxy
    self.name = name
    self.ft232r = ft232r
    self.chain = chain
    self.jtag = JTAG(ft232r, chain)
    
    self.asleep = True

    self.firmware_rev = 0
    self.firmware_build = 0
  
  def detect(self):
    """Detect all devices on the JTAG chain"""
    with self.ft232r.mutex:
      self.jtag.detect()

      # Always use the last part in the chain
      if self.jtag.deviceCount > 0:
        self.jtag.part(self.jtag.deviceCount-1)

        usercode = self._readUserCode()

        if usercode == 0xFFFFFFFF:
          self.firmware_rev = 0
          self.firmware_build = 0
        else:
          self.firmware_rev = (usercode >> 8) & 0xFF
          self.firmware_build = usercode & 0xFF

  # Read the FPGA's USERCODE register, which gets set by the firmware
  # In our case this should be 0xFFFFFFFF for all old firmware revs,
  # and 0x4224???? for newer revs. The 2nd byte determines firmware rev/version,
  # and the 1st byte determines firmware build.
  def _readUserCode(self):
    with self.ft232r.mutex:
      if self.asleep: self.wake()
      self.jtag.tap.reset()
      self.jtag.instruction(USERCODE)
      self.jtag.shift_ir()
      usercode = bits2int(self.jtag.read_dr(int2bits(0, 32)))

    return usercode
  
  # Old JTAG Comm:
  def _readByte(self):
    bits = int2bits(0, 13)
    byte = bits2int(self.jtag.read_dr(bits))
    return byte
   
  # New JTAG Comm
  # Read a 32-bit register
  def _readRegister(self, address):
    address = address & 0xF

    with self.ft232r.mutex:
      if self.asleep: self.wake()
      self.jtag.tap.reset()
      self.jtag.instruction(USER_INSTRUCTION)
      self.jtag.shift_ir()

      # Tell the FPGA what address we would like to read
      data = int2bits(address, 5)
      data = data + jtagcomm_checksum(data)
      self.jtag.shift_dr(data)

      # Now read back the register
      data = self.jtag.read_dr(int2bits(0, 32))
      data = bits2int(data)

      self.jtag.tap.reset()

    return data
  # Write a single 32-bit register
  # If doing multiple writes, this won't be as efficient
  def _writeRegister(self, address, data):
    address = address & 0xF
    data = data & 0xFFFFFFFF

    with self.ft232r.mutex:
      if self.asleep: self.wake()
      self.jtag.tap.reset()
      self.jtag.instruction(USER_INSTRUCTION)
      self.jtag.shift_ir()

      # Tell the FPGA what address we would like to write
      # and the data.
      data = int2bits(data, 32) + int2bits(address, 4) + [1]
      data = data + jtagcomm_checksum(data)
      self.jtag.shift_dr(data)

      self.jtag.tap.reset()
      self.ft232r.flush()
  
  def _burstWriteHelper(self, address, data):
    address = address & 0xF
    x = int2bits(data, 32)
    x += int2bits(address, 4)
    x += [1]
    x = x + jtagcomm_checksum(x)

    self.jtag.shift_dr(x)

  
  # Writes multiple 32-bit registers.
  # data should be an array of 32-bit values
  # address is the starting address.
  # TODO: Implement readback of some kind to ensure all our writes succeeded.
  # TODO: This is difficult, because reading back data will slow things down.
  # TODO: If the JTAG class let us read data back after a shift, we could probably
  # TODO: use that at the end of the burst write.
  def _burstWrite(self, address, data):
    with self.ft232r.mutex:
      if self.asleep: self.wake()
      self.jtag.tap.reset()
      self.jtag.instruction(USER_INSTRUCTION)
      self.jtag.shift_ir()

      for offset in range(len(data)):
        self._burstWriteHelper(address + offset, data[offset])

      self.jtag.tap.reset()
      self.ft232r.flush()

    return True
  
  # TODO: Remove backwards compatibility in a future rev.
  def _old_readNonce(self):
    with self.ft232r.mutex:
      if self.asleep: self.wake()
      self.jtag.tap.reset()
      self.jtag.instruction(USER_INSTRUCTION)
      self.jtag.shift_ir()
      self.asleep = False

      # Sync to the beginning of a nonce.
      # The MSB is a VALID flag. If 0, data is invalid (queue empty).
      # The next 4-bits indicate which byte of the nonce we got.
      # 1111 is LSB, and then 0111, 0011, 0001.
      byte = None
      while True:
        byte = self._readByte()

        # check data valid bit:
        if byte < 0x1000:
          self.jtag.tap.reset()
          return None
        
        #self.logger.reportDebug("%d: Read: %04x" % (self.id, byte))
        
        # check byte counter:
        if (byte & 0xF00) == 0xF00:
          break
      
      # We now have the first byte
      nonce = byte & 0xFF
      count = 1
      #self.logger.reportDebug("%d: Potential nonce, reading the rest..." % self.id)
      while True:
        byte = self._readByte()
        
        #self.logger.reportDebug("%d: Read: %04x" % (self.id, byte))
        
        # check data valid bit:
        if byte < 0x1000:
          self.jtag.tap.reset()
          return None
        
        # check byte counter:
        if (byte & 0xF00) >> 8 != (0xF >> count):
          self.jtag.tap.reset()
          return None
        
        nonce |= (byte & 0xFF) << (count * 8)
        count += 1
        
        if (byte & 0xF00) == 0x100:
          break

      self.jtag.tap.reset()

    #self.logger.reportDebug("%d: Nonce completely read: %08x" % (self.id, nonce))

    return struct.pack("<I", nonce)
  
  # TODO: This may not actually clear the queue, but should be correct most of the time.
  def _old_clearQueue(self):
    with self.ft232r.mutex:
      self.proxy.log(self.name + ": Clearing queue...\n", 600)
      self.wake()
      self.jtag.tap.reset()
      self.jtag.instruction(USER_INSTRUCTION)
      self.jtag.shift_ir()
      
      while True:
        if self._readByte() < 0x1000:
          break
      self.jtag.tap.reset()
    
  def _old_writeJob(self, job):
    # We need the 256-bit midstate, and 12 bytes from data.
    # The first 64 bytes of data are already hashed (hence midstate),
    # so we skip that. Of the last 64 bytes, 52 bytes are constant and
    # not needed by the FPGA.
    
    data = job[31::-1] + job[:31:-1] + b"\0"

    with self.ft232r.mutex:
      if self.asleep: self.wake()
      self.jtag.tap.reset()
      self.jtag.instruction(USER_INSTRUCTION)
      self.jtag.shift_ir()

      for i in range(len(data)):
        x = struct.unpack("B", data[i : i + 1])[0]

        if i != 0:
          x = 0x100 | x
          
        self.jtag.shift_dr(int2bits(x, 13))
      
      self.jtag.tap.reset()

      self.ft232r.flush()
    
  def _readNonce(self):
    nonce = self._readRegister(0xE)
    if nonce == 0xFFFFFFFF:
      return None
    return struct.pack("<I", nonce)
  
  def _clearQueue(self):
    while True:
      if self._readNonce() is None:
        break
    
  def _writeJob(self, job):
    # We need the 256-bit midstate, and 12 bytes from data.
    # The first 64 bytes of data are already hashed (hence midstate),
    # so we skip that. Of the last 64 bytes, 52 bytes are constant and
    # not needed by the FPGA.
    
    #start_time = time.time()
    
    words = struct.unpack("<11I", job)
    if not self._burstWrite(1, words):
      return
    
  # Read the FPGA's current clock speed, in MHz
  # NOTE: This is currently just what we've written into the clock speed
  # register, so it does NOT take into account hard limits in the firmware.
  def readClockSpeed(self):
    if self.firmware_rev == 0:
      return None
    
    frequency = self._readRegister(0xD)

    return frequency

  # Set the FPGA's clock speed, in MHz
  # NOTE: Be VERY careful not to set the clock speed too high!!!
  def setClockSpeed(self, speed):
    if self.firmware_rev == 0:
      return False

    return self._writeRegister(0xD, speed)
  
  def readNonce(self):
    if self.firmware_rev == 0:
      return self._old_readNonce()
    else:
      return self._readNonce()
  
  def clearQueue(self):
    if self.firmware_rev == 0:
      return self._old_clearQueue()
    else:
      return self._clearQueue()
  
  def writeJob(self, job):
    if self.firmware_rev == 0:
      return self._old_writeJob(job)
    else:
      return self._writeJob(job)
  
  def sleep(self):
    if self.firmware_rev == 0:
      with self.ft232r.mutex:
        self.proxy.log(self.name + ": Going to sleep...\n", 500)
        self.jtag.tap.reset()
        self.jtag.instruction(JSHUTDOWN)
        self.jtag.shift_ir()
        self.jtag.runtest(24)
        self.jtag.tap.reset()
        
        self.ft232r.flush()
    self.asleep = True
  
  def wake(self):
    if self.firmware_rev == 0:
      with self.ft232r.mutex:
        self.proxy.log(self.name + ": Waking up...\n", 500)
        self.jtag.tap.reset()
        self.jtag.instruction(JSTART)
        self.jtag.shift_ir()
        self.jtag.runtest(24)
        self.jtag.instruction(BYPASS)
        self.jtag.shift_ir()
        self.jtag.instruction(BYPASS)
        self.jtag.shift_ir()
        self.jtag.instruction(JSTART)
        self.jtag.shift_ir()
        self.jtag.runtest(24)
        self.jtag.tap.reset()
        
        self.ft232r.flush()
    self.asleep = False
  
  @staticmethod
  def programBitstream(ft232r, jtag, bitstream, progresscallback = None):
    with ft232r.mutex:
      # Select the device
      jtag.reset()
      jtag.part(jtag.deviceCount-1)
      
      jtag.instruction(BYPASS) 
      jtag.shift_ir()

      jtag.instruction(JPROGRAM)
      jtag.shift_ir()

      jtag.instruction(CFG_IN)
      jtag.shift_ir()

      # Clock TCK for 10000 cycles
      jtag.runtest(10000)

      jtag.instruction(CFG_IN)
      jtag.shift_ir()
      jtag.shift_dr([0]*32)
      jtag.instruction(CFG_IN)
      jtag.shift_ir()

      ft232r.flush()
      
      # Load bitstream into CFG_IN
      jtag.load_bitstream(bitstream, progresscallback)

      jtag.instruction(JSTART)
      jtag.shift_ir()

      # Let the device start
      jtag.runtest(24)
      
      jtag.instruction(BYPASS)
      jtag.shift_ir()
      jtag.instruction(BYPASS)
      jtag.shift_ir()

      jtag.instruction(JSTART)
      jtag.shift_ir()

      jtag.runtest(24)
      
      # Check done pin
      #jtag.instruction(BYPASS)
      # TODO: Figure this part out. & 0x20 should equal 0x20 to check the DONE pin ... ???
      #print jtag.read_ir() # & 0x20 == 0x21
      #jtag.instruction(BYPASS)
      #jtag.shift_ir()
      #jtag.shift_dr([0])

      ft232r.flush()

########NEW FILE########
__FILENAME__ = ft232r
# Copyright (C) 2011 by fpgaminer <fpgaminer@bitcoin-mining.com>
#                       fizzisist <fizzisist@fpgamining.com>
# Copyright (C) 2012 by TheSeven
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import time
import struct
import threading
from .jtag import JTAG

class DeviceNotOpened(Exception): pass
class NoAvailableDevices(Exception): pass
class InvalidChain(Exception): pass
class WriteError(Exception): pass


class FT232R_PortList:
  """Information about which of the 8 GPIO pins to use."""
  def __init__(self, tck0, tms0, tdi0, tdo0, tck1, tms1, tdi1, tdo1):
    self.tck0 = tck0
    self.tms0 = tms0
    self.tdi0 = tdi0
    self.tdo0 = tdo0
    self.tck1 = tck1
    self.tms1 = tms1
    self.tdi1 = tdi1
    self.tdo1 = tdo1
  
  def output_mask(self):
    return (1 << self.tck0) | (1 << self.tms0) | (1 << self.tdi0) | \
           (1 << self.tck1) | (1 << self.tms1) | (1 << self.tdi1)

  def format(self, tck, tms, tdi, chain=2):
    """Format the pin states as a single byte for sending to the FT232R
    Chain is the JTAG chain: 0 or 1, or 2 for both
    """
    if chain == 0:
      return struct.pack('B', ((tck & 1) << self.tck0) | ((tms & 1) << self.tms0) | ((tdi & 1) << self.tdi0))
    if chain == 1:
      return struct.pack('B', ((tck & 1) << self.tck1) | ((tms & 1) << self.tms1) | ((tdi & 1) << self.tdi1))
    if chain == 2:
      return struct.pack('B', ((tck & 1) << self.tck0) | ((tms & 1) << self.tms0) | ((tdi & 1) << self.tdi0) |
                              ((tck & 1) << self.tck1) | ((tms & 1) << self.tms1) | ((tdi & 1) << self.tdi1))
    else:
      raise InvalidChain()
  
  def chain_portlist(self, chain=0):
    """Returns a JTAG_PortList object for the specified chain"""
    if chain == 0:
      return JTAG_PortList(self.tck0, self.tms0, self.tdi0, self.tdo0)
    elif chain == 1:
      return JTAG_PortList(self.tck1, self.tms1, self.tdi1, self.tdo1)
    elif chain == 2:
      return self
    else:
      raise InvalidChain()


class JTAG_PortList:
  """A smaller version of the FT232R_PortList class, specific to the JTAG chain"""
  def __init__(self, tck, tms, tdi, tdo):
    self.tck = tck
    self.tms = tms
    self.tdi = tdi
    self.tdo = tdo
  
  def format(self, tck, tms, tdi):
    return struct.pack('B', ((tck & 1) << self.tck) | ((tms & 1) << self.tms) | ((tdi & 1) << self.tdi))


class FT232R:
  def __init__(self, handle):
    self.mutex = threading.RLock()
    self.handle = handle
    self.serial = handle.serial
    self.synchronous = None
    self.write_buffer = b""
    self.portlist = FT232R_PortList(7, 6, 5, 4, 3, 2, 1, 0)
    self.setSyncMode()
    self.handle.purgeBuffers()
    
  def __enter__(self): 
    return self

  # Be sure to close the opened handle, if there is one.
  # The device may become locked if we don't (requiring an unplug/plug cycle)
  def __exit__(self, exc_type, exc_value, traceback):
    self.close()
    return False
  
  def close(self):
    with self.mutex:
      self.handle.close()
  
  def setSyncMode(self):
    """Put the FT232R into Synchronous mode."""
    self.handle.setBitMode(self.portlist.output_mask(), 0)
    self.handle.setBitMode(self.portlist.output_mask(), 4)
    self.synchronous = True

  def setAsyncMode(self):
    """Put the FT232R into Asynchronous mode."""
    self.handle.setBitMode(self.portlist.output_mask(), 0)
    self.handle.setBitMode(self.portlist.output_mask(), 1)
    self.synchronous = False
  
  def purgeBuffers(self):
    self.handle.purgeBuffers()

  def _setCBUSBits(self, sc, cs):
    # CBUS pins:
    #  SIO_0 = CBUS0 = input
    #  SIO_1 = CBUS1 = input
    #  CS    = CBUS2 = output
    #  SC    = CBUS3 = output
    
    SIO_0 = 0
    SIO_1 = 1
    CS    = 2
    SC    = 3
    read_mask = ( (1 << SC) | (1 << CS) | (0 << SIO_1) | (0 << SIO_0) ) << 4
    CBUS_mode = 0x20
    
    # set up I/O and start conversion:
    pin_state = (sc << SC) | (cs << CS)
    self.handle.setBitMode(read_mask | pin_state, CBUS_mode)

  def _getCBUSBits(self):
    SIO_0 = 0
    SIO_1 = 1
    data = self.handle.getBitMode()
    return (((data >> SIO_0) & 1), ((data >> SIO_1) & 1)) 
    
  def write(self, data):
    with self.mutex:
      self.handle.write(data)
    
  def read(self, size, timeout):
    with self.mutex:
      return self.handle.write(size, timeout)
    
  def flush(self):
    with self.mutex:
      """Write all data in the write buffer and purge the FT232R buffers"""
      self.setAsyncMode()
      self.handle.write(self.write_buffer)
      self.write_buffer = b""
      self.setSyncMode()
      self.handle.purgeBuffers()
  
  def read_data(self, num):
    with self.mutex:
      """Read num bytes from the FT232R and return an array of data."""
      
      if num == 0:
        self.flush()
        return b""

      # Repeat the last byte so we can read the last bit of TDO.
      write_buffer = self.write_buffer[-(num*3):]
      self.write_buffer = self.write_buffer[:-(num*3)]

      # Write all data that we don't care about.
      if len(self.write_buffer) > 0:
        self.flush()
        self.handle.purgeBuffers()

      data = b""

      while len(write_buffer) > 0:
        bytes_to_write = min(len(write_buffer), 3072)
        
        self.write(write_buffer[:bytes_to_write])
        write_buffer = write_buffer[bytes_to_write:]
        
        data = data + self.handle.read(bytes_to_write, 3)
        
      return data

  def read_temps(self):
    with self.mutex:
      
      # clock SC with CS high:
      self._setCBUSBits(0, 1)
      self._setCBUSBits(1, 1)
      self._setCBUSBits(0, 1)
      self._setCBUSBits(1, 1)
      
      # drop CS to start conversion:
      self._setCBUSBits(0, 0)
      
      code0 = 0
      code1 = 0
      
      for i in range(16):
        self._setCBUSBits(1, 0)
        (sio_0, sio_1) = self._getCBUSBits()
        code0 |= sio_0 << (15 - i)
        code1 |= sio_1 << (15 - i)
        self._setCBUSBits(0, 0)
      
      # assert CS and clock SC:
      self._setCBUSBits(0, 1)
      self._setCBUSBits(1, 1)
      self._setCBUSBits(0, 1)
      
      if code0 == 0xFFFF or code0 == 0: temp0 = None
      else:
        if (code0 >> 15) & 1 == 1: code0 -= (1 << 16)
        temp0 = (code0 >> 2) * 0.03125
      if code1 == 0xFFFF or code1 == 0: temp1 = None
      else:
        if (code1 >> 15) & 1 == 1: code1 -= (1 << 16)
        temp1 = (code1 >> 2) * 0.03125
      
      return (temp0, temp1)
      
      
class FT232R_D2XX:
  def __init__(self, deviceid):
    import d2xx
    self.handle = None
    self.serial = deviceid
    devices = d2xx.listDevices()
    for devicenum, serial in enumerate(devices):
      if deviceid != "" and deviceid != serial: continue
      try:
        self.handle = d2xx.open(devicenum)
        self.serial = serial
        break
      except: pass
    if self.handle == None: raise Exception("Can not open the specified device")
    self.handle.setBaudRate(3000000)
    
  def __enter__(self): 
    return self

  # Be sure to close the opened handle, if there is one.
  # The device may become locked if we don't (requiring an unplug/plug cycle)
  def __exit__(self, exc_type, exc_value, traceback):
    self.close()
    return False
  
  def close(self):
    if self.handle is None:
      return
    try:
      self.handle.close()
    finally:
      self.handle = None
  
  def purgeBuffers(self):
    if self.handle is None:
      raise DeviceNotOpened()
    self.handle.purge(0)
  
  def setBitMode(self, mask, mode):
    if self.handle is None:
      raise DeviceNotOpened()
    self.handle.setBitMode(mask, mode)

  def getBitMode(self):
    if self.handle is None:
      raise DeviceNotOpened()
    return self.handle.getBitMode()
    
  def write(self, data):
    if self.handle is None:
      raise DeviceNotOpened()
    size = len(data)
    offset = 0
    while offset < size:
      write_size = min(4096, size - offset)
      ret = self.handle.write(data[offset : offset + write_size])
      offset = offset + ret
    
  def read(self, size, timeout):
    if self.handle is None:
      raise DeviceNotOpened()
    timeout = timeout + time.time()
    data = b""
    offset = 0
    while offset < size and time.time() < timeout:
      ret = self.handle.read(min(4096, size - offset))
      data = data + ret
      offset = offset + len(ret)
    return data
    
      
class FT232R_PyUSB:
  def __init__(self, deviceid, takeover):
    import usb
    self.handle = None
    self.serial = deviceid
    permissionproblem = False
    deviceinuse = False
    for bus in usb.busses():
      if self.handle != None: break
      for dev in bus.devices:
        if self.handle != None: break
        if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
          try:
            handle = dev.open()
            manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
            product = handle.getString(dev.iProduct, 100).decode("latin1")
            serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
            if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner"):
              if deviceid == "" or deviceid == serial:
                try:
                  if takeover:
                    handle.reset()
                    time.sleep(1)
                  configuration = dev.configurations[0]
                  interface = configuration.interfaces[0][0]
                  handle.setConfiguration(configuration.value)
                  handle.claimInterface(interface.interfaceNumber)
                  handle.setAltInterface(interface.alternateSetting)
                  self.inep = interface.endpoints[0].address
                  self.inepsize = interface.endpoints[0].maxPacketSize
                  self.outep = interface.endpoints[1].address
                  self.outepsize = interface.endpoints[1].maxPacketSize
                  self.index = 1
                  self.handle = handle
                  self.serial = serial
                except: deviceinuse = True
          except: permissionproblem = True
    if self.handle == None:
      if deviceinuse:
        raise Exception("Can not open the specified device, possibly because it is already in use")
      if permissionproblem:
        raise Exception("Can not open the specified device, possibly due to insufficient permissions")
      raise Exception("Can not open the specified device")
    self.handle.controlMsg(0x40, 3, None, 0, 0, 1000)
    
  def __enter__(self): 
    return self

  # Be sure to close the opened handle, if there is one.
  # The device may become locked if we don't (requiring an unplug/plug cycle)
  def __exit__(self, exc_type, exc_value, traceback):
    self.close()
    return False
  
  def close(self):
    if self.handle is None:
      return
    try:
      self.handle.releaseInterface()
      self.handle.setConfiguration(0)
      self.handle.reset()
    finally:
      self.handle = None
  
  def purgeBuffers(self):
    if self.handle is None:
      raise DeviceNotOpened()
    self.handle.controlMsg(0x40, 0, None, 1, self.index, 1000)
    self.handle.controlMsg(0x40, 0, None, 2, self.index, 1000)
    
  def setBitMode(self, mask, mode):
    if self.handle is None:
      raise DeviceNotOpened()
    self.handle.controlMsg(0x40, 0xb, None, (mode << 8) | mask, self.index, 1000)
  
  def getBitMode(self):
    if self.handle is None:
      raise DeviceNotOpened()
    return struct.unpack("B", bytes(bytearray(self.handle.controlMsg(0xc0, 0xc, 1, 0, self.index, 1000))))[0]
    
  def write(self, data):
    if self.handle is None:
      raise DeviceNotOpened()
    size = len(data)
    offset = 0
    while offset < size:
      write_size = min(4096, size - offset)
      ret = self.handle.bulkWrite(self.outep, data[offset : offset + write_size], 1000)
      offset = offset + ret
    
  def read(self, size, timeout):
    if self.handle is None:
      raise DeviceNotOpened()
    timeout = timeout + time.time()
    data = b""
    offset = 0
    while offset < size and time.time() < timeout:
      ret = bytes(bytearray(self.handle.bulkRead(self.inep, min(64, size - offset + 2), 1000)))
      data = data + ret[2:]
      offset = offset + len(ret) - 2
    return data

########NEW FILE########
__FILENAME__ = jtag
# Copyright (C) 2011 by fpgaminer <fpgaminer@bitcoin-mining.com>
#                       fizzisist <fizzisist@fpgamining.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# Usage Example:
# with JTAG() as jtag:
#   blah blah blah ...
#

from .TAP import TAP
import sys
import time
import struct
import threading
try: import queue
except ImportError: import Queue as queue


class NoDevicesDetected(Exception): pass
class IDCodesNotRead(Exception): pass
class ChainNotProperlyDetected(Exception): pass
class InvalidChain(Exception): pass
class WriteError(Exception): pass

class UnknownIDCode(Exception):
  def __init__(self, idcode):
    self.idcode = idcode
  def __str__(self):
    return repr(self.idcode)

# LUT for instruction register length based on ID code:
irlength_lut = {0x403d093: 6, 0x401d093: 6, 0x4008093: 6, 0x5057093: 16, 0x5059093: 16};
# LUT for device name based on ID code:
name_lut = {0x403d093: 'Spartan 6 LX150T', 0x401d093: 'Spartan 6 LX150', 0x5059093: 'Unknown', 0x5057093: 'Unknown'}

class JTAG:
  def __init__(self, ft232r, chain):
    self.ft232r = ft232r
    self.chain = chain
    self.deviceCount = None
    self.idcodes = None
    self.irlengths = None
    self.current_instructions = [1] * 100  # Default is to put all possible devices into BYPASS. # TODO: Should be 1000
    self.current_part = 0
    self._tckcount = 0
    self.portlist = ft232r.portlist.chain_portlist(chain)
    self.tap = TAP(self.jtagClock)

    
  def detect(self):
    """Detect all devices on the JTAG chain. Call this after open."""
    self.deviceCount = None
    self.idcodes = None
    self.irlengths = None
    
    retries_left = 5
    while retries_left > 0:
      self.deviceCount = self._readDeviceCount()
      if self.deviceCount is None or self.deviceCount == 0:
        retries_left -= 1
      else:
        break
    if self.deviceCount is None or self.deviceCount == 0:
      raise NoDevicesDetected
    
    self._readIdcodes()
    self._processIdcodes()
    
    self.reset()
    self.part(0)
    self.ft232r.flush()
  
  def part(self, part):
    """Change the active part."""
    self.current_part = part
  
  def instruction(self, instruction):
    """Sets the current_instructions to a new instruction.
    Accepts an integer instruction and builds an array of bits.
    """
    if self.irlengths is None:
      raise ChainNotProperlyDetected()
    
    start = sum(self.irlengths[self.current_part+1:])
    end = start + self.irlengths[self.current_part]
    
    for i in range(len(self.current_instructions)):
      if i >= start and i < end:
        self.current_instructions[i] = instruction & 1
        instruction >>= 1
      else:
        self.current_instructions[i] = 1
  
  def reset(self):
    """Reset JTAG chain"""
    total_ir = 100 # TODO: Should be 1000
    if self.irlengths is not None:
      total_ir = sum(self.irlengths)

    self.current_instructions = [1] * total_ir
    #self.shift_ir()
    self.tap.reset()
  
  def shift_ir(self, read=False):
    self.tap.goto(TAP.SELECT_IR)
    self.tap.goto(TAP.SHIFT_IR)
    
    for bit in self.current_instructions[:-1]:
      self.jtagClock(tdi=bit)
    self.jtagClock(tdi=self.current_instructions[-1], tms=1)

    self._tckcount = 0
    self.tap.goto(TAP.IDLE)

    if read:
      return self.read_tdo(len(self.current_instructions)+self._tckcount)[:-self._tckcount]
  
  def read_ir(self):
    return self.shift_ir(read=True)
  
  # TODO: Doesn't work correctly if not operating on the last device in the chain
  def shift_dr(self, bits, read=False):
    self.tap.goto(TAP.SELECT_DR)
    self.tap.goto(TAP.SHIFT_DR)

    bits += [0] * self.current_part

    for bit in bits[:-1]:
      self.jtagClock(tdi=bit)
    self.jtagClock(tdi=bits[-1], tms=1)

    self._tckcount = 0
    self.tap.goto(TAP.IDLE)

    if read:
      return self.read_tdo(len(bits)+self._tckcount)[:len(bits)-self.current_part]
  
  def read_dr(self, bits):
    return self.shift_dr(bits, read=True)
  
  def read_tdo(self, num):
    """Reads num bits from TDO, and returns the bits as an array."""
    data = self.ft232r.read_data(num)
    bits = []
    for n in range(len(data)//3):
      bits.append((struct.unpack("B", data[n*3+2:n*3+3])[0] >> self.portlist.tdo)&1)
    
    return bits
  
  def runtest(self, tckcount):
    """Clock TCK in the IDLE state for tckcount cycles"""
    self.tap.goto(TAP.IDLE)
    for i in range(tckcount):
      self.jtagClock(tms=0)
      
  def bitstream_preparation_thread(self, bitstream, buffer):
    python2 = sys.hexversion // 0x1000000 < 3
    bytetotal = len(bitstream)
    for i in range(0, bytetotal, 1024):
      chunk = b""
      for d in bitstream[i : min(bytetotal - 1, i + 1024)]:
        if python2: d = ord(d)
        val7 = (d >> 6) & 2
        val7 = val7 | (val7 << 4)
        val6 = (d >> 5) & 2
        val6 = val6 | (val6 << 4)
        val5 = (d >> 4) & 2
        val5 = val5 | (val5 << 4)
        val4 = (d >> 3) & 2
        val4 = val4 | (val4 << 4)
        val3 = (d >> 2) & 2
        val3 = val3 | (val3 << 4)
        val2 = (d >> 1) & 2
        val2 = val2 | (val2 << 4)
        val1 = d & 2
        val1 = val1 | (val1 << 4)
        val0 = (d & 1) << 1
        val0 = val0 | (val0 << 4)
        chunk += struct.pack("16B", val7, val7 | 0x88, val6, val6 | 0x88, \
                                    val5, val5 | 0x88, val4, val4 | 0x88, \
                                    val3, val3 | 0x88, val2, val2 | 0x88, \
                                    val1, val1 | 0x88, val0, val0 | 0x88)
      buffer.put(chunk)               
    buffer.put(None)
  
  def load_bitstream(self, bitstream, progressCallback=None):
    self.tap.goto(TAP.SELECT_DR)
    self.tap.goto(TAP.SHIFT_DR)
    self.ft232r.flush()
    
    self.ft232r.setAsyncMode()
    
    start_time = time.time()
    last_update = 0

    bytetotal = len(bitstream)
    written = 0
    buffer = queue.Queue(16)
    thread = threading.Thread(None, self.bitstream_preparation_thread, "bitstreamprepare", kwargs = {"bitstream": bitstream, "buffer": buffer})
    thread.daemon = True
    thread.start()
    
    while True:
      chunk = buffer.get()
      if chunk == None: break
      self.ft232r.write(chunk)
      written = written + len(chunk) / 16
      
      if time.time() > (last_update + 3) and progressCallback:
        progressCallback(start_time, time.time(), written, bytetotal)
        last_update = time.time()
    
    self.ft232r.setSyncMode()
    self.ft232r.purgeBuffers()
    
    d = struct.unpack("B", bitstream[-1:])[0]
    for i in range(7, 0, -1):
      self.jtagClock(tdi=(d >> i) & 1)
    self.jtagClock(tdi=d & 1, tms=1)
    
    self.tap.goto(TAP.IDLE)
    self.ft232r.flush()
  
  def _formatJtagClock(self, tms=0, tdi=0):
    return self._formatJtagState(0, tms, tdi) + self._formatJtagState(1, tms, tdi)
  
  def _formatJtagState(self, tck, tms, tdi):
    return self.portlist.format(tck, tms, tdi)
  
  def jtagClock(self, tms=0, tdi=0):    
    self.ft232r.write_buffer += self._formatJtagState(0, tms, tdi)
    self.ft232r.write_buffer += self._formatJtagState(1, tms, tdi)
    self.ft232r.write_buffer += self._formatJtagState(1, tms, tdi)

    self.tap.clocked(tms)
    self._tckcount += 1
  
  def parseByte(self, bits):
    return (bits[7] << 7) | (bits[6] << 6) | (bits[5] << 5) | (bits[4] << 4) | (bits[3] << 3) | (bits[2] << 2) |  (bits[1] << 1) | bits[0]
  
  def _readDeviceCount(self):
    deviceCount = None
    #self.tap.reset()

    # Force BYPASS
    self.reset()
    self.part(0)

    # Force BYPASS
    self.shift_ir()
    #self.shiftIR([1]*100)  # Should be 1000

    # Flush DR registers
    self.shift_dr([0]*100)


    # Fill with 1s to detect chain length
    data = self.read_dr([1]*100)

    # Now see how many devices there were.
    for i in range(0, len(data)-1):
      if data[i] == 1:
        deviceCount = i
        break

    return deviceCount
  
  def _readIdcodes(self):
    if self.deviceCount is None:
      raise NoDevicesDetected()

    self.idcodes = []

    #self.tap.reset()
    self.reset()
    self.part(0)

    data = self.read_dr([1]*32*self.deviceCount)
    
    for d in range(self.deviceCount):
      idcode = self.parseByte(data[0:8])
      idcode |= self.parseByte(data[8:16]) << 8
      idcode |= self.parseByte(data[16:24]) << 16
      idcode |= self.parseByte(data[24:32]) << 24
      data = data[32:]

      self.idcodes.insert(0, idcode)
  
  def _processIdcodes(self):
    if self.idcodes is None:
      raise IDCodesNotRead()

    self.irlengths = []


    for idcode in self.idcodes:
      if (idcode & 0x0FFFFFFF) in irlength_lut:
        self.irlengths.append(irlength_lut[idcode & 0x0FFFFFFF])
      else:
        self.irlengths = None
        raise UnknownIDCode(idcode)
  
  @staticmethod
  def decodeIdcode(idcode):
    if (idcode & 1) != 1:
      return "Warning: Bit 0 of IDCODE is not 1. Not a valid Xilinx IDCODE."

    manuf = (idcode >> 1) & 0x07ff
    size = (idcode >> 12) & 0x01ff
    family = (idcode >> 21) & 0x007f
    rev = (idcode >> 28) & 0x000f

    return name_lut[idcode & 0xFFFFFFF]
    #print "Manuf: %x, Part Size: %x, Family Code: %x, Revision: %0d" % (manuf, size, family, rev)

########NEW FILE########
__FILENAME__ = TAP
# Copyright (C) 2011 by fpgaminer <fpgaminer@bitcoin-mining.com>
#                       fizzisist <fizzisist@fpgamining.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

class TAPStateError(Exception):
  def __init__(self, current, destination):
    self.current = TAP.STR_TRANSLATE[current]
    self.destination = TAP.STR_TRANSLATE[destination]
  def __str__(self):
    return self.current + " -> " + self.destination

class TAP:
  TLR = 0
  IDLE = 1
  SELECT_DR = 2
  CAPTURE_DR = 3
  SHIFT_DR = 4
  EXIT1_DR = 5
  PAUSE_DR = 6
  EXIT2_DR = 7
  UPDATE_DR = 8
  SELECT_IR = 9
  CAPTURE_IR = 10
  SHIFT_IR = 11
  EXIT1_IR = 12
  PAUSE_IR = 13
  EXIT2_IR = 14
  UPDATE_IR = 15

  STR_TRANSLATE = ['TLR','IDLE','SELECT_DR','CAPTURE_DR','SHIFT_DR','EXIT1_DR','PAUSE_DR','EXIT2_DR','UPDATE_DR','SELECT_IR','CAPTURE_IR','SHIFT_IR','EXIT1_IR','PAUSE_IR','EXIT2_IR','UPDATE_IR']

  TRANSITIONS = {
    TLR: [IDLE, TLR],
    IDLE: [IDLE, SELECT_DR],
    SELECT_DR: [CAPTURE_DR, SELECT_IR],
    CAPTURE_DR: [SHIFT_DR, EXIT1_DR],
    SHIFT_DR: [SHIFT_DR, EXIT1_DR],
    EXIT1_DR: [PAUSE_DR, UPDATE_DR],
    PAUSE_DR: [PAUSE_DR, EXIT2_DR],
    EXIT2_DR: [SHIFT_DR, UPDATE_DR],
    UPDATE_DR: [IDLE, SELECT_DR],
    SELECT_IR: [CAPTURE_IR, TLR],
    CAPTURE_IR: [SHIFT_IR, EXIT1_IR],
    SHIFT_IR: [SHIFT_IR, EXIT1_IR],
    EXIT1_IR: [PAUSE_IR, UPDATE_IR],
    PAUSE_IR: [PAUSE_IR, EXIT2_IR],
    EXIT2_IR: [SHIFT_IR, UPDATE_IR],
    UPDATE_IR: [IDLE, SELECT_DR]
  }

  def __init__(self, jtagClock):
    self.jtagClock = jtagClock
    self.state = None
  
  def reset(self):
    for i in range(6):
      self.jtagClock(tms=1)

    self.state = TAP.TLR
  
  def clocked(self, tms):
    if self.state is None:
      return
    
    state = self.state
    self.state = TAP.TRANSITIONS[self.state][tms]

  
  # When goto is called, we look at where we want to go and where we are.
  # Based on that we choose where to clock TMS low or high.
  # After that we see if we've reached our goal. If not, call goto again.
  # This recursive behavior keeps the function simple.
  def goto(self, state):
    # If state is Unknown, reset.
    if self.state is None:
      self.reset()
    elif state == TAP.TLR:
      self.jtagClock(tms=1)
    elif self.state == TAP.TLR:
      self.jtagClock(tms=0)
    elif state == TAP.SELECT_DR:
      if self.state != TAP.IDLE:
        raise TAPStateError(self.state, state)

      self.jtagClock(tms=1)
    elif state == TAP.SELECT_IR:
      if self.state != TAP.IDLE:
        raise TAPStateError(self.state, state)

      self.jtagClock(tms=1)
      self.jtagClock(tms=1)
    elif state == TAP.SHIFT_DR:
      if self.state != TAP.SELECT_DR:
        raise TAPStateError(self.state, state)

      self.jtagClock(tms=0)
      self.jtagClock(tms=0)
    elif state == TAP.SHIFT_IR:
      if self.state != TAP.SELECT_IR:
        raise TAPStateError(self.state, state)

      self.jtagClock(tms=0)
      self.jtagClock(tms=0)
    elif state == TAP.IDLE:
      if self.state == TAP.IDLE:
        self.jtagClock(tms=0)
      elif self.state == TAP.EXIT1_DR or self.state == TAP.EXIT1_IR:
        self.jtagClock(tms=1)
        self.jtagClock(tms=0)
      else:
        raise TAPStateError(self.state, state)
    else:
      raise TAPStateError(self.state, state)


    if self.state != state:
      self.goto(state)
    
  
  


########NEW FILE########
__FILENAME__ = x6500hotplug
# Modular Python Bitcoin Miner
# Copyright (C) 2011-2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



####################################################################
# FPGA Mining LLC X6500 FPGA Miner Board hotplug controller module #
####################################################################



import traceback
from threading import Condition, Thread
from core.baseworker import BaseWorker
from .x6500worker import X6500Worker



# Worker main class, referenced from __init__.py
class X6500HotplugWorker(BaseWorker):
  
  version = "fpgamining.x6500 hotplug manager v0.1.0"
  default_name = "X6500 hotplug manager"
  can_autodetect = True
  settings = dict(BaseWorker.settings, **{
    "useftd2xx": {
      "title": "Driver",
      "type": "enum",
      "values": [
        {"value": False, "title": "PyUSB"},
        {"value": True, "title": "D2XX"},
      ],
      "position": 1100
    },
    "takeover": {"title": "Reset board if it appears to be in use", "type": "boolean", "position": 1200},
    "uploadfirmware": {"title": "Force firmware upload", "type": "boolean", "position": 1300},
    "firmware": {"title": "Firmware file location", "type": "string", "position": 1400},
    "blacklist": {
      "title": "Board list type",
      "type": "enum",
      "values": [
        {"value": True, "title": "Blacklist"},
        {"value": False, "title": "Whitelist"},
      ],
      "position": 2000
    },
    "boards": {
      "title": "Board list",
      "type": "list",
      "element": {"title": "Serial number", "type": "string"},
      "position": 2100
    },
    "scaninterval": {"title": "Bus scan interval", "type": "float", "position": 2200},
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 3000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 3100},
    "tempwarning": {"title": "Warning temperature", "type": "int", "position": 4000},
    "tempcritical": {"title": "Critical temperature", "type": "int", "position": 4100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 4200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 4300},
    "warmupstepshares": {"title": "Shares per warmup step", "type": "int", "position": 4400},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 4500},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 5100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 5200},
  })
  
  
  @classmethod
  def autodetect(self, core):
    return  #Disabled in favor of FTDIJTAG module
    try:
      found = False
      try:
        import usb
        for bus in usb.busses():
          for dev in bus.devices:
            if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
              try:
                handle = dev.open()
                manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                product = handle.getString(dev.iProduct, 100).decode("latin1")
                serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner"):
                  try:
                    configuration = dev.configurations[0]
                    interface = configuration.interfaces[0][0]
                    handle.setConfiguration(configuration.value)
                    handle.claimInterface(interface.interfaceNumber)
                    handle.releaseInterface()
                    handle.setConfiguration(0)
                    found = True
                    break
                  except: pass
              except: pass
          if found: break
      except: pass
      if not found:
        try:
          import d2xx
          devices = d2xx.listDevices()
          for devicenum, serial in enumerate(devices):
            try:
              handle = d2xx.open(devicenum)
              handle.close()
              found = True
              break
            except: pass
        except: pass
      if found: core.add_worker(self(core))
    except: pass
    
    
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Check if pyusb is installed
    self.pyusb_available = False
    try:
      import usb
      self.pyusb_available = True
    except: pass
    self.d2xx_available = False
    try:
      import d2xx
      self.d2xx_available = True
    except: pass

    # Initialize bus scanner wakeup event
    self.wakeup = Condition()

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(X6500HotplugWorker, self).__init__(core, state)

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500HotplugWorker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "useftd2xx" in self.settings:
      self.settings.useftd2xx = self.d2xx_available and not self.pyusb_available
    if self.settings.useftd2xx == "false": self.settings.useftd2xx = False
    else: self.settings.useftd2xx = not not self.settings.useftd2xx
    if not "takeover" in self.settings: self.settings.takeover = self.pyusb_available
    if not "uploadfirmware" in self.settings: self.settings.uploadfirmware = True
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/fpgamining/x6500/firmware/x6500.bit"
    if not "blacklist" in self.settings: self.settings.blacklist = True
    if self.settings.blacklist == "false": self.settings.blacklist = False
    else: self.settings.blacklist = not not self.settings.blacklist
    if not "boards" in self.settings: self.settings.boards = []
    if not "initialspeed" in self.settings: self.settings.initialspeed = 150
    self.settings.initialspeed = min(max(self.settings.initialspeed, 4), 250)
    if not "maximumspeed" in self.settings: self.settings.maximumspeed = 200
    self.settings.maximumspeed = min(max(self.settings.maximumspeed, 4), 300)
    if not "tempwarning" in self.settings: self.settings.tempwarning = 45
    self.settings.tempwarning = min(max(self.settings.tempwarning, 0), 60)
    if not "tempcritical" in self.settings: self.settings.tempcritical = 55
    self.settings.tempcritical = min(max(self.settings.tempcritical, 0), 80)
    if not "invalidwarning" in self.settings: self.settings.invalidwarning = 2
    self.settings.invalidwarning = min(max(self.settings.invalidwarning, 1), 10)
    if not "invalidcritical" in self.settings: self.settings.invalidcritical = 10
    self.settings.invalidcritical = min(max(self.settings.invalidcritical, 1), 50)
    if not "warmupstepshares" in self.settings: self.settings.warmupstepshares = 5
    self.settings.warmupstepshares = min(max(self.settings.warmupstepshares, 1), 10000)
    if not "speedupthreshold" in self.settings: self.settings.speedupthreshold = 100
    self.settings.speedupthreshold = min(max(self.settings.speedupthreshold, 50), 10000)
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    if not "scaninterval" in self.settings or not self.settings.scaninterval: self.settings.scaninterval = 10
    # We can't switch the driver on the fly, so trigger a restart if it changed.
    # self.useftd2xx is a cached copy of self.settings.useftd2xx
    if self.started and self.settings.useftd2xx != self.useftd2xx: self.async_restart()
    # Push our settings down to our children
    fields = ["takeover", "uploadfirmware", "firmware", "initialspeed", "maximumspeed", "tempwarning", "tempcritical",
              "invalidwarning", "invalidcritical", "warmupstepshares", "speedupthreshold", "jobinterval", "pollinterval"]
    for child in self.children:
      for field in fields: child.settings[field] = self.settings[field]
      child.apply_settings()
    # Rescan the bus immediately to apply the new settings
    with self.wakeup: self.wakeup.notify()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500HotplugWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.useftd2xx = None


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500HotplugWorker, self)._start()
    # Cache the driver, as we don't like that to change on the fly
    self.useftd2xx = self.settings.useftd2xx
    # Initialize child map
    self.childmap = {}
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500HotplugWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(10)
    # Shut down child workers
    while self.children:
      child = self.children.pop(0)
      try:
        self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
        child.stop()
      except Exception as e:
        self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")

      
  # Main thread entry point
  # This thread is responsible for scanning for boards and spawning worker modules for them
  def main(self):
    # Loop until we are shut down
    while not self.shutdown:
    
      if self.useftd2xx: import d2xx
      if not self.useftd2xx or self.settings.takeover: import usb

      try:
        boards = {}
        if self.useftd2xx:
          devices = d2xx.listDevices()
          for devicenum, serial in enumerate(devices):
            try:
              handle = d2xx.open(devicenum)
              handle.close()
              available = True
            except: availabale = False
            boards[serial] = available
        else:
          for bus in usb.busses():
            for dev in bus.devices:
              if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
                try:
                  handle = dev.open()
                  manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                  product = handle.getString(dev.iProduct, 100).decode("latin1")
                  serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                  if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner"):
                    try:
                      configuration = dev.configurations[0]
                      interface = configuration.interfaces[0][0]
                      handle.setConfiguration(configuration.value)
                      handle.claimInterface(interface.interfaceNumber)
                      handle.releaseInterface()
                      handle.setConfiguration(0)
                      available = True
                    except: available = False
                    boards[serial] = available
                except: pass
                
        for serial in boards.keys():
          if self.settings.blacklist:
            if serial in self.settings.boards: del boards[serial]
          else:
            if serial not in self.settings.boards: del boards[serial]
                
        kill = []
        for serial, child in self.childmap.items():
          if not serial in boards:
            kill.append((serial, child))
            
        for serial, child in kill:
          try:
            self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
            child.stop()
          except Exception as e:
            self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
          childstats = child.get_statistics()
          fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
          for field in fields: self.stats[field] += childstats[field]
          try: self.child.destroy()
          except: pass
          del self.childmap[serial]
          try: self.children.remove(child)
          except: pass
              
        for serial, available in boards.items():
          if serial in self.childmap: continue
          if not available and self.settings.takeover:
            try:
              for bus in usb.busses():
                if available: break
                for dev in bus.devices:
                  if available: break
                  if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
                    handle = dev.open()
                    manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                    product = handle.getString(dev.iProduct, 100).decode("latin1")
                    _serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                    if ((manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner")) and _serial == serial:
                      handle.reset()
                      time.sleep(1)
                      configuration = dev.configurations[0]
                      interface = configuration.interfaces[0][0]
                      handle.setConfiguration(configuration.value)
                      handle.claimInterface(interface.interfaceNumber)
                      handle.releaseInterface()
                      handle.setConfiguration(0)
                      handle.reset()
                      time.sleep(1)
                      available = True
            except: pass
          if available:
            child = X6500Worker(self.core)
            child.settings.name = "X6500 board " + serial
            child.settings.serial = serial
            fields = ["takeover", "useftd2xx", "uploadfirmware", "firmware", "initialspeed", "maximumspeed", "tempwarning", "tempcritical",
                      "invalidwarning", "invalidcritical", "warmupstepshares", "speedupthreshold", "jobinterval", "pollinterval"]
            for field in fields: child.settings[field] = self.settings[field]
            child.apply_settings()
            self.childmap[serial] = child
            self.children.append(child)
            try:
              self.core.log(self, "Starting up worker %s...\n" % (child.settings.name), 800)
              child.start()
            except Exception as e:
              self.core.log(self, "Could not start worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
              
      except: self.core.log(self, "Caught exception: %s\n" % traceback.format_exc(), 100, "rB")
          
      with self.wakeup: self.wakeup.wait(self.settings.scaninterval)

########NEW FILE########
__FILENAME__ = x6500worker
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



###########################################################
# FPGA Mining LLC X6500 FPGA Miner Board interface module #
###########################################################



import time
import struct
import traceback
from multiprocessing import Pipe
from threading import RLock, Condition, Thread
from binascii import hexlify, unhexlify
from core.baseworker import BaseWorker
from core.job import ValidationJob
from .boardproxy import X6500BoardProxy
try: from queue import Queue
except: from Queue import Queue



# Worker main class, referenced from __init__.py
class X6500Worker(BaseWorker):
  
  version = "fpgamining.x6500 worker v0.1.0"
  default_name = "Untitled X6500 worker"
  settings = dict(BaseWorker.settings, **{
    "serial": {"title": "Board serial number", "type": "string", "position": 1000},
    "useftd2xx": {
      "title": "Driver",
      "type": "enum",
      "values": [
        {"value": False, "title": "PyUSB"},
        {"value": True, "title": "D2XX"},
      ],
      "position": 1100
    },
    "takeover": {"title": "Reset board if it appears to be in use", "type": "boolean", "position": 1200},
    "uploadfirmware": {"title": "Force firmware upload", "type": "boolean", "position": 1300},
    "firmware": {"title": "Firmware file location", "type": "string", "position": 1400},
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 2000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 2100},
    "tempwarning": {"title": "Warning temperature", "type": "int", "position": 3000},
    "tempcritical": {"title": "Critical temperature", "type": "int", "position": 3100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 3200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 3300},
    "warmupstepshares": {"title": "Shares per warmup step", "type": "int", "position": 3400},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 3500},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 4100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 4200},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    self.pyusb_available = False
    try:
      import usb
      self.pyusb_available = True
    except: pass
    self.d2xx_available = False
    try:
      import d2xx
      self.d2xx_available = True
    except: pass

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(X6500Worker, self).__init__(core, state)

    # Initialize proxy access locks and wakeup event
    self.lock = RLock()
    self.transactionlock = RLock()
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500Worker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "useftd2xx" in self.settings:
      self.settings.useftd2xx = self.d2xx_available and not self.pyusb_available
    if self.settings.useftd2xx == "false": self.settings.useftd2xx = False
    else: self.settings.useftd2xx = not not self.settings.useftd2xx
    if not "takeover" in self.settings: self.settings.takeover = False
    if not "uploadfirmware" in self.settings: self.settings.uploadfirmware = True
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/fpgamining/x6500/firmware/x6500.bit"
    if not "initialspeed" in self.settings: self.settings.initialspeed = 150
    self.settings.initialspeed = min(max(self.settings.initialspeed, 4), 250)
    if not "maximumspeed" in self.settings: self.settings.maximumspeed = 200
    self.settings.maximumspeed = min(max(self.settings.maximumspeed, 4), 300)
    if not "tempwarning" in self.settings: self.settings.tempwarning = 45
    self.settings.tempwarning = min(max(self.settings.tempwarning, 0), 60)
    if not "tempcritical" in self.settings: self.settings.tempcritical = 55
    self.settings.tempcritical = min(max(self.settings.tempcritical, 0), 80)
    if not "invalidwarning" in self.settings: self.settings.invalidwarning = 2
    self.settings.invalidwarning = min(max(self.settings.invalidwarning, 1), 10)
    if not "invalidcritical" in self.settings: self.settings.invalidcritical = 10
    self.settings.invalidcritical = min(max(self.settings.invalidcritical, 1), 50)
    if not "warmupstepshares" in self.settings: self.settings.warmupstepshares = 5
    self.settings.warmupstepshares = min(max(self.settings.warmupstepshares, 1), 10000)
    if not "speedupthreshold" in self.settings: self.settings.speedupthreshold = 100
    self.settings.speedupthreshold = min(max(self.settings.speedupthreshold, 50), 10000)
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    # We can't switch the device or driver on the fly, so trigger a restart if they changed.
    # self.serial/self.useftd2xx are cached copys of self.settings.serial/self.settings.useftd2xx
    if self.started and (self.settings.serial != self.serial or self.settings.useftd2xx != self.useftd2xx):
      self.async_restart()
    # We need to inform the proxy about a poll interval change
    if self.started and self.settings.pollinterval != self.pollinterval: self._notify_poll_interval_changed()
    for child in self.children: child.apply_settings()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500Worker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.serial = None
    self.useftd2xx = None
    self.pollinterval = None


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500Worker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.serial = self.settings.serial
    self.useftd2xx = self.settings.useftd2xx
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500Worker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Ping the proxy, otherwise the main thread might be blocked and can't wake up.
    try: self._proxy_message("ping")
    except: pass
    # Wait for the main thread to terminate, which in turn kills the child workers.
    self.mainthread.join(10)

      
  # Main thread entry point
  # This thread is responsible for booting the individual FPGAs and spawning worker threads for them
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()
        
        # Check if we have a device serial number
        if not self.serial: raise Exception("Device serial number not set!")
        
        # Try to start the board proxy
        proxy_rxconn, self.txconn = Pipe(False)
        self.rxconn, proxy_txconn = Pipe(False)
        self.pollinterval = self.settings.pollinterval
        self.proxy = X6500BoardProxy(proxy_rxconn, proxy_txconn, self.serial, self.useftd2xx,
                                     self.settings.takeover, self.settings.uploadfirmware,
                                     self.settings.firmware, self.pollinterval)
        self.proxy.daemon = True
        self.proxy.start()
        proxy_txconn.close()
        self.response = None
        self.response_queue = Queue()
        
        # Tell the board proxy to connect to the board
        self._proxy_message("connect")
        
        while not self.shutdown:
          data = self.rxconn.recv()
          if data[0] == "log": self.core.log(self, "Proxy: %s" % data[1], data[2], data[3])
          elif data[0] == "ping": self._proxy_message("pong")
          elif data[0] == "pong": pass
          elif data[0] == "dying": raise Exception("Proxy died!")
          elif data[0] == "response": self.response_queue.put(data[1:])
          elif data[0] == "started_up": self._notify_proxy_started_up(*data[1:])
          elif data[0] == "nonce_found": self._notify_nonce_found(*data[1:])
          elif data[0] == "temperature_read": self._notify_temperature_read(*data[1:])
          else: raise Exception("Proxy sent unknown message: %s" % str(data))
        
        
      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        try:
          for i in range(100): self.response_queue.put(None)
        except: pass
        while self.children:
          try:
            child = self.children.pop(0)
            child.stop()
            childstats = child.get_statistics()
            fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
            for field in fields: self.stats[field] += childstats[field]
            try: self.child.destroy()
            except: pass
          except: pass
        try: self._proxy_message("shutdown")
        except: pass
        try: self.proxy.join(4)
        except: pass
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)

        
  def _proxy_message(self, *args):
    with self.lock:
      self.txconn.send(args)


  def _proxy_transaction(self, *args):
    with self.transactionlock:
      with self.lock:
        self.txconn.send(args)
      return self.response_queue.get()
      
      
  def _notify_poll_interval_changed(self):
    self.pollinterval = self.settings.pollinterval
    try: self._proxy_message("set_pollinterval", self.pollinterval)
    except: pass
    
    
  def _notify_proxy_started_up(self, fpga0version, fpga1version):
    # The proxy is up and running, start up child workers
    self.children = [X6500FPGA(self.core, self, 0, fpga0version),
                     X6500FPGA(self.core, self, 1, fpga1version)]
    for child in self.children: child.start()

    
  def _notify_nonce_found(self, fpga, now, nonce):
    if self.children and fpga < len(self.children):
      try: self.children[fpga].notify_nonce_found(now, nonce)
      except Exception as e: self.children[fpga].error = e


  def _notify_temperature_read(self, fpga0, fpga1):
    if self.children:
      self.children[0].stats.temperature = fpga0
      self.children[1].stats.temperature = fpga1
      if fpga0: self.core.event(350, self.children[0], "temperature", fpga0 * 1000, "%f \xc2\xb0C" % fpga0, worker = self.children[0])
      if fpga1: self.core.event(350, self.children[1], "temperature", fpga1 * 1000, "%f \xc2\xb0C" % fpga1, worker = self.children[1])

      
  def send_job(self, fpga, job):
    return self._proxy_transaction("send_job", fpga, job.midstate + job.data[64:76])


  def clear_queue(self, fpga):
    self._proxy_message("clear_queue", fpga)


  def shutdown_fpga(self, fpga):
    self._proxy_message("shutdown_fpga", fpga)


  def set_speed(self, fpga, speed):
    self._proxy_message("set_speed", fpga, speed)


  def get_speed(self, fpga):
    return self._proxy_transaction("get_speed", fpga)[0]



# FPGA handler main class, child worker of X6500Worker
class X6500FPGA(BaseWorker):

  # Constructor, gets passed a reference to the miner core, the X6500Worker,
  # its FPGA id, and the bitstream version currently running on that FPGA
  def __init__(self, core, parent, fpga, bitstreamversion):
    self.parent = parent
    self.fpga = fpga
    self.firmware_rev = bitstreamversion

    # Let our superclass do some basic initialization
    super(X6500FPGA, self).__init__(core, None)
    
    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()


    
  # Validate settings, mostly coping them from our parent
  # Called from the constructor and after every settings change on the parent.
  def apply_settings(self):
    self.settings.name = "%s FPGA%d" % (self.parent.settings.name, self.fpga)
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self).apply_settings()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self)._reset()
    self.stats.temperature = None
    self.stats.speed = None
    self.initialramp = True


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self)._start()
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.parent.settings.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(2)

      
  # This function should interrupt processing of the specified job if possible.
  # This is necesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast. We don't care whether it's a
  # graceful cancellation for this module because the work upload overhead is low. 
  def notify_canceled(self, job, graceful):
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.wakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.wakeup.notify()

        
  # Report custom statistics.
  def _get_statistics(self, stats, childstats):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self)._get_statistics(stats, childstats)
    stats.temperature = self.stats.temperature


  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()

        # Initialize megahashes per second to zero, will be measured later.
        self.stats.mhps = 0

        # Job that the device is currently working on, or that is currently being uploaded.
        # This variable is used by BaseWorker to figure out the current work source for statistics.
        self.job = None
        # Job that was previously being procesed. Has been destroyed, but there might be some late nonces.
        self.oldjob = None

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Eat up leftover wakeups
        self.wakeup.wait(0)
        # Honor shutdown flag (in case it was a real wakeup)
        if self.shutdown: break
        # Set validation success flag to false
        self.checksuccess = False
        # Set validation job second iteration flag to false
        self.seconditeration = False
        
        # Initialize hash rate tracking data
        self.lasttime = None
        self.lastnonce = None

        # Initialize malfunction tracking data
        self.recentshares = 0
        self.recentinvalid = 0

        # Configure core clock, if the bitstream supports that
        if self.firmware_rev > 0: self._set_speed(self.parent.settings.initialspeed)
        
        # Clear FPGA's nonce queue
        self.parent.clear_queue(self.fpga)

        # Send validation job to device
        job = ValidationJob(self.core, unhexlify(b"00000001c3bf95208a646ee98a58cf97c3a0c4b7bf5de4c89ca04495000005200000000024d1fff8d5d73ae11140e4e48032cd88ee01d48c67147f9a09cd41fdec2e25824f5c038d1a0b350c5eb01f04"))
        self._sendjob(job)

        # Wait for the validation job to complete. The wakeup flag will be set by the listener
        # thread when the validation job completes. 180 seconds should be sufficient for devices
        # down to about 50MH/s, for slower devices this timeout will need to be increased.
        if self.stats.speed: self.wakeup.wait((2**32 / 1000000. / self.stats.speed) * 1.1)
        else: self.wakeup.wait(180)
        # Honor shutdown flag
        if self.shutdown: break
        # We woke up, but the validation job hasn't succeeded in the mean time.
        # This usually means that the wakeup timeout has expired.
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")
        # self.stats.mhps has now been populated by the listener thread
        self.core.log(self, "Running at %f MH/s\n" % self.stats.mhps, 300, "B")
        self._update_job_interval()

        # Main loop, continues until something goes wrong or we're shutting down.
        while not self.shutdown:

          # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
          # Blocks until one is available. Because of this we need to release the
          # wakeup lock temporarily in order to avoid possible deadlocks.
          self.wakeup.release()
          job = self.core.get_job(self, self.jobinterval + 2)
          self.wakeup.acquire()
          
          # If a new block was found while we were fetching that job, just discard it and get a new one.
          if job.canceled:
            job.destroy()
            continue

          # Upload the job to the device
          self._sendjob(job)
          
          # Go through the safety checks and reduce the clock if necessary
          self.safetycheck()
          
          # If the job was already caught by a long poll while we were uploading it,
          # jump back to the beginning of the main loop in order to immediately fetch new work.
          # Don't check for the canceled flag before the job was accepted by the device,
          # otherwise we might get out of sync.
          if self.job.canceled: continue
          # Wait while the device is processing the job. If nonces are sent by the device, they
          # will be processed by the listener thread. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        try: self.wakeup.release()
        except: pass
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, restart the parent worker as well.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5:
              self.parent.async_restart()
              return
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  def notify_nonce_found(self, now, nonce):
    # Snapshot the current jobs to avoid race conditions
    oldjob = self.oldjob
    newjob = self.job
    # If there is no job, this must be a leftover from somewhere, e.g. previous invocation
    # or reiterating the keyspace because we couldn't provide new work fast enough.
    # In both cases we can't make any use of that nonce, so just discard it.
    if not oldjob and not newjob: return
    # Pass the nonce that we found to the work source, if there is one.
    # Do this before calculating the hash rate as it is latency critical.
    job = None
    if newjob:
      if newjob.nonce_found(nonce, oldjob): job = newjob
    if not job and oldjob:
      if oldjob.nonce_found(nonce): job = oldjob
    self.recentshares += 1
    if not job: self.recentinvalid += 1
    nonceval = struct.unpack("<I", nonce)[0]
    if isinstance(newjob, ValidationJob):
      # This is a validation job. Validate that the nonce is correct, and complain if not.
      if newjob.nonce != nonce:
        raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (hexlify(nonce).decode("ascii"), hexlify(newjob.nonce).decode("ascii")))
      else:
        # The nonce was correct
        if self.firmware_rev > 0:
          # The FPGA is running overclocker firmware, so we don't need to use this method to calculate the hashrate.
          # In fact, it will not work because the FPGA will go to sleep after working through all possible nonces.
          with self.wakeup:
            self.checksuccess = True
            self.wakeup.notify()
        else:
          if self.seconditeration == True:
            with self.wakeup:
              # This is the second iteration. We now know the actual nonce rotation time.
              delta = (now - newjob.starttime)
              # Calculate the hash rate based on the nonce rotation time.
              self.stats.mhps = 2**32 / 1000000. / delta
              # Update hash rate tracking information
              self.lasttime = now
              self.lastnonce = nonceval
              # Wake up the main thread
              self.checksuccess = True
              self.wakeup.notify()
          else:
            with self.wakeup:
              # This was the first iteration. Wait for another one to figure out nonce rotation time.
              newjob.starttime = now
              self.seconditeration = True
    else:
      if self.firmware_rev == 0:
        # Adjust hash rate tracking
        delta = (now - self.lasttime)
        estimatednonce = int(round(self.lastnonce + self.stats.mhps * 1000000 * delta))
        noncediff = nonceval - (estimatednonce & 0xffffffff)
        if noncediff < -0x80000000: noncediff = noncediff + 0x100000000
        elif noncediff > 0x7fffffff: noncediff = noncediff - 0x100000000
        estimatednonce = estimatednonce + noncediff
        # Calculate the hash rate based on adjusted tracking information
        currentmhps = (estimatednonce - self.lastnonce) / 1000000. / delta
        weight = min(0.5, delta / 100.)
        self.stats.mhps = (1 - weight) * self.stats.mhps + weight * currentmhps
        # Update hash rate tracking information
        self.lasttime = now
        self.lastnonce = nonceval
      

  # This function uploads a job to the device
  def _sendjob(self, job):
    # Move previous job to oldjob, and new one to job
    self.oldjob = self.job
    self.job = job
    # Send it to the FPGA
    start, now = self.parent.send_job(self.fpga, job)
    # Calculate how long the old job was running
    if self.oldjob:
      if self.oldjob.starttime:
        self.oldjob.hashes_processed((now - self.oldjob.starttime) * self.stats.mhps * 1000000)
      self.oldjob.destroy()
    self.job.starttime = now

    
  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job != None:
      if self.job.starttime:
        self.job.hashes_processed((now - self.job.starttime) * self.stats.mhps * 1000000)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.oldjob = self.job
      self.job.destroy()
      self.job = None
  
  
  # Check the invalid rate and temperature, and reduce the FPGA clock if these exceed safe values
  def safetycheck(self):
    
    warning = False
    critical = False
    if self.recentinvalid >= self.parent.settings.invalidwarning: warning = True
    if self.recentinvalid >= self.parent.settings.invalidcritical: critical = True
    if self.stats.temperature:
      if self.stats.temperature > self.parent.settings.tempwarning: warning = True    
      if self.stats.temperature > self.parent.settings.tempcritical: critical = True    

    threshold = self.parent.settings.warmupstepshares if self.initialramp and not self.recentinvalid else self.parent.settings.speedupthreshold

    if warning: self.core.log(self, "Detected overload condition!\n", 200, "y")
    if critical: self.core.log(self, "Detected CRITICAL condition!\n", 100, "rB")

    if critical:
      speedstep = -20
      self.initialramp = False
    elif warning:
      speedstep = -2
      self.initialramp = False
    elif not self.recentinvalid and self.recentshares >= threshold:
      speedstep = 2
    else: speedstep = 0    

    if self.firmware_rev > 0:
      if speedstep: self._set_speed(self.stats.speed + speedstep)
    elif warning or critical:
      self.core.log(self, "Firmware too old, can not automatically reduce clock!\n", 200, "yB")
      if critical:
        self.core.log(self, "Shutting down FPGA to protect it!\n", 100, "rB")
        self.parent.shutdown_fpga(self.fpga)
        self.async_stop(2)

    if speedstep or self.recentshares >= threshold:
      self.recentinvalid = 0
      self.recentshares = 0
    
   
  def _set_speed(self, speed):
    speed = min(max(speed, 4), self.parent.settings.maximumspeed)
    if self.stats.speed == speed: return
    if speed == self.parent.settings.maximumspeed: self.initialramp = False
    self.core.log(self, "%s: Setting clock speed to %.2f MHz...\n" % ("Warmup" if self.initialramp else "Tracking", speed), 500, "B")
    self.parent.set_speed(self.fpga, speed)
    self.stats.speed = self.parent.get_speed(self.fpga)
    self.stats.mhps = self.stats.speed
    self._update_job_interval()
    if self.stats.speed != speed:
      self.core.log(self, "Setting clock speed failed!\n", 100, "rB")
   
   
  def _update_job_interval(self):
    self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, self)
    # Calculate the time that the device will need to process 2**32 nonces.
    # This is limited at 60 seconds in order to have some regular communication,
    # even with very slow devices (and e.g. detect if the device was unplugged).
    interval = min(60, 2**32 / 1000000. / self.stats.mhps)
    # Add some safety margin and take user's interval setting (if present) into account.
    self.jobinterval = min(self.parent.settings.jobinterval, max(0.5, interval * 0.8 - 1))
    self.core.log(self, "Job interval: %f seconds\n" % self.jobinterval, 400, "B")
    # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
    self.jobs_per_second = 1. / self.jobinterval
    self.core.notify_speed_changed(self)
  
########NEW FILE########
__FILENAME__ = logfilelogger
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##########################
# Simple log file logger #
##########################



import os
from threading import RLock
from core.basefrontend import BaseFrontend



class LogFileLogger(BaseFrontend):

  version = "theseven.basicloggers log file logger v0.1.0"
  default_name = "Untitled log file logger"
  can_log = True
  can_autodetect = False
  settings = dict(BaseFrontend.settings, **{
    "filename": {"title": "Log file name", "type": "string", "position": 1000},
    "loglevel": {"title": "Log level", "type": "int", "position": 2000},
    "useansi": {"title": "Use ANSI codes", "type": "boolean", "position": 3000},
  })


  def __init__(self, core, state = None):
    super(LogFileLogger, self).__init__(core, state)
    
    
  def apply_settings(self):
    super(LogFileLogger, self).apply_settings()
    if not "filename" in self.settings or not self.settings.filename: self.settings.filename = "mpbm.log"
    if not "loglevel" in self.settings: self.settings.loglevel = self.core.default_loglevel
    if not "useansi" in self.settings: self.settings.useansi = False
    if self.started and self.settings.filename != self.filename: self.async_restart()
    
  
  def _start(self):
    super(LogFileLogger, self)._start()
    self.filename = self.settings.filename
    self.handle = open(self.filename, "ab")
    self.handle.write(("\n" + "=" * 200 + "\n\n").encode("utf_8"))
  
  
  def _stop(self):
    self.handle.close()
    super(LogFileLogger, self)._stop()

      
  def write_log_message(self, source, timestamp, loglevel, messages):
    if not self.started: return
    if loglevel > self.settings.loglevel: return
    prefix = "%s [%3d] %s: " % (timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"), loglevel, source.settings.name)
    newline = True
    for message, format in messages:
      for line in message.splitlines(True):
        if self.settings.useansi:
          modes = ""
          if "r" in format: modes += ";31"
          elif "y" in format: modes += ";33"
          elif "g" in format: modes += ";32"
          if "B" in format: modes += ";1"
          if modes: line = "\x1b[0%sm%s\x1b[0m" % (modes, line)
        self.handle.write((prefix + line if newline else line).encode("utf_8"))
        newline = line[-1:] == "\n"
    
########NEW FILE########
__FILENAME__ = stderrlogger
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



########################
# Simple stderr logger #
########################



import os
from threading import RLock
from core.basefrontend import BaseFrontend



class StderrLogger(BaseFrontend):

  version = "theseven.basicloggers stderr logger v0.1.0"
  default_name = "stderr logger"
  can_log = True
  can_autodetect = True
  settings = dict(BaseFrontend.settings, **{
    "loglevel": {"title": "Log level", "type": "int", "position": 1000},
    "useansi": {"title": "Use ANSI codes", "type": "boolean", "position": 2000},
  })


  @classmethod
  def autodetect(self, core):
    core.add_frontend(self(core))
    
    
  def __init__(self, core, state = None):
    super(StderrLogger, self).__init__(core, state)
    
    
  def apply_settings(self):
    super(StderrLogger, self).apply_settings()
    if not "loglevel" in self.settings: self.settings.loglevel = self.core.default_loglevel
    if not "useansi" in self.settings: self.settings.useansi = "TERM" in os.environ
    
  
  def _start(self):
    super(StderrLogger, self)._start()

    # Clear screen
    if self.settings.useansi: self.core.stderr.write("\x1b[2J")
    else: self.core.stderr.write("\n" * 100)
  
  
  def write_log_message(self, source, timestamp, loglevel, messages):
    if not self.started: return
    if loglevel > self.settings.loglevel: return
    prefix = "%s [%3d] %s: " % (timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"), loglevel, source.settings.name)
    newline = True
    for message, format in messages:
      for line in message.splitlines(True):
        if self.settings.useansi:
          modes = ""
          if "r" in format: modes += ";31"
          elif "y" in format: modes += ";33"
          elif "g" in format: modes += ";32"
          if "B" in format: modes += ";1"
          if modes: line = "\x1b[0%sm%s\x1b[0m" % (modes, line)
        self.core.stderr.write(prefix + line if newline else line)
        newline = line[-1:] == "\n"
    
########NEW FILE########
__FILENAME__ = bcjsonrpcworksource
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#######################################
# Bitcoin JSON RPC work source module #
#######################################



import time
import json
import struct
import base64
import traceback
from binascii import hexlify, unhexlify
from threading import Thread, RLock, Condition
from core.actualworksource import ActualWorkSource
from core.job import Job
try: from queue import Queue
except: from Queue import Queue
try: import http.client as http_client
except ImportError: import httplib as http_client



class BCJSONRPCWorkSource(ActualWorkSource):
  
  version = "theseven.bcjsonrpc work source v0.1.0"
  default_name = "Untitled BCJSONRPC work source"
  settings = dict(ActualWorkSource.settings, **{
    "getworktimeout": {"title": "Getwork timeout", "type": "float", "position": 19000},
    "sendsharetimeout": {"title": "Sendshare timeout", "type": "float", "position": 19100},
    "longpolltimeout": {"title": "Long poll connect timeout", "type": "float", "position": 19200},
    "longpollresponsetimeout": {"title": "Long poll response timeout", "type": "float", "position": 19200},
    "host": {"title": "Host", "type": "string", "position": 1000},
    "port": {"title": "Port", "type": "int", "position": 1010},
    "path": {"title": "Path", "type": "string", "position": 1020},
    "username": {"title": "User name", "type": "string", "position": 1100},
    "password": {"title": "Password", "type": "password", "position": 1120},
    "useragent": {"title": "User agent string", "type": "string", "position": 1200},
    "getworkconnections": {"title": "Job fetching connnections", "type": "int", "position": 1300},
    "uploadconnections": {"title": "Share upload connnections", "type": "int", "position": 1400},
    "longpollconnections": {"title": "Long poll connnections", "type": "int", "position": 1500},
    "expirymargin": {"title": "Job expiry safety margin", "type": "int", "position": 1600},
  })
  

  def __init__(self, core, state = None):
    self.fetcherlock = Condition()
    self.fetcherthreads = []
    self.fetchersrunning = 0
    self.fetcherspending = 0
    self.fetcherjobsrunning = 0
    self.fetcherjobspending = 0
    self.uploadqueue = Queue()
    self.uploaderthreads = []
    super(BCJSONRPCWorkSource, self).__init__(core, state)
    self.extensions = "longpoll midstate rollntime"
    self.runcycle = 0
    
    
  def apply_settings(self):
    super(BCJSONRPCWorkSource, self).apply_settings()
    if not "getworktimeout" in self.settings or not self.settings.getworktimeout:
      self.settings.getworktimeout = 3
    if not "sendsharetimeout" in self.settings or not self.settings.sendsharetimeout:
      self.settings.sendsharetimeout = 5
    if not "longpolltimeout" in self.settings or not self.settings.longpolltimeout:
      self.settings.longpolltimeout = 10
    if not "longpollresponsetimeout" in self.settings or not self.settings.longpollresponsetimeout:
      self.settings.longpollresponsetimeout = 1800
    if not "host" in self.settings: self.settings.host = ""
    if self.started and self.settings.host != self.host: self.async_restart()
    if not "port" in self.settings or not self.settings.port: self.settings.port = 8332
    if self.started and self.settings.port != self.port: self.async_restart()
    if not "path" in self.settings or not self.settings.path:
      self.settings.path = "/"
    if not "username" in self.settings: self.settings.username = ""
    if not "password" in self.settings: self.settings.password = ""
    if not self.settings.username and not self.settings.password: self.auth = None
    else:
      credentials = self.settings.username + ":" + self.settings.password
      self.auth = "Basic " + base64.b64encode(credentials.encode("utf_8")).decode("ascii")
    if not "useragent" in self.settings: self.settings.useragent = ""
    if self.settings.useragent: self.useragent = self.settings.useragent
    else: self.useragent = "%s (%s)" % (self.core.__class__.version, self.__class__.version)
    if not "getworkconnections" in self.settings: self.settings.getworkconnections = 1
    if self.started and self.settings.getworkconnections != self.getworkconnections: self.async_restart()
    if not "uploadconnections" in self.settings: self.settings.uploadconnections = 1
    if self.started and self.settings.uploadconnections != self.uploadconnections: self.async_restart()
    if not "longpollconnections" in self.settings: self.settings.longpollconnections = 1
    if self.started and self.settings.longpollconnections != self.longpollconnections: self.async_restart()
    if not "expirymargin" in self.settings: self.settings.expirymargin = 5

    
  def _reset(self):
    super(BCJSONRPCWorkSource, self)._reset()
    self.stats.supports_rollntime = None
    self.longpollurl = None
    self.fetchersrunning = 0
    self.fetcherspending = 0
    self.fetcherjobsrunning = 0
    self.fetcherjobspending = 0
    self.fetcherthreads = []
    self.uploadqueue = Queue()
    self.uploaderthreads = []
    self.lastidentifier = None
    self.jobepoch = 0
    self.lpepoch = 0
    
    
  def _start(self):
    super(BCJSONRPCWorkSource, self)._start()
    self.host = self.settings.host
    self.port = self.settings.port
    self.getworkconnections = self.settings.getworkconnections
    self.uploadconnections = self.settings.uploadconnections
    self.longpollconnections = self.settings.longpollconnections
    if not self.settings.host or not self.settings.port: return
    self.shutdown = False
    for i in range(self.getworkconnections):
      thread = Thread(None, self.fetcher, "%s_fetcher_%d" % (self.settings.name, i))
      thread.daemon = True
      thread.start()
      self.fetcherthreads.append(thread)
    for i in range(self.uploadconnections):
      thread = Thread(None, self.uploader, "%s_uploader_%d" % (self.settings.name, i))
      thread.daemon = True
      thread.start()
      self.uploaderthreads.append(thread)
    
    
  def _stop(self):
    self.runcycle += 1
    self.shutdown = True
    with self.fetcherlock: self.fetcherlock.notify_all()
    for thread in self.fetcherthreads: thread.join(1)
    for i in self.uploaderthreads: self.uploadqueue.put(None)
    for thread in self.uploaderthreads: thread.join(1)
    super(BCJSONRPCWorkSource, self)._stop()
    
    
  def _get_statistics(self, stats, childstats):
    super(BCJSONRPCWorkSource, self)._get_statistics(stats, childstats)
    stats.supports_rollntime = self.stats.supports_rollntime
    
  
  def _get_running_fetcher_count(self):
    return self.fetchersrunning, self.fetcherjobsrunning + self.fetcherjobspending
  
  
  def _start_fetcher(self):
    count = len(self.fetcherthreads)
    if not count: return False, 0
    with self.fetcherlock:
      if self.fetchersrunning >= count: return 0, 0
      self.fetcherjobspending += self.estimated_jobs
      self.fetchersrunning += 1
      self.fetcherspending += 1
      self.fetcherlock.notify()
    return 1, self.estimated_jobs


  def fetcher(self):
    conn = None
    while not self.shutdown:
      with self.fetcherlock:
        while not self.fetcherspending:
          self.fetcherlock.wait()
          if self.shutdown: return
        self.fetcherspending -= 1
        myjobs = self.estimated_jobs
        self.fetcherjobsrunning += myjobs
        self.fetcherjobspending -= myjobs
        if not self.fetcherspending or self.fetcherjobspending < 0: self.fetcherjobspending = 0
      jobs = None
      try:
        req = json.dumps({"method": "getwork", "params": [], "id": 0}).encode("utf_8")
        headers = {"User-Agent": self.useragent, "X-Mining-Extensions": self.extensions,
                   "Content-Type": "application/json", "Content-Length": len(req), "Connection": "Keep-Alive"}
        if self.auth != None: headers["Authorization"] = self.auth
        try:
          if conn:
            try:
              epoch = self.jobepoch
              now = time.time()
              conn.request("POST", self.settings.path, req, headers)
              conn.sock.settimeout(self.settings.getworktimeout)
              response = conn.getresponse()
            except:
              conn = None
              self.core.log(self, "Keep-alive job fetching connection died\n", 500)
          if not conn:
            conn = http_client.HTTPConnection(self.settings.host, self.settings.port, True, self.settings.getworktimeout)
            epoch = self.jobepoch
            now = time.time()
            conn.request("POST", self.settings.path, req, headers)
            conn.sock.settimeout(self.settings.getworktimeout)
            response = conn.getresponse()
          data = response.read()
        except:
          conn = None
          raise
        with self.statelock:
          if not self.settings.longpollconnections: self.signals_new_block = False
          else:
            lpfound = False
            headers = response.getheaders()
            for h in headers:
              if h[0].lower() == "x-long-polling":
                lpfound = True
                url = h[1]
                if url == self.longpollurl: break
                self.longpollurl = url
                try:
                  if url[0] == "/": url = "http://" + self.settings.host + ":" + str(self.settings.port) + url
                  if url[:7] != "http://": raise Exception("Long poll URL isn't HTTP!")
                  parts = url[7:].split("/", 1)
                  if len(parts) == 2: path = "/" + parts[1]
                  else: path = "/"
                  parts = parts[0].split(":")
                  if len(parts) != 2: raise Exception("Long poll URL contains host but no port!")
                  host = parts[0]
                  port = int(parts[1])
                  self.core.log(self, "Found long polling URL: %s\n" % (url), 500, "g")
                  self.signals_new_block = True
                  self.runcycle += 1
                  for i in range(self.settings.longpollconnections):
                    thread = Thread(None, self._longpollingworker, "%s_longpolling_%d" % (self.settings.name, i), (host, port, path))
                    thread.daemon = True
                    thread.start()
                except Exception as e:
                  self.core.log(self, "Invalid long polling URL: %s (%s)\n" % (url, str(e)), 200, "y")
                break
            if self.signals_new_block and not lpfound:
              self.runcycle += 1
              self.signals_new_block = False
        jobs = self._build_jobs(response, data, epoch, now, "getwork")
      except:
        self.core.log(self, "Error while fetching job: %s\n" % (traceback.format_exc()), 200, "y")
        self._handle_error()
      finally:
        with self.fetcherlock:
          self.fetchersrunning -= 1
          self.fetcherjobsrunning -= myjobs
      if jobs:
        self._push_jobs(jobs, "getwork response")
        
        
  def nonce_found(self, job, data, nonce, noncediff):
    self.uploadqueue.put((job, data, nonce, noncediff))
      
      
  def uploader(self):
    conn = None
    while not self.shutdown:
      share = self.uploadqueue.get()
      if not share: continue
      job, data, nonce, noncediff = share
      tries = 0
      while True:
        try:
          req = json.dumps({"method": "getwork", "params": [hexlify(data).decode("ascii")], "id": 0}).encode("utf_8")
          headers = {"User-Agent": self.useragent, "X-Mining-Extensions": self.extensions,
                     "Content-Type": "application/json", "Content-Length": len(req)}
          if self.auth != None: headers["Authorization"] = self.auth
          try:
            if conn:
              try:
                conn.request("POST", self.settings.path, req, headers)
                response = conn.getresponse()
              except:
                conn = None
                self.core.log(self, "Keep-alive share upload connection died\n", 500)
            if not conn:
              conn = http_client.HTTPConnection(self.settings.host, self.settings.port, True, self.settings.sendsharetimeout)
              conn.request("POST", self.settings.path, req, headers)
              response = conn.getresponse()
            rdata = response.read()
          except:
            conn = None
            raise
          rdata = json.loads(rdata.decode("utf_8"))
          result = False
          if rdata["result"] == True: result = True
          elif rdata["error"] != None: result =  rdata["error"]
          else:
            headers = response.getheaders()
            for h in headers:
              if h[0].lower() == "x-reject-reason":
                result = h[1]
                break
          if result is not True:
            self.jobepoch += 1
            self._cancel_jobs(True)
          self._handle_success()
          job.nonce_handled_callback(nonce, noncediff, result)
          break
        except:
          self.core.log(self, "Error while sending share %s (difficulty %.5f): %s\n" % (hexlify(nonce).decode("ascii"), noncediff, traceback.format_exc()), 200, "y")
          tries += 1
          self._handle_error(True)
          time.sleep(min(30, tries))


  def _longpollingworker(self, host, port, path):
    runcycle = self.runcycle
    tries = 0
    starttime = time.time()
    conn = None
    while True:
      if self.runcycle > runcycle: return
      try:
        headers = {"User-Agent": self.useragent, "X-Mining-Extensions": self.extensions, "Connection": "Keep-Alive"}
        if self.auth != None: headers["Authorization"] = self.auth
        if conn:
          try:
            if conn.sock: conn.sock.settimeout(self.settings.longpolltimeout)
            epoch = self.lpepoch + 1
            conn.request("GET", path, None, headers)
            conn.sock.settimeout(self.settings.longpollresponsetimeout)
            response = conn.getresponse()
          except:
            conn = None
            self.core.log(self, "Keep-alive long poll connection died\n", 500)
        if not conn:
          conn = http_client.HTTPConnection(host, port, True, self.settings.longpolltimeout)
          epoch = self.lpepoch + 1
          conn.request("GET", path, None, headers)
          conn.sock.settimeout(self.settings.longpollresponsetimeout)
          response = conn.getresponse()
        if self.runcycle > runcycle: return
        if epoch > self.lpepoch:
          self.lpepoch = epoch
          self.jobepoch += 1
          self._cancel_jobs(True)
        data = response.read()
        jobs = self._build_jobs(response, data, self.jobepoch, time.time() - 1, "long poll", True, True)
        if not jobs: continue
        self._push_jobs(jobs, "long poll response")
      except:
        conn = None
        self.core.log(self, "Long poll failed: %s\n" % (traceback.format_exc()), 200, "y")
        tries += 1
        if time.time() - starttime >= 60: tries = 0
        if tries > 5: time.sleep(30)
        else: time.sleep(1)
        starttime = time.time()
        
        
  def _build_jobs(self, response, data, epoch, now, source, ignoreempty = False, discardiffull = False):
    decoded = data.decode("utf_8")
    if len(decoded) == 0 and ignoreempty:
      self.core.log(self, "Got empty %s response\n" % source, 500)
      return
    decoded = json.loads(decoded)
    data = unhexlify(decoded["result"]["data"].encode("ascii"))
    target = unhexlify(decoded["result"]["target"].encode("ascii"))
    try: identifier = int(decoded["result"]["identifier"])
    except: identifier = None
    if identifier != self.lastidentifier:
      self._cancel_jobs()
      self.lastidentifier = identifier
    self.blockchain.check_job(Job(self.core, self, 0, data, target, True, identifier))
    roll_ntime = 1
    expiry = 60
    isp2pool = False
    headers = response.getheaders()
    for h in headers:
      if h[0].lower() == "x-is-p2pool" and h[1].lower() == "true": isp2pool = True
      elif h[0].lower() == "x-roll-ntime" and h[1] and h[1].lower() != "n":
        roll_ntime = 60
        parts = h[1].split("=", 1)
        if parts[0].strip().lower() == "expire":
          try: roll_ntime = int(parts[1])
          except: pass
        expiry = roll_ntime
    if isp2pool: expiry = 60
    self.stats.supports_rollntime = roll_ntime > 1
    if epoch != self.jobepoch:
      self.core.log(self, "Discarding %d jobs from %s response because request was issued before flush\n" % (roll_ntime, source), 500)
      with self.stats.lock: self.stats.jobsreceived += roll_ntime
      return
    if self.core.workqueue.count > self.core.workqueue.target * (1 if discardiffull else 5):
      self.core.log(self, "Discarding %d jobs from %s response because work buffer is full\n" % (roll_ntime, source), 500)
      with self.stats.lock: self.stats.jobsreceived += roll_ntime
      return
    expiry += now - self.settings.expirymargin
    midstate = Job.calculate_midstate(data)
    prefix = data[:68]
    timebase = struct.unpack(">I", data[68:72])[0]
    suffix = data[72:]
    return [Job(self.core, self, expiry, prefix + struct.pack(">I", timebase + i) + suffix, target, midstate, identifier) for i in range(roll_ntime)]
  
########NEW FILE########
__FILENAME__ = bflsinglehotplug
# Modular Python Bitcoin Miner
# Copyright (C) 2011-2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#################################################################
# Butterfly Labs Inc. BitFORCE Single hotplug controller module #
#################################################################



import traceback
from glob import glob
from threading import Condition, Thread
from core.baseworker import BaseWorker
from .bflsingleworker import BFLSingleWorker



# Worker main class, referenced from __init__.py
class BFLSingleHotplugWorker(BaseWorker):

  version = "theseven.bflsingle hotplug manager v0.1.0"
  default_name = "BFL Single hotplug manager"
  can_autodetect = True
  settings = dict(BaseWorker.settings, **{
    "scaninterval": {"title": "Bus scan interval", "type": "float", "position": 2200},
  })


  @classmethod
  def autodetect(self, core):
    try:
      import serial
      found = False
      for port in glob("/dev/serial/by-id/usb-Butterfly_Labs_Inc._BitFORCE_SHA256-*"):
        try:
          handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
          handle.close()
          found = True
          break
        except: pass
      if found: core.add_worker(self(core))
    except: pass


  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Initialize bus scanner wakeup event
    self.wakeup = Condition()

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(BFLSingleHotplugWorker, self).__init__(core, state)


  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleHotplugWorker, self).apply_settings()
    if not "scaninterval" in self.settings or not self.settings.scaninterval: self.settings.scaninterval = 10
    # Rescan the bus immediately to apply the new settings
    with self.wakeup: self.wakeup.notify()


  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleHotplugWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleHotplugWorker, self)._start()
    # Initialize child map
    self.childmap = {}
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()


  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleHotplugWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(10)
    # Shut down child workers
    while self.children:
      child = self.children.pop(0)
      try:
        self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
        child.stop()
      except Exception as e:
        self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")


  # Main thread entry point
  # This thread is responsible for scanning for boards and spawning worker modules for them
  def main(self):
    import serial
    number = 0

    # Loop until we are shut down
    while not self.shutdown:

      try:
        boards = {}
        for port in glob("/dev/serial/by-id/usb-Butterfly_Labs_Inc._BitFORCE_SHA256-*"):
          available = False
          try:
            handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
            handle.close()
            available = True
          except: pass
          boards[port] = available

        kill = []
        for port, child in self.childmap.items():
          if not port in boards:
            kill.append((port, child))

        for port, child in kill:
          try:
            self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
            child.stop()
          except Exception as e:
            self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
          childstats = child.get_statistics()
          fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
          for field in fields: self.stats[field] += childstats[field]
          try: self.child.destroy()
          except: pass
          del self.childmap[port]
          try: self.children.remove(child)
          except: pass

        for port, available in boards.items():
          if port in self.childmap or not available: continue
          number += 1
          child = BFLSingleWorker(self.core)
          child.settings.name = "Autodetected BFL Single %d" % number
          child.settings.port = port
          child.apply_settings()
          self.childmap[port] = child
          self.children.append(child)
          try:
            self.core.log(self, "Starting up worker %s...\n" % (child.settings.name), 800)
            child.start()
          except Exception as e:
            self.core.log(self, "Could not start worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")

      except: self.core.log(self, "Caught exception: %s\n" % traceback.format_exc(), 100, "rB")

      with self.wakeup: self.wakeup.wait(self.settings.scaninterval)

########NEW FILE########
__FILENAME__ = bflsingleworker
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



###############################################################
# Butterfly Labs Inc. BitFORCE Single worker interface module #
###############################################################



import time
import traceback
from threading import Condition, Thread
from binascii import unhexlify
from core.baseworker import BaseWorker



# Worker main class, referenced from __init__.py
class BFLSingleWorker(BaseWorker):
  
  version = "theseven.bflsingle worker v0.1.0"
  default_name = "Untitled BFL Single worker"
  settings = dict(BaseWorker.settings, **{
    "port": {"title": "Port", "type": "string", "position": 1000},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(BFLSingleWorker, self).__init__(core, state)

    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self).apply_settings()
    # Pretty much self-explanatory...
    if not "port" in self.settings or not self.settings.port: self.settings.port = "/dev/ttyUSB0"
    # We can't change the port name on the fly, so trigger a restart if they changed.
    # self.port is a cached copy of self.settings.port.
    if self.started and self.settings.port != self.port: self.async_restart()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.port = None
    self.stats.temperature = 0


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.port = self.settings.port
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobinterval = 2**32 / 800000000.
    self.jobs_per_second = 1 / self.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(10)

      
  # This function should interrupt processing of the specified job if possible.
  # This is neccesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast. Canceling a job is very expensive
  # for this module due to bad firmware design, so completely ignore graceful cancellation.
  def notify_canceled(self, job, graceful):
    if graceful: return
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.wakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.wakeup.notify()

        
  # Report custom statistics.
  def _get_statistics(self, stats, childstats):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self)._get_statistics(stats, childstats)
    stats.temperature = self.stats.temperature
        
        
  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()

        # Initialize megahashes per second to zero, will be measured later.
        self.stats.mhps = 0

        # Job that the device is currently working on, or that is currently being uploaded.
        # This variable is used by BaseWorker to figure out the current work source for statistics.
        self.job = None

        # Open the serial port
        import serial
        self.handle = serial.Serial(self.port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        
        self.handle.write(b"ZGX")
        response = self.handle.readline()
        if response[:31] != b">>>ID: BitFORCE SHA256 Version " or response[-4:] != b">>>\n":
          raise Exception("Bad ZGX response: %s\n" % response.decode("ascii", "replace").strip())
        self.core.log(self, "Firmware: %s\n" % (response[7:-4].decode("ascii", "replace")), 400, "B")

        # Main loop, continues until something goes wrong or we're shutting down.
        while not self.shutdown:

          # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
          # Blocks until one is available. Because of this we need to release the
          # wakeup lock temporarily in order to avoid possible deadlocks.
          self.wakeup.release()
          job = self.core.get_job(self, self.jobinterval + 2)
          self.wakeup.acquire()
          
          # If a new block was found while we were fetching that job, just discard it and get a new one.
          if job.canceled:
            job.destroy()
            continue

          self._jobend()
          self.job = job
          self.handle.write(b"ZDX")
          response = self.handle.readline()
          if response != b"OK\n": raise Exception("Bad ZDX response: %s\n" % response.decode("ascii", "replace").strip())
          if self.shutdown: break
          self.handle.write(b">>>>>>>>" + job.midstate + job.data[64:76] + b">>>>>>>>")
          response = self.handle.readline()
          if response != b"OK\n": raise Exception("Bad job response: %s\n" % response.decode("ascii", "replace").strip())
          if self.shutdown: break

          # If a new block was found while we were sending that job, just discard it and get a new one.
          if job.canceled:
            self.job = None
            job.destroy()
            continue

          self.job.starttime = time.time()
          
          # Read device temperature
          self.handle.write(b"ZLX")
          response = self.handle.readline()
          if response[:23] != b"Temperature (celcius): " or response[-1:] != b"\n":
            raise Exception("Bad ZLX response: %s\n" % response.decode("ascii", "replace").strip())
          self.stats.temperature = float(response[23:-1])
          self.core.event(350, self, "temperature", self.stats.temperature * 1000, "%f \xc2\xb0C" % self.stats.temperature, worker = self)
          if self.shutdown: break

          # Wait while the device is processing the job. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)
          if self.shutdown: break
          
          # Poll the device for job results
          while True:
            now = time.time()
            if self.job.canceled: break
            self.handle.write(b"ZFX")
            response = self.handle.readline()
            if self.shutdown: break
            if response == b"BUSY\n": continue
            if response == b"NO-NONCE\n": break
            if response[:12] != "NONCE-FOUND:" or response[-1:] != "\n":
              raise Exception("Bad ZFX response: %s\n" % response.decode("ascii", "replace").strip())
            nonces = response[12:-1]
            while nonces:
              self.job.nonce_found(unhexlify(nonces[:8])[::-1])
              if len(nonces) != 8 and nonces[8] != b",":
                raise Exception("Bad ZFX response: %s\n" % response.decode("ascii", "replace").strip())
              nonces = nonces[9:]
            break
          if not self.job.canceled:
            delta = now - self.job.starttime
            self.stats.mhps = 2**32 / delta / 1000000.
            self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
            self.jobinterval = delta - 0.2
            self.jobspersecond = 1. / self.jobinterval
            self.core.notify_speed_changed(self)
          self._jobend(now)

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        try: self.wakeup.release()
        except: pass
        # Close the serial port handle, otherwise we can't reopen it after restarting.
        try: self.handle.close()
        except: pass
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, wait a bit longer until restarting the worker.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job:
      if self.job.starttime:
        self.job.hashes_processed((now - self.job.starttime) * self.stats.mhps * 1000000)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.job.destroy()
      self.job = None

########NEW FILE########
__FILENAME__ = cairnsmorehotplug
# Modular Python Bitcoin Miner
# Copyright (C) 2011-2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



########################################
# Cairnsmore hotplug controller module #
########################################



import re
import traceback
from glob import glob
from threading import Condition, Thread
from core.baseworker import BaseWorker
from .cairnsmoreworker import CairnsmoreWorker



# Worker main class, referenced from __init__.py
class CairnsmoreHotplugWorker(BaseWorker):

  version = "theseven.cairnsmore hotplug manager v0.1.0"
  default_name = "Cairnsmore hotplug manager"
  can_autodetect = True
  settings = dict(BaseWorker.settings, **{
    "baudrate": {"title": "Baud rate", "type": "int", "position": 1100},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 1200},
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 2000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 2100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 3200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 3300},
    "warmupstepshares": {"title": "Shares per warmup step", "type": "int", "position": 3400},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 3500},
    "scaninterval": {"title": "Bus scan interval", "type": "float", "position": 4000},
  })


  @classmethod
  def autodetect(self, core):
    try:
      import serial
      found = False
      for port in glob("/dev/serial/by-id/usb-FTDI_Cairnsmore1_*-if0?-port0"):
        try:
          handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
          handle.close()
          found = True
          break
        except: pass
      if found: core.add_worker(self(core))
    except: pass


  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Initialize bus scanner wakeup event
    self.wakeup = Condition()

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(CairnsmoreHotplugWorker, self).__init__(core, state)


  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(CairnsmoreHotplugWorker, self).apply_settings()
    if not "scaninterval" in self.settings or not self.settings.scaninterval: self.settings.scaninterval = 10
    if not "baudrate" in self.settings or not self.settings.baudrate: self.settings.baudrate = 115200
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 20
    if not "initialspeed" in self.settings: self.settings.initialspeed = 150
    self.settings.initialspeed = min(max(self.settings.initialspeed, 4), 250)
    if not "maximumspeed" in self.settings: self.settings.maximumspeed = 200
    self.settings.maximumspeed = min(max(self.settings.maximumspeed, 4), 300)
    if not "invalidwarning" in self.settings: self.settings.invalidwarning = 2
    self.settings.invalidwarning = min(max(self.settings.invalidwarning, 1), 10)
    if not "invalidcritical" in self.settings: self.settings.invalidcritical = 10
    self.settings.invalidcritical = min(max(self.settings.invalidcritical, 1), 50)
    if not "warmupstepshares" in self.settings: self.settings.warmupstepshares = 5
    self.settings.warmupstepshares = min(max(self.settings.warmupstepshares, 1), 10000)
    if not "speedupthreshold" in self.settings: self.settings.speedupthreshold = 100
    self.settings.speedupthreshold = min(max(self.settings.speedupthreshold, 50), 10000)
    # Push our settings down to our children
    fields = ["baudrate", "jobinterval", "initialspeed", "maximumspeed", "invalidwarning",
              "invalidcritical", "warmupstepshares", "speedupthreshold"]
    for child in self.children:
      for field in fields: child.settings[field] = self.settings[field]
      child.apply_settings()
    # Rescan the bus immediately to apply the new settings
    with self.wakeup: self.wakeup.notify()


  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(CairnsmoreHotplugWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(CairnsmoreHotplugWorker, self)._start()
    # Initialize child map
    self.childmap = {}
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()


  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(CairnsmoreHotplugWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(10)
    # Shut down child workers
    while self.children:
      child = self.children.pop(0)
      try:
        self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
        child.stop()
      except Exception as e:
        self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")


  # Main thread entry point
  # This thread is responsible for scanning for boards and spawning worker modules for them
  def main(self):
    import serial

    # Loop until we are shut down
    while not self.shutdown:

      try:
        boards = {}
        for port in glob("/dev/serial/by-id/usb-FTDI_Cairnsmore1_*-if0?-port0"):
          available = False
          try:
            handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
            handle.close()
            available = True
          except: pass
          boards[port] = available

        kill = []
        for port, child in self.childmap.items():
          if not port in boards:
            kill.append((port, child))

        for port, child in kill:
          try:
            self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
            child.stop()
          except Exception as e:
            self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
          childstats = child.get_statistics()
          fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
          for field in fields: self.stats[field] += childstats[field]
          try: self.child.destroy()
          except: pass
          del self.childmap[port]
          try: self.children.remove(child)
          except: pass

        for port, available in boards.items():
          if port in self.childmap or not available: continue
          child = CairnsmoreWorker(self.core)
          child.settings.name = "Cairnsmore1 board %s FPGA%s" % (re.match("/dev/serial/by-id/usb-FTDI_Cairnsmore1_([0-9A-Z]+)-if0([0-3])-port0", port).group(1, 2))
          child.settings.port = port
          fields = ["jobinterval", "baudrate", "initialspeed", "maximumspeed", "invalidwarning",
                    "invalidcritical", "warmupstepshares",  "speedupthreshold"]
          for field in fields: child.settings[field] = self.settings[field]
          child.apply_settings()
          self.childmap[port] = child
          self.children.append(child)
          try:
            self.core.log(self, "Starting up worker %s...\n" % (child.settings.name), 800)
            child.start()
          except Exception as e:
            self.core.log(self, "Could not start worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")

      except: self.core.log(self, "Caught exception: %s\n" % traceback.format_exc(), 100, "rB")

      with self.wakeup: self.wakeup.wait(self.settings.scaninterval)

########NEW FILE########
__FILENAME__ = cairnsmoreworker
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.


######################################
# Cairnsmore worker interface module #
######################################



import time
import struct
import traceback
from threading import Condition, Thread
from binascii import hexlify, unhexlify
from core.baseworker import BaseWorker
from core.job import ValidationJob

# Worker main class, referenced from __init__.py
class CairnsmoreWorker(BaseWorker):
  
  version = "theseven.cairnsmore worker v0.1.0"
  default_name = "Untitled Cairnsmore worker"
  settings = dict(BaseWorker.settings, **{
    "port": {"title": "Port", "type": "string", "position": 1000},
    "baudrate": {"title": "Baud rate", "type": "int", "position": 1100},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 1200},
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 2000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 2100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 3200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 3300},
    "warmupstepshares": {"title": "Shares per warmup step", "type": "int", "position": 3400},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 3500},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(CairnsmoreWorker, self).__init__(core, state)

    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(CairnsmoreWorker, self).apply_settings()
    # Pretty much self-explanatory...
    if not "port" in self.settings or not self.settings.port: self.settings.port = "/dev/ttyUSB0"
    if not "baudrate" in self.settings or not self.settings.baudrate: self.settings.baudrate = 115200
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 20
    if not "initialspeed" in self.settings: self.settings.initialspeed = 150
    self.settings.initialspeed = min(max(self.settings.initialspeed, 4), 250)
    if not "maximumspeed" in self.settings: self.settings.maximumspeed = 200
    self.settings.maximumspeed = min(max(self.settings.maximumspeed, 4), 300)
    if not "invalidwarning" in self.settings: self.settings.invalidwarning = 2
    self.settings.invalidwarning = min(max(self.settings.invalidwarning, 1), 10)
    if not "invalidcritical" in self.settings: self.settings.invalidcritical = 10
    self.settings.invalidcritical = min(max(self.settings.invalidcritical, 1), 50)
    if not "warmupstepshares" in self.settings: self.settings.warmupstepshares = 5
    self.settings.warmupstepshares = min(max(self.settings.warmupstepshares, 1), 10000)
    if not "speedupthreshold" in self.settings: self.settings.speedupthreshold = 100
    self.settings.speedupthreshold = min(max(self.settings.speedupthreshold, 50), 10000)
    # We can't change the port name or baud rate on the fly, so trigger a restart if they changed.
    # self.port/self.baudrate are cached copys of self.settings.port/self.settings.baudrate
    if self.started and (self.settings.port != self.port or self.settings.baudrate != self.baudrate): self.async_restart()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(CairnsmoreWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.port = None
    self.baudrate = None

#    # Initialize custom statistics. This is not neccessary for this worker module,
#    # but might be interesting for other modules, so it is kept here for reference.
#    self.stats.field1 = 0
#    self.stats.field2 = 0
#    self.stats.field3 = 0


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(CairnsmoreWorker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.port = self.settings.port
    self.baudrate = self.settings.baudrate
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.settings.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(CairnsmoreWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # The listener thread will hopefully die because the main thread closes the serial port handle.
    # Wait for the main thread to terminate, which in turn waits for the listener thread to die.
    self.mainthread.join(10)

      
  # This function should interrupt processing of the specified job if possible.
  # This is neccesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast.
  def notify_canceled(self, job, graceful):
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.wakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.wakeup.notify()

        
#  # Report custom statistics. This is not neccessary for this worker module,
#  # but might be interesting for other modules, so it is kept here for reference.
#  def _get_statistics(self, stats, childstats):
#    # Let our superclass handle everything that isn't specific to this worker module
#    super(IcarusWorker, self)._get_statistics(stats, childstats)
#    stats.field1 = self.stats.field1
#    stats.field2 = self.stats.field2 + childstats.calculatefieldsum("field2")
#    stats.field3 = self.stats.field3 + childstats.calculatefieldavg("field3")
        
        
  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()
        # Exception container: If an exception occurs in the listener thread, the listener thread
        # will store it here and terminate, and the main thread will rethrow it and then restart.
        self.error = None
        self.hasheswithoutshare = 0

        # Initialize megahashes per second to zero, will be measured later.
        self.stats.mhps = 0
        self.offset = 0

        # Initialize clocking tracking data
        self.speed = 0
        self.recentshares = 0
        self.recentinvalid = 0
        
        # Job that the device is currently working on, or that is currently being uploaded.
        # This variable is used by BaseWorker to figure out the current work source for statistics.
        self.job = None
        # Job that was previously being procesed. Has been destroyed, but there might be some late nonces.
        self.oldjob = None

        # Open the serial port
        import serial
        self.handle = serial.Serial(self.port, self.baudrate, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Set validation success flag to false
        self.checksuccess = False
        # Start device response listener thread
        self.listenerthread = Thread(None, self._listener, self.settings.name + "_listener")
        self.listenerthread.daemon = True
        self.listenerthread.start()

        # Configure core clock
        self.initialramp = True
        self._set_speed(self.settings.initialspeed // 2.5)
        
        # Send validation job to device
        job = ValidationJob(self.core, unhexlify(b"00000001c3bf95208a646ee98a58cf97c3a0c4b7bf5de4c89ca04495000005200000000024d1fff8d5d73ae11140e4e48032cd88ee01d48c67147f9a09cd41fdec2e25824f5c038d1a0b350c5eb01f04"))
        self._sendjob(job)

        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error

        # Wait for the validation job to complete. The wakeup flag will be set by the listener
        # thread when the validation job completes. 60 seconds should be sufficient for devices
        # down to about 2.6MH/s, for slower devices this timeout will need to be increased.
        self.wakeup.wait(60)
        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error
        # Honor shutdown flag
        if self.shutdown: break
        # We woke up, but the validation job hasn't succeeded in the mean time.
        # This usually means that the wakeup timeout has expired.
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")

        # Main loop, continues until something goes wrong or we're shutting down.
        while not self.shutdown:

          # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
          # Blocks until one is available. Because of this we need to release the
          # wakeup lock temporarily in order to avoid possible deadlocks.
          self.wakeup.release()
          job = self.core.get_job(self, self.jobinterval + 2)
          self.wakeup.acquire()

          # If the job could be interpreted as a command, ignore it.
          if job.data[68:72] == unhexlify(b"ffffffff"):
            job.destroy()
            continue

          # Go through the safety checks and adjust the clock if necessary
          self.safetycheck()
          
          # If a new block was found while we were fetching this job, just discard it and get a new one.
          if job.canceled:
            job.destroy()
            continue

          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

          # Upload the job to the device
          self._sendjob(job)
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error
          # If the job was already caught by a long poll while we were uploading it,
          # jump back to the beginning of the main loop in order to immediately fetch new work.
          # Don't check for the canceled flag before the job was accepted by the device,
          # otherwise we might get out of sync.
          if self.job.canceled: continue
          # Wait while the device is processing the job. If nonces are sent by the device, they
          # will be processed by the listener thread. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
        # Make sure that the listener thread realizes that something went wrong
        self.error = e
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        # Release the wake lock to allow the listener thread to move. Ignore it if that goes wrong.
        try: self.wakeup.release()
        except: pass
        # Close the serial port handle, otherwise we can't reopen it after restarting.
        # This should hopefully also make reads on that port from the listener thread fail,
        # so that the listener thread will realize that it's supposed to shut down.
        try: self.handle.close()
        except: pass
        # Wait for the listener thread to terminate.
        # If it doens't within 5 seconds, continue anyway. We can't do much about that.
        try: self.listenerthread.join(5)
        except: pass
        # Set MH/s to zero again, the listener thread might have overwritten that.
        self.stats.mhps = 0
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, wait a bit longer until restarting the worker.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  # Device response listener thread
  def _listener(self):
    # Catch all exceptions and forward them to the main thread
    try:
      # Loop forever unless something goes wrong
      while True:
        # If the main thread has a problem, make sure we die before it restarts
        if self.error != None: break

        # If there were suspiciously many hashes without even a single share,
        # assume that PL2303 did it's job (i.e. serial port locked up),
        # and restart the board worker.
        if self.hasheswithoutshare > 16 * 2**32:
          raise Exception("Watchdog triggered: %.6f MHashes without share" % (self.hasheswithoutshare / 1000000.))

        # Try to read a response from the device
        nonce = self.handle.read(4)
        # If no response was available, retry
        if len(nonce) != 4: continue
        nonce = struct.pack("<I", struct.unpack(">I", nonce)[0] - self.offset)

        # Snapshot the current jobs to avoid race conditions
        newjob = self.job
        oldjob = self.oldjob
        # If there is no job, this must be a leftover from somewhere, e.g. previous invocation
        # or reiterating the keyspace because we couldn't provide new work fast enough.
        # In both cases we can't make any use of that nonce, so just discard it.
        if not oldjob and not newjob: return
        # Stop time measurement
        now = time.time()
        self.hasheswithoutshare = 0
        # Pass the nonce that we found to the work source, if there is one.
        # Do this before calculating the hash rate as it is latency critical.
        job = None
        if newjob:
          if newjob.nonce_found(nonce, oldjob): job = newjob
        if not job and oldjob:
          if oldjob.nonce_found(nonce): job = oldjob
        self.recentshares += 1
        if not job: self.recentinvalid += 1
        if not job and isinstance(newjob, ValidationJob): job = newjob
        # If the nonce is too low, the measurement may be inaccurate.
        nonceval = struct.unpack("<I", nonce)[0]
        if job and job.starttime and nonceval >= 0x04000000:
          # Calculate actual on-device processing time (not including transfer times) of the job.
          delta = (now - job.starttime) - 40. / self.baudrate
          # Calculate the hash rate based on the processing time and number of neccessary MHashes.
          # This assumes that the device processes all nonces (starting at zero) sequentially.
          self.stats.mhps = nonceval / 1000000. / delta
          self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
        # This needs self.stats.mhps to be set.
        if isinstance(newjob, ValidationJob):
          # This is a validation job. Validate that the nonce is correct, and complain if not.
          if newjob.nonce != nonce and struct.unpack("<I", newjob.nonce)[0] != struct.unpack("<I", nonce)[0] + 256:
            raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (hexlify(nonce).decode("ascii"), hexlify(newjob.nonce).decode("ascii")))
          else:
            # The nonce was correct. Wake up the main thread.
            self.offset = struct.unpack("<I", nonce)[0] - struct.unpack("<I", newjob.nonce)[0]
            with self.wakeup:
              self.checksuccess = True
              self.wakeup.notify()
        else:
          with self.wakeup:
            self._jobend(now)
            self.wakeup.notify()

    # If an exception is thrown in the listener thread...
    except Exception as e:
      # ...complain about it...
      self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      # ...put it into the exception container...
      self.error = e
      # ...wake up the main thread...
      with self.wakeup: self.wakeup.notify()
      # ...and terminate the listener thread.


  # This function uploads a job to the device
  def _sendjob(self, job):
    # Move previous job to oldjob, and new one to job
    self.oldjob = self.job
    self.job = job
    # Send it to the device
    now = time.time()
    self.handle.write(job.midstate[::-1] + b"\0" * 20 + job.data[75:63:-1])
    self.handle.flush()
    self.job.starttime = time.time()
    # Calculate how long the old job was running
    if self.oldjob and self.oldjob.starttime:
      if self.oldjob.starttime:
        hashes = min(2**32, (now - self.oldjob.starttime) * self.stats.mhps * 1000000)
        self.hasheswithoutshare += hashes
        self.oldjob.hashes_processed(hashes)
      self.oldjob.destroy()

    
  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job:
      if self.job.starttime:
        hashes = min(2**32, (now - self.job.starttime) * self.stats.mhps * 1000000)
        self.hasheswithoutshare += hashes
        self.job.hashes_processed(hashes)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.oldjob = self.job
      self.job.destroy()
      self.job = None
  
  
  # Check the invalid rate and adjust the FPGA clock accordingly
  def safetycheck(self):

    warning = False
    critical = False
    if self.recentinvalid >= self.settings.invalidwarning: warning = True
    if self.recentinvalid >= self.settings.invalidcritical: critical = True

    threshold = self.settings.warmupstepshares if self.initialramp and not self.recentinvalid else self.settings.speedupthreshold

    if warning: self.core.log(self, "Detected overload condition!\n", 200, "y")
    if critical: self.core.log(self, "Detected CRITICAL condition!\n", 100, "rB")

    if critical:
      speedstep = -10
      self.initialramp = False
    elif warning:
      speedstep = -1
      self.initialramp = False
    elif not self.recentinvalid and self.recentshares >= threshold:
      speedstep = 1
    else: speedstep = 0

    if speedstep: self._set_speed(self.speed + speedstep)

    if speedstep or self.recentshares >= threshold:
      self.recentinvalid = 0
      self.recentshares = 0


  def _set_speed(self, speed):
    speed = min(max(speed, 2), self.settings.maximumspeed // 2.5)
    if self.speed == speed: return
    if speed == self.settings.maximumspeed // 2.5: self.initialramp = False
    self.core.log(self, "%s: Setting clock speed to %.2f MHz...\n" % ("Warmup" if self.initialramp else "Tracking", speed * 2.5), 500, "B")
    command_id = 0
    command_data = int(speed)
    command_prefix = 0b10110111
    command_validator = (command_id ^ command_data ^ command_prefix ^ 0b01101101)
    commandpacket = struct.pack("BBBB", command_validator, command_data, command_id, command_prefix)
    self.handle.write(b"\0" * 32 + commandpacket + b"\xff" * 28)
    self.handle.flush()
    self.speed = speed
    self.stats.mhps = speed * 2.5
    self._update_job_interval()


  def _update_job_interval(self):
    self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
    # Calculate the time that the device will need to process 2**32 nonces.
    # This is limited at 60 seconds in order to have some regular communication,
    # even with very slow devices (and e.g. detect if the device was unplugged).
    interval = min(60, 2**32 / 1000000. / self.stats.mhps)
    # Add some safety margin and take user's interval setting (if present) into account.
    self.jobinterval = min(self.settings.jobinterval, max(0.5, interval * 0.8 - 1))
    self.core.log(self, "Job interval: %f seconds\n" % self.jobinterval, 400, "B")
    # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
    self.jobs_per_second = 1. / self.jobinterval
    self.core.notify_speed_changed(self)
  
########NEW FILE########
__FILENAME__ = boardproxy
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##############################################################################
# Generic FTDI JTAG bitbanging worker out of process board access dispatcher #
##############################################################################



import time
import signal
import traceback
from threading import Thread, Condition, RLock
from multiprocessing import Process
from .driver import FTDIJTAGDevice



class FTDIJTAGBoardProxy(Process):
  

  def __init__(self, rxconn, txconn, serial, takeover, firmware, pollinterval):
    super(FTDIJTAGBoardProxy, self).__init__()
    self.rxconn = rxconn
    self.txconn = txconn
    self.serial = serial
    self.takeover = takeover
    self.firmware = firmware
    self.pollinterval = pollinterval


  def run(self):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    self.lock = RLock()
    self.wakeup = Condition()
    self.error = None
    self.pollingthread = None
    self.shutdown = False
  
    try:

      # Listen for setup commands
      while True:
        data = self.rxconn.recv()
        
        if data[0] == "connect": break
        
        else: raise Exception("Unknown setup message: %s" % str(data))
        
      # Connect to board
      self.device = FTDIJTAGDevice(self, self.serial, self.takeover, self.firmware)
      self.fpgacount = self.device.get_fpga_count()
      self.log("Found %i FPGA%s\n" % (self.fpgacount, 's' if self.fpgacount != 1 else ''), 500)
      if not self.fpgacount: raise Exception("No FPGAs detected!")
      
      # Drain leftover nonces
      while True:
        nonces = self.device.read_nonces()
        if not nonces: break

      # Start polling thread
      self.pollingthread = Thread(None, self.polling_thread, "polling_thread")
      self.pollingthread.daemon = True
      self.pollingthread.start()
      
      self.send("started_up", self.fpgacount)

      # Listen for commands
      while True:
        if self.error: raise self.error
      
        data = self.rxconn.recv()
        
        if data[0] == "shutdown": break

        elif data[0] == "ping": self.send("pong")

        elif data[0] == "pong": pass

        elif data[0] == "set_pollinterval":
          self.pollinterval = data[1]
          with self.wakeup: self.wakeup.notify()
        
        elif data[0] == "send_job":
          start = time.time()
          self.device.send_job(data[1], data[2])
          end = time.time()
          self.respond(start, end)
        
        elif data[0] == "set_speed":
          self.device.set_speed(data[1], data[2])
        
        elif data[0] == "get_speed":
          self.respond(self.device.get_speed(data[1]))
        
        else: raise Exception("Unknown message: %s" % str(data))
      
    except: self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
    finally:
      self.shutdown = True
      with self.wakeup: self.wakeup.notify()
      try: self.pollingthread.join(2)
      except: pass
      self.send("dying")
      
      
  def send(self, *args):
    with self.lock: self.txconn.send(args)
      
      
  def respond(self, *args):
    self.send("response", *args)
      
      
  def log(self, message, loglevel, format = ""):
    self.send("log", message, loglevel, format)
    
    
  def polling_thread(self):
    try:
      counter = 0
      while not self.shutdown:
        # Poll for nonces
        nonces = self.device.read_nonces()
        for fpga in nonces: self.send("nonce_found", fpga, time.time(), nonces[fpga])
        
        counter += 1
        if counter >= 20:
          counter = 0
          self.send("temperatures_read", self.device.read_temperatures())
    
        with self.wakeup: self.wakeup.wait(self.pollinterval)
        
    except Exception as e:
      self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
      self.error = e
      # Unblock main thread
      self.send("ping")

########NEW FILE########
__FILENAME__ = driver
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



########################################################
# Generic FTDI JTAG bitbanging worker low level driver #
########################################################



import time
import usb
import struct
from binascii import unhexlify
from threading import RLock



jtagscript_mmq = {}
jtagscript_mmq["Bus 0"] = {}
jtagscript_mmq["Bus 0"]["s6_user1"] = unhexlify(b"000401050004000400040004")
jtagscript_mmq["Bus 0"]["leave_shift"] = unhexlify(b"080c")
jtagscript_mmq["Bus 0"]["tdi"] = unhexlify(b"01")
jtagscript_mmq["Bus 0"]["tms"] = unhexlify(b"08")
jtagscript_mmq["Bus 0"]["tdo"] = unhexlify(b"02")
jtagscript_mmq["Bus 0"]["shift_dr"] = unhexlify(b"080c00040004")
jtagscript_mmq["Bus 0"]["highclock"] = unhexlify(b"0105")
jtagscript_mmq["Bus 0"]["clock"] = unhexlify(b"0004")
jtagscript_mmq["Bus 0"]["tap_reset"] = unhexlify(b"080c080c080c080c080c0004")
jtagscript_mmq["Bus 0"]["s6_cfg_in"] = unhexlify(b"010500040105000400040004")
jtagscript_mmq["Bus 0"]["shift_ir"] = unhexlify(b"080c080c00040004")
jtagscript_mmq["Bus 0"]["s6_jprogram"] = unhexlify(b"010501050004010500040004")
jtagscript_mmq["Bus 0"]["tck"] = unhexlify(b"04")
jtagscript_mmq["Bus 0"]["s6_jstart"] = unhexlify(b"000400040105010500040004")
jtagscript_mmq["Bus 0"]["fm_getnonce"] = unhexlify(b"000401050105010500040004")
jtagscript_mmq["Bus 0"]["s6_usercode"] = unhexlify(b"000400040004010500040004")
jtagscript_mmq["Bus 0"]["s6_jshutdown"] = unhexlify(b"010500040105010500040004")
jtagscript_x6500 = {}
jtagscript_x6500["Bus 1"] = {}
jtagscript_x6500["Bus 1"]["s6_user1"] = unhexlify(b"c0c8c2cac0c8c0c8c0c8c0c8")
jtagscript_x6500["Bus 1"]["leave_shift"] = unhexlify(b"c4cc")
jtagscript_x6500["Bus 1"]["tdi"] = unhexlify(b"c2")
jtagscript_x6500["Bus 1"]["tms"] = unhexlify(b"c4")
jtagscript_x6500["Bus 1"]["tdo"] = unhexlify(b"01")
jtagscript_x6500["Bus 1"]["shift_dr"] = unhexlify(b"c4ccc0c8c0c8")
jtagscript_x6500["Bus 1"]["highclock"] = unhexlify(b"c2ca")
jtagscript_x6500["Bus 1"]["clock"] = unhexlify(b"c0c8")
jtagscript_x6500["Bus 1"]["tap_reset"] = unhexlify(b"c4ccc4ccc4ccc4ccc4ccc0c8")
jtagscript_x6500["Bus 1"]["s6_cfg_in"] = unhexlify(b"c2cac0c8c2cac0c8c0c8c0c8")
jtagscript_x6500["Bus 1"]["shift_ir"] = unhexlify(b"c4ccc4ccc0c8c0c8")
jtagscript_x6500["Bus 1"]["s6_jprogram"] = unhexlify(b"c2cac2cac0c8c2cac0c8c0c8")
jtagscript_x6500["Bus 1"]["tck"] = unhexlify(b"c8")
jtagscript_x6500["Bus 1"]["s6_jstart"] = unhexlify(b"c0c8c0c8c2cac2cac0c8c0c8")
jtagscript_x6500["Bus 1"]["fm_getnonce"] = unhexlify(b"c0c8c2cac2cac2cac0c8c0c8")
jtagscript_x6500["Bus 1"]["s6_usercode"] = unhexlify(b"c0c8c0c8c0c8c2cac0c8c0c8")
jtagscript_x6500["Bus 1"]["s6_jshutdown"] = unhexlify(b"c2cac0c8c2cac2cac0c8c0c8")
jtagscript_x6500["Bus 0"] = {}
jtagscript_x6500["Bus 0"]["s6_user1"] = unhexlify(b"0c8c2cac0c8c0c8c0c8c0c8c")
jtagscript_x6500["Bus 0"]["leave_shift"] = unhexlify(b"4ccc")
jtagscript_x6500["Bus 0"]["tdi"] = unhexlify(b"2c")
jtagscript_x6500["Bus 0"]["tms"] = unhexlify(b"4c")
jtagscript_x6500["Bus 0"]["tdo"] = unhexlify(b"10")
jtagscript_x6500["Bus 0"]["shift_dr"] = unhexlify(b"4ccc0c8c0c8c")
jtagscript_x6500["Bus 0"]["highclock"] = unhexlify(b"2cac")
jtagscript_x6500["Bus 0"]["clock"] = unhexlify(b"0c8c")
jtagscript_x6500["Bus 0"]["tap_reset"] = unhexlify(b"4ccc4ccc4ccc4ccc4ccc0c8c")
jtagscript_x6500["Bus 0"]["s6_cfg_in"] = unhexlify(b"2cac0c8c2cac0c8c0c8c0c8c")
jtagscript_x6500["Bus 0"]["shift_ir"] = unhexlify(b"4ccc4ccc0c8c0c8c")
jtagscript_x6500["Bus 0"]["s6_jprogram"] = unhexlify(b"2cac2cac0c8c2cac0c8c0c8c")
jtagscript_x6500["Bus 0"]["tck"] = unhexlify(b"8c")
jtagscript_x6500["Bus 0"]["s6_jstart"] = unhexlify(b"0c8c0c8c2cac2cac0c8c0c8c")
jtagscript_x6500["Bus 0"]["fm_getnonce"] = unhexlify(b"0c8c2cac2cac2cac0c8c0c8c")
jtagscript_x6500["Bus 0"]["s6_usercode"] = unhexlify(b"0c8c0c8c0c8c2cac0c8c0c8c")
jtagscript_x6500["Bus 0"]["s6_jshutdown"] = unhexlify(b"2cac0c8c2cac2cac0c8c0c8c")


def byte2int(byte):
  if type(byte) is int: return byte
  return struct.unpack("B", byte)[0]


def int2byte(value):
  return struct.pack("B", value)


def orbytes(byte1, byte2):
  return int2byte(byte2int(byte1) | byte2int(byte2))
  
  
def int2bits(bits, value):
  result = []
  for bit in range(bits):
    result.append(value & 1)
    value = value >> 1
  return result


def bits2int(data):
  result = 0
  for bit in range(len(data)): result |= data[bit] << bit
  return result

  
def jtagcomm_checksum(bits):
  checksum = 1
  for bit in bits: checksum ^= bit
  return [checksum]
  
  
  
class DeviceException(Exception): pass
    
  

class Spartan6FPGA(object):

  
  def __init__(self, proxy, driver, bus, id, idcode):
    self.proxy = proxy
    self.driver = driver
    self.bus = bus
    self.id = id
    self.idcode = idcode
    self.usable = False
    self.irlength = idcodemap[idcode & 0xfffffff]["irlength"]
    if idcode & 0xfffffff == 0x401d093: self.typename = "Xilinx Spartan 6 LX150 FPGA"
    elif idcode & 0xfffffff == 0x403d093: self.typename = "Xilinx Spartan 6 LX150T FPGA"
    else: self.typename = "Unknown Xilinx Spartan 6 FPGA (0x%08X)" % idcode
    self.name = "%s Device %d" % (bus, id)
    
  
  def init(self):
    self._prepare_firmware()
    script = self.driver.jtagscript[self.bus]
    self.driver.set_ir(self, script["s6_usercode"])
    self.usercode = bits2int(self.driver.get_dr(self, 32))
    if self.usercode != self.fwusercode: self._upload_firmware()
    self.driver.set_ir(self, script["s6_usercode"])
    self.usercode = bits2int(self.driver.get_dr(self, 32))
    if self.usercode == 0xffffffff: raise DeviceException("USERCODE register not available!")
    self.firmware_rev = (self.usercode >> 8) & 0xff
    self.firmware_build = self.usercode & 0xf
    self.proxy.log("%s: Firmware version %d, build %d\n" % (self.name, self.firmware_rev, self.firmware_build), 500)
    clock = script["clock"]
    hc = script["highclock"]
    self.selectscript = script["shift_ir"] \
                      + self.driver._tmstail(self.bus, hc * self.irhead + script["s6_user1"] + hc * self.irtail) \
                      + script["ir_to_dr"]
    self.unselectscript = script["leave_shift"]
    self.reselectscript = script["shift_dr"]
    self.writescript = script["clock"] * self.drtail
    self.readscript = script["clock"] * self.drhead
    self.readnonce_ir = script["s6_user1"]
    self.readnonce_push_dr = clock * 32 + script["fm_getnonce"]
    self.readnonce_pull_len = 38
    self.usable = True
    self.driver.register(self)
    
    
  def _format_reg_write_dr(self, addr, data):
    bits = int2bits(32, data) + int2bits(4, addr) + [1]
    bits += jtagcomm_checksum(bits)
    return self.driver.format_dr(self.bus, bits)
    
    
  def _write_reg(self, reg, data):
    data = self.selectscript \
         + self.driver._tmstail(self.bus, self._format_reg_write_dr(reg, data) + self.writescript) \
         + self.unselectscript
    with self.driver.lock: self.driver._write(data)
  
  
  def _format_reg_read_dr(self, addr):
    bits = int2bits(4, addr) + [0]
    bits += jtagcomm_checksum(bits)
    return self.driver.format_dr(self.bus, bits)
    
    
  def _read_reg(self, reg):
    script = self.driver.jtagscript[self.bus]
    data1 = self.selectscript \
          + self.driver._tmstail(self.bus, self._format_reg_read_dr(reg) + self.writescript) \
          + self.unselectscript \
          + self.reselectscript \
          + self.readscript
    data2 = self.driver._tmstail(self.bus, script["clock"] * 32)
    data3 = script["leave_shift"]
    with self.driver.lock:
      self.driver._write(data1)
      data = self.driver._shift(self.bus, data2)
      self.driver._write(data3)
    return bits2int(data)
    
    
  def _prepare_firmware(self):
    try:
      self.firmware = self.driver.firmware
      if self.firmware[-1] == "/": self.firmware += "%08x.bit" % (self.idcode & 0xfffffff)
      with open(self.firmware, "rb") as file:
        if struct.unpack(">H", file.read(2))[0] != 9: raise Exception("Bad firmware file format!")
        file.read(11)
        if file.read(1) != b"a": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwdesignname = file.read(bytes).decode("latin1").rstrip('\0')
        self.fwusercode = int(self.fwdesignname.split(';')[-1].split('=')[-1], base = 16)
        if file.read(1) != b"b": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwpart = file.read(bytes).decode("latin1").rstrip('\0')
        if file.read(1) != b"c": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwdate = file.read(bytes).decode("latin1").rstrip('\0')
        if file.read(1) != b"d": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwtime = file.read(bytes).decode("latin1").rstrip('\0')
        if file.read(1) != b"e": raise Exception("Bad firmware file format!")
        self.fwlength = struct.unpack(">I", file.read(4))[0]
        self.fwoffset = file.tell()
      self.proxy.log("%s: Firmware file %s information:\n" % (self.name, self.firmware), 500, "B")
      self.proxy.log("%s:   Design name: %s\n" % (self.name, self.fwdesignname), 500)
      self.proxy.log("%s:   Version: %d, build %d\n" % (self.name, (self.fwusercode >> 8) & 0xff, self.fwusercode & 0xff), 500)
      self.proxy.log("%s:   Build time: %s %s\n" % (self.name, self.fwdate, self.fwtime), 500)
      self.proxy.log("%s:   Part number: %s\n" % (self.name, self.fwpart), 500)
      self.proxy.log("%s:   Bitstream length: %d bytes\n" % (self.name, self.fwlength), 500)
      idcodemap = {"6slx150fgg484": 0x401d093, "6slx150tfgg676": 0x403d093}
      if not self.fwpart in idcodemap or idcodemap[self.fwpart] != self.idcode & 0xfffffff:
        raise Exception("Firmware is for wrong device type!")
      if self.fwusercode == 0xffffffff: raise Exception("Firmware does not support USERCODE!")
    except Exception as e: raise DeviceException(str(e))
    
  def _upload_firmware(self):
    with open(self.firmware, "rb") as file:
      file.seek(self.fwoffset)
      script = self.driver.jtagscript[self.bus]
      clock = script["clock"]
      hc = script["highclock"]
      self.proxy.log("%s: Programming FPGA...\n" % self.name, 300, "B")
      starttime = time.time()
      with self.driver.lock:
        data = script["shift_ir"] \
             + self.driver._tmstail(self.bus, hc * self.irhead + script["s6_jprogram"] + hc * self.irtail) \
             + script["leave_shift"] \
             + script["shift_ir"] \
             + self.driver._tmstail(self.bus, hc * self.irhead + script["s6_cfg_in"] + hc * self.irtail) \
             + script["ir_to_dr"]
        self.driver._write(data)
        bytesleft = self.fwlength
        bytes = 0
        while bytesleft:
          chunksize = min(4096, bytesleft)
          bytes += chunksize
          bytesleft -= chunksize
          chunk = file.read(chunksize)
          data = b""
          for byte in chunk:
            if type(byte) is not int: byte = struct.unpack("B", byte)[0]
            data += (hc if byte & 0x80 else clock) \
                  + (hc if byte & 0x40 else clock) \
                  + (hc if byte & 0x20 else clock) \
                  + (hc if byte & 0x10 else clock) \
                  + (hc if byte & 0x08 else clock) \
                  + (hc if byte & 0x04 else clock) \
                  + (hc if byte & 0x02 else clock) \
                  + (hc if byte & 0x01 else clock)
          if not bytesleft: data = self.driver._tmstail(self.bus, data + clock * self.drtail)
          self.driver._write(data)
          if not bytes & 0x3ffff:
            percent = 100. * bytes / self.fwlength
            speed = bytes / (time.time() - starttime) / 1024.
            self.proxy.log("%s: Programming: %.1f%% done, %.1f kiB/s\n" % (self.name, percent, speed), 300, "B")
        data = script["leave_shift"] \
             + script["shift_ir"] \
             + self.driver._tmstail(self.bus, hc * self.irhead + script["s6_jstart"] + hc * self.irtail) \
             + script["leave_shift"] \
             + clock * 16
        self.driver._write(data)
        status = self.driver.get_ir(self)
        if not status[-1]: raise DeviceException("FPGA did not accept bitstream!")
    
    
  def get_speed(self):
    return self._read_reg(0xd)
    
    
  def set_speed(self, speed):
    self._write_reg(0xd, speed)
    
    
  def send_job(self, job):
    job = struct.unpack("<11I", job)
    data = b""
    for i in range(11):
      data += (self.reselectscript if i else self.selectscript) \
            + self.driver._tmstail(self.bus, self._format_reg_write_dr(1 + i, job[i]) + self.writescript) \
            + self.unselectscript
    with self.driver.lock: self.driver._write(data)
    
    
  def parse_nonce(self, data):
    data = bits2int(data[:32])
    if data != 0xffffffff: return struct.pack("<I", data)

    
    
class UnknownJTAGDevice(object):

  
  def __init__(self, proxy, driver, bus, id, idcode):
    self.proxy = proxy
    self.driver = driver
    self.bus = bus
    self.id = id
    self.idcode = idcode
    self.usable = False
    self.irlength = idcodemap[idcode & 0xfffffff]["irlength"]
    self.typename = "Unknown JTAG Device (0x%08X)" % idcode
    self.name = "%s Device %d" % (bus, id)
    
    
  def init(self): pass

    
    
idcodemap = {
  0x401d093: {"irlength": 6, "handler": Spartan6FPGA},
  0x403d093: {"irlength": 6, "handler": Spartan6FPGA},
}



class FTDIJTAGDevice(object):
  

  def __init__(self, proxy, deviceid, takeover, firmware):
    self.lock = RLock()
    self.proxy = proxy
    self.serial = deviceid
    self.takeover = takeover
    self.firmware = firmware
    self.handle = None
    permissionproblem = False
    deviceinuse = False
    for bus in usb.busses():
      if self.handle != None: break
      for dev in bus.devices:
        if self.handle != None: break
        if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
          try:
            handle = dev.open()
            manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
            product = handle.getString(dev.iProduct, 100).decode("latin1")
            serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
            boardtype = None
            if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner"):
              boardtype = "X6500"
            elif manufacturer == "BTCFPGA" and product == "ModMiner":
              boardtype = "ModMiner"
            if boardtype and (deviceid == "" or deviceid == serial):
              try:
                if takeover:
                  handle.reset()
                  time.sleep(1)
                configuration = dev.configurations[0]
                interface = configuration.interfaces[0][0]
                handle.setConfiguration(configuration.value)
                handle.claimInterface(interface.interfaceNumber)
                handle.setAltInterface(interface.alternateSetting)
                self.inep = interface.endpoints[0].address
                self.inepsize = interface.endpoints[0].maxPacketSize
                self.outep = interface.endpoints[1].address
                self.outepsize = interface.endpoints[1].maxPacketSize
                self.index = 1
                self.handle = handle
                self.serial = serial
                self.boardtype = boardtype
              except: deviceinuse = True
          except: permissionproblem = True
    if self.handle == None:
      if deviceinuse:
        raise Exception("Can not open the specified device, possibly because it is already in use")
      if permissionproblem:
        raise Exception("Can not open the specified device, possibly due to insufficient permissions")
      raise Exception("Can not open the specified device")
    self.outmask = 0
    if self.boardtype == "X6500": self.jtagscript = jtagscript_x6500
    elif self.boardtype == "ModMiner": self.jtagscript = jtagscript_mmq
    else: raise Exception("Unknown board: %s" % self.boardtype)
    for bus in self.jtagscript:
      script = self.jtagscript[bus]
      script["clocklen"] = len(script["clock"])
      script["tckmask"] = byte2int(script["tck"])
      script["tmsmask"] = byte2int(script["tms"])
      script["tdimask"] = byte2int(script["tdi"])
      script["tdomask"] = byte2int(script["tdo"])
      script["ir_to_dr"] = script["leave_shift"] + script["shift_dr"]
      self.outmask |= script["tckmask"] | script["tmsmask"] | script["tdimask"]
    self.handle.controlMsg(0x40, 3, None, 0, 0)
    self._switch_async()
    self.initialized = {}
    self.busdevices = {}
    self.devices = []
    for bus in sorted(self.jtagscript.keys()):
      self.initialized[bus] = False
      try: self._init_bus(bus)
      except Exception as e: self.proxy.log("%s\n" % e, 150, "rB")
    
    
  def _init_bus(self, bus):
    max_devices = 100
    max_ir_len = 16
    script = self.jtagscript[bus]
    clock = script["clock"]
    hc = script["highclock"]
    data = script["tap_reset"] \
         + script["shift_ir"] \
         + self._tmstail(bus, script["highclock"] * max_ir_len * max_devices) \
         + script["ir_to_dr"] \
         + clock * max_devices
    self._write(data)
    data = self._shift(bus, self._tmstail(bus, hc * max_devices))
    devicecount = 0
    for bit in data:
      if not bit: devicecount += 1
      else: break
    if devicecount == max_devices: raise Exception("%s: JTAG chain contains more than 99 devices!" % bus)
    for i in range(devicecount, max_devices):
      if not data[i]: raise Exception("%s: Failed to detect JTAG chain device count!" % bus)
    self.proxy.log("%s: Detected %d devices\n" % (bus, devicecount), 500)
    devices = []
    if devicecount:
      self._write(script["tap_reset"] + script["shift_dr"])
      data = self._shift(bus, self._tmstail(bus, clock * devicecount * 32))
      self._write(script["leave_shift"])
      totalirlength = 0
      for i in range(devicecount):
        if not data[0]: raise Exception("%s: Device %d does not support IDCODE!" % (bus, i))
        idcode = bits2int(data[:32])
        data = data[32:]
        if not idcode & 0xfffffff in idcodemap:
          raise Exception("%s Device %d: Unknown IDCODE 0x%08X!" % (bus, i, idcode))
        if not "handler" in idcodemap[idcode & 0xfffffff]:
          idcodemap[idcode & 0xfffffff]["handler"] = UnknownJTAGDevice
        device = idcodemap[idcode & 0xfffffff]["handler"](self.proxy, self, bus, i, idcode)
        self.proxy.log("%s: %s\n" % (device.name, device.typename), 500)
        totalirlength += device.irlength
        devices.append(device)
    self.busdevices[bus] = devices
    irpos = 0
    for device in devices:
      device.irhead = irpos
      device.irtail = totalirlength - irpos - device.irlength
      device.drhead = device.id
      device.drtail = devicecount - device.id - 1
      irpos += device.irlength
      try: device.init()
      except DeviceException as e: self.proxy.log("%s: %s\n" % (device.name, str(e)), 200, "r")
    readnonce_ir = b""
    readnonce_push_dr = b""
    readnonce_pull_len = 0
    for device in devices:
      if device.usable:
        readnonce_ir += device.readnonce_ir
        readnonce_push_dr += device.readnonce_push_dr
        readnonce_pull_len += device.readnonce_pull_len
      else:
        readnonce_ir += hc * device.irlength
        readnonce_push_dr += clock
        readnonce_pull_len += 1
    script["readnonce_head"] = script["shift_ir"] \
                             + self._tmstail(bus, readnonce_ir) \
                             + script["ir_to_dr"] \
                             + self._tmstail(bus, readnonce_push_dr) \
                             + script["leave_shift"] \
                             + script["shift_dr"]
    script["readnonce_pull"] = self._tmstail(bus, clock * readnonce_pull_len)
    script["readnonce_tail"] = script["leave_shift"]
    self.initialized[bus] = True
    
    
  def register(self, device):
    device.index = len(self.devices)
    self.devices.append(device)
      

  def set_ir(self, device, ir):
    script = self.jtagscript[device.bus]
    hc = script["highclock"]
    self._write(script["shift_ir"] + self._tmstail(device.bus, hc * device.irhead + ir + hc * device.irtail) + script["leave_shift"])
    
    
  def get_ir(self, device):
    script = self.jtagscript[device.bus]
    hc = script["highclock"]
    self._write(script["shift_ir"] + hc * device.irhead)
    data = self._shift(device.bus, hc * device.irlength)
    self._write(self._tmstail(device.bus, hc * max(1, device.irtail)) + script["leave_shift"])
    return data
    
    
  def set_dr(self, device, dr):
    script = self.jtagscript[device.bus]
    clock = script["clock"]
    self._write(script["shift_dr"] + self._tmstail(device.bus, dr + script["clock"] * device.drtail) + script["leave_shift"])
    
    
  def get_dr(self, device, length):
    script = self.jtagscript[device.bus]
    self._write(script["shift_dr"] + script["clock"] * device.drhead)
    data = self._shift(device.bus, self._tmstail(device.bus, script["clock"] * length))
    self._write(script["leave_shift"])
    return data
    
    
  def format_dr(self, bus, bits):
    script = self.jtagscript[bus]
    clock = script["clock"]
    hc = script["highclock"]
    result = b""
    for bit in bits: result += hc if bit else clock
    return result
    
    
  def _tmstail(self, bus, data):
    script = self.jtagscript[bus]
    clocklen = script["clocklen"]
    tmsmask = script["tmsmask"]
    result = data[:-clocklen]
    for byte in data[-clocklen:]: result += int2byte(byte2int(byte) | tmsmask)
    return result
    
    
  def _purge_buffers(self):
    self.handle.controlMsg(0x40, 0, None, 1, self.index)
    self.handle.controlMsg(0x40, 0, None, 2, self.index)
    
    
  def _set_bit_mode(self, mask, mode):
    self.handle.controlMsg(0x40, 0xb, None, (mode << 8) | mask, self.index)
  
  
  def _get_bit_mode(self):
    return struct.unpack("B", bytes(bytearray(self.handle.controlMsg(0xc0, 0xc, 1, 0, self.index))))[0]
    
  
  def _switch_async(self):
    self._set_bit_mode(self.outmask, 0)
    self._set_bit_mode(self.outmask, 1)
    
    
  def _switch_sync(self):
    self._set_bit_mode(self.outmask, 0)
    self._set_bit_mode(self.outmask, 4)
    
    
  def _write(self, data):
    size = len(data)
    offset = 0
    while offset < size:
      write_size = min(4096, size - offset)
      ret = self.handle.bulkWrite(self.outep, data[offset : offset + write_size])
      offset = offset + ret
    
    
  def _read(self, size, timeout = 1):
    timeout = timeout + time.time()
    data = b""
    offset = 0
    while offset < size and time.time() < timeout:
      ret = bytes(bytearray(self.handle.bulkRead(self.inep, min(64, size - offset + 2))))
      data += ret[2:]
      offset += len(ret) - 2
    return data
    
    
  def _bidi(self, data, timeout = 1):
    recv = b""
    offset = 0
    self._switch_sync()
    self._purge_buffers()
    while offset < len(data):
      bytes = min(124, len(data) - offset)
      self._write(data[offset : offset + bytes])
      recv += self._read(bytes, timeout)
      offset += bytes
    self._switch_async()
    return recv
    
    
  def _shift(self, bus, data, timeout = 1):
    script = self.jtagscript[bus]
    tdomask = script["tdomask"]
    clocklen = script["clocklen"]
    data = self._bidi(data + data[-1:], timeout)
    result = []
    for i in range(clocklen, len(data), clocklen):
      result.append(1 if byte2int(data[i]) & tdomask else 0)
    return result
    
    
  def _set_cbus_bits(self, outmask, data):
    self._set_bit_mode((outmask << 4) | data, 0x20)

    
  def _get_cbus_bits(self):
    return self._get_bit_mode()
    
    
  def get_fpga_count(self):
    return len(self.devices)

  
  def send_job(self, fpga, job):
    self.devices[fpga].send_job(job)

  
  def set_speed(self, fpga, speed):
    self.devices[fpga].set_speed(speed)

  
  def get_speed(self, fpga):
    return self.devices[fpga].get_speed()

  
  def read_nonces(self):
    nonces = {}
    for bus in self.jtagscript:
      script = self.jtagscript[bus]
      if not self.initialized[bus]: continue
      with self.lock:
        self._write(script["readnonce_head"])
        data = self._shift(bus, script["readnonce_pull"])
        self._write(script["readnonce_tail"])
      for device in self.busdevices[bus]:
        if not device.usable:
          data = data[1:]
          continue
        slice = data[:device.readnonce_pull_len]
        data = data[device.readnonce_pull_len:]
        nonce = device.parse_nonce(slice)
        if nonce is not None: nonces[device.index] = nonce
    return nonces
    
    
  def read_temperatures(self):
    temps = {}
    
    if self.boardtype == "X6500":
      with self.lock:
        self._set_cbus_bits(0xc, 0x4)
        self._set_cbus_bits(0xc, 0xc)
        self._set_cbus_bits(0xc, 0x4)
        self._set_cbus_bits(0xc, 0xc)
        self._set_cbus_bits(0xc, 0x0)
        data0 = 0
        data1 = 0
        for i in range(16):
          self._set_cbus_bits(0xc, 0x8)
          data = self._get_cbus_bits()
          data0 = (data0 << 1) | (data & 1)
          data1 = (data1 << 1) | ((data >> 1) & 1)
          self._set_cbus_bits(0xc, 0x0)
        self._set_cbus_bits(0xc, 0x4)
        self._set_cbus_bits(0xc, 0xc)
        self._set_cbus_bits(0xc, 0x4)
        self._switch_async()
      if data0 != 0xffff and data0 != 0:
        if ((data0 >> 15) & 1) == 1: data0 -= (1 << 16)
        temps[0] = (data0 >> 2) * 0.03125
      if data1 != 0xffff and data1 != 0:
        if ((data1 >> 15) & 1) == 1: data1 -= (1 << 16)
        temps[1] = (data1 >> 2) * 0.03125
          
    return temps
########NEW FILE########
__FILENAME__ = ftdijtaghotplug
# Modular Python Bitcoin Miner
# Copyright (C) 2011-2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##########################################################
# Generic FTDI JTAG bitbanging hotplug controller module #
##########################################################



import traceback
from threading import Condition, Thread
from core.baseworker import BaseWorker
from .ftdijtagworker import FTDIJTAGWorker



# Worker main class, referenced from __init__.py
class FTDIJTAGHotplugWorker(BaseWorker):
  
  version = "theseven.ftdijtag hotplug manager v0.1.0beta"
  default_name = "FTDIJTAG hotplug manager"
  can_autodetect = True
  settings = dict(BaseWorker.settings, **{
    "takeover": {"title": "Reset board if it appears to be in use", "type": "boolean", "position": 1200},
    "firmware": {"title": "Firmware file location", "type": "string", "position": 1400},
    "blacklist": {
      "title": "Board list type",
      "type": "enum",
      "values": [
        {"value": True, "title": "Blacklist"},
        {"value": False, "title": "Whitelist"},
      ],
      "position": 2000
    },
    "boards": {
      "title": "Board list",
      "type": "list",
      "element": {"title": "Serial number", "type": "string"},
      "position": 2100
    },
    "scaninterval": {"title": "Bus scan interval", "type": "float", "position": 2200},
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 3000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 3100},
    "tempwarning": {"title": "Warning temperature", "type": "int", "position": 4000},
    "tempcritical": {"title": "Critical temperature", "type": "int", "position": 4100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 4200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 4300},
    "warmupstepshares": {"title": "Shares per warmup step", "type": "int", "position": 4400},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 4500},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 5100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 5200},
  })
  
  
  @classmethod
  def autodetect(self, core):
    try:
      import usb
      found = False
      try:
        for bus in usb.busses():
          for dev in bus.devices:
            if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
              try:
                handle = dev.open()
                manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                product = handle.getString(dev.iProduct, 100).decode("latin1")
                serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner") or (manufacturer == "BTCFPGA" and product == "ModMiner"):
                  try:
                    configuration = dev.configurations[0]
                    interface = configuration.interfaces[0][0]
                    handle.setConfiguration(configuration.value)
                    handle.claimInterface(interface.interfaceNumber)
                    handle.releaseInterface()
                    handle.setConfiguration(0)
                    found = True
                    break
                  except: pass
              except: pass
          if found: break
      except: pass
      if found: core.add_worker(self(core))
    except: pass
    
    
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Initialize bus scanner wakeup event
    self.wakeup = Condition()

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(FTDIJTAGHotplugWorker, self).__init__(core, state)

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGHotplugWorker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "takeover" in self.settings: self.settings.takeover = True
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/theseven/ftdijtag/firmware/"
    if not "blacklist" in self.settings: self.settings.blacklist = True
    if self.settings.blacklist == "false": self.settings.blacklist = False
    else: self.settings.blacklist = not not self.settings.blacklist
    if not "boards" in self.settings: self.settings.boards = []
    if not "initialspeed" in self.settings: self.settings.initialspeed = 150
    self.settings.initialspeed = min(max(self.settings.initialspeed, 4), 250)
    if not "maximumspeed" in self.settings: self.settings.maximumspeed = 200
    self.settings.maximumspeed = min(max(self.settings.maximumspeed, 4), 300)
    if not "tempwarning" in self.settings: self.settings.tempwarning = 45
    self.settings.tempwarning = min(max(self.settings.tempwarning, 0), 60)
    if not "tempcritical" in self.settings: self.settings.tempcritical = 55
    self.settings.tempcritical = min(max(self.settings.tempcritical, 0), 80)
    if not "invalidwarning" in self.settings: self.settings.invalidwarning = 2
    self.settings.invalidwarning = min(max(self.settings.invalidwarning, 1), 10)
    if not "invalidcritical" in self.settings: self.settings.invalidcritical = 10
    self.settings.invalidcritical = min(max(self.settings.invalidcritical, 1), 50)
    if not "warmupstepshares" in self.settings: self.settings.warmupstepshares = 5
    self.settings.warmupstepshares = min(max(self.settings.warmupstepshares, 1), 10000)
    if not "speedupthreshold" in self.settings: self.settings.speedupthreshold = 100
    self.settings.speedupthreshold = min(max(self.settings.speedupthreshold, 50), 10000)
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    if not "scaninterval" in self.settings or not self.settings.scaninterval: self.settings.scaninterval = 10
    # Push our settings down to our children
    fields = ["takeover", "firmware", "initialspeed", "maximumspeed", "tempwarning", "tempcritical", "invalidwarning",
              "invalidcritical", "warmupstepshares", "speedupthreshold", "jobinterval", "pollinterval"]
    for child in self.children:
      for field in fields: child.settings[field] = self.settings[field]
      child.apply_settings()
    # Rescan the bus immediately to apply the new settings
    with self.wakeup: self.wakeup.notify()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGHotplugWorker, self)._reset()


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGHotplugWorker, self)._start()
    # Initialize child map
    self.childmap = {}
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGHotplugWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(10)
    # Shut down child workers
    while self.children:
      child = self.children.pop(0)
      try:
        self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
        child.stop()
      except Exception as e:
        self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")

      
  # Main thread entry point
  # This thread is responsible for scanning for boards and spawning worker modules for them
  def main(self):
    import usb

    # Loop until we are shut down
    while not self.shutdown:
      try:
        boards = {}
        for bus in usb.busses():
          for dev in bus.devices:
            if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
              try:
                handle = dev.open()
                manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                product = handle.getString(dev.iProduct, 100).decode("latin1")
                serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                boardtype = None
                if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner"):
                  boardtype = "X6500"
                elif manufacturer == "BTCFPGA" and product == "ModMiner":
                  boardtype = "ModMiner"
                if boardtype:
                  try:
                    configuration = dev.configurations[0]
                    interface = configuration.interfaces[0][0]
                    handle.setConfiguration(configuration.value)
                    handle.claimInterface(interface.interfaceNumber)
                    handle.releaseInterface()
                    handle.setConfiguration(0)
                    available = True
                  except: available = False
                  boards[serial] = (available, boardtype)
              except: pass
                
        for serial in boards.keys():
          if self.settings.blacklist:
            if serial in self.settings.boards: del boards[serial]
          else:
            if serial not in self.settings.boards: del boards[serial]
                
        kill = []
        for serial, child in self.childmap.items():
          if not serial in boards:
            kill.append((serial, child))
            
        for serial, child in kill:
          try:
            self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
            child.stop()
          except Exception as e:
            self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
          childstats = child.get_statistics()
          fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
          for field in fields: self.stats[field] += childstats[field]
          try: self.child.destroy()
          except: pass
          del self.childmap[serial]
          try: self.children.remove(child)
          except: pass
                
        for serial, (available, boardtype) in boards.items():
          if serial in self.childmap: continue
          if not available and self.settings.takeover:
            try:
              for bus in usb.busses():
                if available: break
                for dev in bus.devices:
                  if available: break
                  if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
                    handle = dev.open()
                    manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                    product = handle.getString(dev.iProduct, 100).decode("latin1")
                    _serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                    if ((manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner") or (manufacturer == "BTCFPGA" and product == "ModMiner")) and _serial == serial:
                      handle.reset()
                      time.sleep(1)
                      configuration = dev.configurations[0]
                      interface = configuration.interfaces[0][0]
                      handle.setConfiguration(configuration.value)
                      handle.claimInterface(interface.interfaceNumber)
                      handle.releaseInterface()
                      handle.setConfiguration(0)
                      handle.reset()
                      time.sleep(1)
                      available = True
            except: pass
          if available:
            child = FTDIJTAGWorker(self.core)
            child.settings.name = boardtype + " board " + serial
            child.settings.serial = serial
            fields = ["takeover", "firmware", "initialspeed", "maximumspeed", "tempwarning", "tempcritical", "invalidwarning",
                      "invalidcritical", "warmupstepshares",  "speedupthreshold", "jobinterval", "pollinterval"]
            for field in fields: child.settings[field] = self.settings[field]
            child.apply_settings()
            self.childmap[serial] = child
            self.children.append(child)
            try:
              self.core.log(self, "Starting up worker %s...\n" % (child.settings.name), 800)
              child.start()
            except Exception as e:
              self.core.log(self, "Could not start worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
              
      except: self.core.log(self, "Caught exception: %s\n" % traceback.format_exc(), 100, "rB")
          
      with self.wakeup: self.wakeup.wait(self.settings.scaninterval)

########NEW FILE########
__FILENAME__ = ftdijtagworker
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



########################################################
# Generic FTDI JTAG bitbanging worker interface module #
########################################################



import usb
import time
import struct
import traceback
from multiprocessing import Pipe
from threading import RLock, Condition, Thread
from binascii import hexlify, unhexlify
from core.baseworker import BaseWorker
from core.job import ValidationJob
from .boardproxy import FTDIJTAGBoardProxy
try: from queue import Queue
except: from Queue import Queue



# Worker main class, referenced from __init__.py
class FTDIJTAGWorker(BaseWorker):
  
  version = "theseven.ftdijtag worker v0.1.0"
  default_name = "Untitled FTDIJTAG worker"
  settings = dict(BaseWorker.settings, **{
    "serial": {"title": "Board serial number", "type": "string", "position": 1000},
    "takeover": {"title": "Reset board if it appears to be in use", "type": "boolean", "position": 1200},
    "firmware": {"title": "Firmware file location", "type": "string", "position": 1400},
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 2000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 2100},
    "tempwarning": {"title": "Warning temperature", "type": "int", "position": 3000},
    "tempcritical": {"title": "Critical temperature", "type": "int", "position": 3100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 3200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 3300},
    "warmupstepshares": {"title": "Shares per warmup step", "type": "int", "position": 3400},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 3500},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 4100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 4200},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(FTDIJTAGWorker, self).__init__(core, state)

    # Initialize proxy access locks and wakeup event
    self.lock = RLock()
    self.transactionlock = RLock()
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGWorker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "takeover" in self.settings: self.settings.takeover = False
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/theseven/ftdijtag/firmware/"
    if not "initialspeed" in self.settings: self.settings.initialspeed = 150
    self.settings.initialspeed = min(max(self.settings.initialspeed, 4), 250)
    if not "maximumspeed" in self.settings: self.settings.maximumspeed = 200
    self.settings.maximumspeed = min(max(self.settings.maximumspeed, 4), 300)
    if not "tempwarning" in self.settings: self.settings.tempwarning = 45
    self.settings.tempwarning = min(max(self.settings.tempwarning, 0), 60)
    if not "tempcritical" in self.settings: self.settings.tempcritical = 55
    self.settings.tempcritical = min(max(self.settings.tempcritical, 0), 80)
    if not "invalidwarning" in self.settings: self.settings.invalidwarning = 2
    self.settings.invalidwarning = min(max(self.settings.invalidwarning, 1), 10)
    if not "invalidcritical" in self.settings: self.settings.invalidcritical = 10
    self.settings.invalidcritical = min(max(self.settings.invalidcritical, 1), 50)
    if not "warmupstepshares" in self.settings: self.settings.warmupstepshares = 5
    self.settings.warmupstepshares = min(max(self.settings.warmupstepshares, 1), 10000)
    if not "speedupthreshold" in self.settings: self.settings.speedupthreshold = 100
    self.settings.speedupthreshold = min(max(self.settings.speedupthreshold, 50), 10000)
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    # We can't switch the device on the fly, so trigger a restart if it changed.
    # self.serial is a cached copys of self.settings.serial
    if self.started and self.settings.serial != self.serial: self.async_restart()
    # We need to inform the proxy about a poll interval change
    if self.started and self.settings.pollinterval != self.pollinterval: self._notify_poll_interval_changed()
    for child in self.children: child.apply_settings()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.serial = None
    self.pollinterval = None


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGWorker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.serial = self.settings.serial
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Ping the proxy, otherwise the main thread might be blocked and can't wake up.
    try: self._proxy_message("ping")
    except: pass
    # Wait for the main thread to terminate, which in turn kills the child workers.
    self.mainthread.join(10)

      
  # Main thread entry point
  # This thread is responsible for booting the individual FPGAs and spawning worker threads for them
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()
        
        # Check if we have a device serial number
        if not self.serial: raise Exception("Device serial number not set!")
        
        # Try to start the board proxy
        proxy_rxconn, self.txconn = Pipe(False)
        self.rxconn, proxy_txconn = Pipe(False)
        self.pollinterval = self.settings.pollinterval
        self.proxy = FTDIJTAGBoardProxy(proxy_rxconn, proxy_txconn, self.serial, self.settings.takeover,
                                   self.settings.firmware, self.pollinterval)
        self.proxy.daemon = True
        self.proxy.start()
        proxy_txconn.close()
        self.response = None
        self.response_queue = Queue()
        
        # Tell the board proxy to connect to the board
        self._proxy_message("connect")
        
        while not self.shutdown:
          data = self.rxconn.recv()
          if data[0] == "log": self.core.log(self, "Proxy: %s" % data[1], data[2], data[3])
          elif data[0] == "ping": self._proxy_message("pong")
          elif data[0] == "pong": pass
          elif data[0] == "dying": raise Exception("Proxy died!")
          elif data[0] == "response": self.response_queue.put(data[1:])
          elif data[0] == "started_up": self._notify_proxy_started_up(*data[1:])
          elif data[0] == "nonce_found": self._notify_nonce_found(*data[1:])
          elif data[0] == "temperatures_read": self._notify_temperatures_read(*data[1:])
          else: raise Exception("Proxy sent unknown message: %s" % str(data))
        
        
      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        try:
          for i in range(100): self.response_queue.put(None)
        except: pass
        while self.children:
          try:
            child = self.children.pop(0)
            child.stop()
            childstats = child.get_statistics()
            fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
            for field in fields: self.stats[field] += childstats[field]
            try: self.child.destroy()
            except: pass
          except: pass
        try: self._proxy_message("shutdown")
        except: pass
        try: self.proxy.join(4)
        except: pass
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)

        
  def _proxy_message(self, *args):
    with self.lock:
      self.txconn.send(args)


  def _proxy_transaction(self, *args):
    with self.transactionlock:
      with self.lock:
        self.txconn.send(args)
      return self.response_queue.get()
      
      
  def _notify_poll_interval_changed(self):
    self.pollinterval = self.settings.pollinterval
    try: self._proxy_message("set_pollinterval", self.pollinterval)
    except: pass
    
    
  def _notify_proxy_started_up(self, fpgacount):
    # The proxy is up and running, start up child workers
    for i in range(fpgacount):
        self.children.append(FTDIJTAGFPGA(self.core, self, i))
    for child in self.children: child.start()

    
  def _notify_nonce_found(self, fpga, now, nonce):
    if self.children and fpga < len(self.children):
      try: self.children[fpga].notify_nonce_found(now, nonce)
      except Exception as e: self.children[fpga].error = e


  def _notify_temperatures_read(self, temperatures):
    if self.children:
      for fpga in temperatures:
        if len(self.children) > fpga:
          self.children[fpga].stats.temperature = temperatures[fpga]
          if temperatures[fpga]:
            self.core.event(350, self.children[fpga], "temperature", temperatures[fpga] * 1000, "%f \xc2\xb0C" % temperatures[fpga], worker = self.children[fpga])

      
  def send_job(self, fpga, job):
    return self._proxy_transaction("send_job", fpga, job.midstate + job.data[64:76])


  def set_speed(self, fpga, speed):
    self._proxy_message("set_speed", fpga, speed)


  def get_speed(self, fpga):
    return self._proxy_transaction("get_speed", fpga)[0]



# FPGA handler main class, child worker of FTDIJTAGWorker
class FTDIJTAGFPGA(BaseWorker):

  # Constructor, gets passed a reference to the miner core, the FTDIJTAGWorker,
  # its FPGA id, and the bitstream version currently running on that FPGA
  def __init__(self, core, parent, fpga):
    self.parent = parent
    self.fpga = fpga

    # Let our superclass do some basic initialization
    super(FTDIJTAGFPGA, self).__init__(core, None)
    
    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()


    
  # Validate settings, mostly coping them from our parent
  # Called from the constructor and after every settings change on the parent.
  def apply_settings(self):
    self.settings.name = "%s FPGA%d" % (self.parent.settings.name, self.fpga)
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGFPGA, self).apply_settings()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGFPGA, self)._reset()
    self.stats.temperature = None
    self.initialramp = True


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGFPGA, self)._start()
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.parent.settings.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGFPGA, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(1)

      
  # This function should interrupt processing of the specified job if possible.
  # This is necesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast. We don't care whether it's a
  # graceful cancellation for this module because the work upload overhead is low. 
  def notify_canceled(self, job, graceful):
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.wakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.wakeup.notify()

        
  # Report custom statistics.
  def _get_statistics(self, stats, childstats):
    # Let our superclass handle everything that isn't specific to this worker module
    super(FTDIJTAGFPGA, self)._get_statistics(stats, childstats)
    stats.temperature = self.stats.temperature


  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()
        self.error = None

        # Initialize megahashes per second to zero, will be measured later.
        self.stats.mhps = 0

        # Job that the device is currently working on, or that is currently being uploaded.
        # This variable is used by BaseWorker to figure out the current work source for statistics.
        self.job = None
        # Job that was previously being procesed. Has been destroyed, but there might be some late nonces.
        self.oldjob = None

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Eat up leftover wakeups
        self.wakeup.wait(0)
        # Honor shutdown flag (in case it was a real wakeup)
        if self.shutdown: break
        # Set validation success flag to false
        self.checksuccess = False
        
        # Initialize hash rate tracking data
        self.lasttime = None
        self.lastnonce = None

        # Initialize malfunction tracking data
        self.recentshares = 0
        self.recentinvalid = 0

        # Configure core clock, if the bitstream supports that
        self._set_speed(self.parent.settings.initialspeed)
        
        # Send validation job to device
        job = ValidationJob(self.core, unhexlify(b"00000001c3bf95208a646ee98a58cf97c3a0c4b7bf5de4c89ca04495000005200000000024d1fff8d5d73ae11140e4e48032cd88ee01d48c67147f9a09cd41fdec2e25824f5c038d1a0b350c5eb01f04"))
        self._sendjob(job)

        # Wait for the validation job to complete. The wakeup flag will be
        # set by the listener thread when the validation job completes.
        self.wakeup.wait((100. / self.stats.mhps) + 1)
        # Honor shutdown flag
        if self.shutdown: break
        # We woke up, but the validation job hasn't succeeded in the mean time.
        # This usually means that the wakeup timeout has expired.
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")

        # Main loop, continues until something goes wrong or we're shutting down.
        while not self.shutdown:

          # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
          # Blocks until one is available. Because of this we need to release the
          # wakeup lock temporarily in order to avoid possible deadlocks.
          self.wakeup.release()
          job = self.core.get_job(self, self.jobinterval + 2)
          self.wakeup.acquire()
          if self.error: raise self.error
          
          # If a new block was found while we were fetching that job, just discard it and get a new one.
          if job.canceled:
            job.destroy()
            continue

          # Upload the job to the device
          self._sendjob(job)
          if self.error: raise self.error
          
          # Go through the safety checks and reduce the clock if necessary
          self.safetycheck()
          
          # If the job was already caught by a long poll while we were uploading it,
          # jump back to the beginning of the main loop in order to immediately fetch new work.
          # Don't check for the canceled flag before the job was accepted by the device,
          # otherwise we might get out of sync.
          if self.job.canceled: continue
          # Wait while the device is processing the job. If nonces are sent by the device, they
          # will be processed by the listener thread. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)
          if self.error: raise self.error

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        try: self.wakeup.release()
        except: pass
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, restart the parent worker as well.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5:
              self.parent.async_restart()
              return
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  def notify_nonce_found(self, now, nonce):
    # Snapshot the current jobs to avoid race conditions
    oldjob = self.oldjob
    newjob = self.job
    # If there is no job, this must be a leftover from somewhere, e.g. previous invocation
    # or reiterating the keyspace because we couldn't provide new work fast enough.
    # In both cases we can't make any use of that nonce, so just discard it.
    if not oldjob and not newjob: return
    # Pass the nonce that we found to the work source, if there is one.
    # Do this before calculating the hash rate as it is latency critical.
    job = None
    if newjob:
      if newjob.nonce_found(nonce, oldjob): job = newjob
    if not job and oldjob:
      if oldjob.nonce_found(nonce): job = oldjob
    self.recentshares += 1
    nonceval = struct.unpack("<I", nonce)[0]
    if not job:
      self.recentinvalid += 1
      if not nonceval: raise Exception("Firmware might have crashed, restarting!")
    if isinstance(newjob, ValidationJob):
      # This is a validation job. Validate that the nonce is correct, and complain if not.
      if newjob.nonce != nonce:
        raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (hexlify(nonce).decode("ascii"), hexlify(newjob.nonce).decode("ascii")))
      else:
        # The nonce was correct
        with self.wakeup:
          self.checksuccess = True
          self.wakeup.notify()
      

  # This function uploads a job to the device
  def _sendjob(self, job):
    # Move previous job to oldjob, and new one to job
    self.oldjob = self.job
    self.job = job
    # Send it to the FPGA
    start, now = self.parent.send_job(self.fpga, job)
    # Calculate how long the old job was running
    if self.oldjob:
      if self.oldjob.starttime:
        self.oldjob.hashes_processed((now - self.oldjob.starttime) * self.stats.mhps * 1000000)
      self.oldjob.destroy()
    self.job.starttime = now

    
  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job != None:
      if self.job.starttime:
        self.job.hashes_processed((now - self.job.starttime) * self.stats.mhps * 1000000)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.oldjob = self.job
      self.job.destroy()
      self.job = None
  
  
  # Check the invalid rate and temperature, and reduce the FPGA clock if these exceed safe values
  def safetycheck(self):
    
    warning = False
    critical = False
    if self.recentinvalid >= self.parent.settings.invalidwarning: warning = True
    if self.recentinvalid >= self.parent.settings.invalidcritical: critical = True
    if self.stats.temperature:
      if self.stats.temperature > self.parent.settings.tempwarning: warning = True    
      if self.stats.temperature > self.parent.settings.tempcritical: critical = True    

    threshold = self.parent.settings.warmupstepshares if self.initialramp and not self.recentinvalid else self.parent.settings.speedupthreshold

    if warning: self.core.log(self, "Detected overload condition!\n", 200, "y")
    if critical: self.core.log(self, "Detected CRITICAL condition!\n", 100, "rB")

    if critical:
      speedstep = -20
      self.initialramp = False
    elif warning:
      speedstep = -2
      self.initialramp = False
    elif not self.recentinvalid and self.recentshares >= threshold:
      speedstep = 2
    else: speedstep = 0    

    if speedstep: self._set_speed(self.stats.mhps + speedstep)

    if speedstep or self.recentshares >= threshold:
      self.recentinvalid = 0
      self.recentshares = 0
    
   
  def _set_speed(self, speed):
    speed = min(max(speed, 4), self.parent.settings.maximumspeed)
    if self.stats.mhps == speed: return
    if speed == self.parent.settings.maximumspeed: self.initialramp = False
    self.core.log(self, "%s: Setting clock speed to %.2f MHz...\n" % ("Warmup" if self.initialramp else "Tracking", speed), 500, "B")
    self.parent.set_speed(self.fpga, speed)
    self.stats.mhps = self.parent.get_speed(self.fpga)
    self._update_job_interval()
    if self.stats.mhps != speed:
      self.core.log(self, "Setting clock speed failed!\n", 100, "rB")
   
   
  def _update_job_interval(self):
    self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
    # Calculate the time that the device will need to process 2**32 nonces.
    # This is limited at 60 seconds in order to have some regular communication,
    # even with very slow devices (and e.g. detect if the device was unplugged).
    interval = min(60, 2**32 / 1000000. / self.stats.mhps)
    # Add some safety margin and take user's interval setting (if present) into account.
    self.jobinterval = min(self.parent.settings.jobinterval, max(0.5, interval * 0.8 - 1))
    self.core.log(self, "Job interval: %f seconds\n" % self.jobinterval, 400, "B")
    # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
    self.jobs_per_second = 1. / self.jobinterval
    self.core.notify_speed_changed(self)
  

########NEW FILE########
__FILENAME__ = icarusworker
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##################################
# Icarus worker interface module #
##################################



import time
import struct
import traceback
from threading import Condition, Thread
from binascii import hexlify, unhexlify
from core.baseworker import BaseWorker
from core.job import ValidationJob



# Worker main class, referenced from __init__.py
class IcarusWorker(BaseWorker):
  
  version = "theseven.icarus worker v0.1.0"
  default_name = "Untitled Icarus worker"
  settings = dict(BaseWorker.settings, **{
    "port": {"title": "Port", "type": "string", "position": 1000},
    "baudrate": {"title": "Baud rate", "type": "int", "position": 1100},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 1200},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(IcarusWorker, self).__init__(core, state)

    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(IcarusWorker, self).apply_settings()
    # Pretty much self-explanatory...
    if not "port" in self.settings or not self.settings.port: self.settings.port = "/dev/ttyUSB0"
    if not "baudrate" in self.settings or not self.settings.baudrate: self.settings.baudrate = 115200
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    # We can't change the port name or baud rate on the fly, so trigger a restart if they changed.
    # self.port/self.baudrate are cached copys of self.settings.port/self.settings.baudrate
    if self.started and (self.settings.port != self.port or self.settings.baudrate != self.baudrate): self.async_restart()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(IcarusWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.port = None
    self.baudrate = None
#    # Initialize custom statistics. This is not neccessary for this worker module,
#    # but might be interesting for other modules, so it is kept here for reference.
#    self.stats.field1 = 0
#    self.stats.field2 = 0
#    self.stats.field3 = 0


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(IcarusWorker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.port = self.settings.port
    self.baudrate = self.settings.baudrate
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.settings.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(IcarusWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # The listener thread will hopefully die because the main thread closes the serial port handle.
    # Wait for the main thread to terminate, which in turn waits for the listener thread to die.
    self.mainthread.join(10)

      
  # This function should interrupt processing of the specified job if possible.
  # This is neccesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast.
  def notify_canceled(self, job, graceful):
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.wakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.wakeup.notify()

        
#  # Report custom statistics. This is not neccessary for this worker module,
#  # but might be interesting for other modules, so it is kept here for reference.
#  def _get_statistics(self, stats, childstats):
#    # Let our superclass handle everything that isn't specific to this worker module
#    super(IcarusWorker, self)._get_statistics(stats, childstats)
#    stats.field1 = self.stats.field1
#    stats.field2 = self.stats.field2 + childstats.calculatefieldsum("field2")
#    stats.field3 = self.stats.field3 + childstats.calculatefieldavg("field3")
        
        
  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()
        # Exception container: If an exception occurs in the listener thread, the listener thread
        # will store it here and terminate, and the main thread will rethrow it and then restart.
        self.error = None
        self.hasheswithoutshare = 0

        # Initialize megahashes per second to zero, will be measured later.
        self.stats.mhps = 0

        # Job that the device is currently working on, or that is currently being uploaded.
        # This variable is used by BaseWorker to figure out the current work source for statistics.
        self.job = None
        # Job that was previously being procesed. Has been destroyed, but there might be some late nonces.
        self.oldjob = None

        # Open the serial port
        import serial
        self.handle = serial.Serial(self.port, self.baudrate, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Set validation success flag to false
        self.checksuccess = False
        # Start device response listener thread
        self.listenerthread = Thread(None, self._listener, self.settings.name + "_listener")
        self.listenerthread.daemon = True
        self.listenerthread.start()

        # Send validation job to device
        job = ValidationJob(self.core, unhexlify(b"00000001c3bf95208a646ee98a58cf97c3a0c4b7bf5de4c89ca04495000005200000000024d1fff8d5d73ae11140e4e48032cd88ee01d48c67147f9a09cd41fdec2e25824f5c038d1a0b350c5eb01f04"))
        self._sendjob(job)

        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error

        # Wait for the validation job to complete. The wakeup flag will be set by the listener
        # thread when the validation job completes. 60 seconds should be sufficient for devices
        # down to about 2.6MH/s, for slower devices this timeout will need to be increased.
        self.wakeup.wait(60)
        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error
        # Honor shutdown flag
        if self.shutdown: break
        # We woke up, but the validation job hasn't succeeded in the mean time.
        # This usually means that the wakeup timeout has expired.
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")
        # self.stats.mhps has now been populated by the listener thread
        self.core.log(self, "Running at %f MH/s\n" % self.stats.mhps, 300, "B")
        # Calculate the time that the device will need to process 2**32 nonces.
        # This is limited at 60 seconds in order to have some regular communication,
        # even with very slow devices (and e.g. detect if the device was unplugged).
        interval = min(60, 2**32 / 1000000. / self.stats.mhps)
        # Add some safety margin and take user's interval setting (if present) into account.
        self.jobinterval = min(self.settings.jobinterval, max(0.5, interval * 0.8 - 1))
        self.core.log(self, "Job interval: %f seconds\n" % self.jobinterval, 400, "B")
        # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
        self.jobspersecond = 1. / self.jobinterval
        self.core.notify_speed_changed(self)

        # Main loop, continues until something goes wrong or we're shutting down.
        while not self.shutdown:

          # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
          # Blocks until one is available. Because of this we need to release the
          # wakeup lock temporarily in order to avoid possible deadlocks.
          self.wakeup.release()
          job = self.core.get_job(self, self.jobinterval + 2)
          self.wakeup.acquire()
          
          # If a new block was found while we were fetching that job, just discard it and get a new one.
          if job.canceled:
            job.destroy()
            continue

          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

          # Upload the job to the device
          self._sendjob(job)
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error
          # If the job was already caught by a long poll while we were uploading it,
          # jump back to the beginning of the main loop in order to immediately fetch new work.
          # Don't check for the canceled flag before the job was accepted by the device,
          # otherwise we might get out of sync.
          if self.job.canceled: continue
          # Wait while the device is processing the job. If nonces are sent by the device, they
          # will be processed by the listener thread. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
        # Make sure that the listener thread realizes that something went wrong
        self.error = e
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        # Release the wake lock to allow the listener thread to move. Ignore it if that goes wrong.
        try: self.wakeup.release()
        except: pass
        # Close the serial port handle, otherwise we can't reopen it after restarting.
        # This should hopefully also make reads on that port from the listener thread fail,
        # so that the listener thread will realize that it's supposed to shut down.
        try: self.handle.close()
        except: pass
        # Wait for the listener thread to terminate.
        # If it doens't within 5 seconds, continue anyway. We can't do much about that.
        try: self.listenerthread.join(5)
        except: pass
        # Set MH/s to zero again, the listener thread might have overwritten that.
        self.stats.mhps = 0
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, wait a bit longer until restarting the worker.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  # Device response listener thread
  def _listener(self):
    # Catch all exceptions and forward them to the main thread
    try:
      # Loop forever unless something goes wrong
      while True:
        # If the main thread has a problem, make sure we die before it restarts
        if self.error != None: break
        
        # If there were suspiciously many hashes without even a single share,
        # assume that PL2303 did it's job (i.e. serial port locked up),
        # and restart the board worker.
        if self.hasheswithoutshare > 16 * 2**32:
          raise Exception("Watchdog triggered: %.6f MHashes without share" % (self.hasheswithoutshare / 1000000.))

        # Try to read a response from the device
        nonce = self.handle.read(4)
        # If no response was available, retry
        if len(nonce) != 4: continue
        nonce = nonce[::-1]
        # Snapshot the current jobs to avoid race conditions
        newjob = self.job
        oldjob = self.oldjob
        # If there is no job, this must be a leftover from somewhere, e.g. previous invocation
        # or reiterating the keyspace because we couldn't provide new work fast enough.
        # In both cases we can't make any use of that nonce, so just discard it.
        if not oldjob and not newjob: return
        # Stop time measurement
        now = time.time()
        self.hasheswithoutshare = 0
        # Pass the nonce that we found to the work source, if there is one.
        # Do this before calculating the hash rate as it is latency critical.
        job = None
        if newjob:
          if newjob.nonce_found(nonce, oldjob): job = newjob
        if not job and oldjob:
          if oldjob.nonce_found(nonce): job = oldjob
        # If the nonce is too low, the measurement may be inaccurate.
        nonceval = struct.unpack("<I", nonce)[0] & 0x7fffffff
        if job and job.starttime and nonceval >= 0x04000000:
          # Calculate actual on-device processing time (not including transfer times) of the job.
          delta = (now - job.starttime) - 40. / self.baudrate
          # Calculate the hash rate based on the processing time and number of neccessary MHashes.
          # This assumes that the device processes all nonces (starting at zero) sequentially.
          self.stats.mhps = nonceval / 500000. / delta
          self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
        # This needs self.stats.mhps to be set.
        if isinstance(newjob, ValidationJob):
          # This is a validation job. Validate that the nonce is correct, and complain if not.
          if newjob.nonce != nonce:
            raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (hexlify(nonce).decode("ascii"), hexlify(newjob.nonce).decode("ascii")))
          else:
            # The nonce was correct. Wake up the main thread.
            with self.wakeup:
              self.checksuccess = True
              self.wakeup.notify()
        else:
          with self.wakeup:
            self._jobend(now)
            self.wakeup.notify()

    # If an exception is thrown in the listener thread...
    except Exception as e:
      # ...complain about it...
      self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      # ...put it into the exception container...
      self.error = e
      # ...wake up the main thread...
      with self.wakeup: self.wakeup.notify()
      # ...and terminate the listener thread.


  # This function uploads a job to the device
  def _sendjob(self, job):
    # Move previous job to oldjob, and new one to job
    self.oldjob = self.job
    self.job = job
    # Send it to the device
    now = time.time()
    self.handle.write(job.midstate[::-1] + b"\0" * 20 + job.data[75:63:-1])
    self.handle.flush()
    self.job.starttime = time.time()
    # Calculate how long the old job was running
    if self.oldjob and self.oldjob.starttime:
      if self.oldjob.starttime:
        hashes = (now - self.oldjob.starttime) * self.stats.mhps * 1000000
        self.hasheswithoutshare += hashes
        self.oldjob.hashes_processed(hashes)
      self.oldjob.destroy()

    
  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job:
      if self.job.starttime:
        hashes = (now - self.job.starttime) * self.stats.mhps * 1000000
        self.hasheswithoutshare += hashes
        self.job.hashes_processed(hashes)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.oldjob = self.job
      self.job.destroy()
      self.job = None

########NEW FILE########
__FILENAME__ = boardproxy
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



###############################################################
# ModMiner Quad worker out of process board access dispatcher #
###############################################################



import time
import signal
import traceback
from threading import RLock, Thread, Condition
from multiprocessing import Process
from .driver import MMQDevice



class MMQBoardProxy(Process):
  

  def __init__(self, rxconn, txconn, port, firmware, pollinterval):
    super(MMQBoardProxy, self).__init__()
    self.rxconn = rxconn
    self.txconn = txconn
    self.port = port
    self.firmware = firmware
    self.pollinterval = pollinterval


  def run(self):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    self.lock = RLock()
    self.wakeup = Condition()
    self.error = None
    self.pollingthread = None
    self.shutdown = False
  
    try:

      # Listen for setup commands
      while True:
        data = self.rxconn.recv()
        
        if data[0] == "connect": break
        
        else: raise Exception("Unknown setup message: %s" % str(data))
        
      # Connect to board
      self.device = MMQDevice(self, self.port, self.firmware)
      self.fpgacount = self.device.get_fpga_count()
      self.log("Found %i FPGA%s\n" % (self.fpgacount, 's' if self.fpgacount != 1 else ''), 500)
      if not self.fpgacount: raise Exception("No FPGAs detected!")
      
      # Start polling thread
      self.pollingthread = Thread(None, self.polling_thread, "polling_thread")
      self.pollingthread.daemon = True
      self.pollingthread.start()
      
      self.send("started_up", self.fpgacount)

      # Listen for commands
      while True:
        if self.error: raise self.error
      
        data = self.rxconn.recv()
        
        if data[0] == "shutdown": break

        elif data[0] == "ping": self.send("pong")

        elif data[0] == "pong": pass

        elif data[0] == "set_pollinterval":
          self.pollinterval = data[1]
          with self.wakeup: self.wakeup.notify()
        
        elif data[0] == "send_job":
          start = time.time()
          self.device.send_job(data[1], data[2])
          end = time.time()
          self.respond(start, end)
        
        elif data[0] == "read_reg":
          self.respond(self.device.read_reg(data[1], data[2]))
        
        elif data[0] == "write_reg":
          self.device.write_reg(data[1], data[2], data[3])
        
        elif data[0] == "set_speed":
          self.device.set_speed(data[1], data[2])
        
        elif data[0] == "get_speed":
          self.respond(self.device.get_speed(data[1]))
        
        else: raise Exception("Unknown message: %s" % str(data))
      
    except: self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
    finally:
      self.shutdown = True
      with self.wakeup: self.wakeup.notify()
      try: self.pollingthread.join(2)
      except: pass
      try: self.device.close()
      except: pass
      self.send("dying")
      
      
  def send(self, *args):
    with self.lock: self.txconn.send(args)
      
      
  def respond(self, *args):
    self.send("response", *args)
      
      
  def log(self, message, loglevel, format = ""):
    self.send("log", message, loglevel, format)
    
    
  def nonce_found(self, fpga, nonce):
    self.send("nonce_found", fpga, time.time(), nonce)
    
  
  def temperatures_read(self, temperatures):
    self.send("temperatures_read", temperatures)
    
    
  def error(self, exception):
    self.error = exception
    self.send("ping")
    
    
  def polling_thread(self):
    try:
      counter = 0
      while not self.shutdown:
        # Poll for nonces
        nonces = self.device.read_nonces()
        for fpga in nonces: self.nonce_found(fpga, nonces[fpga])
        
        counter += 1
        if counter >= 20:
          counter = 0
          self.temperatures_read(self.device.read_temperatures())
    
        with self.wakeup: self.wakeup.wait(self.pollinterval)
        
    except Exception as e:
      self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
      self.error = e
      # Unblock main thread
      self.send("ping")

########NEW FILE########
__FILENAME__ = driver
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#########################################
# ModMiner Quad worker low level driver #
#########################################



import time
import serial
import struct
from binascii import hexlify, unhexlify
from threading import RLock, Condition, Thread
try: from queue import Queue
except: from Queue import Queue



class DeviceException(Exception): pass



class Spartan6FPGA(object):

  
  def __init__(self, proxy, driver, id, idcode):
    self.proxy = proxy
    self.driver = driver
    self.id = id
    self.idcode = idcode
    self.usable = False
    self.speed = 0
    if idcode & 0xfffffff == 0x401d093: self.typename = "Xilinx Spartan 6 LX150 FPGA"
    elif idcode & 0xfffffff == 0x403d093: self.typename = "Xilinx Spartan 6 LX150T FPGA"
    else: self.typename = "Unknown Xilinx Spartan 6 FPGA (0x%08X)" % idcode
    self.name = "Device %d" % id
    
  
  def init(self):
    self._prepare_firmware()
    self.usercode = self.driver.get_usercode(self.id)
    if self.usercode != self.fwusercode: self._upload_firmware()
    self.usercode = self.driver.get_usercode(self.id)
    if self.usercode == 0xffffffff: raise DeviceException("USERCODE register not available!")
    self.firmware_rev = (self.usercode >> 8) & 0xff
    self.firmware_build = self.usercode & 0xf
    self.proxy.log("%s: Firmware version %d, build %d\n" % (self.name, self.firmware_rev, self.firmware_build), 500)
    self.usable = True
    self.driver.register(self)
    
    
  def _prepare_firmware(self):
    try:
      self.firmware = self.driver.firmware
      if self.firmware[-1] == "/": self.firmware += "%08x.bit" % (self.idcode & 0xfffffff)
      with open(self.firmware, "rb") as file:
        if struct.unpack(">H", file.read(2))[0] != 9: raise Exception("Bad firmware file format!")
        file.read(11)
        if file.read(1) != b"a": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwdesignname = file.read(bytes).decode("latin1").rstrip('\0')
        self.fwusercode = int(self.fwdesignname.split(';')[-1].split('=')[-1], base = 16)
        if file.read(1) != b"b": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwpart = file.read(bytes).decode("latin1").rstrip('\0')
        if file.read(1) != b"c": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwdate = file.read(bytes).decode("latin1").rstrip('\0')
        if file.read(1) != b"d": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwtime = file.read(bytes).decode("latin1").rstrip('\0')
        if file.read(1) != b"e": raise Exception("Bad firmware file format!")
        self.fwlength = struct.unpack(">I", file.read(4))[0]
        self.fwoffset = file.tell()
      self.proxy.log("%s: Firmware file %s information:\n" % (self.name, self.firmware), 500, "B")
      self.proxy.log("%s:   Design name: %s\n" % (self.name, self.fwdesignname), 500)
      self.proxy.log("%s:   Version: %d, build %d\n" % (self.name, (self.fwusercode >> 8) & 0xff, self.fwusercode & 0xff), 500)
      self.proxy.log("%s:   Build time: %s %s\n" % (self.name, self.fwdate, self.fwtime), 500)
      self.proxy.log("%s:   Part number: %s\n" % (self.name, self.fwpart), 500)
      self.proxy.log("%s:   Bitstream length: %d bytes\n" % (self.name, self.fwlength), 500)
      idcodemap = {"6slx150fgg484": 0x401d093, "6slx150tfgg676": 0x403d093}
      if not self.fwpart in idcodemap or idcodemap[self.fwpart] != self.idcode & 0xfffffff:
        raise Exception("Firmware is for wrong device type!")
      if self.fwusercode == 0xffffffff: raise Exception("Firmware does not support USERCODE!")
    except Exception as e: raise DeviceException(str(e))
    
  def _upload_firmware(self):
    with open(self.firmware, "rb") as file:
      file.seek(self.fwoffset)
      self.proxy.log("%s: Programming FPGA...\n" % self.name, 300, "B")
      starttime = time.time()
      with self.driver.lock:
        if struct.unpack("B", self.driver._txn(struct.pack("<BBI", 5, self.id, self.fwlength), 1))[0] != 1:
          raise DeviceException("Failed to start bitstream upload!")
        bytesleft = self.fwlength
        bytes = 0
        while bytesleft:
          chunksize = min(32, bytesleft)
          bytesleft -= chunksize
          chunk = file.read(chunksize)
          if struct.unpack("B", self.driver._txn(chunk, 1))[0] != 1:
            raise DeviceException("Error during bitstream upload!")
          bytes += chunksize
          if not bytes & 0x3ffff:
            percent = 100. * bytes / self.fwlength
            speed = bytes / (time.time() - starttime) / 1024.
            self.proxy.log("%s: Programming: %.1f%% done, %.1f kiB/s\n" % (self.name, percent, speed), 300, "B")
    if struct.unpack("B", self.driver._txn(b"", 1))[0] != 1: raise DeviceException("FPGA didn't accept bitstream!")
    
    
  def parse_nonce(self, data):
    value = struct.unpack("<I", data)[0]
    if value != 0xffffffff: return data

    
    
class UnknownDevice(object):

  
  def __init__(self, proxy, driver, bus, id, idcode):
    self.proxy = proxy
    self.driver = driver
    self.bus = bus
    self.id = id
    self.idcode = idcode
    self.usable = False
    self.typename = "Unknown Device (IDCODE 0x%08X)" % idcode
    self.name = "%s Device %d" % (bus, id)
    
    
  def init(self): pass

    
    
idcodemap = {
  0x401d093: {"handler": Spartan6FPGA},
  0x403d093: {"handler": Spartan6FPGA},
}



class MMQDevice(object):
  

  def __init__(self, proxy, port, firmware):
    self.lock = RLock()
    self.proxy = proxy
    self.port = port
    self.firmware = firmware
    self.handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
    self.handle.write(b"\0" + b"\xff" * 45)
    self.handle.write(b"\0")
    result = self.handle.read(64)
    if result[-1:] != b"\0": raise Exception("Failed to sync interface: %s" % (hexlify(result).decode("ascii") if result else str(result)))
    self.handle.write(b"\x01")
    data = b""
    while True:
      byte = self.handle.read(1)
      if byte == b"\0": break
      data += byte
    proxy.log("Device model: %s\n" % data.decode("utf_8"), 400)
    devicecount = struct.unpack("B", self._txn(struct.pack("B", 2), 1))[0]
    proxy.log("Number of chips: %s\n" % devicecount, 450)
    self.devices = []
    devices = []
    for i in range(devicecount):
      try:
        idcode = struct.unpack("<I", self._txn(struct.pack("BB", 3, i), 4))[0]
        if not idcode & 0xfffffff in idcodemap or not "handler" in idcodemap[idcode & 0xfffffff]:
          idcodemap[idcode & 0xfffffff] = {"handler": UnknownDevice}
        device = idcodemap[idcode & 0xfffffff]["handler"](self.proxy, self, i, idcode)
        devices.append(device)
        self.proxy.log("%s: %s\n" % (device.name, device.typename), 500)
      except Exception as e: self.proxy.log("%s\n" % str(e), 150, "rB")
    for device in devices:
      try: device.init()
      except DeviceException as e: self.proxy.log("%s: %s\n" % (device.name, str(e)), 200, "r")
    
    
  def register(self, device):
    device.index = len(self.devices)
    self.devices.append(device)
    
    
  def close(self):
    self.shutdown = True
    try: self.listenerthread.join(2)
    except: pass
    
    
  def _txn(self, data, expectlen):
    with self.lock:
      self.handle.write(data)
      result = self.handle.read(expectlen)
    if len(result) != expectlen: raise Exception("Short read: Expected %d bytes, got %d (%s)!" % (expectlen, len(result), hexlify(result).decode("ascii")))
    return result
    
    
  def get_usercode(self, id):
    return struct.unpack("<I", self._txn(struct.pack("BB", 4, id), 4))[0]
    
    
  def get_fpga_count(self):
    return len(self.devices)

  
  def send_job(self, fpga, job):
    result = struct.unpack("B", self._txn(struct.pack("BB", 8, self.devices[fpga].id) + job, 1))[0]
    if result != 1: raise Exception("%s: Device didn't accept job: 0x%02x" % (self.devices[fpga].name, result))

  
  def write_reg(self, fpga, reg, value):
    result = struct.unpack("B", self._txn(struct.pack("<BBBI", 11, self.devices[fpga].id, reg, value), 1))[0]
    if result != 1: raise Exception("%s: Writing register %d failed: 0x%02x" % (self.devices[fpga].name, reg, result))

  
  def read_reg(self, fpga, reg):
    return struct.unpack("<I", self._txn(struct.pack("BBB", 12, self.devices[fpga].id, reg), 4))[0]

  
  def set_speed(self, fpga, speed):
    result = struct.unpack("B", self._txn(struct.pack("<BBI", 6, self.devices[fpga].id, speed), 1))[0]
    if result != 1: raise Exception("%s: Device didn't accept clock speed %d!" % (self.devices[fpga].name, speed))

  
  def get_speed(self, fpga):
    return struct.unpack("<I", self._txn(struct.pack("BB", 7, self.devices[fpga].id), 4))[0]

  
  def read_nonces(self):
    nonces = {}
    with self.lock:
      for device in self.devices:
        if not device.usable: continue
        nonce = device.parse_nonce(self._txn(struct.pack("BB", 9, device.id), 4))
        if nonce is not None: nonces[device.index] = nonce
    return nonces
    
    
  def read_temperatures(self):
    temps = {}
    with self.lock:
      for device in self.devices:
        temps[device.index] = struct.unpack("<h", self._txn(struct.pack("BB", 13, device.id), 2))[0] / 128.
    return temps

########NEW FILE########
__FILENAME__ = mmqhotplug
# Modular Python Bitcoin Miner
# Copyright (C) 2011-2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



###########################################
# ModMiner Quad hotplug controller module #
###########################################



import traceback
from glob import glob
from threading import Condition, Thread
from core.baseworker import BaseWorker
from .mmqworker import MMQWorker



# Worker main class, referenced from __init__.py
class MMQHotplugWorker(BaseWorker):
  
  version = "theseven.mmq hotplug manager v0.1.0"
  default_name = "MMQ hotplug manager"
  can_autodetect = True
  settings = dict(BaseWorker.settings, **{
    "firmware": {"title": "Firmware file location", "type": "string", "position": 1200},
    "scaninterval": {"title": "Bus scan interval", "type": "float", "position": 2200},
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 3000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 3100},
    "tempwarning": {"title": "Warning temperature", "type": "int", "position": 4000},
    "tempcritical": {"title": "Critical temperature", "type": "int", "position": 4100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 4200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 4300},
    "warmupstepshares": {"title": "Shares per warmup step", "type": "int", "position": 4400},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 4500},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 5100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 5200},
  })
  
  
  @classmethod
  def autodetect(self, core):
    try:
      import serial
      found = False
      for port in glob("/dev/serial/by-id/usb-BTCFPGA_ModMiner_LJRalpha_*"):
        try:
          handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
          handle.close()
          found = True
          break
        except: pass
      if found: core.add_worker(self(core))
    except: pass
    
    
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Initialize bus scanner wakeup event
    self.wakeup = Condition()

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(MMQHotplugWorker, self).__init__(core, state)

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQHotplugWorker, self).apply_settings()
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/theseven/mmq/firmware/"
    if not "initialspeed" in self.settings: self.settings.initialspeed = 150
    self.settings.initialspeed = min(max(self.settings.initialspeed, 4), 250)
    if not "maximumspeed" in self.settings: self.settings.maximumspeed = 200
    self.settings.maximumspeed = min(max(self.settings.maximumspeed, 4), 300)
    if not "tempwarning" in self.settings: self.settings.tempwarning = 45
    self.settings.tempwarning = min(max(self.settings.tempwarning, 0), 60)
    if not "tempcritical" in self.settings: self.settings.tempcritical = 55
    self.settings.tempcritical = min(max(self.settings.tempcritical, 0), 80)
    if not "invalidwarning" in self.settings: self.settings.invalidwarning = 2
    self.settings.invalidwarning = min(max(self.settings.invalidwarning, 1), 10)
    if not "invalidcritical" in self.settings: self.settings.invalidcritical = 10
    self.settings.invalidcritical = min(max(self.settings.invalidcritical, 1), 50)
    if not "warmupstepshares" in self.settings: self.settings.warmupstepshares = 5
    self.settings.warmupstepshares = min(max(self.settings.warmupstepshares, 1), 10000)
    if not "speedupthreshold" in self.settings: self.settings.speedupthreshold = 100
    self.settings.speedupthreshold = min(max(self.settings.speedupthreshold, 50), 10000)
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    if not "scaninterval" in self.settings or not self.settings.scaninterval: self.settings.scaninterval = 10
    # Push our settings down to our children
    fields = ["firmware", "initialspeed", "maximumspeed", "tempwarning", "tempcritical", "invalidwarning",
              "invalidcritical", "warmupstepshares", "speedupthreshold", "jobinterval", "pollinterval"]
    for child in self.children:
      for field in fields: child.settings[field] = self.settings[field]
      child.apply_settings()
    # Rescan the bus immediately to apply the new settings
    with self.wakeup: self.wakeup.notify()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQHotplugWorker, self)._reset()


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQHotplugWorker, self)._start()
    # Initialize child map
    self.childmap = {}
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQHotplugWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(10)
    # Shut down child workers
    while self.children:
      child = self.children.pop(0)
      try:
        self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
        child.stop()
      except Exception as e:
        self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")

      
  # Main thread entry point
  # This thread is responsible for scanning for boards and spawning worker modules for them
  def main(self):
    import serial
    number = 0

    # Loop until we are shut down
    while not self.shutdown:

      try:
        boards = {}
        for port in glob("/dev/serial/by-id/usb-BTCFPGA_ModMiner_LJRalpha_*"):
          available = False
          try:
            handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
            handle.close()
            available = True
          except: pass
          boards[port] = available

        kill = []
        for port, child in self.childmap.items():
          if not port in boards:
            kill.append((port, child))

        for port, child in kill:
          try:
            self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
            child.stop()
          except Exception as e:
            self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
          childstats = child.get_statistics()
          fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
          for field in fields: self.stats[field] += childstats[field]
          try: self.child.destroy()
          except: pass
          del self.childmap[port]
          try: self.children.remove(child)
          except: pass

        for port, available in boards.items():
          if port in self.childmap or not available: continue
          number += 1
          child = MMQWorker(self.core)
          child.settings.name = "Autodetected MMQ device %d" % number
          child.settings.port = port
          fields = ["firmware", "initialspeed", "maximumspeed", "tempwarning", "tempcritical", "invalidwarning",
                    "invalidcritical", "warmupstepshares", "speedupthreshold", "jobinterval", "pollinterval"]
          for field in fields: child.settings[field] = self.settings[field]
          child.apply_settings()
          self.childmap[port] = child
          self.children.append(child)
          try:
            self.core.log(self, "Starting up worker %s...\n" % (child.settings.name), 800)
            child.start()
          except Exception as e:
            self.core.log(self, "Could not start worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")

      except: self.core.log(self, "Caught exception: %s\n" % traceback.format_exc(), 100, "rB")

      with self.wakeup: self.wakeup.wait(self.settings.scaninterval)

########NEW FILE########
__FILENAME__ = mmqworker
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#########################################
# ModMiner Quad worker interface module #
#########################################



import time
import struct
import traceback
from multiprocessing import Pipe
from threading import RLock, Condition, Thread
from binascii import hexlify, unhexlify
from core.baseworker import BaseWorker
from core.job import ValidationJob
from .boardproxy import MMQBoardProxy
try: from queue import Queue
except: from Queue import Queue



# Worker main class, referenced from __init__.py
class MMQWorker(BaseWorker):
  
  version = "theseven.mmq worker v0.1.0"
  default_name = "Untitled MMQ worker"
  settings = dict(BaseWorker.settings, **{
    "port": {"title": "Port", "type": "string", "position": 1000},
    "firmware": {"title": "Firmware file location", "type": "string", "position": 1400},
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 2000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 2100},
    "tempwarning": {"title": "Warning temperature", "type": "int", "position": 3000},
    "tempcritical": {"title": "Critical temperature", "type": "int", "position": 3100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 3200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 3300},
    "warmupstepshares": {"title": "Shares per warmup step", "type": "int", "position": 3400},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 3500},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 4100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 4200},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(MMQWorker, self).__init__(core, state)

    # Initialize proxy access locks and wakeup event
    self.lock = RLock()
    self.transactionlock = RLock()
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQWorker, self).apply_settings()
    if not "port" in self.settings or not self.settings.port: self.settings.port = "/dev/ttyACM0"
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/theseven/mmq/firmware/"
    if not "initialspeed" in self.settings: self.settings.initialspeed = 150
    self.settings.initialspeed = min(max(self.settings.initialspeed, 4), 250)
    if not "maximumspeed" in self.settings: self.settings.maximumspeed = 200
    self.settings.maximumspeed = min(max(self.settings.maximumspeed, 4), 300)
    if not "tempwarning" in self.settings: self.settings.tempwarning = 45
    self.settings.tempwarning = min(max(self.settings.tempwarning, 0), 60)
    if not "tempcritical" in self.settings: self.settings.tempcritical = 55
    self.settings.tempcritical = min(max(self.settings.tempcritical, 0), 80)
    if not "invalidwarning" in self.settings: self.settings.invalidwarning = 2
    self.settings.invalidwarning = min(max(self.settings.invalidwarning, 1), 10)
    if not "invalidcritical" in self.settings: self.settings.invalidcritical = 10
    self.settings.invalidcritical = min(max(self.settings.invalidcritical, 1), 50)
    if not "warmupstepshares" in self.settings: self.settings.warmupstepshares = 5
    self.settings.warmupstepshares = min(max(self.settings.warmupstepshares, 1), 10000)
    if not "speedupthreshold" in self.settings: self.settings.speedupthreshold = 100
    self.settings.speedupthreshold = min(max(self.settings.speedupthreshold, 50), 10000)
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    # We can't change the port name or baud rate on the fly, so trigger a restart
    # if they changed. self.port is a cached copy of self.settings.port.
    if self.started and (self.settings.port != self.port): self.async_restart()
    # We need to inform the proxy about a poll interval change
    if self.started and self.settings.pollinterval != self.pollinterval: self._notify_poll_interval_changed()
    for child in self.children: child.apply_settings()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.port = None
    self.pollinterval = None


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQWorker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.port = self.settings.port
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Ping the proxy, otherwise the main thread might be blocked and can't wake up.
    try: self._proxy_message("ping")
    except: pass
    # Wait for the main thread to terminate, which in turn kills the child workers.
    self.mainthread.join(10)

      
  # Main thread entry point
  # This thread is responsible for booting the individual FPGAs and spawning worker threads for them
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()
        
        # Check if we have a device serial number
        if not self.port: raise Exception("Device port not set!")
        
        # Try to start the board proxy
        proxy_rxconn, self.txconn = Pipe(False)
        self.rxconn, proxy_txconn = Pipe(False)
        self.pollinterval = self.settings.pollinterval
        self.proxy = MMQBoardProxy(proxy_rxconn, proxy_txconn, self.port, self.settings.firmware, self.pollinterval)
        self.proxy.daemon = True
        self.proxy.start()
        proxy_txconn.close()
        self.response = None
        self.response_queue = Queue()
        
        # Tell the board proxy to connect to the board
        self._proxy_message("connect")
        
        while not self.shutdown:
          data = self.rxconn.recv()
          if data[0] == "log": self.core.log(self, "Proxy: %s" % data[1], data[2], data[3])
          elif data[0] == "ping": self._proxy_message("pong")
          elif data[0] == "pong": pass
          elif data[0] == "dying": raise Exception("Proxy died!")
          elif data[0] == "response": self.response_queue.put(data[1:])
          elif data[0] == "started_up": self._notify_proxy_started_up(*data[1:])
          elif data[0] == "nonce_found": self._notify_nonce_found(*data[1:])
          elif data[0] == "temperatures_read": self._notify_temperatures_read(*data[1:])
          else: raise Exception("Proxy sent unknown message: %s" % str(data))
        
        
      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        try:
          for i in range(100): self.response_queue.put(None)
        except: pass
        while self.children:
          try:
            child = self.children.pop(0)
            child.stop()
            childstats = child.get_statistics()
            fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
            for field in fields: self.stats[field] += childstats[field]
            try: self.child.destroy()
            except: pass
          except: pass
        try: self._proxy_message("shutdown")
        except: pass
        try: self.proxy.join(4)
        except: pass
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)

        
  def _proxy_message(self, *args):
    with self.lock:
      self.txconn.send(args)


  def _proxy_transaction(self, *args):
    with self.transactionlock:
      with self.lock:
        self.txconn.send(args)
      return self.response_queue.get()
      
      
  def _notify_poll_interval_changed(self):
    self.pollinterval = self.settings.pollinterval
    try: self._proxy_message("set_pollinterval", self.pollinterval)
    except: pass
    
    
  def _notify_proxy_started_up(self, fpgacount):
    # The proxy is up and running, start up child workers
    for i in range(fpgacount):
        self.children.append(MMQFPGA(self.core, self, i))
    for child in self.children: child.start()

    
  def _notify_nonce_found(self, fpga, now, nonce):
    if self.children and fpga < len(self.children):
      try: self.children[fpga].notify_nonce_found(now, nonce)
      except Exception as e: self.children[fpga].error = e


  def _notify_temperatures_read(self, temperatures):
    if self.children:
      for fpga in temperatures:
        if len(self.children) > fpga:
          self.children[fpga].stats.temperature = temperatures[fpga]
          if temperatures[fpga]:
            self.core.event(350, self.children[fpga], "temperature", temperatures[fpga] * 1000, "%f \xc2\xb0C" % temperatures[fpga], worker = self.children[fpga])

      
  def send_job(self, fpga, job):
    return self._proxy_transaction("send_job", fpga, job.midstate + job.data[64:76])


  def read_reg(self, fpga, reg):
    return self._proxy_transaction("read_reg", fpga, reg)[0]

  
  def write_reg(self, fpga, reg, value):
    self._proxy_transaction("write_reg", fpga, reg, value)

  
  def read_job(self, fpga):
    data = b""
    for i in range(1, 12): data += struct.pack("<I", self.read_reg(fpga, i))
    return data

  
  def set_speed(self, fpga, speed):
    self._proxy_message("set_speed", fpga, speed)


  def get_speed(self, fpga):
    return self._proxy_transaction("get_speed", fpga)[0]



# FPGA handler main class, child worker of MMQWorker
class MMQFPGA(BaseWorker):

  # Constructor, gets passed a reference to the miner core, the MMQWorker,
  # its FPGA id, and the bitstream version currently running on that FPGA
  def __init__(self, core, parent, fpga):
    self.parent = parent
    self.fpga = fpga

    # Let our superclass do some basic initialization
    super(MMQFPGA, self).__init__(core, None)
    
    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()


    
  # Validate settings, mostly coping them from our parent
  # Called from the constructor and after every settings change on the parent.
  def apply_settings(self):
    self.settings.name = "%s FPGA%d" % (self.parent.settings.name, self.fpga)
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQFPGA, self).apply_settings()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQFPGA, self)._reset()
    self.stats.temperature = None
    self.initialramp = True


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQFPGA, self)._start()
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.parent.settings.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQFPGA, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(1)

      
  # This function should interrupt processing of the specified job if possible.
  # This is necesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast. We don't care whether it's a
  # graceful cancellation for this module because the work upload overhead is low. 
  def notify_canceled(self, job, graceful):
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.wakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.wakeup.notify()

        
  # Report custom statistics.
  def _get_statistics(self, stats, childstats):
    # Let our superclass handle everything that isn't specific to this worker module
    super(MMQFPGA, self)._get_statistics(stats, childstats)
    stats.temperature = self.stats.temperature


  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()

        # Initialize megahashes per second to zero, will be measured later.
        self.stats.mhps = 0

        # Job that the device is currently working on, or that is currently being uploaded.
        # This variable is used by BaseWorker to figure out the current work source for statistics.
        self.job = None
        # Job that was previously being procesed. Has been destroyed, but there might be some late nonces.
        self.oldjob = None
        self.diagjob = False

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Eat up leftover wakeups
        self.wakeup.wait(0)
        # Honor shutdown flag (in case it was a real wakeup)
        if self.shutdown: break
        # Set validation success flag to false
        self.checksuccess = False
        
        # Initialize hash rate tracking data
        self.lasttime = None
        self.lastnonce = None

        # Initialize malfunction tracking data
        self.recentshares = 0
        self.recentinvalid = 0

        # Configure core clock, if the bitstream supports that
        self._set_speed(self.parent.settings.initialspeed)
        
        # Send validation job to device
        job = ValidationJob(self.core, unhexlify(b"00000001c3bf95208a646ee98a58cf97c3a0c4b7bf5de4c89ca04495000005200000000024d1fff8d5d73ae11140e4e48032cd88ee01d48c67147f9a09cd41fdec2e25824f5c038d1a0b350c5eb01f04"))
        self._sendjob(job)

        # Wait for the validation job to complete. The wakeup flag will be
        # set by the listener thread when the validation job completes.
        self.wakeup.wait((100. / self.stats.mhps) + 1)
        # Honor shutdown flag
        if self.shutdown: break
        # We woke up, but the validation job hasn't succeeded in the mean time.
        # This usually means that the wakeup timeout has expired.
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")

        # Main loop, continues until something goes wrong or we're shutting down.
        while not self.shutdown:

          # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
          # Blocks until one is available. Because of this we need to release the
          # wakeup lock temporarily in order to avoid possible deadlocks.
          self.wakeup.release()
          job = self.core.get_job(self, self.jobinterval + 2)
          self.wakeup.acquire()
          
          # If a new block was found while we were fetching that job, just discard it and get a new one.
          if job.canceled:
            job.destroy()
            continue

          # Upload the job to the device
          self._sendjob(job)
          
          # Go through the safety checks and reduce the clock if necessary
          self.safetycheck()
          
          # If the job was already caught by a long poll while we were uploading it,
          # jump back to the beginning of the main loop in order to immediately fetch new work.
          # Don't check for the canceled flag before the job was accepted by the device,
          # otherwise we might get out of sync.
          if self.job.canceled: continue
          # Wait while the device is processing the job. If nonces are sent by the device, they
          # will be processed by the listener thread. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        try: self.wakeup.release()
        except: pass
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, restart the parent worker as well.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5:
              self.parent.async_restart()
              return
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  def notify_nonce_found(self, now, nonce):
    # Snapshot the current jobs to avoid race conditions
    oldjob = self.oldjob
    newjob = self.job
    # If there is no job, this must be a leftover from somewhere, e.g. previous invocation
    # or reiterating the keyspace because we couldn't provide new work fast enough.
    # In both cases we can't make any use of that nonce, so just discard it.
    if not oldjob and not newjob: return
    # Pass the nonce that we found to the work source, if there is one.
    # Do this before calculating the hash rate as it is latency critical.
    job = None
    if newjob:
      if newjob.nonce_found(nonce, oldjob): job = newjob
    if not job and oldjob:
      if oldjob.nonce_found(nonce): job = oldjob
    self.recentshares += 1
    if not job:
      self.recentinvalid += 1
      self.diagjob = True
    nonceval = struct.unpack("<I", nonce)[0]
    if isinstance(newjob, ValidationJob):
      # This is a validation job. Validate that the nonce is correct, and complain if not.
      if newjob.nonce != nonce:
        raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (hexlify(nonce).decode("ascii"), hexlify(newjob.nonce).decode("ascii")))
      else:
        # The nonce was correct
        with self.wakeup:
          self.checksuccess = True
          self.wakeup.notify()
      

  # This function uploads a job to the device
  def _sendjob(self, job):
    # Move previous job to oldjob, and new one to job
    self.oldjob = self.job
    self.job = job
    if self.oldjob and self.diagjob:
      self.diagjob = False
      data = self.oldjob.midstate + self.oldjob.data[64:76]
      readback = self.parent.read_job(self.fpga)
      if readback != data: self.core.log(self, "Bad job readback: Expected %s, got %s!\n" % (hexlify(data).decode("ascii"), hexlify(readback).decode("ascii")), 200, "yB")
      else: self.core.log(self, "Good job readback: %s\n" % hexlify(readback).decode("ascii"), 500, "g")
    # Send it to the FPGA
    start, now = self.parent.send_job(self.fpga, job)
    #data = job.midstate + job.data[64:76]
    #readback = self.parent.read_job(self.fpga)
    #if readback != data: self.core.log(self, "Bad job readback: Expected %s, got %s!\n" % (hexlify(data).decode("ascii"), hexlify(readback).decode("ascii")), 200, "yB")
    #else: self.core.log(self, "Good job readback: %s\n" % hexlify(readback).decode("ascii"), 500, "g")
    # Calculate how long the old job was running
    if self.oldjob:
      if self.oldjob.starttime:
        self.oldjob.hashes_processed((now - self.oldjob.starttime) * self.stats.mhps * 1000000)
      self.oldjob.destroy()
    self.job.starttime = now

    
  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job != None:
      if self.job.starttime:
        self.job.hashes_processed((now - self.job.starttime) * self.stats.mhps * 1000000)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.oldjob = self.job
      self.job.destroy()
      self.job = None
  
  
  # Check the invalid rate and temperature, and reduce the FPGA clock if these exceed safe values
  def safetycheck(self):
    
    warning = False
    critical = False
    if self.recentinvalid >= self.parent.settings.invalidwarning: warning = True
    if self.recentinvalid >= self.parent.settings.invalidcritical: critical = True
    if self.stats.temperature:
      if self.stats.temperature > self.parent.settings.tempwarning: warning = True    
      if self.stats.temperature > self.parent.settings.tempcritical: critical = True    

    threshold = self.parent.settings.warmupstepshares if self.initialramp and not self.recentinvalid else self.parent.settings.speedupthreshold

    if warning: self.core.log(self, "Detected overload condition!\n", 200, "y")
    if critical: self.core.log(self, "Detected CRITICAL condition!\n", 100, "rB")

    if critical:
      speedstep = -20
      self.initialramp = False
    elif warning:
      speedstep = -2
      self.initialramp = False
    elif not self.recentinvalid and self.recentshares >= threshold:
      speedstep = 2
    else: speedstep = 0    

    if speedstep: self._set_speed(self.stats.mhps + speedstep)

    if speedstep or self.recentshares >= threshold:
      self.recentinvalid = 0
      self.recentshares = 0
    
   
  def _set_speed(self, speed):
    speed = min(max(speed, 4), self.parent.settings.maximumspeed)
    if self.stats.mhps == speed: return
    if speed == self.parent.settings.maximumspeed: self.initialramp = False
    self.core.log(self, "%s: Setting clock speed to %.2f MHz...\n" % ("Warmup" if self.initialramp else "Tracking", speed), 500, "B")
    self.parent.set_speed(self.fpga, speed)
    self.stats.mhps = self.parent.get_speed(self.fpga)
    self._update_job_interval()
    if self.stats.mhps != speed:
      self.core.log(self, "Setting clock speed failed!\n", 100, "rB")
   
   
  def _update_job_interval(self):
    self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
    # Calculate the time that the device will need to process 2**32 nonces.
    # This is limited at 60 seconds in order to have some regular communication,
    # even with very slow devices (and e.g. detect if the device was unplugged).
    interval = min(60, 2**32 / 1000000. / self.stats.mhps)
    # Add some safety margin and take user's interval setting (if present) into account.
    self.jobinterval = min(self.parent.settings.jobinterval, max(0.5, interval * 0.8 - 1))
    self.core.log(self, "Job interval: %f seconds\n" % self.jobinterval, 400, "B")
    # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
    self.jobs_per_second = 1. / self.jobinterval
    self.core.notify_speed_changed(self)
  

########NEW FILE########
__FILENAME__ = simplers232worker
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



########################################
# Simple RS232 worker interface module #
########################################



import time
import struct
import traceback
from threading import Condition, Thread
from binascii import hexlify, unhexlify
from core.baseworker import BaseWorker
from core.job import ValidationJob



# Worker main class, referenced from __init__.py
class SimpleRS232Worker(BaseWorker):
  
  version = "theseven.simplers232 worker v0.1.0"
  default_name = "Untitled SimpleRS232 worker"
  settings = dict(BaseWorker.settings, **{
    "port": {"title": "Port", "type": "string", "position": 1000},
    "baudrate": {"title": "Baud rate", "type": "int", "position": 1100},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 1200},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(SimpleRS232Worker, self).__init__(core, state)

    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(SimpleRS232Worker, self).apply_settings()
    # Pretty much self-explanatory...
    if not "port" in self.settings or not self.settings.port: self.settings.port = "/dev/ttyS0"
    if not "baudrate" in self.settings or not self.settings.baudrate: self.settings.baudrate = 115200
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    # We can't change the port name or baud rate on the fly, so trigger a restart if they changed.
    # self.port/self.baudrate are cached copys of self.settings.port/self.settings.baudrate
    if self.started and (self.settings.port != self.port or self.settings.baudrate != self.baudrate): self.async_restart()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(SimpleRS232Worker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.port = None
    self.baudrate = None
#    # Initialize custom statistics. This is not neccessary for this worker module,
#    # but might be interesting for other modules, so it is kept here for reference.
#    self.stats.field1 = 0
#    self.stats.field2 = 0
#    self.stats.field3 = 0


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(SimpleRS232Worker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.port = self.settings.port
    self.baudrate = self.settings.baudrate
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.settings.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(SimpleRS232Worker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # The listener thread will hopefully die because the main thread closes the serial port handle.
    # Wait for the main thread to terminate, which in turn waits for the listener thread to die.
    self.mainthread.join(10)

      
  # This function should interrupt processing of the specified job if possible.
  # This is necesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast. We don't care whether it's a
  # graceful cancellation for this module because the work upload overhead is low. 
  def notify_canceled(self, job, graceful):
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.wakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job or self.nextjob == job:
        self.wakeup.notify()

        
#  # Report custom statistics. This is not neccessary for this worker module,
#  # but might be interesting for other modules, so it is kept here for reference.
#  def _get_statistics(self, stats, childstats):
#    # Let our superclass handle everything that isn't specific to this worker module
#    super(SimpleRS232Worker, self)._get_statistics(stats, childstats)
#    stats.field1 = self.stats.field1
#    stats.field2 = self.stats.field2 + childstats.calculatefieldsum("field2")
#    stats.field3 = self.stats.field3 + childstats.calculatefieldavg("field3")
        
        
  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()
        # Exception container: If an exception occurs in the listener thread, the listener thread
        # will store it here and terminate, and the main thread will rethrow it and then restart.
        self.error = None

        # Initialize megahashes per second to zero, will be measured later.
        self.stats.mhps = 0

        # Job that the device is currently working on (found nonces are coming from this one).
        # This variable is used by BaseWorker to figure out the current work source for statistics.
        self.job = None
        # Job that is currently being uploaded to the device but not yet being processed.
        self.nextjob = None

        # Open the serial port
        import serial
        self.handle = serial.Serial(self.port, self.baudrate, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)

        # Send enough zero bytes to make sure that the device is not expecting data any more.
        # Command zero is a ping request, which is answered by a zero byte from the device.
        # This means that superfluous zero bytes (but at least one) will just bounce back to us.
        self.handle.write(struct.pack("45B", *([0] * 45)))
        # Read the device's response.
        # There should be at least one byte, and the last byte must be zero.
        # If not, something is wrong with the device or communication channel.
        data = self.handle.read(100)
        if len(data) == 0: raise Exception("Failed to sync with mining device: Device does not respond")
        if data[-1:] != b"\0": raise Exception("Failed to sync with mining device: Device sends garbage")

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Set validation success flag to false
        self.checksuccess = False
        # Start device response listener thread
        self.listenerthread = Thread(None, self._listener, self.settings.name + "_listener")
        self.listenerthread.daemon = True
        self.listenerthread.start()

        # Send validation job to device
        job = ValidationJob(self.core, unhexlify(b"00000001c3bf95208a646ee98a58cf97c3a0c4b7bf5de4c89ca04495000005200000000024d1fff8d5d73ae11140e4e48032cd88ee01d48c67147f9a09cd41fdec2e25824f5c038d1a0b350c5eb01f04"))
        self._sendjob(job)

        # Wait for validation job to be accepted by the device
        self.wakeup.wait(1)
        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error
        # Honor shutdown flag
        if self.shutdown: break
        # If the job that was enqueued above has not been moved from nextjob to job by the
        # listener thread yet, something went wrong. Throw an exception to make everything restart.
        if self.nextjob != None: raise Exception("Timeout waiting for job ACK")

        # Wait for the validation job to complete. The wakeup flag will be set by the listener
        # thread when the validation job completes. 60 seconds should be sufficient for devices
        # down to about 1.3MH/s, for slower devices this timeout will need to be increased.
        self.wakeup.wait(60)
        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error
        # Honor shutdown flag
        if self.shutdown: break
        # We woke up, but the validation job hasn't succeeded in the mean time.
        # This usually means that the wakeup timeout has expired.
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")
        # self.stats.mhps has now been populated by the listener thread
        self.core.log(self, "Running at %f MH/s\n" % self.stats.mhps, 300, "B")
        # Calculate the time that the device will need to process 2**32 nonces.
        # This is limited at 60 seconds in order to have some regular communication,
        # even with very slow devices (and e.g. detect if the device was unplugged).
        interval = min(60, 2**32 / 1000000. / self.stats.mhps)
        # Add some safety margin and take user's interval setting (if present) into account.
        self.jobinterval = min(self.settings.jobinterval, max(0.5, interval * 0.8 - 1))
        self.core.log(self, "Job interval: %f seconds\n" % self.jobinterval, 400, "B")
        # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
        self.jobspersecond = 1. / self.jobinterval
        self.core.notify_speed_changed(self)

        # Main loop, continues until something goes wrong or we're shutting down.
        while not self.shutdown:

          # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
          # Blocks until one is available. Because of this we need to release the
          # wakeup lock temporarily in order to avoid possible deadlocks.
          self.wakeup.release()
          job = self.core.get_job(self, self.jobinterval + 2)
          self.wakeup.acquire()
          
          # If a new block was found while we were fetching that job, just discard it and get a new one.
          if job.canceled:
            job.destroy()
            continue

          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

          # Upload the job to the device
          self._sendjob(job)
          # Wait for up to one second for the device to accept it
          self.wakeup.wait(1)
          # Honor shutdown flag
          if self.shutdown: break
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error
          # If the job that was send above has not been moved from nextjob to job by the listener
          # thread yet, something went wrong. Throw an exception to make everything restart.
          if self.nextjob != None: raise Exception("Timeout waiting for job ACK")
          # If the job was already caught by a long poll while we were uploading it,
          # jump back to the beginning of the main loop in order to immediately fetch new work.
          # Don't check for the canceled flag before the job was accepted by the device,
          # otherwise we might get out of sync.
          if self.job.canceled: continue
          # Wait while the device is processing the job. If nonces are sent by the device, they
          # will be processed by the listener thread. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
        # Make sure that the listener thread realizes that something went wrong
        self.error = e
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        # Release the wake lock to allow the listener thread to move. Ignore it if that goes wrong.
        try: self.wakeup.release()
        except: pass
        # Close the serial port handle, otherwise we can't reopen it after restarting.
        # This should hopefully also make reads on that port from the listener thread fail,
        # so that the listener thread will realize that it's supposed to shut down.
        try: self.handle.close()
        except: pass
        # Wait for the listener thread to terminate.
        # If it doens't within 5 seconds, continue anyway. We can't do much about that.
        try: self.listenerthread.join(5)
        except: pass
        # Set MH/s to zero again, the listener thread might have overwritten that.
        self.stats.mhps = 0
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, wait a bit longer until restarting the worker.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  # Device response listener thread
  def _listener(self):
    # Catch all exceptions and forward them to the main thread
    try:
      # Loop forever unless something goes wrong
      while True:
        # If the main thread has a problem, make sure we die before it restarts
        if self.error != None: break

        # Try to read a response from the device
        data = self.handle.read(1)
        # If no response was available, retry
        if len(data) == 0: continue
        # Decode the response
        result = struct.unpack("B", data)[0]

        if result == 1:
          # Got a job acknowledgement message.
          # If we didn't expect one (no job waiting to be accepted in nextjob), throw an exception.
          if self.nextjob == None: raise Exception("Got spurious job ACK from mining device")
          # The job has been uploaded. Start counting time for the new job, and if there was a
          # previous one, calculate for how long that one was running and destroy it.
          now = time.time()
          self._jobend(now)

          # Acknowledge the job by moving it from nextjob to job and wake up
          # the main thread that's waiting for the job acknowledgement.
          with self.wakeup:
            self.job = self.nextjob
            self.job.starttime = now
            self.nextjob = None
            self.wakeup.notify()
          continue

        elif result == 2:
          # We found a share! Download the nonce.
          nonce = self.handle.read(4)[::-1]
          # If there is no job, this must be a leftover from somewhere, e.g. previous invocation
          # or reiterating the keyspace because we couldn't provide new work fast enough.
          # In both cases we can't make any use of that nonce, so just discard it.
          if self.job == None: continue
          # Stop time measurement
          now = time.time()
          # Pass the nonce that we found to the work source, if there is one.
          # Do this before calculating the hash rate as it is latency critical.
          self.job.nonce_found(nonce)
          # If the nonce is too low, the measurement may be inaccurate.
          nonceval = struct.unpack("<I", nonce)[0]
          if nonceval >= 0x02000000:
            # Calculate actual on-device processing time (not including transfer times) of the job.
            delta = (now - self.job.starttime) - 40. / self.baudrate
            # Calculate the hash rate based on the processing time and number of neccessary MHashes.
            # This assumes that the device processes all nonces (starting at zero) sequentially.
            self.stats.mhps = nonceval / delta / 1000000.
            self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
          # This needs self.mhps to be set.
          if isinstance(self.job, ValidationJob):
            # This is a validation job. Validate that the nonce is correct, and complain if not.
            if self.job.nonce != nonce:
              raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (hexlify(nonce).decode("ascii"), hexlify(self.job.nonce).decode("ascii")))
            else:
              # The nonce was correct. Wake up the main thread.
              with self.wakeup:
                self.checksuccess = True
                self.wakeup.notify()
          continue

        if result == 3:
          # The device managed to process the whole 2**32 keyspace before we sent it new work.
          self.core.log(self, "Exhausted keyspace!\n", 200, "y")
          # If it was a validation job, this probably means that there is a hardware/firmware bug
          # or that the "found share" message was lost on the communication channel.
          if isinstance(self.job, ValidationJob): raise Exception("Validation job terminated without finding a share")
          # Stop measuring time because the device is doing duplicate work right now
          self._jobend()
          # Wake up the main thread to fetch new work ASAP.
          with self.wakeup: self.wakeup.notify()
          continue

        # If we end up here, we received a message from the device that was invalid or unexpected.
        # All valid cases are terminated with a "continue" statement above.
        raise Exception("Got bad message from mining device: %d" % result)

    # If an exception is thrown in the listener thread...
    except Exception as e:
      # ...complain about it...
      self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      # ...put it into the exception container...
      self.error = e
      # ...wake up the main thread...
      with self.wakeup: self.wakeup.notify()
      # ...and terminate the listener thread.


  # This function uploads a job to the device
  def _sendjob(self, job):
    # Put it into nextjob. It will be moved to job by the listener
    # thread as soon as it gets acknowledged by the device.
    self.nextjob = job
    # Send it to the device
    self.handle.write(struct.pack("B", 1) + job.midstate[::-1] + job.data[75:63:-1])
    self.handle.flush()

    
  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job != None:
      if self.job.starttime != None:
        self.job.hashes_processed((now - self.job.starttime) * self.stats.mhps * 1000000)
        self.job.starttime = None
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.job.destroy()
      self.job = None

########NEW FILE########
__FILENAME__ = sqlitestats
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#####################################
# SQLite Statistics Logger Frontend #
#####################################



import os
import time
import numbers
import sqlite3
from threading import RLock, Condition, Thread
from core.basefrontend import BaseFrontend
from core.statistics import Statistics



class SQLiteStats(BaseFrontend):

  version = "theseven.sqlite statistics logger v0.1.0"
  default_name = "Untitled SQLite statistics logger"
  can_log = True
  can_handle_events = True
  can_autodetect = False
  settings = dict(BaseFrontend.settings, **{
    "filename": {"title": "Database file name", "type": "string", "position": 1000},
    "loglevel": {"title": "Log level", "type": "int", "position": 2000},
    "eventlevel": {"title": "Event filter level", "type": "int", "position": 2100},
    "statinterval": {"title": "Statistics logging interval", "type": "int", "position": 3000},
  })


  def __init__(self, core, state = None):
    super(SQLiteStats, self).__init__(core, state)
    self.lock = RLock()
    self.conn = None
    self.statwakeup = Condition()


  def apply_settings(self):
    super(SQLiteStats, self).apply_settings()
    if not "filename" in self.settings or not self.settings.filename: self.settings.filename = "stats.db"
    if not "loglevel" in self.settings: self.settings.loglevel = self.core.default_loglevel
    if not "eventlevel" in self.settings: self.settings.eventlevel = self.core.default_loglevel
    if not "statinterval" in self.settings: self.settings.statinterval = 60
    if not "worksourceinterval" in self.settings: self.settings.worksourceinterval = 60
    if not "blockchaininterval" in self.settings: self.settings.blockchaininterval = 60
    if self.started:
      if self.settings.filename != self.filename: self.async_restart()
      else:
        with self.statwakeup: self.statwakeup.notify()


  def _start(self):
    super(SQLiteStats, self)._start()
    with self.lock:
      self.shutdown = False
      self.filename = self.settings.filename
      self.db = sqlite3.connect(self.filename, check_same_thread = False)
      self.db.text_factory = str
      self.cursor = self.db.cursor()
      self._check_schema()
      self.eventtypes = {}
      self.statcolumns = {}
      self.statthread = Thread(None, self._statloop, "%s_statthread" % self.settings.name)
      self.statthread.daemon = True
      self.statthread.start()


  def _stop(self):
    self.shutdown = True
    with self.statwakeup: self.statwakeup.notify()
    self.statthread.join(5)
    with self.lock:
      self.cursor.close()
      self.cursor = None
      self.db.commit()
      self.db.close()
      self.db = None
    super(SQLiteStats, self)._stop()


  def write_log_message(self, source, timestamp, loglevel, messages):
    if not self.started: return
    if loglevel > self.settings.loglevel: return
    timestamp = time.mktime(timestamp.timetuple()) + timestamp.microsecond / 1000000.
    with self.lock:
      source = self._get_object_id(source)
      self.cursor.execute("INSERT INTO [log]([level], [timestamp], [source]) VALUES(:level, :timestamp, :source)",
                          {"level": loglevel, "timestamp": timestamp, "source": source})
      parent = self.cursor.lastrowid
      self.cursor.executemany("INSERT INTO [logfragment]([parent], [message], [format]) VALUES(:parent, :message, :format)",
                              [{"parent": parent, "message": message, "format": format} for message, format in messages])


  def handle_stats_event(self, level, source, event, arg, message, worker, worksource, blockchain, job, timestamp):
    if not self.started: return
    if level > self.settings.eventlevel: return
    timestamp = time.mktime(timestamp.timetuple()) + timestamp.microsecond / 1000000.
    with self.lock:
      source = self._get_object_id(source)
      worker = self._get_object_id(worker)
      worksource = self._get_object_id(worksource)
      blockchain = self._get_object_id(blockchain)
      job = self._get_job_id(job)
      eventtype = self._get_eventtype_id(event)
      self.cursor.execute("INSERT INTO [event]([level], [timestamp], [source], [type], [argument], "
                                              "[message], [worker], [worksource], [blockchain], [job]) "
                                      "VALUES(:level, :timestamp, :source, :type, :argument, "
                                             ":message, :worker, :worksource, :blockchain, :job)",
                          {"level": level, "timestamp": timestamp, "source": source, "type": eventtype, "argument": arg,
                           "message": message, "worker": worker, "worksource": worksource, "blockchain": blockchain, "job": job})
      
      
  def _statloop(self):
    while not self.shutdown:
      with self.statwakeup:
        if self.settings.statinterval <= 0: self.statwakeup.wait()
        else:
          now = time.time()
          stats = Statistics(obj = self.core, ghashes = self.core.stats.ghashes, starttime = self.core.stats.starttime)
          stats.avgmhps =  1000. * stats.ghashes / (now - stats.starttime)
          stats.children = self.core.get_worker_statistics() \
                         + self.core.get_work_source_statistics() \
                         + self.core.get_blockchain_statistics()
          with self.lock:
            self._insert_stats(now, stats)
            self.db.commit()
          self.statwakeup.wait(self.settings.statinterval)
          
          
  def _insert_stats(self, timestamp, stats, parent = None):
    self.cursor.execute("INSERT INTO [statrow]([timestamp], [subject], [parent]) VALUES(:timestamp, :subject, :parent)",
                        {"timestamp": timestamp, "subject": self._get_object_id(stats.obj), "parent": parent})
    row = self.cursor.lastrowid
    for key, value in stats.items():
      if isinstance(value, numbers.Number):
        self.cursor.execute("INSERT INTO [statfield]([row], [column], [value]) VALUES(:row, :column, :value)",
                            {"row": row, "column": self._get_statcolumn_id(key), "value": value})
    for child in stats.children: self._insert_stats(timestamp, child, row)
        
    
  def _get_objecttype_id(self, objtype):
    if hasattr(objtype, "_ext_theseven_sqlite_objtypeid"): return objtype._ext_theseven_sqlite_objtypeid
    name = objtype.__module__ + "." + objtype.__name__
    try:
      self.cursor.execute("SELECT [id] FROM [objecttype] WHERE [name] = :name", {"name": name})
      id = int(self.cursor.fetchone()[0])
    except:
      self.cursor.execute("INSERT INTO [objecttype]([name]) VALUES(:name)", {"name": name})
      id = self.cursor.lastrowid
    objtype._ext_theseven_sqlite_objtypeid = id
    return id


  def _get_object_id(self, obj):
    if obj is None: return None
    if hasattr(obj, "_ext_theseven_sqlite_objid"): return obj._ext_theseven_sqlite_objid
    type = self._get_objecttype_id(obj.__class__)
    try:
      self.cursor.execute("SELECT [id] FROM [object] WHERE [type] = :type AND [name] = :name",
                          {"type": type, "name": obj.settings.name})
      id = int(self.cursor.fetchone()[0])
    except:
      self.cursor.execute("INSERT INTO [object]([type], [name]) VALUES(:type, :name)",
                          {"type": type, "name": obj.settings.name})
      id = self.cursor.lastrowid
    obj._ext_theseven_sqlite_objid = id
    return id


  def _get_job_id(self, job):
    if job is None: return None
    if hasattr(job, "_ext_theseven_sqlite_jobid"): return job._ext_theseven_sqlite_jobid
    worksource = self._get_object_id(job.worksource)
    self.cursor.execute("INSERT INTO [job]([worksource], [data]) VALUES(:worksource, :data)",
                        {"worksource": worksource, "data": job.data[:76]})
    job._ext_theseven_sqlite_jobid = self.cursor.lastrowid
    return self.cursor.lastrowid


  def _get_eventtype_id(self, eventtype):
    if eventtype in self.eventtypes: return self.eventtypes[eventtype]
    try:
      self.cursor.execute("SELECT [id] FROM [eventtype] WHERE [name] = :name", {"name": eventtype})
      id = int(self.cursor.fetchone()[0])
    except:
      self.cursor.execute("INSERT INTO [eventtype]([name]) VALUES(:name)", {"name": eventtype})
      id = self.cursor.lastrowid
    self.eventtypes[eventtype] = id
    return id


  def _get_statcolumn_id(self, column):
    if column in self.statcolumns: return self.statcolumns[column]
    try:
      self.cursor.execute("SELECT [id] FROM [statcolumn] WHERE [name] = :name", {"name": column})
      id = int(self.cursor.fetchone()[0])
    except:
      self.cursor.execute("INSERT INTO [statcolumn]([name]) VALUES(:name)", {"name": column})
      id = self.cursor.lastrowid
    self.statcolumns[column] = id
    return id


  def _check_schema(self):
    try:
      self.cursor.execute("SELECT [value] FROM [dbinfo] WHERE [key] = 'version'")
      version = int(self.cursor.fetchone()[0])
    except: version = 0
    try:
      self.db.commit()
      if version == 0:
        self.cursor.execute("CREATE TABLE [dbinfo]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                  "[key] TEXT UNIQUE NOT NULL, "
                                                  "[value] TEXT UNIQUE NOT NULL)")
        self.cursor.execute("CREATE TABLE [objecttype]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                         "             [name] TEXT UNIQUE NOT NULL)")
        self.cursor.execute("CREATE TABLE [object]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                  "[type] INTEGER NOT NULL REFERENCES [objecttype] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                  "[name] TEXT NOT NULL, "
                                                  "CONSTRAINT object_unique_type_name UNIQUE (type, name))")
        self.cursor.execute("CREATE TABLE [job]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                               "[worksource] INTEGER NOT NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                               "[data] BLOB NOT NULL)")
        self.cursor.execute("CREATE TABLE [eventtype]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                     "[name] TEXT UNIQUE NOT NULL)")
        self.cursor.execute("CREATE TABLE [event]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                 "[level] INTEGER NOT NULL, "
                                                 "[timestamp] REAL NOT NULL, "
                                                 "[source] INTEGER NOT NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[type] INTEGER NOT NULL REFERENCES [eventtype] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[argument] INTEGER NULL, [message] TEXT NULL, "
                                                 "[worker] INTEGER NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[worksource] INTEGER NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[blockchain] INTEGER NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[job] INTEGER NULL REFERENCES [job] ON DELETE RESTRICT ON UPDATE RESTRICT)")
        self.cursor.execute("CREATE TABLE [log]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                               "[level] INTEGER NOT NULL, "
                                               "[timestamp] REAL NOT NULL, "
                                               "[source] INTEGER NOT NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT)")
        self.cursor.execute("CREATE TABLE [logfragment]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                       "[parent] INTEGER NOT NULL REFERENCES [log] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                       "[message] TEXT NOT NULL, "
                                                       "[format] TEXT NOT NULL)")
        self.cursor.execute("INSERT INTO [dbinfo]([key], [value]) VALUES('version', :version)", {"version": version + 1})
        self.db.commit()
        version = 1
      if version == 1:
        self.cursor.execute("CREATE TABLE [statcolumn]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                      "[name] TEXT UNIQUE NOT NULL)")
        self.cursor.execute("CREATE TABLE [statrow]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                   "[timestamp] REAL NOT NULL, "
                                                   "[subject] INTEGER NOT NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                   "[parent] INTEGER NULL REFERENCES [statrow] ON DELETE RESTRICT ON UPDATE RESTRICT)")
        self.cursor.execute("CREATE TABLE [statfield]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                     "[row] INTEGER NOT NULL REFERENCES [statrow] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                     "[column] INTEGER NOT NULL REFERENCES [statcolumn] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                     "[value] REAL NOT NULL)")
        self.cursor.execute("UPDATE [dbinfo] SET [value] = :version WHERE [key] = 'version'", {"version": version + 1})
        self.db.commit()
        version = 2
    except: self.db.rollback()

########NEW FILE########
__FILENAME__ = stratumworksource
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##############################
# Stratum work source module #
##############################



import sys
import socket
import time
import json
import struct
import traceback
from binascii import hexlify, unhexlify
from threading import Thread, RLock, Condition
from hashlib import sha256
from core.actualworksource import ActualWorkSource
from core.job import Job



class StratumWorkSource(ActualWorkSource):
  
  version = "theseven.stratum work source v0.1.0"
  default_name = "Untitled Stratum work source"
  settings = dict(ActualWorkSource.settings, **{
    "connecttimeout": {"title": "Connect timeout", "type": "float", "position": 19000},
    "responsetimeout": {"title": "Response timeout", "type": "float", "position": 19100},
    "host": {"title": "Host", "type": "string", "position": 1000},
    "port": {"title": "Port", "type": "int", "position": 1010},
    "username": {"title": "User name", "type": "string", "position": 1100},
    "password": {"title": "Password", "type": "password", "position": 1120},
  })
  

  def __init__(self, core, state = None):
    super(StratumWorkSource, self).__init__(core, state)
    self.datalock = RLock()
    self.txnlock = RLock()
    self.wakeup = Condition()
    self.tail = unhexlify(b"00000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000")
    
    
  def apply_settings(self):
    super(StratumWorkSource, self).apply_settings()
    if not "connecttimeout" in self.settings or not self.settings.connecttimeout:
      self.settings.connecttimeout = 5
    if not "responsetimeout" in self.settings or not self.settings.responsetimeout:
      self.settings.responsetimeout = 5
    if not "host" in self.settings: self.settings.host = ""
    if not "port" in self.settings or not self.settings.port: self.settings.port = 3333
    if not "username" in self.settings: self.settings.username = ""
    if not "password" in self.settings: self.settings.password = ""
    if self.started and (self.settings.host != self.host or self.settings.port != self.port or self.settings.username != self.username or self.settings.password != self.password): self.async_restart()

    
  def _reset(self):
    super(StratumWorkSource, self)._reset()
    self.timeoutthread = None
    self.listenerthread = None
    self.data = None
    self.txns = {}
    self.txnid = 1
    self.difficulty = 1
    self._calculate_target()
    
    
  def _start(self):
    super(StratumWorkSource, self)._start()
    self.host = self.settings.host
    self.port = self.settings.port
    self.username = self.settings.username
    self.password = self.settings.password
    if not self.settings.host or not self.settings.port: return
    self.shutdown = False
    self.listenerthread = Thread(None, self._listener, "%s_listener" % self.settings.name)
    self.listenerthread.daemon = True
    self.listenerthread.start()
    self.timeoutthread = Thread(None, self._timeout, "%s_timeout" % self.settings.name)
    self.timeoutthread.daemon = True
    self.timeoutthread.start()
    
    
  def _stop(self):
    self.shutdown = True
    with self.wakeup: self.wakeup.notify()
    if self.timeoutthread: self.timeoutthread.join(3)
    if self.listenerthread: self.listenerthread.join(3)
    super(StratumWorkSource, self)._stop()
    
    
  def _calculate_target(self):
    target = int(0xffff0000000000000000000000000000000000000000000000000000 / self.difficulty)
    self.target = b""
    for i in range(8):
      self.target += struct.pack("<I", target & 0xffffffff)
      target >>= 32    
    
    
  def _get_running_fetcher_count(self):
    return 0, 0
  
  
  def _start_fetcher(self):
    with self.datalock:
      if not self.data or self.shutdown: return False, 0
      extranonce2 = unhexlify((("%%0%dx" % (2 * self.data["extranonce2len"])) % self.data["extranonce2"]).encode("ascii"))
      self.data["extranonce2"] += 1
      coinbase = self.data["coinb1"] + self.data["extranonce1"] + extranonce2 + self.data["coinb2"]
      merkle = sha256(sha256(coinbase).digest()).digest()
      for branch in self.data["merkle_branch"]: merkle = sha256(sha256(merkle + branch).digest()).digest()
      merkle = struct.pack("<8I", *struct.unpack(">8I", merkle))
      ntime = struct.pack(">I", self.data["ntime"] + int(time.time()))
      data = self.data["version"] + self.data["prevhash"] + merkle + ntime + self.data["nbits"] + self.tail
      target = self.data["target"]
      job_id = self.data["job_id"]
    job = Job(self.core, self, time.time() + 60, data, target)
    job._stratum_job_id = job_id
    job._stratum_extranonce2 = hexlify(extranonce2).decode("ascii")
    job._stratum_ntime = hexlify(ntime).decode("ascii")
    self._push_jobs([job], "stratum generator")
    return 1, 1
  
  
  def _txn(self, method, params = None, callback = None, errorcallback = None, timeoutcallback = None, timeout = None):
    if not timeout: timeout = self.settings.responsetimeout
    with self.txnlock:
      if not self.conn: raise Exception("Connection is not active")
      txn = self.txnid
      self.txnid += 1
      self.txns[txn] = {
        "method": method,
        "params": params,
        "timeout": time.time() + timeout,
        "callback": callback,
        "errorcallback": errorcallback,
        "timeoutcallback": timeoutcallback,
      }
      self.connw.write(json.dumps({"id": txn, "method": method, "params": params}) + "\n")
      self.connw.flush()


  def _close_connection(self):
    with self.txnlock:
      try: self.connw.close()
      except: pass
      try: self.connr.close()
      except: pass
      try: self.conn.shutdown()
      except: pass
      try: self.conn.close()
      except: pass
      self.conn = None
    self._cancel_jobs()
      
  
  def _listener(self):
    tries = 0
    starttime = time.time()
    while not self.shutdown:
      try:
        with self.txnlock:
          self.conn = socket.create_connection((self.host, self.port), self.settings.connecttimeout)
          self.conn.settimeout(None)
          if sys.version_info[0] < 3:
            self.connr = self.conn.makefile("r", 1)
            self.connw = self.conn.makefile("w", 1)
          else:
            self.connr = self.conn.makefile("r", buffering = 1, encoding = "utf_8", newline = "\n")
            self.connw = self.conn.makefile("w", buffering = 1, encoding = "utf_8", newline = "\n")
          self._txn("mining.authorize", [self.username, self.password], self._authorized, self._setup_failed, self._setup_timeout)
        while not self.shutdown:
          msgs = json.loads(self.connr.readline())
          if not isinstance(msgs, list): msgs = [msgs]
          for msg in msgs: 
            if "id" in msg and msg["id"]:
              with self.txnlock:
                if not msg["id"] in self.txns:
                  self.core.log(self, "Received unexpected Stratum response: %s\n" % msg, 200, "y")
                  continue
                txn = self.txns[msg["id"]]
                if "error" in msg and msg["error"]:
                  if txn["errorcallback"]: txn["errorcallback"](txn, msg["error"])
                  else: self._default_error_handler(txn, msg["error"])
                elif txn["callback"]: txn["callback"](txn, msg["result"])
                del self.txns[msg["id"]]
            elif msg["method"] == "mining.notify":
              with self.datalock:
                self.data = {
                  "job_id": msg["params"][0],
                  "prevhash": unhexlify(msg["params"][1].encode("ascii")),
                  "coinb1": unhexlify(msg["params"][2].encode("ascii")),
                  "coinb2": unhexlify(msg["params"][3].encode("ascii")),
                  "merkle_branch": [unhexlify(branch.encode("ascii")) for branch in msg["params"][4]],
                  "version": unhexlify(msg["params"][5].encode("ascii")),
                  "nbits": unhexlify(msg["params"][6].encode("ascii")),
                  "ntime": struct.unpack(">I", unhexlify(msg["params"][7].encode("ascii")))[0] - int(time.time()),
                  "extranonce1": self.extranonce1,
                  "extranonce2len": self.extranonce2len,
                  "extranonce2": 0,
                  "difficulty": self.difficulty,
                  "target": self.target,
                }
              self.core.log(self, "Received new job generation data (%sflushing old jobs)\n" % ("" if msg["params"][8] else "not "), 500)
              if msg["params"][8]: self._cancel_jobs()
              self.blockchain.check_job(Job(self.core, self, 0, self.data["version"] + self.data["prevhash"] + b"\0" * 68 + self.data["nbits"] + self.tail, self.target, True))
            elif msg["method"] == "mining.set_difficulty":
              self.difficulty = float(msg["params"][0])
              self._calculate_target()
              self.core.log(self, "Received new job difficulty: %f\n" % self.difficulty, 500)
              self._cancel_jobs()
            else: self.core.log(self, "Received unknown Stratum notification: %s\n" % msg, 300, "y")
      except:
        with self.datalock: self.data = None
        self.core.log(self, "Stratum connection died: %s\n" % (traceback.format_exc()), 200, "r")
        self._close_connection()
        tries += 1
        if time.time() - starttime >= 60: tries = 0
        if tries > 5: time.sleep(30)
        else: time.sleep(1)
        starttime = time.time()


  def _timeout(self):
    with self.wakeup:
      while not self.shutdown:
        with self.txnlock:
          now = time.time()
          for txn in list(self.txns):
            if self.txns[txn]["timeout"] < now:
              if self.txns[txn]["timeoutcallback"]: self.txns[txn]["timeoutcallback"](self.txns[txn], False)
              else: self._default_timeout_handler(self.txns[txn], False)
              del self.txns[txn]
        self.wakeup.wait(1)
      for txn in list(self.txns):
        if self.txns[txn]["timeoutcallback"]: self.txns[txn]["timeoutcallback"](self.txns[txn], True)
        else: self._default_timeout_handler(self.txns[txn], True)
    self._close_connection()
    
    
  def _default_error_handler(txn, error):
    self.core.log(self, "Stratum transaction failed: method=%s, params=%s, error=%s\n" % (txn["method"], txn["params"], error), 200, "y")
    
    
  def _default_timeout_handler(txn, shutdown):
    if shutdown: return
    self.core.log(self, "Stratum transaction timed out: method=%s, params=%s\n" % (txn["method"], txn["params"]), 200, "y")
    
    
  def _subscribed(self, txn, response):
    self.extranonce1 = unhexlify(response[1].encode("ascii"))
    self.extranonce2len = int(response[2])
    self.core.log(self, "Successfully subscribed to Stratum service\n", 400, "g")

  
  def _authorized(self, txn, response):
    self._txn("mining.subscribe", [], self._subscribed, self._setup_failed, self._setup_timeout)
    self.core.log(self, "Successfully authorized Stratum worker %s\n" % self.settings.username, 400, "g")
    
    
  def _setup_failed(self, txn, error):
    self.core.log(self, "Stratum worker authorization failed: %s\n" % error, 200, "r")
    self._close_connection()
    
    
  def _setup_timeout(self, txn, shutdown):
    if shutdown: return
    self.core.log(self, "Stratum worker authorization timed out\n", 200, "r")
    self._close_connection()
    
    
  def _nonce_timeout_err(self, shutdown):
    if shutdown: return "shutting down"
    self._close_connection()
    return "timed out"
        
        
  def nonce_found(self, job, data, nonce, noncediff):
    data = [self.username, job._stratum_job_id, job._stratum_extranonce2, job._stratum_ntime, hexlify(nonce).decode("ascii")]
    submitted = lambda txn, result: job.nonce_handled_callback(nonce, noncediff, result)
    submit_failed = lambda txn, error: job.nonce_handled_callback(nonce, noncediff, error)
    submit_timeout = lambda txn, shutdown: job.nonce_handled_callback(nonce, noncediff, self._nonce_timeout_err(shutdown))
    try: self._txn("mining.submit", data, submitted, submit_failed, submit_timeout)
    except Exception as e: job.nonce_handled_callback(nonce, noncediff, str(e))

########NEW FILE########
__FILENAME__ = blockchaineditor
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi
import traceback



@jsonapi
def getblockchains(core, webui, httprequest, path, request, privileges):
  return [{"id": b.id, "name": b.settings.name} for b in core.blockchains]

  

@jsonapi
def createblockchain(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    name = request["name"]
    from core.blockchain import Blockchain
    blockchain = Blockchain(core)
    blockchain.settings.name = name
    blockchain.apply_settings()
    core.add_blockchain(blockchain)
    return {}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def deleteblockchain(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    blockchain = core.registry.get(request["id"])
    core.remove_blockchain(blockchain)
    blockchain.destroy()
    return {}
  except: return {"error": traceback.format_exc()}

########NEW FILE########
__FILENAME__ = debug
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



import sys
import threading
import traceback
from ..decorators import jsonapi



@jsonapi
def dumpthreadstates(core, webui, httprequest, path, request, privileges):
  id2name = dict([(th.ident, th.name) for th in threading.enumerate()])
  code = []
  for threadId, stack in sys._current_frames().items():
      code.append("\n# Thread: %s(%d)" % (id2name.get(threadId,""), threadId))
      for filename, lineno, name, line in traceback.extract_stack(stack):
          code.append('File: "%s", line %d, in %s' % (filename, lineno, name))
          if line: code.append("  %s" % (line.strip()))
  return {"data": "\n".join(code)}

########NEW FILE########
__FILENAME__ = frontendeditor
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi
import traceback



@jsonapi
def getfrontendclasses(core, webui, httprequest, path, request, privileges):
  return [{"id": c.id, "version": c.version} for c in core.frontendclasses]

  

@jsonapi
def getfrontends(core, webui, httprequest, path, request, privileges):
  return [{"id": f.id, "name": f.settings.name, "class": f.__class__.id} for f in core.frontends]

  

@jsonapi
def createfrontend(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    frontendclass = core.registry.get(request["class"])
    frontend = frontendclass(core)
    core.add_frontend(frontend)
    return {}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def deletefrontend(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    frontend = core.registry.get(request["id"])
    core.remove_frontend(frontend)
    frontend.destroy()
    return {}
  except: return {"error": traceback.format_exc()}

  
  
@jsonapi
def restartfrontend(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    frontend = core.registry.get(request["id"])
    frontend.restart()
    return {}
  except: return {"error": traceback.format_exc()}
  
########NEW FILE########
__FILENAME__ = gadgethost
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi



@jsonapi
def getgadgets(core, webui, httprequest, path, request, privileges):
  if request["collection"] == "dashboard":
    return [
      {"width": 200, "entries": [
        {"module": "menugadget", "moduleparam": None},
      ]},
      {"entries": [
        {"module": "statsgadget", "moduleparam": None},
        {"module": "loggadget", "moduleparam": None},
      ]},
    ]
  return [{"width": 0, "entries": []}]

########NEW FILE########
__FILENAME__ = init
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi



@jsonapi
def init(core, webui, httprequest, path, request, privileges):
  return {
    "services": [[], ["nls", "errorlayer"]],
    "rootmodule": "theme",
    "rootmoduleparam": { "default": "default", "module": "gadgethost", "moduleparam": "dashboard" },
  }

########NEW FILE########
__FILENAME__ = log
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi
import json
try: from queue import Queue
except: from Queue import Queue



@jsonapi
def stream(core, webui, httprequest, path, request, privileges):
  # Figure out the loglevel, by default send all messages
  loglevel = int(request["loglevel"]) if "loglevel" in request else 1000

  # Stream this by means of a chunked transfer
  httprequest.protocol_version = "HTTP/1.1"
  httprequest.log_request(200, "<chunked>")
  httprequest.send_response(200)
  httprequest.send_header("Content-Type", "application/json")
  httprequest.send_header("Transfer-Encoding", "chunked")
  httprequest.end_headers()

  def write_chunk(data):
    data = data.encode("utf_8")
    httprequest.wfile.write(("%X\r\n" % len(data)).encode("ascii") + data + "\r\n".encode("ascii"))
    httprequest.wfile.flush()

  queue = Queue()
    
  try:
    # Register our log message queue
    webui.register_log_listener(queue)
    
    while True:
      # Wait for data to turn up in the queue
      message = queue.get()
      messages = [message] if message["loglevel"] <= loglevel else []
      # If there's more in the queue, fetch that as well
      while True:
        try: message = queue.get_nowait()
        except: break
        if message["loglevel"] <= loglevel: messages.append(message)
      # Send the messages that we got to the client
      write_chunk(json.dumps(messages, ensure_ascii = False) + "\0")
      
  except: pass
  finally: webui.unregister_log_listener(queue)

########NEW FILE########
__FILENAME__ = menugadget
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi
import traceback



@jsonapi
def saveconfiguration(core, webui, httprequest, path, request, privileges):
  try:
    core.save()
    return {}
  except: return {"error": traceback.format_exc()}

########NEW FILE########
__FILENAME__ = settingseditor
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi
import traceback



@jsonapi
def readsettings(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    item = core.registry.get(request["id"])
    settings = {}
    for setting, data in item.__class__.settings.items():
      settings[data["position"]] = {"name": setting, "spec": data, "value": item.settings[setting]}
    return {"settings": settings}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def writesettings(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    item = core.registry.get(request["id"])
    for setting in item.__class__.settings.keys():
      if setting in request["settings"]:
          item.settings[setting] = request["settings"][setting]
    item.apply_settings()
    return {}
  except: return {"error": traceback.format_exc()}

########NEW FILE########
__FILENAME__ = statsgadget
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



import time
from ..decorators import jsonapi



@jsonapi
def getworkerstats(core, webui, httprequest, path, request, privileges):
  now = time.time()
  ghashes = core.stats.ghashes
  return {
    "timestamp": now,
    "starttime": core.stats.starttime,
    "ghashes": ghashes,
    "avgmhps": 1000. * ghashes / (now - core.stats.starttime),
    "workers": core.get_worker_statistics(),
  }


@jsonapi
def getworksourcestats(core, webui, httprequest, path, request, privileges):
  return {
    "timestamp": time.time(),
    "worksources": core.get_work_source_statistics(),
  }


@jsonapi
def getblockchainstats(core, webui, httprequest, path, request, privileges):
  return {
    "timestamp": time.time(),
    "blockchains": core.get_blockchain_statistics(),
  }


@jsonapi
def getallstats(core, webui, httprequest, path, request, privileges):
  now = time.time()
  ghashes = core.stats.ghashes
  return {
    "timestamp": now,
    "starttime": core.stats.starttime,
    "ghashes": ghashes,
    "avgmhps": 1000. * ghashes / (now - core.stats.starttime),
    "workers": core.get_worker_statistics(),
    "worksources": core.get_work_source_statistics(),
    "blockchains": core.get_blockchain_statistics(),
  }

########NEW FILE########
__FILENAME__ = uiconfig
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi



@jsonapi
def read(core, webui, httprequest, path, request, privileges):
  return webui.settings.uiconfig

  

@jsonapi
def write(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  webui.settings.uiconfig = request
  return {}

########NEW FILE########
__FILENAME__ = workereditor
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi
import traceback



@jsonapi
def getworkerclasses(core, webui, httprequest, path, request, privileges):
  return [{"id": c.id, "version": c.version} for c in core.workerclasses]

  

@jsonapi
def getworkers(core, webui, httprequest, path, request, privileges):
  return [{"id": w.id, "name": w.settings.name, "class": w.__class__.id} for w in core.workers]

  

@jsonapi
def createworker(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    workerclass = core.registry.get(request["class"])
    worker = workerclass(core)
    core.add_worker(worker)
    return {}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def deleteworker(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worker = core.registry.get(request["id"])
    core.remove_worker(worker)
    worker.destroy()
    return {}
  except: return {"error": traceback.format_exc()}
  
  
  
@jsonapi
def restartworker(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worker = core.registry.get(request["id"])
    worker.restart()
    return {}
  except: return {"error": traceback.format_exc()}
  
########NEW FILE########
__FILENAME__ = worksourceeditor
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



from ..decorators import jsonapi
import traceback



@jsonapi
def getworksourceclasses(core, webui, httprequest, path, request, privileges):
  return [{"id": c.id, "version": c.version, "is_group": c.is_group} for c in core.worksourceclasses]

  

@jsonapi
def getworksources(core, webui, httprequest, path, request, privileges):
  def format_work_source(worksource):
    data = {"id": worksource.id, "name": worksource.settings.name,
            "class": worksource.__class__.id, "is_group": worksource.is_group}
    if worksource.is_group: data["children"] = [format_work_source(c) for c in worksource.children]
    else:
      blockchain = worksource.get_blockchain()
      data["blockchain"] = blockchain.id if blockchain else 0
    return data
  return format_work_source(core.get_root_work_source())

  
  
@jsonapi
def createworksource(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksourceclass = core.registry.get(request["class"])
    parent = core.registry.get(request["parent"])
    worksource = worksourceclass(core)
    parent.add_work_source(worksource)
    return {}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def deleteworksource(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksource = core.registry.get(request["id"])
    if worksource.is_group:
      with worksource.childlock:
        for child in worksource.children:
          worksource.remove_work_source(child)
          child.destroy()
    worksource.get_parent().remove_work_source(worksource)
    worksource.destroy()
    return {}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def moveworksource(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksource = core.registry.get(request["id"])
    parent = core.registry.get(request["parent"])
    parent.add_work_source(worksource)
    return {}
  except: return {"error": traceback.format_exc()}

  
  
@jsonapi
def getblockchains(core, webui, httprequest, path, request, privileges):
  return [{"id": b.id, "name": b.settings.name} for b in core.blockchains]

  
  
@jsonapi
def setblockchain(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksource = core.registry.get(request["id"])
    try: blockchain = core.registry.get(request["blockchain"])
    except: blockchain = None
    worksource.set_blockchain(blockchain)
    return {}
  except: return {"error": traceback.format_exc()}
  
  
  
@jsonapi
def restartworksource(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksource = core.registry.get(request["id"])
    worksource.restart()
    return {}
  except: return {"error": traceback.format_exc()}
  
########NEW FILE########
__FILENAME__ = decorators
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



import json
import traceback



class jsonapi(object):


  def __init__(self, f):
    self.f = f

    
  def __call__(self, core, webui, httprequest, path, privileges):
    try:
      # We only accept JSON. If this is something different => 400 Bad Request
      if httprequest.headers.get("content-type", None) not in ("application/json", "application/json; charset=UTF-8"):
        return httprequest.send_response(400)
      length = int(httprequest.headers.get("content-length"))
      # Read request from the connection
      data = b""
      while len(data) < length: data += httprequest.rfile.read(length - len(data))
      # Decode the request
      data = json.loads(data.decode("utf_8"))
      # Run the API function
      data = self.f(core, webui, httprequest, path, data, privileges)
      if data == None: return
      # Encode the response
      data = json.dumps(data, ensure_ascii = False, default = lambda obj: None).encode("utf_8")
      # Send response headers
      httprequest.log_request(200, len(data))
      httprequest.send_response(200)
      httprequest.send_header("Content-Type", "application/json; charset=UTF-8")
      httprequest.send_header("Content-Length", len(data))
      httprequest.end_headers()
      httprequest.wfile.write(data)
    # Something went wrong, no matter what => 500 Internal Server Error
    except:
      core.log(webui, "Exception while handling API call: %s\n" % traceback.format_exc(), 700, "y")
      try: httprequest.send_response(500)
      except: pass

########NEW FILE########
__FILENAME__ = webui
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##########################################################################
# Web-based status and configuration user interface, offering a JSON API #
##########################################################################



import os
import time
import shutil
import base64
from threading import RLock, Thread
from core.basefrontend import BaseFrontend
from .api import handlermap
try: import urllib.parse as urllib
except: import urllib
try: from socketserver import ThreadingTCPServer
except: from SocketServer import ThreadingTCPServer
try: from http.server import BaseHTTPRequestHandler
except: from BaseHTTPServer import BaseHTTPRequestHandler



class WebUI(BaseFrontend):

  version = "theseven.webui v0.1.0"
  default_name = "WebUI"
  can_log = True
  can_configure = True
  can_autodetect = True
  settings = dict(BaseFrontend.settings, **{
    "port": {"title": "HTTP port", "type": "int", "position": 1000},
    "users": {
      "title": "Users",
      "type": "dict",
      "key": {"title": "User:Password", "type": "string"},
      "value": {
        "title": "Privilege level",
        "type": "enum",
        "values": [
          {"value": "readonly", "title": "Read only access"},
          {"value": "admin", "title": "Full access"},
        ],
      },
      "position": 2000
    },
    "log_buffer_max_length": {"title": "Maximum log buffer length", "type": "int", "position": 3000},
    "log_buffer_purge_size": {"title": "Log buffer purge size", "type": "int", "position": 3010},
  })


  @classmethod
  def autodetect(self, core):
    core.add_frontend(self(core))


  def __init__(self, core, state = None):
    super(WebUI, self).__init__(core, state)
    self.log_lock = RLock()


  def apply_settings(self):
    super(WebUI, self).apply_settings()
    if not "port" in self.settings: self.settings.port = 8832
    if not "users" in self.settings: self.settings.users = {"admin:mpbm": "admin"}
    if not "uiconfig" in self.settings: self.settings.uiconfig = {"loggadget": {"loglevel": self.core.default_loglevel}}
    if not "log_buffer_max_length" in self.settings: self.settings.log_buffer_max_length = 1000
    if not "log_buffer_purge_size" in self.settings: self.settings.log_buffer_purge_size = 100
    if self.started and self.settings.port != self.port: self.async_restart(3)


  def _reset(self):
    self.log_buffer = []
    self.log_listeners = []


  def _start(self):
    super(WebUI, self)._start()
    self.httpd = ThreadingTCPServer(("", self.settings.port), RequestHandler, False)
    self.httpd.webui = self
    self.httpd.allow_reuse_address = True
    self.httpd.daemon_threads = True
    self.httpd.server_bind()
    self.httpd.server_activate()
    self.serverthread = Thread(None, self.httpd.serve_forever, self.settings.name + "_httpd")
    self.serverthread.daemon = True
    self.serverthread.start()
    self.port = self.settings.port


  def _stop(self):
    self.httpd.shutdown()
    self.serverthread.join(10)
    self.httpd.server_close()
    super(WebUI, self)._stop()


  def write_log_message(self, source, timestamp, loglevel, messages):
    if not self.started: return
    data = {
      "timestamp": time.mktime(timestamp.timetuple()) * 1000 + timestamp.microsecond / 1000.,
      "loglevel": loglevel,
      "source": source.settings.name,
      "message": [{"data": data, "format": format} for data, format in messages],
    }
    with self.log_lock:
      for queue in self.log_listeners:
        queue.put(data)
      self.log_buffer.append(data)
      if len(self.log_buffer) > self.settings.log_buffer_max_length:
        self.log_buffer = self.log_buffer[self.settings.log_buffer_purge_size:]


  def register_log_listener(self, listener):
    with self.log_lock:
      if not listener in self.log_listeners:
        self.log_listeners.append(listener)
      for data in self.log_buffer: listener.put(data)


  def unregister_log_listener(self, listener):
    with self.log_lock:
      while listener in self.log_listeners:
        self.log_listeners.remove(listener)



class RequestHandler(BaseHTTPRequestHandler):

  server_version = WebUI.version
  rootfile = "/static/init/init.htm"
  mimetypes = {
    '': 'application/octet-stream',  # Default
    '.htm': 'text/html; charset=UTF-8',
    '.html': 'text/html; charset=UTF-8',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.js': 'text/javascript; charset=UTF-8',
    '.css': 'text/css; charset=UTF-8',
  }


  def log_request(self, code = '-', size = '-'):
    if code == 200:
      if size != "-": self.log_message("HTTP request: %s \"%s\" %s %s", self.address_string(), self.requestline, str(code), str(size))
    else: self.log_error("Request failed: %s \"%s\" %s %s", self.address_string(), self.requestline, str(code), str(size))


  def log_error(self, format, *args):
    webui = self.server.webui
    webui.core.log(webui, "%s\n" % (format % args), 600, "y")


  def log_message(self, format, *args):
    webui = self.server.webui
    webui.core.log(webui, "%s\n" % (format % args), 800, "")


  def do_HEAD(self):
    # Essentially the same as GET, just without a body
    self.do_GET(False)


  def do_GET(self, send_body = True):
    # Figure out the base path that will be prepended to the requested path
    basepath = os.path.realpath(os.path.join(os.path.dirname(__file__), "wwwroot"))
    # Remove query strings and anchors, and unescape the path
    path = urllib.unquote(self.path.split('?',1)[0].split('#',1)[0])
    # Rewrite requests to "/" to the specified root file
    if path == "/": path = self.__class__.rootfile
    # Paths that don't start with a slash are invalid => 400 Bad Request
    if path[0] != "/": return self.fail(400)
    # Check authentication and figure out privilege level
    privileges = self.check_auth()
    if not privileges:
      # Invalid credentials => 401 Authorization Required
      self.fail(401, [("WWW-Authenticate", "Basic realm=\"MPBM WebUI\"")])
      return None
    # Figure out the actual filesystem path to the requested file
    path = os.path.realpath(os.path.join(basepath, path[1:]))
    # If it tries to escape from the wwwroot directory => 403 Forbidden
    if path[:len(basepath)] != basepath: return self.fail(403)
    # If it simply isn't there => 404 Not Found
    if not os.path.exists(path): return self.fail(404)
    # If it isn't a regular file (but e.g. a directory) => 403 Forbidden
    if not os.path.isfile(path): return self.fail(403)
    # Try to figure out the mime type based on the file name extension
    ext = os.path.splitext(path)[1]
    mimetypes = self.__class__.mimetypes
    if ext in mimetypes: mimetype = mimetypes[ext]
    elif ext.lower() in mimetypes: mimetype = mimetypes[ext.lower()]
    else: mimetype = mimetypes['']
    try:
      f = open(path, "rb")
      # Figure out file size using seek/tell
      f.seek(0, os.SEEK_END)
      length = f.tell()
      f.seek(0, os.SEEK_SET)
      # Send response headers
      self.log_request(200, length)
      self.send_response(200)
      self.send_header("Content-Type", mimetype)
      self.send_header("Content-Length", length)
      self.end_headers()
      # Send file data to the client, if this isn't a HEAD request
      if send_body: shutil.copyfileobj(f, self.wfile, length)
    # Something went wrong, no matter what => 500 Internal Server Error
    except: self.fail(500)
    finally:
      try: f.close()
      except: pass


  def do_POST(self):
    # Remove query strings and anchors, and unescape the path
    path = urllib.unquote(self.path.split('?',1)[0].split('#',1)[0])
    # Paths that don't start with a slash are invalid => 400 Bad Request
    if path[0] != "/": return self.fail(400)
    # Check authentication and figure out privilege level
    privileges = self.check_auth()
    if not privileges:
      # Invalid credentials => 401 Authorization Required
      self.fail(401, [("WWW-Authenticate", "Basic realm=\"MPBM WebUI\"")])
      return None
    # Look for a handler for that path and execute it if present
    if path in handlermap:
      handlermap[path](self.server.webui.core, self.server.webui, self, path, privileges)
    # No handler for that path found => 404 Not Found
    else: self.fail(404)


  def check_auth(self):
    # Check authentication and figure out privilege level
    authdata = self.headers.get("authorization", None)
    credentials = ""
    if authdata != None:
      authdata = authdata.split(" ", 1)
      if authdata[0].lower() == "basic":
        try: credentials = base64.b64decode(authdata[1].encode("ascii")).decode("utf_8")
        except: pass
    privileges = None
    if credentials in self.server.webui.settings.users:
      privileges = self.server.webui.settings.users[credentials]
    return privileges


  def fail(self, status, headers = []):
    self.send_response(status)
    for header in headers:
      self.send_header(*header)
    self.send_header("Content-Length", 0)
    self.end_headers()

########NEW FILE########
__FILENAME__ = boardproxy
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



###############################################################
# ZTEX USB FPGA Module out of process board access dispatcher #
###############################################################



import time
import signal
import struct
import traceback
from threading import Thread, Condition, RLock
from multiprocessing import Process
from core.job import Job
from .driver import ZtexDevice


class ZtexBoardProxy(Process):
  

  def __init__(self, rxconn, txconn, serial, takeover, firmware, pollinterval):
    super(ZtexBoardProxy, self).__init__()
    self.rxconn = rxconn
    self.txconn = txconn
    self.serial = serial
    self.takeover = takeover
    self.firmware = firmware
    self.pollinterval = pollinterval


  def run(self):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    self.lock = RLock()
    self.wakeup = Condition()
    self.error = None
    self.pollingthread = None
    self.shutdown = False
    self.job = None
    self.checklockout = 0
    self.lastnonce = 0
    self.multiplier = 0
  
    try:

      # Listen for setup commands
      while True:
        data = self.rxconn.recv()
        
        if data[0] == "connect": break
        
        else: raise Exception("Unknown setup message: %s" % str(data))
        
      # Connect to board and upload firmware if neccessary
      self.device = ZtexDevice(self, self.serial, self.takeover, self.firmware)
      
      # Configure clock
      self._set_multiplier(self.device.default_multiplier)

      # Start polling thread
      self.pollingthread = Thread(None, self.polling_thread, "polling_thread")
      self.pollingthread.daemon = True
      self.pollingthread.start()
      
      self.send("started_up")

      # Listen for commands
      while True:
        if self.error: raise self.error
      
        data = self.rxconn.recv()
        
        if data[0] == "shutdown": break

        elif data[0] == "ping": self.send("pong")

        elif data[0] == "pong": pass

        elif data[0] == "set_pollinterval":
          self.pollinterval = data[1]
          with self.wakeup: self.wakeup.notify()
        
        elif data[0] == "send_job":
          self.checklockout = time.time() + 1
          self.job = data[1]
          with self.wakeup:
            start = time.time()
            self.device.send_job(data[1][64:76] + data[2])
            end = time.time()
            self.lastnonce = 0
          self.checklockout = end + 0.5
          self.respond(start, end)
        
        else: raise Exception("Unknown message: %s" % str(data))
      
    except: self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
    finally:
      self.shutdown = True
      with self.wakeup: self.wakeup.notify()
      try: self.pollingthread.join(2)
      except: pass
      self.send("dying")
      
      
  def send(self, *args):
    with self.lock: self.txconn.send(args)
      
      
  def respond(self, *args):
    self.send("response", *args)
      
      
  def log(self, message, loglevel, format = ""):
    self.send("log", message, loglevel, format)
    
    
  def polling_thread(self):
    try:
      lastshares = []
      errorcount = [0] * (self.device.maximum_multiplier + 1)
      errorweight = [0] * (self.device.maximum_multiplier + 1)
      maxerrorrate = [0] * (self.device.maximum_multiplier + 1)
      errorlimit = 0.05
      errorhysteresis = 0.1
      counter = 0
      
      while not self.shutdown:
      
        counter += 1
      
        # Poll for nonces
        now = time.time()
        nonces = self.device.read_nonces()
        exhausted = False
        with self.wakeup:
          if nonces[0][1] < self.lastnonce:
            self.lastnonce = nonces[0][1]
            exhausted = True
        if exhausted: self.send("keyspace_exhausted")
        for nonce in nonces:
          if nonce[0] != -self.device.nonce_offset and not nonce[0] in lastshares:
            if self.job: self.send("nonce_found", time.time(), struct.pack("<I", nonce[0]))
            lastshares.append(nonce[0])
            while len(lastshares) > len(nonces): lastshares.pop(0)
        
        # Verify proper operation and adjust clocking if neccessary
        if now > self.checklockout and self.job:
          errorcount[self.multiplier] *= 0.995
          errorweight[self.multiplier] = errorweight[self.multiplier] * 0.995 + 1
          for nonce in nonces:
            invalid = True
            for offset in (0, 1, -1, 2, -2):
              hash = Job.calculate_hash(self.job[:76] + struct.pack("<I", nonce[1] + offset))
              if struct.unpack("!I", hash[-4:])[0] == (nonce[2] + 0x5be0cd19) & 0xffffffff:
                invalid = False
                break
            if invalid: errorcount[self.multiplier] += 1. / len(nonces)
          certainty = min(1, errorweight[self.multiplier] / 100)
          errorrate = errorcount[self.multiplier] / errorweight[self.multiplier]
          maxerrorrate[self.multiplier] = max(maxerrorrate[self.multiplier], errorrate * certainty)
          for i in range(len(maxerrorrate) - 1):
            if maxerrorrate[i + 1] * i < maxerrorrate[i] * (i + 20):
              maxerrorrate[i + 1] = maxerrorrate[i] * (1 + 20.0 / i)
          limit = 0
          while limit < self.device.default_multiplier and maxerrorrate[limit + 1] < errorlimit: limit += 1
          while limit < self.device.maximum_multiplier and errorweight[limit] > 150 and maxerrorrate[limit + 1] < errorlimit: limit += 1
          multiplier = 0
          best = 0
          for i in range(limit + 1):
            effective = (i + 1 + (errorhysteresis if i == self.multiplier else 0)) * (1 - maxerrorrate[i])
            if effective > best:
              best = effective
              multiplier = i
          self._set_multiplier(multiplier)
          
          if counter >= 10:
            counter = 0
            try: self.send("error_rate", errorcount[self.multiplier] / errorweight[self.multiplier])
            except: pass

        with self.wakeup: self.wakeup.wait(self.pollinterval)
        
    except Exception as e:
      self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
      self.error = e
      # Unblock main thread
      self.send("ping")

      
  def _set_multiplier(self, multiplier):
    multiplier = min(max(multiplier, 1), self.device.maximum_multiplier)
    if multiplier == self.multiplier: return
    self.device.set_multiplier(multiplier)
    self.multiplier = multiplier
    self.checklockout = time.time() + 2
    self.send("speed_changed", (multiplier + 1) * self.device.base_frequency * self.device.hashes_per_clock)

########NEW FILE########
__FILENAME__ = driver
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#########################################
# ZTEX USB FPGA Module low level driver #
#########################################



import time
import usb
import struct
import traceback
from array import array
from threading import RLock



class ZtexDevice(object):
  

  def __init__(self, proxy, serial, takeover, firmware):
    self.lock = RLock()
    self.proxy = proxy
    self.serial = serial
    self.takeover = takeover
    self.firmware = firmware
    self.handle = None
    permissionproblem = False
    deviceinuse = False
    for bus in usb.busses():
      if self.handle != None: break
      for dev in bus.devices:
        if self.handle != None: break
        if dev.idVendor == 0x221a and dev.idProduct >= 0x100 and dev.idProduct <= 0x1ff:
          try:
            handle = dev.open()
            _serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
            if serial == "" or serial == _serial:
              try:
                if self.takeover:
                  handle.reset()
                  time.sleep(1)
                configuration = dev.configurations[0]
                interface = configuration.interfaces[0][0]
                handle.setConfiguration(configuration.value)
                handle.claimInterface(interface.interfaceNumber)
                handle.setAltInterface(interface.alternateSetting)
                self.handle = handle
                self.serial = _serial
              except: deviceinuse = True
          except: permissionproblem = True
    if self.handle == None:
      if deviceinuse:
        raise Exception("Can not open the specified device, possibly because it is already in use")
      if permissionproblem:
        raise Exception("Can not open the specified device, possibly due to insufficient permissions")
      raise Exception("Can not open the specified device")

    descriptor = array("B", self.handle.controlMsg(0xc0, 0x22, 40, 0, 0, 100))
    if len(descriptor) != 40: raise Exception("Bad ZTEX descriptor length: %d" % len(descriptor))
    size, version, magic = struct.unpack("<2BI", descriptor[:6])
    product = struct.unpack("4B", descriptor[6:10])
    fwversion, ifversion, = struct.unpack("2B", descriptor[10:12])
    ifcaps = struct.unpack("6B", descriptor[12:18])
    moduledata = struct.unpack("12B", descriptor[18:30])
    sn = struct.unpack("10s", descriptor[30:])[0].decode("ascii")
    if size != 40: raise Exception("Bad ZTEX descriptor size: %d" % size)
    if version != 1: raise Exception("Bad ZTEX descriptor version: %d" % version)
    if magic != struct.unpack("<I", b"ZTEX")[0]: raise Exception("Bad ZTEX descriptor magic: %08X" % magic)
    if product[0] != 10: raise Exception("Firmware vendor is not ZTEX: %d.%d.%d.%d" % product)
    if product[2:] != (1, 1): raise Exception("Device is not running a bitcoin miner firmware: %02X %02X %02X %02X" % product)
    if ifversion != 1: raise Exception("Bad ZTEX interface version: %d" % ifversion)
    if not (ifcaps[0] & 2): raise Exception("Firmware doesn't support FPGA capability")
    self.hs_supported = ifcaps[0] & 32
    self.proxy.log("MCU firmware: %d.%d.%d.%d, version %d, serial number %s, high speed programming%s supported\n" % (product + (fwversion, sn, "" if self.hs_supported else " NOT")), 400, "B")
    
    descriptor = array("B", self.handle.controlMsg(0xc0, 0x82, 64, 0, 0, 100))
    if len(descriptor) != 64: raise Exception("Bad BTCMiner descriptor length: %d" % len(descriptor))
    version, numnonces, offset, basefreq, defaultmultiplier, maxmultiplier, hashesperclock = struct.unpack("<BBHHBBH", descriptor[:10])
    firmware = struct.unpack("54s", descriptor[10:])[0].split(b"\0", 1)[0].decode("ascii")
    if version != 4: raise Exception("Bad BTCMiner descriptor version: %d, firmware outdated?" % version)
    self.num_nonces = numnonces + 1
    self.nonce_offset = offset - 10000
    self.base_frequency = basefreq * 10000
    self.default_multiplier = min(defaultmultiplier, maxmultiplier)
    self.maximum_multiplier = maxmultiplier
    self.hashes_per_clock = hashesperclock / 128.
    self.firmware_name = firmware
    defaultspeed = self.base_frequency * self.default_multiplier * self.hashes_per_clock / 1000000
    maxspeed = self.base_frequency * self.maximum_multiplier * self.hashes_per_clock / 1000000
    self.proxy.log("FPGA firmware: %s, default speed: %f MH/s, maximum speed: %f MH/s\n" % (self.firmware_name, defaultspeed, maxspeed), 400, "B")
    
    unconfigured, checksum, bytestransferred, initb, result, bitswap = struct.unpack("<BBIBBB", array("B", self.handle.controlMsg(0xc0, 0x30, 9, 0, 0, 100)))
    if unconfigured:
      self.proxy.log("Programming FPGA with firmware %s...\n" % self.firmware_name, 300, "B")
      firmwarepath = "%s/%s.bit" % (self.firmware, self.firmware_name)
      try:
        fwfile = open(firmwarepath, "rb")
        bitstream = fwfile.read()
        fwfile.close()
      except Exception as e: raise Exception("Could not read firmware from %s: %s" % (firmwarepath, str(e)))
      sig1 = bitstream.find(b"\xaa\x99\x55\x66")
      sig2 = bitstream.find(b"\x55\x99\xaa\x66")
      if sig2 < 0 or (sig1 >= 0 and sig1 < sig2): raise Exception("Signature not found in bitstream, wrong bit order?")
      self.handle.controlMsg(0x40, 0x31, b"", 0, 0, 100)
      if self.hs_supported:
        ep, interface = struct.unpack("<BB", array("B", self.handle.controlMsg(0xc0, 0x33, 2, 0, 0, 100)))
        self.handle.controlMsg(0x40, 0x34, b"", 0, 0, 100)
        pos = 0
        while pos < len(bitstream): pos += self.handle.bulkWrite(ep, bitstream[pos : pos + 65536], 500)
        self.handle.controlMsg(0x40, 0x35, b"", 0, 0, 100)
      else:
        pos = 0
        while pos < len(bitstream): pos += self.handle.controlMsg(0x40, 0x32, bitstream[pos : pos + 2048], 0, 0, 500)
      unconfigured, checksum, bytestransferred, initb, result, bitswap = struct.unpack("<BBIBBB", array("B", self.handle.controlMsg(0xc0, 0x30, 9, 0, 0, 100)))
      if unconfigured: raise Exception("FPGA configuration failed: FPGA did not assert DONE")
      
  
  def set_multiplier(self, multiplier):
    with self.lock:
      self.handle.controlMsg(0x40, 0x83, b"", multiplier, 0, 100)
      
  
  def send_job(self, data):
    with self.lock:
      self.handle.controlMsg(0x40, 0x80, data, 0, 0, 100)
      
  
  def read_nonces(self):
    with self.lock:
      data = array("B", self.handle.controlMsg(0xc0, 0x81, 12 * self.num_nonces, 0, 0, 100))
    nonces = []
    for i in range(self.num_nonces):
      values = struct.unpack("<III", data[12 * i : 12 * (i + 1)])
      nonces.append((values[0] - self.nonce_offset, values[1] - self.nonce_offset, values[2]))
    return nonces
      
########NEW FILE########
__FILENAME__ = ztexhotplug
# Modular Python Bitcoin Miner
# Copyright (C) 2011-2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##################################################
# ZTEX USB FPGA Module hotplug controller module #
##################################################



import traceback
from threading import Condition, Thread
from core.baseworker import BaseWorker
from .ztexworker import ZtexWorker



# Worker main class, referenced from __init__.py
class ZtexHotplugWorker(BaseWorker):
  
  version = "theseven.ztex hotplug manager v0.1.0"
  default_name = "ZTEX hotplug manager"
  can_autodetect = True
  settings = dict(BaseWorker.settings, **{
    "takeover": {"title": "Reset board if it appears to be in use", "type": "boolean", "position": 1200},
    "firmware": {"title": "Firmware file location", "type": "string", "position": 1400},
    "blacklist": {
      "title": "Board list type",
      "type": "enum",
      "values": [
        {"value": True, "title": "Blacklist"},
        {"value": False, "title": "Whitelist"},
      ],
      "position": 2000
    },
    "boards": {
      "title": "Board list",
      "type": "list",
      "element": {"title": "Serial number", "type": "string"},
      "position": 2100
    },
    "scaninterval": {"title": "Bus scan interval", "type": "float", "position": 2200},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 5100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 5200},
  })
  
  
  @classmethod
  def autodetect(self, core):
    try:
      found = False
      try:
        import usb
        for bus in usb.busses():
          for dev in bus.devices:
            if dev.idVendor == 0x221a and dev.idProduct >= 0x100 and dev.idProduct <= 0x1ff:
              try:
                handle = dev.open()
                serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                try:
                  configuration = dev.configurations[0]
                  interface = configuration.interfaces[0][0]
                  handle.setConfiguration(configuration.value)
                  handle.claimInterface(interface.interfaceNumber)
                  handle.releaseInterface()
                  handle.setConfiguration(0)
                  found = True
                  break
                except: pass
              except: pass
          if found: break
      except: pass
      if found: core.add_worker(self(core))
    except: pass
    
    
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Initialize bus scanner wakeup event
    self.wakeup = Condition()

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(ZtexHotplugWorker, self).__init__(core, state)

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexHotplugWorker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "takeover" in self.settings: self.settings.takeover = True
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/ztex/firmware/"
    if not "blacklist" in self.settings: self.settings.blacklist = True
    if self.settings.blacklist == "false": self.settings.blacklist = False
    else: self.settings.blacklist = not not self.settings.blacklist
    if not "boards" in self.settings: self.settings.boards = []
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    if not "scaninterval" in self.settings or not self.settings.scaninterval: self.settings.scaninterval = 10
    # Push our settings down to our children
    fields = ["takeover", "firmware", "jobinterval", "pollinterval"]
    for child in self.children:
      for field in fields: child.settings[field] = self.settings[field]
      child.apply_settings()
    # Rescan the bus immediately to apply the new settings
    with self.wakeup: self.wakeup.notify()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexHotplugWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexHotplugWorker, self)._start()
    # Initialize child map
    self.childmap = {}
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexHotplugWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(10)
    # Shut down child workers
    while self.children:
      child = self.children.pop(0)
      try:
        self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
        child.stop()
      except Exception as e:
        self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")

      
  # Main thread entry point
  # This thread is responsible for scanning for boards and spawning worker modules for them
  def main(self):
    import usb

    # Loop until we are shut down
    while not self.shutdown:
    
      try:
        boards = {}
        for bus in usb.busses():
          for dev in bus.devices:
            if dev.idVendor == 0x221a and dev.idProduct >= 0x100 and dev.idProduct <= 0x1ff:
              try:
                handle = dev.open()
                serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                try:
                  configuration = dev.configurations[0]
                  interface = configuration.interfaces[0][0]
                  handle.setConfiguration(configuration.value)
                  handle.claimInterface(interface.interfaceNumber)
                  handle.releaseInterface()
                  handle.setConfiguration(0)
                  available = True
                except: available = False
                boards[serial] = available
              except: pass
                
        for serial in boards.keys():
          if self.settings.blacklist:
            if serial in self.settings.boards: del boards[serial]
          else:
            if serial not in self.settings.boards: del boards[serial]
                
        kill = []
        for serial, child in self.childmap.items():
          if not serial in boards:
            kill.append((serial, child))
            
        for serial, child in kill:
          try:
            self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
            child.stop()
          except Exception as e:
            self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
          childstats = child.get_statistics()
          fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
          for field in fields: self.stats[field] += childstats[field]
          try: self.child.destroy()
          except: pass
          del self.childmap[serial]
          try: self.children.remove(child)
          except: pass
              
        for serial, available in boards.items():
          if serial in self.childmap: continue
          if not available and self.settings.takeover:
            try:
              for bus in usb.busses():
                if available: break
                for dev in bus.devices:
                  if available: break
                  if dev.idVendor == 0x221a and dev.idProduct >= 0x100 and dev.idProduct <= 0x1ff:
                    handle = dev.open()
                    _serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                    if _serial == serial:
                      handle.reset()
                      time.sleep(1)
                      configuration = dev.configurations[0]
                      interface = configuration.interfaces[0][0]
                      handle.setConfiguration(configuration.value)
                      handle.claimInterface(interface.interfaceNumber)
                      handle.releaseInterface()
                      handle.setConfiguration(0)
                      handle.reset()
                      time.sleep(1)
                      available = True
            except: pass
          if available:
            child = ZtexWorker(self.core)
            child.settings.name = "Ztex board " + serial
            child.settings.serial = serial
            fields = ["takeover", "firmware", "jobinterval", "pollinterval"]
            for field in fields: child.settings[field] = self.settings[field]
            child.apply_settings()
            self.childmap[serial] = child
            self.children.append(child)
            try:
              self.core.log(self, "Starting up worker %s...\n" % (child.settings.name), 800)
              child.start()
            except Exception as e:
              self.core.log(self, "Could not start worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
              
      except: self.core.log(self, "Caught exception: %s\n" % traceback.format_exc(), 100, "rB")
          
      with self.wakeup: self.wakeup.wait(self.settings.scaninterval)

########NEW FILE########
__FILENAME__ = ztexworker
# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#########################################
# ZTEX USB FPGA Module interface module #
#########################################



import time
import traceback
from multiprocessing import Pipe
from threading import RLock, Condition, Thread
from core.baseworker import BaseWorker
from .boardproxy import ZtexBoardProxy
try: from queue import Queue
except: from Queue import Queue



# Worker main class, referenced from __init__.py
class ZtexWorker(BaseWorker):
  
  version = "theseven.ztex worker v0.1.0"
  default_name = "Untitled ZTEX worker"
  settings = dict(BaseWorker.settings, **{
    "serial": {"title": "Board serial number", "type": "string", "position": 1000},
    "takeover": {"title": "Reset board if it appears to be in use", "type": "boolean", "position": 1200},
    "firmware": {"title": "Firmware base path", "type": "string", "position": 1400},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 4100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 4200},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(ZtexWorker, self).__init__(core, state)

    # Initialize proxy access locks and wakeup event
    self.lock = RLock()
    self.transactionlock = RLock()
    self.wakeup = Condition()
    self.workloopwakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "takeover" in self.settings: self.settings.takeover = False
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/fpgamining/x6500/firmware/x6500.bit"
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    # We can't switch the device on the fly, so trigger a restart if they changed.
    # self.serial is a cached copy of self.settings.serial.
    if self.started and self.settings.serial != self.serial: self.async_restart()
    # We need to inform the proxy about a poll interval change
    if self.started and self.settings.pollinterval != self.pollinterval: self._notify_poll_interval_changed()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.serial = None
    self.pollinterval = None
    self.stats.mhps = 0
    self.stats.errorrate = 0


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.serial = self.settings.serial
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Ping the proxy, otherwise the main thread might be blocked and can't wake up.
    try: self._proxy_message("ping")
    except: pass
    # Wait for the main thread to terminate, which in turn kills the child workers.
    self.mainthread.join(10)

      
  # Report custom statistics.
  def _get_statistics(self, stats, childstats):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self)._get_statistics(stats, childstats)
    stats.errorrate = self.stats.errorrate


  # Main thread entry point
  # This thread is responsible for booting the individual FPGAs and spawning worker threads for them
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()
        self.dead = False
        
        # Check if we have a device serial number
        if not self.serial: raise Exception("Device serial number not set!")
        
        # Try to start the board proxy
        proxy_rxconn, self.txconn = Pipe(False)
        self.rxconn, proxy_txconn = Pipe(False)
        self.pollinterval = self.settings.pollinterval
        self.proxy = ZtexBoardProxy(proxy_rxconn, proxy_txconn, self.serial,
                                    self.settings.takeover, self.settings.firmware, self.pollinterval)
        self.proxy.daemon = True
        self.proxy.start()
        proxy_txconn.close()
        self.response = None
        self.response_queue = Queue()
        
        # Tell the board proxy to connect to the board
        self._proxy_message("connect")
        
        while not self.shutdown:
          data = self.rxconn.recv()
          if self.dead: break
          if data[0] == "log": self.core.log(self, "Proxy: %s" % data[1], data[2], data[3])
          elif data[0] == "ping": self._proxy_message("pong")
          elif data[0] == "pong": pass
          elif data[0] == "dying": raise Exception("Proxy died!")
          elif data[0] == "response": self.response_queue.put(data[1:])
          elif data[0] == "started_up": self._notify_proxy_started_up(*data[1:])
          elif data[0] == "nonce_found": self._notify_nonce_found(*data[1:])
          elif data[0] == "speed_changed": self._notify_speed_changed(*data[1:])
          elif data[0] == "error_rate": self._notify_error_rate(*data[1:])
          elif data[0] == "keyspace_exhausted": self._notify_keyspace_exhausted(*data[1:])
          else: raise Exception("Proxy sent unknown message: %s" % str(data))
        
        
      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        with self.workloopwakeup: self.workloopwakeup.notify()
        try:
          for i in range(100): self.response_queue.put(None)
        except: pass
        try: self.workloopthread.join(2)
        except: pass
        try: self._proxy_message("shutdown")
        except: pass
        try: self.proxy.join(4)
        except: pass
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)

        
  def _proxy_message(self, *args):
    with self.lock:
      self.txconn.send(args)


  def _proxy_transaction(self, *args):
    with self.transactionlock:
      with self.lock:
        self.txconn.send(args)
      return self.response_queue.get()
      
      
  def _notify_poll_interval_changed(self):
    self.pollinterval = self.settings.pollinterval
    try: self._proxy_message("set_pollinterval", self.pollinterval)
    except: pass
    
    
  def _notify_proxy_started_up(self):
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.settings.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Start up the work loop thread, which handles pushing work to the device.
    self.workloopthread = Thread(None, self._workloop, self.settings.name + "_workloop")
    self.workloopthread.daemon = True
    self.workloopthread.start()

    
  def _notify_nonce_found(self, now, nonce):
    # Snapshot the current jobs to avoid race conditions
    oldjob = self.oldjob
    newjob = self.job
    # If there is no job, this must be a leftover from somewhere, e.g. previous invocation
    # or reiterating the keyspace because we couldn't provide new work fast enough.
    # In both cases we can't make any use of that nonce, so just discard it.
    if not oldjob and not newjob: return
    # Pass the nonce that we found to the work source, if there is one.
    # Do this before calculating the hash rate as it is latency critical.
    job = None
    if newjob:
      if newjob.nonce_found(nonce, oldjob): job = newjob
    if not job and oldjob:
      if oldjob.nonce_found(nonce): job = oldjob


  def _notify_speed_changed(self, speed):
    self.stats.mhps = speed / 1000000.
    self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
    self.core.log(self, "Running at %f MH/s\n" % self.stats.mhps, 300, "B")
    # Calculate the time that the device will need to process 2**32 nonces.
    # This is limited at 60 seconds in order to have some regular communication,
    # even with very slow devices (and e.g. detect if the device was unplugged).
    interval = min(60, 2**32 / speed)
    # Add some safety margin and take user's interval setting (if present) into account.
    self.jobinterval = min(self.settings.jobinterval, max(0.5, interval * 0.8 - 1))
    self.core.log(self, "Job interval: %f seconds\n" % self.jobinterval, 400, "B")
    # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
    self.jobs_per_second = 1. / self.jobinterval
    self.core.notify_speed_changed(self)

      
  def _notify_error_rate(self, rate):
    self.stats.errorrate = rate

      
  def _notify_keyspace_exhausted(self):
    with self.workloopwakeup: self.workloopwakeup.notify()
    self.core.log(self, "Exhausted keyspace!\n", 200, "y")

      
  def _send_job(self, job):
    return self._proxy_transaction("send_job", job.data, job.midstate)


  # This function should interrupt processing of the specified job if possible.
  # This is necesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast. We don't care whether it's a
  # graceful cancellation for this module because the work upload overhead is low. 
  def notify_canceled(self, job, graceful):
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.workloopwakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.workloopwakeup.notify()

        
  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def _workloop(self):
    try:
      # Job that the device is currently working on, or that is currently being uploaded.
      # This variable is used by BaseWorker to figure out the current work source for statistics.
      self.job = None
      # Job that was previously being procesed. Has been destroyed, but there might be some late nonces.
      self.oldjob = None

      # We keep control of the wakeup lock at all times unless we're sleeping
      self.workloopwakeup.acquire()
      # Eat up leftover wakeups
      self.workloopwakeup.wait(0)

      # Main loop, continues until something goes wrong or we're shutting down.
      while not self.shutdown:

        # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
        # Blocks until one is available. Because of this we need to release the
        # wakeup lock temporarily in order to avoid possible deadlocks.
        self.workloopwakeup.release()
        job = self.core.get_job(self, self.jobinterval + 2)
        self.workloopwakeup.acquire()
        
        # If a new block was found while we were fetching that job, just discard it and get a new one.
        if job.canceled:
          job.destroy()
          continue

        # Upload the job to the device
        self._sendjob(job)
        
        # If the job was already caught by a long poll while we were uploading it,
        # jump back to the beginning of the main loop in order to immediately fetch new work.
        if self.job.canceled: continue
        # Wait while the device is processing the job. If nonces are sent by the device, they
        # will be processed by the listener thread. If the job gets canceled, we will be woken up.
        self.workloopwakeup.wait(self.jobinterval)

    # If something went wrong...
    except Exception as e:
      # ...complain about it!
      self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
    finally:
      # We're not doing productive work any more, update stats and destroy current job
      self._jobend()
      self.stats.mhps = 0
      # Make the proxy and its listener thread restart
      self.dead = True
      try: self.workloopwakeup.release()
      except: pass
      # Ping the proxy, otherwise the main thread might be blocked and can't wake up.
      try: self._proxy_message("ping")
      except: pass
      

  # This function uploads a job to the device
  def _sendjob(self, job):
    # Move previous job to oldjob, and new one to job
    self.oldjob = self.job
    self.job = job
    # Send it to the FPGA
    start, now = self._send_job(job)
    # Calculate how long the old job was running
    if self.oldjob:
      if self.oldjob.starttime:
        self.oldjob.hashes_processed((now - self.oldjob.starttime) * self.stats.mhps * 1000000)
      self.oldjob.destroy()
    self.job.starttime = now

    
  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job != None:
      if self.job.starttime:
        self.job.hashes_processed((now - self.job.starttime) * self.stats.mhps * 1000000)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.oldjob = self.job
      self.job.destroy()
      self.job = None

########NEW FILE########
__FILENAME__ = run-mpbm
#!/usr/bin/env python


# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



################
# Bootstrapper #
################



import sys
import time
import signal
from optparse import OptionParser
from core.core import Core


if __name__ == "__main__":

  # Set up command line argument parset
  parser = OptionParser("Usage: %prog [instancename] [options]", version = Core.version)
  parser.add_option("--default-loglevel", "-l", action = "store", type = "int", default = 500,
                    help = "Set the default loglevel for new loggers and the fallback logger")
  parser.add_option("--detect-frontends", action = "store_true", default = False,
                    help = "Autodetect available frontends and add them to the instance")
  parser.add_option("--detect-workers", action = "store_true", default = False,
                    help = "Autodetect available workers and add them to the instance")
  parser.add_option("--add-example-work-sources", action = "store_true", default = False,
                    help = "Add the example work sources to the instance")
  (options, args) = parser.parse_args()

  # Figure out instance name
  if len(args) == 0: instancename = "default"
  elif len(args) == 1: instancename = args[0]
  else: parser.error("Incorrect number of arguments")

  # Create core instance, will load saved instance state if present
  core = Core(instance = instancename, default_loglevel = options.default_loglevel)

  # Autodetect appropriate frontends if requested or if a new instance is being set up
  if options.detect_frontends or core.is_new_instance:
    core.detect_frontends()

  # Autodetect available workers if requested or if a new instance is being set up
  if options.detect_workers or core.is_new_instance:
    core.detect_workers()

  # Add example work sources if requested or if a new instance is being set up
  if options.add_example_work_sources or core.is_new_instance:
    from core.blockchain import Blockchain
    from core.worksourcegroup import WorkSourceGroup
    from modules.theseven.bcjsonrpc.bcjsonrpcworksource import BCJSONRPCWorkSource
    # Find the Bitcoin block chain, or create it if neccessary
    blockchain = core.get_blockchain_by_name("Bitcoin")
    if not blockchain:
      blockchain = Blockchain(core)
      blockchain.settings.name = "Bitcoin"
      core.add_blockchain(blockchain)
    # Save the old root work source (will be moved around)
    usersources = core.get_root_work_source()
    # Create the new root work source group
    newroot = WorkSourceGroup(core)
    # Copy the old root work source's name to the new one
    newroot.settings.name = usersources.settings.name
    # Reconfigure the old root work source
    usersources.settings.name = "User work sources"
    usersources.settings.priority = 1000
    usersources.apply_settings()
    newroot.add_work_source(usersources)
    # Create example work source group
    examplesources = WorkSourceGroup(core)
    examplesources.settings.name = "Example/donation work sources"
    examplesources.settings.priority = 10
    examplesources.apply_settings()
    newroot.add_work_source(examplesources)
    # Register the new root work source
    core.set_root_work_source(newroot)
    # Add example work sources to their group
    worksource = BCJSONRPCWorkSource(core)
    worksource.set_blockchain(blockchain)
    worksource.settings.name = "BTCMP (donation)"
    worksource.settings.priority = 1
    worksource.settings.host = "rr.btcmp.com"
    worksource.settings.port = 7332
    worksource.settings.username = "TheSeven.worker"
    worksource.settings.password = "TheSeven"
    worksource.apply_settings()
    examplesources.add_work_source(worksource)
    worksource = BCJSONRPCWorkSource(core)
    worksource.set_blockchain(blockchain)
    worksource.settings.name = "BTCGuild (donation)"
    worksource.settings.priority = 1
    worksource.settings.host = "mine3.btcguild.com"
    worksource.settings.username = "TheSeven_guest"
    worksource.settings.password = "x"
    worksource.settings.longpollconnections = 0
    worksource.apply_settings()
    examplesources.add_work_source(worksource)
    worksource = BCJSONRPCWorkSource(core)
    worksource.set_blockchain(blockchain)
    worksource.settings.name = "Eligius (donation)"
    worksource.settings.priority = 1
    worksource.settings.host = "mining.eligius.st"
    worksource.settings.port = 8337
    worksource.settings.username = "1FZMW7BCzExsLmErT2o8oCMLcMYKwd7sHQ"
    worksource.settings.longpollconnections = 0
    worksource.apply_settings()
    examplesources.add_work_source(worksource)

  def stop(signum, frame):
    core.stop()
    sys.exit(0)

  signal.signal(signal.SIGINT, stop)
  signal.signal(signal.SIGTERM, stop)
  core.start()

  while True: time.sleep(100)

########NEW FILE########
