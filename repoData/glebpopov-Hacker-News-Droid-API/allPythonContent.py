__FILENAME__ = APIContent
import APIUtils
import DataCache
import logging
import AppConfig


#get cached content
def getCache(pageId, format):
    logging.debug('getCache: %s' % pageId)
    try:
        dbData = DataCache.getData(pageId, format)
        if (dbData):
            if (DataCache.hasExpired(dbData)):
                #data has expired, remove it
                try:
                    dbData[0].delete()
                    return None
                except:
                    logging.error('getCache: unable to remove cache')
                    return None
            else:
                logging.debug('getCache: got cached data for id %s' % id)
                return dbData[0].rec_xml
    except:
        logging.error('getCache: unable to get/retrieve cache')
        return None

#get post by id
def getHackerNewsPost(articleId, format='json', url='', referer='', remote_addr=''):
    #only cache homepage data
    apiURL = "%s/item?id=%s" % (AppConfig.hackerNewsURL, articleId)
    apiURLBackup = "%s/item?id=%s" % (AppConfig.hackerNewsURLBackup, articleId)
    id = '/post/%s' % (articleId)
    cachedData = getCache(id,format)
    if (cachedData):
        return cachedData
    else:
        hnData = APIUtils.parsePostContent(apiURL, apiURLBackup, '/post', None,format)
        if (hnData):
            logging.debug('getHackerNewsPost: storing cached value for id %s' % id)
            DataCache.putData(id, format,APIUtils.removeNonAscii(hnData), url, referer, remote_addr)
            return hnData
        else:
            logging.warning('getHackerNewsPost: unable to retrieve data for id %s' % id)
            return ''

#parse HN's submissions by user
def getHackerNewsSubmittedContent(user, format='json', url='', referer='', remote_addr=''):
    #only cache homepage data
    apiURL = "%s/submitted?id=%s" % (AppConfig.hackerNewsURL, user)
    apiURLBackup = "%s/submitted?id=%s" % (AppConfig.hackerNewsURLBackup, user)
    id = '/submitted/%s' % (user)
    cachedData = None
    cachedData = getCache(id, format)
    if (cachedData):
        return cachedData
    else:
        hnData = APIUtils.parsePageContent(apiURL, apiURLBackup, '/submitted', None, format)
        if (hnData):
            logging.debug('getHackerNewsSubmittedContent: storing cached value for id %s' % id)
            DataCache.putData(id, format, APIUtils.removeNonAscii(hnData), url, referer, remote_addr)
            return hnData
        else:
            logging.warning('getHackerNewsSubmittedContent: unable to retrieve data for id %s' % id)
            return ''


#parse HN's comments by story id
def getHackerNewsComments(articleId, format='json', url='', referer='', remote_addr=''):
    #only cache homepage data
    apiURL = "%s/item?id=%s" % (AppConfig.hackerNewsURL, articleId)
    apiURLBackup = "%s/item?id=%s" % (AppConfig.hackerNewsURLBackup, articleId)
    id = '/comments/%s' % (articleId)
    cachedData = getCache(id, format)
    if (cachedData):
        return cachedData
    else:
        hnData = APIUtils.parseCommentsContent(apiURL, apiURLBackup, '/comments', None, format)
        if (hnData):
            logging.debug('getHackerNewsComments: storing cached value for id %s' % id)
            DataCache.putData(id, format, APIUtils.removeNonAscii(hnData), url, referer, remote_addr)
            return hnData
        else:
            logging.warning('getHackerNewsComments: unable to retrieve data for id %s' % id)
            return ''


#parse HN's comments by story id
def getHackerNewsNestedComments(articleId, format='json', url='', referer='', remote_addr=''):
    #only cache homepage data
    apiURL = "%s/item?id=%s" % (AppConfig.hackerNewsURL, articleId)
    apiURLBackup = "%s/item?id=%s" % (AppConfig.hackerNewsURLBackup, articleId)
    id = '/nestedcomments/%s' % (articleId)
    #cache data
    cachedData = getCache(id, format)
    if (cachedData):
        return cachedData
    else:
        try:
            hnData = APIUtils.parseNestedCommentsContent(apiURL, apiURLBackup, '/nestedcomments', None, format)
            if (hnData):
                logging.debug('getHackerNewsComments: storing cached value for id %s' % id)
                DataCache.putData(id, format, APIUtils.removeNonAscii(hnData), url, referer, remote_addr)
                return hnData
            else:
                logging.warning('getHackerNewsComments: unable to retrieve data for id %s' % id)
                return ''
        except:
            logging.warning('getHackerNewsComments: error(s) getting comments %s' % id)
            return ''


def getHackerNewsSimpleContent(fetcherURL, fetcherBackupURL, id, page='', format='json', url='', referer='', remote_addr=''):
    #don't cache paginated content
    if (page):
        return APIUtils.parsePageContent(fetcherURL, fetcherBackupURL, id, page, format)
    else:
        cachedData = getCache(id, format)
        if (cachedData):
            return cachedData
        else:
            hnData = APIUtils.parsePageContent(fetcherURL, fetcherBackupURL, id, page, format)
            if (hnData):
                logging.debug('getHackerNewsSimpleContent: storing cached value for id %s' % id)
                DataCache.putData(id, format, APIUtils.removeNonAscii(hnData), url, referer, remote_addr)
                return hnData
            else:
                logging.warning('getHackerNewsSimpleContent: unable to retrieve data for id %s' % id)
                return ''


#parse HN's ask content
def getHackerNewsAskContent(page='', format='json', url='', referer='', remote_addr=''):
    return getHackerNewsSimpleContent(AppConfig.hackerNewsAskURL, AppConfig.hackerNewsAskURLBackup, '/ask', page, format, url, referer, remote_addr)


#parse HN's best content
def getHackerNewsBestContent(page='', format='json', url='', referer='', remote_addr=''):
    return getHackerNewsSimpleContent(AppConfig.hackerNewsBestURL, AppConfig.hackerNewsBestURLBackup, '/best', page, format, url, referer, remote_addr)


#parse HN's newest content
def getHackerNewsNewestContent(page='', format='json', url='', referer='', remote_addr=''):
    return getHackerNewsSimpleContent(AppConfig.hackerNewsNewestURL, AppConfig.hackerNewsNewestURLBackup, '/newest', page, format, url, referer, remote_addr)


#get homepage second page stories
def getHackerNewsSecondPageContent(page='', format='json', url='', referer='', remote_addr=''):
    return getHackerNewsSimpleContent(AppConfig.hackerNewsPage2URL, AppConfig.hackerNewsPage2URLBackup, '/news2', page, format, url, referer, remote_addr)


#get homepage first page stories
def getHackerNewsPageContent(page='', format='json', url='', referer='', remote_addr=''):
    return getHackerNewsSimpleContent(AppConfig.hackerNewsURL, AppConfig.hackerNewsURLBackup, '/news', page, format, url, referer, remote_addr)


#get latest homepage stories
def getHackerNewsLatestContent(page='', format='json', url='', referer='', remote_addr='', limit=1):
    #only cache homepage data
    limit = int(limit)
    if (page):
        return APIUtils.parsePageContent(AppConfig.hackerNewsURL, AppConfig.hackerNewsURLBackup, '/latest', page, format, limit)
    else:
        id = '/latest/%s' % limit
        cachedData = getCache(id, format)
        if (cachedData):
            return cachedData
        else:
            hnData = APIUtils.parsePageContent(AppConfig.hackerNewsURL, AppConfig.hackerNewsURLBackup,  '/latest', page, format, limit)
            if (hnData):
                logging.debug('getHackerNewsLatestContent: storing cached value for id %s' % id)
                DataCache.putData(id, format, APIUtils.removeNonAscii(hnData), url, referer, remote_addr)
                return hnData
            else:
                logging.warning('getHackerNewsLatestContent: unable to retrieve data for id %s' % id)
                return ''

########NEW FILE########
__FILENAME__ = APIUtils
#
# Main Library to parse Hacker News homepage, rss, newest, and best content
#

from UserString import MutableString
import re
import logging
import Formatter
from xml.dom import minidom
from xml.sax.saxutils import escape
import urllib
import AppConfig
from google.appengine.api import urlfetch
from BeautifulSoup import BeautifulSoup
from django.utils import simplejson
from structured import list2xml

def removeHtmlTags(data):
	p = re.compile(r'<.*?>')
	return p.sub('', data)

def removeNonAscii(s): return "" . join(filter(lambda x: ord(x)<128, s))

#call urlfetch to get remote data
def fetchRemoteData(urlStr, deadline):
	result = urlfetch.fetch(url=urlStr, deadline=deadline)
	if result.status_code == 200 and result and result.content:
		return result
	else:
		logging.error('fetchRemoteData: unable to get remote data: %s' % urlStr)
		raise Exception("fetchRemoteData: failed")

#call remote server to get data. If failed (timeout), try again and again and again and again (4 attempts because urlfetch on the GAE f-ing sucks)
def getRemoteData(urlStr, backupUrl):
	#attempt #1
	try:	
		logging.debug('getRemoteData: Attempt #1: %s' % urlStr)
		return fetchRemoteData(urlStr, 30)
	except:
		#attempt #2
		try:
			logging.debug('getRemoteData: First attempt failed... Attempt #2(Backup URL): %s' % backupUrl)
			return fetchRemoteData(backupUrl, 30)
		except:
			#attempt #3
			try:
				logging.debug('getRemoteData: First attempt failed... Attempt #3: %s' % urlStr)
				return fetchRemoteData(urlStr, 30)
			except:
				#attempt #4
				try:
					logging.debug('getRemoteData: First attempt failed... Attempt #4 (Backup URL): %s' % backupUrl)
					return fetchRemoteData(backupUrl, 30)
				except:
					logging.error('getRemoteData: unable to get remote data...Attempt #4. Stack')
					return None
	return None

