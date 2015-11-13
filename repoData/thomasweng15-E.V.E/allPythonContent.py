__FILENAME__ = actions_helper
import urllib2

DATAFILE = "./data/user_config.txt"

class ActionsHelper():
	"""
	Hold helper functions for actions.
	
	"""
	def __init__(self, speaker):
		self.speaker = speaker

	def test_url(self, phrase):
		"""Test existence of domain at url."""
		try: 
			phrase = phrase.lower()
			code = urllib2.urlopen(phrase).code
			if (code / 100 >= 4):
				return ""
			else: 
				return phrase
		except urllib2.URLError as err: pass
		return ""

	def get_value_from_datafile(self, key):
		"""Find key and return value from datafile."""
		try:
			f = open(DATAFILE, 'r')
		except IOError:
			self.speaker.say("Error, datafile cannot be found.")
			sys.exit(1)

		for line in f:
			if line.find(key + "::") != -1:
				f.close()
				return line[len(key + "::"):].rstrip('\n')

		self.speaker.say("Oops, datafile does not contain the needed info.")
		f.close()
		return None
########NEW FILE########
__FILENAME__ = chatbot
import aiml

BRAINFILE = "./data/aiml/standard.brn"
CHATBOT_CONFIG = "./data/aiml/chatbot_config.txt"

class Chatbot():
	"""
	Process requests to converse with the chatbot.

	"""
	def __init__(self, speaker):
		self.chatbot = aiml.Kernel()
		self.chatbot.bootstrap(brainFile=BRAINFILE)
		self.speaker = speaker
		self.configure_predicates()

	def configure_predicates(self):
		"""Load bot predicates from brainfile."""
		try: 
			f = open(CHATBOT_CONFIG)
		except IOError:
			self.speaker.say("Error: chatbot configuration file not found.")
			sys.exit(1)

		bot_predicates = f.readlines()
		f.close()
		for bot_predicate in bot_predicates:
			key_value = bot_predicate.split('::')
			if len(key_value) == 2:
				self.chatbot.setBotPredicate(key_value[0], key_value[1].rstrip('\n'))

	def process(self, job):
		"""Process chat bot job requests."""
		if job.query != "":
			response = self.chatbot.respond(job.query)
		else:
			response = self.chatbot.respond(job.recorded())
		self.speaker.say(response)

		job.is_processed = True
########NEW FILE########
__FILENAME__ = music


class Music():
	"""
	Process requests to play music.
	
	"""
	def __init__(self, speaker, actions_helper):
		self.speaker = speaker
		self.helper = actions_helper

	def process(self, job, controller):
		"""Process play radio job request."""
		# TODO make check of whether last.fm is not already open.
		# Last.fm radio glitches out when two or more of them 
		# run at the same time.
		self.speaker.say("Starting radio.")
		phrase = job.query
		phrase = self.replace_spaces(phrase)
		music_url = "http://www.last.fm/listen/artist/" + \
					phrase + "/similarartists"
		if self.helper.test_url(music_url) != "":
			controller.open(music_url)
		else:
			self.speaker.say("Oops, page does not exist.")

	def replace_spaces(self, phrase):
		"""Replace spaces in string with %2B."""
		space = phrase.find(' ')
		while space != -1:
			phrase = phrase[:space] + "%2B" + phrase[space + 1:]
			space = phrase.find(' ')
		return phrase.lower()

	
########NEW FILE########
__FILENAME__ = news
import sys


class News():
	"""
	Process jobs requesting the news.
	
	"""
	def __init__(self, speaker, actions_helper):
		self.speaker = speaker
		self.helper = actions_helper
		self.news_url = self.helper.get_value_from_datafile("news_url")

	def process(self, job, controller):
		"""Process News job request."""
		self.speaker.say("getting the news.")
		controller.open(self.news_url)

	

	
########NEW FILE########
__FILENAME__ = screenshot
import gtk.gdk
import os
import sys


