__FILENAME__ = boot
#!/usr/bin/env python

import os, json
import urllib2
import yaml

import vocabcompiler

def say(phrase, OPTIONS = " -vdefault+m3 -p 40 -s 160 --stdout > say.wav"):
    os.system("espeak " + json.dumps(phrase) + OPTIONS)
    os.system("aplay -D hw:1,0 say.wav")

def configure():
    try:
        urllib2.urlopen("http://www.google.com").getcode()

        print "CONNECTED TO INTERNET"
        print "COMPILING DICTIONARY"
        vocabcompiler.compile("../client/sentences.txt", "../client/dictionary.dic", "../client/languagemodel.lm")

        print "STARTING CLIENT PROGRAM"
        os.system("/home/pi/jasper/client/start.sh &")
        
    except:
        
        print "COULD NOT CONNECT TO NETWORK"
        say("Hello, I could not connect to a network. Please read the documentation to configure your Raspberry Pi.")
        os.system("sudo shutdown -r now")

if __name__ == "__main__":
    print "==========STARTING JASPER CLIENT=========="
    print "=========================================="
    print "COPYRIGHT 2013 SHUBHRO SAHA, CHARLIE MARSH"
    print "=========================================="
    say("Hello.... I am Jasper... Please wait one moment.")
    configure()

########NEW FILE########
__FILENAME__ = test
import os
import sys
import unittest
from mock import patch
import vocabcompiler

lib_path = os.path.abspath('../client')
mod_path = os.path.abspath('../client/modules/')

sys.path.append(lib_path)
sys.path.append(mod_path)

import g2p


class TestVocabCompiler(unittest.TestCase):

    def testWordExtraction(self):
        sentences = "temp_sentences.txt"
        dictionary = "temp_dictionary.dic"
        languagemodel = "temp_languagemodel.lm"

        words = [
            'HACKER', 'LIFE', 'FACEBOOK', 'THIRD', 'NO', 'JOKE',
            'NOTIFICATION', 'MEANING', 'TIME', 'TODAY', 'SECOND',
            'BIRTHDAY', 'KNOCK KNOCK', 'INBOX', 'OF', 'NEWS', 'YES',
            'TOMORROW', 'EMAIL', 'WEATHER', 'FIRST', 'MUSIC', 'SPOTIFY'
        ]

        with patch.object(g2p, 'translateWords') as translateWords:
            with patch.object(vocabcompiler, 'text2lm') as text2lm:
                vocabcompiler.compile(sentences, dictionary, languagemodel)

                # 'words' is appended with ['MUSIC', 'SPOTIFY']
                # so must be > 2 to have received WORDS from modules
                translateWords.assert_called_once_with(words)
                self.assertTrue(text2lm.called)
        os.remove(sentences)
        os.remove(dictionary)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = vocabcompiler
"""
    Iterates over all the WORDS variables in the modules and creates a dictionary for the client.
"""

import os
import sys
import glob

lib_path = os.path.abspath('../client')
mod_path = os.path.abspath('../client/modules/')

sys.path.append(lib_path)
sys.path.append(mod_path)

import g2p


def text2lm(in_filename, out_filename):
    """Wrapper around the language model compilation tools"""
    def text2idngram(in_filename, out_filename):
        cmd = "text2idngram -vocab %s < %s -idngram temp.idngram" % (out_filename,
                                                                     in_filename)
        os.system(cmd)

    def idngram2lm(in_filename, out_filename):
        cmd = "idngram2lm -idngram temp.idngram -vocab %s -arpa %s" % (
            in_filename, out_filename)
        os.system(cmd)

    text2idngram(in_filename, in_filename)
    idngram2lm(in_filename, out_filename)


def compile(sentences, dictionary, languagemodel):
    """
        Gets the words and creates the dictionary
    """

    m = [os.path.basename(f)[:-3]
         for f in glob.glob(os.path.dirname("../client/modules/") + "/*.py")]

    words = []
    for module_name in m:
        try:
            exec("import %s" % module_name)
            eval("words.extend(%s.WORDS)" % module_name)
        except:
            pass  # module probably doesn't have the property

    words = list(set(words))

    # for spotify module
    words.extend(["MUSIC", "SPOTIFY"])

    # create the dictionary
    pronounced = g2p.translateWords(words)
    zipped = zip(words, pronounced)
    lines = ["%s %s" % (x, y) for x, y in zipped]

    with open(dictionary, "w") as f:
        f.write("\n".join(lines) + "\n")

    # create the language model
    with open(sentences, "w") as f:
        f.write("\n".join(words) + "\n")
        f.write("<s> \n </s> \n")
        f.close()

    # make language model
    text2lm(sentences, languagemodel)

########NEW FILE########
__FILENAME__ = alteration
import re


def detectYears(input):
    YEAR_REGEX = re.compile(r'(\b)(\d\d)([1-9]\d)(\b)')
    return YEAR_REGEX.sub('\g<1>\g<2> \g<3>\g<4>', input)


def clean(input):
    """
        Manually adjust output text before it's translated into
        actual speech by the TTS system. This is to fix minior
        idiomatic issues, for example, that 1901 is pronounced
        "one thousand, ninehundred and one" rather than
        "nineteen ninety one".

        Arguments:
        input -- original speech text to-be modified
    """
    return detectYears(input)

########NEW FILE########
__FILENAME__ = brain
import logging
from os import listdir


def logError():
    logger = logging.getLogger('jasper')
    fh = logging.FileHandler('jasper.log')
    fh.setLevel(logging.WARNING)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.error('Failed to execute module', exc_info=True)


class Brain(object):

    def __init__(self, mic, profile):
        """
        Instantiates a new Brain object, which cross-references user
        input with a list of modules. Note that the order of brain.modules
        matters, as the Brain will cease execution on the first module
        that accepts a given input.

        Arguments:
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
        """

        def get_modules():
            """
            Dynamically loads all the modules in the modules folder and sorts
            them by the PRIORITY key. If no PRIORITY is defined for a given
            module, a priority of 0 is assumed.
            """

            folder = 'modules'

            def get_module_names():
                module_names = [m.replace('.py', '')
                                for m in listdir(folder) if m.endswith('.py')]
                module_names = map(lambda s: folder + '.' + s, module_names)
                return module_names

            def import_module(name):
                mod = __import__(name)
                components = name.split('.')
                for comp in components[1:]:
                    mod = getattr(mod, comp)
                return mod

            def get_module_priority(m):
                try:
                    return m.PRIORITY
                except:
                    return 0

            modules = map(import_module, get_module_names())
            modules = filter(lambda m: hasattr(m, 'WORDS'), modules)
            modules.sort(key=get_module_priority, reverse=True)
            return modules

        self.mic = mic
        self.profile = profile
        self.modules = get_modules()

    def query(self, text):
        """
        Passes user input to the appropriate module, testing it against
        each candidate module's isValid function.

        Arguments:
        text -- user input, typically speech, to be parsed by a module
        """
        for module in self.modules:
            if module.isValid(text):

                try:
                    module.handle(text, self.mic, self.profile)
                    break
                except:
                    logError()
                    self.mic.say(
                        "I'm sorry. I had some trouble with that operation. Please try again later.")
                    break

########NEW FILE########
__FILENAME__ = conversation
from notifier import Notifier
from musicmode import *
from brain import Brain
from mpd import MPDClient

