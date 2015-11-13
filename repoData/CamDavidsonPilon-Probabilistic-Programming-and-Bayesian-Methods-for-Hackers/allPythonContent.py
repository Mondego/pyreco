__FILENAME__ = daft_plot
#daft drawing for SMS example
import matplotlib.pyplot as plt



try:
    import daft
except ImportError:
    print "python library Daft required."
    

pgm = daft.PGM([9, 4], origin=[.5,.5])
pgm.add_node(daft.Node("tau", r"$\tau$", 4.0, 3.5))
pgm.add_node(daft.Node("alpha", r"$\alpha$", 6, 4.0))
pgm.add_node(daft.Node("lambda1", r"$\lambda_1$", 5.5, 3.2,))
pgm.add_node(daft.Node("lambda2", r"$\lambda_2$", 6.5, 3.2))
pgm.add_node(daft.Node("lambda", r"$\lambda$", 5.0, 2.0))
pgm.add_node(daft.Node("obs", "obs", 5.0, 1.0, 1.2, observed=True))



pgm.add_edge("tau", "lambda")
pgm.add_edge("alpha", "lambda1")
pgm.add_edge("alpha", "lambda2")
pgm.add_edge("lambda1", "lambda")
pgm.add_edge("lambda2", "lambda")

pgm.add_edge("lambda", "obs")
pgm.render()
plt.figure( figsize=(12,5) )
plt.show()
########NEW FILE########
__FILENAME__ = separation_plot
# separation plot
# Author: Cameron Davidson-Pilon,2013
# see http://mdwardlab.com/sites/default/files/GreenhillWardSacks.pdf


import matplotlib.pyplot as plt
import numpy as np



def separation_plot( p, y, **kwargs ):
    """
    This function creates a separation plot for logistic and probit classification. 
    See http://mdwardlab.com/sites/default/files/GreenhillWardSacks.pdf
    
    p: The proportions/probabilities, can be a nxM matrix which represents M models.
    y: the 0-1 response variables.
    
    """    
    assert p.shape[0] == y.shape[0], "p.shape[0] != y.shape[0]"
    n = p.shape[0]

    try:
        M = p.shape[1]
    except:
        p = p.reshape( n, 1 )
        M = p.shape[1]

    #colors = np.array( ["#fdf2db", "#e44a32"] )
    colors_bmh = np.array( ["#eeeeee", "#348ABD"] )


    fig = plt.figure( )#figsize = (8, 1.3*M) )
    
    for i in range(M):
        ax = fig.add_subplot(M, 1, i+1)
        ix = np.argsort( p[:,i] )
        #plot the different bars
        bars = ax.bar( np.arange(n), np.ones(n), width=1., 
                color = colors_bmh[ y[ix].astype(int) ], 
                edgecolor = 'none')
        ax.plot( np.arange(n), p[ix,i], "k", 
                linewidth = 1.,drawstyle="steps-post" )
        #create expected value bar.
        ax.vlines( [(1-p[ix,i]).sum()], [0], [1] )
        #ax.grid(False)
        #ax.axis('off')
        plt.xlim( 0, n-1)
        
    plt.tight_layout()
    
    return
    

    

########NEW FILE########
__FILENAME__ = github_pull
#github data scrapper

"""
variables of interest:
    indp. variables
    - language, given as a binary variable. Need 4 positions for 5 langagues
    - #number of days created ago, 1 position
    - has wiki? Boolean, 1 position
    - followers, 1 position
    - following, 1 position
    - constant
    
    dep. variables
    -stars/watchers
    -forks

"""
from json import loads
import datetime
import numpy as np
from requests import get



MAX = 8000000
today =  datetime.datetime.today()
randint = np.random.randint
N = 120 #sample size. 
auth = ("username", "password" )

language_mappings = {"Python": 0, "JavaScript": 1, "Ruby": 2, "Java":3, "Shell":4, "PHP":5}

#define data matrix: 
X = np.zeros( (N , 12), dtype = int )

for i in xrange(N):
    is_fork = True
    is_valid_language = False
    
    while is_fork == True or is_valid_language == False:
        is_fork = True
        is_valid_language = False
        
        params = {"since":randint(0, MAX ) }
        r = get("https://api.github.com/repositories", params = params, auth=auth )
        results = loads( r.text )[0]
        #im only interested in the first one, and if it is not a fork.
        is_fork = results["fork"]
        
        r = get( results["url"], auth = auth)
        
        #check the language
        repo_results = loads( r.text )
        try: 
            language_mappings[ repo_results["language" ] ]
            is_valid_language = True
        except:
            pass
        
    

    #languages 
    X[ i, language_mappings[ repo_results["language" ] ] ] = 1
    
    #delta time
    X[ i, 6] = ( today - datetime.datetime.strptime( repo_results["created_at"][:10], "%Y-%m-%d" ) ).days
    
    #haswiki
    X[i, 7] = repo_results["has_wiki"]
    
    #get user information
    r = get( results["owner"]["url"] , auth = auth)
    user_results = loads( r.text )
    X[i, 8] = user_results["following"]
    X[i, 9] = user_results["followers"]
    
    #get dep. data
    X[i, 10] = repo_results["watchers_count"]
    X[i, 11] = repo_results["forks_count"]
    print 
    print " -------------- "
    print i, ": ", results["full_name"], repo_results["language" ], repo_results["watchers_count"], repo_results["forks_count"]
    print " -------------- "
    print 
    
np.savetxt("data/github_data.csv", X, delimiter=",", fmt="%d" )
    



