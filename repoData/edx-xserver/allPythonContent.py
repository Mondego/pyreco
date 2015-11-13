__FILENAME__ = answer
print "hello world"

########NEW FILE########
__FILENAME__ = wrong_cpu
i = 1
for x in range(10**7):
    i += x

# correct output, but takes too long
print "hello world"

# Debugging
import sys
sys.stdout = sys.__stdout__

print "#" * 80
print "Still running!  Should have been killed."
print "#" * 80

########NEW FILE########
__FILENAME__ = wrong_fork
import os

for i in range(1):
    try:
        if os.fork() == 0:
            # in child
            break
        print "forked!"
    except:
        import sys
        print "Got exception: " + str(sys.exc_info())

import time
time.sleep(60)   # Can I see a bunch of these in top?
print "hello world"


########NEW FILE########
__FILENAME__ = wrong_network
import requests
r = requests.get('http://www.edx.org')
print "hello world"


########NEW FILE########
__FILENAME__ = wrong_output
# We start so well...
print "hello world"

# but then get a bit too excited...
for i in range(10000):
    print "hello world!"

########NEW FILE########
__FILENAME__ = wrong_sleep
import time
time.sleep(10)
print "hello world"

########NEW FILE########
__FILENAME__ = wrong_stdout
# take back stdout
import sys
sys.stdout = sys.__stdout__

print "O hai"

########NEW FILE########
__FILENAME__ = infinite
import time
while True:
 time.sleep(1)

########NEW FILE########
__FILENAME__ = answer
def isVowel(char):
    '''
    char: a single letter of any case

    returns: True if char is a vowel and False otherwise.
    '''
    if char == 'a' or char == 'e' or char == 'i' or char == 'o' or char == 'u':
        return True
    elif char == 'A' or char == 'E' or char == 'I' or char == 'O' or char == 'U':
        return True
    else:
        return False

########NEW FILE########
__FILENAME__ = logsettings
import os
import platform
import sys
from logging.handlers import SysLogHandler


def get_logger_config(log_dir,
                      logging_env="no_env",
                      edx_filename="edx.log",
                      dev_env=False,
                      debug=False,
                      local_loglevel='INFO'):

    """
    Return the appropriate logging config dictionary. You should assign the
    result of this to the LOGGING var in your settings. The reason it's done
    this way instead of registering directly is because I didn't want to worry
    about resetting the logging state if this is called multiple times when
    settings are extended.

    If dev_env is set to true logging will not be done via local rsyslogd,
    instead, application logs will be dropped in log_dir.

    "edx_filename" are ignored unless dev_env
    is set to true since otherwise logging is handled by rsyslogd.

    """

    # Revert to INFO if an invalid string is passed in
    if local_loglevel not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
        local_loglevel = 'INFO'

    hostname = platform.node().split(".")[0]
    syslog_format = ("[%(name)s][env:{logging_env}] %(levelname)s "
                     "[{hostname}  %(process)d] [%(filename)s:%(lineno)d] "
                     "- %(message)s").format(
                        logging_env=logging_env, hostname=hostname)

    handlers = ['console', 'local'] if debug else ['console', 'local']

    logger_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'standard': {
                'format': '%(asctime)s %(levelname)s %(process)d '
                          '[%(name)s] %(filename)s:%(lineno)d - %(message)s',
            },
            'syslog_format': {'format': syslog_format},
            'raw': {'format': '%(message)s'},
        },
        'handlers': {
            'console': {
                'level': 'DEBUG' if debug else 'INFO',
                'class': 'logging.StreamHandler',
                'formatter': 'standard',
                'stream': sys.stdout,
            },
        },
        'loggers': {
            '': {
                'handlers': handlers,
                'level': 'DEBUG',
                'propagate': False
            },
            'xserver': {
                'handlers': handlers,
                'level': 'DEBUG',
                'propagate': False
            },
        }
    }

    if dev_env:
        edx_file_loc = os.path.join(log_dir, edx_filename)
        logger_config['handlers'].update({
            'local': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': local_loglevel,
                'formatter': 'standard',
                'filename': edx_file_loc,
                'maxBytes': 1024 * 1024 * 2,
                'backupCount': 5,
            },
        })
    else:
        logger_config['handlers'].update({
            'local': {
                'level': local_loglevel,
                'class': 'logging.handlers.SysLogHandler',
                'address': '/dev/log',
                'formatter': 'syslog_format',
                'facility': SysLogHandler.LOG_LOCAL0,
            },
        })

    return logger_config

