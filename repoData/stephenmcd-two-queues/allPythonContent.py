__FILENAME__ = bench
#!/usr/bin/env python

from os import mkdir
from os.path import join
from multiprocessing import cpu_count
from subprocess import Popen, check_output, PIPE
from sys import stdout


def popen_args(filename, *args):
    """
    Returns the initial popen args for a given Python or Go file.
    """
    args = [filename, "--quiet"] + list(args)
    if filename.split(".")[-1] == "py":
        return ["python"] + args
    else:
        return ["go", "run"] + list(args)


def run_clients(lang, *args):
    """
    Runs the test_client program for Python or Go, for the range
    from 1 to cpus * 2 as the number of clients, returning the
    median messsages per second for each.
    """
    if "--redis" not in args:
        broker = Popen(popen_args("run_broker.%s" % lang), stderr=PIPE)
    args = popen_args("test_client.%s" % lang, *args)
    results = []
    num_runs = cpu_count() * 2
    print " ".join(args)
    for clients in range(1, num_runs + 1):
        bar = ("#" * clients).ljust(num_runs)
        stdout.write("\r[%s] %s/%s " % (bar, clients, num_runs))
        stdout.flush()
        out = check_output(args + ["--num-clients=%s" % clients], stderr=PIPE)
        results.append(out.split(" ")[0].strip())
    stdout.write("\n")
    if "--redis" not in args:
        broker.kill()
    return results

# All test_client runs and their cli args.
runs = {
    "py_redis": ["py", "--redis", "--unbuffered"],
    "py_redis_buffered": ["py", "--redis"],
    "py_zmq": ["py"],
    "go_redis": ["go", "--redis"],
    "go_zmq": ["go"],
}

# Consistent graph colours defined for each of the runs.
colours = {
    "py_redis": "red",
    "py_redis_buffered": "green",
    "py_zmq": "blue",
    "go_redis": "violet",
    "go_zmq": "orange",
}

# Groups of runs mapped to each graph.
plots = {
    "two-queues-1": ["py_zmq", "py_redis"],
    "two-queues-2": ["py_zmq", "py_redis", "py_redis_buffered"],
    "two-queues-3": ["py_zmq", "py_redis", "py_redis_buffered",
                     "go_zmq", "go_redis"],
}

# Store all results in an output directory.
output_path = lambda s="": join("output", s)
try:
    mkdir(output_path())
except OSError:
    pass

# Store results from each test_client run into files.
for name, args in runs.items():
    with open(output_path(name + ".dat"), "w") as f:
        f.write("\n".join(run_clients(*args)))

# Generate graphs.
with open("plot.p", "r") as f:
    plotfile = f.read()
line = '"%s.dat" using ($0+1):1 with lines title "%s" lw 2 lt rgb "%s"'
for name, names in plots.items():
    name = output_path(name)
    with open(output_path(names[0] + ".dat"), "r") as f:
        clients = len(f.read().split())
    with open(name + ".p", "w") as f:
        lines = ", ".join([line % (l, l.replace("_", " "), colours[l])
                           for l in names])
        f.write(plotfile % {"name": name, "lines": lines, "clients": clients})
    Popen(["gnuplot", name + ".p"], stderr=PIPE)

########NEW FILE########
__FILENAME__ = buffered_redis

import thread
import threading
import time
import redis


class BufferedRedis(redis.Redis):
    """
    Wrapper for Redis pub-sub that uses a pipeline internally
    for buffering message publishing. A thread is run that
    periodically flushes the buffer pipeline.
    """

    def __init__(self, *args, **kwargs):
        super(BufferedRedis, self).__init__(*args, **kwargs)
        self.buffer = self.pipeline()
        self.lock = threading.Lock()
        thread.start_new_thread(self.flusher, ())

    def flusher(self):
        """
        Thread that periodically flushes the buffer pipeline.
        """
        while True:
            time.sleep(.2)
            with self.lock:
                self.buffer.execute()

    def publish(self, *args, **kwargs):
        """
        Overrides publish to use the buffer pipeline, flushing
        it when the defined buffer size is reached.
        """
        with self.lock:
            self.buffer.publish(*args, **kwargs)
            if len(self.buffer.command_stack) >= 1000:
                self.buffer.execute()

########NEW FILE########
__FILENAME__ = run_broker
#!/usr/bin/env python

import argparse
import zmq_pubsub

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    zmq_pubsub.serve(args.quiet)