#parse post data 
def parsePostContent(hnAPIUrl,hnBackupAPIUrl, apiURL, page='',format='json',limit=0):
	returnData = MutableString()
	returnData = ''
	logging.debug('HN URL: %s' % hnAPIUrl)
	
	#next page content (not allowed - robots.txt Disallow)
	#if (page):
	#	hnAPIUrl = '%s/x?fnid=%s' % (AppConfig.hackerNewsURL, page)
	
	#call HN website to get data
	httpData = getRemoteData(hnAPIUrl)
	if (httpData):
		htmlData = httpData
		#php parser (primary API)
		if ('{"title":"' in htmlData and 'HNDroidAPI PHP Parser' in htmlData):
			return htmlData

		#classic API fallback
		soup = BeautifulSoup(htmlData)
		urlLinksContent = soup('td', {'class' : 'title'})
		counter = 0
		url_links = {}
		for node in urlLinksContent:
			if (node.a):
				url_links[counter] = [node.a['href'], node.a.string]
				counter = counter + 1
				if (limit > 0 and counter == limit):
					break;
		
		#get comments & the rest
		commentsContent = soup('td', {'class' : 'subtext'})
		counter = 0
		comments_stuff = {}
		for node in commentsContent:
			if (node):
				#parsing this
				#<td class="subtext"><span id="score_3002117">110 points</span> by <a href="user?id=JoelSutherland">JoelSutherland</a> 3 hours ago  | <a href="item?id=3002117">36 comments</a></td>
				nodeString = removeHtmlTags(str(node))
				score = node.first('span', {'id' : re.compile('^score.*')}).string
				user = node.first('a', {'href' : re.compile('^user.*')}).string
				itemId = node.first('a', {'href' : re.compile('^item.*')})["href"]
				comments = node.first('a', {'href' : re.compile('^item.*')}).string
				#since 'XX hours ago' string isn't part of any element we need to simply search and replace other text to get it
				timeAgo = nodeString.replace(str(score), '')
				timeAgo = timeAgo.replace('by %s' % str(user), '')
				timeAgo = timeAgo.replace(str(comments), '')
				timeAgo = timeAgo.replace('|', '')
				comments_stuff[counter] = [score, user, comments, timeAgo.strip(), itemId, nodeString]
				counter = counter + 1
				if (limit > 0 and counter == limit):
					break;
		
		#build up string		
		for key in url_links.keys():
			tupURL = url_links[key]
			if (key in comments_stuff):
				tupComments = comments_stuff[key]
			else:
				tupComments = None
			if (tupURL):
				url = ''
				title = ''
				score = ''
				user = ''
				comments = ''
				timeAgo = ''
				itemId = ''
				itemInfo = ''
				
				#assign vars
				url = tupURL[0]
				title = tupURL[1]
				if (title):
					title = title.decode("string-escape")
				
				if (tupComments):
					score = tupComments[0]
					if (score):
						score = score.decode("string-escape")
					user = tupComments[1]
					if (user):
						user = user.decode("string-escape")
					comments = tupComments[2]
					if (comments):
						comments = comments.decode("string-escape")
					timeAgo = tupComments[3]
					if (timeAgo):
						timeAgo = timeAgo.decode("string-escape")
					itemId = tupComments[4]
					if (itemId):
						itemId = itemId.decode("string-escape")
					itemInfo = tupComments[5]
					if (itemInfo):
						itemInfo = itemInfo.decode("string-escape")
				else:
					#need this for formatting
					itemInfo = 'n/a '
				
				#last record (either news2 or x?fnid)
				if (title.lower() == 'more' or '/x?fnid' in url):
					title = 'NextId'
					if ('/x?fnid' in url):
						url = '%s/format/%s/page/%s' % (apiURL, format, url.replace('/x?fnid=', ''))
					else:
						url = '/news2'
					itemInfo = 'hn next id %s ' % tupURL[0]
				
				if (format == 'json'):
					startTag = '{'
					endTag = '},'
					
					#cleanup
					if (title):
						title = re.sub("\n", "", title)
						title = re.sub("\"", "\\\"", title)
						#title = re.sub("&euro;", "", title)
					
					if (itemInfo):
						itemInfo = re.sub("\"", "\\\"", itemInfo)
						itemInfo = re.sub("\n", "", itemInfo)
						itemInfo = re.sub("\t", " ", itemInfo)
						itemInfo = re.sub("\r", "", itemInfo)
						#itemInfo = re.sub("&euro;", "", itemInfo)

					if (len(itemInfo) > 0):
						itemInfo = Formatter.data(format, 'description', escape(itemInfo))[:-1]
				else:
					startTag = '<record>'
					endTag = '</record>'
					if (len(title) > 0):
						title = escape(removeNonAscii(title))
						
					if (len(url) > 0):
						url = escape(url)
					
					if (len(user) > 0):
						user = escape(user)
						
					if (len(itemInfo) > 0):
						itemInfo = Formatter.data(format, 'description', escape(itemInfo))								

				if (len(title) > 0):
					returnData += startTag + Formatter.data(format, 'title', title)

				if (len(url) > 0):
					returnData += Formatter.data(format, 'url', url) 

				if (len(score) > 0):
					returnData += Formatter.data(format, 'score', score)
					
				if (len(user) > 0):
					returnData += Formatter.data(format, 'user', user)
				
				if (len(comments) > 0):
					returnData += Formatter.data(format, 'comments', comments)

				if (len(timeAgo) > 0):
					returnData += Formatter.data(format, 'time', timeAgo)
					
				if (len(itemId) > 0):
					#cleanup
					if ('item?id=' in itemId):
						itemId = itemId.replace('item?id=', '')
					returnData += Formatter.data(format, 'item_id', itemId)

				if (len(itemInfo) > 0 ):
					returnData += itemInfo + endTag
	else:
		returnData = None
	
	return returnData

#parse content using Beautiful Soup
def parsePageContent(hnAPIUrl,hnBackupAPIUrl, apiURL, page='',format='json',limit=0):
	returnData = MutableString()
	returnData = ''
	logging.debug('HN URL: %s' % hnAPIUrl)
	
	#next page content
	if (page):
		hnAPIUrl = '%s/x?fnid=%s' % (AppConfig.hackerNewsURL, page)
	
	#call HN website to get data
	result = getRemoteData(hnAPIUrl,hnBackupAPIUrl)
	if (result):
		htmlData = result.content	
		soup = BeautifulSoup(htmlData)
		urlLinksContent = soup('td', {'class' : 'title'})
		counter = 0
		url_links = {}
		for node in urlLinksContent:
			if (node.a):
				url_links[counter] = [node.a['href'], node.a.string]
				counter = counter + 1
				if (limit > 0 and counter == limit):
					break;
		
		#get comments & the rest
		commentsContent = soup('td', {'class' : 'subtext'})
		counter = 0
		comments_stuff = {}
		for node in commentsContent:
			if (node):
				#parsing this
				#<td class="subtext"><span id="score_3002117">110 points</span> by <a href="user?id=JoelSutherland">JoelSutherland</a> 3 hours ago  | <a href="item?id=3002117">36 comments</a></td>
				nodeString = removeHtmlTags(str(node))
				score = node.first('span', {'id' : re.compile('^score.*')}).string
				user = node.first('a', {'href' : re.compile('^user.*')}).string
				itemId = node.first('a', {'href' : re.compile('^item.*')})["href"]
				comments = node.first('a', {'href' : re.compile('^item.*')}).string
				#since 'XX hours ago' string isn't part of any element we need to simply search and replace other text to get it
				timeAgo = nodeString.replace(str(score), '')
				timeAgo = timeAgo.replace('by %s' % str(user), '')
				timeAgo = timeAgo.replace(str(comments), '')
				timeAgo = timeAgo.replace('|', '')
				comments_stuff[counter] = [score, user, comments, timeAgo.strip(), itemId, nodeString]
				counter = counter + 1
				if (limit > 0 and counter == limit):
					break;
		
		#build up string		
		for key in url_links.keys():
			tupURL = url_links[key]
			if (key in comments_stuff):
				tupComments = comments_stuff[key]
			else:
				tupComments = None
			if (tupURL):
				url = ''
				title = ''
				score = ''
				user = ''
				comments = ''
				timeAgo = ''
				itemId = ''
				itemInfo = ''
				
				#assign vars
				url = tupURL[0]
				title = tupURL[1]
				
				if (tupComments):
					score = tupComments[0]
					user = tupComments[1]
					comments = tupComments[2]
					timeAgo = tupComments[3]
					itemId = tupComments[4]
					itemInfo = tupComments[5]
				else:
					#need this for formatting
					itemInfo = 'n/a '
				
				#last record (either news2 or x?fnid)
				if (title.lower() == 'more' or '/x?fnid' in url):
					title = 'NextId'
					if ('/x?fnid' in url):
						url = '%s/format/%s/page/%s' % (apiURL, format, url.replace('/x?fnid=', ''))
					else:
						url = '/news2'
					itemInfo = 'hn next id %s ' % tupURL[0]
				
				if (format == 'json'):
					startTag = '{'
					endTag = '},'
					
					#cleanup
					if (title):
						title = re.sub("\n", "", title)
						title = re.sub("\"", "\\\"", title)
					
					if (itemInfo):
						itemInfo = re.sub("\"", "\\\"", itemInfo)
						itemInfo = re.sub("\n", "", itemInfo)
						itemInfo = re.sub("\t", " ", itemInfo)
						itemInfo = re.sub("\r", "", itemInfo)

					if (len(itemInfo) > 0):
						itemInfo = Formatter.data(format, 'description', escape(itemInfo))[:-1]
				else:
					startTag = '<record>'
					endTag = '</record>'
					if (len(title) > 0):
						title = escape(removeNonAscii(title))
						
					if (len(url) > 0):
						url = escape(url)
					
					if (len(user) > 0):
						user = escape(user)
						
					if (len(itemInfo) > 0):
						itemInfo = Formatter.data(format, 'description', escape(itemInfo))								

				if (len(title) > 0):
					returnData += startTag + Formatter.data(format, 'title', title)

				if (len(url) > 0):
					returnData += Formatter.data(format, 'url', url) 

				if (len(score) > 0):
					returnData += Formatter.data(format, 'score', score)
					
				if (len(user) > 0):
					returnData += Formatter.data(format, 'user', user)
				
				if (len(comments) > 0):
					returnData += Formatter.data(format, 'comments', comments)

				if (len(timeAgo) > 0):
					returnData += Formatter.data(format, 'time', timeAgo)
					
				if (len(itemId) > 0):
					#cleanup
					if ('item?id=' in itemId):
						itemId = itemId.replace('item?id=', '')
					returnData += Formatter.data(format, 'item_id', itemId)

				if (len(itemInfo) > 0 ):
					returnData += itemInfo + endTag
	else:
		returnData = None
	
	return returnData

#retrieves multi-paragraph comments
def getParagraphCommentSiblings(node):
	nodeText = MutableString()
	if (node):
		#get first paragraph
		nodeText = str(node.font)
		nextSib = node.nextSibling
		if (nextSib and "<p>" in str(nextSib)):
			while (nextSib and "<p>" in str(nextSib)):
				tmpStr = str(nextSib)
				if (nodeText):
					nodeText += "__BR__%s" % tmpStr
				else:
					nodeText = tmpStr
				nextSib = nextSib.nextSibling
		return nodeText

#parse comments using Beautiful Soup
def parseCommentsContent(hnAPIUrl, hnAPIUrlBackup, apiURL, page='',format='json'):
	returnData = MutableString()
	returnData = ''
	logging.debug('HN URL: %s' % hnAPIUrl)

	result = getRemoteData(hnAPIUrl, hnAPIUrlBackup)
	if (result):
		htmlData = result.content	
		soup = BeautifulSoup(htmlData)
		urlLinksContent = soup('table')
		counter = 0
		comment_container = {}
		for node in urlLinksContent:
			commentTd = node.first('td', {'class' : 'default'})
			if (commentTd):
				authorSpan = commentTd.first('span', {'class' : 'comhead'})
				#multi-paragraph comments are a bit tricky, parser wont' retrieve them using "span class:comment" selector
				commentSpan = getParagraphCommentSiblings(commentTd.first('span', {'class' : 'comment'}))
				replyLink = commentTd.first('a', {'href' : re.compile('^reply.*')})['href']
				if (replyLink and "reply?id=" in replyLink):
					replyLink = replyLink.replace('reply?id=', '')
				if (authorSpan and commentSpan):
					#author span: <span class="comhead"><a href="user?id=dendory">dendory</a> 1 day ago  | <a href="item?id=3015166">link</a></span>
					commentId = authorSpan.first('a', {'href' : re.compile('^item.*')})
					user = authorSpan.first('a', {'href' : re.compile('^user.*')})
					#get time posted...lame but works. for some reason authorSpan.string returns NULL
					timePosted = str(authorSpan).replace('<span class="comhead">', '').replace('</span>', '')
					#now replace commentId and user blocks
					timePosted = timePosted.replace(str(user), '').replace('| ', '').replace(str(commentId), '')
					if (commentId['href'] and "item?id=" in commentId['href']):
						commentId = commentId['href'].replace('item?id=', '')
					#cleanup
					commentString = removeHtmlTags(str(commentSpan))
					if ('__BR__reply' in commentString):
						commentString = commentString.replace('__BR__reply', '')
					comment_container[counter] = [commentId, user.string, timePosted.strip(), commentString, replyLink]
					counter = counter + 1
			
		#build up string	
		commentKeyContainer = {}	
		for key in comment_container.keys():
			listCommentData = comment_container[key]
			if (listCommentData and not commentKeyContainer.has_key(listCommentData[0])):
				commentId = listCommentData[0]
				if (commentId):
					commentKeyContainer[commentId] = 1
				userName = listCommentData[1]
				whenPosted = listCommentData[2]
				commentsString = listCommentData[3]
				replyId = listCommentData[4]
				
				if (format == 'json'):
					startTag = '{'
					endTag = '},'

					#cleanup
					if (commentsString):
						commentsString = re.sub("\"", "\\\"", commentsString)
						commentsString = re.sub("\n", "", commentsString)
						commentsString = re.sub("\t", " ", commentsString)
						commentsString = re.sub("\r", "", commentsString)

					if (len(commentsString) > 0):
						commentsString = Formatter.data(format, 'comment', escape(removeNonAscii(commentsString)))
					else:
						commentsString = "n/a "
				else:
					startTag = '<record>'
					endTag = '</record>'
					if (len(userName) > 0):
						userName = escape(removeNonAscii(userName))

					if (len(whenPosted) > 0):
						whenPosted = escape(whenPosted)

					if (len(commentsString) > 0):
						commentsString = Formatter.data(format, 'comment', escape(removeNonAscii(commentsString)))								

				if (commentId and userName and whenPosted and replyId and commentsString):
					if (len(commentId) > 0):
						returnData += startTag + Formatter.data(format, 'id', commentId)
							
					if (len(userName) > 0):
						returnData += Formatter.data(format, 'username', userName)

					if (len(whenPosted) > 0):
						returnData += Formatter.data(format, 'time', whenPosted)

					if (len(replyId) > 0):
						returnData += Formatter.data(format, 'reply_id', escape(replyId))

					if (len(commentsString) > 0 ):
						returnData += commentsString + endTag
	else:
		returnData = None

	return returnData