class Conversation(object):

    def __init__(self, persona, mic, profile):
        self.persona = persona
        self.mic = mic
        self.profile = profile
        self.brain = Brain(mic, profile)
        self.notifier = Notifier(profile)

    def delegateInput(self, text):
        """A wrapper for querying brain."""

        # check if input is meant to start the music module
        if any(x in text.upper() for x in ["SPOTIFY","MUSIC"]):
            # check if mpd client is running
            try:
                client = MPDClient()
                client.timeout = None
                client.idletimeout = None
                client.connect("localhost", 6600)
            except:
                self.mic.say("I'm sorry. It seems that Spotify is not enabled. Please read the documentation to learn how to configure Spotify.")
                return
            
            self.mic.say("Please give me a moment, I'm loading your Spotify playlists.")
            music_mode = MusicMode(self.persona, self.mic)
            music_mode.handleForever()
            return


        self.brain.query(text)

    def handleForever(self):
        """Delegates user input to the handling function when activated."""
        while True:

            # Print notifications until empty
            notifications = self.notifier.getAllNotifications()
            for notif in notifications:
                print notif

            try:
                threshold, transcribed = self.mic.passiveListen(self.persona)
            except:
                continue

            if threshold:
                input = self.mic.activeListen(threshold)
                if input:
                    self.delegateInput(input)
                else:
                    self.mic.say("Pardon?")

########NEW FILE########
__FILENAME__ = g2p
import os
import subprocess
import re

TEMP_FILENAME = "g2ptemp"
PHONE_MATCH = re.compile(r'<s> (.*) </s>')


def parseLine(line):
    return PHONE_MATCH.search(line).group(1)


def parseOutput(output):
    return PHONE_MATCH.findall(output)


def translateWord(word):
    out = subprocess.check_output(['phonetisaurus-g2p', '--model=%s' %
                                  os.path.expanduser("~/phonetisaurus/g014b2b.fst"), '--input=%s' % word])
    return parseLine(out)


def translateWords(words):
    full_text = '\n'.join(words)

    f = open(TEMP_FILENAME, "wb")
    f.write(full_text)
    f.flush()

    output = translateFile(TEMP_FILENAME)
    os.remove(TEMP_FILENAME)

    return output


def translateFile(input_filename, output_filename=None):
    out = subprocess.check_output(['phonetisaurus-g2p', '--model=%s' % os.path.expanduser(
        "~/phonetisaurus/g014b2b.fst"), '--input=%s' % input_filename, '--words', '--isfile'])
    out = parseOutput(out)

    if output_filename:
        out = '\n'.join(out)

        f = open(output_filename, "wb")
        f.write(out)
        f.close()

        return None

    return out

if __name__ == "__main__":

    translateFile(os.path.expanduser("~/phonetisaurus/sentences.txt"),
                  os.path.expanduser("~/phonetisaurus/dictionary.dic"))

########NEW FILE########
__FILENAME__ = local_mic
"""
A drop-in replacement for the Mic class that allows for all I/O to occur
over the terminal. Useful for debugging. Unlike with the typical Mic
implementation, Jasper is always active listening with local_mic.
"""


class Mic:
    prev = None

    def __init__(self, lmd, dictd, lmd_persona, dictd_persona):
        return

    def passiveListen(self, PERSONA):
        return True, "JASPER"

    def activeListen(self, THRESHOLD=None, LISTEN=True, MUSIC=False):
        if not LISTEN:
            return self.prev

        input = raw_input("YOU: ")
        self.prev = input
        return input

    def say(self, phrase, OPTIONS=None):
        print "JASPER: " + phrase

########NEW FILE########
__FILENAME__ = main
import yaml
import sys
from conversation import Conversation


def isLocal():
    return len(sys.argv) > 1 and sys.argv[1] == "--local"

if isLocal():
    from local_mic import Mic
else:
    from mic import Mic

if __name__ == "__main__":

    print "==========================================================="
    print " JASPER The Talking Computer                               "
    print " Copyright 2013 Shubhro Saha & Charlie Marsh               "
    print "==========================================================="

    profile = yaml.safe_load(open("profile.yml", "r"))

    mic = Mic("languagemodel.lm", "dictionary.dic",
              "languagemodel_persona.lm", "dictionary_persona.dic")

    mic.say("How can I be of service?")

    conversation = Conversation("JASPER", mic, profile)

    conversation.handleForever()

########NEW FILE########
__FILENAME__ = mic
"""
    The Mic class handles all interactions with the microphone and speaker.
"""

import os
import json
from wave import open as open_audio
import audioop
import pyaudio
import alteration


# quirky bug where first import doesn't work
try:
    import pocketsphinx as ps
except:
    import pocketsphinx as ps