########NEW FILE########
__FILENAME__ = test_client
#!/usr/bin/env python

import argparse
import multiprocessing
import random
import time

import redis

import buffered_redis
import zmq_pubsub


def new_client():
    """
    Returns a new pubsub client instance - either the Redis or ZeroMQ
    client, based on command-line arg.
    """
    if args.redis:
        if args.unbuffered:
            Client = redis.Redis
        else:
            Client = buffered_redis.BufferedRedis
    else:
        Client = zmq_pubsub.ZMQPubSub
    return Client(host=args.host)


def publisher():
    """
    Loops forever, publishing messages to random channels.
    """
    client = new_client()
    message = u"x" * args.message_size
    while True:
        client.publish(random.choice(channels), message)


def subscriber():
    """
    Subscribes to all channels, keeping a count of the number of
    messages received. Publishes and resets the total every second.
    """
    client = new_client()
    pubsub = client.pubsub()
    for channel in channels:
        pubsub.subscribe(channel)
    last = time.time()
    messages = 0
    for message in pubsub.listen():
        messages += 1
        now = time.time()
        if now - last > 1:
            if not args.quiet:
                print messages, "msg/sec"
            client.publish("metrics", str(messages))
            last = now
            messages = 0


def run_workers(target):
    """
    Creates processes * --num-clients, running the given target
    function for each.
    """
    for _ in range(args.num_clients):
        proc = multiprocessing.Process(target=target)
        proc.daemon = True
        proc.start()


def get_metrics():
    """
    Subscribes to the metrics channel and returns messages from
    it until --num-seconds has passed.
    """
    client = new_client().pubsub()
    client.subscribe("metrics")
    start = time.time()
    while time.time() - start <= args.num_seconds:
        message = client.listen().next()
        if message["type"] == "message":
            yield int(message["data"])


if __name__ == "__main__":

    # Set up and parse command-line args.
    global args, channels
    default_num_clients = multiprocessing.cpu_count() / 2
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--num-clients", type=int, default=default_num_clients)
    parser.add_argument("--num-seconds", type=int, default=10)
    parser.add_argument("--num-channels", type=int, default=50)
    parser.add_argument("--message-size", type=int, default=20)
    parser.add_argument("--redis", action="store_true")
    parser.add_argument("--unbuffered", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    channels = [str(i) for i in range(args.num_channels)]

    # Create publisher/subscriber workers, pausing to allow
    # publishers to hit full throttle
    run_workers(publisher)
    time.sleep(1)
    run_workers(subscriber)

    # Consume metrics until --num-seconds has passed, and display
    # the median value.
    metrics = sorted(get_metrics())
    print metrics[len(metrics) / 2], "median msg/sec"

########NEW FILE########
__FILENAME__ = zmq_pubsub

import time
import zmq


class ZMQPubSub(object):

    def __init__(self, host="127.0.0.1"):
        context = zmq.Context()
        self.pub = context.socket(zmq.PUSH)
        self.pub.connect("tcp://%s:%s" % (host, 5562))
        self.sub = context.socket(zmq.SUB)
        self.sub.connect("tcp://%s:%s" % (host, 5561))
        self.channels = set()

    def publish(self, channel, message):
        self.pub.send_unicode("%s %s" % (channel, message))

    def subscribe(self, channels):
        for channel in channels:
            self.channels.add(channel)
            self.sub.setsockopt(zmq.SUBSCRIBE, channel)

    def unsubscribe(self, channels):
        for channel in channels:
            self.channels.remove(channel)
            self.sub.setsockopt(zmq.UNSUBSCRIBE, channel)

    def pubsub(self):
        return self

    def listen(self):
        while True:
            channel, _, data = self.sub.recv().partition(" ")
            yield {"type": "message", "channel": channel, "data": data}


def serve(quiet):
    context = zmq.Context()
    receiver = context.socket(zmq.PULL)
    receiver.bind("tcp://*:%s" % 5562)
    sender = context.socket(zmq.PUB)
    sender.bind("tcp://*:%s" % 5561)
    last = time.time()
    messages = 0
    try:
        while True:
            sender.send(receiver.recv())
            if not quiet:
                messages += 1
                now = time.time()
                if now - last > 1:
                    print "%s msg/sec" % messages
                    last = now
                    messages = 0
    except (KeyboardInterrupt, SystemExit):
        pass

########NEW FILE########
