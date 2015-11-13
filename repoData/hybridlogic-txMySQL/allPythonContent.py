__FILENAME__ = example
from txmysql.protocol import MySQLClientFactory, MySQLProtocol, error
from twisted.internet import reactor, defer
import secrets
from twisted.application.service import Application

factory = MySQLClientFactory(username='root', password=secrets.MYSQL_ROOT_PASS)

class TestProtocol(MySQLProtocol):
    def __init__(self, *args, **kw):
        MySQLProtocol.__init__(self, *args, **kw)

    def connectionMade(self):
        MySQLProtocol.connectionMade(self)
        self.do_test()

    def connectionLost(self, reason):
        print reason
    def connectionFailed(self, reason):
        print reason

    @defer.inlineCallbacks
    def do_test(self):
        yield self.ready_deferred
        yield self.select_db('foo')
        try:
            yield self.query("drop table testing")
        except error.MySQLError, e:
            print "Table doesn't exist, ignoring %s" % str(e)

        yield self.query("""create table testing (
            id int primary key auto_increment,
            strings varchar(255),
            numbers int)""")
        
        results = yield self.fetchall("select * from testing")
        print results # should be []

        for i in range(10):
            yield self.query("insert into testing set strings='Hello world', numbers=%i" % i)
        results = yield self.fetchall("select * from testing")
        print results

factory.protocol = TestProtocol
#factory = policies.SpewingFactory(factory)
reactor.connectTCP('127.0.0.1', 3306, factory)

application = Application("Telnet Echo Server")


########NEW FILE########
__FILENAME__ = HybridUtils
import time
import re
import os
import sys
import pprint
import inspect

from twisted.internet import protocol,reactor,defer
from twisted.spread import pb
from twisted.internet import abstract,fdesc,threads
from twisted.python import log, failure
from collections import defaultdict

from twisted.web.client import Agent
from twisted.web.http_headers import Headers
import urllib

from twisted.web.iweb import IBodyProducer
from zope.interface import implements
from twisted.internet.defer import succeed

class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass

def httpRequest(url, values={}, headers={}, method='POST'):
    # Construct an Agent.
    agent = Agent(reactor)
    data = urllib.urlencode(values)

    d = agent.request(method,
                      url,
                      Headers(headers),
                      StringProducer(data) if data else None)

    def handle_response(response):
        if response.code == 204:
            d = defer.succeed('')
        else:
            class SimpleReceiver(protocol.Protocol):
                def __init__(s, d):
                    s.buf = ''; s.d = d
                def dataReceived(s, data):
                    s.buf += data
                def connectionLost(s, reason):
                    # TODO: test if reason is twisted.web.client.ResponseDone, if not, do an errback
                    s.d.callback(s.buf)

            d = defer.Deferred()
            response.deliverBody(SimpleReceiver(d))
        return d

    d.addCallback(handle_response)
    return d

def send_email(to, subject, body, from_addr='clusters@hybrid-logic.co.uk'):
    from twisted.mail.smtp import sendmail # XXX This causes blocking on
                                           # looking up our own IP address,
                                           # which will only work if bind is
                                           # running
    from email.mime.text import MIMEText
    host = 'localhost'
    to_addrs = list(set([to, 'tech@hybrid-logic.co.uk']))
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)

    d = sendmail(host, from_addr, to_addrs, msg.as_string())
    def success(r):
        print "CRITICAL Success sending email %s" % str(r)
    def error(e):
        print "CRITICAL Error sending email %s" % str(e)
    d.addCallback(success)
    d.addErrback(error)
    return d

def undefaulted(x):
  return dict(
    (k, undefaulted(v))
    for (k, v) in x.iteritems()
  ) if isinstance(x, defaultdict) else x

class SimpleListener():
    def __init__(self, noisy=False):
        self.noisy = noisy
        if self.noisy:
            print "*** Job started at %s\n" % (time.ctime(),)
        self.deferred = defer.Deferred()
       
    def startCmd(self, cmd):
        if self.noisy:
            print "*** Runnning command %s at %s\n" % (cmd, time.ctime())

    def outReceived(self, data):
        if self.noisy:
            print "OUT: " + data.strip()

    def errReceived(self, data):
        if self.noisy:
            print "ERR: " + data.strip()

    def processEnded(self, status):
        if self.noisy:
            print "\n*** Process ended at %s with status code %s\n" % (time.ctime(), status)

    def lastProcessEnded(self):
        if self.noisy:
            print "\n*** Job ended at %s\n" % time.ctime()
        self.deferred.callback(True)

class SpecialLock:
    # TODO: Add support for Deferreds to this so that we can return a deferred
    # which will fire when the queued function eventually runs - and unit test this.

    # Means "is currently running, if I get run again then add to run_next"
    locks = {}  # e.g., {'recompileZones':    True
                #       'recompileVhosts':    True}

    # Means "next time it finishes, start it again with this fn"
    run_again = {}  # e.g., {'recompileZones':    self.recompileZones,
                    #       'recompileVhosts':    self.recompileVhosts}

    def handleLock(self, lock_name, function):
        """Handles a special type of lock:
            * if it's already taken, set run_again = function but in such a way that it only runs again exactly once...
            * when removeLock is run, if run_again exists then do run it again, after setting it to False
        """
        print "*****************************************************"
        print "*** We have been called upon to handle a lock for %s" % lock_name
        
        # If not locked, carry on.
        if not self.locks.has_key(lock_name):
            print "*** Not locked, adding lock and carrying on"
            print "*****************************************************"
            self.locks[lock_name] = True
            return True

        else:
            # Otherwise, schedule a run (possibly overwriting the previous lock, so this only happens once):
            self.run_again[lock_name] = function
            print "*** Locked, setting run_again"
            print "*****************************************************"
            return False

    def removeLock(self, lock_name):

        print "*****************************************************"
        print "*** We have been called upon to remove a lock for %s" % lock_name

        # Unset the lock
        if self.locks.has_key(lock_name):
            del self.locks[lock_name]

        # Run the function again if we've been asked to
        if self.run_again.has_key(lock_name):
            fn = self.run_again[lock_name]
            del self.run_again[lock_name]
            print "*** Running the function again"
            print "*****************************************************"
            fn() # Recurse
        else:
            print "*** Not running the function again"
            print "*****************************************************"


class ExceptionLogger(log.FileLogObserver):
    def emit(self,eventDict):
        is_exception = eventDict.has_key('failure')
        
        connection_error = False
        if is_exception:
            # Some connection errors we don't care about
            connection_error = 'twisted.internet.error.ConnectionRefusedError' in repr(eventDict['failure']) or 'twisted.internet.error.ConnectionLost' in repr(eventDict['failure']) or 'twisted.spread.pb.PBConnectionLost' in repr(eventDict['failure'])

        other_loggable = 'CRITICAL' in repr(eventDict)

        if (is_exception and not connection_error) or other_loggable:
            log.FileLogObserver.emit(self,eventDict)


def all_in(phrases, list):
    """Used to check whether all of the phrases are somewhere in the list
    Useful for error checking when given a return value which may be something
    like:
    
    ['most recent snapshot of rpool/hcfs/mysql-hybridcluster does not\nmatch incremental snapshot',...]

    You can call all_in(['most recent snapshot of','does not','match incremental snapshot'], statuses)
    """

    combined = ''.join(list)

    for phrase in phrases:
        if phrase not in combined:
            return False
    
    return True

def sleep(secs, data=None):
    d = defer.Deferred()
    reactor.callLater(secs, d.callback, data)
    return d

def add_delay(d, secs):
    "Adds a callback to the specified deferred which delays the firing of the callback by the given number of seconds"
    def delay(data):
        print "Starting delay of %f seconds" % secs
        d = sleep(secs, data)
        return d
    d.addCallback(delay)
    return d

class TooManyAttempts(Exception):
    pass

class BackOffUtil(object):
    verbose = False

    def __init__(self, max_retries=10, scale=1.5, tag=None):
        self.attempt = 0
        self.max_retries = max(max_retries, 0)
        self.scale = scale
        self.tag = tag
        if self.verbose:
            print "Starting a %s" % tag

    def backoff(self, result):
        d = defer.Deferred()
        if self.attempt < self.max_retries:
            delay = self.scale ** self.attempt
            self.attempt += 1
            if self.verbose:
                if self.attempt < 2:
                    if self.tag is not None:
                        print ('[%s]' % (self.tag,))
                    print ('backing off by %.2fs..' % (delay,))
                else:
                    print ('%.2fs..' % (delay,))
            reactor.callLater(delay, d.callback, result)
        else:
            if self.verbose:
                if self.tag is not None:
                    print ('[%s]' % (self.tag,))
                print ('(backoff attempt %s excedes limit %s)' % (self.attempt+1, self.max_retries))
            d.errback(failure.Failure(TooManyAttempts('made %d attempts; failing' % (self.attempt,))))
        return d


def is_database(filesystem):
    if filesystem[:6]=='mysql-':
        return filesystem[6:]
    else:
        return False

def is_site(filesystem):
    if filesystem[:5]=='site-':
        return filesystem[5:]
    else:
        return False

def is_mail(filesystem):
    if filesystem[:5]=='mail-':
        return filesystem[5:]
    else:
        return False

def mysql_set(n, s="%s"):
    return "("+(",".join(["%s" for i in range(n)]))+")"

def format_datetime(x):
    return time.strftime('%Y-%m-%d %H:%M:%S',time.gmtime(float(x)))

def format_time(x):
    return time.strftime('%H:%M:%S',time.gmtime(float(x)))

def clearLogs(type):
    #print "Clearing out %s logs...." % type
    os.system("bash -c \"for X in /opt/HybridCluster/log/%s.log.*; do rm \\$X; done\"" % type) # delete all non-current logfiles

def email_error(subject, body):
    #import platform
    #from twisted.mail.smtp import sendmail
    #from email.mime.text import MIMEText

    #hostname = platform.node()

    #msg = MIMEText(time.ctime()+"\n"+body)
    #msg['Subject'] = 'Error from %s - %s' % (hostname, subject)
    #msg['From'] = "errors@%s" % hostname
    #msg['To'] = "bulk@lukemarsden.net"

    print "CRITICAL: "+body
    #sendmail('smtp.digital-crocus.com', msg['From'], msg['To'], msg.as_string())


class SelectableFile(abstract.FileDescriptor):
    def __init__(self, fname, protocol):
        abstract.FileDescriptor.__init__(self)
        self.fname = fname
        self.protocol = protocol
        self._openFile()

    def _openFile(self):
        self.fp = open(self.fname,'r+') # rob voodoo (opening it read/write stops it blocking - this makes 'sense' because you might want to write to the OS buffer)
        self.fileno = self.fp.fileno
        fdesc.setNonBlocking(self.fp)
        self.protocol.makeConnection(self)
    
    def doRead(self):
        buf = self.fp.read(4096)
        if buf:
            self.protocol.dataReceived(buf)
        else:
            print "File (%s) has closed under our feet, not trying to open it again..." % self.fname
            #reactor.callLater(1,self._openFile)
            #self._openFile()
            #self.protocol.connectionLost()

    def write(self, data):
        pass # what can we do with the data?

    def loseConnection(self):
        self.fp.close()