########NEW FILE########
__FILENAME__ = top_pic_comments
import sys

import numpy as np
from IPython.core.display import Image

import praw


reddit = praw.Reddit("BayesianMethodsForHackers")
subreddit  = reddit.get_subreddit( "pics" )

top_submissions = subreddit.get_top()


n_pic = int( sys.argv[1] ) if sys.argv[1] else 1

i = 0
while i < n_pic:
    top_submission = top_submissions.next()
    while "i.imgur.com" not in top_submission.url:
        #make sure it is linking to an image, not a webpage.
        top_submission = top_submissions.next()
    i+=1

print "Title of submission: \n", top_submission.title
top_post_url = top_submission.url
#top_submission.replace_more_comments(limit=5, threshold=0)
print top_post_url

upvotes = []
downvotes = []
contents = []
_all_comments = top_submission.comments
all_comments=[]
for comment in _all_comments:
            try:
                upvotes.append( comment.ups )
                downvotes.append( comment.downs )
                contents.append( comment.body )
            except Exception as e:
                continue
                
votes = np.array( [ upvotes, downvotes] ).T




    
    
    
    
    
    
    
    
    
    
    
    
    

    


########NEW FILE########
__FILENAME__ = DarkWorldsMetric
""" DarkWorldsMetricMountianOsteric.py
Custom evaluation metric for the 'Observing Dark Worlds' competition.

[Description of metric, or reference to documentation.]

Update: Made for the training set only so users can check there results from the training c

@Author: David Harvey
Created: 22 August 2012
"""

import numpy as np
import math as mt
import itertools as it
import csv as c
import getopt as gt
import sys as sys
import argparse as ap
import string as st
import random as rd

def calc_delta_r(x_predicted,y_predicted,x_true,y_true): 
    """ Compute the scalar distance between predicted halo centers
    and the true halo centers. Predictions are matched to the closest
    halo center.
    Notes: It takes in the predicted and true positions, and then loops over each possible configuration and finds the most optimal one.
    Arguments:
        x_predicted, y_predicted: vector for predicted x- and y-positions (1 to 3 elements)
        x_true, y_true: vector for known x- and y-positions (1 to 3 elements)
    Returns:
        radial_distance: vector containing the scalar distances between the predicted halo centres and the true halo centres (1 to 3 elements)
        true_halo_idexes: vector containing indexes of the input true halos which matches the predicted halo indexes (1 to 3 elements)
        measured_halo_indexes: vector containing indexes of the predicted halo position with the  reference to the true halo position.
       e.g if true_halo_indexes=[0,1] and measured_halo_indexes=[1,0] then the first x,y coordinates of the true halo position matches the second input of the predicted x,y coordinates.
    """
    
    num_halos=len(x_true) #Only works for number of halos > 1
    num_configurations=mt.factorial(num_halos) #The number of possible different comb
    configurations=np.zeros([num_halos,num_configurations],int) #The array of combinations
                                                                #I will pass back
    distances = np.zeros([num_configurations],float) #The array of the distances
                                                     #for all possible combinations
    
    radial_distance=[]  #The vector of distances
                        #I will pass back
    
    #Pick a combination of true and predicted 
    a=['01','012'] #Input for the permutatiosn, 01 number halos or 012
    count=0 #For the index of the distances array
    true_halo_indexes=[] #The tuples which will show the order of halos picked
    predicted_halo_indexes=[]
    distances_perm=np.zeros([num_configurations,num_halos],float) #The distance between each
                                                                  #true and predicted
                                                                  #halo for every comb
    true_halo_indexes_perm=[] #log of all the permutations of true halos used
    predicted_halo_indexes_perm=[] #log of all the predicted permutations
    
    for  perm in it.permutations(a[num_halos-2],num_halos):
        which_true_halos=[]
        which_predicted_halos=[]
        for j in xrange(num_halos): #loop through all the true halos with the

            distances_perm[count,j]=np.sqrt((x_true[j]-x_predicted[int(perm[j])])**2\
                                      +(y_true[j]-y_predicted[int(perm[j])])**2)
                                      #This array logs the distance between true and
                                      #predicted halo for ALL configurations
                                      
            which_true_halos.append(j) #log the order in which I try each true halo
            which_predicted_halos.append(int(perm[j])) #log the order in which I true
                                                       #each predicted halo
        true_halo_indexes_perm.append(which_true_halos) #this is a tuple of tuples of
                                                        #all of thifferent config
                                                        #true halo indexes
        predicted_halo_indexes_perm.append(which_predicted_halos)
        
        distances[count]=sum(distances_perm[count,0::]) #Find what the total distances
                                                        #are for each configuration
        count=count+1

    config = np.where(distances == min(distances))[0][0] #The configuration used is the one
                                                         #which has the smallest distance
    radial_distance.append(distances_perm[config,0::]) #Find the tuple of distances that
                                                       #correspond to this smallest distance
    true_halo_indexes=true_halo_indexes_perm[config] #Find the tuple of the index which refers
                                                     #to the smallest distance
    predicted_halo_indexes=predicted_halo_indexes_perm[config]
            
    return radial_distance,true_halo_indexes,predicted_halo_indexes


