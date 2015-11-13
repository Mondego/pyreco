__FILENAME__ = build_hashes
import sys
import json

spamtokens = {}
notspamtokens = {}
probabilities = {}

spam_count = 0
notspam_count = 0

print 'building dictionaries...'
f = open('spam', 'r')
for line in f:
  tokens = line.split()
  for token in tokens:
    if token == "bbSEP":
      spam_count = spam_count + 1
      continue
    token = token.lower()
    if token in spamtokens:
      spamtokens[token] = spamtokens[token] + 1
    else:
      spamtokens[token] = 1

f.close()

f = open('notspam', 'r')
for line in f:
  tokens = line.split()
  for token in tokens:
    if token == "bbSEP":
      notspam_count = notspam_count + 1
    token = token.lower()
    if token in notspamtokens:
      notspamtokens[token] = notspamtokens[token] + 1
    else:
      notspamtokens[token] = 1

f.close()


for k in spamtokens:
  num_in_spam = spamtokens[k]
  if k in notspamtokens:
    num_in_notspam = notspamtokens[k] * 2
  else:
    num_in_notspam = 0
  p = ( num_in_spam / float(spam_count)) / ( (num_in_spam / float(spam_count)) + (num_in_notspam / float(notspam_count)))
  probabilities[k] = p

for k in notspamtokens:
  if not (k in spamtokens):
    probabilities[k] = 0

print "saving dictionaries as json..."
# save the hashes as json
f = open('spam.dict.json', 'w')
f.write(json.dumps(spamtokens))
f.close()

f = open('notspam.dict.json', 'w')
f.write(json.dumps(notspamtokens))
f.close()

f = open('probabilities.dict.json', 'w')
f.write(json.dumps(probabilities))
f.close()
########NEW FILE########
__FILENAME__ = scrape_comments
import urllib
import urllib2
from xml.dom import minidom

data = None
headers = {   
    'GData-Version' : 2
}

spamfile = open('spam', 'w')
notspamfile = open('notspam', 'w')

# get list of most popular videos
url = 'http://gdata.youtube.com/feeds/api/videos?max-results=50&orderby=viewCount'
req = urllib2.Request(url, data, headers)
response = urllib2.urlopen(req)
xmldata = response.read()
videos = minidom.parseString(xmldata)
video_entries = videos.getElementsByTagName("gd:feedLink")
for entry in video_entries:
  link = entry.attributes["href"].value
  print "processing: " + link
# get comments
  start = 1
  while start<=1000:
    url = link + '?max-results=50&start-index=' + str(start)

    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    xmldata = response.read()
    comments = minidom.parseString(xmldata)

    entries = comments.getElementsByTagName("entry")

    for entry in entries:
      content = entry.getElementsByTagName("content")
      spam = entry.getElementsByTagName("yt:spam")
      if len(spam) > 0:
        spamfile.write(content[0].firstChild.nodeValue.encode('utf8'))
        spamfile.write('\nbbSEP\n')
      else:
        notspamfile.write(content[0].firstChild.nodeValue.encode('utf8'))
        notspamfile.write('\nbbSEP\n')
    start += 50

spam.close()
notspam.close()
########NEW FILE########
__FILENAME__ = spamcheck
#!/usr/bin/python

import sys
import json

def sort_func(x):
  return abs(token_probs[x] - 0.5)

f = open('probabilities.dict.json', 'r')
json_probs = f.read()
probabilities = json.loads(json_probs)
f.close()


comment = sys.stdin.read()

token_probs = {}
tokens = comment.split()
for token in tokens:
  token = token.lower()
  if token in probabilities:
    token_probs[token] = probabilities[token]
  else:
    token_probs[token] = 0.4


# sort token probabilities by distance from .5
# and pull out the top X ones to use to calculate total probability
max_tokens = 10
interesting_tokens = []
c=0
for w in sorted(token_probs, key=sort_func, reverse=True):
  interesting_tokens.append(token_probs[w])
  if c >= max_tokens:
    break
  c = c+1

# calculate real probabilitiy
a=1
b=1
for token in interesting_tokens:
  a = a * token
  b = b * (1-token)
if a + b == 0:
  print "0"
  sys.exit()
spam_probability = a / ( a + b)
print spam_probability



########NEW FILE########
__FILENAME__ = testit
import urllib
import urllib2
import subprocess
from xml.dom import minidom

data = None
headers = {   
    'GData-Version' : 2
}
num_spam = 0
num_notspam = 0 
num_marked_as_spam = 0
num_marked_as_notspam = 0
false_positives = 0
false_negatives = 0

# get list of most popular videos
url = 'http://gdata.youtube.com/feeds/api/videos?max-results=2&start-index=50&orderby=viewCount'
req = urllib2.Request(url, data, headers)
response = urllib2.urlopen(req)
xmldata = response.read()
videos = minidom.parseString(xmldata)
video_entries = videos.getElementsByTagName("gd:feedLink")
for entry in video_entries:
  link = entry.attributes["href"].value
  print "processing: " + link
# get comments
  start = 1
  while start<=1000:
    url = link + '?max-results=50&start-index=' + str(start)

    req = urllib2.Request(url, data, headers)
    response = urllib2.urlopen(req)
    xmldata = response.read()
    comments = minidom.parseString(xmldata)

    entries = comments.getElementsByTagName("entry")

    for entry in entries:
      content = entry.getElementsByTagName("content")

      comment_string = content[0].firstChild.nodeValue.encode('utf8')
      print "checking: " + comment_string
      # get content score
      p = subprocess.Popen("./spamcheck.py", stdin=subprocess.PIPE, stdout=subprocess.PIPE)
      p.stdin.write(comment_string)
      p.stdin.close()
      score = float(p.stdout.readline())
      p.kill()
      print "score: " + str(score)
      if score >= 0.9:
        num_marked_as_spam = num_marked_as_spam + 1
      else:
        num_marked_as_notspam = num_marked_as_notspam + 1

      spam = entry.getElementsByTagName("yt:spam")
      if len(spam) > 0:
        if score < 0.9:
          false_negatives = false_negatives + 1
        num_spam = num_spam + 1
      else:
        if score >= 0.9:
          false_positives = false_positives + 1
        num_notspam = num_notspam + 1
        
    start += 50

print "total comments: " +  str(num_spam + num_notspam)
print "Spams: " + str(num_spam)
print "Not spams: " + str(num_notspam)
print "Marked as spam: " + str(num_marked_as_spam)
print "Marked as notspam: " + str(num_marked_as_notspam)
print "False positives: " + str(false_positives)
print "False negatives: " + str(false_negatives)

########NEW FILE########