#parse comments using Beautiful Soup
def parseNestedCommentsContent(hnAPIUrl, hnAPIUrlBackup, apiURL, page='',format='json'):
	returnData = None
	logging.debug('HN URL: %s' % hnAPIUrl)

	result = getRemoteData(hnAPIUrl, hnAPIUrlBackup)
	if (result):
		htmlData = result.content	
		soup = BeautifulSoup(htmlData)
		urlLinksContent = soup('table')
		counter = 0
		comment_container = {}
		for node in urlLinksContent:
			commentTd = node.first('td', {'class' : 'default'})
			if (commentTd):
				previousTds = commentTd.fetchPreviousSiblings('td')
				nestLevel = 0
				if (previousTds[-1].first('img')['width']):
					nestLevel = int(previousTds[-1].first('img')['width'])/40

				authorSpan = commentTd.first('span', {'class' : 'comhead'})
				#multi-paragraph comments are a bit tricky, parser wont' retrieve them using "span class:comment" selector
				commentSpan = commentTd.first('span', {'class' : 'comment'})
				commentText = getParagraphCommentSiblings(commentSpan)
				replyLink = commentTd.first('a', {'href' : re.compile('^reply.*')})['href']
				if (replyLink and "reply?id=" in replyLink):
					replyLink = replyLink.replace('reply?id=', '')
				if (authorSpan and commentText):
					#author span: <span class="comhead"><a href="user?id=dendory">dendory</a> 1 day ago  | <a href="item?id=3015166">link</a></span>
					commentId = authorSpan.first('a', {'href' : re.compile('^item.*')})
					user = authorSpan.first('a', {'href' : re.compile('^user.*')})
					#get time posted...lame but works. for some reason authorSpan.string returns NULL
					timePosted = str(authorSpan).replace('<span class="comhead">', '').replace('</span>', '')
					#now replace commentId and user blocks
					timePosted = timePosted.replace(str(user), '').replace('| ', '').replace(str(commentId), '')
					if (commentId['href'] and "item?id=" in commentId['href']):
						commentId = commentId['href'].replace('item?id=', '')
					#cleanup
					commentString = removeHtmlTags(str(commentText))
					if ('__BR__reply' in commentString):
						commentString = commentString.replace('__BR__reply', '')

					# Determine if comment is being "grayed out" due to downvotes
					grayedOutPercent = 0
					commentFont = commentSpan.first('font')
					if(commentFont and commentFont['color'] != '#000000'):
						fontBrightness = int(commentFont['color'][1:3], 16)
						grayedOutPercent = int(fontBrightness /
							float(AppConfig.hackerNewsBgroundBrightness) * 100)

					comment_container[counter] =	[
														commentId,
														user.string,
														timePosted.strip(),
														commentString,
														replyLink,
														grayedOutPercent,
														nestLevel
													]
					counter = counter + 1
			
		#build up string	
		commentKeyContainer = {}
		nestLevels = []
		comments = []
		for key in comment_container.keys():
			comment = {}
			listCommentData = comment_container[key]
			if (listCommentData and not commentKeyContainer.has_key(listCommentData[0])):
				commentId = listCommentData[0]
				if (commentId):
					commentKeyContainer[commentId] = 1
				userName = listCommentData[1]
				whenPosted = listCommentData[2]
				commentsString = listCommentData[3]
				replyId = listCommentData[4]
				grayedOutPercent = listCommentData[5]
				nestLevel = listCommentData[6]
				
				if (format == 'json'):

					#cleanup
					if (commentsString):
						commentsString = re.sub("\"", "\\\"", commentsString)
						commentsString = re.sub("\n", "", commentsString)
						commentsString = re.sub("\t", " ", commentsString)
						commentsString = re.sub("\r", "", commentsString)

					if (len(commentsString) > 0):
						commentsString = escape(removeNonAscii(commentsString))
					else:
						commentsString = "n/a "
				else:
					if (len(userName) > 0):
						userName = escape(removeNonAscii(userName))

					if (len(whenPosted) > 0):
						whenPosted = escape(whenPosted)

					if (len(commentsString) > 0):
						commentsString = escape(removeNonAscii(commentsString))

				if (commentId and userName and whenPosted and replyId and commentsString):
					comment['children'] = []

					if (len(commentId) > 0):
						comment['id'] = commentId
							
					if (len(userName) > 0):
						comment['username'] = userName

					if (len(whenPosted) > 0):
						comment['time'] = whenPosted

					if (len(replyId) > 0):
						comment['reply_id'] = escape(replyId)

					if (len(commentsString) > 0 ):
						comment['comment'] = commentsString

					comment['grayedOutPercent'] = grayedOutPercent

					if nestLevel == 0:
						comments.append(comment)
					else:
						nestLevels[nestLevel - 1]['children'].append(comment)
					nestLevels.insert(nestLevel, comment)

	if (format == 'json'):
		returnData = simplejson.dumps(comments)
	else:
		returnData = list2xml(comments, 'root', 'record', listnames = {'children': 'record'})
	return returnData

#parse HN's RSS feed
def getHackerNewsRSS(format='json'):
	returnData = MutableString()
	returnData = ''
	dom = minidom.parse(urllib.urlopen(AppConfig.hackerNewsRSSFeed))
	rssTitle = MutableString()
	rssDescription = MutableString()
	rssURL = MutableString()
	for node in dom.getElementsByTagName('item'):
		for item_node in node.childNodes:
			rssTitle = ''
			rssDescription = ''
			rssURL = ''
			#item title
			if (item_node.nodeName == "title"):
				for text_node in item_node.childNodes:
					if (text_node.nodeType == node.TEXT_NODE):
						rssTitle += text_node.nodeValue
			#description
			if (item_node.nodeName == "description"):
				for text_node in item_node.childNodes:
					rssDescription += text_node.nodeValue
			#link to URL
			if (item_node.nodeName == "link"):
				for text_node in item_node.childNodes:
					rssURL += text_node.nodeValue
			
			if (format == 'json'):
				startTag = '{'
				endTag = '},'
				
				#cleanup
				#rssTitle = re.sub("\"", "'", rssTitle)
				rssTitle = re.sub("\n", "", rssTitle)
				rssTitle = re.sub("\"", "\\\"", rssTitle)
				rssDescription = re.sub("\"", "\\\"", rssDescription)
				rssDescription = re.sub("\n", "", rssDescription)
				rssDescription = re.sub("\t", " ", rssDescription)
				rssDescription = re.sub("\r", "", rssDescription)
				
				if (len(rssDescription) > 0):
					rssDescription = Formatter.data(format, 'description', escape(rssDescription))[:-1]
			else:
				startTag = '<record>'
				endTag = '</record>'		
				
				if (len(rssTitle) > 0):
					rssTitle = escape(removeNonAscii(rssTitle))
					
				if (len(rssURL) > 0):
					rssURL = escape(rssURL)
					
				if (len(rssDescription) > 0):
					rssDescription = Formatter.data(format, 'description', escape(rssDescription))								
			
			if (len(rssTitle) > 0):
				returnData += startTag + Formatter.data(format, 'title', rssTitle)
				
			if (len(rssURL) > 0):
				returnData += Formatter.data(format, 'url', rssURL) 
			
			if (len(rssDescription) > 0 ):
				returnData += rssDescription + endTag
	
	return returnData

########NEW FILE########
__FILENAME__ = AppConfig
#!/usr/bin/env python
#
# Hacker News API Config
#
#main server
hackerNewsRSSFeed = 'http://tinyurl.com/6y37ehb'  # http://news.ycombinator.com/rss
hackerNewsURL = 'http://tinyurl.com/3nkabdb'  # http://news.ycombinator.com
hackerNewsPage2URL = 'http://tinyurl.com/69cgmyd'  # http://news.ycombinator.com/news2
hackerNewsNewestURL = 'http://tinyurl.com/3ouh6ml'  # http://news.ycombinator.org/newest
hackerNewsBestURL = 'http://tinyurl.com/68y3nzx'  # http://news.ycombinator.org/best
hackerNewsAskURL = 'http://tinyurl.com/3lduuz8'  # http://news.ycombinator.org/ask
#backup
hackerNewsRSSFeedBackup = 'http://tinyurl.com/6y37ehb'  # http://news.ycombinator.com/rss
hackerNewsURLBackup = 'http://tinyurl.com/3nkabdb'  # http://news.ycombinator.com
hackerNewsPage2URLBackup = 'http://tinyurl.com/69cgmyd'  # http://news.ycombinator.com/news2
hackerNewsNewestURLBackup = 'http://tinyurl.com/3ouh6ml'  # http://news.ycombinator.org/newest
hackerNewsBestURLBackup = 'http://tinyurl.com/68y3nzx'  # http://news.ycombinator.org/best
hackerNewsAskURLBackup = 'http://tinyurl.com/3lduuz8'  # http://news.ycombinator.org/ask

#other settings
hackerNewsRSSFeed = 'http://tinyurl.com/6y37ehb'  # http://news.ycombinator.com/rss
hackerNewsBgroundBrightness = 0xf6	 # HN pages' background color "R" value (out of "RGB")

googleAnalyticsKey = 'XYZ'  # your GA code
dataExpirationPolicy = '180'  # in seconds
appDomain = 'hndroidapi.appspot.com'  # hndroidapi.appspot.com

########NEW FILE########
__FILENAME__ = BeautifulSoup
"""Beautiful Soup
Elixir and Tonic
"The Screen-Scraper's Friend"
v2.1.1
http://www.crummy.com/software/BeautifulSoup/

Beautiful Soup parses arbitrarily invalid XML- or HTML-like substance
into a tree representation. It provides methods and Pythonic idioms
that make it easy to search and modify the tree.

A well-formed XML/HTML document will yield a well-formed data
structure. An ill-formed XML/HTML document will yield a
correspondingly ill-formed data structure. If your document is only
locally well-formed, you can use this library to find and process the
well-formed part of it. The BeautifulSoup class has heuristics for
obtaining a sensible parse tree in the face of common HTML errors.

Beautiful Soup has no external dependencies. It works with Python 2.2
and up.

Beautiful Soup defines classes for four different parsing strategies:

 * BeautifulStoneSoup, for parsing XML, SGML, or your domain-specific
   language that kind of looks like XML.

 * BeautifulSoup, for parsing run-of-the-mill HTML code, be it valid
   or invalid.

 * ICantBelieveItsBeautifulSoup, for parsing valid but bizarre HTML
   that trips up BeautifulSoup.

 * BeautifulSOAP, for making it easier to parse XML documents that use
   lots of subelements containing a single string, where you'd prefer
   they put that string into an attribute (such as SOAP messages).

You can subclass BeautifulStoneSoup or BeautifulSoup to create a
parsing strategy specific to an XML schema or a particular bizarre
HTML document. Typically your subclass would just override
SELF_CLOSING_TAGS and/or NESTABLE_TAGS.
"""
from __future__ import generators

__author__ = "Leonard Richardson (leonardr@segfault.org)"
__version__ = "2.1.1"
__date__ = "$Date: 2004/10/18 00:14:20 $"
__copyright__ = "Copyright (c) 2004-2005 Leonard Richardson"
__license__ = "PSF"

from sgmllib import SGMLParser, SGMLParseError
import types
import re
import sgmllib

#This code makes Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')

class NullType(object):

    """Similar to NoneType with a corresponding singleton instance
    'Null' that, unlike None, accepts any message and returns itself.

    Examples:
    >>> Null("send", "a", "message")("and one more",
    ...      "and what you get still") is Null
    True
    """

    def __new__(cls):                    return Null
    def __call__(self, *args, **kwargs): return Null
