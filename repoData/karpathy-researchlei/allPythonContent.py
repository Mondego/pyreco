__FILENAME__ = addpaper
# adds paper to database

# usage: python addpaper.py [name|id] [query|id]
# examples:
# python addpaper.py name title of a nice paper
# python addpaper.py id 31415926535

# this should technically be several scripts, todo later

import cPickle as pickle
import time
import string
import json
import urllib2
import urllib
import os.path
import os
import sys

if len(sys.argv) <= 2:
  print "use script properly:"
  print "usage: python addpaper.py [name|id] [query|id]"
  print "examples:"
  print "python addpaper.py name title of a nice paper"
  print "python addpaper.py id 31415926535"
  sys.exit(1)

if not os.path.isfile('appid.txt'):
  print "OOPS! You're missing Microsoft Academic Search APP ID key in file appid.txt!"
  print "See Readme.md for instructions on obtaining one."
  print "Exitting."
  sys.exit(1)

if not os.path.isdir('db'): os.mkdir('db')

appid= open('appid.txt', 'r').read().rstrip()
globaldb = os.path.join('db', 'papers.p')
if not os.path.isfile(globaldb): pickle.dump([], open(globaldb, "wb"))

# form the query URL to MAS
url = "http://academic.research.microsoft.com/json.svc/search?AppId=%s" % (appid, )
url += "&StartIdx=1&EndIdx=1"
url += "&ResultObjects=publication"
qtype = sys.argv[1]
if qtype == "name":
  q = " ".join(sys.argv[2:])
  q = q.replace(' ', '+')
  url += "&TitleQuery=%s" % (q, )

elif qtype == "id":
  pubid = sys.argv[2]
  url += "&PublicationID=%s" % (pubid, )  

else:
  print "invalid query type. use [name|id]. quitting."
  sys.exit(1)

# perform request
print "querying url: %s..." % (url, )
j = json.load(urllib2.urlopen(url))
if len(j['d']['Publication']['Result']) == 0:
  print "No results found found! quitting!"
  sys.exit(1)

# go down the results...
rix = 0
while True:
  pub = j['d']['Publication']['Result'][rix] # publication json

  idstr = str(pub['ID'])
  dirpath = os.path.join('db', idstr)
  title = pub['Title']

  # print some info and ask user if this is the right paper to make sure
  papers = pickle.load(open(globaldb, "rb"))
  seenthis = any([pub['ID']==x['ID'] for x in papers])
  havethis = os.path.isdir(dirpath)

  v=""
  if pub['Conference']: v=pub['Conference'] 
  if pub['Journal']: v = pub['Journal']
  print "Found a record:"
  print "title: ", title
  print "author: ", (", ".join(a['FirstName'] + ' ' + a['LastName'] for a in pub['Author']))
  print "published in: ", v, pub['Year']
  print "citations: ", pub['CitationCount']
  print "have record of this: ", seenthis
  print "is in library: ", havethis

  isgood = raw_input("add to library? y/n: ")
  if isgood=="y" or isgood=="": 
    break
  else:
    print "ok moving to the next result..."
    rix+=1
    if rix>=len(j['d']['Publication']['Result']):
      print "that's it, not found! quitting."
      sys.exit(1)

# save the information into global papers database, if we don't already have it
if not seenthis:
  print "Updating papers.p global database."
  papers.append(pub)
  pickle.dump(papers, open(globaldb, "wb"))

# save the individual record for this paper in db/$ID/json.p
if not havethis: 
  print "Creating folder %s..." % (dirpath, )
  os.mkdir(dirpath)
jsonpath = os.path.join(dirpath, 'json.p')
pickle.dump(pub, open(jsonpath, "wb"))
print "Writing ", jsonpath

