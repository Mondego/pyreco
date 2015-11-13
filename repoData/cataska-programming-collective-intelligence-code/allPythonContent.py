__FILENAME__ = clusters
import random
import math
from math import sqrt
from PIL import Image,ImageDraw,ImageFont

# Returns the Pearson correlation coefficient for p1 and p2
def pearson(v1,v2):
  # Simple sums
  sum1=sum(v1)
  sum2=sum(v2)
  
  # Sums of the squares
  sum1Sq=sum([pow(v,2) for v in v1])
  sum2Sq=sum([pow(v,2) for v in v2])	
  
  # Sum of the products
  pSum=sum([v1[i]*v2[i] for i in range(len(v1))])
  
  # Calculate r (Pearson score)
  num=pSum-(sum1*sum2/len(v1))
  den=sqrt((sum1Sq-pow(sum1,2)/len(v1))*(sum2Sq-pow(sum2,2)/len(v1)))
  if den==0: return 0

  return 1.0-(num/den)


class bicluster:
  def __init__(self,vec,left=None,right=None,distance=0.0,id=None):
    self.left=left
    self.right=right
    self.vec=vec
    self.id=id
    self.distance=distance

def euclidean(v1,v2):
  sqsum=sum([math.pow(v1[i]-v2[i],2) for i in range(len(v1))])
  return math.sqrt(sqsum)

def printclust(clust,labels=None,n=0):
  for i in range(n): print ' ',
  if clust.id<0:
    print '-'
  else:
    if labels==None: print clust.id
    else: print labels[clust.id]
  if clust.left!=None: printclust(clust.left,labels=labels,n=n+1)
  if clust.right!=None: printclust(clust.right,labels=labels,n=n+1)

def hcluster(vecs,distance=pearson):
  distances={}
  currentclustid=-1
  clust=[bicluster(vecs[i],id=i) for i in range(len(vecs))]

  while len(clust)>1:
    lowestpair=(0,1)
    closest=distance(clust[0].vec,clust[1].vec)
    for i in range(len(clust)):
      for j in range(i+1,len(clust)):
        if (clust[i].id,clust[j].id) not in distances: 
          distances[(clust[i].id,clust[j].id)]=distance(clust[i].vec,clust[j].vec)
        d=distances[(clust[i].id,clust[j].id)]

        if d<closest:
          closest=d
          lowestpair=(i,j)

    mergevec=[(clust[lowestpair[0]].vec[i]+clust[lowestpair[1]].vec[i])/2.0 for i in range(len(clust[0].vec))]
    error=closest
    newcluster=bicluster(mergevec,left=clust[lowestpair[0]],right=clust[lowestpair[1]],distance=error,id=currentclustid)
    
    currentclustid-=1
    del clust[lowestpair[1]]
    del clust[lowestpair[0]]
    clust.append(newcluster)

  return clust[0]
  
  
def kcluster(vecs,distance=pearson,k=4):
  ranges=[(min([vec[i] for vec in vecs]),max([vec[i] for vec in vecs])) for i in range(len(vecs[0]))]
  clusters=[[random.random()*(ranges[i][1]-ranges[i][0])+ranges[i][0] for i in range(len(vecs[0]))] for j in range(k)]
  
  lastmatches=None
  for t in range(100):
    print 'Iteration %d' % t
    bestmatches=[[] for i in range(k)]
    
    for j in range(len(vecs)):
      vec=vecs[j]
      bestmatch=0
      for i in range(k):
        d=distance(clusters[i],vec)
        if d<distance(clusters[bestmatch],vec): bestmatch=i
      bestmatches[bestmatch].append(j)

    if bestmatches==lastmatches: break
    lastmatches=bestmatches
    
    for i in range(k):
      avgs=[0.0]*len(vecs[0])
      if len(bestmatches[i])>0:
        for vecid in bestmatches[i]:
          for m in range(len(vecs[vecid])):
            avgs[m]+=vecs[vecid][m]
        for j in range(len(avgs)):
          avgs[j]/=len(bestmatches[i])
        clusters[i]=avgs
      
  return bestmatches

def readfile(filename):
  lines=[line for line in file(filename)]
  colnames=lines[0].strip().split('\t')[1:]
  rownames=[]
  data=[]
  for line in lines[1:]:
    p=line.strip().split('\t')
    rownames.append(p[0])
    data.append([float(x) for x in p[1:]])
  return rownames,colnames,data

def test2():
  rownames,colnames,data=readfile('datafile.txt')
  return hcluster(data)
  #for i in range(len(rownames)):
  #  print i,rownames[i]

def distance(v1,v2):
  c1,c2,shr=0,0,0
  
  for i in range(len(v1)):
    if v1[i]!=0: c1+=1
    if v2[i]!=0: c2+=1
    if v1[i]!=0 and v2[i]!=0: shr+=1
  
  return float(shr)/(c1+c2-shr)


#test2()

def getheight(clust):
  if clust.left==None and clust.right==None: return 1
  return getheight(clust.left)+getheight(clust.right)

def getdepth(clust):
  if clust.left==None and clust.right==None: return 0
  return max(getdepth(clust.left),getdepth(clust.right))+clust.distance

def drawdendrogram(clust,labels,jpeg='clusters.jpg'):
  h=getheight(clust)*20
  depth=getdepth(clust)
  w=1200
  scaling=float(w-150)/depth
  img=Image.new('RGB',(w,h),(255,255,255))
  draw=ImageDraw.Draw(img)

  draw.line((0,h/2,10,h/2),fill=(255,0,0))    

  drawnode(draw,clust,10,(h/2),scaling,labels)
  img.save(jpeg,'JPEG')

def drawnode(draw,clust,x,y,scaling,labels):
  if clust.id<0:
    h1=getheight(clust.left)*20
    h2=getheight(clust.right)*20
    top=y-(h1+h2)/2
    bottom=y+(h1+h2)/2
    
    ll=clust.distance*scaling
    
    draw.line((x,top+h1/2,x,bottom-h2/2),fill=(255,0,0))    

    draw.line((x,top+h1/2,x+ll,top+h1/2),fill=(255,0,0))    
    draw.line((x,bottom-h2/2,x+ll,bottom-h2/2),fill=(255,0,0))        
    
    drawnode(draw,clust.left,x+ll,top+h1/2,scaling,labels)
    drawnode(draw,clust.right,x+ll,bottom-h2/2,scaling,labels)
  else:   
    draw.text((x+5,y-7),labels[clust.id].encode('utf8'),(0,0,0))

def rotatematrix(data):
  newdata=[]
  for i in range(len(data[0])):
    newrow=[data[j][i] for j in range(len(data))]
    newdata.append(newrow)
  return newdata

def scaledown(data,distance=pearson,rate=0.01):
  n=len(data)
  realdist=[[distance(data[i],data[j]) for j in range(n)] for i in range(0,n)]

  outersum=0.0
  
  loc=[[random.random(),random.random()] for i in range(n)] 
  fakedist=[[0.0 for j in range(n)] for i in range(n)]
  
  lasterror=None
  for m in range(0,1000):
    # Find projected distances
    for i in range(n):
      for j in range(n):
        fakedist[i][j]=sqrt(sum([pow(loc[i][x]-loc[j][x],2) 
                                 for x in range(len(loc[i]))]))
  
    # Move points
    grad=[[0.0,0.0] for i in range(n)]
    
    totalerror=0
    for k in range(n):
      for j in range(n):
        if j==k: continue
        errorterm=(fakedist[j][k]-realdist[j][k])/realdist[j][k]
        grad[k][0]+=((loc[k][0]-loc[j][0])/fakedist[j][k])*errorterm
        grad[k][1]+=((loc[k][1]-loc[j][1])/fakedist[j][k])*errorterm    
        totalerror+=abs(errorterm)
    print totalerror
    if lasterror and lasterror<totalerror: break
    lasterror=totalerror
    
    for k in range(n):
      loc[k][0]-=rate*grad[k][0]
      loc[k][1]-=rate*grad[k][1]

  return loc

def draw2d(data,labels,jpg='mds2d.jpg'):
  img=Image.new('RGB',(2000,2000),(255,255,255))
  draw=ImageDraw.Draw(img)
  for i in range(len(data)):
    x=(data[i][0]+0.5)*1000
    y=(data[i][1]+0.5)*1000
    draw.text((x,y),labels[i],(0,0,0))
  img.save(jpg,'JPEG')  
  img.show()

########NEW FILE########
__FILENAME__ = docclass
import re
import math
import cPickle
from pysqlite2 import dbapi2 as sqlite

def getwords(doc):
  splitter=re.compile('\\W*')
  words=[s.lower() for s in splitter.split(doc) 
          if len(s)>2 and len(s)<20]
  
  # Return the unique set of words only
  return dict([(w,1) for w in words])

#def entryfeatures(entry):

def sampletrain(cl):
  cl.train('Nobody owns the water.','good')
  cl.train('the quick rabbit jumps fences','good')
  cl.train('buy pharmaceuticals now','bad')
  cl.train('make quick money at the online casino','bad')
  cl.train('the quick brown fox jumps','good')

class classifier:
  def __init__(self,getfeatures):
    self.fc={}
    self.cc={}
    self.getfeatures=getfeatures
  
  def setdb(self,dbfile):
    self.con=sqlite.connect(dbfile)    
    self.con.execute('create table if not exists fc(feature,category,count)')
    self.con.execute('create table if not exists cc(category,count)')
  
  def incf(self,f,cat):
    count=self.fcount(f,cat)
    if count==0:
      self.con.execute("insert into fc values ('%s','%s',1)" 
                       % (f,cat))
    else:
      self.con.execute(
        "update fc set count=%d where feature='%s' and category='%s'" 
        % (count+1,f,cat)) 
  
  def fcount(self,f,cat):
    res=self.con.execute(
      'select count from fc where feature="%s" and category="%s"'
      %(f,cat)).fetchone()
    if res==None: return 0
    else: return float(res[0])

  def incc(self,cat):
    count=self.catcount(cat)
    if count==0:
      self.con.execute("insert into cc values ('%s',1)" % (cat))
    else:
      self.con.execute("update cc set count=%d where category='%s'" 
                       % (count+1,cat))    
      
  def catcount(self,cat):
    res=self.con.execute('select count from cc where category="%s"'
                         %(cat)).fetchone()
    if res==None: return 0.0
    else: return float(res[0])
    
  def categories(self):
    cur=self.con.execute('select category from cc');
    return [d[0] for d in cur]

  def totalcount(self):
    res=self.con.execute('select sum(count) from cc').fetchone();
    if res==None: return 0
    return res[0]
    

  """  
  def incf(self,f,cat):
    self.fc.setdefault(f,{})
    self.fc[f].setdefault(cat,0)
    self.fc[f][cat]+=1
  
  def incc(self,cat):
    self.cc.setdefault(cat,0)
    self.cc[cat]+=1
 
  def fcount(self,f,cat):
    if f in self.fc and cat in self.fc[f]: 
      return float(self.fc[f][cat])
    return 0.0
  
  def catcount(self,cat):
    if cat in self.cc:
      return float(self.cc[cat])
    return 0

  def totalcount(self):
    return sum(self.cc.values())

  def categories(self):
    return self.cc.keys()
  """  
  
  
  def train(self,item,cat):
    features=self.getfeatures(item)   
    for f in features:
      self.incf(f,cat)
    self.incc(cat)
    self.con.commit()
   
  def fprob(self,f,cat):
    if self.catcount(cat)==0: return 0
    return self.fcount(f,cat)/self.catcount(cat)

  def setfilename(self,filename):
    self.filename=filename
    self.restoredata()

  def restoredata(self):
    try: f=file(self.filename,'rb')
    except: return
    self.fc=cPickle.load(f)
    self.cc=cPickle.load(f)
    f.close()
    
  def savedata(self):
    f=file(self.filename,'wb')
    cPickle.dump(self.fc,f,True)
    cPickle.dump(self.cc,f,True)
    f.close()
  def weightedprob(self,f,cat,prf,weight=1.0,ap=0.5):
    basicprob=prf(f,cat)
    totals=sum([self.fcount(f,c) for c in self.categories()])
    bp=((weight*ap)+(totals*basicprob))/(weight+totals)
    return bp
    
      
  
class naivebayes(classifier):
  def __init__(self,getfeatures):
    classifier.__init__(self,getfeatures)
    self.thresholds={}

  def setthreshold(self,cat,t):
    self.thresholds[cat]=t
    
  def getthreshold(self,cat):
    if cat not in self.thresholds: return 1.0
    return self.thresholds[cat]

  def classify(self,item,default=None):
    probs={}
    max=0.0
    for cat in self.categories():
      probs[cat]=self.prob(item,cat)
      if probs[cat]>max: 
        max=probs[cat]
        best=cat
    for cat in probs:
      if cat==best: continue
      if probs[cat]*self.getthreshold(best)>probs[best]: return default
    return best
    
  def docprob(self,item,cat):
    features=self.getfeatures(item)   
    p=1
    for f in features: p*=self.weightedprob(f,cat,self.fprob)
    return p


  def prob(self,item,cat):
    catprob=self.catcount(cat)/self.totalcount()
    docprob=self.docprob(item,cat)
    return docprob*catprob