class Screenshot:
	"""
	Process jobs requesting a screenshot.
	
	"""
	def __init__(self, speaker, actions_helper):
		self.w = gtk.gdk.get_default_root_window()
		self.size = self.w.get_size()
		self.speaker = speaker
		self.helper = actions_helper
		self.screenshot_dir = self.helper.get_value_from_datafile("screenshot_dir")

	def take(self):
		"""Take a screenshot and store it."""
		pb = gtk.gdk.Pixbuf(gtk.gdk.COLORSPACE_RGB,False,8,self.size[0],self.size[1])
		pb = pb.get_from_drawable(self.w,self.w.get_colormap(),0,0,0,0,self.size[0],self.size[1])
		
		if (pb != None):
			name = "screenshot.jpeg"
			while 1: # check if name exists - change if already exists
				if os.path.isfile(self.screenshot_dir + name): 
					if name[10].isdigit():
						num = int(name[10]) + 1
						name = name[:10] + str(num) + name[11:]
					else:
						name = name[:10] + "1." + name[11:] 
				else:
					break

			pb.save(self.screenshot_dir + name,"jpeg")
			self.speaker.say("Screenshot saved.")
			print "Screenshot saved to '" + self.screenshot_dir + "' folder."

		else:
			self.speaker.say("Unable to get screenshot.")
			print "Screenshot failed."

########NEW FILE########
__FILENAME__ = search


class Search():
	"""
	Process web searches.
	
	"""
	def __init__(self, speaker, actions_helper):
		self.speaker = speaker
		self.helper = actions_helper
		self.search_url = self.helper.get_value_from_datafile("search_url")

	def process(self, job, controller):
		"""Process web search job request."""
		self.speaker.say("Pulling up search results.")
		phrase = job.query
		url = self.search_url + phrase.replace(" ", "+")
		controller.open(url)
########NEW FILE########
__FILENAME__ = webpage


class Webpage():
	"""
	Process jobs that request to open a specified webpage.
	
	"""
	def __init__(self, speaker, actions_helper):
		self.speaker = speaker
		self.helper = actions_helper

	def process(self, job, controller):
		"""Process open webpage job request."""
		phrase = job.query
		url = self.make_url(phrase)
		if url != "":
			self.speaker.say("opening " + url[12:])
			controller.open(url)
			return True
		else:
			self.speaker.say("Sorry, I couldn't find the web page.")
			return False

	def make_url(self, phrase):
		"""Create url using the query and check domain existence."""
		# remove spaces in the phrase
		phrase = self.remove_spaces(phrase)

		# if phrase does not end with .com or other suffix append .com
		if phrase.find('.com') == -1 \
		and phrase.find('.edu') == -1 \
		and phrase.find('.org') == -1:
			phrase = phrase + ".com"

		# test website existence, return "" if website doesn't exist
		return self.helper.test_url(phrase)

	def remove_spaces(self, phrase):
		"""Remove spaces from the phrase."""
		space = phrase.find(' ')
		while space != -1:
			phrase = phrase[:space] + phrase[space + 1:]
			space = phrase.find(' ')
		return "https://www." + phrase.lower()

	
########NEW FILE########
__FILENAME__ = wolfram
# -*- coding: utf-8 -*-

import urllib2
import xml.etree.ElementTree as ET


class Wolfram:
	""" 
	Process jobs that request to query the wolfram alpha database.

	"""
	def __init__(self, speaker, key):
		self.speaker = speaker
		self.key = key

	def process(self, job, controller):
		"""Process the Wolfram Alpha job request."""
		if job.get_is_processed(): 
			return False

		if not self.key:
			self.speaker.say("Please provide an API key to query Wolfram Alpha.")
			return False

		response = self.query(job.recorded(), self.key)
		
		if response.find('No results') != -1:
			return False
		elif response == "Pulling up visual.":
			self.speaker.say(response)
			self.open(False, job.recorded(), controller)
		else:
			self.speaker.say(response)

		job.is_processed = True
		return True

	def query(self, phrase, key):
		"""Send job query to WolframAlpha for a text or visual response."""
		phrase = phrase.replace(' ', '%20')
		w_url = "http://api.wolframalpha.com/v2/query?input=" + phrase + "&appid=" + key
		xml_data = urllib2.urlopen(w_url).read()
		root = ET.fromstring(xml_data)

		# Parse response
		try:
			pods = root.findall('.//pod')
			if pods == []:
				raise StopIteration()

			# if first and second pods are input interpretation and response, stop and ignore
			if pods[0].attrib['title'] == "Input interpretation" and \
				pods[1].attrib['title'] == "Response":
				raise StopIteration()

			for pod in pods:
				# skip input human response (we are doing that ourselves) and input interpretation
				if pod.attrib['title'] != "Response" and \
					pod.attrib['title'] != "Input interpretation":
					plaintexts = pod.findall('.//plaintext')
					text = plaintexts[0].text
					if text is not None and len(text) < 100: 	
						return "the answer is " + \
							text.replace("°", ' degrees ').encode('ascii', 'ignore')
					else:
						return "Pulling up visual."

		except StopIteration:
			return "No results"

	def open(self, wolfram, text, controller):
		"""Open webpage of visual WolframAlpha result."""
		wolfram_url = "http://www.wolframalpha.com/input/?i=" + text.replace(" ", "+")
		controller.open(wolfram_url)

