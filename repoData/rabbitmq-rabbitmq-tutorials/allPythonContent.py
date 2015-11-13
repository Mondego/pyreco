__FILENAME__ = emit_log
#!/usr/bin/env python
import pika
import sys

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='logs',
                         type='fanout')

message = ' '.join(sys.argv[1:]) or "info: Hello World!"
channel.basic_publish(exchange='logs',
                      routing_key='',
                      body=message)
print " [x] Sent %r" % (message,)
connection.close()

########NEW FILE########
__FILENAME__ = emit_log_direct
#!/usr/bin/env python
import pika
import sys

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='direct_logs',
                         type='direct')

severity = sys.argv[1] if len(sys.argv) > 1 else 'info'
message = ' '.join(sys.argv[2:]) or 'Hello World!'
channel.basic_publish(exchange='direct_logs',
                      routing_key=severity,
                      body=message)
print " [x] Sent %r:%r" % (severity, message)
connection.close()

########NEW FILE########
__FILENAME__ = emit_log_topic
#!/usr/bin/env python
import pika
import sys

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='topic_logs',
                         type='topic')

routing_key = sys.argv[1] if len(sys.argv) > 1 else 'anonymous.info'
message = ' '.join(sys.argv[2:]) or 'Hello World!'
channel.basic_publish(exchange='topic_logs',
                      routing_key=routing_key,
                      body=message)
print " [x] Sent %r:%r" % (routing_key, message)
connection.close()

########NEW FILE########
__FILENAME__ = new_task
#!/usr/bin/env python
import pika
import sys

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='task_queue', durable=True)

message = ' '.join(sys.argv[1:]) or "Hello World!"
channel.basic_publish(exchange='',
                      routing_key='task_queue',
                      body=message,
                      properties=pika.BasicProperties(
                         delivery_mode = 2, # make message persistent
                      ))
print " [x] Sent %r" % (message,)
connection.close()

########NEW FILE########
__FILENAME__ = receive
#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()


channel.queue_declare(queue='hello')

print ' [*] Waiting for messages. To exit press CTRL+C'

def callback(ch, method, properties, body):
    print " [x] Received %r" % (body,)

channel.basic_consume(callback,
                      queue='hello',
                      no_ack=True)

channel.start_consuming()

########NEW FILE########
__FILENAME__ = receive_logs
#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='logs',
                         type='fanout')

result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue

channel.queue_bind(exchange='logs',
                   queue=queue_name)

print ' [*] Waiting for logs. To exit press CTRL+C'

def callback(ch, method, properties, body):
    print " [x] %r" % (body,)

channel.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True)

channel.start_consuming()

########NEW FILE########
__FILENAME__ = receive_logs_direct
#!/usr/bin/env python
import pika
import sys

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='direct_logs',
                         type='direct')

result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue

severities = sys.argv[1:]
if not severities:
    print >> sys.stderr, "Usage: %s [info] [warning] [error]" % (sys.argv[0],)
    sys.exit(1)

for severity in severities:
    channel.queue_bind(exchange='direct_logs',
                       queue=queue_name,
                       routing_key=severity)

print ' [*] Waiting for logs. To exit press CTRL+C'

def callback(ch, method, properties, body):
    print " [x] %r:%r" % (method.routing_key, body,)

channel.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True)

channel.start_consuming()

########NEW FILE########
__FILENAME__ = receive_logs_topic
#!/usr/bin/env python
import pika
import sys

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.exchange_declare(exchange='topic_logs',
                         type='topic')

result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue

binding_keys = sys.argv[1:]
if not binding_keys:
    print >> sys.stderr, "Usage: %s [binding_key]..." % (sys.argv[0],)
    sys.exit(1)

for binding_key in binding_keys:
    channel.queue_bind(exchange='topic_logs',
                       queue=queue_name,
                       routing_key=binding_key)

print ' [*] Waiting for logs. To exit press CTRL+C'

def callback(ch, method, properties, body):
    print " [x] %r:%r" % (method.routing_key, body,)

channel.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True)

channel.start_consuming()

########NEW FILE########
__FILENAME__ = rpc_client
#!/usr/bin/env python
import pika
import uuid

