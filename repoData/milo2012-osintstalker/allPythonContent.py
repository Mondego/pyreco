__FILENAME__ = fbstalker1
# -*- coding: utf-8 -*-
from __future__ import division
import httplib2,json
import zlib
import zipfile
import sys
import re
import datetime
import operator
import sqlite3
import os
from datetime import datetime
from datetime import date
import pytz 
from tzlocal import get_localzone
import requests
from termcolor import colored, cprint
from pygraphml.GraphMLParser import *
from pygraphml.Graph import *
from pygraphml.Node import *
from pygraphml.Edge import *

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
import time,re,sys
from selenium.webdriver.common.keys import Keys
import datetime
from bs4 import BeautifulSoup
from StringIO import StringIO

requests.adapters.DEFAULT_RETRIES = 10

h = httplib2.Http(".cache")


facebook_username = ""
facebook_password = ""

global uid
uid = ""
username = ""
internetAccess = True
cookies = {}
all_cookies = {}
reportFileName = ""

#For consonlidating all likes across Photos Likes+Post Likes
peopleIDList = []
likesCountList = []
timePostList = []
placesVisitedList = []

#Chrome Options
chromeOptions = webdriver.ChromeOptions()
prefs = {"profile.managed_default_content_settings.images":2}
chromeOptions.add_experimental_option("prefs",prefs)
driver = webdriver.Chrome(chrome_options=chromeOptions)



def createDatabase():
	conn = sqlite3.connect('facebook.db')
	c = conn.cursor()
	sql = 'create table if not exists photosLiked (sourceUID TEXT, description TEXT, photoURL TEXT unique, pageURL TEXT, username TEXT)'
	sql1 = 'create table if not exists photosCommented (sourceUID TEXT, description TEXT, photoURL TEXT unique, pageURL TEXT, username TEXT)'
	sql2 = 'create table if not exists friends (sourceUID TEXT, name TEXT, userName TEXT unique, month TEXT, year TEXT)'
	sql3 = 'create table if not exists friendsDetails (sourceUID TEXT, userName TEXT unique, userEduWork TEXT, userLivingCity TEXT, userCurrentCity TEXT, userLiveEvents TEXT, userGender TEXT, userStatus TEXT, userGroups TEXT)'
	sql4 = 'create table if not exists videosBy (sourceUID TEXT, title TEXT unique, url TEXT)'
	sql5 = 'create table if not exists pagesLiked (sourceUID TEXT, name TEXT unique, category TEXT,url TEXT)'
	sql6 = 'create table if not exists photosOf (sourceUID TEXT, description TEXT, photoURL TEXT unique, pageURL TEXT, username TEXT)'
	sql7 = 'create table if not exists photosBy (sourceUID TEXT, description TEXT, photoURL TEXT unique, pageURL TEXT, username TEXT)'
    
	c.execute(sql)
    	c.execute(sql1)
    	c.execute(sql2)
    	c.execute(sql3)
    	c.execute(sql4)
    	c.execute(sql5)
    	c.execute(sql6)
    	c.execute(sql7)
    	conn.commit()

createDatabase()
conn = sqlite3.connect('facebook.db')

def createMaltego(username):
	g = Graph()
	totalCount = 50
	start = 0
	nodeList = []
	edgeList = []

	while(start<totalCount):
       		nodeList.append("")	
	        edgeList.append("")
	        start+=1

	nodeList[0] = g.add_node('Facebook_'+username)
	nodeList[0]['node'] = createNodeFacebook(username,"https://www.facebook.com/"+username,uid)


	counter1=1
	counter2=0                
	userList=[]

	c = conn.cursor()
	c.execute('select userName from friends where sourceUID=?',(uid,))
	dataList = c.fetchall()
	nodeUid = ""
	for i in dataList:
		if i[0] not in userList:
			userList.append(i[0])
			try:
				nodeUid = str(convertUser2ID2(driver,str(i[0])))
				#nodeUid = str(convertUser2ID(str(i[0])))
			   	nodeList[counter1] = g.add_node("Facebook_"+str(i[0]))
   				nodeList[counter1]['node'] = createNodeFacebook(i[0],'https://www.facebook.com/'+str(i[0]),nodeUid)
   				edgeList[counter2] = g.add_edge(nodeList[0], nodeList[counter1])
   				edgeList[counter2]['link'] = createLink('Facebook')
    				nodeList.append("")
 		   		edgeList.append("")
    				counter1+=1
    				counter2+=1
			except IndexError:
				continue
	if len(nodeUid)>0:	
		parser = GraphMLParser()
		if not os.path.exists(os.getcwd()+'/Graphs'):
	    		os.makedirs(os.getcwd()+'/Graphs')
		filename = 'Graphs/Graph1.graphml'
		parser.write(g, "Graphs/Graph1.graphml")
		cleanUpGraph(filename)
		filename = username+'_maltego.mtgx'
		print 'Creating archive: '+filename
		zf = zipfile.ZipFile(filename, mode='w')
		print 'Adding Graph1.graphml'
		zf.write('Graphs/Graph1.graphml')
		print 'Closing'
		zf.close()
 
def createLink(label):
	xmlString = '<mtg:MaltegoLink xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.link.manual-link">'
	xmlString += '<mtg:Properties>'
	xmlString += '<mtg:Property displayName="Description" hidden="false" name="maltego.link.manual.description" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Style" hidden="false" name="maltego.link.style" nullable="true" readonly="false" type="int">'
	xmlString += '<mtg:Value>0</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Label" hidden="false" name="maltego.link.manual.type" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+label+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Show Label" hidden="false" name="maltego.link.show-label" nullable="true" readonly="false" type="int">'
	xmlString += '<mtg:Value>0</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Thickness" hidden="false" name="maltego.link.thickness" nullable="true" readonly="false" type="int">'
	xmlString += '<mtg:Value>2</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Color" hidden="false" name="maltego.link.color" nullable="true" readonly="false" type="color">'
	xmlString += '<mtg:Value>8421505</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '</mtg:Properties>'
	xmlString += '</mtg:MaltegoLink>'
	return xmlString

def createNodeImage(name,url):
	xmlString = '<mtg:MaltegoEntity xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.Image">'
	xmlString += '<mtg:Properties>'
	xmlString += '<mtg:Property displayName="Description" hidden="false" name="description" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+name+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="URL" hidden="false" name="url" nullable="true" readonly="false" type="url">'
	xmlString += '<mtg:Value>'+url+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '</mtg:Properties>'
	xmlString += '</mtg:MaltegoEntity>'
	return xmlString

def createNodeFacebook(displayName,url,uid):
	xmlString = '<mtg:MaltegoEntity xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.affiliation.Facebook">'
	xmlString += '<mtg:Properties>'
	xmlString += '<mtg:Property displayName="Name" hidden="false" name="person.name" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+displayName+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Network" hidden="false" name="affiliation.network" nullable="true" readonly="true" type="string">'
	xmlString += '<mtg:Value>Facebook</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="UID" hidden="false" name="affiliation.uid" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+str(uid)+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Profile URL" hidden="false" name="affiliation.profile-url" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+url+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '</mtg:Properties>'
	xmlString += '</mtg:MaltegoEntity>'
	return xmlString

def createNodeUrl(displayName,url):
        xmlString = '<mtg:MaltegoEntity xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.URL">'
        xmlString += '<mtg:Properties>'
        xmlString += '<mtg:Property displayName="'+displayName+'" hidden="false" name="short-title" nullable="true" readonly="false" type="string">'
        xmlString += '<mtg:Value>'+displayName+'</mtg:Value>'
        xmlString += '</mtg:Property>'
        xmlString += '<mtg:Property displayName="'+displayName+'" hidden="false" name="url" nullable="true" readonly="false" type="url">'  
        xmlString += '<mtg:Value>'+displayName+'</mtg:Value>'
        xmlString += '</mtg:Property>'
        xmlString += '<mtg:Property displayName="Title" hidden="false" name="title" nullable="true" readonly="false" type="string">'
        xmlString += '<mtg:Value/>'    
        xmlString += '</mtg:Property>'
        xmlString += '</mtg:Properties>'
        xmlString += '</mtg:MaltegoEntity>'
	return xmlString

def createNodeLocation(lat,lng):
	xmlString = '<mtg:MaltegoEntity xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.Location">'
	xmlString += '<mtg:Properties>'
	xmlString += '<mtg:Property displayName="Name" hidden="false" name="location.name" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>lat='+str(lat)+' lng='+str(lng)+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Area Code" hidden="false" name="location.areacode" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Area" hidden="false" name="location.area" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Latitude" hidden="false" name="latitude" nullable="true" readonly="false" type="float">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Longitude" hidden="false" name="longitude" nullable="true" readonly="false" type="float">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Country" hidden="false" name="country" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Country Code" hidden="false" name="countrycode" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="City" hidden="false" name="city" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Street Address" hidden="false" name="streetaddress" nullable="true" readonly="false" type="string">'	
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '</mtg:Properties>'
	xmlString += '</mtg:MaltegoEntity>'
	return xmlString

def cleanUpGraph(filename):
	newContent = []
	with open(filename) as f:
		content = f.readlines()
		for i in content:
			if '<key attr.name="node" attr.type="string" id="node"/>' in i:
				i = i.replace('name="node" attr.type="string"','name="MaltegoEntity" for="node"')
			if '<key attr.name="link" attr.type="string" id="link"/>' in i:
				i = i.replace('name="link" attr.type="string"','name="MaltegoLink" for="edge"')
			i = i.replace("&lt;","<")
			i = i.replace("&gt;",">")
			i = i.replace("&quot;",'"')
			print i.strip()
			newContent.append(i.strip())

	f = open(filename,'w')
	for item in newContent:
		f.write("%s\n" % item)
	f.close()

def normalize(s):
	if type(s) == unicode: 
       		return s.encode('utf8', 'ignore')
	else:
        	return str(s)

def findUser(findName):
	stmt = "SELECT uid,current_location,username,name FROM user WHERE contains('"+findName+"')"
	stmt = stmt.replace(" ","+")
	url="https://graph.facebook.com/fql?q="+stmt+"&access_token="+facebook_access_token
	resp, content = h.request(url, "GET")
	results = json.loads(content)
	count=1
	for x in results['data']:
		print str(count)+'\thttp://www.facebook.com/'+x['username']
		count+=1

def convertUser2ID2(driver,username):
	url="http://graph.facebook.com/"+username
	resp, content = h.request(url, "GET")
	if resp.status==200:
		results = json.loads(content)
		if len(results['id'])>0:
			fbid = results['id']
			return fbid

def convertUser2ID(username):
	stmt = "SELECT uid,current_location,username,name FROM user WHERE username=('"+username+"')"
	stmt = stmt.replace(" ","+")
	url="https://graph.facebook.com/fql?q="+stmt+"&access_token="+facebook_access_token
	resp, content = h.request(url, "GET")
	if resp.status==200:
		results = json.loads(content)
		if len(results['data'])>0:
			return results['data'][0]['uid']
		else:
			print "[!] Can't convert username 2 uid. Please check username"
			sys.exit()
			return 0
	else:
		print "[!] Please check your facebook_access_token before continuing"
		sys.exit()
		return 0

def convertID2User(uid):
	stmt = "SELECT uid,current_location,username,name FROM user WHERE uid=('"+uid+"')"
	stmt = stmt.replace(" ","+")
	url="https://graph.facebook.com/fql?q="+stmt+"&access_token="+facebook_access_token
	resp, content = h.request(url, "GET")
	results = json.loads(content)
	return results['data'][0]['uid']


def loginFacebook(driver):
	driver.implicitly_wait(120)
	driver.get("https://www.facebook.com/")
	assert "Welcome to Facebook" in driver.title
	time.sleep(3)
	driver.find_element_by_id('email').send_keys(facebook_username)
	driver.find_element_by_id('pass').send_keys(facebook_password)
	driver.find_element_by_id("loginbutton").click()
	global all_cookies
	all_cookies = driver.get_cookies()
	html = driver.page_source
	if "Incorrect Email/Password Combination" in html:
		print "[!] Incorrect Facebook username (email address) or password"
		sys.exit()
def write2Database(dbName,dataList):
	try:
		cprint("[*] Writing "+str(len(dataList))+" record(s) to database table: "+dbName,"white")
		#print "[*] Writing "+str(len(dataList))+" record(s) to database table: "+dbName
		numOfColumns = len(dataList[0])
		c = conn.cursor()
		if numOfColumns==3:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
		if numOfColumns==4:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
		if numOfColumns==5:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
		if numOfColumns==9:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?,?,?,?,?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
	except TypeError as e:
		print e
		pass
	except IndexError as e:
		print e
		pass

def downloadFile(url):	
	global cookies
	for s_cookie in all_cookies:
			cookies[s_cookie["name"]]=s_cookie["value"]
	r = requests.get(url,cookies=cookies)
	html = r.content
	return html

def parsePost(id,username):
	filename = 'posts__'+str(id)
	if not os.path.lexists(filename):
		print "[*] Caching Facebook Post: "+str(id)
		url = "https://www.facebook.com/"+username+"/posts/"+str(id)
		driver.get(url)	
		if "Sorry, this page isn't available" in driver.page_source:
			print "[!] Cannot access page "+url
			return ""
        	lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        	match=False
        	while(match==False):
        	        time.sleep(1)
        	        lastCount = lenOfPage
               		lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                	if lastCount==lenOfPage:
                	        match=True
		html1 = driver.page_source	
		text_file = open(filename, "w")
		text_file.write(normalize(html1))
		text_file.close()
	else:
		html1 = open(filename, 'r').read()
	soup1 = BeautifulSoup(html1)
	htmlList = soup1.find("h5",{"class" : "_6nl"})
	tlTime = soup1.find("abbr")
	if " at " in str(htmlList):
		soup2 = BeautifulSoup(str(htmlList))
		locationList = soup2.findAll("a",{"class" : "profileLink"})
		locUrl = locationList[len(locationList)-1]['href']
		locDescription = locationList[len(locationList)-1].text
		locTime = tlTime['data-utime']
		placesVisitedList.append([locTime,locDescription,locUrl])


def parseLikesPosts(id):
	peopleID = []
	filename = 'likes_'+str(id)
	if not os.path.lexists(filename):
		print "[*] Caching Post Likes: "+str(id)
		url = "https://www.facebook.com/browse/likes?id="+str(id)
		driver.get(url)	
		if "Sorry, this page isn't available" in driver.page_source:
			print "[!] Cannot access page "+url
			return ""
        	lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        	match=False
        	while(match==False):
        	        time.sleep(1)
        	        lastCount = lenOfPage
               		lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                	if lastCount==lenOfPage:
                	        match=True
		html1 = driver.page_source	
		text_file = open(filename, "w")
		text_file.write(normalize(html1))
		text_file.close()
	else:
		html1 = open(filename, 'r').read()
	soup1 = BeautifulSoup(html1)
	peopleLikeList = soup1.findAll("div",{"class" : "fsl fwb fcb"})

	if len(peopleLikeList)>0:
		print "[*] Extracting Likes from Post: "+str(id)
		for x in peopleLikeList:
			soup2 = BeautifulSoup(str(x))
			peopleLike = soup2.find("a")
			peopleLikeID = peopleLike['href'].split('?')[0].replace('https://www.facebook.com/','')
			if peopleLikeID == 'profile.php':	
				r = re.compile('id=(.*?)&fref')
				m = r.search(str(peopleLike['href']))
				if m:
					peopleLikeID = m.group(1)
			print "[*] Liked Post: "+"\t"+peopleLikeID
			if peopleLikeID not in peopleID:
				peopleID.append(peopleLikeID)
		
		return peopleID	
		


