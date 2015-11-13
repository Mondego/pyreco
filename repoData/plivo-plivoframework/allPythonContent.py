__FILENAME__ = wavdump
import urllib2
import sys

url = sys.argv[1]
req = urllib2.Request(url)
handler = urllib2.urlopen(req)
buffer = handler.read()
sys.stdout.write(buffer)
sys.stdout.flush()

########NEW FILE########
__FILENAME__ = inbound_api
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger

if __name__ == '__main__':
    log = StdoutLogger()
    try:
        inbound_event_listener = InboundEventSocket('127.0.0.1', 8021, 'ClueCon', filter="ALL")
        try:
            inbound_event_listener.connect()
        except ConnectError, e:
            log.error("connect failed: %s" % str(e))
            raise SystemExit('exit')

        fs_api_string = "originate user/1000 &playback(/usr/local/freeswitch/sounds/en/us/callie/base256/8000/liberty.wav)"
        api_response = inbound_event_listener.api(fs_api_string)
        log.info(str(api_response))
        if not api_response.is_success():
            log.error("api failed with response %s" % api_response.get_response())
            raise SystemExit('exit')

        log.info("api success with response %s" % api_response.get_response())

    except (SystemExit, KeyboardInterrupt): pass

    log.info("exit")

########NEW FILE########
__FILENAME__ = inbound_api_notfound
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger

if __name__ == '__main__':
    log = StdoutLogger()
    try:
        inbound_event_listener = InboundEventSocket('127.0.0.1', 8021, 'ClueCon', filter="ALL")
        try:
            inbound_event_listener.connect()
        except ConnectError, e:
            log.error("connect failed: %s" % str(e))
            raise SystemExit('exit')

        api_response = inbound_event_listener.api("FALSECOMMAND")
        log.info(str(api_response))
        if not api_response.is_success():
            log.error("api failed with response %s" % api_response.get_response())
            raise SystemExit('exit')

        log.info("api success with response %s" % api_response.get_response())

    except (SystemExit, KeyboardInterrupt): pass

    log.info("exit")

########NEW FILE########
__FILENAME__ = inbound_autoreconnect
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

import gevent
from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger


class MyInboundEventSocket(InboundEventSocket):
    '''Inbound eventsocket connector that automatically reconnects
    when the freeswitch eventsocket module closed the connection
    '''
    def __init__(self, host, port, password, filter="ALL", pool_size=500, connect_timeout=5):
        InboundEventSocket.__init__(self, host, port, password, filter, pool_size, connect_timeout)
        self.log = StdoutLogger()

    def start(self):
        self.log.info("Start Inbound socket %s:%d with filter %s" \
            % (self.transport.host, self.transport.port, self._filter))
        while True:
            try:
                self.connect()
                self.log.info("Inbound socket connected")
                self.serve_forever()
            except ConnectError, e:
                self.log.error("ConnectError: %s" % str(e))
            except (SystemExit, KeyboardInterrupt):
                break
            self.log.error("Inbound socket closed, try to reconnect ...")
            gevent.sleep(1.0)
        self.log.info("Inbound socket terminated")


if __name__ == '__main__':
    c = MyInboundEventSocket('127.0.0.1', 8021, 'ClueCon')
    c.start()

########NEW FILE########
__FILENAME__ = inbound_bgapi
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger

if __name__ == '__main__':
    log = StdoutLogger()
    try:
        inbound_event_listener = InboundEventSocket('127.0.0.1', 8021, 'ClueCon', filter="BACKGROUND_JOB")
        try:
            inbound_event_listener.connect()
        except ConnectError, e:
            log.error("connect failed: %s" % str(e))
            raise SystemExit('exit')

        fs_bg_api_string = "originate user/1000 &playback(/usr/local/freeswitch/sounds/en/us/callie/base256/8000/liberty.wav)"
        bg_api_response = inbound_event_listener.bgapi(fs_bg_api_string)
        log.info(str(bg_api_response))
        log.info(bg_api_response.get_response())
        if not bg_api_response.is_success():
            log.error("bgapi failed !")
            raise SystemExit('exit')

        job_uuid = bg_api_response.get_job_uuid()
        if not job_uuid:
            log.error("bgapi jobuuid not found !")
            raise SystemExit('exit')

        log.info("bgapi success with Job-UUID " + job_uuid)

    except (SystemExit, KeyboardInterrupt): pass

    log.info("exit")

########NEW FILE########
__FILENAME__ = inbound_bgapi2
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger
import gevent.event


class MyEventSocket(InboundEventSocket):
    def __init__(self, host, port, password, filter, log=None):
        InboundEventSocket.__init__(self, host, port, password, filter)
        self.log = log
        self.jobqueue = gevent.event.AsyncResult()

    def on_background_job(self, ev):
        '''
        Recieves callbacks for BACKGROUND_JOB event.
        '''
        self.jobqueue.set(ev)

    def wait_background_job(self):
        '''
        Waits until BACKGROUND_JOB event was caught and returns Event.
        '''
        return self.jobqueue.get()



if __name__ == '__main__':
    log = StdoutLogger()
    try:
        inbound_event_listener = MyEventSocket('127.0.0.1', 8021, 'ClueCon', filter="BACKGROUND_JOB", log=log)
        try:
            inbound_event_listener.connect()
        except ConnectError, e:
            log.error("connect failed: %s" % str(e))
            raise SystemExit('exit')

        fs_bg_api_string = "originate user/1000 &playback(/usr/local/freeswitch/sounds/en/us/callie/base256/8000/liberty.wav)"
        bg_api_response = inbound_event_listener.bgapi(fs_bg_api_string)
        log.info(str(bg_api_response))
        log.info(bg_api_response.get_response())
        if not bg_api_response.is_success():
            log.error("bgapi failed !")
            raise SystemExit('exit')

        job_uuid = bg_api_response.get_job_uuid()
        log.info("bgapi success with Job-UUID " + job_uuid)
        log.info("waiting background job ...")
        ev = inbound_event_listener.wait_background_job()
        log.info("background job: %s" % str(ev))


    except (SystemExit, KeyboardInterrupt): pass

    log.info("exit")

########NEW FILE########
__FILENAME__ = inbound_concurrent_bgapi
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger
import gevent.event



CONTACTS = (
            '{originate_timeout=20}sofia/internal/hansolo@star.war',
            '{originate_timeout=20}sofia/internal/luke@star.war',
            '{originate_timeout=20}sofia/internal/anakin@star.war',
            '{originate_timeout=20}sofia/internal/palpatine@star.war',
            '{originate_timeout=20}sofia/internal/c3po@star.war',
            '{originate_timeout=20}sofia/internal/r2d2@star.war',
            '{originate_timeout=20}sofia/internal/chewbacca@star.war',
            '{originate_timeout=20}sofia/internal/leia@star.war',
            '{originate_timeout=20}sofia/internal/padme@star.war',
            '{originate_timeout=20}sofia/internal/yoda@star.war',
            '{originate_timeout=20}sofia/internal/obiwan@star.war',
           )


class MyEventSocket(InboundEventSocket):
    def __init__(self, host, port, password, filter="ALL", log=None):
        self.log = log
        self.jobs = {}
        InboundEventSocket.__init__(self, host, port, password, filter)

    def track_job(self, job_uuid):
        self.jobs[job_uuid] = gevent.event.AsyncResult()

    def untrack_job(self, job_uuid):
        try:
            del self.jobs[job_uuid]
        except:
            pass

    def on_background_job(self, ev):
        '''
        Receives callbacks for BACKGROUND_JOB event.
        '''
        job_uuid = ev['Job-UUID']
        job_cmd = ev['Job-Command']
        job_arg = ev['Job-Command-Arg']
        self.log.debug("%s %s, args %s => %s" % (job_uuid, job_cmd, job_arg, ev.get_body()))
        try:
            async_result = self.jobs[job_uuid]
            async_result.set(ev)
        except KeyError:
            # job is not tracked
            return

    def wait_for_job(self, job_uuid):
        '''
        Waits until BACKGROUND_JOB event was caught and returns Event.
        '''
        try:
            async_result = self.jobs[job_uuid]
            return async_result.wait()
        except KeyError:
            # job is not tracked
            return None


def spawn_originate(inbound_event_listener, contact, log):
    fs_bg_api_string = \
        "originate %s &playback(/usr/local/freeswitch/sounds/en/us/callie/base256/8000/liberty.wav)" \
        % contact
    bg_api_response = inbound_event_listener.bgapi(fs_bg_api_string)
    log.info(str(bg_api_response))
    job_uuid = bg_api_response.get_job_uuid()
    if not job_uuid:
        log.error("bgapi %s: job uuid not found" % fs_bg_api_string)
        return
    inbound_event_listener.track_job(job_uuid)
    log.info("bgapi %s => Job-UUID %s" % (fs_bg_api_string, job_uuid))
    log.info("waiting job %s ..." % job_uuid)
    ev = inbound_event_listener.wait_for_job(job_uuid)

    log.info("bgapi %s => %s" % (fs_bg_api_string, str(ev.get_body())))


if __name__ == '__main__':
    log = StdoutLogger()
    try:
        inbound_event_listener = MyEventSocket('127.0.0.1', 8021, 'ClueCon', filter="BACKGROUND_JOB", log=log)
        try:
            inbound_event_listener.connect()
        except ConnectError, e:
            log.error("connect failed: %s" % str(e))
            raise SystemExit('exit')
        if not CONTACTS:
            log.error("No CONTACTS !")
            raise SystemExit('exit')
        pool = gevent.pool.Pool(len(CONTACTS))
        for contact in CONTACTS:
            pool.spawn(spawn_originate, inbound_event_listener, contact, log)
        pool.join()
        log.debug("all originate commands done")
    except (SystemExit, KeyboardInterrupt):
        pass
    log.info("exit")

########NEW FILE########
__FILENAME__ = inbound_concurrent_dialer_server
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger

import gevent
from gevent import wsgi


CONTACTS = (
            '{originate_timeout=20}user/1000 &playback(/usr/local/freeswitch/sounds/en/us/callie/base256/8000/liberty.wav)',
            '{originate_timeout=20}user/1000 &playback(/usr/local/freeswitch/sounds/en/us/callie/base256/8000/liberty.wav)',
            '{originate_timeout=20}user/1000 &playback(/usr/local/freeswitch/sounds/en/us/callie/base256/8000/liberty.wav)',
           )


class MyEventSocket(InboundEventSocket):
    def __init__(self, host, port, password, filter="ALL", log=None):
        InboundEventSocket.__init__(self, host, port, password, filter)
        self.log = log


    def on_background_job(self, ev):
        '''
        Receives callbacks for BACKGROUND_JOB event.
        '''
        job_uuid = ev['Job-UUID']
        job_cmd = ev['Job-Command']
        job_arg = ev['Job-Command-Arg']
        self.log.debug("BackGround JOB Recieved" )
        self.log.debug("%s %s, args %s \n\n" % (job_uuid, job_cmd, job_arg))


    def on_channel_hangup(self, ev):
        '''
        Receives callbacks for BACKGROUND_JOB event.
        '''
        job_uuid = ev['Job-UUID']
        job_cmd = ev['Job-Command']
        job_arg = ev['Job-Command-Arg']
        self.log.debug("Channel Hangup" )
        self.log.debug("%s %s, args %s \n\n " % (job_uuid, job_cmd, job_arg))


def spawn_originate(inbound_event_listener, contact, log):
    log.info("Originate command")
    fs_bg_api_string = \
        "originate %s &playback(/usr/local/freeswitch/sounds/en/us/callie/base256/8000/liberty.wav)" \
        % contact
    bg_api_response = inbound_event_listener.bgapi(fs_bg_api_string)
    log.info(str(bg_api_response))
    job_uuid = bg_api_response.get_job_uuid()
    if not job_uuid:
        log.error("bgapi %s: job uuid not found \n\n" % fs_bg_api_string)
        return

    log.info("bgapi %s => Job-UUID %s \n\n" % (fs_bg_api_string, job_uuid))


def dispatch_requests(env, start_response):
    if env['PATH_INFO'] == '/':
        if CONTACTS:
            start_response('200 OK', [('Content-Type', 'text/html')])

            #Put logic to handle the request each time
            pool = gevent.pool.Pool(len(CONTACTS))
            jobs = [pool.spawn(spawn_originate, inbound_event_listener, contact, log) for contact in CONTACTS]
            gevent.joinall(jobs)
            log.debug("All originate commands done")

            return ["<b>Executed Request</b>"]

    start_response('404 Not Found', [('Content-Type', 'text/html')])
    return ['<h1>Wrong Usage - Command Not found</h1>']


if __name__ == '__main__':
    log = StdoutLogger()
    #Connect to freeswitch ESL in inbound mode
    inbound_event_listener = MyEventSocket('127.0.0.1', 8021, 'ClueCon', filter="ALL", log=log)
    try:
        inbound_event_listener.connect()
    except ConnectError, e:
        log.error("connect failed: %s" % str(e))
        raise SystemExit('exit')

    #Connect to freeswitch ESL in inbound mode
    wsgi.WSGIServer(('', 8088), dispatch_requests).serve_forever()

########NEW FILE########
__FILENAME__ = inbound_connectfailure
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

import traceback
from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.utils.logger import StdoutLogger

if __name__ == '__main__':
    log = StdoutLogger()

    log.info('#'*60)
    log.info("Connect with bad host")
    try:
        inbound_event_listener = InboundEventSocket('falsehost', 8021, 'ClueCon')
        inbound_event_listener.connect()
    except:
        [ log.info(line) for line in traceback.format_exc().splitlines() ]
    log.info('#'*60 + '\n')

    log.info('#'*60)
    log.info("Connect with bad port")
    try:
        inbound_event_listener = InboundEventSocket('127.0.0.1', 9999999, 'ClueCon')
        inbound_event_listener.connect()
    except:
        [ log.info(line) for line in traceback.format_exc().splitlines() ]
    log.info('#'*60 + '\n')

    log.info('#'*60)
    log.info("Connect with bad password")
    try:
        inbound_event_listener = InboundEventSocket('127.0.0.1', 8021, 'falsepassword')
        inbound_event_listener.connect()
    except:
        [ log.info(line) for line in traceback.format_exc().splitlines() ]
    log.info('#'*60 + '\n')

    log.info('exit')

########NEW FILE########
__FILENAME__ = inbound_filter
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger

if __name__ == '__main__':
    log = StdoutLogger()
    try:
        inbound_event_listener = InboundEventSocket('127.0.0.1', 8021, 'ClueCon', filter="ALL")
        try:
            inbound_event_listener.connect()
        except ConnectError, e:
            log.error("connect failed: %s" % str(e))
            raise SystemExit('exit')

        filter_response = inbound_event_listener.filter("Event-Name CHANNEL_ANSWER")
        log.info(str(filter_response))
        if not filter_response.is_success():
            log.error("filter failed with response %s" % filter_response.get_response())
            raise SystemExit('exit')

        log.info("filter success with response %s" % filter_response.get_response())

    except (SystemExit, KeyboardInterrupt): pass

    log.info("exit")

########NEW FILE########
__FILENAME__ = inbound_stop
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger

if __name__ == '__main__':
    log = StdoutLogger()
    try:
        inbound_event_listener = InboundEventSocket('127.0.0.1', 8021, 'ClueCon', filter="ALL")
        try:
            inbound_event_listener.connect()
        except ConnectError, e:
            log.error("connect failed: %s" % str(e))
            raise SystemExit('exit')

        log.info("stopping now !")
        inbound_event_listener.disconnect()

    except (SystemExit, KeyboardInterrupt): pass

    log.info("exit")

########NEW FILE########
__FILENAME__ = inbound_stop_spawned
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.errors import ConnectError
from plivo.utils.logger import StdoutLogger
import gevent

def stop(inbound_event_listener, log):
    log.info("stopping now !")
    inbound_event_listener.disconnect()
    log.info("stopped !")

if __name__ == '__main__':
    log = StdoutLogger()
    try:
        inbound_event_listener = InboundEventSocket('127.0.0.1', 8021, 'ClueCon', filter="ALL")
        try:
            inbound_event_listener.connect()
        except ConnectError, e:
            log.error("connect failed: %s" % str(e))
            raise SystemExit('exit')

        log.info("stopping in 5 seconds !")
        gevent.spawn_later(5, stop, inbound_event_listener, log)

        inbound_event_listener.serve_forever()

    except (SystemExit, KeyboardInterrupt): pass

    log.info("exit")

########NEW FILE########
__FILENAME__ = outbound_async_server_test
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Outbound server example in async mode full .
"""

from plivo.core.freeswitch.outboundsocket import OutboundEventSocket, OutboundServer
from plivo.utils.logger import StdoutLogger
import gevent.queue
import gevent


class AsyncOutboundEventSocket(OutboundEventSocket):
    def __init__(self, socket, address, log, filter=None):
        self.log = log
        self._action_queue = gevent.queue.Queue()
        OutboundEventSocket.__init__(self, socket, address, filter)

    def _protocol_send(self, command, args=""):
        self.log.info("[%s] args='%s'" % (command, args))
        response = super(AsyncOutboundEventSocket, self)._protocol_send(command, args)
        self.log.info(str(response))
        return response

    def _protocol_sendmsg(self, name, args=None, uuid="", lock=False, loops=1):
        self.log.info("[%s] args=%s, uuid='%s', lock=%s, loops=%d" \
                      % (name, str(args), uuid, str(lock), loops))
        response = super(AsyncOutboundEventSocket, self)._protocol_sendmsg(name, args, uuid, lock, loops)
        self.log.info(str(response))
        return response

    def on_channel_execute_complete(self, event):
        if event.get_header('Application') == 'playback':
            self._action_queue.put(event)

    def on_channel_answer(self, event):
        self._action_queue.put(event)

    def run(self):
        self.connect()
        self.log.info("Channel Unique ID => %s" % self.get_channel_unique_id())
        # only catch events for this channel
        self.myevents()
        # answer channel
        self.answer()
        self.log.info("Wait answer")
        gevent.sleep(1) # sleep 1 sec: sometimes sound is truncated after answer
        self.log.info("Channel answered")

        # play file
        self.playback("/usr/local/freeswitch/sounds/en/us/callie/ivr/8000/ivr-hello.wav", terminators="*")
        # wait until playback is done
        self.log.info("Waiting end of playback ...")
        event = self._action_queue.get()
        # log playback execute response
        self.log.info("Playback done (%s)" % str(event.get_header('Application-Response')))
        # finally hangup
        self.hangup()


class AsyncOutboundServer(OutboundServer):
    def __init__(self, address, handle_class, filter=None):
        self.log = StdoutLogger()
        self.log.info("Start server %s ..." % str(address))
        OutboundServer.__init__(self, address, handle_class, filter)

    def handle_request(self, socket, address):
        self.log.info("New request from %s" % str(address))
        self._requestClass(socket, address, self.log, self._filter)
        self.log.info("End request from %s" % str(address))



if __name__ == '__main__':
    outboundserver = AsyncOutboundServer(('127.0.0.1', 8084), AsyncOutboundEventSocket)
    outboundserver.serve_forever()

########NEW FILE########
__FILENAME__ = outbound_sync_server_test
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Outbound server example in sync mode full .
"""

from plivo.core.freeswitch.outboundsocket import OutboundEventSocket, OutboundServer
from plivo.utils.logger import StdoutLogger
import gevent.queue


class SyncOutboundEventSocket(OutboundEventSocket):
    def __init__(self, socket, address, log, filter=None):
        self.log = log
        self._action_queue = gevent.queue.Queue()
        OutboundEventSocket.__init__(self, socket, address, filter)

    def _protocol_send(self, command, args=""):
        self.log.info("[%s] args='%s'" % (command, args))
        response = super(SyncOutboundEventSocket, self)._protocol_send(command, args)
        self.log.info(str(response))
        return response

    def _protocol_sendmsg(self, name, args=None, uuid="", lock=False, loops=1):
        self.log.info("[%s] args=%s, uuid='%s', lock=%s, loops=%d" \
                      % (name, str(args), uuid, str(lock), loops))
        response = super(SyncOutboundEventSocket, self)._protocol_sendmsg(name, args, uuid, lock, loops)
        self.log.info(str(response))
        return response

    def on_channel_execute_complete(self, event):
        if event.get_header('Application') == 'playback':
            self.log.info("Playback done (%s)" % str(event.get_header('Application-Response')))

    def on_channel_answer(self, event):
        self._action_queue.put(event)

    def run(self):
        self.connect()
        self.log.info("Channel Unique ID => %s" % self.get_channel_unique_id())
        # only catch events for this channel
        self.myevents()
        # answer channel
        self.answer()
        self.log.info("Wait answer")
        event = self._action_queue.get()
        gevent.sleep(1) # sleep 1 sec: sometimes sound is truncated after answer
        self.log.info("Channel answered")

        # play file
        self.playback("/usr/local/freeswitch/sounds/en/us/callie/ivr/8000/ivr-hello.wav", terminators="*")
        # finally hangup
        self.hangup()


class SyncOutboundServer(OutboundServer):
    def __init__(self, address, handle_class, filter=None):
        self.log = StdoutLogger()
        self.log.info("Start server %s ..." % str(address))
        OutboundServer.__init__(self, address, handle_class, filter)

    def handle_request(self, socket, address):
        self.log.info("New request from %s" % str(address))
        self._requestClass(socket, address, self.log, filter=self._filter)
        self.log.info("End request from %s" % str(address))



if __name__ == '__main__':
    outboundserver = SyncOutboundServer(('127.0.0.1', 8084), SyncOutboundEventSocket)
    outboundserver.serve_forever()

########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Exceptions classes
"""

class LimitExceededError(Exception):
    '''Exception class when MAXLINES_PER_EVENT is reached'''
    pass


class ConnectError(Exception):
    '''Exception class for connection'''
    pass

########NEW FILE########
__FILENAME__ = commands
# -*- coding: utf-8 -*-
# Initial code for this file derived from eventsocket project - (https://github.com/fiorix/eventsocket),
# which is distributed under the Mozilla Public License Version 1.1

"""
FreeSWITCH Commands class

Please refer to http://wiki.freeswitch.org/wiki/Mod_event_socket#Command_documentation
"""


class Commands(object):
    def api(self, args):
        "Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#api"
        return self._protocol_send("api", args)

    def bgapi(self, args):
        "Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#bgapi"
        return self._protocol_send("bgapi", args)

    def exit(self):
        "Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#exit"
        return self._protocol_send("exit")

    def resume(self):
        """Socket resume for Outbound connection only.

        If enabled, the dialplan will resume execution with the next action

        after the call to the socket application.

        If there is a bridge active when the disconnect happens, it is killed.
        """
        return self._protocol_send("resume")

    def eventplain(self, args):
        "Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#event"
        return self._protocol_send('event plain', args)

    def eventjson(self, args):
        "Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#event"
        return self._protocol_send('event json', args)

    def event(self, args):
        "Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#event"
        return self._protocol_send("event", args)

    def execute(self, command, args='', uuid='', lock=True):
        return self._protocol_sendmsg(command, args, uuid, lock)

    def get_var(self, var, uuid=""):
        """
        Please refer to http://wiki.freeswitch.org/wiki/Mod_commands#uuid_getvar

        For Inbound connection, uuid argument is mandatory.
        """
        if not uuid:
            try:
                uuid = self.get_channel_unique_id()
            except AttributeError:
                uuid = None
        if not uuid:
            return None
        api_response = self.api("uuid_getvar %s %s" % (uuid, var))
        result = api_response.get_body().strip()
        if result == '_undef_' or result[:4] == '-ERR':
            result = None
        return result

    def set_var(self, var, value, uuid=""):
        """
        Please refer to http://wiki.freeswitch.org/wiki/Mod_commands#uuid_setvar

        For Inbound connection, uuid argument is mandatory.
        """
        if not value:
            value = ''
        if not uuid:
            try:
                uuid = self.get_channel_unique_id()
            except AttributeError:
                uuid = None
        if not uuid:
            return None
        api_response = self.api("uuid_setvar %s %s %s" % (uuid, var, str(value)))
        result = api_response.get_body()
        if not result == '_undef_' or result[:4] == '-ERR':
            result = ''
        result = result.strip()
        return result

    def filter(self, args):
        """Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#filter

        The user might pass any number of values to filter an event for. But, from the point
        filter() is used, just the filtered events will come to the app - this is where this
        function differs from event().

        >>> filter('Event-Name MYEVENT')
        >>> filter('Unique-ID 4f37c5eb-1937-45c6-b808-6fba2ffadb63')
        """
        return self._protocol_send('filter', args)

    def filter_delete(self, args):
        """Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#filter_delete

        >>> filter_delete('Event-Name MYEVENT')
        """
        return self._protocol_send('filter delete', args)

    def divert_events(self, flag):
        """Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#divert_events

        >>> divert_events("off")
        >>> divert_events("on")
        """
        return self._protocol_send('divert_events', flag)

    def sendevent(self, args):
        """Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#sendevent

        >>> sendevent("CUSTOM\nEvent-Name: CUSTOM\nEvent-Subclass: myevent::test\n")

        This example will send event :
          Event-Subclass: myevent%3A%3Atest
          Command: sendevent%20CUSTOM
          Event-Name: CUSTOM
        """
        return self._protocol_send('sendevent', args)

    def auth(self, args):
        """Please refer to http://wiki.freeswitch.org/wiki/Event_Socket#auth

        This method is only used for Inbound connections.
        """
        return self._protocol_send("auth", args)

    def myevents(self, uuid=""):
        """For Inbound connection, please refer to http://wiki.freeswitch.org/wiki/Event_Socket#Special_Case_-_.27myevents.27

        For Outbound connection, please refer to http://wiki.freeswitch.org/wiki/Event_Socket_Outbound#Events

        >>> myevents()

        For Inbound connection, uuid argument is mandatory.
        """
        if self._is_eventjson:
            return self._protocol_send("myevents json", uuid)
        else:
            return self._protocol_send("myevents", uuid)

    def linger(self):
        """Tell Freeswitch to wait for the last channel event before ending the connection

        Can only be used with Outbound connection.

        >>> linger()

        """
        return self._protocol_send("linger")

    def verbose_events(self, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_verbose_events

        >>> verbose_events()

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("verbose_events", "", uuid, lock)

    def answer(self, uuid="", lock=True):
        """
        Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_answer

        >>> answer()

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("answer", "", uuid, lock)

    def bridge(self, args, uuid="", lock=True):
        """
        Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_bridge

        >>> bridge("{ignore_early_media=true}sofia/gateway/myGW/177808")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("bridge", args, uuid, lock)

    def hangup(self, cause="", uuid="", lock=True):
        """Hangup call.

        Hangup `cause` list : http://wiki.freeswitch.org/wiki/Hangup_Causes (Enumeration column)

        >>> hangup()

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("hangup", cause, uuid, lock)

    def ring_ready(self, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_ring_ready

        >>> ring_ready()

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("ring_ready", "", uuid)

    def record_session(self, filename, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_record_session

        >>> record_session("/tmp/dump.gsm")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("record_session", filename, uuid, lock)

    def bind_meta_app(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_bind_meta_app

        >>> bind_meta_app("2 ab s record_session::/tmp/dump.gsm")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("bind_meta_app", args, uuid, lock)

    def bind_digit_action(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_bind_digit_action

        >>> bind_digit_action("test1,456,exec:playback,ivr/ivr-welcome_to_freeswitch.wav")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("bind_digit_action", args, uuid, lock)

    def digit_action_set_realm(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_digit_action_set_realm

        >>> digit_action_set_realm("test1")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("digit_action_set_realm", args, uuid, lock)

    def clear_digit_action(self, args, uuid="", lock=True):
        """
        >>> clear_digit_action("test1")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("clear_digit_action", args, uuid, lock)

    def wait_for_silence(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_wait_for_silence

        >>> wait_for_silence("200 15 10 5000")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("wait_for_silence", args, uuid, lock)

    def sleep(self, milliseconds, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_sleep

        >>> sleep(5000)
        >>> sleep("5000")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("sleep", milliseconds, uuid, lock)

    def vmd(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Mod_vmd

        >>> vmd("start")
        >>> vmd("stop")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("vmd", args, uuid, lock)

    def set(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_set

        >>> set("ringback=${us-ring}")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("set", args, uuid, lock)

    def set_global(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_set_global

        >>> set_global("global_var=value")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("set_global", args, uuid, lock)

    def unset(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_unset

        >>> unset("ringback")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("unset", args, uuid, lock)

    def start_dtmf(self, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_start_dtmf

        >>> start_dtmf()

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("start_dtmf", "", uuid, lock)

    def stop_dtmf(self, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_stop_dtmf

        >>> stop_dtmf()

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("stop_dtmf", "", uuid, lock)

    def start_dtmf_generate(self, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_start_dtmf_generate

        >>> start_dtmf_generate()

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("start_dtmf_generate", "true", uuid, lock)

    def stop_dtmf_generate(self, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_stop_dtmf_generate

        >>> stop_dtmf_generate()

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("stop_dtmf_generate", "", uuid, lock)

    def queue_dtmf(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_queue_dtmf

        Enqueue each received dtmf, that'll be sent once the call is bridged.

        >>> queue_dtmf("0123456789")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("queue_dtmf", args, uuid, lock)

    def flush_dtmf(self, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_flush_dtmf

        >>> flush_dtmf()

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("flush_dtmf", "", uuid, lock)

    def play_fsv(self, filename, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Mod_fsv

        >>> play_fsv("/tmp/video.fsv")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("play_fsv", filename, uuid, lock)

    def record_fsv(self, filename, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Mod_fsv

        >>> record_fsv("/tmp/video.fsv")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("record_fsv", filename, uuid, lock)

    def playback(self, filename, terminators=None, uuid="", lock=True, loops=1):
        """Please refer to http://wiki.freeswitch.org/wiki/Mod_playback

        The optional argument `terminators` may contain a string with
        the characters that will terminate the playback.

        >>> playback("/tmp/dump.gsm", terminators="#8")

        In this case, the audio playback is automatically terminated
        by pressing either '#' or '8'.

        For Inbound connection, uuid argument is mandatory.
        """
        if not terminators:
            self.set("playback_terminators=%s" % terminators, uuid)
        return self._protocol_sendmsg("playback", filename, uuid, lock, loops)

    def transfer(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_transfer

        >>> transfer("3222 XML default")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("transfer", args, uuid, lock)

    def att_xfer(self, url, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_att_xfer

        >>> att_xfer("user/1001")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("att_xfer", url, uuid, lock)

    def endless_playback(self, filename, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_endless_playback

        >>> endless_playback("/tmp/dump.gsm")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("endless_playback", filename, uuid, lock)

    def record(self, filename, time_limit_secs="", silence_thresh="", \
                silence_hits="", terminators=None, uuid="", lock=True, loops=1):
        """
        Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_record

        """
        if terminators:
            self.set("playback_terminators=%s" % terminators)
        args = "%s %s %s %s" %(filename, time_limit_secs, silence_thresh, silence_hits)
        self._protocol_sendmsg("record", args=args, uuid=uuid, lock=True)

    def play_and_get_digits(self, min_digits=1, max_digits=1, max_tries=1, timeout=5000, \
                            terminators='', sound_files=[], invalid_file = "", var_name='pagd_input', \
                            valid_digits='0123456789*#', digit_timeout=None, play_beep=False):
        """
        Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_play_and_get_digits
        """
        if not sound_files:
            if play_beep:
                play_str = 'tone_stream://%(300,200,700)'
            else:
                play_str = 'silence_stream://10'
        else:
            self.set("playback_delimiter=!")
            play_str = "file_string://silence_stream://1"
            for sound_file in sound_files:
                play_str = "%s!%s" % (play_str, sound_file)
            if play_beep:
                beep = 'tone_stream://%(300,200,700)'
                play_str = "%s!%s" % (play_str, beep)

        if not invalid_file:
            invalid_file='silence_stream://150'
        if digit_timeout is None:
            digit_timeout = timeout
        reg = []
        for d in valid_digits:
            if d == '*':
                d = '\*'
            reg.append(d)
        regexp = '|'.join(reg)
        regexp = '^(%s)+' % regexp

        play_str = play_str.replace("'", "\\'")

        args = "%d %d %d %d '%s' '%s' %s %s %s %d" % (min_digits, max_digits, max_tries, \
                                                    timeout, terminators, play_str,
                                                    invalid_file, var_name, regexp,
                                                    digit_timeout)
        self.execute('play_and_get_digits', args)

    def preanswer(self):
        """
        Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_pre_answer

        Can only be used for outbound connection
        """
        self.execute("pre_answer")

    def conference(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Mod_conference

        >>> conference(args)

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("conference", args, uuid, lock)

    def speak(self, text, uuid="", lock=True, loops=1):
        """Please refer to http://wiki.freeswitch.org/wiki/TTS

        >>> "set" data="tts_engine=flite"
        >>> "set" data="tts_voice=kal"
        >>> speak(text)

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("speak", text, uuid, lock, loops)

    def hupall(self, args):
        "Please refer to http://wiki.freeswitch.org/wiki/Mod_commands#hupall"
        return self._protocol_sendmsg("hupall", args, uuid='', lock=True)

    def say(self, args, uuid="", lock=True, loops=1):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_say

        >>> say(en number pronounced 12345)

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("say", args, uuid, lock)

    def sched_hangup(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_sched_hangup

        >>> sched_hangup("+60 ALLOTTED_TIMEOUT")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("sched_hangup", args, uuid, lock)

    def sched_transfer(self, args, uuid="", lock=True):
        """Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_sched_transfer

        >>> sched_transfer("+60 9999 XML default")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("sched_transfer", args, uuid, lock)

    def redirect(self, args, uuid="", lock=True):
        """
        Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_redirect

        >>> redirect("sip:foo@bar.com")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("redirect", args, uuid, lock)

    def deflect(self, args, uuid="", lock=True):
        """
        Please refer to http://wiki.freeswitch.org/wiki/Misc._Dialplan_Tools_deflect

        >>> deflect("sip:foo@bar.com")

        For Inbound connection, uuid argument is mandatory.
        """
        return self._protocol_sendmsg("deflect", args, uuid, lock)

########NEW FILE########
__FILENAME__ = eventsocket
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Event Socket class
"""

from uuid import uuid1

import gevent
import gevent.event
import gevent.socket as socket
from gevent.coros import RLock
import gevent.pool
from gevent import GreenletExit

from plivo.core.freeswitch.commands import Commands
from plivo.core.freeswitch.eventtypes import Event, CommandResponse, ApiResponse, BgapiResponse, JsonEvent
from plivo.core.errors import LimitExceededError, ConnectError


EOL = "\n"
MAXLINES_PER_EVENT = 1000



class InternalSyncError(Exception):
    pass


class EventSocket(Commands):
    '''EventSocket class'''
    def __init__(self, filter="ALL", eventjson=True, pool_size=5000, trace=False):
        self._is_eventjson = eventjson
        # Callbacks for reading events and sending responses.
        self._response_callbacks = {'api/response':self._api_response,
                                    'command/reply':self._command_reply,
                                    'text/disconnect-notice':self._disconnect_notice,
                                    'text/event-json':self._event_json,
                                    'text/event-plain':self._event_plain
                                   }
        # Closing state flag
        self._closing_state = False
        # Default event filter.
        self._filter = filter
        # Commands pool list
        self._commands_pool = []
        # Lock to force eventsocket commands to be sequential.
        self._lock = RLock()
        # Sets connected to False.
        self.connected = False
        # Sets greenlet handler to None
        self._g_handler = None
        # Build events callbacks dict
        self._event_callbacks = {}
        for meth in dir(self):
            if meth[:3] == 'on_':
                event_name = meth[3:].upper()
                func = getattr(self, meth, None)
                if func:
                    self._event_callbacks[event_name] = func
        unbound = getattr(self, 'unbound_event', None)
        self._event_callbacks['unbound_event'] = unbound
        # Set greenlet spawner
        if pool_size > 0:
            self.pool = gevent.pool.Pool(pool_size)
            self._spawn = self.pool.spawn
        else:
            self._spawn = gevent.spawn_raw
        # set tracer
        try:
            logger = self.log
        except AttributeError:
            logger = None
        if logger and trace is True:
            self.trace = self._trace
        else:
            self.trace = self._notrace

    def _trace(self, msg):
        self.log.debug("[TRACE] %s" % str(msg))

    def _notrace(self, msg):
        pass

    def is_connected(self):
        '''
        Checks if connected and authenticated to eventsocket.

        Returns True or False.
        '''
        return self.connected

    def start_event_handler(self):
        '''
        Starts Event handler in background.
        '''
        self._g_handler = gevent.spawn(self.handle_events)

    def stop_event_handler(self):
        '''
        Stops Event handler.
        '''
        if self._g_handler and not self._g_handler.ready():
            self._g_handler.kill()

    def handle_events(self):
        '''
        Gets and Dispatches events in an endless loop using gevent spawn.
        '''
        self.trace("handle_events started")
        while True:
            # Gets event and dispatches to handler.
            try:
                self.get_event()
                gevent.sleep(0)
                if not self.connected:
                    self.trace("Not connected !")
                    break
            except LimitExceededError:
                break
            except ConnectError:
                break
            except socket.error, se:
                break
            except GreenletExit, e:
                break
            except Exception, ex:
                self.trace("handle_events error => %s" % str(ex))
        self.trace("handle_events stopped now")

        try: 
            self.trace("handle_events socket.close")
            self.transport.sockfd.close()
            self.trace("handle_events socket.close success")
        except Exception, e:
            self.trace("handle_eventssocket.close ERROR: %s" % e)

        self.connected = False
        # prevent any pending request to be stuck
        self._flush_commands()
        return

    def read_event(self):
        '''
        Reads one Event from socket until EOL.

        Returns Event instance.

        Raises LimitExceededError if MAXLINES_PER_EVENT is reached.
        '''
        buff = ''
        for x in range(MAXLINES_PER_EVENT):
            line = self.transport.read_line()
            if line == '':
                self.trace("no more data in read_event !")
                raise ConnectError("connection closed")
            elif line == EOL:
                # When matches EOL, creates Event and returns it.
                return Event(buff)
            else:
                # Else appends line to current buffer.
                buff = "%s%s" % (buff, line)
        raise LimitExceededError("max lines per event (%d) reached" % MAXLINES_PER_EVENT)

    def read_raw(self, event):
        '''
        Reads raw data based on Event Content-Length.

        Returns raw string or None if not found.
        '''
        length = event.get_content_length()
        # Reads length bytes if length > 0
        if length:
            res = self.transport.read(int(length))
            if not res or len(res) != int(length):
                raise ConnectError("no more data in read_raw !")
            return res
        return None

    def read_raw_response(self, event, raw):
        '''
        Extracts raw response from raw buffer and length based on Event Content-Length.

        Returns raw string or None if not found.
        '''
        length = event.get_content_length()
        if length:
            return raw[-length:]
        return None

    def get_event(self):
        '''
        Gets complete Event, and processes response callback.
        '''
        self.trace("read_event")
        event = self.read_event()
        self.trace("read_event done")
        # Gets callback response for this event
        try:
            func = self._response_callbacks[event.get_content_type()]
        except KeyError:
            self.trace("no callback for %s" % str(event))
            return
        self.trace("callback %s" % str(func))
        # If callback response found, starts this method to get final event.
        event = func(event)
        self.trace("callback %s done" % str(func))
        if event and event['Event-Name']:
            self.trace("dispatch")
            self._spawn(self.dispatch_event, event)
            self.trace("dispatch done")

    def _api_response(self, event):
        '''
        Receives api/response callback.
        '''
        # Gets raw data for this event.
        raw = self.read_raw(event)
        # If raw was found, this is our Event body.
        if raw:
            event.set_body(raw)
        # Wake up waiting command.
        try:
            _cmd_uuid, _async_res = self._commands_pool.pop(0)
        except (IndexError, ValueError):
            raise InternalSyncError("Cannot wakeup command !")
        _async_res.set((_cmd_uuid, event))
        return None

    def _command_reply(self, event):
        '''
        Receives command/reply callback.
        '''
        # Wake up waiting command.
        try:
            _cmd_uuid, _async_res = self._commands_pool.pop(0)
        except (IndexError, ValueError):
            raise InternalSyncError("Cannot wakeup command !")
        _async_res.set((_cmd_uuid, event))
        return None

    def _event_plain(self, event):
        '''
        Receives text/event-plain callback.
        '''
        # Gets raw data for this event
        raw = self.read_raw(event)
        # If raw was found drops current event
        # and replaces with Event created from raw
        if raw:
            event = Event(raw)
            # Gets raw response from Event Content-Length header
            # and raw buffer
            raw_response = self.read_raw_response(event, raw)
            # If rawresponse was found, this is our Event body
            if raw_response:
                event.set_body(raw_response)
        # Returns Event
        return event

    def _event_json(self, event):
        '''
        Receives text/event-json callback.
        '''
        # Gets json data for this event
        json_data = self.read_raw(event)
        # If raw was found drops current event
        # and replaces with JsonEvent created from json_data
        if json_data:
            event = JsonEvent(json_data)
        # Returns Event
        return event

    def _disconnect_notice(self, event):
        '''
        Receives text/disconnect-notice callback.
        '''
        self._closing_state = True
        # Gets raw data for this event
        raw = self.read_raw(event)
        if raw:
            event = Event(raw)
            # Gets raw response from Event Content-Length header
            # and raw buffer
            raw_response = self.read_raw_response(event, raw)
            # If rawresponse was found, this is our Event body
            if raw_response:
                event.set_body(raw_response)
        return None

    def dispatch_event(self, event):
        '''
        Dispatches one event with callback.

        E.g. Receives Background_Job event and calls on_background_job function.
        '''
        # When no callbacks found, try unbound_event.
        try:
            callback = self._event_callbacks[event['Event-Name']]
        except KeyError:
            callback = self._event_callbacks['unbound_event']
        if not callback:
            return
        # Calls callback.
        try:
            callback(event)
        except:
            self.callback_failure(event)

    def callback_failure(self, event):
        '''
        Called when callback to an event fails.

        Can be implemented by the subclass.
        '''
        pass

    def connect(self):
        '''
        Connects to eventsocket.
        '''
        self._closing_state = False

    def disconnect(self):
        '''
        Disconnect and release socket and finally kill event handler.
        '''
        self.connected = False
        self.trace("releasing ...")
        try:
            # avoid handler stuck
            self._g_handler.get(block=True, timeout=2.0)
        except:
            self.trace("releasing forced")
            self._g_handler.kill()
        self.trace("releasing done")
        # prevent any pending request to be stuck
        self._flush_commands()

    def _flush_commands(self):
        # Flush all commands pending
        for _cmd_uuid, _async_res in self._commands_pool:
            _async_res.set((_cmd_uuid, Event()))

    def _send(self, cmd):
        self.transport.write(cmd + EOL*2)

    def _sendmsg(self, name, arg=None, uuid="", lock=False, loops=1, async=False):
        msg = "sendmsg %s\ncall-command: execute\nexecute-app-name: %s\n" \
                % (uuid, name)
        if lock is True:
            msg += "event-lock: true\n"
        if loops > 1:
            msg += "loops: %d\n" % loops
        if async is True:
            msg += "async: true\n"
        if arg:
            arglen = len(arg)
            msg += "content-type: text/plain\ncontent-length: %d\n\n%s\n" % (arglen, arg)
        self.transport.write(msg + EOL)

    def _protocol_send(self, command, args=""):
        if self._closing_state:
            return Event()
        self.trace("_protocol_send %s %s" % (command, args))
        # Append command to pool
        # and send it to eventsocket
        _cmd_uuid = str(uuid1())
        _async_res = gevent.event.AsyncResult()
        with self._lock:
            self._commands_pool.append((_cmd_uuid, _async_res))
            self._send("%s %s" % (command, args))
        self.trace("_protocol_send %s wait ..." % command)
        _uuid, event = _async_res.get()
        if _cmd_uuid != _uuid:
            raise InternalSyncError("in _protocol_send")
        # Casts Event to appropriate event type :
        # Casts to ApiResponse, if event is api
        if command == 'api':
            event = ApiResponse.cast(event)
        # Casts to BgapiResponse, if event is bgapi
        elif command == "bgapi":
            event = BgapiResponse.cast(event)
        # Casts to CommandResponse by default
        else:
            event = CommandResponse.cast(event)
        self.trace("_protocol_send %s done" % command)
        return event

    def _protocol_sendmsg(self, name, args=None, uuid="", lock=False, loops=1, async=False):
        if self._closing_state:
            return Event()
        self.trace("_protocol_sendmsg %s" % name)
        # Append command to pool
        # and send it to eventsocket
        _cmd_uuid = str(uuid1())
        _async_res = gevent.event.AsyncResult()
        with self._lock:
            self._commands_pool.append((_cmd_uuid, _async_res))
            self._sendmsg(name, args, uuid, lock, loops, async)
        self.trace("_protocol_sendmsg %s wait ..." % name)
        _uuid, event = _async_res.get()
        if _cmd_uuid != _uuid:
            raise InternalSyncError("in _protocol_sendmsg")
        self.trace("_protocol_sendmsg %s done" % name)
        # Always casts Event to CommandResponse
        return CommandResponse.cast(event)

########NEW FILE########
__FILENAME__ = eventtypes
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Event Types classes
"""

from urllib import unquote
import ujson as json


class Event(object):
    '''Event class'''
    __slots__ = ('__weakref__',
                 '_headers',
                 '_raw_body',
                )

    def __init__(self, buffer=""):
        self._headers = {}
        self._raw_body = ''
        if buffer:
            buffer = buffer.decode('utf-8', 'ignore')
            buffer = buffer.encode('utf-8')
            # Sets event headers from buffer.
            for line in buffer.splitlines():
                try:
                    var, val = line.rstrip().split(': ', 1)
                    self.set_header(var, val)
                except ValueError:
                    pass

    def __getitem__(self, key):
        return self.get_header(key)

    def __setitem__(self, key, value):
        self.set_header(key, value)

    def get_content_length(self):
        '''
        Gets Content-Length header as integer.

        Returns 0 If length not found.
        '''
        length = self.get_header('Content-Length')
        if length:
            try:
                return int(length)
            except:
                return 0
        return 0

    def get_reply_text(self):
        '''
        Gets Reply-Text header as string.

        Returns None if header not found.
        '''
        return self.get_header('Reply-Text')

    def is_reply_text_success(self):
        '''
        Returns True if ReplyText header begins with +OK.

        Returns False otherwise.
        '''
        reply = self.get_reply_text()
        return reply and reply[:3] == '+OK'

    def get_content_type(self):
        '''
        Gets Content-Type header as string.

        Returns None if header not found.
        '''
        return self.get_header('Content-Type')

    def get_headers(self):
        '''
        Gets all headers as a python dict.
        '''
        return self._headers

    def set_headers(self, headers):
        '''
        Sets all headers from dict.
        '''
        self._headers = headers.copy()

    def get_header(self, key, defaultvalue=None):
        '''
        Gets a specific header as string.

        Returns None if header not found.
        '''
        try:
            return self._headers[key]
        except KeyError:
            return defaultvalue

    def set_header(self, key, value):
        '''
        Sets a specific header.
        '''
        self._headers[key.strip()] = unquote(value.strip())

    def get_body(self):
        '''
        Gets raw Event body.
        '''
        return self._raw_body

    def set_body(self, data):
        '''
        Sets raw Event body.
        '''
        self._raw_body = data

    def is_empty(self):
        '''Return True if no headers and no body.'''
        return not self._raw_body and not self._headers

    def get_response(self):
        '''
        Gets response (body).
        '''
        return self.get_body().strip()

    def is_success(self):
        '''
        Returns True if body begins with +OK.

        Otherwise returns False.
        '''
        return self._raw_body and self._raw_body[:3] == '+OK'

    def __str__(self):
        return '<%s headers=%s, body=%s>' \
               % (self.__class__.__name__,
                  str(self._headers),
                  str(self._raw_body))


class ApiResponse(Event):
    def __init__(self, buffer=""):
        Event.__init__(self, buffer)

    @classmethod
    def cast(self, event):
        '''
        Makes an ApiResponse instance from Event instance.
        '''
        cls = ApiResponse()
        cls._headers = event._headers
        cls._raw_body = event._raw_body
        return cls


class BgapiResponse(Event):
    def __init__(self, buffer=""):
        Event.__init__(self, buffer)

    @classmethod
    def cast(self, event):
        '''
        Makes a BgapiResponse instance from Event instance.
        '''
        cls = BgapiResponse()
        cls._headers = event._headers
        cls._raw_body = event._raw_body
        return cls

    def get_response(self):
        '''
        Gets response for bgapi command.
        '''
        return self.get_reply_text()

    def get_job_uuid(self):
        '''
        Gets Job-UUID from bgapi command.
        '''
        return self.get_header('Job-UUID')

    def is_success(self):
        '''
        Returns True if bgapi command is a success.

        Otherwise returns False.
        '''
        return self.is_reply_text_success()


class CommandResponse(Event):
    def __init__(self, buffer=""):
        Event.__init__(self, buffer)

    @classmethod
    def cast(self, event):
        '''
        Makes a CommandResponse instance from Event instance.
        '''
        cls = CommandResponse()
        cls._headers = event._headers
        cls._raw_body = event._raw_body
        return cls

    def get_response(self):
        '''
        Gets response for a command.
        '''
        return self.get_reply_text()

    def is_success(self):
        '''
        Returns True if command is a success.

        Otherwise returns False.
        '''
        return self.is_reply_text_success()


class JsonEvent(Event):
    '''Json Event class'''
    def __init__(self, buffer=""):
        self._headers = {}
        self._raw_body = ''
        if buffer:
            buffer = buffer.decode('utf-8', 'ignore')
            buffer = buffer.encode('utf-8')
            self._headers = json.loads(buffer)
            try:
                self._raw_body = self._headers['_body']
            except KeyError:
                pass


########NEW FILE########
__FILENAME__ = inboundsocket
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Inbound Event Socket class
"""

import gevent
import gevent.event
from gevent.timeout import Timeout

from plivo.core.freeswitch.eventsocket import EventSocket
from plivo.core.freeswitch.transport import InboundTransport
from plivo.core.errors import ConnectError


class InboundEventSocket(EventSocket):
    '''
    FreeSWITCH Inbound Event Socket
    '''
    def __init__(self, host, port, password, filter="ALL",
             eventjson=True, pool_size=5000, trace=False, connect_timeout=20):
        EventSocket.__init__(self, filter, eventjson, pool_size, trace=trace)
        # add the auth request event callback
        self._response_callbacks['auth/request'] = self._auth_request
        self._wait_auth_event = gevent.event.AsyncResult()
        self.password = password
        self.transport = InboundTransport(host, port, connect_timeout=connect_timeout)

    def _auth_request(self, event):
        '''
        Receives auth/request callback.

        Only used by InboundEventSocket.
        '''
        # Wake up waiting request
        self._wait_auth_event.set(True)

    def _wait_auth_request(self):
        '''
        Waits until auth/request event is received.
        '''
        # Sets timeout to wait for auth/request
        timer = Timeout(self.transport.get_connect_timeout())
        timer.start()
        try:
            # When auth/request is received,
            # _auth_request method will wake up async result 
            # so we will just wait this event here.
            return self._wait_auth_event.get()
        except Timeout:
            raise ConnectError("Timeout waiting auth/request")
        finally:
            timer.cancel()

    def connect(self):
        '''
        Connects to mod_eventsocket, authenticates and sets event filter.

        Returns True on success or raises ConnectError exception on failure.
        '''
        try:
            self.run()
        except ConnectError, e:
            self.connected = False
            raise

    def run(self):
        super(InboundEventSocket, self).connect()
        # Connects transport, if connection fails, raise ConnectError
        try:
            self.transport.connect()
        except Exception, e:
            raise ConnectError("Transport failure: %s" % str(e))
        # Sets connected flag to True
        self.connected = True

        # Be sure command pool is empty before starting
        self._flush_commands()

        # Starts handling events
        self.start_event_handler()

        # Waits for auth/request, if timeout, raises ConnectError
        self._wait_auth_request()

        # We are ready now !
        # Authenticate or raise ConnectError
        auth_response = self.auth(self.password)
        if not auth_response.is_reply_text_success():
            raise ConnectError("Auth failure")

        # Sets event filter or raises ConnectError
        if self._filter:
            if self._is_eventjson:
                filter_response = self.eventjson(self._filter)
            else:
                filter_response = self.eventplain(self._filter)
            if not filter_response.is_reply_text_success():
                raise ConnectError("Event filter failure")
        return

    def serve_forever(self):
        """
        Starts waiting for events in endless loop.
        """
        while self.is_connected():
            gevent.sleep(0.1)

########NEW FILE########
__FILENAME__ = outboundsocket
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Outbound Event Socket class

This manage Event Socket communication with the Freeswitch Server
"""

import gevent
from gevent.server import StreamServer
from gevent.timeout import Timeout

from plivo.core.freeswitch.eventsocket import EventSocket
from plivo.core.freeswitch.transport import OutboundTransport
from plivo.core.errors import ConnectError


BACKLOG = 2048


class OutboundEventSocket(EventSocket):
    '''
    FreeSWITCH Outbound Event Socket.

    A new instance of this class is created for every call/ session from FreeSWITCH.
    '''
    def __init__(self, socket, address, filter="ALL",
                 connect_timeout=60, eventjson=True, 
                 pool_size=5000, trace=False):
        EventSocket.__init__(self, filter, eventjson, pool_size, trace=trace)
        self.transport = OutboundTransport(socket, address, connect_timeout)
        self._uuid = None
        self._channel = None
        # Runs the main function .
        try:
            self.trace("run now")
            self.run()
            self.trace("run done")
        finally:
            self.trace("disconnect now")
            self.disconnect()
            self.trace("disconnect done")

    def connect(self):
        super(OutboundEventSocket, self).connect()
        # Starts event handler for this client/session.
        self.start_event_handler()

        # Sends connect and sets timeout while connecting.
        timer = Timeout(self.transport.get_connect_timeout())
        timer.start()
        try:
            connect_response = self._protocol_send("connect")
            if not connect_response.is_success():
                raise ConnectError("Error while connecting")
        except Timeout:
            raise ConnectError("Timeout connecting")
        finally:
            timer.cancel()

        # Sets channel and channel unique id from this event
        self._channel = connect_response
        self._uuid = connect_response.get_header("Unique-ID")

        # Set connected flag to True
        self.connected = True

        # Sets event filter or raises ConnectError
        if self._filter:
            if self._is_eventjson:
                self.trace("using eventjson")
                filter_response = self.eventjson(self._filter)
            else:
                self.trace("using eventplain")
                filter_response = self.eventplain(self._filter)
            if not filter_response.is_success():
                raise ConnectError("Event filter failure")

    def get_channel(self):
        return self._channel

    def get_channel_unique_id(self):
        return self._uuid

    def run(self):
        '''
        This method must be implemented by subclass.

        This is the entry point for outbound application.
        '''
        pass


class OutboundServer(StreamServer):
    '''
    FreeSWITCH Outbound Event Server
    '''
    # Sets the maximum number of consecutive accepts that a process may perform on
    # a single wake up. High values give higher priority to high connection rates,
    # while lower values give higher priority to already established connections.
    max_accept = 50000

    # the number of seconds to sleep in case there was an error in accept() call
    # for consecutive errors the delay will double until it reaches max_delay
    # when accept() finally succeeds the delay will be reset to min_delay again
    min_delay = 0.001
    max_delay = 0.01

    def __init__(self, address, handle_class, filter="ALL"):
        self._filter = filter
        #Define the Class that will handle process when receiving message
        self._requestClass = handle_class
        StreamServer.__init__(self, address, self.do_handle, 
                        backlog=BACKLOG, spawn=gevent.spawn_raw)

    def do_handle(self, socket, address):
        try:
            self.handle_request(socket, address)
        finally:
            self.finish_request(socket, address)

    def finish_request(self, socket, address):
        try: 
            socket.shutdown(2)
        except:
            pass
        try: 
            socket.close()
        except:
            pass

    def handle_request(self, socket, address):
        self._requestClass(socket, address, self._filter)
        







if __name__ == '__main__':
    outboundserver = OutboundServer(('127.0.0.1', 8084), OutboundEventSocket)
    outboundserver.serve_forever()

########NEW FILE########
__FILENAME__ = transport
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Freeswitch Transport classes
"""

import gevent.socket as socket
from plivo.core.errors import ConnectError
from plivo.core.transport import Transport


class InboundTransport(Transport):
    def __init__(self, host, port, connect_timeout=5):
        self.host = host
        self.port = port
        self.timeout = connect_timeout
        self.sockfd = None
        self.closed = True

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))
        self.sock.settimeout(None)
        self.sockfd = self.sock.makefile()
        self.closed = False

    def write(self, data):
        if self.closed:
            raise ConnectError('not connected')
        self.sockfd.write(data)
        self.sockfd.flush()



class OutboundTransport(Transport):
    def __init__(self, socket, address, connect_timeout=5):
        inactivity_timeout = 3600
        self.sock = socket
        # safe guard inactivity timeout
        self.sock.settimeout(inactivity_timeout)
        self.sockfd = socket.makefile()
        self.address = address
        self.timeout = connect_timeout
        self.closed = False


########NEW FILE########
__FILENAME__ = transport
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.


"""
Transport class
"""

class Transport(object):
    def __init__(self):
        self.closed = True

    def write(self, data):
        self.sockfd.write(bytearray(data, "utf-8"))
        self.sockfd.flush()

    def read_line(self):
        return self.sockfd.readline()

    def read(self, length):
        return self.sockfd.read(length)

    def close(self):
        if self.closed:
            return
        try:
            self.sock.shutdown(2)
        except:
            pass
        try:
            self.sock.close()
        except:
            pass
        self.closed = True

    def get_connect_timeout(self):
        return self.timeout

########NEW FILE########
__FILENAME__ = api
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details

import base64
import re
import uuid
import os
import os.path
from datetime import datetime
try:
    import xml.etree.cElementTree as etree
except ImportError:
    from xml.etree.elementtree import ElementTree as etree

import ujson as json
import flask
from flask import request
from werkzeug.exceptions import Unauthorized
import gevent.queue

from plivo.rest.freeswitch.helpers import is_valid_url, get_conf_value, \
                                            get_post_param, get_resource, \
                                            normalize_url_space, \
                                            HTTPRequest
import plivo.rest.freeswitch.elements as elements

MAX_LOOPS = elements.MAX_LOOPS


def auth_protect(decorated_func):
    def wrapper(obj):
        if obj._validate_http_auth() and obj._validate_ip_auth():
            return decorated_func(obj)
    wrapper.__name__ = decorated_func.__name__
    wrapper.__doc__ = decorated_func.__doc__
    return wrapper



class Gateway(object):
    __slots__ = ('__weakref__',
                 'request_uuid',
                 'to', 'gw', 'codecs',
                 'timeout'
                )

    def __init__(self, request_uuid, to, gw, codecs, timeout):
        self.request_uuid = request_uuid
        self.to = to
        self.gw = gw
        self.codecs = codecs
        self.timeout = timeout

    def __repr__(self):
        return "<Gateway RequestUUID=%s To=%s Gw=%s Codecs=%s Timeout=%s>" \
            % (self.request_uuid, self.to, self.gw, self.codecs, self.timeout)


class CallRequest(object):
    __slots__ = ('__weakref__',
                 'request_uuid',
                 'gateways',
                 'answer_url',
                 'ring_url',
                 'hangup_url',
                 'state_flag',
                 'extra_dial_string',
                 'to',
                 '_from',
                 '_accountsid',
                 '_qe',
                )

    def __init__(self, request_uuid, gateways,
                 answer_url, ring_url, hangup_url, 
                 to='', _from='', accountsid='',
                 extra_dial_string=''):
        self.request_uuid = request_uuid
        self.gateways = gateways
        self.answer_url = answer_url
        self.ring_url = ring_url
        self.hangup_url = hangup_url
        self.state_flag = None
        self.to = to
        self._from = _from
        self._accountsid = accountsid
        self.extra_dial_string = extra_dial_string
        self._qe = gevent.queue.Queue()

    def notify_call_try(self):
        self._qe.put(False)

    def notify_call_end(self):
        self._qe.put(True)

    def wait_call_attempt(self):
        return self._qe.get(timeout=86400)

    def __repr__(self):
        return "<CallRequest RequestUUID=%s AccountSID=%s To=%s From=%s Gateways=%s AnswerUrl=%s RingUrl=%s HangupUrl=%s StateFlag=%s ExtraDialString=%s>" \
            % (self.request_uuid, self._accountsid, self.gateways, self.to, self._from,
               self.answer_url, self.ring_url, self.hangup_url, str(self.state_flag),
               str(self.extra_dial_string))



class PlivoRestApi(object):
    _config = None
    _rest_inbound_socket = None
    allowed_ips = []
    key = ''
    secret = ''

    def _validate_ip_auth(self):
        """Verify request is from allowed ips
        """
        if not self.allowed_ips:
            return True
        for ip in self.allowed_ips:
            if ip.strip() == request.remote_addr.strip():
                return True
        raise Unauthorized("IP Auth Failed")

    def _validate_http_auth(self):
        """Verify http auth request with values in "Authorization" header
        """
        if not self.key or not self.secret:
            return True
        try:
            auth_type, encoded_auth_str = \
                request.headers['Authorization'].split(' ', 1)
            if auth_type == 'Basic':
                decoded_auth_str = base64.decodestring(encoded_auth_str)
                auth_id, auth_token = decoded_auth_str.split(':', 1)
                if auth_id == self.key and auth_token == self.secret:
                    return True
        except (KeyError, ValueError, TypeError):
            pass
        raise Unauthorized("HTTP Auth Failed")

    def send_response(self, Success, Message, **kwargs):
        if Success is True:
            self._rest_inbound_socket.log.info(Message)
            return flask.jsonify(Success=True, Message=Message, **kwargs)
        self._rest_inbound_socket.log.error(Message)
        return flask.jsonify(Success=False, Message=Message, **kwargs)

    def _prepare_play_string(self, remote_url):
        sound_files = []
        if not remote_url:
            return sound_files
        self._rest_inbound_socket.log.info('Fetching remote sound from restxml %s' % remote_url)
        try:
            response = self._rest_inbound_socket.send_to_url(remote_url, params={}, method='POST')
            doc = etree.fromstring(response)
            if doc.tag != 'Response':
                self._rest_inbound_socket.log.warn('No Response Tag Present')
                return sound_files

            # build play string from remote restxml
            for element in doc:
                # Play element
                if element.tag == 'Play':
                    child_instance = elements.Play()
                    child_instance.parse_element(element)
                    child_instance.prepare(self._rest_inbound_socket)
                    sound_file = child_instance.sound_file_path
                    if sound_file:
                        sound_file = get_resource(self._rest_inbound_socket, sound_file)
                        loop = child_instance.loop_times
                        if loop == 0:
                            loop = MAX_LOOPS  # Add a high number to Play infinitely
                        # Play the file loop number of times
                        for i in range(loop):
                            sound_files.append(sound_file)
                        # Infinite Loop, so ignore other children
                        if loop == MAX_LOOPS:
                            break
                # Speak element
                elif element.tag == 'Speak':
                    child_instance = elements.Speak()
                    child_instance.parse_element(element)
                    text = child_instance.text
                    # escape simple quote
                    text = text.replace("'", "\\'")
                    loop = child_instance.loop_times
                    child_type = child_instance.item_type
                    method = child_instance.method
                    say_str = ''
                    if child_type and method:
                        language = child_instance.language
                        say_args = "%s.wav %s %s %s '%s'" \
                                        % (language, language, child_type, method, text)
                        say_str = "${say_string %s}" % say_args
                    else:
                        engine = child_instance.engine
                        voice = child_instance.voice
                        say_str = "say:%s:%s:'%s'" % (engine, voice, text)
                    if not say_str:
                        continue
                    for i in range(loop):
                        sound_files.append(say_str)
                # Wait element
                elif element.tag == 'Wait':
                    child_instance = elements.Wait()
                    child_instance.parse_element(element)
                    pause_secs = child_instance.length
                    pause_str = 'file_string://silence_stream://%s' % (pause_secs * 1000)
                    sound_files.append(pause_str)
        except Exception, e:
            self._rest_inbound_socket.log.warn('Fetching remote sound from restxml failed: %s' % str(e))
        finally:
            self._rest_inbound_socket.log.info('Fetching remote sound from restxml done for %s' % remote_url)
            return sound_files


    def _prepare_call_request(self, caller_id, caller_name, to, extra_dial_string, gw, gw_codecs,
                                gw_timeouts, gw_retries, send_digits, send_preanswer, time_limit,
                                hangup_on_ring, answer_url, ring_url, hangup_url, accountsid=''):
        gateways = []
        gw_retry_list = []
        gw_codec_list = []
        gw_timeout_list = []
        args_list = []
        sched_hangup_id = None
        # don't allow "|" and "," in 'to' (destination) to avoid call injection
        to = re.split(',|\|', to)[0]
        # build gateways list removing trailing '/' character
        gw_list = gw.split(',')
        # split gw codecs by , but only outside the ''
        if gw_codecs:
            gw_codec_list = re.split(''',(?=(?:[^'"]|'[^']*'|"[^"]*")*$)''',
                                                                    gw_codecs)
        if gw_timeouts:
            gw_timeout_list = gw_timeouts.split(',')
        if gw_retries:
            gw_retry_list = gw_retries.split(',')

        # create a new request uuid
        request_uuid = str(uuid.uuid1())
        # append args
        args_list.append("plivo_request_uuid=%s" % request_uuid)
        args_list.append("plivo_answer_url=%s" % answer_url)
        args_list.append("plivo_ring_url=%s" % ring_url)
        args_list.append("plivo_hangup_url=%s" % hangup_url)
        args_list.append("origination_caller_id_number=%s" % caller_id)
        if caller_name:
            args_list.append("origination_caller_id_name='%s'" % caller_name)

        # set extra_dial_string
        if extra_dial_string:
             args_list.append(extra_dial_string)

        if accountsid:
            args_list.append("plivo_accountsid=%s" % accountsid)

        # set hangup_on_ring
        try:
            hangup_on_ring = int(hangup_on_ring)
        except ValueError:
            hangup_on_ring = -1
        exec_on_media = 1

        if hangup_on_ring == 0:
            args_list.append("execute_on_media='hangup ORIGINATOR_CANCEL'")
            args_list.append("execute_on_ring='hangup ORIGINATOR_CANCEL'")
            exec_on_media += 1
        elif hangup_on_ring > 0:
            args_list.append("execute_on_media_%d='sched_hangup +%d ORIGINATOR_CANCEL'" \
                                                        % (exec_on_media, hangup_on_ring))
            args_list.append("execute_on_ring='sched_hangup +%d ORIGINATOR_CANCEL'" \
                                                        % hangup_on_ring)
            exec_on_media += 1

        # set send_digits
        if send_digits:
            if send_preanswer:
                args_list.append("execute_on_media_%d='send_dtmf %s'" \
                                                    % (exec_on_media, send_digits))
                exec_on_media += 1
            else:
                args_list.append("execute_on_answer='send_dtmf %s'" % send_digits)

        # set time_limit
        try:
            time_limit = int(time_limit)
        except ValueError:
            time_limit = -1
        if time_limit > 0:
            # create sched_hangup_id
            sched_hangup_id = str(uuid.uuid1())
            args_list.append("api_on_answer_1='sched_api +%d %s hupall ALLOTTED_TIMEOUT plivo_request_uuid %s'" \
                                                % (time_limit, sched_hangup_id, request_uuid))
            args_list.append("plivo_sched_hangup_id=%s" % sched_hangup_id)

        # set plivo_from / plivo_to
        if caller_id:
            var_from = "plivo_from=%s" % caller_id
        else:
            var_from = "plivo_from=' '" % caller_id
        var_to = "plivo_to=%s" % to
        args_list.append(var_from)
        args_list.append(var_to)

        # build originate string
        args_str = ','.join(args_list)

        for gw in gw_list:
            try:
                codecs = gw_codec_list.pop(0)
            except (ValueError, IndexError):
                codecs = ''
            try:
                retry = int(gw_retry_list.pop(0))
            except (ValueError, IndexError):
                retry = 1
            try:
                timeout = int(gw_timeout_list.pop(0))
            except (ValueError, IndexError):
                timeout = 60 # TODO allow no timeout ?
            for i in range(retry):
                gateway = Gateway(request_uuid, to, gw, codecs, timeout)
                gateways.append(gateway)

        call_req = CallRequest(request_uuid, gateways, answer_url, ring_url, hangup_url, 
                               to=to, _from=caller_id, accountsid=accountsid,
                               extra_dial_string=args_str)
        return call_req

    @staticmethod
    def _parse_conference_xml_list(xmlstr, member_filter=None, uuid_filter=None, mute_filter=False, deaf_filter=False):
        res = {}
        if member_filter:
            mfilter = tuple( [ mid.strip() for mid in member_filter.split(',') if mid != '' ])
        else:
            mfilter = ()
        if uuid_filter:
            ufilter = tuple( [ uid.strip() for uid in uuid_filter.split(',') if uid != '' ])
        else:
            ufilter = ()

        doc = etree.fromstring(xmlstr)

        if doc.tag != 'conferences':
            raise Exception("Root tag must be 'conferences'")
        for conf in doc:
            conf_name = conf.get("name", None)
            if not conf_name:
                continue
            res[conf_name] = {}
            res[conf_name]['ConferenceUUID'] = conf.get("uuid")
            res[conf_name]['ConferenceRunTime'] = conf.get("run_time")
            res[conf_name]['ConferenceName'] = conf_name
            res[conf_name]['ConferenceMemberCount'] = conf.get("member-count")
            res[conf_name]['Members'] = []
            for member in conf.findall('members/member'):
                m = {}
                member_id = member.find('id').text
                call_uuid = member.find("uuid").text
                is_muted = member.find("flags/can_speak").text == "false"
                is_deaf = member.find("flags/can_hear").text == "false"
                if not member_id or not call_uuid:
                    continue
                filter_match = 0
                if not mfilter and not ufilter and not mute_filter and not deaf_filter:
                    filter_match = 1
                else:
                    if mfilter and member_id in mfilter:
                        filter_match += 1
                    if ufilter and call_uuid in ufilter:
                        filter_match += 1
                    if mute_filter and is_muted:
                        filter_match += 1
                    if deaf_filter and is_deaf:
                        filter_match += 1
                if filter_match == 0:
                    continue
                m["MemberID"] = member_id
                m["Deaf"] = is_deaf
                m["Muted"] = is_muted
                m["CallUUID"] = call_uuid
                m["CallName"] = member.find("caller_id_name").text
                m["CallNumber"] = member.find("caller_id_number").text
                m["JoinTime"] = member.find("join_time").text
                res[conf_name]['Members'].append(m)
        return res

    @auth_protect
    def index(self):
        message = """
        Welcome to Plivo - http://www.plivo.org/<br>
        <br>
        Plivo is a Communication Framework to rapidly build Voice based apps,
        to make and receive calls, using your existing web development skills
        and infrastructure.<br>
        <br>
        <br>
        For further information please visit our website :
        http://www.plivo.org/ <br>
        <br>
        <br>
        """
        return message

    @auth_protect
    def reload_config(self):
        """Reload plivo config for rest server
        """
        self._rest_inbound_socket.log.debug("RESTAPI Reload with %s" \
                                        % str(request.form.items()))
        msg = "Plivo config reload failed"
        result = False

        if self._rest_inbound_socket:
            try:
                self._rest_inbound_socket.get_server().reload()
                extra = "rest_server"
                outbound_pidfile = self._rest_inbound_socket.get_server().fs_out_pidfile
                if outbound_pidfile:
                    try:
                        pid = int(open(outbound_pidfile, 'r').read().strip())
                        os.kill(pid, 1)
                        extra += " and outbound_server"
                    except Exception, e:
                        extra += ", failed for outbound_server (%s)" % str(e)
                else:
                    extra += ", failed for outbound_server (no pidfile)"
                msg = "Plivo config reloaded : %s" % extra
                result = True
            except Exception, e:
                msg += ' : %s' % str(e)
                result = False

        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def reload_cache_config(self):
        """Reload plivo cache server config
        """
        self._rest_inbound_socket.log.debug("RESTAPI ReloadCacheConfig with %s" \
                                        % str(request.form.items()))
        msg = "ReloadCacheConfig Failed"
        result = False

        try:
            cache_api_url = self.cache['url']
        except KeyError:
            msg = "ReloadCacheConfig Failed -- CACHE_URL not found"
            result = False
            return self.send_response(Success=result, Message=msg)

        try:
            req = HTTPRequest(auth_id=self.key, auth_token=self.secret)
            data = req.fetch_response(cache_api_url + '/ReloadConfig/', params={}, method='POST')
            res = json.loads(data)
            try:
                success = res['Success']
                msg = res['Message']
            except:
                success = False
                msg = "unknown"
            if success:
                msg = "Plivo Cache Server config reloaded"
                result = True
                self._rest_inbound_socket.log.info("ReloadCacheConfig Done")
            else:
                raise Exception(msg)

        except Exception, e:
            msg = "Plivo Cache Server config reload failed"
            self._rest_inbound_socket.log.error("ReloadCacheConfig Failed -- %s" % str(e))
            result = False

        return self.send_response(Success=result, Message=msg)


    @auth_protect
    def call(self):
        """Make Outbound Call
        Allow initiating outbound calls via the REST API. To make an
        outbound call, make an HTTP POST request to the resource URI.

        POST Parameters
        ----------------

        Required Parameters - You must POST the following parameters:

        From: The phone number to use as the caller id for the call without
        the leading +

        To: The number to call without the leading +

        Gateways: Comma separated string of gateways to dial the call out

        GatewayCodecs: Comma separated string of codecs for gateways

        GatewayTimeouts: Comma separated string of timeouts for gateways

        GatewayRetries: Comma separated string of retries for gateways

        AnswerUrl: The URL that should be requested for XML when the call
        connects


        Optional Parameters - You may POST the following parameters:

        [CallerName]: the caller name to use for call

        [TimeLimit]: Define the max time of the call

        [HangupUrl]: URL that Plivo will notify to, with POST params when
        calls ends

        [RingUrl]: URL that Plivo will notify to, with POST params when
        calls starts ringing

        [HangupOnRing]: If Set to 0 we will hangup as soon as the number ring,
        if set to value X we will wait X seconds when start ringing and then
        hang up

        [ExtraDialString]: Additional Originate dialstring to be executed
        while making the outbound call

        [SendDigits]: A string of keys to dial after connecting to the number.
        Valid digits in the string include: any digit (0-9), '#' and '*'.
        Very useful, if you want to connect to a company phone number,
        and wanted to dial extension 1234 and then the pound key,
        use SendDigits=1234#.
        Remember to URL-encode this string, since the '#' character has
        special meaning in a URL.
        To wait before sending DTMF to the extension, you can add leading 'w'
        characters.
        Each 'w' character waits 0.5 seconds instead of sending a digit.
        Each 'W' character waits 1.0 seconds instead of sending a digit.
        You can also add the tone duration in ms by appending @[duration] after string.
        Eg. 1w2w3@1000

        [SendOnPreanswer]: SendDigits on early media instead of answer.
        """
        self._rest_inbound_socket.log.debug("RESTAPI Call with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False
        request_uuid = ""

        caller_id = get_post_param(request, 'From')
        to = get_post_param(request, 'To')
        gw = get_post_param(request, 'Gateways')
        answer_url = get_post_param(request, 'AnswerUrl')

        if not caller_id or not to or not gw or not answer_url:
            msg = "Mandatory Parameters Missing"
        elif not is_valid_url(answer_url):
            msg = "AnswerUrl is not Valid"
        else:
            hangup_url = get_post_param(request, 'HangupUrl')
            ring_url = get_post_param(request, 'RingUrl')
            if not hangup_url:
                hangup_url = answer_url
            if hangup_url and not is_valid_url(hangup_url):
                msg = "HangupUrl is not Valid"
            elif ring_url and not is_valid_url(ring_url):
                msg = "RingUrl is not Valid"
            else:
                extra_dial_string = get_post_param(request, 'ExtraDialString')
                gw_codecs = get_post_param(request, 'GatewayCodecs')
                gw_timeouts = get_post_param(request, 'GatewayTimeouts')
                gw_retries = get_post_param(request, 'GatewayRetries')
                send_digits = get_post_param(request, 'SendDigits')
                send_preanswer = get_post_param(request, 'SendOnPreanswer') == 'true'
                time_limit = get_post_param(request, 'TimeLimit')
                hangup_on_ring = get_post_param(request, 'HangupOnRing')
                caller_name = get_post_param(request, 'CallerName') or ''
                accountsid = get_post_param(request, 'AccountSID') or ''

                call_req = self._prepare_call_request(
                                    caller_id, caller_name, to, extra_dial_string,
                                    gw, gw_codecs, gw_timeouts, gw_retries,
                                    send_digits, send_preanswer, time_limit, hangup_on_ring,
                                    answer_url, ring_url, hangup_url, accountsid)

                request_uuid = call_req.request_uuid
                self._rest_inbound_socket.call_requests[request_uuid] = call_req
                self._rest_inbound_socket.spawn_originate(request_uuid)
                msg = "Call Request Executed"
                result = True

        return self.send_response(Success=result,
                             Message=msg,
                             RequestUUID=request_uuid)

    @auth_protect
    def bulk_call(self):
        """Make Bulk Outbound Calls in one request
        Allow initiating bulk outbound calls via the REST API. To make a
        bulk outbound call, make an HTTP POST request to the resource URI.

        POST Parameters
        ----------------

        Required Parameters - You must POST the following parameters:

        Delimiter: Any special character (with the exception of '/' and ',')
        which will be used as a delimiter for the string of parameters below. E.g. '<'

        From: The phone number to use as the caller id for the call without
        the leading +

        To: The numbers to call without the leading +

        Gateways: Comma separated string of gateways to dial the call out

        GatewayCodecs: Comma separated string of codecs for gateways

        GatewayTimeouts: Comma separated string of timeouts for gateways

        GatewayRetries: Comma separated string of retries for gateways

        AnswerUrl: The URL that should be requested for XML when the call
        connects. Similar to the URL for your inbound calls

        Optional Parameters - You may POST the following parameters:

        [CallerName]: the caller name to use for call

        [TimeLimit]: Define the max time of the call

        [HangupUrl]: URL that Plivo will notify to, with POST params when
        calls ends

        [RingUrl]: URL that Plivo will notify to, with POST params when
        calls starts ringing

        [HangupOnRing]: If Set to 0 we will hangup as soon as the number ring,
        if set to value X we will wait X seconds when start ringing and then
        hang up

        [ExtraDialString]: Additional Originate dialstring to be executed
        while making the outbound call

        [SendDigits]: A string of keys to dial after connecting to the number.
        Valid digits in the string include: any digit (0-9), '#' and '*'.
        Very useful, if you want to connect to a company phone number,
        and wanted to dial extension 1234 and then the pound key,
        use SendDigits=1234#.
        Remember to URL-encode this string, since the '#' character has
        special meaning in a URL.
        To wait before sending DTMF to the extension, you can add leading 'w' or 'W' characters.
        Each 'w' character waits 0.5 seconds instead of sending a digit.
        Each 'W' character waits 1.0 seconds instead of sending a digit.
        You can also add the tone duration in ms by appending @[duration] after string.
        Eg. 1w2w3@1000

        [SendOnPreanswer]: SendDigits on early media instead of answer.
        """
        self._rest_inbound_socket.log.debug("RESTAPI BulkCall with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False
        request_uuid = ""

        request_uuid_list = []
        i = 0

        caller_id = get_post_param(request, 'From')
        to_str = get_post_param(request, 'To')
        gw_str = get_post_param(request, 'Gateways')
        answer_url = get_post_param(request, 'AnswerUrl')
        delimiter = get_post_param(request, 'Delimiter')

        if delimiter in (',', '/'):
            msg = "This Delimiter is not allowed"
        elif not caller_id or not to_str or not gw_str or not answer_url or\
            not delimiter:
            msg = "Mandatory Parameters Missing"
        elif not is_valid_url(answer_url):
            msg = "AnswerUrl is not Valid"
        else:
            hangup_url = get_post_param(request, 'HangupUrl')
            if not hangup_url:
                hangup_url = answer_url
            ring_url = get_post_param(request, 'RingUrl')
            if hangup_url and not is_valid_url(hangup_url):
                msg = "HangupUrl is not Valid"
            elif ring_url and not is_valid_url(ring_url):
                msg = "RingUrl is not Valid"
            else:
                extra_dial_string = get_post_param(request,
                                                        'ExtraDialString')
                # Is a string of strings
                gw_codecs_str = get_post_param(request, 'GatewayCodecs')
                gw_timeouts_str = get_post_param(request, 'GatewayTimeouts')
                gw_retries_str = get_post_param(request, 'GatewayRetries')
                send_digits_str = get_post_param(request, 'SendDigits')
                send_preanswer_str = get_post_param(request, 'SendOnPreanswer')
                time_limit_str = get_post_param(request, 'TimeLimit')
                hangup_on_ring_str = get_post_param(request, 'HangupOnRing')
                caller_name_str = get_post_param(request, 'CallerName')
                accountsid = get_post_param(request, 'AccountSID') or ''

                to_str_list = to_str.split(delimiter)
                gw_str_list = gw_str.split(delimiter)
                gw_codecs_str_list = gw_codecs_str.split(delimiter)
                gw_timeouts_str_list = gw_timeouts_str.split(delimiter)
                gw_retries_str_list = gw_retries_str.split(delimiter)
                send_digits_list = send_digits_str.split(delimiter)
                send_preanswer_list = send_preanswer_str.split(delimiter)
                time_limit_list = time_limit_str.split(delimiter)
                hangup_on_ring_list = hangup_on_ring_str.split(delimiter)
                caller_name_list = caller_name_str.split(delimiter)

                if len(to_str_list) < 2:
                    msg = "BulkCalls should be used for at least 2 numbers"
                elif len(to_str_list) != len(gw_str_list):
                    msg = "'To' parameter length does not match 'Gateways' Length"
                else:
                    for to in to_str_list:
                        try:
                            gw_codecs = gw_codecs_str_list[i]
                        except IndexError:
                            gw_codecs = ""
                        try:
                            gw_timeouts = gw_timeouts_str_list[i]
                        except IndexError:
                            gw_timeouts = ""
                        try:
                            gw_retries = gw_retries_str_list[i]
                        except IndexError:
                            gw_retries = ""
                        try:
                            send_digits = send_digits_list[i]
                        except IndexError:
                            send_digits = ""
                        try:
                            send_preanswer = send_preanswer_list[i] == 'true'
                        except IndexError:
                            send_preanswer = False
                        try:
                            time_limit = time_limit_list[i]
                        except IndexError:
                            time_limit = ""
                        try:
                            hangup_on_ring = hangup_on_ring_list[i]
                        except IndexError:
                            hangup_on_ring = ""
                        try:
                            caller_name = caller_name_list[i]
                        except IndexError:
                            caller_name = ""


                        call_req = self._prepare_call_request(
                                    caller_id, caller_name, to, extra_dial_string,
                                    gw_str_list[i], gw_codecs, gw_timeouts, gw_retries,
                                    send_digits, send_preanswer, time_limit, hangup_on_ring,
                                    answer_url, ring_url, hangup_url, accountsid)
                        request_uuid = call_req.request_uuid
                        request_uuid_list.append(request_uuid)
                        self._rest_inbound_socket.call_requests[request_uuid] = call_req
                        i += 1

                    # now do the calls !
                    if self._rest_inbound_socket.bulk_originate(request_uuid_list):
                        msg = "BulkCalls Requests Executed"
                        result = True
                    else:
                        msg = "BulkCalls Requests Failed"
                        request_uuid_list = []

        return self.send_response(Success=result, Message=msg,
                             RequestUUID=request_uuid_list)

    @auth_protect
    def hangup_call(self):
        """Hangup Call
        Realtime call hangup allows you to interrupt an in-progress
        call and terminate it.

        To terminate a live call, you make an HTTP POST request to a
        resource URI.

        POST Parameters
        ---------------
        Call ID Parameters: One of these parameters must be supplied :

        CallUUID: Unique Call ID to which the action should occur to.

        RequestUUID: Unique request ID which was given on a API response. This
        should be used for calls which are currently in progress and have no CallUUID.
        """
        self._rest_inbound_socket.log.debug("RESTAPI HangupCall with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        call_uuid = get_post_param(request, 'CallUUID')
        request_uuid= get_post_param(request, 'RequestUUID')

        if not call_uuid and not request_uuid:
            msg = "CallUUID or RequestUUID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        elif call_uuid and request_uuid:
            msg = "Both CallUUID and RequestUUID Parameters cannot be present"
            return self.send_response(Success=result, Message=msg)
        res = self._rest_inbound_socket.hangup_call(call_uuid, request_uuid)
        if res:
            msg = "Hangup Call Executed"
            result = True
        else:
            msg = "Hangup Call Failed"
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def transfer_call(self):
        """Transfer Call
        Realtime call transfer allows you to interrupt an in-progress
        call and place it another scenario.

        To transfer a live call, you make an HTTP POST request to a
        resource URI.

        POST Parameters
        ---------------
        CallUUID: Unique Call ID to which the action should occur to.

        Url: A valid URL that returns RESTXML. Plivo will immediately fetch
              the XML and continue the call as the new XML.
        """
        msg = ""
        result = False

        call_uuid = get_post_param(request, 'CallUUID')
        new_xml_url = get_post_param(request, 'Url')

        if not call_uuid:
            msg = "CallUUID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        elif not new_xml_url:
            msg = "Url Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        elif not is_valid_url(new_xml_url):
            msg = "Url is not Valid"
            return self.send_response(Success=result, Message=msg)

        res = self._rest_inbound_socket.transfer_call(new_xml_url,
                                                      call_uuid)
        if res:
            msg = "Transfer Call Executed"
            result = True
        else:
            msg = "Transfer Call Failed"
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def hangup_all_calls(self):
        self._rest_inbound_socket.log.debug("RESTAPI HangupAllCalls with %s" \
                                        % str(request.form.items()))
        """Hangup All Live Calls in the system
        """
        msg = "All Calls Hungup"
        self._rest_inbound_socket.hangup_all_calls()
        return self.send_response(Success=True, Message=msg)

    @auth_protect
    def schedule_hangup(self):
        """Schedule Call Hangup
        Schedule an hangup on a call in the future.

        To schedule a hangup, you make an HTTP POST request to a
        resource URI.

        POST Parameters
        ---------------
        CallUUID: Unique Call ID to which the action should occur to.

        Time: When hanging up call in seconds.


        Returns a scheduled task with id SchedHangupId that you can use to cancel hangup.
        """

        msg = ""
        result = False
        sched_id = ""

        time = get_post_param(request, 'Time')
        call_uuid = get_post_param(request, 'CallUUID')

        if not call_uuid:
            msg = "CallUUID Parameter must be present"
        elif not time:
            msg = "Time Parameter must be present"
        else:
            try:
                time = int(time)
                if time <= 0:
                    msg = "Time Parameter must be > 0 !"
                else:
                    sched_id = str(uuid.uuid1())
                    res = self._rest_inbound_socket.api("sched_api +%d %s uuid_kill %s ALLOTTED_TIMEOUT" \
                                                        % (time, sched_id, call_uuid))
                    if res.is_success():
                        msg = "ScheduleHangup Done with SchedHangupId %s" % sched_id
                        result = True
                    else:
                        msg = "ScheduleHangup Failed: %s" % res.get_response()
            except ValueError:
                msg = "Invalid Time Parameter !"
        return self.send_response(Success=result, Message=msg, SchedHangupId=sched_id)

    @auth_protect
    def cancel_scheduled_hangup(self):
        """Cancel a Scheduled Call Hangup
        Unschedule an hangup on a call.

        To unschedule a hangup, you make an HTTP POST request to a
        resource URI.

        POST Parameters
        ---------------
        SchedHangupId: id of the scheduled hangup.
        """
        self._rest_inbound_socket.log.debug("RESTAPI ScheduleHangup with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        sched_id = get_post_param(request, 'SchedHangupId')
        if not sched_id:
            msg = "SchedHangupId Parameter must be present"
        else:
            res = self._rest_inbound_socket.api("sched_del %s" % sched_id)
            if res.is_success():
                msg = "Scheduled Hangup Canceled"
                result = True
            else:
                msg = "Scheduled Hangup Cancelation Failed: %s" % res.get_response()
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def record_start(self):
        """RecordStart
        Start Recording a call

        POST Parameters
        ---------------
        CallUUID: Unique Call ID to which the action should occur to.
        FileFormat: file format, can be be "mp3" or "wav" (default "mp3")
        FilePath: complete file path to save the file to
        FileName: Default empty, if given this will be used for the recording
        TimeLimit: Max recording duration in seconds
        """
        self._rest_inbound_socket.log.debug("RESTAPI RecordStart with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        calluuid = get_post_param(request, 'CallUUID')
        fileformat = get_post_param(request, 'FileFormat')
        filepath = get_post_param(request, 'FilePath')
        filename = get_post_param(request, 'FileName')
        timelimit = get_post_param(request, 'TimeLimit')
        if not calluuid:
            msg = "CallUUID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not fileformat:
            fileformat = "mp3"
        if not fileformat in ("mp3", "wav"):
            msg = "FileFormat Parameter must be 'mp3' or 'wav'"
            return self.send_response(Success=result, Message=msg)
        if not timelimit:
            timelimit = 60
        else:
            try:
                timelimit = int(timelimit)
            except ValueError:
                msg = "RecordStart Failed: invalid TimeLimit '%s'" % str(timelimit)
                return self.send_response(Success=result, Message=msg)

        if filepath:
            filepath = os.path.normpath(filepath) + os.sep
        if not filename:
            filename = "%s_%s" % (datetime.now().strftime("%Y%m%d-%H%M%S"), calluuid)
        recordfile = "%s%s.%s" % (filepath, filename, fileformat)
        res = self._rest_inbound_socket.api("uuid_record %s start %s %d" \
                % (calluuid, recordfile, timelimit))
        if res.is_success():
            msg = "RecordStart Executed with RecordFile %s" % recordfile
            result = True
            return self.send_response(Success=result, Message=msg, RecordFile=recordfile)

        msg = "RecordStart Failed: %s" % res.get_response()
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def record_stop(self):
        """RecordStop
        Stop Recording a call

        POST Parameters
        ---------------
        CallUUID: Unique Call ID to which the action should occur to.
        RecordFile: full file path to the recording file (the one returned by RecordStart)
                    or 'all' to stop all current recordings on this call
        """
        self._rest_inbound_socket.log.debug("RESTAPI RecordStop with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        calluuid = get_post_param(request, 'CallUUID')
        recordfile = get_post_param(request, 'RecordFile')
        if not calluuid:
            msg = "CallUUID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not recordfile:
            msg = "RecordFile Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        res = self._rest_inbound_socket.api("uuid_record %s stop %s" \
                % (calluuid, recordfile))
        if res.is_success():
            msg = "RecordStop Executed"
            result = True
            return self.send_response(Success=result, Message=msg)

        msg = "RecordStop Failed: %s" % res.get_response()
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def conference_mute(self):
        """ConferenceMute
        Mute a Member in a Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        MemberID: conference member id or list of comma separated member ids to mute
                or 'all' to mute all members
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceMute with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        member_id = get_post_param(request, 'MemberID')
        members = []

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not member_id:
            msg = "MemberID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        # mute members
        for member in member_id.split(','):
            res = self._rest_inbound_socket.conference_api(room, "mute %s" % member, async=False)
            if not res or res[:2] != 'OK':
                self._rest_inbound_socket.log.warn("Conference Mute Failed for %s" % str(member))
            elif res.startswith('Conference %s not found' % str(room)) or res.startswith('Non-Existant'):
                self._rest_inbound_socket.log.warn("Conference Mute %s for %s" % (str(res), str(member)))
            else:
                self._rest_inbound_socket.log.debug("Conference Mute done for %s" % str(member))
                members.append(member)
        msg = "Conference Mute Executed"
        result = True
        return self.send_response(Success=result, Message=msg, MemberID=members)

    @auth_protect
    def conference_unmute(self):
        """ConferenceUnmute
        Unmute a Member in a Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        MemberID: conference member id or list of comma separated member ids to mute
                or 'all' to unmute all members
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceUnmute with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        member_id = get_post_param(request, 'MemberID')
        members = []

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not member_id:
            msg = "MemberID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        # unmute members
        for member in member_id.split(','):
            res = self._rest_inbound_socket.conference_api(room, "unmute %s" % member, async=False)
            if not res or res[:2] != 'OK':
                self._rest_inbound_socket.log.warn("Conference Unmute Failed for %s" % str(member))
            elif res.startswith('Conference %s not found' % str(room)) or res.startswith('Non-Existant'):
                self._rest_inbound_socket.log.warn("Conference Unmute %s for %s" % (str(res), str(member)))
            else:
                self._rest_inbound_socket.log.debug("Conference Unmute done for %s" % str(member))
                members.append(member)
        msg = "Conference Unmute Executed"
        result = True
        return self.send_response(Success=result, Message=msg, MemberID=members)

    @auth_protect
    def conference_kick(self):
        """ConferenceKick
        Kick a Member from a Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        MemberID: conference member id or list of comma separated member ids to mute
                or 'all' to kick all members
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceKick with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        member_id = get_post_param(request, 'MemberID')
        members = []

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not member_id:
            msg = "MemberID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        # kick members
        for member in member_id.split(','):
            res = self._rest_inbound_socket.conference_api(room, "kick %s" % member, async=False)
            if not res:
                self._rest_inbound_socket.log.warn("Conference Kick Failed for %s" % str(member))
            elif res.startswith('Conference %s not found' % str(room)) or res.startswith('Non-Existant'):
                self._rest_inbound_socket.log.warn("Conference Kick %s for %s" % (str(res), str(member)))
            else:
                self._rest_inbound_socket.log.debug("Conference Kick done for %s" % str(member))
                members.append(member)
        msg = "Conference Kick Executed"
        result = True
        return self.send_response(Success=result, Message=msg, MemberID=members)

    @auth_protect
    def conference_hangup(self):
        """ConferenceHangup
        Hangup a Member in Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        MemberID: conference member id or list of comma separated member ids to mute
                or 'all' to hangup all members
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceHangup with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        member_id = get_post_param(request, 'MemberID')
        members = []

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not member_id:
            msg = "MemberID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        # hangup members
        for member in member_id.split(','):
            res = self._rest_inbound_socket.conference_api(room, "hup %s" % member, async=False)
            if not res:
                self._rest_inbound_socket.log.warn("Conference Hangup Failed for %s" % str(member))
            elif res.startswith('Conference %s not found' % str(room)) or res.startswith('Non-Existant'):
                self._rest_inbound_socket.log.warn("Conference Hangup %s for %s" % (str(res), str(member)))
            else:
                self._rest_inbound_socket.log.debug("Conference Hangup done for %s" % str(member))
                members.append(member)
        msg = "Conference Hangup Executed"
        result = True
        return self.send_response(Success=result, Message=msg, MemberID=members)

    @auth_protect
    def conference_deaf(self):
        """ConferenceDeaf
        Deaf a Member in Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        MemberID: conference member id or list of comma separated member ids to mute
                or 'all' to deaf all members
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceDeaf with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        member_id = get_post_param(request, 'MemberID')
        members = []

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not member_id:
            msg = "MemberID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        # deaf members
        for member in member_id.split(','):
            res = self._rest_inbound_socket.conference_api(room, "deaf %s" % member, async=False)
            if not res or res[:2] != 'OK':
                self._rest_inbound_socket.log.warn("Conference Deaf Failed for %s" % str(member))
            elif res.startswith('Conference %s not found' % str(room)) or res.startswith('Non-Existant'):
                self._rest_inbound_socket.log.warn("Conference Deaf %s for %s" % (str(res), str(member)))
            else:
                self._rest_inbound_socket.log.debug("Conference Deaf done for %s" % str(member))
                members.append(member)
        msg = "Conference Deaf Executed"
        result = True
        return self.send_response(Success=result, Message=msg, MemberID=members)

    @auth_protect
    def conference_undeaf(self):
        """ConferenceUndeaf
        Undeaf a Member in Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        MemberID: conference member id or list of comma separated member ids to mute
                or 'all' to undeaf all members
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceUndeaf with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        member_id = get_post_param(request, 'MemberID')
        members = []

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        elif not member_id:
            msg = "MemberID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        # deaf members
        for member in member_id.split(','):
            res = self._rest_inbound_socket.conference_api(room, "undeaf %s" % member, async=False)
            if not res or res[:2] != 'OK':
                self._rest_inbound_socket.log.warn("Conference Undeaf Failed for %s" % str(member))
            elif res.startswith('Conference %s not found' % str(room)) or res.startswith('Non-Existant'):
                self._rest_inbound_socket.log.warn("Conference Undeaf %s for %s" % (str(res), str(member)))
            else:
                self._rest_inbound_socket.log.debug("Conference Undeaf done for %s" % str(member))
                members.append(member)
        msg = "Conference Undeaf Executed"
        result = True
        return self.send_response(Success=result, Message=msg, MemberID=members)

    @auth_protect
    def conference_record_start(self):
        """ConferenceRecordStart
        Start Recording Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        FileFormat: file format, can be be "mp3" or "wav" (default "mp3")
        FilePath: complete file path to save the file to
        FileName: Default empty, if given this will be used for the recording
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceRecordStart with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        fileformat = get_post_param(request, 'FileFormat')
        filepath = get_post_param(request, 'FilePath')
        filename = get_post_param(request, 'FileName')

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not fileformat:
            fileformat = "mp3"
        if not fileformat in ("mp3", "wav"):
            msg = "FileFormat Parameter must be 'mp3' or 'wav'"
            return self.send_response(Success=result, Message=msg)

        if filepath:
            filepath = os.path.normpath(filepath) + os.sep
        if not filename:
            filename = "%s_%s" % (datetime.now().strftime("%Y%m%d-%H%M%S"), room)
        recordfile = "%s%s.%s" % (filepath, filename, fileformat)

        res = self._rest_inbound_socket.conference_api(room, "record %s" % recordfile, async=False)
        if not res:
            msg = "Conference RecordStart Failed"
            result = False
            return self.send_response(Success=result, Message=msg)
        elif res.startswith('Conference %s not found' % str(room)):
            msg = "Conference RecordStart %s" % str(res)
            result = False
            return self.send_response(Success=result, Message=msg)
        msg = "Conference RecordStart Executed"
        result = True
        return self.send_response(Success=result, Message=msg, RecordFile=recordfile)

    @auth_protect
    def conference_record_stop(self):
        """ConferenceRecordStop
        Stop Recording Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        RecordFile: full file path to the recording file (the one returned by ConferenceRecordStart)
                    or 'all' to stop all current recordings on conference
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceRecordStop with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        recordfile = get_post_param(request, 'RecordFile')

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not recordfile:
            msg = "RecordFile Parameter must be present"
            return self.send_response(Success=result, Message=msg)

        res = self._rest_inbound_socket.conference_api(room,
                                        "norecord %s" % recordfile,
                                        async=False)
        if not res:
            msg = "Conference RecordStop Failed"
            result = False
            return self.send_response(Success=result, Message=msg)
        elif res.startswith('Conference %s not found' % str(room)):
            msg = "Conference RecordStop %s" % str(res)
            result = False
            return self.send_response(Success=result, Message=msg)
        msg = "Conference RecordStop Executed"
        result = True
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def conference_play(self):
        """ConferencePlay
        Play something into Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        FilePath: full path to file to be played
        MemberID: conference member id or 'all' to play file to all members
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferencePlay with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        filepath = get_post_param(request, 'FilePath')
        member_id = get_post_param(request, 'MemberID')

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not filepath:
            msg = "FilePath Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        filepath = get_resource(self._rest_inbound_socket, filepath)
        if not member_id:
            msg = "MemberID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if member_id == 'all':
            arg = "async"
        else:
            arg = member_id
        if is_valid_url(filepath):
            url = normalize_url_space(filepath)
            filepath = get_resource(self, url)
            res = self._rest_inbound_socket.conference_api(room, "play '%s' %s" % (filepath, arg), async=False)
        else:
            res = self._rest_inbound_socket.conference_api(room, "play %s %s" % (filepath, arg), async=False)
        if not res:
            msg = "Conference Play Failed"
            result = False
            return self.send_response(Success=result, Message=msg)
        elif res.startswith('Conference %s not found' % str(room)) or res.startswith('Non-Existant'):
            msg = "Conference Play %s" % str(res)
            result = False
            return self.send_response(Success=result, Message=msg)
        msg = "Conference Play Executed"
        result = True
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def conference_speak(self):
        """ConferenceSpeak
        Say something into Conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        Text: text to say in conference
        MemberID: conference member id or 'all' to say text to all members
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceSpeak with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        text = get_post_param(request, 'Text')
        member_id = get_post_param(request, 'MemberID')

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not text:
            msg = "Text Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not member_id:
            msg = "MemberID Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if member_id == 'all':
            res = self._rest_inbound_socket.conference_api(room, "say '%s'" % text, async=False)
        else:
            res = self._rest_inbound_socket.conference_api(room, "saymember %s '%s'" % (member_id, text), async=False)
        if not res:
            msg = "Conference Speak Failed"
            result = False
            return self.send_response(Success=result, Message=msg)
        elif res.startswith('Conference %s not found' % str(room)) or res.startswith('Non-Existant'):
            msg = "Conference Speak %s" % str(res)
            result = False
            return self.send_response(Success=result, Message=msg)
        msg = "Conference Speak Executed"
        result = True
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def conference_list_members(self):
        """ConferenceListMembers
        List all or some members in a conference

        POST Parameters
        ---------------
        ConferenceName: conference room name
        MemberFilter: a list of MemberID separated by comma.
                If set only get the members matching the MemberIDs in list.
                (default empty)
        CallUUIDFilter: a list of CallUUID separated by comma.
                If set only get the channels matching the CallUUIDs in list.
                (default empty)
        MutedFilter: 'true' or 'false', only get muted members or not (default 'false')
        DeafFilter: 'true' or 'false', only get deaf members or not (default 'false')

        All Filter parameters can be mixed.
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceListMembers with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        room = get_post_param(request, 'ConferenceName')
        members = get_post_param(request, 'MemberFilter')
        calluuids = get_post_param(request, 'CallUUIDFilter')
        onlymuted = get_post_param(request, 'MutedFilter') == 'true'
        onlydeaf = get_post_param(request, 'DeafFilter') == 'true'

        if not room:
            msg = "ConferenceName Parameter must be present"
            return self.send_response(Success=result, Message=msg)
        if not members:
            members = None
        res = self._rest_inbound_socket.conference_api(room, "xml_list", async=False)
        if not res:
            msg = "Conference ListMembers Failed"
            result = False
            return self.send_response(Success=result, Message=msg)
        elif res.startswith('Conference %s not found' % str(room)):
            msg = "Conference ListMembers %s" % str(res)
            result = False
            return self.send_response(Success=result, Message=msg)
        try:
            member_list = self._parse_conference_xml_list(res, member_filter=members,
                                uuid_filter=calluuids, mute_filter=onlymuted, deaf_filter=onlydeaf)
            msg = "Conference ListMembers Executed"
            result = True
            return self.send_response(Success=result, Message=msg, List=member_list)
        except Exception, e:
            msg = "Conference ListMembers Failed to parse result"
            result = False
            self._rest_inbound_socket.log.error("Conference ListMembers Failed -- %s" % str(e))
            return self.send_response(Success=result, Message=msg)

    @auth_protect
    def conference_list(self):
        """ConferenceList
        List all conferences with members

        POST Parameters
        ---------------
        MemberFilter: a list of MemberID separated by comma.
                If set only get the members matching the MemberIDs in list.
                (default empty)
        CallUUIDFilter: a list of CallUUID separated by comma.
                If set only get the channels matching the CallUUIDs in list.
                (default empty)
        MutedFilter: 'true' or 'false', only get muted members or not (default 'false')
        DeafFilter: 'true' or 'false', only get deaf members or not (default 'false')

        All Filter parameters can be mixed.
        """
        self._rest_inbound_socket.log.debug("RESTAPI ConferenceList with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        members = get_post_param(request, 'MemberFilter')
        calluuids = get_post_param(request, 'CallUUIDFilter')
        onlymuted = get_post_param(request, 'MutedFilter') == 'true'
        onlydeaf = get_post_param(request, 'DeafFilter') == 'true'

        res = self._rest_inbound_socket.conference_api(room='', command="xml_list", async=False)
        if res:
            try:
                confs = self._parse_conference_xml_list(res, member_filter=members,
                                uuid_filter=calluuids, mute_filter=onlymuted, deaf_filter=onlydeaf)
                msg = "Conference List Executed"
                result = True
                return self.send_response(Success=result, Message=msg, List=confs)
            except Exception, e:
                msg = "Conference List Failed to parse result"
                result = False
                self._rest_inbound_socket.log.error("Conference List Failed -- %s" % str(e))
                return self.send_response(Success=result, Message=msg)
        msg = "Conference List Failed"
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def group_call(self):
        """Make Outbound Group Calls in one request
        Allow initiating group outbound calls via the REST API. To make a
        group outbound call, make an HTTP POST request to the resource URI.

        POST Parameters
        ----------------

        Required Parameters - You must POST the following parameters:

        Delimiter: Any special character (with the exception of '/' and ',')
        which will be used as a delimiter for the string of parameters below. E.g. '<'

        From: The phone number to use as the caller id for the call without
        the leading +

        To: The numbers to call without the leading +

        Gateways: Comma separated string of gateways to dial the call out

        GatewayCodecs: Comma separated string of codecs for gateways

        GatewayTimeouts: Comma separated string of timeouts for gateways

        GatewayRetries: Comma separated string of retries for gateways

        AnswerUrl: The URL that should be requested for XML when the call
        connects. Similar to the URL for your inbound calls

        TimeLimit: Define the max time of the calls

        Optional Parameters - You may POST the following parameters:

        [CallerName]: the caller name to use for call

        [HangupUrl]: URL that Plivo will notify to, with POST params when
        calls ends

        [RingUrl]: URL that Plivo will notify to, with POST params when
        calls starts ringing

        [HangupOnRing]: If Set to 0 we will hangup as soon as the number ring,
        if set to value X we will wait X seconds when start ringing and then
        hang up

        [ExtraDialString]: Additional Originate dialstring to be executed
        while making the outbound call

        [RejectCauses]: List of reject causes for each number (comma ',' separated).
        If attempt to call one number failed with a reject cause matching in this parameter,
        there isn't more call attempts for this number.

        [SendDigits]: A string of keys to dial after connecting to the number.
        Valid digits in the string include: any digit (0-9), '#' and '*'.
        Very useful, if you want to connect to a company phone number,
        and wanted to dial extension 1234 and then the pound key,
        use SendDigits=1234#.
        Remember to URL-encode this string, since the '#' character has
        special meaning in a URL.
        To wait before sending DTMF to the extension, you can add leading 'w' or 'W' characters.
        Each 'w' character waits 0.5 seconds instead of sending a digit.
        Each 'W' character waits 1.0 seconds instead of sending a digit.
        You can also add the tone duration in ms by appending @[duration] after string.
        Eg. 1w2w3@1000

        [SendOnPreanswer]: SendDigits on early media instead of answer.

        [ConfirmSound]: Sound to play to called party before bridging call.

        [ConfirmKey]: A one key digits the called party must press to accept the call.
        """
        self._rest_inbound_socket.log.debug("RESTAPI GroupCall with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False
        request_uuid = str(uuid.uuid1())
        default_reject_causes = "NO_ANSWER ORIGINATOR_CANCEL ALLOTTED_TIMEOUT NO_USER_RESPONSE CALL_REJECTED"

        caller_id = get_post_param(request, 'From')
        to_str = get_post_param(request, 'To')
        gw_str = get_post_param(request, 'Gateways')
        answer_url = get_post_param(request, 'AnswerUrl')
        delimiter = get_post_param(request, 'Delimiter')

        if delimiter in (',', '/'):
            msg = "This Delimiter is not allowed"
            return self.send_response(Success=result, Message=msg)
        elif not caller_id or not to_str or not gw_str or not answer_url or not delimiter:
            msg = "Mandatory Parameters Missing"
            return self.send_response(Success=result, Message=msg)
        elif not is_valid_url(answer_url):
            msg = "AnswerUrl is not Valid"
            return self.send_response(Success=result, Message=msg)

        hangup_url = get_post_param(request, 'HangupUrl')
        ring_url = get_post_param(request, 'RingUrl')
        if hangup_url and not is_valid_url(hangup_url):
            msg = "HangupUrl is not Valid"
            return self.send_response(Success=result, Message=msg)
        elif ring_url and not is_valid_url(ring_url):
            msg = "RingUrl is not Valid"
            return self.send_response(Success=result, Message=msg)


        extra_dial_string = get_post_param(request, 'ExtraDialString')
        gw_codecs_str = get_post_param(request, 'GatewayCodecs')
        gw_timeouts_str = get_post_param(request, 'GatewayTimeouts')
        gw_retries_str = get_post_param(request, 'GatewayRetries')
        send_digits_str = get_post_param(request, 'SendDigits')
        send_preanswer_str = get_post_param(request, 'SendOnPreanswer')
        time_limit_str = get_post_param(request, 'TimeLimit')
        hangup_on_ring_str = get_post_param(request, 'HangupOnRing')
        confirm_sound = get_post_param(request, 'ConfirmSound')
        confirm_key = get_post_param(request, 'ConfirmKey')
        reject_causes = get_post_param(request, 'RejectCauses')
        caller_name_str = get_post_param(request, 'CallerName')
        accountsid = get_post_param(request, 'AccountSID') or ''
        if reject_causes:
            reject_causes = " ".join([ r.strip() for r in reject_causes.split(',') ])

        to_str_list = to_str.split(delimiter)
        gw_str_list = gw_str.split(delimiter)
        gw_codecs_str_list = gw_codecs_str.split(delimiter)
        gw_timeouts_str_list = gw_timeouts_str.split(delimiter)
        gw_retries_str_list = gw_retries_str.split(delimiter)
        send_digits_list = send_digits_str.split(delimiter)
        send_preanswer_list = send_preanswer_str.split(delimiter)
        time_limit_list = time_limit_str.split(delimiter)
        hangup_on_ring_list = hangup_on_ring_str.split(delimiter)
        caller_name_list = caller_name_str.split(delimiter)

        if len(to_str_list) < 2:
            msg = "GroupCall should be used for at least 2 numbers"
            return self.send_response(Success=result, Message=msg)
        elif len(to_str_list) != len(gw_str_list):
            msg = "'To' parameter length does not match 'Gateways' Length"
            return self.send_response(Success=result, Message=msg)


        # set group
        group_list = []
        group_options = []
        # set confirm
        confirm_options = ""
        if confirm_sound:
            confirm_sounds = self._prepare_play_string(confirm_sound)
            if confirm_sounds:
                play_str = '!'.join(confirm_sounds)
                play_str = "file_string://silence_stream://1!%s" % play_str
                # Use confirm key if present else just play music
                if confirm_key:
                    confirm_music_str = "group_confirm_file=%s" % play_str
                    confirm_key_str = "group_confirm_key=%s" % confirm_key
                else:
                    confirm_music_str = "group_confirm_file=playback %s" % play_str
                    confirm_key_str = "group_confirm_key=exec"
                # Cancel the leg timeout after the call is answered
                confirm_cancel = "group_confirm_cancel_timeout=1"
                confirm_options = "%s,%s,%s,playback_delimiter=!" % (confirm_music_str, confirm_key_str, confirm_cancel)
        group_options.append(confirm_options)

        # build calls
        for to in to_str_list:
            try:
                gw = gw_str_list.pop(0)
            except IndexError:
                break
            try:
                gw_codecs = gw_codecs_str_list.pop(0)
            except IndexError:
                gw_codecs = ""
            try:
                gw_timeouts = gw_timeouts_str_list.pop(0)
            except IndexError:
                gw_timeouts = ""
            try:
                gw_retries = gw_retries_str_list.pop(0)
            except IndexError:
                gw_retries = ""
            try:
                send_digits = send_digits_list.pop(0)
            except IndexError:
                send_digits = ""
            try:
                send_preanswer = send_preanswer_list.pop(0) == 'true'
            except IndexError:
                send_preanswer = ""
            try:
                time_limit = time_limit_list.pop(0)
            except IndexError:
                time_limit = ""
            try:
                hangup_on_ring = hangup_on_ring_list.pop(0)
            except IndexError:
                hangup_on_ring = ""
            try:
                caller_name = caller_name_list.pop(0)
            except IndexError:
                caller_name = ""

            call_req = self._prepare_call_request(
                        caller_id, caller_name, to, extra_dial_string,
                        gw, gw_codecs, gw_timeouts, gw_retries,
                        send_digits, send_preanswer, time_limit, hangup_on_ring,
                        answer_url, ring_url, hangup_url, accountsid)
            group_list.append(call_req)

        # now do the calls !
        if self._rest_inbound_socket.group_originate(request_uuid, group_list, group_options, reject_causes):
            msg = "GroupCall Request Executed"
            result = True
            return self.send_response(Success=result, Message=msg, RequestUUID=request_uuid)

        msg = "GroupCall Request Failed"
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def play(self):
        """Play something to a Call or bridged leg or both legs.
        Allow playing a sound to a Call via the REST API. To play sound,
        make an HTTP POST request to the resource URI.

        POST Parameters
        ----------------

        Required Parameters - You must POST the following parameters:

        CallUUID: Unique Call ID to which the action should occur to.

        Sounds: Comma separated list of sound files to play.

        Optional Parameters:

        [Length]: number of seconds before terminating sounds.

        [Legs]: 'aleg'|'bleg'|'both'. On which leg(s) to play something.
                'aleg' means only play on the Call.
                'bleg' means only play on the bridged leg of the Call.
                'both' means play on the Call and the bridged leg of the Call.
                Default is 'aleg' .

        [Loop]: 'true'|'false'. Play sound loop indefinitely (default 'false')

        [Mix]: 'true'|'false'. Mix with current audio stream (default 'true')

        [Delimiter]: The delimiter used in the sounds list (default: ',')

        """
        self._rest_inbound_socket.log.debug("RESTAPI Play with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        calluuid = get_post_param(request, 'CallUUID')
        sounds = get_post_param(request, 'Sounds')
        legs = get_post_param(request, 'Legs')
        length = get_post_param(request, 'Length')
        loop = get_post_param(request, 'Loop') == 'true'
        mix = get_post_param(request, 'Mix')
        delimiter = get_post_param(request, 'Delimiter')
        
        if mix == 'false':
            mix = False
        else:
            mix = True

        if not calluuid:
            msg = "CallUUID Parameter Missing"
            return self.send_response(Success=result, Message=msg)
        if not sounds:
            msg = "Sounds Parameter Missing"
            return self.send_response(Success=result, Message=msg)
        if not legs:
            legs = 'aleg'
        if not length:
            length = 3600
        else:
            try:
                length = int(length)
            except (ValueError, TypeError):
                msg = "Length Parameter must be a positive integer"
                return self.send_response(Success=result, Message=msg)
            if length < 1:
                msg = "Length Parameter must be a positive integer"
                return self.send_response(Success=result, Message=msg)

        if not delimiter: delimiter = ','
        
        sounds_list = sounds.split(delimiter)
        if not sounds_list:
            msg = "Sounds Parameter is Invalid"
            return self.send_response(Success=result, Message=msg)

        # now do the job !
        if self._rest_inbound_socket.play_on_call(calluuid, sounds_list, legs,
                                        length=length, schedule=0, mix=mix, loop=loop):
            msg = "Play Request Executed"
            result = True
            return self.send_response(Success=result, Message=msg)
        msg = "Play Request Failed"
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def schedule_play(self):
        """Schedule playing something to a Call or bridged leg or both legs.
        Allow to schedule playing a sound to a Call via the REST API. To play sound,
        make an HTTP POST request to the resource URI.

        POST Parameters
        ----------------

        Required Parameters - You must POST the following parameters:

        CallUUID: Unique Call ID to which the action should occur to.

        Sounds: Comma separated list of sound files to play.

        Time: When playing sounds in seconds.

        Optional Parameters:

        [Length]: number of seconds before terminating sounds.

        [Legs]: 'aleg'|'bleg'|'both'. On which leg(s) to play something.
                'aleg' means only play on the Call.
                'bleg' means only play on the bridged leg of the Call.
                'both' means play on the Call and the bridged leg of the Call.
                Default is 'aleg' .

        [Loop]: 'true'|'false'. Play sound loop indefinitely (default 'false')

        [Mix]: 'true'|'false'. Mix with current audio stream (default 'true')

        Returns a scheduled task with id SchedPlayId that you can use to cancel play.
        """
        self._rest_inbound_socket.log.debug("RESTAPI SchedulePlay with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        calluuid = get_post_param(request, 'CallUUID')
        sounds = get_post_param(request, 'Sounds')
        legs = get_post_param(request, 'Legs')
        time = get_post_param(request, 'Time')
        length = get_post_param(request, 'Length')
        loop = get_post_param(request, 'Loop') == 'true'
        mix = get_post_param(request, 'Mix')
        if mix == 'false':
            mix = False
        else:
            mix = True

        if not calluuid:
            msg = "CallUUID Parameter Missing"
            return self.send_response(Success=result, Message=msg)
        if not sounds:
            msg = "Sounds Parameter Missing"
            return self.send_response(Success=result, Message=msg)
        if not legs:
            legs = 'aleg'
        if not time:
            msg = "Time Parameter Must be Present"
            return self.send_response(Success=result, Message=msg)
        try:
            time = int(time)
        except (ValueError, TypeError):
            msg = "Time Parameter is Invalid"
            return self.send_response(Success=result, Message=msg)
        if time < 1:
            msg = "Time Parameter must be > 0"
            return self.send_response(Success=result, Message=msg)
        if not length:
            length = 3600
        else:
            try:
                length = int(length)
            except (ValueError, TypeError):
                msg = "Length Parameter must be a positive integer"
                return self.send_response(Success=result, Message=msg)
            if length < 1:
                msg = "Length Parameter must be a positive integer"
                return self.send_response(Success=result, Message=msg)

        sounds_list = sounds.split(',')
        if not sounds_list:
            msg = "Sounds Parameter is Invalid"
            return self.send_response(Success=result, Message=msg)

        # now do the job !
        sched_id = self._rest_inbound_socket.play_on_call(calluuid, sounds_list, legs,
                                    length=length, schedule=time, mix=mix, loop=loop)
        if sched_id:
            msg = "SchedulePlay Request Done with SchedPlayId %s" % sched_id
            result = True
            return self.send_response(Success=result, Message=msg, SchedPlayId=sched_id)
        msg = "SchedulePlay Request Failed"
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def cancel_scheduled_play(self):
        """Cancel a Scheduled Call Play
        Unschedule a play on a call.

        To unschedule a play, you make an HTTP POST request to a
        resource URI.

        POST Parameters
        ---------------
        SchedPlayId: id of the scheduled play.
        """
        self._rest_inbound_socket.log.debug("RESTAPI CancelScheduledPlay with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        sched_id = get_post_param(request, 'SchedPlayId')
        if not sched_id:
            msg = "SchedPlayId Parameter must be present"
        else:
            res = self._rest_inbound_socket.api("sched_del %s" % sched_id)
            if res.is_success():
                msg = "Scheduled Play Canceled"
                result = True
            else:
                msg = "Scheduled Play Cancelation Failed: %s" % res.get_response()
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def play_stop(self):
        """Call PlayStop
        Stop a play on a call.

        To stop a play, you make an HTTP POST request to a
        resource URI.

        Notes:
            You can not stop a ScheduledPlay with PlayStop.
            PlayStop will stop play for both legs (aleg and bleg, if it exists).

        POST Parameters
        ---------------

        Required Parameters - You must POST the following parameters:

        CallUUID: Unique Call ID to which the action should occur to.

        """
        self._rest_inbound_socket.log.debug("RESTAPI PlayStop with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        calluuid = get_post_param(request, 'CallUUID')

        if not calluuid:
            msg = "CallUUID Parameter Missing"
            return self.send_response(Success=result, Message=msg)

        self._rest_inbound_socket.play_stop_on_call(calluuid)
        msg = "PlayStop executed"
        result = True
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def sound_touch(self):
        """Add audio effects on a Call

        To add audio effects on a Call, you make an HTTP POST request to a
        resource URI.

        POST Parameters
        ---------------

        Required Parameters - You must POST the following parameters:

        CallUUID: Unique Call ID to which the action should occur to.

        Optional Parameters:

        [AudioDirection]: 'in' or 'out'. Change incoming or outgoing audio stream. (default 'out')

        [PitchSemiTones]: Adjust the pitch in semitones, values should be between -14 and 14, default 0

        [PitchOctaves]: Adjust the pitch in octaves, values should be between -1 and 1, default 0

        [Pitch]: Set the pitch directly, value should be > 0, default 1 (lower = lower tone)

        [Rate]: Set the rate, value should be > 0, default 1 (lower = slower)

        [Tempo]: Set the tempo, value should be > 0, default 1 (lower = slower)

        """
        self._rest_inbound_socket.log.debug("RESTAPI SoundTouch with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        calluuid = get_post_param(request, 'CallUUID')
        audiodirection = get_post_param(request, 'AudioDirection')

        if not calluuid:
            msg = "CallUUID Parameter Missing"
            return self.send_response(Success=result, Message=msg)
        if not audiodirection:
            audiodirection = 'out'
        if not audiodirection in ('in', 'out'):
            msg = "AudioDirection Parameter Must be 'in' or 'out'"
            return self.send_response(Success=result, Message=msg)

        pitch_s = get_post_param(request, 'PitchSemiTones')
        if pitch_s:
            try:
                pitch_s = float(pitch_s)
                if not -14 <= pitch_s <= 14:
                    msg = "PitchSemiTones Parameter must be between -14 and 14"
                    return self.send_response(Success=result, Message=msg)
            except (ValueError, TypeError):
                msg = "PitchSemiTones Parameter must be float"
                return self.send_response(Success=result, Message=msg)

        pitch_o = get_post_param(request, 'PitchOctaves')
        if pitch_o:
            try:
                pitch_o = float(pitch_o)
                if not -1 <= pitch_o <= 1:
                    msg = "PitchOctaves Parameter must be between -1 and 1"
                    return self.send_response(Success=result, Message=msg)
            except (ValueError, TypeError):
                msg = "PitchOctaves Parameter must be float"
                return self.send_response(Success=result, Message=msg)

        pitch_p = get_post_param(request, 'Pitch')
        if pitch_p:
            try:
                pitch_p = float(pitch_p)
                if pitch_p <= 0:
                    msg = "Pitch Parameter must be > 0"
                    return self.send_response(Success=result, Message=msg)
            except (ValueError, TypeError):
                msg = "Pitch Parameter must be float"
                return self.send_response(Success=result, Message=msg)

        pitch_r = get_post_param(request, 'Rate')
        if pitch_r:
            try:
                pitch_r = float(pitch_r)
                if pitch_r <= 0:
                    msg = "Rate Parameter must be > 0"
                    return self.send_response(Success=result, Message=msg)
            except (ValueError, TypeError):
                msg = "Rate Parameter must be float"
                return self.send_response(Success=result, Message=msg)

        pitch_t = get_post_param(request, 'Tempo')
        if pitch_t:
            try:
                pitch_t = float(pitch_t)
                if pitch_t <= 0:
                    msg = "Tempo Parameter must be > 0"
                    return self.send_response(Success=result, Message=msg)
            except (ValueError, TypeError):
                msg = "Tempo Parameter must be float"
                return self.send_response(Success=result, Message=msg)

        if self._rest_inbound_socket.sound_touch(calluuid,
                        direction=audiodirection, s=pitch_s,
                        o=pitch_o, p=pitch_p, r=pitch_r, t=pitch_t):
            msg = "SoundTouch executed"
            result = True
        else:
            msg = "SoundTouch Failed"
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def sound_touch_stop(self):
        """Remove audio effects on a Call

        To remove audio effects on a Call, you make an HTTP POST request to a
        resource URI.

        POST Parameters
        ---------------

        Required Parameters - You must POST the following parameters:

        CallUUID: Unique Call ID to which the action should occur to.
        """
        self._rest_inbound_socket.log.debug("RESTAPI SoundTouchStop with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        calluuid = get_post_param(request, 'CallUUID')
        if not calluuid:
            msg = "CallUUID Parameter Missing"
            return self.send_response(Success=result, Message=msg)
        cmd = "soundtouch %s stop" % calluuid
        bg_api_response = self._rest_inbound_socket.bgapi(cmd)
        job_uuid = bg_api_response.get_job_uuid()
        if not job_uuid:
            self._rest_inbound_socket.log.error("SoundTouchStop Failed '%s' -- JobUUID not received" % cmd)
            msg = "SoundTouchStop Failed"
            return self.send_response(Success=result, Message=msg)
        msg = "SoundTouchStop executed"
        result = True
        return self.send_response(Success=result, Message=msg)

    @auth_protect
    def send_digits(self):
        """Send DTMFs to a Call.

        To send DTMFs to a Call, you make an HTTP POST request to a
        resource URI.

        POST Parameters
        ---------------

        Required Parameters - You must POST the following parameters:

        CallUUID: Unique Call ID to which the action should occur to.

        Digits: A string of keys to send.
        Valid digits in the string include: any digit (0-9), '#' and '*'.
        Remember to URL-encode this string, since the '#' character has special meaning in a URL.
        To wait before sending DTMF to the extension, you can add leading 'w' or 'W' characters.
        Each 'w' character waits 0.5 seconds instead of sending a digit.
        Each 'W' character waits 1.0 seconds instead of sending a digit.
        You can also add the tone duration in ms by appending @[duration] after string.
        Eg. 1w2W3@1000

        Optional Parameters:

        [Leg]: 'aleg'|'bleg'. On which leg(s) to send DTMFs.
                'aleg' means only send to the Call.
                'bleg' means only send to the bridged leg of the Call.
                Default is 'aleg' .
        """
        self._rest_inbound_socket.log.debug("RESTAPI SendDigits with %s" \
                                        % str(request.form.items()))
        msg = ""
        result = False

        calluuid = get_post_param(request, 'CallUUID')
        if not calluuid:
            msg = "CallUUID Parameter Missing"
            return self.send_response(Success=result, Message=msg)
        digits = get_post_param(request, 'Digits')
        if not digits:
            msg = "Digits Parameter Missing"
            return self.send_response(Success=result, Message=msg)

        leg = get_post_param(request, 'Leg')
        if not leg:
            leg = 'aleg'
        if leg == 'aleg':
            cmd = "uuid_send_dtmf %s %s" % (calluuid, digits)
        elif leg == 'bleg':
            cmd = "uuid_recv_dtmf %s %s" % (calluuid, digits)
        else:
            msg = "Invalid Leg Parameter"
            return self.send_response(Success=result, Message=msg)

        res = self._rest_inbound_socket.bgapi(cmd)
        job_uuid = res.get_job_uuid()
        if not job_uuid:
            self._rest_inbound_socket.log.error("SendDigits Failed -- JobUUID not received" % job_uuid)
            msg = "SendDigits Failed"
            return self.send_response(Success=result, Message=msg)

        msg = "SendDigits executed"
        result = True
        return self.send_response(Success=result, Message=msg)


########NEW FILE########
__FILENAME__ = apiserver
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details

from gevent import monkey
monkey.patch_all()

import grp
import os
import pwd
import signal
import sys
import optparse

from flask import Flask
import gevent
from gevent.wsgi import WSGIServer
from gevent.pywsgi import WSGIServer as PyWSGIServer

from plivo.core.errors import ConnectError
from plivo.rest.freeswitch.api import PlivoRestApi
from plivo.rest.freeswitch.inboundsocket import RESTInboundSocket
from plivo.rest.freeswitch import urls, helpers
import plivo.utils.daemonize
from plivo.utils.logger import StdoutLogger, FileLogger, SysLogger, DummyLogger, HTTPLogger


class PlivoRestServer(PlivoRestApi):
    """Class PlivoRestServer"""
    name = 'PlivoRestServer'
    default_http_method = 'POST'

    def __init__(self, configfile, daemon=False,
                        pidfile='/tmp/plivo_rest.pid'):
        """Initialize main properties such as daemon, pidfile, config, etc...

        This will init the http server that will provide the Rest interface,
        the rest server is configured on HTTP_ADDRESS

        Extra:
        * FS_INBOUND_ADDRESS : Define the event_socket interface to connect to
        in order to initialize CallSession with Freeswitch

        * FS_OUTBOUND_ADDRESS : Define where on which address listen to
        initialize event_socket session with Freeswitch in order to control
        new CallSession

        """
        self._daemon = daemon
        self._run = False
        self._pidfile = pidfile
        self.configfile = configfile
        self._wsgi_mode = WSGIServer
        self._ssl_cert = None
        self._ssl = False
        # create flask app
        self.app = Flask(self.name)

        # load config
        self._config = None
        self.cache = {}
        self.load_config()

        # create inbound socket instance
        self._rest_inbound_socket = RESTInboundSocket(server=self)
        # expose API functions to flask app
        for path, func_desc in urls.URLS.iteritems():
            func, methods = func_desc
            fn = getattr(self, func.__name__)
            self.app.add_url_rule(path, func.__name__, fn, methods=methods)
        # create WSGI Server
        if self._ssl and self._ssl_cert and helpers.file_exists(self._ssl_cert):
            self._wsgi_mode = PyWSGIServer
            self.log.info("Listening HTTPS")
            self.log.info("Force %s mode with HTTPS" % str(self._wsgi_mode))
            self.http_server = self._wsgi_mode((self.http_host, self.http_port),
                                               self.app, log=self.log,
                                               certfile=self._ssl_cert)
        else:
            self.log.info("Listening HTTP")
            self.log.info("%s mode set" % str(self._wsgi_mode))
            self.http_server = self._wsgi_mode((self.http_host, self.http_port),
                                               self.app, log=self.log)

    def get_log(self):
        return self.log

    def get_config(self):
        return self._config

    def get_cache(self):
        return self.cache

    def create_logger(self, config):
        """This will create a logger using helpers.PlivoConfig instance

        Based on the settings in the configuration file,
        LOG_TYPE will determine if we will log in file, syslog, stdout, http or dummy (no log)
        """
        if self._daemon is False:
            logtype = config.get('rest_server', 'LOG_TYPE')
            if logtype == 'dummy':
                new_log = DummyLogger()
            else:
                new_log = StdoutLogger()
            new_log.set_debug()
            self.app.debug = True
            self.log = new_log
        else:
            logtype = config.get('rest_server', 'LOG_TYPE')
            if logtype == 'file':
                logfile = config.get('rest_server', 'LOG_FILE')
                new_log = FileLogger(logfile)
            elif logtype == 'syslog':
                syslogaddress = config.get('rest_server', 'SYSLOG_ADDRESS')
                syslogfacility = config.get('rest_server', 'SYSLOG_FACILITY')
                new_log = SysLogger(syslogaddress, syslogfacility)
            elif logtype == 'dummy':
                new_log = DummyLogger()
            elif logtype == 'http':
                url = config.get('rest_server', 'HTTP_LOG_URL')
                method = config.get('rest_server', 'HTTP_LOG_METHOD')
                fallback_file = config.get('rest_server', 'HTTP_LOG_FILE_FAILURE')
                new_log = HTTPLogger(url=url, method=method, fallback_file=fallback_file)
            else:
                new_log = StdoutLogger()
            log_level = config.get('rest_server', 'LOG_LEVEL', default='INFO')
            if log_level == 'DEBUG' or self._trace is True:
                new_log.set_debug()
                self.app.debug = True
            elif log_level == 'INFO':
                new_log.set_info()
                self.app.debug = False
            elif log_level == 'ERROR':
                new_log.set_error()
                self.app.debug = False
            elif log_level in ('WARN', 'WARNING'):
                new_log.set_warn()
                self.app.debug = False

        new_log.name = self.name
        self.log = new_log
        self.app._logger = self.log

    def load_config(self, reload=False):
        # backup config
        backup_config = self._config
        # create config
        config = helpers.PlivoConfig(self.configfile)

        try:
            # read config
            config.read()

            # set trace flag
            self._trace = config.get('rest_server', 'TRACE', default='false') == 'true'
            self.key = config.get('common', 'AUTH_ID', default='')
            self.secret = config.get('common', 'AUTH_TOKEN', default='')
            self.proxy_url = config.get('common', 'PROXY_URL', default=None)
            allowed_ips = config.get('rest_server', 'ALLOWED_IPS', default='')
            if allowed_ips:
                self.allowed_ips = allowed_ips.split(",")

            if not reload:
                # create first logger if starting
                self.create_logger(config=config)
                self.log.info("Starting ...")
                self.log.warn("Logger %s" % str(self.log))

                self.app.secret_key = config.get('rest_server', 'SECRET_KEY')
                self.app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
                self.http_address = config.get('rest_server', 'HTTP_ADDRESS')
                self.http_host, http_port = self.http_address.split(':', 1)
                self.http_port = int(http_port)

                self.fs_inbound_address = config.get('rest_server', 'FS_INBOUND_ADDRESS')
                self.fs_host, fs_port = self.fs_inbound_address.split(':', 1)
                self.fs_port = int(fs_port)

                self.fs_password = config.get('rest_server', 'FS_INBOUND_PASSWORD')

                # get outbound socket host/port
                self.fs_out_address = config.get('outbound_server', 'FS_OUTBOUND_ADDRESS')
                self.fs_out_host, self.fs_out_port  = self.fs_out_address.split(':', 1)

                # if outbound host is 0.0.0.0, send to 127.0.0.1
                if self.fs_out_host == '0.0.0.0':
                    self.fs_out_address = '127.0.0.1:%s' % self.fs_out_port
                # set wsgi mode
                _wsgi_mode = config.get('rest_server', 'WSGI_MODE', default='wsgi')
                if _wsgi_mode in ('pywsgi', 'python', 'py'):
                    self._wsgi_mode = PyWSGIServer
                else:
                    self._wsgi_mode = WSGIServer
                # set ssl or not
                self._ssl = config.get('rest_server', 'SSL', default='false') == 'true'
                self._ssl_cert = config.get('rest_server', 'SSL_CERT', default='')


            self.default_answer_url = config.get('common', 'DEFAULT_ANSWER_URL')

            self.default_hangup_url = config.get('common', 'DEFAULT_HANGUP_URL', default='')

            self.default_http_method = config.get('common', 'DEFAULT_HTTP_METHOD', default='')
            if not self.default_http_method in ('GET', 'POST'):
                self.default_http_method = 'POST'

            self.extra_fs_vars = config.get('common', 'EXTRA_FS_VARS', default='')

            # get call_heartbeat url
            self.call_heartbeat_url = config.get('rest_server', 'CALL_HEARTBEAT_URL', default='')

            # get record url
            self.record_url = config.get('rest_server', 'RECORD_URL', default='')

            # load cache params
            # load cache params
            self.cache['url'] = config.get('common', 'CACHE_URL', default='')
            self.cache['script'] = config.get('common', 'CACHE_SCRIPT', default='')
            if not self.cache['url'] or not self.cache['script']:
                self.cache = {}

            # get pid file for reloading outbound server (ugly hack ...)
            try:
                self.fs_out_pidfile = self._pidfile.replace('rest-', 'outbound-')
            except Exception, e:
                self.fs_out_pidfile = None

            # create new logger if reloading
            if reload:
                self.create_logger(config=config)
                self.log.warn("New logger %s" % str(self.log))

            # set new config
            self._config = config
            self.log.info("Config : %s" % str(self._config.dumps()))

        except Exception, e:
            if backup_config:
                self._config = backup_config
                self.load_config()
                self.log.warn("Error reloading config: %s" % str(e))
                self.log.warn("Rollback to the last config")
                self.log.info("Config : %s" % str(self._config.dumps()))
            else:
                sys.stderr.write("Error loading config: %s" % str(e))
                sys.stderr.flush()
                raise e

    def reload(self):
        self.log.warn("Reload ...")
        self.load_config(reload=True)
        self._rest_inbound_socket.log = self.log
        self.log.warn("Reload done")

    def do_daemon(self):
        """This will daemonize the current application

        Two settings from our configuration files are also used to run the
        daemon under a determine user & group.

        USER : determine the user running the daemon
        GROUP : determine the group running the daemon
        """
        # get user/group from config
        user = self._config.get('rest_server', 'USER', default=None)
        group = self._config.get('rest_server', 'GROUP', default=None)
        if not user or not group:
            uid = os.getuid()
            user = pwd.getpwuid(uid)[0]
            gid = os.getgid()
            group = grp.getgrgid(gid)[0]
        # daemonize now
        plivo.utils.daemonize.daemon(user, group, path='/',
                                     pidfile=self._pidfile,
                                     other_groups=())

    def sig_term(self, *args):
        """if we receive a term signal, we will shutdown properly
        """
        self.log.warn("Shutdown ...")
        self.stop()
        sys.exit(0)

    def sig_hup(self, *args):
        self.reload()

    def stop(self):
        """Method stop stop the infinite loop from start method
        and close the socket
        """
        self._run = False
        self._rest_inbound_socket.exit()

    def start(self):
        """start method is where we decide to :
            * catch term signal
            * run as daemon
            * start the http server
            * connect to Freeswitch via our Inbound Socket interface
            * wait even if it takes forever, ever, ever, evveeerrr...
        """
        self.log.info("RESTServer starting ...")
        # catch SIG_TERM
        gevent.signal(signal.SIGTERM, self.sig_term)
        gevent.signal(signal.SIGHUP, self.sig_hup)
        # run
        self._run = True
        if self._daemon:
            self.do_daemon()
        # connection counter
        retries = 1
        # start http server
        self.http_proc = gevent.spawn(self.http_server.serve_forever)
        if self._ssl:
            self.log.info("RESTServer started at: 'https://%s'" % self.http_address)
        else:
            self.log.info("RESTServer started at: 'http://%s'" % self.http_address)
        # Start inbound socket
        try:
            while self._run:
                try:
                    self.log.info("Trying to connect to FreeSWITCH at: %s" \
                                            % self.fs_inbound_address)
                    self._rest_inbound_socket.connect()
                    # reset retries when connection is a success
                    retries = 1
                    self.log.info("Connected to FreeSWITCH")
                    # serve forever
                    self._rest_inbound_socket.serve_forever()
                except ConnectError, e:
                    if self._run is False:
                        break
                    self.log.error("Connect failed: %s" % str(e))
                # sleep after connection failure
                sleep_for = retries * 10
                self.log.error("Reconnecting in %d seconds" % sleep_for)
                gevent.sleep(sleep_for)
                # don't sleep more than 30 secs
                if retries < 3:
                    retries += 1
        except (SystemExit, KeyboardInterrupt):
            pass
        # kill http server
        self.http_proc.kill()
        # finish here
        self.log.info("RESTServer Exited")


def main():
    parser = optparse.OptionParser()
    parser.add_option("-c", "--configfile", action="store", type="string",
                      dest="configfile",
                      help="use plivo config file (argument is mandatory)",
                      metavar="CONFIGFILE")
    parser.add_option("-p", "--pidfile", action="store", type="string",
                      dest="pidfile",
                      help="write pid to PIDFILE (argument is mandatory)",
                      metavar="PIDFILE")
    (options, args) = parser.parse_args()

    configfile = options.configfile
    pidfile = options.pidfile

    if not configfile:
        configfile = './etc/plivo/default.conf'
        if not os.path.isfile(configfile):
            raise SystemExit("Error : Default config file mising at '%s'. Please specify -c <configfilepath>" %configfile)
    if not pidfile:
        pidfile='/tmp/plivo_rest.pid'

    server = PlivoRestServer(configfile=configfile, pidfile=pidfile,
                                                        daemon=False)
    server.start()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = cacheapi
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details

import base64
import re
import uuid
import os
import os.path
from datetime import datetime
import urllib
import urllib2
import urlparse
import traceback

import redis
import redis.exceptions
import flask
from flask import request
from werkzeug.datastructures import MultiDict
from werkzeug.exceptions import Unauthorized

# remove depracated warning in python2.6
try:
    from hashlib import md5 as _md5
except ImportError:
    import md5
    _md5 = md5.new

from plivo.rest.freeswitch.helpers import is_valid_url, get_conf_value, \
                                            get_post_param, get_http_param

MIME_TYPES = {'audio/mpeg': 'mp3',
              'audio/x-wav': 'wav',
              'application/srgs+xml': 'grxml',
              'application/x-jsgf': 'jsgf',
             }



def ip_protect(decorated_func):
    def wrapper(obj):
        if obj._validate_ip_auth():
            return decorated_func(obj)
    wrapper.__name__ = decorated_func.__name__
    wrapper.__doc__ = decorated_func.__doc__
    return wrapper



class UnsupportedResourceFormat(Exception):
    pass


class ResourceCache(object):
    """Uses redis cache as a backend for storing cached files infos and datas.
    """
    def __init__(self, redis_host='localhost', redis_port=6379, redis_db=0, redis_pw=None, 
                 proxy_url=None, http_timeout=60):
        self.host = redis_host
        self.port = redis_port
        self.db = redis_db
        self.pw = redis_pw
        self.proxy_url = proxy_url
        self.http_timeout = http_timeout

    def get_cx(self):
        return redis.Redis(host=self.host, port=self.port, db=self.db,
                            socket_timeout=5.0, password=self.pw)

    def get_resource_params(self, url):
        resource_key = self.get_resource_key(url)
        cx = self.get_cx()
        if cx.sismember("resource_key", resource_key):
            resource_type = cx.hget("resource_key:%s" % resource_key, "resource_type")
            etag = cx.hget("resource_key:%s" % resource_key, "etag")
            last_modified = cx.hget("resource_key:%s" % resource_key, "last_modified")
            return resource_key, resource_type, etag, last_modified
        else:
            return None, None, None, None

    def update_resource_params(self, resource_key, resource_type, etag, last_modified, buffer):
        if etag is None:
            etag = ""
        if last_modified is None:
            last_modified = ""
        cx = self.get_cx()
        if not cx.sismember("resource_key", resource_key):
            cx.sadd("resource_key", resource_key)
        cx.hset("resource_key:%s" % resource_key, "resource_type", resource_type)
        cx.hset("resource_key:%s" % resource_key, "etag", etag)
        cx.hset("resource_key:%s" % resource_key, "last_modified", last_modified)
        cx.hset("resource_key:%s" % resource_key, "file", buffer)
        cx.hset("resource_key:%s" % resource_key, "last_update_time", str(datetime.now().strftime('%s')))

    def delete_resource(self, resource_key):
        cx = self.get_cx()
        if cx.sismember("resource_key", resource_key):
            cx.srem("resource_key", resource_key)
            cx.delete("resource_key:%s" % resource_key)

    def cache_resource(self, url):
        if self.proxy_url is not None:
            proxy = urllib2.ProxyHandler({'http': self.proxy_url})
            opener = urllib2.build_opener(proxy)
            urllib2.install_opener(opener)
        request = urllib2.Request(url)
        user_agent = 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.835.35 Safari/535.1'
        request.add_header('User-Agent', user_agent)
        handler = urllib2.urlopen(request, timeout=self.http_timeout)
        try:
            resource_type = MIME_TYPES[handler.headers.get('Content-Type')]
            if not resource_type:
                raise UnsupportedResourceFormat("Resource format not found")
        except KeyError:
            raise UnsupportedResourceFormat("Resource format not supported")
        etag = handler.headers.get('ETag')
        last_modified = handler.headers.get('Last-Modified')
        resource_key = self.get_resource_key(url)
        stream = handler.read()
        self.update_resource_params(resource_key, resource_type, etag, last_modified, stream)
        return stream, resource_type

    def get_stream(self, resource_key):
        stream = self.get_cx().hget("resource_key:%s" % resource_key, "file")
        resource_type = self.get_cx().hget("resource_key:%s" % resource_key, "resource_type")
        return stream, resource_type

    def get_resource_key(self, url):
        return base64.urlsafe_b64encode(_md5(url).digest())

    def is_resource_updated(self, url, etag, last_modified):
        no_change = (False, None, None)
        # if no ETag, then check for 'Last-Modified' header
        if etag is not None and etag != "":
            request = urllib2.Request(url)
            request.add_header('If-None-Match', etag)
        elif last_modified is not None and last_modified != "":
            request = urllib2.Request(url)
            request.add_header('If-Modified-Since', last_modified)
        else:
            return no_change
        try:
            second_try = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            # if http code is 304, no change
            if e.code == 304:
                return no_change
        return True, etag, last_modified


def get_resource_type(server, url):
    resource_type = None
    resource_key, resource_type, etag, last_modified = server.cache.get_resource_params(url)
    if resource_type:
        return resource_type
    full_file_name, stream, resource_type = get_resource(server, url)
    return resource_type

def get_resource(server, url):
    if not url:
        return url
    full_file_name = url
    stream = ''
    resource_type = None

    if server.cache is not None:
        # don't do cache if not a remote file
        if not full_file_name[:7].lower() == "http://" \
            and not full_file_name[:8].lower() == "https://":
            return (full_file_name, stream, resource_type)

        rk = server.cache.get_resource_key(url)
        server.log.debug("Cache -- Resource key %s for %s" % (rk, url))
        try:
            resource_key, resource_type, etag, last_modified = server.cache.get_resource_params(url)
            if resource_key is None:
                server.log.info("Cache -- %s not found. Downloading" % url)
                try:
                    stream, resource_type = server.cache.cache_resource(url)
                except UnsupportedResourceFormat:
                    server.log.error("Cache -- Ignoring Unsupported File at - %s" % url)
            else:
                server.log.debug("Cache -- Checking if %s source is newer" % url)
                updated, new_etag, new_last_modified = server.cache.is_resource_updated(url, etag, last_modified)
                if not updated:
                    server.log.debug("Cache -- Using Cached %s" % url)
                    stream, resource_type = server.cache.get_stream(resource_key)
                else:
                    server.log.debug("Cache -- Updating Cached %s" % url)
                    try:
                        stream, resource_type = server.cache.cache_resource(url)
                    except UnsupportedResourceFormat:
                        server.log.error("Cache -- Ignoring Unsupported File at - %s" % url)
        except Exception, e:
            server.log.error("Cache -- Failure !")
            [ server.log.debug('Cache -- Error: %s' % line) for line in \
                            traceback.format_exc().splitlines() ]

    if stream:
        return (full_file_name, stream, resource_type)

    if full_file_name[:7].lower() == "http://":
        audio_path = full_file_name[7:]
        full_file_name = "shout://%s" % audio_path
    elif full_file_name[:8].lower() == "https://":
        audio_path = full_file_name[8:]
        full_file_name = "shout://%s" % audio_path

    return (full_file_name, stream, resource_type)



class PlivoCacheApi(object):
    _config = None
    log = None
    allowed_ips = []

    def _validate_ip_auth(self):
        """Verify request is from allowed ips
        """
        if not self.allowed_ips:
            return True
        remote_ip = request.remote_addr.strip()
        if remote_ip in self.allowed_ips:
            return True
        self.log.debug("IP Auth Failed: remote ip %s not in %s" % (remote_ip, str(self.allowed_ips)))
        raise Unauthorized("IP Auth Failed")

    @ip_protect
    def index(self):
        return "OK"

    @ip_protect
    def do_cache(self):
        url = get_http_param(request, "url")
        if not url:
            self.log.debug("No Url")
            return "NO URL", 404
        self.log.debug("Url is %s" % str(url))
        try:
            file_path, stream, resource_type = get_resource(self, url)
            if not stream:
                self.log.debug("Url %s: no stream" % str(url))
                return "NO STREAM", 404
            if resource_type == 'mp3':
                _type = 'audio/mp3'
            elif resource_type == 'wav':
                _type = 'audio/wav'
            elif resource_type == 'grxml':
                _type = 'application/srgs+xml'
            elif resource_type == 'jsgf':
                _type = 'application/x-jsgf'
            else:
                self.log.debug("Url %s: not supported format" % str(url))
                return "NOT SUPPORTED FORMAT", 404
            self.log.debug("Url %s: stream found" % str(url))
            return flask.Response(response=stream, status=200,
                                  headers=None, mimetype=_type,
                                  content_type=_type,
                                  direct_passthrough=False)
        except Exception, e:
            self.log.error("/Cache/ Error: %s" % str(e))
            [ self.log.error('/Cache/ Error: %s' % line) for line in \
                            traceback.format_exc().splitlines() ]
            raise e

    @ip_protect
    def do_cache_type(self):
        url = get_http_param(request, "url")
        if not url:
            self.log.debug("No Url")
            return "NO URL", 404
        self.log.debug("Url is %s" % str(url))
        try:
            resource_type = get_resource_type(self, url)
            if not resource_type:
                self.log.debug("Url %s: no type" % str(url))
                return "NO TYPE", 404
            self.log.debug("Url %s: type is %s" % (str(url), str(resource_type)))
            return flask.jsonify(CacheType=resource_type)
        except Exception, e:
            self.log.error("/CacheType/ Error: %s" % str(e))
            [ self.log.error('/CacheType/ Error: %s' % line) for line in \
                            traceback.format_exc().splitlines() ]
            raise e

    @ip_protect
    def do_reload_config(self):
        try:
            self.reload()
            return flask.jsonify(Success=True, Message="ReloadConfig done")
        except Exception, e:
            self.log.error("/ReloadConfig/ Error: %s" % str(e))
            [ self.log.error('/ReloadConfig/ Error: %s' % line) for line in \
                            traceback.format_exc().splitlines() ]
            raise e


########NEW FILE########
__FILENAME__ = cacheserver
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details

from gevent import monkey
monkey.patch_all()

import grp
import os
import pwd
import signal
import sys
import optparse

from flask import Flask
import gevent
from gevent.wsgi import WSGIServer
from gevent.pywsgi import WSGIServer as PyWSGIServer

from plivo.rest.freeswitch.cacheapi import PlivoCacheApi
import plivo.utils.daemonize
from plivo.rest.freeswitch import cacheurls, helpers, cacheapi
from plivo.utils.logger import StdoutLogger, FileLogger, SysLogger, DummyLogger, HTTPLogger


class PlivoCacheServer(PlivoCacheApi):
    """Class PlivoCacheServer"""
    name = 'PlivoCacheServer'

    def __init__(self, configfile, daemon=False,
                        pidfile='/tmp/plivo_cache.pid'):
        self._daemon = daemon
        self._run = False
        self._pidfile = pidfile
        self.configfile = configfile
        self._wsgi_mode = WSGIServer
        # create flask app
        self.app = Flask(self.name)

        # load config
        self.cache = None
        self._config = None
        self.load_config()

        # expose API functions to flask app
        for path, func_desc in cacheurls.URLS.iteritems():
            func, methods = func_desc
            fn = getattr(self, func.__name__)
            self.app.add_url_rule(path, func.__name__, fn, methods=methods)

        self.log.info("Listening HTTP")
        self.log.info("%s mode set" % str(self._wsgi_mode))
        self.http_server = self._wsgi_mode((self.http_host, self.http_port),
                                            self.app, log=self.log)

    def create_cache(self, config):
        # load cache params
        self.redis_host = config.get('cache_server', 'REDIS_HOST', default='')
        self.redis_port = config.get('cache_server', 'REDIS_PORT', default='')
        self.redis_db = config.get('cache_server', 'REDIS_DB', default='')
        self.redis_pw = config.get('cache_server', 'REDIS_PASSWORD', default=None)
        self.proxy_url = config.get('cache_server', 'PROXY_URL', default=None)
        self.http_timeout = int(config.get('cache_server', 'HTTP_TIMEOUT', default=60))
        if self.redis_host and self.redis_port and self.redis_db:
            self.cache = cacheapi.ResourceCache(self.redis_host,
                                        int(self.redis_port),
                                        int(self.redis_db),
                                        self.redis_pw,
                                        self.proxy_url,
                                        self.http_timeout)
            return True

        self.log.error("Cannot run cache server, cache not set !")
        raise Exception("Cannot run cache server, cache not set !")


    def get_log(self):
        return self.log

    def get_config(self):
        return self._config

    def get_cache(self):
        return self.cache

    def create_logger(self, config):
        """This will create a logger using helpers.PlivoConfig instance

        Based on the settings in the configuration file,
        LOG_TYPE will determine if we will log in file, syslog, stdout, http or dummy (no log)
        """
        if self._daemon is False:
            logtype = config.get('cache_server', 'LOG_TYPE')
            if logtype == 'dummy':
                new_log = DummyLogger()
            else:
                new_log = StdoutLogger()
            new_log.set_debug()
            self.app.debug = True
            self.log = new_log
        else:
            logtype = config.get('cache_server', 'LOG_TYPE')
            if logtype == 'file':
                logfile = config.get('cache_server', 'LOG_FILE')
                new_log = FileLogger(logfile)
            elif logtype == 'syslog':
                syslogaddress = config.get('cache_server', 'SYSLOG_ADDRESS')
                syslogfacility = config.get('cache_server', 'SYSLOG_FACILITY')
                new_log = SysLogger(syslogaddress, syslogfacility)
            elif logtype == 'dummy':
                new_log = DummyLogger()
            elif logtype == 'http':
                url = config.get('cache_server', 'HTTP_LOG_URL')
                method = config.get('cache_server', 'HTTP_LOG_METHOD')
                fallback_file = config.get('cache_server', 'HTTP_LOG_FILE_FAILURE')
                new_log = HTTPLogger(url=url, method=method, fallback_file=fallback_file)
            else:
                new_log = StdoutLogger()
            log_level = config.get('cache_server', 'LOG_LEVEL', default='INFO')
            if log_level == 'DEBUG':
                new_log.set_debug()
                self.app.debug = True
            elif log_level == 'INFO':
                new_log.set_info()
                self.app.debug = False
            elif log_level == 'ERROR':
                new_log.set_error()
                self.app.debug = False
            elif log_level in ('WARN', 'WARNING'):
                new_log.set_warn()
                self.app.debug = False

        new_log.name = self.name
        self.log = new_log
        self.app._logger = self.log

    def load_config(self, reload=False):
        # backup config
        backup_config = self._config
        # create config
        config = helpers.PlivoConfig(self.configfile)

        try:
            # read config
            config.read()

            if not reload:
                # create first logger if starting
                self.create_logger(config=config)
                self.log.info("Starting ...")
                self.log.warn("Logger %s" % str(self.log))

                self.app.secret_key = config.get('cache_server', 'SECRET_KEY')
                self.app.config['MAX_CONTENT_LENGTH'] = 1024 * 10240
                self.http_address = config.get('cache_server', 'HTTP_ADDRESS')
                self.http_host, http_port = self.http_address.split(':', 1)
                self.http_port = int(http_port)

                # load cache params
                self.redis_host = config.get('cache_server', 'REDIS_HOST', default='')
                self.redis_port = config.get('cache_server', 'REDIS_PORT', default='')
                self.redis_db = config.get('cache_server', 'REDIS_DB', default='')
                # create new cache
                self.create_cache(config=config)
                self.log.warn("Cache %s" % str(self.cache))

                # set wsgi mode
                _wsgi_mode = config.get('cache_server', 'WSGI_MODE', default='wsgi')
                if _wsgi_mode in ('pywsgi', 'python', 'py'):
                    self._wsgi_mode = PyWSGIServer
                else:
                    self._wsgi_mode = WSGIServer

            if reload:
                # create new logger if reloading
                self.create_logger(config=config)
                self.log.warn("New logger %s" % str(self.log))
                # create new cache
                self.create_cache(config=config)
                self.log.warn("New cache %s" % str(self.cache))


            # allowed ips to access cache server
            allowed_ips = config.get('common', 'ALLOWED_IPS', default='')
            if not allowed_ips.strip():
                self.allowed_ips = []
            else:
                self.allowed_ips = [ ip.strip() for ip in allowed_ips.split(',') ]

            # set new config
            self._config = config
            self.log.info("Config : %s" % str(self._config.dumps()))

        except Exception, e:
            if backup_config:
                self._config = backup_config
                self.load_config()
                self.log.warn("Error reloading config: %s" % str(e))
                self.log.warn("Rollback to the last config")
                self.log.info("Config : %s" % str(self._config.dumps()))
            else:
                sys.stderr.write("Error loading config: %s" % str(e))
                sys.stderr.flush()
                raise e

    def reload(self):
        self.log.warn("Reload ...")
        self.load_config(reload=True)
        self.log.warn("Reload done")

    def do_daemon(self):
        """This will daemonize the current application

        Two settings from our configuration files are also used to run the
        daemon under a determine user & group.

        USER : determine the user running the daemon
        GROUP : determine the group running the daemon
        """
        # get user/group from config
        user = self._config.get('cache_server', 'USER', default=None)
        group = self._config.get('cache_server', 'GROUP', default=None)
        if not user or not group:
            uid = os.getuid()
            user = pwd.getpwuid(uid)[0]
            gid = os.getgid()
            group = grp.getgrgid(gid)[0]
        # daemonize now
        plivo.utils.daemonize.daemon(user, group, path='/',
                                     pidfile=self._pidfile,
                                     other_groups=())

    def sig_term(self, *args):
        """if we receive a term signal, we will shutdown properly
        """
        self.log.warn("Shutdown ...")
        self.stop()
        sys.exit(0)

    def sig_hup(self, *args):
        self.reload()

    def stop(self):
        """Method stop stop the infinite loop from start method
        and close the socket
        """
        self._run = False

    def start(self):
        """start method is where we decide to :
            * catch term signal
            * run as daemon
            * start the http server
        """
        self.log.info("CacheServer starting ...")
        # catch SIG_TERM
        gevent.signal(signal.SIGTERM, self.sig_term)
        gevent.signal(signal.SIGHUP, self.sig_hup)
        # run
        self._run = True
        if self._daemon:
            self.do_daemon()
        # start http server
        self.log.info("CacheServer started at: 'http://%s'" % self.http_address)
        # Start cache server
        try:
            self.http_server.serve_forever()
        except (SystemExit, KeyboardInterrupt):
            pass
        # finish here
        self.log.info("CacheServer Exited")


def main():
    parser = optparse.OptionParser()
    parser.add_option("-c", "--configfile", action="store", type="string",
                      dest="configfile",
                      help="use plivo config file (argument is mandatory)",
                      metavar="CONFIGFILE")
    parser.add_option("-p", "--pidfile", action="store", type="string",
                      dest="pidfile",
                      help="write pid to PIDFILE (argument is mandatory)",
                      metavar="PIDFILE")
    (options, args) = parser.parse_args()

    configfile = options.configfile
    pidfile = options.pidfile

    if not configfile:
        configfile = './etc/plivo/default.conf'
        if not os.path.isfile(configfile):
            raise SystemExit("Error : Default config file mising at '%s'. Please specify -c <configfilepath>" %configfile)
    if not pidfile:
        pidfile='/tmp/plivo_cache.pid'

    server = PlivoCacheServer(configfile=configfile, pidfile=pidfile,
                                                    daemon=False)
    server.start()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = cacheurls
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details

from plivo.rest.freeswitch.cacheapi import PlivoCacheApi


URLS = {
        # API Index
        '/': (PlivoCacheApi.index, ['GET']),
        # API to get cache url content
        '/Cache/': (PlivoCacheApi.do_cache, ['GET']),
        # API to get cache url type
        '/CacheType/': (PlivoCacheApi.do_cache_type, ['GET']),
        # API to reload cache server config
        '/ReloadConfig/': (PlivoCacheApi.do_reload_config, ['GET', 'POST']),
       }

########NEW FILE########
__FILENAME__ = elements
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.


import os
import os.path
from datetime import datetime
import re
import uuid
try:
    import xml.etree.cElementTree as etree
except ImportError:
    from xml.etree.elementtree import ElementTree as etree

import gevent
from gevent import spawn_raw

from plivo.rest.freeswitch.helpers import is_valid_url, is_sip_url, \
                                        file_exists, normalize_url_space, \
                                        get_resource, get_grammar_resource, \
                                        HTTPRequest

from plivo.rest.freeswitch.exceptions import RESTFormatException, \
                                            RESTAttributeException, \
                                            RESTRedirectException, \
                                            RESTSIPTransferException, \
                                            RESTNoExecuteException, \
                                            RESTHangup


ELEMENTS_DEFAULT_PARAMS = {
        'Conference': {
                #'room': SET IN ELEMENT BODY
                'waitSound': '',
                'muted': 'false',
                'startConferenceOnEnter': 'true',
                'endConferenceOnExit': 'false',
                'stayAlone': 'true',
                'maxMembers': 200,
                'enterSound': '',
                'exitSound': '',
                'timeLimit': 0 ,
                'hangupOnStar': 'false',
                'recordFilePath': '',
                'recordFileFormat': 'mp3',
                'recordFileName': '',
                'action': '',
                'method': 'POST',
                'callbackUrl': '',
                'callbackMethod': 'POST',
                'digitsMatch': '',
                'floorEvent': 'false'
        },
        'Dial': {
                #action: DYNAMIC! MUST BE SET IN METHOD,
                'method': 'POST',
                'hangupOnStar': 'false',
                #callerId: DYNAMIC! MUST BE SET IN METHOD,
                #callerName: DYNAMIC! MUST BE SET IN METHOD,
                'timeLimit': 0,
                'confirmSound': '',
                'confirmKey': '',
                'dialMusic': '',
                'redirect': 'true',
                'callbackUrl': '',
                'callbackMethod': 'POST',
                'digitsMatch': ''
        },
        'GetDigits': {
                #action: DYNAMIC! MUST BE SET IN METHOD,
                'method': 'POST',
                'timeout': 5,
                'finishOnKey': '#',
                'numDigits': 99,
                'retries': 1,
                'playBeep': 'false',
                'validDigits': '0123456789*#',
                'invalidDigitsSound': ''
        },
        'Hangup': {
                'reason': '',
                'schedule': 0
        },
        'Number': {
                #'gateways': DYNAMIC! MUST BE SET IN METHOD,
                #'gatewayCodecs': DYNAMIC! MUST BE SET IN METHOD,
                #'gatewayTimeouts': DYNAMIC! MUST BE SET IN METHOD,
                #'gatewayRetries': DYNAMIC! MUST BE SET IN METHOD,
                #'extraDialString': DYNAMIC! MUST BE SET IN METHOD,
                'sendDigits': '',
        },
        'Wait': {
                'length': 1
        },
        'Play': {
                #url: SET IN ELEMENT BODY
                'loop': 1
        },
        'PreAnswer': {
        },
        'Record': {
                #action: DYNAMIC! MUST BE SET IN METHOD,
                'method': 'POST',
                'timeout': 15,
                'finishOnKey': '1234567890*#',
                'maxLength': 60,
                'playBeep': 'true',
                'filePath': '/usr/local/freeswitch/recordings/',
                'fileFormat': 'mp3',
                'fileName': '',
                'redirect': 'true',
                'bothLegs': 'false'
        },
        'SIPTransfer': {
                #url: SET IN ELEMENT BODY
        },
        'Redirect': {
                #url: SET IN ELEMENT BODY
                'method': 'POST'
        },
        'Notify': {
                #url: SET IN ELEMENT BODY
                'method': 'POST'
        },
        'Speak': {
                'voice': 'slt',
                'language': 'en',
                'loop': 1,
                'engine': 'flite',
                'method': '',
                'type': ''
        },
        'GetSpeech': {
                #action: DYNAMIC! MUST BE SET IN METHOD,
                'method': 'POST',
                'timeout': 5,
                'playBeep': 'false',
                'engine': 'pocketsphinx',
                'grammar': '',
                'grammarPath': '/usr/local/freeswitch/grammar'
        }
    }


MAX_LOOPS = 10000


class Element(object):
    """Abstract Element Class to be inherited by all other elements"""

    def __init__(self):
        self.name = str(self.__class__.__name__)
        self.nestables = None
        self.attributes = {}
        self.text = ''
        self.children = []
        self.uri = None
        self._element = None

    def get_element(self):
        return self._element

    def parse_element(self, element, uri=None):
        self.uri = uri 
        self._element = element
        self.prepare_attributes(element)
        self.prepare_text(element)

    def run(self, outbound_socket):
        outbound_socket.log.info("[%s] %s %s" \
            % (self.name, self.text, self.attributes))
        execute = getattr(self, 'execute', None)
        if not execute:
            outbound_socket.log.error("[%s] Element cannot be executed !" % self.name)
            raise RESTNoExecuteException("Element %s cannot be executed !" % self.name)
        try:
            outbound_socket.current_element = self.name
            result = execute(outbound_socket)
            outbound_socket.current_element = None
        except RESTHangup:
            outbound_socket.log.info("[%s] Done (hangup)" % self.name)
            raise
        except RESTRedirectException:
            outbound_socket.log.info("[%s] Done (redirect)" % self.name)
            raise
        except RESTSIPTransferException:
            outbound_socket.log.info("[%s] Done (sip transfer)" % self.name)
            raise
        if not result:
            outbound_socket.log.info("[%s] Done" % self.name)
        else:
            outbound_socket.log.info("[%s] Done -- Result %s" % (self.name, result))

    def extract_attribute_value(self, item, default=None):
        try:
            item = self.attributes[item]
        except KeyError:
            item = default
        return item

    def prepare_attributes(self, element):
        element_dict = ELEMENTS_DEFAULT_PARAMS[self.name]
        if element.attrib and not element_dict:
            raise RESTFormatException("%s does not require any attributes!"
                                                                % self.name)
        self.attributes = dict(element_dict, **element.attrib)

    def prepare_text(self, element):
        text = element.text
        if not text:
            self.text = ''
        else:
            self.text = text.strip()

    def fetch_rest_xml(self, url, params={}, method='POST'):
        raise RESTRedirectException(url, params, method)


class Conference(Element):
    """Go to a Conference Room
    room name is body text of Conference element.

    waitSound: sound to play while alone in conference
          Can be a list of sound files separated by comma.
          (default no sound)
    muted: enter conference muted
          (default false)
    startConferenceOnEnter: the conference start when this member joins
          (default true)
    endConferenceOnExit: close conference after all members
        with this attribute set to 'true' leave. (default false)
    stayAlone: if 'false' and member is alone, conference is closed and member kicked out
          (default true)
    maxMembers: max members in conference
          (0 for max : 200)
    enterSound: sound to play when a member enters
          if empty, disabled
          if 'beep:1', play one beep
          if 'beep:2', play two beeps
          (default disabled)
    exitSound: sound to play when a member exits
          if empty, disabled
          if 'beep:1', play one beep
          if 'beep:2', play two beeps
          (default disabled)
    timeLimit: max time in seconds before closing conference
          (default 0, no timeLimit)
    hangupOnStar: exit conference when member press '*'
          (default false)
    recordFilePath: path where recording is saved.
        (default "" so recording wont happen)
    recordFileFormat: file format in which recording tis saved
        (default mp3)
    recordFileName: By default empty, if provided this name will be used for the recording
        (any unique name)
    action: redirect to this URL after leaving conference
    method: submit to 'action' url using GET or POST
    callbackUrl: url to request when call enters/leaves conference
            or has pressed digits matching (digitsMatch) or member is speaking (speakEvent)
    callbackMethod: submit to 'callbackUrl' url using GET or POST
    digitsMatch: a list of matching digits to send with callbackUrl
            Can be a list of digits patterns separated by comma.
    floorEvent: 'true' or 'false'. When this member holds the floor, 
            send notification to callbackUrl. (default 'false')
    """
    DEFAULT_TIMELIMIT = 0
    DEFAULT_MAXMEMBERS = 200

    def __init__(self):
        Element.__init__(self)
        self.full_room = ''
        self.room = ''
        self.moh_sound = None
        self.muted = False
        self.start_on_enter = True
        self.end_on_exit = False
        self.stay_alone = False
        self.time_limit = self.DEFAULT_TIMELIMIT
        self.max_members = self.DEFAULT_MAXMEMBERS
        self.enter_sound = ''
        self.exit_sound = ''
        self.hangup_on_star = False
        self.record_file_path = ""
        self.record_file_format = "mp3"
        self.record_filename = ""
        self.action = ''
        self.method = ''
        self.callback_url = ''
        self.callback_method = ''
        self.speaker = False
        self.conf_id = ''
        self.member_id = ''

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        room = self.text
        if not room:
            raise RESTFormatException('Conference Room must be defined')
        self.full_room = room + '@plivo'
        self.room = room
        self.moh_sound = self.extract_attribute_value('waitSound')
        self.muted = self.extract_attribute_value('muted') \
                        == 'true'
        self.start_on_enter = self.extract_attribute_value('startConferenceOnEnter') \
                                == 'true'
        self.end_on_exit = self.extract_attribute_value('endConferenceOnExit') \
                                == 'true'
        self.stay_alone = self.extract_attribute_value('stayAlone') \
                                == 'true'
        self.hangup_on_star = self.extract_attribute_value('hangupOnStar') \
                                == 'true'
        try:
            self.time_limit = int(self.extract_attribute_value('timeLimit',
                                                          self.DEFAULT_TIMELIMIT))
        except ValueError:
            self.time_limit = self.DEFAULT_TIMELIMIT
        if self.time_limit <= 0:
            self.time_limit = self.DEFAULT_TIMELIMIT
        try:
            self.max_members = int(self.extract_attribute_value('maxMembers',
                                                        self.DEFAULT_MAXMEMBERS))
        except ValueError:
            self.max_members = self.DEFAULT_MAXMEMBERS
        if self.max_members <= 0 or self.max_members > self.DEFAULT_MAXMEMBERS:
            self.max_members = self.DEFAULT_MAXMEMBERS

        self.enter_sound = self.extract_attribute_value('enterSound')
        self.exit_sound = self.extract_attribute_value('exitSound')

        self.record_file_path = self.extract_attribute_value("recordFilePath")
        if self.record_file_path:
            self.record_file_path = os.path.normpath(self.record_file_path)\
                                                                    + os.sep
        self.record_file_format = \
                            self.extract_attribute_value("recordFileFormat")
        if self.record_file_format not in ('wav', 'mp3'):
            raise RESTFormatException("Format must be 'wav' or 'mp3'")
        self.record_filename = \
                            self.extract_attribute_value("recordFileName")

        self.method = self.extract_attribute_value("method")
        if not self.method in ('GET', 'POST'):
            raise RESTAttributeException("method must be 'GET' or 'POST'")
        self.action = self.extract_attribute_value("action")

        self.callback_url = self.extract_attribute_value("callbackUrl")
        self.callback_method = self.extract_attribute_value("callbackMethod")
        if not self.callback_method in ('GET', 'POST'):
            raise RESTAttributeException("callbackMethod must be 'GET' or 'POST'")
        self.digits_match = self.extract_attribute_value("digitsMatch")
        self.floor = self.extract_attribute_value("floorEvent") == 'true'

    def _prepare_moh(self, outbound_socket):
        sound_files = []
        if not self.moh_sound:
            return sound_files
        outbound_socket.log.info('Fetching remote sound from restxml %s' % self.moh_sound)
        try:
            response = outbound_socket.send_to_url(self.moh_sound, params={}, method='POST')
            doc = etree.fromstring(response)
            if doc.tag != 'Response':
                outbound_socket.log.warn('No Response Tag Present')
                return sound_files

            # build play string from remote restxml
            for element in doc:
                # Play element
                if element.tag == 'Play':
                    child_instance = Play()
                    child_instance.parse_element(element)
                    child_instance.prepare(outbound_socket)
                    sound_file = child_instance.sound_file_path
                    if sound_file:
                        sound_file = get_resource(outbound_socket, sound_file)
                        loop = child_instance.loop_times
                        if loop == 0:
                            loop = MAX_LOOPS  # Add a high number to Play infinitely
                        # Play the file loop number of times
                        for i in range(loop):
                            sound_files.append(sound_file)
                        # Infinite Loop, so ignore other children
                        if loop == MAX_LOOPS:
                            break
                # Wait element
                elif element.tag == 'Wait':
                    child_instance = Wait()
                    child_instance.parse_element(element)
                    pause_secs = child_instance.length
                    pause_str = 'file_string://silence_stream://%s' % (pause_secs * 1000)
                    sound_files.append(pause_str)
        except Exception, e:
            outbound_socket.log.warn('Fetching remote sound from restxml failed: %s' % str(e))
        finally:
            outbound_socket.log.info('Fetching remote sound from restxml done')
            return sound_files

    def _notify_enter_conf(self, outboundsocket):
        if not self.callback_url or not self.conf_id or not self.member_id:
            return
        params = {}
        params['ConferenceName'] = self.room
        params['ConferenceUUID'] = self.conf_id or ''
        params['ConferenceMemberID'] = self.member_id or ''
        params['ConferenceAction'] = 'enter'
        spawn_raw(outboundsocket.send_to_url, self.callback_url, params, self.callback_method)

    def _notify_exit_conf(self, outboundsocket):
        if not self.callback_url or not self.conf_id or not self.member_id:
            return
        params = {}
        params['ConferenceName'] = self.room
        params['ConferenceUUID'] = self.conf_id or ''
        params['ConferenceMemberID'] = self.member_id or ''
        params['ConferenceAction'] = 'exit'
        spawn_raw(outboundsocket.send_to_url, self.callback_url, params, self.callback_method)

    def _notify_floor_holder(self, outboundsocket):
        if not self.floor or not self.callback_url or not self.conf_id or not self.member_id:
            return
        outboundsocket.log.debug("Floor holder into Conference")
        params = {}
        params['ConferenceName'] = self.room
        params['ConferenceUUID'] = self.conf_id or ''
        params['ConferenceMemberID'] = self.member_id or ''
        params['ConferenceAction'] = 'floor'
        spawn_raw(outboundsocket.send_to_url, self.callback_url, params, self.callback_method)

    def execute(self, outbound_socket):
        flags = []
        # settings for conference room
        outbound_socket.set("conference_controls=none")
        if self.max_members > 0:
            outbound_socket.set("conference_max_members=%d" % self.max_members)
        else:
            outbound_socket.unset("conference_max_members")

        if self.record_file_path:
            file_path = os.path.normpath(self.record_file_path) + os.sep
            if self.record_filename:
                filename = self.record_filename
            else:
                filename = "%s_%s" % (datetime.now().strftime("%Y%m%d-%H%M%S"),
                                      outbound_socket.get_channel_unique_id())
            record_file = "%s%s.%s" % (file_path, filename,
                                        self.record_file_format)
        else:
            record_file = None

        # set moh sound
        mohs = self._prepare_moh(outbound_socket)
        if mohs:
            outbound_socket.set("playback_delimiter=!")
            play_str = '!'.join(mohs)
            play_str = "file_string://silence_stream://1!%s" % play_str
            outbound_socket.set("conference_moh_sound=%s" % play_str)
        else:
            outbound_socket.unset("conference_moh_sound")
        # set member flags
        if self.muted:
            flags.append("mute")
        if self.start_on_enter:
            flags.append("moderator")
        if not self.stay_alone:
            flags.append("mintwo")
        if self.end_on_exit:
            flags.append("endconf")
        flags_opt = ','.join(flags)
        if flags_opt:
            outbound_socket.set("conference_member_flags=%s" % flags_opt)
        else:
            outbound_socket.unset("conference_member_flags")

        # play beep on exit if enabled
        if self.exit_sound == 'beep:1':
            outbound_socket.set("conference_exit_sound=tone_stream://%%(300,200,700)")
        elif self.exit_sound == 'beep:2':
            outbound_socket.set("conference_exit_sound=tone_stream://L=2;%%(300,200,700)")

        # set new kickall scheduled task if timeLimit > 0
        if self.time_limit > 0:
            # set timeLimit scheduled group name for the room
            sched_group_name = "conf_%s" % self.room
            # always clean old kickall tasks for the room
            outbound_socket.api("sched_del %s" % sched_group_name)
            # set new kickall task for the room
            outbound_socket.api("sched_api +%d %s conference %s kick all" \
                                % (self.time_limit, sched_group_name, self.room))
            outbound_socket.log.warn("Conference: Room %s, timeLimit set to %d seconds" \
                                    % (self.room, self.time_limit))
        # really enter conference room
        outbound_socket.log.info("Entering Conference: Room %s (flags %s)" \
                                        % (self.room, flags_opt))
        res = outbound_socket.conference(self.full_room, lock=False)
        if not res.is_success():
            outbound_socket.log.error("Conference: Entering Room %s Failed" \
                                % (self.room))
            return
        # get next event
        event = outbound_socket.wait_for_action()

        # if event is add-member, get Member-ID
        # and set extra features for conference
        # else conference element ending here
        try:
            digit_realm = ''
            if event['Event-Subclass'] == 'conference::maintenance' \
                and event['Action'] == 'add-member':
                self.member_id = event['Member-ID']
                self.conf_id = event['Conference-Unique-ID']
                outbound_socket.log.debug("Entered Conference: Room %s with Member-ID %s" \
                                % (self.room, self.member_id))
                has_floor = event['Floor'] == 'true'
                can_speak = event['Speak'] == 'true'
                is_first = event['Conference-Size'] == '1'
                # notify channel has entered room
                self._notify_enter_conf(outbound_socket)
                # notify floor holder only if :
                # floor is true and member is not muted and member is the first one
                if has_floor and can_speak and is_first:
                    self._notify_floor_holder(outbound_socket)

                # set bind digit actions
                if self.digits_match and self.callback_url:
                    # create event template
                    event_template = "Event-Name=CUSTOM,Event-Subclass=conference::maintenance,Action=digits-match,Unique-ID=%s,Callback-Url=%s,Callback-Method=%s,Member-ID=%s,Conference-Name=%s,Conference-Unique-ID=%s" \
                        % (outbound_socket.get_channel_unique_id(), self.callback_url, self.callback_method, self.member_id, self.room, self.conf_id)
                    digit_realm = "plivo_bda_%s" % outbound_socket.get_channel_unique_id()
                    # for each digits match, set digit binding action
                    for dmatch in self.digits_match.split(','):
                        dmatch = dmatch.strip()
                        if dmatch:
                            raw_event = "%s,Digits-Match=%s" % (event_template, dmatch)
                            cmd = "%s,%s,exec:event,'%s'" % (digit_realm, dmatch, raw_event)
                            outbound_socket.bind_digit_action(cmd)
                # set hangup on star
                if self.hangup_on_star:
                    # create event template
                    raw_event = "Event-Name=CUSTOM,Event-Subclass=conference::maintenance,Action=kick,Unique-ID=%s,Member-ID=%s,Conference-Name=%s,Conference-Unique-ID=%s" \
                        % (outbound_socket.get_channel_unique_id(), self.member_id, self.room, self.conf_id)
                    digit_realm = "plivo_bda_%s" % outbound_socket.get_channel_unique_id()
                    cmd = "%s,*,exec:event,'%s'" % (digit_realm, raw_event)
                    outbound_socket.bind_digit_action(cmd)
                # set digit realm
                if digit_realm:
                    outbound_socket.digit_action_set_realm(digit_realm)

                # play beep on enter if enabled
                if self.member_id:
                    if self.enter_sound == 'beep:1':
                        outbound_socket.bgapi("conference %s play tone_stream://%%(300,200,700) async" % self.room)
                    elif self.enter_sound == 'beep:2':
                        outbound_socket.bgapi("conference %s play tone_stream://L=2;%%(300,200,700) async" % self.room)

                # record conference if set
                if record_file:
                    outbound_socket.bgapi("conference %s record %s" % (self.room, record_file))
                    outbound_socket.log.info("Conference: Room %s, recording to file %s" \
                                    % (self.room, record_file))

                # wait conference ending for this member
                outbound_socket.log.debug("Conference: Room %s, waiting end ..." % self.room)
                for x in range(10000):
                    event = outbound_socket.wait_for_action(timeout=30, raise_on_hangup=True)
                    if event['Action'] == 'floor-change':
                        self._notify_floor_holder(outbound_socket)
                        continue
                    if event.is_empty():
                        continue
                    break

            # unset digit realm
            if digit_realm:
                outbound_socket.clear_digit_action(digit_realm)

        finally:
            # notify channel has left room
            self._notify_exit_conf(outbound_socket)
            outbound_socket.log.info("Leaving Conference: Room %s" % self.room)

            # If action is set, redirect to this url
            # Otherwise, continue to next Element
            if self.action and is_valid_url(self.action):
                params = {}
                params['ConferenceName'] = self.room
                params['ConferenceUUID'] = self.conf_id or ''
                params['ConferenceMemberID'] = self.member_id or ''
                if record_file:
                    params['RecordFile'] = record_file
                self.fetch_rest_xml(self.action, params, method=self.method)



class Dial(Element):
    """Dial another phone number and connect it to this call

    action: submit the result of the dial and redirect to this URL
    method: submit to 'action' url using GET or POST
    hangupOnStar: hangup the b leg if a leg presses start and this is true
    callerId: caller id to be send to the dialed number
    timeLimit: hangup the call after these many seconds. 0 means no timeLimit
    confirmSound: Sound to be played to b leg before call is bridged
    confirmKey: Key to be pressed to bridge the call.
    dialMusic: Play music to a leg while doing a dial to b leg
                Can be a list of files separated by comma
    redirect: if 'false', don't redirect to 'action', only request url
        and continue to next element. (default 'true')
    callbackUrl: url to request when bridge starts and bridge ends
    callbackMethod: submit to 'callbackUrl' url using GET or POST
    """
    DEFAULT_TIMELIMIT = 14400

    def __init__(self):
        Element.__init__(self)
        self.nestables = ('Number',)
        self.method = ''
        self.action = ''
        self.hangup_on_star = False
        self.caller_id = ''
        self.caller_name = ''
        self.time_limit = self.DEFAULT_TIMELIMIT
        self.timeout = -1
        self.dial_str = ''
        self.confirm_sound = ''
        self.confirm_key = ''
        self.dial_music = ''
        self.redirect = True

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        self.action = self.extract_attribute_value('action')
        self.caller_id = self.extract_attribute_value('callerId')
        self.caller_name = self.extract_attribute_value('callerName')
        try:
            self.time_limit = int(self.extract_attribute_value('timeLimit',
                                                      self.DEFAULT_TIMELIMIT))
        except ValueError:
            self.time_limit = self.DEFAULT_TIMELIMIT
        if self.time_limit <= 0:
            self.time_limit = self.DEFAULT_TIMELIMIT
        try:
            self.timeout = int(self.extract_attribute_value("timeout", -1))
        except ValueError:
            self.timeout = -1
        if self.timeout <= 0:
            self.timeout = -1
        self.confirm_sound = self.extract_attribute_value("confirmSound")
        self.confirm_key = self.extract_attribute_value("confirmKey")
        self.dial_music = self.extract_attribute_value("dialMusic")
        self.hangup_on_star = self.extract_attribute_value("hangupOnStar") \
                                                                == 'true'
        self.redirect = self.extract_attribute_value("redirect") == 'true'

        method = self.extract_attribute_value("method")
        if not method in ('GET', 'POST'):
            raise RESTAttributeException("method must be 'GET' or 'POST'")
        self.method = method

        self.callback_url = self.extract_attribute_value("callbackUrl")
        self.callback_method = self.extract_attribute_value("callbackMethod")
        if not self.callback_method in ('GET', 'POST'):
            raise RESTAttributeException("callbackMethod must be 'GET' or 'POST'")
        self.digits_match = self.extract_attribute_value("digitsMatch")

    def _prepare_play_string(self, outbound_socket, remote_url):
        sound_files = []
        if not remote_url:
            return sound_files
        outbound_socket.log.info('Fetching remote sound from restxml %s' % remote_url)
        try:
            response = outbound_socket.send_to_url(remote_url, params={}, method='POST')
            doc = etree.fromstring(response)
            if doc.tag != 'Response':
                outbound_socket.log.warn('No Response Tag Present')
                return sound_files

            # build play string from remote restxml
            for element in doc:
                # Play element
                if element.tag == 'Play':
                    child_instance = Play()
                    child_instance.parse_element(element)
                    child_instance.prepare(outbound_socket)
                    sound_file = child_instance.sound_file_path
                    if sound_file:
                        sound_file = get_resource(outbound_socket, sound_file)
                        loop = child_instance.loop_times
                        if loop == 0:
                            loop = MAX_LOOPS  # Add a high number to Play infinitely
                        # Play the file loop number of times
                        for i in range(loop):
                            sound_files.append(sound_file)
                        # Infinite Loop, so ignore other children
                        if loop == MAX_LOOPS:
                            break
                # Speak element
                elif element.tag == 'Speak':
                    child_instance = Speak()
                    child_instance.parse_element(element)
                    text = child_instance.text
                    # escape simple quote
                    text = text.replace("'", "\\'")
                    loop = child_instance.loop_times
                    child_type = child_instance.item_type
                    method = child_instance.method
                    say_str = ''
                    if child_type and method:
                        language = child_instance.language
                        say_args = "%s.wav %s %s %s '%s'" \
                                        % (language, language, child_type, method, text)
                        say_str = "${say_string %s}" % say_args
                    else:
                        engine = child_instance.engine
                        voice = child_instance.voice
                        say_str = "say:%s:%s:'%s'" % (engine, voice, text)
                    if not say_str:
                        continue
                    for i in range(loop):
                        sound_files.append(say_str)
                # Wait element
                elif element.tag == 'Wait':
                    child_instance = Wait()
                    child_instance.parse_element(element)
                    pause_secs = child_instance.length
                    pause_str = 'file_string://silence_stream://%s' % (pause_secs * 1000)
                    sound_files.append(pause_str)
        except Exception, e:
            outbound_socket.log.warn('Fetching remote sound from restxml failed: %s' % str(e))
        finally:
            outbound_socket.log.info('Fetching remote sound from restxml done for %s' % remote_url)
            return sound_files

    def create_number(self, number_instance, outbound_socket):
        num_gw = []
        # skip number object without gateway or number
        if not number_instance.gateways:
            outbound_socket.log.error("Gateway not defined on Number object !")
            return ''
        if not number_instance.number:
            outbound_socket.log.error("Number not defined on Number object  !")
            return ''
        if number_instance.send_digits:
            if number_instance.send_on_preanswer is True:
                option_send_digits = "api_on_media='uuid_recv_dtmf ${uuid} %s'" \
                                                    % number_instance.send_digits
            else:
                option_send_digits = "api_on_answer_2='uuid_recv_dtmf ${uuid} %s'" \
                                                    % number_instance.send_digits
        else:
            option_send_digits = ''
        count = 0
        for gw in number_instance.gateways:
            num_options = []

            if self.callback_url and self.callback_method:
                num_options.append('plivo_dial_callback_url=%s' % self.callback_url)
                num_options.append('plivo_dial_callback_method=%s' % self.callback_method)
                num_options.append('plivo_dial_callback_aleg=%s' % outbound_socket.get_channel_unique_id())

            if option_send_digits:
                num_options.append(option_send_digits)
            try:
                gw_codec = number_instance.gateway_codecs[count]
                num_options.append('absolute_codec_string=%s' % gw_codec)
            except IndexError:
                pass
            try:
                gw_timeout = int(number_instance.gateway_timeouts[count])
                if gw_timeout > 0:
                    num_options.append('leg_timeout=%d' % gw_timeout)
            except (IndexError, ValueError):
                pass
            try:
                gw_retries = int(number_instance.gateway_retries[count])
                if gw_retries <= 0:
                    gw_retries = 1
            except (IndexError, ValueError):
                gw_retries = 1
            extra_dial_string = number_instance.extra_dial_string
            if extra_dial_string:
                num_options.append(extra_dial_string)
            if num_options:
                options = '[%s]' % (','.join(num_options))
            else:
                options = ''
            num_str = "%s%s%s" % (options, gw, number_instance.number)
            dial_num = '|'.join([num_str for retry in range(gw_retries)])
            num_gw.append(dial_num)
            count += 1
        result = '|'.join(num_gw)
        return result

    def execute(self, outbound_socket):
        numbers = []
        # Set timeout
        if self.timeout > 0:
            outbound_socket.set("call_timeout=%d" % self.timeout)
        else:
            outbound_socket.unset("call_timeout")

        # Set callerid or unset if not provided
        if self.caller_id == 'none':
            outbound_socket.set("effective_caller_id_number=''")
        elif self.caller_id:
            outbound_socket.set("effective_caller_id_number=%s" % self.caller_id)
        else:
            outbound_socket.unset("effective_caller_id_number")
        # Set callername or unset if not provided
        if self.caller_name == 'none':
            outbound_socket.set("effective_caller_id_name=''")
        elif self.caller_name:
            outbound_socket.set("effective_caller_id_name='%s'" % self.caller_name)
        else:
            outbound_socket.unset("effective_caller_id_name")
        # Set continue on fail
        outbound_socket.set("continue_on_fail=true")
        # Don't hangup after bridge !
        outbound_socket.set("hangup_after_bridge=false")

        # Set ring flag if dial will ring.
        # But first set plivo_dial_rang to false
        # to be sure we don't get it from an old Dial
        outbound_socket.set("plivo_dial_rang=false")
        ring_flag = "api_on_ring='uuid_setvar %s plivo_dial_rang true',api_on_pre_answer='uuid_setvar %s plivo_dial_rang true'" \
                    % (outbound_socket.get_channel_unique_id(), outbound_socket.get_channel_unique_id())

        # Set numbers to dial from Number nouns
        for child in self.children:
            if isinstance(child, Number):
                dial_num = self.create_number(child, outbound_socket)
                if not dial_num:
                    continue
                numbers.append(dial_num)
        if not numbers:
            outbound_socket.log.error("Dial Aborted, No Number to dial !")
            return
        # Create dialstring
        self.dial_str = ':_:'.join(numbers)

        # Set time limit: when reached, B Leg is hung up
        sched_hangup_id = str(uuid.uuid1())
        dial_time_limit = "api_on_answer_1='sched_api +%d %s uuid_transfer %s -bleg hangup:ALLOTTED_TIMEOUT inline'" \
                      % (self.time_limit, sched_hangup_id, outbound_socket.get_channel_unique_id())

        # Set confirm sound and key or unset if not provided
        dial_confirm = ''
        if self.confirm_sound:
            confirm_sounds = self._prepare_play_string(outbound_socket, self.confirm_sound)
            if confirm_sounds:
                play_str = '!'.join(confirm_sounds)
                play_str = "file_string://silence_stream://1!%s" % play_str
                # Use confirm key if present else just play music
                if self.confirm_key:
                    confirm_music_str = "group_confirm_file=%s" % play_str
                    confirm_key_str = "group_confirm_key=%s" % self.confirm_key
                else:
                    confirm_music_str = "group_confirm_file=playback %s" % play_str
                    confirm_key_str = "group_confirm_key=exec"
                # Cancel the leg timeout after the call is answered
                confirm_cancel = "group_confirm_cancel_timeout=1"
                dial_confirm = ",%s,%s,%s,playback_delimiter=!" % (confirm_music_str, confirm_key_str, confirm_cancel)

        # Append time limit and group confirm to dial string
        self.dial_str = '<%s,%s%s>%s' % (ring_flag, dial_time_limit, dial_confirm, self.dial_str)
        # Ugly hack to force use of enterprise originate because simple originate lacks speak support in ringback
        if len(numbers) < 2:
            self.dial_str += ':_:'

        # Set hangup on '*' or unset if not provided
        if self.hangup_on_star:
            outbound_socket.set("bridge_terminate_key=*")
        else:
            outbound_socket.unset("bridge_terminate_key")

        # Play Dial music or bridge the early media accordingly
        ringbacks = ''
        if self.dial_music and self.dial_music not in ("none", "real"):
            ringbacks = self._prepare_play_string(outbound_socket, self.dial_music)
            if ringbacks:
                outbound_socket.set("playback_delimiter=!")
                play_str = '!'.join(ringbacks)
                play_str = "file_string://silence_stream://1!%s" % play_str
                outbound_socket.set("bridge_early_media=false")
                outbound_socket.set("instant_ringback=true")
                outbound_socket.set("ringback=%s" % play_str)
            else:
                self.dial_music = ''
        if not self.dial_music:
            outbound_socket.set("bridge_early_media=false")
            outbound_socket.set("instant_ringback=true")
            outbound_socket.set("ringback=${us-ring}")
        elif self.dial_music == "none":
            outbound_socket.set("bridge_early_media=false")
            outbound_socket.unset("instant_ringback")
            outbound_socket.unset("ringback")
        elif self.dial_music == "real":
            outbound_socket.set("bridge_early_media=true")
            outbound_socket.set("instant_ringback=false")
            outbound_socket.unset("ringback")

        # Start dial
        bleg_uuid = ''
        dial_rang = ''
        digit_realm = ''
        hangup_cause = 'NORMAL_CLEARING'
        outbound_socket.log.info("Dial Started %s" % self.dial_str)
        try:
            # send ring ready to originator
            outbound_socket.ring_ready()
            # execute bridge
            res = outbound_socket.bridge(self.dial_str, lock=False)

            # set bind digit actions
            if self.digits_match and self.callback_url:
                # create event template
                event_template = "Event-Name=CUSTOM,Event-Subclass=plivo::dial,Action=digits-match,Unique-ID=%s,Callback-Url=%s,Callback-Method=%s" \
                    % (outbound_socket.get_channel_unique_id(), self.callback_url, self.callback_method)
                digit_realm = "plivo_bda_dial_%s" % outbound_socket.get_channel_unique_id()
                # for each digits match, set digit binding action
                for dmatch in self.digits_match.split(','):
                    dmatch = dmatch.strip()
                    if dmatch:
                        raw_event = "%s,Digits-Match=%s" % (event_template, dmatch)
                        cmd = "%s,%s,exec:event,'%s'" % (digit_realm, dmatch, raw_event)
                        outbound_socket.bind_digit_action(cmd)
            # set digit realm
            if digit_realm:
                outbound_socket.digit_action_set_realm(digit_realm)

            # waiting event
            for x in range(10000):
                event = outbound_socket.wait_for_action(timeout=30, raise_on_hangup=True)
                if event.is_empty():
                    continue
                elif event['Event-Name'] == 'CHANNEL_BRIDGE':
                    outbound_socket.log.info("Dial bridged")
                elif event['Event-Name'] == 'CHANNEL_UNBRIDGE':
                    outbound_socket.log.info("Dial unbridged")
                    break
                elif event['Event-Name'] == 'CHANNEL_EXECUTE_COMPLETE':
                    outbound_socket.log.info("Dial completed %s" % str(event))
                    break

            # parse received events
            if event['Event-Name'] == 'CHANNEL_UNBRIDGE':
                bleg_uuid = event['variable_bridge_uuid'] or ''
                event = outbound_socket.wait_for_action(timeout=30, raise_on_hangup=True)
            reason = None
            originate_disposition = event['variable_originate_disposition']
            hangup_cause = originate_disposition
            if hangup_cause == 'ORIGINATOR_CANCEL':
                reason = '%s (A leg)' % hangup_cause
            else:
                reason = '%s (B leg)' % hangup_cause
            if not hangup_cause or hangup_cause == 'SUCCESS':
                hangup_cause = outbound_socket.get_hangup_cause()
                reason = '%s (A leg)' % hangup_cause
                if not hangup_cause:
                    hangup_cause = outbound_socket.get_var('bridge_hangup_cause')
                    reason = '%s (B leg)' % hangup_cause
                    if not hangup_cause:
                        hangup_cause = outbound_socket.get_var('hangup_cause')
                        reason = '%s (A leg)' % hangup_cause
                        if not hangup_cause:
                            hangup_cause = 'NORMAL_CLEARING'
                            reason = '%s (A leg)' % hangup_cause
            outbound_socket.log.info("Dial Finished with reason: %s" \
                                     % reason)
            # Unschedule hangup task
            outbound_socket.bgapi("sched_del %s" % sched_hangup_id)
            # Get ring status
            dial_rang = outbound_socket.get_var("plivo_dial_rang") == 'true'
        finally:
            # If action is set, redirect to this url
            # Otherwise, continue to next Element
            if self.action and is_valid_url(self.action):
                params = {}
                if dial_rang:
                    params['DialRingStatus'] = 'true'
                else:
                    params['DialRingStatus'] = 'false'
                params['DialHangupCause'] = hangup_cause
                params['DialALegUUID'] = outbound_socket.get_channel_unique_id()
                if bleg_uuid:
                    params['DialBLegUUID'] = bleg_uuid
                else:
                    params['DialBLegUUID'] = ''
                if self.redirect:
                    self.fetch_rest_xml(self.action, params, method=self.method)
                else:
                    spawn_raw(outbound_socket.send_to_url, self.action, params, method=self.method)


class GetDigits(Element):
    """Get digits from the caller's keypad

    action: URL to which the digits entered will be sent
    method: submit to 'action' url using GET or POST
    numDigits: how many digits to gather before returning
    timeout: wait for this many seconds before retry or returning
    finishOnKey: key that triggers the end of caller input
    tries: number of tries to execute all says and plays one by one
    playBeep: play a after all plays and says finish
    validDigits: digits which are allowed to be pressed
    invalidDigitsSound: Sound played when invalid digit pressed
    """
    DEFAULT_MAX_DIGITS = 99
    DEFAULT_TIMEOUT = 5

    def __init__(self):
        Element.__init__(self)
        self.nestables = ('Speak', 'Play', 'Wait')
        self.num_digits = None
        self.timeout = None
        self.finish_on_key = None
        self.action = None
        self.play_beep = ""
        self.valid_digits = ""
        self.invalid_digits_sound = ""
        self.retries = None
        self.sound_files = []
        self.method = ""

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        try:
            num_digits = int(self.extract_attribute_value('numDigits',
                             self.DEFAULT_MAX_DIGITS))
        except ValueError:
            num_digits = self.DEFAULT_MAX_DIGITS
        if num_digits > self.DEFAULT_MAX_DIGITS:
            num_digits = self.DEFAULT_MAX_DIGITS
        if num_digits < 1:
            raise RESTFormatException("GetDigits 'numDigits' must be greater than 0")
        try:
            timeout = int(self.extract_attribute_value("timeout", self.DEFAULT_TIMEOUT))
        except ValueError:
            timeout = self.DEFAULT_TIMEOUT * 1000
        if timeout < 1:
            raise RESTFormatException("GetDigits 'timeout' must be a positive integer")

        finish_on_key = self.extract_attribute_value("finishOnKey")
        self.play_beep = self.extract_attribute_value("playBeep") == 'true'
        self.invalid_digits_sound = \
                            self.extract_attribute_value("invalidDigitsSound")
        self.valid_digits = self.extract_attribute_value("validDigits")

        try:
            retries = int(self.extract_attribute_value("retries"))
        except ValueError:
            retries = 1
        if retries <= 0:
            raise RESTFormatException("GetDigits 'retries' must be greater than 0")

        method = self.extract_attribute_value("method")
        if not method in ('GET', 'POST'):
            raise RESTAttributeException("method must be 'GET' or 'POST'")
        self.method = method

        action = self.extract_attribute_value("action")
        if action and is_valid_url(action):
            self.action = action
        else:
            self.action = None
        self.num_digits = num_digits
        self.timeout = timeout * 1000
        self.finish_on_key = finish_on_key
        self.retries = retries

    def prepare(self, outbound_socket):
        for child_instance in self.children:
            if hasattr(child_instance, "prepare"):
                # :TODO Prepare Element concurrently
                child_instance.prepare(outbound_socket)

    def execute(self, outbound_socket):
        for child_instance in self.children:
            if isinstance(child_instance, Play):
                sound_file = child_instance.sound_file_path
                if sound_file:
                    loop = child_instance.loop_times
                    if loop == 0:
                        loop = MAX_LOOPS  # Add a high number to Play infinitely
                    # Play the file loop number of times
                    for i in range(loop):
                        self.sound_files.append(sound_file)
                    # Infinite Loop, so ignore other children
                    if loop == MAX_LOOPS:
                        break
            elif isinstance(child_instance, Wait):
                pause_secs = child_instance.length
                pause_str = 'file_string://silence_stream://%s'\
                                % (pause_secs * 1000)
                self.sound_files.append(pause_str)
            elif isinstance(child_instance, Speak):
                text = child_instance.text
                # escape simple quote
                text = text.replace("'", "\\'")
                loop = child_instance.loop_times
                child_type = child_instance.item_type
                method = child_instance.method
                say_str = ''
                if child_type and method:
                    language = child_instance.language
                    say_args = "%s.wav %s %s %s '%s'" \
                                    % (language, language, child_type, method, text)
                    say_str = "${say_string %s}" % say_args
                else:
                    engine = child_instance.engine
                    voice = child_instance.voice
                    say_str = "say:%s:%s:'%s'" % (engine, voice, text)
                if not say_str:
                    continue
                for i in range(loop):
                    self.sound_files.append(say_str)

        if self.invalid_digits_sound:
            invalid_sound = get_resource(outbound_socket, self.invalid_digits_sound)
        else:
            invalid_sound = ''

        outbound_socket.log.info("GetDigits Started %s" % self.sound_files)
        if self.play_beep:
            outbound_socket.log.debug("GetDigits play Beep enabled")
        outbound_socket.play_and_get_digits(max_digits=self.num_digits,
                            max_tries=self.retries, timeout=self.timeout,
                            terminators=self.finish_on_key,
                            sound_files=self.sound_files,
                            invalid_file=invalid_sound,
                            valid_digits=self.valid_digits,
                            play_beep=self.play_beep)
        event = outbound_socket.wait_for_action()
        digits = outbound_socket.get_var('pagd_input')
        # digits received
        if digits is not None:
            outbound_socket.log.info("GetDigits, Digits '%s' Received" % str(digits))
            if self.action:
                # Redirect
                params = {'Digits': digits}
                self.fetch_rest_xml(self.action, params, self.method)
            return
        # no digits received
        outbound_socket.log.info("GetDigits, No Digits Received")


class Hangup(Element):
    """Hangup the call
    schedule: schedule hangup in X seconds (default 0, immediate hangup)
    reason: rejected, busy or "" (default "", no reason)

    Note: when hangup is scheduled, reason is not taken into account.
    """
    def __init__(self):
        Element.__init__(self)
        self.reason = ""
        self.schedule = 0

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        self.schedule = self.extract_attribute_value("schedule", 0)
        reason = self.extract_attribute_value("reason")
        if reason == 'rejected':
            self.reason = 'CALL_REJECTED'
        elif reason == 'busy':
            self.reason = 'USER_BUSY'
        else:
            self.reason = ""

    def execute(self, outbound_socket):
        if self.text:
            self.log.info("Hangup Report: %s" % str(self.text))
        try:
            self.schedule = int(self.schedule)
        except ValueError:
            outbound_socket.log.error("Hangup (scheduled) Failed: bad value for 'schedule'")
            return
        # Schedule the call for hangup at a later time if 'schedule' param > 0
        if self.schedule > 0:
            if not self.reason:
                self.reason = "NORMAL_CLEARING"
            res = outbound_socket.sched_hangup("+%d %s" % (self.schedule, self.reason),
                                               lock=True)
            if res.is_success():
                outbound_socket.log.info("Hangup (scheduled) will be fired in %d secs !" \
                                                            % self.schedule)
            else:
                outbound_socket.log.error("Hangup (scheduled) Failed: %s"\
                                                    % str(res.get_response()))
            return "Scheduled in %d secs" % self.schedule
        # Immediate hangup
        else:
            if not self.reason:
                reason = "NORMAL_CLEARING"
            else:
                reason = self.reason
            outbound_socket.log.info("Hanging up now (%s)" % reason)
            outbound_socket.hangup(reason)
        return self.reason


class Number(Element):
    """Specify phone number in a nested Dial element.

    number: number to dial
    sendDigits: key to press after connecting to the number
    sendOnPreanswer: true or false, if true SendDigits is executed on early media (default false)
    gateways: gateway string separated by comma to dialout the number
    gatewayCodecs: codecs for each gateway separated by comma
    gatewayTimeouts: timeouts for each gateway separated by comma
    gatewayRetries: number of times to retry each gateway separated by comma
    extraDialString: extra freeswitch dialstring to be added while dialing out to number
    """
    def __init__(self):
        Element.__init__(self)
        self.number = ''
        self.gateways = []
        self.gateway_codecs = []
        self.gateway_timeouts = []
        self.gateway_retries = []
        self.extra_dial_string = ''
        self.send_digits = ''
        self.send_on_preanswer = False

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        self.number = element.text.strip()
        # don't allow "|" and "," in a number noun to avoid call injection
        self.number = re.split(',|\|', self.number)[0]
        self.extra_dial_string = \
                                self.extract_attribute_value('extraDialString')
        self.send_digits = self.extract_attribute_value('sendDigits')
        self.send_on_preanswer = self.extract_attribute_value('sendOnPreanswer') == 'true'

        gateways = self.extract_attribute_value('gateways')
        gateway_codecs = self.extract_attribute_value('gatewayCodecs')
        gateway_timeouts = self.extract_attribute_value('gatewayTimeouts')
        gateway_retries = self.extract_attribute_value('gatewayRetries')

        if gateways:
            # get list of gateways
            self.gateways = gateways.split(',')
        # split gw codecs by , but only outside the ''
        if gateway_codecs:
            self.gateway_codecs = \
                            re.split(''',(?=(?:[^'"]|'[^']*'|"[^"]*")*$)''',
                                                            gateway_codecs)
        if gateway_timeouts:
            self.gateway_timeouts = gateway_timeouts.split(',')
        if gateway_retries:
            self.gateway_retries = gateway_retries.split(',')



class Wait(Element):
    """Wait for some time to further process the call

    length: length of wait time in seconds
    """
    def __init__(self):
        Element.__init__(self)
        self.length = 1

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        try:
            length = int(self.extract_attribute_value('length'))
        except ValueError:
            raise RESTFormatException("Wait 'length' must be a positive integer")
        if length < 1:
            raise RESTFormatException("Wait 'length' must be a positive integer")
        self.length = length

    def execute(self, outbound_socket):
        outbound_socket.log.info("Wait Started for %d seconds" \
                                                    % self.length)
        pause_str = 'file_string://silence_stream://%s'\
                                % str(self.length * 1000)
        outbound_socket.playback(pause_str)
        event = outbound_socket.wait_for_action()


class Play(Element):
    """Play local audio file or at a URL

    url: url of audio file, MIME type on file must be set correctly
    loop: number of time to play the audio - (0 means infinite)
    """
    def __init__(self):
        Element.__init__(self)
        self.audio_directory = ''
        self.loop_times = 1
        self.sound_file_path = ''
        self.temp_audio_path = ''

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        # Extract Loop attribute
        try:
            loop = int(self.extract_attribute_value("loop", 1))
        except ValueError:
            loop = 1
        if loop < 0:
            raise RESTFormatException("Play 'loop' must be a positive integer or 0")
        if loop == 0 or loop > MAX_LOOPS:
            self.loop_times = MAX_LOOPS
        else:
            self.loop_times = loop
        # Pull out the text within the element
        audio_path = element.text.strip()

        if not audio_path:
            raise RESTFormatException("No File to play set !")

        if not is_valid_url(audio_path):
            self.sound_file_path = audio_path
        else:
            # set to temp path for prepare to process audio caching async
            self.temp_audio_path = audio_path

    def prepare(self, outbound_socket):
        if not self.sound_file_path:
            url = normalize_url_space(self.temp_audio_path)
            self.sound_file_path = get_resource(outbound_socket, url)

    def execute(self, outbound_socket):
        if self.sound_file_path:
            outbound_socket.set("playback_sleep_val=0")
            if self.loop_times == 1:
                play_str = self.sound_file_path
            else:
                outbound_socket.set("playback_delimiter=!")
                play_str = "file_string://silence_stream://1!"
                play_str += '!'.join([ self.sound_file_path for x in range(self.loop_times) ])
            outbound_socket.log.debug("Playing %d times" % self.loop_times)
            res = outbound_socket.playback(play_str)
            if res.is_success():
                event = outbound_socket.wait_for_action()
                if event.is_empty():
                    outbound_socket.log.warn("Play Break (empty event)")
                    return
                outbound_socket.log.debug("Play done (%s)" \
                        % str(event['Application-Response']))
            else:
                outbound_socket.log.error("Play Failed - %s" \
                                % str(res.get_response()))
            outbound_socket.log.info("Play Finished")
            return
        else:
            outbound_socket.log.error("Invalid Sound File - Ignoring Play")


class PreAnswer(Element):
    """Answer the call in Early Media Mode and execute nested element
    """
    def __init__(self):
        Element.__init__(self)
        self.nestables = ('Play', 'Speak', 'GetDigits', 'Wait', 'GetSpeech', 'Redirect', 'SIPTransfer')

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)

    def prepare(self, outbound_socket):
        for child_instance in self.children:
            if hasattr(child_instance, "prepare"):
                outbound_socket.validate_element(child_instance.get_element(), 
                                                 child_instance)
                child_instance.prepare(outbound_socket)

    def execute(self, outbound_socket):
        outbound_socket.preanswer()
        for child_instance in self.children:
            if hasattr(child_instance, "run"):
                child_instance.run(outbound_socket)
        outbound_socket.log.info("PreAnswer Completed")


class Record(Element):
    """Record audio from caller

    action: submit the result of the record to this URL
    method: submit to 'action' url using GET or POST
    maxLength: maximum number of seconds to record (default 60)
    timeout: seconds of silence before considering the recording complete (default 500)
            Only used when bothLegs is 'false' !
    playBeep: play a beep before recording (true/false, default true)
            Only used when bothLegs is 'false' !
    finishOnKey: Stop recording on this key
    fileFormat: file format (default mp3)
    filePath: complete file path to save the file to
    fileName: Default empty, if given this will be used for the recording
    bothLegs: record both legs (true/false, default false)
              no beep will be played
    redirect: if 'false', don't redirect to 'action', only request url
        and continue to next element. (default 'true')
    """
    def __init__(self):
        Element.__init__(self)
        self.silence_threshold = 500
        self.max_length = None
        self.timeout = None
        self.finish_on_key = ""
        self.file_path = ""
        self.play_beep = ""
        self.file_format = ""
        self.filename = ""
        self.both_legs = False
        self.action = ''
        self.method = ''
        self.redirect = True

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        max_length = self.extract_attribute_value("maxLength")
        timeout = self.extract_attribute_value("timeout")
        finish_on_key = self.extract_attribute_value("finishOnKey")
        self.file_path = self.extract_attribute_value("filePath")
        if self.file_path:
            self.file_path = os.path.normpath(self.file_path) + os.sep
        self.play_beep = self.extract_attribute_value("playBeep") == 'true'
        self.file_format = self.extract_attribute_value("fileFormat")
        if self.file_format not in ('wav', 'mp3'):
            raise RESTFormatException("Format must be 'wav' or 'mp3'")
        self.filename = self.extract_attribute_value("fileName")
        self.both_legs = self.extract_attribute_value("bothLegs") == 'true'
        self.redirect = self.extract_attribute_value("redirect") == 'true'

        self.action = self.extract_attribute_value("action")
        method = self.extract_attribute_value("method")
        if not method in ('GET', 'POST'):
            raise RESTAttributeException("method must be 'GET' or 'POST'")
        self.method = method

        # Validate maxLength
        try:
            max_length = int(max_length)
        except (ValueError, TypeError):
            raise RESTFormatException("Record 'maxLength' must be a positive integer")
        if max_length < 1:
            raise RESTFormatException("Record 'maxLength' must be a positive integer")
        self.max_length = str(max_length)
        # Validate timeout
        try:
            timeout = int(timeout)
        except (ValueError, TypeError):
            raise RESTFormatException("Record 'timeout' must be a positive integer")
        if timeout < 1:
            raise RESTFormatException("Record 'timeout' must be a positive integer")
        self.timeout = str(timeout)
        # Finish on Key
        self.finish_on_key = finish_on_key

    def execute(self, outbound_socket):
        if self.filename:
            filename = self.filename
        else:
            filename = "%s_%s" % (datetime.now().strftime("%Y%m%d-%H%M%S"),
                                outbound_socket.get_channel_unique_id())
        record_file = "%s%s.%s" % (self.file_path, filename, self.file_format)

        if self.both_legs:
            outbound_socket.set("RECORD_STEREO=true")
            outbound_socket.api("uuid_record %s start %s" \
                                %  (outbound_socket.get_channel_unique_id(),
                                   record_file)
                               )
            outbound_socket.api("sched_api +%s none uuid_record %s stop %s" \
                                % (self.max_length,
                                   outbound_socket.get_channel_unique_id(),
                                   record_file)
                               )
            outbound_socket.log.info("Record Both Executed")
        else:
            if self.play_beep:
                beep = 'tone_stream://%(300,200,700)'
                outbound_socket.playback(beep)
                event = outbound_socket.wait_for_action()
                # Log playback execute response
                outbound_socket.log.debug("Record Beep played (%s)" \
                                % str(event.get_header('Application-Response')))
            outbound_socket.start_dtmf()
            outbound_socket.log.info("Record Started")
            outbound_socket.record(record_file, self.max_length,
                                self.silence_threshold, self.timeout,
                                self.finish_on_key)
            event = outbound_socket.wait_for_action()
            outbound_socket.stop_dtmf()
            outbound_socket.log.info("Record Completed")

        # If action is set, redirect to this url
        # Otherwise, continue to next Element
        if self.action and is_valid_url(self.action):
            params = {}
            params['RecordingFileFormat'] = self.file_format
            params['RecordingFilePath'] = self.file_path
            params['RecordingFileName'] = filename
            params['RecordFile'] = record_file
            # case bothLegs is True
            if self.both_legs:
                # RecordingDuration not available for bothLegs because recording is in progress
                # Digits is empty for the same reason
                params['RecordingDuration'] = "-1"
                params['Digits'] = ""
            # case bothLegs is False
            else:
                try:
                    record_ms = event.get_header('variable_record_ms')
                    if not record_ms:
                        record_ms = "-1"
                    else:
                        record_ms = str(int(record_ms)) # check if integer
                except (ValueError, TypeError):
                    outbound_socket.log.warn("Invalid 'record_ms' : '%s'" % str(record_ms))
                    record_ms = "-1"
                params['RecordingDuration'] = record_ms
                record_digits = event.get_header("variable_playback_terminator_used")
                if record_digits:
                    params['Digits'] = record_digits
                else:
                    params['Digits'] = ""
            # fetch xml
            if self.redirect:
                self.fetch_rest_xml(self.action, params, method=self.method)
            else:
                spawn_raw(outbound_socket.send_to_url, self.action, params, method=self.method)


class SIPTransfer(Element):
    def __init__(self):
        Element.__init__(self)
        self.sip_url = ""

    def parse_element(self, element, uri=None):
        url = element.text.strip()
        sip_uris = set()
        for sip_uri in url.split(','):
            sip_uri = sip_uri.strip()
            if is_sip_url(sip_uri):
                sip_uris.add(sip_uri)
        self.sip_url = ','.join(list(sip_uris))

    def execute(self, outbound_socket):
        if self.sip_url:
            outbound_socket.log.info("SIPTransfer using sip uri '%s'" % str(self.sip_url))
            outbound_socket.set("plivo_sip_transfer_uri=%s" % self.sip_url)
            if outbound_socket.has_answered():
                outbound_socket.log.debug("SIPTransfer using deflect")
                outbound_socket.deflect(self.sip_url)
            else:
                outbound_socket.log.debug("SIPTransfer using redirect")
                outbound_socket.redirect(self.sip_url) 
            raise RESTSIPTransferException(self.sip_url)
        raise RESTFormatException("SIPTransfer must have a sip uri")


class Redirect(Element):
    """Redirect call flow to another Url.
    Url is set in element body
    method: GET or POST
    """
    def __init__(self):
        Element.__init__(self)
        self.method = ""
        self.url = ""

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        method = self.extract_attribute_value("method")
        if not method in ('GET', 'POST'):
            raise RESTAttributeException("Method must be 'GET' or 'POST'")
        url = element.text.strip()
        if not url:
            raise RESTFormatException("Redirect must have an URL")
        if is_valid_url(url):
            self.method = method
            self.url = url
            return
        raise RESTFormatException("Redirect URL '%s' not valid!" % str(url))

    def execute(self, outbound_socket):
        if self.url:
            self.fetch_rest_xml(self.url, method=self.method)
            return
        raise RESTFormatException("Redirect must have an URL")

class Notify(Element):
    """Callback to Url to notify this element has been executed.
    Url is set in element body
    method: GET or POST
    """
    def __init__(self):
        Element.__init__(self)
        self.method = ""
        self.url = ""

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        method = self.extract_attribute_value("method")
        if not method in ('GET', 'POST'):
            raise RESTAttributeException("Method must be 'GET' or 'POST'")
        url = element.text.strip()
        if not url:
            raise RESTFormatException("Notify must have an URL")
        if is_valid_url(url):
            self.method = method
            self.url = url
            return
        raise RESTFormatException("Notify URL '%s' not valid!" % str(url))

    def execute(self, outbound_socket):
        if not self.url:
            raise RESTFormatException("Notify must have an URL")

        if self.method is None:
            self.method = outbound_socket.default_http_method

        if not self.url:
            self.log.warn("Cannot send %s, no url !" % self.method)
            return None

        params = outbound_socket.session_params

        try:
            http_obj = HTTPRequest(outbound_socket.key, outbound_socket.secret, proxy_url=outbound_socket.proxy_url)
            data = http_obj.fetch_response(self.url, params, self.method, log=outbound_socket.log)
            return data
        except Exception, e:
            self.log.error("Sending to %s %s with %s -- Error: %s" \
                                        % (self.method, self.url, params, e))
        return None

class Speak(Element):
    """Speak text

    text: text to say
    voice: voice to be used based on engine
    language: language to use
    loop: number of times to say this text (0 for unlimited)
    engine: voice engine to be used for Speak (flite, cepstral)

    Extended params - Currently uses Callie (Female) Voice
    type: NUMBER, ITEMS, PERSONS, MESSAGES, CURRENCY, TIME_MEASUREMENT,
          CURRENT_DATE, CURRENT_TIME, CURRENT_DATE_TIME, TELEPHONE_NUMBER,
          TELEPHONE_EXTENSION, URL, IP_ADDRESS, EMAIL_ADDRESS, POSTAL_ADDRESS,
          ACCOUNT_NUMBER, NAME_SPELLED, NAME_PHONETIC, SHORT_DATE_TIME
    method: PRONOUNCED, ITERATED, COUNTED

    Flite Voices  : slt, rms, awb, kal
    Cepstral Voices : (Use any voice here supported by cepstral)
    """
    valid_methods = ('PRONOUNCED', 'ITERATED', 'COUNTED')
    valid_types = ('NUMBER', 'ITEMS', 'PERSONS', 'MESSAGES',
                   'CURRENCY', 'TIME_MEASUREMENT', 'CURRENT_DATE', ''
                   'CURRENT_TIME', 'CURRENT_DATE_TIME', 'TELEPHONE_NUMBER',
                   'TELEPHONE_EXTENSION', 'URL', 'IP_ADDRESS', 'EMAIL_ADDRESS',
                   'POSTAL_ADDRESS', 'ACCOUNT_NUMBER', 'NAME_SPELLED',
                   'NAME_PHONETIC', 'SHORT_DATE_TIME')

    def __init__(self):
        Element.__init__(self)
        self.loop_times = 1
        self.language = "en"
        self.sound_file_path = ""
        self.engine = ""
        self.voice = ""
        self.item_type = ""
        self.method = ""

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)
        # Extract Loop attribute
        try:
            loop = int(self.extract_attribute_value("loop", 1))
        except ValueError:
            loop = 1
        if loop < 0:
            raise RESTFormatException("Speak 'loop' must be a positive integer or 0")
        if loop == 0 or loop > MAX_LOOPS:
            self.loop_times = MAX_LOOPS
        else:
            self.loop_times = loop
        self.engine = self.extract_attribute_value("engine")
        self.language = self.extract_attribute_value("language")
        self.voice = self.extract_attribute_value("voice")
        item_type = self.extract_attribute_value("type")
        if item_type in self.valid_types:
            self.item_type = item_type
        method = self.extract_attribute_value("method")
        if method in self.valid_methods:
            self.method = method

    def execute(self, outbound_socket):
        if self.item_type and self.method:
            say_args = "%s %s %s %s" \
                    % (self.language, self.item_type,
                       self.method, self.text)
        else:
            say_args = "%s|%s|%s" % (self.engine, self.voice, self.text)
        if self.item_type and self.method:
            res = outbound_socket.say(say_args, loops=self.loop_times)
        else:
            res = outbound_socket.speak(say_args, loops=self.loop_times)
        if res.is_success():
            for i in range(self.loop_times):
                outbound_socket.log.debug("Speaking %d times ..." % (i+1))
                event = outbound_socket.wait_for_action()
                if event.is_empty():
                    outbound_socket.log.warn("Speak Break (empty event)")
                    return
                outbound_socket.log.debug("Speak %d times done (%s)" \
                            % ((i+1), str(event['Application-Response'])))
                gevent.sleep(0.01)
            outbound_socket.log.info("Speak Finished")
            return
        else:
            outbound_socket.log.error("Speak Failed - %s" \
                            % str(res.get_response()))
            return


class GetSpeech(Element):
    """Get speech from the caller

    action: URL to which the detected speech will be sent
    method: submit to 'action' url using GET or POST
    timeout: wait for this many seconds before returning
    playBeep: play a beep after all plays and says finish
    engine: engine to be used by detect speech
    grammar: grammar to load
    grammarPath: grammar path directory (default /usr/local/freeswitch/grammar)
    """
    def __init__(self):
        Element.__init__(self)
        self.nestables = ('Speak', 'Play', 'Wait')
        self.num_digits = None
        self.timeout = None
        self.finish_on_key = None
        self.action = None
        self.play_beep = ""
        self.valid_digits = ""
        self.invalid_digits_sound = ""
        self.retries = None
        self.sound_files = []
        self.method = ""

    def parse_element(self, element, uri=None):
        Element.parse_element(self, element, uri)

        self.grammar = self.extract_attribute_value("grammar")
        if not self.grammar:
            raise RESTAttributeException("GetSpeech 'grammar' is mandatory")
        self.grammarPath = self.extract_attribute_value("grammarPath").rstrip(os.sep)

        self.engine = self.extract_attribute_value("engine")
        if not self.engine:
            raise RESTAttributeException("GetSpeech 'engine' is mandatory")

        try:
            timeout = int(self.extract_attribute_value("timeout"))
        except (ValueError, TypeError):
            raise RESTFormatException("GetSpeech 'timeout' must be a positive integer")
        if timeout < 1:
            raise RESTFormatException("GetSpeech 'timeout' must be a positive integer")
        self.timeout = timeout

        self.play_beep = self.extract_attribute_value("playBeep") == 'true'

        action = self.extract_attribute_value("action")

        method = self.extract_attribute_value("method")
        if not method in ('GET', 'POST'):
            raise RESTAttributeException("Method, must be 'GET' or 'POST'")
        self.method = method

        if action and is_valid_url(action):
            self.action = action
        else:
            self.action = None

    def prepare(self, outbound_socket):
        for child_instance in self.children:
            if hasattr(child_instance, "prepare"):
                # :TODO Prepare Element concurrently
                child_instance.prepare(outbound_socket)

    def _parse_speech_result(self, result):
        return speech_result

    def execute(self, outbound_socket):
        speech_result = ''
        grammar_loaded = False
        grammars = self.grammar.split(';')

        # unload previous grammars
        outbound_socket.execute("detect_speech", "grammarsalloff")

        for i, grammar in enumerate(grammars):
            grammar_file = ''
            gpath = None
            raw_grammar = get_grammar_resource(outbound_socket, grammar)
            if raw_grammar:
                outbound_socket.log.debug("Found grammar : %s" % str(raw_grammar))
                grammar_file = "%s_%s" % (datetime.now().strftime("%Y%m%d-%H%M%S"),
                                          outbound_socket.get_channel_unique_id())
                gpath = self.grammarPath + os.sep + grammar_file + '.gram'
                outbound_socket.log.debug("Writing grammar to %s" % str(gpath))
                try:
                    f = open(gpath, 'w')
                    f.write(raw_grammar)
                    f.close()
                except Exception, e:
                    outbound_socket.log.error("GetSpeech result failure, cannot write grammar: %s" % str(grammar_file))
                    grammar_file = ''
            elif raw_grammar is None:
                outbound_socket.log.debug("Using grammar %s" % str(grammar))
                grammar_file = grammar
            else:
                outbound_socket.log.error("GetSpeech result failure, cannot get grammar: %s" % str(grammar))

            if grammar_file:
                if self.grammarPath and grammar_file[:4] != 'url:' and grammar_file[:8] != 'builtin:':
                    grammar_full_path = self.grammarPath + os.sep + grammar_file
                else:
                    if grammar_file[:4] == 'url:':
                        grammar_file = grammar_file[4:]

                    grammar_full_path = grammar_file
                # set grammar tag name
                grammar_tag = os.path.basename(grammar_file)

                if i == 0:
                    # init detection
                    speech_args = "%s %s %s" % (self.engine, grammar_full_path, grammar_tag)
                    res = outbound_socket.execute("detect_speech", speech_args)
                    if not res.is_success():
                        outbound_socket.log.error("GetSpeech Failed - %s" \
                                                      % str(res.get_response()))
                        if gpath:
                            try:
                                os.remove(gpath)
                            except:
                                pass
                        return
                    else:
                        grammar_loaded = True
                else:
                    # define grammar
                    speech_args = "grammar %s %s" % (grammar_full_path, grammar_tag)
                    res = outbound_socket.execute("detect_speech", speech_args)
                    if not res.is_success():
                        outbound_socket.log.error("GetSpeech Failed - %s" \
                                                      % str(res.get_response()))
                        if gpath:
                            try:
                                os.remove(gpath)
                            except:
                                pass
                        return
                # enable grammar
                speech_args = "grammaron %s" % (grammar_tag)
                res = outbound_socket.execute("detect_speech", speech_args)
                if not res.is_success():
                    outbound_socket.log.error("GetSpeech Failed - %s" \
                                                  % str(res.get_response()))
                    if gpath:
                        try:
                            os.remove(gpath)
                        except:
                            pass
                    return

        if grammar_loaded == True:
            outbound_socket.execute("detect_speech", "resume")
            for child_instance in self.children:
                if isinstance(child_instance, Play):
                    sound_file = child_instance.sound_file_path
                    if sound_file:
                        loop = child_instance.loop_times
                        if loop == 0:
                            loop = MAX_LOOPS  # Add a high number to Play infinitely
                        # Play the file loop number of times
                        for i in range(loop):
                            self.sound_files.append(sound_file)
                        # Infinite Loop, so ignore other children
                        if loop == MAX_LOOPS:
                            break
                elif isinstance(child_instance, Wait):
                    pause_secs = child_instance.length
                    pause_str = 'file_string://silence_stream://%s'\
                                    % (pause_secs * 1000)
                    self.sound_files.append(pause_str)
                elif isinstance(child_instance, Speak):
                    text = child_instance.text
                    # escape simple quote
                    text = text.replace("'", "\\'")
                    loop = child_instance.loop_times
                    child_type = child_instance.item_type
                    method = child_instance.method
                    say_str = ''
                    if child_type and method:
                        language = child_instance.language
                        say_args = "%s.wav %s %s %s '%s'" \
                                        % (language, language, child_type, method, text)
                        say_str = "${say_string %s}" % say_args
                    else:
                        engine = child_instance.engine
                        voice = child_instance.voice
                        say_str = "say:%s:%s:'%s'" % (engine, voice, text)
                    if not say_str:
                        continue
                    for i in range(loop):
                        self.sound_files.append(say_str)

            outbound_socket.log.info("GetSpeech Started %s" % self.sound_files)
            if self.play_beep:
                outbound_socket.log.debug("GetSpeech play Beep enabled")
                self.sound_files.append('tone_stream://%(300,200,700)')

            if self.sound_files:
                play_str = "!".join(self.sound_files)
                outbound_socket.set("playback_delimiter=!")
            else:
                play_str = ''

            if play_str:
                outbound_socket.playback(play_str)
                event = outbound_socket.wait_for_action()
                # Log playback execute response
                outbound_socket.log.debug("GetSpeech prompt played (%s)" \
                                % str(event.get_header('Application-Response')))
                outbound_socket.execute("detect_speech", "resume")

            timer = gevent.timeout.Timeout(self.timeout)
            timer.start()
            try:
                for x in range(1000):
                    event = outbound_socket.wait_for_action()
                    if event.is_empty():
                        outbound_socket.log.warn("GetSpeech Break (empty event)")
                        outbound_socket.execute("detect_speech", "stop")
                        outbound_socket.bgapi("uuid_break %s all" \
                            % outbound_socket.get_channel_unique_id())
                        return
                    elif event['Event-Name'] == 'DETECTED_SPEECH'\
                        and event['Speech-Type'] == 'detected-speech':
                            speech_result = event.get_body()
                            if speech_result is None:
                                speech_result = ''
                            outbound_socket.log.info("GetSpeech, result '%s'" % str(speech_result))
                            break
            except gevent.timeout.Timeout:
                outbound_socket.log.warn("GetSpeech Break (timeout)")
                outbound_socket.execute("detect_speech", "stop")
                if play_str:
                    outbound_socket.bgapi("uuid_break %s all" \
                        % outbound_socket.get_channel_unique_id())
                return
            finally:
                timer.cancel()
                if gpath:
                    try:
                        os.remove(gpath) 
                    except:
                        pass

            outbound_socket.execute("detect_speech", "stop")
            outbound_socket.bgapi("uuid_break %s all" \
                                % outbound_socket.get_channel_unique_id())

        if self.action:
            params = {'Grammar':'', 'Confidence':'0', 'Mode':'', 'SpeechResult':'', 'SpeechInterpretation': ''}
            if speech_result:
                try:
                    result = ' '.join(speech_result.splitlines())
                    doc = etree.fromstring(result)
                    sinterp = doc.find('interpretation')
                    sinput = doc.find('interpretation/input')
                    sinstance = doc.find('interpretation/instance/*')
                    if sinstance == None:
                        sinstance = doc.find('interpretation/instance')
                    if doc.tag != 'result':
                        raise RESTFormatException('No result Tag Present')
                    outbound_socket.log.debug("GetSpeech %s %s %s" % (str(doc), str(sinterp), str(sinput)))
                    params['Grammar'] = sinterp.get('grammar', '')
                    params['Confidence'] = sinterp.get('confidence', '0')
                    params['Mode'] = sinput.get('mode', '')
                    params['SpeechResult'] = sinput.text
                    params['SpeechInterpretation'] = sinstance.text
                except Exception, e:
                    params['Confidence'] = "-1"
                    params['SpeechResultError'] = str(speech_result)
                    outbound_socket.log.error("GetSpeech result failure, cannot parse result: %s" % str(e))
            # Redirect
            self.fetch_rest_xml(self.action, params, self.method)

########NEW FILE########
__FILENAME__ = exceptions
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.


class RESTFormatException(Exception):
    pass


class RESTSyntaxException(Exception):
    pass


class RESTAttributeException(Exception):
    pass


class RESTDownloadException(Exception):
    pass


class RESTNoExecuteException(Exception):
    pass


class RESTHangup(Exception):
    pass


class RESTRedirectException(Exception):
    def __init__(self, url=None, params={}, method=None):
        self.url = url
        self.method = method
        self.params = params

    def get_url(self):
        return self.url

    def get_method(self):
        return self.method

    def get_params(self):
        return self.params


class RESTSIPTransferException(Exception):
    def __init__(self, sip_url=None):
        self.sip_url = sip_url

    def get_sip_url(self):
        return self.sip_url


class UnrecognizedElementException(Exception):
    pass


class UnsupportedResourceFormat(Exception):
    pass

########NEW FILE########
__FILENAME__ = helpers
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from gevent import monkey
monkey.patch_all()

import base64
import ConfigParser
from hashlib import sha1
import hmac
import httplib
import os
import os.path
import urllib
import urllib2
import urlparse
import uuid
import traceback
import re
import ujson as json
from werkzeug.datastructures import MultiDict

# remove depracated warning in python2.6
try:
    from hashlib import md5 as _md5
except ImportError:
    import md5
    _md5 = md5.new


MIME_TYPES = {'audio/mpeg': 'mp3',
              'audio/x-wav': 'wav',
              }


VALID_SOUND_PROTOCOLS = (
    "tone_stream://",
    "shout://",
    "vlc://",
)

_valid_sound_proto_re = re.compile(r"^({0})".format("|".join(VALID_SOUND_PROTOCOLS)))

def get_substring(start_char, end_char, data):
    if data is None or not data:
        return ""
    start_pos = data.find(start_char)
    if start_pos < 0:
        return ""
    end_pos = data.find(end_char)
    if end_pos < 0:
        return ""
    return data[start_pos+len(start_char):end_pos]

def url_exists(url):
    p = urlparse.urlparse(url)
    if p[4]:
        extra_string = "%s?%s" %(p[2], p[4])
    else:
        extra_string = p[2]
    try:
        connection = httplib.HTTPConnection(p[1])
        connection.request('HEAD', extra_string)
        response = connection.getresponse()
        connection.close()
        return response.status == httplib.OK
    except Exception:
        return False

def file_exists(filepath):
    return os.path.isfile(filepath)

def normalize_url_space(url):
    return url.strip().replace(' ', '+')

def get_post_param(request, key):
    try:
        return request.form[key]
    except KeyError:
        return ""

def get_http_param(request, key):
    try:
        return request.args[key]
    except KeyError:
        return ""

def is_valid_url(value):
    if not value:
        return False
    return value[:7] == 'http://' or value[:8] == 'https://'

def is_sip_url(value):
    if not value:
        return False
    return value[:4] == 'sip:'


def is_valid_sound_proto(value):
    if not value:
        return False
    return True if _valid_sound_proto_re.match(value) else False


class HTTPErrorProcessor(urllib2.HTTPErrorProcessor):
    def https_response(self, request, response):
        code, msg, hdrs = response.code, response.msg, response.info()
        if code >= 300:
            response = self.parent.error(
                'http', request, response, code, msg, hdrs)
        return response


class HTTPUrlRequest(urllib2.Request):
    def get_method(self):
        if getattr(self, 'http_method', None):
            return self.http_method
        return urllib2.Request.get_method(self)


class HTTPRequest:
    """Helper class for preparing HTTP requests.
    """
    USER_AGENT = 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.835.35 Safari/535.1'

    def __init__(self, auth_id='', auth_token='', proxy_url=None):
        """initialize a object

        auth_id: Plivo SID/ID
        auth_token: Plivo token

        returns a HTTPRequest object
        """
        self.auth_id = auth_id
        self.auth_token = auth_token.encode('ascii')
        self.opener = None
        self.proxy_url = proxy_url

    def _build_get_uri(self, uri, params):
        if params:
            if uri.find('?') > 0:
                uri =  uri.split('?')[0]
            uri = uri + '?' + urllib.urlencode(params)
        return uri

    def _prepare_http_request(self, uri, params, method='POST'):
        # install error processor to handle HTTP 201 response correctly
        if self.opener is None:
            self.opener = urllib2.build_opener(HTTPErrorProcessor)
            urllib2.install_opener(self.opener)

        proxy_url = self.proxy_url
        if proxy_url:
            proxy = proxy_url.split('http://')[1]
            proxyhandler = urllib2.ProxyHandler({'http': proxy})
            opener = urllib2.build_opener(proxyhandler)
            urllib2.install_opener(opener)

        if method and method == 'GET':
            uri = self._build_get_uri(uri, params)
            _request = HTTPUrlRequest(uri)
        else:
            _request = HTTPUrlRequest(uri, urllib.urlencode(params))
            if method and (method == 'DELETE' or method == 'PUT'):
                _request.http_method = method

        _request.add_header('User-Agent', self.USER_AGENT)

        if self.auth_id and self.auth_token:
            # append the POST variables sorted by key to the uri
            # and transform None to '' and unicode to string
            s = uri
            for k, v in sorted(params.items()):
                if k:
                    if v is None:
                        x = ''
                    else:
                        x = str(v)
                    s += k + x

            # compute signature and compare signatures
            signature =  base64.encodestring(hmac.new(self.auth_token, s, sha1).\
                                                                digest()).strip()
            _request.add_header("X-PLIVO-SIGNATURE", "%s" % signature)
        return _request

    def fetch_response(self, uri, params={}, method='POST', log=None):
        if not method in ('GET', 'POST'):
            raise NotImplementedError('HTTP %s method not implemented' \
                                                            % method)
        # Read all params in the query string and include them in params
        _params = params.copy()
        query = urlparse.urlsplit(uri)[3]
        if query:
            if log:
                log.debug("Extra params found in url query for %s %s" \
                                % (method, uri))
            qs = urlparse.parse_qs(query)
            for k, v in qs.iteritems():
                if v:
                    _params[k] = v[-1]
        if log:
            log.info("Fetching %s %s with %s" \
                            % (method, uri, _params))
        req = self._prepare_http_request(uri, _params, method)
        res = urllib2.urlopen(req).read()
        if log:
            log.info("Sent to %s %s with %s -- Result: %s" \
                                % (method, uri, _params, res))
        return res


def get_config(filename):
    config = ConfigParser.SafeConfigParser()
    config.read(filename)
    return config


def get_json_config(url):
    config = HTTPJsonConfig()
    config.read(url)
    return config


def get_conf_value(config, section, key):
    try:
        value = config.get(section, key)
        return str(value)
    except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
        return ""


class HTTPJsonConfig(object):
    """
    Json Config Format is :
    {'section1':{'key':'value', ..., 'keyN':'valueN'},
     'section2 :{'key':'value', ..., 'keyN':'valueN'},
     ...
     'sectionN :{'key':'value', ..., 'keyN':'valueN'},
    }
    """
    def __init__(self):
        self.jdata = None

    def read(self, url):
        req = HTTPRequest()
        data = req.fetch_response(url, params={}, method='POST')
        self.jdata = json.loads(data)

    def get(self, section, key):
        try:
            val = self.jdata[section][key]
            if val is None:
                return ""
            return str(val)
        except KeyError:
            return ""

    def dumps(self):
        return self.jdata


class PlivoConfig(object):
    def __init__(self, source):
        self._cfg = ConfigParser.SafeConfigParser()
        self._cfg.optionxform = str # make case sensitive
        self._source = source
        self._json_cfg = None
        self._json_source = None
        self._cache = {}

    def _set_cache(self):
        if self._json_cfg:
            self._cache = dict(self._json_cfg.dumps())
        else:
            self._cache = {}
            for section in self._cfg.sections():
                self._cache[section] = {}
                for var, val in self._cfg.items(section):
                    self._cache[section][var] = val

    def read(self):
        self._cfg.read(self._source)
        try:
            self._json_source = self._cfg.get('common', 'JSON_CONFIG_URL')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            self._json_source = None
        if self._json_source:
            self._json_cfg = HTTPJsonConfig()
            self._json_cfg.read(self._json_source)
        else:
            self._json_source = None
            self._json_cfg = None
        self._set_cache()

    def dumps(self):
        return self._cache

    def __getitem__(self, section):
        return self._cache[section]

    def get(self, section, key, **kwargs):
        try:
            return self._cache[section][key].strip()
        except KeyError, e:
            try:
                d = kwargs['default']
                return d
            except KeyError:
                raise e

    def reload(self):
        self.read()


def get_resource(socket, url):
    try:
        if socket.cache:
            # don't do cache if not a remote file
            if not url[:7].lower() == "http://" \
                and not url[:8].lower() == "https://":
                return url

            cache_url = socket.cache['url'].strip('/')
            data = {}
            data['url'] = url
            url_values = urllib.urlencode(data)
            full_url = '%s/CacheType/?%s' % (cache_url, url_values)
            req = urllib2.Request(full_url)
            handler = urllib2.urlopen(req)
            response = handler.read()
            result = json.loads(response)
            cache_type = result['CacheType']
            if cache_type == 'wav':
                wav_stream = 'shell_stream://%s %s/Cache/?%s' % (socket.cache['script'], cache_url, url_values)
                return wav_stream
            elif cache_type == 'mp3':
                _url = socket.cache['url'][7:].strip('/')
                mp3_stream = "shout://%s/Cache/?%s" % (_url, url_values)
                return mp3_stream
            else:
                socket.log.warn("Unsupported format %s" % str(cache_type))

    except Exception, e:
        socket.log.error("Cache Error !")
        socket.log.error("Cache Error: %s" % str(e))

    if url[:7].lower() == "http://":
        if url[-4:] != ".wav":
            audio_path = url[7:]
            url = "shout://%s" % audio_path
    elif url[:8].lower() == "https://":
        if url[-4:] != ".wav":
            audio_path = url[8:]
            url = "shout://%s" % audio_path

    return url


def get_grammar_resource(socket, grammar):
    try:
        # don't do cache if not a remote file
        # (local file or raw grammar)
        if grammar[:4] == 'raw:':
            socket.log.debug("Using raw grammar")
            return grammar[4:]
        if grammar[:4] == 'url:':
            socket.log.debug("Using raw grammar url")
            return None
        if grammar[:8] == 'builtin:':
            socket.log.debug("Using builtin grammar")
            return None
        if grammar[:7].lower() != "http://" \
            and grammar[:8].lower() != "https://":
            socket.log.debug("Using local grammar file")
            return None
        socket.log.debug("Using remote grammar url")
        # do cache
        if socket.cache:
            try:
                cache_url = socket.cache['url'].strip('/')
                data = {}
                data['url'] = grammar
                url_values = urllib.urlencode(data)
                full_url = '%s/CacheType/?%s' % (cache_url, url_values)
                req = urllib2.Request(full_url)
                handler = urllib2.urlopen(req)
                response = handler.read()
                result = json.loads(response)
                cache_type = result['CacheType']
                if not cache_type in ('grxml', 'jsgf'):
                    socket.log.warn("Unsupported format %s" % str(cache_type))
                    raise("Unsupported format %s" % str(cache_type))
                full_url = '%s/Cache/?%s' % (cache_url, url_values)
                socket.log.debug("Fetch grammar from %s" % str(full_url))
                req = urllib2.Request(full_url)
                handler = urllib2.urlopen(req)
                response = handler.read()
                return response
            except Exception, e:
                socket.log.error("Grammar Cache Error !")
                socket.log.error("Grammar Cache Error: %s" % str(e))
        # default fetch direct url
        socket.log.debug("Fetching grammar from %s" % str(grammar))
        req = urllib2.Request(grammar)
        handler = urllib2.urlopen(req)
        response = handler.read()
        socket.log.debug("Grammar fetched from %s: %s" % (str(grammar), str(response)))
        if not response:
            raise Exception("No Grammar response")
        return response
    except Exception, e:
        socket.log.error("Grammar Cache Error !")
        socket.log.error("Grammar Cache Error: %s" % str(e))
    return False



########NEW FILE########
__FILENAME__ = inboundsocket
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from gevent import monkey
monkey.patch_all()

import os.path
import uuid
try:
    import xml.etree.cElementTree as etree
except ImportError:
    from xml.etree.elementtree import ElementTree as etree

from gevent import spawn_raw
from gevent import pool
import gevent.event

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.rest.freeswitch.helpers import HTTPRequest, get_substring, \
                                        is_valid_url, \
                                        file_exists, normalize_url_space, \
                                        get_resource, \
                                        is_valid_sound_proto


EVENT_FILTER = "BACKGROUND_JOB CHANNEL_PROGRESS CHANNEL_PROGRESS_MEDIA CHANNEL_HANGUP_COMPLETE CHANNEL_STATE SESSION_HEARTBEAT CALL_UPDATE RECORD_STOP CUSTOM conference::maintenance"


class RESTInboundSocket(InboundEventSocket):
    """
    Interface between REST API and the InboundSocket
    """
    def __init__(self, server):
        self.server = server
        self.log = self.server.log
        self.cache = self.server.get_cache()

        InboundEventSocket.__init__(self, self.get_server().fs_host,
                                    self.get_server().fs_port,
                                    self.get_server().fs_password,
                                    filter=EVENT_FILTER,
                                    trace=self.get_server()._trace)
        # Mapping of Key: job-uuid - Value: request_uuid
        self.bk_jobs = {}
        # Transfer jobs: call_uuid - Value: inline dptools to execute
        self.xfer_jobs = {}
        # Conference sync jobs
        self.conf_sync_jobs = {}
        # Call Requests
        self.call_requests = {}

    def get_server(self):
        return self.server

    def reload_config(self):
        self.get_server().load_config(reload=True)
        self.log = self.server.log
        self.cache = self.server.get_cache()

    def get_extra_fs_vars(self, event):
        params = {}
        if not event or not self.get_server().extra_fs_vars:
            return params
        for var in self.get_server().extra_fs_vars.split(','):
            var = var.strip()
            if var:
                val = event.get_header(var)
                if val is None:
                    val = ''
                params[var] = val
        return params

    def on_record_stop(self, event):
        if not self.get_server().record_url:
            return
        rpath = event['Record-File-Path'] or ''
        if not rpath or rpath == 'all':
            return
        calluuid = event['Unique-ID'] or ''
        rms = event['variable_record_seconds'] or ''
        params = {'CallUUID': calluuid,
                  'RecordFile': rpath,
                  'RecordDuration': rms}
        self.log.info("Record Stop event %s"  % str(params))
        self.send_to_url(self.get_server().record_url, params)

    def on_custom(self, event):
        if event['Event-Subclass'] == 'conference::maintenance' \
            and event['Action'] == 'stop-recording':
            if not self.get_server().record_url:
                return
            # special case to manage record files
            rpath = event['Path']
            # if filename is empty or 'all', skip upload
            if not rpath or rpath == 'all':
                return
            # get room name
            room = event["Conference-Name"]
            rms = event['variable_record_seconds'] or ''
            params = {'ConferenceName': room,
                      'RecordFile': rpath,
                      'RecordDuration': rms}
            self.log.info("Conference Record Stop event %s"  % str(params))
            self.send_to_url(self.get_server().record_url, params)

    def on_background_job(self, event):
        """
        Capture Job Event
        Capture background job only for originate and conference,
        and ignore all other jobs
        """
        job_cmd = event['Job-Command']
        job_uuid = event['Job-UUID']
        # TEST MIKE
        if job_cmd == 'originate' and job_uuid:
            try:
                status, reason = event.get_body().split(' ', 1)
            except ValueError:
                return
            request_uuid = self.bk_jobs.pop(job_uuid, None)
            if not request_uuid:
                return

            # case GroupCall
            if event['variable_plivo_group_call'] == 'true':
                status = status.strip()
                reason = reason.strip()
                if status[:3] != '+OK':
                    self.log.info("GroupCall Attempt Done for RequestUUID %s (%s)" \
                                                    % (request_uuid, reason))
                    return
                self.log.warn("GroupCall Attempt Failed for RequestUUID %s (%s)" \
                                                    % (request_uuid, reason))
                return

            # case Call and BulkCall
            try:
                call_req = self.call_requests[request_uuid]
            except KeyError:
                return
            # Handle failure case of originate
            # This case does not raise a on_channel_hangup event.
            # All other failures will be captured by on_channel_hangup
            status = status.strip()
            reason = reason.strip()
            if status[:3] != '+OK':
                # In case ring/early state done, just warn
                # releasing call request will be done in hangup event
                if call_req.state_flag in ('Ringing', 'EarlyMedia'):
                    self.log.warn("Call Attempt Done (%s) for RequestUUID %s but Failed (%s)" \
                                                    % (call_req.state_flag, request_uuid, reason))
                    # notify end
                    self.log.debug("Notify Call success for RequestUUID %s" % request_uuid)
                    call_req.notify_call_end()
                    return
                # If no more gateways, release call request
                elif not call_req.gateways:
                    self.log.warn("Call Failed for RequestUUID %s but No More Gateways (%s)" \
                                                    % (request_uuid, reason))
                    # notify end
                    self.log.debug("Notify Call success for RequestUUID %s" % request_uuid)
                    call_req.notify_call_end()
                    # set an empty call_uuid
                    call_uuid = ''
                    hangup_url = call_req.hangup_url
                    self.set_hangup_complete(request_uuid, call_uuid,
                                             reason, event, hangup_url)
                    return
                # If there are gateways and call request state_flag is not set
                # try again a call
                elif call_req.gateways:
                    self.log.warn("Call Failed without Ringing/EarlyMedia for RequestUUID %s - Retrying Now (%s)" \
                                                    % (request_uuid, reason))
                    # notify try a new call
                    self.log.debug("Notify Call retry for RequestUUID %s" % request_uuid)
                    call_req.notify_call_try()
        elif job_cmd == 'conference' and job_uuid:
            result = event.get_body().strip() or ''
            async_res = self.conf_sync_jobs.pop(job_uuid, None)
            if async_res is None:
                return
            elif async_res is True:
                self.log.info("Conference Api (async) Response for JobUUID %s -- %s" % (job_uuid, result))
                return
            async_res.set(result)
            self.log.info("Conference Api (sync) Response for JobUUID %s -- %s" % (job_uuid, result))

    def on_channel_progress(self, event):
        request_uuid = event['variable_plivo_request_uuid']
        direction = event['Call-Direction']
        # Detect ringing state
        if request_uuid and direction == 'outbound':
            accountsid = event['variable_plivo_accountsid']
            # case GroupCall
            if event['variable_plivo_group_call'] == 'true':
                # get ring_url
                ring_url = event['variable_plivo_ring_url']
            # case BulkCall and Call
            else:
                try:
                    call_req = self.call_requests[request_uuid]
                except (KeyError, AttributeError):
                    return
                # notify call and
                self.log.debug("Notify Call success (Ringing) for RequestUUID %s" % request_uuid)
                call_req.notify_call_end()
                # only send if not already ringing/early state
                if not call_req.state_flag:
                    # set state flag to 'Ringing'
                    call_req.state_flag = 'Ringing'
                    # clear gateways to avoid retry
                    call_req.gateways = []
                    # get ring_url
                    ring_url = call_req.ring_url
                else:
                    return

            # send ring if ring_url found
            if ring_url:
                called_num = event['variable_plivo_destination_number']
                if not called_num or called_num == '_undef_':
                    called_num = event['Caller-Destination-Number'] or ''
                called_num = called_num.lstrip('+')
                caller_num = event['Caller-Caller-ID-Number'] or ''
                call_uuid = event['Unique-ID'] or ''
                self.log.info("Call from %s to %s Ringing for RequestUUID %s" \
                                % (caller_num, called_num, request_uuid))
                params = {'To': called_num,
                          'RequestUUID': request_uuid,
                          'Direction': direction,
                          'CallStatus': 'ringing',
                          'From': caller_num,
                          'CallUUID': call_uuid
                         }
                # add extra params
                extra_params = self.get_extra_fs_vars(event)
                if extra_params:
                    params.update(extra_params)
                if accountsid:
                    params['AccountSID'] = accountsid
                spawn_raw(self.send_to_url, ring_url, params)

    def on_channel_progress_media(self, event):
        request_uuid = event['variable_plivo_request_uuid']
        direction = event['Call-Direction']
        # Detect early media state
        # See http://wiki.freeswitch.org/wiki/Early_media#Early_Media_And_Dialing_Out
        if request_uuid and direction == 'outbound':
            accountsid = event['variable_plivo_accountsid']
            # case BulkCall and Call
            try:
                call_req = self.call_requests[request_uuid]
            except (KeyError, AttributeError):
                return
            # notify call end
            self.log.debug("Notify Call success (EarlyMedia) for RequestUUID %s" % request_uuid)
            call_req.notify_call_end()
            # only send if not already ringing/early state
            if not call_req.state_flag:
                # set state flag to 'EarlyMedia'
                call_req.state_flag = 'EarlyMedia'
                # clear gateways to avoid retry
                call_req.gateways = []
                # get ring_url
                ring_url = call_req.ring_url
            else:
                return

            # send ring if ring_url found
            if ring_url:
                called_num = event['variable_plivo_destination_number']
                if not called_num or called_num == '_undef_':
                    called_num = event['Caller-Destination-Number'] or ''
                called_num = called_num.lstrip('+')
                caller_num = event['Caller-Caller-ID-Number'] or ''
                call_uuid = event['Unique-ID'] or ''
                self.log.info("Call from %s to %s in EarlyMedia for RequestUUID %s" \
                                % (caller_num, called_num, request_uuid))
                params = {'To': called_num,
                          'RequestUUID': request_uuid,
                          'Direction': direction,
                          'CallStatus': 'ringing',
                          'From': caller_num,
                          'CallUUID': call_uuid
                         }
                # add extra params
                extra_params = self.get_extra_fs_vars(event)
                if extra_params:
                    params.update(extra_params)
                if accountsid:
                    params['AccountSID'] = accountsid
                spawn_raw(self.send_to_url, ring_url, params)

    def on_call_update(self, event):
        """A Leg from API outbound call answered
        """
        # if plivo_app != 'true', check b leg Dial callback
        plivo_app_flag = event['variable_plivo_app'] == 'true'
        if not plivo_app_flag:
            # request Dial callbackUrl if needed
            aleg_uuid = event['Bridged-To']
            if not aleg_uuid:
                return
            bleg_uuid = event['Unique-ID']
            if not bleg_uuid:
                return
            disposition = event['variable_endpoint_disposition']
            if disposition != 'ANSWER':
                return
            ck_url = event['variable_plivo_dial_callback_url']
            if not ck_url:
                return
            ck_method = event['variable_plivo_dial_callback_method']
            if not ck_method:
                return
            params = {'DialBLegUUID': bleg_uuid,
                      'DialALegUUID': aleg_uuid,
                      'DialBLegStatus': 'answer',
                      'CallUUID': aleg_uuid
                     }
            # add extra params
            extra_params = self.get_extra_fs_vars(event)
            if extra_params:
                params.update(extra_params)
            spawn_raw(self.send_to_url, ck_url, params, ck_method)
            return

    def on_channel_bridge(self, event):
        """B Leg from Dial element answered
        """
        # if plivo_app != 'true', check b leg Dial callback
        # request Dial callbackUrl if needed
        aleg_uuid = event['Bridge-A-Unique-ID']
        if not aleg_uuid:
            return
        bleg_uuid = event['Bridge-B-Unique-ID']
        if not bleg_uuid:
            return
        disposition = event['variable_endpoint_disposition']
        if disposition != 'ANSWER':
            return
        app_vars = event['variable_current_application_data']
        if not 'plivo_dial_callback_url' in app_vars:
            return
        ck_url = app_vars.split('plivo_dial_callback_url=')[1].split(',')[0]
        if not 'plivo_dial_callback_method' in app_vars:
            return
        ck_method = app_vars.split('plivo_dial_callback_method=')[1].split(',')[0]
        params = {'DialBLegUUID': bleg_uuid,
                  'DialALegUUID': aleg_uuid,
                  'DialBLegStatus': 'answer',
                  'CallUUID': aleg_uuid
                 }
        spawn_raw(self.send_to_url, ck_url, params, ck_method)
        return

    def on_channel_hangup_complete(self, event):
        """Capture Channel Hangup Complete
        """
        # if plivo_app != 'true', check b leg Dial callback

        plivo_app_flag = event['variable_plivo_app'] == 'true'
        if not plivo_app_flag:
            # request Dial callbackUrl if needed
            ck_url = event['variable_plivo_dial_callback_url']
            if not ck_url:
                return
            ck_method = event['variable_plivo_dial_callback_method']
            if not ck_method:
                return
            aleg_uuid = event['variable_plivo_dial_callback_aleg']
            if not aleg_uuid:
                return
            hangup_cause = event['Hangup-Cause'] or ''
            # don't send http request for B legs losing bridge race
            if hangup_cause == 'LOSE_RACE':
                return
            bleg_uuid = event['Unique-ID']
            
            params = {'DialBLegUUID': bleg_uuid,
                      'DialALegUUID': aleg_uuid,
                      'DialBLegStatus': 'hangup',
                      'DialBLegHangupCause': hangup_cause,
                      'CallUUID': aleg_uuid
                     }
            # add extra params
            extra_params = self.get_extra_fs_vars(event)
            if extra_params:
                params.update(extra_params)
            spawn_raw(self.send_to_url, ck_url, params, ck_method)
            return

        # Get call direction
        direction = event['Call-Direction']

        # Handle incoming call hangup
        if direction == 'inbound':
            call_uuid = event['Unique-ID']
            reason = event['Hangup-Cause']
            # send hangup
            try:
                self.set_hangup_complete(None, call_uuid, reason, event, None)
            except Exception, e:
                self.log.error(str(e))
        # Handle outgoing call hangup
        else:
            # check if found a request uuid
            # if not, ignore hangup event
            request_uuid = event['variable_plivo_request_uuid']
            if not request_uuid and direction != 'outbound':
                return

            call_uuid = event['Unique-ID']
            reason = event['Hangup-Cause']

            # case GroupCall
            if event['variable_plivo_group_call'] == 'true':
                hangup_url = event['variable_plivo_hangup_url']
            # case BulkCall and Call
            else:
                try:
                    call_req = self.call_requests[request_uuid]
                except KeyError:
                    return
                # If there are gateways to try again, spawn originate
                if call_req.gateways:
                    self.log.debug("Call Failed for RequestUUID %s - Retrying (%s)" \
                                    % (request_uuid, reason))
                    # notify try call
                    self.log.debug("Notify Call retry for RequestUUID %s" % request_uuid)
                    call_req.notify_call_try()
                    return
                # else clean call request
                hangup_url = call_req.hangup_url
                # notify call end
                self.log.debug("Notify Call success for RequestUUID %s" % request_uuid)
                call_req.notify_call_end()

            # send hangup
            try:
                self.set_hangup_complete(request_uuid, call_uuid, reason, event, hangup_url)
            except Exception, e:
                self.log.error(str(e))

    def on_channel_state(self, event):
        # When transfer is ready to start,
        # channel goes in state CS_RESET
        if event['Channel-State'] == 'CS_RESET':
            call_uuid = event['Unique-ID']
            xfer = self.xfer_jobs.pop(call_uuid, None)
            if not xfer:
                return
            self.log.info("TransferCall In Progress for %s" % call_uuid)
            # unset transfer progress flag
            self.set_var("plivo_transfer_progress", "false", uuid=call_uuid)
            # really transfer now
            res = self.api("uuid_transfer %s '%s' inline" % (call_uuid, xfer))
            if res.is_success():
                self.log.info("TransferCall Done for %s" % call_uuid)
            else:
                self.log.info("TransferCall Failed for %s: %s" \
                               % (call_uuid, res.get_response()))
        # On state CS_HANGUP, remove transfer job linked to call_uuid
        elif event['Channel-State'] == 'CS_HANGUP':
            call_uuid = event['Unique-ID']
            # try to clean transfer call
            xfer = self.xfer_jobs.pop(call_uuid, None)
            if xfer:
                self.log.warn("TransferCall Aborted (hangup) for %s" % call_uuid)

    def on_session_heartbeat(self, event):
        """Capture every heartbeat event in a session and post info
        """
        params = {}
        answer_seconds_since_epoch = float(event['Caller-Channel-Answered-Time'])/1000000
        # using UTC here .. make sure FS is using UTC also
        params['AnsweredTime'] = str(answer_seconds_since_epoch)
        heartbeat_seconds_since_epoch = float(event['Event-Date-Timestamp'])/1000000
        # using UTC here .. make sure FS is using UTC also
        params['HeartbeatTime'] = str(heartbeat_seconds_since_epoch)
        params['ElapsedTime'] = str(heartbeat_seconds_since_epoch - answer_seconds_since_epoch)
        called_num = event['variable_plivo_destination_number']
        if not called_num or called_num == '_undef_':
            called_num = event['Caller-Destination-Number'] or ''
        called_num = called_num.lstrip('+')
        params['To'] = called_num
        params['From'] = event['Caller-Caller-ID-Number'].lstrip('+')
        params['CallUUID'] = event['Unique-ID']
        params['Direction'] = event['Call-Direction']
        forwarded_from = get_substring(':', '@',
                            event['variable_sip_h_Diversion'])
        if forwarded_from:
            params['ForwardedFrom'] = forwarded_from.lstrip('+')
        if event['Channel-State'] == 'CS_EXECUTE':
            params['CallStatus'] = 'in-progress'
        # RequestUUID through which this call was initiated if outbound
        request_uuid = event['variable_plivo_request_uuid']
        if request_uuid:
            params['RequestUUID'] = request_uuid
        accountsid = event['variable_plivo_accountsid']
        if accountsid:
            params['AccountSID'] = accountsid

        self.log.debug("Got Session Heartbeat from Freeswitch: %s" % params)

        if self.get_server().call_heartbeat_url:
            self.log.debug("Sending heartbeat to callback: %s" % self.get_server().call_heartbeat_url)
            spawn_raw(self.send_to_url, self.get_server().call_heartbeat_url, params)

    def set_hangup_complete(self, request_uuid, call_uuid, reason, event, hangup_url):
        params = {}
        # add extra params
        params = self.get_extra_fs_vars(event)

        # case incoming call
        if not request_uuid:
            self.log.info("Hangup for Incoming CallUUID %s Completed, HangupCause %s" \
                                                        % (call_uuid, reason))
            # get hangup url
            hangup_url = event['variable_plivo_hangup_url']
            if hangup_url:
                self.log.debug("Using HangupUrl for CallUUID %s" \
                                                        % call_uuid)
            else:
                if self.get_server().default_hangup_url:
                    hangup_url = self.get_server().default_hangup_url
                    self.log.debug("Using HangupUrl from DefaultHangupUrl for CallUUID %s" \
                                                        % call_uuid)
                elif event['variable_plivo_answer_url']:
                    hangup_url = event['variable_plivo_answer_url']
                    self.log.debug("Using HangupUrl from AnswerUrl for CallUUID %s" \
                                                        % call_uuid)
                elif self.get_server().default_answer_url:
                    hangup_url = self.get_server().default_answer_url
                    self.log.debug("Using HangupUrl from DefaultAnswerUrl for CallUUID %s" \
                                                        % call_uuid)
            if not hangup_url:
                self.log.debug("No HangupUrl for Incoming CallUUID %s" % call_uuid)
                return
            called_num = event['variable_plivo_destination_number']
            if not called_num or called_num == '_undef_':
                called_num = event['Caller-Destination-Number'] or ''
            called_num = called_num.lstrip('+')
            caller_num = event['Caller-Caller-ID-Number']
            direction = event['Call-Direction']
        # case outgoing call, add params
        else:
            self.log.info("Hangup for Outgoing CallUUID %s Completed, HangupCause %s, RequestUUID %s"
                                        % (call_uuid, reason, request_uuid))
            try:
                call_req = self.call_requests[request_uuid]
                called_num = call_req.to.lstrip('+')
                caller_num = call_req._from
                if call_req._accountsid:
                    params['AccountSID'] = call_req._accountsid
                direction = "outbound"
                self.call_requests[request_uuid] = None
                del self.call_requests[request_uuid]
            except (KeyError, AttributeError):
                called_num = ''
                caller_num = ''
                direction = "outbound"

            self.log.debug("Call Cleaned up for RequestUUID %s" % request_uuid)

            if not hangup_url:
                self.log.debug("No HangupUrl for Outgoing Call %s, RequestUUID %s" % (call_uuid, request_uuid))
                return

            forwarded_from = get_substring(':', '@', event['variable_sip_h_Diversion'])
            aleg_uuid = event['Caller-Unique-ID']
            aleg_request_uuid = event['variable_plivo_request_uuid']
            sched_hangup_id = event['variable_plivo_sched_hangup_id']
            params['RequestUUID'] = request_uuid
            if forwarded_from:
                params['ForwardedFrom'] = forwarded_from.lstrip('+')
            if aleg_uuid:
                params['ALegUUID'] = aleg_uuid
            if aleg_request_uuid:
                params['ALegRequestUUID'] = aleg_request_uuid
            if sched_hangup_id:
                params['ScheduledHangupId'] = sched_hangup_id
        # if hangup url, handle http request
        if hangup_url:
            sip_uri = event['variable_plivo_sip_transfer_uri'] or ''
            if sip_uri:
                params['SIPTransfer'] = 'true'
                params['SIPTransferURI'] = sip_uri
            params['CallUUID'] = call_uuid or ''
            params['HangupCause'] = reason
            params['To'] = called_num or ''
            params['From'] = caller_num or ''
            params['Direction'] = direction or ''
            params['CallStatus'] = 'completed'
            spawn_raw(self.send_to_url, hangup_url, params)

    def send_to_url(self, url=None, params={}, method=None):
        if method is None:
            method = self.get_server().default_http_method

        if not url:
            self.log.warn("Cannot send %s, no url !" % method)
            return None
        try:
            http_obj = HTTPRequest(self.get_server().key, self.get_server().secret, self.get_server().proxy_url)
            data = http_obj.fetch_response(url, params, method, log=self.log)
            return data
        except Exception, e:
            self.log.error("Sending to %s %s with %s -- Error: %s"
                                        % (method, url, params, e))
        return None

    def spawn_originate(self, request_uuid):
        try:
            call_req = self.call_requests[request_uuid]
        except KeyError:
            self.log.warn("Call Request not found for RequestUUID %s" % request_uuid)
            return False
        spawn_raw(self._spawn_originate, call_req)
        self.log.warn("Call Request Spawned for RequestUUID %s" % request_uuid)
        return True

    def _spawn_originate(self, call_req):
        try:
            request_uuid = call_req.request_uuid
            gw_count = len(call_req.gateways)
            for x in range(gw_count):
                try:
                    gw = call_req.gateways.pop(0)
                except IndexError:
                    self.log.warn("No more Gateways to call for RequestUUID %s" % request_uuid)
                    try:
                        self.call_requests[request_uuid] = None
                        del self.call_requests[request_uuid]
                    except KeyError:
                        pass
                    return

                _options = []
                # Set plivo app flag
                _options.append("plivo_app=true")
                # Add codecs option
                if gw.codecs:
                    _options.append("absolute_codec_string=%s" % gw.codecs)
                # Add timeout option
                if gw.timeout:
                    _options.append("originate_timeout=%s" % gw.timeout)
                # Set early media
                _options.append("ignore_early_media=true")
                # Build originate dial string
                options = ','.join(_options)
                outbound_str = "&socket('%s async full')" \
                                % self.get_server().fs_out_address

                dial_str = "originate {%s,%s}%s%s %s" \
                    % (call_req.extra_dial_string, options, gw.gw, gw.to, outbound_str)
                self.log.debug("Call try for RequestUUID %s with Gateway %s" \
                            % (request_uuid, gw.gw))
                # Execute originate on background
                self.log.debug("spawn_originate: %s" % str(dial_str))
                bg_api_response = self.bgapi(dial_str)
                job_uuid = bg_api_response.get_job_uuid()
                self.bk_jobs[job_uuid] = request_uuid
                if not job_uuid:
                    self.log.error("Call Failed for RequestUUID %s -- JobUUID not received" \
                                                                    % request_uuid)
                    continue
                # wait for current call attempt to finish
                self.log.debug("Waiting Call attempt for RequestUUID %s ..." % request_uuid)
                success = call_req.wait_call_attempt()
                if success is True:
                    self.log.info("Call Attempt OK for RequestUUID %s" % request_uuid)
                    return
                self.log.info("Call Attempt Failed for RequestUUID %s, retrying next gateway ..." % request_uuid)
                continue
        except Exception, e:
            self.log.error(str(e))

    def group_originate(self, request_uuid, group_list, group_options=[], reject_causes=''):
        self.log.debug("GroupCall => %s %s" % (str(request_uuid), str(group_options)))

        outbound_str = "&socket('%s async full')" % self.get_server().fs_out_address
        # Set plivo app flag and request uuid
        group_options.append('plivo_request_uuid=%s' % request_uuid)
        group_options.append("plivo_app=true")
        group_options.append("plivo_group_call=true")

        dial_calls = []

        for call_req in group_list:
            extras = []
            dial_gws = []
            for gw in call.gateways:
                _options = []
                # Add codecs option
                if gw.codecs:
                    _options.append("absolute_codec_string=%s" % gw.codecs)
                # Add timeout option
                if gw.timeout:
                    _options.append("originate_timeout=%s" % gw.timeout)
                # Set early media
                _options.append("ignore_early_media=true")
                # Build gateway dial string
                options = ','.join(_options)
                gw_str = '[%s]%s%s' % (options, gw.gw, gw.to)
                dial_gws.append(gw_str)
            # Build call dial string
            dial_call_str = ",".join(dial_gws)

            if call_req.extra_dial_string:
                extras.append(call_req.extra_dial_string)
            if reject_causes:
                extras.append("fail_on_single_reject='%s'" % reject_causes)
            # set extra options
            extra_opts = ','.join(extras)
            # set dial string and append to global dial string
            dial_call_str = "{%s}%s" % (extra_opts, dial_call_str)
            dial_calls.append(dial_call_str)

        # Build global dial string
        dial_str = ":_:".join(dial_calls)
        global_options = ",".join(group_options)
        if global_options:
            if len(dial_calls) > 1:
                dial_str = "<%s>%s" % (global_options, dial_str)
            else:
                if dial_str[0] == '{':
                    dial_str = "{%s,%s" % (global_options, dial_str[1:])
                else:
                    dial_str = "{%s}%s" % (global_options, dial_str)

        # Execute originate on background
        dial_str = "originate %s %s" \
                % (dial_str, outbound_str)
        self.log.debug("GroupCall : %s" % str(dial_str))

        bg_api_response = self.bgapi(dial_str)
        job_uuid = bg_api_response.get_job_uuid()
        self.bk_jobs[job_uuid] = request_uuid
        self.log.debug(str(bg_api_response))
        if not job_uuid:
            self.log.error("GroupCall Failed for RequestUUID %s -- JobUUID not received" \
                                                            % request_uuid)
            return False
        return True

    def bulk_originate(self, request_uuid_list):
        if request_uuid_list:
            self.log.info("BulkCall for RequestUUIDs %s" % str(request_uuid_list))
            job_pool = pool.Pool(len(request_uuid_list))
            [ job_pool.spawn(self.spawn_originate, request_uuid)
                                        for request_uuid in request_uuid_list ]
            return True
        self.log.error("BulkCall Failed -- No RequestUUID !")
        return False

    def transfer_call(self, new_xml_url, call_uuid):
        # Set transfer progress flag to prevent hangup
        # when the current outbound_socket flow will end
        self.set_var("plivo_transfer_progress", "true", uuid=call_uuid)
        # set original destination number
        called_num = self.get_var("plivo_destination_number", uuid=call_uuid)
        if not called_num:
            called_num = self.get_var("destination_number", uuid=call_uuid)
            self.set_var("plivo_destination_number", called_num, uuid=call_uuid)
        # Set transfer url
        self.set_var("plivo_transfer_url", new_xml_url, uuid=call_uuid)
        # Link inline dptools (will be run when ready to start transfer)
        # to the call_uuid job
        outbound_str = "socket:%s async full" \
                        % (self.get_server().fs_out_address)
        self.xfer_jobs[call_uuid] = outbound_str
        # Transfer into sleep state a little waiting for real transfer
        res = self.api("uuid_transfer %s 'sleep:5000' inline" % call_uuid)
        if res.is_success():
            self.log.info("TransferCall Spawned for %s" % call_uuid)
            return True
        # On failure, remove the job and log error
        try:
            del self.xfer_jobs[call_uuid]
        except KeyError:
            pass
        self.log.error("TransferCall Spawning Failed for %s : %s" \
                        % (call_uuid, str(res.get_response())))
        return False

    def hangup_call(self, call_uuid="", request_uuid=""):
        if not call_uuid and not request_uuid:
            self.log.error("Call Hangup Failed -- Missing CallUUID or RequestUUID")
            return False
        if call_uuid:
            callid = "CallUUID %s" % call_uuid
            cmd = "uuid_kill %s NORMAL_CLEARING" % call_uuid
        else:  # Use request uuid
            callid = "RequestUUID %s" % request_uuid
            try:
                call_req = self.call_requests[request_uuid]
            except (KeyError, AttributeError):
                self.log.error("Call Hangup Failed -- %s not found" \
                            % (callid))
                return False
            cmd = "hupall NORMAL_CLEARING plivo_request_uuid %s" % request_uuid
        res = self.api(cmd)
        if not res.is_success():
            self.log.error("Call Hangup Failed for %s -- %s" \
                % (callid, res.get_response()))
            return False
        self.log.info("Executed Call Hangup for %s" % callid)
        return True

    def hangup_all_calls(self):
        bg_api_response = self.bgapi("hupall NORMAL_CLEARING")
        job_uuid = bg_api_response.get_job_uuid()
        if not job_uuid:
            self.log.error("Hangup All Calls Failed -- JobUUID not received")
            return False
        self.log.info("Executed Hangup for all calls")
        return True

    def conference_api(self, room=None, command=None, async=True):
        if not command:
            self.log.error("Conference Api Failed -- 'command' is empty")
            return False
        if room:
            cmd = "conference '%s' %s" % (room, command)
        else:
            cmd = "conference %s" % command
        # async mode
        if async:
            bg_api_response = self.bgapi(cmd)
            job_uuid = bg_api_response.get_job_uuid()
            if not job_uuid:
                self.log.error("Conference Api (async) Failed '%s' -- JobUUID not received" \
                                        % (cmd))
                return False
            self.conf_sync_jobs[job_uuid] = True
            self.log.info("Conference Api (async) '%s' with JobUUID %s" \
                                    % (cmd, job_uuid))
            return True
        # sync mode
        else:
            res = gevent.event.AsyncResult()
            bg_api_response = self.bgapi(cmd)
            job_uuid = bg_api_response.get_job_uuid()
            if not job_uuid:
                self.log.error("Conference Api (async) Failed '%s' -- JobUUID not received" \
                                        % (cmd))
                return False
            self.log.info("Conference Api (sync) '%s' with JobUUID %s" \
                                    % (cmd, job_uuid))
            self.conf_sync_jobs[job_uuid] = res
            try:
                result = res.wait(timeout=120)
                return result
            except gevent.timeout.Timeout:
                self.log.error("Conference Api (sync) '%s' with JobUUID %s -- timeout getting response" \
                                    % (cmd, job_uuid))
                return False
        return False

    def play_on_call(self, call_uuid="", sounds_list=[], legs="aleg", length=3600, schedule=0, mix=True, loop=False):
        cmds = []
        error_count = 0
        bleg = None

        # set flags
        if loop:
            aflags = "l"
            bflags = "l"
        else:
            aflags = ""
            bflags = ""
        if mix:
            aflags += "m"
            bflags += "mr"
        else:
            bflags += "r"

        if schedule <= 0:
            name = "Call Play"
        else:
            name = "Call SchedulePlay"
        if not call_uuid:
            self.log.error("%s Failed -- Missing CallUUID" % name)
            return False
        if not sounds_list:
            self.log.error("%s Failed -- Missing Sounds" % name)
            return False
        if not legs in ('aleg', 'bleg', 'both'):
            self.log.error("%s Failed -- Invalid legs arg '%s'" % (name, str(legs)))
            return False

        # get sound files
        sounds_to_play = []
        for sound in sounds_list:
            if is_valid_sound_proto(sound):
                sounds_to_play.append(sound)
            elif not is_valid_url(sound):
                if file_exists(sound):
                    sounds_to_play.append(sound)
                else:
                    self.log.warn("%s -- File %s not found" % (name, sound))
            else:
                url = normalize_url_space(sound)
                sound_file_path = get_resource(self, url)
                if sound_file_path:
                    sounds_to_play.append(sound_file_path)
                else:
                    self.log.warn("%s -- Url %s not found" % (name, url))
        if not sounds_to_play:
            self.log.error("%s Failed -- Sound files not found" % name)
            return False

        # build command
        play_str = '!'.join(sounds_to_play)
        play_aleg = 'file_string://%s' % play_str
        play_bleg = 'file_string://silence_stream://1!%s' % play_str

        # aleg case
        if legs == 'aleg':
            # add displace command
            for displace in self._get_displace_media_list(call_uuid):
                cmd = "uuid_displace %s stop %s" % (call_uuid, displace)
                cmds.append(cmd)
            cmd = "uuid_displace %s start %s %d %s" % (call_uuid, play_aleg, length, aflags)
            cmds.append(cmd)
        # bleg case
        elif legs  == 'bleg':
            # get bleg
            bleg = self.get_var("bridge_uuid", uuid=call_uuid)
            # add displace command
            if bleg:
                for displace in self._get_displace_media_list(call_uuid):
                    cmd = "uuid_displace %s stop %s" % (call_uuid, displace)
                    cmds.append(cmd)
                cmd = "uuid_displace %s start %s %d %s" % (call_uuid, play_bleg, length, bflags)
                cmds.append(cmd)
            else:
                self.log.error("%s Failed -- No BLeg found" % name)
                return False
        # both legs case
        elif legs == 'both':
            # get bleg
            bleg = self.get_var("bridge_uuid", uuid=call_uuid)
            # add displace commands
            for displace in self._get_displace_media_list(call_uuid):
                cmd = "uuid_displace %s stop %s" % (call_uuid, displace)
                cmds.append(cmd)
            cmd = "uuid_displace %s start %s %d %s" % (call_uuid, play_aleg, length, aflags)
            cmds.append(cmd)
            # get the bleg
            if bleg:
                cmd = "uuid_displace %s start %s %d %s" % (call_uuid, play_bleg, length, bflags)
                cmds.append(cmd)
            else:
                self.log.warn("%s -- No BLeg found" % name)
        else:
            self.log.error("%s Failed -- Invalid Legs '%s'" % (name, legs))
            return False

        # case no schedule
        if schedule <= 0:
            for cmd in cmds:
                res = self.api(cmd)
                if not res.is_success():
                    self.log.error("%s Failed '%s' -- %s" % (name, cmd, res.get_response()))
                    error_count += 1
            if error_count > 0:
                return False
            return True

        # case schedule
        sched_id = str(uuid.uuid1())
        for cmd in cmds:
            sched_cmd = "sched_api +%d %s %s" % (schedule, sched_id, cmd)
            res = self.api(sched_cmd)
            if res.is_success():
                self.log.info("%s '%s' with SchedPlayId %s" % (name, sched_cmd, sched_id))
            else:
                self.log.error("%s Failed '%s' -- %s" % (name, sched_cmd, res.get_response()))
                error_count += 1
        if error_count > 0:
            return False
        return sched_id

    def play_stop_on_call(self, call_uuid=""):
        cmds = []
        error_count = 0

        # get bleg
        bleg = self.get_var("bridge_uuid", uuid=call_uuid)

        for displace in self._get_displace_media_list(call_uuid):
            cmd = "uuid_displace %s stop %s" % (call_uuid, displace)
            cmds.append(cmd)

        if not cmds:
            self.log.warn("PlayStop -- Nothing to stop")
            return True

        for cmd in cmds:
            bg_api_response = self.bgapi(cmd)
            job_uuid = bg_api_response.get_job_uuid()
            if not job_uuid:
                self.log.error("PlayStop Failed '%s' -- JobUUID not received" % cmd)
                error_count += 1
        if error_count > 0:
            return False
        return True

    def _get_displace_media_list(self, uuid=''):
        if not uuid:
            return []
        result = []
        cmd = "uuid_buglist %s" % uuid
        res = self.api(cmd)
        if not res.get_response():
            self.log.warn("cannot get displace_media_list: no list" % str(e))
            return result
        try:
            doc = etree.fromstring(res.get_response())
            if doc.tag != 'media-bugs':
                return result
            for node in doc:
                if node.tag == 'media-bug':
                    try:
                        func = node.find('function').text
                        if func == 'displace':
                            target = node.find('target').text
                            result.append(target)
                    except:
                        continue
            return result
        except Exception, e:
            self.log.warn("cannot get displace_media_list: %s" % str(e))
            return result

    def sound_touch(self, call_uuid="", direction='out', s=None, o=None,
                    p=None, r=None, t=None):
        stop_cmd = "soundtouch %s stop" % call_uuid
        cmd = "soundtouch %s start " % call_uuid
        if direction == "in":
            cmd += "send_leg "
        if s:
            cmd += "%ss " % str(s)
        if o:
            cmd += "%so " % str(o)
        if p:
            cmd += "%sp " % str(p)
        if r:
            cmd += "%sr " % str(r)
        if t:
            cmd += "%st " % str(t)
        self.api(stop_cmd)
        res = self.api(cmd)
        if res.is_success():
            return True
        self.log.error("SoundTouch Failed '%s' -- %s" % (cmd, res.get_response()))
        return False





########NEW FILE########
__FILENAME__ = outboundserver
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.


from gevent import monkey
monkey.patch_all()

import grp
import os
import pwd
import signal
import sys
import optparse

import gevent

from plivo.core.freeswitch import outboundsocket
from plivo.rest.freeswitch.outboundsocket import PlivoOutboundEventSocket
from plivo.rest.freeswitch import helpers
import plivo.utils.daemonize
from plivo.utils.logger import StdoutLogger, FileLogger, SysLogger, DummyLogger, HTTPLogger

"""
PlivoOutboundServer is our event_socket server listening for connection
with Freeswitch.

This server by default is listens on 127.0.0.1:8084
"""


class PlivoOutboundServer(outboundsocket.OutboundServer):
    def __init__(self, configfile, daemon=False,
                    pidfile='/tmp/plivo_outbound.pid'):
        self._request_id = 0
        self._daemon = daemon
        self._run = False
        self._pidfile = pidfile
        self.configfile = configfile
        # load config
        self._config = None
        self.cache = {}
        self.load_config()

        # This is where we define the connection with the
        # Plivo XML element Processor
        outboundsocket.OutboundServer.__init__(self, (self.fs_host, self.fs_port),
                                PlivoOutboundEventSocket, filter=None)

    def load_config(self, reload=False):
        # backup config
        backup_config = self._config
        # create config
        config = helpers.PlivoConfig(self.configfile)
        try:
            # read config
            config.read()

            # set trace flag
            self._trace = config.get('outbound_server', 'TRACE', default='false') == 'true'

            if not reload:
                # create first logger if starting
                self.create_logger(config=config)
                self.log.info("Starting ...")
                self.log.warn("Logger %s" % str(self.log))

            # create outbound server
            if not reload:
                self.fs_outbound_address = config.get('outbound_server', 'FS_OUTBOUND_ADDRESS')
                self.fs_host, fs_port = self.fs_outbound_address.split(':', 1)
                self.fs_port = int(fs_port)

            self.default_answer_url = config.get('common', 'DEFAULT_ANSWER_URL')

            self.default_hangup_url = config.get('common', 'DEFAULT_HANGUP_URL', default='')

            self.default_http_method = config.get('common', 'DEFAULT_HTTP_METHOD', default='')
            if not self.default_http_method in ('GET', 'POST'):
                self.default_http_method = 'POST'

            self.key = config.get('common', 'AUTH_ID', default='')
            self.secret = config.get('common', 'AUTH_TOKEN', default='')

            self.extra_fs_vars = config.get('common', 'EXTRA_FS_VARS', default='')
            self.proxy_url = config.get('common', 'PROXY_URL', default=None)

            # load cache params
            self.cache['url'] = config.get('common', 'CACHE_URL', default='')
            self.cache['script'] = config.get('common', 'CACHE_SCRIPT', default='')
            if not self.cache['url'] or not self.cache['script']:
                self.cache = {}

            # create new logger if reloading
            if reload:
                self.create_logger(config=config)
                self.log.warn("New logger %s" % str(self.log))

            # set new config
            self._config = config
            self.log.info("Config : %s" % str(self._config.dumps()))

        except Exception, e:
            if backup_config:
                self._config = backup_config
                self.log.warn("Error reloading config: %s" % str(e))
                self.log.warn("Rollback to the last config")
                self.log.info("Config : %s" % str(self._config.dumps()))
            else:
                sys.stderr.write("Error loading config: %s" % str(e))
                sys.stderr.flush()
                raise e

    def reload(self):
        self.log.warn("Reload ...")
        self.load_config(reload=True)
        self.log.warn("Reload done")

    def _get_request_id(self):
        try:
            self._request_id += 1
        except OverflowError:
            self._request_id = 1
        return self._request_id

    def handle_request(self, socket, address):
        request_id = self._get_request_id()
        self.log.info("(%d) New request from %s" % (request_id, str(address)))
        req = self._requestClass(socket, address, self.log, self.cache,
                                 default_answer_url=self.default_answer_url,
                                 default_hangup_url=self.default_hangup_url,
                                 default_http_method=self.default_http_method,
                                 extra_fs_vars=self.extra_fs_vars,
                                 auth_id=self.key,
                                 auth_token=self.secret,
                                 request_id=request_id,
                                 trace=self._trace,
                                 proxy_url=self.proxy_url
                                )
        self.log.info("(%d) End request from %s" % (request_id, str(address)))
        try:
            req = None
            del req
        except:
            pass

    def create_logger(self, config):
        """This will create a logger using helpers.PlivoConfig instance

        Based on the settings in the configuration file,
        LOG_TYPE will determine if we will log in file, syslog, stdout, http or dummy (no log)
        """

        if self._daemon is False:
            logtype = config.get('outbound_server', 'LOG_TYPE')
            if logtype == 'dummy':
                self.log = DummyLogger()
            else:
                self.log = StdoutLogger()
            self.log.set_debug()
        else:
            logtype = config.get('outbound_server', 'LOG_TYPE')
            if logtype == 'file':
                logfile = config.get('outbound_server', 'LOG_FILE')
                self.log = FileLogger(logfile)
            elif logtype == 'syslog':
                syslogaddress = config.get('outbound_server', 'SYSLOG_ADDRESS')
                syslogfacility = config.get('outbound_server', 'SYSLOG_FACILITY')
                self.log = SysLogger(syslogaddress, syslogfacility)
            elif logtype == 'dummy':
                self.log = DummyLogger()
            elif logtype == 'http':
                url = config.get('outbound_server', 'HTTP_LOG_URL')
                method = config.get('outbound_server', 'HTTP_LOG_METHOD')
                fallback_file = config.get('outbound_server', 'HTTP_LOG_FILE_FAILURE')
                self.log = HTTPLogger(url=url, method=method, fallback_file=fallback_file)
            else:
                self.log = StdoutLogger()
            log_level = config.get('outbound_server', 'LOG_LEVEL', default='INFO')
            if log_level == 'DEBUG' or self._trace is True:
                self.log.set_debug()
            elif log_level == 'INFO':
                self.log.set_info()
            elif log_level == 'ERROR':
                self.log.set_error()
            elif log_level in ('WARN', 'WARNING'):
                self.log.set_warn()

    def do_daemon(self):
        """This will daemonize the current application

        Two settings from our configuration files are also used to run the
        daemon under a determine user & group.

        USER : determine the user running the daemon
        GROUP : determine the group running the daemon
        """
        # get user/group from config
        user = self._config.get('outbound_server', 'USER', default='')
        group = self._config.get('outbound_server', 'GROUP', default='')
        if not user or not group:
            uid = os.getuid()
            user = pwd.getpwuid(uid)[0]
            gid = os.getgid()
            group = grp.getgrgid(gid)[0]
        # daemonize now
        plivo.utils.daemonize.daemon(user, group, path='/',
                                     pidfile=self._pidfile,
                                     other_groups=())

    def sig_term(self, *args):
        self.stop()
        self.log.warn("Shutdown ...")
        sys.exit(0)

    def sig_hup(self, *args):
        self.reload()

    def start(self):
        self.log.info("Starting OutboundServer ...")
        # catch SIG_TERM
        gevent.signal(signal.SIGTERM, self.sig_term)
        gevent.signal(signal.SIGHUP, self.sig_hup)
        # run
        self._run = True
        if self._daemon:
            self.do_daemon()
        super(PlivoOutboundServer, self).start()
        self.log.info("OutboundServer started at '%s'" \
                                    % str(self.fs_outbound_address))
        self.serve_forever()
        self.log.info("OutboundServer Exited")


def main():
    parser = optparse.OptionParser()
    parser.add_option("-c", "--configfile", action="store", type="string",
                      dest="configfile",
                      help="use plivo config file (argument is mandatory)",
                      metavar="CONFIGFILE")
    parser.add_option("-p", "--pidfile", action="store", type="string",
                      dest="pidfile",
                      help="write pid to PIDFILE (argument is mandatory)",
                      metavar="PIDFILE")
    (options, args) = parser.parse_args()

    configfile = options.configfile
    pidfile = options.pidfile

    if not configfile:
        configfile = './etc/plivo/default.conf'
        if not os.path.isfile(configfile):
            raise SystemExit("Error : Default config file mising at '%s'. Please specify -c <configfilepath>" %configfile)
    if not pidfile:
        pidfile='/tmp/plivo_outbound.pid'

    outboundserver = PlivoOutboundServer(configfile=configfile,
                                    pidfile=pidfile, daemon=False)
    outboundserver.start()


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = outboundsocket
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from gevent import monkey
monkey.patch_all()

import os.path
import traceback
try:
    import xml.etree.cElementTree as etree
except ImportError:
    from xml.etree.elementtree import ElementTree as etree

import gevent
import gevent.queue
from gevent import spawn_raw
from gevent.event import AsyncResult

from plivo.utils.encode import safe_str
from plivo.core.freeswitch.eventtypes import Event
from plivo.rest.freeswitch.helpers import HTTPRequest, get_substring
from plivo.core.freeswitch.outboundsocket import OutboundEventSocket
from plivo.rest.freeswitch import elements
from plivo.rest.freeswitch.exceptions import RESTFormatException, \
                                    RESTSyntaxException, \
                                    UnrecognizedElementException, \
                                    RESTRedirectException, \
                                    RESTSIPTransferException, \
                                    RESTHangup


MAX_REDIRECT = 9999


class RequestLogger(object):
    """
    Class RequestLogger

    This Class allows a quick way to log a message with request ID
    """
    def __init__(self, logger, request_id=0):
        self.logger = logger
        self.request_id = request_id

    def info(self, msg):
        """Log info level"""
        self.logger.info('(%s) %s' % (self.request_id, safe_str(msg)))

    def warn(self, msg):
        """Log warn level"""
        self.logger.warn('(%s) %s' % (self.request_id, safe_str(msg)))

    def error(self, msg):
        """Log error level"""
        self.logger.error('(%s) %s' % (self.request_id, safe_str(msg)))

    def debug(self, msg):
        """Log debug level"""
        self.logger.debug('(%s) %s' % (self.request_id, safe_str(msg)))



class PlivoOutboundEventSocket(OutboundEventSocket):
    """Class PlivoOutboundEventSocket

    An instance of this class is created every time an incoming call is received.
    The instance requests for a XML element set to execute the call and acts as a
    bridge between Event_Socket and the web application
    """
    WAIT_FOR_ACTIONS = ('playback',
                        'record',
                        'play_and_get_digits',
                        'bridge',
                        'say',
                        'sleep',
                        'speak',
                        'conference',
                        'park',
                       )
    NO_ANSWER_ELEMENTS = ('Wait',
                          'PreAnswer',
                          'Hangup',
                          'Dial',
                          'Notify',
                         )

    def __init__(self, socket, address,
                 log, cache,
                 default_answer_url=None,
                 default_hangup_url=None,
                 default_http_method='POST',
                 extra_fs_vars=None,
                 auth_id='',
                 auth_token='',
                 request_id=0,
                 trace=False,
                 proxy_url=None):
        # the request id
        self._request_id = request_id
        # set logger
        self._log = log
        self.log = RequestLogger(logger=self._log, request_id=self._request_id)
        # set auth id/token
        self.key = auth_id
        self.secret = auth_token
        # set all settings empty
        self.xml_response = ''
        self.parsed_element = []
        self.lexed_xml_response = []
        self.target_url = ''
        self.hangup_url = ''
        self.session_params = {}
        self._hangup_cause = ''
        # flag to track current element
        self.current_element = None
        # create queue for waiting actions
        self._action_queue = gevent.queue.Queue(10)
        # set default answer url
        self.default_answer_url = default_answer_url
        # set default hangup_url
        self.default_hangup_url = default_hangup_url
        # set proxy url
        self.proxy_url =  proxy_url
        # set default http method POST or GET
        self.default_http_method = default_http_method
        # identify the extra FS variables to be passed along
        self.extra_fs_vars = extra_fs_vars
        # set answered flag
        self.answered = False
        self.cache = cache
        # inherits from outboundsocket
        OutboundEventSocket.__init__(self, socket, address, filter=None,
                                     eventjson=True, pool_size=200, trace=trace)

    def _protocol_send(self, command, args=''):
        """Access parent method _protocol_send
        """
        self.log.debug("Execute: %s args='%s'" % (command, safe_str(args)))
        response = super(PlivoOutboundEventSocket, self)._protocol_send(
                                                                command, args)
        self.log.debug("Response: %s" % str(response))
        if self.has_hangup():
            raise RESTHangup()
        return response

    def _protocol_sendmsg(self, name, args=None, uuid='', lock=False, loops=1):
        """Access parent method _protocol_sendmsg
        """
        self.log.debug("Execute: %s args=%s, uuid='%s', lock=%s, loops=%d" \
                      % (name, safe_str(args), uuid, str(lock), loops))
        response = super(PlivoOutboundEventSocket, self)._protocol_sendmsg(
                                                name, args, uuid, lock, loops)
        self.log.debug("Response: %s" % str(response))
        if self.has_hangup():
            raise RESTHangup()
        return response

    def wait_for_action(self, timeout=3600, raise_on_hangup=False):
        """
        Wait until an action is over
        and return action event.
        """
        self.log.debug("wait for action start")
        try:
            event = self._action_queue.get(timeout=timeout)
            self.log.debug("wait for action end %s" % str(event))
            if raise_on_hangup is True and self.has_hangup():
                self.log.warn("wait for action call hung up !")
                raise RESTHangup()
            return event
        except gevent.queue.Empty:
            if raise_on_hangup is True and self.has_hangup():
                self.log.warn("wait for action call hung up !")
                raise RESTHangup()
            self.log.warn("wait for action end timed out!")
            return Event()


    # In order to "block" the execution of our service until the
    # command is finished, we use a synchronized queue from gevent
    # and wait for such event to come. The on_channel_execute_complete
    # method will put that event in the queue, then we may continue working.
    # However, other events will still come, like for instance, DTMF.
    def on_channel_execute_complete(self, event):
        if event['Application'] in self.WAIT_FOR_ACTIONS:
            # If transfer has begun, put empty event to break current action
            if event['variable_plivo_transfer_progress'] == 'true':
                self._action_queue.put(Event())
            else:
                self._action_queue.put(event)

    def on_channel_hangup_complete(self, event):
        """
        Capture Channel Hangup Complete
        """
        self._hangup_cause = event['Hangup-Cause']
        self.log.info('Event: channel %s has hung up (%s)' %
                      (self.get_channel_unique_id(), self._hangup_cause))
        self.session_params['HangupCause'] = self._hangup_cause
        self.session_params['CallStatus'] = 'completed'
        # Prevent command to be stuck while waiting response
        self._action_queue.put_nowait(Event())

    def on_channel_bridge(self, event):
        # send bridge event to Dial
        if self.current_element == 'Dial':
            self._action_queue.put(event)

    def on_channel_unbridge(self, event):
        # special case to get bleg uuid for Dial
        if self.current_element == 'Dial':
            self._action_queue.put(event)

    def on_detected_speech(self, event):
        # detect speech for GetSpeech
        if self.current_element == 'GetSpeech' \
            and event['Speech-Type'] == 'detected-speech':
            self._action_queue.put(event)

    def on_custom(self, event):
        # case conference event
        if self.current_element == 'Conference':
            # special case to get Member-ID for Conference
            if event['Event-Subclass'] == 'conference::maintenance' \
                and event['Action'] == 'add-member' \
                and event['Unique-ID'] == self.get_channel_unique_id():
                self.log.debug("Entered Conference")
                self._action_queue.put(event)
            # special case for hangupOnStar in Conference
            elif event['Event-Subclass'] == 'conference::maintenance' \
                and event['Action'] == 'kick' \
                and event['Unique-ID'] == self.get_channel_unique_id():
                room = event['Conference-Name']
                member_id = event['Member-ID']
                if room and member_id:
                    self.bgapi("conference %s kick %s" % (room, member_id))
                    self.log.warn("Conference Room %s, member %s pressed '*', kicked now !" \
                            % (room, member_id))
            # special case to send callback for Conference
            elif event['Event-Subclass'] == 'conference::maintenance' \
                and event['Action'] == 'digits-match' \
                and event['Unique-ID'] == self.get_channel_unique_id():
                self.log.debug("Digits match on Conference")
                digits_action = event['Callback-Url']
                digits_method = event['Callback-Method']
                if digits_action and digits_method:
                    params = {}
                    params['ConferenceMemberID'] = event['Member-ID'] or ''
                    params['ConferenceUUID'] = event['Conference-Unique-ID'] or ''
                    params['ConferenceName'] = event['Conference-Name'] or ''
                    params['ConferenceDigitsMatch'] = event['Digits-Match'] or ''
                    params['ConferenceAction'] = 'digits'
                    spawn_raw(self.send_to_url, digits_action, params, digits_method)
            # special case to send callback when Member take the floor in Conference
            # but only if member can speak (not muted)
            elif event['Event-Subclass'] == 'conference::maintenance' \
                and event['Action'] == 'floor-change' \
                and event['Unique-ID'] == self.get_channel_unique_id() \
                and event['Speak'] == 'true':
                self._action_queue.put(event)

        # case dial event
        elif self.current_element == 'Dial':
            if event['Event-Subclass'] == 'plivo::dial' \
                and event['Action'] == 'digits-match' \
                and event['Unique-ID'] == self.get_channel_unique_id():
                self.log.debug("Digits match on Dial")
                digits_action = event['Callback-Url']
                digits_method = event['Callback-Method']
                if digits_action and digits_method:
                    params = {}
                    params['DialDigitsMatch'] = event['Digits-Match'] or ''
                    params['DialAction'] = 'digits'
                    params['DialALegUUID'] = event['Unique-ID']
                    params['DialBLegUUID'] = event['variable_bridge_uuid']
                    spawn_raw(self.send_to_url, digits_action, params, digits_method)

    def has_hangup(self):
        if self._hangup_cause:
            return True
        return False

    def ready(self):
        if self.has_hangup():
            return False
        return True

    def has_answered(self):
        return self.answered

    def get_hangup_cause(self):
        return self._hangup_cause

    def get_extra_fs_vars(self, event):
        params = {}
        if not event or not self.extra_fs_vars:
            return params
        for var in self.extra_fs_vars.split(','):
            var = var.strip()
            if var:
                val = event.get_header(var)
                if val is None:
                    val = ''
                params[var] = val
        return params

    def disconnect(self):
        # Prevent command to be stuck while waiting response
        try:
            self._action_queue.put_nowait(Event())
        except gevent.queue.Full:
            pass
        self.log.debug('Releasing Connection ...')
        super(PlivoOutboundEventSocket, self).disconnect()
        self.log.debug('Releasing Connection Done')

    def run(self):
        try:
            self._run()
        except RESTHangup:
            self.log.warn('Hangup')
        except Exception, e:
            [ self.log.error(line) for line in \
                        traceback.format_exc().splitlines() ]
            raise e


    def _run(self):
        self.connect()
        self.resume()
        # Linger to get all remaining events before closing
        self.linger()
        self.myevents()
        self.divert_events('on')
        if self._is_eventjson:
            self.eventjson('CUSTOM conference::maintenance plivo::dial')
        else:
            self.eventplain('CUSTOM conference::maintenance plivo::dial')
        # Set plivo app flag
        self.set('plivo_app=true')
        # Don't hangup after bridge
        self.set('hangup_after_bridge=false')
        channel = self.get_channel()
        self.call_uuid = self.get_channel_unique_id()
        # Set CallerName to Session Params
        self.session_params['CallerName'] = channel.get_header('Caller-Caller-ID-Name') or ''
        # Set CallUUID to Session Params
        self.session_params['CallUUID'] = self.call_uuid
        # Set Direction to Session Params
        self.session_params['Direction'] = channel.get_header('Call-Direction')
        aleg_uuid = ''
        aleg_request_uuid = ''
        forwarded_from = get_substring(':', '@',
                            channel.get_header('variable_sip_h_Diversion'))

        # Case Outbound
        if self.session_params['Direction'] == 'outbound':
            # Set To / From
            called_no = channel.get_header("variable_plivo_to")
            if not called_no or called_no == '_undef_':
                called_no = channel.get_header('Caller-Destination-Number')
            called_no = called_no or ''
            from_no = channel.get_header("variable_plivo_from")
            if not from_no or from_no == '_undef_':
                from_no = channel.get_header('Caller-Caller-ID-Number') or ''
            # Set To to Session Params
            self.session_params['To'] = called_no.lstrip('+')
            # Set From to Session Params
            self.session_params['From'] = from_no.lstrip('+')

            # Look for variables in channel headers
            aleg_uuid = channel.get_header('Caller-Unique-ID')
            aleg_request_uuid = channel.get_header('variable_plivo_request_uuid')
            # Look for target url in order below :
            #  get plivo_transfer_url from channel var
            #  get plivo_answer_url from channel var
            xfer_url = channel.get_header('variable_plivo_transfer_url')
            answer_url = channel.get_header('variable_plivo_answer_url')
            if xfer_url:
                self.target_url = xfer_url
                self.log.info("Using TransferUrl %s" % self.target_url)
            elif answer_url:
                self.target_url = answer_url
                self.log.info("Using AnswerUrl %s" % self.target_url)
            else:
                self.log.error('Aborting -- No Call Url found !')
                if not self.has_hangup():
                    self.hangup()
                    raise RESTHangup()
                return
            # Look for a sched_hangup_id
            sched_hangup_id = channel.get_header('variable_plivo_sched_hangup_id')
            # Don't post hangup in outbound direction
            # because it is handled by inboundsocket
            self.default_hangup_url = None
            self.hangup_url = None
            # Set CallStatus to Session Params
            self.session_params['CallStatus'] = 'in-progress'
            # Set answered flag to true in case outbound call
            self.answered = True
            accountsid = channel.get_header("variable_plivo_accountsid")
            if accountsid:
                self.session_params['AccountSID'] = accountsid
        # Case Inbound
        else:
            # Set To / From
            called_no = channel.get_header("variable_plivo_destination_number")
            if not called_no or called_no == '_undef_':
                called_no = channel.get_header('Caller-Destination-Number')
            called_no = called_no or ''
            from_no = channel.get_header('Caller-Caller-ID-Number') or ''
            # Set To to Session Params
            self.session_params['To'] = called_no.lstrip('+')
            # Set From to Session Params
            self.session_params['From'] = from_no.lstrip('+')
            
            # Look for target url in order below :
            #  get plivo_transfer_url from channel var
            #  get plivo_answer_url from channel var
            #  get default answer_url from config
            xfer_url = self.get_var('plivo_transfer_url')
            answer_url = self.get_var('plivo_answer_url')
            if xfer_url:
                self.target_url = xfer_url
                self.log.info("Using TransferUrl %s" % self.target_url)
            elif answer_url:
                self.target_url = answer_url
                self.log.info("Using AnswerUrl %s" % self.target_url)
            elif self.default_answer_url:
                self.target_url = self.default_answer_url
                self.log.info("Using DefaultAnswerUrl %s" % self.target_url)
            else:
                self.log.error('Aborting -- No Call Url found !')
                if not self.has_hangup():
                    self.hangup()
                    raise RESTHangup()
                return
            # Look for a sched_hangup_id
            sched_hangup_id = self.get_var('plivo_sched_hangup_id')
            # Set CallStatus to Session Params
            self.session_params['CallStatus'] = 'ringing'

        if not sched_hangup_id:
            sched_hangup_id = ''

        # Add more Session Params if present
        if aleg_uuid:
            self.session_params['ALegUUID'] = aleg_uuid
        if aleg_request_uuid:
            self.session_params['ALegRequestUUID'] = aleg_request_uuid
        if sched_hangup_id:
            self.session_params['ScheduledHangupId'] = sched_hangup_id
        if forwarded_from:
            self.session_params['ForwardedFrom'] = forwarded_from.lstrip('+')

        # Remove sched_hangup_id from channel vars
        if sched_hangup_id:
            self.unset('plivo_sched_hangup_id')

        # Run application
        self.log.info('Processing Call')
        try:
            self.process_call()
        except RESTHangup:
            self.log.warn('Channel has hung up, breaking Processing Call')
        except Exception, e:
            self.log.error('Processing Call Failure !')
            # If error occurs during xml parsing
            # log exception and break
            self.log.error(str(e))
            [ self.log.error(line) for line in \
                        traceback.format_exc().splitlines() ]
        self.log.info('Processing Call Ended')

    def process_call(self):
        """Method to proceed on the call
        This will fetch the XML, validate the response
        Parse the XML and Execute it
        """
        params = {}
        for x in range(MAX_REDIRECT):
            try:
                # update call status if needed
                if self.has_hangup():
                    self.session_params['CallStatus'] = 'completed'
                # case answer url, add extra vars to http request :
                if x == 0:
                    params = self.get_extra_fs_vars(event=self.get_channel())
                # fetch remote restxml
                self.fetch_xml(params=params)
                # check hangup
                if self.has_hangup():
                    raise RESTHangup()
                if not self.xml_response:
                    self.log.warn('No XML Response')
                    if not self.has_hangup():
                        self.hangup()
                    raise RESTHangup()
                # parse and execute restxml
                self.lex_xml()
                self.parse_xml()
                self.execute_xml()
                self.log.info('End of RESTXML')
                return
            except RESTRedirectException, redirect:
                # double check channel exists/hung up
                if self.has_hangup():
                    raise RESTHangup()
                res = self.api('uuid_exists %s' % self.get_channel_unique_id())
                if res.get_response() != 'true':
                    self.log.warn("Call doesn't exist !")
                    raise RESTHangup()
                # Set target URL to Redirect URL
                # Set method to Redirect method
                # Set additional params to Redirect params
                self.target_url = redirect.get_url()
                fetch_method = redirect.get_method()
                params = redirect.get_params()
                if not fetch_method:
                    fetch_method = 'POST'
                # Reset all the previous response and element
                self.xml_response = ""
                self.parsed_element = []
                self.lexed_xml_response = []
                self.log.info("Redirecting to %s %s to fetch RESTXML" \
                                        % (fetch_method, self.target_url))
                # If transfer is in progress, break redirect
                xfer_progress = self.get_var('plivo_transfer_progress') == 'true'
                if xfer_progress:
                    self.log.warn('Transfer in progress, breaking redirect to %s %s' \
                                  % (fetch_method, self.target_url))
                    return
                gevent.sleep(0.010)
                continue
            except RESTSIPTransferException, sip_redirect:
                self.session_params['SIPTransfer'] = 'true'
                self.session_params['SIPTransferURI'] = sip_redirect.get_sip_url() \
                            or ''
                self.log.info("End of RESTXML -- SIPTransfer done to %s" % sip_redirect.get_sip_url())
                return
        self.log.warn('Max Redirect Reached !')

    def fetch_xml(self, params={}, method=None):
        """
        This method will retrieve the xml from the answer_url
        The url result expected is an XML content which will be stored in
        xml_response
        """
        self.log.info("Fetching RESTXML from %s" % self.target_url)
        self.xml_response = self.send_to_url(self.target_url, params, method)
        self.log.info("Requested RESTXML to %s" % self.target_url)

    def send_to_url(self, url=None, params={}, method=None):
        """
        This method will do an http POST or GET request to the Url
        """
        if method is None:
            method = self.default_http_method

        if not url:
            self.log.warn("Cannot send %s, no url !" % method)
            return None
        params.update(self.session_params)
        try:
            http_obj = HTTPRequest(self.key, self.secret, proxy_url=self.proxy_url)
            data = http_obj.fetch_response(url, params, method, log=self.log)
            return data
        except Exception, e:
            self.log.error("Sending to %s %s with %s -- Error: %s" \
                                        % (method, url, params, e))
        return None

    def lex_xml(self):
        """
        Validate the XML document and make sure we recognize all Element
        """
        # Parse XML into a doctring
        xml_str = ' '.join(self.xml_response.split())
        try:
            #convert the string into an Element instance
            doc = etree.fromstring(xml_str)
        except Exception, e:
            raise RESTSyntaxException("Invalid RESTXML Response Syntax: %s" \
                        % str(e))

        # Make sure the document has a <Response> root
        if doc.tag != 'Response':
            raise RESTFormatException('No Response Tag Present')

        # Make sure we recognize all the Element in the xml
        for element in doc:
            invalid_element = []
            if not hasattr(elements, element.tag):
                invalid_element.append(element.tag)
            else:
                self.lexed_xml_response.append(element)
            if invalid_element:
                raise UnrecognizedElementException("Unrecognized Element: %s"
                                                        % invalid_element)

    def parse_xml(self):
        """
        This method will parse the XML
        and add the Elements into parsed_element
        """
        # Check all Elements tag name
        for element in self.lexed_xml_response:
            element_class = getattr(elements, str(element.tag), None)
            element_instance = element_class()
            element_instance.parse_element(element, self.target_url)
            self.parsed_element.append(element_instance)
            # Validate, Parse & Store the nested children
            # inside the main element element
            self.validate_element(element, element_instance)

    def validate_element(self, element, element_instance):
        children = element.getchildren()
        if children and not element_instance.nestables:
            raise RESTFormatException("%s cannot have any children!"
                                            % element_instance.name)
        for child in children:
            if child.tag not in element_instance.nestables:
                raise RESTFormatException("%s is not nestable inside %s"
                                            % (child, element_instance.name))
            else:
                self.parse_children(child, element_instance)

    def parse_children(self, child_element, parent_instance):
        child_element_class = getattr(elements, str(child_element.tag), None)
        child_element_instance = child_element_class()
        child_element_instance.parse_element(child_element, None)
        parent_instance.children.append(child_element_instance)

    def execute_xml(self):
        try:
            while True:
                try:
                    element_instance = self.parsed_element.pop(0)
                except IndexError:
                    self.log.warn("No more Elements !")
                    break
                if hasattr(element_instance, 'prepare'):
                    # TODO Prepare element concurrently
                    element_instance.prepare(self)
                # Check if it's an inbound call
                if self.session_params['Direction'] == 'inbound':
                    # Answer the call if element need it
                    if not self.answered and \
                        not element_instance.name in self.NO_ANSWER_ELEMENTS:
                        self.log.debug("Answering because Element %s need it" \
                            % element_instance.name)
                        self.answer()
                        self.answered = True
                        # After answer, update callstatus to 'in-progress'
                        self.session_params['CallStatus'] = 'in-progress'
                # execute Element
                element_instance.run(self)
                try:
                    del element_instance
                except:
                    pass
        finally:
            # clean parsed elements
            for element in self.parsed_element:
                element = None
            self.parsed_element = []

        # If transfer is in progress, don't hangup call
        if not self.has_hangup():
            xfer_progress = self.get_var('plivo_transfer_progress') == 'true'
            if not xfer_progress:
                self.log.info('No more Elements, Hangup Now !')
                self.session_params['CallStatus'] = 'completed'
                self.session_params['HangupCause'] = 'NORMAL_CLEARING'
                self.hangup()
            else:
                self.log.info('Transfer In Progress !')


########NEW FILE########
__FILENAME__ = urls
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details

from plivo.rest.freeswitch.api import PlivoRestApi

"""
We are defining here the different Urls available on our Plivo WSGIServer

Each API refers to a specific version number which needs to be added
before each API method.

For instance /v0.1/Call and /v0.2/Call refer to be different version of the API and
so what provide different options to initiate calls.
Refer to the API documentation in order to see the changes made
"""

PLIVO_VERSION = 'v0.1';


URLS = {
        # API Index
        '/': (PlivoRestApi.index, ['GET']),
        # API to reload Plivo config
        '/' + PLIVO_VERSION + '/ReloadConfig/': (PlivoRestApi.reload_config, ['POST', 'GET']),
        # API to reload Plivo Cache config
        '/' + PLIVO_VERSION + '/ReloadCacheConfig/': (PlivoRestApi.reload_cache_config, ['POST', 'GET']),
        # API to originate several calls simultaneously
        '/' + PLIVO_VERSION + '/BulkCall/': (PlivoRestApi.bulk_call, ['POST']),
        # API to originate a single call
        '/' + PLIVO_VERSION + '/Call/': (PlivoRestApi.call, ['POST']),
        # API to originate a call group simultaneously
        '/' + PLIVO_VERSION + '/GroupCall/': (PlivoRestApi.group_call, ['POST']),
        # API to hangup a single call
        '/' + PLIVO_VERSION + '/HangupCall/': (PlivoRestApi.hangup_call, ['POST']),
        # API to transfer a single call
        '/' + PLIVO_VERSION + '/TransferCall/': (PlivoRestApi.transfer_call, ['POST']),
        # API to hangup all calls
        '/' + PLIVO_VERSION + '/HangupAllCalls/': (PlivoRestApi.hangup_all_calls, ['POST']),
        # API to schedule hangup on a single call
        '/' + PLIVO_VERSION + '/ScheduleHangup/': (PlivoRestApi.schedule_hangup, ['POST']),
        # API to cancel a scheduled hangup on a single call
        '/' + PLIVO_VERSION + '/CancelScheduledHangup/': (PlivoRestApi.cancel_scheduled_hangup, ['POST']),
        # API to start recording a call
        '/' + PLIVO_VERSION + '/RecordStart/': (PlivoRestApi.record_start, ['POST']),
        # API to stop recording a call
        '/' + PLIVO_VERSION + '/RecordStop/': (PlivoRestApi.record_stop, ['POST']),
        # API to play something on a single call
        '/' + PLIVO_VERSION + '/Play/': (PlivoRestApi.play, ['POST']),
        # API to stop play something on a single call
        '/' + PLIVO_VERSION + '/PlayStop/': (PlivoRestApi.play_stop, ['POST']),
        # API to schedule playing something  on a single call
        '/' + PLIVO_VERSION + '/SchedulePlay/': (PlivoRestApi.schedule_play, ['POST']),
        # API to cancel a scheduled play on a single call
        '/' + PLIVO_VERSION + '/CancelScheduledPlay/': (PlivoRestApi.cancel_scheduled_play, ['POST']),
        # API to add soundtouch audio effects to a call
        '/' + PLIVO_VERSION + '/SoundTouch/': (PlivoRestApi.sound_touch, ['POST']),
        # API to remove soundtouch audio effects on a call
        '/' + PLIVO_VERSION + '/SoundTouchStop/': (PlivoRestApi.sound_touch_stop, ['POST']),
        # API to send digits to a call
        '/' + PLIVO_VERSION + '/SendDigits/': (PlivoRestApi.send_digits, ['POST']),
        # API to mute a member in a conference
        '/' + PLIVO_VERSION + '/ConferenceMute/': (PlivoRestApi.conference_mute, ['POST']),
        # API to unmute a member in a conference
        '/' + PLIVO_VERSION + '/ConferenceUnmute/': (PlivoRestApi.conference_unmute, ['POST']),
        # API to kick a member from a conference
        '/' + PLIVO_VERSION + '/ConferenceKick/': (PlivoRestApi.conference_kick, ['POST']),
        # API to hangup a conference member
        '/' + PLIVO_VERSION + '/ConferenceHangup/': (PlivoRestApi.conference_hangup, ['POST']),
        # API to deaf a member in a conference
        '/' + PLIVO_VERSION + '/ConferenceDeaf/': (PlivoRestApi.conference_deaf, ['POST']),
        # API to undeaf a member in a conference
        '/' + PLIVO_VERSION + '/ConferenceUndeaf/': (PlivoRestApi.conference_undeaf, ['POST']),
        # API to start recording a conference
        '/' + PLIVO_VERSION + '/ConferenceRecordStart/': (PlivoRestApi.conference_record_start, ['POST']),
        # API to stop recording a conference
        '/' + PLIVO_VERSION + '/ConferenceRecordStop/': (PlivoRestApi.conference_record_stop, ['POST']),
        # API to play a sound file into a conference
        '/' + PLIVO_VERSION + '/ConferencePlay/': (PlivoRestApi.conference_play, ['POST']),
        # API to say something into a conference
        '/' + PLIVO_VERSION + '/ConferenceSpeak/': (PlivoRestApi.conference_speak, ['POST']),
        # API to list a conference with members
        '/' + PLIVO_VERSION + '/ConferenceListMembers/': (PlivoRestApi.conference_list_members, ['POST']),
        # API to list all conferences with members
        '/' + PLIVO_VERSION + '/ConferenceList/': (PlivoRestApi.conference_list, ['POST']),
       }

########NEW FILE########
__FILENAME__ = daemonize
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Daemonize application.
"""

import os
import sys
import grp
import pwd
from subprocess import Popen
import optparse
import gevent


__default_servicename__ = os.path.splitext(os.path.basename(sys.argv[0]))[0]


def daemon(user, group, path='/', pidfile='/tmp/%s.pid' % __default_servicename__, other_groups=()):
    '''
    Daemonizes current application.
    '''
    # Get uid and gid from user and group names
    uid = int(pwd.getpwnam(user)[2])
    gid = int(grp.getgrnam(group)[2])
    # Get ID of other groups
    other_groups_id = []
    for name in other_groups:
        try:
            other_groups_id.append(int(grp.getgrnam(name)[2]) )
        except:
            pass
    # First fork
    pid = gevent.fork()
    if not pid == 0:
        os._exit(0)
    # Creates a session and sets the process group ID
    os.setsid()
    # Second fork
    pid = gevent.fork()
    if not pid == 0:
        os._exit(0)
    # Change directoty
    os.chdir(path)
    # Set umask
    os.umask(0)
    # Write pidfile
    open(pidfile, 'w').write(str(os.getpid()))
    # Set group and groups
    os.setgid(gid)
    if other_groups_id:
        os.setgroups(other_groups_id)
    # Set user
    os.setuid(uid)
    # Redirect stdout/stderr to /dev/null
    sys.stdout = sys.stderr = open(os.devnull, 'a+')
    gevent.reinit()


def daemon_script(script, user, group, path='/', pidfile=None, script_args=(), other_groups=(), python_bin=None):
    '''
    Daemonize a python script.
    '''
    # Autocreate path for pidfile (based on script arg) if not set
    if not pidfile:
        pidfile = '/tmp/' + os.path.splitext(os.path.basename(script))[0] + '.pid'
    # Get full/real path to script
    real_script = os.path.realpath(script)
    # Get uid and gid from user and group names
    uid = int(pwd.getpwnam(user)[2])
    gid = int(grp.getgrnam(group)[2])
    # Get ID of other groups
    other_groups_id = []
    for name in other_groups:
        try:
            other_groups_id.append(int(grp.getgrnam(name)[2]) )
        except:
            pass
    # First fork
    pid = os.fork()
    if not pid == 0:
        os._exit(0)
    # Creates a session and sets the process group ID
    os.setsid()
    # Second fork
    pid = os.fork()
    if not pid == 0:
        os._exit(0)
    # Change directoty
    os.chdir(path)
    # Set umask
    os.umask(0)
    # Set group and groups
    os.setgid(gid)
    if other_groups_id:
        os.setgroups(other_groups_id)
    # Set user
    os.setuid(uid)
    # Set python binary
    if not python_bin:
        cmd = ["/usr/bin/env", "python"]
    else:
        cmd = [python_bin]
    cmd.append(real_script)
    # Add script_args
    for arg in script_args:
        cmd.append(arg)
    # Run script
    pid = Popen(cmd).pid
    # Write pidfile
    open(pidfile, 'w').write(str(pid))
    # Redirect stdout/stderr to /dev/null
    sys.stdout = sys.stderr = open(os.devnull, 'a+')
    # Wait pid end
    os.waitpid(pid, 0)


def main():
    parser = optparse.OptionParser()
    parser.add_option("-s", "--script", action="store", type="string",
                      dest="script", help="python script SCRIPT to run (argument is mandatory)",
                      metavar="SCRIPT")
    parser.add_option("-p", "--pidfile", action="store", type="string",
                      dest="pidfile", help="write pid to PIDFILE (argument is mandatory)",
                      metavar="PIDFILE")
    parser.add_option("-u", "--user", action="store", type="string",
                      dest="user", help="set uid to USER (argument is mandatory)",
                      metavar="USER")
    parser.add_option("-g", "--group", action="store", type="string",
                      dest="group", help="set gid to GROUP (argument is mandatory)",
                      metavar="GROUP")
    parser.add_option("-G", "--groups", action="append", type="string", default=[],
                      dest="groups", help="set other groups gid to OTHERGROUP (can be added multiple times)",
                      metavar="OTHERGROUP")
    parser.add_option("-P", "--pybin", action="store", type="string", default=None,
                      dest="pybin", help="set python binary PYBIN to run script",
                      metavar="PYBIN")
    parser.add_option("-a", "--scriptarg", action="append", type="string", default=[],
                      dest="scriptargs", help="add ARG to python script (can be added multiple times)",
                      metavar="ARG")
    (options, args) = parser.parse_args()

    script = options.script
    user = options.user
    group = options.group
    pidfile = options.pidfile
    ogroups = options.groups
    pybin = options.pybin
    scriptargs = options.scriptargs

    if not script or not user or not group or not pidfile:
        parser.print_help()
        sys.exit(1)

    daemon_script(script, user, group, pidfile=pidfile,
                  script_args=scriptargs, other_groups=ogroups,
                  python_bin=pybin)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = encode
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

import sys


def safe_str(o):
    try:
        return str(o)
    except:
        if isinstance(o, unicode):
            encoding = sys.getdefaultencoding()
            return o.encode(encoding, 'backslashreplace')
        return o

########NEW FILE########
__FILENAME__ = logger
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

"""
Log classes : stdout, syslog and file loggers
"""

from gevent import monkey
monkey.patch_all()

import logging
import logging.handlers
from logging import RootLogger
import sys
import os

from plivo.utils.encode import safe_str

monkey.patch_thread() # thread must be patched after import

LOG_DEBUG = logging.DEBUG
LOG_ERROR = logging.ERROR
LOG_INFO = logging.INFO
LOG_WARN = logging.WARN
LOG_WARNING = logging.WARNING
LOG_CRITICAL = logging.CRITICAL
LOG_FATAL = logging.FATAL
LOG_NOTSET = logging.NOTSET


__default_servicename__ = os.path.splitext(os.path.basename(sys.argv[0]))[0]



class StdoutLogger(object):
    def __init__(self, loglevel=LOG_DEBUG, servicename=__default_servicename__):
        self.loglevel = loglevel
        h = logging.StreamHandler()
        h.setLevel(loglevel)
        fmt = logging.Formatter("%(asctime)s "+servicename+"[%(process)d]: %(levelname)s: %(message)s")
        h.setFormatter(fmt)
        self._logger = RootLogger(loglevel)
        self._logger.addHandler(h)

    def set_debug(self):
        self.loglevel = LOG_DEBUG
        self._logger.setLevel(self.loglevel)

    def set_info(self):
        self.loglevel = LOG_INFO
        self._logger.setLevel(self.loglevel)

    def set_error(self):
        self.loglevel = LOG_ERROR
        self._logger.setLevel(self.loglevel)

    def set_warn(self):
        self.loglevel = LOG_WARN
        self._logger.setLevel(self.loglevel)

    def info(self, msg):
        self._logger.info(safe_str(msg))

    def debug(self, msg):
        self._logger.debug(safe_str(msg))

    def warn(self, msg):
        self._logger.warn(safe_str(msg))

    def error(self, msg):
        self._logger.error(safe_str(msg))

    def write(self, msg):
        self.info(msg)


class Syslog(logging.handlers.SysLogHandler):
    LOG_EMERG     = 0       #  system is unusable
    LOG_ALERT     = 1       #  action must be taken immediately
    LOG_CRIT      = 2       #  critical conditions
    LOG_ERR       = 3       #  error conditions
    LOG_WARNING   = 4       #  warning conditions
    LOG_NOTICE    = 5       #  normal but significant condition
    LOG_INFO      = 6       #  informational
    LOG_DEBUG     = 7       #  debug-level messages


    #  facility codes
    LOG_KERN      = 0       #  kernel messages
    LOG_USER      = 1       #  random user-level messages
    LOG_MAIL      = 2       #  mail system
    LOG_DAEMON    = 3       #  system daemons
    LOG_AUTH      = 4       #  security/authorization messages
    LOG_SYSLOG    = 5       #  messages generated internally by syslogd
    LOG_LPR       = 6       #  line printer subsystem
    LOG_NEWS      = 7       #  network news subsystem
    LOG_UUCP      = 8       #  UUCP subsystem
    LOG_CRON      = 9       #  clock daemon
    LOG_AUTHPRIV  = 10  #  security/authorization messages (private)

    #  other codes through 15 reserved for system use
    LOG_LOCAL0    = 16      #  reserved for local use
    LOG_LOCAL1    = 17      #  reserved for local use
    LOG_LOCAL2    = 18      #  reserved for local use
    LOG_LOCAL3    = 19      #  reserved for local use
    LOG_LOCAL4    = 20      #  reserved for local use
    LOG_LOCAL5    = 21      #  reserved for local use
    LOG_LOCAL6    = 22      #  reserved for local use
    LOG_LOCAL7    = 23      #  reserved for local use


    priority_names = {
        "alert":    LOG_ALERT,
        "crit":     LOG_CRIT,
        "critical": LOG_CRIT,
        "debug":    LOG_DEBUG,
        "emerg":    LOG_EMERG,
        "err":      LOG_ERR,
        "error":    LOG_ERR,        #  DEPRECATED
        "info":     LOG_INFO,
        "notice":   LOG_NOTICE,
        "panic":    LOG_EMERG,      #  DEPRECATED
        "notice":   LOG_NOTICE,
        "warn":     LOG_WARNING,    #  DEPRECATED
        "warning":  LOG_WARNING,
        "info_srv":  LOG_INFO,
        "error_srv":  LOG_ERR,
        "debug_srv":  LOG_DEBUG,
        "warn_srv":  LOG_WARNING,
        }

    facility_names = {
        "auth":     LOG_AUTH,
        "authpriv": LOG_AUTHPRIV,
        "cron":     LOG_CRON,
        "daemon":   LOG_DAEMON,
        "kern":     LOG_KERN,
        "lpr":      LOG_LPR,
        "mail":     LOG_MAIL,
        "news":     LOG_NEWS,
        "security": LOG_AUTH,       #  DEPRECATED
        "syslog":   LOG_SYSLOG,
        "user":     LOG_USER,
        "uucp":     LOG_UUCP,
        "local0":   LOG_LOCAL0,
        "local1":   LOG_LOCAL1,
        "local2":   LOG_LOCAL2,
        "local3":   LOG_LOCAL3,
        "local4":   LOG_LOCAL4,
        "local5":   LOG_LOCAL5,
        "local6":   LOG_LOCAL6,
        "local7":   LOG_LOCAL7,
        }


class SysLogger(StdoutLogger):
    def __init__(self, addr='/dev/log', syslogfacility="local0", \
                 loglevel=LOG_DEBUG, servicename=__default_servicename__):
        if ':' in addr:
            host, port = addr.split(':', 1)
            port = int(port)
            addr = (host, port)
        fac = Syslog.facility_names[syslogfacility]
        h = Syslog(address=addr, facility=fac)
        h.setLevel(loglevel)
        fmt = logging.Formatter(servicename+"[%(process)d]: %(levelname)s: %(message)s")
        h.setFormatter(fmt)
        self._logger = RootLogger(loglevel)
        self._logger.addHandler(h)


class FileLogger(StdoutLogger):
    def __init__(self, logfile='/tmp/%s.log' % __default_servicename__, \
                 loglevel=LOG_DEBUG, servicename=__default_servicename__):
        h = logging.FileHandler(filename=logfile)
        h.setLevel(loglevel)
        fmt = logging.Formatter("%(asctime)s "+servicename+"[%(process)d]: %(levelname)s: %(message)s")
        h.setFormatter(fmt)
        self._logger = RootLogger(loglevel)
        self._logger.addHandler(h)


class DummyLogger(object):
    def set_debug(self):
        pass

    def set_info(self):
        pass

    def set_error(self):
        pass

    def set_warn(self):
        pass

    def info(self, msg):
        pass

    def debug(self, msg):
        pass

    def warn(self, msg):
        pass

    def error(self, msg):
        pass

    def write(self, msg):
        pass

class HTTPHandler(logging.handlers.HTTPHandler):
    def __init__(self, host, url, method="GET"):
        logging.handlers.HTTPHandler.__init__(self, host, url, method)

    def emit(self, record):
        """
        Emit a record.

        Send the record to the Web server as a percent-encoded dictionary
        """
        try:
            import httplib, urllib
            host = self.host
            h = httplib.HTTP(host)
            url = self.url
            data = urllib.urlencode(self.mapLogRecord(record))
            if self.method == "GET":
                if (url.find('?') >= 0):
                    sep = '&'
                else:
                    sep = '?'
                url = url + "%c%s" % (sep, data)
            h.putrequest(self.method, url)
            # support multiple hosts on one IP address...
            # need to strip optional :port from host, if present
            i = host.find(":")
            if i >= 0:
                host = host[:i]
            h.putheader("Host", host)
            if self.method == "POST":
                h.putheader("Content-type",
                            "application/x-www-form-urlencoded")
                h.putheader("Content-length", str(len(data)))
            h.endheaders(data if self.method == "POST" else None)
            h.getreply()    #can't do anything with the result
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            raise



class HTTPLogger(object):
    def __init__(self, url, method='POST', fallback_file=None, loglevel=LOG_DEBUG, servicename=__default_servicename__):
        import urlparse
        self.loglevel = loglevel
        self.fallback_file = fallback_file
        p = urlparse.urlparse(url)
        netloc = p.netloc
        urlpath = p.path
        if p.query:
            urlpath += '?' + query
        h = HTTPHandler(host=netloc, url=urlpath, method=method)
        h.setLevel(loglevel)
        fmt = logging.Formatter(servicename+"[%(process)d]: %(levelname)s: %(message)s")
        h.setFormatter(fmt)
        self._logger = RootLogger(loglevel)
        self._logger.addHandler(h)
        if self.fallback_file:
            self._fallback = FileLogger(logfile=self.fallback_file,
                                        loglevel=self.loglevel,
                                        servicename=servicename)
        else:
            self._fallback = DummyLogger()

    def set_debug(self):
        self.loglevel = LOG_DEBUG
        self._logger.setLevel(self.loglevel)
        self._fallback.set_debug()

    def set_info(self):
        self.loglevel = LOG_INFO
        self._logger.setLevel(self.loglevel)
        self._fallback.set_info()

    def set_error(self):
        self.loglevel = LOG_ERROR
        self._logger.setLevel(self.loglevel)
        self._fallback.set_error()

    def set_warn(self):
        self.loglevel = LOG_WARN
        self._logger.setLevel(self.loglevel)
        self._fallback.set_warn()

    def info(self, msg):
        try:
            self._logger.info(safe_str(msg))
        except:
            self._fallback.info(safe_str(msg))

    def debug(self, msg):
        try:
            self._logger.debug(safe_str(msg))
        except:
            self._fallback.debug(safe_str(msg))

    def warn(self, msg):
        try:
            self._logger.warn(safe_str(msg))
        except:
            self._fallback.warn(safe_str(msg))

    def error(self, msg):
        try:
            self._logger.error(safe_str(msg))
        except:
            self._fallback.error(safe_str(msg))

    def write(self, msg):
        try:
            self.info(msg)
        except:
            self._fallback.info(safe_str(msg))


########NEW FILE########
__FILENAME__ = test_events
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from unittest import TestCase

from plivo.core.freeswitch.eventtypes import Event


class TestEvent(TestCase):
    EVENT_COMMAND_REPLY = "Content-Type: command/reply\nReply-Text: +OK accepted\n\n"
    EVENT_AUTH_REQUEST = "Content-Type: auth/request\n\n"
    EVENT_CONTENT_LENGTH = "Content-Length: 491\nContent-Type: text/event-plain\n\n"
    EVENT_PLAIN = """Event-Name: RE_SCHEDULE
Core-UUID: 12640749-db62-421c-beac-4863eac76510
FreeSWITCH-Hostname: vocaldev
FreeSWITCH-IPv4: 10.0.0.108
FreeSWITCH-IPv6: %3A%3A1
Event-Date-Local: 2011-01-03%2018%3A33%3A56
Event-Date-GMT: Mon,%2003%20Jan%202011%2017%3A33%3A56%20GMT
Event-Date-Timestamp: 1294076036427219
Event-Calling-File: switch_scheduler.c
Event-Calling-Function: switch_scheduler_execute
Event-Calling-Line-Number: 65
Task-ID: 1
Task-Desc: heartbeat
Task-Group: core
Task-Runtime: 1294076056

"""


    def test_command_reply(self):
        ev = Event(self.EVENT_COMMAND_REPLY)
        self.assertEquals(ev.get_content_type(), "command/reply")
        self.assertEquals(ev.get_reply_text(), "+OK accepted")
        self.assertTrue(ev.is_reply_text_success())

    def test_auth_request(self):
        ev = Event(self.EVENT_AUTH_REQUEST)
        self.assertEquals(ev.get_content_type(), "auth/request")

    def test_event_plain(self):
        ev1 = Event(self.EVENT_CONTENT_LENGTH)
        self.assertEquals(ev1.get_content_length(), 491)
        self.assertEquals(ev1.get_content_type(), "text/event-plain")
        ev2 = Event(self.EVENT_PLAIN)
        self.assertEquals(ev2.get_header("Event-Name"), "RE_SCHEDULE")
        self.assertEquals(len(self.EVENT_PLAIN), ev1.get_content_length())

########NEW FILE########
__FILENAME__ = test_inboundsocket
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

from unittest import TestCase

import gevent
from gevent import socket
from gevent import Timeout
from gevent.server import StreamServer

from plivo.core.freeswitch.inboundsocket import InboundEventSocket
from plivo.core.freeswitch.eventtypes import Event
from plivo.core.errors import ConnectError


class TestClient(object):
    '''
    Client class on test inbound server side.
    '''
    def __init__(self, sock):
        self.socket = sock
        self.fd = self.socket.makefile()
        self.auth = False
        self.event_plain = False

    def send(self, msg):
        self.fd.write(msg)
        self.fd.flush()

    def recv(self):
        return self.fd.readline()

    def close(self):
        try:
            self.socket.close()
        except:
            pass


class TestEventSocketServer(object):
    '''
    Test inbound socket server.
    '''
    def __init__(self):
        self.server = StreamServer(('127.0.0.1', 18021), self.emulate)

    def start(self):
        self.server.serve_forever()

    def emulate(self, sock, address):
        client = TestClient(sock)
        client.send("Content-Type: auth/request\n\n")
        buff = ""
        # do auth (3 tries)
        for i in range(3):
            while True:
                line = client.recv()
                if not line:
                    break
                elif line == '\r\n' or line == '\n':
                    self.check_auth(client, buff)
                    buff = ""
                    break
                else:
                    buff += line
                    if buff.startswith('exit'):
                        self.disconnect(client)
                        return
            if client.auth is True:
                break
        if client.auth is False:
            self.disconnect(client)
            return

        # wait event plain ALL (3 tries)
        buff = ""
        for i in range(3):
            while True:
                line = client.recv()
                if not line:
                    break
                elif line == '\r\n' or line == '\n':
                    self.event_plain(client, buff)
                    buff = ""
                    break
                else:
                    buff += line
                    if buff.startswith('exit'):
                        self.disconnect(client)
                        return
            if client.event_plain is True:
                break
        if client.event_plain is False:
            self.disconnect(client)
            return

        # send fake heartbeat and re_schedule events to client 10 times
        for i in range(10):
            self.send_heartbeat(client)
            gevent.sleep(0.01)
            self.send_re_schedule(client)
            gevent.sleep(0.01)

        self.disconnect(client)
        return

    def disconnect(self, client):
        client.send("Content-Type: text/disconnect-notice\nContent-Length: 67\n\nDisconnected, goodbye.\nSee you at ClueCon! http://www.cluecon.com/\n\n")
        client.close()

    def send_heartbeat(self, client):
        msg = \
"""Content-Length: 630
Content-Type: text/event-plain

Event-Name: HEARTBEAT
Core-UUID: 12640749-db62-421c-beac-4863eac76510
FreeSWITCH-Hostname: vocaldev
FreeSWITCH-IPv4: 10.0.0.108
FreeSWITCH-IPv6: %3A%3A1
Event-Date-Local: 2011-01-04%2010%3A19%3A56
Event-Date-GMT: Tue,%2004%20Jan%202011%2009%3A19%3A56%20GMT
Event-Date-Timestamp: 1294132796167745
Event-Calling-File: switch_core.c
Event-Calling-Function: send_heartbeat
Event-Calling-Line-Number: 65
Event-Info: System%20Ready
Up-Time: 0%20years,%203%20days,%2017%20hours,%2043%20minutes,%2039%20seconds,%20644%20milliseconds,%2091%20microseconds
Session-Count: 0
Session-Per-Sec: 30
Session-Since-Startup: 0
Idle-CPU: 100.000000

"""
        client.send(msg)

    def send_re_schedule(self, client):
        msg = \
"""Content-Length: 491
Content-Type: text/event-plain

Event-Name: RE_SCHEDULE
Core-UUID: 12640749-db62-421c-beac-4863eac76510
FreeSWITCH-Hostname: vocaldev
FreeSWITCH-IPv4: 10.0.0.108
FreeSWITCH-IPv6: %3A%3A1
Event-Date-Local: 2011-01-04%2010%3A19%3A56
Event-Date-GMT: Tue,%2004%20Jan%202011%2009%3A19%3A56%20GMT
Event-Date-Timestamp: 1294132796167745
Event-Calling-File: switch_scheduler.c
Event-Calling-Function: switch_scheduler_execute
Event-Calling-Line-Number: 65
Task-ID: 1
Task-Desc: heartbeat
Task-Group: core
Task-Runtime: 1294132816

"""
        client.send(msg)

    def check_auth(self, client, buff):
        # auth request
        if buff.startswith('auth '):
            try:
                password = buff.split(' ')[1].strip()
                if password == 'ClueCon':
                    client.auth = True
                    client.send("Content-Type: command/reply\nReply-Text: +OK accepted\n\n")
                    return True
                raise Exception("Invalid auth password")
            except:
                client.send("Content-Type: command/reply\nReply-Text: -ERR invalid\n\n")
                return False
        client.send("Content-Type: command/reply\nReply-Text: -ERR invalid\n\n")
        return False

    def event_plain(self, client, buff):
        if buff.startswith('event plain'):
            client.event_plain = True
            client.send("Content-Type: command/reply\nReply-Text: +OK event listener enabled plain\n\n")
            return True
        return False


class TestInboundEventSocket(InboundEventSocket):
    def __init__(self, host, port, password, filter='ALL', pool_size=500, connect_timeout=5):
        InboundEventSocket.__init__(self, host, port, password, filter, pool_size=pool_size,
                                        connect_timeout=connect_timeout, eventjson=False)
        self.heartbeat_events = []
        self.re_schedule_events = []

    def on_re_schedule(self, ev):
        self.re_schedule_events.append(ev)

    def on_heartbeat(self, ev):
        self.heartbeat_events.append(ev)

    def serve_for_test(self):
        timeout = Timeout(10)
        timeout.start()
        try:
            while self.is_connected():
                if len(self.re_schedule_events) == 10 and len(self.heartbeat_events) == 10:
                    break
                gevent.sleep(0.01)
        finally:
            timeout.cancel()


class TestInboundCase(TestCase):
    '''
    Test case for Inbound Event Socket.
    '''
    def setUp(self):
        s = TestEventSocketServer()
        self.server_proc = gevent.spawn(s.start)
        gevent.sleep(0.2)

    def tearDown(self):
        try:
            self.server_proc.kill()
        except:
            pass

    def test_login_failure(self):
        isock = InboundEventSocket('127.0.0.1', 23333, 'ClueCon')
        self.assertRaises(ConnectError, isock.connect)

    def test_login_success(self):
        isock = InboundEventSocket('127.0.0.1', 18021, 'ClueCon', eventjson=False)
        try:
            isock.connect()
        except socket.error, se:
            self.fail("socket error: %s" % str(se))
        except ConnectError, e:
            self.fail("connect error: %s" % str(e))

    def test_events(self):
        isock = TestInboundEventSocket('127.0.0.1', 18021, 'ClueCon')
        try:
            isock.connect()
        except socket.error, se:
            self.fail("socket error: %s" % str(se))
        except ConnectError, e:
            self.fail("connect error: %s" % str(e))
        try:
            isock.serve_for_test()
        except Timeout, t:
            self.fail("timeout error: cannot get all events")
        self.assertEquals(len(isock.heartbeat_events), 10)
        self.assertEquals(len(isock.re_schedule_events), 10)
        for ev in isock.heartbeat_events:
            self.assertEquals(ev.get_header('Event-Name'), 'HEARTBEAT')
        for ev in isock.re_schedule_events:
            self.assertEquals(ev.get_header('Event-Name'), 'RE_SCHEDULE')

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
# Copyright (c) 2011 Plivo Team. See LICENSE for details.

import os
import sys
import unittest


def make_test():
    return unittest.TextTestRunner()

def make_suite():
    return unittest.TestLoader().loadTestsFromNames([
        'tests.freeswitch.test_events',
        'tests.freeswitch.test_inboundsocket',
    ])

def run_test():
    return make_suite()

def run():
    runner = make_test()
    suite = make_suite()
    runner.run(suite)


if __name__ == '__main__':
    #sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    sys.path.insert(0, '.')
    run()

########NEW FILE########
