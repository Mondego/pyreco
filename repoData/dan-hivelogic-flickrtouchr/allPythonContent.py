__FILENAME__ = flickrtouchr
#!/usr/bin/env python

#
# FlickrTouchr - a simple python script to grab all your photos from flickr, 
#                dump into a directory - organised into folders by set - 
#                along with any favourites you have saved.
#
#                You can then sync the photos to an iPod touch.
#
# Version:       1.2
#
# Original Author:	colm - AT - allcosts.net  - Colm MacCarthaigh - 2008-01-21
#
# Modified by:			Dan Benjamin - http://hivelogic.com										
#
# License:       		Apache 2.0 - http://www.apache.org/licenses/LICENSE-2.0.html
#

import xml.dom.minidom
import webbrowser
import urlparse
import urllib2
import unicodedata
import cPickle
import md5
import sys
import os

API_KEY       = "e224418b91b4af4e8cdb0564716fa9bd"
SHARED_SECRET = "7cddb9c9716501a0"

#
# Utility functions for dealing with flickr authentication
#
def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc.encode("utf-8")

#
# Get the frob based on our API_KEY and shared secret
#
def getfrob():
    # Create our signing string
    string = SHARED_SECRET + "api_key" + API_KEY + "methodflickr.auth.getFrob"
    hash   = md5.new(string).digest().encode("hex")

    # Formulate the request
    url    = "http://api.flickr.com/services/rest/?method=flickr.auth.getFrob"
    url   += "&api_key=" + API_KEY + "&api_sig=" + hash

    try:
        # Make the request and extract the frob
        response = urllib2.urlopen(url)
    
        # Parse the XML
        dom = xml.dom.minidom.parse(response)

        # get the frob
        frob = getText(dom.getElementsByTagName("frob")[0].childNodes)

        # Free the DOM 
        dom.unlink()

        # Return the frob
        return frob

    except:
        raise "Could not retrieve frob"

#
# Login and get a token
#
def froblogin(frob, perms):
    string = SHARED_SECRET + "api_key" + API_KEY + "frob" + frob + "perms" + perms
    hash   = md5.new(string).digest().encode("hex")

    # Formulate the request
    url    = "http://api.flickr.com/services/auth/?"
    url   += "api_key=" + API_KEY + "&perms=" + perms
    url   += "&frob=" + frob + "&api_sig=" + hash

    # Tell the user what's happening
    print "In order to allow FlickrTouchr to read your photos and favourites"
    print "you need to allow the application. Please press return when you've"
    print "granted access at the following url (which should have opened"
    print "automatically)."
    print
    print url
    print 
    print "Waiting for you to press return"

    # We now have a login url, open it in a web-browser
    webbrowser.open_new(url)

    # Wait for input
    sys.stdin.readline()

    # Now, try and retrieve a token
    string = SHARED_SECRET + "api_key" + API_KEY + "frob" + frob + "methodflickr.auth.getToken"
    hash   = md5.new(string).digest().encode("hex")
    
    # Formulate the request
    url    = "http://api.flickr.com/services/rest/?method=flickr.auth.getToken"
    url   += "&api_key=" + API_KEY + "&frob=" + frob
    url   += "&api_sig=" + hash

    # See if we get a token
    try:
        # Make the request and extract the frob
        response = urllib2.urlopen(url)
    
        # Parse the XML
        dom = xml.dom.minidom.parse(response)

        # get the token and user-id
        token = getText(dom.getElementsByTagName("token")[0].childNodes)
        nsid  = dom.getElementsByTagName("user")[0].getAttribute("nsid")

        # Free the DOM
        dom.unlink()

        # Return the token and userid
        return (nsid, token)
    except:
        raise "Login failed"

# 
# Sign an arbitrary flickr request with a token
# 
def flickrsign(url, token):
    query  = urlparse.urlparse(url).query
    query += "&api_key=" + API_KEY + "&auth_token=" + token
    params = query.split('&') 

    # Create the string to hash
    string = SHARED_SECRET
    
    # Sort the arguments alphabettically
    params.sort()
    for param in params:
        string += param.replace('=', '')
    hash   = md5.new(string).digest().encode("hex")

    # Now, append the api_key, and the api_sig args
    url += "&api_key=" + API_KEY + "&auth_token=" + token + "&api_sig=" + hash
    
    # Return the signed url
    return url