class BaseUITalker(pb.Root):
    def remote_setRemoteUIConnection(self,ui_connection):
        def callback(conn):
            self.ui_connections.remove(conn)
        ui_connection.notifyOnDisconnect(callback)
        self.ui_connections.append(ui_connection)

class ConnectionDispatcher:
    def __init__(s,context):
        s.context = context
    def callRemote(s, *args, **kw):
        d = DeferredDispatcher(s.context)
        for conn in s.context.ui_connections:
            d.deferreds.append(conn.callRemote(*args, **kw))
        return d

class DeferredDispatcher:
    def __init__(s, context):
        s.context = context
        s.deferreds = []
    def addCallback(s, *args, **kw):
        d = DeferredDispatcher(s.context)
        for deferred in s.deferreds:
            d.deferreds.append(deferred.addCallback(*args, **kw))
        return d
    def addErrback(s, *args, **kw):
        d = DeferredDispatcher(s.context)
        for deferred in s.deferreds:
            d.deferreds.append(deferred.addErrback(*args, **kw))
        return d

def mktup(item):
    # makes a singleton tuple out of item, if it isn't already a tuple
    if type(item)==tuple:
        return item
    else:
        return (item,)

def run_return(cmd):
    import popen2
    #print 'Running command '+cmd
    pipe = popen2.Popen4(cmd)
    ret = (pipe.fromchild.readlines(),pipe.poll())
    # close the pipes
    pipe.fromchild.close()
    pipe.tochild.close()
    return ret

def lookup_ip_mapping_in_config(my_ip):
    import platform
    config = read_config()
    node = platform.node()
    if '.' in node:
        node = node.split('.')[0]
    return config['ips'][node] # i.e. srv-qs3ur on BrightBox

def read_config():
    import yaml
    return yaml.load(open('/etc/cluster/config.yml','r').read())

def get_my_ip(get_local=False):
    my_ip = False
    for line in run_return("/sbin/ifconfig")[0]:
        m = re.match('^.*inet (addr:|)([0-9\.]+) .*(broadcast|Bcast).*$',line) # only check for interfaces which support UDP broadcast...
        if m is not None and m.group(2) != '127.0.0.1' and '172.16.23.' not in m.group(2): # ignore the loopback interface and vmware's NAT interface
            my_ip = m.group(2)
            break

    if my_ip:
        if my_ip.startswith('10.') and not get_local:
            # Assume we're on BrightBox or EC2
            try:
                my_ip = lookup_ip_mapping_in_config(my_ip)
            except (KeyError, IOError):
                print "We're on a 10. network but not actually a cluster node"
                pass
        #print "I reckon my IP is %s" % (my_ip)
        return my_ip
    else:
        #print "HybridUtils.get_my_ip FAILED"
        return '0.0.0.0'

import platform
if platform.win32_ver()[0] == '':
    ip = get_my_ip()
    local_ip = get_my_ip(get_local=True)

def ip_to_alpha(ip):
        alpha = map(lambda x: str(x), range(99))
#        alpha = ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']

        lastdigit = alpha[(int(re.search("[0-9]+\.[0-9]+\.[0-9]+\.([0-9]+)",ip).group(1))%100) % len(alpha)]
        return lastdigit


class curry:
    def __init__(self, fun, *args, **kwargs):
        self.fun = fun
        self.pending = args[:]
        self.kwargs = kwargs.copy()

    def __call__(self, *args, **kwargs):
        if kwargs and self.kwargs:
            kw = self.kwargs.copy()
            kw.update(kwargs)
        else:
            kw = kwargs or self.kwargs

        return self.fun(*(self.pending + args), **kw)

class CallbackProcessProtocol(protocol.ProcessProtocol):
    collector = ''
    def __init__(self, viewer=None):
        self.viewer = viewer

    def outReceived(self,data):
        if self.viewer:
            self.viewer.outReceived(data)
        self.collector += data

    def errReceived(self,data):
        if self.viewer:
            self.viewer.errReceived(data)
        self.collector += data

    def processEnded(self,status):
        if self.viewer:
            self.viewer.processEnded(status)
        self.callback(status,self.collector)

class AlreadyQueuedError(Exception):
    pass

class SlotManager:
    """
    A slot manager handles running a queue of tasks, ensuring that only n of them run simultaneously.
    This ensures that, as well as the server not getting overloaded, we never run out of FDs.

    Each task is a list of commands which get executed sequentially by AsyncExecCmds.
    Each task can be tagged with a tag which is either None - in which case there is no mutual exclusion,
    or a string, in which case no two tasks with the same tag will ever run simultaneously. This
    is useful as a way of locking around a resource, such as a filesystem.

    When a task is queued, its commands are compared to those of the existing tasks in the
    queue. If an identical command is already in the queue, then an AlreadyQueuedException is raised,
    since the same command is due to be run as soon as possible anyway. This helps avoid commands
    unnecessarily building up in the queue.

    Sample code:
    sm = SlotManager(n_slots=4);

    ... lots of other tasks added to the slotmanager...

    sm.queueTask(['cd /var/www','tar cfv backup.tar .','scp backup.tar server...'],
                callback=lambda x: sys.stdout.write('done backup'),
                description="Backup website",
                tag='backup')

    Now this backup will only run when all other tasks tagged with 'backup' are completed *and* there
    is a free slot.

    TODO: Add a timeout argument for each task.

    Internally -
    self.slots contain instances of AsyncExecCmds() or None
    self.queue contain dictionaries of the arguments passed to queueTask
    """
    def __init__(self,n_slots=4,ui=None,target='tasks',timeout=None):
        self.n_slots = n_slots

        self.queue = []
        self.slots = {}

        self.ui = ui
        self.target = target
        self.timeout = timeout

#        self.id_counter = 0

        for x in range(n_slots):
            self.slots[x]=None

    def checkQueue(self):
        #print 'checkQueue called'
        if not None in self.slots.values():
            # No available slots right now, try again later"
            return

        #print 'Got here, queue looks like: '+str(self.queue)

        # XXX: This algorithm is terribly inefficient for long queues.

        negative_new_queue = [] # contains things we've taken out of the queue this time

        for task in self.queue: # run the oldest command first
            running_tags = [t.tag for t in filter(lambda x: x is not None, self.slots.values())] # avoid KeyError
            if task['tag'] is None or task['tag'] not in running_tags:
                # Find the first open slot
                for n,slot in self.slots.items():
                    if slot is None:
                        #print "We're good to go, this tag isn't currently running and there's a free slot"
                        # Spawning task "+task['description']+" in slot "+str(n)
                        self.startTask(task,n)
                        negative_new_queue.append(task)
                        break # don't continue the for loop
            else:
                print "This tag (" + task['tag'] + ") is currently running, so not started"

        self.queue = [x for x in self.queue if x not in negative_new_queue]
        
        """old_queue = self.queue

        self.queue = []
        for x in old_queue:
            if x not in negative_new_queue:
                self.queue.append(x)"""
    
        def callback():
            pass

    def startTask(self,task,n):
        """Starts task described by dictionary task in slot n, which is assumed to be None at time of calling"""
        task_callback = task['callback']
        print "Running task %s" % (task['description'])

        def custom_callback(statuses,outputs=[],parameters={}):
            # Set the slot to empty, then run the task's callback
            # Got callback on "+task['description']+" of "+str(statuses)
            #print "Updating cell for task "+str(task['id'])+" with "+str(statuses)
            if self.ui is not None:
                try:
                    self.ui.callRemote('updateCell',item=(task['id'],ip,task['description']),column=3,type=self.target,value="Finished: "+str(statuses),outputs=outputs)
                except Exception,e:
                    print "Carrying on after exception in updateCell: "+str(e)
            
            if task_callback is not None:
                args_for_callback = {}

                # Introspection: Nasty or nice? I can't decide
                if 'parameters' in inspect.getargspec(task_callback).args:
                    args_for_callback['parameters'] = parameters
                if 'outputs' in inspect.getargspec(task_callback).args:
                    args_for_callback['outputs'] = outputs
                if 'cmds' in inspect.getargspec(task_callback).args:
                    args_for_callback['cmds'] = task['cmds']

                task_callback(statuses, **args_for_callback)

            self.slots[n]=None
            # check if there's anything we want to run now that we've freed up a slot
            try:
                self.checkQueue()
            except Exception,e:
                print "CRITICAL: Exception caught when running checkQueue "+str(e)

        # Starting task "+task['description']

        p = {"now":str(time.time())}

        if self.ui is not None:
            try:
                self.ui.callRemote('updateCell',item=(task['id'],ip,task['description']),column=3,type='tasks',value="Running in slot "+str(n))
            except Exception,e:
                print "Carrying on after exception in updateCell: "+str(e)

        # apply the parameter transformation to elements which aren't functions (if they're functions, they get called in a thread)
        for i,cmd in enumerate(task['cmds']):
            if type(cmd) == str or type(cmd) == unicode:
                task['cmds'][i] = task['cmds'][i] % p

        print "!" * 80
        pprint.pprint(task)
        print "!" * 80

        self.slots[n]=AsyncExecCmds(
                task['cmds'],
                callback=curry(custom_callback, parameters=p),
                verbose=task['cmds'], # XXX !?
                ui=self.ui,
                description=task['description'],
                tag=task['tag'],
                id=task['id'])

    # XXX UI argument (below) is deprecated and not used, retained for compatibility
    def queueTask(self,cmds,callback=None,verbose=0,ui=None,description='<no description>',tag=None,id=None,skip_uniqueness_check=False, errback=None): # TODO: Make this return a deferred, obviously

        if not skip_uniqueness_check:
            for task in self.queue:
                if task['cmds']==cmds:
                    print "Error - this task already queued: "+str(cmds)

                    if errback is not None:
                        errback()
                    return False

            # The following seems to cause trouble
            """for slot in self.slots.values():
                if slot is not None:
                    if slot.cmds == cmds:
                        print "CRITICAL Error - this task CURRENTLY RUNNING: "+str(cmds)
                    
                        if errback is not None:
                            errback()
                        return False"""


#                    raise AlreadyQueuedError

        # append this task to the queue

        id = int(long(time.time()*1000) % 999999999)
        self.queue.append({'cmds':cmds,'callback':callback,'verbose':verbose,'description':description,'tag':tag,'id':id})
#        self.id_counter += 1

        # since commands are always unique, we can identify the command in the UI by the descr & cmdlist
        # XXX if skip_uniqueness_check == True the above assumption is false

        # Add the task to the UI
        if self.ui is not None:
            def callback(*args):
                self.ui.callRemote('updateCell',item=(id,ip,description),column=3,type='tasks',value="Queued")

            try:
                self.ui.callRemote('addTask',{(id,ip,description): map(lambda cmd: (id,'',cmd),cmds)}).addCallback(callback)

            except Exception, e:
                print "Caught "+str(e)+" when updating UI but carrying on regardless"

        self.checkQueue()