def calc_theta(x_predicted, y_predicted, x_true, y_true, x_ref, y_ref):
    """ Calculate the angle the predicted position and the true position, where the zero degree corresponds to the line joing the true halo position and the reference point given.
    Arguments:
        x_predicted, y_predicted: vector for predicted x- and y-positions (1 to 3 elements)
        x_true, y_true: vector for known x- and y-positions (1 to 3 elements)
        Note that the input of these are matched up so that the first elements of each
        vector are associated with one another
        x_ref, y_ref: scalars of the x,y coordinate of reference point
    Returns:
        Theta: A vector containing the angles of the predicted halo w.r.t the true halo
        with the vector joining the reference point and the halo as the zero line. 
    """

    num_halos=len(x_predicted)
    theta=np.zeros([num_halos+1],float) #Set up the array which will pass back the values
    phi = np.zeros([num_halos],float)
    
    psi = np.arctan( (y_true-y_ref)/(x_true-x_ref) )

    
                     # Angle at which the halo is at
                                                     #with respect to the reference point
    phi[x_true != x_ref] = np.arctan((y_predicted[x_true != x_predicted]-\
                                      y_true[x_true != x_predicted])\
                    /(x_predicted[x_true != x_predicted]-\
                      x_true[x_true != x_predicted])) # Angle of the estimate
                                                               #wrt true halo centre

    #Before finding the angle with the zero line as the line joiing the halo and the reference
    #point I need to convert the angle produced by Python to an angle between 0 and 2pi
    phi =convert_to_360(phi, x_predicted-x_true,\
         y_predicted-y_true)
    psi = convert_to_360(psi, x_true-x_ref,\
                             y_true-y_ref)
    theta = phi-psi #The angle with the baseline as the line joing the ref and the halo

    
    theta[theta< 0.0]=theta[theta< 0.0]+2.0*mt.pi #If the angle of the true pos wrt the ref is
                                                  #greater than the angle of predicted pos
                                                  #and the true pos then add 2pi
    return theta


def convert_to_360(angle, x_in, y_in):
    """ Convert the given angle to the true angle in the range 0:2pi 
    Arguments:
        angle:
        x_in, y_in: the x and y coordinates used to determine the quartile
        the coordinate lies in so to add of pi or 2pi
    Returns:
        theta: the angle in the range 0:2pi
    """
    n = len(x_in)
    for i in xrange(n):
        if x_in[i] < 0 and y_in[i] > 0:
            angle[i] = angle[i]+mt.pi
        elif x_in[i] < 0 and y_in[i] < 0:
            angle[i] = angle[i]+mt.pi
        elif x_in[i] > 0 and y_in[i] < 0:
            angle[i] = angle[i]+2.0*mt.pi
        elif x_in[i] == 0 and y_in[i] == 0:
            angle[i] = 0
        elif x_in[i] == 0 and y_in[i] > 0:
            angle[i] = mt.pi/2.
        elif x_in[i] < 0 and y_in[i] == 0:
            angle[i] = mt.pi
        elif x_in[i] == 0 and y_in[i] < 0:
            angle[i] = 3.*mt.pi/2.



    return angle

def get_ref(x_halo,y_halo,weight):
    """ Gets the reference point of the system of halos by weighted averaging the x and y
    coordinates.
    Arguments:
         x_halo, y_halo: Vector num_halos referring to the coordinates of the halos
         weight: the weight which will be assigned to the position of the halo
         num_halos: number of halos in the system
    Returns:
         x_ref, y_ref: The coordinates of the reference point for the metric
    """
 

        #Find the weighted average of the x and y coordinates
    x_ref = np.sum([x_halo*weight])/np.sum([weight])
    y_ref = np.sum([y_halo*weight])/np.sum([weight])


    return x_ref,y_ref

    
def main_score( nhalo_all, x_true_all, y_true_all, x_ref_all, y_ref_all, sky_prediction):
    """abstracts the score from the old command-line interface. 
       sky_prediction is a dx2 array of predicted x,y positions
    
    -camdp"""
    
    r=np.array([],dtype=float) # The array which I will log all the calculated radial distances
    angle=np.array([],dtype=float) #The array which I will log all the calculated angles
    #Load in the sky_ids from the true
    num_halos_total=0 #Keep track of how many halos are input into the metric

        

    for selectskyinsolutions, sky in enumerate(sky_prediction): #Loop through each line in result.csv and analyse each one


        nhalo=int(nhalo_all[selectskyinsolutions])#How many halos in the
                                                       #selected sky?
        x_true=x_true_all[selectskyinsolutions][0:nhalo]
        y_true=y_true_all[selectskyinsolutions][0:nhalo]
                    
        x_predicted=np.array([],dtype=float)
        y_predicted=np.array([],dtype=float)
        for i in xrange(nhalo):
            x_predicted=np.append(x_predicted,float(sky[0])) #get the predicted values
            y_predicted=np.append(y_predicted,float(sky[1]))
            #The solution file for the test data provides masses 
            #to calculate the centre of mass where as the Training_halo.csv
            #direct provides x_ref y_ref. So in the case of test data
            #we need to calculate the ref point from the masses using
            #Get_ref()
  
        x_ref=x_ref_all[selectskyinsolutions]
        y_ref=y_ref_all[selectskyinsolutions]

        num_halos_total=num_halos_total+nhalo


        #Single halo case, this needs to be separately calculated since
        #x_ref = x_true
        if nhalo == 1:
            #What is the radial distance between the true and predicted position
            r=np.append(r,np.sqrt( (x_predicted-x_true)**2 \
                                          + (y_predicted-y_true)**2)) 
            #What is the angle between the predicted position and true halo position
            if (x_predicted-x_true) != 0:
                psi = np.arctan((y_predicted-y_true)/(x_predicted-x_true))
            else: psi=0.
            theta = convert_to_360([psi], [x_predicted-x_true], [y_predicted-y_true])
            angle=np.append(angle,theta)

        
        else:        
            #r_index_index, contains the radial distances of the predicted to
            #true positions. These are found by matching up the true halos to
            #the predicted halos such that the average of all the radial distances
            #is optimal. it also contains indexes of the halos used which are used to
            #show which halo has been mathced to which.
            
            r_index_index = calc_delta_r(x_predicted, y_predicted, x_true, \
                                         y_true)
  
            r=np.append(r,r_index_index[0][0])
            halo_index= r_index_index[1] #The true halos indexes matched with the 
            predicted_index=r_index_index[2] #predicted halo index

            angle=np.append(angle,calc_theta\
                                  (x_predicted[predicted_index],\
                                   y_predicted[predicted_index],\
                                   x_true[halo_index],\
                                   y_true[halo_index],x_ref,\
                                   y_ref)) # Find the angles of the predicted
                                               #position wrt to the halo and
                                               # add to the vector angle

    
    # Find what the average distance the estimate is from the halo position
    av_r=sum(r)/len(r)
    
    #In order to quantify the orientation invariance we will express each angle 
    # as a vector and find the average vector
    #R_bar^2=(1/N Sum^Ncos(theta))^2+(1/N Sum^Nsin(theta))**2
    
    N = float(num_halos_total)
    angle_vec = np.sqrt(( 1.0/N * sum(np.cos(angle)) )**2 + \
        ( 1.0/N * sum(np.sin(angle)) )**2)
    
    W1=1./1000. #Weight the av_r such that < 1 is a good score > 1 is not so good.
    W2=1.
    metric = W1*av_r + W2*angle_vec #Weighted metric, weights TBD
    print 'Your average distance in pixels you are away from the true halo is', av_r
    print 'Your average angular vector is', angle_vec
    print 'Your score for the training data is', metric
    return metric
    
    