class FibonacciRpcClient(object):
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
                host='localhost'))

        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(self.on_response, no_ack=True,
                                   queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key='rpc_queue',
                                   properties=pika.BasicProperties(
                                         reply_to = self.callback_queue,
                                         correlation_id = self.corr_id,
                                         ),
                                   body=str(n))
        while self.response is None:
            self.connection.process_data_events()
        return int(self.response)

fibonacci_rpc = FibonacciRpcClient()

print " [x] Requesting fib(30)"
response = fibonacci_rpc.call(30)
print " [.] Got %r" % (response,)

########NEW FILE########
__FILENAME__ = rpc_server
#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))

channel = connection.channel()

channel.queue_declare(queue='rpc_queue')

def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-1) + fib(n-2)

def on_request(ch, method, props, body):
    n = int(body)

    print " [.] fib(%s)"  % (n,)
    response = fib(n)

    ch.basic_publish(exchange='',
                     routing_key=props.reply_to,
                     properties=pika.BasicProperties(correlation_id = \
                                                         props.correlation_id),
                     body=str(response))
    ch.basic_ack(delivery_tag = method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(on_request, queue='rpc_queue')

print " [x] Awaiting RPC requests"
channel.start_consuming()

########NEW FILE########
__FILENAME__ = send
#!/usr/bin/env python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()


channel.queue_declare(queue='hello')

channel.basic_publish(exchange='',
                      routing_key='hello',
                      body='Hello World!')
print " [x] Sent 'Hello World!'"
connection.close()

########NEW FILE########
__FILENAME__ = worker
#!/usr/bin/env python
import pika
import time

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='task_queue', durable=True)
print ' [*] Waiting for messages. To exit press CTRL+C'

def callback(ch, method, properties, body):
    print " [x] Received %r" % (body,)
    time.sleep( body.count('.') )
    print " [x] Done"
    ch.basic_ack(delivery_tag = method.delivery_tag)

channel.basic_qos(prefetch_count=1)
channel.basic_consume(callback,
                      queue='task_queue')

channel.start_consuming()

########NEW FILE########
__FILENAME__ = emit_log
#!/usr/bin/env python
import puka
import sys

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.exchange_declare(exchange='logs', type='fanout')
client.wait(promise)

message = ' '.join(sys.argv[1:]) or "info: Hello World!"
promise = client.basic_publish(exchange='logs', routing_key='', body=message)
client.wait(promise)

print " [x] Sent %r" % (message,)
client.close()

########NEW FILE########
__FILENAME__ = emit_log_direct
#!/usr/bin/env python
import puka
import sys

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.exchange_declare(exchange='direct_logs', type='direct')
client.wait(promise)

severity = sys.argv[1] if len(sys.argv) > 1 else 'info'
message = ' '.join(sys.argv[2:]) or 'Hello World!'
promise = client.basic_publish(exchange='direct_logs', routing_key=severity,
                               body=message)
client.wait(promise)

print " [x] Sent %r:%r" % (severity, message)
client.close()

########NEW FILE########
__FILENAME__ = emit_log_topic
#!/usr/bin/env python
import puka
import sys

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.exchange_declare(exchange='topic_logs', type='topic')
client.wait(promise)

routing_key = sys.argv[1] if len(sys.argv) > 1 else 'anonymous.info'
message = ' '.join(sys.argv[2:]) or 'Hello World!'
promise = client.basic_publish(exchange='topic_logs', routing_key=routing_key,
                               body=message)
client.wait(promise)

print " [x] Sent %r:%r" % (routing_key, message)
client.close()

########NEW FILE########
__FILENAME__ = new_task
#!/usr/bin/env python
import puka
import sys

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.queue_declare(queue='task_queue', durable=True)
client.wait(promise)

message = ' '.join(sys.argv[1:]) or "Hello World!"
promise = client.basic_publish(exchange='',
                               routing_key='task_queue',
                               body=message,
                               headers={'delivery_mode': 2})
client.wait(promise)
print " [x] Sent %r" % (message,)

client.close()

########NEW FILE########
__FILENAME__ = receive
#!/usr/bin/env python
import puka

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.queue_declare(queue='hello')
client.wait(promise)