########NEW FILE########
__FILENAME__ = pyxserver_wsgi
#!/usr/bin/python
#------------------------------------------------------------
# Run me with (may need su privilege for logging):
#        gunicorn -w 4 -b 127.0.0.1:3031 pyxserver_wsgi:application
#  (remove the -w 4 for debugging--don't want 4 workers)
# gunicorn --preload -b 127.0.0.1:3031 --timeout=35 --pythonpath=. pyxserver_wsgi:application
#------------------------------------------------------------

import cgi    # for the escape() function
import json
import logging
import os
import os.path
from statsd import statsd
import sys
from time import localtime, strftime, time

import settings    # Not django, but do something similar

from sandbox import sandbox

# make sure we can find the grader files
sys.path.append(settings.GRADER_ROOT)
import grade

logging.config.dictConfig(settings.LOGGING)

log = logging.getLogger("xserver." + __name__)


results_template = u"""
<div class="test">
<header>Test results</header>
  <section>
    <div class="shortform">
    {status}
    </div>
    <div class="longform">
      {errors}
      {results}
    </div>
  </section>
</div>
"""


results_correct_template = u"""
  <div class="result-output result-correct">
    <h4>{short-description}</h4>
    <pre>{long-description}</pre>
    <dl>
    <dt>Output:</dt>
    <dd class="result-actual-output">
       <pre>{actual-output}</pre>
       </dd>
    </dl>
  </div>
"""


results_incorrect_template = u"""
  <div class="result-output result-incorrect">
    <h4>{short-description}</h4>
    <pre>{long-description}</pre>
    <dl>
    <dt>Your output:</dt>
    <dd class="result-actual-output"><pre>{actual-output}</pre></dd>
    <dt>Correct output:</dt>
    <dd><pre>{expected-output}</pre></dd>
    </dl>
  </div>
"""


def format_errors(errors):
    esc = cgi.escape
    error_string = ''
    error_list = [esc(e) for e in errors or []]
    if error_list:
        try:
            items = u'\n'.join([u'<li><pre>{0}</pre></li>\n'.format(e) for e in error_list])
            error_string = u'<ul>\n{0}</ul>\n'.format(items)
            error_string = u'<div class="result-errors">{0}</div>'.format(error_string)
        except UnicodeDecodeError:
            # See http://wiki.python.org/moin/UnicodeDecodeError; this error happens in the above unicode encoding
            # because it's assuming str `e` is in ascii encoding; when it is in Unicode already it gets sad.
            items = '\n'.join(['<li><pre>{0}</pre></li>\n'.format(e) for e in error_list])
            error_string = '<ul>\n{0}</ul>\n'.format(items)
            error_string = '<div class="result-errors">{0}</div>'.format(error_string)
    return error_string


def to_dict(result):
    # long description may or may not be provided.  If not, don't display it.
    # TODO: replace with mako template
    esc = cgi.escape
    if result[1]:
        long_desc = u'<p>{0}</p>'.format(esc(result[1]))
    else:
        long_desc = u''
    return {'short-description': esc(result[0]),
            'long-description': long_desc,
            'correct': result[2],   # Boolean; don't escape.
            'expected-output': esc(result[3]),
            'actual-output': esc(result[4])
            }


def render_results(results):
    output = []
    test_results = [to_dict(r) for r in results['tests']]
    for result in test_results:
        if result['correct']:
            template = results_correct_template
        else:
            template = results_incorrect_template
        output += template.format(**result)

    errors = format_errors(results['errors'])

    status = 'INCORRECT'
    if errors:
        status = 'ERROR'
    elif results['correct']:
        status = 'CORRECT'

    return results_template.format(status=status,
                                   errors=errors,
                                   results=''.join(output))


def do_GET(data):
    return "Hey, the time is %s" % strftime("%a, %d %b %Y %H:%M:%S", localtime())