def main(user_fname, fname):
    """ Script to compute the evaluation metric for the Observing Dark Worlds competition. You can run it on your training data to understand how well you have done with the training data.
    """

    r=np.array([],dtype=float) # The array which I will log all the calculated radial distances
    angle=np.array([],dtype=float) #The array which I will log all the calculated angles
    #Load in the sky_ids from the true
    
    true_sky_id=[]
    sky_loader = c.reader(open(fname, 'rb')) #Load in the sky_ids from the solution file
    for row in sky_loader:
        true_sky_id.append(row[0])

    #Load in the true values from the solution file

    nhalo_all=np.loadtxt(fname,usecols=(1,),delimiter=',',skiprows=1)
    x_true_all=np.loadtxt(fname,usecols=(4,6,8),delimiter=',',skiprows=1)
    y_true_all=np.loadtxt(fname,usecols=(5,7,9),delimiter=',',skiprows=1)
    x_ref_all=np.loadtxt(fname,usecols=(2,),delimiter=',',skiprows=1)
    y_ref_all=np.loadtxt(fname,usecols=(3,),delimiter=',',skiprows=1)

    
    for row in sky_loader:
        true_sky_id.append(row[1])
        

    
    num_halos_total=0 #Keep track of how many halos are input into the metric


    sky_prediction = c.reader(open(user_fname, 'rb')) #Open the result.csv   
   
    try: #See if the input file from user has a header on it
         #with open('JoyceTest/trivialUnitTest_Pred.txt', 'r') as f:
        with open(user_fname, 'r') as f:   
            header = float((f.readline()).split(',')[1]) #try and make where the
                                                         #first input would be
                                                         #a float, if succeed it
                                                         #is not a header
        print 'THE INPUT FILE DOES NOT APPEAR TO HAVE A HEADER'
    except :
        print 'THE INPUT FILE APPEARS TO HAVE A HEADER, SKIPPING THE FIRST LINE'

        skip_header = sky_prediction.next()
        

    for sky in sky_prediction: #Loop through each line in result.csv and analyse each one
        sky_id = str(sky[0]) #Get the sky_id of the input
        does_it_exist=true_sky_id.count(sky_id) #Is the input sky_id
                                                #from user a real one?
        
        if does_it_exist > 0: #If it does then find the matching solutions to the sky_id
                            selectskyinsolutions=true_sky_id.index(sky_id)-1
        else: #Otherwise exit
            print 'Sky_id does not exist, formatting problem: ',sky_id
            sys.exit(2)


        nhalo=int(nhalo_all[selectskyinsolutions])#How many halos in the
                                                       #selected sky?
        x_true=x_true_all[selectskyinsolutions][0:nhalo]
        y_true=y_true_all[selectskyinsolutions][0:nhalo]
                    
        x_predicted=np.array([],dtype=float)
        y_predicted=np.array([],dtype=float)
        for i in xrange(nhalo):
            x_predicted=np.append(x_predicted,float(sky[2*i+1])) #get the predicted values
            y_predicted=np.append(y_predicted,float(sky[2*i+2]))
            #The solution file for the test data provides masses 
            #to calculate the centre of mass where as the Training_halo.csv
            #direct provides x_ref y_ref. So in the case of test data
            #we need to calculae the ref point from the masses using
            #Get_ref()
  
        x_ref=x_ref_all[selectskyinsolutions]
        y_ref=y_ref_all[selectskyinsolutions]

        num_halos_total=num_halos_total+nhalo


        #Single halo case, this needs to be separately calculated since
        #x_ref = x_true
        if nhalo == 1:
            #What is the radial distance between the true and predicted position
            r=np.append(r,np.sqrt( (x_predicted-x_true)**2 \
                                          + (y_predicted-y_true)**2)) 
            #What is the angle between the predicted position and true halo position
            if (x_predicted-x_true) != 0:
                psi = np.arctan((y_predicted-y_true)/(x_predicted-x_true))
            else: psi=0.
            theta = convert_to_360([psi], [x_predicted-x_true], [y_predicted-y_true])
            angle=np.append(angle,theta)

        
        else:        
            #r_index_index, contains the radial distances of the predicted to
            #true positions. These are found by matching up the true halos to
            #the predicted halos such that the average of all the radial distances
            #is optimal. it also contains indexes of the halos used which are used to
            #show which halo has been mathced to which.
            
            r_index_index = calc_delta_r(x_predicted, y_predicted, x_true, \
                                         y_true)
  
            r=np.append(r,r_index_index[0][0])
            halo_index= r_index_index[1] #The true halos indexes matched with the 
            predicted_index=r_index_index[2] #predicted halo index

            angle=np.append(angle,calc_theta\
                                  (x_predicted[predicted_index],\
                                   y_predicted[predicted_index],\
                                   x_true[halo_index],\
                                   y_true[halo_index],x_ref,\
                                   y_ref)) # Find the angles of the predicted
                                               #position wrt to the halo and
                                               # add to the vector angle

    
    # Find what the average distance the estimate is from the halo position
    av_r=sum(r)/len(r)
    
    #In order to quantify the orientation invariance we will express each angle 
    # as a vector and find the average vector
    #R_bar^2=(1/N Sum^Ncos(theta))^2+(1/N Sum^Nsin(theta))**2
    
    N = float(num_halos_total)
    angle_vec = np.sqrt(( 1.0/N * sum(np.cos(angle)) )**2 + \
        ( 1.0/N * sum(np.sin(angle)) )**2)
    
    W1=1./1000. #Weight the av_r such that < 1 is a good score > 1 is not so good.
    W2=1.
    metric = W1*av_r + W2*angle_vec #Weighted metric, weights TBD
    print 'Your average distance in pixels you are away from the true halo is', av_r
    print 'Your average angular vector is', angle_vec
    print 'Your score for the training data is', metric