print ' [*] Waiting for messages. To exit press CTRL+C'

consume_promise = client.basic_consume(queue='hello', no_ack=True)
while True:
    msg_result = client.wait(consume_promise)
    print " [x] Received %r" % (msg_result['body'],)

########NEW FILE########
__FILENAME__ = receive_logs
#!/usr/bin/env python
import puka

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.exchange_declare(exchange='logs', type='fanout')
client.wait(promise)

promise = client.queue_declare(exclusive=True)
queue_name = client.wait(promise)['queue']

promise = client.queue_bind(exchange='logs', queue=queue_name)
client.wait(promise)


print ' [*] Waiting for logs. To exit press CTRL+C'

consume_promise = client.basic_consume(queue=queue_name, no_ack=True)
while True:
    msg_result = client.wait(consume_promise)
    print " [x] %r" % (msg_result['body'],)

########NEW FILE########
__FILENAME__ = receive_logs_direct
#!/usr/bin/env python
import puka
import sys

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.exchange_declare(exchange='direct_logs', type='direct')
client.wait(promise)

promise = client.queue_declare(exclusive=True)
queue_name = client.wait(promise)['queue']

severities = sys.argv[1:]
if not severities:
    print >> sys.stderr, "Usage: %s [info] [warning] [error]" % (sys.argv[0],)
    sys.exit(1)

for severity in severities:
    promise = client.queue_bind(exchange='direct_logs', queue=queue_name,
                                routing_key=severity)
    client.wait(promise)


print ' [*] Waiting for logs. To exit press CTRL+C'

consume_promise = client.basic_consume(queue=queue_name, no_ack=True)
while True:
    msg_result = client.wait(consume_promise)
    print " [x] %r:%r" % (msg_result['routing_key'], msg_result['body'])

########NEW FILE########
__FILENAME__ = receive_logs_topic
#!/usr/bin/env python
import puka
import sys

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.exchange_declare(exchange='topic_logs', type='topic')
client.wait(promise)

promise = client.queue_declare(exclusive=True)
queue_name = client.wait(promise)['queue']

binding_keys = sys.argv[1:]
if not binding_keys:
    print >> sys.stderr, "Usage: %s [binding_key]..." % (sys.argv[0],)
    sys.exit(1)

for binding_key in binding_keys:
    promise = client.queue_bind(exchange='topic_logs', queue=queue_name,
                                routing_key=binding_key)
    client.wait(promise)


print ' [*] Waiting for logs. To exit press CTRL+C'

consume_promise = client.basic_consume(queue=queue_name, no_ack=True)
while True:
    msg_result = client.wait(consume_promise)
    print " [x] %r:%r" % (msg_result['routing_key'], msg_result['body'])

########NEW FILE########
__FILENAME__ = rpc_client
#!/usr/bin/env python
import puka
import uuid

class FibonacciRpcClient(object):
    def __init__(self):
        self.client = client = puka.Client("amqp://localhost/")
        promise = client.connect()
        client.wait(promise)

        promise = client.queue_declare(exclusive=True)
        self.callback_queue = client.wait(promise)['queue']

        self.consume_promise = client.basic_consume(queue=self.callback_queue,
                                                    no_ack=True)

    def call(self, n):
        correlation_id = str(uuid.uuid4())
        # We don't need to wait on promise from publish, let it happen async.
        self.client.basic_publish(exchange='',
                                  routing_key='rpc_queue',
                                  headers={'reply_to': self.callback_queue,
                                           'correlation_id': correlation_id},
                                  body=str(n))
        while True:
            msg_result = self.client.wait(self.consume_promise)
            if msg_result['headers']['correlation_id'] == correlation_id:
                return int(msg_result['body'])


fibonacci_rpc = FibonacciRpcClient()

print " [x] Requesting fib(30)"
response = fibonacci_rpc.call(30)
print " [.] Got %r" % (response,)

########NEW FILE########
__FILENAME__ = rpc_server
#!/usr/bin/env python
import puka

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)

promise = client.queue_declare(queue='rpc_queue')
client.wait(promise)

# The worlds worst algorithm:
def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-1) + fib(n-2)