class fisherclassifier(classifier):
  def __init__(self,getfeatures):
    classifier.__init__(self,getfeatures)
    self.minimums={}

  def setminimum(self,cat,min):
    self.minimums[cat]=min
  
  def getminimum(self,cat):
    if cat not in self.minimums: return 0
    return self.minimums[cat]
  
  def classify(self,item,default=None):
    best=default
    max=0.0
    for c in self.categories():
      p=self.fisherprob(item,c)
      if p>self.getminimum(c) and p>max:
        best=c
        max=p
    return best
        

  def cprob(self,f,cat):
    # The frequency of this feature in this category    
    clf=self.fprob(f,cat)

    if clf==0: return 0.0

    # The frequency of this feature in all the categories
    freqsum=sum([self.fprob(f,c) for c in self.categories()])

    # The probability is the frequency in this category divided by
    # the overall frequency
    p=clf/(freqsum)
    
    return p
  
  
  def fisherprob(self,item,cat):
    p=1
    features=self.getfeatures(item)
    for f in features:
      p*=(self.weightedprob(f,cat,self.cprob))
    fscore=-2*math.log(p)
    return self.chi2P(fscore,len(features)*2)
  
  def chi2P(self,chi,df):
    m = chi / 2.0
    sum = term = math.exp(-m)
    for i in range(1, df//2):
        term *= m / i
        sum += term
    return min(sum, 1.0)


########NEW FILE########
__FILENAME__ = newsfeatures
import feedparser
import re


feedlist=['http://today.reuters.com/rss/topNews',
          'http://today.reuters.com/rss/domesticNews',
          'http://today.reuters.com/rss/worldNews',
          'http://hosted.ap.org/lineups/TOPHEADS-rss_2.0.xml',
          'http://hosted.ap.org/lineups/USHEADS-rss_2.0.xml',
          'http://hosted.ap.org/lineups/WORLDHEADS-rss_2.0.xml',
          'http://hosted.ap.org/lineups/POLITICSHEADS-rss_2.0.xml',
          'http://www.nytimes.com/services/xml/rss/nyt/HomePage.xml',
          'http://www.nytimes.com/services/xml/rss/nyt/International.xml',
          'http://news.google.com/?output=rss',
          'http://feeds.salon.com/salon/news',
          'http://www.foxnews.com/xmlfeed/rss/0,4313,0,00.rss',
          'http://www.foxnews.com/xmlfeed/rss/0,4313,80,00.rss',
          'http://www.foxnews.com/xmlfeed/rss/0,4313,81,00.rss',
          'http://rss.cnn.com/rss/edition.rss',
          'http://rss.cnn.com/rss/edition_world.rss',
          'http://rss.cnn.com/rss/edition_us.rss']

def stripHTML(h):
  p=''
  s=0
  for c in h:
    if c=='<': s=1
    elif c=='>':
      s=0
      p+=' '
    elif s==0: p+=c
  return p


def separatewords(text):
  splitter=re.compile('\\W*')
  return [s.lower() for s in splitter.split(text) if len(s)>3]

def getarticlewords():
  allwords={}
  articlewords=[]
  articletitles=[]
  ec=0
  # Loop over every feed
  for feed in feedlist:
    f=feedparser.parse(feed)
    
    # Loop over every article
    for e in f.entries:
      # Ignore identical articles
      if e.title in articletitles: continue
      
      # Extract the words
      txt=e.title.encode('utf8')+stripHTML(e.description.encode('utf8'))
      words=separatewords(txt)
      articlewords.append({})
      articletitles.append(e.title)
      
      # Increase the counts for this word in allwords and in articlewords
      for word in words:
        allwords.setdefault(word,0)
        allwords[word]+=1
        articlewords[ec].setdefault(word,0)
        articlewords[ec][word]+=1
      ec+=1
  return allwords,articlewords,articletitles

def makematrix(allw,articlew):
  wordvec=[]
  
  # Only take words that are common but not too common
  for w,c in allw.items():
    if c>3 and c<len(articlew)*0.6:
      wordvec.append(w) 
  
  # Create the word matrix
  l1=[[(word in f and f[word] or 0) for word in wordvec] for f in articlew]
  return l1,wordvec

from numpy import *

def showfeatures(w,h,titles,wordvec,out='features.txt'): 
  outfile=file(out,'w')  
  pc,wc=shape(h)
  toppatterns=[[] for i in range(len(titles))]
  patternnames=[]
  
  # Loop over all the features
  for i in range(pc):
    slist=[]
    # Create a list of words and their weights
    for j in range(wc):
      slist.append((h[i,j],wordvec[j]))
    # Reverse sort the word list
    slist.sort()
    slist.reverse()
    
    # Print the first six elements
    n=[s[1] for s in slist[0:6]]
    outfile.write(str(n)+'\n')
    patternnames.append(n)
    
    # Create a list of articles for this feature
    flist=[]
    for j in range(len(titles)):
      # Add the article with its weight
      flist.append((w[j,i],titles[j]))
      toppatterns[j].append((w[j,i],i,titles[j]))
    
    # Reverse sort the list
    flist.sort()
    flist.reverse()
    
    # Show the top 3 articles
    for f in flist[0:3]:
      outfile.write(str(f)+'\n')
    outfile.write('\n')

  outfile.close()
  # Return the pattern names for later use
  return toppatterns,patternnames

def showarticles(titles,toppatterns,patternnames,out='articles.txt'):
  outfile=file(out,'w')  
  
  # Loop over all the articles
  for j in range(len(titles)):
    outfile.write(titles[j].encode('utf8')+'\n')
    
    # Get the top features for this article and
    # reverse sort them
    toppatterns[j].sort()
    toppatterns[j].reverse()
    
    # Print the top three patterns
    for i in range(3):
      outfile.write(str(toppatterns[j][i][0])+' '+
                    str(patternnames[toppatterns[j][i][1]])+'\n')
    outfile.write('\n')
    
  outfile.close()

########NEW FILE########
__FILENAME__ = nnmf
from numpy import *

def difcost(a,b):
  dif=0
  for i in range(shape(a)[0]):
    for j in range(shape(a)[1]):
      # Euclidean Distance
      dif+=pow(a[i,j]-b[i,j],2)
  return dif

def factorize(v,pc=10,iter=50):
  ic=shape(v)[0]
  fc=shape(v)[1]

  # Initialize the weight and feature matrices with random values
  w=matrix([[random.random() for j in range(pc)] for i in range(ic)])
  h=matrix([[random.random() for i in range(fc)] for i in range(pc)])

  # Perform operation a maximum of iter times
  for i in range(iter):
    wh=w*h
    
    # Calculate the current difference
    cost=difcost(v,wh)
    
    if i%10==0: print cost
    
    # Terminate if the matrix has been fully factorized
    if cost==0: break
    
    # Update feature matrix
    hn=(transpose(w)*v)
    hd=(transpose(w)*w*h)
  
    h=matrix(array(h)*array(hn)/array(hd))

    # Update weights matrix
    wn=(v*transpose(h))
    wd=(w*h*transpose(h))

    w=matrix(array(w)*array(wn)/array(wd))  
    
  return w,h

########NEW FILE########
__FILENAME__ = stockvolume
import nnmf
import urllib2
from numpy import *

tickers=['YHOO','AVP','BIIB','BP','CL','CVX',
         'DNA','EXPE','GOOG','PG','XOM','AMGN']

shortest=300
prices={}
dates=None

for t in tickers:
  # Open the URL
  rows=urllib2.urlopen('http://ichart.finance.yahoo.com/table.csv?'+\
                       's=%s&d=11&e=26&f=2006&g=d&a=3&b=12&c=1996'%t +\
                       '&ignore=.csv').readlines()

  
  # Extract the volume field from every line
  prices[t]=[float(r.split(',')[5]) for r in rows[1:] if r.strip()!='']
  if len(prices[t])<shortest: shortest=len(prices[t])
  
  if not dates:
    dates=[r.split(',')[0] for r in rows[1:] if r.strip()!='']

l1=[[prices[tickers[i]][j] 
     for i in range(len(tickers))] 
    for j in range(shortest)]

w,h=nnmf.factorize(matrix(l1),pc=5)

print h
print w

# Loop over all the features
for i in range(shape(h)[0]):
  print "Feature %d" %i
  
  # Get the top stocks for this feature
  ol=[(h[i,j],tickers[j]) for j in range(shape(h)[1])]
  ol.sort()
  ol.reverse()
  for j in range(12):
    print ol[j]
  print
  
  # Show the top dates for this feature
  porder=[(w[d,i],d) for d in range(300)]
  porder.sort()
  porder.reverse()
  print [(p[0],dates[p[1]]) for p in porder[0:3]]
  print

########NEW FILE########
__FILENAME__ = gp
from random import random,randint,choice
from copy import deepcopy
from math import log

class fwrapper:
  def __init__(self,function,childcount,name):
    self.function=function
    self.childcount=childcount
    self.name=name

class node:
  def __init__(self,fw,children):
    self.function=fw.function
    self.name=fw.name
    self.children=children

  def evaluate(self,inp):    
    results=[n.evaluate(inp) for n in self.children]
    return self.function(results)
  def display(self,indent=0):
    print (' '*indent)+self.name
    for c in self.children:
      c.display(indent+1)
    

class paramnode:
  def __init__(self,idx):
    self.idx=idx

  def evaluate(self,inp):
    return inp[self.idx]
  def display(self,indent=0):
    print '%sp%d' % (' '*indent,self.idx)
    
    
class constnode:
  def __init__(self,v):
    self.v=v
  def evaluate(self,inp):
    return self.v
  def display(self,indent=0):
    print '%s%d' % (' '*indent,self.v)
    

addw=fwrapper(lambda l:l[0]+l[1],2,'add')
subw=fwrapper(lambda l:l[0]-l[1],2,'subtract') 
mulw=fwrapper(lambda l:l[0]*l[1],2,'multiply')

def iffunc(l):
  if l[0]>0: return l[1]
  else: return l[2]
ifw=fwrapper(iffunc,3,'if')

def isgreater(l):
  if l[0]>l[1]: return 1
  else: return 0
gtw=fwrapper(isgreater,2,'isgreater')

flist=[addw,mulw,ifw,gtw,subw]

def exampletree():
  return node(ifw,[
                  node(gtw,[paramnode(0),constnode(3)]),
                  node(addw,[paramnode(1),constnode(5)]),
                  node(subw,[paramnode(1),constnode(2)]),
                  ]
              )

def makerandomtree(pc,maxdepth=4,fpr=0.5,ppr=0.6):
  if random()<fpr and maxdepth>0:
    f=choice(flist)
    children=[makerandomtree(pc,maxdepth-1,fpr,ppr) 
              for i in range(f.childcount)]
    return node(f,children)
  elif random()<ppr:
    return paramnode(randint(0,pc-1))
  else:
    return constnode(randint(0,10))
              

def hiddenfunction(x,y):
    return x**2+2*y+3*x+5

def buildhiddenset():
  rows=[]
  for i in range(200):
    x=randint(0,40)
    y=randint(0,40)
    rows.append([x,y,hiddenfunction(x,y)])
  return rows

def scorefunction(tree,s):
  dif=0
  for data in s:
    v=tree.evaluate([data[0],data[1]])
    dif+=abs(v-data[2])
  return dif


def mutate(t,pc,probchange=0.1):
  if random()<probchange:
    return makerandomtree(pc)
  else:
    result=deepcopy(t)
    if hasattr(t,"children"):
      result.children=[mutate(c,pc,probchange) for c in t.children]
    return result

def crossover(t1,t2,probswap=0.7,top=1):
  if random()<probswap and not top:
    return deepcopy(t2) 
  else:
    result=deepcopy(t1)
    if hasattr(t1,'children') and hasattr(t2,'children'):
      result.children=[crossover(c,choice(t2.children),probswap,0) 
                       for c in t1.children]
    return result

def getrankfunction(dataset):
  def rankfunction(population):
    scores=[(scorefunction(t,dataset),t) for t in population]
    scores.sort()
    return scores
  return rankfunction
  
    

def evolve(pc,popsize,rankfunction,maxgen=500,
           mutationrate=0.1,breedingrate=0.4,pexp=0.7,pnew=0.05):
  # Returns a random number, tending towards lower numbers. The lower pexp
  # is, more lower numbers you will get
  def selectindex():
    return int(log(random())/log(pexp))

  # Create a random initial population
  population=[makerandomtree(pc) for i in range(popsize)]
  for i in range(maxgen):
    scores=rankfunction(population)
    print scores[0][0]
    if scores[0][0]==0: break
    
    # The two best always make it
    newpop=[scores[0][1],scores[1][1]]
    
    # Build the next generation
    while len(newpop)<popsize:
      if random()>pnew:
        newpop.append(mutate(
                      crossover(scores[selectindex()][1],
                                 scores[selectindex()][1],
                                probswap=breedingrate),
                        pc,probchange=mutationrate))
      else:
      # Add a random node to mix things up
        newpop.append(makerandomtree(pc))
        
    population=newpop
  scores[0][1].display()    
  return scores[0][1]


def gridgame(p):
  # Board size
  max=(3,3)
  
  # Remember the last move for each player
  lastmove=[-1,-1]
  
  # Remember the player's locations
  location=[[randint(0,max[0]),randint(0,max[1])]]
  
  # Put the second player a sufficient distance from the first
  location.append([(location[0][0]+2)%4,(location[0][1]+2)%4])
  # Maximum of 50 moves before a tie
  for o in range(50):
  
    # For each player
    for i in range(2):
      locs=location[i][:]+location[1-i][:]
      locs.append(lastmove[i])
      move=p[i].evaluate(locs)%4
      
      # You lose if you move the same direction twice in a row
      if lastmove[i]==move: return 1-i
      lastmove[i]=move
      if move==0: 
        location[i][0]-=1
        # Board wraps
        if location[i][0]<0: location[i][0]=0
      if move==1: 
        location[i][0]+=1
        if location[i][0]>max[0]: location[i][0]=max[0]
      if move==2: 
        location[i][1]-=1
        if location[i][1]<0: location[i][1]=0
      if move==3: 
        location[i][1]+=1
        if location[i][1]>max[1]: location[i][1]=max[1]
      
      # If you have captured the other player, you win
      if location[i]==location[1-i]: return i
  return -1


def tournament(pl):
  # Count losses
  losses=[0 for p in pl]
  
  # Every player plays every other player
  for i in range(len(pl)):
    for j in range(len(pl)):
      if i==j: continue
      
      # Who is the winner?
      winner=gridgame([pl[i],pl[j]])
      
      # Two points for a loss, one point for a tie
      if winner==0:
        losses[j]+=2
      elif winner==1:
        losses[i]+=2
      elif winner==-1:
        losses[i]+=1
        losses[i]+=1
        pass

  # Sort and return the results
  z=zip(losses,pl)
  z.sort()
  return z      

class humanplayer:
  def evaluate(self,board):

    # Get my location and the location of other players
    me=tuple(board[0:2])
    others=[tuple(board[x:x+2]) for x in range(2,len(board)-1,2)]
    
    # Display the board
    for i in range(4):
      for j in range(4):
        if (i,j)==me:
          print 'O',
        elif (i,j) in others:
          print 'X',
        else:
          print '.',
      print
      
    # Show moves, for reference
    print 'Your last move was %d' % board[len(board)-1]
    print ' 0'
    print '2 3'
    print ' 1'
    print 'Enter move: ',
    
    # Return whatever the user enters
    move=int(raw_input())
    return move


class fwrapper:
  def __init__(self,function,params,name):
    self.function=function
    self.childcount=param
    self.name=name
    
#flist={'str':[substringw,concatw],'int':[indexw]}
flist=[addw,mulw,ifw,gtw,subw]

########NEW FILE########
__FILENAME__ = deliciousrec
from pydelicious import get_popular,get_userposts,get_urlposts
import time

def initializeUserDict(tag,count=5):
  user_dict={}
  # get the top count' popular posts
  for p1 in get_popular(tag=tag)[0:count]:
    # find all users who posted this
    for p2 in get_urlposts(p1['href']):
      user=p2['user']
      user_dict[user]={}
  return user_dict

def fillItems(user_dict):
  all_items={}
  # Find links posted by all users
  for user in user_dict:
    for i in range(3):
      try:
        posts=get_userposts(user)
        break
      except:
        print "Failed user "+user+", retrying"
        time.sleep(4)
    for post in posts:
      url=post['href']
      user_dict[user][url]=1.0
      all_items[url]=1
  
  # Fill in missing items with 0
  for ratings in user_dict.values():
    for item in all_items:
      if item not in ratings:
        ratings[item]=0.0

########NEW FILE########
__FILENAME__ = pydelicious
"""Library to access del.icio.us data via Python.

:examples:

  Using the API class directly:

  >>> a = pydelicious.apiNew('user', 'passwd')
  >>> # or:
  >>> a = DeliciousAPI('user', 'passwd')
  >>> a.tags_get() # Same as:
  >>> a.request('tags/get', )

  Or by calling the 'convenience' methods on the module.

  - def add(user, passwd, url, description, tags = "", extended = "", dt = "", replace="no"):
  - def get(user, passwd, tag="", dt="",  count = 0):
  - def get_all(user, passwd, tag = ""):
  - def delete(user, passwd, url):
  - def rename_tag(user, passwd, oldtag, newtag):
  - def get_tags(user, passwd):

  >>> a = apiNew(user, passwd)
  >>> a.posts_add(url="http://my.com/", desciption="my.com", extended="the url is my.moc", tags="my com")
  True
  >>> len(a.posts_all())
  1
  >>> get_all(user, passwd)
  1

  This are short functions for getrss calls.

  >>> rss_

def get_userposts(user):
def get_tagposts(tag):
def get_urlposts(url):
def get_popular(tag = ""):

  >>> json_posts()
  >>> json_tags()
  >>> json_network()
  >>> json_fans()

:License: pydelicious is released under the BSD license. See 'license.txt'
 for more informations.

:berend:
 - Rewriting comments to english. More documentation, examples.
 - Added JSON-like return values for XML data (del.icio.us also serves some JSON...)
 - better error/exception classes and handling, work in progress.
 - Encoding seems to be working (using UTF-8 here).

:@todo:
 - Source code SHOULD BE ASCII!
 - More tests.
 - Parse datetimes in XML.
 - Salvage and test RSS functionality?
 - Setup not used, Still works? Should setup.py be tested?
 - API functions need required argument checks.

 * lizense einbinden und auch via setup.py verteilen
 * readme auch schreiben und via setup.py verteilen
 * auch auf anderen systemen testen (linux -> uni)
 * automatisch releases bauen lassen, richtig benennen und in das
   richtige verzeichnis verschieben.
 * was k[o]nnen die anderen librarys denn noch so? (ruby, java, perl, etc)
 * was wollen die, die es benutzen?
 * wof[u]r k[o]nnte ich es benutzen?
 * entschlacken?

:done:
 * Refactored the API class, much cleaner now and functions dlcs_api_request, dlcs_parse_xml are available for who wants them.
 * stimmt das so? muss eher noch t[a]g str2utf8 konvertieren
   >>> pydelicious.getrss(tag="t[a]g")
   url: http://del.icio.us/rss/tag/t[a]g
 * requester muss eine sekunde warten
 * __init__.py gibt die funktionen weiter
 * html parser funktioniert noch nicht, gar nicht
 * alte funktionen fehlen, get_posts_by_url, etc.
 * post funktion erstellen, die auch die fehlenden attribs addiert.
 * die api muss ich noch weiter machen
 * requester muss die 503er abfangen
 * rss parser muss auf viele m[o]glichkeiten angepasst werden
"""
import sys
import os
import time
import datetime
import md5, httplib
import urllib, urllib2, time
from StringIO import StringIO

try:
    from elementtree.ElementTree import parse as parse_xml
except ImportError:
    from  xml.etree.ElementTree import parse as parse_xml

import feedparser


### Static config

__version__ = '0.5.0'
__author__ = 'Frank Timmermann <regenkind_at_gmx_dot_de>' # GP: does not respond to emails
__contributors__ = [
    'Greg Pinero',
    'Berend van Berkum <berend+pydelicious@dotmpe.com>']
__url__ = 'http://code.google.com/p/pydelicious/'
__author_email__ = ""
# Old URL: 'http://deliciouspython.python-hosting.com/'

__description__ = '''pydelicious.py allows you to access the web service of del.icio.us via it's API through python.'''
__long_description__ = '''the goal is to design an easy to use and fully functional python interface to del.icio.us. '''

DLCS_OK_MESSAGES = ('done', 'ok') # Known text values of positive del.icio.us <result> answers
DLCS_WAIT_TIME = 4
DLCS_REQUEST_TIMEOUT = 444 # Seconds before socket triggers timeout
#DLCS_API_REALM = 'del.icio.us API'
DLCS_API_HOST = 'https://api.del.icio.us'
DLCS_API_PATH = 'v1'
DLCS_API = "%s/%s" % (DLCS_API_HOST, DLCS_API_PATH)
DLCS_RSS = 'http://del.icio.us/rss/'

ISO_8601_DATETIME = '%Y-%m-%dT%H:%M:%SZ'

USER_AGENT = 'pydelicious.py/%s %s' % (__version__, __url__)

DEBUG = 0
if 'DLCS_DEBUG' in os.environ:
    DEBUG = int(os.environ['DLCS_DEBUG'])


# Taken from FeedParser.py
# timeoutsocket allows feedparser to time out rather than hang forever on ultra-slow servers.
# Python 2.3 now has this functionality available in the standard socket library, so under
# 2.3 you don't need to install anything.  But you probably should anyway, because the socket
# module is buggy and timeoutsocket is better.
try:
    import timeoutsocket # http://www.timo-tasi.org/python/timeoutsocket.py
    timeoutsocket.setDefaultSocketTimeout(DLCS_REQUEST_TIMEOUT)
except ImportError:
    import socket
    if hasattr(socket, 'setdefaulttimeout'): socket.setdefaulttimeout(DLCS_REQUEST_TIMEOUT)
if DEBUG: print >>sys.stderr, "Set socket timeout to %s seconds" % DLCS_REQUEST_TIMEOUT


### Utility classes

class _Waiter:
    """Waiter makes sure a certain amount of time passes between
    successive calls of `Waiter()`.

    Some attributes:
    :last: time of last call
    :wait: the minimum time needed between calls
    :waited: the number of calls throttled

    pydelicious.Waiter is an instance created when the module is loaded.
    """
    def __init__(self, wait):
        self.wait = wait
        self.waited = 0
        self.lastcall = 0;

    def __call__(self):
        tt = time.time()

        timeago = tt - self.lastcall

        if self.lastcall and DEBUG>2:
            print >>sys.stderr, "Lastcall: %s seconds ago." % lastcall

        if timeago <= self.wait:
            if DEBUG>0: print >>sys.stderr, "Waiting %s seconds." % self.wait
            time.sleep(self.wait)
            self.waited += 1
            self.lastcall = tt + self.wait
        else:
            self.lastcall = tt

Waiter = _Waiter(DLCS_WAIT_TIME)

class PyDeliciousException(Exception):
    '''Std. pydelicious error'''
    pass

class DeliciousError(Exception):
	"""Raised when the server responds with a negative answer"""


class DefaultErrorHandler(urllib2.HTTPDefaultErrorHandler):
    '''@xxx:bvb: Where is this used? should it be registered somewhere with urllib2?

    Handles HTTP Error, currently only 503.
    '''
    def http_error_503(self, req, fp, code, msg, headers):
        raise urllib2.HTTPError(req, code, throttled_message, headers, fp)


class post(dict):
    """Post object, contains href, description, hash, dt, tags,
    extended, user, count(, shared).

    @xxx:bvb: Is this needed? Right now this is superfluous,
    """
    def __init__(self, href = "", description = "", hash = "", time = "", tag = "", extended = "", user = "", count = "",
                 tags = "", url = "", dt = ""): # tags or tag?
        self["href"] = href
        if url != "": self["href"] = url
        self["description"] = description
        self["hash"] = hash
        self["dt"] = dt
        if time != "": self["dt"] = time
        self["tags"] = tags
        if tag != "":  self["tags"] = tag     # tag or tags? # !! tags
        self["extended"] = extended
        self["user"] = user
        self["count"] = count

    def __getattr__(self, name):
        try: return self[name]
        except: object.__getattribute__(self, name)


class posts(list):
    """@xxx:bvb: idem as class post, python structures (dict/list) might
    suffice or a more generic solution is needed.
    """
    def __init__(self, *args):
        for i in args: self.append(i)

    def __getattr__(self, attr):
        try: return [p[attr] for p in self]
        except: object.__getattribute__(self, attr)

### Utility functions

def str2uni(s):
    # type(in) str or unicode
    # type(out) unicode
    return ("".join([unichr(ord(i)) for i in s]))

def str2utf8(s):
    # type(in) str or unicode
    # type(out) str
    return ("".join([unichr(ord(i)).encode("utf-8") for i in s]))

def str2quote(s):
    return urllib.quote_plus("".join([unichr(ord(i)).encode("utf-8") for i in s]))

def dict0(d):
    # Trims empty dict entries
    # {'a':'a', 'b':'', 'c': 'c'} => {'a': 'a', 'c': 'c'}
    dd = dict()
    for i in d:
            if d[i] != "": dd[i] = d[i]
    return dd

def delicious_datetime(str):
    """Parse a ISO 8601 formatted string to a Python datetime ...
    """
    return datetime.datetime(*time.strptime(str, ISO_8601_DATETIME)[0:6])

def http_request(url, user_agent=USER_AGENT, retry=4):
    """Retrieve the contents referenced by the URL using urllib2.

    Retries up to four times (default) on exceptions.
    """
    request = urllib2.Request(url, headers={'User-Agent':user_agent})

    # Remember last error
    e = None

    # Repeat request on time-out errors
    tries = retry;
    while tries:
        try:
            return urllib2.urlopen(request)

        except urllib2.HTTPError, e: # protocol errors,
            raise PyDeliciousException, "%s" % e

        except urllib2.URLError, e:
            # @xxx: Ugly check for time-out errors
			#if len(e)>0 and 'timed out' in arg[0]:
			print >> sys.stderr, "%s, %s tries left." % (e, tries)
			Waiter()
			tries = tries - 1
			#else:
			#	tries = None

    # Give up
    raise PyDeliciousException, \
            "Unable to retrieve data at '%s', %s" % (url, e)

def http_auth_request(url, host, user, passwd, user_agent=USER_AGENT):
    """Call an HTTP server with authorization credentials using urllib2.
    """
    if DEBUG: httplib.HTTPConnection.debuglevel = 1

    # Hook up handler/opener to urllib2
    password_manager = urllib2.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(None, host, user, passwd)
    auth_handler = urllib2.HTTPBasicAuthHandler(password_manager)
    opener = urllib2.build_opener(auth_handler)
    urllib2.install_opener(opener)

    return http_request(url, user_agent)

def dlcs_api_request(path, params='', user='', passwd='', throttle=True):
    """Retrieve/query a path within the del.icio.us API.

    This implements a minimum interval between calls to avoid
    throttling. [#]_ Use param 'throttle' to turn this behaviour off.

    @todo: back off on 503's (HTTPError, URLError? @todo: testing).

    Returned XML does not always correspond with given del.icio.us examples
    @todo: (cf. help/api/... and post's attributes)

    .. [#] http://del.icio.us/help/api/
    """
    if throttle:
        Waiter()

    if params:
        # params come as a dict, strip empty entries and urlencode
        url = "%s/%s?%s" % (DLCS_API, path, urllib.urlencode(dict0(params)))
    else:
        url = "%s/%s" % (DLCS_API, path)

    if DEBUG: print >>sys.stderr, "dlcs_api_request: %s" % url

    try:
        return http_auth_request(url, DLCS_API_HOST, user, passwd, USER_AGENT)

    # @bvb: Is this ever raised? When?
    except DefaultErrorHandler, e:
        print >>sys.stderr, "%s" % e

def dlcs_parse_xml(data, split_tags=False):
    """Parse any del.icio.us XML document and return Python data structure.

    Recognizes all XML document formats as returned by the version 1 API and
    translates to a JSON-like data structure (dicts 'n lists).

    Returned instance is always a dictionary. Examples::

     {'posts': [{'url':'...','hash':'...',},],}
     {'tags':['tag1', 'tag2',]}
     {'dates': [{'count':'...','date':'...'},], 'tag':'', 'user':'...'}
	 {'result':(True, "done")}
     # etcetera.
    """

    if DEBUG>3: print >>sys.stderr, "dlcs_parse_xml: parsing from ", data

    if not hasattr(data, 'read'):
        data = StringIO(data)

    doc = parse_xml(data)
    root = doc.getroot()
    fmt = root.tag

	# Split up into three cases: Data, Result or Update
    if fmt in ('tags', 'posts', 'dates', 'bundles'):

        # Data: expect a list of data elements, 'resources'.
        # Use `fmt` (without last 's') to find data elements, elements
        # don't have contents, attributes contain all the data we need:
        # append to list
        elist = [el.attrib for el in doc.findall(fmt[:-1])]

        # Return list in dict, use tagname of rootnode as keyname.
        data = {fmt: elist}

        # Root element might have attributes too, append dict.
        data.update(root.attrib)

        return data

    elif fmt == 'result':

        # Result: answer to operations
        if root.attrib.has_key('code'):
            msg = root.attrib['code']
        else:
            msg = root.text

		# Return {'result':(True, msg)} for /known/ O.K. messages,
        # use (False, msg) otherwise
        v = msg in DLCS_OK_MESSAGES
        return {fmt: (v, msg)}

    elif fmt == 'update':

        # Update: "time"
        #return {fmt: root.attrib}
		return {fmt: {'time':time.strptime(root.attrib['time'], ISO_8601_DATETIME)}}

    else:
        raise PyDeliciousException, "Unknown XML document format '%s'" % fmt

def dlcs_rss_request(tag = "", popular = 0, user = "", url = ''):
    """Handle a request for RSS

    @todo: translate from German

    rss sollte nun wieder funktionieren, aber diese try, except scheisse ist so nicht schoen

    rss wird unterschiedlich zusammengesetzt. ich kann noch keinen einheitlichen zusammenhang
    zwischen daten (url, desc, ext, usw) und dem feed erkennen. warum k[o]nnen die das nicht einheitlich machen?
    """
    tag = str2quote(tag)
    user = str2quote(user)
    if url != '':
        # http://del.icio.us/rss/url/efbfb246d886393d48065551434dab54
        url = DLCS_RSS + '''url/%s'''%md5.new(url).hexdigest()
    elif user != '' and tag != '':
        url = DLCS_RSS + '''%(user)s/%(tag)s'''%dict(user=user, tag=tag)
    elif user != '' and tag == '':
        # http://del.icio.us/rss/delpy
        url = DLCS_RSS + '''%s'''%user
    elif popular == 0 and tag == '':
        url = DLCS_RSS
    elif popular == 0 and tag != '':
        # http://del.icio.us/rss/tag/apple
        # http://del.icio.us/rss/tag/web2.0
        url = DLCS_RSS + "tag/%s"%tag
    elif popular == 1 and tag == '':
        url = DLCS_RSS + '''popular/'''
    elif popular == 1 and tag != '':
        url = DLCS_RSS + '''popular/%s'''%tag
    rss = http_request(url).read()
    rss = feedparser.parse(rss)
    # print rss
#     for e in rss.entries: print e;print
    l = posts()
    for e in rss.entries:
        if e.has_key("links") and e["links"]!=[] and e["links"][0].has_key("href"):
            url = e["links"][0]["href"]
        elif e.has_key("link"):
            url = e["link"]
        elif e.has_key("id"):
            url = e["id"]
        else:
            url = ""
        if e.has_key("title"):
            description = e['title']
        elif e.has_key("title_detail") and e["title_detail"].has_key("title"):
            description = e["title_detail"]['value']
        else:
            description = ''
        try: tags = e['categories'][0][1]
        except:
            try: tags = e["category"]
            except: tags = ""
        if e.has_key("modified"):
            dt = e['modified']
        else:
            dt = ""
        if e.has_key("summary"):
            extended = e['summary']
        elif e.has_key("summary_detail"):
            e['summary_detail']["value"]
        else:
            extended = ""
        if e.has_key("author"):
            user = e['author']
        else:
            user = ""
#  time = dt ist weist auf ein problem hin
# die benennung der variablen ist nicht einheitlich
#  api senden und
#  xml bekommen sind zwei verschiedene schuhe :(
        l.append(post(url = url, description = description, tags = tags, dt = dt, extended = extended, user = user))
    return l


### Main module class

class DeliciousAPI:
    """Class providing main interace to del.icio.us API.

    Methods ``request`` and ``request_raw`` represent the core. For all API
    paths there are furthermore methods (e.g. posts_add for 'posts/all') with
    an explicit declaration of the parameters and documentation. These all call
    ``request`` and pass on extra keywords like ``_raw``.
    """

    def __init__(self, user, passwd, codec='iso-8859-1', api_request=dlcs_api_request, xml_parser=dlcs_parse_xml):
        """Initialize access to the API with ``user`` and ``passwd``.

        ``codec`` sets the encoding of the arguments.

        The ``api_request`` and ``xml_parser`` parameters by default point to
        functions within this package with standard implementations to
        request and parse a resource. See ``dlcs_api_request()`` and
        ``dlcs_parse_xml()``. Note that ``api_request`` should return a
        file-like instance with an HTTPMessage instance under ``info()``,
        see ``urllib2.openurl`` for more info.
        """
        assert user != ""
        self.user = user
        self.passwd = passwd
        self.codec = codec

        # Implement communication to server and parsing of respons messages:
        assert callable(api_request)
        self._api_request = api_request
        assert callable(xml_parser)
        self._parse_response = xml_parser

    def _call_server(self, path, **params):
        params = dict0(params)
        for key in params:
            params[key] = params[key].encode(self.codec)

        # see __init__ for _api_request()
        return self._api_request(path, params, self.user, self.passwd)


    ### Core functionality

    def request(self, path, _raw=False, **params):
        """Calls a path in the API, parses the answer to a JSON-like structure by
        default. Use with ``_raw=True`` or ``call request_raw()`` directly to
        get the filehandler and process the response message manually.

        Calls to some paths will return a `result` message, i.e.::

            <result code="..." />

        or::

            <result>...</result>

        These are all parsed to ``{'result':(Boolean, MessageString)}`` and this
        method will raise ``DeliciousError`` on negative `result` answers. Using
        ``_raw=True`` bypasses all parsing and will never raise ``DeliciousError``.

        See ``dlcs_parse_xml()`` and ``self.request_raw()``."""

        # method _parse_response is bound in `__init__()`, `_call_server`
        # uses `_api_request` also set in `__init__()`
        if _raw:
            # return answer
            return self.request_raw(path, **params)

        else:
            # get answer and parse
            fl = self._call_server(path, **params)
            rs = self._parse_response(fl)

			# Raise an error for negative 'result' answers
            if type(rs) == dict and rs == 'result' and not rs['result'][0]:
                errmsg = ""
                if len(rs['result'])>0:
                    errmsg = rs['result'][1:]
                raise DeliciousError, errmsg

            return rs

    def request_raw(self, path, **params):
        """Calls the path in the API, returns the filehandle. Returned
        file-like instances have an ``HTTPMessage`` instance with HTTP header
        information available. Use ``filehandle.info()`` or refer to the
        ``urllib2.openurl`` documentation.
        """
        # see `request()` on how the response can be handled
        return self._call_server(path, **params)

    ### Explicit declarations of API paths, their parameters and docs

    # Tags
    def tags_get(self, **kwds):
        """Returns a list of tags and the number of times it is used by the user.
        ::

            <tags>
                <tag tag="TagName" count="888">
        """
        return self.request("tags/get", **kwds)

    def tags_rename(self, old, new, **kwds):
        """Rename an existing tag with a new tag name. Returns a `result`
        message or raises an ``DeliciousError``. See ``self.request()``.

        &old (required)
            Tag to rename.
        &new (required)
            New name.
        """
        return self.request("tags/rename", old=old, new=new, **kwds)

    # Posts
    def posts_update(self, **kwds):
        """Returns the last update time for the user. Use this before calling
        `posts_all` to see if the data has changed since the last fetch.
        ::

            <update time="CCYY-MM-DDThh:mm:ssZ">
		"""
        return self.request("posts/update", **kwds)

    def posts_dates(self, tag="", **kwds):
        """Returns a list of dates with the number of posts at each date.
        ::

            <dates>
                <date date="CCYY-MM-DD" count="888">

        &tag (optional).
            Filter by this tag.
        """
        return self.request("posts/dates", tag=tag, **kwds)

    def posts_get(self, tag="", dt="", url="", **kwds):
        """Returns posts matching the arguments. If no date or url is given,
        most recent date will be used.
        ::

            <posts dt="CCYY-MM-DD" tag="..." user="...">
                <post ...>

        &tag (optional).
            Filter by this tag.
        &dt (optional).
            Filter by this date (CCYY-MM-DDThh:mm:ssZ).
        &url (optional).
            Filter by this url.
        """
        return self.request("posts/get", tag=tag, dt=dt, url=url, **kwds)

    def posts_recent(self, tag="", count="", **kwds):
        """Returns a list of the most recent posts, filtered by argument.
        ::

            <posts tag="..." user="...">
                <post ...>

        &tag (optional).
            Filter by this tag.
        &count (optional).
            Number of items to retrieve (Default:15, Maximum:100).
        """
        return self.request("posts/recent", tag=tag, count=count, **kwds)

    def posts_all(self, tag="", **kwds):
        """Returns all posts. Please use sparingly. Call the `posts_update`
        method to see if you need to fetch this at all.
        ::

            <posts tag="..." user="..." update="CCYY-MM-DDThh:mm:ssZ">
                <post ...>

        &tag (optional).
            Filter by this tag.
        """
        return self.request("posts/all", tag=tag, **kwds)

    def posts_add(self, url, description, extended="", tags="", dt="",
            replace="no", shared="yes", **kwds):
        """Add a post to del.icio.us. Returns a `result` message or raises an
        ``DeliciousError``. See ``self.request()``.

        &url (required)
            the url of the item.
        &description (required)
            the description of the item.
        &extended (optional)
            notes for the item.
        &tags (optional)
            tags for the item (space delimited).
        &dt (optional)
            datestamp of the item (format "CCYY-MM-DDThh:mm:ssZ").

        Requires a LITERAL "T" and "Z" like in ISO8601 at http://www.cl.cam.ac.uk/~mgk25/iso-time.html for example: "1984-09-01T14:21:31Z"
        &replace=no (optional) - don't replace post if given url has already been posted.
        &shared=no (optional) - make the item private
        """
        return self.request("posts/add", url=url, description=description,
                extended=extended, tags=tags, dt=dt,
                replace=replace, shared=shared, **kwds)

    def posts_delete(self, url, **kwds):
        """Delete a post from del.icio.us. Returns a `result` message or
        raises an ``DeliciousError``. See ``self.request()``.

        &url (required)
            the url of the item.
        """
        return self.request("posts/delete", url=url, **kwds)

    # Bundles
    def bundles_all(self, **kwds):
        """Retrieve user bundles from del.icio.us.
        ::

            <bundles>
                <bundel name="..." tags=...">
        """
        return self.request("tags/bundles/all", **kwds)

    def bundles_set(self, bundle, tags, **kwds):
        """Assign a set of tags to a single bundle, wipes away previous
        settings for bundle. Returns a `result` messages or raises an
        ``DeliciousError``. See ``self.request()``.

        &bundle (required)
            the bundle name.
        &tags (required)
            list of tags (space seperated).
        """
        if type(tags)==list:
            tags = " ".join(tags)
        return self.request("tags/bundles/set", bundle=bundle, tags=tags,
                **kwds)

    def bundles_delete(self, bundle, **kwds):
        """Delete a bundle from del.icio.us. Returns a `result` message or
        raises an ``DeliciousError``. See ``self.request()``.

        &bundle (required)
            the bundle name.
        """
        return self.request("tags/bundles/delete", bundle=bundle, **kwds)

    ### Utils

    # Lookup table for del.icio.us url-path to DeliciousAPI method.
    paths = {
        'tags/get': tags_get,
        'tags/rename': tags_rename,
        'posts/update': posts_update,
        'posts/dates': posts_dates,
        'posts/get': posts_get,
        'posts/recent': posts_recent,
        'posts/all': posts_all,
        'posts/add': posts_add,
        'posts/delete': posts_delete,
        'tags/bundles/all': bundles_all,
        'tags/bundles/set': bundles_set,
        'tags/bundles/delete': bundles_delete,
    }

    def get_url(self, url):
        """Return the del.icio.us url at which the HTML page with posts for
        ``url`` can be found.
        """
        return "http://del.icio.us/url/?url=%s" % (url,)


### Convenience functions on this package

def apiNew(user, passwd):
    """creates a new DeliciousAPI object.
    requires user(name) and passwd
	"""
    return DeliciousAPI(user=user, passwd=passwd)

def add(user, passwd, url, description, tags="", extended="", dt="", replace="no"):
    return apiNew(user, passwd).posts_add(url=url, description=description, extended=extended, tags=tags, dt=dt, replace=replace)

def get(user, passwd, tag="", dt="",  count = 0):
    posts = apiNew(user, passwd).posts_get(tag=tag,dt=dt)
    if count != 0: posts = posts[0:count]
    return posts

def get_all(user, passwd, tag=""):
    return apiNew(user, passwd).posts_all(tag=tag)

def delete(user, passwd, url):
    return apiNew(user, passwd).posts_delete(url=url)

def rename_tag(user, passwd, oldtag, newtag):
    return apiNew(user=user, passwd=passwd).tags_rename(old=oldtag, new=newtag)

def get_tags(user, passwd):
    return apiNew(user=user, passwd=passwd).tags_get()


### RSS functions @bvb: still working...?
def getrss(tag="", popular=0, url='', user=""):
    """get posts from del.icio.us via parsing RSS @bvb[or HTML]

	@bvb[not tested]

    tag (opt) sort by tag
    popular (opt) look for the popular stuff
    user (opt) get the posts by a user, this striks popular
    url (opt) get the posts by url
	"""
    return dlcs_rss_request(tag=tag, popular=popular, user=user, url=url)

def get_userposts(user):
    return getrss(user = user)

def get_tagposts(tag):
    return getrss(tag = tag)

def get_urlposts(url):
    return getrss(url = url)

def get_popular(tag = ""):
    return getrss(tag = tag, popular = 1)


### @TODO: implement JSON fetching
def json_posts(user, count=15):
    """http://del.icio.us/feeds/json/mpe
    http://del.icio.us/feeds/json/mpe/art+history
    count=###   the number of posts you want to get (default is 15, maximum is 100)
    raw         a raw JSON object is returned, instead of an object named Delicious.posts
    """

def json_tags(user, atleast, count, sort='alpha'):
    """http://del.icio.us/feeds/json/tags/mpe
    atleast=###         include only tags for which there are at least ### number of posts
    count=###           include ### tags, counting down from the top
    sort={alpha|count}  construct the object with tags in alphabetic order (alpha), or by count of posts (count)
    callback=NAME       wrap the object definition in a function call NAME(...), thus invoking that function when the feed is executed
    raw                 a pure JSON object is returned, instead of code that will construct an object named Delicious.tags
    """

def json_network(user):
    """http://del.icio.us/feeds/json/network/mpe
    callback=NAME       wrap the object definition in a function call NAME(...)
    ?raw         a raw JSON object is returned, instead of an object named Delicious.posts
    """

def json_fans(user):
    """http://del.icio.us/feeds/json/fans/mpe
    callback=NAME       wrap the object definition in a function call NAME(...)
    ?raw         a pure JSON object is returned, instead of an object named Delicious.
    """


########NEW FILE########
__FILENAME__ = recommendations
# A dictionary of movie critics and their ratings of a small
# set of movies
critics={'Lisa Rose': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.5,
 'Just My Luck': 3.0, 'Superman Returns': 3.5, 'You, Me and Dupree': 2.5, 
 'The Night Listener': 3.0},
'Gene Seymour': {'Lady in the Water': 3.0, 'Snakes on a Plane': 3.5, 
 'Just My Luck': 1.5, 'Superman Returns': 5.0, 'The Night Listener': 3.0, 
 'You, Me and Dupree': 3.5}, 
'Michael Phillips': {'Lady in the Water': 2.5, 'Snakes on a Plane': 3.0,
 'Superman Returns': 3.5, 'The Night Listener': 4.0},
'Claudia Puig': {'Snakes on a Plane': 3.5, 'Just My Luck': 3.0,
 'The Night Listener': 4.5, 'Superman Returns': 4.0, 
 'You, Me and Dupree': 2.5},
'Mick LaSalle': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0, 
 'Just My Luck': 2.0, 'Superman Returns': 3.0, 'The Night Listener': 3.0,
 'You, Me and Dupree': 2.0}, 