if __name__ == "__main__":
    #For help just typed 'python DarkWorldsMetric.py -h'

    parser = ap.ArgumentParser(description='Work out the Metric for your input file')
    parser.add_argument('inputfile',type=str,nargs=1,help='Input file of halo positions. Needs to be in the format SkyId,halo_x1,haloy1,halox_2,halo_y2,halox3,halo_y3 ')
    parser.add_argument('reffile',type=str,nargs=1,help='This should point to Training_halos.csv')
    args = parser.parse_args()

    user_fname=args.inputfile[0]
    filename = (args.reffile[0]).count('Training_halos.csv')
    if filename == 0:
        fname=args.reffile[0]+str('Training_halos.csv')
    else:
        fname=args.reffile[0]

    main(user_fname, fname)
    

########NEW FILE########
__FILENAME__ = draw_sky2
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
import numpy as np

def draw_sky( galaxies ):
    """adapted from Vishal Goklani"""
    size_multiplier = 45
    fig = plt.figure(figsize=(10,10))
    #fig.patch.set_facecolor("blue")
    ax = fig.add_subplot(111, aspect='equal')
    n = galaxies.shape[0]
    for i in xrange(n):
        _g = galaxies[i,:]
        x,y = _g[0], _g[1]
        d = np.sqrt( _g[2]**2 + _g[3]**2 )
        a = 1.0/ ( 1 - d )
        b = 1.0/( 1 + d)
        theta = np.degrees( np.arctan2( _g[3], _g[2])*0.5 )
        
        ax.add_patch( Ellipse(xy=(x, y), width=size_multiplier*a, height=size_multiplier*b, angle=theta) )
    ax.autoscale_view(tight=True)
    
    return fig
########NEW FILE########
__FILENAME__ = other_strats
#other strats.
# TODO: UBC strat, epsilon-greedy

import scipy.stats as stats
import numpy as np
from pymc import rbeta

rand = np.random.rand
beta = stats.beta


class GeneralBanditStrat( object ):	

    """
    Implements a online, learning strategy to solve
    the Multi-Armed Bandit problem.
    
    parameters:
        bandits: a Bandit class with .pull method
		choice_function: accepts a self argument (which gives access to all the variables), and 
						returns and int between 0 and n-1
    methods:
        sample_bandits(n): sample and train on n pulls.

    attributes:
        N: the cumulative number of samples
        choices: the historical choices as a (N,) array
        bb_score: the historical score as a (N,) array

    """
    
    def __init__(self, bandits, choice_function):
        
        self.bandits = bandits
        n_bandits = len( self.bandits )
        self.wins = np.zeros( n_bandits )
        self.trials = np.zeros(n_bandits )
        self.N = 0
        self.choices = []
        self.score = []
        self.choice_function = choice_function

    def sample_bandits( self, n=1 ):
        
        score = np.zeros( n )
        choices = np.zeros( n )
        
        for k in range(n):
            #sample from the bandits's priors, and select the largest sample
            choice = self.choice_function(self)
            
            #sample the chosen bandit
            result = self.bandits.pull( choice )
            
            #update priors and score
            self.wins[ choice ] += result
            self.trials[ choice ] += 1
            score[ k ] = result 
            self.N += 1
            choices[ k ] = choice
            
        self.score = np.r_[ self.score, score ]
        self.choices = np.r_[ self.choices, choices ]
        return 
        
	