class Mic:

    speechRec = None
    speechRec_persona = None

    def __init__(self, lmd, dictd, lmd_persona, dictd_persona, lmd_music=None, dictd_music=None):
        """
            Initiates the pocketsphinx instance.

            Arguments:
            lmd -- filename of the full language model
            dictd -- filename of the full dictionary (.dic)
            lmd_persona -- filename of the 'Persona' language model (containing, e.g., 'Jasper')
            dictd_persona -- filename of the 'Persona' dictionary (.dic)
        """

        hmdir = "/usr/local/share/pocketsphinx/model/hmm/en_US/hub4wsj_sc_8k"

        if lmd_music and dictd_music:
            self.speechRec_music = ps.Decoder(hmm = hmdir, lm = lmd_music, dict = dictd_music)
        self.speechRec_persona = ps.Decoder(
            hmm=hmdir, lm=lmd_persona, dict=dictd_persona)
        self.speechRec = ps.Decoder(hmm=hmdir, lm=lmd, dict=dictd)

    def transcribe(self, audio_file_path, PERSONA_ONLY=False, MUSIC=False):
        """
            Performs TTS, transcribing an audio file and returning the result.

            Arguments:
            audio_file_path -- the path to the audio file to-be transcribed
            PERSONA_ONLY -- if True, uses the 'Persona' language model and dictionary
            MUSIC -- if True, uses the 'Music' language model and dictionary
        """

        wavFile = file(audio_file_path, 'rb')
        wavFile.seek(44)

        if MUSIC:
            self.speechRec_music.decode_raw(wavFile)
            result = self.speechRec_music.get_hyp()
        elif PERSONA_ONLY:
            self.speechRec_persona.decode_raw(wavFile)
            result = self.speechRec_persona.get_hyp()
        else:
            self.speechRec.decode_raw(wavFile)
            result = self.speechRec.get_hyp()

        print "==================="
        print "JASPER: " + result[0]
        print "==================="

        return result[0]

    def getScore(self, data):
        rms = audioop.rms(data, 2)
        score = rms / 3
        return score

    def fetchThreshold(self):

        # TODO: Consolidate all of these variables from the next three
        # functions
        THRESHOLD_MULTIPLIER = 1.8
        AUDIO_FILE = "passive.wav"
        RATE = 16000
        CHUNK = 1024

        # number of seconds to allow to establish threshold
        THRESHOLD_TIME = 1

        # number of seconds to listen before forcing restart
        LISTEN_TIME = 10

        # prepare recording stream
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

        # stores the audio data
        frames = []

        # stores the lastN score values
        lastN = [i for i in range(20)]

        # calculate the long run average, and thereby the proper threshold
        for i in range(0, RATE / CHUNK * THRESHOLD_TIME):

            data = stream.read(CHUNK)
            frames.append(data)

            # save this data point as a score
            lastN.pop(0)
            lastN.append(self.getScore(data))
            average = sum(lastN) / len(lastN)

        # this will be the benchmark to cause a disturbance over!
        THRESHOLD = average * THRESHOLD_MULTIPLIER

        return THRESHOLD

    def passiveListen(self, PERSONA):
        """
            Listens for PERSONA in everyday sound
            Times out after LISTEN_TIME, so needs to be restarted
        """

        THRESHOLD_MULTIPLIER = 1.8
        AUDIO_FILE = "passive.wav"
        RATE = 16000
        CHUNK = 1024

        # number of seconds to allow to establish threshold
        THRESHOLD_TIME = 1

        # number of seconds to listen before forcing restart
        LISTEN_TIME = 10

        # prepare recording stream
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

        # stores the audio data
        frames = []

        # stores the lastN score values
        lastN = [i for i in range(30)]

        # calculate the long run average, and thereby the proper threshold
        for i in range(0, RATE / CHUNK * THRESHOLD_TIME):

            data = stream.read(CHUNK)
            frames.append(data)

            # save this data point as a score
            lastN.pop(0)
            lastN.append(self.getScore(data))
            average = sum(lastN) / len(lastN)

        # this will be the benchmark to cause a disturbance over!
        THRESHOLD = average * THRESHOLD_MULTIPLIER

        # save some memory for sound data
        frames = []

        # flag raised when sound disturbance detected
        didDetect = False

        # start passively listening for disturbance above threshold
        for i in range(0, RATE / CHUNK * LISTEN_TIME):

            data = stream.read(CHUNK)
            frames.append(data)
            score = self.getScore(data)

            if score > THRESHOLD:
                didDetect = True
                break

        # no use continuing if no flag raised
        if not didDetect:
            print "No disturbance detected"
            return

        # cutoff any recording before this disturbance was detected
        frames = frames[-20:]

        # otherwise, let's keep recording for few seconds and save the file
        DELAY_MULTIPLIER = 1
        for i in range(0, RATE / CHUNK * DELAY_MULTIPLIER):

            data = stream.read(CHUNK)
            frames.append(data)

        # save the audio data
        stream.stop_stream()
        stream.close()
        audio.terminate()
        write_frames = open_audio(AUDIO_FILE, 'wb')
        write_frames.setnchannels(1)
        write_frames.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        write_frames.setframerate(RATE)
        write_frames.writeframes(''.join(frames))
        write_frames.close()

        # check if PERSONA was said
        transcribed = self.transcribe(AUDIO_FILE, PERSONA_ONLY=True)

        if PERSONA in transcribed:
            return (THRESHOLD, PERSONA)

        return (False, transcribed)

    def activeListen(self, THRESHOLD=None, LISTEN=True, MUSIC=False):
        """
            Records until a second of silence or times out after 12 seconds
        """

        AUDIO_FILE = "active.wav"
        RATE = 16000
        CHUNK = 1024
        LISTEN_TIME = 12

        # user can request pre-recorded sound
        if not LISTEN:
            if not os.path.exists(AUDIO_FILE):
                return None

            return self.transcribe(AUDIO_FILE)

        # check if no threshold provided
        if THRESHOLD == None:
            THRESHOLD = self.fetchThreshold()

        os.system("aplay -D hw:1,0 beep_hi.wav")

        # prepare recording stream
        audio = pyaudio.PyAudio()
        stream = audio.open(format=pyaudio.paInt16,
                            channels=1,
                            rate=RATE,
                            input=True,
                            frames_per_buffer=CHUNK)

        frames = []
        # increasing the range # results in longer pause after command
        # generation
        lastN = [THRESHOLD * 1.2 for i in range(30)]

        for i in range(0, RATE / CHUNK * LISTEN_TIME):

            data = stream.read(CHUNK)
            frames.append(data)
            score = self.getScore(data)

            lastN.pop(0)
            lastN.append(score)

            average = sum(lastN) / float(len(lastN))

            # TODO: 0.8 should not be a MAGIC NUMBER!
            if average < THRESHOLD * 0.8:
                break

        os.system("aplay -D hw:1,0 beep_lo.wav")

        # save the audio data
        stream.stop_stream()
        stream.close()
        audio.terminate()
        write_frames = open_audio(AUDIO_FILE, 'wb')
        write_frames.setnchannels(1)
        write_frames.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
        write_frames.setframerate(RATE)
        write_frames.writeframes(''.join(frames))
        write_frames.close()

        # DO SOME AMPLIFICATION
        # os.system("sox "+AUDIO_FILE+" temp.wav vol 20dB")

        if MUSIC:
            return self.transcribe(AUDIO_FILE, MUSIC=True)

        return self.transcribe(AUDIO_FILE)
        
    def say(self, phrase, OPTIONS=" -vdefault+m3 -p 40 -s 160 --stdout > say.wav"):
        # alter phrase before speaking
        phrase = alteration.clean(phrase)

        os.system("espeak " + json.dumps(phrase) + OPTIONS)
        os.system("aplay -D hw:1,0 say.wav")

########NEW FILE########
__FILENAME__ = app_utils
import smtplib
from email.MIMEText import MIMEText
import urllib2
import re
import requests
from pytz import timezone


def sendEmail(SUBJECT, BODY, TO, FROM, SENDER, PASSWORD, SMTP_SERVER):
    """Sends an HTML email."""
    for body_charset in 'US-ASCII', 'ISO-8859-1', 'UTF-8':
        try:
            BODY.encode(body_charset)
        except UnicodeError:
            pass
        else:
            break
    msg = MIMEText(BODY.encode(body_charset), 'html', body_charset)
    msg['From'] = SENDER
    msg['To'] = TO
    msg['Subject'] = SUBJECT

    SMTP_PORT = 587
    session = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    session.starttls()
    session.login(FROM, PASSWORD)
    session.sendmail(SENDER, TO, msg.as_string())
    session.quit()


def emailUser(profile, SUBJECT="", BODY=""):
    """
        Sends an email.

        Arguments:
        profile -- contains information related to the user (e.g., email address)
        SUBJECT -- subject line of the email
        BODY -- body text of the email
    """
    def generateSMSEmail(profile):
        """Generates an email from a user's phone number based on their carrier."""
        if profile['carrier'] is None or not profile['phone_number']:
            return None

        return str(profile['phone_number']) + "@" + profile['carrier']

    if profile['prefers_email'] and profile['gmail_address']:
        # add footer
        if BODY:
            BODY = profile['first_name'] + \
                ",<br><br>Here are your top headlines:" + BODY
            BODY += "<br>Sent from your Jasper"

        recipient = profile['gmail_address']
        if profile['first_name'] and profile['last_name']:
            recipient = profile['first_name'] + " " + \
                profile['last_name'] + " <%s>" % recipient
    else:
        recipient = generateSMSEmail(profile)

    if not recipient:
        return False

    try:
        if 'mailgun' in profile:
            user = profile['mailgun']['username']
            password = profile['mailgun']['password']
            server = 'smtp.mailgun.org'
        else:
            user = profile['gmail_address']
            password = profile['gmail_password']
            server = 'smtp.gmail.com'
        sendEmail(SUBJECT, BODY, recipient, user,
                  "Jasper <jasper>", password, server)

        return True
    except:
        return False


def getTimezone(profile):
    """
        Returns the pytz timezone for a given profile.

        Arguments:
        profile -- contains information related to the user (e.g., email address)
    """
    try:
        return timezone(profile['timezone'])
    except:
        return None


def generateTinyURL(URL):
    """
        Generates a compressed URL.

        Arguments:
        URL -- the original URL to-be compressed
    """
    target = "http://tinyurl.com/api-create.php?url=" + URL
    response = urllib2.urlopen(target)
    return response.read()


def isNegative(phrase):
    """
        Returns True if the input phrase has a negative sentiment.

        Arguments:
        phrase -- the input phrase to-be evaluated
    """
    return bool(re.search(r'\b(no(t)?|don\'t|stop|end)\b', phrase, re.IGNORECASE))


def isPositive(phrase):
    """
        Returns True if the input phrase has a positive sentiment.

        Arguments:
        phrase -- the input phrase to-be evaluated
    """
    return re.search(r'\b(sure|yes|yeah|go)\b', phrase, re.IGNORECASE)

########NEW FILE########
__FILENAME__ = Birthday
import datetime
import re
from facebook import *
from app_utils import getTimezone

WORDS = ["BIRTHDAY"]