'Jack Matthews': {'Lady in the Water': 3.0, 'Snakes on a Plane': 4.0,
 'The Night Listener': 3.0, 'Superman Returns': 5.0, 'You, Me and Dupree': 3.5},
'Toby': {'Snakes on a Plane':4.5,'You, Me and Dupree':1.0,'Superman Returns':4.0}}


from math import sqrt

# Returns a distance-based similarity score for person1 and person2
def sim_distance(prefs,person1,person2):
  # Get the list of shared_items
  si={}
  for item in prefs[person1]: 
    if item in prefs[person2]: si[item]=1

  # if they have no ratings in common, return 0
  if len(si)==0: return 0

  # Add up the squares of all the differences
  sum_of_squares=sum([pow(prefs[person1][item]-prefs[person2][item],2) 
                      for item in prefs[person1] if item in prefs[person2]])

  return 1/(1+sum_of_squares)

# Returns the Pearson correlation coefficient for p1 and p2
def sim_pearson(prefs,p1,p2):
  # Get the list of mutually rated items
  si={}
  for item in prefs[p1]: 
    if item in prefs[p2]: si[item]=1

  # if they are no ratings in common, return 0
  if len(si)==0: return 0

  # Sum calculations
  n=len(si)
  
  # Sums of all the preferences
  sum1=sum([prefs[p1][it] for it in si])
  sum2=sum([prefs[p2][it] for it in si])
  
  # Sums of the squares
  sum1Sq=sum([pow(prefs[p1][it],2) for it in si])
  sum2Sq=sum([pow(prefs[p2][it],2) for it in si])	
  
  # Sum of the products
  pSum=sum([prefs[p1][it]*prefs[p2][it] for it in si])
  
  # Calculate r (Pearson score)
  num=pSum-(sum1*sum2/n)
  den=sqrt((sum1Sq-pow(sum1,2)/n)*(sum2Sq-pow(sum2,2)/n))
  if den==0: return 0

  r=num/den

  return r