def bayesian_bandit_choice(self):
	return np.argmax( rbeta( 1 + self.wins, 1 + self.trials - self.wins) )
    
def max_mean( self ):
    """pick the bandit with the current best observed proportion of winning """
    return np.argmax( self.wins / ( self.trials +1 ) )

def lower_credible_choice( self ):
    """pick the bandit with the best LOWER BOUND. See chapter 5"""
    def lb(a,b):
        return a/(a+b) - 1.65*np.sqrt( (a*b)/( (a+b)**2*(a+b+1) ) )
    a = self.wins + 1
    b = self.trials - self.wins + 1
    return np.argmax( lb(a,b) )
    
def upper_credible_choice( self ):
    """pick the bandit with the best LOWER BOUND. See chapter 5"""
    def lb(a,b):
        return a/(a+b) + 1.65*np.sqrt( (a*b)/( (a+b)**2*(a+b+1) ) )
    a = self.wins + 1
    b = self.trials - self.wins + 1
    return np.argmax( lb(a,b) )
    
def random_choice( self):
    return np.random.randint( 0, len( self.wins ) )
    
    
def ucb_bayes( self ):
	C = 0
	n = 10000
	alpha =1 - 1./( (self.N+1) )
	return np.argmax( beta.ppf( alpha,
							   1 + self.wins, 
							   1 + self.trials - self.wins ) )
							   
	
	
	
class Bandits(object):
    """
    This class represents N bandits machines.

    parameters:
        p_array: a (n,) Numpy array of probabilities >0, <1.

    methods:
        pull( i ): return the results, 0 or 1, of pulling 
                   the ith bandit.
    """
    def __init__(self, p_array):
        self.p = p_array
        self.optimal = np.argmax(p_array)
        
    def pull( self, i ):
        #i is which arm to pull
        return rand() < self.p[i]
    
    def __len__(self):
        return len(self.p)

########NEW FILE########
__FILENAME__ = ystockquote
#
#  ystockquote : Python module - retrieve stock quote data from Yahoo Finance
#
#  Copyright (c) 2007,2008,2013 Corey Goldberg (cgoldberg@gmail.com)
#
#  license: GNU LGPL
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2.1 of the License, or (at your option) any later version.
#
#  Requires: Python 2.7/3.2+


__version__ = '0.2.2'


try:
    # py3
    from urllib.request import Request, urlopen
    from urllib.parse import urlencode
except ImportError:
    # py2
    from urllib2 import Request, urlopen
    from urllib import urlencode


def _request(symbol, stat):
    url = 'http://finance.yahoo.com/d/quotes.csv?s=%s&f=%s' % (symbol, stat)
    req = Request(url)
    resp = urlopen(req)
    return str(resp.read().decode('utf-8').strip())


def get_all(symbol):
    """
    Get all available quote data for the given ticker symbol.

    Returns a dictionary.
    """
    values = _request(symbol, 'l1c1va2xj1b4j4dyekjm3m4rr5p5p6s7').split(',')
    return dict(
        price=values[0],
        change=values[1],
        volume=values[2],
        avg_daily_volume=values[3],
        stock_exchange=values[4],
        market_cap=values[5],
        book_value=values[6],
        ebitda=values[7],
        dividend_per_share=values[8],
        dividend_yield=values[9],
        earnings_per_share=values[10],
        fifty_two_week_high=values[11],
        fifty_two_week_low=values[12],
        fifty_day_moving_avg=values[13],
        two_hundred_day_moving_avg=values[14],
        price_earnings_ratio=values[15],
        price_earnings_growth_ratio=values[16],
        price_sales_ratio=values[17],
        price_book_ratio=values[18],
        short_ratio=values[19],
    )


def get_price(symbol):
    return _request(symbol, 'l1')


def get_change(symbol):
    return _request(symbol, 'c1')


def get_volume(symbol):
    return _request(symbol, 'v')


def get_avg_daily_volume(symbol):
    return _request(symbol, 'a2')


def get_stock_exchange(symbol):
    return _request(symbol, 'x')


def get_market_cap(symbol):
    return _request(symbol, 'j1')


def get_book_value(symbol):
    return _request(symbol, 'b4')


def get_ebitda(symbol):
    return _request(symbol, 'j4')


def get_dividend_per_share(symbol):
    return _request(symbol, 'd')


def get_dividend_yield(symbol):
    return _request(symbol, 'y')


def get_earnings_per_share(symbol):
    return _request(symbol, 'e')


def get_52_week_high(symbol):
    return _request(symbol, 'k')


def get_52_week_low(symbol):
    return _request(symbol, 'j')


def get_50day_moving_avg(symbol):
    return _request(symbol, 'm3')


def get_200day_moving_avg(symbol):
    return _request(symbol, 'm4')


def get_price_earnings_ratio(symbol):
    return _request(symbol, 'r')


def get_price_earnings_growth_ratio(symbol):
    return _request(symbol, 'r5')


def get_price_sales_ratio(symbol):
    return _request(symbol, 'p5')


def get_price_book_ratio(symbol):
    return _request(symbol, 'p6')


def get_short_ratio(symbol):
    return _request(symbol, 's7')