# download both citations and references. 
# Done with one loop since these are so similar
xx = ['CitationCount', 'ReferenceCount']
yy = ['Citation', 'Reference']
ff = ['citations.p', 'references.p']
for i in range(2):
  maxn = pub[xx[i]]
  desc = yy[i]
  fname = ff[i]

  doskip = False
  while True:
    nd = raw_input("how many top %s (up to %d) to download for %s? [empty default = all]: " % (desc, maxn, title))
    if nd=="": ndi = maxn
    else: ndi = int(nd)
    if ndi==0: 
      print "ok skipping %s." % (desc, )
      doskip = True
      break
    if ndi>maxn: ndi = maxn

    if ndi>1000:
      print "More than 1000 is too many. That's crazy, won't allow it."
    else:
      break

  if doskip: continue

  # form request URL and query. Page through results (only top 100 are given)
  print "downloading top %d %s for %s" % (ndi, desc, title)
  pubs = []
  istart = 1
  while True:
    iend = istart + 99
    if iend>ndi: iend=ndi

    print "downloading %d to %d" % (istart, iend)
    url = "http://academic.research.microsoft.com/json.svc/search?AppId=%s" % (appid, )
    url += "&ResultObjects=Publication"
    url += "&ReferenceType=%s" % (desc, )
    url += "&StartIdx=%d&EndIdx=%d" % (istart, iend)
    url += "&PublicationID=%s" % (idstr, )
    print "querying %s ... " % (url, )
    j2 = json.load(urllib2.urlopen(url))
    pubs.extend(j2['d']['Publication']['Result'])

    if iend>=ndi: break
    istart = istart+100

  # save ids
  ids = [x['ID'] for x in pubs]
  refPicklePath = os.path.join('db', idstr, fname)
  print "writing ", refPicklePath
  pickle.dump(ids, open(refPicklePath, "wb"))

  # extend global papers database
  papers = pickle.load(open(globaldb, "rb"))
  numadded=0
  for p in pubs:
    if not any([p['ID']==x['ID'] for x in papers]):
      papers.append(p)
      numadded += 1
  pickle.dump(papers, open(globaldb, "wb"))

  print "wrote %d/%d new entries to papers.p pickle." % (numadded, len(pubs))


opencommand = "gnome-open"
if sys.platform == 'darwin':
  opencommand = "open"

# download full PDF
pdfpath = os.path.join('db', idstr, 'paper.pdf')
urls = pub['FullVersionURL']
pdfurls = [u for u in urls if u.endswith('.pdf')]
gotit = False
print "All paper links:"
for u in urls: print u
for u in pdfurls:
  print "trying to retrieve: ", u
  try:
    urllib.urlretrieve(u, pdfpath)
    print "saved pdf at ", pdfpath
    try:
      print "opening the pdf using %s (%s) for your convenience to verify the download..." %(opencommand, sys.platform)
      os.system(opencommand + " " + pdfpath)
    except Error, e:
      print "%s failed. Make sure the downloaded %s pdf is correct." % (opencommand, pdfpath, )
    isok = raw_input("download good? y/n: ")
    if isok=="y":
      gotit = True
      break
  except Exception, e:
    print "ERROR retrieving: ", e

if not gotit:
  print "Couldn't get the paper pdf. Please download manually and save as %s." % (pdfpath, )
  kk = raw_input("waiting... press key to continue")

# create thumbnails
try:
  print "creating paper thumbnails..."
  thumbpath = os.path.join('db', idstr, 'thumb.png')
  cmd = "convert %s -thumbnail 150 -trim %s" % (pdfpath, thumbpath)
  print "running: " + cmd
  os.system(cmd)
except Error, e:
  print "creating thumbnails failed:"
  print e

# analyze the paper for top words
try:
  print "running topwords.py..."
  os.system("python topwords.py %s" % (idstr, ))
except Error, e:
  print "topwords.py error:"
  print e

try:
  print "running genjson.py..."
  os.system("python genjson.py")
except Error, e:
  print "genjson.py error:"
  print e

try:
  print "running copyresources.py..."
  os.system("python copyresources.py %s" % (idstr, ))
except Error, e:
  print "copyresources.py error:"
  print e

print "done. Open client/index.html to view library."

########NEW FILE########
__FILENAME__ = copyresources
# copies resources from db/ to client/ that are necessary to view the database
import os.path
import os
import sys
import re
import shutil

# if an id is provided, use it. If not, do all papers
if len(sys.argv)>1: 
  pids = [sys.argv[1]]
else: 
  pids = os.listdir('db') # grab em all
  pids = [x for x in pids if os.path.isdir(os.path.join('db', x))]

# make sure client/imgs folder exists
imdir = os.path.join('client', 'resources')
if not os.path.isdir(imdir): os.mkdir(imdir)