# Returns the best matches for person from the prefs dictionary. 
# Number of results and similarity function are optional params.
def topMatches(prefs,person,n=5,similarity=sim_pearson):
  scores=[(similarity(prefs,person,other),other) 
                  for other in prefs if other!=person]
  scores.sort()
  scores.reverse()
  return scores[0:n]

# Gets recommendations for a person by using a weighted average
# of every other user's rankings
def getRecommendations(prefs,person,similarity=sim_pearson):
  totals={}
  simSums={}
  for other in prefs:
    # don't compare me to myself
    if other==person: continue
    sim=similarity(prefs,person,other)

    # ignore scores of zero or lower
    if sim<=0: continue
    for item in prefs[other]:
	    
      # only score movies I haven't seen yet
      if item not in prefs[person] or prefs[person][item]==0:
        # Similarity * Score
        totals.setdefault(item,0)
        totals[item]+=prefs[other][item]*sim
        # Sum of similarities
        simSums.setdefault(item,0)
        simSums[item]+=sim

  # Create the normalized list
  rankings=[(total/simSums[item],item) for item,total in totals.items()]

  # Return the sorted list
  rankings.sort()
  rankings.reverse()
  return rankings

def transformPrefs(prefs):
  result={}
  for person in prefs:
    for item in prefs[person]:
      result.setdefault(item,{})
      
      # Flip item and person
      result[item][person]=prefs[person][item]
  return result


def calculateSimilarItems(prefs,n=10):
  # Create a dictionary of items showing which other items they
  # are most similar to.
  result={}
  # Invert the preference matrix to be item-centric
  itemPrefs=transformPrefs(prefs)
  c=0
  for item in itemPrefs:
    # Status updates for large datasets
    c+=1
    if c%100==0: print "%d / %d" % (c,len(itemPrefs))
    # Find the most similar items to this one
    scores=topMatches(itemPrefs,item,n=n,similarity=sim_distance)
    result[item]=scores
  return result

def getRecommendedItems(prefs,itemMatch,user):
  userRatings=prefs[user]
  scores={}
  totalSim={}
  # Loop over items rated by this user
  for (item,rating) in userRatings.items( ):

    # Loop over items similar to this one
    for (similarity,item2) in itemMatch[item]:

      # Ignore if this user has already rated this item
      if item2 in userRatings: continue
      # Weighted sum of rating times similarity
      scores.setdefault(item2,0)
      scores[item2]+=similarity*rating
      # Sum of all the similarities
      totalSim.setdefault(item2,0)
      totalSim[item2]+=similarity

  # Divide each total score by total weighting to get an average
  rankings=[(score/totalSim[item],item) for item,score in scores.items( )]

  # Return the rankings from highest to lowest
  rankings.sort( )
  rankings.reverse( )
  return rankings

def loadMovieLens(path='/data/movielens'):
  # Get movie titles
  movies={}
  for line in open(path+'/u.item'):
    (id,title)=line.split('|')[0:2]
    movies[id]=title
  
  # Load data
  prefs={}
  for line in open(path+'/u.data'):
    (user,movieid,rating,ts)=line.split('\t')
    prefs.setdefault(user,{})
    prefs[user][movies[movieid]]=float(rating)
  return prefs

########NEW FILE########
__FILENAME__ = clusters
from PIL import Image,ImageDraw

def readfile(filename):
  lines=[line for line in file(filename)]
  
  # First line is the column titles
  colnames=lines[0].strip().split('\t')[1:]
  rownames=[]
  data=[]
  for line in lines[1:]:
    p=line.strip().split('\t')
    # First column in each row is the rowname
    rownames.append(p[0])
    # The data for this row is the remainder of the row
    data.append([float(x) for x in p[1:]])
  return rownames,colnames,data


from math import sqrt

def pearson(v1,v2):
  # Simple sums
  sum1=sum(v1)
  sum2=sum(v2)
  
  # Sums of the squares
  sum1Sq=sum([pow(v,2) for v in v1])
  sum2Sq=sum([pow(v,2) for v in v2])	
  
  # Sum of the products
  pSum=sum([v1[i]*v2[i] for i in range(len(v1))])
  
  # Calculate r (Pearson score)
  num=pSum-(sum1*sum2/len(v1))
  den=sqrt((sum1Sq-pow(sum1,2)/len(v1))*(sum2Sq-pow(sum2,2)/len(v1)))
  if den==0: return 0

  return 1.0-num/den

class bicluster:
  def __init__(self,vec,left=None,right=None,distance=0.0,id=None):
    self.left=left
    self.right=right
    self.vec=vec
    self.id=id
    self.distance=distance

def hcluster(rows,distance=pearson):
  distances={}
  currentclustid=-1

  # Clusters are initially just the rows
  clust=[bicluster(rows[i],id=i) for i in range(len(rows))]

  while len(clust)>1:
    lowestpair=(0,1)
    closest=distance(clust[0].vec,clust[1].vec)

    # loop through every pair looking for the smallest distance
    for i in range(len(clust)):
      for j in range(i+1,len(clust)):
        # distances is the cache of distance calculations
        if (clust[i].id,clust[j].id) not in distances: 
          distances[(clust[i].id,clust[j].id)]=distance(clust[i].vec,clust[j].vec)

        d=distances[(clust[i].id,clust[j].id)]

        if d<closest:
          closest=d
          lowestpair=(i,j)

    # calculate the average of the two clusters
    mergevec=[
    (clust[lowestpair[0]].vec[i]+clust[lowestpair[1]].vec[i])/2.0 
    for i in range(len(clust[0].vec))]

    # create the new cluster
    newcluster=bicluster(mergevec,left=clust[lowestpair[0]],
                         right=clust[lowestpair[1]],
                         distance=closest,id=currentclustid)

    # cluster ids that weren't in the original set are negative
    currentclustid-=1
    del clust[lowestpair[1]]
    del clust[lowestpair[0]]
    clust.append(newcluster)

  return clust[0]

def printclust(clust,labels=None,n=0):
  # indent to make a hierarchy layout
  for i in range(n): print ' ',
  if clust.id<0:
    # negative id means that this is branch
    print '-'
  else:
    # positive id means that this is an endpoint
    if labels==None: print clust.id
    else: print labels[clust.id]

  # now print the right and left branches
  if clust.left!=None: printclust(clust.left,labels=labels,n=n+1)
  if clust.right!=None: printclust(clust.right,labels=labels,n=n+1)

def getheight(clust):
  # Is this an endpoint? Then the height is just 1
  if clust.left==None and clust.right==None: return 1

  # Otherwise the height is the same of the heights of
  # each branch
  return getheight(clust.left)+getheight(clust.right)

def getdepth(clust):
  # The distance of an endpoint is 0.0
  if clust.left==None and clust.right==None: return 0

  # The distance of a branch is the greater of its two sides
  # plus its own distance
  return max(getdepth(clust.left),getdepth(clust.right))+clust.distance


def drawdendrogram(clust,labels,jpeg='clusters.jpg'):
  # height and width
  h=getheight(clust)*20
  w=1200
  depth=getdepth(clust)

  # width is fixed, so scale distances accordingly
  scaling=float(w-150)/depth

  # Create a new image with a white background
  img=Image.new('RGB',(w,h),(255,255,255))
  draw=ImageDraw.Draw(img)

  draw.line((0,h/2,10,h/2),fill=(255,0,0))    

  # Draw the first node
  drawnode(draw,clust,10,(h/2),scaling,labels)
  img.save(jpeg,'JPEG')

def drawnode(draw,clust,x,y,scaling,labels):
  if clust.id<0:
    h1=getheight(clust.left)*20
    h2=getheight(clust.right)*20
    top=y-(h1+h2)/2
    bottom=y+(h1+h2)/2
    # Line length
    ll=clust.distance*scaling
    # Vertical line from this cluster to children    
    draw.line((x,top+h1/2,x,bottom-h2/2),fill=(255,0,0))    
    
    # Horizontal line to left item
    draw.line((x,top+h1/2,x+ll,top+h1/2),fill=(255,0,0))    

    # Horizontal line to right item
    draw.line((x,bottom-h2/2,x+ll,bottom-h2/2),fill=(255,0,0))        

    # Call the function to draw the left and right nodes    
    drawnode(draw,clust.left,x+ll,top+h1/2,scaling,labels)
    drawnode(draw,clust.right,x+ll,bottom-h2/2,scaling,labels)
  else:   
    # If this is an endpoint, draw the item label
    draw.text((x+5,y-7),labels[clust.id],(0,0,0))

def rotatematrix(data):
  newdata=[]
  for i in range(len(data[0])):
    newrow=[data[j][i] for j in range(len(data))]
    newdata.append(newrow)
  return newdata

import random

def kcluster(rows,distance=pearson,k=4):
  # Determine the minimum and maximum values for each point
  ranges=[(min([row[i] for row in rows]),max([row[i] for row in rows])) 
  for i in range(len(rows[0]))]

  # Create k randomly placed centroids
  clusters=[[random.random()*(ranges[i][1]-ranges[i][0])+ranges[i][0] 
  for i in range(len(rows[0]))] for j in range(k)]
  
  lastmatches=None
  for t in range(100):
    print 'Iteration %d' % t
    bestmatches=[[] for i in range(k)]
    
    # Find which centroid is the closest for each row
    for j in range(len(rows)):
      row=rows[j]
      bestmatch=0
      for i in range(k):
        d=distance(clusters[i],row)
        if d<distance(clusters[bestmatch],row): bestmatch=i
      bestmatches[bestmatch].append(j)

    # If the results are the same as last time, this is complete
    if bestmatches==lastmatches: break
    lastmatches=bestmatches
    
    # Move the centroids to the average of their members
    for i in range(k):
      avgs=[0.0]*len(rows[0])
      if len(bestmatches[i])>0:
        for rowid in bestmatches[i]:
          for m in range(len(rows[rowid])):
            avgs[m]+=rows[rowid][m]
        for j in range(len(avgs)):
          avgs[j]/=len(bestmatches[i])
        clusters[i]=avgs
      
  return bestmatches

def tanamoto(v1,v2):
  c1,c2,shr=0,0,0
  
  for i in range(len(v1)):
    if v1[i]!=0: c1+=1 # in v1
    if v2[i]!=0: c2+=1 # in v2
    if v1[i]!=0 and v2[i]!=0: shr+=1 # in both
  
  return 1.0-(float(shr)/(c1+c2-shr))

def scaledown(data,distance=pearson,rate=0.01):
  n=len(data)

  # The real distances between every pair of items
  realdist=[[distance(data[i],data[j]) for j in range(n)] 
             for i in range(0,n)]

  # Randomly initialize the starting points of the locations in 2D
  loc=[[random.random(),random.random()] for i in range(n)]
  fakedist=[[0.0 for j in range(n)] for i in range(n)]
  
  lasterror=None
  for m in range(0,1000):
    # Find projected distances
    for i in range(n):
      for j in range(n):
        fakedist[i][j]=sqrt(sum([pow(loc[i][x]-loc[j][x],2) 
                                 for x in range(len(loc[i]))]))
  
    # Move points
    grad=[[0.0,0.0] for i in range(n)]
    
    totalerror=0
    for k in range(n):
      for j in range(n):
        if j==k: continue
        # The error is percent difference between the distances
        errorterm=(fakedist[j][k]-realdist[j][k])/realdist[j][k]
        
        # Each point needs to be moved away from or towards the other
        # point in proportion to how much error it has
        grad[k][0]+=((loc[k][0]-loc[j][0])/fakedist[j][k])*errorterm
        grad[k][1]+=((loc[k][1]-loc[j][1])/fakedist[j][k])*errorterm

        # Keep track of the total error
        totalerror+=abs(errorterm)
    print totalerror

    # If the answer got worse by moving the points, we are done
    if lasterror and lasterror<totalerror: break
    lasterror=totalerror
    
    # Move each of the points by the learning rate times the gradient
    for k in range(n):
      loc[k][0]-=rate*grad[k][0]
      loc[k][1]-=rate*grad[k][1]

  return loc

def draw2d(data,labels,jpeg='mds2d.jpg'):
  img=Image.new('RGB',(2000,2000),(255,255,255))
  draw=ImageDraw.Draw(img)
  for i in range(len(data)):
    x=(data[i][0]+0.5)*1000
    y=(data[i][1]+0.5)*1000
    draw.text((x,y),labels[i],(0,0,0))
  img.save(jpeg,'JPEG')  

########NEW FILE########
__FILENAME__ = downloadzebodata
from BeautifulSoup import BeautifulSoup
import urllib2
import re
chare=re.compile(r'[!-\.&]')
itemowners={}

# Words to remove
dropwords=['a','new','some','more','my','own','the','many','other','another']

currentuser=0
for i in range(1,51):
  # URL for the want search page
  c=urllib2.urlopen(
  'http://member.zebo.com/Main?event_key=USERSEARCH&wiowiw=wiw&keyword=car&page=%d'
  % (i))
  soup=BeautifulSoup(c.read())
  for td in soup('td'):
    # Find table cells of bgverdanasmall class
    if ('class' in dict(td.attrs) and td['class']=='bgverdanasmall'):
      items=[re.sub(chare,'',str(a.contents[0]).lower()).strip() for a in td('a')]
      for item in items:
        # Remove extra words
        txt=' '.join([t for t in item.split(' ') if t not in dropwords])
        if len(txt)<2: continue
        itemowners.setdefault(txt,{})
        itemowners[txt][currentuser]=1
      currentuser+=1
      
out=file('zebo.txt','w')
out.write('Item')
for user in range(0,currentuser): out.write('\tU%d' % user)
out.write('\n')
for item,owners in itemowners.items():
  if len(owners)>10:
    out.write(item)
    for user in range(0,currentuser):
      if user in owners: out.write('\t1')
      else: out.write('\t0')
    out.write('\n')

########NEW FILE########
__FILENAME__ = generatefeedvector
import feedparser
import re

# Returns title and dictionary of word counts for an RSS feed
def getwordcounts(url):
  # Parse the feed
  d=feedparser.parse(url)
  wc={}

  # Loop over all the entries
  for e in d.entries:
    if 'summary' in e: summary=e.summary
    else: summary=e.description

    # Extract a list of words
    words=getwords(e.title+' '+summary)
    for word in words:
      wc.setdefault(word,0)
      wc[word]+=1
  return d.feed.title,wc

def getwords(html):
  # Remove all the HTML tags
  txt=re.compile(r'<[^>]+>').sub('',html)

  # Split words by all non-alpha characters
  words=re.compile(r'[^A-Z^a-z]+').split(txt)

  # Convert to lowercase
  return [word.lower() for word in words if word!='']


apcount={}
wordcounts={}
feedlist=[line for line in file('feedlist.txt')]
for feedurl in feedlist:
  try:
    title,wc=getwordcounts(feedurl)
    wordcounts[title]=wc
    for word,count in wc.items():
      apcount.setdefault(word,0)
      if count>1:
        apcount[word]+=1
  except:
    print 'Failed to parse feed %s' % feedurl

wordlist=[]
for w,bc in apcount.items():
  frac=float(bc)/len(feedlist)
  if frac>0.1 and frac<0.5:
    wordlist.append(w)

out=file('blogdata1.txt','w')
out.write('Blog')
for word in wordlist: out.write('\t%s' % word)
out.write('\n')
for blog,wc in wordcounts.items():
  print blog
  out.write(blog)
  for word in wordlist:
    if word in wc: out.write('\t%d' % wc[word])
    else: out.write('\t0')
  out.write('\n')

########NEW FILE########
__FILENAME__ = nn
from math import tanh
from pysqlite2 import dbapi2 as sqlite

def dtanh(y):
    return 1.0-y*y

class searchnet:
    def __init__(self,dbname):
      self.con=sqlite.connect(dbname)
  
    def __del__(self):
      self.con.close()

    def maketables(self):
      self.con.execute('create table hiddennode(create_key)')
      self.con.execute('create table wordhidden(fromid,toid,strength)')
      self.con.execute('create table hiddenurl(fromid,toid,strength)')
      self.con.commit()

    def getstrength(self,fromid,toid,layer):
      if layer==0: table='wordhidden'
      else: table='hiddenurl'
      res=self.con.execute('select strength from %s where fromid=%d and toid=%d' % (table,fromid,toid)).fetchone()
      if res==None: 
          if layer==0: return -0.2
          if layer==1: return 0
      return res[0]

    def setstrength(self,fromid,toid,layer,strength):
      if layer==0: table='wordhidden'
      else: table='hiddenurl'
      res=self.con.execute('select rowid from %s where fromid=%d and toid=%d' % (table,fromid,toid)).fetchone()
      if res==None: 
        self.con.execute('insert into %s (fromid,toid,strength) values (%d,%d,%f)' % (table,fromid,toid,strength))
      else:
        rowid=res[0]
        self.con.execute('update %s set strength=%f where rowid=%d' % (table,strength,rowid))

    def generatehiddennode(self,wordids,urls):
      if len(wordids)>3: return None
      # Check if we already created a node for this set of words
      sorted_words=[str(id) for id in wordids]
      sorted_words.sort()
      createkey='_'.join(sorted_words)
      res=self.con.execute(
      "select rowid from hiddennode where create_key='%s'" % createkey).fetchone()

      # If not, create it
      if res==None:
        cur=self.con.execute(
        "insert into hiddennode (create_key) values ('%s')" % createkey)
        hiddenid=cur.lastrowid
        # Put in some default weights
        for wordid in wordids:
          self.setstrength(wordid,hiddenid,0,1.0/len(wordids))
        for urlid in urls:
          self.setstrength(hiddenid,urlid,1,0.1)
        self.con.commit()

    def getallhiddenids(self,wordids,urlids):
      l1={}
      for wordid in wordids:
        cur=self.con.execute(
        'select toid from wordhidden where fromid=%d' % wordid)
        for row in cur: l1[row[0]]=1
      for urlid in urlids:
        cur=self.con.execute(
        'select fromid from hiddenurl where toid=%d' % urlid)
        for row in cur: l1[row[0]]=1
      return l1.keys()

    def setupnetwork(self,wordids,urlids):
        # value lists
        self.wordids=wordids
        self.hiddenids=self.getallhiddenids(wordids,urlids)
        self.urlids=urlids
 
        # node outputs
        self.ai = [1.0]*len(self.wordids)
        self.ah = [1.0]*len(self.hiddenids)
        self.ao = [1.0]*len(self.urlids)
        
        # create weights matrix
        self.wi = [[self.getstrength(wordid,hiddenid,0) 
                    for hiddenid in self.hiddenids] 
                   for wordid in self.wordids]
        self.wo = [[self.getstrength(hiddenid,urlid,1) 
                    for urlid in self.urlids] 
                   for hiddenid in self.hiddenids]

    def feedforward(self):
        # the only inputs are the query words
        for i in range(len(self.wordids)):
            self.ai[i] = 1.0

        # hidden activations
        for j in range(len(self.hiddenids)):
            sum = 0.0
            for i in range(len(self.wordids)):
                sum = sum + self.ai[i] * self.wi[i][j]
            self.ah[j] = tanh(sum)

        # output activations
        for k in range(len(self.urlids)):
            sum = 0.0
            for j in range(len(self.hiddenids)):
                sum = sum + self.ah[j] * self.wo[j][k]
            self.ao[k] = tanh(sum)

        return self.ao[:]

    def getresult(self,wordids,urlids):
      self.setupnetwork(wordids,urlids)
      return self.feedforward()

    def backPropagate(self, targets, N=0.5):
        # calculate errors for output
        output_deltas = [0.0] * len(self.urlids)
        for k in range(len(self.urlids)):
            error = targets[k]-self.ao[k]
            output_deltas[k] = dtanh(self.ao[k]) * error

        # calculate errors for hidden layer
        hidden_deltas = [0.0] * len(self.hiddenids)
        for j in range(len(self.hiddenids)):
            error = 0.0
            for k in range(len(self.urlids)):
                error = error + output_deltas[k]*self.wo[j][k]
            hidden_deltas[j] = dtanh(self.ah[j]) * error

        # update output weights
        for j in range(len(self.hiddenids)):
            for k in range(len(self.urlids)):
                change = output_deltas[k]*self.ah[j]
                self.wo[j][k] = self.wo[j][k] + N*change

        # update input weights
        for i in range(len(self.wordids)):
            for j in range(len(self.hiddenids)):
                change = hidden_deltas[j]*self.ai[i]
                self.wi[i][j] = self.wi[i][j] + N*change

    def trainquery(self,wordids,urlids,selectedurl): 
      # generate a hidden node if necessary
      self.generatehiddennode(wordids,urlids)

      self.setupnetwork(wordids,urlids)      
      self.feedforward()
      targets=[0.0]*len(urlids)
      targets[urlids.index(selectedurl)]=1.0
      error = self.backPropagate(targets)
      self.updatedatabase()

    def updatedatabase(self):
      # set them to database values
      for i in range(len(self.wordids)):
          for j in range(len(self.hiddenids)):
              self.setstrength(self.wordids[i],self. hiddenids[j],0,self.wi[i][j])
      for j in range(len(self.hiddenids)):
          for k in range(len(self.urlids)):
              self.setstrength(self.hiddenids[j],self.urlids[k],1,self.wo[j][k])
      self.con.commit()