########NEW FILE########
__FILENAME__ = youtube
from urllib2 import urlopen
import json


class Youtube:
	"""
	Processes jobs requesting to interact with YouTube.

	"""
	def __init__(self, speaker):
		self.speaker = speaker

	def process(self, job, controller):
		"""Process Youtube job request."""
		self.speaker.say("Playing video.")

		if job.get_is_processed():
			return False
			
		result = self.get_first_video(job.query, controller)
		job.is_processed = True

	# get the URL of the first video and open in firefox
	def get_first_video(self, phrase, controller):
		"""Open webpage of first Youtube video from search to play it."""
		y_url = "http://gdata.youtube.com/feeds/api/videos?max-results=1&alt=json&orderby=relevance&q="
		url = y_url + phrase.replace(" ", "+")
		inp = urlopen(url)
		resp = json.load(inp)
		inp.close()

		first = resp['feed']['entry'][0]
		url = first['link'][0]['href']
		controller.open(url)

	def search(self, job, controller):
		"""Open webpage of Youtube search results based on job text."""
		self.speaker.say("Pulling up youtube results.")
		y_url = "http://www.youtube.com/results?search_query="
		phrase = job.query
		url = y_url + phrase.replace(" ", "+")
		controller.open(url)
	



########NEW FILE########
__FILENAME__ = brain
from voicecmd import VoiceCommand
from inputs.microphone import Microphone
from ex.exception import NotUnderstoodException
from ex.exception import ConnectionLostException

import tts
import stt
import sys
import subprocess
import os

# natural voice command parsing keywords
T_KEYS = ['google', 'youtube', 'search', 'open', 'computer', 'radio', 'video']
I_KEYS = ['news','screenshot']
ACTION_VERBS = ['search', 'look', 'pull', 'get', 'give']
PREPOSITIONS = ['for', 'on', 'of']


class Job:
	"""
	Store text converted from recorded voice input, 
	and a boolean describing the job's state of whether 
	or not it has been processed. Job instances are 
	processed through the VoiceCommand class.
	
	"""
	def __init__(self, recorded_text):
		self.recorded_text = recorded_text
		self.query = ""
		self.is_processed = False

	def get_is_processed(self):
		""" 
		Return whether the job has been processed 
		through the VoiceCommand process or not.
		
		"""
		return self.is_processed

	def recorded(self):
		"""
		Return the text version of audio input 
		interpreted by the Google text to speech engine.

		"""
		return self.recorded_text

	def set_query(self, query):
		"""
		Set the query of the job, extracted from recorded text 
		by Brain.classify_job(). 

		"""
		self.query = query

	def query(self):
		"""Return the query associated with the job."""
		return self.query


class Brain:
	"""
	Initialize everything EVE needs to function, 
	listen for activation input from pocketsphinx, 
	and execute commands based on voice input.
	The Brain class coordinates all other components
	of EVE.
	
	"""
	def __init__(self):
		self.speaker = tts.Google()
		self.voice_cmd = VoiceCommand(self.speaker)
		self.print_welcome()

		print "Saying: Hello there!"
		self.speaker.play_wav("./wav/hello.wav")

	def print_welcome(self):
		"""
		Print welcome message in terminal when E.V.E. first starts up
		and initializes the Brain class.
		
		"""
		welcome_message =  """
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+++++++++++++++++++++  Welcome to E.V.E.  ++++++++++++++++++++++
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
+                                                              +
+                 Say 'okay computer' to start!                +
+                                                              +
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
	"""
		print welcome_message

