__FILENAME__ = chaos
#!python
# chaos.py
import pylab as pl
import numpy as np

# we import the fortran extension module here
import _chaos

# here is the logistic function
# this uses some advanced Python features.
# Logistic is a function that returns another function.
# This is known as a 'closure' and is a very powerful feature.
def logistic(r):
    def _inner(x):
        return r * x * (1.0 - x)
    return _inner

def sine(r):
    from math import sin, pi
    def _inner(x):
        return r * sin(pi * x)
    return _inner

def driver(func, lower, upper, N=400):
    # X will scan over the parameter value.
    X = np.linspace(lower, upper, N)
    nresults, niter = 1000, 1000
    for x in X:
        # We call the fortran function, passing the appropriate Python function.
        results = _chaos.iterate_limit(func(x), 0.5, niter, nresults)
        pl.plot([x]*len(results), results, 'k,')

if __name__ == '__main__':
    pl.figure()
    driver(logistic, 0.0, 4.0)
    pl.xlabel('r')
    pl.ylabel('X limit')
    pl.title('Logistic Map')
    pl.figure()
    driver(sine, 0.0, 1.0)
    pl.xlabel('r')
    pl.ylabel('X limit')
    pl.title('Sine Map')
    pl.show()

########NEW FILE########
__FILENAME__ = pass_args
# pass_args.py
import numpy as np
import _scalar_args

print _scalar_args.scalar_args.__doc__

# these are simple python scalars.
int_in = 1.0
real_in = 10.0

# since these are intent(inout) variables, these must be arrays
int=inout = np.zeros((1,), dtype = np.int32)
real=inout = np.zeros((1,), dtype = np.float32)

# all intent(out) variables are returned in a tuple, so they aren't passed as
# arguments.

int_out, real_out = _scalar_args.scalar_args(int_in, real_in, int_inout, real_inout)

for name in ('int_inout', 'real_inout', 'int_out', 'real_out'):
    print '%s == %s' % (name, locals()[name])

########NEW FILE########
__FILENAME__ = pass_array_args
# pass_array_args.py
import numpy as np
import _array_args

print _array_args.array_args.__doc__

# int_arr is a 10 X 10 array filled with consecutive integers.
# It is in 'fortran' order.
int_arr = np.asfortranarray(np.arange(100, dtype = 'i').reshape(10,10))

# cplx_arr is a 10 X 10 complex array filled with zeros.
# It is in 'fortran' order.
cplx_arr = np.asfortranarray(np.zeros((10,10), dtype = 'F'))

# We invoke the wrapped fortran subroutine.
real_arr = _array_args.array_args(int_arr, cplx_arr)

# Here are the results.
print "int_arr  = %s" %  int_arr
print "real_arr = %s" % real_arr
print "cplx_arr = %s" % cplx_arr

########NEW FILE########
__FILENAME__ = recommend
'''
Original example from Toby Segaran: "Programming Collective Intelligence"
Altered by Richard T. Guy (2010)
'''

from math import sqrt
import numpy

EPS = 1.0e-9 # Never use == for floats.

raw_scores = {

  'Bhargan Basepair' : {
    'Jackson 1999' : 2.5,
    'Chen 2002' : 3.5,
    'Rollins and Khersau 2002' : 3.0,
    'El Awy 2005' : 3.5,
    'Chen 2008' : 2.5,
    'Falkirk et al 2006' : 3.0
  },

  'Fan Fullerene' : {
    'Jackson 1999' : 3.0,
    'Chen 2002' : 3.5,
    'Rollins and Khersau 2002' : 1.5,
    'El Awy 2005' : 5.0,
    'Falkirk et al 2006' : 3.0,
    'Chen 2008' : 3.5
  },

  'Helen Helmet' : {
    'Jackson 1999' : 2.5,
    'Chen 2002' : 3.0,
    'El Awy 2005' : 3.5,
    'Falkirk et al 2006' : 4.0
  },

  'Mehrdad Mapping' : {
    'Chen 2002' : 3.5,
    'Rollins and Khersau 2002' : 3.0,
    'Falkirk et al 2006' : 4.5,
    'El Awy 2005' : 4.0,
    'Chen 2008' : 2.5
  },

  'Miguel Monopole' : {
    'Jackson 1999' : 3.0,
    'Chen 2002' : 4.0,
    'Rollins and Khersau 2002' : 2.0,
    'El Awy 2005' : 3.0,
    'Falkirk et al 2006' : 3.0,
    'Chen 2008' : 2.0
  },

  'Gail Graphics' : {
    'Jackson 1999' : 3.0,
    'Chen 2002' : 4.0,
    'Falkirk et al 2006' : 3.0,
    'El Awy 2005' : 5.0,
    'Chen 2008' : 3.5
  },

  'Stephen Scanner' : {
    'Chen 2002' :4.5,
    'Chen 2008' :1.0,
    'El Awy 2005' :4.0
  }
}