########NEW FILE########
__FILENAME__ = searchengine
import urllib2
from BeautifulSoup import *
from urlparse import urljoin
from pysqlite2 import dbapi2 as sqlite
import nn
mynet=nn.searchnet('nn.db')

# Create a list of words to ignore
ignorewords={'the':1,'of':1,'to':1,'and':1,'a':1,'in':1,'is':1,'it':1}


class crawler:
  # Initialize the crawler with the name of database
  def __init__(self,dbname):
    self.con=sqlite.connect(dbname)
  
  def __del__(self):
    self.con.close()

  def dbcommit(self):
    self.con.commit()

  # Auxilliary function for getting an entry id and adding 
  # it if it's not present
  def getentryid(self,table,field,value,createnew=True):
    cur=self.con.execute(
    "select rowid from %s where %s='%s'" % (table,field,value))
    res=cur.fetchone()
    if res==None:
      cur=self.con.execute(
      "insert into %s (%s) values ('%s')" % (table,field,value))
      return cur.lastrowid
    else:
      return res[0] 


  # Index an individual page
  def addtoindex(self,url,soup):
    if self.isindexed(url): return
    print 'Indexing '+url
  
    # Get the individual words
    text=self.gettextonly(soup)
    words=self.separatewords(text)
    
    # Get the URL id
    urlid=self.getentryid('urllist','url',url)
    
    # Link each word to this url
    for i in range(len(words)):
      word=words[i]
      if word in ignorewords: continue
      wordid=self.getentryid('wordlist','word',word)
      self.con.execute("insert into wordlocation(urlid,wordid,location) values (%d,%d,%d)" % (urlid,wordid,i))
  

  
  # Extract the text from an HTML page (no tags)
  def gettextonly(self,soup):
    v=soup.string
    if v==Null:   
      c=soup.contents
      resulttext=''
      for t in c:
        subtext=self.gettextonly(t)
        resulttext+=subtext+'\n'
      return resulttext
    else:
      return v.strip()

  # Seperate the words by any non-whitespace character
  def separatewords(self,text):
    splitter=re.compile('\\W*')
    return [s.lower() for s in splitter.split(text) if s!='']

    
  # Return true if this url is already indexed
  def isindexed(self,url):
    return False
  
  # Add a link between two pages
  def addlinkref(self,urlFrom,urlTo,linkText):
    words=self.separateWords(linkText)
    fromid=self.getentryid('urllist','url',urlFrom)
    toid=self.getentryid('urllist','url',urlTo)
    if fromid==toid: return
    cur=self.con.execute("insert into link(fromid,toid) values (%d,%d)" % (fromid,toid))
    linkid=cur.lastrowid
    for word in words:
      if word in ignorewords: continue
      wordid=self.getentryid('wordlist','word',word)
      self.con.execute("insert into linkwords(linkid,wordid) values (%d,%d)" % (linkid,wordid))

  # Starting with a list of pages, do a breadth
  # first search to the given depth, indexing pages
  # as we go
  def crawl(self,pages,depth=2):
    for i in range(depth):
      newpages={}
      for page in pages:
        try:
          c=urllib2.urlopen(page)
        except:
          print "Could not open %s" % page
          continue
        try:
          soup=BeautifulSoup(c.read())
          self.addtoindex(page,soup)
  
          links=soup('a')
          for link in links:
            if ('href' in dict(link.attrs)):
              url=urljoin(page,link['href'])
              if url.find("'")!=-1: continue
              url=url.split('#')[0]  # remove location portion
              if url[0:4]=='http' and not self.isindexed(url):
                newpages[url]=1
              linkText=self.gettextonly(link)
              self.addlinkref(page,url,linkText)
  
          self.dbcommit()
        except:
          print "Could not parse page %s" % page

      pages=newpages

  
  # Create the database tables
  def createindextables(self): 
    self.con.execute('create table urllist(url)')
    self.con.execute('create table wordlist(word)')
    self.con.execute('create table wordlocation(urlid,wordid,location)')
    self.con.execute('create table link(fromid integer,toid integer)')
    self.con.execute('create table linkwords(wordid,linkid)')
    self.con.execute('create index wordidx on wordlist(word)')
    self.con.execute('create index urlidx on urllist(url)')
    self.con.execute('create index wordurlidx on wordlocation(wordid)')
    self.con.execute('create index urltoidx on link(toid)')
    self.con.execute('create index urlfromidx on link(fromid)')
    self.dbcommit()

  def calculatepagerank(self,iterations=20):
    # clear out the current page rank tables
    self.con.execute('drop table if exists pagerank')
    self.con.execute('create table pagerank(urlid primary key,score)')
    
    # initialize every url with a page rank of 1
    for (urlid,) in self.con.execute('select rowid from urllist'):
      self.con.execute('insert into pagerank(urlid,score) values (%d,1.0)' % urlid)
    self.dbcommit()
    
    for i in range(iterations):
      print "Iteration %d" % (i)
      for (urlid,) in self.con.execute('select rowid from urllist'):
        pr=0.15
        
        # Loop through all the pages that link to this one
        for (linker,) in self.con.execute(
        'select distinct fromid from link where toid=%d' % urlid):
          # Get the page rank of the linker
          linkingpr=self.con.execute(
          'select score from pagerank where urlid=%d' % linker).fetchone()[0]

          # Get the total number of links from the linker
          linkingcount=self.con.execute(
          'select count(*) from link where fromid=%d' % linker).fetchone()[0]
          pr+=0.85*(linkingpr/linkingcount)
        self.con.execute(
        'update pagerank set score=%f where urlid=%d' % (pr,urlid))
      self.dbcommit()

class searcher:
  def __init__(self,dbname):
    self.con=sqlite.connect(dbname)

  def __del__(self):
    self.con.close()

  def getmatchrows(self,q):
    # Strings to build the query
    fieldlist='w0.urlid'
    tablelist=''  
    clauselist=''
    wordids=[]

    # Split the words by spaces
    words=q.split(' ')  
    tablenumber=0

    for word in words:
      # Get the word ID
      wordrow=self.con.execute(
      "select rowid from wordlist where word='%s'" % word).fetchone()
      if wordrow!=None:
        wordid=wordrow[0]
        wordids.append(wordid)
        if tablenumber>0:
          tablelist+=','
          clauselist+=' and '
          clauselist+='w%d.urlid=w%d.urlid and ' % (tablenumber-1,tablenumber)
        fieldlist+=',w%d.location' % tablenumber
        tablelist+='wordlocation w%d' % tablenumber      
        clauselist+='w%d.wordid=%d' % (tablenumber,wordid)
        tablenumber+=1

    # Create the query from the separate parts
    fullquery='select %s from %s where %s' % (fieldlist,tablelist,clauselist)
    print fullquery
    cur=self.con.execute(fullquery)
    rows=[row for row in cur]

    return rows,wordids

  def getscoredlist(self,rows,wordids):
    totalscores=dict([(row[0],0) for row in rows])

    # This is where we'll put our scoring functions
    weights=[(1.0,self.locationscore(rows)), 
             (1.0,self.frequencyscore(rows)),
             (1.0,self.pagerankscore(rows)),
             (1.0,self.linktextscore(rows,wordids)),
             (5.0,self.nnscore(rows,wordids))]
    for (weight,scores) in weights:
      for url in totalscores:
        totalscores[url]+=weight*scores[url]

    return totalscores

  def geturlname(self,id):
    return self.con.execute(
    "select url from urllist where rowid=%d" % id).fetchone()[0]

  def query(self,q):
    rows,wordids=self.getmatchrows(q)
    scores=self.getscoredlist(rows,wordids)
    rankedscores=[(score,url) for (url,score) in scores.items()]
    rankedscores.sort()
    rankedscores.reverse()
    for (score,urlid) in rankedscores[0:10]:
      print '%f\t%s' % (score,self.geturlname(urlid))
    return wordids,[r[1] for r in rankedscores[0:10]]

  def normalizescores(self,scores,smallIsBetter=0):
    vsmall=0.00001 # Avoid division by zero errors
    if smallIsBetter:
      minscore=min(scores.values())
      return dict([(u,float(minscore)/max(vsmall,l)) for (u,l) in scores.items()])
    else:
      maxscore=max(scores.values())
      if maxscore==0: maxscore=vsmall
      return dict([(u,float(c)/maxscore) for (u,c) in scores.items()])

  def frequencyscore(self,rows):
    counts=dict([(row[0],0) for row in rows])
    for row in rows: counts[row[0]]+=1
    return self.normalizescores(counts)

  def locationscore(self,rows):
    locations=dict([(row[0],1000000) for row in rows])
    for row in rows:
      loc=sum(row[1:])
      if loc<locations[row[0]]: locations[row[0]]=loc
    
    return self.normalizescores(locations,smallIsBetter=1)

  def distancescore(self,rows):
    # If there's only one word, everyone wins!
    if len(rows[0])<=2: return dict([(row[0],1.0) for row in rows])

    # Initialize the dictionary with large values
    mindistance=dict([(row[0],1000000) for row in rows])

    for row in rows:
      dist=sum([abs(row[i]-row[i-1]) for i in range(2,len(row))])
      if dist<mindistance[row[0]]: mindistance[row[0]]=dist
    return self.normalizescores(mindistance,smallIsBetter=1)

  def inboundlinkscore(self,rows):
    uniqueurls=dict([(row[0],1) for row in rows])
    inboundcount=dict([(u,self.con.execute('select count(*) from link where toid=%d' % u).fetchone()[0]) for u in uniqueurls])   
    return self.normalizescores(inboundcount)

  def linktextscore(self,rows,wordids):
    linkscores=dict([(row[0],0) for row in rows])
    for wordid in wordids:
      cur=self.con.execute('select link.fromid,link.toid from linkwords,link where wordid=%d and linkwords.linkid=link.rowid' % wordid)
      for (fromid,toid) in cur:
        if toid in linkscores:
          pr=self.con.execute('select score from pagerank where urlid=%d' % fromid).fetchone()[0]
          linkscores[toid]+=pr
    maxscore=max(linkscores.values())
    normalizedscores=dict([(u,float(l)/maxscore) for (u,l) in linkscores.items()])
    return normalizedscores

  def pagerankscore(self,rows):
    pageranks=dict([(row[0],self.con.execute('select score from pagerank where urlid=%d' % row[0]).fetchone()[0]) for row in rows])
    maxrank=max(pageranks.values())
    normalizedscores=dict([(u,float(l)/maxrank) for (u,l) in pageranks.items()])
    return normalizedscores

  def nnscore(self,rows,wordids):
    # Get unique URL IDs as an ordered list
    urlids=[urlid for urlid in dict([(row[0],1) for row in rows])]
    nnres=mynet.getresult(wordids,urlids)
    scores=dict([(urlids[i],nnres[i]) for i in range(len(urlids))])
    return self.normalizescores(scores)

########NEW FILE########
__FILENAME__ = dorm
import random
import math

# The dorms, each of which has two available spaces
dorms=['Zeus','Athena','Hercules','Bacchus','Pluto']

# People, along with their first and second choices
prefs=[('Toby', ('Bacchus', 'Hercules')),
       ('Steve', ('Zeus', 'Pluto')),
       ('Karen', ('Athena', 'Zeus')),
       ('Sarah', ('Zeus', 'Pluto')),
       ('Dave', ('Athena', 'Bacchus')), 
       ('Jeff', ('Hercules', 'Pluto')), 
       ('Fred', ('Pluto', 'Athena')), 
       ('Suzie', ('Bacchus', 'Hercules')), 
       ('Laura', ('Bacchus', 'Hercules')), 
       ('James', ('Hercules', 'Athena'))]

# [(0,9),(0,8),(0,7),(0,6),...,(0,0)]
domain=[(0,(len(dorms)*2)-i-1) for i in range(0,len(dorms)*2)]

def printsolution(vec):
  slots=[]
  # Create two slots for each dorm
  for i in range(len(dorms)): slots+=[i,i]

  # Loop over each students assignment
  for i in range(len(vec)):
    x=int(vec[i])

    # Choose the slot from the remaining ones
    dorm=dorms[slots[x]]
    # Show the student and assigned dorm
    print prefs[i][0],dorm
    # Remove this slot
    del slots[x]

def dormcost(vec):
  cost=0
  # Create list a of slots
  slots=[0,0,1,1,2,2,3,3,4,4]

  # Loop over each student
  for i in range(len(vec)):
    x=int(vec[i])
    dorm=dorms[slots[x]]
    pref=prefs[i][1]
    # First choice costs 0, second choice costs 1
    if pref[0]==dorm: cost+=0
    elif pref[1]==dorm: cost+=1
    else: cost+=3
    # Not on the list costs 3

    # Remove selected slot
    del slots[x]
    
  return cost

########NEW FILE########
__FILENAME__ = kayak
import time
import urllib2
import xml.dom.minidom

kayakkey='YOUR KEY HERE'

def getkayaksession():
  # Construct the URL to start a session
  url='http://www.kayak.com/k/ident/apisession?token=%s&version=1' % kayakkey
  
  # Parse the resulting XML
  doc=xml.dom.minidom.parseString(urllib2.urlopen(url).read())
  
  # Find <sid>xxxxxxxx</sid>
  sid=doc.getElementsByTagName('sid')[0].firstChild.data
  return sid

def flightsearch(sid,origin,destination,depart_date):
  
  # Construct search URL
  url='http://www.kayak.com/s/apisearch?basicmode=true&oneway=y&origin=%s' % origin
  url+='&destination=%s&depart_date=%s' % (destination,depart_date)
  url+='&return_date=none&depart_time=a&return_time=a'
  url+='&travelers=1&cabin=e&action=doFlights&apimode=1'
  url+='&_sid_=%s&version=1' % (sid)

  # Get the XML
  doc=xml.dom.minidom.parseString(urllib2.urlopen(url).read())

  # Extract the search ID
  searchid=doc.getElementsByTagName('searchid')[0].firstChild.data

  return searchid

def flightsearchresults(sid,searchid):
  def parseprice(p): 
    return float(p[1:].replace(',',''))

  # Polling loop
  while 1:
    time.sleep(2)

    # Construct URL for polling
    url='http://www.kayak.com/s/basic/flight?'
    url+='searchid=%s&c=5&apimode=1&_sid_=%s&version=1' % (searchid,sid)
    doc=xml.dom.minidom.parseString(urllib2.urlopen(url).read())

    # Look for morepending tag, and wait until it is no longer true
    morepending=doc.getElementsByTagName('morepending')[0].firstChild
    if morepending==None or morepending.data=='false': break

  # Now download the complete list
  url='http://www.kayak.com/s/basic/flight?'
  url+='searchid=%s&c=999&apimode=1&_sid_=%s&version=1' % (searchid,sid)
  doc=xml.dom.minidom.parseString(urllib2.urlopen(url).read())

  # Get the various elements as lists
  prices=doc.getElementsByTagName('price')
  departures=doc.getElementsByTagName('depart')
  arrivals=doc.getElementsByTagName('arrive')  

  # Zip them together
  return zip([p.firstChild.data.split(' ')[1] for p in departures],
             [p.firstChild.data.split(' ')[1] for p in arrivals],
             [parseprice(p.firstChild.data) for p in prices])


def createschedule(people,dest,dep,ret):
  # Get a session id for these searches
  sid=getkayaksession()
  flights={}
  
  for p in people:
    name,origin=p
    # Outbound flight
    searchid=flightsearch(sid,origin,dest,dep)
    flights[(origin,dest)]=flightsearchresults(sid,searchid)
    
    # Return flight
    searchid=flightsearch(sid,dest,origin,ret)
    flights[(dest,origin)]=flightsearchresults(sid,searchid)
    
  return flights

########NEW FILE########
__FILENAME__ = optimization
import time
import random
import math

people = [('Seymour','BOS'),
          ('Franny','DAL'),
          ('Zooey','CAK'),
          ('Walt','MIA'),
          ('Buddy','ORD'),
          ('Les','OMA')]
# Laguardia
destination='LGA'

flights={}
# 
for line in file('schedule.txt'):
  origin,dest,depart,arrive,price=line.strip().split(',')
  flights.setdefault((origin,dest),[])

  # Add details to the list of possible flights
  flights[(origin,dest)].append((depart,arrive,int(price)))

def getminutes(t):
  x=time.strptime(t,'%H:%M')
  return x[3]*60+x[4]

def printschedule(r):
  for d in range(len(r)/2):
    name=people[d][0]
    origin=people[d][1]
    out=flights[(origin,destination)][int(r[d*2])]
    ret=flights[(destination,origin)][int(r[d*2+1])]
    print '%10s%10s %5s-%5s $%3s %5s-%5s $%3s' % (name,origin,
                                                  out[0],out[1],out[2],
                                                  ret[0],ret[1],ret[2])

def schedulecost(sol):
  totalprice=0
  latestarrival=0
  earliestdep=24*60

  for d in range(len(sol)/2):
    # Get the inbound and outbound flights
    origin=people[d][1]
    outbound=flights[(origin,destination)][int(sol[d*2])]
    returnf=flights[(destination,origin)][int(sol[d*2+1])]
    
    # Total price is the price of all outbound and return flights
    totalprice+=outbound[2]
    totalprice+=returnf[2]
    
    # Track the latest arrival and earliest departure
    if latestarrival<getminutes(outbound[1]): latestarrival=getminutes(outbound[1])
    if earliestdep>getminutes(returnf[0]): earliestdep=getminutes(returnf[0])
  
  # Every person must wait at the airport until the latest person arrives.
  # They also must arrive at the same time and wait for their flights.
  totalwait=0  
  for d in range(len(sol)/2):
    origin=people[d][1]
    outbound=flights[(origin,destination)][int(sol[d*2])]
    returnf=flights[(destination,origin)][int(sol[d*2+1])]
    totalwait+=latestarrival-getminutes(outbound[1])
    totalwait+=getminutes(returnf[0])-earliestdep  

  # Does this solution require an extra day of car rental? That'll be $50!
  if latestarrival>earliestdep: totalprice+=50
  
  return totalprice+totalwait

def randomoptimize(domain,costf):
  best=999999999
  bestr=None
  for i in range(0,1000):
    # Create a random solution
    r=[float(random.randint(domain[i][0],domain[i][1])) 
       for i in range(len(domain))]
    
    # Get the cost
    cost=costf(r)
    
    # Compare it to the best one so far
    if cost<best:
      best=cost
      bestr=r 
  return r