def parseTimeline(html,username):
	soup = BeautifulSoup(html)	
	tlTime = soup.findAll("abbr")
	temp123 = soup.findAll("div",{"role" : "article"})
	placesCheckin = []
	timeOfPostList = []

	counter = 0

	for y in temp123:
		soup1 = BeautifulSoup(str(y))
		tlDateTimeLoc = soup1.findAll("a",{"class" : "uiLinkSubtle"})
		#Universal Time
		try:
			soup2 = BeautifulSoup(str(tlDateTimeLoc[0]))
			tlDateTime = soup2.find("abbr")	
			#Facebook Post Link	
			tlLink = tlDateTimeLoc[0]['href']

			try:
				tz = get_localzone()
				unixTime = str(tlDateTime['data-utime'])
				localTime = (datetime.datetime.fromtimestamp(int(unixTime)).strftime('%Y-%m-%d %H:%M:%S'))
				timePostList.append(localTime)
				timeOfPost = localTime
				timeOfPostList.append(localTime)

				print "[*] Time of Post: "+localTime
			except TypeError:
				continue
			if "posts" in tlLink:
				#print tlLink.strip()
				pageID = tlLink.split("/")

				parsePost(pageID[3],username)
				peopleIDLikes = parseLikesPosts(pageID[3])

				try:
					for id1 in peopleIDLikes:
						global peopleIDList
						global likesCountList
						if id1 in peopleIDList:
							lastCount = 0
							position = peopleIDList.index(id1)
							likesCountList[position] +=1
						else:
							peopleIDList.append(id1)
							likesCountList.append(1)
				except TypeError:
					continue
				
			if len(tlDateTimeLoc)>2:
				try:
					#Device / Location
					if len(tlDateTimeLoc[1].text)>0:
						print "[*] Location of Post: "+unicode(tlDateTimeLoc[1].text)
					if len(tlDateTimeLoc[2].text)>0:
						print "[*] Device: "+str(tlDateTimeLoc[2].text)
				except IndexError:
					continue	

			else:
				try:
					#Device / Location
					if len(tlDateTimeLoc[1].text)>0:
						if "mobile" in tlDateTimeLoc[1].text:
							print "[*] Device: "+str(tlDateTimeLoc[1].text)
						else:
							print "[*] Location of Post: "+unicode(tlDateTimeLoc[1].text)
					
				except IndexError:
					continue	
			#Facebook Posts
			tlPosts = soup1.find("span",{"class" : "userContent"})
			
			try:
				tlPostSec = soup1.findall("span",{"class" : "userContentSecondary fcg"})
				tlPostMsg = ""
			
				#Places Checked In
			except TypeError:
				continue
			soup3 = BeautifulSoup(str(tlPostSec))
			hrefLink = soup3.find("a")

			"""
			if len(str(tlPostSec))>0:
				tlPostMsg = str(tlPostSec)
				#if " at " in str(tlPostMsg) and " with " not in str(tlPostMsg):
				if " at " in str(tlPostMsg):
					print str(tlPostSec)

					print tlPostMsg
					#print hrefLink
					#placeUrl = hrefLink['href'].encode('utf8').split('?')[0]
					#print "[*] Place: "+placeUrl										
					#placesCheckin.append([timeOfPost,placeUrl])
			"""

			try:
				if len(tlPosts)>0:				
					tlPostStr = re.sub('<[^>]*>', '', str(tlPosts))
					if tlPostStr!=None:
						print "[*] Message: "+str(tlPostStr)
			except TypeError as e:
				continue


			tlPosts = soup1.find("div",{"class" : "translationEligibleUserMessage userContent"})
			try:
				if len(tlPosts)>0:
					tlPostStr = re.sub('<[^>]*>', '', str(tlPosts))
					print "[*] Message: "+str(tlPostStr)	
			except TypeError:
				continue
		except IndexError as e:
			continue
		counter+=1
	
	tlDeviceLoc = soup.findAll("a",{"class" : "uiLinkSubtle"})

	print '\n'

	global reportFileName
	if len(reportFileName)<1:
		reportFileName = username+"_report.txt"
	reportFile = open(reportFileName, "w")
	
	reportFile.write("\n********** Places Visited By "+str(username)+" **********\n")
	filename = username+'_placesVisited.htm'
	if not os.path.lexists(filename):
		html = downloadPlacesVisited(driver,uid)
		text_file = open(filename, "w")
		text_file.write(html.encode('utf8'))
		text_file.close()
	else:
		html = open(filename, 'r').read()
	dataList = parsePlacesVisited(html)
	count=1
	for i in dataList:
		reportFile.write(normalize(i[2])+'\t'+normalize(i[1])+'\t'+normalize(i[3])+'\n')
		count+=1
	
	reportFile.write("\n********** Places Liked By "+str(username)+" **********\n")
	filename = username+'_placesLiked.htm'
	if not os.path.lexists(filename):
		html = downloadPlacesLiked(driver,uid)
		text_file = open(filename, "w")
		text_file.write(html.encode('utf8'))
		text_file.close()
	else:
		html = open(filename, 'r').read()
	dataList = parsePlacesLiked(html)
	count=1
	for i in dataList:
		reportFile.write(normalize(i[2])+'\t'+normalize(i[1])+'\t'+normalize(i[3])+'\n')
		count+=1

	reportFile.write("\n********** Places checked in **********\n")
	for places in placesVisitedList:
		unixTime = places[0]
		localTime = (datetime.datetime.fromtimestamp(int(unixTime)).strftime('%Y-%m-%d %H:%M:%S'))
		reportFile.write(localTime+'\t'+normalize(places[1])+'\t'+normalize(places[2])+'\n')

	reportFile.write("\n********** Apps used By "+str(username)+" **********\n")
	filename = username+'_apps.htm'
	if not os.path.lexists(filename):
		html = downloadAppsUsed(driver,uid)
		text_file = open(filename, "w")
		text_file.write(html.encode('utf8'))
		text_file.close()
	else:
		html = open(filename, 'r').read()
	data1 = parseAppsUsed(html)
	result = ""
	for x in data1:
		reportFile.write(normalize(x)+'\n')
		x = x.lower()
		if "blackberry" in x:
			result += "[*] User is using a Blackberry device\n"
		if "android" in x:
			result += "[*] User is using an Android device\n"
		if "ios" in x or "ipad" in x or "iphone" in x:
			result += "[*] User is using an iOS Apple device\n"
		if "samsung" in x:
			result += "[*] User is using a Samsung Android device\n"
	reportFile.write(result)

	reportFile.write("\n********** Videos Posted By "+str(username)+" **********\n")
	filename = username+'_videosBy.htm'
	if not os.path.lexists(filename):
		html = downloadVideosBy(driver,uid)
		text_file = open(filename, "w")
		text_file.write(html.encode('utf8'))
		text_file.close()
	else:
		html = open(filename, 'r').read()
	dataList = parseVideosBy(html)
	count=1
	for i in dataList:
		reportFile.write(normalize(i[2])+'\t'+normalize(i[1])+'\n')
		count+=1

	reportFile.write("\n********** Pages Liked By "+str(username)+" **********\n")
	filename = username+'_pages.htm'
	if not os.path.lexists(filename):
		print "[*] Caching Pages Liked: "+username
		html = downloadPagesLiked(driver,uid)
		text_file = open(filename, "w")
		text_file.write(html.encode('utf8'))
		text_file.close()
	else:
		html = open(filename, 'r').read()
	dataList = parsePagesLiked(html)
	for i in dataList:
		pageName = normalize(i[0])
		tmpStr	= normalize(i[3])+'\t'+normalize(i[2])+'\t'+normalize(i[1])+'\n'
		reportFile.write(tmpStr)
	print "\n"

	c = conn.cursor()
	reportFile.write("\n********** Friendship History of "+str(username)+" **********\n")
	c.execute('select * from friends where sourceUID=?',(uid,))
	dataList = c.fetchall()
	try:
		if len(str(dataList[0][4]))>0:
			for i in dataList:
				#Date First followed by Username
				reportFile.write(normalize(i[4])+'\t'+normalize(i[3])+'\t'+normalize(i[2])+'\t'+normalize(i[1])+'\n')
				#Username followed by Date
				#reportFile.write(normalize(i[4])+'\t'+normalize(i[3])+'\t'+normalize(i[2])+'\t'+normalize(i[1])+'\n')
		print '\n'
	except IndexError:
		pass

	reportFile.write("\n********** Friends of "+str(username)+" **********\n")
	reportFile.write("*** Backtracing from Facebook Likes/Comments/Tags ***\n\n")
	c = conn.cursor()
	c.execute('select userName from friends where sourceUID=?',(uid,))
	dataList = c.fetchall()
	for i in dataList:
		reportFile.write(str(i[0])+'\n')
	print '\n'

	tempList = []
	totalLen = len(timeOfPostList)
	timeSlot1 = 0
	timeSlot2 = 0
	timeSlot3 = 0 
	timeSlot4 = 0
	timeSlot5 = 0 
	timeSlot6 = 0 
	timeSlot7 = 0 
	timeSlot8 = 0 

	count = 0
	if len(peopleIDList)>0:
		likesCountList, peopleIDList  = zip(*sorted(zip(likesCountList,peopleIDList),reverse=True))
	
		reportFile.write("\n********** Analysis of Facebook Post Likes **********\n")
		while count<len(peopleIDList):
			testStr = str(likesCountList[count]).encode('utf8')+'\t'+str(peopleIDList[count]).encode('utf8')
			reportFile.write(testStr+"\n")
			count+=1	

	reportFile.write("\n********** Analysis of Interactions between "+str(username)+" and Friends **********\n")
	c = conn.cursor()
	c.execute('select userName from friends where sourceUID=?',(uid,))
	dataList = c.fetchall()
	photosliked = []
	photoscommented = []
	userID = []
	
	photosLikedUser = []
	photosLikedCount = []
	photosCommentedUser = []
	photosCommentedCount = []
	
	for i in dataList:
		c.execute('select * from photosLiked where sourceUID=? and username=?',(uid,i[0],))
		dataList1 = []
		dataList1 = c.fetchall()
		if len(dataList1)>0:
			photosLikedUser.append(normalize(i[0]))
			photosLikedCount.append(len(dataList1))
	for i in dataList:
		c.execute('select * from photosCommented where sourceUID=? and username=?',(uid,i[0],))
		dataList1 = []
		dataList1 = c.fetchall()
		if len(dataList1)>0:	
			photosCommentedUser.append(normalize(i[0]))
			photosCommentedCount.append(len(dataList1))
	if(len(photosLikedCount)>1):	
		reportFile.write("Photo Likes: "+str(username)+" and Friends\n")
		photosLikedCount, photosLikedUser  = zip(*sorted(zip(photosLikedCount, photosLikedUser),reverse=True))	
		count=0
		while count<len(photosLikedCount):
			tmpStr = str(photosLikedCount[count])+'\t'+normalize(photosLikedUser[count])+'\n'
			count+=1
			reportFile.write(tmpStr)
	if(len(photosCommentedCount)>1):	
		reportFile.write("\n********** Comments on "+str(username)+"'s Photos **********\n")
		photosCommentedCount, photosCommentedUser  = zip(*sorted(zip(photosCommentedCount, photosCommentedUser),reverse=True))	
		count=0
		while count<len(photosCommentedCount):
			tmpStr = str(photosCommentedCount[count])+'\t'+normalize(photosCommentedUser[count])+'\n'
			count+=1
			reportFile.write(tmpStr)


	reportFile.write("\n********** Analysis of Time in Facebook **********\n")
	for timePost in timeOfPostList:
		tempList.append(timePost.split(" ")[1])
		tempTime = (timePost.split(" ")[1]).split(":")[0]
		tempTime = int(tempTime)
		if tempTime >= 21:
			timeSlot8+=1
		if tempTime >= 18 and tempTime < 21:
			timeSlot7+=1
		if tempTime >= 15 and tempTime < 18:
			timeSlot6+=1
		if tempTime >= 12 and tempTime < 15:
			timeSlot5+=1
		if tempTime >= 9 and tempTime < 12:
			timeSlot4+=1
		if tempTime >= 6 and tempTime < 9:
			timeSlot3+=1
		if tempTime >= 3 and tempTime < 6:
			timeSlot2+=1
		if tempTime >= 0 and tempTime < 3:
			timeSlot1+=1
	reportFile.write("Total % (00:00 to 03:00) "+str((timeSlot1/totalLen)*100)+" %\n")
	reportFile.write("Total % (03:00 to 06:00) "+str((timeSlot2/totalLen)*100)+" %\n")
	reportFile.write("Total % (06:00 to 09:00) "+str((timeSlot3/totalLen)*100)+" %\n")
	reportFile.write("Total % (09:00 to 12:00) "+str((timeSlot4/totalLen)*100)+" %\n")
	reportFile.write("Total % (12:00 to 15:00) "+str((timeSlot5/totalLen)*100)+" %\n")
	reportFile.write("Total % (15:00 to 18:00) "+str((timeSlot6/totalLen)*100)+" %\n")
	reportFile.write("Total % (18:00 to 21:00) "+str((timeSlot7/totalLen)*100)+" %\n")
	reportFile.write("Total % (21:00 to 24:00) "+str((timeSlot8/totalLen)*100)+" %\n")

	"""
	reportFile.write("\nDate/Time of Facebook Posts\n")
	for timePost in timeOfPostList:
		reportFile.write(timePost+'\n')	
	"""
	reportFile.close()

def downloadTimeline(username):
	url = 'https://www.facebook.com/'+username.strip()
	driver.get(url)	
	print "[*] Crawling Timeline"
	if "Sorry, this page isn't available" in driver.page_source:
		print "[!] Cannot access page "+url
		return ""
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                lastCount = lenOfPage
                time.sleep(3)
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
			print "[*] Looking for 'Show Older Stories' Link"
			try:
				clickLink = WebDriverWait(driver, 1).until(lambda driver : driver.find_element_by_link_text('Show Older Stories'))
				if clickLink:
					print "[*] Clicked 'Show Older Stories' Link"
					driver.find_element_by_link_text('Show Older Stories').click()
				else:
					print "[*] Indexing Timeline"
					break
		                        match=True
			except TimeoutException:				
				match = True
	return driver.page_source




def downloadPlacesVisited(driver,userid):
	url = 'https://www.facebook.com/search/'+str(userid).strip()+'/places-visited'
	driver.get(url)	
	if "Sorry, this page isn't available" in driver.page_source:
		print "[!] Cannot access page "+url
		return ""
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                time.sleep(3)
                lastCount = lenOfPage
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
                        match=True
	return driver.page_source

def downloadPlacesLiked(driver,userid):
	url = 'https://www.facebook.com/search/'+str(userid).strip()+'/places-liked'
	driver.get(url)	
	if "Sorry, this page isn't available" in driver.page_source:
		print "[!] Cannot access page "+url
		return ""
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                time.sleep(3)
                lastCount = lenOfPage
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
                        match=True
	return driver.page_source


def downloadVideosBy(driver,userid):
	url = 'https://www.facebook.com/search/'+str(userid).strip()+'/videos-by'
	driver.get(url)	
	if "Sorry, this page isn't available" in driver.page_source:
		print "[!] Cannot access page "+url
		return ""
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                time.sleep(3)
                lastCount = lenOfPage
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
                        match=True
	return driver.page_source

def downloadUserInfo(driver,userid):
	url = 'https://www.facebook.com/'+str(userid).strip()+'/info'
	driver.get(url)	
	if "Sorry, this page isn't available" in driver.page_source:
		print "[!] Cannot access page "+url
		return ""
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                time.sleep(3)
                lastCount = lenOfPage
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
                        match=True
	return driver.page_source

def downloadPhotosBy(driver,userid):
	driver.get('https://www.facebook.com/search/'+str(userid)+'/photos-by')
	if "Sorry, we couldn't find any results for this search." in driver.page_source:
		print "Photos commented list is hidden"
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                time.sleep(3)
                lastCount = lenOfPage
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
                        match=True
	return driver.page_source

def downloadPhotosOf(driver,userid):
	driver.get('https://www.facebook.com/search/'+str(userid)+'/photos-of')
	if "Sorry, we couldn't find any results for this search." in driver.page_source:
		print "Photos commented list is hidden"
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                time.sleep(3)
                lastCount = lenOfPage
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
                        match=True
	return driver.page_source

def downloadPhotosCommented(driver,userid):
	driver.get('https://www.facebook.com/search/'+str(userid)+'/photos-commented')
	if "Sorry, we couldn't find any results for this search." in driver.page_source:
		print "Photos commented list is hidden"
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                time.sleep(3)
                lastCount = lenOfPage
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
                        match=True
	return driver.page_source
	
def downloadPhotosLiked(driver,userid):
	driver.get('https://www.facebook.com/search/'+str(userid)+'/photos-liked')
	if "Sorry, we couldn't find any results for this search." in driver.page_source:
		print "Pages liked list is hidden"
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                time.sleep(2)
                lastCount = lenOfPage
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
                        match=True
	return driver.page_source
	

def downloadPagesLiked(driver,userid):
	driver.get('https://www.facebook.com/search/'+str(userid)+'/pages-liked')
	if "Sorry, we couldn't find any results for this search." in driver.page_source:
		print "Pages liked list is hidden"
        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match=False
        while(match==False):
                time.sleep(3)
                lastCount = lenOfPage
                lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                if lastCount==lenOfPage:
                        match=True
	return driver.page_source

def downloadFriends(driver,userid):
	driver.get('https://www.facebook.com/search/'+str(userid)+'/friends')
	if "Sorry, we couldn't find any results for this search." in driver.page_source:
		print "Friends list is hidden"
		return ""
	else:
		#assert "Friends of " in driver.title
	        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
       		match=False
        	while(match==False):
        	        time.sleep(3)
               		lastCount = lenOfPage
                	lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                	if lastCount==lenOfPage:
                	        match=True
		return driver.page_source

def downloadAppsUsed(driver,userid):
	driver.get('https://www.facebook.com/search/'+str(userid)+'/apps-used')
	if "Sorry, we couldn't find any results for this search." in driver.page_source:
		print "[!] Apps used list is hidden"
		return ""
	else:
	        lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
       		match=False
        	while(match==False):
                	time.sleep(3)
                	lastCount = lenOfPage
                	lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                	if lastCount==lenOfPage:
                	        match=True
		return driver.page_source