class AsyncExecCmds: # for when you want to run things one after another

    def __init__(self,cmds,callback=None,verbose=0,ui=None,description='<no description>',tag=None,id=None,auto_run=True,cmd_prefix=None,viewer=None):
        "Asynchronously run a list of commands, return a list of status codes"
        self.cmds = cmds
        self.callback = callback
        self.statuses = []
        self.outputs = []
        self.verbose = verbose
        self.ui = ui
        self.description = description
        self.tag = tag
        self.id = id
        self.cmd_prefix = cmd_prefix
        self.viewer = viewer

        if auto_run:
            self.runNextCmd()

    def getDeferred(self):
        "Return a deferred which fires when the callback would have been called."
        d = defer.Deferred()
        def callback(statuses,outputs):
            try:
                d.callback((statuses,outputs))
            except failure.NoCurrentExceptionError, e:
                print "*"*80
                print "How odd, failure.NoCurrentExceptionError when I was trying to callback with:"
                print statuses, outputs
                print "*"*80
                print e
                print "*"*80
                
        self.callback = callback
        return d

    def deferredOutputLines(self):
        """Utility function so you can just do:

        outputs = yield AsyncExecCmds(['some cmd']).deferredOutputLines()
        for line in outputs[0]: # output of the first command
            # do something with this line
        """
        d = defer.Deferred()
        def callback(statuses,outputs):
            d.callback([x.strip().split('\n') for x in outputs])
        self.callback = callback
        return d


    def runNextCmd(self):
        "Pops the first command in the current list, then runs it, recursing in the callback"
        #print self.cmds
        if self.cmds == []: # we're done, return the list of statuses
            if self.viewer:
                self.viewer.lastProcessEnded() # Allow the viewer to do cleanup (like closing file handles)

            def to_string(status):
                if type(status) in [int,str,unicode,bool]:
                    return status
                if "twisted.internet.error.ProcessDone" in repr(status):
                    return "Done"
                if "twisted.internet.error.ProcessTerminated" in repr(status):
                    return "Failed"
                return repr(status)
            if self.callback is not None:
                self.callback(map(to_string,self.statuses),self.outputs)
            return

        cmd = self.cmds.pop(0)

        if self.viewer:
            self.viewer.startCmd(cmd)

        cpp = CallbackProcessProtocol(self.viewer)

        def cmd_callback(status,output):
            self.statuses.append(status)
            self.outputs.append(output)
            self.runNextCmd()

        cpp.callback = cmd_callback

        if type(cmd) in [str,unicode]: # it's a system call
            # run everything through bash so that fun things like pipes work
            if cmd[0:16] in ['/usr/bin/ssh']:
                prefix = ''
            else:
                prefix = '/usr/local/bin/sudo '

            # override this logic for times when the app wants to choose whether to sudo or not
            if self.cmd_prefix is not None:
                prefix = self.cmd_prefix

            if self.verbose>=0:
                print "running "+prefix+cmd
            reactor.callLater(0,reactor.spawnProcess,cpp,'/bin/bash',['/bin/sh', '-c',(prefix+cmd).encode('ascii','ignore')])

        else: # assume it's a function, find out whether it's advertised itself as returning a deferred (assume it isn't)

            def generic_callback(x='Finished'):
                cmd_callback(x)

            returns_deferred = False

            if hasattr(cmd,'returns_deferred'):
                returns_deferred = cmd.returns_deferred

            if returns_deferred:
                # execute it directly (i.e. database queries etc)
                d = cmd()
            else:
                # pop it in a thread
                d = threads.deferToThread(cmd)

            d.addCallback(generic_callback)

    def run(self):
        self.runNextCmd()


class AsyncExecCmd(AsyncExecCmds):
    def __init__(self,cmd,callback=None,verbose=0,ui=None,description='<no description>'):
        AsyncExecCmds.__init__(self,[cmd],callback,verbose,ui,description)

"""
        self.verbose = verbose
        if self.verbose:
            print cmd,' '.join(args)
        cpp = CallbackProcessProtocol()
        cpp.callback=callback
        reactor.spawnProcess(cpp,cmd,args)"""

def ntp():
    import struct, telnetlib, time, socket

    EPOCH = 2208988800L

    try:
        fromNTP = telnetlib.Telnet('time.nrc.ca', 37).read_all()
        #the string's a big endian uInt
        remoteTime = struct.unpack('!I', fromNTP )[0] - EPOCH

        # NTP time converted to time struct & made friendly
        return time.gmtime(remoteTime)
    
    except socket.gaierror:
        print "WARNING: NTP server unavailable"
        return False

def nice_time(t):
    """ turns a unix timestamp into human-readable AND unix timestamp """
    return time.ctime(t)+" "+str(t)

def shellquote(s):
        return "'" + s.replace("'", "'\\''") + "'"

@defer.inlineCallbacks
def safe_write(file, contents, perms=None): # FIXME: this is not really a "safe" write any more (the move and permissions fix cannot be done atomically), but as long as we wait until it's finished before reloading the program, we'll be okay
    tmpname = '/tmp/'+file.replace('/','%')+".tmp"
    fp = open(tmpname, "w")
    fp.write(contents)
    fp.close()
    yield AsyncExecCmds(["/bin/mv %s %s" % (shellquote(tmpname), shellquote(file))]).getDeferred()
    if perms is not None:
        yield AsyncExecCmds(["/bin/chmod %s %s" % (perms, shellquote(file))]).getDeferred()

def hex2ip(sender):
    _,hex,priv = sender.split('#')
    quads = [hex[0:2],hex[2:4],hex[4:6],hex[6:8]]
    ip = '.'.join(map(lambda x: str(int(x,16)),quads))
    return ip

#def test_callback(data):
#    print data
#    print map(lambda x: x, data)

#AsyncExecCmds(['/bin/false','/bin/true','/bin/false'],test_callback)
#AsyncExecCmd('/bin/false',['/bin/false'],test_callback)
#reactor.run()
#raise SystemExit

def natsort(list_):
    try:
        # decorate
        tmp = [ (int(re.search('\d+', i).group(0)), i) for i in list_ ]
        tmp.sort()
        # undecorate
        return [ i[1] for i in tmp ]
    except AttributeError:
        list_.sort()
        return list_

def setproctitle(name):
    try:
        from ctypes import cdll, byref, create_string_buffer
        libc = cdll.LoadLibrary('libc.so.7')
        libc.setproctitle(name+'\0')
    except:
        print "Unable to set process name, not on FreeBSD?"

def parse_zfs_list(data,zpool):
    zfs_data = {}
    for line in data.split('\n'):
        match = re.match(zpool+'/hcfs/([^/@]+)@?([0-9\.]*)',line.strip())
        if match is not None:
            site,snapshot = match.groups()
            if site not in zfs_data.keys():
                zfs_data[site] = []
            if snapshot != '':
                zfs_data[site].append(snapshot)
    return zfs_data

def remote_prefix(username,ip_to,sudo='sudo'):
    return '/usr/bin/env ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no '+username+'@'+ip_to+' -i /home/hybrid/.ssh/id_rsa '+sudo+' ' # NB should we remove the id_rsa bit? I think it's a solarisism


class Spinner:
    def __init__(self, type=0):
        if type == 0:
            self.char = ['.', 'o', 'O', 'o']
        else:
            self.char = ['|', '/', '-', '\\', '-']
        self.len  = len(self.char)
        self.curr = 0

    def Get(self):
        self.curr = (self.curr + 1) % self.len
        str = self.char[self.curr]
        return str

    def Print(self):
        self.curr = (self.curr + 1) % self.len
        str = self.char[self.curr]
        sys.stdout.write("\b \b%s" % str)
        sys.stdout.flush()

    def Done(self):
        sys.stdout.write("\b \b")
        sys.stdout.flush()

########NEW FILE########
__FILENAME__ = test
from txmysql.protocol import MySQLProtocol
from twisted.internet import defer
from twisted.application.internet import UNIXClient
from twisted.internet.protocol import ClientFactory
from twisted.internet import reactor
from twisted.application.service import Application
from twisted.protocols import policies
import pprint
import secrets

class MySQLClientFactory(ClientFactory):
    protocol = MySQLProtocol

    def __init__(self, username, password, database=None):
        self.username = username
        self.password = password
        self.database = database

    def buildProtocol(self, addr):
        p = self.protocol(self.username, self.password, self.database)
        p.factory = self
        return p

factory = MySQLClientFactory(username='root', password=secrets.MYSQL_ROOT_PASS, database='mysql')

class TestProtocol(MySQLProtocol):
    def __init__(self, *args, **kw):
        MySQLProtocol.__init__(self, *args, **kw)

    def connectionMade(self):
        MySQLProtocol.connectionMade(self)
        self.do_test()

    def connectionLost(self, reason):
        print reason
    def connectionFailed(self, reason):
        print reason

    @defer.inlineCallbacks
    def do_test(self):
        yield self.ready_deferred
        yield self.select_db('foo')
        result = yield self.query('insert into bar set thing="yeah"')
        result = yield self.fetchall('select * from bar')
        print result

factory.protocol = TestProtocol
#factory = policies.SpewingFactory(factory)
reactor.connectTCP('127.0.0.1', 3306, factory)

application = Application("Telnet Echo Server")


########NEW FILE########
__FILENAME__ = test_connectionpool
import sys

from twisted.internet import reactor
from twisted.python import log

from txmysql import client
from secrets import *

import functools

log.startLogging(sys.stdout)

class ConnectionPoolTest:
    def __init__(self):
        # Create a connection pool with one connection only. When
        # another connection is requested from the pool, a
        # DeferredConnection is created. The latter is executed when a
        # Connection becomes available.
        self._pool = client.ConnectionPool(MYSQL_HOST, MYSQL_USER,MYSQL_PASS,
                                           database='test', num_connections=1,
                                           idle_timeout=120,
                                           connect_timeout=30)
    def doInsertRow(self, deferred, data, ignored):
        print "run insert deferred=%s ignored=%s" % (deferred, ignored)
        self._pool.runOperation("insert into example set data='%s'" % data)

    def doSelect(self, deferred, ignored):
        print "doing select deferred=%s ignored=%s" % (deferred, ignored)
        return self._pool.runQuery("select * from example")

    def selectTakeResults(self, deferred, data):
        print "selectTakeResults deferred=%s, data=%s" % (deferred, repr(data))

    def handleFailure(self, reason):
        # reason can be a MySQLError with message, errno, sqlstate, query
        print reason

    def stop(self, ignored):
        reactor.stop()

    def whenRunning(self):
        d = self._pool.selectDb("test")
        d.addCallback(functools.partial(self.doInsertRow, d, 'first'))
        d.addCallback(functools.partial(self.doSelect, d))
        d.addCallback(functools.partial(self.selectTakeResults, d))
        d.addErrback(self.handleFailure)

    def whenRunning2(self):
        d2 = self._pool.selectDb("test")
        d2.addCallback(functools.partial(self.doInsertRow, d2, 'second'))
        d2.addCallback(functools.partial(self.doSelect, d2))
        d2.addCallback(functools.partial(self.selectTakeResults, d2))
        d2.addCallback(self.stop)
        d2.addErrback(self.handleFailure)

