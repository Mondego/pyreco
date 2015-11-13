__FILENAME__ = hutils
#!/usr/bin/env python

import datetime
import re

# Compiled regexs
find_n_max_age = re.compile( r"max-age=(\d+)", re.IGNORECASE )
find_s_max_age = re.compile( r"s-maxage=(\d+)", re.IGNORECASE ) 

# Given the headers from a request object find the time when the 
# entity must be refreshed in the cache.
# Order of presidence: 
# 1. Cache-Control: s-maxage 
# 2. Cache-Control: max-age 
# 3. Now + ( Expires - Date ) 
# 4. Set a default cache delta

def get_expires( headers ):
    if "Cache-Control" in headers:
        s_maxage = find_s_max_age.match( headers["Cache-Control"] )
        max_age = find_n_max_age.match( headers["Cache-Control"] )
        if s_maxage:
            return datetime.datetime.now() + datetime.timedelta(int(s_maxage.group(1)))
        elif max_age:
            return datetime.datetime.now() + datetime.timedelta(seconds=int(max_age.group(1)))
    
    if "Expires" in headers:
        h_expires = datetime.datetime.strptime( headers["Expires"], "%a, %d %b %Y %H:%M:%S GMT"  )
        h_date    = datetime.datetime.strptime( headers["Date"], "%a, %d %b %Y %H:%M:%S GMT"  )
        delta     = datetime.timedelta = h_expires - h_date
        return datetime.datetime.now() + delta
    
    return datetime.datetime.now() + datetime.timedelta( days=7 )

def get_header( want, headers ):
    if want in headers:
        return headers[want]
    else:
        return None

########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.api.urlfetch import fetch
import datetime
import models
import hutils
import re

################################################################################
#                        SymPullCDN Configuration                              #
################################################################################
#                                                                              #
#  1. Origin                                                                   #
#     The origin server will be mirrored by this instance of SymPullCDN        #
#     configure a full http:// path with a FQDN, trailing slash included       #
origin = "http://replace*me/"                                                  #
#                                                                              #
#  2. Cachable Codes                                                           #
#     This is a list of HTTP Status Codes that will be cached when sent from   #
#     the origin.  By default only 200 OK codes will be cached.  Edit this     #
#     list only if you have a reason.                                          #
#                                                                              #
cache_codes = ( 200, )                                                         #
#                                                                              #
#                                                                              #
################################################################################





# Compiled Regular Expressions
no_cache_regex = re.compile( "(no-cache|no-store|private)", re.IGNORECASE )

class Entity(db.Model):
    uri          = db.StringProperty(required=True)
    LastModified = db.StringProperty()
    headers      = models.DictProperty()
    expires      = db.DateTimeProperty()
    status       = db.IntegerProperty()
    content      = db.BlobProperty(required=True)

class MainHandler(webapp.RequestHandler):
    def get(self):

       ############################################################################################
       #                                                                                          #
       #        Getting entity from cache, Passing to the user, possibly revalidating it          #  
       #                                                                                          #
       ############################################################################################
       
        entity = Entity.all().filter("uri =", self.request.path).get()
        if entity:
            # Revalidate if required.  Note, revalidation here updates the
            # request /after/ this one for the given entity.
            if entity.expires <= datetime.datetime.now():
                request_entity = fetch( origin + self.request.path, method="GET", 
                        headers={"If-Modified-Since" : entity.LastModified} )
                
                # If 304 JUST update the headers.
                if request_entity.status_code == 304:
                    headers      = dict(request_entity.headers)
                    entity.expires = hutils.get_expires( request_entity.headers )
                    entity.LastModified = hutils.get_header( "Last-Modified", request_entity.headers )
                    entity.save()
                # If 200, update the content too.
                elif request_entity.status_code == 200:
                    headers      = dict(request_entity.headers)
                    entity.expires = hutils.get_expires( request_entity.headers )
                    entity.LastModified = hutils.get_header( "Last-Modified", request_entity.headers )
                    entity.content = request_entity.content
                    entity.save()
                #Revalidation failed, send the entity stale and delete from the cache.
                else:
                    for key in iter(entity.headers):
                        self.response.headers[key] = entity.headers[key]
                    self.response.set_status(entity.status)
                    self.response.headers["X-SymPullCDN-Status"] = "Hit[EVALIDFAIL]"
                    self.response.out.write(entity.content)
                    entity.delete()
                    return True
            
            # See if we can send a 304
            if "If-Modified-Since" in self.request.headers:
                if self.request.headers["If-Modified-Since"] == entity.LastModified:
                    for key in iter(entity.headers):
                        self.response.headers[key] = entity.headers[key]
                    self.response.set_status(304)
                    self.response.headers["X-SymPullCDN-Status"] = "Hit[304]"
                    self.response.out.write(None)
                    return True

            for key in iter(entity.headers):
                self.response.headers[key] = entity.headers[key]
            self.response.set_status(entity.status)
            self.response.headers["X-SymPullCDN-Status"] = "Hit[200]"
            self.response.out.write(entity.content)
            return True
       
       ############################################################################################
       #                                                                                          #
       #             Fetching The Entity, Passing it to the user, possibly storing it             #  
       #                                                                                          #
       ############################################################################################
       
        request_entity = fetch( origin + self.request.path, method="GET", payload=None )
        
        # Respect no-cache and private
        if "Cache-Control" in request_entity.headers:
            m = no_cache_regex.match( request_entity.headers["Cache-Control"] )
            if m:
                self.response.headers["X-SymPullCDN-Status"] = "Miss[NoCtrl]"
                for key in iter(request_entity.headers):
                    self.response.headers[key] = request_entity.headers[key]
                self.response.out.write(request_entity.content)
                return True
        # Only Cache Specific Codes
        if request_entity.status_code not in cache_codes:
            self.response.headers["X-SymPullCDN-Status"] = "Miss[NoCode]"
            for key in iter(request_entity.headers):
                self.response.headers[key] = request_entity.headers[key]
            self.response.set_status(request_entity.status_code)
            self.response.out.write(request_entity.content)
            return True
        
        # Set up data to store.
        entity = Entity(
            uri          = self.request.path,
            headers      = dict(request_entity.headers),
            expires      = hutils.get_expires( request_entity.headers ),
            LastModified = hutils.get_header( "Last-Modified", request_entity.headers ),
            status       = request_entity.status_code,
            content      = request_entity.content).save()

        for key in iter(request_entity.headers):
            self.response.headers[key] = request_entity.headers[key]
        self.response.headers["X-SymPullCDN-Status"] = "Miss[Cached]"
        self.response.out.write(request_entity.content)


def main():
    application = webapp.WSGIApplication([('/.*', MainHandler)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = models
#!/usr/bin/env python
from google.appengine.ext import db
import pickle

# Class taken from http://stackoverflow.com/questions/1953784
class DictProperty(db.Property):
  data_type = dict

  def get_value_for_datastore(self, model_instance):
    value = super(DictProperty, self).get_value_for_datastore(model_instance)
    return db.Blob(pickle.dumps(value))

  def make_value_from_datastore(self, value):
    if value is None:
      return dict()
    return pickle.loads(value)

  def default_value(self):
    if self.default is None:
      return dict()
    else:
      return super(DictProperty, self).default_value().copy()

  def validate(self, value):
    if not isinstance(value, dict):
      raise db.BadValueError('Property %s needs to be convertible '
                             'to a dict instance (%s) of class dict' % (self.name, value))
    return super(DictProperty, self).validate(value)

  def empty(self, value):
    return value is None

########NEW FILE########