################################################################################

	def process_input(self, line, proc):
		"""
		Take input text and extract activation commands
		from it if they exist.
		
		"""
		startstring = 'sentence1: <s> '
		endstring = ' </s>'

		line = line.lower()
		if not line:
			return False

		if 'missing phones' in line:
			sys.exit('Error: Missing phonemes for the used grammar file.')

		if line.startswith(startstring) and line.strip().endswith(endstring):
			phrase = line.strip('\n')[len(startstring):-len(endstring)]
			return self.parse(phrase, proc)

	def parse(self, phrase, proc):
		"""
		Identify activation commands from input 
		extracted by the 'process_input' function and
		call the appropriate function for a given command.
		
		"""
		params = phrase.split()
		if params == ['okay', 'computer']:
			if proc is not None:
				proc.kill()
			self.okaycomputer()

		elif params == ['computer', 'lets', 'talk']:
			if proc is not None:
				proc.kill()
			self.conversation()

		elif params == ['computer', 'shut', 'down']:
			if proc is not None:
				proc.kill()
			self.shutdown()

		elif params == ['computer', 'go', 'sleep']:
			if proc is not None:
				proc.kill()
			self.sleep()
		else: 
			return False

		return True

	def okaycomputer(self):
		"""
		Start recording and listening for a voice command
		if internet connection is available.

		"""
		print "Activating..."
		# ensure that internet connection is available
		if not self.speaker.say("Yes?"): 
			return 
		self.listen(False) # False for not conversation mode

	def conversation(self):
		"""Start a conversation with E.V.E."""
		print "Activating..."
		# ensure that internet connection is available
		if not self.speaker.say("Okay, what do you want to talk about?"):
			return
		while 1:
			self.listen(True) # True for conversation mode

	def shutdown(self):
		"""Close the E.V.E. program."""
		# TODO turn into local wav file
		self.speaker.say("E.V.E. will shut down now. Goodbye!")
		sys.exit('+++++++++++++++++++++  E.V.E. HAS SHUTDOWN  ++++++++++++++++++++')
		
	def sleep(self):
		"""Puts E.V.E. to sleep."""
		self.speaker.say("E.V.E. will go to sleep now. Wake me when you need me!")
		print('+++++++++++++++  E.V.E. IS IN SLEEP MODE  ++++++++++++++')
		os.system("python idle.py")
		sys.exit(1) # does this script terminate before idle.py terminates?