def prep_data(all_scores):
  '''
  Turn {person : {title : score, ...} ...} into NumPy array.
  Each row is a person, each column is a paper title.
  Note that input data is sparse (does not contain all person X paper pairs).
  '''

  # Names of all people in alphabetical order.
  people = all_scores.keys()
  people.sort()

  # Names of all papers in alphabetical order.
  papers = set()
  for person in people:
    for title in all_scores[person].keys():
      papers.add(title)
  papers = list(papers)
  papers.sort()

  # Create and fill array.
  ratings = numpy.zeros((len(people), len(papers)))
  for (person_id, person) in enumerate(people):
    for (title_id, title) in enumerate(papers):
      rating = all_scores[person].get(title, 0)
      ratings[person_id, title_id] = float(rating)

  return people, papers, ratings

def sim_distance(prefs, left_index, right_index):
  '''
  Calculate distance-based similarity score for two people.
  Prefs is array[person X paper].

  Calculated a similarity difference btween two people (rows),
  which is 0 if they have no preferences in common.
  '''

  # Where do both people have preferences?
  left_has_prefs = prefs[left_index, :] > 0
  right_has_prefs = prefs[right_index, :] > 0
  mask = numpy.logical_and(left_has_prefs, right_has_prefs)

  # Not enough signal.
  if numpy.sum(mask) < EPS:
    return 0

  # Return sum-of-squares distance.
  diff = prefs[left_index, mask] - prefs[right_index, mask]
  sum_of_squares = numpy.linalg.norm(diff) ** 2
  result = 1. / (1. + sum_of_squares)
  return result

def sim_pearson(prefs, left_index, right_index):
  '''
  Calculate Pearson correlation between two individuals.
  '''

  # Where do both have ratings?
  rating_left = prefs[left_index, :]
  rating_right = prefs[right_index, :]
  mask = numpy.logical_and(rating_left > 0, rating_right > 0)

  # Note that summing over Booleans gives number of Trues
  num_common = sum(mask)

  # Return zero if there are no common ratings.
  if num_common == 0:
    return 0

  # Calculate Pearson score "r"
  varcovar = numpy.cov(rating_left[mask], rating_right[mask])
  numerator = varcovar[0,1]

  denominator = sqrt(varcovar[0,0]) * sqrt(varcovar[1,1])

  if denominator < EPS:
    return 0

  r = numerator / denominator
  return r

def top_matches(ratings, person, num, sim_func):
  '''
  Return the most similar individuals to a person.
  '''

  scores = []
  for other in range(ratings.shape[0]):
    if other != person:
      scores.append((sim_func(ratings, person, other), other))

  scores.sort()
  scores.reverse()
  return scores[0:num]

def calculate_similar(paper_ids, ratings, num=10):
  '''
  Find the papers that are most similar to each other.
  '''

  result = {}
  ratings_by_paper = ratings.T
  for item in range(ratings_by_paper.shape[0]):
    unnamed_scores = top_matches(ratings_by_paper, item, num, sim_distance)
    scores = [(x[0], paper_ids[x[1]]) for x in unnamed_scores]
    result[paper_ids[item]] = scores

  return result