#
# Grab the photo from the server
#
def getphoto(id, token, filename):
    try:
        # Contruct a request to find the sizes
        url  = "http://api.flickr.com/services/rest/?method=flickr.photos.getSizes"
        url += "&photo_id=" + id
    
        # Sign the request
        url = flickrsign(url, token)
    
        # Make the request
        response = urllib2.urlopen(url)
        
        # Parse the XML
        dom = xml.dom.minidom.parse(response)

        # Get the list of sizes
        sizes =  dom.getElementsByTagName("size")

        # Grab the original if it exists
        if (sizes[-1].getAttribute("label") == "Original"):
          imgurl = sizes[-1].getAttribute("source")
        else:
          print "Failed to get original for photo id " + id


        # Free the DOM memory
        dom.unlink()

        # Grab the image file
        response = urllib2.urlopen(imgurl)
        data = response.read()
    
        # Save the file!
        fh = open(filename, "w")
        fh.write(data)
        fh.close()

        return filename
    except:
        print "Failed to retrieve photo id " + id
    
######## Main Application ##########
if __name__ == '__main__':

    # The first, and only argument needs to be a directory
    try:
        os.chdir(sys.argv[1])
    except:
        print "usage: %s directory" % sys.argv[0] 
        sys.exit(1)

    # First things first, see if we have a cached user and auth-token
    try:
        cache = open("touchr.frob.cache", "r")
        config = cPickle.load(cache)
        cache.close()

    # We don't - get a new one
    except:
        (user, token) = froblogin(getfrob(), "read")
        config = { "version":1 , "user":user, "token":token }  

        # Save it for future use
        cache = open("touchr.frob.cache", "w")
        cPickle.dump(config, cache)
        cache.close()

    # Now, construct a query for the list of photo sets
    url  = "http://api.flickr.com/services/rest/?method=flickr.photosets.getList"
    url += "&user_id=" + config["user"]
    url  = flickrsign(url, config["token"])

    # get the result
    response = urllib2.urlopen(url)
    
    # Parse the XML
    dom = xml.dom.minidom.parse(response)

    # Get the list of Sets
    sets =  dom.getElementsByTagName("photoset")

    # For each set - create a url
    urls = []
    for set in sets:
        pid = set.getAttribute("id")
        dir = getText(set.getElementsByTagName("title")[0].childNodes)
        dir = unicodedata.normalize('NFKD', dir.decode("utf-8", "ignore")).encode('ASCII', 'ignore') # Normalize to ASCII

        # Build the list of photos
        url   = "http://api.flickr.com/services/rest/?method=flickr.photosets.getPhotos"
        url  += "&photoset_id=" + pid

        # Append to our list of urls
        urls.append( (url , dir) )
    
    # Free the DOM memory
    dom.unlink()

    # Add the photos which are not in any set
    url   = "http://api.flickr.com/services/rest/?method=flickr.photos.getNotInSet"
    urls.append( (url, "No Set") )

    # Add the user's Favourites
    url   = "http://api.flickr.com/services/rest/?method=flickr.favorites.getList"
    urls.append( (url, "Favourites") )

    # Time to get the photos
    inodes = {}
    for (url , dir) in urls:
        # Create the directory
        try:
            os.makedirs(dir)
        except:
            pass

        # Get 500 results per page
        url += "&per_page=500"
        pages = page = 1

        while page <= pages: 
            request = url + "&page=" + str(page)

            # Sign the url
            request = flickrsign(request, config["token"])

            # Make the request
            response = urllib2.urlopen(request)

            # Parse the XML
            dom = xml.dom.minidom.parse(response)

            # Get the total
            pages = int(dom.getElementsByTagName("photo")[0].parentNode.getAttribute("pages"))

            # Grab the photos
            for photo in dom.getElementsByTagName("photo"):
                # Tell the user we're grabbing the file
                print photo.getAttribute("title").encode("utf8") + " ... in set ... " + dir

                # Grab the id
                photoid = photo.getAttribute("id")

                # The target
                target = dir + "/" + photoid + ".jpg"

                # Skip files that exist
                if os.access(target, os.R_OK):
                    inodes[photoid] = target
                    continue
                
                # Look it up in our dictionary of inodes first
                if photoid in inodes and inodes[photoid] and os.access(inodes[photoid], os.R_OK):
                    # woo, we have it already, use a hard-link
                    os.link(inodes[photoid], target)
                else:
                    inodes[photoid] = getphoto(photo.getAttribute("id"), config["token"], target)

            # Move on the next page
            page = page + 1

########NEW FILE########