def get_historical_prices(symbol, start_date, end_date):
    """
    Get historical prices for the given ticker symbol.
    Date format is 'YYYY-MM-DD'

    Returns a nested list (first item is list of column headers).
    """
    params = urlencode({
        's': symbol,
        'a': int(start_date[5:7]) - 1,
        'b': int(start_date[8:10]),
        'c': int(start_date[0:4]),
        'd': int(end_date[5:7]) - 1,
        'e': int(end_date[8:10]),
        'f': int(end_date[0:4]),
        'g': 'd',
        'ignore': '.csv',
    })
    url = 'http://ichart.yahoo.com/table.csv?%s' % params
    req = Request(url)
    resp = urlopen(req)
    content = str(resp.read().decode('utf-8').strip())
    days = content.splitlines()
    return [day.split(',') for day in days]
########NEW FILE########
__FILENAME__ = auc
#contributed by Ben Hammer, 2013 


def tied_rank(x):
    """
    Computes the tied rank of elements in x.

    This function computes the tied rank of elements in x.

    Parameters
    ----------
    x : list of numbers, numpy array

    Returns
    -------
    score : list of numbers
            The tied rank f each element in x

    """
    sorted_x = sorted(zip(x,range(len(x))))
    r = [0 for k in x]
    cur_val = sorted_x[0][0]
    last_rank = 0
    for i in range(len(sorted_x)):
        if cur_val != sorted_x[i][0]:
            cur_val = sorted_x[i][0]
            for j in range(last_rank, i): 
                r[sorted_x[j][1]] = float(last_rank+1+i)/2.0
            last_rank = i
        if i==len(sorted_x)-1:
            for j in range(last_rank, i+1): 
                r[sorted_x[j][1]] = float(last_rank+i+2)/2.0
    return r

def auc(actual, posterior):
    """
    Computes the area under the receiver-operater characteristic (AUC)

    This function computes the AUC error metric for binary classification.

    Parameters
    ----------
    actual : list of binary numbers, numpy array
             The ground truth value
    posterior : same type as actual
                Defines a ranking on the binary numbers, from most likely to
                be positive to least likely to be positive.

    Returns
    -------
    score : double
            The mean squared error between actual and posterior

    """
    r = tied_rank(posterior)
    num_positive = len([0 for x in actual if x==1])
    num_negative = len(actual)-num_positive
    sum_positive = sum([r[i] for i in range(len(r)) if actual[i]==1])
    auc = ((sum_positive - num_positive*(num_positive+1)/2.0) /
           (num_negative*num_positive))
    return auc
########NEW FILE########
__FILENAME__ = SMS_behaviour
import pymc as pm
import numpy as np

count_data = np.loadtxt("../../Chapter1_Introduction/data/txtdata.csv")
n_count_data = len(count_data)

alpha = 1.0 / count_data.mean()  # recall count_data is
                                 # the variable that holds our txt counts

lambda_1 = pm.Exponential("lambda_1",  alpha)
lambda_2 = pm.Exponential("lambda_2", alpha)

tau = pm.DiscreteUniform("tau", lower=0, upper=n_count_data)


@pm.deterministic
def lambda_(tau=tau, lambda_1=lambda_1, lambda_2=lambda_2):
    out = np.zeros(n_count_data)
    out[:tau] = lambda_1  # lambda before tau is lambda1
    out[tau:] = lambda_2  # lambda after tau is lambda2
    return out

observation = pm.Poisson("obs", lambda_, value=count_data, observed=True)
model = pm.Model([observation, lambda_1, lambda_2, tau])


mcmc = pm.MCMC(model)
mcmc.sample(100000, 50000, 1)

########NEW FILE########
__FILENAME__ = ABtesting
"""
This is an example of using Bayesian A/B testing

"""

import pymc as pm

# these two quantities are unknown to us.
true_p_A = 0.05
true_p_B = 0.04

# notice the unequal sample sizes -- no problem in Bayesian analysis.
N_A = 1500
N_B = 1000

# generate data
observations_A = pm.rbernoulli(true_p_A, N_A)
observations_B = pm.rbernoulli(true_p_B, N_B)


# set up the pymc model. Again assume Uniform priors for p_A and p_B
p_A = pm.Uniform("p_A", 0, 1)
p_B = pm.Uniform("p_B", 0, 1)


# define the deterministic delta function. This is our unknown of interest.

@pm.deterministic
def delta(p_A=p_A, p_B=p_B):
    return p_A - p_B


# set of observations, in this case we have two observation datasets.
obs_A = pm.Bernoulli("obs_A", p_A, value=observations_A, observed=True)
obs_B = pm.Bernoulli("obs_B", p_B, value=observations_B, observed=True)

# to be explained in chapter 3.
mcmc = pm.MCMC([p_A, p_B, delta, obs_A, obs_B])
mcmc.sample(20000, 1000)

########NEW FILE########
__FILENAME__ = FreqOfCheaters
import pymc as pm

p = pm.Uniform("freq_cheating", 0, 1)


@pm.deterministic
def p_skewed(p=p):
    return 0.5 * p + 0.25

yes_responses = pm.Binomial(
    "number_cheaters", 100, p_skewed, value=35, observed=True)

model = pm.Model([yes_responses, p_skewed, p])

# To Be Explained in Chapter 3!
mcmc = pm.MCMC(model)
mcmc.sample(50000, 25000)

########NEW FILE########
__FILENAME__ = ORingFailure
import numpy as np
import pymc as pm


challenger_data = np.genfromtxt(
    "../../Chapter2_MorePyMC/data/challenger_data.csv",
    skip_header=1, usecols=[1, 2], missing_values="NA", delimiter=",")
# drop the NA values
challenger_data = challenger_data[~np.isnan(challenger_data[:, 1])]


temperature = challenger_data[:, 0]
D = challenger_data[:, 1]  # defect or not?

