__FILENAME__ = gain_vis
#!/usr/bin/env python3

import time, json, threading, subprocess, queue, platform, os, sys
import numpy as np
from housepy import log, config, strings, net, s3, util, process, drawing
from scipy.io import wavfile

DURATION = 10
AUDIO_TMP = os.path.abspath(os.path.join(os.path.dirname(__file__), "audio_tmp"))

t = sys.argv[1]

filename = "%s/%s.wav" % (AUDIO_TMP, t)
sample_rate, signal = wavfile.read(filename)
log.debug("samples %s" % len(signal))
log.debug("sample_rate %s" % sample_rate)
duration = float(len(signal)) / sample_rate
log.debug("duration %ss" % strings.format_time(duration))
signal = (np.array(signal).astype('float') / (2**16 * 0.5))   # assuming 16-bit PCM, -1 - 1
signal = abs(signal)    # magnitude

ctx = drawing.Context()
ctx.plot(signal)
ctx.line(0, config['noise_threshold'], 1, config['noise_threshold'], stroke=(255, 0, 0))
ctx.output("screenshots")

log.debug("noise threshold is %s" % config['noise_threshold'])
log.debug("found magnitude")
content_samples = 0
for sample in signal:
    if sample > config['noise_threshold']:
        content_samples += 1
total_content_time = float(content_samples) / sample_rate
log.info("total_content_time %s" % total_content_time)


########NEW FILE########
__FILENAME__ = mturkcore
"""
Copyright (c) 2013 Fredrick R Brennan, mturkconsultant.com. Licensed under the Apache License, Version 2.0 (the "License"); you may not use this software except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
"""
# http://mturkconsultant.com/blog/index.php/2013/01/my-python-mechanical-turk-api-mturkcore-py/
# modified for Python 3 and housepy integration

import time
import hmac
import hashlib
import base64
import json
import requests
import logging
import xmltodict
import collections
import re
from datetime import datetime
from housepy import config, log

#Convenient flags for qualification types.
P_SUBMITTED = "00000000000000000000"
P_ABANDONED = "00000000000000000070"
P_RETURNED = "000000000000000000E0"
P_APPROVED = "000000000000000000L0"
P_REJECTED = "000000000000000000S0"
N_APPROVED = "00000000000000000040"
LOCALE = "00000000000000000071"
ADULT = "00000000000000000060"

class MechanicalTurk(object):
    """The main class. Initialize this class with a valid Python dictionary passed as a string containing properties that mTurk needs to carry out your request. These are use_sandbox, stdout_log [useful to see the request and reply], AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY."""
    def __init__(self,mturk_config_dict=None):
        """Try to set config variables with a file called 'mturkconfig.json' if no argument is passed to the class instance. Else get our config from the argument passed."""
        if mturk_config_dict is None:
            mturk_config_dict = config['mturk']
        if 'stdout_log' not in mturk_config_dict:
            logging.getLogger('requests').setLevel(logging.WARNING)
        self.sandbox = mturk_config_dict["use_sandbox"] # Use sandbox?
        self.aws_key = mturk_config_dict["access_key_id"]
        self.aws_secret_key = mturk_config_dict["secret_access_key"]

    def _generate_timestamp(self, gmtime):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", gmtime)

    def _generate_signature(self, service, operation, timestamp, secret_access_key):
        my_sha_hmac = hmac.new(secret_access_key.encode('utf-8'), ("%s%s%s" % (service, operation, timestamp)).encode('utf-8'), hashlib.sha1)
        my_b64_hmac_digest = base64.encodestring(my_sha_hmac.digest()).strip().decode('utf-8')
        return my_b64_hmac_digest

    def _flatten(self, obj, inner=False):
        if isinstance(obj, str):
            return {"": obj}
        elif isinstance(obj, collections.Mapping):
            if inner: obj.update({'':''})
            iterable = list(obj.items())
        elif isinstance(obj, collections.Iterable):
            iterable = enumerate(obj, start=1)
        else:  
            return {"": obj}
        rv = {}
        for key, value in iterable:
            for inner_key, inner_value in list(self._flatten(value, inner=True).items()):
                rv.update({("{}.{}" if inner_key else "{}{}").format(key, inner_key): inner_value})
        return rv

    def _find_item(self, obj, key):
        if key in obj: return obj[key]
        for k, v in list(obj.items()):
            if isinstance(v, dict):
                item = self._find_item(v, key)
                if item is not None:
                    return item

    def create_request(self, operation, request_parameters={}):
        """Create a Mechanical Turk client request. Unlike other libraries (thankfully), my help ends here. You can pass the operation (view the list here: http://docs.amazonwebservices.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_OperationsArticle.html) as parameter one, and a dictionary of arguments as parameter two. To send multiple of the same argument (for instance, multiple workers to notify in NotifyWorkers), you can send a list."""
        self.operation = operation
        if self.sandbox:
            self.service_url = 'https://mechanicalturk.sandbox.amazonaws.com/?Service=AWSMechanicalTurkRequester'
        else:
            self.service_url = 'https://mechanicalturk.amazonaws.com/?Service=AWSMechanicalTurkRequester'
        # create the operation signature
        timestamp = self._generate_timestamp(time.gmtime())
        signature = self._generate_signature('AWSMechanicalTurkRequester', operation, timestamp, self.aws_secret_key)
        # Add common parameters to request dict
        request_parameters.update({"Operation": operation, "Version": "2012-03-25", "AWSAccessKeyId": self.aws_key, "Signature": signature, "Timestamp": timestamp})
        self.flattened_parameters = self._flatten(request_parameters)
        request = requests.get(self.service_url, params=self.flattened_parameters)
        request.encoding = 'utf-8'
        self.xml_response = request.text # Store XML response, might need it        
        self.response = xmltodict.parse(self.xml_response.encode('utf-8'))
        return self.response

    def get_response_element(self, element, response=None):
        if response is None:
            response = self.response
        return self._find_item(response, element)   

    def is_valid(self, response=None):
        """Convenience function to figure out if the last request we made was valid."""
        if response is None:
            response = self.response
        try:
            return self.get_response_element("Request", response=response)["IsValid"] == "True"
        except Exception as e:
            log.error(response)
            return False