print " [x] Awaiting RPC requests"
consume_promise = client.basic_consume(queue='rpc_queue', prefetch_count=1)
while True:
    msg_result = client.wait(consume_promise)
    n = int(msg_result['body'])

    print " [.] fib(%s)"  % (n,)
    response = fib(n)

    # This publish doesn't need to be synchronous.
    client.basic_publish(exchange='',
                         routing_key=msg_result['headers']['reply_to'],
                         headers={'correlation_id':
                                      msg_result['headers']['correlation_id']},
                         body=str(response))
    client.basic_ack(msg_result)

########NEW FILE########
__FILENAME__ = send
#!/usr/bin/env python
import puka

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.queue_declare(queue='hello')
client.wait(promise)

promise = client.basic_publish(exchange='',
                               routing_key='hello',
                               body="Hello World!")
client.wait(promise)

print " [x] Sent 'Hello World!'"
client.close()

########NEW FILE########
__FILENAME__ = worker
#!/usr/bin/env python
import puka
import time

client = puka.Client("amqp://localhost/")
promise = client.connect()
client.wait(promise)


promise = client.queue_declare(queue='task_queue', durable=True)
client.wait(promise)
print ' [*] Waiting for messages. To exit press CTRL+C'

consume_promise = client.basic_consume(queue='task_queue', prefetch_count=1)
while True:
    msg_result = client.wait(consume_promise)
    body = msg_result['body']
    print " [x] Received %r" % (body,)
    time.sleep( body.count('.') )
    print " [x] Done"
    client.basic_ack(msg_result)

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
import time
import random
import re
import subprocess
import signal
import sys
import os

multiplier = float(os.environ.get('SLOWNESS', 1))

def run(cmd, **kwargs):
    p = subprocess.Popen(cmd.split(),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         **kwargs)
    p.wait()
    out = p.stdout.read()
    err = p.stderr.read()

    # compensate for slow Clojure examples startup:
    # lein trampoline run + clojure.core recompilation
    if kwargs.get("cwd") == "clojure":
        x = 3
    else:
        x = 1
    time.sleep(0.2 * multiplier * x)
    return p.returncode, out + '\n' + err

def spawn(cmd, **kwargs):
    p = subprocess.Popen(cmd.split(),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         **kwargs)
    if kwargs.get("cwd") == "clojure":
        x = 3
    else:
        x = 1
    time.sleep(0.5 * multiplier * x)
    return p

def wait(p, match):
    os.kill(p.pid, signal.SIGINT)
    p.wait()
    out = p.stdout.read()
    err = p.stderr.read()
    return bool(re.search(match, out)), out + '\n' + err



def gen(prog, arg="", **kwargs):
    Prog = ''.join([w.capitalize() for w in prog.split('_')])
    ctx = {
        'prog': prog,
        'Prog': Prog,
        # clojure ns
        'ns': prog.replace("_", "-"),
        'arg': arg,
        'java': kwargs.get('java', Prog),
        'dotnet': kwargs.get('dotnet', Prog),
        'ruby': kwargs.get('ruby', os.environ.get('RUBY', 'ruby1.9.1')),
        }
    return [
        ('python', './venv/bin/python %(prog)s.py %(arg)s' % ctx),
        # ('perl', 'perl %(prog)s.pl %(arg)s' % ctx),
        ('erlang', './%(prog)s.erl %(arg)s' % ctx),
        ('java', 'java -cp .:commons-io-1.2.jar:commons-cli-1.1.jar:'
             'rabbitmq-client.jar %(java)s %(arg)s' % ctx),
        ('clojure', './bin/lein trampoline run -m rabbitmq.tutorials.%(ns)s %(arg)s' % ctx),
        ('dotnet', 'env MONO_PATH=lib/bin mono %(dotnet)s.exe %(arg)s' % ctx),
        ('ruby', 'env RUBYOPT=-rubygems GEM_HOME=gems/gems RUBYLIB=gems/lib '
             '%(ruby)s %(prog)s.rb %(arg)s' % ctx),
        ('ruby-amqp', 'env RUBYOPT=-rubygems GEM_HOME=gems/gems RUBYLIB=gems/lib '
             '%(ruby)s %(prog)s.rb %(arg)s' % ctx),
        ('php', 'php %(prog)s.php %(arg)s' % ctx),
        ('python-puka', './venv/bin/python %(prog)s.py %(arg)s' % ctx),
        ]