def recommend(prefs, subject, sim_func):
  '''
  Get recommendations for an individual from a weighted average of other people.
  '''

  totals = {}
  sim_sums = {}
  num_people = prefs.shape[0]
  num_papers = prefs.shape[1]

  for other in range(num_people):

    # Don't compare people to themselves.
    if other == subject:
      continue
    sim = sim_func(prefs, subject, other)

    # ignore scores of zero or lower
    if sim < EPS:
      continue

    for title in range(num_papers):
      
      # Only score papers this person hasn't seen yet.
      if prefs[subject, title] < EPS and prefs[other, title] > EPS:
        
        # Similarity * Score
        if title in totals:
          totals[title] += prefs[other, title] * sim
        else:
          totals[title] = 0

        # Sum of similarities
        if title in sim_sums():
          sim_sums[title] += sim
        else:
          sim_sums[title] = 0

  # Create the normalized list
  
  rankings = []
  for title, total in totals.items():
    rankings.append((total/sim_sums[title], title))

  # Return the sorted list
  rankings.sort()
  rankings.reverse()
  return rankings

def test():
  person_ids, paper_ids, all_ratings = prep_data(raw_scores)
  print 'person_ids', person_ids
  print 'paper_ids', paper_ids
  print 'all_ratings', all_ratings
  print 'similarity distance', sim_distance(all_ratings, 0, 1)
  print 'similarity Pearson', sim_pearson(all_ratings, 0, 1)
  print top_matches(all_ratings, 0, 5, sim_pearson)
  print calculate_similar(paper_ids, all_ratings)
  print recommend(all_ratings, 0, sim_distance)
  print recommend(all_ratings, 1, sim_distance)
	
if __name__ == '__main__':
  test()

########NEW FILE########
__FILENAME__ = segaran-recommend
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
__FILENAME__ = constants
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy constants, Crawl before you walk!

#A plethora of important fundamental constants can be found in
import scipy.constants
#NOTE: this module is not automatically included when you "import scipy"

#Some very basic pieces of information are given as module attributes
print("SciPy thinks that pi = %.16f"%scipy.constants.pi)
import math
print("While math thinks that pi = %.16f"%math.pi)
print("SciPy also thinks that the speed of light is c = %.1F"%scipy.constants.c)
print("")

#But the real value of SciPy constants is its enormous physical constant database
print("SciPy physical constants are of the form:")
print("      scipy.constants.physical_constants[name] = (value, units, uncertainty)")
print("")

print("For example the mass of an alpha particle is %s"%str(scipy.constants.physical_constants["alpha particle mass"]))
print("But buyer beware! Let's look at the speed of light again.")
print("c = %s"%str(scipy.constants.physical_constants["speed of light in vacuum"]))
print("The uncertainty in c should not be zero!")
print("")

print("Check http://docs.scipy.org/doc/scipy/reference/constants.html for a complete listing.")


########NEW FILE########
__FILENAME__ = image_tricks
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy Image Tricks, fly before you....You can do that?!

#For some reason that has yet to be explained to me, SciPy has the ability to treat 2D & 3D arrays
#as images.  You can even convert PIL images or read in external files as numpy arrays!
#From here, you can fool around with the raw image data at will.  Naturally, this functionality 
#is buried within the 'miscellaneous' module.
import scipy.misc

#First let's read in an image file.  For now, make it a JPEG.
img = scipy.misc.imread("image.jpg")
#Note that this really is an array!
print(str(img))

#We can now apply some basic filters...
img = scipy.misc.imfilter(img, 'blur')

#We can even rotate the image, counter-clockwise by degrees.
img = scipy.misc.imrotate(img, 45)

#And then, we can rewrite the array to an image file.
scipy.misc.imsave("image1.jpg", img)

#Because the array takes integer values from 0 - 255, we can easily define our own filters as well!
def InverseImage(imgarr):
	return 255 - imgarr

#Starting fresh we get... 
img = scipy.misc.imread("image.jpg")
img = scipy.misc.imrotate(img, 330)
img = InverseImage(img)
scipy.misc.imsave("image2.jpg", img)

#Check out http://docs.scipy.org/doc/scipy/reference/misc.html for a complete listing.


########NEW FILE########
__FILENAME__ = integrate
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy Integration, run before you glide. 

#Tools used to calculate numerical, definite integrals may be found in the 'integrate' module.
import scipy.integrate
#For kicks, let's also grab
import scipy.special
import numpy

#There are two basic ways you can integrate in SciPy:
#     1. Integrate a function, or
#     2. Integrate piecewise data.

#First Let's deal with integration of functions.
#Recall that in Python, functions are also objects.  
#Therefore you can pass functions as arguments to other functions!
#Just make sure that the function that you want to integrate returns a float, 
#or, at the very least, an object that has a __float__() method.