beta = pm.Normal("beta", 0, 0.001, value=0)
alpha = pm.Normal("alpha", 0, 0.001, value=0)


@pm.deterministic
def p(temp=temperature, alpha=alpha, beta=beta):
    return 1.0 / (1. + np.exp(beta * temperature + alpha))


observed = pm.Bernoulli("bernoulli_obs", p, value=D, observed=True)

model = pm.Model([observed, beta, alpha])

# mysterious code to be explained in Chapter 3
map_ = pm.MAP(model)
map_.fit()
mcmc = pm.MCMC(model)
mcmc.sample(260000, 220000, 2)

########NEW FILE########
__FILENAME__ = ClusteringWithGaussians
import numpy as np
import pymc as pm


data = np.loadtxt("../../Chapter3_MCMC/data/mixture_data.csv",  delimiter=",")


p = pm.Uniform("p", 0, 1)

assignment = pm.Categorical("assignment", [p, 1 - p], size=data.shape[0])

taus = 1.0 / pm.Uniform("stds", 0, 100, size=2) ** 2  # notice the size!
centers = pm.Normal("centers", [150, 150], [0.001, 0.001], size=2)

"""
The below deterministic functions map a assingment, in this case 0 or 1,
to a set of parameters, located in the (1,2) arrays `taus` and `centers.`
"""


@pm.deterministic
def center_i(assignment=assignment, centers=centers):
        return centers[assignment]


@pm.deterministic
def tau_i(assignment=assignment, taus=taus):
        return taus[assignment]

# and to combine it with the observations:
observations = pm.Normal("obs", center_i, tau_i,
                         value=data, observed=True)

# below we create a model class
model = pm.Model([p, assignment, taus, centers])


map_ = pm.MAP(model)
map_.fit()
mcmc = pm.MCMC(model)
mcmc.sample(100000, 50000)

########NEW FILE########
__FILENAME__ = github_datapull

try:
    import numpy as np
    from requests import get
    from bs4 import BeautifulSoup




    stars_to_explore = ( 2**np.arange( -1, 16 ) ).astype("int")
    forks_to_explore = ( 2**np.arange( -1, 16 ) ).astype("int")
    repo_with_stars = np.ones_like( stars_to_explore )
    repo_with_forks = np.ones_like( forks_to_explore )

    URL = "https://github.com/search"
    print "Scrapping data from Github. Sorry Github..."
    print "The data is contained in variables `foo_to_explore` and `repo_with_foo`"
    print
    print "stars first..."
    payload = {"q":""}
    for i, _star in enumerate(stars_to_explore):
        payload["q"] = "stars:>=%d"%_star
        r = get( URL, params = payload )
        soup = BeautifulSoup( r.text )
        try:
            h3 = soup.find( class_="sort-bar").find( "h3" ).text #hopefully the github search results page plays nicely.
            value = int( h3.split(" ")[2].replace(",", "" ) )
        except AttributeError as e:
            #there might be less than 10 repos, so I'll count the number of display results
            value  = len( soup.findAll(class_= "mega-icon-public-repo" ) )
        
        repo_with_stars[i] = value
        print "number of repos with greater than or equal to %d stars: %d"%(_star, value )
    
    #repo_with_stars = repo_with_stars.astype("float")/repo_with_stars[0]


    print 
    print "forks second..."
    payload = {"q":""}
    for i, _fork in enumerate(stars_to_explore):
        payload["q"] = "forks:>=%d"%_fork
        r = get( URL, params = payload )
        soup = BeautifulSoup( r.text )
        try:
            h3 = soup.find( class_="sort-bar").find( "h3" ).text #hopefully the github search results page plays nicely.
            value = int( h3.split(" ")[2].replace(",", "" ) )
        except AttributeError as e:
            #there might be less than 10 repos, so I'll count the number of display results
            value  = len( soup.findAll(class_= "mega-icon-public-repo" ) )
        
        repo_with_forks[i] = value
        print "number of repos with greater than or equal to %d forks: %d"%(_fork, value )
    
    #repo_with_forks = repo_with_forks.astype("float")/repo_with_forks[0]
    
    np.savetxt( "data/gh_forks.csv", np.concatenate( [forks_to_explore, repo_with_forks], axis=1) )
    np.savetxt( "data/gh_stars.csv", np.concatenate( [stars_to_explore, repo_with_stars], axis=1) )

except ImportError as e:
    print e
    print "requests / BeautifulSoup not found. Using data pulled on Feburary 11, 2013"
    _data = np.genfromtxt( "data/gh_forks.csv", delimiter = "," ) #cehck this.
    forks_to_explore = _data[:,0]
    repo_with_forks  = _data[:,1]    
    
    _data = np.genfromtxt( "data/gh_stars.csv", delimiter = "," ) #cehck this.
    stars_to_explore = _data[:,0]
    repo_with_stars  = _data[:,1]
    
    
    
########NEW FILE########
__FILENAME__ = github_events
#github_events.py

try:
    from json import loads

    import numpy as np
    from requests import get

except ImportError as e:
    raise e


URL = "https://api.github.com/events"

#github allows up to 10 pages of 30 events, but we will only keep the unique ones. 
ids = np.empty(300, dtype=int)

k  = 0
for page in range(10,0, -1):
    
    r = get( URL, params = {"page":page} )
    data = loads(r.text)
    for event in data:
        ids[k] = ( event["actor"]["id"] )
        k+=1
  
ids = np.unique( ids.astype(int) )
########NEW FILE########