for pid in pids:

  # copy images from db/ to client/imgs/
  pdir = os.path.join('db', pid)
  imfiles = [f for f in os.listdir(pdir) if re.match(r'thumb.*\.png', f)]
  dirto = os.path.join(imdir, pid)
  if not os.path.isdir(dirto): os.mkdir(dirto)

  for imfile in imfiles:
    pfrom = os.path.join(pdir, imfile)
    pto = os.path.join(dirto, imfile)
    shutil.copy2(pfrom, pto)

  # copy the pdf of the paper
  pfrom = os.path.join(pdir, 'paper.pdf')
  pto = os.path.join(dirto, 'paper.pdf')
  if os.path.isfile(pfrom):
    shutil.copy2(pfrom, pto)




########NEW FILE########
__FILENAME__ = genjson
# form the JSON database that will be read on the client

import cPickle as pickle
import os
import re
import json
import shutil

# build up list of papers
globaldb = os.path.join('db', 'papers.p')
papers = pickle.load(open(globaldb, "rb"))

out = []
for j in papers:

  pid = str(j['ID'])

  # basic meta information about this paper
  p={}
  p['i'] = j['ID']
  p['t'] = j['Title']
  p['a'] = [a['FirstName'] + ' ' + a['LastName'] for a in j['Author']]
  p['k'] = [k['Name'] for k in j['Keyword']]
  p['y'] = j['Year']
  p['b'] = j['Abstract']
  p['rn'] = j['ReferenceCount']
  p['cn'] = j['CitationCount']
  p['p'] = j['FullVersionURL']

  if j['Conference']: p['v'] = j['Conference']['ShortName']
  if j['Journal']: p['v'] = j['Journal']['ShortName']

  # see if we have computed other information for this paper
  pdir = os.path.join('db', pid)
  if os.path.isdir(pdir):

    # enter references if available
    refpath = os.path.join(pdir, 'references.p')
    if os.path.isfile(refpath):
      p['r'] = pickle.load(open(refpath, "rb"))

    # add citations if available
    citpath = os.path.join(pdir, 'citations.p')
    if os.path.isfile(citpath):
      p['c'] = pickle.load(open(citpath, "rb"))

    topWordsPicklePath = os.path.join(pdir, 'topwords.p')
    if os.path.isfile(topWordsPicklePath):
      twslist = pickle.load(open(topWordsPicklePath, "rb"))
      p['tw'] = [x[0] for x in twslist]

    # image paths
    imfiles = [f for f in os.listdir(pdir) if re.match(r'thumb.*\.png', f)]
    if len(imfiles)>0:
      thumbfiles = [("thumb-%d.png" % (i, )) for i in range(len(imfiles))]
      thumbs = [os.path.join('resources', pid, x) for x in thumbfiles]
      p['h'] = thumbs

  out.append(p)

outfile = os.path.join('client', 'db.json')
jout = json.dumps(out)
f = open(outfile, 'w')
f.write(jout)
f.close()




########NEW FILE########
__FILENAME__ = topwords
# finds top words in a paper and saves them to db/$PAPERID/topwords.p
# requires paper.pdf for the paper to exist

import os.path
import os
import sys
import cPickle as pickle
from string import punctuation
from operator import itemgetter
import re

N= 100 # how many top words to retain

# load in stopwords (i.e. boring words, these we will ignore)
stopwords = open("stopwords.txt", "r").read().split()
stopwords = [x.strip(punctuation) for x in stopwords if len(x)>2]

pid = sys.argv[1]

pdfpath = os.path.join('db', pid, 'paper.pdf')
if not os.path.isfile(pdfpath):
  print "wat?? %s is missing. Can't extract top words. Exitting." % (pdfpath, )
  sys.exit(1)

picklepath = os.path.join('db', pid, 'topwords.p')
if os.path.isfile(pdfpath):

  print "processing %s " % (pid, )
  topwords = {}

  cmd = "pdftotext %s %s" % (pdfpath, "out.txt")
  print "running: " + cmd
  os.system(cmd)

  txtlst = open("out.txt").read().split() # get all words in a giant list
  words = [x.lower() for x in txtlst if re.match('^[\w-]+$', x) is not None] # take only alphanumerics
  words = [x for x in words if len(x)>2 and (not x in stopwords)] # remove stop words

  # count up frequencies of all words
  wcount = {} 
  for w in words: wcount[w] = wcount.get(w, 0) + 1
  top = sorted(wcount.iteritems(), key=itemgetter(1), reverse=True)[:N] # sort and take top N

  # top is a list of (word, frequency) items. Save it
  pickle.dump(top, open(picklepath, "wb"))
  
print "all done."

########NEW FILE########