##    def __getstate__(self, *args):       return Null
    def __getattr__(self, attr):         return Null
    def __getitem__(self, item):         return Null
    def __setattr__(self, attr, value):  pass
    def __setitem__(self, item, value):  pass
    def __len__(self):                   return 0
    # FIXME: is this a python bug? otherwise ``for x in Null: pass``
    #        never terminates...
    def __iter__(self):                  return iter([])
    def __contains__(self, item):        return False
    def __repr__(self):                  return "Null"
Null = object.__new__(NullType)

class PageElement:
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    def setup(self, parent=Null, previous=Null):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous = previous
        self.next = Null
        self.previousSibling = Null
        self.nextSibling = Null
        if self.parent and self.parent.contents:
            self.previousSibling = self.parent.contents[-1]
            self.previousSibling.nextSibling = self

    def findNext(self, name=None, attrs={}, text=None):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._first(self.fetchNext, name, attrs, text)
    firstNext = findNext

    def fetchNext(self, name=None, attrs={}, text=None, limit=None):
        """Returns all items that match the given criteria and appear
        before after Tag in the document."""
        return self._fetch(name, attrs, text, limit, self.nextGenerator)

    def findNextSibling(self, name=None, attrs={}, text=None):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._first(self.fetchNextSiblings, name, attrs, text)
    firstNextSibling = findNextSibling

    def fetchNextSiblings(self, name=None, attrs={}, text=None, limit=None):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._fetch(name, attrs, text, limit, self.nextSiblingGenerator)

    def findPrevious(self, name=None, attrs={}, text=None):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._first(self.fetchPrevious, name, attrs, text)

    def fetchPrevious(self, name=None, attrs={}, text=None, limit=None):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._fetch(name, attrs, text, limit, self.previousGenerator)
    firstPrevious = findPrevious

    def findPreviousSibling(self, name=None, attrs={}, text=None):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._first(self.fetchPreviousSiblings, name, attrs, text)
    firstPreviousSibling = findPreviousSibling

    def fetchPreviousSiblings(self, name=None, attrs={}, text=None,
                              limit=None):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._fetch(name, attrs, text, limit,
                           self.previousSiblingGenerator)

    def findParent(self, name=None, attrs={}):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        r = Null
        l = self.fetchParents(name, attrs, 1)
        if l:
            r = l[0]
        return r
    firstParent = findParent

    def fetchParents(self, name=None, attrs={}, limit=None):
        """Returns the parents of this Tag that match the given
        criteria."""
        return self._fetch(name, attrs, None, limit, self.parentGenerator)

    #These methods do the real heavy lifting.

    def _first(self, method, name, attrs, text):
        r = Null
        l = method(name, attrs, text, 1)
        if l:
            r = l[0]
        return r
    
    def _fetch(self, name, attrs, text, limit, generator):
        "Iterates over a generator looking for things that match."
        if not hasattr(attrs, 'items'):
            attrs = {'class' : attrs}

        results = []
        g = generator()
        while True:
            try:
                i = g.next()
            except StopIteration:
                break
            found = None
            if isinstance(i, Tag):
                if not text:
                    if not name or self._matches(i, name):
                        match = True
                        for attr, matchAgainst in attrs.items():
                            check = i.get(attr)
                            if not self._matches(check, matchAgainst):
                                match = False
                                break
                        if match:
                            found = i
            elif text:
                if self._matches(i, text):
                    found = i                    
            if found:
                results.append(found)
                if limit and len(results) >= limit:
                    break
        return results

    #Generators that can be used to navigate starting from both
    #NavigableTexts and Tags.                
    def nextGenerator(self):
        i = self
        while i:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i:
            i = i.parent
            yield i

    def _matches(self, chunk, howToMatch):
        #print 'looking for %s in %s' % (howToMatch, chunk)
        #
        # If given a list of items, return true if the list contains a
        # text element that matches.
        if isList(chunk) and not isinstance(chunk, Tag):
            for tag in chunk:
                if isinstance(tag, NavigableText) and self._matches(tag, howToMatch):
                    return True
            return False
        if callable(howToMatch):
            return howToMatch(chunk)
        if isinstance(chunk, Tag):
            #Custom match methods take the tag as an argument, but all other
            #ways of matching match the tag name as a string
            chunk = chunk.name
        #Now we know that chunk is a string
        if not isinstance(chunk, basestring):
            chunk = str(chunk)
        if hasattr(howToMatch, 'match'):
            # It's a regexp object.
            return howToMatch.search(chunk)
        if isList(howToMatch):
            return chunk in howToMatch
        if hasattr(howToMatch, 'items'):
            return howToMatch.has_key(chunk)
        #It's just a string
        return str(howToMatch) == chunk

class NavigableText(PageElement):

    def __getattr__(self, attr):
        "For backwards compatibility, text.string gives you text"
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)
        
class NavigableString(str, NavigableText):
    pass

class NavigableUnicodeString(unicode, NavigableText):
    pass