if __name__ == "__main__":
    t = ConnectionPoolTest()
    reactor.callWhenRunning(t.whenRunning)
    reactor.callWhenRunning(t.whenRunning2)
    reactor.run()

########NEW FILE########
__FILENAME__ = test_timeout
from txmysql.client import MySQLConnection, error
from twisted.internet import reactor, defer
import secrets
from twisted.application.service import Application
import time
import random
import shutil
import pprint
from HybridUtils import AsyncExecCmds, sleep
from twisted.python import log

defer.setDebugging(True)
"""

Simulate the worst possible scenario for connectivity to a MySQL server

The server randomly disappears and re-appears, and is sometimes replaced by
an imposter who accepts packets but never responds.

This is sorta like being on a train between Bristol and London on O2's 3G
network.

"""

conn = MySQLConnection('127.0.0.1', 'root', secrets.MYSQL_ROOT_PASS, 'foo',
        connect_timeout=5, query_timeout=5, idle_timeout=10, retry_on_error=True)

@defer.inlineCallbacks
def fuck_with_mysql_server():
    print "Stopping MySQL"
    yield AsyncExecCmds(['pkill -9 mysqld; sudo stop mysql'], cmd_prefix='sudo ').getDeferred()
    # The pkill -9 mysqld causes "Lost connection to MySQL server during query"
    # or "MySQL server has gone away" if you try to query on a connection which has died
    while 1:
        if random.choice([0,1]) == 0:
            # Only sometimes will the MySQL server be up for long enough to
            # successfully return a SELECT
            print "Starting MySQL"
            yield AsyncExecCmds(['start mysql'], cmd_prefix='sudo ').getDeferred()
            wait = random.randrange(30, 31)
            yield sleep(wait)
            print "Stopping MySQL"
            yield AsyncExecCmds(['pkill -9 mysqld; sudo stop mysql'], cmd_prefix='sudo ').getDeferred()
            wait = random.randrange(1, 5)
            yield sleep(wait)
        else:
            # And sometimes MySQL will be replaced with an evil daemon
            # which accepts TCP connections for 10-20 seconds but stays silent
            # This causes the official MySQL client to say:
            # Lost connection to MySQL server at 'reading initial communication packet', system error: 0
            # ... when the connection finally dies (i.e. when evildaemon.py stops)
            print "Starting evil daemon"
            yield AsyncExecCmds(['stop mysql; sudo python test/evildaemon.py'], cmd_prefix='sudo ').getDeferred()
            print "Evil daemon stopped"
            wait = random.randrange(1, 5)
            yield sleep(wait)

@defer.inlineCallbacks
def render_status():
    while 1:
        fp = open("status.tmp", "w")
        yield sleep(0.1)
        fp.write("Operations:\n\n")
        fp.write(pprint.pformat(conn._pending_operations) + "\n\n")
        fp.write("Current operation;\n\n")
        fp.write(pprint.pformat(conn._current_operation) + "\n\n")
        fp.write("Current operation deferred:\n\n")
        fp.write(pprint.pformat(conn._current_operation_dfr) + "\n\n")
        fp.write("Current user deferred:\n\n")
        fp.write(pprint.pformat(conn._current_user_dfr) + "\n\n")
        fp.close()
        shutil.move("status.tmp", "status.txt")

@defer.inlineCallbacks
def main():
    fuck_with_mysql_server()
    render_status()
    while 1:
        # pick a random value which may or may not trigger query timeout
        # remember, the mysql server only stays up for a short while
        wait = random.randrange(3, 7)
        print "About to yield on select sleep(%i)" % wait
        try:
            d1 = conn.runQuery("select sleep(%i)" % wait)
            d2 = conn.runQuery("select sleep(%i)" % (wait + 1))
            d3 = conn.runQuery("select sleep(%i)" % (wait + 2))
            print "============================================================="
            print "I have been promised a result on %s" % str([d1,d2,d3])
            print "============================================================="
            d = defer.DeferredList([d1, d2, d3])
            result = yield d
            print "============================================================="
            print "THIS RESULT IS SACRED AND SHOULD ALWAYS BE RETURNED CORRECTLY %s" % str(d)
            print result
            print "============================================================="
            print "about to go under..."
            yield sleep(random.randrange(3, 7))
        except Exception, e:
            print "AAAAAAAAAAAAAARGH I GOT A FAILURE AS AN EXCEPTION"
            print e
            print "AAAAAAAAAAAAAARGH I GOT A FAILURE AS AN EXCEPTION, sleeping..."
            yield sleep(1)

reactor.callLater(0, main)

application = Application("Evil MySQL reconnection tester")



########NEW FILE########
__FILENAME__ = client
from twisted.internet.protocol import ReconnectingClientFactory
from twisted.internet import reactor, defer
from protocol import MySQLProtocol # One instance of this per actual connection to MySQL
from txmysql import error
from twisted.python.failure import Failure
from twisted.python import log
import pprint

DEBUG = False

def _escape(query, args=None, text_factory=str): # XXX: Add Rob's suggestion for escaping
    # TODO: Turn %% into % so that you can do a real %s
    if args is None:
        return query
    escaped_args = []
    for arg in args:
        escaped_args.append("null" if arg is None else "'%s'" % text_factory(arg).replace("\\","\\\\").replace("'", "\\'"))
    parts = ("[%s]" % str(query)).split('%s') # Add square brackets to
                                              # guarantee that %s on the end or
                                              # beginning get a corresponding
                                              # split
    if len(escaped_args) + 1 != len(parts):
        raise TypeError, 'not enough arguments for MySQL format string %s | %s' % (str(query), str(args))
    # Pad args so that there are an equal number of args and query
    escaped_args.insert(0, '')
    if len(parts) != len(escaped_args):
        raise TypeError, 'INTERNAL ERROR'
    # Now interpolate and remove the square brackets
    return (''.join(x + y for x, y in zip(escaped_args, parts)))[1:-1]