################################################################################

	def listen(self, conversation):
		"""Initiate listening for voice commands."""
		self.audioInput = Microphone()
		self.audioInput.listen()
		job = self.set_job()
		
		if job is None:
			return

		if conversation is False:
			self.classify_job(job)
		else: 
			if job.recorded().find("no stop") != -1:
				self.speaker.say("Ending conversation. It was nice talking to you!")
				sys.exit(1)
			
			self.execute_voice_cmd(job, "computer", job.query)

	def set_job(self):
		"""
		Send audio input to Google's Speech to text
		engine to be interpreted, and then init a Job class 
		with the returned text if successful. 

		"""
		speech_to_text = stt.Google(self.audioInput)
		try:
			recorded_text = speech_to_text.get_text().lower()
			return Job(recorded_text)
		except NotUnderstoodException:
			print "Sorry, I didn't get that."
			self.speaker.play_wav("./wav/didntget.wav")
			return None
		except ConnectionLostException:
			print "No connection."
			self.speaker.play_wav("./wav/internet_err.wav")
			return None

	def classify_job(self, job):
		"""
		Match keywords and keyword order with 
		words in the job to classify which voice command 
		the job requires.

		"""
		action_verb = "" 
		command_type = ""
		t_key = "" 
		i_key = ""
		preposition = ""
		query = ""

		words = job.recorded().split()
		for word in words:
			# set action verb if it comes before any other goalpost
			if word in ACTION_VERBS and action_verb == "" and t_key == "":
				action_verb = word 
			# set t_key if it comes before any other t_key
			elif word in T_KEYS and t_key == "":
				t_key = word
				command_type = word
			# set i_key if it comes before any other key
			elif word in I_KEYS and t_key == "" and i_key == "":
				i_key = word
				command_type = word
			# find prepositions in cases such as "youtube video of" or "google for"
			elif word in PREPOSITIONS and t_key != "":
				preposition = word
			# catch the stop recording case
			elif word == "no" and words[words.index(word) + 1] == "stop":
				print "Accidental recording"
				command_type = "no stop"
				break

		# get query if it exists
		if command_type not in I_KEYS and \
			command_type != "" and command_type != "no stop": 
			if preposition == "":
				query_list = words[words.index(command_type) + 1:]
			else:
				query_list = words[words.index(preposition) + 1:]
			query = ' '.join(query_list)
			job.set_query(query)
		
		self.execute_voice_cmd(job, command_type, query)

	def execute_voice_cmd(self, job, command_type, query):
		"""
		Execute the method in the VoiceCommand class 
		that is associated with the classified command type.

		"""
		if command_type == "no stop":
			self.voice_cmd.accidental_recording()

		elif command_type == "open":
			if query != "":
				self.voice_cmd.open_webpage(job)
			else:
				self.speaker.say("no webpage specified.")

		elif command_type == "google" or command_type == "search":
			if query != "":
				self.voice_cmd.search(job)
			else: 
				self.speaker.say("no query provided.")

		elif command_type == "youtube" or command_type == "video":
			if query != "":
				# TODO there are flaws with this method of differentiating
				# between search and play for youtube. Improve method.
				if job.recorded().find('search') != -1: 
					self.voice_cmd.search_youtube(job)
				else: 
					self.voice_cmd.play_youtube(job)
			else:
				self.speaker.say("no query provided.")

		elif command_type == "screenshot": 
			self.voice_cmd.take_screenshot()

		elif command_type == "computer":
			self.voice_cmd.chatbot_respond(job)

		elif command_type == "news": 
			self.voice_cmd.get_news(job)

		elif command_type == "radio":
			self.voice_cmd.play_music(job)

		else:
			self.voice_cmd.ask_wolfram(job)


		if not job.get_is_processed:
			self.speaker.say("Sorry, I didn't find any results.")



########NEW FILE########
__FILENAME__ = voicecmd

from actions.screenshot import Screenshot
from actions.youtube import Youtube
from actions.wolfram import Wolfram
from actions.music import Music
from actions.news import News
from actions.webpage import Webpage
from actions.chatbot import Chatbot
from actions.search import Search
from actions.actions_helper import ActionsHelper

import webbrowser
import os


class VoiceCommand:
	"""
	Distribute jobs to the appropriate action.

	"""
	def __init__(self, speaker):
		self.speaker = speaker
		self.controller = webbrowser.get()

		# initialize action class instances
		self.Chatbot = Chatbot(self.speaker)
		self.Youtube = Youtube(self.speaker)

		self.Helper = ActionsHelper(self.speaker)
		self.Webpage = Webpage(self.speaker, self.Helper)
		self.News = News(self.speaker, self.Helper)
		self.Search = Search(self.speaker, self.Helper)
		self.Screenshot = Screenshot(self.speaker, self.Helper)
		self.Music = Music(self.speaker, self.Helper)

		self.Wolfram = Wolfram(self.speaker, os.environ.get('WOLFRAM_API_KEY'))

	def accidental_recording(self):
		"""Started recording by accident, just post message."""
		print "---Accidental recording---"
		print "Saying: Oops, sorry."
		self.speaker.play_wav("./wav/sorry.wav")

	def open_webpage(self, job):
		"""Send to open webpage action; if no page found, search."""
		if self.Webpage.process(job, self.controller) != True:
			self.Search.process(job, self.controller)

	def search(self, job):
		"""Send to web search action."""
		self.Search.process(job, self.controller)

	def search_youtube(self, job):
		"""Send to search youtube action."""
		self.Youtube.search(job, self.controller)

	def play_youtube(self, job):
		"""Send to play first youtube video from search action."""
		self.Youtube.process(job, self.controller)

	def take_screenshot(self):
		"""Send to take screenshot action."""
		self.Screenshot.take()

	def chatbot_respond(self, job):
		"""Send to chatbot to respond action."""
		self.Chatbot.process(job)

	def get_news(self, job):
		"""Send to open news action."""
		self.News.process(job, self.controller)

	def ask_wolfram(self, job):
		"""
		Send to WolframAlpha for a response. 
		If no response is found, send to chatbot for response.

		"""
		if not self.Wolfram.process(job, self.controller):
			self.chatbot_respond(job)

	def play_music(self, job):
		"""Send to play radio action."""
		self.Music.process(job, self.controller)