#The simplest way to compute a functions definite integral is via the quad(...) function.
def CrazyFunc(x):
	return (scipy.special.i1(x) - 1)**3

print("Try integrating CrazyFunc on the range [-5, 10]...")

val, err = scipy.integrate.quad(CrazyFunc, -5, 10)

print("A Crazy Function integrates to %.8E"%val)  
print("And with insanely low error of %.8E"%err)  
print("")

#You can also use scipy.integrate.Inf for infinity in the limits of integration
print("Now try integrating e^x on [-inf, 0]")
print("(val, err) = " + str( scipy.integrate.quad(scipy.exp, -scipy.integrate.Inf, 0.0) ))
print("")

#2D integrations follows similarly, 
def dA_Sphere(phi, theta):
	return  scipy.sin(phi)

print("Integrate the surface area of the unit sphere...")
val, err = scipy.integrate.dblquad(dA_Sphere, 0.0, 2.0*scipy.pi, lambda theta: 0.0,  lambda theta: scipy.pi )
print("val = %.8F"%val)
print("err = %.8E"%err)
print("")

def dV_Sphere(phi, theta, r):
	return r * r * dA_Sphere(phi, theta)

print("Integrate the volume of a sphere with r=3.5...")
val, err = scipy.integrate.tplquad(dV_Sphere, 0.0, 3.5, lambda r: 0.0, lambda r: 2.0*scipy.pi, lambda x, y: 0.0, lambda x, y: scipy.pi)
print("val = %.8F"%val)
print("err = %.8E"%err)
print("")

#Now, only very rarely will scientists (and even more rarely engineers) will truely 'know' 
#the function that they wish to integrate.  Much more often we'll have piecewise data 
#that we wish numerically integrate (ie sum an array y(x), biased by array x).  
#This can be done in SciPy through the trapz function.

y = range(0, 11)
print("Trapazoidally integrate y = x on [0,10]...")
val = scipy.integrate.trapz(y)
print("val = %F"%val)
print("")

#You can also define a domain to integrate over.
x = numpy.arange(0.0, 20.5, 0.5)
y = x * x
print("Trapazoidally integrate y = x^2 on [0,20] with half steps...")
val = scipy.integrate.trapz(y, x)
print("val = %F"%val)
print("")

print("Trapazoidally integrate y = x^2 with dx=0.5...")
val = scipy.integrate.trapz(y, dx=0.5)
print("val = %F"%val)
print("")

def dDecay(y, t, lam):
	return -lam*y

#Of course, sometimes we have simple ODEs that we want to integrate over time for...
#These are generally of the form:
#     dy / dt = f(y, t)
#For example take the decay equation...
#     f(y, t) = - lambda * y
#We can integrate this using SciPy's 'odeint'  This is of the form:
#     odeint( f, y0, [t0, t1, ...])
#Let's try it... 
vals = scipy.integrate.odeint( lambda y, t: dDecay(y, t, 0.2), 1.0, [0.0, 10.0] ) 
print("If you start with a mass of y(0) = %F"%vals[0][0])
print("you'll only have y(t=10) = %F left."%vals[1][0])

#Check out http://docs.scipy.org/doc/scipy/reference/integrate.html for a complete listing.

########NEW FILE########
__FILENAME__ = pade1
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy Pade, glide before you fly!

#As you have seen, SciPy has some really neat functionality that comes stock.
#Oddly, some of the best stuff is in the 'miscelaneous' module.
import scipy.misc 

#Most people are familar with the polynomial expansions of a function:
#     f(x) = a + bx + cx^2 + ...
#Or a Taylor expansion:
#     f(x) = sum( d^n f(a) / dx^n (x-a)^n /n! )
#However, there exists the lesser known, more exact Pade approximation.
#This basically splits up a function into a numerator and a denominator.
#     f(x) = p(x) / q(x)
#Then, you can approximate p(x) and q(x) using a power series.  
#A more complete treatment is available in Section 5.12 in 'Numerical Recipes' by W. H. Press, et al.


#The stregnth of this method is demonstated though figures...
from pylab import *

#Let's expand e^x to fith order and record the coefficents 
e_exp = [1.0, 1.0, 1.0/2.0, 1.0/6.0, 1.0/24.0, 1.0/120.0]