def hillclimb(domain,costf):
  # Create a random solution
  sol=[random.randint(domain[i][0],domain[i][1])
      for i in range(len(domain))]
  # Main loop
  while 1:
    # Create list of neighboring solutions
    neighbors=[]
    
    for j in range(len(domain)):
      # One away in each direction
      if sol[j]>domain[j][0]:
        neighbors.append(sol[0:j]+[sol[j]+1]+sol[j+1:])
      if sol[j]<domain[j][1]:
        neighbors.append(sol[0:j]+[sol[j]-1]+sol[j+1:])

    # See what the best solution amongst the neighbors is
    current=costf(sol)
    best=current
    for j in range(len(neighbors)):
      cost=costf(neighbors[j])
      if cost<best:
        best=cost
        sol=neighbors[j]

    # If there's no improvement, then we've reached the top
    if best==current:
      break
  return sol

def annealingoptimize(domain,costf,T=10000.0,cool=0.95,step=1):
  # Initialize the values randomly
  vec=[float(random.randint(domain[i][0],domain[i][1])) 
       for i in range(len(domain))]
  
  while T>0.1:
    # Choose one of the indices
    i=random.randint(0,len(domain)-1)

    # Choose a direction to change it
    dir=random.randint(-step,step)

    # Create a new list with one of the values changed
    vecb=vec[:]
    vecb[i]+=dir
    if vecb[i]<domain[i][0]: vecb[i]=domain[i][0]
    elif vecb[i]>domain[i][1]: vecb[i]=domain[i][1]

    # Calculate the current cost and the new cost
    ea=costf(vec)
    eb=costf(vecb)
    p=pow(math.e,(-eb-ea)/T)

    # Is it better, or does it make the probability
    # cutoff?
    if (eb<ea or random.random()<p):
      vec=vecb      

    # Decrease the temperature
    T=T*cool
  return vec

def geneticoptimize(domain,costf,popsize=50,step=1,
                    mutprod=0.2,elite=0.2,maxiter=100):
  # Mutation Operation
  def mutate(vec):
    i=random.randint(0,len(domain)-1)
    if random.random()<0.5 and vec[i]>domain[i][0]:
      return vec[0:i]+[vec[i]-step]+vec[i+1:] 
    elif vec[i]<domain[i][1]:
      return vec[0:i]+[vec[i]+step]+vec[i+1:]
  
  # Crossover Operation
  def crossover(r1,r2):
    i=random.randint(1,len(domain)-2)
    return r1[0:i]+r2[i:]

  # Build the initial population
  pop=[]
  for i in range(popsize):
    vec=[random.randint(domain[i][0],domain[i][1]) 
         for i in range(len(domain))]
    pop.append(vec)
  
  # How many winners from each generation?
  topelite=int(elite*popsize)
  
  # Main loop 
  for i in range(maxiter):
    scores=[(costf(v),v) for v in pop]
    scores.sort()
    ranked=[v for (s,v) in scores]
    
    # Start with the pure winners
    pop=ranked[0:topelite]
    
    # Add mutated and bred forms of the winners
    while len(pop)<popsize:
      if random.random()<mutprob:

        # Mutation
        c=random.randint(0,topelite)
        pop.append(mutate(ranked[c]))
      else:
      
        # Crossover
        c1=random.randint(0,topelite)
        c2=random.randint(0,topelite)
        pop.append(crossover(ranked[c1],ranked[c2]))
    
    # Print current best score
    print scores[0][0]
    
  return scores[0][1]

########NEW FILE########
__FILENAME__ = socialnetwork
import math

people=['Charlie','Augustus','Veruca','Violet','Mike','Joe','Willy','Miranda']

links=[('Augustus', 'Willy'), 
       ('Mike', 'Joe'), 
       ('Miranda', 'Mike'), 
       ('Violet', 'Augustus'), 
       ('Miranda', 'Willy'), 
       ('Charlie', 'Mike'), 
       ('Veruca', 'Joe'), 
       ('Miranda', 'Augustus'), 
       ('Willy', 'Augustus'), 
       ('Joe', 'Charlie'), 
       ('Veruca', 'Augustus'), 
       ('Miranda', 'Joe')]


def crosscount(v):
  # Convert the number list into a dictionary of person:(x,y)
  loc=dict([(people[i],(v[i*2],v[i*2+1])) for i in range(0,len(people))])
  total=0
  
  # Loop through every pair of links
  for i in range(len(links)):
    for j in range(i+1,len(links)):

      # Get the locations 
      (x1,y1),(x2,y2)=loc[links[i][0]],loc[links[i][1]]
      (x3,y3),(x4,y4)=loc[links[j][0]],loc[links[j][1]]
      
      den=(y4-y3)*(x2-x1)-(x4-x3)*(y2-y1)

      # den==0 if the lines are parallel
      if den==0: continue

      # Otherwise ua and ub are the fraction of the
      # line where they cross
      ua=((x4-x3)*(y1-y3)-(y4-y3)*(x1-x3))/den
      ub=((x2-x1)*(y1-y3)-(y2-y1)*(x1-x3))/den
      
      # If the fraction is between 0 and 1 for both lines
      # then they cross each other
      if ua>0 and ua<1 and ub>0 and ub<1:
        total+=1
    for i in range(len(people)):
      for j in range(i+1,len(people)):
        # Get the locations of the two nodes
        (x1,y1),(x2,y2)=loc[people[i]],loc[people[j]]

        # Find the distance between them
        dist=math.sqrt(math.pow(x1-x2,2)+math.pow(y1-y2,2))
        # Penalize any nodes closer than 50 pixels
        if dist<50:
          total+=(1.0-(dist/50.0))
        
  return total
from PIL import Image,ImageDraw

def drawnetwork(sol):
  # Create the image
  img=Image.new('RGB',(400,400),(255,255,255))
  draw=ImageDraw.Draw(img)

  # Create the position dict
  pos=dict([(people[i],(sol[i*2],sol[i*2+1])) for i in range(0,len(people))])

  for (a,b) in links:
    draw.line((pos[a],pos[b]),fill=(255,0,0))

  for n,p in pos.items():
    draw.text(p,n,(0,0,0))

  img.show()


domain=[(10,370)]*(len(people)*2)
########NEW FILE########
__FILENAME__ = docclass
from pysqlite2 import dbapi2 as sqlite
import re
import math

def getwords(doc):
  splitter=re.compile('\\W*')
  print doc
  # Split the words by non-alpha characters
  words=[s.lower() for s in splitter.split(doc) 
          if len(s)>2 and len(s)<20]
  
  # Return the unique set of words only
  return dict([(w,1) for w in words])

class classifier:
  def __init__(self,getfeatures,filename=None):
    # Counts of feature/category combinations
    self.fc={}
    # Counts of documents in each category
    self.cc={}
    self.getfeatures=getfeatures
    
  def setdb(self,dbfile):
    self.con=sqlite.connect(dbfile)    
    self.con.execute('create table if not exists fc(feature,category,count)')
    self.con.execute('create table if not exists cc(category,count)')


  def incf(self,f,cat):
    count=self.fcount(f,cat)
    if count==0:
      self.con.execute("insert into fc values ('%s','%s',1)" 
                       % (f,cat))
    else:
      self.con.execute(
        "update fc set count=%d where feature='%s' and category='%s'" 
        % (count+1,f,cat)) 
  
  def fcount(self,f,cat):
    res=self.con.execute(
      'select count from fc where feature="%s" and category="%s"'
      %(f,cat)).fetchone()
    if res==None: return 0
    else: return float(res[0])

  def incc(self,cat):
    count=self.catcount(cat)
    if count==0:
      self.con.execute("insert into cc values ('%s',1)" % (cat))
    else:
      self.con.execute("update cc set count=%d where category='%s'" 
                       % (count+1,cat))    

  def catcount(self,cat):
    res=self.con.execute('select count from cc where category="%s"'
                         %(cat)).fetchone()
    if res==None: return 0
    else: return float(res[0])

  def categories(self):
    cur=self.con.execute('select category from cc');
    return [d[0] for d in cur]

  def totalcount(self):
    res=self.con.execute('select sum(count) from cc').fetchone();
    if res==None: return 0
    return res[0]


  def train(self,item,cat):
    features=self.getfeatures(item)
    # Increment the count for every feature with this category
    for f in features:
      self.incf(f,cat)

    # Increment the count for this category
    self.incc(cat)
    self.con.commit()

  def fprob(self,f,cat):
    if self.catcount(cat)==0: return 0

    # The total number of times this feature appeared in this 
    # category divided by the total number of items in this category
    return self.fcount(f,cat)/self.catcount(cat)

  def weightedprob(self,f,cat,prf,weight=1.0,ap=0.5):
    # Calculate current probability
    basicprob=prf(f,cat)

    # Count the number of times this feature has appeared in
    # all categories
    totals=sum([self.fcount(f,c) for c in self.categories()])

    # Calculate the weighted average
    bp=((weight*ap)+(totals*basicprob))/(weight+totals)
    return bp




class naivebayes(classifier):
  
  def __init__(self,getfeatures):
    classifier.__init__(self,getfeatures)
    self.thresholds={}
  
  def docprob(self,item,cat):
    features=self.getfeatures(item)   

    # Multiply the probabilities of all the features together
    p=1
    for f in features: p*=self.weightedprob(f,cat,self.fprob)
    return p

  def prob(self,item,cat):
    catprob=self.catcount(cat)/self.totalcount()
    docprob=self.docprob(item,cat)
    return docprob*catprob
  
  def setthreshold(self,cat,t):
    self.thresholds[cat]=t
    
  def getthreshold(self,cat):
    if cat not in self.thresholds: return 1.0
    return self.thresholds[cat]
  
  def classify(self,item,default=None):
    probs={}
    # Find the category with the highest probability
    max=0.0
    for cat in self.categories():
      probs[cat]=self.prob(item,cat)
      if probs[cat]>max: 
        max=probs[cat]
        best=cat

    # Make sure the probability exceeds threshold*next best
    for cat in probs:
      if cat==best: continue
      if probs[cat]*self.getthreshold(best)>probs[best]: return default
    return best

