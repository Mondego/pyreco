
import json 
import requests
import time
from requests.auth import HTTPBasicAuth

PER_PAGE_COUNT = 100
LANGUAGE = 'Python'
GITHUB_MAX_RESULTS = 1000
INITIAL_STAR_COUNT = 5
REQUEST_LIMIT = 30
MAX_NEEDED_RESULTS = 60000
requestCounter = 0


username = "emma_happy_2011@hotmail.com"
password = "123abc!@#"


def pageResultsFetcher(starCountOp, starCount, pageNum):

	global requestCounter,username,password 

	queryDict = { 
		'language' : LANGUAGE,
		'stars' : starCountOp+str(starCount),
		'size': '>=10',
		'fork' : 'false'
	}

	def querySerializer(qDict):
		queryChunks = ''
		for key, value in qDict.items():
			queryChunks += ("%s:%s" % (key, value))+' '
		return queryChunks.rstrip()

	paramDict = {
		'q' : querySerializer(queryDict),
		'per_page' : str(PER_PAGE_COUNT),
		'sort' : 'stars',
		'order' : 'desc',
		'page' : pageNum,
	}

	if(requestCounter == REQUEST_LIMIT):
		requestCounter = 0
		time.sleep(60)

	requestCounter += 1
	r = requests.get('https://api.github.com/search/repositories',params=paramDict, auth=HTTPBasicAuth(username,password))

	print r.url
	if(r.ok):
		results = json.loads(r.text)
		return results	
	else:
		print "ERROR: Can't fetch results."
		print "URL: "+r.url
		exit(1)

initialResults = pageResultsFetcher('>=', INITIAL_STAR_COUNT, 1)

print initialResults["incomplete_results"]

HIGHEST_STAR_COUNT = initialResults["items"][0]["watchers_count"]

if(initialResults["total_count"] <= PER_PAGE_COUNT):
	dumpProjectMetaData(initialResults["items"])
else:
	resultsCounter = PER_PAGE_COUNT
	resultsDict = initialResults["items"]
	starCount = HIGHEST_STAR_COUNT
	resultPageNumber = 2
	starCountList = []
	blockCounter = PER_PAGE_COUNT
	while(resultsCounter < MAX_NEEDED_RESULTS and starCount > INITIAL_STAR_COUNT):
		pageResults = pageResultsFetcher('<=', starCount, resultPageNumber)
		#print pageResults['incomplete_results']
		resultsDict.extend(pageResults["items"])
		resultsCounter += len(pageResults["items"])
		resultPageNumber += 1
		blockCounter += PER_PAGE_COUNT
		print resultsCounter
		if(blockCounter%GITHUB_MAX_RESULTS == 0):
			starCount = int(pageResults["items"][-1]["watchers_count"])
			while(resultsDict[-1]["watchers_count"] == starCount):
				del resultsDict[-1]
				resultsCounter -= 1
			starCountList.append(starCount)
			resultPageNumber = 1

with open('projects_meta_data.json', 'w') as outfile:
  json.dump(resultsDict, outfile)
  outfile.close()

print(len(resultsDict))
print starCountList