#The Pade coefficients are given simply by, 
p, q = scipy.misc.pade(e_exp, 2)
#p and q are of numpy's polynomial class
#So the Pade approximation is given by 
def PadeAppx(x):
	return p(x) / q(x)

#Let's test it...
x = arange(0.0, 3.1, 0.1)

e_exp.reverse()
e_poly = poly1d(e_exp)

plot(x, PadeAppx(x), 'k--', label="Pade Approximation")
plot(x, scipy.e**x, 'k-', label=r'$e^x$')
plot(x, e_poly(x), 'r-', label="Power Series")

#axis([0, 10, -2, 1.25])
xlabel(r'$x$')
ylabel("Exponential Functions")

legend(loc=0)

show()

#Check out http://docs.scipy.org/doc/scipy/reference/misc.html for a complete listing.


########NEW FILE########
__FILENAME__ = pade2
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy Pade, glide before you fly!

#As you have seen, SciPy has some really neat functionality that comes stock.
#Oddly, some of the best stuff is in the 'miscelaneous' module.
import scipy.misc 
from pylab import *

#So our exponential pade approimation didn't give us great gains, 
#But let's try approximating a rougher function.
def f(x):
	return (7.0 + (1+x)**(4.0/3.0))**(1.0/3.0)

#Through someone else's labors we know the expansion to be... 
f_exp = [2.0, 1.0/9.0, 1.0/81.0, -49.0/8748.0, 175.0/78732.0]

#The Pade coefficients are given simply by, 
p, q = scipy.misc.pade(f_exp, (5-1)/2)
#p and q are of numpy's polynomial class
#So the Pade approximation is given by 
def PadeAppx(x):
	return p(x) / q(x)

#Let's test it...
x = arange(0.0, 10.01, 0.01)

f_exp.reverse()
f_poly = poly1d(f_exp)

plot(x, PadeAppx(x), 'k--', label="Pade Approximation")
plot(x, f(x), 'k-', label=r'$f(x)$')
plot(x, f_poly(x), 'r-', label="Power Series")

xlabel(r'$x$')
ylabel("Polynomial Function")

legend(loc=0)

show()

#Check out http://docs.scipy.org/doc/scipy/reference/misc.html for a complete listing.


########NEW FILE########
__FILENAME__ = special_functions
#The Hacker Within: Python Boot Camp 2010 - Session 07 - Using SciPy.
#Presented by Anthony Scopatz.
#
#SciPy special functions, walk before you run!

#Code that numerically approximates common (and some not-so-common) special functions can be found in 'scipy.special'
from scipy.special import *

#Here you can find things like error functions, gamma functions, Legendre polynomials, etc.
#But as a example let's focus on my favorites: Bessel functions.
#Time for some graphs...
from pylab import *

x = arange(0.0, 10.1, 0.1)

for n in range(4):
	j = jn(n, x)
	plot(x, j, 'k-')
	text(x[10*(n+1)+1], j[10*(n+1)], r'$J_%r$'%n)

for n in range(3):
	y = yn(n, x)
	plot(x, y, 'k--')
	text(x[10*(n)+6], y[10*(n)+5], r'$Y_%r$'%n)

axis([0, 10, -2, 1.25])
xlabel(r'$x$')
ylabel("Bessel Functions")

show()

#Check out http://docs.scipy.org/doc/scipy/reference/special.html for a complete listing.

#Note that the figure that was created here is a reproduction of 
#Figure 6.5.1 in 'Numerical Recipes' by W. H. Press, et al.

########NEW FILE########
__FILENAME__ = generate_data
import sys
import os
import math
from random import choice, randint, random
import calendar