class fisherclassifier(classifier):
  def cprob(self,f,cat):
    # The frequency of this feature in this category    
    clf=self.fprob(f,cat)
    if clf==0: return 0

    # The frequency of this feature in all the categories
    freqsum=sum([self.fprob(f,c) for c in self.categories()])

    # The probability is the frequency in this category divided by
    # the overall frequency
    p=clf/(freqsum)
    
    return p
  def fisherprob(self,item,cat):
    # Multiply all the probabilities together
    p=1
    features=self.getfeatures(item)
    for f in features:
      p*=(self.weightedprob(f,cat,self.cprob))

    # Take the natural log and multiply by -2
    fscore=-2*math.log(p)

    # Use the inverse chi2 function to get a probability
    return self.invchi2(fscore,len(features)*2)
  def invchi2(self,chi, df):
    m = chi / 2.0
    sum = term = math.exp(-m)
    for i in range(1, df//2):
        term *= m / i
        sum += term
    return min(sum, 1.0)
  def __init__(self,getfeatures):
    classifier.__init__(self,getfeatures)
    self.minimums={}

  def setminimum(self,cat,min):
    self.minimums[cat]=min
  
  def getminimum(self,cat):
    if cat not in self.minimums: return 0
    return self.minimums[cat]
  def classify(self,item,default=None):
    # Loop through looking for the best result
    best=default
    max=0.0
    for c in self.categories():
      p=self.fisherprob(item,c)
      # Make sure it exceeds its minimum
      if p>self.getminimum(c) and p>max:
        best=c
        max=p
    return best


def sampletrain(cl):
  cl.train('Nobody owns the water.','good')
  cl.train('the quick rabbit jumps fences','good')
  cl.train('buy pharmaceuticals now','bad')
  cl.train('make quick money at the online casino','bad')
  cl.train('the quick brown fox jumps','good')

########NEW FILE########
__FILENAME__ = feedfilter
import feedparser
import re

# Takes a filename of URL of a blog feed and classifies the entries
def read(feed,classifier):
  # Get feed entries and loop over them
  f=feedparser.parse(feed)
  for entry in f['entries']:
    print
    print '-----'
    # Print the contents of the entry
    print 'Title:     '+entry['title'].encode('utf-8')
    print 'Publisher: '+entry['publisher'].encode('utf-8')
    print
    print entry['summary'].encode('utf-8')
    

    # Combine all the text to create one item for the classifier
    fulltext='%s\n%s\n%s' % (entry['title'],entry['publisher'],entry['summary'])

    # Print the best guess at the current category
    print 'Guess: '+str(classifier.classify(entry))

    # Ask the user to specify the correct category and train on that
    cl=raw_input('Enter category: ')
    classifier.train(entry,cl)


def entryfeatures(entry):
  splitter=re.compile('\\W*')
  f={}
  
  # Extract the title words and annotate
  titlewords=[s.lower() for s in splitter.split(entry['title']) 
          if len(s)>2 and len(s)<20]
  for w in titlewords: f['Title:'+w]=1
  
  # Extract the summary words
  summarywords=[s.lower() for s in splitter.split(entry['summary']) 
          if len(s)>2 and len(s)<20]

  # Count uppercase words
  uc=0
  for i in range(len(summarywords)):
    w=summarywords[i]
    f[w]=1
    if w.isupper(): uc+=1
    
    # Get word pairs in summary as features
    if i<len(summarywords)-1:
      twowords=' '.join(summarywords[i:i+1])
      f[twowords]=1
    
  # Keep creator and publisher whole
  f['Publisher:'+entry['publisher']]=1

  # UPPERCASE is a virtual word flagging too much shouting  
  if float(uc)/len(summarywords)>0.3: f['UPPERCASE']=1
  
  return f

########NEW FILE########
__FILENAME__ = hotornot
import urllib2
import xml.dom.minidom

api_key='YOUR KEY HERE'

def getrandomratings(c):
  # Construct URL for getRandomProfile
  url="http://services.hotornot.com/rest/?app_key=%s" % api_key
  url+="&method=Rate.getRandomProfile&retrieve_num=%d" % c
  url+="&get_rate_info=true&meet_users_only=true"
  
  f1=urllib2.urlopen(url).read()

  doc=xml.dom.minidom.parseString(f1)
  
  emids=doc.getElementsByTagName('emid')
  ratings=doc.getElementsByTagName('rating')

  # Combine the emids and ratings together into a list
  result=[]
  for e,r in zip(emids,ratings):
    if r.firstChild!=None:
      result.append((e.firstChild.data,r.firstChild.data))
  return result

stateregions={'New England':['ct','mn','ma','nh','ri','vt'],
              'Mid Atlantic':['de','md','nj','ny','pa'],
              'South':['al','ak','fl','ga','ky','la','ms','mo',
                       'nc','sc','tn','va','wv'],
              'Midwest':['il','in','ia','ks','mi','ne','nd','oh','sd','wi'],
              'West':['ak','ca','co','hi','id','mt','nv','or','ut','wa','wy']}

def getpeopledata(ratings):
  result=[]
  for emid,rating in ratings:
    # URL for the MeetMe.getProfile method
    url="http://services.hotornot.com/rest/?app_key=%s" % api_key
    url+="&method=MeetMe.getProfile&emid=%s&get_keywords=true" % emid

    # Get all the info about this person
    try:
      rating=int(float(rating)+0.5)
      doc2=xml.dom.minidom.parseString(urllib2.urlopen(url).read())
      gender=doc2.getElementsByTagName('gender')[0].firstChild.data
      age=doc2.getElementsByTagName('age')[0].firstChild.data
      loc=doc2.getElementsByTagName('location')[0].firstChild.data[0:2]

      # Convert state to region
      for r,s in stateregions.items():
        if loc in s: region=r

      if region!=None:
        result.append((gender,int(age),region,rating))
    except:
      pass
  return result


########NEW FILE########
__FILENAME__ = treepredict
my_data=[['slashdot','USA','yes',18,'None'],
        ['google','France','yes',23,'Premium'],
        ['digg','USA','yes',24,'Basic'],
        ['kiwitobes','France','yes',23,'Basic'],
        ['google','UK','no',21,'Premium'],
        ['(direct)','New Zealand','no',12,'None'],
        ['(direct)','UK','no',21,'Basic'],
        ['google','USA','no',24,'Premium'],
        ['slashdot','France','yes',19,'None'],
        ['digg','USA','no',18,'None'],
        ['google','UK','no',18,'None'],
        ['kiwitobes','UK','no',19,'None'],
        ['digg','New Zealand','yes',12,'Basic'],
        ['slashdot','UK','no',21,'None'],
        ['google','UK','yes',18,'Basic'],
        ['kiwitobes','France','yes',19,'Basic']]

class decisionnode:
  def __init__(self,col=-1,value=None,results=None,tb=None,fb=None):
    self.col=col
    self.value=value
    self.results=results
    self.tb=tb
    self.fb=fb

# Divides a set on a specific column. Can handle numeric
# or nominal values
def divideset(rows,column,value):
   # Make a function that tells us if a row is in 
   # the first group (true) or the second group (false)
   split_function=None
   if isinstance(value,int) or isinstance(value,float):
      split_function=lambda row:row[column]>=value
   else:
      split_function=lambda row:row[column]==value
   
   # Divide the rows into two sets and return them
   set1=[row for row in rows if split_function(row)]
   set2=[row for row in rows if not split_function(row)]
   return (set1,set2)


# Create counts of possible results (the last column of 
# each row is the result)
def uniquecounts(rows):
   results={}
   for row in rows:
      # The result is the last column
      r=row[len(row)-1]
      if r not in results: results[r]=0
      results[r]+=1
   return results

# Probability that a randomly placed item will
# be in the wrong category
def giniimpurity(rows):
  total=len(rows)
  counts=uniquecounts(rows)
  imp=0
  for k1 in counts:
    p1=float(counts[k1])/total
    for k2 in counts:
      if k1==k2: continue
      p2=float(counts[k2])/total
      imp+=p1*p2
  return imp

# Entropy is the sum of p(x)log(p(x)) across all 
# the different possible results
def entropy(rows):
   from math import log
   log2=lambda x:log(x)/log(2)  
   results=uniquecounts(rows)
   # Now calculate the entropy
   ent=0.0
   for r in results.keys():
      p=float(results[r])/len(rows)
      ent=ent-p*log2(p)
   return ent




def printtree(tree,indent=''):
   # Is this a leaf node?
   if tree.results!=None:
      print str(tree.results)
   else:
      # Print the criteria
      print str(tree.col)+':'+str(tree.value)+'? '

      # Print the branches
      print indent+'T->',
      printtree(tree.tb,indent+'  ')
      print indent+'F->',
      printtree(tree.fb,indent+'  ')


def getwidth(tree):
  if tree.tb==None and tree.fb==None: return 1
  return getwidth(tree.tb)+getwidth(tree.fb)

def getdepth(tree):
  if tree.tb==None and tree.fb==None: return 0
  return max(getdepth(tree.tb),getdepth(tree.fb))+1


from PIL import Image,ImageDraw

def drawtree(tree,jpeg='tree.jpg'):
  w=getwidth(tree)*100
  h=getdepth(tree)*100+120

  img=Image.new('RGB',(w,h),(255,255,255))
  draw=ImageDraw.Draw(img)

  drawnode(draw,tree,w/2,20)
  img.save(jpeg,'JPEG')
  
def drawnode(draw,tree,x,y):
  if tree.results==None:
    # Get the width of each branch
    w1=getwidth(tree.fb)*100
    w2=getwidth(tree.tb)*100

    # Determine the total space required by this node
    left=x-(w1+w2)/2
    right=x+(w1+w2)/2

    # Draw the condition string
    draw.text((x-20,y-10),str(tree.col)+':'+str(tree.value),(0,0,0))

    # Draw links to the branches
    draw.line((x,y,left+w1/2,y+100),fill=(255,0,0))
    draw.line((x,y,right-w2/2,y+100),fill=(255,0,0))
    
    # Draw the branch nodes
    drawnode(draw,tree.fb,left+w1/2,y+100)
    drawnode(draw,tree.tb,right-w2/2,y+100)
  else:
    txt=' \n'.join(['%s:%d'%v for v in tree.results.items()])
    draw.text((x-20,y),txt,(0,0,0))


def classify(observation,tree):
  if tree.results!=None:
    return tree.results
  else:
    v=observation[tree.col]
    branch=None
    if isinstance(v,int) or isinstance(v,float):
      if v>=tree.value: branch=tree.tb
      else: branch=tree.fb
    else:
      if v==tree.value: branch=tree.tb
      else: branch=tree.fb
    return classify(observation,branch)

def prune(tree,mingain):
  # If the branches aren't leaves, then prune them
  if tree.tb.results==None:
    prune(tree.tb,mingain)
  if tree.fb.results==None:
    prune(tree.fb,mingain)
    
  # If both the subbranches are now leaves, see if they
  # should merged
  if tree.tb.results!=None and tree.fb.results!=None:
    # Build a combined dataset
    tb,fb=[],[]
    for v,c in tree.tb.results.items():
      tb+=[[v]]*c
    for v,c in tree.fb.results.items():
      fb+=[[v]]*c
    
    # Test the reduction in entropy
    delta=entropy(tb+fb)-(entropy(tb)+entropy(fb)/2)

    if delta<mingain:
      # Merge the branches
      tree.tb,tree.fb=None,None
      tree.results=uniquecounts(tb+fb)

def mdclassify(observation,tree):
  if tree.results!=None:
    return tree.results
  else:
    v=observation[tree.col]
    if v==None:
      tr,fr=mdclassify(observation,tree.tb),mdclassify(observation,tree.fb)
      tcount=sum(tr.values())
      fcount=sum(fr.values())
      tw=float(tcount)/(tcount+fcount)
      fw=float(fcount)/(tcount+fcount)
      result={}
      for k,v in tr.items(): result[k]=v*tw
      for k,v in fr.items(): result[k]=v*fw      
      return result
    else:
      if isinstance(v,int) or isinstance(v,float):
        if v>=tree.value: branch=tree.tb
        else: branch=tree.fb
      else:
        if v==tree.value: branch=tree.tb
        else: branch=tree.fb
      return mdclassify(observation,branch)

def variance(rows):
  if len(rows)==0: return 0
  data=[float(row[len(row)-1]) for row in rows]
  mean=sum(data)/len(data)
  variance=sum([(d-mean)**2 for d in data])/len(data)
  return variance

def buildtree(rows,scoref=entropy):
  if len(rows)==0: return decisionnode()
  current_score=scoref(rows)

  # Set up some variables to track the best criteria
  best_gain=0.0
  best_criteria=None
  best_sets=None
  
  column_count=len(rows[0])-1
  for col in range(0,column_count):
    # Generate the list of different values in
    # this column
    column_values={}
    for row in rows:
       column_values[row[col]]=1
    # Now try dividing the rows up for each value
    # in this column
    for value in column_values.keys():
      (set1,set2)=divideset(rows,col,value)
      
      # Information gain
      p=float(len(set1))/len(rows)
      gain=current_score-p*scoref(set1)-(1-p)*scoref(set2)
      if gain>best_gain and len(set1)>0 and len(set2)>0:
        best_gain=gain
        best_criteria=(col,value)
        best_sets=(set1,set2)
  # Create the sub branches   
  if best_gain>0:
    trueBranch=buildtree(best_sets[0])
    falseBranch=buildtree(best_sets[1])
    return decisionnode(col=best_criteria[0],value=best_criteria[1],
                        tb=trueBranch,fb=falseBranch)
  else:
    return decisionnode(results=uniquecounts(rows))

########NEW FILE########
__FILENAME__ = zillow
import xml.dom.minidom
import urllib2

zwskey="YOUR API KEY"

def getaddressdata(address,city):
  escad=address.replace(' ','+')
  url='http://www.zillow.com/webservice/GetDeepSearchResults.htm?'
  url+='zws-id=%s&address=%s&citystatezip=%s' % (zwskey,escad,city)
  doc=xml.dom.minidom.parseString(urllib2.urlopen(url).read())
  code=doc.getElementsByTagName('code')[0].firstChild.data
  if code!='0': return None
  if 1:
    zipcode=doc.getElementsByTagName('zipcode')[0].firstChild.data
    use=doc.getElementsByTagName('useCode')[0].firstChild.data
    year=doc.getElementsByTagName('yearBuilt')[0].firstChild.data
    sqft=doc.getElementsByTagName('finishedSqFt')[0].firstChild.data
    bath=doc.getElementsByTagName('bathrooms')[0].firstChild.data
    bed=doc.getElementsByTagName('bedrooms')[0].firstChild.data
    rooms=1 #doc.getElementsByTagName('totalRooms')[0].firstChild.data
    price=doc.getElementsByTagName('amount')[0].firstChild.data
  else:
    return None
       
  return (zipcode,use,int(year),float(bath),int(bed),int(rooms),price)

def getpricelist():
  l1=[]
  for line in file('addresslist.txt'):
    data=getaddressdata(line.strip(),'Cambridge,MA')
    l1.append(data)
  return l1

########NEW FILE########
__FILENAME__ = ebaypredict
import httplib
from xml.dom.minidom import parse, parseString, Node

devKey = 'YOUR DEV KEY'
appKey = 'YOUR APP KEY'
certKey = 'YOUR CERT KEY'
serverUrl = 'api.ebay.com'
userToken = 'YOUR TOKEN'

def getHeaders(apicall,siteID="0",compatabilityLevel = "433"):
  headers = {"X-EBAY-API-COMPATIBILITY-LEVEL": compatabilityLevel,	
             "X-EBAY-API-DEV-NAME": devKey,
             "X-EBAY-API-APP-NAME": appKey,
             "X-EBAY-API-CERT-NAME": certKey,
             "X-EBAY-API-CALL-NAME": apicall,
             "X-EBAY-API-SITEID": siteID,
             "Content-Type": "text/xml"}
  return headers

def sendRequest(apicall,xmlparameters):
  connection = httplib.HTTPSConnection(serverUrl)
  connection.request("POST", '/ws/api.dll', xmlparameters, getHeaders(apicall))
  response = connection.getresponse()
  if response.status != 200:
    print "Error sending request:" + response.reason
  else: 
    data = response.read()
    connection.close()
  return data

def getSingleValue(node,tag):
  nl=node.getElementsByTagName(tag)
  if len(nl)>0:
    tagNode=nl[0]
    if tagNode.hasChildNodes():
      return tagNode.firstChild.nodeValue
  return '-1'


def doSearch(query,categoryID=None,page=1):
  xml = "<?xml version='1.0' encoding='utf-8'?>"+\
        "<GetSearchResultsRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">"+\
        "<RequesterCredentials><eBayAuthToken>" +\
        userToken +\
        "</eBayAuthToken></RequesterCredentials>" + \
        "<Pagination>"+\
          "<EntriesPerPage>200</EntriesPerPage>"+\
          "<PageNumber>"+str(page)+"</PageNumber>"+\
        "</Pagination>"+\
        "<Query>" + query + "</Query>"
  if categoryID!=None:
    xml+="<CategoryID>"+str(categoryID)+"</CategoryID>"
  xml+="</GetSearchResultsRequest>"
  
  data=sendRequest('GetSearchResults',xml)
  response = parseString(data)
  itemNodes = response.getElementsByTagName('Item');
  results = []
  for item in itemNodes:
    itemId=getSingleValue(item,'ItemID')
    itemTitle=getSingleValue(item,'Title')
    itemPrice=getSingleValue(item,'CurrentPrice')
    itemEnds=getSingleValue(item,'EndTime')
    results.append((itemId,itemTitle,itemPrice,itemEnds))
  return results


def getCategory(query='',parentID=None,siteID='0'):
  lquery=query.lower()
  xml = "<?xml version='1.0' encoding='utf-8'?>"+\
        "<GetCategoriesRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">"+\
        "<RequesterCredentials><eBayAuthToken>" +\
        userToken +\
        "</eBayAuthToken></RequesterCredentials>"+\
        "<DetailLevel>ReturnAll</DetailLevel>"+\
        "<ViewAllNodes>true</ViewAllNodes>"+\
        "<CategorySiteID>"+siteID+"</CategorySiteID>"
  if parentID==None:
    xml+="<LevelLimit>1</LevelLimit>"
  else:
    xml+="<CategoryParent>"+str(parentID)+"</CategoryParent>"
  xml += "</GetCategoriesRequest>"
  data=sendRequest('GetCategories',xml)
  categoryList=parseString(data)
  catNodes=categoryList.getElementsByTagName('Category')
  for node in catNodes:
    catid=getSingleValue(node,'CategoryID')
    name=getSingleValue(node,'CategoryName')
    if name.lower().find(lquery)!=-1:
      print catid,name

def getItem(itemID):
  xml = "<?xml version='1.0' encoding='utf-8'?>"+\
        "<GetItemRequest xmlns=\"urn:ebay:apis:eBLBaseComponents\">"+\
        "<RequesterCredentials><eBayAuthToken>" +\
        userToken +\
        "</eBayAuthToken></RequesterCredentials>" + \
        "<ItemID>" + str(itemID) + "</ItemID>"+\
        "<DetailLevel>ItemReturnAttributes</DetailLevel>"+\
        "</GetItemRequest>"
  data=sendRequest('GetItem',xml)
  result={}
  response=parseString(data)
  result['title']=getSingleValue(response,'Title')
  sellingStatusNode = response.getElementsByTagName('SellingStatus')[0];
  result['price']=getSingleValue(sellingStatusNode,'CurrentPrice')
  result['bids']=getSingleValue(sellingStatusNode,'BidCount')
  seller = response.getElementsByTagName('Seller')
  result['feedback'] = getSingleValue(seller[0],'FeedbackScore')

  attributeSet=response.getElementsByTagName('Attribute');
  attributes={}
  for att in attributeSet:
    attID=att.attributes.getNamedItem('attributeID').nodeValue
    attValue=getSingleValue(att,'ValueLiteral')
    attributes[attID]=attValue
  result['attributes']=attributes
  return result


def makeLaptopDataset():
  searchResults=doSearch('laptop',categoryID=51148)
  result=[]
  for r in searchResults:
    item=getItem(r[0])
    att=item['attributes']
    try:
      data=(float(att['12']),float(att['26444']),
            float(att['26446']),float(att['25710']),
            float(item['feedback'])
           )
      entry={'input':data,'result':float(item['price'])}
      result.append(entry)
    except:
      print item['title']+' failed'
  return result

########NEW FILE########
__FILENAME__ = numpredict
from random import random,randint
import math

def wineprice(rating,age):
  peak_age=rating-50
  
  # Calculate price based on rating
  price=rating/2
  if age>peak_age:
    # Past its peak, goes bad in 10 years
    price=price*(5-(age-peak_age)/2)
  else:
    # Increases to 5x original value as it
    # approaches its peak
    price=price*(5*((age+1)/peak_age))
  if price<0: price=0
  return price


def wineset1():
  rows=[]
  for i in range(300):
    # Create a random age and rating
    rating=random()*50+50
    age=random()*50

    # Get reference price
    price=wineprice(rating,age)
    
    # Add some noise
    price*=(random()*0.2+0.9)

    # Add to the dataset
    rows.append({'input':(rating,age),
                 'result':price})
  return rows

def euclidean(v1,v2):
  d=0.0
  for i in range(len(v1)):
    d+=(v1[i]-v2[i])**2
  return math.sqrt(d)


def getdistances(data,vec1):
  distancelist=[]
  
  # Loop over every item in the dataset
  for i in range(len(data)):
    vec2=data[i]['input']
    
    # Add the distance and the index
    distancelist.append((euclidean(vec1,vec2),i))
  
  # Sort by distance
  distancelist.sort()
  return distancelist

def knnestimate(data,vec1,k=5):
  # Get sorted distances
  dlist=getdistances(data,vec1)
  avg=0.0
  
  # Take the average of the top k results
  for i in range(k):
    idx=dlist[i][1]
    avg+=data[idx]['result']
  avg=avg/k
  return avg

def inverseweight(dist,num=1.0,const=0.1):
  return num/(dist+const)

def subtractweight(dist,const=1.0):
  if dist>const: 
    return 0
  else: 
    return const-dist

def gaussian(dist,sigma=5.0):
  return math.e**(-dist**2/(2*sigma**2))

def weightedknn(data,vec1,k=5,weightf=gaussian):
  # Get distances
  dlist=getdistances(data,vec1)
  avg=0.0
  totalweight=0.0
  
  # Get weighted average
  for i in range(k):
    dist=dlist[i][0]
    idx=dlist[i][1]
    weight=weightf(dist)
    avg+=weight*data[idx]['result']
    totalweight+=weight
  if totalweight==0: return 0
  avg=avg/totalweight
  return avg

def dividedata(data,test=0.05):
  trainset=[]
  testset=[]
  for row in data:
    if random()<test:
      testset.append(row)
    else:
      trainset.append(row)
  return trainset,testset

def testalgorithm(algf,trainset,testset):
  error=0.0
  for row in testset:
    guess=algf(trainset,row['input'])
    error+=(row['result']-guess)**2
    #print row['result'],guess
  #print error/len(testset)
  return error/len(testset)

def crossvalidate(algf,data,trials=100,test=0.1):
  error=0.0
  for i in range(trials):
    trainset,testset=dividedata(data,test)
    error+=testalgorithm(algf,trainset,testset)
  return error/trials

def wineset2():
  rows=[]
  for i in range(300):
    rating=random()*50+50
    age=random()*50
    aisle=float(randint(1,20))
    bottlesize=[375.0,750.0,1500.0][randint(0,2)]
    price=wineprice(rating,age)
    price*=(bottlesize/750)
    price*=(random()*0.2+0.9)
    rows.append({'input':(rating,age,aisle,bottlesize),
                 'result':price})
  return rows

def rescale(data,scale):
  scaleddata=[]
  for row in data:
    scaled=[scale[i]*row['input'][i] for i in range(len(scale))]
    scaleddata.append({'input':scaled,'result':row['result']})
  return scaleddata

def createcostfunction(algf,data):
  def costf(scale):
    sdata=rescale(data,scale)
    return crossvalidate(algf,sdata,trials=20)
  return costf

weightdomain=[(0,10)]*4

def wineset3():
  rows=wineset1()
  for row in rows:
    if random()<0.5:
      # Wine was bought at a discount store
      row['result']*=0.6
  return rows

def probguess(data,vec1,low,high,k=5,weightf=gaussian):
  dlist=getdistances(data,vec1)
  nweight=0.0
  tweight=0.0
  
  for i in range(k):
    dist=dlist[i][0]
    idx=dlist[i][1]
    weight=weightf(dist)
    v=data[idx]['result']
    
    # Is this point in the range?
    if v>=low and v<=high:
      nweight+=weight
    tweight+=weight
  if tweight==0: return 0
  
  # The probability is the weights in the range
  # divided by all the weights
  return nweight/tweight

from pylab import *

def cumulativegraph(data,vec1,high,k=5,weightf=gaussian):
  t1=arange(0.0,high,0.1)
  cprob=array([probguess(data,vec1,0,v,k,weightf) for v in t1])
  plot(t1,cprob)
  show()


def probabilitygraph(data,vec1,high,k=5,weightf=gaussian,ss=5.0):
  # Make a range for the prices
  t1=arange(0.0,high,0.1)
  
  # Get the probabilities for the entire range
  probs=[probguess(data,vec1,v,v+0.1,k,weightf) for v in t1]
  
  # Smooth them by adding the gaussian of the nearby probabilites
  smoothed=[]
  for i in range(len(probs)):
    sv=0.0
    for j in range(0,len(probs)):
      dist=abs(i-j)*0.1
      weight=gaussian(dist,sigma=ss)
      sv+=weight*probs[j]
    smoothed.append(sv)
  smoothed=array(smoothed)
    
  plot(t1,smoothed)
  show()

########NEW FILE########
__FILENAME__ = optimization
import time
import random
import math

people = [('Seymour','BOS'),
          ('Franny','DAL'),
          ('Zooey','CAK'),
          ('Walt','MIA'),
          ('Buddy','ORD'),
          ('Les','OMA')]
# Laguardia
destination='LGA'

flights={}
# 
"""
for line in file('schedule.txt'):
  origin,dest,depart,arrive,price=line.strip().split(',')
  flights.setdefault((origin,dest),[])

  # Add details to the list of possible flights
  flights[(origin,dest)].append((depart,arrive,int(price)))
"""
def getminutes(t):
  x=time.strptime(t,'%H:%M')
  return x[3]*60+x[4]

def printschedule(r):
  for d in range(len(r)/2):
    name=people[d][0]
    origin=people[d][1]
    out=flights[(origin,destination)][int(r[d])]
    ret=flights[(destination,origin)][int(r[d+1])]
    print '%10s%10s %5s-%5s $%3s %5s-%5s $%3s' % (name,origin,
                                                  out[0],out[1],out[2],
                                                  ret[0],ret[1],ret[2])

def schedulecost(sol):
  totalprice=0
  latestarrival=0
  earliestdep=24*60

  for d in range(len(sol)/2):
    # Get the inbound and outbound flights
    origin=people[d][1]
    outbound=flights[(origin,destination)][int(sol[d])]
    returnf=flights[(destination,origin)][int(sol[d+1])]
    
    # Total price is the price of all outbound and return flights
    totalprice+=outbound[2]
    totalprice+=returnf[2]
    
    # Track the latest arrival and earliest departure
    if latestarrival<getminutes(outbound[1]): latestarrival=getminutes(outbound[1])
    if earliestdep>getminutes(returnf[0]): earliestdep=getminutes(returnf[0])
  
  # Every person must wait at the airport until the latest person arrives.
  # They also must arrive at the same time and wait for their flights.
  totalwait=0  
  for d in range(len(sol)/2):
    origin=people[d][1]
    outbound=flights[(origin,destination)][int(sol[d])]
    returnf=flights[(destination,origin)][int(sol[d+1])]
    totalwait+=latestarrival-getminutes(outbound[1])
    totalwait+=getminutes(returnf[0])-earliestdep  

  # Does this solution require an extra day of car rental? That'll be $50!
  if latestarrival>earliestdep: totalprice+=50
  
  return totalprice+totalwait

def randomoptimize(domain,costf):
  best=999999999
  bestr=None
  for i in range(0,1000):
    # Create a random solution
    r=[float(random.randint(domain[i][0],domain[i][1])) 
       for i in range(len(domain))]
    
    # Get the cost
    cost=costf(r)
    
    # Compare it to the best one so far
    if cost<best:
      best=cost
      bestr=r 
  return r


def annealingoptimize(domain,costf,T=10000.0,cool=0.95,step=1):
  # Initialize the values randomly
  vec=[float(random.randint(domain[i][0],domain[i][1])) 
       for i in range(len(domain))]
  
  while T>0.1:
    # Choose one of the indices
    i=random.randint(0,len(domain)-1)

    # Choose a direction to change it
    dir=random.randint(-step,step)

    # Create a new list with one of the values changed
    vecb=vec[:]
    vecb[i]+=dir
    if vecb[i]<domain[i][0]: vecb[i]=domain[i][0]
    elif vecb[i]>domain[i][1]: vecb[i]=domain[i][1]

    # Calculate the current cost and the new cost
    ea=costf(vec)
    eb=costf(vecb)
    p=pow(math.e,(-eb-ea)/T)

    print vec,ea


    # Is it better, or does it make the probability
    # cutoff?
    if (eb<ea or random.random()<p):
      vec=vecb      

    # Decrease the temperature
    T=T*cool
  return vec

def swarmoptimize(domain,costf,popsize=20,lrate=0.1,maxv=2.0,iters=50):
  # Initialize individuals
  # current solutions
  x=[]

  # best solutions
  p=[]

  # velocities
  v=[]
  
  for i in range(0,popsize):
    vec=[float(random.randint(domain[i][0],domain[i][1])) 
         for i in range(len(domain))]
    x.append(vec)
    p.append(vec[:])
    v.append([0.0 for i in vec])
  
  
  for ml in range(0,iters):
    for i in range(0,popsize):
      # Best solution for this particle
      if costf(x[i])<costf(p[i]):
        p[i]=x[i][:]
      g=i

      # Best solution for any particle
      for j in range(0,popsize):
        if costf(p[j])<costf(p[g]): g=j
      for d in range(len(x[i])):
        # Update the velocity of this particle
        v[i][d]+=lrate*(p[i][d]-x[i][d])+lrate*(p[g][d]-x[i][d])

        # constrain velocity to a maximum
        if v[i][d]>maxv: v[i][d]=maxv
        elif v[i][d]<-maxv: v[i][d]=-maxv

        # constrain bounds of solutions
        x[i][d]+=v[i][d]
        if x[i][d]<domain[d][0]: x[i][d]=domain[d][0]
        elif x[i][d]>domain[d][1]: x[i][d]=domain[d][1]

    print p[g],costf(p[g])
  return p[g]

########NEW FILE########
__FILENAME__ = advancedclassify
class matchrow:
  def __init__(self,row,allnum=False):
    if allnum:
      self.data=[float(row[i]) for i in range(len(row)-1)]
    else:
      self.data=row[0:len(row)-1]
    self.match=int(row[len(row)-1])

def loadmatch(f,allnum=False):
  rows=[]
  for line in file(f):
    rows.append(matchrow(line.split(','),allnum))
  return rows
 
from pylab import *
def plotagematches(rows):
  xdm,ydm=[r.data[0] for r in rows if r.match==1],\
          [r.data[1] for r in rows if r.match==1]
  xdn,ydn=[r.data[0] for r in rows if r.match==0],\
          [r.data[1] for r in rows if r.match==0] 
  
  plot(xdm,ydm,'bo')
  plot(xdn,ydn,'b+')
  
  show()

def lineartrain(rows):
  averages={}
  counts={}
  
  for row in rows:
    # Get the class of this point
    cl=row.match
    
    averages.setdefault(cl,[0.0]*(len(row.data)))
    counts.setdefault(cl,0)
    
    # Add this point to the averages
    for i in range(len(row.data)):
      averages[cl][i]+=float(row.data[i])
      
    # Keep track of how many points in each class
    counts[cl]+=1
    
  # Divide sums by counts to get the averages
  for cl,avg in averages.items():
    for i in range(len(avg)):
      avg[i]/=counts[cl]
  
  return averages

def dotproduct(v1,v2):
  return sum([v1[i]*v2[i] for i in range(len(v1))])

def veclength(v):
  return sum([p**2 for p in v])

def dpclassify(point,avgs):
  b=(dotproduct(avgs[1],avgs[1])-dotproduct(avgs[0],avgs[0]))/2
  y=dotproduct(point,avgs[0])-dotproduct(point,avgs[1])+b
  if y>0: return 0
  else: return 1

def yesno(v):
  if v=='yes': return 1
  elif v=='no': return -1
  else: return 0
  
def matchcount(interest1,interest2):
  l1=interest1.split(':')
  l2=interest2.split(':')
  x=0
  for v in l1:
    if v in l2: x+=1
  return x

yahookey="YOUR API KEY"
from xml.dom.minidom import parseString
from urllib import urlopen,quote_plus

loc_cache={}
def getlocation(address):
  if address in loc_cache: return loc_cache[address]
  data=urlopen('http://api.local.yahoo.com/MapsService/V1/'+\
               'geocode?appid=%s&location=%s' %
               (yahookey,quote_plus(address))).read()
  doc=parseString(data)
  lat=doc.getElementsByTagName('Latitude')[0].firstChild.nodeValue
  long=doc.getElementsByTagName('Longitude')[0].firstChild.nodeValue  
  loc_cache[address]=(float(lat),float(long))
  return loc_cache[address]

def milesdistance(a1,a2):
  lat1,long1=getlocation(a1)
  lat2,long2=getlocation(a2)
  latdif=69.1*(lat2-lat1)
  longdif=53.0*(long2-long1)
  return (latdif**2+longdif**2)**.5

def loadnumerical():
  oldrows=loadmatch('matchmaker.csv')
  newrows=[]
  for row in oldrows:
    d=row.data
    data=[float(d[0]),yesno(d[1]),yesno(d[2]),
          float(d[5]),yesno(d[6]),yesno(d[7]),
          matchcount(d[3],d[8]),
          milesdistance(d[4],d[9]),
          row.match]
    newrows.append(matchrow(data))
  return newrows

def scaledata(rows):
  low=[999999999.0]*len(rows[0].data)
  high=[-999999999.0]*len(rows[0].data)
  # Find the lowest and highest values
  for row in rows:
    d=row.data
    for i in range(len(d)):
      if d[i]<low[i]: low[i]=d[i]
      if d[i]>high[i]: high[i]=d[i]
  
  # Create a function that scales data
  def scaleinput(d):
     return [(d[i]-low[i])/(high[i]-low[i])
            for i in range(len(low))]
  
  # Scale all the data
  newrows=[matchrow(scaleinput(row.data)+[row.match])
           for row in rows]
  
  # Return the new data and the function
  return newrows,scaleinput


def rbf(v1,v2,gamma=10):
  dv=[v1[i]-v2[i] for i in range(len(v1))]
  l=veclength(dv)
  return math.e**(-gamma*l)

def nlclassify(point,rows,offset,gamma=10):
  sum0=0.0
  sum1=0.0
  count0=0
  count1=0
  
  for row in rows:
    if row.match==0:
      sum0+=rbf(point,row.data,gamma)
      count0+=1
    else:
      sum1+=rbf(point,row.data,gamma)
      count1+=1
  y=(1.0/count0)*sum0-(1.0/count1)*sum1+offset

  if y>0: return 0
  else: return 1

def getoffset(rows,gamma=10):
  l0=[]
  l1=[]
  for row in rows:
    if row.match==0: l0.append(row.data)
    else: l1.append(row.data)
  sum0=sum(sum([rbf(v1,v2,gamma) for v1 in l0]) for v2 in l0)
  sum1=sum(sum([rbf(v1,v2,gamma) for v1 in l1]) for v2 in l1)
  
  return (1.0/(len(l1)**2))*sum1-(1.0/(len(l0)**2))*sum0

########NEW FILE########
__FILENAME__ = facebook
import urllib,md5,webbrowser,time
from xml.dom.minidom import parseString

apikey="47e953c8ea9ed30db904af453125c759"
secret="ea703e4721e8c7bf88b92110a46a9b06"
FacebookURL = "https://api.facebook.com/restserver.php"

def getsinglevalue(node,tag):
  nl=node.getElementsByTagName(tag)
  if len(nl)>0:
    tagNode=nl[0]
    if tagNode.hasChildNodes():
      return tagNode.firstChild.nodeValue
  return ''

def callid(): 
  return str(int(time.time()*10))

class fbsession:
  def __init__(self):
    self.session_secret=None
    self.session_key=None
    self.createtoken()
    webbrowser.open(self.getlogin())
    print "Press enter after logging in:",
    raw_input()
    self.getsession()
  def sendrequest(self, args):
    args['api_key'] = apikey
    args['sig'] = self.makehash(args)
    post_data = urllib.urlencode(args)
    url = FacebookURL + "?" + post_data
    data=urllib.urlopen(url).read()
    print data
    return parseString(data)
  def makehash(self,args):
    hasher = md5.new(''.join([x + '=' + args[x] for x in sorted(args.keys())]))
    if self.session_secret: hasher.update(self.session_secret)
    else: hasher.update(secret)
    return hasher.hexdigest()
  def createtoken(self):
    res = self.sendrequest({'method':"facebook.auth.createToken"})
    self.token = getsinglevalue(res,'token')
  def getlogin(self):
    return "http://api.facebook.com/login.php?api_key="+apikey+\
           "&auth_token=" + self.token
  def getsession(self):
    doc=self.sendrequest({'method':'facebook.auth.getSession',
                               'auth_token':self.token})
    self.session_key=getsinglevalue(doc,'session_key')
    self.session_secret=getsinglevalue(doc,'secret')
  def getfriends(self):
    doc=self.sendrequest({'method':'facebook.friends.get',
                          'session_key':self.session_key,'call_id':callid()})
    results=[]
    for n in doc.getElementsByTagName('result_elt'):
      results.append(n.firstChild.nodeValue)
    return results

  def getinfo(self,users):
    ulist=','.join(users)
    
    fields='gender,current_location,relationship_status,'+\
           'affiliations,hometown_location'
    
    doc=self.sendrequest({'method':'facebook.users.getInfo',
    'session_key':self.session_key,'call_id':callid(),
    'users':ulist,'fields':fields})

    results={}
    for n,id in zip(doc.getElementsByTagName('result_elt'),users):
      # Get the location
      locnode=n.getElementsByTagName('hometown_location')[0]
      loc=getsinglevalue(locnode,'city')+', '+getsinglevalue(locnode,'state')
      
      # Get school
      college=''
      gradyear='0'
      affiliations=n.getElementsByTagName('affiliations_elt')
      for aff in affiliations:
        # Type 1 is college
        if getsinglevalue(aff,'type')=='1': 
          college=getsinglevalue(aff,'name')
          gradyear=getsinglevalue(aff,'year')
      
      results[id]={'gender':getsinglevalue(n,'gender'),
                   'status':getsinglevalue(n,'relationship_status'),
                   'location':loc,'college':college,'year':gradyear}
    return results

  def arefriends(self,idlist1,idlist2):
    id1=','.join(idlist1)
    id2=','.join(idlist2)
    doc=self.sendrequest({'method':'facebook.friends.areFriends',
                          'session_key':self.session_key,'call_id':callid(),
                          'id1':id1,'id2':id2})
    results=[]
    for n in doc.getElementsByTagName('result_elt'):
      results.append(int(n.firstChild.nodeValue))
    return results
  
  

  def makedataset(self):
    from advancedclassify import milesdistance
    # Get all the info for all my friends
    friends=self.getfriends()
    info=self.getinfo(friends)
    ids1,ids2=[],[]
    rows=[]

    # Nested loop to look at every pair of friends
    for i in range(len(friends)):
      f1=friends[i]
      data1=info[f1]
      
      # Start at i+1 so we don't double up
      for j in range(i+1,len(friends)):
        f2=friends[j]
        data2=info[f2]
        ids1.append(f1)
        ids2.append(f2)

        # Generate some numbers from the data
        if data1['college']==data2['college']: sameschool=1
        else: sameschool=0
        male1=(data1['gender']=='Male') and 1 or 0
        male2=(data2['gender']=='Male') and 1 or 0        
        
        row=[male1,int(data1['year']),male2,int(data2['year']),sameschool]
        rows.append(row)
    # Call arefriends in blocks for every pair of people
    arefriends=[]
    for i in range(0,len(ids1),30):
      j=min(i+30,len(ids1))
      pa=self.arefriends(ids1[i:j],ids2[i:j])
      arefriends+=pa
    return arefriends,rows
  

########NEW FILE########
__FILENAME__ = svm
import svmc
from svmc import C_SVC, NU_SVC, ONE_CLASS, EPSILON_SVR, NU_SVR
from svmc import LINEAR, POLY, RBF, SIGMOID
from math import exp, fabs

def _int_array(seq):
	size = len(seq)
	array = svmc.new_int(size)
	i = 0
	for item in seq:
		svmc.int_setitem(array,i,item)
		i = i + 1
	return array

def _double_array(seq):
	size = len(seq)
	array = svmc.new_double(size)
	i = 0
	for item in seq:
		svmc.double_setitem(array,i,item)
		i = i + 1
	return array

def _free_int_array(x):
	if x != 'NULL' and x != None:
		svmc.delete_int(x)

def _free_double_array(x):
	if x != 'NULL' and x != None:
		svmc.delete_double(x)

def _int_array_to_list(x,n):
	return map(svmc.int_getitem,[x]*n,range(n))

def _double_array_to_list(x,n):
	return map(svmc.double_getitem,[x]*n,range(n))

class svm_parameter:
	
	# default values
	default_parameters = {
	'svm_type' : C_SVC,
	'kernel_type' : RBF,
	'degree' : 3,
	'gamma' : 0,		# 1/k
	'coef0' : 0,
	'nu' : 0.5,
	'cache_size' : 40,
	'C' : 1,
	'eps' : 1e-3,
	'p' : 0.1,
	'shrinking' : 1,
	'nr_weight' : 0,
	'weight_label' : [],
	'weight' : [],
	'probability' : 0
	}

	def __init__(self,**kw):
		self.__dict__['param'] = svmc.new_svm_parameter()
		for attr,val in self.default_parameters.items():
			setattr(self,attr,val)
		for attr,val in kw.items():
			setattr(self,attr,val)

	def __getattr__(self,attr):
		get_func = getattr(svmc,'svm_parameter_%s_get' % (attr))
		return get_func(self.param)

	def __setattr__(self,attr,val):

		if attr == 'weight_label':
			self.__dict__['weight_label_len'] = len(val)
			val = _int_array(val)
			_free_int_array(self.weight_label)
		elif attr == 'weight':
			self.__dict__['weight_len'] = len(val)
			val = _double_array(val)
			_free_double_array(self.weight)

		set_func = getattr(svmc,'svm_parameter_%s_set' % (attr))
		set_func(self.param,val)

	def __repr__(self):
		ret = '<svm_parameter:'
		for name in dir(svmc):
			if name[:len('svm_parameter_')] == 'svm_parameter_' and name[-len('_set'):] == '_set':
				attr = name[len('svm_parameter_'):-len('_set')]
				if attr == 'weight_label':
					ret = ret+' weight_label = %s,' % _int_array_to_list(self.weight_label,self.weight_label_len)
				elif attr == 'weight':
					ret = ret+' weight = %s,' % _double_array_to_list(self.weight,self.weight_len)
				else:
					ret = ret+' %s = %s,' % (attr,getattr(self,attr))
		return ret+'>'

	def __del__(self):
		_free_int_array(self.weight_label)
		_free_double_array(self.weight)
		svmc.delete_svm_parameter(self.param)

def _convert_to_svm_node_array(x):
	""" convert a sequence or mapping to an svm_node array """
	import operator

	# Find non zero elements
	iter_range = []
	if type(x) == dict:
		for k, v in x.iteritems():
# all zeros kept due to the precomputed kernel; no good solution yet
#			if v != 0:
				iter_range.append( k )
	elif operator.isSequenceType(x):
		for j in range(len(x)):
#			if x[j] != 0:
				iter_range.append( j )
	else:
		raise TypeError,"data must be a mapping or a sequence"

	iter_range.sort()
	data = svmc.svm_node_array(len(iter_range)+1)
	svmc.svm_node_array_set(data,len(iter_range),-1,0)

	j = 0
	for k in iter_range:
		svmc.svm_node_array_set(data,j,k,x[k])
		j = j + 1
	return data

class svm_problem:
	def __init__(self,y,x):
		assert len(y) == len(x)
		self.prob = prob = svmc.new_svm_problem()
		self.size = size = len(y)

		self.y_array = y_array = svmc.new_double(size)
		for i in range(size):
			svmc.double_setitem(y_array,i,y[i])

		self.x_matrix = x_matrix = svmc.svm_node_matrix(size)
		self.data = []
		self.maxlen = 0;
		for i in range(size):
			data = _convert_to_svm_node_array(x[i])
			self.data.append(data);
			svmc.svm_node_matrix_set(x_matrix,i,data)
			if type(x[i]) == dict:
				if (len(x[i]) > 0):
					self.maxlen = max(self.maxlen,max(x[i].keys()))
			else:
				self.maxlen = max(self.maxlen,len(x[i]))

		svmc.svm_problem_l_set(prob,size)
		svmc.svm_problem_y_set(prob,y_array)
		svmc.svm_problem_x_set(prob,x_matrix)

	def __repr__(self):
		return "<svm_problem: size = %s>" % (self.size)

	def __del__(self):
		svmc.delete_svm_problem(self.prob)
		svmc.delete_double(self.y_array)
		for i in range(self.size):
			svmc.svm_node_array_destroy(self.data[i])
		svmc.svm_node_matrix_destroy(self.x_matrix)

class svm_model:
	def __init__(self,arg1,arg2=None):
		if arg2 == None:
			# create model from file
			filename = arg1
			self.model = svmc.svm_load_model(filename)
		else:
			# create model from problem and parameter
			prob,param = arg1,arg2
			self.prob = prob
			if param.gamma == 0:
				param.gamma = 1.0/prob.maxlen
			msg = svmc.svm_check_parameter(prob.prob,param.param)
			if msg: raise ValueError, msg
			self.model = svmc.svm_train(prob.prob,param.param)

		#setup some classwide variables
		self.nr_class = svmc.svm_get_nr_class(self.model)
		self.svm_type = svmc.svm_get_svm_type(self.model)
		#create labels(classes)
		intarr = svmc.new_int(self.nr_class)
		svmc.svm_get_labels(self.model,intarr)
		self.labels = _int_array_to_list(intarr, self.nr_class)
		svmc.delete_int(intarr)
		#check if valid probability model
		self.probability = svmc.svm_check_probability_model(self.model)

	def predict(self,x):
		data = _convert_to_svm_node_array(x)
		ret = svmc.svm_predict(self.model,data)
		svmc.svm_node_array_destroy(data)
		return ret


	def get_nr_class(self):
		return self.nr_class

	def get_labels(self):
		if self.svm_type == NU_SVR or self.svm_type == EPSILON_SVR or self.svm_type == ONE_CLASS:
			raise TypeError, "Unable to get label from a SVR/ONE_CLASS model"
		return self.labels
		
	def predict_values_raw(self,x):
		#convert x into svm_node, allocate a double array for return
		n = self.nr_class*(self.nr_class-1)//2
		data = _convert_to_svm_node_array(x)
		dblarr = svmc.new_double(n)
		svmc.svm_predict_values(self.model, data, dblarr)
		ret = _double_array_to_list(dblarr, n)
		svmc.delete_double(dblarr)
		svmc.svm_node_array_destroy(data)
		return ret

	def predict_values(self,x):
		v=self.predict_values_raw(x)
		if self.svm_type == NU_SVR or self.svm_type == EPSILON_SVR or self.svm_type == ONE_CLASS:
			return v[0]
		else: #self.svm_type == C_SVC or self.svm_type == NU_SVC
			count = 0
			d = {}
			for i in range(len(self.labels)):
				for j in range(i+1, len(self.labels)):
					d[self.labels[i],self.labels[j]] = v[count]
					d[self.labels[j],self.labels[i]] = -v[count]
					count += 1
			return  d

	def predict_probability(self,x):
		#c code will do nothing on wrong type, so we have to check ourself
		if self.svm_type == NU_SVR or self.svm_type == EPSILON_SVR:
			raise TypeError, "call get_svr_probability or get_svr_pdf for probability output of regression"
		elif self.svm_type == ONE_CLASS:
			raise TypeError, "probability not supported yet for one-class problem"
		#only C_SVC,NU_SVC goes in
		if not self.probability:
			raise TypeError, "model does not support probabiliy estimates"

		#convert x into svm_node, alloc a double array to receive probabilities
		data = _convert_to_svm_node_array(x)
		dblarr = svmc.new_double(self.nr_class)
		pred = svmc.svm_predict_probability(self.model, data, dblarr)
		pv = _double_array_to_list(dblarr, self.nr_class)
		svmc.delete_double(dblarr)
		svmc.svm_node_array_destroy(data)
		p = {}
		for i in range(len(self.labels)):
			p[self.labels[i]] = pv[i]
		return pred, p
	
	def get_svr_probability(self):
		#leave the Error checking to svm.cpp code
		ret = svmc.svm_get_svr_probability(self.model)
		if ret == 0:
			raise TypeError, "not a regression model or probability information not available"
		return ret

	def get_svr_pdf(self):
		#get_svr_probability will handle error checking
		sigma = self.get_svr_probability()
		return lambda z: exp(-fabs(z)/sigma)/(2*sigma)


	def save(self,filename):
		svmc.svm_save_model(filename,self.model)

	def __del__(self):
		svmc.svm_destroy_model(self.model)


def cross_validation(prob, param, fold):
	if param.gamma == 0:
		param.gamma = 1.0/prob.maxlen
	dblarr = svmc.new_double(prob.size)
	svmc.svm_cross_validation(prob.prob, param.param, fold, dblarr)
	ret = _double_array_to_list(dblarr, prob.size)
	svmc.delete_double(dblarr)
	return ret

########NEW FILE########