class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def __init__(self, name, attrs=None, parent=Null, previous=Null):
        "Basic constructor."
        self.name = name
        if attrs == None:
            attrs = []
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)    

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self._getAttrMap()[key]

    def __iter__(self):
        "Iterating over a tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __nonzero__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):        
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self._getAttrMap()
        self.attrMap[key] = value
        found = False
        for i in range(0, len(self.attrs)):
            if self.attrs[i][0] == key:
                self.attrs[i] = (key, value)
                found = True
        if not found:
            self.attrs.append((key, value))
        self._getAttrMap()[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        for item in self.attrs:
            if item[0] == key:
                self.attrs.remove(item)
                #We don't break because bad HTML can define the same
                #attribute multiple times.
            self._getAttrMap()
            if self.attrMap.has_key(key):
                del self.attrMap[key]

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        fetch() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return apply(self.fetch, args, kwargs)

    def __getattr__(self, tag):
        if len(tag) > 3 and tag.rfind('Tag') == len(tag)-3:
            return self.first(tag[:-3])
        elif tag.find('__') != 0:
            return self.first(tag)

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag.

        NOTE: right now this will return false if two tags have the
        same attributes in a different order. Should this be fixed?"""
        if not hasattr(other, 'name') or not hasattr(other, 'attrs') or not hasattr(other, 'contents') or self.name != other.name or self.attrs != other.attrs or len(self) != len(other):
            return False
        for i in range(0, len(self.contents)):
            if self.contents[i] != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self):
        """Renders this tag as a string."""
        return str(self)

    def __unicode__(self):
        return self.__str__(1)

    def __str__(self, needUnicode=None, showStructureIndent=None):
        """Returns a string or Unicode representation of this tag and
        its contents.

        NOTE: since Python's HTML parser consumes whitespace, this
        method is not certain to reproduce the whitespace present in
        the original string."""
        
        attrs = []
        if self.attrs:
            for key, val in self.attrs:
                attrs.append('%s="%s"' % (key, val))
        close = ''
        closeTag = ''
        if self.isSelfClosing():
            close = ' /'
        else:
            closeTag = '</%s>' % self.name
        indentIncrement = None        
        if showStructureIndent != None:
            indentIncrement = showStructureIndent
            if not self.hidden:
                indentIncrement += 1
        contents = self.renderContents(indentIncrement, needUnicode=needUnicode)        
        if showStructureIndent:
            space = '\n%s' % (' ' * showStructureIndent)
        if self.hidden:
            s = contents
        else:
            s = []
            attributeString = ''
            if attrs:
                attributeString = ' ' + ' '.join(attrs)            
            if showStructureIndent:
                s.append(space)
            s.append('<%s%s%s>' % (self.name, attributeString, close))
            s.append(contents)
            if closeTag and showStructureIndent != None:
                s.append(space)
            s.append(closeTag)
            s = ''.join(s)
        isUnicode = type(s) == types.UnicodeType
        if needUnicode and not isUnicode:
            s = unicode(s)
        elif isUnicode and needUnicode==False:
            s = str(s)
        return s

    def prettify(self, needUnicode=None):
        return self.__str__(needUnicode, showStructureIndent=True)

    def renderContents(self, showStructureIndent=None, needUnicode=None):
        """Renders the contents of this tag as a (possibly Unicode) 
        string."""
        s=[]
        for c in self:
            text = None
            if isinstance(c, NavigableUnicodeString) or type(c) == types.UnicodeType:
                text = unicode(c)
            elif isinstance(c, Tag):
                s.append(c.__str__(needUnicode, showStructureIndent))
            elif needUnicode:
                text = unicode(c)
            else:
                text = str(c)
            if text:
                if showStructureIndent != None:
                    if text[-1] == '\n':
                        text = text[:-1]
                s.append(text)
        return ''.join(s)    

    #Soup methods

    def firstText(self, text, recursive=True):
        """Convenience method to retrieve the first piece of text matching the
        given criteria. 'text' can be a string, a regular expression object,
        a callable that takes a string and returns whether or not the
        string 'matches', etc."""
        return self.first(recursive=recursive, text=text)

    def fetchText(self, text, recursive=True, limit=None):
        """Convenience method to retrieve all pieces of text matching the
        given criteria. 'text' can be a string, a regular expression object,
        a callable that takes a string and returns whether or not the
        string 'matches', etc."""
        return self.fetch(recursive=recursive, text=text, limit=limit)

    def first(self, name=None, attrs={}, recursive=True, text=None):
        """Return only the first child of this
        Tag matching the given criteria."""
        r = Null
        l = self.fetch(name, attrs, recursive, text, 1)
        if l:
            r = l[0]
        return r
    findChild = first

    def fetch(self, name=None, attrs={}, recursive=True, text=None,
              limit=None):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""
        generator = self.recursiveChildGenerator
        if not recursive:
            generator = self.childGenerator
        return self._fetch(name, attrs, text, limit, generator)
    fetchChildren = fetch
    
    #Utility methods

    def isSelfClosing(self):
        """Returns true iff this is a self-closing tag as defined in the HTML
        standard.

        TODO: This is specific to BeautifulSoup and its subclasses, but it's
        used by __str__"""
        return self.name in BeautifulSoup.SELF_CLOSING_TAGS

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.contents.append(tag)

    #Private methods

    def _getAttrMap(self):
        """Initializes a map representation of this tag's attributes,
        if not already initialized."""
        if not getattr(self, 'attrMap'):
            self.attrMap = {}
            for (key, value) in self.attrs:
                self.attrMap[key] = value 
        return self.attrMap

    #Generator methods
    def childGenerator(self):
        for i in range(0, len(self.contents)):
            yield self.contents[i]
        raise StopIteration
    
    def recursiveChildGenerator(self):
        stack = [(self, 0)]
        while stack:
            tag, start = stack.pop()
            if isinstance(tag, Tag):            
                for i in range(start, len(tag.contents)):
                    a = tag.contents[i]
                    yield a
                    if isinstance(a, Tag) and tag.contents:
                        if i < len(tag.contents) - 1:
                            stack.append((tag, i+1))
                        stack.append((a, 0))
                        break
        raise StopIteration


def isList(l):
    """Convenience method that works with all 2.x versions of Python
    to determine whether or not something is listlike."""
    return hasattr(l, '__iter__') \
           or (type(l) in (types.ListType, types.TupleType))

def buildTagMap(default, *args):
    """Turns a list of maps, lists, or scalars into a single map.
    Used to build the SELF_CLOSING_TAGS and NESTABLE_TAGS maps out
    of lists and partial maps."""
    built = {}
    for portion in args:
        if hasattr(portion, 'items'):
            #It's a map. Merge it.
            for k,v in portion.items():
                built[k] = v
        elif isList(portion):
            #It's a list. Map each item to the default.
            for k in portion:
                built[k] = default
        else:
            #It's a scalar. Map it to the default.
            built[portion] = default
    return built

class BeautifulStoneSoup(Tag, SGMLParser):

    """This class contains the basic parser and fetch code. It defines
    a parser that knows nothing about tag behavior except for the
    following:
   
      You can't close a tag without closing all the tags it encloses.
      That is, "<foo><bar></foo>" actually means
      "<foo><bar></bar></foo>".

    [Another possible explanation is "<foo><bar /></foo>", but since
    this class defines no SELF_CLOSING_TAGS, it will never use that
    explanation.]

    This class is useful for parsing XML or made-up markup languages,
    or when BeautifulSoup makes an assumption counter to what you were
    expecting."""

    SELF_CLOSING_TAGS = {}
    NESTABLE_TAGS = {}
    RESET_NESTING_TAGS = {}
    QUOTE_TAGS = {}

    #As a public service we will by default silently replace MS smart quotes
    #and similar characters with their HTML or ASCII equivalents.
    MS_CHARS = { '\x80' : '&euro;',
                 '\x81' : ' ',
                 '\x82' : '&sbquo;',
                 '\x83' : '&fnof;',
                 '\x84' : '&bdquo;',
                 '\x85' : '&hellip;',
                 '\x86' : '&dagger;',
                 '\x87' : '&Dagger;',
                 '\x88' : '&caret;',
                 '\x89' : '%',
                 '\x8A' : '&Scaron;',
                 '\x8B' : '&lt;',
                 '\x8C' : '&OElig;',
                 '\x8D' : '?',
                 '\x8E' : 'Z',
                 '\x8F' : '?',
                 '\x90' : '?',
                 '\x91' : '&lsquo;',
                 '\x92' : '&rsquo;',
                 '\x93' : '&ldquo;',
                 '\x94' : '&rdquo;',
                 '\x95' : '&bull;',
                 '\x96' : '&ndash;',
                 '\x97' : '&mdash;',
                 '\x98' : '&tilde;',
                 '\x99' : '&trade;',
                 '\x9a' : '&scaron;',
                 '\x9b' : '&gt;',
                 '\x9c' : '&oelig;',
                 '\x9d' : '?',
                 '\x9e' : 'z',
                 '\x9f' : '&Yuml;',}

    PARSER_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                       lambda(x):x.group(1) + ' />'),
                      (re.compile('<!\s+([^<>]*)>'),
                       lambda(x):'<!' + x.group(1) + '>'),
                      (re.compile("([\x80-\x9f])"),
                       lambda(x): BeautifulStoneSoup.MS_CHARS.get(x.group(1)))
                      ]

    ROOT_TAG_NAME = '[document]'

    def __init__(self, text=None, avoidParserProblems=True,
                 initialTextIsEverything=True):
        """Initialize this as the 'root tag' and feed in any text to
        the parser.

        NOTE about avoidParserProblems: sgmllib will process most bad
        HTML, and BeautifulSoup has tricks for dealing with some HTML
        that kills sgmllib, but Beautiful Soup can nonetheless choke
        or lose data if your data uses self-closing tags or
        declarations incorrectly. By default, Beautiful Soup sanitizes
        its input to avoid the vast majority of these problems. The
        problems are relatively rare, even in bad HTML, so feel free
        to pass in False to avoidParserProblems if they don't apply to
        you, and you'll get better performance. The only reason I have
        this turned on by default is so I don't get so many tech
        support questions.

        The two most common instances of invalid HTML that will choke
        sgmllib are fixed by the default parser massage techniques:

         <br/> (No space between name of closing tag and tag close)
         <! --Comment--> (Extraneous whitespace in declaration)

        You can pass in a custom list of (RE object, replace method)
        tuples to get Beautiful Soup to scrub your input the way you
        want."""
        Tag.__init__(self, self.ROOT_TAG_NAME)
        if avoidParserProblems \
           and not isList(avoidParserProblems):
            avoidParserProblems = self.PARSER_MASSAGE            
        self.avoidParserProblems = avoidParserProblems
        SGMLParser.__init__(self)
        self.quoteStack = []
        self.hidden = 1
        self.reset()
        if hasattr(text, 'read'):
            #It's a file-type object.
            text = text.read()
        if text:
            self.feed(text)
        if initialTextIsEverything:
            self.done()

    def __getattr__(self, methodName):
        """This method routes method call requests to either the SGMLParser
        superclass or the Tag superclass, depending on the method name."""
        if methodName.find('start_') == 0 or methodName.find('end_') == 0 \
               or methodName.find('do_') == 0:
            return SGMLParser.__getattr__(self, methodName)
        elif methodName.find('__') != 0:
            return Tag.__getattr__(self, methodName)
        else:
            raise AttributeError

    def feed(self, text):
        if self.avoidParserProblems:
            for fix, m in self.avoidParserProblems:
                text = fix.sub(m, text)
        SGMLParser.feed(self, text)

    def done(self):
        """Called when you're done parsing, so that the unclosed tags can be
        correctly processed."""
        self.endData() #NEW
        while self.currentTag.name != self.ROOT_TAG_NAME:
            self.popTag()
            
    def reset(self):
        SGMLParser.reset(self)
        self.currentData = []
        self.currentTag = None
        self.tagStack = []
        self.pushTag(self)        
    
    def popTag(self):
        tag = self.tagStack.pop()
        # Tags with just one string-owning child get the child as a
        # 'string' property, so that soup.tag.string is shorthand for
        # soup.tag.contents[0]
        if len(self.currentTag.contents) == 1 and \
           isinstance(self.currentTag.contents[0], NavigableText):
            self.currentTag.string = self.currentTag.contents[0]

        #print "Pop", tag.name
        if self.tagStack:
            self.currentTag = self.tagStack[-1]
        return self.currentTag

    def pushTag(self, tag):
        #print "Push", tag.name
        if self.currentTag:
            self.currentTag.append(tag)
        self.tagStack.append(tag)
        self.currentTag = self.tagStack[-1]

    def endData(self):
        currentData = ''.join(self.currentData)
        if currentData:
            if not currentData.strip():
                if '\n' in currentData:
                    currentData = '\n'
                else:
                    currentData = ' '
            c = NavigableString
            if type(currentData) == types.UnicodeType:
                c = NavigableUnicodeString
            o = c(currentData)
            o.setup(self.currentTag, self.previous)
            if self.previous:
                self.previous.next = o
            self.previous = o
            self.currentTag.contents.append(o)
        self.currentData = []

    def _popToTag(self, name, inclusivePop=True):
        """Pops the tag stack up to and including the most recent
        instance of the given tag. If inclusivePop is false, pops the tag
        stack up to but *not* including the most recent instqance of
        the given tag."""
        if name == self.ROOT_TAG_NAME:
            return            

        numPops = 0
        mostRecentTag = None
        for i in range(len(self.tagStack)-1, 0, -1):
            if name == self.tagStack[i].name:
                numPops = len(self.tagStack)-i
                break
        if not inclusivePop:
            numPops = numPops - 1

        for i in range(0, numPops):
            mostRecentTag = self.popTag()
        return mostRecentTag    

    def _smartPop(self, name):

        """We need to pop up to the previous tag of this type, unless
        one of this tag's nesting reset triggers comes between this
        tag and the previous tag of this type, OR unless this tag is a
        generic nesting trigger and another generic nesting trigger
        comes between this tag and the previous tag of this type.

        Examples:
         <p>Foo<b>Bar<p> should pop to 'p', not 'b'.
         <p>Foo<table>Bar<p> should pop to 'table', not 'p'.
         <p>Foo<table><tr>Bar<p> should pop to 'tr', not 'p'.
         <p>Foo<b>Bar<p> should pop to 'p', not 'b'.

         <li><ul><li> *<li>* should pop to 'ul', not the first 'li'.
         <tr><table><tr> *<tr>* should pop to 'table', not the first 'tr'
         <td><tr><td> *<td>* should pop to 'tr', not the first 'td'
        """

        nestingResetTriggers = self.NESTABLE_TAGS.get(name)
        isNestable = nestingResetTriggers != None
        isResetNesting = self.RESET_NESTING_TAGS.has_key(name)
        popTo = None
        inclusive = True
        for i in range(len(self.tagStack)-1, 0, -1):
            p = self.tagStack[i]
            if (not p or p.name == name) and not isNestable:
                #Non-nestable tags get popped to the top or to their
                #last occurance.
                popTo = name
                break
            if (nestingResetTriggers != None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers == None and isResetNesting
                    and self.RESET_NESTING_TAGS.has_key(p.name)):
                
                #If we encounter one of the nesting reset triggers
                #peculiar to this tag, or we encounter another tag
                #that causes nesting to reset, pop up to but not
                #including that tag.

                popTo = p.name
                inclusive = False
                break
            p = p.parent
        if popTo:
            self._popToTag(popTo, inclusive)

    def unknown_starttag(self, name, attrs, selfClosing=0):
        #print "Start tag %s" % name
        if self.quoteStack:
            #This is not a real tag.
            #print "<%s> is not real!" % name
            attrs = ''.join(map(lambda(x, y): ' %s="%s"' % (x, y), attrs))
            self.handle_data('<%s%s>' % (name, attrs))
            return
        self.endData()
        if not name in self.SELF_CLOSING_TAGS and not selfClosing:
            self._smartPop(name)
        tag = Tag(name, attrs, self.currentTag, self.previous)        
        if self.previous:
            self.previous.next = tag
        self.previous = tag
        self.pushTag(tag)
        if selfClosing or name in self.SELF_CLOSING_TAGS:
            self.popTag()                
        if name in self.QUOTE_TAGS:
            #print "Beginning quote (%s)" % name
            self.quoteStack.append(name)
            self.literal = 1

    def unknown_endtag(self, name):
        if self.quoteStack and self.quoteStack[-1] != name:
            #This is not a real end tag.
            #print "</%s> is not real!" % name
            self.handle_data('</%s>' % name)
            return
        self.endData()
        self._popToTag(name)
        if self.quoteStack and self.quoteStack[-1] == name:
            self.quoteStack.pop()
            self.literal = (len(self.quoteStack) > 0)

    def handle_data(self, data):
        self.currentData.append(data)

    def handle_pi(self, text):
        "Propagate processing instructions right through."
        self.handle_data("<?%s>" % text)

    def handle_comment(self, text):
        "Propagate comments right through."
        self.handle_data("<!--%s-->" % text)

    def handle_charref(self, ref):
        "Propagate char refs right through."
        self.handle_data('&#%s;' % ref)

    def handle_entityref(self, ref):
        "Propagate entity refs right through."
        self.handle_data('&%s;' % ref)
        
    def handle_decl(self, data):
        "Propagate DOCTYPEs and the like right through."
        self.handle_data('<!%s>' % data)

    def parse_declaration(self, i):
        """Treat a bogus SGML declaration as raw data. Treat a CDATA
        declaration as regular data."""
        j = None
        if self.rawdata[i:i+9] == '<![CDATA[':
             k = self.rawdata.find(']]>', i)
             if k == -1:
                 k = len(self.rawdata)
             self.handle_data(self.rawdata[i+9:k])
             j = k+3
        else:
            try:
                j = SGMLParser.parse_declaration(self, i)
            except SGMLParseError:
                toHandle = self.rawdata[i:]
                self.handle_data(toHandle)
                j = i + len(toHandle)
        return j

class BeautifulSoup(BeautifulStoneSoup):

    """This parser knows the following facts about HTML:

    * Some tags have no closing tag and should be interpreted as being
      closed as soon as they are encountered.

    * The text inside some tags (ie. 'script') may contain tags which
      are not really part of the document and which should be parsed
      as text, not tags. If you want to parse the text as tags, you can
      always fetch it and parse it explicitly.

    * Tag nesting rules:

      Most tags can't be nested at all. For instance, the occurance of
      a <p> tag should implicitly close the previous <p> tag.

       <p>Para1<p>Para2
        should be transformed into:
       <p>Para1</p><p>Para2

      Some tags can be nested arbitrarily. For instance, the occurance
      of a <blockquote> tag should _not_ implicitly close the previous
      <blockquote> tag.

       Alice said: <blockquote>Bob said: <blockquote>Blah
        should NOT be transformed into:
       Alice said: <blockquote>Bob said: </blockquote><blockquote>Blah

      Some tags can be nested, but the nesting is reset by the
      interposition of other tags. For instance, a <tr> tag should
      implicitly close the previous <tr> tag within the same <table>,
      but not close a <tr> tag in another table.

       <table><tr>Blah<tr>Blah
        should be transformed into:
       <table><tr>Blah</tr><tr>Blah
        but,
       <tr>Blah<table><tr>Blah
        should NOT be transformed into
       <tr>Blah<table></tr><tr>Blah

    Differing assumptions about tag nesting rules are a major source
    of problems with the BeautifulSoup class. If BeautifulSoup is not
    treating as nestable a tag your page author treats as nestable,
    try ICantBelieveItsBeautifulSoup before writing your own
    subclass."""

    SELF_CLOSING_TAGS = buildTagMap(None, ['br' , 'hr', 'input', 'img', 'meta',
                                           'spacer', 'link', 'frame', 'base'])

    QUOTE_TAGS = {'script': None}
    
    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ['span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center']

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ['blockquote', 'div', 'fieldset', 'ins', 'del']

    #Lists can contain other lists, but there are restrictions.    
    NESTABLE_LIST_TAGS = { 'ol' : [],
                           'ul' : [],
                           'li' : ['ul', 'ol'],
                           'dl' : [],
                           'dd' : ['dl'],
                           'dt' : ['dl'] }

    #Tables can contain other tables, but there are restrictions.    
    NESTABLE_TABLE_TAGS = {'table' : [], 
                           'tr' : ['table', 'tbody', 'tfoot', 'thead'],
                           'td' : ['tr'],
                           'th' : ['tr'],
                           }

    NON_NESTABLE_BLOCK_TAGS = ['address', 'form', 'p', 'pre']

    #If one of these tags is encountered, all tags up to the next tag of
    #this type are popped.
    RESET_NESTING_TAGS = buildTagMap(None, NESTABLE_BLOCK_TAGS, 'noscript',
                                     NON_NESTABLE_BLOCK_TAGS,
                                     NESTABLE_LIST_TAGS,
                                     NESTABLE_TABLE_TAGS)

    NESTABLE_TAGS = buildTagMap([], NESTABLE_INLINE_TAGS, NESTABLE_BLOCK_TAGS,
                                NESTABLE_LIST_TAGS, NESTABLE_TABLE_TAGS)
    
class ICantBelieveItsBeautifulSoup(BeautifulSoup):

    """The BeautifulSoup class is oriented towards skipping over
    common HTML errors like unclosed tags. However, sometimes it makes
    errors of its own. For instance, consider this fragment:

     <b>Foo<b>Bar</b></b>

    This is perfectly valid (if bizarre) HTML. However, the
    BeautifulSoup class will implicitly close the first b tag when it
    encounters the second 'b'. It will think the author wrote
    "<b>Foo<b>Bar", and didn't close the first 'b' tag, because
    there's no real-world reason to bold something that's already
    bold. When it encounters '</b></b>' it will close two more 'b'
    tags, for a grand total of three tags closed instead of two. This
    can throw off the rest of your document structure. The same is
    true of a number of other tags, listed below.

    It's much more common for someone to forget to close (eg.) a 'b'
    tag than to actually use nested 'b' tags, and the BeautifulSoup
    class handles the common case. This class handles the
    not-co-common case: where you can't believe someone wrote what
    they did, but it's valid HTML and BeautifulSoup screwed up by
    assuming it wouldn't be.

    If this doesn't do what you need, try subclassing this class or
    BeautifulSoup, and providing your own list of NESTABLE_TAGS."""

    I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS = \
     ['em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big']

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ['noscript']

    NESTABLE_TAGS = buildTagMap([], BeautifulSoup.NESTABLE_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS)

class BeautifulSOAP(BeautifulStoneSoup):
    """This class will push a tag with only a single string child into
    the tag's parent as an attribute. The attribute's name is the tag
    name, and the value is the string child. An example should give
    the flavor of the change:

    <foo><bar>baz</bar></foo>
     =>
    <foo bar="baz"><bar>baz</bar></foo>

    You can then access fooTag['bar'] instead of fooTag.barTag.string.

    This is, of course, useful for scraping structures that tend to
    use subelements instead of attributes, such as SOAP messages. Note
    that it modifies its input, so don't print the modified version
    out.

    I'm not sure how many people really want to use this class; let me
    know if you do. Mainly I like the name."""

    def popTag(self):
        if len(self.tagStack) > 1:
            tag = self.tagStack[-1]
            parent = self.tagStack[-2]
            parent._getAttrMap()
            if (isinstance(tag, Tag) and len(tag.contents) == 1 and
                isinstance(tag.contents[0], NavigableText) and 
                not parent.attrMap.has_key(tag.name)):
                parent[tag.name] = tag.contents[0]
        BeautifulStoneSoup.popTag(self)

#Enterprise class names! It has come to our attention that some people
#think the names of the Beautiful Soup parser classes are too silly
#and "unprofessional" for use in enterprise screen-scraping. We feel
#your pain! For such-minded folk, the Beautiful Soup Consortium And
#All-Night Kosher Bakery recommends renaming this file to
#"RobustParser.py" (or, in cases of extreme enterprisitude,
#"RobustParserBeanInterface.class") and using the following
#enterprise-friendly class aliases:
class RobustXMLParser(BeautifulStoneSoup):
    pass
class RobustHTMLParser(BeautifulSoup):
    pass
class RobustWackAssHTMLParser(ICantBelieveItsBeautifulSoup):
    pass
class SimplifyingSOAPParser(BeautifulSOAP):
    pass

###


#By default, act as an HTML pretty-printer.
if __name__ == '__main__':
    import sys
    soup = BeautifulStoneSoup(sys.stdin.read())
    print soup.prettify()

########NEW FILE########
__FILENAME__ = DataCache
import datetime
import time
from google.appengine.ext import db
from models.NewsCache import NewsCacheModel
import AppConfig

#retrieves data by ID
def getData(recordId,format):
	q = NewsCacheModel.all()
	q.filter("rec_id =", recordId)
	q.filter("rec_format =", format)
	q.order("-rec_date")
	results = q.fetch(1)
	return results

#verifies that data hasn't expired
def hasExpired(dataObj):
	if (dataObj):
		dataObjTime = dataObj[0].rec_date
		now = datetime.datetime.now()
		if (dataObjTime + datetime.timedelta(seconds=int(AppConfig.dataExpirationPolicy)) < now):
			return True
		else:
			return False

#stores data	
def putData(recordId, format,data, url, referer, ip):
	d = NewsCacheModel(key_name='%s_%s' % (recordId,format))
	d.rec_id = recordId
	d.rec_xml = data
	d.rec_format = format
	d.rec_url = url
	d.rec_referrer = referer
	d.rec_ip = ip
	d.put()
########NEW FILE########
__FILENAME__ = Formatter


#output the error
def error(format, msg):
    if (format == 'json'):
        return '{"status":"error","message":"%s"}' % msg
    else:
        return '<?xml version="1.0"?><root><status>error</status><message>%s</message></root>' % msg


def dataWrapper(format, returnData, callback):
    if (format == 'json'):
        returnData = '{"items":[%s]}' % returnData.lstrip('[').rstrip('],')
        if (callback):
            return '%s(%s);' % (callback, returnData)
        else:
            return returnData
    else:
        if (not returnData.startswith('<root>')):
            returnData = '<root>' + returnData
        if (not returnData.endswith('</root>')):
            returnData += '</root>'
        return '<?xml version="1.0"?>%s' % returnData


def contentType(format):
    if (format == 'json'):
        return 'application/json; charset=utf-8'
    else:
        return 'application/xml; charset=utf-8'


#output simple string in json|xml format
def data(format, elm, msg):
    if (format == 'json'):
        return '"%s":"%s",' % (elm, msg)
    else:
        return '<%s>%s</%s>' % (elm, msg, elm)


#output complex types in json|xml format
def dataComplex(format, elm, msg):
    if (format == 'json'):
        return '{"%s":[%s]},' % (elm, msg)
    else:
        return '<%s>%s</%s>' % (elm, msg, elm)

########NEW FILE########
__FILENAME__ = GAHelper
import logging
import time
from UserString import MutableString
from google.appengine.api import urlfetch
import AppConfig
import random


def trackGARequests(path, remoteAddr, referer=''):
    logging.debug('trackRSSRequests: calling GA GIF service')

    var_utmac = AppConfig.googleAnalyticsKey  # enter the new urchin code
    var_utmhn = AppConfig.appDomain  # enter your domain
    var_utmn = str(random.randint(1000000000, 9999999999))  # random request number
    var_cookie = str(random.randint(10000000, 99999999))  # random cookie number
    var_random = str(random.randint(1000000000, 2147483647))  # number under 2147483647
    var_today = str(int(time.time()))  # today
    var_referer = referer  # referer url
    var_uservar = '-'  # enter your own user defined variable
    var_utmp = '%s/%s' % (path, remoteAddr)  # this example adds a fake page request to the (fake) rss directory (the viewer IP to check for absolute unique RSS readers)
    #build URL
    urchinUrl = MutableString()
    urchinUrl = 'http://www.google-analytics.com/__utm.gif?utmwv=1&utmn=' + var_utmn
    urchinUrl += '&utmsr=-&utmsc=-&utmul=-&utmje=0&utmfl=-&utmdt=-&utmhn='
    urchinUrl += var_utmhn + '&utmr=' + var_referer + '&utmp=' + var_utmp
    urchinUrl += '&utmac=' + var_utmac + '&utmcc=__utma%3D' + var_cookie
    urchinUrl += '.' + var_random + '.' + var_today + '.' + var_today + '.'
    urchinUrl += var_today + '.2%3B%2B__utmb%3D' + var_cookie
    urchinUrl += '%3B%2B__utmc%3D' + var_cookie + '%3B%2B__utmz%3D' + var_cookie
    urchinUrl += '.' + var_today
    urchinUrl += '.2.2.utmccn%3D(direct)%7Cutmcsr%3D(direct)%7Cutmcmd%3D(none)%3B%2B__utmv%3D'
    urchinUrl += var_cookie + '.' + var_uservar + '%3B'

    #async request to GA's GIF service
    rpcGA = None
    try:
        rpcGA = urlfetch.create_rpc()
        urlfetch.make_fetch_call(rpcGA, urchinUrl)
    except Exception, exT:
        logging.error('trackRSSRequests: Errors calling GA GIF service : %s' % exT)

    #validate request
    if (rpcGA):
        try:
            result = rpcGA.get_result()
            if (result and result.status_code == 200):
                logging.debug('trackRSSRequests: GA logged successfully')
        except Exception, ex:
            logging.error('trackRSSRequests: Errors : %s' % ex)

########NEW FILE########
__FILENAME__ = GetHNAskHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns ask HN data in JSON or XML using HTML Parser
# Gleb Popov. September 2011
#

import os
from google.appengine.ext import webapp
import Formatter
import GAHelper
import APIContent


class HackerNewsAskHandler(webapp.RequestHandler):

    #controller main entry
    def get(self, format='json', page=''):
        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)

        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        returnData = APIContent.getHackerNewsAskContent(page, format, self.request.url, referer, self.request.remote_addr)
        if (not returnData or returnData == None or returnData == '' or returnData == 'None'):
            #call the service again this time without the pageID
            returnData = APIContent.getHackerNewsAskContent('', format, self.request.url, referer, self.request.remote_addr)

        #track this request
        GAHelper.trackGARequests('/ask', self.request.remote_addr, referer)

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNBestHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns best articles in JSON or XML using HTML Parser
# Gleb Popov. September 2011
#

import os
from google.appengine.ext import webapp
import Formatter
import GAHelper
import APIContent


class HackerNewsBestHandler(webapp.RequestHandler):

    #controller main entry
    def get(self, format='json', page=''):
        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)

        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        returnData = APIContent.getHackerNewsBestContent(page, format, self.request.url, referer, self.request.remote_addr)
        if (not returnData or returnData == None or returnData == '' or returnData == 'None'):
            #call the service again this time without the pageID
            returnData = APIContent.getHackerNewsBestContent('', format, self.request.url, referer, self.request.remote_addr)

        #track this request
        GAHelper.trackGARequests('/best', self.request.remote_addr, referer)

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNCommentsHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns comments for a given post id in JSON or XML using HTML Parser
# Gleb Popov. September 2011
#

import os
from google.appengine.ext import webapp
import Formatter
import GAHelper
import APIContent


class HackerNewsCommentsHandler(webapp.RequestHandler):

    #controller main entry
    def get(self, format, id):
        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)

        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        returnData = APIContent.getHackerNewsComments(id, format, self.request.url, referer, self.request.remote_addr)

        #track this request
        GAHelper.trackGARequests('/comments/%s' % (id), self.request.remote_addr, referer)

        if (not returnData):
            returnData = ''

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNLatestHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns latest stories in JSON or XML using HTML Parser
# Gleb Popov. September 2011
#

import os
from google.appengine.ext import webapp
import Formatter
import GAHelper
import APIContent


class HackerNewsLatestPageHandler(webapp.RequestHandler):

    # controller main entry
    def get(self, format='json', limit=1):
        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)

        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        returnData = APIContent.getHackerNewsLatestContent('', format, self.request.url, referer, self.request.remote_addr, limit)

        #track this request
        GAHelper.trackGARequests('/latest', self.request.remote_addr, referer)

        if (not returnData):
            returnData = ''

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNNestedCommentsHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns nested comments for a given post id in JSON or XML using HTML Parser
#

import os
from google.appengine.ext import webapp
import Formatter
import GAHelper
import APIContent


class HackerNewsNestedCommentsHandler(webapp.RequestHandler):

    #controller main entry
    def get(self, format, id):
        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)

        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        returnData = APIContent.getHackerNewsNestedComments(id, format, self.request.url, referer, self.request.remote_addr)

        #track this request
        GAHelper.trackGARequests('/nestedcomments/%s' % (id), self.request.remote_addr, referer)

        if (not returnData):
            returnData = ''

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNNewestHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns newest articles in JSON or XML using HTML Parser
# Gleb Popov. September 2011
#

import os
from google.appengine.ext import webapp
import Formatter
import GAHelper
import APIContent


class HackerNewsNewestHandler(webapp.RequestHandler):

    #controller main entry
    def get(self, format='json', page=''):
        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)

        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        returnData = APIContent.getHackerNewsNewestContent(page, format, self.request.url, referer, self.request.remote_addr)
        if (not returnData or returnData == None or returnData == '' or returnData == 'None'):
            #call the service again this time without the pageID
            returnData = APIContent.getHackerNewsNewestContent('', format, self.request.url, referer, self.request.remote_addr)

        #track this request
        GAHelper.trackGARequests('/newest', self.request.remote_addr, referer)

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNPageContentHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns homepage news in JSON or XML using HTML Parser
# Gleb Popov. September 2011
#

import os
from google.appengine.ext import webapp
import Formatter
import GAHelper
import APIContent


class HackerNewsPageHandler(webapp.RequestHandler):

    #controller main entry
    def get(self, format='json', page=''):
        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)

        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        returnData = APIContent.getHackerNewsPageContent(page, format, self.request.url, referer, self.request.remote_addr)

        if (not returnData or returnData == None or returnData == '' or returnData == 'None'):
            #call the service again this time without the pageID
            returnData = APIContent.getHackerNewsPageContent('', format, self.request.url, referer, self.request.remote_addr)

        #track this request
        GAHelper.trackGARequests('/news', self.request.remote_addr, referer)

        if (not returnData):
            returnData = ''

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNPostHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns post data by ID
#

import os
import re
import logging
import datetime
import time
from UserString import MutableString
from google.appengine.api import urlfetch
from google.appengine.ext import webapp 
from google.appengine.ext import db
from google.appengine.ext.webapp import util
import Formatter
import AppConfig
import GAHelper
from xml.sax.saxutils import escape
import APIContent
import GAHelper
from BeautifulSoup import BeautifulSoup

class HackerNewsPostHandler(webapp.RequestHandler):
	
	#controller main entry		
	def get(self,format,id):
		#set content-type
		self.response.headers['Content-Type'] = Formatter.contentType(format)
		
		#get consumer/client app id
		appid = 'Unknown'
		if (self.request.GET):
			if ('appid' in self.request.GET):
				appid = self.request.GET['appid']
			if ('app' in self.request.GET):
				appid = self.request.GET['app']
		
		referer = ''
		if ('HTTP_REFERER' in os.environ):
			referer = os.environ['HTTP_REFERER']
		
		returnData = APIContent.getHackerNewsPost(id,format,self.request.url, referer, self.request.remote_addr)
			
		#track this request
		GAHelper.trackGARequests('/post/%s' % (id), appid, referer)
		
		if (not returnData):
			returnData = ''
		
		#output to the browser
		self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNRSSHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns RSS feed from the HN website in JSON or XML
# Gleb Popov. September 2011
#

import os
from google.appengine.ext import webapp
from UserString import MutableString
import Formatter
import GAHelper
import APIContent


class HackerNewsRSSHandler(webapp.RequestHandler):
    #controller main entry
    def get(self, format='json'):
        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)

        returnData = MutableString()
        returnData = APIContent.getHackerNewsRSS(format)

        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        #track this request
        GAHelper.trackGARequests('/rss', self.request.remote_addr, referer)

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNSecondPageHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns homepage news in JSON or XML using HTML Parser
# Gleb Popov. September 2011
#

import os
from google.appengine.ext import webapp
import Formatter
import GAHelper
import APIContent


class HackerNewsSecondPageHandler(webapp.RequestHandler):

    #controller main entry
    def get(self, format='json', page=''):

        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)
        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        returnData = APIContent.getHackerNewsSecondPageContent(page, format, self.request.url, referer, self.request.remote_addr)
        if (not returnData or returnData == None or returnData == '' or returnData == 'None'):
            #call the service again
            returnData = APIContent.getHackerNewsSecondPageContent(page, format, self.request.url, referer, self.request.remote_addr)

        #track this request
        GAHelper.trackGARequests('/news2', self.request.remote_addr, referer)

        if (not returnData):
            returnData = ''

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = GetHNSubmittedHandler
#!/usr/bin/env python
#
# Hacker News Droid API: returns user submitted content by username in JSON or XML using HTML Parser
# Gleb Popov. September 2011
#

import os
from google.appengine.ext import webapp
import Formatter
import GAHelper
import APIContent


class HackerNewsSubmittedHandler(webapp.RequestHandler):
    #controller main entry
    def get(self, format, user):
        #set content-type
        self.response.headers['Content-Type'] = Formatter.contentType(format)

        referer = ''
        if ('HTTP_REFERER' in os.environ):
            referer = os.environ['HTTP_REFERER']

        returnData = APIContent.getHackerNewsSubmittedContent(user, format, self.request.url, referer, self.request.remote_addr)

        #track this request
        GAHelper.trackGARequests('/submitted/%s' % (user), self.request.remote_addr, referer)

        if (not returnData):
            returnData = ''

        #output to the browser
        self.response.out.write(Formatter.dataWrapper(format, returnData, self.request.get('callback')))

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#
# Hacker News API for Droid
# Gleb Popov. September 2011
#
import os
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from GetHNRSSHandler import HackerNewsRSSHandler
from GetHNSecondPageHandler import HackerNewsSecondPageHandler
from GetHNPageContentHandler import HackerNewsPageHandler
from GetHNNewestHandler import HackerNewsNewestHandler
from GetHNBestHandler import HackerNewsBestHandler
from GetHNAskHandler import HackerNewsAskHandler
from GetHNSubmittedHandler import HackerNewsSubmittedHandler
from GetHNCommentsHandler import HackerNewsCommentsHandler
from GetHNNestedCommentsHandler import HackerNewsNestedCommentsHandler
from GetHNLatestHandler import HackerNewsLatestPageHandler
from SandboxController import HackerNewsSandboxHandler
from GetHNPostHandler import HackerNewsPostHandler

class MainHandler(webapp.RequestHandler):
    def get(self):
		template_values = {'last_updated': '01/04/12'}
		path = os.path.join(os.path.dirname(__file__), 'templates')
		path = os.path.join(path, 'index.html')
		self.response.out.write(template.render(path, template_values))


def main():
    application = webapp.WSGIApplication([('/', MainHandler),
										 (r'/rss/format/(json|xml)', HackerNewsRSSHandler),
										 ('/rss', HackerNewsRSSHandler),
										 ('/sandbox', HackerNewsSandboxHandler),
										 ('/latest', HackerNewsLatestPageHandler),
										 ('/latest/format/(json|xml)/limit/(.*)', HackerNewsLatestPageHandler),
										 ('/news', HackerNewsPageHandler),
										 ('/news2', HackerNewsSecondPageHandler),
										 ('/news/format/(json|xml)', HackerNewsPageHandler),
										 ('/news2/format/(json|xml)', HackerNewsPageHandler),
										 (r'/news/format/(json|xml)/page/(.*)', HackerNewsPageHandler),
										 (r'/news2/format/(json|xml)/page/(.*)', HackerNewsPageHandler),
										 ('/newest', HackerNewsNewestHandler),
										 ('/newest/format/(json|xml)', HackerNewsNewestHandler),
										 (r'/newest/format/(json|xml)/page/(.*)', HackerNewsNewestHandler),
										 ('/best', HackerNewsBestHandler),
										 ('/best/format/(json|xml)', HackerNewsBestHandler),
										 (r'/best/format/(json|xml)/page/(.*)', HackerNewsBestHandler),
										 ('/ask', HackerNewsAskHandler),
										 ('/ask/format/(json|xml)', HackerNewsAskHandler),
										 (r'/ask/format/(json|xml)/page/(.*)', HackerNewsAskHandler),
										 (r'/submitted/format/(json|xml)/user/(.*)', HackerNewsSubmittedHandler),
										 (r'/comments/format/(json|xml)/id/(.*)', HackerNewsCommentsHandler),
										 (r'/nestedcomments/format/(json|xml)/id/(.*)', HackerNewsNestedCommentsHandler),
										 (r'/post/format/(json|xml)/id/(.*)', HackerNewsPostHandler)
										],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = NewsCache
import logging
from google.appengine.ext import db

class NewsCacheModel(db.Model):
	rec_date = db.DateTimeProperty(auto_now_add=True)
	rec_id = db.StringProperty()
	rec_xml = db.TextProperty()
	rec_url = db.StringProperty()
	rec_referrer = db.StringProperty()
	rec_ip = db.StringProperty()
	rec_format = db.StringProperty()
	

########NEW FILE########
__FILENAME__ = SandboxController
#!/usr/bin/env python
#
# Hacker News Droid API: returns best articles in JSON or XML using HTML Parser
# Gleb Popov. September 2011
#

import os
import re
import logging
from UserString import MutableString
from django.utils import simplejson
from google.appengine.ext import webapp 
from google.appengine.ext import db
from google.appengine.ext.webapp import util
import Formatter
import AppConfig
import GAHelper
from xml.sax.saxutils import escape
import APIUtils
import GAHelper
from BeautifulSoup import BeautifulSoup
from google.appengine.api import urlfetch

class HackerNewsSandboxHandler(webapp.RequestHandler):
	def get(self):
		try:
			result = urlfetch.fetch(url=AppConfig.hackerNewsURL, deadline=30)
			self.response.out.write(result.status_code)
			self.response.out.write(result.content)
		except:
			self.response.out.write('unable to get data')
########NEW FILE########
__FILENAME__ = structured
# encoding: utf-8

"""
structured.py - handle structured data/dicts/objects
"""

# Created by Maximillian Dornseif on 2009-12-27.
# Created by Maximillian Dornseif on 2010-06-04.
# Copyright (c) 2009, 2010, 2011 HUDORA. All rights reserved.


import xml.etree.cElementTree as ET


# Basic conversation goal here is converting a dict to an object allowing
# more comfortable access. `Struct()` and `make_struct()` are used to archive
# this goal.
# See http://stackoverflow.com/questions/1305532/convert-python-dict-to-object for the inital Idea
#
# The reasoning for this is the observation that we ferry arround hundreds of dicts via JSON
# and accessing them as `obj['key']` is tiresome after some time. `obj.key` is much nicer.
class Struct(object):
    """Emulate a cross over between a dict() and an object()."""
    def __init__(self, entries, default=None, nodefault=False):
        # ensure all keys are strings and nothing else
        entries = dict([(str(x), y) for x, y in entries.items()])
        self.__dict__.update(entries)
        self.__default = default
        self.__nodefault = nodefault

    def __getattr__(self, name):
        """Emulate Object access.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.a
        'b'
        >>> obj.foobar
        'c'

        `hasattr` results in strange behaviour if you give a default value. This might change in the future.
        >>> hasattr(obj, 'a')
        True
        >>> hasattr(obj, 'foobar')
        True
        """
        if name.startswith('_'):
            # copy expects __deepcopy__, __getnewargs__ to raise AttributeError
            # see http://groups.google.com/group/comp.lang.python/browse_thread/thread/6ac8a11de4e2526f/
            # e76b9fbb1b2ee171?#e76b9fbb1b2ee171
            raise AttributeError("'<Struct>' object has no attribute '%s'" % name)
        if self.__nodefault:
            raise AttributeError("'<Struct>' object has no attribute '%s'" % name)
        return self.__default

    def __getitem__(self, key):
        """Emulate dict like access.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj['a']
        'b'

        While the standard dict access via [key] uses the default given when creating the struct,
        access via get(), results in None for keys not set. This might be considered a bug and
        should change in the future.
        >>> obj['foobar']
        'c'
        >>> obj.get('foobar')
        'c'
        """
        # warnings.warn("dict_accss[foo] on a Struct, use object_access.foo instead",
        #                DeprecationWarning, stacklevel=2)
        if self.__nodefault:
            return self.__dict__[key]
        return self.__dict__.get(key, self.__default)

    def get(self, key, default=None):
        """Emulate dictionary access.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.get('a')
        'b'
        >>> obj.get('foobar')
        'c'
        """
        if key in self.__dict__:
            return self.__dict__[key]
        if not self.__nodefault:
            return self.__default
        return default

    def __contains__(self, item):
        """Emulate dict 'in' functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> 'a' in obj
        True
        >>> 'foobar' in obj
        False
        """
        return item in self.__dict__

    def __nonzero__(self):
        """Returns whether the instance evaluates to False"""
        return bool(self.items())

    def has_key(self, item):
        """Emulate dict.has_key() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.has_key('a')
        True
        >>> obj.has_key('foobar')
        False
        """
        return item in self

    def items(self):
        """Emulate dict.items() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.items()
        [('a', 'b')]
        """
        return [(k, v) for (k, v) in self.__dict__.items() if not k.startswith('_Struct__')]

    def keys(self):
        """Emulate dict.keys() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.keys()
        ['a']
        """
        return [k for (k, _v) in self.__dict__.items() if not k.startswith('_Struct__')]

    def values(self):
        """Emulate dict.values() functionality.

        >>> obj = Struct({'a': 'b'}, default='c')
        >>> obj.values()
        ['b']
        """
        return [v for (k, v) in self.__dict__.items() if not k.startswith('_Struct__')]

    def __repr__(self):
        return "<Struct: %r>" % dict(self.items())


def make_struct(obj, default=None, nodefault=False):
    """Converts a dict to an object, leaves objects untouched.

    Someting like obj.vars() = dict() - Read Only!

    >>> obj = make_struct(dict(foo='bar'))
    >>> obj.foo
    'bar'

    `make_struct` leaves objects alone.
    >>> class MyObj(object): pass
    >>> data = MyObj()
    >>> data.foo = 'bar'
    >>> obj = make_struct(data)
    >>> obj.foo
    'bar'

    `make_struct` also is idempotent
    >>> obj = make_struct(make_struct(dict(foo='bar')))
    >>> obj.foo
    'bar'

    `make_struct` recursively handles dicts and lists of dicts
    >>> obj = make_struct(dict(foo=dict(bar='baz')))
    >>> obj.foo.bar
    'baz'

    >>> obj = make_struct([dict(foo='baz')])
    >>> obj
    [<Struct: {'foo': 'baz'}>]
    >>> obj[0].foo
    'baz'

    >>> obj = make_struct(dict(foo=dict(bar=dict(baz='end'))))
    >>> obj.foo.bar.baz
    'end'

    >>> obj = make_struct(dict(foo=[dict(bar='baz')]))
    >>> obj.foo[0].bar
    'baz'
    >>> obj.items()
    [('foo', [<Struct: {'bar': 'baz'}>])]
    """
    if type(obj) == type(Struct):
        return obj
    if (not hasattr(obj, '__dict__')) and hasattr(obj, 'iterkeys'):
        # this should be a dict
        struc = Struct(obj, default, nodefault)
        # handle recursive sub-dicts
        for key, val in obj.items():
            setattr(struc, key, make_struct(val, default, nodefault))
        return struc
    elif hasattr(obj, '__delslice__') and hasattr(obj, '__getitem__'):
        #
        return [make_struct(v, default, nodefault) for v in obj]
    else:
        return obj


# Code is based on http://code.activestate.com/recipes/573463/
def _convert_dict_to_xml_recurse(parent, dictitem, listnames):
    """Helper Function for XML conversion."""
    # we can't convert bare lists
    assert not isinstance(dictitem, list)

    if isinstance(dictitem, dict):
        for (tag, child) in sorted(dictitem.iteritems()):
            if isinstance(child, list):
                # iterate through the array and convert
                listelem = ET.Element(tag)
                parent.append(listelem)
                for listchild in child:
                    elem = ET.Element(listnames.get(tag, 'item'))
                    listelem.append(elem)
                    _convert_dict_to_xml_recurse(elem, listchild, listnames)
            else:
                elem = ET.Element(tag)
                parent.append(elem)
                _convert_dict_to_xml_recurse(elem, child, listnames)
    elif not dictitem is None:
        parent.text = unicode(dictitem)


def dict2et(xmldict, roottag='data', listnames=None):
    """Converts a dict to an Elementtree.

    Converts a dictionary to an XML ElementTree Element::

    >>> data = {"nr": "xq12", "positionen": [{"m": 12}, {"m": 2}]}
    >>> root = dict2et(data)
    >>> ET.tostring(root)
    '<data><nr>xq12</nr><positionen><item><m>12</m></item><item><m>2</m></item></positionen></data>'

    Per default ecerything ins put in an enclosing '<data>' element. Also per default lists are converted
    to collecitons of `<item>` elements. But by provding a mapping between list names and element names,
    you van generate different elements::

    >>> data = {"positionen": [{"m": 12}, {"m": 2}]}
    >>> root = dict2et(data, roottag='xml')
    >>> ET.tostring(root)
    '<xml><positionen><item><m>12</m></item><item><m>2</m></item></positionen></xml>'

    >>> root = dict2et(data, roottag='xml', listnames={'positionen': 'position'})
    >>> ET.tostring(root)
    '<xml><positionen><position><m>12</m></position><position><m>2</m></position></positionen></xml>'

    >>> data = {"kommiauftragsnr":2103839, "anliefertermin":"2009-11-25", "prioritaet": 7,
    ... "ort": u"Hücksenwagen",
    ... "positionen": [{"menge": 12, "artnr": "14640/XL", "posnr": 1},],
    ... "versandeinweisungen": [{"guid": "2103839-XalE", "bezeichner": "avisierung48h",
    ...                          "anweisung": "48h vor Anlieferung unter 0900-LOGISTIK avisieren"},
    ... ]}

    >>> print ET.tostring(dict2et(data, 'kommiauftrag',
    ... listnames={'positionen': 'position', 'versandeinweisungen': 'versandeinweisung'}))
    ...  # doctest: +SKIP
    '''<kommiauftrag>
    <anliefertermin>2009-11-25</anliefertermin>
    <positionen>
        <position>
            <posnr>1</posnr>
            <menge>12</menge>
            <artnr>14640/XL</artnr>
        </position>
    </positionen>
    <ort>H&#xC3;&#xBC;cksenwagen</ort>
    <versandeinweisungen>
        <versandeinweisung>
            <bezeichner>avisierung48h</bezeichner>
            <anweisung>48h vor Anlieferung unter 0900-LOGISTIK avisieren</anweisung>
            <guid>2103839-XalE</guid>
        </versandeinweisung>
    </versandeinweisungen>
    <prioritaet>7</prioritaet>
    <kommiauftragsnr>2103839</kommiauftragsnr>
    </kommiauftrag>'''
    """

    if not listnames:
        listnames = {}
    root = ET.Element(roottag)
    _convert_dict_to_xml_recurse(root, xmldict, listnames)
    return root


def list2et(xmllist, root, elementname, listnames={}):
    """Converts a list to an Elementtree.

        See also dict2et()
    """

    listnames[root] = elementname
    basexml = dict2et({root: xmllist}, 'xml', listnames)
    return basexml.find(root)


def dict2xml(datadict, roottag='data', listnames=None, pretty=False):
    """Converts a dictionary to an UTF-8 encoded XML string.

    See also dict2et()
    """
    tree = dict2et(datadict, roottag, listnames)
    if pretty:
        indent(tree)
    return ET.tostring(tree, 'utf-8')


def list2xml(datalist, root, elementname, listnames=None, pretty=False):
    """Converts a list to an UTF-8 encoded XML string.

    See also dict2et()
    """
    tree = list2et(datalist, root, elementname, listnames)
    if pretty:
        indent(tree)
    return ET.tostring(tree, 'utf-8')


# From http://effbot.org/zone/element-lib.htm
# prettyprint: Prints a tree with each node indented according to its depth. This is
# done by first indenting the tree (see below), and then serializing it as usual.
# indent: Adds whitespace to the tree, so that saving it as usual results in a prettyprinted tree.
# in-place prettyprint formatter

def indent(elem, level=0):
    """XML prettyprint: Prints a tree with each node indented according to its depth."""
    i = "\n" + level * " "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + " "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent(child, level + 1)
        if child:
            if not child.tail or not child.tail.strip():
                child.tail = i
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def test():
    """Simple selftest."""
    # warenzugang
    data = {"guid": "3104247-7",
            "menge": 7,
            "artnr": "14695",
            "batchnr": "3104247"}
    xmlstr = dict2xml(data, roottag='warenzugang')
    #print xmlstr
    assert xmlstr == ('<warenzugang><artnr>14695</artnr><batchnr>3104247</batchnr><guid>3104247-7</guid>'
                      '<menge>7</menge></warenzugang>')

    data = {"kommiauftragsnr": 2103839,
     "anliefertermin": "2009-11-25",
     "fixtermin": True,
     "prioritaet": 7,
     "info_kunde": "Besuch H. Gerlach",
     "auftragsnr": 1025575,
     "kundenname": "Ute Zweihaus 400424990",
     "kundennr": "21548",
     "name1": "Uwe Zweihaus",
     "name2": "400424990",
     "name3": "",
     u"strasse": u"Bahnhofstr. 2",
     "land": "DE",
     "plz": "42499",
     "ort": u"Hücksenwagen",
     "positionen": [{"menge": 12,
                     "artnr": "14640/XL",
                     "posnr": 1},
                    {"menge": 4,
                     "artnr": "14640/03",
                     "posnr": 2},
                    {"menge": 2,
                     "artnr": "10105",
                     "posnr": 3}],
     "versandeinweisungen": [{"guid": "2103839-XalE",
                              "bezeichner": "avisierung48h",
                              "anweisung": "48h vor Anlieferung unter 0900-LOGISTIK avisieren"},
                             {"guid": "2103839-GuTi",
                              "bezeichner": "abpackern140",
                              "anweisung": u"Paletten höchstens auf 140 cm Packen"}]
    }

    xmlstr = dict2xml(data, roottag='kommiauftrag')
    # print xmlstr

    # Rückmeldung
    data = {"kommiauftragsnr": 2103839,
     "positionen": [{"menge": 4,
                     "artnr": "14640/XL",
                     "posnr": 1,
                     "nve": "23455326543222553"},
                    {"menge": 8,
                     "artnr": "14640/XL",
                     "posnr": 1,
                     "nve": "43255634634653546"},
                    {"menge": 4,
                     "artnr": "14640/03",
                     "posnr": 2,
                     "nve": "43255634634653546"},
                    {"menge": 2,
                     "artnr": "10105",
                     "posnr": 3,
                     "nve": "23455326543222553"}],
     "nves": [{"nve": "23455326543222553",
               "gewicht": 28256,
               "art": "paket"},
              {"nve": "43255634634653546",
               "gewicht": 28256,
                "art": "paket"}]}

    xmlstr = dict2xml(data, roottag='rueckmeldung')
    #print xmlstr


if __name__ == '__main__':
    import doctest
    import sys
    failure_count, test_count = doctest.testmod()
    d = make_struct({
        'item1': 'string',
        'item2': ['dies', 'ist', 'eine', 'liste'],
        'item3': dict(dies=1, ist=2, ein=3, dict=4),
        'item4': 10,
        'item5': [dict(dict=1, in_einer=2, liste=3)]})
    test()
    sys.exit(failure_count)

########NEW FILE########