def skip(cwd_cmd, to_skip):
    return [(cwd,cmd) for cwd, cmd in cwd_cmd if cwd not in to_skip]

tests = {
    'tut1': (gen('send'), gen('receive', java='Recv'), 'Hello World!'),
    'tut2': (gen('new_task', arg='%(arg)s'), gen('worker'), '%(arg)s'),
    'tut3': (gen('emit_log', arg='%(arg)s'), gen('receive_logs'), '%(arg)s'),
    'tut4': (skip(gen('emit_log_direct', arg='%(arg)s %(arg2)s'),
                  ['php']),
             skip(gen('receive_logs_direct', arg='%(arg)s'),
                  ['php']),
             '%(arg2)s'),
    'tut5': (skip(gen('emit_log_topic', arg='%(arg)s.foo %(arg2)s'),
                  ['php']),
             skip(gen('receive_logs_topic', arg='%(arg)s.*'),
                  ['php']),
             '%(arg2)s'),
    'tut6': (skip(gen('rpc_client', java='RPCClient', dotnet='RPCClient'),
                  ['erlang', 'clojure']),
             skip(gen('rpc_server', java='RPCServer', dotnet='RPCServer'),
                  ['erlang', 'clojure']),
             'fib[(]30[)]'),
    }

def tests_to_run():
    if os.environ.get('TUTORIALS'):
        return sorted(str.split(os.environ.get('TUTORIALS'), ","))
    else:
        return sorted(tests.keys())

errors = 0
ts     = tests_to_run()

print " [.] Running tests with SLOWNESS=%r" % (multiplier,)
print " [.] Will test %s" % (ts)
for test in ts:
    (send_progs, recv_progs, output_mask) = tests[test]
    for scwd, send_cmd in send_progs:
        for rcwd, recv_cmd in recv_progs:
            ctx = {
                'arg':  'rand_%s' % (random.randint(1,100),),
                'arg2': 'rand_%s' % (random.randint(1,100),),
                }
            rcmd = recv_cmd % ctx
            scmd = send_cmd % ctx
            mask = output_mask % ctx
            p = spawn(rcmd, cwd=rcwd)
            exit_code, sout = run(scmd, cwd=scwd)
            matched, rout = wait(p, mask)
            if matched and exit_code == 0:
                print " [+] %s %-30s ok" % (test, scwd+'/'+rcwd)
            else:
                print " [!] %s %-30s FAILED" % (test, scwd+'/'+rcwd)
                print " [!] %r exited with status %s, output:\n%s\n" % (scmd, exit_code,
                                                            sout.strip())
                print " [!] %r output:\n%s\n" % (rcmd, rout.strip())
                errors += 1

if errors:
    print " [!] %s tests failed" % (errors,)

sys.exit(errors)

########NEW FILE########
__FILENAME__ = travisci
#!/usr/bin/env python
import time
import random
import re
import subprocess
import signal
import sys
import os

multiplier = float(os.environ.get('SLOWNESS', 6))

def run(cmd, **kwargs):
    p = subprocess.Popen(cmd.split(),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         **kwargs)
    p.wait()
    out = p.stdout.read()
    err = p.stderr.read()

    # compensate for slow Clojure examples startup:
    # lein trampoline run + clojure.core recompilation
    if kwargs.get("cwd") == "clojure":
        x = 4
    else:
        x = 1
    time.sleep(0.2 * multiplier * x)
    return p.returncode, out + '\n' + err

def spawn(cmd, **kwargs):
    p = subprocess.Popen(cmd.split(),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         **kwargs)
    if kwargs.get("cwd") == "clojure":
        x = 4
    else:
        x = 1
    time.sleep(0.5 * multiplier * x)
    return p

def wait(p, match):
    os.kill(p.pid, signal.SIGINT)
    p.wait()
    out = p.stdout.read()
    err = p.stderr.read()
    return bool(re.search(match, out)), out + '\n' + err