def parseUserInfo(html):
	userEduWork = []
	userLivingCity = ""
	userCurrentCity = ""
	userLiveEvents = []
	userGender = ""
	userStatus = ""
	userGroups = []

	#try:
	soup = BeautifulSoup(str(html))
	
	pageLeft = soup.findAll("div", {"class" : "_4_g4 lfloat"})
	pageRight = soup.findAll("div", {"class" : "_4_g5 rfloat"})
	tempList = []

	try:
		soup1 = BeautifulSoup(str(pageLeft[0]))
		eduWork = soup.findAll("div", {"class" : "clearfix fbProfileExperience"})
		for i in eduWork:
			soup1 = BeautifulSoup(str(i))
			eduWorkCo = soup1.findAll("div", {"class" : "experienceTitle"},text=True)		
			eduWorkExp = soup1.findAll("div",{"class" : "experienceBody fsm fwn fcg"},text=True)
			try:
				strEduWork = eduWorkExp[0].encode('utf8')+'\t'+ eduWorkExp[1].encode('utf8')
				userEduWork.append(strEduWork)
			except IndexError:
				strEduWork = eduWorkExp[0].encode('utf8')				
				userEduWork.append(strEduWork)
				continue		
	except IndexError:
		pass
	relationships = soup.findAll("div", {"id" : "pagelet_relationships"})
	featured_pages = soup.findAll("div", {"id" : "pagelet_featured_pages"})
	bio = soup.findAll("div", {"id" : "pagelet_bio"})
	quotes = soup.findAll("div", {"id" : "pagelet_quotes"})

	hometown1 = soup.findAll("div", {"id" : "pagelet_hometown"})
	soup1 = BeautifulSoup(str(hometown1))
	hometown2  = soup1.findAll("div", {"id" : "hometown"},text=True)
	counter=0
	for z in hometown2:
		if z=="Current City":
			userCurrentCity = hometown2[counter+1]
			#print "CurrentCity: "+hometown2[counter+1]
		elif z=="Living":
			userLivingCity = hometown2[counter+1]
			#print "Living: "+hometown2[counter+1]
		counter+=1

	try:
		soup1 = BeautifulSoup(str(pageRight[0]))
		liveEvents = soup1.findAll("div",{"class" : "fbTimelineSection mtm fbTimelineCompactSection"},text=True)
		printOn=False
		for i in liveEvents:
			if printOn==True:
				userLiveEvents.append(i.encode('utf8'))
				#print "Life Events: "+i.encode('utf8')
			if i=="Life Events":
				printOn=True	
	except IndexError:
		pass
	basicInfo = soup1.findAll("div",{"class" : "fbTimelineSection mtm _bak fbTimelineCompactSection"},text=True)
	printOn=False
	counter=0
	for i in basicInfo:
		if printOn==True:
			if basicInfo[counter-1]=="Gender":
				#print "userGender: "+i.encode('utf8')
				userGender = i.encode('utf8')
			if basicInfo[counter-1]=="Relationship Status":
				#print "userStatus: "+i.encode('utf8')
				userStatus = i.encode('utf8')
			printOff=False
		if i=="Gender":
			printOn=True
		if i=="Relationship Status":
			printOn=True	
		counter+=1
	soup = BeautifulSoup(html)	
	groups = soup.findAll("div",{"class" : "mbs fwb"})
	r = re.compile('a href="(.*?)\"')
	for g in groups:
		m = r.search(str(g))
		if m:
			userGroups.append(['https://www.facebook.com'+m.group(1),g.text])
	#for x in userGroups:
	#	print x[0].encode('utf8')+'\t'+x[1].encode('utf8')
	tempList.append([userEduWork,userLivingCity,userCurrentCity,userLiveEvents,userGender,userStatus,userGroups])
	return tempList

def parsePlacesVisited(html):
	soup = BeautifulSoup(html)	
	pageName = soup.findAll("div", {"class" : "_zs fwb"})
	pageCategory = soup.findAll("div", {"class" : "_dew _dj_"})
	tempList = []
	count=0
	r = re.compile('a href="(.*?)\?ref=')
	for x in pageName:
		m = r.search(str(x))
		if m:
			pageCategory[count]
			tempList.append([uid,x.text,pageCategory[count].text,m.group(1)])
		count+=1
	return tempList

def parsePlacesLiked(html):
	soup = BeautifulSoup(html)	
	pageName = soup.findAll("div", {"class" : "_zs fwb"})
	pageCategory = soup.findAll("div", {"class" : "_dew _dj_"})
	tempList = []
	count=0
	r = re.compile('a href="(.*?)\?ref=')
	for x in pageName:
		m = r.search(str(x))
		if m:
			pageCategory[count]
			tempList.append([uid,x.text,pageCategory[count].text,m.group(1)])
		count+=1
	return tempList


def parsePagesLiked(html):
	soup = BeautifulSoup(html)	
	pageName = soup.findAll("div", {"class" : "_zs fwb"})
	pageCategory = soup.findAll("div", {"class" : "_dew _dj_"})
	tempList = []
	count=0
	r = re.compile('a href="(.*?)\?ref=')
	for x in pageName:
		m = r.search(str(x))
		if m:
			pageCategory[count]
			tempList.append([uid,x.text,pageCategory[count].text,m.group(1)])
		count+=1
	return tempList