def handle(text, mic, profile):
    """
        Responds to user-input, typically speech text, by listing the user's
        Facebook friends with birthdays today.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """
    oauth_access_token = profile['keys']["FB_TOKEN"]

    graph = GraphAPI(oauth_access_token)

    try:
        results = graph.request(
            "me/friends", args={'fields': 'id,name,birthday'})
    except GraphAPIError:
        mic.say(
            "I have not been authorized to query your Facebook. If you would like to check birthdays in the future, please visit the Jasper dashboard.")
        return
    except:
        mic.say(
            "I apologize, there's a problem with that service at the moment.")
        return

    needle = datetime.datetime.now(tz=getTimezone(profile)).strftime("%m/%d")

    people = []
    for person in results['data']:
        try:
            if needle in person['birthday']:
                people.append(person['name'])
        except:
            continue

    if len(people) > 0:
        if len(people) == 1:
            output = people[0] + " has a birthday today."
        else:
            output = "Your friends with birthdays today are " + \
                ", ".join(people[:-1]) + " and " + people[-1] + "."
    else:
        output = "None of your friends have birthdays today."

    mic.say(output)


def isValid(text):
    """
        Returns True if the input is related to birthdays.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'birthday', text, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = Gmail
import imaplib
import email
import re
from dateutil import parser
from app_utils import *

WORDS = ["EMAIL", "INBOX"]


def getSender(email):
    """
        Returns the best-guess sender of an email.

        Arguments:
        email -- the email whose sender is desired

        Returns:
        Sender of the email.
    """
    sender = email['From']
    m = re.match(r'(.*)\s<.*>', sender)
    if m:
        return m.group(1)
    return sender


def getDate(email):
    return parser.parse(email.get('date'))


def getMostRecentDate(emails):
    """
        Returns the most recent date of any email in the list provided.

        Arguments:
        emails -- a list of emails to check

        Returns:
        Date of the most recent email.
    """
    dates = [getDate(e) for e in emails]
    dates.sort(reverse=True)
    if dates:
        return dates[0]
    return None


def fetchUnreadEmails(profile, since=None, markRead=False, limit=None):
    """
        Fetches a list of unread email objects from a user's Gmail inbox.

        Arguments:
        profile -- contains information related to the user (e.g., Gmail address)
        since -- if provided, no emails before this date will be returned
        markRead -- if True, marks all returned emails as read in target inbox

        Returns:
        A list of unread email objects.
    """
    conn = imaplib.IMAP4_SSL('imap.gmail.com')
    conn.debug = 0
    conn.login(profile['gmail_address'], profile['gmail_password'])
    conn.select(readonly=(not markRead))

    msgs = []
    (retcode, messages) = conn.search(None, '(UNSEEN)')

    if retcode == 'OK' and messages != ['']:
        numUnread = len(messages[0].split(' '))
        if limit and numUnread > limit:
            return numUnread

        for num in messages[0].split(' '):
            # parse email RFC822 format
            ret, data = conn.fetch(num, '(RFC822)')
            msg = email.message_from_string(data[0][1])

            if not since or getDate(msg) > since:
                msgs.append(msg)
    conn.close()
    conn.logout()

    return msgs


def handle(text, mic, profile):
    """
        Responds to user-input, typically speech text, with a summary of
        the user's Gmail inbox, reporting on the number of unread emails
        in the inbox, as well as their senders.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., Gmail address)
    """
    try:
        msgs = fetchUnreadEmails(profile, limit=5)

        if isinstance(msgs, int):
            response = "You have %d unread emails." % msgs
            mic.say(response)
            return

        senders = [getSender(e) for e in msgs]
    except imaplib.IMAP4.error:
        mic.say(
            "I'm sorry. I'm not authenticated to work with your Gmail.")
        return

    if not senders:
        mic.say("You have no unread emails.")
    elif len(senders) == 1:
        mic.say("You have one unread email from " + senders[0] + ".")
    else:
        response = "You have %d unread emails" % len(
            senders)
        unique_senders = list(set(senders))
        if len(unique_senders) > 1:
            unique_senders[-1] = 'and ' + unique_senders[-1]
            response += ". Senders include: "
            response += '...'.join(senders)
        else:
            response += " from " + unittest[0]

        mic.say(response)


def isValid(text):
    """
        Returns True if the input is related to email.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'\bemail\b', text, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = HN
import urllib2
import re
import random
from bs4 import BeautifulSoup
import app_utils
from semantic.numbers import NumberService

WORDS = ["HACKER", "NEWS", "YES", "NO", "FIRST", "SECOND", "THIRD"]

PRIORITY = 4

URL = 'http://news.ycombinator.com'


class HNStory:

    def __init__(self, title, URL):
        self.title = title
        self.URL = URL


def getTopStories(maxResults=None):
    """
        Returns the top headlines from Hacker News.

        Arguments:
        maxResults -- if provided, returns a random sample of size maxResults
    """
    hdr = {'User-Agent': 'Mozilla/5.0'}
    req = urllib2.Request(URL, headers=hdr)
    page = urllib2.urlopen(req).read()
    soup = BeautifulSoup(page)
    matches = soup.findAll('td', class_="title")
    matches = [m.a for m in matches if m.a and m.text != u'More']
    matches = [HNStory(m.text, m['href']) for m in matches]

    if maxResults:
        num_stories = min(maxResults, len(matches))
        return random.sample(matches, num_stories)

    return matches


def handle(text, mic, profile):
    """
        Responds to user-input, typically speech text, with a sample of
        Hacker News's top headlines, sending them to the user over email
        if desired.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """
    mic.say("Pulling up some stories.")
    stories = getTopStories(maxResults=3)
    all_titles = '... '.join(str(idx + 1) + ") " +
                             story.title for idx, story in enumerate(stories))

    def handleResponse(text):

        def extractOrdinals(text):
            output = []
            service = NumberService()
            for w in text.split():
                if w in service.__ordinals__:
                    output.append(service.__ordinals__[w])
            return [service.parse(w) for w in output]

        chosen_articles = extractOrdinals(text)
        send_all = chosen_articles is [] and app_utils.isPositive(text)

        if send_all or chosen_articles:
            mic.say("Sure, just give me a moment")

            if profile['prefers_email']:
                body = "<ul>"

            def formatArticle(article):
                tiny_url = app_utils.generateTinyURL(article.URL)

                if profile['prefers_email']:
                    return "<li><a href=\'%s\'>%s</a></li>" % (tiny_url,
                                                               article.title)
                else:
                    return article.title + " -- " + tiny_url

            for idx, article in enumerate(stories):
                if send_all or (idx + 1) in chosen_articles:
                    article_link = formatArticle(article)

                    if profile['prefers_email']:
                        body += article_link
                    else:
                        if not app_utils.emailUser(profile, SUBJECT="", BODY=article_link):
                            mic.say(
                                "I'm having trouble sending you these articles. Please make sure that your phone number and carrier are correct on the dashboard.")
                            return

            # if prefers email, we send once, at the end
            if profile['prefers_email']:
                body += "</ul>"
                if not app_utils.emailUser(profile, SUBJECT="From the Front Page of Hacker News", BODY=body):
                    mic.say(
                        "I'm having trouble sending you these articles. Please make sure that your phone number and carrier are correct on the dashboard.")
                    return

            mic.say("All done.")

        else:
            mic.say("OK I will not send any articles")

    if not profile['prefers_email'] and profile['phone_number']:
        mic.say("Here are some front-page articles. " +
                all_titles + ". Would you like me to send you these? If so, which?")
        handleResponse(mic.activeListen())

    else:
        mic.say(
            "Here are some front-page articles. " + all_titles)


