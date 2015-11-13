__FILENAME__ = bingsearch
import string
import httplib, sys
import parser
import re
import time

class search_bing:
	def __init__(self,word,limit,start):
		self.word=word.replace(' ', '%20')
		self.results=""
		self.totalresults=""
		self.server="www.bing.com"
		self.apiserver="api.search.live.net"
		self.hostname="www.bing.com"
		self.userAgent="(Mozilla/5.0 (Windows; U; Windows NT 6.0;en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6"
		self.quantity="100"
		self.limit=int(limit)
		self.bingApi=""
		self.counter=start
		
	def do_search(self):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "/search?q=" + self.word + "&first="+ str(self.counter))
		h.putheader('Host', self.hostname)
		h.putheader('Cookie: SRCHHPGUSR=ADLT=OFF&NRSLT=100')
		h.putheader('Accept-Language: en-us,en')
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results

	def do_search_api(self):
		h = httplib.HTTP(self.apiserver)
		h.putrequest('GET', "/xml.aspx?Appid="+ self.bingApi + "&query=%40" + self.word +"&sources=web&web.count=40&web.offset="+str(self.counter))
		h.putheader('Host', "api.search.live.net")
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results
	
	def do_search_vhost(self):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "/search?q=ip:" + self.word + "&go=&count=50&FORM=QBHL&qs=n&first="+ str(self.counter))
		h.putheader('Host', self.hostname)
		h.putheader('Cookie: mkt=en-US;ui=en-US;SRCHHPGUSR=NEWWND=0&ADLT=DEMOTE&NRSLT=50')
		h.putheader('Accept-Language: en-us,en')
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results
				
	def get_emails(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.emails()
	
	def get_hostnames(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.hostnames()
	
	def get_allhostnames(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.hostnames_all()
	
	
	def process(self,api):
		if api=="yes":
				if self.bingApi=="":
					print "Please insert your API key in the discovery/bingsearch.py"
					sys.exit()
		while (self.counter < self.limit):
			if api=="yes":
				self.do_search_api()
				time.sleep(0.3)	
			else:
				self.do_search()
				time.sleep(1)
			self.counter+=100
			print "\tSearching "+ str(self.counter) + " results..."

	def process_vhost(self):
		while (self.counter < self.limit):#Maybe it is good to use other limit for this.
			self.do_search_vhost()
			self.counter+=100

########NEW FILE########
__FILENAME__ = exaleadsearch
import string
import httplib, sys
import parser
import re
import time

class search_exalead:
	def __init__(self,word,limit,start):
		self.word=word
		self.files="pdf"
		self.results=""
		self.totalresults=""
		self.server="www.exalead.com"
		self.hostname="www.exalead.com"
		self.userAgent="(Mozilla/5.0 (Windows; U; Windows NT 6.0;en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6"
		self.limit=limit
		self.counter=start
		
	def do_search(self):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "/search/web/results/?q=%40"+ self.word + "&elements_per_page=100&start_index="+str(self.counter))
		h.putheader('Host', self.hostname)
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results

	def do_search_files(self,files):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "search/web/results/?q="+ self.word + "filetype:"+ self.files +"&elements_per_page=100&start_index="+self.counter)
		h.putheader('Host', self.hostname)
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results

	def check_next(self):
		renext = re.compile('topNextUrl')
		nextres=renext.findall(self.results)	
		if nextres !=[]:
			nexty="1"
			print str(self.counter)
		else:
			nexty="0"
		return nexty
		
	def get_emails(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.emails()
	
	def get_hostnames(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.hostnames()
	
	def get_files(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.fileurls(self.files)
	

	def process(self):
		while self.counter <= self.limit:
			self.do_search()
			self.counter+=100
			print "\tSearching " + str(self.counter) + " results..."
			
				
	def process_files(self,files):
		while self.counter < self.limit:
			self.do_search_files(files)
			time.sleep(1)
			more = self.check_next()
			if more == "1":
				self.counter+=100
			else:
				break


########NEW FILE########
__FILENAME__ = googlesearch
import string
import httplib, sys
import parser
import re
import time

class search_google:
	def __init__(self,word,limit,start):
		self.word=word
		self.files="pdf"
		self.results=""
		self.totalresults=""
		self.server="www.google.com"
		self.hostname="www.google.com"
		self.userAgent="(Mozilla/5.0 (Windows; U; Windows NT 6.0;en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6"
		self.quantity="100"
		self.limit=limit
		self.counter=start
		
	def do_search(self):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "/search?num="+self.quantity+"&start=" + str(self.counter) + "&hl=en&meta=&q=%40\"" + self.word + "\"")
		h.putheader('Host', self.hostname)
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results

	def do_search_files(self,files):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "/search?num="+self.quantity+"&start=" + str(self.counter) + "&hl=en&meta=&q=filetype:"+files+"%20site:" + self.word)
		h.putheader('Host', self.hostname)
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results

	def do_search_profiles(self):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', '/search?num='+ self.quantity + '&start=' + str(self.counter) + '&hl=en&meta=&q=site:www.google.com%20intitle:"Google%20Profile"%20"Companies%20I%27ve%20worked%20for"%20"at%20' + self.word + '"')
		h.putheader('Host', self.hostname)
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results
	
				
	def check_next(self):
		renext = re.compile('>  Next  <')
		nextres=renext.findall(self.results)	
		if nextres !=[]:
			nexty="1"
		else:
			nexty="0"
		return nexty
		
	def get_emails(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.emails()
	
	def get_hostnames(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.hostnames()
	
	def get_files(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.fileurls(self.files)
	
	def get_profiles(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.profiles()
	


	def process(self):
		while self.counter <= self.limit:
			self.do_search()
			more = self.check_next()
			time.sleep(1)
			self.counter+=100
			print "\tSearching "+ str(self.counter) + " results..."
				
	def process_files(self,files):
		while self.counter <= self.limit:
			self.do_search_files(files)
			time.sleep(1)
			self.counter+=100
			print "\tSearching "+ str(self.counter) + " results..."

	def process_profiles(self):
		while self.counter < self.limit:
			self.do_search_profiles()
			time.sleep(0.3)
			more = self.check_next()
			if more == "1":
				self.counter+=100
			else:
				break
	

########NEW FILE########
__FILENAME__ = linkedinsearch
import string
import httplib, sys
import parser
import re

class search_linkedin:
	def __init__(self,word,limit):
		self.word=word.replace(' ', '%20')
		self.results=""
		self.totalresults=""
		self.server="www.google.com"
		self.hostname="www.google.com"
		self.userAgent="(Mozilla/5.0 (Windows; U; Windows NT 6.0;en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6"
		self.quantity="100"
		self.limit=int(limit)
		self.counter=0
		
	def do_search(self):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "/search?num=100&start=" + str(self.counter) + "&hl=en&meta=&q=site%3Alinkedin.com%20" + self.word)
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results

	def check_next(self):
		renext = re.compile('>  Next  <')
		nextres=renext.findall(self.results)
		if nextres !=[]:
			nexty="1"
		else:
			nexty="0"
		return nexty
		
	def get_people(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.people_linkedin()
	
	def process(self):
		while (self.counter < self.limit):
			self.do_search()
			more = self.check_next()
			if more == "1":
				self.counter+=100
			else:
				break

########NEW FILE########
__FILENAME__ = pgpsearch
import string
import httplib, sys
import parser

class search_pgp:
	def __init__(self,word):
		self.word=word
		self.results=""
		self.server="pgp.rediris.es:11371"
		self.hostname="pgp.rediris.es"
		self.userAgent="(Mozilla/5.0 (Windows; U; Windows NT 6.0;en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6"
		
	def process(self):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "/pks/lookup?search=" + self.word + "&op=index")
		h.putheader('Host', self.hostname)
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		
		
	def get_emails(self):
		rawres=parser.parser(self.results,self.word)
		return rawres.emails()
	
	def get_hostnames(self):
		rawres=parser.parser(self.results,self.word)
		return rawres.hostnames()
	
	

########NEW FILE########
__FILENAME__ = yandexsearch
import string
import httplib, sys
import parser
import re
import time

class search_yandex:
	def __init__(self,word,limit,start):
		self.word=word
		self.results=""
		self.totalresults=""
		self.server="yandex.com"
		self.hostname="yandex.com"
		self.userAgent="(Mozilla/5.0 (Windows; U; Windows NT 6.0;en-US; rv:1.9.2) Gecko/20100115 Firefox/3.6"
		self.limit=limit
		self.counter=start
		
	def do_search(self):
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "/search?text=%40"+ self.word + "&numdoc=50&lr="+str(self.counter))
		h.putheader('Host', self.hostname)
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results
		print self.results

	def do_search_files(self,files): #TODO
		h = httplib.HTTP(self.server)
		h.putrequest('GET', "/search?text=%40"+ self.word + "&numdoc=50&lr="+str(self.counter))
		h.putheader('Host', self.hostname)
		h.putheader('User-agent', self.userAgent)	
		h.endheaders()
		returncode, returnmsg, headers = h.getreply()
		self.results = h.getfile().read()
		self.totalresults+= self.results

	def check_next(self):
		renext = re.compile('topNextUrl')
		nextres=renext.findall(self.results)	
		if nextres !=[]:
			nexty="1"
			print str(self.counter)
		else:
			nexty="0"
		return nexty
		
	def get_emails(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.emails()
	
	def get_hostnames(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.hostnames()
	
	def get_files(self):
		rawres=parser.parser(self.totalresults,self.word)
		return rawres.fileurls(self.files)
	

	def process(self):
		while self.counter <= self.limit:
			self.do_search()
			self.counter+=50
			print "Searching " + str(self.counter) + " results..."
			
				
	def process_files(self,files):
		while self.counter < self.limit:
			self.do_search_files(files)
			time.sleep(0.3)
			self.counter+=50

########NEW FILE########
__FILENAME__ = hostchecker
#!/usr/bin/env python
# encoding: utf-8
"""
Created by laramies on 2008-08-21.
"""

import sys
import socket

class Checker():
	def __init__(self, hosts):
		self.hosts = hosts
		self.realhosts=[]

	def check(self):
	 	for x in self.hosts:
			try:
				res=socket.gethostbyname(x)
				self.realhosts.append(res+":"+x)	
			except Exception, e:
				pass
		return self.realhosts
		

########NEW FILE########
__FILENAME__ = parser
import string
import re

class parser:
	def __init__(self,results,word):
		self.results=results
		self.word=word
		self.temp=[]
		
	def genericClean(self):
		self.results = re.sub('<em>', '', self.results)
		self.results = re.sub('<b>', '', self.results)
		self.results = re.sub('</b>', '', self.results)
		self.results = re.sub('</em>', '', self.results)
		self.results = re.sub('%2f', ' ', self.results)
		self.results = re.sub('%3a', ' ', self.results)
		self.results = re.sub('<strong>', '', self.results)
		self.results = re.sub('</strong>', '', self.results)


		for e in ('>',':','=', '<', '/', '\\',';','&','%3A','%3D','%3C'):
			self.results = string.replace(self.results, e, ' ')
			
	def urlClean(self):
		self.results = re.sub('<em>', '', self.results)
		self.results = re.sub('</em>', '', self.results)
		self.results = re.sub('%2f', ' ', self.results)
		self.results = re.sub('%3a', ' ', self.results)
		for e in ('<','>',':','=',';','&','%3A','%3D','%3C'):
			self.results = string.replace(self.results, e, ' ')
		
	def emails(self):
		self.genericClean()
		reg_emails = re.compile('[a-zA-Z0-9.-_]*' + '@' + '[a-zA-Z0-9.-]*' + self.word)
		self.temp = reg_emails.findall(self.results)
		emails=self.unique()
		return emails
	
	def fileurls(self,file):
		urls=[]
		reg_urls = re.compile('<a href="(.*?)"')
		self.temp = reg_urls.findall(self.results)
		allurls=self.unique()
		for x in allurls:
			if x.count('webcache') or x.count('google.com') or x.count('search?hl'):
				pass
			else:
				urls.append(x)
		return urls
	
	def people_linkedin(self):
		reg_people = re.compile('">[a-zA-Z0-9._ -]* profiles | LinkedIn')
		
		self.temp = reg_people.findall(self.results)
		resul = []
		for x in self.temp:
				y = string.replace(x, '  LinkedIn', '')
				y = string.replace(y, ' profiles ', '')
				y = string.replace(y, 'LinkedIn', '')
				y = string.replace(y, '"', '')
				y = string.replace(y, '>', '')
				if y !=" ":
					resul.append(y)
		return resul

	def profiles(self):
		reg_people = re.compile('">[a-zA-Z0-9._ -]* - <em>Google Profile</em>')
		self.temp = reg_people.findall(self.results)
		resul = []
		for x in self.temp:
				y = string.replace(x, ' <em>Google Profile</em>', '')
				y = string.replace(y, '-', '')
				y = string.replace(y, '">', '')
				if y !=" ":
					resul.append(y)
		return resul
	
	
	def hostnames(self):
		self.genericClean()
		reg_hosts = re.compile('[a-zA-Z0-9.-]*\.'+ self.word)
		self.temp = reg_hosts.findall(self.results)
		hostnames=self.unique()
		return hostnames

	def hostnames_all(self):
		reg_hosts = re.compile('<cite>(.*?)</cite>')
		temp = reg_hosts.findall(self.results)
		for x in temp:
			if x.count(':'):
				res=x.split(':')[1].split('/')[2]
			else:
				res=x.split("/")[0]
			self.temp.append(res)
		hostnames=self.unique()
		return hostnames
		
	def unique(self):
		self.new=[]
		for x in self.temp:
			if x not in self.new:
				self.new.append(x)
		return self.new

########NEW FILE########
__FILENAME__ = theHarvester
#!/usr/bin/env python

import string
import httplib, sys
from socket import *
import re
import getopt
from discovery import *
import hostchecker


print "\n*************************************"
print "*TheHarvester Ver. 2.0 (reborn)     *"
print "*Coded by Christian Martorella      *"
print "*Edge-Security Research             *"
print "*cmartorella@edge-security.com      *"
print "*************************************\n\n"

def usage():

 print "Usage: theharvester options \n"
 print "       -d: Domain to search or company name"
 print "       -b: Data source (google,bing,bingapi,pgp,linkedin,google-profiles,exalead,all)"
 print "       -s: Start in result number X (default 0)"
 print "       -v: Verify host name via dns resolution and search for vhosts(basic)"
 print "       -l: Limit the number of results to work with(bing goes from 50 to 50 results,"
 print "            google 100 to 100, and pgp does'nt use this option)"
 print "       -f: Save the results into an XML file"
 print "\nExamples:./theharvester.py -d microsoft.com -l 500 -b google"
 print "         ./theharvester.py -d microsoft.com -b pgp"
 print "         ./theharvester.py -d microsoft -l 200 -b linkedin\n"


def start(argv):
	if len(sys.argv) < 4:
		usage()
		sys.exit()
	try :
	       opts, args = getopt.getopt(argv, "l:d:b:s:v:f:")
	except getopt.GetoptError:
  	     	usage()
		sys.exit()
	start=0
	host_ip=[]
	filename=""
	bingapi="yes"
	start=0
	for opt, arg in opts:
		if opt == '-l' :
			limit = int(arg)
		elif opt == '-d':
			word = arg	
		elif opt == '-s':
			start = int(arg)
		elif opt == '-v':
			virtual = arg
		elif opt == '-f':
			filename= arg
		elif opt == '-b':
			engine = arg
			if engine not in ("google", "linkedin", "pgp", "all","google-profiles","exalead","bing","bing_api","yandex"):
				usage()
				print "Invalid search engine, try with: bing, google, linkedin, pgp"
				sys.exit()
			else:
				pass
	if engine == "google":
		print "[-] Searching in Google:"
		search=googlesearch.search_google(word,limit,start)
		search.process()
		all_emails=search.get_emails()
		all_hosts=search.get_hostnames()
	if engine == "exalead":
		print "[-] Searching in Exalead:"
		search=exaleadsearch.search_exalead(word,limit,start)
		search.process()
		all_emails=search.get_emails()
		all_hosts=search.get_hostnames()
	elif engine == "bing" or engine =="bingapi":	
		print "[-] Searching in Bing:"
		search=bingsearch.search_bing(word,limit,start)
		if engine =="bingapi":
			bingapi="yes"
		else:
			bingapi="no"
		search.process(bingapi)
		all_emails=search.get_emails()
		all_hosts=search.get_hostnames()
	elif engine == "yandex":# Not working yet
		print "[-] Searching in Yandex:"
		search=yandexsearch.search_yandex(word,limit,start)
		search.process()
		all_emails=search.get_emails()
		all_hosts=search.get_hostnames()
	elif engine == "pgp":
		print "[-] Searching in PGP key server.."
		search=pgpsearch.search_pgp(word)
		search.process()
		all_emails=search.get_emails()
		all_hosts=search.get_hostnames()
	elif engine == "linkedin":
		print "[-] Searching in Linkedin.."
		search=linkedinsearch.search_linkedin(word,limit)
		search.process()
		people=search.get_people()
		print "Users from Linkedin:"
		print "===================="
		for user in people:
			print user
		sys.exit()
	elif engine == "google-profiles":
		print "[-] Searching in Google profiles.."
		search=googlesearch.search_google(word,limit,start)
		search.process_profiles()
		people=search.get_profiles()
		print "Users from Google profiles:"
		print "---------------------------"
		for users in people:
			print users
		sys.exit()
	elif engine == "all":
		print "Full harvest.."
		all_emails=[]
		all_hosts=[]
		virtual = "basic"
		print "[-] Searching in Google.."
		search=googlesearch.search_google(word,limit,start)
		search.process()
		emails=search.get_emails()
		hosts=search.get_hostnames()
		all_emails.extend(emails)
		all_hosts.extend(hosts)
		print "[-] Searching in PGP Key server.."
		search=pgpsearch.search_pgp(word)
		search.process()
		emails=search.get_emails()
		hosts=search.get_hostnames()
		all_hosts.extend(hosts)
		all_emails.extend(emails)
		print "[-] Searching in Bing.."
		bingapi="yes"
		search=bingsearch.search_bing(word,limit,start)
		search.process(bingapi)
		emails=search.get_emails()
		hosts=search.get_hostnames()
		all_hosts.extend(hosts)
		all_emails.extend(emails)
		print "[-] Searching in Exalead.."
		search=exaleadsearch.search_exalead(word,limit,start)
		search.process()
		emails=search.get_emails()
		hosts=search.get_hostnames()
		all_hosts.extend(hosts)
		all_emails.extend(emails)

	print "\n[+] Emails found:"
	print " -------------"
	if all_emails ==[]:
		print "No emails found"
	else:
		for emails in all_emails:
			print emails 
	print "\n[+] Hosts found"
	print " -----------"
	if all_hosts == []:
		print "No hosts found"
	else:
		full_host=hostchecker.Checker(all_hosts)
		full=full_host.check()
		vhost=[]
		for host in full:
			print host
			ip=host.split(':')[0]
			if host_ip.count(ip.lower()):
				pass
			else:
				host_ip.append(ip.lower())
	if virtual == "basic":
		print "[+] Virtual hosts:"
		print "----------------"
		for l in host_ip:
			search=bingsearch.search_bing(l,limit,start)
 			search.process_vhost()
 			res=search.get_allhostnames()
			for x in res:
				print l+":"+x
				vhost.append(l+":"+x)
				full.append(l+":"+x)
	else:
		pass #Here i need to add explosion mode.
	#Tengo que sacar los TLD para hacer esto.
	recursion=None	
	if recursion:
		limit=300
		start=0
		for word in vhost:
			search=googlesearch.search_google(word,limit,start)
			search.process()
			emails=search.get_emails()
			hosts=search.get_hostnames()
			print emails
			print hosts
	else:
		pass
	if filename!="":
		file = open(filename,'w')
		file.write('<theHarvester>')
		for x in all_emails:
			file.write('<email>'+x+'</email>')
		for x in all_hosts:
			file.write('<host>'+x+'</host>')
		for x in vhosts:
			file.write('<vhost>'+x+'</vhost>')
		file.write('</theHarvester>')
		file.close
		print "Results saved in: "+ filename
	else:
		pass

		
if __name__ == "__main__":
        try: start(sys.argv[1:])
	except KeyboardInterrupt:
		print "Search interrupted by user.."
	except:
		sys.exit()


########NEW FILE########