class Person:
    maxCI = 25
    # teenagers are hereby declared to be between 11 and 20 years old
    birthyears = range(1991,2000)
    repeatFraction = 0.1
    
    names = ['john', 'paul', 'george', 'ringo',\
        'baby','scary','posh','ginger','madonna',\
        'prince','robyn','beyonce','jay'] 
    words =['Beatle','Spice','Backstreet','Sync','Jonas',\
        'Lennon','McCartney','Starr','Harrison','Z',\
        'Carrot','Broccoli','Asparagus','Beet']
    CIs=range(1,maxCI+1)
    birthmonths= range(1,13)
    #ensure unique ids
    serialNum=173
    sexes=['M','F','N']

    def age(self, curyr=2011, curmo=11):
        return curyr+(1.*curmo-1.)/12. - self.birthyear - 1.*(self.birthmonth-1.)/12.

    def __init__(self):
        self.subject = choice(Person.names)+choice(Person.words)+ ('%03d' % Person.serialNum)
        Person.serialNum = Person.serialNum + 1

        self.birthyear  = choice(Person.birthyears)
        self.birthmonth = choice(Person.birthmonths)
   
        self.sex = choice(Person.sexes)
        age = self.age(2011,11)
        self.CI = choice(Person.CIs) 

        # newer CIs have better volume, discrimination;
        # range goes down with age.  (say). 

        CInewness = (self.CI-1.)/(1.*max(Person.CIs))
        # from oldest CI to newest, gain 2 volume pts: 
        self.trueVolume = randint(0,4)+randint(1,4)+round(2.*CInewness)

        # from oldest CI to newest, gain 3 discrimination pts: 
        self.trueDiscrimination = randint(0,3)+randint(1,4)+round(3.*CInewness)
        
        # 21-year-olds would lose 3 range points over 10 year olds (say)
        self.trueRange = randint(0,4)+randint(1,6)+round((10.-(self.age()-11.))*3./10.)

        # Most people don't repeat; those that do take the test 2-5 times
        if (random() > Person.repeatFraction):
            self.repeats = 1
        else:
            self.repeats=choice(range(2,6))


from numpy import polyfit, array
def test_peopleCorrelations():
    testpeople = []
    npeople = 4000
    for pnum in xrange(1,npeople):
        testpeople.append(Person())

    data = [[p.age(), p.CI, p.trueVolume, p.trueRange, p.trueDiscrimination] for p in testpeople]
    ages, cis, vols, ranges, discs = zip(*data)

    CIVolParam, dummy   = polyfit(cis, vols, 1) 
    CIRangeParam, dummy = polyfit(cis, ranges, 1) 
    CIDiscParam, dummy  = polyfit(cis, discs, 1)

    AgeVolParam, dummy   = polyfit(ages, vols, 1) 
    AgeRangeParam, dummy = polyfit(ages, ranges, 1) 
    AgeDiscParam, dummy  = polyfit(ages, discs, 1) 

    assert CIVolParam > 0.75*(2./25.) and CIVolParam < 1.25*(2./25.)
    assert CIDiscParam > 0.75*(3./25.) and CIDiscParam < 1.25*(3./25.)
    assert AgeRangeParam < 0.75*(-3./10.) and AgeRangeParam > 1.25*(-3./10.)

    zeroTol = 0.03
    assert abs(CIRangeParam) < zeroTol
    assert abs(AgeVolParam)  < zeroTol
    assert abs(AgeDiscParam) < zeroTol



class Measurement:
    incompleteFraction = 0.05
    serialNum = 211
    def randomDate(self):
        hrs = range(8,17)
        mins = range(1,60)
        secs = range(1,60)
        months = range(5,10)

        month = choice(months)
        monthname = calendar.month_abbr[month]
        day = choice(range(1,calendar.monthrange(2011, month)[1]))
        dayname = calendar.day_abbr[calendar.weekday(2011, month, day)]
        hr = choice(hrs)
        min = choice(mins)
        sec = choice(secs)
        
        datestring = '%s %s %d %02d:%02d:%02d %s' % (dayname, monthname, day, hr, min, sec, '2011')
        return [datestring, month, day, hr, min, sec]

    def limit(self,n):
        if n < 1 :
            n = 1
        if n > 10 :
            n = 10
        return n 

    def __init__(self, p):
        """Generate a result"""
        self.person = p
        self.datestring, self.month, self.day, self.hr, self.min, self.sec = self.randomDate();

        self.serialNum = Measurement.serialNum
        Measurement.serialNum = Measurement.serialNum + 1

        # +/- 1 random measurement error
        self.volume = self.person.trueVolume + choice([-1,0,0,0,+1])
        self.range  = self.person.trueRange + choice([-1,0,0,0,+1])
        self.discrimination  = self.person.trueDiscrimination + choice([-1,0,0,0,+1])

        self.volume = self.limit(self.volume)
        self.range = self.limit(self.range)
        self.discrimination = self.limit(self.discrimination)

        # before this date, things were being recorded 0..9 rather than 1..10
        fixmonth = 8
        fixday = 18
        fixhr = 10

        fixdate = fixmonth*10000 + fixday*100 + fixhr 
        checkdate = self.month*10000 + self.day*100 + self.hr 
        if checkdate < fixdate:
            self.volume = self.volume - 1
            self.range = self.range - 1
            self.discrimination = self.discrimination - 1
    
        if (random() < Measurement.incompleteFraction):
            self.discrimination = None
        

    def __str__(self):
        text = '# ' + '\n'
        text += "%s: %s\n" % ( 'Reported', self.datestring )
        text += "%s: %s\n" % ( 'Subject',  self.person.subject )
        text += "%s: %4d/%02d\n" % ( 'Year/month of birth', self.person.birthyear,  self.person.birthmonth )
        text += "%s: %s\n" % ( 'Sex', self.person.sex )
        text += "%s: %d\n" % ( 'CI type', self.person.CI )
        text += "%s: %d\n" % ( 'Volume', self.volume )
        text += "%s: %d\n" % ( 'Range', self.range )
        if self.discrimination is None :
            text += "%s: \n" % ( 'Discrimination' )
        else:
            text += "%s: %d\n" % ( 'Discrimination', self.discrimination )
    
        return text