def isValid(text):
    """
        Returns True if the input is related to Hacker News.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'\b(hack(er)?|HN)\b', text, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = Joke
import random
import re

WORDS = ["JOKE", "KNOCK KNOCK"]


def getRandomJoke(filename="JOKES.txt"):
    jokeFile = open(filename, "r")
    jokes = []
    start = ""
    end = ""
    for line in jokeFile.readlines():
        line = line.replace("\n", "")

        if start == "":
            start = line
            continue

        if end == "":
            end = line
            continue

        jokes.append((start, end))
        start = ""
        end = ""

    jokes.append((start, end))
    joke = random.choice(jokes)
    return joke


def handle(text, mic, profile):
    """
        Responds to user-input, typically speech text, by telling a joke.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """
    joke = getRandomJoke()

    mic.say("Knock knock")

    def firstLine(text):
        mic.say(joke[0])

        def punchLine(text):
            mic.say(joke[1])

        punchLine(mic.activeListen())

    firstLine(mic.activeListen())


def isValid(text):
    """
        Returns True if the input is related to jokes/humor.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'\bjoke\b', text, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = Life
import random
import re

WORDS = ["MEANING", "OF", "LIFE"]


def handle(text, mic, profile):
    """
        Responds to user-input, typically speech text, by relaying the
        meaning of life.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """
    messages = ["It's 42, you idiot.",
                "It's 42. How many times do I have to tell you?"]

    message = random.choice(messages)

    mic.say(message)


def isValid(text):
    """
        Returns True if the input is related to the meaning of life.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'\bmeaning of life\b', text, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = News
import feedparser
import app_utils
import re
from semantic.numbers import NumberService

WORDS = ["NEWS", "YES", "NO", "FIRST", "SECOND", "THIRD"]

PRIORITY = 3

URL = 'http://news.ycombinator.com'


class Article:

    def __init__(self, title, URL):
        self.title = title
        self.URL = URL


def getTopArticles(maxResults=None):
    d = feedparser.parse("http://news.google.com/?output=rss")

    count = 0
    articles = []
    for item in d['items']:
        articles.append(Article(item['title'], item['link'].split("&url=")[1]))
        count += 1
        if maxResults and count > maxResults:
            break

    return articles


def handle(text, mic, profile):
    """
        Responds to user-input, typically speech text, with a summary of
        the day's top news headlines, sending them to the user over email
        if desired.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """
    mic.say("Pulling up the news")
    articles = getTopArticles(maxResults=3)
    titles = [" ".join(x.title.split(" - ")[:-1]) for x in articles]
    all_titles = "... ".join(str(idx + 1) + ")" +
                             title for idx, title in enumerate(titles))

    def handleResponse(text):

        def extractOrdinals(text):
            output = []
            service = NumberService()
            for w in text.split():
                if w in service.__ordinals__:
                    output.append(service.__ordinals__[w])
            return [service.parse(w) for w in output]

        chosen_articles = extractOrdinals(text)
        send_all = chosen_articles is [] and app_utils.isPositive(text)

        if send_all or chosen_articles:
            mic.say("Sure, just give me a moment")

            if profile['prefers_email']:
                body = "<ul>"

            def formatArticle(article):
                tiny_url = app_utils.generateTinyURL(article.URL)

                if profile['prefers_email']:
                    return "<li><a href=\'%s\'>%s</a></li>" % (tiny_url,
                                                               article.title)
                else:
                    return article.title + " -- " + tiny_url

            for idx, article in enumerate(articles):
                if send_all or (idx + 1) in chosen_articles:
                    article_link = formatArticle(article)

                    if profile['prefers_email']:
                        body += article_link
                    else:
                        if not app_utils.emailUser(profile, SUBJECT="", BODY=article_link):
                            mic.say(
                                "I'm having trouble sending you these articles. Please make sure that your phone number and carrier are correct on the dashboard.")
                            return

            # if prefers email, we send once, at the end
            if profile['prefers_email']:
                body += "</ul>"
                if not app_utils.emailUser(profile, SUBJECT="Your Top Headlines", BODY=body):
                    mic.say(
                        "I'm having trouble sending you these articles. Please make sure that your phone number and carrier are correct on the dashboard.")
                    return

            mic.say("All set")

        else:

            mic.say("OK I will not send any articles")

    if 'phone_number' in profile:
        mic.say("Here are the current top headlines. " + all_titles +
                ". Would you like me to send you these articles? If so, which?")
        handleResponse(mic.activeListen())

    else:
        mic.say(
            "Here are the current top headlines. " + all_titles)


def isValid(text):
    """
        Returns True if the input is related to the news.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'\b(news|headline)\b', text, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = Notifications
import re
from facebook import *


WORDS = ["FACEBOOK", "NOTIFICATION"]


def handle(text, mic, profile):
    """
        Responds to user-input, typically speech text, with a summary of
        the user's Facebook notifications, including a count and details
        related to each individual notification.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """
    oauth_access_token = profile['keys']['FB_TOKEN']

    graph = GraphAPI(oauth_access_token)

    try:
        results = graph.request("me/notifications")
    except GraphAPIError:
        mic.say(
            "I have not been authorized to query your Facebook. If you would like to check your notifications in the future, please visit the Jasper dashboard.")
        return
    except:
        mic.say(
            "I apologize, there's a problem with that service at the moment.")

    if not len(results['data']):
        mic.say("You have no Facebook notifications. ")
        return

    updates = []
    for notification in results['data']:
        updates.append(notification['title'])

    count = len(results['data'])
    mic.say("You have " + str(count) +
            " Facebook notifications. " + " ".join(updates) + ". ")

    return


def isValid(text):
    """
        Returns True if the input is related to Facebook notifications.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'\bnotification|Facebook\b', text, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = Time
import datetime
import re
from app_utils import getTimezone
from semantic.dates import DateService

WORDS = ["TIME"]


def handle(text, mic, profile):
    """
        Reports the current time based on the user's timezone.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """

    tz = getTimezone(profile)
    now = datetime.datetime.now(tz=tz)
    service = DateService()
    response = service.convertTime(now)
    mic.say("It is %s right now." % response)