########NEW FILE########
__FILENAME__ = loadbrain
#!/usr/bin/python
# -*- coding: utf-8 -*-

# load a new brain after updating aiml files.

import aiml
import os

CHATBOT_CONFIG = "./chatbot_config.txt"
AIML_SET = "./aiml_set/"

def main():
	AI = aiml.Kernel()
		
	AI.learn(AIML_SET + "reduction0.safe.aiml")
	AI.learn(AIML_SET + "reduction1.safe.aiml")
	AI.learn(AIML_SET + "reduction2.safe.aiml")
	AI.learn(AIML_SET + "reduction3.safe.aiml")
	AI.learn(AIML_SET + "reduction4.safe.aiml")
	AI.learn(AIML_SET + "reductions-update.aiml")

	AI.learn(AIML_SET + "mp0.aiml")
	AI.learn(AIML_SET + "mp1.aiml")
	AI.learn(AIML_SET + "mp2.aiml")
	AI.learn(AIML_SET + "mp3.aiml")
	AI.learn(AIML_SET + "mp4.aiml")
	AI.learn(AIML_SET + "mp5.aiml")
	AI.learn(AIML_SET + "mp6.aiml")

	for subdirs, dirs, files in os.walk(AIML_SET):
		for f in files:
			if f.find('aiml') != -1 or f.find('mp') != -1 or f.find('reduction') != -1:
				AI.learn(AIML_SET + f)


	AI.saveBrain("./standard.brn")

	try: 
		f = open(CHATBOT_CONFIG)
	except IOError:
		self.speaker.say("Error: chatbot configuration file not found.")
		sys.exit(1)

	bot_predicates = f.readlines()
	f.close()
	for bot_predicate in bot_predicates:
		key_value = bot_predicate.split('::')
		if len(key_value) == 2:
			AI.setBotPredicate(key_value[0], key_value[1].rstrip('\n'))

	# Loop forever, reading stdin and printing responses
	while 1: 
		print AI.respond(raw_input("> "))
    
if __name__ == '__main__':
	main()
########NEW FILE########
__FILENAME__ = eve
#!/usr/bin/python
# -*- coding: utf-8 -*-

from brain.brain import Brain
import getopt

import subprocess
import sys

JULIUS_FILE = "./data/julius/julian.jconf"

def main():
	try:
		opts, args = getopt.getopt(sys.argv[1:], "hs",)
	except getopt.GetoptError:
		usage()

	# NOTE current functionality does not require for loop
	if opts == []:
		start_listening()
	else:
		for opt in opts:
			opt = opt[0]
			if opt == '-h':
				usage()
			elif opt == '-s':	
				start_text_prompt()

			# break will be removed when/if greater functionality 
			# with cmdline args is required. 
			break