########NEW FILE########
__FILENAME__ = main_raspi
#!/usr/bin/env python3

import time, json, threading, subprocess, queue, platform, os
import numpy as np
from housepy import log, config, strings, net, s3, util, process
from scipy.io import wavfile

DURATION = 10
AUDIO_TMP = os.path.abspath(os.path.join(os.path.dirname(__file__), "audio_tmp"))

process.secure_pid(os.path.abspath(os.path.join(os.path.dirname(__file__), "run")))

class Recorder(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.out_queue = queue.Queue()
        self.start() 

    def run(self):
        while True:
            t = util.timestamp()
            log.info("record %s" % t)
            try:
                command = "/usr/bin/arecord -D plughw:1,0 -d %s -f S16_LE -c1 -r11025 -t wav %s/%s.wav" % (DURATION, AUDIO_TMP, t)  # 10s of mono 11k PCM
                log.info("%s" % command)
                subprocess.check_call(command, shell=True)    
            except Exception as e:
                log.error(log.exc(e))
                time.sleep(DURATION)
                continue
            log.info("--> wrote audio_tmp/%s.wav" % t)
            self.out_queue.put(t)


class Processor(threading.Thread):

    def __init__(self, recorder_queue):
        threading.Thread.__init__(self)
        self.daemon = True
        self.in_queue = recorder_queue
        self.out_queue = queue.Queue()
        self.start()

    def run(self):
        while True:
            t = self.in_queue.get()
            self.process(t)

    def process(self, t):
        log.info("process %s" % t)        
        try:
            filename = "%s/%s.wav" % (AUDIO_TMP, t)
            sample_rate, signal = wavfile.read(filename)
            # log.debug("samples %s" % len(signal))
            # log.debug("sample_rate %s" % sample_rate)
            duration = float(len(signal)) / sample_rate
            # log.debug("duration %ss" % strings.format_time(duration))
            signal = (np.array(signal).astype('float') / (2**16 * 0.5))   # assuming 16-bit PCM, -1 - 1
            signal = abs(signal)    # magnitude
            # log.debug("found magnitude")
            content_samples = 0
            for sample in signal:
                if sample > config['noise_threshold']:
                    content_samples += 1
            total_content_time = float(content_samples) / sample_rate
            log.info("--> %s total_content_time %s" % (t, total_content_time))
            if total_content_time > config['time_threshold']:                
                self.out_queue.put((t, filename))
                log.info("--> %s added to upload queue" % t)
            else:
                os.remove(filename)
                log.info("--> %s deleted" % t)
        except Exception as e:
            log.error(log.exc(e))


class Uploader(threading.Thread):

    def __init__(self, processor_queue):
        threading.Thread.__init__(self)
        self.daemon = True
        self.in_queue = processor_queue
        self.start()

    def run(self):
        while True:
            t, filename = self.in_queue.get()
            self.upload(t, filename)

    def upload(self, t, filename):      
        log.info("upload %s" % filename)          
        try:
            s3.upload(filename)
            log.info("--> uploaded. Pinging server...")
            data = {'t': t}
            response = net.read("http://%s:%s" % (config['server']['host'], config['server']['port']), json.dumps(data).encode('utf-8'))
            log.info(response)
            os.remove(filename)
        except Exception as e:
            log.error(log.exc(e))




recorder = Recorder()
processor = Processor(recorder.out_queue)
uploader = Uploader(processor.out_queue)
while True:
    time.sleep(0.1)


########NEW FILE########
__FILENAME__ = main_server
#!/usr/bin/env python3

import datetime, pytz, model, os, json, mturk, tweet_sender
from housepy import config, log, server, util, process

process.secure_pid(os.path.abspath(os.path.join(os.path.dirname(__file__), "run")))

ts = tweet_sender.TweetSender()


class Home(server.Handler):
    
    def get(self, page=None):
        if page == config['sendpw']:
            message = '"%s"' % self.get_argument('message').strip('"')[:138]
            ts.queue.put(message)
            log.info("remote: %s" % message)
            return self.text("OK")
        if not len(page):            
            return self.text("OK")    
        return self.not_found()

    def post(self, nop=None):
        log.info("Home.post")
        try:
            data = json.loads(self.request.body.decode('utf-8'))
            hit_id = mturk.create_hit("https://s3.amazonaws.com/%s/%s.wav" % (config['s3']['bucket'], data['t']))
            if hit_id != False:
                model.add_clip(data['t'], hit_id)
        except Exception as e:
            return self.error(e)
        return self.text("OK")


handlers = [
    (r"/?([^/]*)", Home),
]    

server.start(handlers)

########NEW FILE########
__FILENAME__ = main_twitter
#!/usr/bin/env python3

import model, mturk, tweet_sender, time, os
from housepy import config, log, process, util

ts = tweet_sender.TweetSender()

process.secure_pid(os.path.abspath(os.path.join(os.path.dirname(__file__), "run")))

while True:
    log.info("//////////")
    clips = model.get_recent()
    log.info("%s recent clips" % len(clips))
    for clip in clips:
        log.info("Checking %s %s %s" % (clip['t'], clip['hit_id'], util.datestring(clip['t'])))
        struct = mturk.retrieve_result(clip['hit_id'])   
        if struct is None:
            continue
        model.mark_clip(clip['t'])                        
        if 'nospeech' in struct and struct['nospeech'] == 'on':
            log.info("--> no speech in clip")
            continue
        try:
            for label in ('line_1', 'line_2', 'line_3'):
                if label in struct and len(struct[label]):
                    message = '"%s"' % struct[label].strip('"')[:138]
                    ts.queue.put(message)
        except Exception as e:
            log.error(log.exc(e))
            continue        
    time.sleep(30)


########NEW FILE########
__FILENAME__ = model
#!/usr/bin/env python3

import sqlite3, json, time, sys, os
from housepy import config, log, util

connection = sqlite3.connect(os.path.abspath(os.path.join(os.path.dirname(__file__), "data.db")))
connection.row_factory = sqlite3.Row
db = connection.cursor()

def init():
    try:
        db.execute("CREATE TABLE IF NOT EXISTS clips (t INTEGER, hit_id TEXT, posted INTEGER)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS clips_t ON clips(t)")
    except Exception as e:
        log.error(log.exc(e))
        return
    connection.commit()
init()

def add_clip(t, hit_id):
    try:
        db.execute("INSERT INTO clips (t, hit_id, posted) VALUES (?, ?, 0)", (t, hit_id))
    except Exception as e:
        log.error(log.exc(e))
        return
    log.info("Added clip %s %s" % (t, hit_id))
    connection.commit()

def get_recent():
    t = util.timestamp()
    db.execute("SELECT * FROM clips WHERE t>=? AND posted=0", (t - config['lag'],))
    clips = [dict(clip) for clip in db.fetchall()]
    return clips

def mark_clip(t):
    log.info("Marking clip %s" % t)
    try:
        db.execute("UPDATE clips SET posted=1 WHERE t=?", (t,))
    except Exception as e:
        log.error(log.exc(e))
        return
    connection.commit()

########NEW FILE########
__FILENAME__ = mturk
#!/usr/bin/env python3

import json, xmltodict
from housepy import config, log, util, strings
from lib import mturkcore

m = mturkcore.MechanicalTurk()

def create_hit(link):
    log.info("Creating HIT...")
    response = m.create_request('CreateHIT', {  'Title': "Transcribe 10 seconds of audio (WARNING: This HIT may contain adult content. Worker discretion is advised.)",
                                                'Description': "Listen to a 10 second audio clip and transcribe what is said.",
                                                'Reward': {'Amount': config['mturk']['payout'], 'CurrencyCode': "USD"},
                                                'AssignmentDurationInSeconds': config['lag'],
                                                'LifetimeInSeconds': config['lag'],
                                                'HITLayoutId': config['mturk']['layout_id'], 
                                                'HITLayoutParameter': {'Name': "link", 'Value': link},
                                                'AutoApprovalDelayInSeconds': 3600,
                                                })
    if not m.is_valid():
        log.error("--> failed: %s" % json.dumps(response, indent=4))
        return False
    try:
        hit_id = response['CreateHITResponse']['HIT']['HITId']
        log.info("--> created HIT %s" % hit_id)
        return hit_id
    except Exception as e:
        log.error(log.exc(e))
        return False


def retrieve_result(hit_id):
    response = m.create_request('GetAssignmentsForHIT', {'HITId': hit_id})
    if not m.is_valid():
        log.error("Request failed: %s" % response)
        return None
    try:
        answer = response['GetAssignmentsForHITResponse']['GetAssignmentsForHITResult']        
        if 'Assignment' not in answer:
            log.info("--> not answered yet")
            return None
        answer = xmltodict.parse(answer['Assignment']['Answer'])
        answer = answer['QuestionFormAnswers']['Answer']
        struct = {}
        for part in answer:
            if part['FreeText'] is None:
                continue
            struct[part['QuestionIdentifier']] = part['FreeText'].strip().replace("&#13;", "").replace("&lt;", "<").replace("&gt;", ">")
        return struct
    except Exception as e:
        log.error("Response malformed: (%s) %s" % (log.exc(e), json.dumps(response, indent=4)))
        return None


if __name__ == "__main__":
    pass
    # import model
    # hit_id = create_hit("http://google.com")
    # model.add_clip(util.timestamp(), hit_id)
    # print(hit_id)
    # struct = retrieve_result("2YYYQ4J3NAB9ZQFXU3PYLT1TUPMQD3")
    # print(struct)


"""
{
    "CreateHITResponse": {
        "OperationRequest": {
            "RequestId": "38c6e751-ce27-4126-8d97-0a7202d35905"
        }, 
        "HIT": {
            "Request": {
                "IsValid": "True"
            }, 
            "HITId": "2ACHYW2GTP9RA5UWMPS6CYSOP30SN4", 
            "HITTypeId": "2IIC6SK9RJ85OXKQ4KDADPMOOE64S7"
        }
    }
}

{
    "GetAssignmentsForHITResponse": {
        "OperationRequest": {
            "RequestId": "8b22554e-386c-4297-81f2-3e8ded87f40f"
        }, 
        "GetAssignmentsForHITResult": {
            "Request": {
                "IsValid": "True"
            }, 
            "NumResults": "1", 
            "TotalNumResults": "1", 
            "PageNumber": "1", 
            "Assignment": {
                "AssignmentId": "2DGH1XERSQV66PNG7LK3KVWAW1G08S", 
                "WorkerId": "A2TM28MRAA0LLD", 
                "HITId": "2ACHYW2GTP9RA5UWMPS6CYSOP30SN4", 
                "AssignmentStatus": "Submitted", 
                "AutoApprovalTime": "2013-10-18T04:22:35Z", 
                "AcceptTime": "2013-09-18T04:22:27Z", 
                "SubmitTime": "2013-09-18T04:22:35Z", 
                "Answer": "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"no\"?>\n<QuestionFormAnswers xmlns=\"http://mechanicalturk.amazonaws.com/AWSMechanicalTurkDataSchemas/2005-10-01/QuestionFormAnswers.xsd\">\n<Answer>\n<QuestionIdentifier>summary</QuestionIdentifier>\n<FreeText>This is my transcription, which involves elephants and shaving cream.</FreeText>\n</Answer>\n</QuestionFormAnswers>"
            }
        }
    }
}


"""


########NEW FILE########
__FILENAME__ = tweeter
#!/usr/bin/env python3

import tweet_sender, time, os, sys


message = sys.argv[1]
message = '"%s"' % message.strip('"')[:138]
print(message)

ts = tweet_sender.TweetSender()
ts.queue.put(message)

time.sleep(3)




########NEW FILE########
__FILENAME__ = tweet_sender
import threading, queue, time, twitter
from housepy import config, log


class TweetSender(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.queue = queue.Queue()
        self.sender = twitter.Twitter(auth=twitter.OAuth(   config['twitter']['access_token'], 
                                                            config['twitter']['access_token_secret'], 
                                                            config['twitter']['consumer_key'], 
                                                            config['twitter']['consumer_secret']
                                                        ))        
        self.start()        


    def run(self):
        while True:
            message = self.queue.get()[:140]
            log.info("SENDING TWEET: %s" % message)
            try:
                self.sender.statuses.update(status=message)
            except Exception as e:
                log.error(log.exc(e))
            else:
                log.info("--> sent")


if __name__ == "__main__":
    tweet_sender = TweetSender()
    tweet_sender.queue.put("A message")
    while True:
        time.sleep(1)
########NEW FILE########