class MySQLConnection(ReconnectingClientFactory):
    """
    Takes the responsibility for the reactor.connectTCP call away from the user.

    Lazily connects to MySQL only when a query is run and stays connected only
    for up to idle_timeout seconds.

    Handles reconnecting on disconnection if there are queries which have not
    yet had results delivered.

    When excuting a query, waits until query_timeout expires before giving up
    and reconnecting (assuming this MySQL connection has "gone dead"). If
    retry_on_error == True, attempts the query again once reconnected.  If not,
    returns a Failure to the user's deferred.

    Also accepts a list of error strings from MySQL which should be considered
    temporary local failures, which should trigger a reconnect-and-retry rather
    than throwing the failure up to the user. These may be application-specific.

    Note that this and MySQLProtocol both serialise database access, so if you
    try to execute multiple queries in parallel, you will have to wait for one
    to finish before the next one starts. A ConnectionPool inspired by
    http://hg.rpath.com/rmake/file/0f76170d71b7/rmake/lib/dbpool.py is coming
    soon to solve this problem (thanks gxti).
    """

    protocol = MySQLProtocol

    def disconnect(self):
        """
        Close the connection and kill all the reconnection attempts
        """
        self.stopTrying()
        self.stateTransition(state='disconnecting')
        if self.client:
            # Do some clean-up
            self.client.setTimeout(None)
            self.client.transport.loseConnection()

    def __init__(self, hostname, username, password, database=None,
                 connect_timeout=None, query_timeout=None, idle_timeout=None,
                 retry_on_error=False, temporary_error_strings=[], port=3306,
                 pool=None, autoRepair=False, text_factory=str):

        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.connect_timeout = connect_timeout
        self.query_timeout = query_timeout
        self.idle_timeout = idle_timeout
        self.retry_on_error = retry_on_error
        self.temporary_error_strings = temporary_error_strings
        self.deferred = defer.Deferred() # This gets fired when we have a new
                                         # client which just got connected
        self._current_selected_db = None
        self._autoRepair = autoRepair

        self.state = 'disconnected'
        self.client = None # Will become an instance of MySQLProtocol
                           # precisely when we have a live connection

        self.pool = pool

        # Attributes relating to the queue
        self._pending_operations = []
        self._current_operation = None
        self._current_operation_dfr = None
        self._current_user_dfr = None

        # Set when we get disconnected, so that we know to attempt
        # a retry of a failed operation
        self._error_condition = False
        self.text_factory=text_factory

    def _handleIncomingRequest(self, name, fn, arg0, arg1):
        """
        A handler for all new requests, gets parameterised by
        runQuery, selectDb and runOperation
        """
        # We have some new work to do, in case we get disconnected, we want to try
        # reconnecting again now.
        self.continueTrying = 1
        user_dfr = defer.Deferred()
        self._pending_operations.append((user_dfr, fn, arg0, arg1))
        self._checkOperations()
        if DEBUG:
            print "Appending %s \"%s\" with args %s which is due to fire back on new user deferred %s" % (name, arg0, arg1, user_dfr)
        return user_dfr

    def runQuery(self, query, query_args=None):
        return self._handleIncomingRequest('query', self._doQuery, query, query_args)

    def fetchone(self, query, query_args=None):
        # XXX DANGER WILL ROBINSON! DANGER!
        # This method does not conform to PEP-249. It returns a single scalar
        # value of the first result in the first row, or None. PEP-249 expects
        # this method to return an entire row or None.
        d = self.runQuery(query, query_args)
        d.addCallback(self._fetchoneHandleResult)
        return d

    def _fetchoneHandleResult(self, result):
        if result == []:
            result = None
        if result:
            result = result[0][0]
        return result

    def runOperation(self, query, query_args=None):
        return self._handleIncomingRequest('operation', self._doOperation, query, query_args)

    def selectDb(self, db):
        self.database = db
        return self._handleIncomingRequest('selectDb', self._doSelectDb, db, None)

    def _executeCurrentOperation(self):
        # Actually execute it, operation_dfr will fire when the database returns
        user_dfr, func, query, query_args = self._current_operation

        if DEBUG:
            print "Setting current operation to %s" % str(self._current_operation)
            print "About to run %s(%s, %s) and fire back on %s" % (str(func), str(query), str(query_args), str(user_dfr))

        self._current_user_dfr = user_dfr
        operation_dfr = func(query, query_args)
        # Store a reference to the current operation (there's gonna be only one running at a time)
        self._current_operation_dfr = operation_dfr

        operation_dfr.addBoth(self._doneQuery)

        # Jump back into the game when that operation completes (done_query_error returns none
        # so the callback, not errback gets called)
        operation_dfr.addBoth(self._checkOperations)

    def _retryOperation(self):
        if DEBUG:
            print "Running retryOperation on current operation %s" % str(self._current_operation)
        if not self._current_operation:
            # Oh, we weren't doing anything
            return
        self._executeCurrentOperation()

    @defer.inlineCallbacks
    def _doneQuery(self, data):
        # The query deferred has fired
        if self._current_user_dfr:
            if isinstance(data, Failure):
                if data.check(error.MySQLError):
                    if data.value.args[0] in self.temporary_error_strings:
                        print "CRITICAL: Caught '%s', reconnecting and retrying" % (data.value.args[0])
                        self.client.transport.loseConnection()
                        return
                    """
                    Incorrect key file for table './autorepair/mailaliases.MYI'; try to repair it", 126, 'HY000'
                    Table './hybridcluster/filesystem_modification_counts' is marked as crashed and last (automatic?) repair failed", 144, 'HY000'
                    """
                    error_string = data.value.args[0]
                    keyCorruptionPrefix = 'Incorrect key file for table \'./'
                    start = None
                    if error_string.startswith(keyCorruptionPrefix) and self._autoRepair:
                        start = len(keyCorruptionPrefix)
                    elif "is marked as crashed and last (automatic?) repair failed" in error_string and self._autoRepair:
                        start = len("Table \'./")
                    if start:
                        dbfile = error_string[start:error_string.find("'", start)]
                        table = dbfile.rsplit('/', 1)[1].rsplit('.', 1)[0]
                        repair = "repair table " + table
                        log.msg(
                            channel="autorepair",
                            msgs=[error_string, "\n\tabout to repair", repr(repair)])
                        result = yield self.client.query(repair)
                        log.msg(
                            channel="autorepair",
                            msgs=["repair completed", repr(result)])
                        self._executeCurrentOperation()
                        return

                    if data.value.args[0] in self.temporary_error_strings:
                        print "CRITICAL: Caught '%s', reconnecting and retrying" % (data.value.args[0])
                        self.client.transport.loseConnection()
                        return
                if DEBUG:
                    print "Query failed with error %s, errback firing back on %s" % (data, self._current_user_dfr)
                # XXX: If this an errback due to MySQL closing the connection,
                # and we are retry_on_true, and so we have set
                # _error_condition,  shouldn't we mask the failure?
                self._current_user_dfr.errback(data)
            else:
                if DEBUG:
                    print "Query is done with result %s, firing back on %s" % (data, self._current_user_dfr)
                self._current_user_dfr.callback(data)
                if self.pool:
                    self.pool._doneQuery(self)
            self._current_user_dfr = None
        else:
            print "CRITICAL WARNING! Current user deferred was None when a query fired back with %s - there should always be a user deferred to fire the response to..." % data
            raise Exception("txMySQL internal inconsistency")
        self._error_condition = False
        self._current_operation = None
        self._current_operation_dfr = None
        # If that was a failure, the buck stops here, returning None instead of the failure stops it propogating

    def _checkOperations(self, _ign=None):
        """
        Takes one thing off the queue and runs it, if we can.  (i.e. if there
        is anything to run, and we're not waiting on a query to fire back to
        the user right now, i.e. current user deferred exists)
        """
        if DEBUG:
            print "Running checkOperations on the current queue of length %s while current operation is %s" % (str(len(self._pending_operations)), str(self._current_operation))
        #print "Got to _checkOperations"

        if self._pending_operations and not self._current_user_dfr:
            # Store its parameters in case we need to run it again
            self._current_operation = self._pending_operations.pop(0)
            self._executeCurrentOperation()

        return _ign

    def stateTransition(self, data=None, state='disconnected', reason=None):
        new_state = state
        old_state = self.state

        if new_state == old_state:
            # Not a transition, heh
            return

        if DEBUG:
            print "Transition from %s to %s" % (self.state, new_state)

        self.state = new_state

        # connected => not connected
        if old_state == 'connected' and new_state != 'connected':
            if DEBUG:
                print "We are disconnecting..."
            # We have just lost a connection, if we're in the middle of
            # something, send an errback, unless we're going to retry
            # on reconnect, in which case do nothing
            if not self.retry_on_error and self._current_operation:
                if DEBUG:
                    print "Not retrying on error, current user deferred %s about to get failure %s" % (self._current_user_dfr, reason)
                if self._current_user_dfr and not self._current_user_dfr.called:
                    if DEBUG:
                        print "Current user deferred exists and has not been called yet, running errback on deferred %s about to get failure %s" % (self._current_user_dfr, reason)
                    self._current_user_dfr.errback(reason)
                    self._current_user_dfr = None
                    self._current_operation = None
                    self._current_operation_dfr = None
                else:
                    if DEBUG:
                        print "Current user deferred has already been fired in error handler, not doing anything"

        # not connected => connected
        if old_state != 'connected' and new_state == 'connected':
            if DEBUG:
                print "We are connected..."
            # We have just made a new connection, if we were in the middle of
            # something when we got disconnected and we want to retry it, retry
            # it now
            if self._current_operation and self._error_condition:
                if self.retry_on_error:
                    print "Would have run retry here... %r" % (reason,)
                    if DEBUG:
                        print "Retrying on error %s, with current operation %s" % (str(reason), str(self._current_operation))
                    # Retry the current operation
                    if not (self.state == 'connecting' and self._error_condition and self.retry_on_error):
                        if DEBUG:
                            print "Not running the query now, because the reconnection handler will handle it"
                        self._retryOperation()

                else:
                    if DEBUG:
                        print "Not retrying on error, connection made, nothing to do."

            else:
                # We may have something in our queue which was waiting until we became connected
                if DEBUG:
                    print "Connected, check whether we have any operations to perform"
                self._checkOperations()

        return data

    def _handleConnectionError(self, reason, is_failed):
        # This may have been caused by TimeoutMixing disconnecting us.
        # TODO: If there's no current operation and no pending operations, don't both reconnecting
        # Use: self.stopTrying() and self.startTrying()?
        if DEBUG:
            print "Discarding client", self.client
        self.client = None
        if self._pending_operations or self._current_operation:
            if not is_failed:
                # On connectionFailed, rather than connectionLost, we will never have
                # started trying to execute the query yet, because we didn't get a connection
                # So only set _error_condition if it was a connectionLost, because it results
                # in behaviour which expects a current_operation
                self._error_condition = True
            if self.state != 'disconnecting':
                self.stateTransition(state='connecting', reason=reason)
        else:
            self.continueTrying = 0
            self.stateTransition(state='disconnected')

    def clientConnectionFailed(self, connector, reason):
        if DEBUG:
            print "Got clientConnectionFailed for reason %s" % str(reason)
        self._handleConnectionError(reason, is_failed=True)
        ReconnectingClientFactory.clientConnectionFailed(self, connector, reason)

    def clientConnectionLost(self, connector, reason):
        if DEBUG:
            print "Got clientConnectionLost for reason %s" % str(reason)
        self._handleConnectionError(reason, is_failed=False)
        ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

    @defer.inlineCallbacks
    def _begin(self):
        if self.state == 'disconnected':
            if DEBUG:
                print "Connecting after being disconnected, with connection timeout %s" % self.connect_timeout
            self.stateTransition(state='connecting')
            # TODO: Use UNIX socket if string is "localhost"
            reactor.connectTCP(self.hostname, self.port, self, timeout=self.connect_timeout)
            if DEBUG:
                print "(1) Yielding on a successful connection, deferred is %s" % self.deferred
            yield self.deferred # will set self.client
            if DEBUG:
                print "Yielding on a successful ready deferred which is", self.client.ready_deferred
            yield self.client.ready_deferred
        elif self.state == 'connecting':
            if DEBUG:
                print "(2) Yielding on a successful connection, deferred is %s" % self.deferred
            yield self.deferred
            if DEBUG:
                print "Yielding on a successful ready deferred"
            yield self.client.ready_deferred
        elif self.state == 'connected':
            if DEBUG:
                print "Already connected when a query was attempted, well that was easy"
            pass

    def buildProtocol(self, addr):
        if DEBUG:
            print "Building a new MySQLProtocol instance for connection to %s, attempting to connect, using idle timeout %s" % (addr, self.idle_timeout)
        #print "Running buildprotocol for %s" % addr
        p = self.protocol(self.username, self.password, self.database,
                idle_timeout=self.idle_timeout)
        p.factory = self
        self.client = p
        if DEBUG:
            print "New client is", self.client
        #print self.client.ready_deferred
        self.deferred.callback(self.client)
        self.deferred = defer.Deferred()
        def when_connected(data):
            if DEBUG:
                print "Connection just successfully made, and MySQL handshake/auth completed. About to transition to connected... (got data)", data
            self.stateTransition(state='connected')
            return data
        self.client.ready_deferred.addCallback(when_connected)
        def checkError(failure):
            if failure.check(error.MySQLError):
                if failure.value.args[0] in self.temporary_error_strings:
                    print "CRITICAL: Caught '%s', reconnecting and retrying" % (failure.value.args[0])
                    self.client.transport.loseConnection()
                    return # Terminate errback chain
            return failure
        if DEBUG:
            print " *** Attaching checkError to client.ready_deferred", self.client.ready_deferred
            print "current ready_deferred callbacks are"
            pprint.pprint(self.client.ready_deferred.callbacks)
        self.client.ready_deferred.addErrback(checkError)
        self.resetDelay()
        return p

    @defer.inlineCallbacks
    def _doQuery(self, query, query_args=None): # TODO query_args
        if DEBUG:
            print "Attempting an actual query \"%s\"" % _escape(query, query_args,self.text_factory)
        yield self._begin()
        if DEBUG:
            print "Finished issuing query, fetching all results"
        result = yield self.client.fetchall(_escape(query, query_args,self.text_factory))
        if DEBUG:
            print "Fetched %d results" % (len(result),)
        defer.returnValue(result)

    @defer.inlineCallbacks
    def _doOperation(self, query, query_args=None): # TODO query_args
        if DEBUG:
            print "Attempting an actual operation \"%s\"" % _escape(query, query_args,self.text_factory)
        yield self._begin()
        result = yield self.client.query(_escape(query, query_args,self.text_factory))
        defer.returnValue(result)

    @defer.inlineCallbacks
    def _doSelectDb(self, db, ignored):
        if DEBUG:
            print "Attempting an actual selectDb \"%s\"" % db
        yield self._begin()
        yield self.client.select_db(db)


class DeferredConnection:
    def __init__(self, pool):
        self._pool = pool
        self._deferred = defer.Deferred()
        self._deferred.addCallback(self._useConnection)

    def _useConnection(self, conn):
        return conn

    def runQuery(self, query, query_args=None):
        def _runQuery(c):
            return c.runQuery(query, query_args)
        self._deferred.addCallback(_runQuery)
        return self._deferred

    def runOperation(self, query, query_args=None):
        def _runOperation(c):
            return c.runOperation(query, query_args)
        self._deferred.addCallback(_runOperation)
        return self._deferred

    def selectDb(self, db):
        self._deferred.addCallback(lambda conn: conn.selectDb(db))
        return self._deferred