def do_POST(data):
    statsd.increment('xserver.post-requests')
    # This server expects jobs to be pushed to it from the queue
    xpackage = json.loads(data)
    body  = xpackage['xqueue_body']
    files = xpackage['xqueue_files']

    # Delivery from the lms
    body = json.loads(body)
    student_response = body['student_response']
    payload = body['grader_payload']
    try:
        grader_config = json.loads(payload)
    except ValueError as err:
        # If parsing json fails, erroring is fine--something is wrong in the content.
        # However, for debugging, still want to see what the problem is
        statsd.increment('xserver.grader_payload_error')

        log.debug("error parsing: '{0}' -- {1}".format(payload, err))
        raise

    log.debug("Processing submission, grader payload: {0}".format(payload))
    relative_grader_path = grader_config['grader']
    grader_path = os.path.join(settings.GRADER_ROOT, relative_grader_path)
    start = time()
    results = grade.grade(grader_path, grader_config, student_response, sandbox)

    statsd.histogram('xserver.grading-time', time() - start)

    # Make valid JSON message
    reply = { 'correct': results['correct'],
              'score': results['score'],
              'msg': render_results(results) }

    statsd.increment('xserver.post-replies (non-exception)')

    return json.dumps(reply)


# Entry point
def application(env, start_response):

    log.info("Starting application")
    # Handle request
    method = env['REQUEST_METHOD']
    data = env['wsgi.input'].read()

    log.debug('-' * 60)
    log.debug(method)

    def post_wrapper(data):
        try:
            return do_POST(data)
        except:
            log.exception("Error processing request: {0}".format(data))
            return None

    handlers = {'GET': do_GET,
                 'POST': post_wrapper,
                 }
    if method in handlers.keys():
        reply = handlers[method](data)

        if reply is not None:
            log.debug(' [*] reply:\n%s\n' % reply)

            start_response('200 OK', [('Content-Type', 'text/html')])
            return reply

    # If we fell through to here, complain.
    start_response('404 Not Found', [('Content-Type', 'text/plain')])
    return ''

########NEW FILE########
__FILENAME__ = sandbox
"""
Setup for apparmor-based sandbox.
"""

import logging

import settings

log = logging.getLogger(__name__)

def record_suspicious_submission(msg, code_str):
    """
    Record a suspicious submission:

    TODO: upload to edx-studentcode-suspicious bucket on S3.  For now, just
    logging to avoids need for more config changes (S3 credentials, python
    requirements).
    """
    log.warning('Suspicious code: {0}, {1}'.format(msg, code_str))

def sandbox_cmd_list():
    """
    Return a command to use to run a python script in a sandboxed env.

    NOTE: this is kind of ugly--we should really have all copy-to-tmp dir and
    run logic here too, but then we'd have to duplicate it for testing in the
    content repo.
    """
    if settings.DO_SANDBOXING:
        return ['sudo', '-u', 'sandbox', settings.SANDBOX_PYTHON]
    else:
        return ['python']

########NEW FILE########
__FILENAME__ = dirs
#!/usr/bin/env python

# Create all the directories. Use all the inodes.
# DO NOT RUN AT HOME...

import os

def main():
    i = 0
    while True:
        i += 1
        if i % 100 == 0:
            print "Made {0} dirs!".format(i)
        os.mkdir('deepdir')
        os.chdir('deepdir')

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = settings
# Not django (for now), but use the same settings format anyway

import json
import os
from logsettings import get_logger_config
from path import path
import sys

ROOT_PATH = path(__file__).dirname()
REPO_PATH = ROOT_PATH
ENV_ROOT = REPO_PATH.dirname()

# DEFAULTS

DEBUG = False


LOGGING = get_logger_config(ENV_ROOT / "log",
                            logging_env="dev",
                            local_loglevel="DEBUG",
                            dev_env=True,
                            debug=True)

GRADER_ROOT = os.path.abspath(os.path.join(ENV_ROOT, 'data/6.00x/graders'))

# Dev setting.
DO_SANDBOXING = False

# AWS