def gen(prog, arg="", **kwargs):
    Prog = ''.join([w.capitalize() for w in prog.split('_')])
    ctx = {
        'prog': prog,
        'Prog': Prog,
        # clojure ns
        'ns': prog.replace("_", "-"),
        'arg': arg,
        'java': kwargs.get('java', Prog),
        'dotnet': kwargs.get('dotnet', Prog),
        'ruby': kwargs.get('ruby', os.environ.get('RUBY', 'ruby1.9.1')),
        }
    return [
        ('python', './venv/bin/python %(prog)s.py %(arg)s' % ctx),
        ('erlang', './%(prog)s.erl %(arg)s' % ctx),
        ('java', 'java -cp .:commons-io-1.2.jar:commons-cli-1.1.jar:'
             'rabbitmq-client.jar %(java)s %(arg)s' % ctx),
        ('clojure', './bin/lein trampoline run -m rabbitmq.tutorials.%(ns)s %(arg)s' % ctx),
        ('dotnet', 'env MONO_PATH=lib/bin mono %(dotnet)s.exe %(arg)s' % ctx),
        ('ruby', 'env RUBYOPT=-rubygems GEM_HOME=gems/gems RUBYLIB=gems/lib '
             '%(ruby)s %(prog)s.rb %(arg)s' % ctx),
        ('php', 'php %(prog)s.php %(arg)s' % ctx)
        ]

def skip(cwd_cmd, to_skip):
    return [(cwd,cmd) for cwd, cmd in cwd_cmd if cwd not in to_skip]

tests = {
    'tut1': (gen('send'), gen('receive', java='Recv'), 'Hello World!'),
    'tut2': (gen('new_task', arg='%(arg)s'), gen('worker'), '%(arg)s'),
    'tut3': (gen('emit_log', arg='%(arg)s'), gen('receive_logs'), '%(arg)s'),
    'tut4': (skip(gen('emit_log_direct', arg='%(arg)s %(arg2)s'),
                  ['php']),
             skip(gen('receive_logs_direct', arg='%(arg)s'),
                  ['php']),
             '%(arg2)s'),
    'tut5': (skip(gen('emit_log_topic', arg='%(arg)s.foo %(arg2)s'),
                  ['php']),
             skip(gen('receive_logs_topic', arg='%(arg)s.*'),
                  ['php']),
             '%(arg2)s'),
    'tut6': (skip(gen('rpc_client', java='RPCClient', dotnet='RPCClient'),
                  ['erlang', 'clojure']),
             skip(gen('rpc_server', java='RPCServer', dotnet='RPCServer'),
                  ['erlang', 'clojure']),
             'fib[(]30[)]'),
    }

def tests_to_run():
    if os.environ.get('TUTORIALS'):
        return sorted(str.split(os.environ.get('TUTORIALS'), ","))
    else:
        return sorted(tests.keys())

errors = 0
ts     = tests_to_run()

print " [.] Running tests with SLOWNESS=%r" % (multiplier,)
print " [.] Will test %s" % (ts)
for test in ts:
    (send_progs, recv_progs, output_mask) = tests[test]
    for scwd, send_cmd in send_progs:
        for rcwd, recv_cmd in recv_progs:
            ctx = {
                'arg':  'rand_%s' % (random.randint(1,100),),
                'arg2': 'rand_%s' % (random.randint(1,100),),
                }
            rcmd = recv_cmd % ctx
            scmd = send_cmd % ctx
            mask = output_mask % ctx
            p = spawn(rcmd, cwd=rcwd)
            exit_code, sout = run(scmd, cwd=scwd)
            matched, rout = wait(p, mask)
            if matched and exit_code == 0:
                print " [+] %s %-30s ok" % (test, scwd+'/'+rcwd)
            else:
                print " [!] %s %-30s FAILED" % (test, scwd+'/'+rcwd)
                print " [!] %r exited with status %s, output:\n%s\n" % (scmd, exit_code,
                                                            sout.strip())
                print " [!] %r output:\n%s\n" % (rcmd, rout.strip())
                errors += 1

if errors:
    print " [!] %s tests failed" % (errors,)

sys.exit(errors)

########NEW FILE########