def isValid(text):
    """
        Returns True if input is related to the time.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'\btime\b', text, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = Unclear
from sys import maxint
import random

WORDS = []

PRIORITY = -(maxint + 1)


def handle(text, mic, profile):
    """
        Reports that the user has unclear or unusable input.

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """

    messages = ["I'm sorry, could you repeat that?",
                "My apologies, could you try saying that again?",
                "Say that again?", "I beg your pardon?"]

    message = random.choice(messages)

    mic.say(message)


def isValid(text):
    return True

########NEW FILE########
__FILENAME__ = Weather
import re
import datetime
import feedparser
from app_utils import getTimezone
from semantic.dates import DateService

WORDS = ["WEATHER", "TODAY", "TOMORROW"]


def replaceAcronyms(text):
    """Replaces some commonly-used acronyms for an improved verbal weather report."""

    def parseDirections(text):
        words = {
            'N': 'north',
            'S': 'south',
            'E': 'east',
            'W': 'west',
        }
        output = [words[w] for w in list(text)]
        return ' '.join(output)
    acronyms = re.findall(r'\b([NESW]+)\b', text)

    for w in acronyms:
        text = text.replace(w, parseDirections(w))

    text = re.sub(r'(\b\d+)F(\b)', '\g<1> Fahrenheit\g<2>', text)
    text = re.sub(r'(\b)mph(\b)', '\g<1>miles per hour\g<2>', text)
    text = re.sub(r'(\b)in\.', '\g<1>inches', text)

    return text


def getForecast(profile):
    return feedparser.parse("http://rss.wunderground.com/auto/rss_full/"
                            + str(profile['location']))['entries']


def handle(text, mic, profile):
    """
        Responds to user-input, typically speech text, with a summary of
        the relevant weather for the requested date (typically, weather
        information will not be available for days beyond tomorrow).

        Arguments:
        text -- user-input, typically transcribed speech
        mic -- used to interact with the user (for both input and output)
        profile -- contains information related to the user (e.g., phone number)
    """

    if not profile['location']:
        mic.say(
            "I'm sorry, I can't seem to access that information. Please make sure that you've set your location on the dashboard.")
        return

    tz = getTimezone(profile)

    service = DateService(tz=tz)
    date = service.extractDay(text)
    if not date:
        date = datetime.datetime.now(tz=tz)
    weekday = service.__daysOfWeek__[date.weekday()]

    if date.weekday() == datetime.datetime.now(tz=tz).weekday():
        date_keyword = "Today"
    elif date.weekday() == (
            datetime.datetime.now(tz=tz).weekday() + 1) % 7:
        date_keyword = "Tomorrow"
    else:
        date_keyword = "On " + weekday

    forecast = getForecast(profile)

    output = None

    for entry in forecast:
        try:
            date_desc = entry['title'].split()[0].strip().lower()
            if date_desc == 'forecast': #For global forecasts
            	date_desc = entry['title'].split()[2].strip().lower()
            	weather_desc = entry['summary']

            elif date_desc == 'current': #For first item of global forecasts
            	continue
            else:
            	weather_desc = entry['summary'].split('-')[1] #US forecasts

            if weekday == date_desc:
                output = date_keyword + \
                    ", the weather will be " + weather_desc + "."
                break
        except:
            continue

    if output:
        output = replaceAcronyms(output)
        mic.say(output)
    else:
        mic.say(
            "I'm sorry. I can't see that far ahead.")


def isValid(text):
    """
        Returns True if the text is related to the weather.

        Arguments:
        text -- user-input, typically transcribed speech
    """
    return bool(re.search(r'\b(weathers?|temperature|forecast|outside|hot|cold|jacket|coat|rain)\b', text, re.IGNORECASE))

########NEW FILE########
__FILENAME__ = music
import re
import difflib
from mpd import MPDClient


def reconnect(func, *default_args, **default_kwargs):
    """
        Reconnects before running
    """

    def wrap(self, *default_args, **default_kwargs):
        try:
            self.client.connect("localhost", 6600)
        except:
            pass

        # sometimes not enough to just connect
        try:
            func(self, *default_args, **default_kwargs)
        except:
            self.client = MPDClient()
            self.client.timeout = None
            self.client.idletimeout = None
            self.client.connect("localhost", 6600)

            func(self, *default_args, **default_kwargs)

    return wrap


class Song:

    def __init__(self, id, title, artist, album):

        self.id = id
        self.title = title
        self.artist = artist
        self.album = album


class Music:

    client = None
    songs = []  # may have duplicates
    playlists = []

    # capitalized strings
    song_titles = []
    song_artists = []

    def __init__(self):
        """
            Prepare the client and music variables
        """
        # prepare client
        self.client = MPDClient()
        self.client.timeout = None
        self.client.idletimeout = None
        self.client.connect("localhost", 6600)

        # gather playlists
        self.playlists = [x["playlist"] for x in self.client.listplaylists()]

        # gather songs
        self.client.clear()
        for playlist in self.playlists:
            self.client.load(playlist)

        soup = self.client.playlist()
        for i in range(0, len(soup) / 10):
            index = i * 10
            id = soup[index].strip()
            title = soup[index + 3].strip().upper()
            artist = soup[index + 2].strip().upper()
            album = soup[index + 4].strip().upper()

            self.songs.append(Song(id, title, artist, album))

            self.song_titles.append(title)
            self.song_artists.append(artist)

    @reconnect
    def play(self, songs=False, playlist_name=False):
        """
            Plays the current song or accepts a song to play.

            Arguments:
            songs -- a list of song objects
            playlist_name -- user-defined, something like "Love Song Playlist"
        """
        if songs:
            self.client.clear()
            for song in songs:
                try:  # for some reason, certain ids don't work
                    self.client.add(song.id)
                except:
                    pass

        if playlist_name:
            self.client.clear()
            self.client.load(playlist_name)

        self.client.play()

    #@reconnect -- this makes the function return None for some reason!
    def current_song(self):
        item = self.client.playlistinfo(int(self.client.status()["song"]))[0]
        result = "%s by %s" % (item["title"], item["artist"])
        return result

    @reconnect
    def volume(self, level=None, interval=None):

        if level:
            self.client.setvol(int(level))
            return

        if interval:
            level = int(self.client.status()['volume']) + int(interval)
            self.client.setvol(int(level))
            return

    @reconnect
    def pause(self):
        self.client.pause()

    @reconnect
    def stop(self):
        self.client.stop()

    @reconnect
    def next(self):
        self.client.next()
        return

    @reconnect
    def previous(self):
        self.client.previous()
        return

    def get_soup(self):
        """
                returns the list of unique words that comprise song and artist titles
        """

        soup = []

        for song in self.songs:
            song_words = song.title.split(" ")
            artist_words = song.artist.split(" ")
            soup.extend(song_words)
            soup.extend(artist_words)

        title_trans = ''.join(
            chr(c) if chr(c).isupper() or chr(c).islower() else '_' for c in range(256))
        soup = [x.decode('utf-8').encode("ascii", "ignore").upper().translate(title_trans).replace("_", "")
                for x in soup]
        soup = [x for x in soup if x != ""]

        return list(set(soup))

    def get_soup_playlist(self):
        """
                returns the list of unique words that comprise playlist names
        """

        soup = []

        for name in self.playlists:
            soup.extend(name.split(" "))

        title_trans = ''.join(
            chr(c) if chr(c).isupper() or chr(c).islower() else '_' for c in range(256))
        soup = [x.decode('utf-8').encode("ascii", "ignore").upper().translate(title_trans).replace("_", "")
                for x in soup]
        soup = [x for x in soup if x != ""]

        return list(set(soup))

    def get_soup_separated(self):
        """
                returns the list of PHRASES that comprise song and artist titles
        """

        title_soup = [song.title for song in self.songs]
        artist_soup = [song.artist for song in self.songs]

        soup = list(set(title_soup + artist_soup))

        title_trans = ''.join(
            chr(c) if chr(c).isupper() or chr(c).islower() else '_' for c in range(256))
        soup = [x.decode('utf-8').encode("ascii", "ignore").upper().translate(title_trans).replace("_", " ")
                for x in soup]
        soup = [re.sub(' +', ' ', x) for x in soup if x != ""]

        return soup

    def fuzzy_songs(self, query):
        """
                Returns songs matching a query best as possible on either artist field, etc
        """

        query = query.upper()

        matched_song_titles = difflib.get_close_matches(
            query, self.song_titles)
        matched_song_artists = difflib.get_close_matches(
            query, self.song_artists)

        # if query is beautifully matched, then forget about everything else
        strict_priority_title = [x for x in matched_song_titles if x == query]
        strict_priority_artists = [
            x for x in matched_song_artists if x == query]

        if strict_priority_title:
            matched_song_titles = strict_priority_title
        if strict_priority_artists:
            matched_song_artists = strict_priority_artists

        matched_songs_bytitle = [
            song for song in self.songs if song.title in matched_song_titles]
        matched_songs_byartist = [
            song for song in self.songs if song.artist in matched_song_artists]

        matches = list(set(matched_songs_bytitle + matched_songs_byartist))

        return matches

    def fuzzy_playlists(self, query):
        """
                returns playlist names that match query best as possible
        """
        query = query.upper()
        lookup = {n.upper(): n for n in self.playlists}
        results = [lookup[r] for r in difflib.get_close_matches(query, lookup)]
        return results

if __name__ == "__main__":
    """
        Plays music and performs unit-testing
    """

    print "Creating client"

    music = Music()

    print "Playing"

    music.play(songs=[music.songs[3]])

    print music.get_soup_separated()

    while True:
        query = raw_input("Query: ")
        songs = music.fuzzy_songs(query)
        print "Results"
        print "======="
        for song in songs:
            print "Title: %s Artist: %s" % (song.title, song.artist)
        music.play(songs=songs)

########NEW FILE########
__FILENAME__ = musicmode
"""
    Manages the conversation