class ConnectionPool:
    """
    Represents a pool of connections to MySQL.
    """

    def __init__(self, hostname=None, username=None, password=None,
                 database=None,
                 num_connections=5, connect_timeout=None,
                 query_timeout=None, idle_timeout=None, retry_on_error=False,
                 temporary_error_strings=[], port=3306):
        # Connections in the pool that can be used to run queries
        self._unused_connections = []

        # Deferred connections whose execution is postponed until a
        # database connection becomes available.
        self._deferred_connections = []

        for i in xrange(0, num_connections):
            conn = MySQLConnection(hostname, username, password, database,
                                   connect_timeout, query_timeout,
                                   idle_timeout, retry_on_error,
                                   temporary_error_strings, port,
                                   self)
            self._unused_connections.append(conn)

    def _doneQuery(self, conn):
        """Called when a connection becomes available."""
        if self._deferred_connections:
            # If we have deferred connections, pick up the oldest one and
            # run it on the newly available connection.
            defconn = self._deferred_connections.pop(0)
            defconn._deferred.callback(conn)
        else:
            # Otherwise just return the connection in the list of
            # available connections.
            self._unused_connections.append(conn)

    def _getConnection(self):
        if self._unused_connections:
            # If we have available connections return one
            conn = self._unused_connections.pop()
            return conn
        else:
            # Otherwise create a deferred connection which will be
            # executed when a connection from the pool becomes
            # available.
            defconn = DeferredConnection(self)
            self._deferred_connections.append(defconn)
            return defconn

    def runQuery(self, query, query_args=None):
        conn = self._getConnection()
        return conn.runQuery(query, query_args)

    def runOperation(self, query, query_args=None):
        conn = self._getConnection()
        return conn.runOperation(query, query_args)

    def selectDb(self, db):
        conn = self._getConnection()
        return conn.selectDb(db)

########NEW FILE########
__FILENAME__ = error
class MySQLError(Exception):
    def __init__(self, message, errno=None, sqlstate=None, query=None):
        super(MySQLError, self).__init__(message, errno, sqlstate, query)
        self.msg, self.errno, self.sqlstate, self.query = message, errno, sqlstate, query

########NEW FILE########
__FILENAME__ = protocol
from __future__ import with_statement
from twisted.internet import defer
from twisted.protocols.policies import TimeoutMixin
from twisted.python import log
from qbuf.twisted_support import MultiBufferer, MODE_STATEFUL
from twisted.internet.protocol import Protocol
from txmysql import util, error
import struct
from hashlib import sha1
import sys
#import pprint
import datetime

typemap = {
    0x01: 1,
    0x02: 2,
    0x03: 4,
    0x04: 4,
    0x05: 8,
    0x08: 8,
    0x09: 3,
    0x0c: 8
}

def _xor(message1, message2):
        length = len(message1)
        result = ''
        for i in xrange(length):
                x = (struct.unpack('B', message1[i:i+1])[0] ^ struct.unpack('B', message2[i:i+1])[0])
                result += struct.pack('B', x)
        return result

def dump_packet(data):
        def is_ascii(data):
                if data.isalnum():
                        return data
                return '.'
        print "packet length %d" % len(data)
        print "method call: %s \npacket dump" % sys._getframe(2).f_code.co_name
        print "-" * 88
        dump_data = [data[i:i+16] for i in xrange(len(data)) if i%16 == 0]
        for d in dump_data:
                print ' '.join(map(lambda x:"%02X" % ord(x), d)) + \
                                '   ' * (16 - len(d)) + ' ' * 2 + ' '.join(map(lambda x:"%s" % is_ascii(x), d))
        print "-" * 88
        print ""

def operation(func):
    func = defer.inlineCallbacks(func)
    def wrap(self, *a, **kw):
        return self._do_operation(func, self, *a, **kw)
    return wrap