if os.path.isfile(ENV_ROOT / "env.json"):
    print "Opening env.json file"
    with open(ENV_ROOT / "env.json") as env_file:
        ENV_TOKENS = json.load(env_file)

    # True by default!  Don't want messed up config to let students run regular python!
    DO_SANDBOXING = ENV_TOKENS.get('DO_SANDBOXING', True)


    LOG_DIR = ENV_TOKENS['LOG_DIR']
    local_loglevel = ENV_TOKENS.get('LOCAL_LOGLEVEL', 'INFO')
    LOGGING = get_logger_config(LOG_DIR,
                                logging_env=ENV_TOKENS['LOGGING_ENV'],
                                local_loglevel=local_loglevel,
                                debug=False)

    # Should be absolute path to 6.00 grader dir.
    # NOTE: This means we only get one version of 6.00 graders available--has to
    # be the same for internal and external class.  Not critical -- can always
    # use different grader file if want different problems.
    GRADER_ROOT = ENV_TOKENS.get('GRADER_ROOT')

    SANDBOX_PYTHON = ENV_TOKENS.get('SANDBOX_PYTHON', '/opt/edx/bin/sandbox-python')

########NEW FILE########
__FILENAME__ = showhide
#!/usr/bin/python
#
# File:   tutor/tutor2/showhide.py
# Date:   22-Jul-11
# Author: I. Chuang <ichuang@mit.edu>
#
# python functions for providing HTML code for javascript show/hide div
#
# change this to use configuration variables, or read from template

def start(sid):
    return '<div id="DivPartHeader"><div id="DivPart%sTitle">' % str(sid)

def link(sid,display=False):
    if display:
        ls = '<img src="/tutorexport/images/minus.png"/>Hide'
    else:
        ls = '<img src="/tutorexport/images/plus.png"/>Show'
    return '<a id="DivLink%s" href="javascript:showhide(\'DivPartContent%s\',\'DivLink%s\');">%s</A></div></div>' % (str(sid),str(sid),str(sid),ls)

def content(sid,display=False):
    if display:
        ls  = 'block'
    else:
        ls = 'none'
    return '<div id="DivPartContent%s" style="display: %s;">' % (str(sid),ls)

def end(sid):
    return '</div>';

########NEW FILE########
__FILENAME__ = error
1/0

########NEW FILE########
__FILENAME__ = answer
print "hello world"

########NEW FILE########
__FILENAME__ = wrong
print "hello"

########NEW FILE########
__FILENAME__ = wrong2
import time
time.sleep(0.1)
print "hello"

########NEW FILE########
__FILENAME__ = hello
print "Hello, world!"

########NEW FILE########
__FILENAME__ = infinite
import time
while True:
 time.sleep(1)

########NEW FILE########
__FILENAME__ = answer
def isVowel(char):
    '''
    char: a single letter of any case

    returns: True if char is a vowel and False otherwise.
    '''
    if char == 'a' or char == 'e' or char == 'i' or char == 'o' or char == 'u':
        return True
    elif char == 'A' or char == 'E' or char == 'I' or char == 'O' or char == 'U':
        return True
    else:
        return False

########NEW FILE########
__FILENAME__ = test-runserver
#!/usr/bin/env python
"""
Send some test programs to an xserver.

For each dir in the current directory, send the contents of payload.xml and each
of the correct*.py and wrong*.py files.
"""

import argparse
import glob
import json
import logging
import os
import os.path
from path import path
import requests
import sys
import time
import random

logging.basicConfig(level=logging.DEBUG)

log = logging.getLogger(__name__)

runserver = 'http://127.0.0.1:3031/'

unique = str(random.randint(100000, 999999))

def upload(paths):
    """
    Given a list of paths, upload them to the sandbox, and return an id that
    identifies the created directory.
    """
    files = dict( (os.path.basename(f)+unique, open(f)) for f in paths)
    return upload_files(files)

def upload_files(files):
    endpoint = upload_server + 'upload'
    r = requests.post(endpoint, files=files)

    if r.status_code != requests.codes.ok:
        log.error("Request error: {0}".format(r.text))
        return None

    if r.json is None:
        log.error("sandbox50 /upload failed to return valid json.  Response:" +  r.text)
        return None

    id = r.json.get('id')
    log.debug('Upload_files response: ' + r.text)
    return id

def run(id, cmd):
    # Making run request

    headers = {'content-type': 'application/json'}
    run_args = {'cmd': cmd,
                'sandbox': { 'homedir': id }}

    endpoint = runserver + 'run'
    r = requests.post(endpoint, headers=headers, data=json.dumps(run_args))

    if r.json is None:
        log.error("sandbox50 /run failed to return valid json.  Response:" +  r.text)
        return None

    log.debug('run response: ' + r.text)
    return r.json