class Datataker:
    names = ['angela', 'JamesD', 'jamesm', 'Frank_Richard',\
        'lab183','THOMAS','alexander','Beth','Lawrence',\
        'Toni', 'gerdal', 'Bert', 'Ernie', 'olivia', 'Leandra',\
        'sonya_p', 'h_jackson'] 
    filenamestyles = ['data_%d','Data%04d','%d','%04d','audioresult-%05d']
    suffixstyles = ['.dat','.txt','','','.DATA']
    tookNotesFraction = 0.5
    notes = ['Took data on Thursday and Friday until 4pm;\nAll day saturday.\n',\
             'Contact Janice about new calibration for data in August.\n',\
             'Submission of hours last week shows only 7 hours because \none was spent cleaning the lab.\n',\
             'Had some trouble accessing data submission form on Saturday,\nso fewer submissions then.\n',\
             'Third subject had real problems with the discrimiation test, so omitted.\n',\
             'Discrimination test seems kind of flaky - had to skip in several cases\n',\
             'Fuse blew midway through this weeks data taking,\nfewer results than last week.\n']
    notefilenames = ['notes.txt','NOTES','ReadMe','misc.txt','About']

    def __init__(self):
        self.name = choice(Datataker.names)
        Datataker.names.remove(self.name)
        self.filenameprefix = choice(Datataker.filenamestyles)
        self.filenamesuffix = choice(Datataker.suffixstyles)
        self.measures = []
        self.tookNotes = False
        if (random() < Datataker.tookNotesFraction) :
            self.tookNotes = True 
            self.notes = choice(Datataker.notes)
            self.noteFilename = choice(Datataker.notefilenames)

    def addmeasurement(self,measurement):
        self.measures.append(measurement)

    def write(self):
        os.mkdir(self.name)
        os.chdir(self.name)

        if (self.tookNotes):
            fname = self.noteFilename
            file = open(fname, 'w')
            file.write(self.notes)
            file.close()

        for m in self.measures:
            fname = self.filenameprefix % m.serialNum + self.filenamesuffix
            file = open(fname, 'w')
            file.write(str(m))
            file.close()
        os.chdir('..')
            
 
def main():
    #test_peopleCorrelations()

    npeople = 300 # should generate ~ .9*300 + 3.5*.1*300 ~ 375 files
    nfiles = 351

    people = []
    for pnum in range(npeople):
        people.append(Person())

    measurements = []
    for p in people:
        for m in range(p.repeats):
            measurements.append(Measurement(p))

    nexperimenters = 7
    experimenters = []
    for i in range(nexperimenters):
        experimenters.append(Datataker())

    for fnum in xrange(min(len(measurements), nfiles)):
        ex = choice(experimenters)
        ex.addmeasurement(measurements[fnum]) 

    os.mkdir('data')
    os.chdir('data')
    for ex in experimenters:
        ex.write()
    os.chdir('..')

if __name__=='__main__':
    sys.exit(main())


########NEW FILE########