def start_listening():
	"""Initialize the program and start listening for activation commands."""
	brn = Brain()
	proc = subprocess.Popen(['padsp', 'julius', '-quiet', 
			'-input', 'mic', 
			'-C', JULIUS_FILE], 
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

	while 1: 
		line = proc.stdout.readline()
		if brn.process_input(line, proc) == True:
			proc = subprocess.Popen(['padsp', 'julius', '-quiet', 
				'-input', 'mic', 
				'-C', JULIUS_FILE], 
				stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		sys.stdout.flush()

def start_text_prompt():
	"""Initialize the program and open text prompt for activation commands."""
	brn = Brain()
	print "Starting standard input mode."
	while 1:
		line = raw_input("> ")
		brn.process_input(line, None)

def usage():
	"""Print usage / help message."""
	usage = """
		Usage: python eve.py [options]

		-h		Prints this message and exits.
		-s		Reads from stdin instead of using pocketsphinx for activation.

		Please report bugs to thomasweng15 on github.com.
	"""
	print usage
	sys.exit(1)


if __name__ == '__main__':
	main()
	
	

########NEW FILE########
__FILENAME__ = exception
class NotUnderstoodException(Exception):
    pass

class NoResultsFoundException(Exception):
    pass

class ConnectionLostException(Exception):
	pass

########NEW FILE########
__FILENAME__ = idle
#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import subprocess
import os

JULIUS_FILE = "./data/julius/julian.jconf"

def main():
	startstring = 'sentence1: <s> '
	endstring = ' </s>'

	proc = subprocess.Popen(['padsp', 'julius', '-quiet', 
			'-input', 'mic', 
			'-C', JULIUS_FILE], 
			stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

	print "Say 'computer wake up' to turn E.V.E. on."

	while 1:
		line = proc.stdout.readline().lower()

		if not line:
			continue

		if 'missing phones' in line:
			sys.exit('Error: Missing phonemes for the used grammar file.')

		if line.startswith(startstring) and line.strip().endswith(endstring):
			line = line.strip('\n')[len(startstring):-len(endstring)]
			params = line.split()
			if params == ['computer', 'wake', 'up']:
				print "Waking up..."
				proc.kill()
				os.system("python eve.py")
				sys.exit(1)

if __name__ == '__main__':
	main()
	
########NEW FILE########
__FILENAME__ = microphone
from array import array
from struct import pack

import tempfile
import pyaudio
import sys
import wave
import os


THRESHOLD = 2000
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
SILENCE_DURATION = 40 # end recording after period of silence reaches this value
WAIT_DURATION = 300 # end recording if no input before this value is reached
SPEECH_DURATION = 300 # end recording if too much input

class Microphone:
	"""
	Control all aspects of recording and receiving input 
	from the microphone.
	
	"""
	def __init__(self):
		self.recordedWavFilename = ""

	def listen(self):
		"""Record speech and store in a temporary file."""
		(_, rec_wav_filename) = tempfile.mkstemp('.wav')

		sample_width, data = self.record()
		data = pack('<' + ('h'*len(data)), *data)

		wf = wave.open(rec_wav_filename, 'wb')
		wf.setnchannels(CHANNELS)
		wf.setsampwidth(sample_width)
		wf.setframerate(RATE)
		wf.writeframes(b''.join(data))
		wf.close()

		self.recordedWavFilename = rec_wav_filename
		return self.recordedWavFilename

	def rate(self):
		"""Return recording rate."""
		return RATE

	def filename(self):
		"""Return temp file storing speech recording."""
		return self.recordedWavFilename

	def housekeeping(self):
		"""Delete temp file when it is no longer needed."""
		os.remove(self.recordedWavFilename)

	def is_silent(self, sound_data):
		"""Check if speech volume is below silence threshold."""
		return max(sound_data) < THRESHOLD

	def add_silence(self, sound_data, seconds):
		"""Pad end of speech recording with silence."""
		r = array('h', [0 for i in xrange(int(seconds*RATE))])
		r.extend(sound_data)
		r.extend([0 for i in xrange(int(seconds*RATE))])
		return r

	def record(self):
		"""Open pyaudio stream and record audio from mic."""
		p = pyaudio.PyAudio()
		stream = p.open(format = FORMAT,
						channels = CHANNELS, 
						rate = RATE, 
						input = True, 
						frames_per_buffer = CHUNK)
		print("* recording")

		speech_started = False
		speech = 0
		silence_before_speech = 0
		silence_after_speech = 0
		r = array('h')

		while 1:
			sound_data = array('h', stream.read(CHUNK))
			if sys.byteorder == 'big':
				sound_data.byteswap()
			r.extend(sound_data)

			silent = self.is_silent(sound_data)

			if speech_started:
				if silent:
					silence_after_speech += 1
				elif not silent:
					silence_after_speech = 0
					speech += 1

				# break after a period of silence
				if silence_after_speech > SILENCE_DURATION:
					break
				# break after too much input
				if speech > SPEECH_DURATION:
					break
			else: 
				if silent:
					silence_before_speech += 1
				elif not silent: 
					speech_started = True
				# break if no input
				if silence_before_speech > WAIT_DURATION:
					print("Warning: no input. Increase the volume on your mic.")
					break

		print("* done recording")

		sample_width = p.get_sample_size(FORMAT)
		stream.stop_stream() 
		stream.close()
		p.terminate()

		r = self.add_silence(r, 0.5)
		return sample_width, r
########NEW FILE########
__FILENAME__ = google
from ex.exception import NotUnderstoodException
from ex.exception import ConnectionLostException
from pydub import AudioSegment

import tempfile
import requests
import json
import os


class Google:
	"""
	Use the Google Speech-to-Text service
	to translate voice input into text
	so that it can be parsed by the program.

	"""
	def __init__(self, audio, rate = 44100):
		self.audio = audio
		self.rec_rate = audio.rate() if audio.rate() else rate
		self.text = None

	def get_text(self):
		"""Send speech file to Google STT and then return text"""
		# convert wav file to FLAC
		(_,stt_flac_filename) = tempfile.mkstemp('.flac')
		sound = AudioSegment.from_wav(self.audio.filename())
		sound.export(stt_flac_filename, format="flac")

		# send to Google to interpret into text
		g_url = "http://www.google.com/speech-api/v1/recognize?lang=en"
		headers = {'Content-Type': 'audio/x-flac; rate= %d;' % self.rec_rate}
		recording_flac_data = open(stt_flac_filename, 'rb').read()
		try:
			r = requests.post(g_url, data=recording_flac_data, headers=headers)
		except requests.exceptions.ConnectionError:
			raise ConnectionLostException()
		
		response = r.text
		os.remove(stt_flac_filename)
		self.audio.housekeeping()

		if not 'hypotheses' in response:
			raise NotUnderstoodException()

		# we are only interested in the most likely utterance
		phrase = json.loads(response)['hypotheses'][0]['utterance']
		print "Heard: " + phrase
		return str(phrase)





########NEW FILE########
__FILENAME__ = google
from pydub import AudioSegment

import wave
import tempfile
import requests
import os


class Google:
	"""
	Use the Google Text-to-Speech service to give EVE
	the ability to speak. 
	
	"""
	def say(self, text):
		"""Speak text string by converting to wav and then playing it"""
		wav_file = self.convert_text_to_wav(text)
		if wav_file == False:
			return False
		print "Saying: " + text
		self.play_wav(wav_file)
		os.remove(wav_file)
		return True

	def convert_text_to_wav(self, text):
		"""Convert text string into wav file."""
		if len(text) == 0:
			self.say("Sorry, I don't know.")
			return False

		if len(text) >= 100:
			self.say("The result is too long for me to read.")
			print "Result: " + text
			return False

		# query google text to speech to convert text, store result in temp mp3
		(_,tts_mp3_filename) = tempfile.mkstemp('.mp3')
		r_url = "http://translate.google.com/translate_tts?ie=utf-8&tl=en&q=" \
				+ text.replace(" ", "+")
		try:
			r = requests.get(r_url)
		except requests.exceptions.ConnectionError:
			print "Error: No connection or connection timed out."
			self.play_wav("./wav/internet_err.wav")
			os.remove(tts_mp3_filename)
			return False
		f = open(tts_mp3_filename, 'wb')
		f.write(r.content) 
		f.close()

		# convert mp3 file into wav using pydub
		(_,tts_wav_filename) = tempfile.mkstemp('.wav')
		sound = AudioSegment.from_mp3(tts_mp3_filename)
		sound.export(tts_wav_filename, format="wav")
		os.remove(tts_mp3_filename)
		return tts_wav_filename

	def play_wav(self, filename): 
		"""Plays wav file specified in filename."""
		os.system("aplay -q " + filename)

########NEW FILE########