class MySQLProtocol(MultiBufferer, TimeoutMixin):
    mode = MODE_STATEFUL
    def getInitialState(self):
        return self._read_header, 4
    
    def timeoutConnection(self):
        #print "Timing out connection"
        TimeoutMixin.timeoutConnection(self)

    def connectionClosed(self, reason):
        #print "CONNECTIONCLOSED"
        #MultiBufferer.connectionClosed(self, reason)
        Protocol.connectionClosed(self, reason)
    
    def connectionLost(self, reason):
        #print "CONNECTIONLOST"
        #MultiBufferer.connectionLost(self, reason)
        # XXX When we call MultiBufferer.connectionLost, we get
        # unhandled errors (something isn't adding an Errback
        # to the deferred which eventually gets GC'd, but I'm
        # not *too* worried because it *does* get GC'd).
        # Do check that the things which yield on read() on
        # the multibufferer get correctly GC'd though.
        Protocol.connectionLost(self, reason)
    
    def _read_header(self, data):
        length, _ = struct.unpack('<3sB', data)
        length = util.unpack_little_endian(length)
        def cb(data):
            log.msg('unhandled packet: %r' % (data,))
            return self._read_header, 4
        return cb, length

    def __init__(self, username, password, database, idle_timeout=None):
        MultiBufferer.__init__(self)
        self.username, self.password, self.database = username, password, database
        self.sequence = None
        self.ready_deferred = defer.Deferred()
        self._operations = []
        self._current_operation = None
        self.factory = None
        self.setTimeout(idle_timeout)
        self.debug_query = None

    @defer.inlineCallbacks
    def read_header(self):
        length, seq = yield self.unpack('<3sB')
        self.sequence = seq + 1
        length = util.unpack_little_endian(length)
        defer.returnValue(util.LengthTracker(self, length))

    @defer.inlineCallbacks
    def read_eof(self, read_header=True):
        ret = {'is_eof': True}
        if read_header:
            t = yield self.read_header()
            yield t.read(1)
            unpacker = t.unpack
        else:
            unpacker = self.unpack
        ret['warning_count'], ret['flags'] = yield unpacker('<HH')
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def read_rows(self, columns):
        ret = []
        while True:
            t = yield self.read_header()
            length = yield t.read_lcb()
            if length is util._EOF:
                break
            x = columns
            row = []
            while True:
                if length is None:
                    row.append(None)
                else:
                    row.append((yield t.read(length)))
                x -= 1
                if not x:
                    break
                length = yield t.read_lcb()
            row.append((yield t.read_rest()))
            ret.append(row)
        defer.returnValue(ret)

    @defer.inlineCallbacks
    def read_result(self, is_prepare=False, read_rows=True, data_types=None):
        self.resetTimeout()
        t = yield self.read_header()
        field_count = yield t.read_lcb()
        ret = {}
        if field_count == util._EOF:
            ret = yield self.read_eof(read_header=False)
        elif field_count == 0:
            if is_prepare:
                ret['stmt_id'], ret['columns'], ret['parameters'], ret['warning_count'] = yield t.unpack('<IHHxH')
                if ret['parameters']:
                    ret['placeholders'] = yield self.read_fields()
                ret['fields'] = yield self.read_fields()
            elif data_types is not None:
                nulls = yield t.read((len(data_types) + 9) // 8)
                nulls = util.unpack_little_endian(nulls) >> 2
                cols = []
                for type in data_types:
                    if nulls & 1:
                        cols.append(None)
                    elif type in typemap:
                        val = yield t.read(typemap[type])
                        if type == 4:
                            val, = struct.unpack('<f', val)
                        elif type == 5:
                            val, = struct.unpack('<d', val)
                        elif type == 12:
                            try:
                                val = datetime.datetime(*struct.unpack("<xHBBBBB",val)).strftime('%Y-%m-%d %H:%M:%S')
                            except Exception, e:
                                print "CRITICAL: Caught exception in txmysql when trying",
                                print "to decode datetime value %r" % (val,),
                                print "exception follows, returning None to application",
                                print e
                                val = None
                        else:
                            val = util.unpack_little_endian(val)
                        cols.append(val)
                    else:
                        cols.append((yield t.read_lcs()))
                    nulls >>= 1
                ret['cols'] = cols
                ret['x'] = yield t.read_rest()
            else:
                ret['affected_rows'] = yield t.read_lcb()
                ret['insert_id'] = yield t.read_lcb()
                ret['server_status'], ret['warning_count'] = yield t.unpack('<HH')
                ret['message'] = yield t.read_rest()
        elif field_count == 0xff:
            errno, sqlstate = yield t.unpack('<Hx5s')
            message = yield t.read_rest()
            raise error.MySQLError(message, errno, sqlstate, self.debug_query)
        else:
            if t:
                ret['extra'] = yield t.read_lcb()
            ret['fields'] = yield self.read_fields()
            if read_rows:
                ret['rows'] = yield self.read_rows(field_count)
                ret['eof'] = yield self.read_eof(read_header=False)

        defer.returnValue(ret)

    @defer.inlineCallbacks
    def read_fields(self):
        fields = []
        while True:
            field = yield self.read_field()
            if field is util._EOF:
                yield self.read_eof(read_header=False)
                break
            fields.append(field)
        defer.returnValue(fields)

    @defer.inlineCallbacks
    def read_field(self):
        t = yield self.read_header()
        ret = {}
        first_length = yield t.read_lcb()
        if first_length is util._EOF:
            defer.returnValue(util._EOF)
        ret['catalog'] = yield t.read(first_length)
        for name in ['db', 'table', 'org_table', 'name', 'org_name']:
            ret[name] = yield t.read_lcs()
        ret['charsetnr'], ret['length'], ret['type'] = yield t.unpack('<xHIB')
        ret['flags'], ret['decimals'] = yield t.unpack('<HBxx')
        if t:
            ret['default'] = yield t.read_lcb()
        defer.returnValue(ret)

    def connectionMade(self):
        d = self.do_handshake()
        def done_handshake(data):
            self.ready_deferred.callback(data) # Handles errbacks too
            self.ready_deferred = defer.Deferred()
        d.addBoth(done_handshake)
    
    def _update_operations(self, _result=None):
        if self._operations:
            d, f, a, kw = self._operations.pop(0)
            self.sequence = 0
            self._current_operation = f(*a, **kw)
            (self._current_operation
                .addBoth(self._update_operations)
                .chainDeferred(d))
        else:
            self._current_operation = None
        return _result
    
    def _do_operation(self, func, *a, **kw):
        d = defer.Deferred()
        self._operations.append((d, func, a, kw))
        if self._current_operation is None:
            self._update_operations()
        return d

    @operation
    def do_handshake(self):
        self.resetTimeout()
        t = yield self.read_header()
        protocol_version, = yield t.unpack('<B')
        yield t.read_cstring() # server_version
        thread_id, scramble_buf = yield t.unpack('<I8sx')
        capabilities, language, status = yield t.unpack('<HBH')
        #print hex(capabilities)
        capabilities ^= capabilities & 32
        capabilities |= 0x30000
        if self.database:
            capabilities |= 1 << 3 # CLIENT_CONNECT_WITH_DB
        yield t.read(13)
        scramble_buf += yield t.read(12) # The last byte is a NUL
	yield t.read_cstring() # the NUL byte.
	yield t.read_remain()

        scramble_response = _xor(sha1(scramble_buf+sha1(sha1(self.password).digest()).digest()).digest(), sha1(self.password).digest())

        with util.DataPacker(self) as p:
            p.pack('<IIB23x', capabilities, 2**23, language)
            p.write_cstring(self.username)
            p.write_lcs(scramble_response)
            if self.database:
                p.write_cstring(self.database)

        result = yield self.read_result()
        defer.returnValue(result)
    
    @operation
    def _ping(self):
        with util.DataPacker(self) as p:
            p.write('\x0e')
        
        result = yield self.read_result()
        import pprint; pprint.pprint(result)
    
    @operation
    def _prepare(self, query):
        with util.DataPacker(self) as p:
            p.write('\x16')
            p.write(query)
        
        result = yield self.read_result(is_prepare=True)
        defer.returnValue(result)
    
    @operation
    def _execute(self, stmt_id):
        with util.DataPacker(self) as p:
            p.pack('<BIBIB', 0x17, stmt_id, 1, 1, 1)
        result = yield self.read_result(read_rows=False)
        defer.returnValue([d['type'] for d in result['fields']])
  

    @operation
    def _fetch(self, stmt_id, rows, types):
        with util.DataPacker(self) as p:
            p.pack('<BII', 0x1c, stmt_id, rows)
        
        rows = []
        while True:
            result = yield self.read_result(data_types=types)
            # TODO: We should check whether this result indicates that there
            # are no rows for us to fetch; then rather than hanging forever we
            # should immediately return to the application code.  Perhaps one
            # of read_result's cases will already cover this eventuality and we
            # can just inspect it here.
            if result.get('is_eof'):
                more_rows = not result['flags'] & 128
                break
            rows.append(result)

        defer.returnValue((rows, more_rows))


    @operation
    def select_db(self, database):
        with util.DataPacker(self) as p:
            p.write('\x02')
            p.write(database)
        
        yield self.read_result()

    
    @operation
    def query(self, query, read_result=False):
        "A query with no response data"
        self.debug_query = query
        with util.DataPacker(self) as p:
            p.write('\x03')
            p.write(query)

        ret = yield self.read_result()
        defer.returnValue(ret)
    
    @operation
    def _close_stmt(self, stmt_id):
        """
        Destroy a prepared statement. The statement handle becomes invalid.
        """
        with util.DataPacker(self) as p:
            p.pack('<BI', 0x19, stmt_id)
        yield defer.succeed(True)


    @defer.inlineCallbacks
    def fetchall(self, query):
        #assert '\0' not in query, 'No NULs in your query, boy!'
        self.debug_query = query
        #print 'about to prepare'
        result = yield self._prepare(query)
        #print 'finished prepare'
        types = yield self._execute(result['stmt_id'])
        #print '!' * 20, 'fetchall got past execute!'
        all_rows = yield self._do_fetch(result, types)
        defer.returnValue(all_rows)


    @defer.inlineCallbacks
    def _do_fetch(self, result, types):
        all_rows = []
        while True:
            #print 'going to fetch some results'
            rows, more_rows = yield self._fetch(result['stmt_id'], 2, types)
            #print 'got some rows', rows
            for row in rows:
                all_rows.append(row['cols'])
            if not more_rows:
                #print 'all done'
                break
        #print "****************************** Got last result" 
        yield self._close_stmt(result['stmt_id'])
        defer.returnValue(all_rows)



########NEW FILE########
__FILENAME__ = evildaemon
from twisted.internet import reactor, protocol
import random
import sys

class Echo(protocol.Protocol):
    def dataReceived(self, data):
        pass

def main():
    factory = protocol.ServerFactory()
    factory.protocol = Echo
    reactor.listenTCP(3306, factory)
    reactor.callLater(int(sys.argv[1]), reactor.stop)
    reactor.run()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = test_txmysql
"""
Test txMySQL against a local MySQL server

This test requires 'sudo' without a password, and expects a stock Ubuntu 10.04
MySQL setup. It will start and stop MySQL and occasionally replace it with an
evil daemon which absorbs packets.

TODO: Check code coverage for every line, then manually any compound expression
in a conditional to check that there is test case coverage for each case.

Please CREATE DATABASE foo and grant the appropriate credentials before running
this test suite.
"""
import os, pwd, sys
from errno import ENOENT

from twisted.python.filepath import FilePath
from twisted.trial import unittest
from twisted.internet import defer, reactor
from twisted.internet.base import DelayedCall
from twisted.internet.error import ConnectionDone

DelayedCall.debug = False
from txmysql import client
from HybridUtils import AsyncExecCmds, sleep
import secrets

if 'freebsd' in sys.platform:
    onFreeBSD = True
    skipReason = "Test only works on Ubuntu"
else:
    onFreeBSD = False
    skipReason = "Test only works on FreeBSD"

FREEBSD_TESTS = []


class MySQLClientTest(unittest.TestCase):

    @defer.inlineCallbacks
    def test_0004_cleanup_prepared_statements(self):
        """
        Checks that when there are no pending or current operations that we
        disconnect and stay disconnected.
        You must set max_prepared_stmt_count = 100 in /etc/mysql/my.cnf for
        this to actually get tested.
        """
        yield self._start_mysql()
        conn = self._connect_mysql()
        for i in range(200):
            if i % 100 == 0:
                print 'Done %i queries' % i
            res = yield conn.runQuery("select 1")
            self.assertEquals(res, [[1]])
        conn.disconnect()

    @defer.inlineCallbacks
    def test_0005_query_timeout_stay_disconnected(self):
        """
        Checks that when there are no pending or current operations that we
        disconnect and stay disconnected
        """
        yield self._start_mysql()
        conn = self._connect_mysql(retry_on_error=True, idle_timeout=2)
        res = yield conn.runQuery("select 1")
        yield sleep(6)
        self.assertIdentical(conn.client, None)
        conn.disconnect()
    
    @defer.inlineCallbacks
    def test_0010_two_queries_disconnected(self):
        yield self._start_mysql()
        conn = self._connect_mysql(retry_on_error=True, idle_timeout=1)
        yield conn.runQuery("select 1")
        yield sleep(2)
        a = conn.runQuery("select 2")
        b = conn.runQuery("select 3")
        a, b = yield defer.gatherResults([a, b])
        self.assertEquals(a, [[2]])
        self.assertEquals(b, [[3]])
        self.assertEquals((yield conn.runQuery("select 4")), [[4]])
        conn.disconnect()

    @defer.inlineCallbacks
    def test_0020_start_query_restart(self):
        yield self._start_mysql()
        conn = self._connect_mysql(retry_on_error=True, idle_timeout=2)
        result = yield conn.runQuery("select 2")
        #yield self._stop_mysql()
        #yield self._start_mysql()
        yield sleep(10)
        conn.disconnect()
        self.assertEquals(result, [[2]])

    def test_0030_escaping(self):
        try:
            client._escape("%s", ())
            self.fail("that should have raised an exception")
        except TypeError:
            pass

        try:
            client._escape("select * from baz baz baz", (1, 2, 3))
            self.fail("that should have raised an exception")
        except TypeError:
            pass

        result = client._escape("update foo set bar=%s where baz=%s or bash=%s", ("%s", "%%s", 123))
        self.assertEquals(result, "update foo set bar='%s' where baz='%%s' or bash='123'")

    @defer.inlineCallbacks
    def test_0040_thrash(self):
        yield self._start_mysql()
        conn = self._connect_mysql(retry_on_error=True)
        yield conn.runOperation("drop table if exists thrashtest")
        yield conn.runOperation("create table thrashtest (id int)")

        dlist = []
        for i in range(100):
            dlist.append(conn.runOperation("insert into thrashtest values (%s)", [i]))
        yield defer.DeferredList(dlist)

        dlist = []
        for i in range(50):
            print "Appending %i" % i
            dlist.append(conn.runQuery("select sleep(0.1)"))
            dlist.append(conn.runQuery("select * from thrashtest where id=%s", [i]))

        yield sleep(3)

        print "About to stop MySQL"
        dstop = self._stop_mysql()
        def and_start(data):
            print "About to start MySQL"
            return self._start_mysql()
        dstop.addCallback(and_start)
        
        for i in range(50,100):
            print "Appending %i" % i
            dlist.append(conn.runQuery("select sleep(0.1)"))
            dlist.append(conn.runQuery("select * from thrashtest where id=%s", [i]))

        results = yield defer.DeferredList(dlist)
        print results

        conn.disconnect()
        #self.assertEquals(result, [[1]])


    @defer.inlineCallbacks
    def test_0050_test_initial_database_selection(self):
        """
        Check that when we connect to a database in the initial handshake, we
        end up in the 'foo' database. TOOD: Check that we're actually in the
        'foo' database somehow.
        """
        yield self._start_mysql()
        conn = self._connect_mysql(database='foo')
        result = yield conn.runOperation("create table if not exists foo (id int primary key)")
        result = yield conn.runOperation("delete from foo.foo")
        result = yield conn.runOperation("insert into foo.foo set id=191919")
        result = yield conn.runQuery("select * from foo order by id desc limit 1")
        conn.disconnect()
        self.assertEquals(result, [[191919]])

    @defer.inlineCallbacks
    def test_0100_start_connect_query(self):
        """
        1. Start MySQL
        2. Connect
        3. Query - check result
        """
        yield self._start_mysql()
        conn = self._connect_mysql()
        result = yield conn.runQuery("select 2")
        conn.disconnect()
        self.assertEquals(result, [[2]])

    @defer.inlineCallbacks
    def test_0200_stop_connect_query_start(self):
        """
        1. Connect, before MySQL is started
        2. Start MySQL
        3. Query - check result
        XXX The comment is correct but the code is wrong!
        """
        conn = self._connect_mysql()
        d = conn.runQuery("select 2") # Should get connection refused, because we're not connected right now
        yield self._start_mysql()
        result = yield d
        conn.disconnect()
        self.assertEquals(result, [[2]])

    @defer.inlineCallbacks
    def test_0210_stop_connect_query_start_retry_on_error(self):
        """
        1. Connect, before MySQL is started
        2. Start MySQL
        3. Query - check result
        """
        conn = self._connect_mysql(retry_on_error=True)
        d = conn.runQuery("select 2")
        yield self._start_mysql()
        result = yield d
        conn.disconnect()
        self.assertEquals(result, [[2]])

    @defer.inlineCallbacks
    def test_0211_stop_connect_query_start_retry_on_error_two_queries(self):
        """
        1. Connect, before MySQL is started
        2. Start MySQL
        3. Query - check result
        """
        conn = self._connect_mysql(retry_on_error=True)
        d = conn.runQuery("select 2")
        d2 = conn.runQuery("select 3")
        yield self._start_mysql()
        result = yield d
        result2 = yield d2
        conn.disconnect()
        self.assertEquals(result, [[2]])
        self.assertEquals(result2, [[3]])

    @defer.inlineCallbacks
    def test_0300_start_idle_timeout(self):
        """
        Connect, with evildaemon in place of MySQL
        Evildaemon stops in 5 seconds, which is longer than our idle timeout
        so the idle timeout should fire, disconnecting us.
        But because we have a query due, we reconnect and get the result.
        """
        daemon_dfr = self._start_evildaemon(secs=10)
        conn = self._connect_mysql(idle_timeout=3, retry_on_error=True)
        d = conn.runQuery("select 2")
        yield daemon_dfr
        yield self._start_mysql()
        result = yield d
        conn.disconnect()
        self.assertEquals(result, [[2]])

    @defer.inlineCallbacks
    def test_0400_start_connect_long_query_timeout(self):
        """
        Connect to the real MySQL, run a long-running query which exceeds the
        idle timeout, check that it times out and returns the appropriate
        Failure object (because we haven't set retry_on_error)
        """
        yield self._start_mysql()
        conn = self._connect_mysql(idle_timeout=3)
        try:
            result = yield conn.runQuery("select sleep(5)")
        except Exception, e:
            print "Caught exception %s" % e
            self.assertTrue(isinstance(e, ConnectionDone))
        finally:
            conn.disconnect()
        
    @defer.inlineCallbacks
    def test_0500_retry_on_error(self):
        """
        Start a couple of queries in parallel.
        Both of them should take 10 seconds, but restart the MySQL
        server after 5 seconds.
        Setting the connection and idle timeouts allows bad connections
        to fail.
        """
        yield self._start_mysql()
        conn = self._connect_mysql(retry_on_error=True)
        d1 = conn.runQuery("select sleep(7)")
        d2 = conn.runQuery("select sleep(7)")
        yield sleep(2)
        yield self._stop_mysql()
        yield self._start_mysql()
        result = yield defer.DeferredList([d1, d2])
        conn.disconnect()
        self.assertEquals(result, [(True, [[0]]), (True, [[0]])])

    @defer.inlineCallbacks
    def test_0550_its_just_one_thing_after_another_with_you(self):
        """
        Sanity check that you can do one thing and then another thing.
        """
        yield self._start_mysql()
        conn = self._connect_mysql(retry_on_error=True)
        yield conn.runQuery("select 2")
        yield conn.runQuery("select 2")
        conn.disconnect()

    @defer.inlineCallbacks
    def test_0600_error_strings_test(self):
        """
        This test causes MySQL to return what we consider a temporary local
        error.  We do this by starting MySQL, querying a table, then physically
        removing MySQL's data files.

        This triggers MySQL to return a certain error code which we want to
        consider a temporary local error, which should result in a reconnection
        to MySQL.

        This is arguably the most application-specific behaviour in the txMySQL
        client library.

        """
        res = yield AsyncExecCmds([
            """sh -c '
            cd /var/lib/mysql/foo;
            chmod 0660 *;
            chown mysql:mysql *
            '"""], cmd_prefix="sudo ").getDeferred()
        yield self._start_mysql()
        conn = self._connect_mysql(retry_on_error=True,
            temporary_error_strings=[
                "Can't find file: './foo/foo.frm' (errno: 13)",
            ])
        yield conn.selectDb("foo")
        yield conn.runOperation("create database if not exists foo")
        yield conn.runOperation("create database if not exists foo")
        yield conn.runOperation("drop table if exists foo")
        yield conn.runOperation("create table foo (id int)")
        yield conn.runOperation("insert into foo set id=1")
        result = yield conn.runQuery("select * from foo")
        self.assertEquals(result, [[1]])

        # Now the tricky bit, we have to force MySQL to yield the error message.
        res = yield AsyncExecCmds([
            """sh -c '
            cd /var/lib/mysql/foo;
            chmod 0600 *;
            chown root:root *'
            """], cmd_prefix="sudo ").getDeferred()
        print res
        
        yield conn.runOperation("flush tables") # cause the files to get re-opened
        d = conn.runQuery("select * from foo") # This will spin until we fix the files, so do that pronto
        yield sleep(1)
        res = yield AsyncExecCmds([
            """sh -c '
            cd /var/lib/mysql/foo;
            chmod 0660 *;
            chown mysql:mysql *
            '"""], cmd_prefix="sudo ").getDeferred()
        print res
        result = yield d
        self.assertEquals(result, [[1]])
        conn.disconnect()
   
    @defer.inlineCallbacks
    def test_0700_error_strings_during_connection_phase(self):
        yield self._start_mysql()
        conn = self._connect_mysql(retry_on_error=True,
            temporary_error_strings=[
                "Unknown database 'databasewhichdoesnotexist'",
            ], database='databasewhichdoesnotexist')

        yield conn.runQuery("select * from foo")

    test_0700_error_strings_during_connection_phase.skip = 'Use in debugging, never passes'


    @defer.inlineCallbacks
    def test_0900_autoRepairKeyError(self):
        """
        
        """
        yield AsyncExecCmds(['/opt/HybridCluster/init.d/mysqld stop']).getDeferred()
        sampleBadDataPath = FilePath(__file__).sibling('bad-data')
        target = FilePath('/var/db/mysql/autorepair')
        try:
            target.remove()
        except OSError, e:
            if e.errno != ENOENT:
                raise
        sampleBadDataPath.copyTo(target)
        passwordEntry = pwd.getpwnam('mysql')
        for path in target.walk():
            os.chown(path.path, passwordEntry.pw_uid, passwordEntry.pw_gid)
        yield AsyncExecCmds(['/opt/HybridCluster/init.d/mysqld start']).getDeferred()
        conn = client.MySQLConnection('127.0.0.1', 'root', secrets.MYSQL_ROOT_PASS, 'autorepair',
                                      port=3307, autoRepair=True)
        yield conn.runQuery("select id from mailaliases where username='iceshaman@gmail.com' and deletedate is null")
        conn.disconnect()
    FREEBSD_TESTS.append(test_0900_autoRepairKeyError.__name__)

    # Utility functions:

    def _stop_mysql(self):
        return AsyncExecCmds(['stop mysql'], cmd_prefix='sudo ').getDeferred()
    
    def _start_mysql(self):
        return AsyncExecCmds(['start mysql'], cmd_prefix='sudo ').getDeferred()
    
    def _start_evildaemon(self, secs):
        """
        Simulates a MySQL server which accepts connections but has mysteriously
        stopped returning responses at all, i.e. it's just /dev/null
        """
        return AsyncExecCmds(['python ../test/evildaemon.py %s' % str(secs)], cmd_prefix='sudo ').getDeferred()
    
    def setUp(self):
        """
        Stop MySQL before each test
        """
        name = self._testMethodName
        if onFreeBSD and name not in FREEBSD_TESTS:
            raise unittest.SkipTest("%r only runs on FreeBSD" % (name,))
        elif not onFreeBSD and name in FREEBSD_TESTS:
            raise unittest.SkipTest("%r does not run on FreeBSD" % (name,))
        return self._stop_mysql()

    def tearDown(self):
        """
        Stop MySQL before each test
        """
        reactor.disconnectAll()

    def _connect_mysql(self, **kw):
        if 'database' in kw:
            return client.MySQLConnection('127.0.0.1', 'root', secrets.MYSQL_ROOT_PASS, **kw)
        else:
            return client.MySQLConnection('127.0.0.1', 'root', secrets.MYSQL_ROOT_PASS, 'foo', **kw)



########NEW FILE########
__FILENAME__ = util
from twisted.internet import defer
import cStringIO
import struct

_EOF = object()
_lcb_lengths = {
    252: 2,
    253: 3,
    254: 8,
}

def unpack_little_endian(s):
    ret = 0
    for c in reversed(s):
        ret = (ret << 8) | ord(c)
    return ret

def pack_little_endian(v, pad_to=None):
    ret = ''
    while v:
        ret += chr(v & 0xff)
        v >>= 8
    if pad_to is not None:
        ret = ret.ljust(pad_to, '\0')
    return ret

class LengthTracker(object):
    def __init__(self, wrap, length):
        self.length = 0
        self.tot_length = length
        self.w = wrap

    def _check_length(self):
        if self.length > self.tot_length:
            import pprint; pprint.pprint(vars(self))
            raise ValueError('reading beyond the length of the packet')

    def read(self, length):
        if not length:
            return defer.succeed('')
        self.length += length
        self._check_length()
        return self.w.read(length)

    def read_remain(self):
        if self.length == self.tot_length:
            return defer.succeed('')
        return self.w.read(self.tot_length-self.length)

    @defer.inlineCallbacks
    def readline(self, delimiter=None):
        line = yield self.w.readline(delimiter)
        self.length += len(line)+1 # 1 is the length of delimiter
        self._check_length()
        defer.returnValue(line)

    def unpack(self, fmt):
        self.length += struct.calcsize(fmt)
        self._check_length()
        return self.w.unpack(fmt)

    def read_cstring(self):
        return self.readline(delimiter='\0')

    @defer.inlineCallbacks
    def read_lcb(self):
        val, = yield self.unpack('<B')
        if val == 0xfe and self.tot_length < 9:
            defer.returnValue(_EOF)
        if val <= 250 or val == 255:
            defer.returnValue(val)
        elif val == 251:
            defer.returnValue(None)
        bytes = yield self.read(_lcb_lengths[val])
        defer.returnValue(unpack_little_endian(bytes))

    @defer.inlineCallbacks
    def read_lcs(self):
        length = yield self.read_lcb()
        defer.returnValue((yield self.read(length)))

    def read_rest(self):
        return self.read(self.tot_length - self.length)
    
    def __nonzero__(self):
        return self.length < self.tot_length

class DataPacker(object):
    def __init__(self, wrap):
        self.io = cStringIO.StringIO()
        self.w = wrap

    def pack(self, fmt, *values):
        self.io.write(struct.pack(fmt, *values))

    def write(self, data):
        self.io.write(data)

    def write_cstring(self, data):
        self.io.write(data)
        self.io.write('\0')

    def write_lcb(self, value):
        if value < 0:
            raise ValueError('write_lcb packs bytes 0 <= x <= 2**64 - 1')
        elif value <= 250:
            self.io.write(chr(value))
            return
        elif value <= 2**16 - 1:
            self.io.write('\xfc')
            pad = 2
        elif value <= 2**24 - 1:
            self.io.write('\xfd')
            pad = 3
        elif value <= 2**64 - 1:
            self.io.write('\xfe')
            pad = 8
        else:
            raise ValueError('write_lcb packs bytes 0 <= x <= 2**64 - 1')
        self.io.write(pack_little_endian(value, pad))

    def write_lcs(self, string):
        self.write_lcb(len(string))
        self.write(string)

    def as_header(self, number):
        length = pack_little_endian(self.io.tell(), 3)
        return length + chr(number)

    def get_value(self):
        return self.io.getvalue()

    def to_transport(self, transport, number):
        transport.write(self.as_header(number))
        transport.write(self.get_value())

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_value is not None:
            return
        self.to_transport(self.w.transport, self.w.sequence)
        self.w.sequence += 1

########NEW FILE########