def main(args):
    global runserver
    global upload_server
    if len(args) < 4:
        print "Usage: test-runserver.py http://x-server-to-upload-to:port/ http://x-server-to-run-on:port/ FILES cmd"
        print "The first file in FILES will be randomized by appending a random string,"
        print "and the name of that file in 'cmd' will be modified the same way."
        sys.exit(1)

    upload_server = args[0]
    if not upload_server.endswith('/'):
        upload_server += '/'
    runserver = args[1]
    if not runserver.endswith('/'):
        runserver += '/'

    files = args[2:-1]
    cmd = args[-1]

    start = time.time()
    id = upload(files)
    print "Upload took %.03f sec" % (time.time() - start)
    
    start = time.time()
    cmd = cmd.replace(files[0], files[0]+unique)
    r = run(id, cmd)
    print "run took %.03f sec" % (time.time() - start)
    if r is None:
        print 'error'

if __name__=="__main__":
    main(sys.argv[1:])


########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
"""
Send some test programs to an xserver.

For each dir in the current directory, send the contents of payload.xml and each
of the answer*.py, right*.py and wrong*.py files.
"""

import argparse
import glob
import json
import os
import os.path
from path import path
import pprint
import requests
import sys
import time

xserver = 'http://127.0.0.1:3031/'

def send(payload, answer):
    """
    Send a grading request to the xserver
    """

    body = {'grader_payload': payload,
            'student_response': answer}

    data = {'xqueue_body': json.dumps(body),
            'xqueue_files': ''}

    start = time.time()
    r = requests.post(xserver, data=json.dumps(data))
    end = time.time()
    print "Request took %.03f sec" % (end - start)

    if r.status_code != requests.codes.ok:
        print "Request error"

    #print "Text: ", r.text
    return r.text


def check_output(data, verbose, expected_correct):
    try:
        d = json.loads(data)
        if d["correct"] != expected_correct:
            print "ERROR: expected correct={0}.  Message: {1}".format(
                expected_correct, pprint.pformat(d))

        elif verbose:
            print "Output: "
            pprint.pprint(d) 

    except ValueError:
        print "ERROR: invalid json %r" % data

def globs(dirname, *patterns):
    """
    Produce a sequence of all the files matching any of our patterns in dirname.
    """
    for pat in patterns:
        for fname in glob.glob(os.path.join(dirname, pat)):
            yield fname

def contents(fname):
    """
    Return the contents of the file `fname`.
    """
    with open(fname) as f:
        return f.read()

def check(dirname, verbose):
    """
    Look for payload.json, answer*.py, right*.py, wrong*.py, run tests.
    """
    payload_file = os.path.join(dirname, 'payload.json')
    if os.path.isfile(payload_file):
        payload = contents(payload_file)
    else:
        graders = list(globs(dirname, 'grade*.py'))
        if not graders:
            #print "No payload.json or grade*.py in {0}".format(dirname)
            return
        if len(graders) > 1:
            print "More than one grader in {0}".format(dirname)
            return
        # strip off everything up to and including graders/

        p = os.path.abspath(graders[0])
        index = p.find('graders/')
        if index < 0:
            #
            print ("{0} is not in the 6.00x graders dir, and there's no payload.json file"
                    ", so we don't know how to grade it".format(p))
            return
        else:
            grader_path = p[index + len('graders/'):]
            print 'grader_path: ' + grader_path
        payload = json.dumps({'grader': grader_path})

    for name in globs(dirname, 'answer*.py', 'right*.py'):
        print "Checking correct response from {0}".format(name)
        answer = contents(name)
        check_output(send(payload, answer), verbose, expected_correct=True)

    for name in globs(dirname, 'wrong*.py'):
        print "Checking wrong response from {0}".format(name)
        answer = contents(name)
        check_output(send(payload, answer), verbose, expected_correct=False)

def main(argv):
    global xserver

    parser = argparse.ArgumentParser(description="Send dummy requests to a qserver")
    parser.add_argument('server')
    parser.add_argument('root', nargs='?')
    parser.add_argument('-v', dest='verbose', action='store_true', help="verbose")

    args = parser.parse_args(argv)

    xserver = args.server
    if not xserver.endswith('/'):
        xserver += '/'

    root = args.root or '.'
    for dirpath, _, _ in os.walk(root):
        check(dirpath, args.verbose)

if __name__=="__main__":
    main(sys.argv[1:])

########NEW FILE########