"""

import os
from mic import Mic
import g2p
from music import *


class MusicMode:

    def __init__(self, PERSONA, mic):
        self.persona = PERSONA
        # self.mic - we're actually going to ignore the mic they passed in
        self.music = Music()

        # index spotify playlists into new dictionary and language models
        original = self.music.get_soup_playlist(
        ) + ["STOP", "CLOSE", "PLAY", "PAUSE",
             "NEXT", "PREVIOUS", "LOUDER", "SOFTER", "LOWER", "HIGHER", "VOLUME", "PLAYLIST"]
        pronounced = g2p.translateWords(original)
        zipped = zip(original, pronounced)
        lines = ["%s %s" % (x, y) for x, y in zipped]

        with open("dictionary_spotify.dic", "w") as f:
            f.write("\n".join(lines) + "\n")

        with open("sentences_spotify.txt", "w") as f:
            f.write("\n".join(original) + "\n")
            f.write("<s> \n </s> \n")
            f.close()

        # make language model
        os.system(
            "text2idngram -vocab sentences_spotify.txt < sentences_spotify.txt -idngram spotify.idngram")
        os.system(
            "idngram2lm -idngram spotify.idngram -vocab sentences_spotify.txt -arpa languagemodel_spotify.lm")

        # create a new mic with the new music models
        self.mic = Mic(
            "languagemodel.lm", "dictionary.dic", "languagemodel_persona.lm",
            "dictionary_persona.dic", "languagemodel_spotify.lm", "dictionary_spotify.dic")

    def delegateInput(self, input):

        command = input.upper()

        # check if input is meant to start the music module
        if "PLAYLIST" in command:
            command = command.replace("PLAYLIST", "")
        elif "STOP" in command:
            self.mic.say("Stopping music")
            self.music.stop()
            return
        elif "PLAY" in command:
            self.mic.say("Playing %s" % self.music.current_song())
            self.music.play()
            return
        elif "PAUSE" in command:
            self.mic.say("Pausing music")
            # not pause because would need a way to keep track of pause/play
            # state
            self.music.stop()
            return
        elif any(ext in command for ext in ["LOUDER", "HIGHER"]):
            self.mic.say("Louder")
            self.music.volume(interval=10)
            self.music.play()
            return
        elif any(ext in command for ext in ["SOFTER", "LOWER"]):
            self.mic.say("Softer")
            self.music.volume(interval=-10)
            self.music.play()
            return
        elif "NEXT" in command:
            self.mic.say("Next song")
            self.music.play()  # backwards necessary to get mopidy to work
            self.music.next()
            self.mic.say("Playing %s" % self.music.current_song())
            return
        elif "PREVIOUS" in command:
            self.mic.say("Previous song")
            self.music.play()  # backwards necessary to get mopidy to work
            self.music.previous()
            self.mic.say("Playing %s" % self.music.current_song())
            return

        # SONG SELECTION... requires long-loading dictionary and language model
        # songs = self.music.fuzzy_songs(query = command.replace("PLAY", ""))
        # if songs:
        #     self.mic.say("Found songs")
        #     self.music.play(songs = songs)

        #     print "SONG RESULTS"
        #     print "============"
        #     for song in songs:
        #         print "Song: %s Artist: %s" % (song.title, song.artist)

        #     self.mic.say("Playing %s" % self.music.current_song())

        # else:
        #     self.mic.say("No songs found. Resuming current song.")
        #     self.music.play()

        # PLAYLIST SELECTION
        playlists = self.music.fuzzy_playlists(query=command)
        if playlists:
            self.mic.say("Loading playlist %s" % playlists[0])
            self.music.play(playlist_name=playlists[0])
            self.mic.say("Playing %s" % self.music.current_song())
        else:
            self.mic.say("No playlists found. Resuming current song.")
            self.music.play()

        return

    def handleForever(self):

        self.music.play()
        self.mic.say("Playing %s" % self.music.current_song())

        while True:

            try:
                threshold, transcribed = self.mic.passiveListen(self.persona)
            except:
                continue

            if threshold:

                self.music.pause()

                input = self.mic.activeListen(MUSIC=True)

                if "close" in input.lower():
                    self.mic.say("Closing Spotify")
                    return

                if input:
                    self.delegateInput(input)
                else:
                    self.mic.say("Pardon?")
                    self.music.play()

if __name__ == "__main__":
    """
        Indexes the Spotify music library to dictionary_spotify.dic and languagemodel_spotify.lm
    """

    musicmode = MusicMode("JASPER", None)
    music = musicmode.music

    original = music.get_soup() + ["STOP", "CLOSE", "PLAY",
                                   "PAUSE", "NEXT", "PREVIOUS", "LOUDER", "SOFTER"]
    pronounced = g2p.translateWords(original)
    zipped = zip(original, pronounced)
    lines = ["%s %s" % (x, y) for x, y in zipped]

    with open("dictionary_spotify.dic", "w") as f:
        f.write("\n".join(lines) + "\n")

    with open("sentences_spotify.txt", "w") as f:
        f.write("\n".join(original) + "\n")
        f.write("<s> \n </s> \n")
        f.close()

    with open("sentences_spotify_separated.txt", "w") as f:
        f.write("\n".join(music.get_soup_separated()) + "\n")
        f.write("<s> \n </s> \n")
        f.close()

    # make language model
    os.system(
        "text2idngram -vocab sentences_spotify.txt < sentences_spotify_separated.txt -idngram spotify.idngram")
    os.system(
        "idngram2lm -idngram spotify.idngram -vocab sentences_spotify.txt -arpa languagemodel_spotify.lm")

    print "Language Model and Dictionary Done"

########NEW FILE########
__FILENAME__ = notifier
import Queue
from modules import Gmail
from apscheduler.scheduler import Scheduler
import logging
logging.basicConfig()


class Notifier(object):

    class NotificationClient(object):

        def __init__(self, gather, timestamp):
            self.gather = gather
            self.timestamp = timestamp

        def run(self):
            self.timestamp = self.gather(self.timestamp)

    def __init__(self, profile):
        self.q = Queue.Queue()
        self.profile = profile
        self.notifiers = [
            self.NotificationClient(self.handleEmailNotifications, None),
        ]

        sched = Scheduler()
        sched.start()
        sched.add_interval_job(self.gather, seconds=30)

    def gather(self):
        [client.run() for client in self.notifiers]

    def handleEmailNotifications(self, lastDate):
        """Places new Gmail notifications in the Notifier's queue."""
        emails = Gmail.fetchUnreadEmails(self.profile, since=lastDate)
        if emails:
            lastDate = Gmail.getMostRecentDate(emails)

        def styleEmail(e):
            return "New email from %s." % Gmail.getSender(e)

        for e in emails:
            self.q.put(styleEmail(e))

        return lastDate

    def getNotification(self):
        """Returns a notification. Note that this function is consuming."""
        try:
            notif = self.q.get(block=False)
            return notif
        except Queue.Empty:
            return None

    def getAllNotifications(self):
        """
            Return a list of notifications in chronological order.
            Note that this function is consuming, so consecutive calls
            will yield different results.
        """
        notifs = []

        notif = self.getNotification()
        while notif:
            notifs.append(notif)
            notif = self.getNotification()

        return notifs

########NEW FILE########
__FILENAME__ = populate
import re
from getpass import getpass
import yaml
from pytz import timezone
import feedparser