def parsePhotosby(html):
	soup = BeautifulSoup(html)	
	photoPageLink = soup.findAll("a", {"class" : "_23q"})
	tempList = []
	for i in photoPageLink:
		html = str(i)
		soup1 = BeautifulSoup(html)
		pageName = soup1.findAll("img", {"class" : "img"})
		pageName1 = soup1.findAll("img", {"class" : "scaledImageFitWidth img"})
		pageName2 = soup1.findAll("img", {"class" : "_46-i img"})	
		for z in pageName2:
			if z['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					filename = filename.replace("profile.php?id=","")
					if not os.path.lexists(filename):
						#html1 = downloadPage(url1)
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
				soup2 = BeautifulSoup(html1)
				username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
				r = re.compile('a href="(.*?)"')
				m = r.search(str(username2))
				if m:	
					username3 = m.group(1)
					username3 = username3.replace("https://www.facebook.com/","")
					username3 = username3.replace("profile.php?id=","")
					print "[*] Extracting Data from Photo Page: "+username3
					tempList.append([str(uid),z['alt'],z['src'],i['href'],username3])
		for y in pageName1:
			if y['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					filename = filename.replace("profile.php?id=","")
					if not os.path.lexists(filename):
						#html1 = downloadPage(url1)
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
				soup2 = BeautifulSoup(html1)
				username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
				r = re.compile('a href="(.*?)"')
				m = r.search(str(username2))
				if m:	
					username3 = m.group(1)
					username3 = username3.replace("https://www.facebook.com/","")
					username3 = username3.replace("profile.php?id=","")
					print "[*] Extracting Data from Photo Page: "+username3
					tempList.append([str(uid),y['alt'],y['src'],i['href'],username3])
		for x in pageName:
			if x['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					filename = filename.replace("profile.php?id=","")
					if not os.path.lexists(filename):
						#html1 = downloadPage(url1)
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
				soup2 = BeautifulSoup(html1)
				username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
				r = re.compile('a href="(.*?)"')
				m = r.search(str(username2))
				if m:	
					username3 = m.group(1)
					username3 = username3.replace("https://www.facebook.com/","")
					username3 = username3.replace("profile.php?id=","")
					print "[*] Extracting Data from Photo Page: "+username3
					tempList.append([str(uid),x['alt'],x['src'],i['href'],username3])
	return tempList


def parsePhotosOf(html):
	soup = BeautifulSoup(html)	
	photoPageLink = soup.findAll("a", {"class" : "_23q"})
	tempList = []
	for i in photoPageLink:
		html = str(i)
		soup1 = BeautifulSoup(html)
		pageName = soup1.findAll("img", {"class" : "img"})
		pageName1 = soup1.findAll("img", {"class" : "scaledImageFitWidth img"})
		pageName2 = soup1.findAll("img", {"class" : "_46-i img"})	
		for z in pageName2:
			if z['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					filename = filename.replace("profile.php?id=","")
					if not os.path.lexists(filename):
						#html1 = downloadPage(url1)
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
				soup2 = BeautifulSoup(html1)
				username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
				r = re.compile('a href="(.*?)"')
				m = r.search(str(username2))
				if m:	
					username3 = m.group(1)
					username3 = username3.replace("https://www.facebook.com/","")
					username3 = username3.replace("profile.php?id=","")
					print "[*] Extracting Data from Photo Page: "+username3
					tempList.append([str(uid),z['alt'],z['src'],i['href'],username3])
		for y in pageName1:
			if y['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					filename = filename.replace("profile.php?id=","")
					if not os.path.lexists(filename):
						#html1 = downloadPage(url1)
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
				soup2 = BeautifulSoup(html1)
				username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
				r = re.compile('a href="(.*?)"')
				m = r.search(str(username2))
				if m:	
					username3 = m.group(1)
					username3 = username3.replace("https://www.facebook.com/","")
					username3 = username3.replace("profile.php?id=","")
					print "[*] Extracting Data from Photo Page: "+username3
					tempList.append([str(uid),y['alt'],y['src'],i['href'],username3])
		for x in pageName:
			if x['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					filename = filename.replace("profile.php?id=","")
					if not os.path.lexists(filename):
						#html1 = downloadPage(url1)
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
				soup2 = BeautifulSoup(html1)
				username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
				r = re.compile('a href="(.*?)"')
				m = r.search(str(username2))
				if m:	
					username3 = m.group(1)
					username3 = username3.replace("https://www.facebook.com/","")
					username3 = username3.replace("profile.php?id=","")
					print "[*] Extracting Data from Photo Page: "+username3
					tempList.append([str(uid),x['alt'],x['src'],i['href'],username3])
	return tempList


def parsePhotosLiked(html):
	soup = BeautifulSoup(html)	
	photoPageLink = soup.findAll("a", {"class" : "_23q"})
	tempList = []

	for i in photoPageLink:
		html = str(i)
		soup1 = BeautifulSoup(html)
		pageName = soup1.findAll("img", {"class" : "img"})
		pageName1 = soup1.findAll("img", {"class" : "scaledImageFitWidth img"})
		pageName2 = soup1.findAll("img", {"class" : "_46-i img"})	
		for z in pageName2:
			if z['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					filename = filename.replace("profile.php?id=","")
					if not os.path.lexists(filename):
						#html1 = downloadPage(url1)
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
					soup2 = BeautifulSoup(html1)
					username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
					r = re.compile('a href="(.*?)"')
					m = r.search(str(username2))
					if m:	
						
						username3 = m.group(1)
						username3 = username3.replace("https://www.facebook.com/","")
						username3 = username3.replace("profile.php?id=","")
						if username3.count('/')==2:
							username3 = username3.split('/')[2]
	
						print "[*] Extracting Data from Photo Page: "+username3
						tmpStr = []
						tmpStr.append([str(uid),repr(zlib.compress(normalize(z['alt']))),normalize(z['src']),normalize(i['href']),normalize(username3)])
						write2Database('photosLiked',tmpStr)

		for y in pageName1:
			if y['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					filename = filename.replace("profile.php?id=","")
					if not os.path.lexists(filename):
						#html1 = downloadPage(url1)
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
					soup2 = BeautifulSoup(html1)
					username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
					r = re.compile('a href="(.*?)"')
					m = r.search(str(username2))
					if m:	
						username3 = m.group(1)
						username3 = username3.replace("https://www.facebook.com/","")
						username3 = username3.replace("profile.php?id=","")
						if username3.count('/')==2:
							username3 = username3.split('/')[2]

						print "[*] Extracting Data from Photo Page: "+username3
						tmpStr = []
						tmpStr.append([str(uid),repr(zlib.compress(normalize(y['alt']))),normalize(y['src']),normalize(i['href']),normalize(username3)])
						write2Database('photosLiked',tmpStr)

		for x in pageName:
			if x['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					filename = filename.replace("profile.php?id=","")
					if not os.path.lexists(filename):
						#html1 = downloadPage(url1)
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
					soup2 = BeautifulSoup(html1)
					username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
					r = re.compile('a href="(.*?)"')
					m = r.search(str(username2))
					if m:	
						username3 = m.group(1)
						username3 = username3.replace("https://www.facebook.com/","")
						username3 = username3.replace("profile.php?id=","")
						if username3.count('/')==2:
							username3 = username3.split('/')[2]

						print "[*] Extracting Data from Photo Page: "+username3
						tmpStr = []
						tmpStr.append([str(uid),repr(zlib.compress(normalize(x['alt']))),normalize(x['src']),normalize(i['href']),normalize(username3)])
						write2Database('photosLiked',tmpStr)

	return tempList

def downloadPage(url):
	driver.get(url)	
	html = driver.page_source
	return html

def parsePhotosCommented(html):
	soup = BeautifulSoup(html)	
	photoPageLink = soup.findAll("a", {"class" : "_23q"})
	tempList = []

	for i in photoPageLink:
		html = str(i)
		soup1 = BeautifulSoup(html)
		pageName = soup1.findAll("img", {"class" : "img"})
		pageName1 = soup1.findAll("img", {"class" : "scaledImageFitWidth img"})
		pageName2 = soup1.findAll("img", {"class" : "_46-i img"})	
		for z in pageName2:
			if z['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					if not os.path.lexists(filename):
						html1 = downloadFile(url1)
						#html1 = downloadPage(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
				soup2 = BeautifulSoup(html1)
				username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
				r = re.compile('a href="(.*?)"')
				m = r.search(str(username2))
				if m:	
					username3 = m.group(1)
					username3 = username3.replace("https://www.facebook.com/","")
					if username3.count('/')==2:
						username3 = username3.split('/')[2]

					print "[*] Extracting Data from Photo Page: "+username3
					tempList.append([str(uid),z['alt'],z['src'],i['href'],username3])
		for y in pageName1:
			if y['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					if not os.path.lexists(filename):
						html1 = downloadFile(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
				soup2 = BeautifulSoup(html1)
				username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
				r = re.compile('a href="(.*?)"')
				m = r.search(str(username2))
				if m:	
					username3 = m.group(1)
					username3 = username3.replace("https://www.facebook.com/","")
					if username3.count('/')==2:
						username3 = username3.split('/')[2]

					print "[*] Extracting Data from Photo Page: "+username3
					tempList.append([str(uid),y['alt'],y['src'],i['href'],username3])
		for x in pageName:
			if x['src'].endswith('.jpg'):
				url1 = i['href']
				r = re.compile('fbid=(.*?)&set=bc')
				m = r.search(url1)
				if m:
					filename = 'fbid_'+ m.group(1)+'.html'
					if not os.path.lexists(filename):
						html1 = downloadFile(url1)
						#html1 = downloadPage(url1)
						print "[*] Caching Photo Page: "+m.group(1)
						text_file = open(filename, "w")
						text_file.write(normalize(html1))
						text_file.close()
					else:
						html1 = open(filename, 'r').read()
				soup2 = BeautifulSoup(html1)
				username2 = soup2.find("div", {"class" : "fbPhotoContributorName"})
				r = re.compile('a href="(.*?)"')
				m = r.search(str(username2))
				if m:	
					username3 = m.group(1)
					username3 = username3.replace("https://www.facebook.com/","")
					if username3.count('/')==2:
						username3 = username3.split('/')[2]
					print "[*] Extracting Data from Photo Page: "+username3
					tempList.append([str(uid),x['alt'],x['src'],i['href'],username3])

	return tempList

def parseVideosBy(html):
	soup = BeautifulSoup(html)	
	appsData = soup.findAll("div", {"class" : "_42bw"})
	tempList = []
	for x in appsData:
		r = re.compile('href="(.*?)&amp;')
		m = r.search(str(x))
		if m:
			filename = str(m.group(1)).replace("https://www.facebook.com/photo.php?v=","v_")
			filename = filename+".html"
			url = m.group(1)
			if not os.path.lexists(filename):
				html1 = downloadFile(url)
				#driver.get(url)	
				#html1 = driver.page_source
				text_file = open(filename, "w")
				text_file.write(normalize(html1))
				text_file.close()
			else:
				html1 = open(filename, 'r').read()
			soup1 = BeautifulSoup(html1)	
			titleData = soup1.find("h2", {"class" : "uiHeaderTitle"})
			tempList.append([uid,(titleData.text).strip(),url])
	return tempList
	
def parseAppsUsed(html):
	soup = BeautifulSoup(html)	
	appsData = soup.findAll("div", {"class" : "_zs fwb"})
	tempList = []
	for x in appsData:
		tempList.append(x.text)
	return tempList

def sidechannelFriends(uid):
	userList = []
	c = conn.cursor()
	c.execute('select distinct username from photosLiked where sourceUID=?',(uid,))
	dataList1 = []
	dataList1 = c.fetchall()
	if len(dataList1)>0:
		for i in dataList1:
			if 'pages' not in str(normalize(i[0])):
				userList.append([uid,'',str(normalize(i[0])),'',''])
	c.execute('select distinct username from photosCommented where sourceUID=?',(uid,))
	dataList1 = []
	dataList1 = c.fetchall()
	if len(dataList1)>0:	
		for i in dataList1:
			if 'pages' not in str(normalize(i[0])):
				userList.append([uid,'',str(normalize(i[0])),'',''])
	c.execute('select distinct username from photosOf where sourceUID=?',(uid,))
	dataList1 = []
	dataList1 = c.fetchall()
	if len(dataList1)>0:	
		for i in dataList1:
			if 'pages' not in str(normalize(i[0])):
				userList.append([uid,'',str(normalize(i[0])),'',''])
	return userList

def getFriends(uid):
	userList = []
	c = conn.cursor()
	c.execute('select username from friends where sourceUID=?',(uid,))
	dataList1 = []
	dataList1 = c.fetchall()
	if len(dataList1)>0:
		for i in dataList1:
			userList.append([uid,'',str(normalize(i)),'',''])
	return userList
	
def parseFriends(html):
	mthList = ['january','february','march','april','may','june','july','august','september','october','november','december']
	if len(html)>0:
		soup = BeautifulSoup(html)	

		friendBlockData = soup.findAll("div",{"class" : "_1zf"})
		friendNameData = soup.findAll("div", {"class" : "_zs fwb"})
		knownSinceData = soup.findAll("div", {"class" : "_52eh"})
	
		friendList=[]
		for i in friendBlockData:
			soup1 = BeautifulSoup(str(i))
			friendNameData = soup1.find("div",{"class" : "_zs fwb"})
			lastKnownData = soup1.find("div",{"class" : "_52eh"})
			r = re.compile('a href=(.*?)\?ref')
			m = r.search(str(friendNameData))
			if m:
				try:	
					friendName = friendNameData.text
					friendName = friendName.replace('"https://www.facebook.com/','')
					value = (lastKnownData.text).split("since")[1].strip()
					#Current year - No year listed in page
					if not re.search('\d+', value):					
						value = value+" "+str((datetime.datetime.now()).year)
						month = ((re.sub(" \d+", " ", value)).lower()).strip()
						monthDigit = 0
						count=0
						for s in mthList:
							if s==month:
								monthDigit=count+1
							count+=1	
						year = re.findall("(\d+)",value)[0]
						fbID = m.group(1).replace('"https://www.facebook.com/','')
						friendList.append([str(uid),friendName,fbID,int(monthDigit),int(year)])
					else:
						#Not current year
						month,year = value.split(" ")
						month = month.lower()
						monthDigit = 0
						count=0
						for s in mthList:
							if s==month:
								monthDigit=count+1
							count+=1
						fbID = m.group(1).replace('"https://www.facebook.com/','')
						friendList.append([str(uid),friendName,fbID,int(monthDigit),int(year)])
	

				except IndexError:
					continue
				except AttributeError:
					continue
		i=0
		data = sorted(friendList, key=operator.itemgetter(4,3))
		#print "Friends List"
		#for x in data:
		#	print x
		#	#print x[2]+'\t'+x[1]
		return data

    	
"""
def analyzeFriends(userid):
	c = conn.cursor()
	c.execute('select * from friends where sourceUID=?',(userid,))
	dataList = c.fetchall()
	photosliked = []
	photoscommented = []
	userID = []
	for i in dataList:
		#print i[1]+'\t'+i[2]
		#c.execute('select username from photosLiked')
		c.execute('select * from photosLiked where sourceUID=? and username=?',(userid,i[2],))
		dataList1 = []
		dataList1 = c.fetchall()
		if len(dataList1)>0:
			str1 = ([dataList1[0][4].encode('utf8'),str(len(dataList1))])
			photosliked.append(str1)
		
		c.execute('select * from photosCommented where sourceUID=? and username=?',(userid,i[2],))
		dataList1 = []
		dataList1 = c.fetchall()
		if len(dataList1)>0:
			str1 = ([dataList1[0][4].encode('utf8'),str(len(dataList1))])
			photoscommented.append(str1)
	print "[*] Videos Posted By "+str(username)
	filename = username+'_videosBy.htm'
	if not os.path.lexists(filename):
		html = downloadVideosBy(driver,uid)
		text_file = open(filename, "w")
		text_file.write(html.encode('utf8'))
		text_file.close()
	else:
		html = open(filename, 'r').read()
	dataList = parseVideosBy(html)
	count=1
	for i in dataList:
		print str(count)+') '+i[1]+'\t'+i[2]
		count+=1
	print "\n"

	print "[*] Pages Liked By "+str(uid)
	filename = username+'_pages.htm'
	if not os.path.lexists(filename):
		html = downloadPagesLiked(driver,uid)
		text_file = open(filename, "w")
		text_file.write(html.encode('utf8'))
		text_file.close()
	else:
		html = open(filename, 'r').read()
	dataList = parsePagesLiked(html)
	for i in dataList:
		print "[*] "+normalize(i[1])
		#print "[*] "+normalize(i[2])+"\t"+normalize(i[1])+"\t"+normalize(i[3])
		#print normalize(i[1])+"\t"+normalize(i[2])+"\t"+normalize(i[3])
	print "\n"

"""

	
def mainProcess(username):
	username = username.strip()
	print "[*] Username:\t"+str(username)
	global uid
	
	loginFacebook(driver)
	uid = convertUser2ID2(driver,username)
	if not uid:
		print "[!] Problem converting username to uid"
		sys.exit()
	else:
		print "[*] Uid:\t"+str(uid)

	filename = username+'_apps.htm'
	if not os.path.lexists(filename):
		print "[*] Caching Facebook Apps Used By: "+username
		html = downloadAppsUsed(driver,uid)
		text_file = open(filename, "w")
		text_file.write(html.encode('utf8'))
		text_file.close()
	else:
		html = open(filename, 'r').read()
	data1 = parseAppsUsed(html)
	result = ""
	for x in data1:
		print x	
		x = x.lower()
		if "blackberry" in x:
			result += "[*] User is using a Blackberry device\n"
		if "android" in x:
			result += "[*] User is using an Android device\n"
		if "ios" in x or "ipad" in x or "iphone" in x:
			result += "[*] User is using an iOS Apple device\n"
		if "samsung" in x:
			result += "[*] User is using a Samsung Android device\n"
	print result

	#Caching Pages Liked - Start
	filename = username+'_pages.htm'
	if not os.path.lexists(filename):
		print "[*] Caching Pages Liked By: "+username
		html = downloadPagesLiked(driver,uid)
          	text_file = open(filename, "w")
          	text_file.write(html.encode('utf8'))
          	text_file.close()
       	else:
        	html = open(filename, 'r').read()
        dataList = parsePagesLiked(html)
        if len(dataList)>0:
	        write2Database('pagesLiked',dataList)
	#Caching Pages Liked - End

        filename = username+'_videosBy.htm'
        if not os.path.lexists(filename):
           	print "[*] Caching Videos Liked By: "+username
           	html = downloadVideosBy(driver,uid)
		text_file = open(filename, "w")
		text_file.write(html.encode('utf8'))
            	text_file.close()
        else:
            	html = open(filename, 'r').read()
        dataList = parseVideosBy(html)
        if len(dataList)>0:
	        write2Database('videosBy',dataList)

        filename = username+'_photosOf.htm'
        if not os.path.lexists(filename):
            	print "[*] Caching Photos Of: "+username
            	html = downloadPhotosOf(driver,uid)
            	text_file = open(filename, "w")
            	text_file.write(html.encode('utf8'))
            	text_file.close()
        else:
            	html = open(filename, 'r').read()
        dataList = parsePhotosOf(html)
        write2Database('photosOf',dataList)
        
        filename = username+'_photosBy.htm'
        if not os.path.lexists(filename):
            	print "[*] Caching Photos By: "+username
            	html = downloadPhotosOf(driver,uid)
            	text_file = open(filename, "w")
            	text_file.write(html.encode('utf8'))
            	text_file.close()
        else:
            	html = open(filename, 'r').read()
        dataList = parsePhotosOf(html)
        write2Database('photosBy',dataList)        

	#Disable
   	filename = username+'_photosLiked.htm'
   	print filename
        if not os.path.lexists(filename):
           	print "[*] Caching Photos Liked By: "+username
            	html = downloadPhotosLiked(driver,uid)
            	text_file = open(filename, "w")
            	text_file.write(html.encode('utf8'))
            	text_file.close()
        else:
            	html = open(filename, 'r').read()
        dataList = parsePhotosLiked(html)
        print "[*] Writing "+str(len(dataList))+" records to table: photosLiked"
        #write2Database('photosLiked',dataList)

        filename = username+'_photoscommented.htm'
    	print filename
        if not os.path.lexists(filename):
           	print "[*] Caching Commented On By: "+username
            	html = downloadPhotosCommented(driver,uid)
            	text_file = open(filename,"w")
            	text_file.write(html.encode('utf8'))
            	text_file.close()
        else:
            	html = open(filename, 'r').read()
        dataList = parsePhotosCommented(html)
        write2Database('photosCommented',dataList)

        filename = username+'_friends.htm'
        print filename
        if not os.path.lexists(filename):
           	print "[*] Caching Friends Page of: "+username
            	html = downloadFriends(driver,uid)
            	text_file = open(filename, "w")
            	text_file.write(html.encode('utf8'))
            	text_file.close()
       	else:
            	html = open(filename, 'r').read()
        if len(html.strip())>1:
            	dataList = parseFriends(html)
            	print "[*] Writing Friends List to Database: "+username
            	write2Database('friends',dataList)
	else:
           	print "[*] Extracting Friends from Likes/Comments: "+username
            	write2Database('friends',sidechannelFriends(uid))	
            	
        c = conn.cursor()
        c.execute('select * from friends where sourceUID=?',(uid,))
        dataList = c.fetchall()
        photosliked = []
        photoscommented = []
        userID = []
        for i in dataList:
            #print i[1]+'\t'+i[2]
            #c.execute('select username from photosLiked')
            c.execute('select * from photosLiked where sourceUID=? and username=?',(uid,i[2],))
            dataList1 = []
            dataList1 = c.fetchall()
            if len(dataList1)>0:
                str1 = ([dataList1[0][4].encode('utf8'),str(len(dataList1))])
                photosliked.append(str1)
        
            c.execute('select * from photosCommented where sourceUID=? and username=?',(uid,i[2],))
            dataList1 = []
            dataList1 = c.fetchall()
            if len(dataList1)>0:
                str1 = ([dataList1[0][4].encode('utf8'),str(len(dataList1))])
                photoscommented.append(str1)            	
            	
	

        #analyzeFriends(str(uid))
        filename = username+'.htm'
        if not os.path.lexists(filename):
           	print "[*] Caching Timeline Page of: "+username
            	html = downloadTimeline(username)
            	text_file = open(filename, "w")
            	text_file.write(html.encode('utf8'))
            	text_file.close()
        else:
            	html = open(filename, 'r').read()
        dataList = parseTimeline(html,username)


	print "\n"
	print "[*] Downloading User Information"

	tmpInfoStr = []
	userID =  getFriends(uid)
	for x in userID:
		i = str(normalize(x[2]))
		i = i.replace("(u'","").replace("',","").replace(')','')
		i = i.replace('"https://www.facebook.com/','')
		print "[*] Looking up information on "+i
		filename = i.encode('utf8')+'.html'
		if "/" not in filename:
			if not os.path.lexists(filename):
				print 'Writing to '+filename
				url = 'https://www.facebook.com/'+i.encode('utf8')+'/info'
				html = downloadFile(url)	
				#html = downloadUserInfo(driver,i.encode('utf8'))
				if len(html)>0:
					text_file = open(filename, "w")
					text_file.write(normalize(html))
					#text_file.write(html.encode('utf8'))
					text_file.close()
			else:
				print 'Skipping: '+filename
			print "[*] Parsing User Information: "+i
			html = open(filename, 'r').read()
			userInfoList = parseUserInfo(html)[0]
			tmpStr = []
			tmpStr.append([uid,str(normalize(i)),str(normalize(userInfoList[0])),str(normalize(userInfoList[1])),str(normalize(userInfoList[2])),str(normalize(userInfoList[3])),str(normalize(userInfoList[4])),str(normalize(userInfoList[5])),normalize(str(userInfoList[6]).encode('utf8'))])
			try:
				write2Database('friendsDetails',tmpStr)
			except:
				continue
			#tmpInfoStr.append([uid,str(normalize(i)),str(normalize(userInfoList[0])),str(normalize(userInfoList[1])),str(normalize(userInfoList[2])),str(normalize(userInfoList[3])),str(normalize(userInfoList[4])),str(normalize(userInfoList[5])),str(normalize(userInfoList[6]))])
			#tmpInfoStr.append([i[1],userInfoList[0],userInfoList[1],userInfoList[2],userInfoList[3],userInfoList[4],userInfoList[5],userInfoList[6]])

	#cprint("[*] Writing "+str(len(dataList))+" record(s) to database table: "+dbName,"white")
	cprint("[*] Report has been written to: "+str(reportFileName),"white")
	cprint("[*] Preparing Maltego output...","white")
	createMaltego(username)
	cprint("[*] Maltego file has been created","white")

    	driver.close()
        driver.quit
        conn.close()


def options(arguments):
	user = ""
	count = 0
 	for arg in arguments:
  		if arg == "-user":
			count+=1
   			user = arguments[count+1]
  		if arg == "-report":
			count+=1
			global reportFileName
   			reportFileName = arguments[count+1]
  	mainProcess(user)


def showhelp():

	print ""
	print "	MMMMMM$ZMMMMMDIMMMMMMMMNIMMMMMMIDMMMMMMM"
	print "	MMMMMMNINMMMMDINMMMMMMMZIMMMMMZIMMMMMMMM"
	print "	MMMMMMMIIMMMMMI$MMMMMMMIIMMMM8I$MMMMMMMM"
	print "	MMMMMMMMIINMMMIIMMMMMMNIIMMMOIIMMMMMMMMM"
	print "	MMMMMMMMOIIIMM$I$MMMMNII8MNIIINMMMMMMMMM"
	print "	MMMMMMMMMZIIIZMIIIMMMIIIM7IIIDMMMMMMMMMM"
	print "	MMMMMMMMMMDIIIIIIIZMIIIIIII$MMMMMMMMMMMM"
	print "	MMMMMMMMMMMM8IIIIIIZIIIIIIMMMMMMMMMMMMMM"
	print "	MMMMMMMMMMMNIIIIIIIIIIIIIIIMMMMMMMMMMMMM"
	print "	MMMMMMMMM$IIIIIIIIIIIIIIIIIII8MMMMMMMMMM"
	print "	MMMMMMMMIIIIIZIIIIZMIIIIIDIIIIIMMMMMMMMM"
	print "	MMMMMMOIIIDMDIIIIZMMMIIIIIMMOIIINMMMMMMM"
	print "	MMMMMNIIIMMMIIII8MMMMM$IIIZMMDIIIMMMMMMM"
	print "	MMMMIIIZMMM8IIIZMMMMMMMIIIIMMMM7IIZMMMMM"
	print "	MMM$IIMMMMOIIIIMMMMMMMMMIIIIMMMM8IIDMMMM"
	print "	MMDIZMMMMMIIIIMMMMMMMMMMNIII7MMMMNIIMMMM"
	print "	MMIOMMMMMNIII8MMMMMMMMMMM7IIIMMMMMM77MMM"
	print "	MO$MMMMMM7IIIMMMMMMMMMMMMMIII8MMMMMMIMMM"
	print "	MIMMMMMMMIIIDMMMMMMMMMMMMM$II7MMMMMMM7MM"
	print "	MMMMMMMMMIIIMMMMMMMMMMMMMMMIIIMMMMMMMDMM"
	print "	MMMMMMMMMII$MMMMMMMMMMMMMMMIIIMMMMMMMMMM"
	print "	MMMMMMMMNIINMMMMMMMMMMMMMMMOIIMMMMMMMMMM"
	print "	MMMMMMMMNIOMMMMMMMMMMMMMMMMM7IMMMMMMMMMM"
	print "	MMMMMMMMNINMMMMMMMMMMMMMMMMMZIMMMMMMMMMM"
	print "	MMMMMMMMMIMMMMMMMMMMMMMMMMMM8IMMMMMMMMMM"

	print """
	#####################################################
	#                  fbStalker.py                 #
	#               [Trustwave Spiderlabs]              #
	#####################################################
	Usage: python fbStalker.py [OPTIONS]

	[OPTIONS]

	-user   [Facebook Username]
	-report [Filename]
	"""

if __name__ == '__main__':
	if len(sys.argv) <= 1:
		showhelp()
		driver.close()
		driver.quit
		conn.close()
		sys.exit()
 	else:
		if len(facebook_username)<1 or len(facebook_password)<1:
			print "[*] Please fill in 'facebook_username' and 'facebook_password' before continuing."
			sys.exit()
  		options(sys.argv)
 

########NEW FILE########
__FILENAME__ = geostalker
#!/usr/env python
#-*- coding: utf-8 -*-
from __future__ import division
import zipfile
from pygraphml.GraphMLParser import *
from pygraphml.Graph import *
from pygraphml.Node import *
from pygraphml.Edge import *
from random import randint
from BeautifulSoup import BeautifulSoup
from datetime import date
from google import search
from instagram.client import InstagramAPI
from linkedin import linkedin
from lxml import etree,html
from pprint import pprint
from pygeocoder import Geocoder
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from StringIO import StringIO
from termcolor import colored, cprint
from TwitterSearch import *
from requests import session
from xml.dom import minidom
import atom.data, gdata.client, gdata.docs.client, gdata.docs.data, gdata.docs.service
import cookielib
import foursquare
import geopy
import geopy.distance
import google
import httplib,httplib2,json
import lxml
import oauth2 as oauth
import os
import re
import requests
import sqlite3
import string
import sys
import time, os, simplejson
import urllib
import urllib2
import webbrowser
import zlib

tweetList = []
globalUserList = []
nodeList = []
edgeList = []	
foursqTwitterSearch = []

report = ""
maltegoXML = ''
wirelessAPData = ""

#Gmail
google_username = ""
google_password = ""
google_drive_collection = "kkk"

#Instagram
#http://instagram.com/developer/register/
instagram_client_id = ""
instagram_client_secret = ""
instagram_access_token = ""

#Foursquare
foursquare_client_id = ""
foursquare_client_secret = ""
foursquare_access_token = ""


#Linkedin
linkedin_api_key = ""
linkedin_api_secret = ""
linkedin_oauth_user_token = ""
linkedin_oauth_user_secret = ""
linkedin_username = ""
linkedin_password = ""

#Flick
#Instructions on getting oauth token and secret
#http://librdf.org/flickcurl/api/flickcurl-auth-authenticate.html
flickr_key = ""
flickr_secret = ""
flickr_oauth_token = ""
flickr_oauth_secret = ""

#Twitter
twitter_consumer_key = ""
twitter_consumer_secret = ""
twitter_access_key = ""
twitter_access_secret = ""

#Wigle.net
wigle_username = ""
wigle_password = ""

requests.adapters.DEFAULT_RETRIES = 30

lat = ''
lng = ''

htmlHeader = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"><html xmlns="http://www.w3.org/1999/xhtml"><head><meta charset="UTF-8"><title>Google Maps Example</title><script src=\'http://code.jquery.com/jquery.min.js\' type=\'text/javascript\'></script></head><body><script type="text/javascript" src="http://maps.google.com/maps/api/js?sensor=false"></script>'

def createDatabase():
	c = conn.cursor()
	sql = 'create table if not exists twitter (username TEXT, tweet TEXT unique, latitude TEXT, longitude TEXT , origLat TEXT, origLng TEXT)'
	sql1 = 'create table if not exists instagram (username TEXT, latitude TEXT, longitude TEXT, url TEXT unique , origLat TEXT, origLng TEXT)'
	#sql2 = 'create table if not exists flickr (URL TEXT unique, username TEXT, cameraModel TEXT, longitude TEXT, latitude TEXT, origLat TEXT, origLng TEXT)'
	sql2 = 'create table if not exists flickr (URL TEXT unique, description TEXT, username TEXT, cameraModel TEXT, longitude TEXT, latitude TEXT, origLat TEXT, origLng TEXT)'
	sql3 = 'create table if not exists macAddress (macAddress TEXT unique, manufacturer TEXT)'
	c.execute(sql)
	c.execute(sql1)
	c.execute(sql2)
	c.execute(sql3)	
	conn.commit()
	

conn = sqlite3.connect('geostalking.db')
createDatabase()

def normalize(s):
	if type(s) == unicode: 
       		return s.encode('utf8', 'ignore')
	else:
        	return str(s)
	        	
def createLink(label):
	xmlString = '<mtg:MaltegoLink xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.link.manual-link">'
	xmlString += '<mtg:Properties>'
	xmlString += '<mtg:Property displayName="Description" hidden="false" name="maltego.link.manual.description" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Style" hidden="false" name="maltego.link.style" nullable="true" readonly="false" type="int">'
	xmlString += '<mtg:Value>0</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Label" hidden="false" name="maltego.link.manual.type" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+label+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Show Label" hidden="false" name="maltego.link.show-label" nullable="true" readonly="false" type="int">'
	xmlString += '<mtg:Value>0</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Thickness" hidden="false" name="maltego.link.thickness" nullable="true" readonly="false" type="int">'
	xmlString += '<mtg:Value>2</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Color" hidden="false" name="maltego.link.color" nullable="true" readonly="false" type="color">'
	xmlString += '<mtg:Value>8421505</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '</mtg:Properties>'
	xmlString += '</mtg:MaltegoLink>'
	return xmlString

def createNodeImage(name,url):
	xmlString = '<mtg:MaltegoEntity xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.Image">'
	xmlString += '<mtg:Properties>'
	xmlString += '<mtg:Property displayName="Description" hidden="false" name="description" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+name+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="URL" hidden="false" name="url" nullable="true" readonly="false" type="url">'
	xmlString += '<mtg:Value>'+url+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '</mtg:Properties>'
	xmlString += '</mtg:MaltegoEntity>'
	return xmlString

def createNodeFacebook(displayName,url,uid):
	xmlString = '<mtg:MaltegoEntity xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.affiliation.Facebook">'
	xmlString += '<mtg:Properties>'
	xmlString += '<mtg:Property displayName="Name" hidden="false" name="person.name" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+displayName+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Network" hidden="false" name="affiliation.network" nullable="true" readonly="true" type="string">'
	xmlString += '<mtg:Value>Facebook</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="UID" hidden="false" name="affiliation.uid" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+uid+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Profile URL" hidden="false" name="affiliation.profile-url" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>'+url+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '</mtg:Properties>'
	xmlString += '</mtg:MaltegoEntity>'
	return xmlString

def createNodeUrl(displayName,url):
        xmlString = '<mtg:MaltegoEntity xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.URL">'
        xmlString += '<mtg:Properties>'
        xmlString += '<mtg:Property displayName="'+displayName+'" hidden="false" name="short-title" nullable="true" readonly="false" type="string">'
        xmlString += '<mtg:Value>'+displayName+'</mtg:Value>'
        xmlString += '</mtg:Property>'
        xmlString += '<mtg:Property displayName="'+displayName+'" hidden="false" name="url" nullable="true" readonly="false" type="url">'  
        xmlString += '<mtg:Value>'+displayName+'</mtg:Value>'
        xmlString += '</mtg:Property>'
        xmlString += '<mtg:Property displayName="Title" hidden="false" name="title" nullable="true" readonly="false" type="string">'
        xmlString += '<mtg:Value/>'    
        xmlString += '</mtg:Property>'
        xmlString += '</mtg:Properties>'
        xmlString += '</mtg:MaltegoEntity>'
	return xmlString

def createNodeLocation(lat,lng):
	xmlString = '<mtg:MaltegoEntity xmlns:mtg="http://maltego.paterva.com/xml/mtgx" type="maltego.Location">'
	xmlString += '<mtg:Properties>'
	xmlString += '<mtg:Property displayName="Name" hidden="false" name="location.name" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value>lat='+str(lat)+' lng='+str(lng)+'</mtg:Value>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Area Code" hidden="false" name="location.areacode" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Area" hidden="false" name="location.area" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Latitude" hidden="false" name="latitude" nullable="true" readonly="false" type="float">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Longitude" hidden="false" name="longitude" nullable="true" readonly="false" type="float">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Country" hidden="false" name="country" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Country Code" hidden="false" name="countrycode" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="City" hidden="false" name="city" nullable="true" readonly="false" type="string">'
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '<mtg:Property displayName="Street Address" hidden="false" name="streetaddress" nullable="true" readonly="false" type="string">'	
	xmlString += '<mtg:Value/>'
	xmlString += '</mtg:Property>'
	xmlString += '</mtg:Properties>'
	xmlString += '</mtg:MaltegoEntity>'
	return xmlString

def cleanUpGraph(filename):
	newContent = []
	with open(filename) as f:
		content = f.readlines()
		for i in content:
			if '<key attr.name="node" attr.type="string" id="node"/>' in i:
				i = i.replace('name="node" attr.type="string"','name="MaltegoEntity" for="node"')
			if '<key attr.name="link" attr.type="string" id="link"/>' in i:
				i = i.replace('name="link" attr.type="string"','name="MaltegoLink" for="edge"')
			i = i.replace("&lt;","<")
			i = i.replace("&gt;",">")
			i = i.replace("&quot;",'"')
			print i.strip()
			newContent.append(i.strip())

	f = open(filename,'w')
	for item in newContent:
		f.write("%s\n" % item)
	f.close()
	        	
def createGoogleMap(dataList,lat,lng):
	html = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
	html += '<html xmlns="http://www.w3.org/1999/xhtml">'
	html += '<head>'
	html += '<title>Google Maps Example</title>'
	html += "<script src='http://code.jquery.com/jquery.min.js' type='text/javascript'></script>"
	html += '</head>'
	html += '<body>'
	html += '<script type="text/javascript" src="http://maps.google.com/maps/api/js?sensor=false"></script>'
	html = ''
	html += '<script type="text/javascript">'
	html += 'var infowindow = null;'
	html += ' $(document).ready(function () { initialize();  });'
	html += '    function initialize() {'
	html += '        var centerMap = new google.maps.LatLng('+str(lat)+','+str(lng)+');'
	html += '        var myOptions = {'
	html += '            zoom: 14,'
	html += '            center: centerMap,'
	html += '            mapTypeId: google.maps.MapTypeId.ROADMAP'
	html += '        }\n'
	html += '        var map = new google.maps.Map(document.getElementById("map_canvas"), myOptions);'
	html += '	  var marker = new google.maps.Marker({'
	html += '      	  	position: centerMap,'
	html += '     		map: map,'
	html += '		title: "Checkpoint"'
	html += '	  });'
	html += '        setMarkers(map, sites);'
	html += '	    infowindow = new google.maps.InfoWindow({'
	html += '                content: "loading..."'
	html += '            });'
	html += '        var bikeLayer = new google.maps.BicyclingLayer();'
	html += '		bikeLayer.setMap(map);'
 	html += '   }'
	html += '   var sites = ['
	
	for i in dataList:	
		popupHtml = ''
		popupHtml += i[0]+'<br>'
		popupHtml += i[1]+','+i[2]+'<br>'
		moreInfo = i[4]
		popupHtml += moreInfo.decode('utf-8')
		popupHtml = popupHtml.replace('\n',' ').replace('\r',' ')
		
		if len(i[3].strip())<1:
			i[3] = 'http://img820.imageshack.us/img820/9217/gtz7.png'
			#i[3]='https://maps.google.com/mapfiles/kml/shapes/man.png'
		#point = '["'+i[0]+'","'+i[1]+'","'+i[2]+'","'+i[3]+'",'"+popupHtml+"'],"
		point = "['"+i[0]+"',"+i[1]+","+i[2]+" ,'"+i[3]+"','"+popupHtml+"'],"
		#point = "['"+i[0]+"',"+i[1]+","+i[2]+" ,'"+i[3]+"','"+str(normalize(popupHtml.encode('ascii','replace')))+"'],"
		#point = "['"+i[0]+"',"+i[1]+","+i[2]+" ,'"+i[3]+"',''],"
		#point = "[\""+str(normalize(i[0].encode('ascii','replace')))+"\","+str(normalize(i[1].encode('ascii','replace')))+","+str(normalize(i[2].encode('ascii','replace')))+" ,'"+str(normalize(i[3].encode('ascii','replace')))+"','"+str(normalize(popupHtml.encode('ascii','replace')))+"'],"
		html += point	
			
	html += '    ];'

	html += '    function setMarkers(map, markers) {'
	html += '        for (var i = 0; i < markers.length; i++) {'
	html += '            var sites = markers[i];'
	html += '            var siteLatLng = new google.maps.LatLng(sites[1], sites[2]);'
	html += ' 	     var myIcon = {'
	html += '		url : sites[3],'
	html += '		size: new google.maps.Size(60,60)'
	html += '	     };'
	html += '            var marker = new google.maps.Marker({'
	html += '                position: siteLatLng,'
	html += '                map: map,'
	html += '                title:sites[0],'
	html += '                html: sites[4],'
	html += '	         icon: myIcon'
	html += '            });'
	html += '            var contentString = "Some content";'
	html += '            google.maps.event.addListener(marker, "click", function () {'
	html += '                infowindow.setContent(this.html);'
	html += '                infowindow.open(map, this);'
	html += '            });'
	html += '        }'
	html += '    }'
	html += '</script>'
	html += '<div id="map_canvas" style="width: 800px; height: 600px;"></div>'

	"""
	html += '</body>'
	html += '</html>'
	"""
	return html
	
def uploadGoogleDocs(fullPath,file_type):
	collection = google_drive_collection 		
	fhandle = open(fullPath)
	file_size = os.path.getsize(fhandle.name)
	directory,filename = os.path.split(fullPath)
	print '[*] Uploading: '+filename+' to Google Docs!'
	docsclient = gdata.docs.client.DocsClient(source='RPi Python-GData 2.0.17')
	print '[*] Logging in...',
	try:
	    docsclient.ClientLogin(google_username, google_password, docsclient.source);
	except (gdata.client.BadAuthentication, gdata.client.Error), e:
	    sys.exit('Unknown Error: ' + str(e))
	except:
	    sys.exit('Login Error, perhaps incorrect username/password')
	print 'Login success!'
        uri = 'https://docs.google.com/feeds/upload/create-session/default/private/full'
        print 'Fetching collection ID...',
        try:
                resources = docsclient.GetAllResources(uri='https://docs.google.com/feeds/default/private/full/-/folder?title=' + collection + '&title-exact=true')
        except:
                sys.exit('ERROR: Unable to retrieve resources')
        # If no matching resources were found
        if not resources:
                sys.exit('Error: The collection "' + collection + '" was not found.')
        uri = resources[0].get_resumable_create_media_link().href
        print 'success!'
        uri += '?convert=false'
        print 'Starting uploading of file...',
        uploader = gdata.client.ResumableUploader(docsclient, fhandle, file_type, file_size, chunk_size=1048576, desired_class=gdata.data.GDEntry)
        new_entry = uploader.UploadFile(uri, entry=gdata.data.GDEntry(title=atom.data.Title(text=os.path.basename(fhandle.name))))
        print 'Upload success!'

def checkGoogleDocsExist(filename):
	print '[*] Checking Google Docs if File Exists'
	docsclient = gdata.docs.client.DocsClient(source='RPi Python-GData 2.0.17')
	# Get a list of all available resources (GetAllResources() requires >= gdata-2.0.15)
	print '[*] Logging in...',
	try:
	    docsclient.ClientLogin(google_username, google_password, docsclient.source);
	except (gdata.client.BadAuthentication, gdata.client.Error), e:
	    sys.exit('[!] Unknown Error: ' + str(e))
	except:
	    sys.exit('[!] Login Error, perhaps incorrect username/password')
	print 'Login success!'

        q = gdata.docs.client.DocsQuery(
            title=filename,
            title_exact='true',
            show_collections='true'
        )
        client = gdata.docs.service.DocsService()
        client.ClientLogin(google_username,google_password)
        try:
                folder = docsclient.GetResources(q=q).entry[0]
        except IndexError:
                print '[*] File does not exists!'
                return False
        cprint('[!] File: '+filename+' exists!','white')
        #print '[!] File: '+filename+' exists!'
        return True

def changePublicGoogleDocs(filename):
	print '[*] Change: '+filename+' Access to Public'
	docsclient = gdata.docs.client.DocsClient(source='RPi Python-GData 2.0.17')
	# Get a list of all available resources (GetAllResources() requires >= gdata-2.0.15)
	print '[*] Logging in...',
	try:
	    docsclient.ClientLogin(google_username, google_password, docsclient.source);
	except (gdata.client.BadAuthentication, gdata.client.Error), e:
	    sys.exit('Unknown Error: ' + str(e))
	except:
	    sys.exit('Login Error, perhaps incorrect username/password')
	print 'Login success!'

        q = gdata.docs.client.DocsQuery(
            title=filename,
            title_exact='true',
            show_collections='true'
        )
        client = gdata.docs.service.DocsService()
        client.ClientLogin(google_username,google_password)
        folder = docsclient.GetResources(q=q).entry[0]
        #print docsclient.GetResource(folder).title.text
        #print docsclient.GetResource(folder).resource_id.text
        resource_id = docsclient.GetResource(folder).resource_id.text
        acl_feed = docsclient.GetResourceAcl(folder)
        for acl in acl_feed.entry:
              print acl.role.value, acl.scope.type, acl.scope.value
        acl1 = gdata.docs.data.AclEntry(
                scope=gdata.acl.data.AclScope(value='', type='default'),
                role=gdata.acl.data.AclRole(value='reader'),
                batch_operation=gdata.data.BatchOperation(type='insert'),
        )
        acl_operations = [acl1]
        docsclient.BatchProcessAclEntries(folder, acl_operations)
        print 'Permissions change success!'
        return docsclient.GetResource(folder).resource_id.text

def loginWigle(wigle_username,wigle_password):
	payload = {
		'credential_0': wigle_username,
		'credential_1': wigle_password,
		'destination': '%2Fgps%2Fgps%2Fmain',
		'noexpire': 'on'
	}
	headers = {
		"Content-Type": "application/x-www-form-urlencoded",
		"Connection": "keep-alive",
		"Host": "wigle.net",
		"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20100101 Firefox/24.0",
		"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
		"Accept-Language": "en-US,en;q=0.5",
		"Accept-Encoding": "1",
		"Referer":"https://wigle.net/",
		"Content-Length": "85"
	}
	with session() as c:
		request = c.post('https://wigle.net//gps/gps/main/login', data=payload, headers=headers)
	wigle_cookie = request.headers.get('Set-Cookie')
	return wigle_cookie

def wigleHTML(inputHTML):
	html = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
	html += '<html xmlns="http://www.w3.org/1999/xhtml">'
	html += '<head>'
	html += '<title>Wigle Maps Export</title>'
	html += "<script src='http://code.jquery.com/jquery.min.js' type='text/javascript'></script>"
	html += '</head>'
	html += '<body>'
	html += '<script type="text/javascript" src="http://maps.google.com/maps/api/js?sensor=false"></script>'
	html += inputHTML
	html += '</body>'
	html += '</html>'
	text_file = open('wigle.html', "w")
	text_file.write(html)
	text_file.close()

def convertWigle2KML(filename):
	print "[*] Convert Wigle Database to KML format"
	f = open(filename,"r")
	data = f.readlines()
	infrastructureList = []
	adhocList = []
	wepList = []
	nowepList = []
	count=0
	for row in data:
		try: 
			if count>1:
				splitString = row.split('~')
				bssid = splitString[1]
				ssid = splitString[0]
				channel = splitString[15]
				coordinates = splitString[12]+","+splitString[11]
				qos = splitString[18].strip()
				lastseen = splitString[8]
				type = splitString[4]
				wep = splitString[10]					

				newAP = "<Placemark>\n<description>\n<![CDATA[\nSSID: "+ssid+"<BR>\n"
				newAP += "BSSID: "+bssid+"<BR>\n"
				newAP += "TYPE: "+type+"<BR>\n"
				newAP += "WEP: "+wep+"<BR>\n"
				newAP += "CHANNEL: "+channel+"<BR>\n"
				newAP += "QOS: "+qos+"<BR>\n"	
				newAP += "Last Seen: "+lastseen+"\n"
				if wep=="Y":
					newAP += "]]>\n</description>\n<name><![CDATA["+ssid+"]]></name>\n<Style>\n<IconStyle>\n<Icon>\n<href>http://irongeek.com/images/wapwep.png</href>\n</Icon>\n</IconStyle>\n</Style>\n<Point id='1'>\n<coordinates>"+coordinates+"</coordinates>\n</Point>\n</Placemark>"	
				else:
					newAP += "]]>\n</description>\n<name><![CDATA["+ssid+"]]></name>\n<Style>\n<IconStyle>\n<Icon>\n<href>http://irongeek.com/images/wap.png</href>\n</Icon>\n</IconStyle>\n</Style>\n<Point id='1'>\n<coordinates>"+coordinates+"</coordinates>\n</Point>\n</Placemark>"	
				newAP += "\n"
				
				if wep=="Y":			
					wepList.append(newAP)	
				else:
					nowepList.append(newAP)
			count+=1
		except IndexError:
			continue
	f.close()
	filenameParts = filename.split(".dat")
	newFilename = filenameParts[0]+".kml"
	print "[*] Convert wigle database to: "+str(newFilename)
	f = open(newFilename,"w")
	f.write('<?xml version="1.0" encoding=\"UTF-8\"?><kml xmlns=\"http://earth.google.com/kml/2.0\"><Folder><name>WiGLE Data</name><open>1</open>\n')
	f.write('<Folder><name>WEP</name><open>1</open>')
	for i in wepList:
		f.write(i)
	f.write('</Folder>\n')
	f.write('<Folder><name>No WEP</name><open>1</open>')
	for i in nowepList:
		f.write(i)
	f.write('</Folder>\n')
	f.write("</Folder></kml>")
	f.close()

def lookupMacAddress(macAddr):
	resultList = {}
	url = 'http://hwaddress.com/?q='+str(macAddr)
	#url = 'http://hwaddress.com/?q='+urllib.urlencode(str(macAddr))
	r = requests.get(url)
	html = r.content
	soup = BeautifulSoup(html)
	htmlBox1 = soup.find('table',attrs={'class':'framedlight'})
	soup2 = BeautifulSoup(str(htmlBox1))
	htmlBox2 = soup2.findAll('a',text=True)
	try:
		if len(htmlBox2)>1:
			return htmlBox2[14]
	except TypeError as e:
		pass
def parseWigleDat(filename):
	print "[*] Extracting MAC addresses from Wigle database: "+filename
	global report
	report += '\n\n[*] Wireless Access Points Database from Wigle'
	tempList = []
	macAddrDict = {}
	with open(filename) as f:
		content = f.readlines()
	counter=0
	for i in content:
		if counter>0:
			macAddr = i.split('~')[0][0:8]
			if macAddr not in tempList:
				tempList.append(macAddr)
		counter+=1
	for i in tempList:
		#print "[*] Looking for vendor name: "+str(i)

		c = conn.cursor()
		c.execute('select manufacturer from macAddress where macAddress=?',(str(i),))
		dataList1 = []
		dataList1 = c.fetchone()
		if dataList1 != None:
			print "[*] Retrieving match for vendor name: "+str(dataList1[0])
			macAddrDict[i] = str(dataList1[0])
		else:
			vendorName =lookupMacAddress(i)
			if vendorName!=None:
				print "Found vendor name: "+str(i)+" - "+str(vendorName)
				tmpList = []
				tmpList.append([str(i),str(vendorName)])
				write2Database('macAddress',tmpList)
				macAddrDict[i] = vendorName
	for k,v in macAddrDict.items():
		print "[*] "+k, 'corresponds to', v
	counter=0
	for i in content:
		if counter>0:
			locLat = i.split('~')[11]
			locLng = i.split('~')[12]
			global lat, lng
			pt1 = geopy.Point(lat, lng)
			pt2 = geopy.Point(locLat, locLng)
			dist = geopy.distance.distance(pt1, pt2).meters
			global 	wirelessAPData
			if i.split('~')[4]!='infra':
				resultStr = i.split('~')[4]+'\t'+i.split('~')[0]+'\t'+i.split('~')[11]+', '+i.split('~')[12]+'\t\t'+str(dist)+' meters'+'\t'+str(macAddrDict.get(i.split('~')[0][0:8]))	
				wirelessAPData += '\n'+str(resultStr)
				report += '\n'+resultStr
				cprint(resultStr,'white')
			else:
				resultStr = i.split('~')[4]+'\t'+i.split('~')[0]+'\t'+i.split('~')[11]+', '+i.split('~')[12]+'\t\t'+str(dist)+' meters'+'\t'+str(macAddrDict.get(i.split('~')[0][0:8]))
				wirelessAPData += '\n'+str(resultStr)
				report += '\n'+resultStr
				print resultStr
		counter+=1

	"""
	locLat = i.split('~')[11]
	locLng = i.split('~')[12]
	global lat, lng
	pt1 = geopy.Point(lat, lng)
	pt2 = geopy.Point(locLat, locLng)
	dist = geopy.distance.distance(pt1, pt2).meters
	tempMacAddr =lookupMacAddress(macAddr)
	try:
			print i.split('~')[4]+'\t'+i.split('~')[0]+'\t'+i.split('~')[11]+', '+i.split('~')[12]+'\t\t'+str(dist)+' meters'+'\t'+tempMacAddr
	except TypeError as e:
		continue
		counter+=1
	"""
	
def downloadWigle(lat,lng,wigle_cookie):
	print "[*] Downloading Wigle database from Internet"
	variance=0.002
	lat1 = str(float(lat)+variance)
	lat2 = str(float(lat)-variance)
	lgn1 = str(float(lng)-variance)
	lgn2 = str(float(lng)+variance)
	currentYear = date.today().year-1	
	h = httplib2.Http(".cache")
	url = "http://wigle.net/gpsopen/gps/GPSDB/confirmquery/?variance="+str(variance)+"&latrange1="+lat1+"&latrange2="+lat2+"&longrange1="+lgn1+"&longrange2="+lgn2+"&lastupdt="+str(currentYear)+"0101000000&credential_0="+wigle_username+"&credential_1="+wigle_password+"&simple=true"	
	filename = str(lat)+"_"+str(lng)+".dat"
	newFilename = filename.split(".dat")[0]+".kml"
	if os.path.lexists(filename) and not os.path.lexists(newFilename):
		print "[*] File exists: "+filename
		print "[*] File not exists: "+newFilename
		convertWigle2KML(filename)
	if not os.path.lexists(filename):
		cookie = wigle_cookie
		if cookie!=None:
			resp, content = h.request(url, "GET")
			headers = {'Cookie': cookie}
			resp, content = h.request(url, "GET",headers=headers)
			if "too many queries" not in content:
				print "[*] Saving wigle database to: "+str(filename)
				f = open(filename,"w")
				f.write(content)
				f.close()
				print "[*] Converting Wigle database to KML format."
				convertWigle2KML(filename)
			else:
				print "[*] Please try again later"
		else:
			url = "http://wigle.net/gpsopen/gps/GPSDB/confirmquery/?variance="+str(variance)+"&latrange1="+lat1+"&latrange2="+lat2+"&longrange1="+lgn1+"&longrange2="+lgn2+"&lastupdt="+str(currentYear)+"0101000000&credential_0="+wigle_username+"&credential_1="+wigle_password+"&simple=true"
			resp, content = h.request(url, "GET")
			headers = {'Cookie': resp['set-cookie']}
			headers = {'Cookie': cookie}
			resp, content = h.request(url, "GET",headers=headers)
	if os.path.lexists(filename):
		print "[*] Wigle database already exists: "+filename		
	fullPath = os.getcwd()+"/"+newFilename
	fhandle = open(fullPath)
	file_size = os.path.getsize(fhandle.name)
	file_type='application/vnd.google-earth.kml+xml'
	directory,filename = os.path.split(fullPath)
	if not checkGoogleDocsExist(newFilename):
		file_type='application/vnd.google-earth.kml+xml'
	        uploadGoogleDocs(fullPath,file_type)
	resourceID = (changePublicGoogleDocs(newFilename)).strip("file:")
	mapLink = "http://maps.google.com/maps?q=docs://"+resourceID+"&output=embed"
	html = ''
	html += '<iframe width="800" height="600" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" src="'+mapLink+'"></iframe><br /><small><a href="'+mapLink+'" style="color:#0000FF;text-align:left">View Larger Map</a></small>'
	return html
	
def address2geocoordinate(address):
        results = Geocoder.geocode(address)
        return results[0].coordinates[0],results[0].coordinates[1]

def retrieveGoogleResults(username):
	global report
	report += '\n\n[*] Google Search Results for: '+str(username)
	results = []
	keyword = username
	tmpStr = "\n************ Google Search Results for "+username+" ************\n"
	print tmpStr
	try:
		for url in search(keyword, stop=20):
			results.append(url)
		google.cookie_jar.clear()
		for i in results:
			print i
			tmpStr += i+'\n'
			report += '\n'+str(normalize(i))
		print "\n"
		return tmpStr
	except urllib2.HTTPError:
		return ""
def retrieveLinkedinData(username):
	print '\n[*] Searching on Linkedin for: '+username
	global report
	if " " in username:
		firstname, lastname = username.split(" ")
	else:
		firstname = username
		lastname = ""
	consumer = oauth.Consumer(linkedin_api_key, linkedin_api_secret)
	access_token = oauth.Token(
	            key=linkedin_oauth_user_token,
	            secret=linkedin_oauth_user_secret)
	client = oauth.Client(consumer, access_token)

	resp, content = client.request("http://api.linkedin.com/v1/people-search?first-name="+firstname+"&last-name="+lastname,"GET","")
	if resp['status']=="200":
		report += "\n\n[*] Linkedin Search Results"
		report += '\nUsername: '+username
		RETURN_URL = "http://127.0.0.1"	
		authentication = linkedin.LinkedInDeveloperAuthentication(linkedin_api_key, linkedin_api_secret,
	                                                          linkedin_oauth_user_token, linkedin_oauth_user_secret,
	                                                          RETURN_URL, linkedin.PERMISSIONS.enums.values())
		application = linkedin.LinkedInApplication(authentication)
		peopleIDList = []
		userList = []	

		count = 10	
		total = 30
		start = 0
		while count<total:
			results =  application.search_profile(selectors=[{'people': ['first-name', 'last-name', 'id', 'headline', 'picture-url']}], params={'first-name': firstname, 'last-name': lastname,'count': 25, 'start': 0})
			total = int(results['people']['_total'])					
			for x in results['people']['values']:
				print x['headline']
				peopleIDList.append([x['id'],x['headline'],x['firstName'],x['lastName']])
			start+=25
			count+=25		

		for x in peopleIDList:
			resp,content = client.request("http://api.linkedin.com/v1/people/id="+str(x[0]), "GET", "")
			
			xmldoc = minidom.parseString(content)
			firstnameResult = xmldoc.getElementsByTagName('first-name') 
			lastnameResult = xmldoc.getElementsByTagName('last-name') 
			headlineResult = xmldoc.getElementsByTagName('headline') 
			urlResult = xmldoc.getElementsByTagName('url') 
			url = " ".join(t.nodeValue for t in urlResult[0].childNodes if t.nodeType == t.TEXT_NODE)
			r = re.compile('id=(.*?)&authType')
			m = r.search(url)
			if m:
				id = m.group(1)
				mobileUrl = "https://touch.www.linkedin.com/#profile/"+id
				userList.append([[0],x[1],x[2],x[3],mobileUrl])			

		driver = webdriver.Chrome()
		driver.get("https://touch.www.linkedin.com/login.html")
		driver.find_element_by_id('username').send_keys(linkedin_username)
		driver.find_element_by_id('password').send_keys(linkedin_password)
		WebDriverWait(driver, 60).until(lambda driver :driver.find_element_by_id('login-button'))
		driver.find_element_by_id("login-button").click()
		if "session" not in driver.current_url:
			time.sleep(1)
		checkWorking = ""
		for user in userList:	
			mobileUrl = user[4]	
			if user[3].lower()!="private":
				#resp = requests.head(mobileUrl)
				#print resp.status_code
				#if resp.status_code=="200":
				driver.get(mobileUrl)
				#WebDriverWait(driver, 10).until(lambda driver :driver.find_element_by_class_name('profile-photo'))
				WebDriverWait(driver, 60).until(lambda driver :driver.find_element_by_class_name('profile-photo'))
				time.sleep(5)
				
				report += '\nFull name: '+user[2]+' '+user[3]
				report += '\nHeadline: '+user[1]
				report += '\nUrl: '+user[4]
				
				WebDriverWait(driver, 60).until(lambda driver :driver.find_element_by_xpath('//*[@id="profile-view-scroller"]/div/div[2]/div[3]/section[1]'))
				try:
					location = driver.find_element_by_xpath('//*[@id="profile-view-scroller"]/div/div[1]/div[2]/div[1]/div/div[2]/h4/span[1]').text
					industry = driver.find_element_by_xpath('//*[@id="profile-view-scroller"]/div/div[1]/div[2]/div[1]/div/div[2]/h4/span[2]').text
					report += '\nLocation: '+location+'\n'
					report += '\nIndustry: '+industry+'\n\n'
					working = driver.find_element_by_xpath('//*[@id="profile-view-scroller"]/div/div[2]/div[3]/section[1]').text
					if len(checkWorking)!=len(working):
						profilePic = driver.find_element_by_class_name('profile-photo').get_attribute("src")
						print profilePic
						report += '\nProfile Picture: '+profilePic
						checkWorking = working
						tempWorking = working.split("\n")	
						#print len(tempWorking[2:len(tempWorking)])
						tempWorking1 = tempWorking[2:len(tempWorking)]
						count=1
						while count<len(tempWorking1):
							print tempWorking[count]+"\t"+tempWorking[count+1]+"\t"+tempWorking[count+2]
							count+=3	
				except:
					continue
			try:
				education = driver.find_element_by_xpath('//*[@id="profile-view-scroller"]/div/div[2]/div[3]/section[2]').text
				#print education.split("\n")
			except:
				continue
			time.sleep(2)

def retrieveInstagramData(lat,lng):
	global report
	report += '[*] Instagram Search Results'
	print "\n[*] Downloading Instagram Data based on Geolocation"
	count=50
	api = InstagramAPI(access_token=instagram_access_token)
	mediaList = api.media_search(count=count, lat=lat, lng=lng)
	instagramMediaList = []
	for media in mediaList:
		username = str(normalize(media.user.username)).replace("'","\\'")
		global globalUserList
		username = str(normalize(username))
		if username not in globalUserList:
			globalUserList.append(username)
		username = 'http://instagram.com/'+username
		print '[*] Found '+str(username)+'\t('+str(media.location.point.latitude)+','+str(media.location.point.longitude)+")"
		report+="\nFound: "+str(media.images['thumbnail'].url)
		report+="\nUsername: "+str(username)
		report+="\nGeolocation "+str(media.location.point.latitude)+','+str(media.location.point.longitude)+'\n'
		instagramMediaList.append([str(username),str(media.location.point.latitude),str(media.location.point.longitude),media.images['thumbnail'].url,lat,lng])
	return instagramMediaList
	

def retrieveFlickrData(lat,lng):
	print "\n[*] Downloading Flickr Data Based on Geolocation"
	global report
	report += '\n[*] Flickr Search Results'
	resultsList = []
	import flickrapi
	h = httplib2.Http(".cache")
	flickr = flickrapi.FlickrAPI(flickr_key)
	retries=0
	while (retries < 3):
		try:
			photos = flickr.photos_search(lat=lat,lon=lng,accuracy='16',radius='1',has_geo='1',per_page='50')
			break
		except:
			cprint('[!] Flickr Error: Retrying.','white')
		retries = retries + 1

	print "[*] Continue Downloading Flickr Data"
	for i in photos[0]:
		url = 'http://www.flickr.com/photos/'+i.get('owner')+'/'+i.get('id')
		resp, content = h.request(url, "GET")
		soup = BeautifulSoup(str(content))
		
		geoLocUrl = 'http://www.flickr.com/photos/'+i.get('owner')+'/'+i.get('id')+'/meta'
		resp, content = h.request(geoLocUrl, "GET")
		root = lxml.html.fromstring(content)
			
		doc = lxml.html.document_fromstring(content)
		photoLat = doc.xpath('//*[@id="main"]/div[2]/table[2]/tbody/tr[26]/td/text()')
		photoLng= doc.xpath('//*[@id="main"]/div[2]/table[2]/tbody/tr[27]/td/text()')

		if photoLat and 'deg' in str(photoLat[0]) and 'deg' in str(photoLng[0]):
			newPhotoLat = photoLat[0].replace('deg','').replace("'","").replace('"','').split(' ')
			newPhotoLng = photoLng[0].replace('deg','').replace("'","").replace('"','').split(' ')
			photoLatStr = str(float(newPhotoLat[0])+float(newPhotoLat[2])/60+float(newPhotoLat[3])/3600)
			photoLngStr = str(float(newPhotoLng[0])+float(newPhotoLng[2])/60+float(newPhotoLng[3])/3600)

			#photoLatStr = str(float(newPhotoLat[0])+float(newPhotoLat[2])/60+float(newPhotoLat[3])/3600)
			#photoLngStr = str(float(newPhotoLng[0])+float(newPhotoLng[2])/60+float(newPhotoLng[3])/3600)

			pt1 = geopy.Point(lat, lng)
			pt2 = geopy.Point(photoLatStr, photoLngStr)
			dist = geopy.distance.distance(pt1, pt2).meters

			outputStr = '[*] Found Matching Geocoordinates in Flickr Data: ('+str(photoLatStr)+','+str(photoLngStr)+')\t'+str(dist)+' meters'
			report += '\n'+outputStr
			#print geoLocUrl
		
			userName = soup.find('span',attrs={'class':'photo-name-line-1'})
			#print userName.text
			
			cameraModel = root.cssselect("html body.zeus div#main.clearfix div.photo-data table tbody tr.lookatme td a")
			if cameraModel:
				cameraModelText = cameraModel[0].text
			else:
				cameraModelText = ''
			
			#url #title #username #cameraModel #latitude #longitude
			url1 = 'http://www.flickr.com/photos/'+str(i.get('owner'))+'/'+str(i.get('id'))
			description = i.get('title')
			resultsList.append([normalize(url1),normalize(description),str(normalize(userName.text)),cameraModelText,normalize(photoLatStr),normalize(photoLngStr),lat,lng])
			print outputStr
	return resultsList
	
def googlePlusSearch(username):
	global report       		
	print "\n[*] Searching Google+ for Possible Matches: "+username
	googlePlusUserList = []
	username = urllib.quote_plus(username)
	url = 'https://plus.google.com/s/'+username+'/people'	
	r = requests.get(url)
	html = r.content
	root = lxml.html.fromstring(html)
	count = 0
	e1 = root.cssselect("html body.je div.NPa div#content.maybe-hide div.z2a div.Kxa div#contentPane.jl div.o-B-Qa div.LE div.wfe div.iSd div.Yyd div.tec div.Nxc div.vtb div.bae div.Xce div.uec div.ge div.Sxa a.T7a")
	e2 = root.cssselect("html body.je div.NPa div#content.maybe-hide div.z2a div.Kxa div#contentPane.jl div.o-B-Qa div.LE div.wfe div.iSd div.Yyd div.tec div.Nxc div.vtb div.bae div.Xce div.uec div.ge div.lkb a.lb img.ue")
	for x in e1:
		userName = x.text
		userID = x.get('href').strip('/')
		imageSrc = e2[count].get('src')
		if imageSrc.startswith('//'):
			imageSrc = 'https:'+imageSrc
		tmpStr = userName+'\thttps://plus.google.com/'+userID+'\t'+imageSrc
		print tmpStr
		report += "\n\n[*] Google+ Search Results"
		report += '\nUsername: '+userName
		report += '\nUrl: '+userID
		report += '\nProfile Picture: '+imageSrc
		googlePlusUserList.append([userName,userID,imageSrc])
		print "\nFound "+str(normalize(userName))
		count+=1
	return googlePlusUserList
	


def retrieve4sqOnTwitterResults():
	global report
	report += '\n\n[*] Retrieving Tweets for Foursquare Check In'
	print '\n\n[*] Retrieving Tweets for Foursquare Check In (Experiemental)'
	try:
		tmpList = []
		for element in foursqTwitterSearch:	
			geoLat = element[1]
			geoLng = element[2]	
			stripLoc = (element[0].replace('4sq.com/','')).strip()
			tso = TwitterSearchOrder() 	
			tso.setKeywords([stripLoc]) 
			tso.setCount(7) 
			tso.setIncludeEntities(False)
			ts = TwitterSearch(
				consumer_key = twitter_consumer_key,
				consumer_secret = twitter_consumer_secret,
				access_token = twitter_access_key ,
				access_token_secret = twitter_access_secret
			 )
			for tweet in ts.searchTweetsIterable(tso): 
				print tweet
				screenName = (normalize(tweet['user']['screen_name']))
				tweetMsg = normalize(tweet['text'])
				tmpStr = '@%s: %s' % (screenName, tweetMsg )
				global lat, lng
				geoLat = lat
				geoLng = lng

				report += '\n'+tmpStr.decode("utf8")
				tmpStr = '@%s: %s (%s,%s)' % (screenName, tweetMsg,geoLat,geoLng )
				print str(normalize(tmpStr.encode('ascii','ignore')))

				tweetText = ''
				try:	
					tweetText = tweet['text'].replace("'","\\'")
					tweetText = str(normalize(tweetText.encode('ascii','ignore')))
					#print tweetText
				except: 
					continue
				tmpList.append(['https://www.twitter.com/'+str(normalize(tweet['user']['screen_name'])),geoLat, geoLng,'',tweetText])
				global globalUserList
				if str(normalize(tweet['user']['screen_name'])) not in globalUserList:
					globalUserList.append(str(normalize(tweet['user']['screen_name'])))				
				tempList1 = []
				tempList1.append(['https://www.twitter.com/'+str(normalize(tweet['user']['screen_name'])),(tweet['text']).encode('ascii','ignore'),geoLat, geoLng ,lat,lng])	
				write2Database('twitter',tempList1)
		return tmpList
	except TwitterSearchException as e: 
		print(e)

def retrieveTwitterResults(lat,lng):
	lat = float(lat)
	lng = float(lng)
	global report
	try:
		start_time = time.time()
		report += '\n\n[*] Twitter Geolocation Search Results'
		print "\n[*] Retrieving Tweets Based on Geolocation"
		tso = TwitterSearchOrder() 
		tso.setGeocode(lat,lng,1)
		tso.setKeywords(['']) 
		tso.setCount(7) 
		tso.setIncludeEntities(False)
		ts = TwitterSearch(
			consumer_key = twitter_consumer_key,
			consumer_secret = twitter_consumer_secret,
			access_token = twitter_access_key ,
			access_token_secret = twitter_access_secret
		 )
		for tweet in ts.searchTweetsIterable(tso): 
			if time.time()>start_time+15.0:
			#if time.time()>start_time+30.0:
				break
			else:
				screenName = (normalize(tweet['user']['screen_name']))
				tweetMsg = normalize(tweet['text'])
				geoLat = ""
				geoLng = ""
				try:
					geoLat, geoLng = str(tweet['geo']['coordinates']).replace('[','').replace(']','').strip().split(',')
					geoLng = geoLng.strip()
				except TypeError:
						continue
				tmpStr = '@%s: %s (%s,%s)' % (screenName, tweetMsg,geoLat,geoLng )
				try:
					print str(normalize(tmpStr.encode('ascii','ignore')))
					report += '\n'+str(normalize(tmpStr.encode('ascii','ignore')))		

					tweetText = ''
					try:
						tweetText = tweet['text'].replace("'","\\'")
						tweetText = str(normalize(tweetText.encode('ascii','ignore')))
						print tweetText
					except: 
						continue
					global tweetList				
					#tweetList.append(['https://www.twitter.com/'+str(normalize(tweet['user']['screen_name'])),geoLat, geoLng,'',''])
					#tweetList.append(['https://www.twitter.com/'+str(normalize(tweet['user']['screen_name'])),geoLat, geoLng,'',tweetText])
					tweetList.append(['https://www.twitter.com/'+str(normalize(tweet['user']['screen_name'])),geoLat, geoLng,'',tweetText])

					global globalUserList
					if str(normalize(tweet['user']['screen_name'])) not in globalUserList:
						globalUserList.append(str(normalize(tweet['user']['screen_name'])))
	
					tempList1 = []
					#tempList1.append(['https://www.twitter.com/'+str(normalize(tweet['user']['screen_name'])),repr(zlib.compress(normalize(tweet['text']))),geoLat, geoLng ,lat,lng])	
					tempList1.append(['https://www.twitter.com/'+str(normalize(tweet['user']['screen_name'])),(tweet['text']).encode('ascii','ignore'),geoLat, geoLng ,lat,lng])	
					write2Database('twitter',tempList1)
				except UnicodeDecodeError:
					continue
	except TwitterSearchException as e: 
		print(e)
	except requests.exceptions.ConnectionError:
		cprint('[!] Connection issue. Continuing with next step.','white')
		pass
	print "[*] Writing twitter feed to database: twitter"
	
def retrieve4sqData(lat,lng):
	print "\n[*] Fetching Data from Foursquare"
	global report
	report += "\n[*] Foursquare Search Results"
	count = 20
	client = foursquare.Foursquare(client_id=foursquare_client_id, client_secret=foursquare_client_secret, redirect_uri='http://127.0.0.1/oauth/authorize')
	client.set_access_token(foursquare_access_token)
	list = []
	failedLinks = []
	geolocation = str(lat)+","+str(lng)
	failedLinks.append("https://foursquare.com/img/categories_v2/building/militarybase.png")
	failedLinks.append("https://foursquare.com/img/categories_v2/building/government.png")
	failedLinks.append("https://foursquare.com/img/categories_v2/building/government_monument.png")
	failedLinks.append("https://foursquare.com/img/categories_v2/building/apartment.png")
	failedLinks.append("https://foursquare.com/img/categories_v2/education/classroom.png")
	failedLinks.append("https://foursquare.com/img/categories_v2/building/eventspace.png")
	failedLinks.append("https://foursquare.com/img/categories_v2/building/office_conferenceroom.png")
	failedLinks.append("https://foursquare.com/img/categories_v2/shops/conveniencestore.png")	
	failedLinks.append("https://foursquare.com/img/categories_v2/shops/gym_martialarts.png")
	failedLinks.append("https://foursquare.com/img/categories_v2/parks_outdoors/sceniclookout.png")
	list = []
	data = client.venues.search(params={'ll': geolocation,'limit':count })
	for venue in data['venues']:
		location = client.venues(venue['id'])
		
		html = ''
		try:
			html += location['venue']['location']['address']+'<br>'
		except KeyError:
			continue
		html += '<a href=javascript:window.open("'+location['venue']['canonicalUrl']+'")>'+location['venue']['canonicalUrl']+'</a><br>'
		if len(venue['categories'])>0:
       		 	venueName = venue['name']
        	       	if len(venue['categories'][0]['pluralName'])>0:
       		         	categoryName = venue['categories'][0]['pluralName']
              		else:
                	  	categoryName = ""
                	icon = str(venue['categories'][0]['icon']['prefix'])[:-1]+venue['categories'][0]['icon']['suffix']
              		if icon not in failedLinks:
               			try:
                	        	f = urllib2.urlopen(urllib2.Request(icon))
                	      	except urllib2.HTTPError:
                	            #print icon
								failedLinks.append(icon)
								icon = 'http://foursquare.com/img/categories/none.png'
              		else:
                	  	icon = 'http://foursquare.com/img/categories/none.png'
		else:
					venueName = venue['name']
					icon = 'http://foursquare.com/img/categories/none.png'
		locLat = str(venue['location']['lat'])
		locLng = str(venue['location']['lng'])
       		
		pt1 = geopy.Point(lat, lng)
		pt2 = geopy.Point(locLat, locLng)
		dist = geopy.distance.distance(pt1, pt2).meters
		
		#Get short url for 4sq sites. Use this to search for 4sq checkins in Twitter
		r = requests.get('https://foursquare.com/v/venues/'+str(venue['id']))
		html = r.content
		soup2 = BeautifulSoup(html)
		shortUrl = soup2.find("input", {"class" : "shareLink formStyle"})
		global foursqTwitterSearch
		foursqTwitterSearch.append([shortUrl['value'].strip("http://"),locLat,locLng])
				
			       		
		report += "\nFound "+venueName+"\t"+"("+locLat+","+locLng+")"+"\t"+str(dist)+" meters"
		print "[*] Found "+venueName+"\t"+"("+locLat+","+locLng+")"+"\t"+str(dist)+" meters"
		point = "[\""+venueName+"\","+locLat+","+locLng+",'"+icon+"']"
		#print point
		venueName = venueName.replace("'","\\'")
		venueName = venueName.replace('"','\\"')
		html = html.replace("'","\\'")
		html = html.replace('"','\\"')
		list.append([venueName,locLat,locLng,icon,html])
	print ""
	report += "\n"
	return list			

def write2Database(dbName,dataList):
	try:
		#cprint("[*] Writing "+str(len(dataList))+" record(s) to database table: "+dbName,"white")
		numOfColumns = len(dataList[0])
		c = conn.cursor()
		if numOfColumns==3:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
		if numOfColumns==2:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
		if numOfColumns==4:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
		if numOfColumns==5:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
		if numOfColumns==6:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?,?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
		if numOfColumns==7:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?,?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
		if numOfColumns==8:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?,?,?,?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
					
		if numOfColumns==9:
			for i in dataList:
				try:
					c.execute('INSERT INTO '+dbName+' VALUES (?,?,?,?,?,?,?,?,?)', i)
					conn.commit()
				except sqlite3.IntegrityError:
					continue
	except TypeError as e:
		print e
		pass
	except IndexError as e:
		print e
		pass

def usernameSearch(username):
	global report
	urlList = []
	urlList.append("https://www.facebook.com/"+username)
	urlList.append("https://www.youtube.com/user/"+username+"/feed")
	urlList.append("http://instagram.com/"+username)
	
	for url in urlList:
		print "\n[*] Searching for valid accounts: "+url
		resp = requests.head(url)
		#print resp.status_code, resp.text, resp.headers
		if resp.status_code==200:
			print "[*] Found: "+url
			report+= "\nFound :"+url
	print "\n[*] Searching for valid accounts on Google+"
	googlePlusSearch(username)
	if len(linkedin_oauth_user_token)>0:	
		print "\n[*] Searching for valid accounts on Linkedin"
		retrieveLinkedinData(username)
	
	print "\n[*] Searching for valid accounts on Google Search"
	retrieveGoogleResults(username)
	
def createMaltegoGeolocation():
	print "\n[*] Create Maltego Mtgx File..."		
	g = Graph()
	totalCount = 50
	start = 0
	nodeList = []
	edgeList = []

	while(start<totalCount):
       		nodeList.append("")	
	        edgeList.append("")
	        start+=1

	nodeList[0] = g.add_node('original')
	nodeList[0]['node'] = createNodeLocation(lat,lng)


	counter1=1
	counter2=0                
	userList=[]

	c = conn.cursor()
	c.execute('select distinct userName from instagram where origLat=? and origLng=?',(lat,lng,))
	dataList = c.fetchall()
	nodeUid = ""
	for i in dataList:
		if i[0] not in userList:
			userList.append(i[0])
			try:
			   	nodeList[counter1] = g.add_node("Instagram_"+str(i[0]))
   				nodeList[counter1]['node'] = createNodeUrl(i[0],str(i[0]))
   				edgeList[counter2] = g.add_edge(nodeList[0], nodeList[counter1])
   				edgeList[counter2]['link'] = createLink('Instagram')
    				nodeList.append("")
 		   		edgeList.append("")
    				counter1+=1
    				counter2+=1
			except IndexError:
				continue
				
	c = conn.cursor()
	c.execute('select distinct URL from flickr where origLat=? and origLng=?',(lat,lng,))
	dataList = c.fetchall()
	nodeUid = ""
	for i in dataList:
		if i[0] not in userList:
			userList.append(i[0])
			try:
			   	nodeList[counter1] = g.add_node("Flickr_"+str(i[0]))
   				nodeList[counter1]['node'] = createNodeUrl(i[0],str(i[0]))
   				edgeList[counter2] = g.add_edge(nodeList[0], nodeList[counter1])
   				edgeList[counter2]['link'] = createLink('Flickr')
    				nodeList.append("")
 		   		edgeList.append("")
    				counter1+=1
    				counter2+=1
			except IndexError:
				continue
				
	c = conn.cursor()
	c.execute('select distinct username from twitter where origLat=? and origLng=?',(lat,lng,))
	dataList = c.fetchall()
	nodeUid = ""
	for i in dataList:
		if i[0] not in userList:
			userList.append(i[0])
			try:
			   	nodeList[counter1] = g.add_node("Twitter1_"+str(i[0]))
   				nodeList[counter1]['node'] = createNodeUrl(i[0],str(i[0]))
   				edgeList[counter2] = g.add_edge(nodeList[0], nodeList[counter1])
   				edgeList[counter2]['link'] = createLink('Twitter_')
    				nodeList.append("")
 		   		edgeList.append("")
    				counter1+=1
    				counter2+=1
			except IndexError:
				continue
	parser = GraphMLParser()
	if not os.path.exists(os.getcwd()+'/Graphs'):
    		os.makedirs(os.getcwd()+'/Graphs')
	filename = 'Graphs/Graph1.graphml'
	parser.write(g, "Graphs/Graph1.graphml")
	cleanUpGraph(filename)
	filename = 'maltego_'+lat+'_'+lng+'.mtgx'
	print 'Creating archive: '+filename
	zf = zipfile.ZipFile(filename, mode='w')
	print 'Adding Graph1.graphml'
	zf.write('Graphs/Graph1.graphml')
	print 'Closing'
	zf.close()

def createMaltegoUsername():
	print "\n[*] Create Maltego Mtgx File..."		
	g = Graph()
	totalCount = 50
	start = 0
	nodeList = []
	edgeList = []

	while(start<totalCount):
       		nodeList.append("")	
	        edgeList.append("")
	        start+=1

	nodeList[0] = g.add_node('original')
	nodeList[0]['node'] = createNodeLocation(lat,lng)

	counter1=1
	counter2=0                
	userList=[]

	nodeUid = ""
	for i in globalUserList:
		i = i.encode('ascii','replace')
		print i
		try:
		   	nodeList[counter1] = g.add_node("Twitter1_"+str(i))
   			nodeList[counter1]['node'] = createNodeUrl(i,str(i))
   			edgeList[counter2] = g.add_edge(nodeList[0], nodeList[counter1])
   			edgeList[counter2]['link'] = createLink('Twitter_')
    			nodeList.append("")
 	   		edgeList.append("")
    			counter1+=1
    			counter2+=1
		except IndexError:
			continue
	parser = GraphMLParser()
	if not os.path.exists(os.getcwd()+'/Graphs'):
    		os.makedirs(os.getcwd()+'/Graphs')
	filename = 'Graphs/Graph1.graphml'
	parser.write(g, "Graphs/Graph1.graphml")
	cleanUpGraph(filename)
	filename = 'maltego1.mtgx'
	print 'Creating archive: '+filename
	zf = zipfile.ZipFile(filename, mode='w')
	print 'Adding Graph1.graphml'
	zf.write('Graphs/Graph1.graphml')
	print 'Closing'
	zf.close()

def usernameSearch(g):
	global report
	counter1=1
	counter2=0                
	userList=[]	
	counter3=0
	secondaryCount = 0

	global globalUserList			
	for username in globalUserList:
		username = str(normalize(username.encode('ascii','replace')))
		username = str(username)
		username = username.replace("(u'","")
		username = username.replace("',)","")

	       	googlePlusSearch(username)
	        if len(linkedin_oauth_user_token)>0:
	               	print "\n[*] Searching for valid accounts on Linkedin"
                	retrieveLinkedinData(username)

	        print "\n[*] Searching for valid accounts on Google Search"
		randNum = randint(10,20)
		print "Sleeping for "+str(randNum)+" seconds to prevent Google bot detection"
		time.sleep(randNum)

        	retrieveGoogleResults(username)


		nodeUid = ""

		url = str(username)
		nodeList[counter1] = g.add_node("Twitter2_"+str(url))
   		nodeList[counter1]['node'] = createNodeUrl(url,str(url))
   		edgeList[counter2] = g.add_edge(nodeList[0], nodeList[counter1])
   		edgeList[counter2]['link'] = createLink('Twitter')	

    		nodeList.append("")
 	   	edgeList.append("")	

		lastCounter = counter1
	    	counter1+=1
    		counter2+=1

		urlList = []
		urlList.append("https://www.facebook.com/"+username)
		urlList.append("https://www.youtube.com/user/"+username+"/feed")
		urlList.append("http://instagram.com/"+username)
		urlList.append("https://twitter.com/"+username)
		

		for url in urlList:
			#print "\n[*] Searching1 for valid accounts: "+url
			try:
				resp = requests.head(url)
				if resp.status_code==200:
					print "[*] Found: "+url
					report+= "\nFound :"+url
				   	nodeList[counter1] = g.add_node("Secondary_"+str(secondaryCount))
   					nodeList[counter1]['node'] = createNodeUrl(url,str(url))
   					edgeList[counter2] = g.add_edge(nodeList[lastCounter], nodeList[counter1])
   					edgeList[counter2]['link'] = createLink('Link_')
		    			nodeList.append("")
		 	   		edgeList.append("")  
 					counter1+=1
    					counter2+=1
					secondaryCount+=1
			except IndexError:
				continue
			except requests.exceptions.ConnectionError:
				continue
	parser = GraphMLParser()
	if not os.path.exists(os.getcwd()+'/Graphs'):
    		os.makedirs(os.getcwd()+'/Graphs')
	filename = 'Graphs/Graph1.graphml'
	parser.write(g, "Graphs/Graph1.graphml")

	cleanUpGraph(filename)
	filename = 'maltego3.mtgx'
	print 'Creating archive: '+filename
	zf = zipfile.ZipFile(filename, mode='w')
	print 'Adding Graph1.graphml'
	zf.write('Graphs/Graph1.graphml')
	print 'Closing'
	zf.close()
	
def geoLocationSearch(lat,lng):
	htmlfile = open("result.html", "w")
	html = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
	html += '<html xmlns="http://www.w3.org/1999/xhtml">'
	html += '<head>'
	html += '<title>Geostalker Tool Google Maps</title>'
	html += "<script src='http://code.jquery.com/jquery.min.js' type='text/javascript'></script>"
	html += '</head>'
	html += '<body>'
	html += '<script type="text/javascript" src="http://maps.google.com/maps/api/js?sensor=false"></script>'
	htmlfile.write(html)
	htmlfile.write('<br><b>Wireless Access Point Database Lookup from Wigle.net</b><br>')
	
	if len(wigle_username)>0:
		wigle_cookie = loginWigle(wigle_username, wigle_password)
		html1 = downloadWigle(lat,lng,wigle_cookie)    	
		htmlfile.write(html1)

		filename = str(lat)+'_'+str(lng)+'.dat'
		parseWigleDat(filename)
	gpsPoints = []
		
	#Foursquare Start
	if len(foursquare_access_token)>0:
		dataList = retrieve4sqData(lat,lng)
		gpsPoints.extend(dataList)

	#Instagram Start
	if len(instagram_access_token)>0:
		dataList = retrieveInstagramData(lat,lng)
		if dataList:
			gpsPoints.extend(dataList)
			write2Database('instagram',dataList)
	#Flickr Start
	if len(flickr_oauth_secret)>0:
		dataList1 = retrieveFlickrData(lat,lng)
		if len(dataList1)>0:
			write2Database('flickr',dataList1)
			html = ''
			for i in dataList1:
				html = '<a href="'+i[0]+'">'+i[0]+'</a><br>'+i[1]+'<br>'+i[3]+'<br>'+'<br>'
				html = html.encode('ascii','replace')
				gpsPoints.append([('http://www.flickr.com/photos/'+i[2]).encode('ascii','replace'),i[4].encode('ascii','encode'),i[5].encode('ascii','encode'),'',html])		
	#Twitter Start
	if len(twitter_access_secret)>0:
		retrieveTwitterResults(lat,lng)
		gpsPoints.extend(tweetList)
		time.sleep(5)
		tmpList = retrieve4sqOnTwitterResults()
		if tmpList:
			gpsPoints.extend(tmpList)
		
	html = createGoogleMap(gpsPoints,lat,lng)		
	#Twitter End

	print "\n[*] Create Google Map using Flickr/Instagram/Twitter Geolocation Data"		
	htmlfile.write('<br><br>')
	htmlfile.write('<br><b>Google Map based on Flickr/Instagram/Twitter Geolocation Data</b><br>')
	htmlfile.write(html.encode('utf8','replace'))
	htmlfile.write('</body></html>')
	htmlfile.close()

	#new
	print "\n[*] Checking additional social networks for active accounts... "
	g = Graph()
	totalCount = 50
	start = 0
	global nodeList
	global edgeList

	while(start<totalCount):
      		nodeList.append("")	
	        edgeList.append("")
	        start+=1	

	nodeList[0] = g.add_node('original')
	nodeList[0]['node'] = createNodeLocation(lat,lng)	

	global report
	usernameSearch(g)


def showhelp():
	print ""
	print "	MMMMMM$ZMMMMMDIMMMMMMMMNIMMMMMMIDMMMMMMM"
	print "	MMMMMMNINMMMMDINMMMMMMMZIMMMMMZIMMMMMMMM"
	print "	MMMMMMMIIMMMMMI$MMMMMMMIIMMMM8I$MMMMMMMM"
	print "	MMMMMMMMIINMMMIIMMMMMMNIIMMMOIIMMMMMMMMM"
	print "	MMMMMMMMOIIIMM$I$MMMMNII8MNIIINMMMMMMMMM"
	print "	MMMMMMMMMZIIIZMIIIMMMIIIM7IIIDMMMMMMMMMM"
	print "	MMMMMMMMMMDIIIIIIIZMIIIIIII$MMMMMMMMMMMM"
	print "	MMMMMMMMMMMM8IIIIIIZIIIIIIMMMMMMMMMMMMMM"
	print "	MMMMMMMMMMMNIIIIIIIIIIIIIIIMMMMMMMMMMMMM"
	print "	MMMMMMMMM$IIIIIIIIIIIIIIIIIII8MMMMMMMMMM"
	print "	MMMMMMMMIIIIIZIIIIZMIIIIIDIIIIIMMMMMMMMM"
	print "	MMMMMMOIIIDMDIIIIZMMMIIIIIMMOIIINMMMMMMM"
	print "	MMMMMNIIIMMMIIII8MMMMM$IIIZMMDIIIMMMMMMM"
	print "	MMMMIIIZMMM8IIIZMMMMMMMIIIIMMMM7IIZMMMMM"
	print "	MMM$IIMMMMOIIIIMMMMMMMMMIIIIMMMM8IIDMMMM"
	print "	MMDIZMMMMMIIIIMMMMMMMMMMNIII7MMMMNIIMMMM"
	print "	MMIOMMMMMNIII8MMMMMMMMMMM7IIIMMMMMM77MMM"
	print "	MO$MMMMMM7IIIMMMMMMMMMMMMMIII8MMMMMMIMMM"
	print "	MIMMMMMMMIIIDMMMMMMMMMMMMM$II7MMMMMMM7MM"
	print "	MMMMMMMMMIIIMMMMMMMMMMMMMMMIIIMMMMMMMDMM"
	print "	MMMMMMMMMII$MMMMMMMMMMMMMMMIIIMMMMMMMMMM"
	print "	MMMMMMMMNIINMMMMMMMMMMMMMMMOIIMMMMMMMMMM"
	print "	MMMMMMMMNIOMMMMMMMMMMMMMMMMM7IMMMMMMMMMM"
	print "	MMMMMMMMNINMMMMMMMMMMMMMMMMMZIMMMMMMMMMM"
	print "	MMMMMMMMMIMMMMMMMMMMMMMMMMMM8IMMMMMMMMMM"

	print """
	#####################################################
	#                  geoStalker.py                 #
	#               [Trustwave Spiderlabs]              #
	#####################################################
	Usage: python geoStalker.py [OPTIONS]

	[OPTIONS]

	-location   [Physical Address or Geocoordinates]
	-user [Username] - Not enabled yet
	"""

def mainProcess(input):
	#input = "252 North Bridge Road singapore"
	#input = raw_input("Please enter an address or GPS coordinates (e.g. 1.358143,103.944826): ")
	while len(input.strip())<1:
		input = raw_input("Please enter an address or GPS coordinates (e.g. 1.358143,103.944826): ")
	try:	
		if any(c.isalpha() for c in input):
			print "[*] Converting address to GPS coordinates: "+str(lat)+" "+str(lng)
			lat,lng = address2geocoordinate(input)
			lat = lat.strip()
			lng = lng.strip()
		else:
			lat,lng = input.split(',')
			lat = lat.strip()
			lng = lng.strip()
	except:
		pass
		#print "[!] Geocoding error"

	c = conn.cursor()
	c.execute('select distinct username from instagram where origLat=? and origLng=?',(lat,lng,))
	dataList1 = []
	dataList1 = c.fetchall()
	for i in dataList1:
		x = str(normalize(i))
		x = str(x.replace('http://instagram.com/',''))
		if x not in globalUserList:
			globalUserList.append(x)

	c = conn.cursor()
	c.execute('select distinct username from flickr where origLat=? and origLng=?',(lat,lng,))
	dataList1 = []
	dataList1 = c.fetchall()
	for i in dataList1:
		x = str(i)
		x = str(x.replace('http://www.flickr.com/photos/',''))
		if x not in globalUserList:
			globalUserList.append(x)

	c = conn.cursor()
	c.execute('select distinct username from twitter where origLat=? and origLng=?',(lat,lng,))
	dataList1 = []
	dataList1 = c.fetchall()
	for i in dataList1:
		x = str(normalize(i))
		x = str(x.replace('https://www.twitter.com/',''))
		if x not in globalUserList:
			globalUserList.append(x)


	#for x in globalUserList:
	#	print x
	geoLocationSearch(lat,lng)
		
	print "\n[*] Analysis report has been written to 'report.txt'"
	reportFile = open('report.txt', "w")
	reportFile.write('\n[*] Geolocation')
	reportFile.write('\n('+str(lat)+','+str(lng)+')')
	reportFile.write('\n\n[*] Found User IDs in Area')
	for x in globalUserList:
		reportFile.write('\n'+str(normalize(x)).encode('utf8','ignore'))

	reportFile.write(report.encode('utf8','ignore'))
	reportFile.close()
	print "[*] Please refer to 'result.html' for generated Google Maps."		
	filename = 'maltego_'+str(lat)+'_'+str(lng)+'.mtgx'
	altfilename = 'maltego_'+str(lat)+'_'+str(lng)+'_all_searches.mtgx'
	print "[*] Please refer to '"+filename+"' for generated Maltego File containing nearby results from social media sites."
	print "[*] Please refer to '"+altfilename+"' for generated Maltego File containing above plus mapping to other social media accounts (huge map)."
	#createMaltegoGeolocation()
	#createMaltegoUsername()


def options(arguments):
	user = ""
	count = 0
 	for arg in arguments:
  		if arg == "-location":
			count+=1
   			location = arguments[count+1]
  	mainProcess(location)

if __name__ == '__main__':
	if len(sys.argv) <= 1:
		showhelp()
		sys.exit()
 	else:
  		options(sys.argv)
  		sys.exit()

########NEW FILE########