def run():
    profile = {}

    print "Welcome to the profile populator. If, at any step, you'd prefer not to enter the requested information, just hit 'Enter' with a blank field to continue."

    def simple_request(var, cleanVar, cleanInput=None):
        input = raw_input(cleanVar + ": ")
        if input:
            if cleanInput:
                input = cleanInput(input)
            profile[var] = input

    # name
    simple_request('first_name', 'First name')
    simple_request('last_name', 'Last name')

    # gmail
    print "\nJasper uses your Gmail to send notifications. Alternatively, you can skip this step (or just fill in the email address if you want to receive email notifications) and setup a Mailgun account, as at http://jasperproject.github.io/documentation/software/#mailgun.\n"
    simple_request('gmail_address', 'Gmail address')
    profile['gmail_password'] = getpass()

    # phone number
    clean_number = lambda s: re.sub(r'[^0-9]', '', s)
    phone_number = clean_number(raw_input(
        "\nPhone number (no country code). Any dashes or spaces will be removed for you: "))
    profile['phone_number'] = phone_number

    # carrier
    print("\nPhone carrier (for sending text notifications).")
    print(
        "If you have a US phone number, you can enter one of the following: 'AT&T', 'Verizon', 'T-Mobile' (without the quotes). If your carrier isn't listed or you have an international number, go to http://www.emailtextmessages.com and enter the email suffix for your carrier (e.g., for Virgin Mobile, enter 'vmobl.com'; for T-Mobile Germany, enter 't-d1-sms.de').")
    carrier = raw_input('Carrier: ')
    if carrier == 'AT&T':
        profile['carrier'] = 'txt.att.net'
    elif carrier == 'Verizon':
        profile['carrier'] = 'vtext.com'
    elif carrier == 'T-Mobile':
        profile['carrier'] = 'tmomail.net'
    else:
        profile['carrier'] = carrier

    # location
    def verifyLocation(place):
        feed = feedparser.parse('http://rss.wunderground.com/auto/rss_full/' + place)
        numEntries = len(feed['entries'])
        if numEntries==0:
            return False
        else:
            print("Location saved as " + feed['feed']['description'][33:])
            return True

    print(
        "\nLocation should be a 5-digit US zipcode (e.g., 08544). If you are outside the US, insert the name of your nearest big town/city. For weather requests.")
    location = raw_input("Location: ")
    while location and (verifyLocation(location)==False):
        print("Weather not found. Please try another location.")
        location = raw_input("Location: ")
    if location:
        profile['location'] = location

    # timezone
    print(
        "\nPlease enter a timezone from the list located in the TZ* column at http://en.wikipedia.org/wiki/List_of_tz_database_time_zones, or none at all.")
    tz = raw_input("Timezone: ")
    while tz:
        try:
            timezone(tz)
            profile['timezone'] = tz
            break
        except:
            print("Not a valid timezone. Try again.")
            tz = raw_input("Timezone: ")

    response = raw_input(
        "\nWould you prefer to have notifications sent by email (E) or text message (T)? ")
    while not response or (response != 'E' and response != 'T'):
        response = raw_input("Please choose email (E) or text message (T): ")
    profile['prefers_email'] = (response == 'E')

    # write to profile
    print("Writing to profile...")
    outputFile = open("profile.yml", "w")
    yaml.dump(profile, outputFile, default_flow_style=False)
    print("Done.")

if __name__ == "__main__":
    run()

########NEW FILE########
__FILENAME__ = test
import unittest
from mock import patch
from urllib2 import URLError, urlopen
import yaml
from test_mic import Mic
import modules
import brain


def activeInternet():
    try:
        urlopen('http://www.google.com', timeout=1)
        return True
    except URLError:
        return False


class TestModules(unittest.TestCase):

    def setUp(self):
        self.profile = yaml.safe_load(open("profile.yml", "r"))
        self.send = False

    def runConversation(self, query, inputs, module):
        """Generic method for spoofing conversation.

        Arguments:
        query -- The initial input to the server.
        inputs -- Additional input, if conversation is extended.

        Returns:
        The server's responses, in a list.
        """
        self.assertTrue(module.isValid(query))
        mic = Mic(inputs)
        module.handle(query, mic, self.profile)
        return mic.outputs

    def testLife(self):
        query = "What is the meaning of life?"
        inputs = []
        outputs = self.runConversation(query, inputs, modules.Life)
        self.assertEqual(len(outputs), 1)
        self.assertTrue("42" in outputs[0])

    def testJoke(self):
        query = "Tell me a joke."
        inputs = ["Who's there?", "Random response"]
        outputs = self.runConversation(query, inputs, modules.Joke)
        self.assertEqual(len(outputs), 3)
        allJokes = open("JOKES.txt", "r").read()
        self.assertTrue(outputs[2] in allJokes)

    def testTime(self):
        query = "What time is it?"
        inputs = []
        self.runConversation(query, inputs, modules.Time)

    @unittest.skipIf(not activeInternet(), "No internet connection")
    def testGmail(self):
        key = 'gmail_password'
        if not key in self.profile or not self.profile[key]:
            return

        query = "Check my email"
        inputs = []
        self.runConversation(query, inputs, modules.Gmail)

    @unittest.skipIf(not activeInternet(), "No internet connection")
    def testHN(self):
        query = "find me some of the top hacker news stories"
        if self.send:
            inputs = ["the first and third"]
        else:
            inputs = ["no"]
        outputs = self.runConversation(query, inputs, modules.HN)
        self.assertTrue("front-page articles" in outputs[1])

    @unittest.skipIf(not activeInternet(), "No internet connection")
    def testNews(self):
        query = "find me some of the top news stories"
        if self.send:
            inputs = ["the first"]
        else:
            inputs = ["no"]
        outputs = self.runConversation(query, inputs, modules.News)
        self.assertTrue("top headlines" in outputs[1])

    @unittest.skipIf(not activeInternet(), "No internet connection")
    def testWeather(self):
        query = "what's the weather like tomorrow"
        inputs = []
        outputs = self.runConversation(query, inputs, modules.Weather)
        self.assertTrue(
            "can't see that far ahead" in outputs[0]
            or "Tomorrow" in outputs[0])


class TestBrain(unittest.TestCase):

    @staticmethod
    def _emptyBrain():
        mic = Mic([])
        profile = yaml.safe_load(open("profile.yml", "r"))
        return brain.Brain(mic, profile)

    @patch.object(brain, 'logError')
    def testLog(self, logError):
        """Does Brain correctly log errors when raised by modules?"""
        my_brain = TestBrain._emptyBrain()
        unclear = my_brain.modules[-1]
        with patch.object(unclear, 'handle') as mocked_handle:
            mocked_handle.side_effect = KeyError('foo')
            my_brain.query("zzz gibberish zzz")
            logError.assert_called_with()

    def testSortByPriority(self):
        """Does Brain sort modules by priority?"""
        my_brain = TestBrain._emptyBrain()
        priorities = filter(lambda m: hasattr(m, 'PRIORITY'), my_brain.modules)
        target = sorted(priorities, key=lambda m: m.PRIORITY, reverse=True)
        self.assertEqual(target, priorities)

    def testPriority(self):
        """Does Brain correctly send query to higher-priority module?"""
        my_brain = TestBrain._emptyBrain()
        hn_module = 'modules.HN'
        hn = filter(lambda m: m.__name__ == hn_module, my_brain.modules)[0]

        with patch.object(hn, 'handle') as mocked_handle:
            my_brain.query("hacker news")
            self.assertTrue(mocked_handle.called)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mic
"""
A drop-in replacement for the Mic class used during unit testing.
Designed to take pre-arranged inputs as an argument and store any
outputs for inspection. Requires a populated profile (profile.yml).
"""


class Mic:

    def __init__(self, inputs):
        self.inputs = inputs
        self.idx = 0
        self.outputs = []

    def passiveListen(self, PERSONA):
        return True, "JASPER"

    def activeListen(self, THRESHOLD=None, LISTEN=True, MUSIC=False):
        if not LISTEN:
            return self.inputs[self.idx - 1]

        input = self.inputs[self.idx]
        self.idx += 1
        return input

    def say(self, phrase, OPTIONS=None):
        self.outputs.append(phrase)

########NEW FILE########
