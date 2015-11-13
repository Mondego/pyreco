__FILENAME__ = acceptInvite
#!/usr/bin/env python
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util, template
class MainHandler(webapp.RequestHandler):

  def get(self):
    import os
    path = os.path.join(os.path.dirname(__file__),'acceptInvite.html')
    self.response.out.write(template.render(path,{"INVITECODE":self.request.get("code")}))
  def post(self):
    from user_sn import User, send_welcome_msg
    from team import Invite
    username = self.request.get("username")
    if User.all().filter("name =",username).get() is not None:
        raise Exception("I already have that user...")
    invite = Invite.get(self.request.get("code"))
    if invite is None:
        raise Exception("Bad invite code!")
    u = User(name=username,team=invite.team,email=invite.email)
    u.put()
    send_welcome_msg(u)
    invite.delete()
    
        
    
def main():
  application = webapp.WSGIApplication([('/accept_invite', MainHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = cache
#!/usr/bin/env python

from google.appengine.ext import db
from google.appengine.ext import search
TYPE_LOCAL_FD = 0
TYPE_EXTERN_FD = 1
TYPE_COMPUTER = 2
TYPE_EXTERNAL_RING = 3 #not actually a cache type, but we use it as a destination flag
# to indicate it should be moved to any extern drive anywhere on the darknet if posssible
from user_sn import User
from Content import Content
from team import Team
class CacheLocation(db.Model):
    description = db.TextProperty()
    team_responsible = db.ReferenceProperty(reference_class=Team)
    image = db.BlobProperty()
    #remember, this is stored in two places: here and in the Cache itself
    type = db.IntegerProperty()
   

    
class Cache(db.Model):
    friendlyName = db.StringProperty()
    type = db.IntegerProperty(required = True)
    last_seen = db.DateTimeProperty(auto_now = True)
    last_touched = db.ReferenceProperty(reference_class=User)
    space_left = db.IntegerProperty(required=True)
    #person_responsible = db.ReferenceProperty(reference_class=User,collection_name="special")
    permanent_location = db.ReferenceProperty(reference_class=CacheLocation)
    #short-term checkout only
    checked_out = db.BooleanProperty(default=False)
    
    #Administratively set for long-term problems (like maybe a cache grew legs and walked away...)
    route_around_me = db.BooleanProperty(default=False)
    
    
class ContentCopy(db.Model):
    content = db.ReferenceProperty(reference_class=Content)
    where = db.ReferenceProperty(reference_class=Cache)

def can_operate_on(cache,user):
    #is it your cache?
    if cache.type==TYPE_COMPUTER and cache.last_touched.key()==user.key():
        return True
    #is it your team's local or ext  cache?
    elif  cache.type == TYPE_LOCAL_FD or cache.type==TYPE_EXTERN_FD and cache.permanent_location.team_responsible.key() == user.team.key() :
        return True
    elif cache.type ==TYPE_EXTERN_FD and user.team_leader_flag:
        return True
    return False
def get_cache_by_name(cache):
    return Cache.all().filter("friendlyName =",cache).get()

def get_copy(cacheid,fileid):
    from Content import content_by_id
    c = get_cache_by_name(cacheid)
    content = content_by_id(fileid)
    return ContentCopy.all().filter("content =",content).filter("where =",c).get()
def is_cache_available_soon(cache):
    import datetime
    diff = datetime.timedelta(days=15)
    if cache.last_seen + diff < datetime.datetime.today():
        return False
    if cache.route_around_me:
        return False
    return True
def is_cache_available_now(cache):
    if is_cache_available_soon(cache):
        if not cache.checked_out:
            return True
    return False
    
    
########NEW FILE########
__FILENAME__ = cachetalk
#!/usr/bin/env python

#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
import logging

class SyncHandler(webapp.RequestHandler):

  def get(self):
    from cache import can_operate_on, ContentCopy, get_cache_by_name, Cache, TYPE_COMPUTER
    from user_sn import confirm
    u = confirm(self)
    cname = self.request.get("cache")
    logging.info("Syncing a cache named %s" % cname)
    c = get_cache_by_name(cname)
    if c==None:
        logging.info("No cached named %s, making a new one" % cname)
        c = Cache(friendlyName = cname,type=TYPE_COMPUTER,last_touched=u,space_left=-1,person_responsible=u)
        c.put()
    if not can_operate_on(c,u):
        raise Exception("You're not permitted to sync this cache.")
    #fetch everything that's "supposed" to be on the key
    copies = ContentCopy.all().filter("where =",c).fetch(limit=1000)
    self.response.out.write("OK\n")
    for copy in copies:
        self.response.out.write(copy.content.file_id + "\n")
  def post(self):
    from user_sn import confirm
    from cache import can_operate_on, get_copy, ContentCopy, get_cache_by_name, TYPE_COMPUTER, TYPE_EXTERN_FD, TYPE_LOCAL_FD, TYPE_EXTERNAL_RING
    from Content import content_by_id
    u = confirm(self)
    cname = self.request.get("cache")
    c = get_cache_by_name(cname)
    if not can_operate_on(c,u):
        raise Exception("You're not permitted to sync this cache.")
    deletes = self.request.get("deletes")
    for item in deletes.split("\n"):
        if item=="": continue
        logging.info("deleting %s" % item)
        get_copy(cname,item).delete()
    adds = self.request.get("adds")
    for item in adds.split("\n"):
        if item=="": continue
        logging.info("adding %s" % item)
        #see if there's an RC associated with this
        from request import RequestCopy
        content = content_by_id(item)
        rcs = RequestCopy.all().filter("file =",content)
        if c.type==TYPE_COMPUTER:
            rcs = rcs.filter("dest =",u).fetch(limit=1000)
        elif c.type==TYPE_LOCAL_FD:
            rcs = rcs.filter("dest =",c.permanent_location.team_responsible).filter("dest_int =",TYPE_LOCAL_FD).fetch(limit=1000)
        elif c.type==TYPE_EXTERN_FD:
            #the common case (closing the RC associated with a swap) is handled in runComplete.
            rcs = RequestCopy.all().filter("file =",content).filter("dest_int =",TYPE_EXTERNAL_RING).fetch(limit=1000)
        for rc in rcs:
            logging.info("Closing %s" % rc.key())
            rc.delete()
        co = ContentCopy(where = c,content=content)
        if co.content is None:
            logging.warning("Not adding %s" % item)
        else:
            co.put()
    c.space_left = int(self.request.get("size"))
    c.last_touched = u
    c.put()
    
    
class ImgHandler(webapp.RequestHandler):
    def get(self):
        from cache import CacheLocation
        c = CacheLocation.get(self.request.get("cache"))
        self.response.headers["Content-Type"] = "image/jpeg"
        self.response.out.write(c.image)
        #self.response.headers["Content-Disposition"] = 'attachment; filename="openthis.sneak"'

def main():
  application = webapp.WSGIApplication([('/cache/sync', SyncHandler),
                                        ('/cache/img',ImgHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = Content
#!/usr/bin/env python

from google.appengine.ext import db
from user_sn import User
from google.appengine.ext.search import SearchableModel
TYPE_MOVIE = 0
TYPE_BOOK = 1
class Content(SearchableModel):
    Name = db.StringProperty(required = True)
    Type = db.IntegerProperty(required = True)
    Link = db.URLProperty()
    SharedBy = db.ReferenceProperty(reference_class = User, required = True)
    file_id = db.StringProperty()
    file_secret = db.StringProperty()
    file_size = db.IntegerProperty() #search.py checks this for None to determine if it should be shown or not
    shared_date = db.DateTimeProperty(auto_now_add=True)
    
def set_file_id(c):
    from random import choice
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    c.file_id = ""
    for i in range(0,8):
        c.file_id += choice(chars)
    c.put()
def content_by_id(id):
    return Content.all().filter("file_id =",id).get()
########NEW FILE########
__FILENAME__ = magic
#!/usr/bin/env python

BASE_URL="http://localhost:8083/"

from google.appengine.ext import db
class Magic (db.Model):
    freeleech = db.BooleanProperty(default=True)
    
def get_magic():
    magic = Magic.all().get()
    #put any hacks here
    #fix for corrupt description
    """from cache import CacheLocation
    c = CacheLocation.get("agpzbmVhazNybmV0chQLEg1DYWNoZUxvY2F0aW9uGPAHDA")
    c.description = ""
    c.put()"""
    #end hacks
    if magic is None:
        magic = Magic()
        magic.put()
    return magic
########NEW FILE########
__FILENAME__ = mail
#!/usr/bin/env python

from google.appengine.api import mail
import logging
FROM_MAIL_ADDRESS="whatever@whatever.com"
ALERT_ADMIN_ADDRESS="whatever@whatever.com"


def send_mail(to,subject,msg,sneakfile=None):
    import logging
    logging.info(msg)
    logging.info(sneakfile)
    if sneakfile!=None:
        mail.send_mail(sender=FROM_MAIL_ADDRESS,to=to,subject=subject,body=msg,attachments=[("openthis.sneak",sneakfile)])
    else:
        mail.send_mail(sender=FROM_MAIL_ADDRESS,to=to,subject=subject,body=msg)
def alert_admins(msg):
    from random import choice
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    errorcode = ""
    for i in range(0,32):
        errorcode += choice(chars)
    msg += "\nError code: " + errorcode
    logging.error("Error code: " + errorcode)
    send_mail(to=ALERT_ADMIN_ADDRESS,subject="SNEAKERNET CRITICAL ERROR",msg=msg)
########NEW FILE########
__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util


class MainHandler(webapp.RequestHandler):

  def get(self):
    self.response.out.write('Hello world!')


def main():
  application = webapp.WSGIApplication([('/', MainHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = makenewteam
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util, template


class MovieHandler(webapp.RequestHandler):

  def get(self):
    import os
    path = os.path.join(os.path.dirname(__file__),'makenewteam.html')
    self.response.out.write(template.render(path,{}))
    
  def post(self):
    from user_sn import User, send_welcome_msg
    from team import Team
    import logging
    t = Team(name=self.request.get("teamname"))
    t.put()
    u = User(email=self.request.get("tlemail"),name=self.request.get("teamleader"),team=t,team_leader_flag=True)
    u.put()
    send_welcome_msg(u)
    

def main():
  application = webapp.WSGIApplication([('/makenewteam', MovieHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
#!/usr/bin/env python


########NEW FILE########
__FILENAME__ = purge
#!/usr/bin/env python
LEAVE_COPIES_ON_DARKNET = 3
LEAVE_COPIES_ON_TEAM = 1


PURGE_AT_WILL = 0
MOVE_TO_SOFTCACHE = 1
LEAVE_IN_PLACE=99
import logging

def team_of(contentcopy):
    from cache import TYPE_EXTERN_FD, TYPE_LOCAL_FD
    if contentcopy.where.type==TYPE_LOCAL_FD or contentcopy.where.type == TYPE_EXTERN_FD:
        return contentcopy.where.permanent_location.team_responsible
    else:
        return contentcopy.where.last_touched.team
def available_soon_cc(contentcopy):
    from cache import is_cache_available_soon
    return is_cache_available_soon(contentcopy.where)
def can_purge(user,contentcopy):
    from cache import ContentCopy, TYPE_COMPUTER
    allCopies = ContentCopy.all().filter("content =",contentcopy.content).fetch(limit = 1000) #now fetch all the copies
    allCopies = filter(available_soon_cc,allCopies) #only the ones that are online
    if len(allCopies) > LEAVE_COPIES_ON_DARKNET+1:
        copies_on_team = 0
        chk_team = team_of(contentcopy)
        for copy in allCopies:
            if copy.key()==contentcopy.key(): continue #not interested in the copy we want to purge
            if chk_team.key()==team_of(copy).key(): copies_on_team += 1
            if copies_on_team >= LEAVE_COPIES_ON_TEAM:
                if not user.team_leader_flag: #wait for the team leader to purge the crap.
                    team_leader_copies = filter(lambda x: x.where.type==TYPE_COMPUTER, copies_on_team)
                    from user_sn import all_team_leaders_for
                    leaders = all_team_leaders_for(user.team)
                    leaders = map(lambda x: x.key(),leaders)
                    team_leader_copies = filter(lambda x: x.where.last_touched.key() in leaders)
                    if len(team_leader_copies) != 0:
                        logging.info("Team leader has a copy.  Not purging.")
                        return MOVE_TO_SOFTCACHE
            else:            
                return PURGE_AT_WILL
    #this is conservative logic.  If there's an outstanding request on the sneakernet, leave the file in place
    from request import Request
    reqs = Request.all().filter("file =",contentcopy.content).get()
    if reqs==None:
        return MOVE_TO_SOFTCACHE
    return LEAVE_IN_PLACE


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util


class MainHandler(webapp.RequestHandler):

  def get(self):
    from user_sn import confirm
    u = confirm(self)
    from cache import get_cache_by_name, can_operate_on, ContentCopy
    from Content import content_by_id
    
    c = get_cache_by_name(self.request.get("cache"))
    if not can_operate_on(c,u):
        raise Exception("You can't sync this cache.")
    content = content_by_id(self.request.get("content"))
    logging.info(c.key())
    logging.info(content.key())
    copy = ContentCopy.all().filter("where =",c).filter("content =",content).get()
    logging.info(copy)
    if copy is None:
        self.repsonse.out.write("NO_SUCH_THING")
        return
    result = can_purge(u,copy)
    if result==PURGE_AT_WILL:
        self.response.out.write("PURGE_AT_WILL")
        logging.info("PURGE_AT_WILL")
    elif result==MOVE_TO_SOFTCACHE:
        self.response.out.write("MOVE_TO_SOFTCACHE")
        logging.info("MOVE_TO_SOFTCACHE")
    else:
        self.response.out.write("LEAVE_IN_PLACE")
        logging.info("LEAVE_IN_PLACE")
    


def main():
  application = webapp.WSGIApplication([('/purge', MainHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = request
#!/usr/bin/env python
from google.appengine.ext import db
from user_sn import User
from Content import Content
import logging

class Request(db.Model):
    user = db.ReferenceProperty(reference_class=User)
    file = db.ReferenceProperty(reference_class=Content)
    made = db.DateTimeProperty(auto_now_add=True)
    last_routed = db.DateTimeProperty(auto_now=True)
class RequestCopy(db.Model):
    file = db.ReferenceProperty(reference_class=Content)
    req = db.ReferenceProperty(reference_class=Request)
    #this can hold a variety of values.
    # Can be a USER (for get_from_local_cache, get_from_ext_cache)
    # Can be a Team + dest_int=TYPE_LOCAL_FD for (get_from_someone_on_team_not_tl, get_from_tl)
    # Can be a Team + dest_int=TYPE_EXTERN_FD for get_from_any_ext_cache
    # Can be None + dest_int = TYPE_EXTERNAL_RING for get_from_really_far_away
    dest = db.ReferenceProperty(collection_name="special")
    dest_int = db.IntegerProperty()
    #The user that we e-mailed to make the run
    emailed_user=db.ReferenceProperty(reference_class=User)

def copies_that_can_fulfill(request):
    from cache import ContentCopy
    return ContentCopy.all().filter("content =",request.file).fetch(limit=1000)

    
def cost_of_content(content):
    from math import ceil
    return int(ceil(0.5*content.file_size / 1024/1024))
def reward_for_content(content):
    from math import ceil
    return int(ceil(content.file_size / 1024/1024))
    
def send_run_msg(user):
    from mail import send_mail
    from magic import BASE_URL
    body = """Hey there,
    
    The sneakernet needs you!  Your elite sneakery skills are required to transport top-secret government data from A to B.  You can accept this mission by clicking this link:
    
    %s
    
    This message will self-destruct.
    
    Thanks,
    
    The sneakernet""" % (BASE_URL + "run")
    send_mail(to=user.email,subject="TOP SECRET MISSION",msg=body)
    

def get_from_local_cache(request,allcopies):
    logging.info("Searching team cache...")
    from cache import TYPE_LOCAL_FD, is_cache_available_soon
    for copy in allcopies:
        if copy.where.type == TYPE_LOCAL_FD and  copy.where.permanent_location.team_responsible.key() == request.user.team.key() and is_cache_available_soon(copy.where):
            logging.info("Found copy in the local team cache!")
            if RequestCopy.all().filter("file =",request.file).filter("dest =",request.user).get()==None:
                logging.info("No RequestCopy currently exists; creating...")
                rc = RequestCopy(file = request.file,req=request,dest=request.user,emailed_user=request.user)
                rc.put()
                send_run_msg(rc.emailed_user)
            else:
                logging.info("RequestCopy already exists")
            return True
    return False
def get_from_ext_cache(request,allcopies):
    logging.info("Searching (our) external cache...")
    from cache import TYPE_EXTERN_FD, is_cache_available_soon
    for copy in allcopies:
        if copy.where.type==TYPE_EXTERN_FD and copy.where.permanent_location.team_responsible.key() == request.user.team.key() and is_cache_available_soon(copy.where):
            logging.info("Found copy in the external cache!")
            if RequestCopy.all().filter("file =",request.file).filter("dest =",request.user).get()==None:
                logging.info("No RequestCopy currently exists; creating...")
                rc = RequestCopy(file = request.file,req=request,dest=request.user,emailed_user=request.user)
                rc.put()
                send_run_msg(rc.emailed_user)
            else:
                logging.info("RequestCopy already exists")
            return True
    return False
def get_from_tl(request,allcopies):
    logging.info("Searching team leader...")
    from user_sn import all_team_leaders_for
    leaders = all_team_leaders_for(request.user.team)
    leader_copies = []
    from cache import TYPE_COMPUTER, is_cache_available_soon, TYPE_LOCAL_FD
    for copy in allcopies:
        if copy.where.last_touched.team.key() == request.user.team.key() and copy.where.type==TYPE_COMPUTER and is_cache_available_soon(copy.where) and copy.where.last_touched.team_leader_flag:
            logging.info("Found copy from team leader!")
            dest = request.user.team
            if RequestCopy.all().filter("file =",request.file).filter("dest =",dest).filter("dest_int =",TYPE_LOCAL_FD).get()==None:
                logging.info("No RequestCopy currently exists; creating...")
                rc = RequestCopy(file = request.file,req=request,dest=dest,dest_int = TYPE_LOCAL_FD,emailed_user=copy.where.last_touched)
                rc.put()
                send_run_msg(rc.emailed_user)
            else:
                logging.info("RequestCopy already exists.")
            return True
    return False

def get_from_any_ext_cache(request,allcopies):
    logging.info("Searching all external caches...")
    from cache import TYPE_EXTERN_FD, is_cache_available_soon
    for copy in allcopies:
        if copy.where.type==TYPE_EXTERN_FD and is_cache_available_soon(copy.where):
            logging.info("Found a copy on team %s's external cache %s" % (copy.where.permanent_location.team_responsible.name, copy.where.friendlyName))
            dest = request.user.team
            if RequestCopy.all().filter("file =",request.file).filter("dest =",dest).filter("dest_int =",TYPE_EXTERN_FD).get()==None:
                logging.info("No RequestCopy currently exists; creating...")
                #we need to get ahold of a team leader
                from user_sn import all_team_leaders_for
                leaders = all_team_leaders_for(request.user.team)
                from random import choice
                flag_leader = choice(leaders)
                rc = RequestCopy(file = request.file,req=request,dest=dest,dest_int = TYPE_EXTERN_FD,emailed_user=flag_leader)
                rc.put()
                send_run_msg(flag_leader)
            else:
                logging.info("RequestCopy already exists.")
            return True
    return False
            
def get_from_someone_on_team_not_tl(request,allcopies):
    from cache import TYPE_COMPUTER, CacheLocation, TYPE_LOCAL_FD, is_cache_available_soon
    for copy in allcopies:
        if copy.where.last_touched.team.key() ==request.user.team.key() and copy.where.type==TYPE_COMPUTER and is_cache_available_soon(copy.where):
            if copy.where.last_touched.team_leader_flag:
                logging.info("Team leader has a copy; ignoring this copy for now")
                continue
            logging.info("Found copy from another teammember!")
            dest = request.user.team
            if RequestCopy.all().filter("file =",request.file).filter("dest =",dest).filter("dest_int =",TYPE_LOCAL_FD).get()==None:
                logging.info("No RequestCopy currently exists; creating...")
                rc = RequestCopy(file = request.file,req=request,dest=dest,dest_int=TYPE_LOCAL_FD,emailed_user=copy.where.last_touched)
                rc.put()
                send_run_msg(rc.emailed_user)
            else:
                logging.info("RequestCopy already exists")
            return True
    return False

def get_from_really_far_away(request,allcopies):
    from cache import TYPE_COMPUTER, TYPE_EXTERNAL_RING, is_cache_available_soon
    for copy in allcopies:
        if copy.where.type==TYPE_COMPUTER and is_cache_available_soon(copy.where):
            logging.info("Found a copy really far away")
            if RequestCopy.all().filter("file =",request.file).filter("dest_int =",TYPE_EXTERNAL_RING).get()==None:
                logging.info("No RequestCopy currently exists; creating...")
                rc = RequestCopy(file = request.file,req=request,emailed_user=copy.where.last_touched,dest_int = TYPE_EXTERNAL_RING)
                rc.put()
                send_run_msg(rc.emailed_user)
            else:
                logging.info("RequestCopy already exists")
            return True
        
            
            
    
def get_from_local_storage(request,allcopies):
    from cache import TYPE_COMPUTER
    from sneakfiles import host_sneakfile
    #Maybe it's in the user's local storage?
    logging.info("Checking loopback...")
    from magic import BASE_URL
    for copy in allcopies:
        #logging.info(copy.where.person_responsible)
        if copy.where.last_touched.key()==request.user.key() and copy.where.type==TYPE_COMPUTER:
            logging.info("Found local copy!")
            from user_sn import user_in_good_standing
            if not user_in_good_standing(request.user):
                logging.info("User not in good standing, so won't decrypt the file.")
                return True #mumble mumble
            from mail import send_mail
            sneakfile = "DECRYPT\n%s\n%s\n%s\n" % (copy.where.friendlyName,copy.content.file_id,copy.content.file_secret)
            body = """Ta-da!  We've got that %s you requested.  That wasn't so bad, was it?
            Just open the .sneak file hosted at %s and watch your file decrypt like magic!
            
            Glad we could help,
            
            The sneakernet""" % (copy.content.Name, BASE_URL + host_sneakfile(sneakfile))
            send_mail(request.user.email,"I've got something for you!",body)
            #give the sharer some points
            request.file.SharedBy.points += reward_for_content(request.file)
            request.file.SharedBy.put()
            request.delete()
            
            
            return True
    return False

def give_up(request):
    from mail import send_mail, alert_admins
    cost = cost_of_content(request.file)
    request.user.points += cost
    request.user.put()
    body = """Dear John,
    I tried.  I really did.  But for some strange reason I can't seem to get you the copy of %s you requested.
    I know it sucks.  I hate being a tease.  I did my best to get it to you, honest.  It just wasn't meant to be.
    Rest assured I've got a team of database wizards descending from the clouds to diagnose what went wrong.  But in our hearts, both of us always knew something wasn't quite right.  Those long runs, always expecting each other, but being rewarded... Long-distance relationships never seem to work out.
    
    You're welcome to try requesting it again.  Maybe this is just a temporary error?  I've given up hope, though.  It's time for me to move on.
    
    I'm returning the points I borrowed from you.  I can't bear to look at them anymore.
    
    Years from now, you will look back on this moment, and know it was for the best.  I hope we can still be friends.
    
    Yours truly,
    
    The sneakernet""" % request.file.Name
    send_mail(to=request.user.email,subject="Sorry",msg=body)
    alert_admins("Can't deliver %s to %s" % (request.file.Name,request.user.name))

    
def try_to_route(request):

    if request==None:
        logging.info("Nothing to do")
        return
    
    logging.info("Routing request %s which delivers %s to %s" % (request.key(),request.file.Name,request.user.name))
    request.put() #updates last_routed
    copies = copies_that_can_fulfill(request)
    logging.info("There are %d copies of this file on the sneakernet" % len(copies))
    if get_from_local_storage(request,copies):
        pass
    elif get_from_local_cache(request,copies):
        pass
    elif get_from_someone_on_team_not_tl(request,copies):
        pass
    elif get_from_ext_cache(request,copies):
        pass
    elif get_from_tl(request,copies):
        pass
    elif get_from_any_ext_cache(request,copies):
        pass
    elif get_from_really_far_away(request,copies):
        pass
    else:
        give_up(request)
        request.delete()
    
########NEW FILE########
__FILENAME__ = requests
#!/usr/bin/env python

#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from user_sn import confirm
from request import Request, cost_of_content, try_to_route
from Content import Content
import logging



class MainHandler(webapp.RequestHandler):

  def post(self):
    user = confirm(self)
    content = Content.get(self.request.get("content"))
    #calculate points
    from math import ceil
    cost = cost_of_content(content)
    logging.info("cost %d" % cost)
    from magic import get_magic
    magic_mod = get_magic()
    if user.points >= cost or magic_mod.freeleech:
        r = Request(user=user,file=content)
        r.put()
        if not magic_mod.freeleech:
            user.points -= int(cost)
            user.put()
        self.response.out.write("OK")
    else:
        self.response.out.write("NEEDMOREPOINTS %d" % (cost - user.points))

class RouteHandler(webapp.RequestHandler):
    def get(self):
        req = Request.all().order("last_routed").get()
        try_to_route(req)
        


def main():
  application = webapp.WSGIApplication([('/requests', MainHandler),
                                        ('/requests/route',RouteHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = resetPW
#!/usr/bin/env python
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util, template
import hashlib
from user_sn import SALT
import logging

class MovieHandler(webapp.RequestHandler):

  def get(self):
    import os
    path = os.path.join(os.path.dirname(__file__),'resetPW.html')
    self.response.out.write(template.render(path,{"USERNAME":self.request.get("user"),"RESETCODE":self.request.get("resetcode")}))
  def post(self):
    from user_sn import get_user_by_name
    u = get_user_by_name(self.request.get("user"))
    if str(u.reset_code)==self.request.get("resetcode"):
        u.passwordhash = hashlib.md5(self.request.get("password")+SALT).hexdigest()
        #logging.info(self.request.get("password"))
        u.put()
        from mail import send_mail
        send_mail(to=u.email,subject="Sneakernet password reset.",msg="Your sneakernet password has been reset.  Hopefully you were the one who did this...")
    else: raise Exception("Incorrect reset code")
    


def main():
  application = webapp.WSGIApplication([('/resetPW', MovieHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python



from google.appengine.ext import webapp
from google.appengine.ext.webapp import util, template
import logging

def my_caches(u):
    from cache import Cache, TYPE_COMPUTER, is_cache_available_now
    return filter(is_cache_available_now,Cache.all().filter("last_touched =",u).filter("type =",TYPE_COMPUTER).fetch(limit=1000))
    
#returns team caches that are available NOW
def team_caches(u):
    from cache import CacheLocation, TYPE_LOCAL_FD, TYPE_EXTERN_FD, is_cache_available_now, Cache
    locs = CacheLocation.all().filter("team_responsible =",u.team).filter("type =",TYPE_LOCAL_FD).fetch(limit=1000)
    locs += CacheLocation.all().filter("team_responsible =",u.team).filter("type =",TYPE_EXTERN_FD).fetch(limit=1000)
    caches = []
    for loc in locs:
        caches += filter(is_cache_available_now,Cache.all().filter("permanent_location =",loc).fetch(limit=1000))
    return caches
    
def find_a_cache_to_get(u):
    #we should prioritize in terms of what gets things off the network the fastest
    from cache import TYPE_EXTERN_FD, TYPE_LOCAL_FD, TYPE_EXTERNAL_RING, is_cache_available_now, ContentCopy, Cache
    from request import RequestCopy
    teamcaches = team_caches(u)
    externs = filter(lambda x: x.type==TYPE_EXTERN_FD,teamcaches)
    if u.team_leader_flag:
        #try to do a team leader run
        rcs = RequestCopy.all().filter("dest =",u.team).filter("dest_int =",TYPE_EXTERN_FD).fetch(limit=1000)
        for rc in rcs:
            #figure out where to get that file
            #get all the external ring drives
            ringdrives = Cache.all().filter("type =",TYPE_EXTERN_FD)
            ringdrives = filter(is_cache_available_now,ringdrives)
            for drive in ringdrives:
                if drive.permanent_location.team_responsible.key()==u.team.key():
                    logging.error("Our own ext cache %s has a copy of %s.  I'm going to ignore this, but probably something bad is happening." % (drive.key(),rc.file.key()))
                    continue
                copy = ContentCopy.all().filter("content =",rc.file).filter("where =",drive).get()
                if copy is not None:
                    logging.info("We need to get ahold of drive %s" % drive.friendlyName)
                    
                    for swapdrive in externs:
                        if not is_cache_available_now(swapdrive): continue
                        logging.info("We will trade %s for it" % swapdrive.friendlyName)
                        return (drive,swapdrive)
                    logging.info("We don't have a drive we can swap for it :-()")
    
    
    #get off extern

    rcs = RequestCopy.all().filter("dest =",u).fetch(limit=1000) #find all requests headed for me


    

    for cache in externs:
        for rc in rcs:
            cc = ContentCopy.all().filter("where =",cache).filter("content =",rc.file).get()
            if cc is not None:
                logging.info("User needs a file from extern cache; instructing user to acquire it")
                return (cache,None)
    #put on extern
    mycaches = my_caches(u)
    for cache in mycaches:
        ccs = ContentCopy.all().filter("where =",cache)
        for cc in ccs:
            rc = RequestCopy.all().filter("file =",cc.content).filter("dest_int =",TYPE_EXTERNAL_RING).get()
            if rc is not None:
                logging.info(rc)
                logging.info("User needs to dump a file to external ring; filesize is %s" % (rc.file.file_size))
                for cache in externs:
                    if cache.space_left > rc.file.file_size:
                        return (cache,None)
                    logging.info("Can't find a cache that will hold that file :-(")
                    
    
    locs = filter(lambda x: x.type==TYPE_LOCAL_FD,teamcaches)
    for cache in locs:
        for rc in rcs:
            cc = ContentCopy.all().filter("where =",cache).filter("content =",rc.file).get()
            if cc is not None:
                logging.info("User needs a file from local team cache; instructing user to acquire it.")
                return (cache,None)

    #find any request we can actually fulfill
 
    for cache in mycaches:
        ccs = ContentCopy.all().filter("where =",cache)
        for cc in ccs:
            #any RC with a file we can access that is also bound for our team
            rc = RequestCopy.all().filter("file =",cc.content).filter("dest =",u.team).get()
            if rc is not None:
                #find a cache big enough to hold it
                logging.info(rc)
                logging.info("User needs to dump a file to a team cache; file is size %s" % (rc.file.file_size))
                for cache in locs:
                    if cache.space_left > rc.file.file_size:
                        return (cache,None)
                logging.info("Can't find a cache that will hold that file.  :-(")
    return (None,None)
                    
                
                
    
    
class MainHandler(webapp.RequestHandler):

  def get(self):
    import os
    path = os.path.join(os.path.dirname(__file__),'run.html')
    self.response.out.write(template.render(path,{}))
  def post(self):
    if self.request.get("accept1")!="on" or self.request.get("accept2")!="on":

        logging.info("Not accepted")
        self.get()
        return
    #find something to do
    from user_sn import confirm
    u = confirm(self)
    if u.has_drive is not None:
        logging.info("User has drive %s, run denied." % u.has_drive.key())
        self.response.out.write("You already have a drive checked out!  You must return it.  Contact the admin or your team leader.")
        return
    (cache,swap) = find_a_cache_to_get(u)
    import os
    if cache==None:
        self.response.out.write("Can't find anything to do.  Sorry...")
    elif swap==None:
        #mark the cache checked out
        cache.checked_out = True
        cache.last_touched = u
        cache.put()
        u.has_drive = cache
        u.put()
        data = {"CACHENAME":cache.friendlyName,
                "IMGURL":"/cache/img?cache="+str(cache.permanent_location.key()),
                "DESCRIPTION":cache.permanent_location.description,
                "USERNAME":self.request.get("username"),
                "PASSWORD":self.request.get("password")}
        path = os.path.join(os.path.dirname(__file__),'run_progress.html')
        self.response.out.write(template.render(path,data))
    else:
        #swap drive
        logging.info("User %s swapping drive %s and %s" % (u.name,cache.friendlyName,swap.friendlyName))
        cache.checked_out = True
        cache.last_touched = u
        cache.put()
        swap.checked_out = True
        swap.last_touched = u
        swap.put()
        u.has_drive = cache
        u.put()
        data = {"CACHENAME":cache.friendlyName,
                "SWAPNAME":swap.friendlyName,
                "DESCRIPTION":cache.permanent_location.description,
                "SWAPDESCRIPTION":swap.permanent_location.description,
                "SWAPURL":"/cache/img?cache="+str(swap.permanent_location.key()),
                "IMGURL":"/cache/img?cache="+str(cache.permanent_location.key()),
                "USERNAME":self.request.get("username"),
                "PASSWORD":self.request.get("password")}
        path = os.path.join(os.path.dirname(__file__),'run_swap.html')
        self.response.out.write(template.render(path,data))
        
        

class RunCompleteHandler(webapp.RequestHandler):
    def post(self):
        from user_sn import confirm
        from cache import Cache
        u = confirm(self)
        cache = u.has_drive
        u.has_drive.checked_out = False
        u.has_drive.put()
        u.has_drive = None
        u.put()
        logging.info("User %s returning cache %s" % (u.name,cache.friendlyName))
        self.response.out.write("Thanks!  Mission complete!")
class SwapCompleteHandler(webapp.RequestHandler):
    def post(self):
        from user_sn import confirm
        from cache import Cache, get_cache_by_name
        u = confirm(self)
        cache = get_cache_by_name(self.request.get("cachename"))
        swap = get_cache_by_name(self.request.get("swapname"))
        cache.checked_out = False
        temp = cache.permanent_location
        cache.permanent_location = swap.permanent_location
        cache.put()
        swap.permanent_location = temp
        swap.checked_out = False
        swap.put()
        u.has_drive = None
        u.put()
        logging.info("User %s completed swapping %s and %s" % (u.name,cache.friendlyName,swap.friendlyName))
        from request import RequestCopy
        self.fulfill(cache)
        self.fulfill(swap)
        
        self.response.out.write("Thanks!  Mission complete!")
    def fulfill(self,cache):
        from request import RequestCopy
        from cache import TYPE_EXTERN_FD, ContentCopy, get_copy
        fulfill_swap_requests = RequestCopy.all().filter("dest =",cache.permanent_location.team_responsible).filter("dest_int =",TYPE_EXTERN_FD).fetch(limit=1000)
        for request in fulfill_swap_requests:
            logging.info("thinking about request %s" % request.key())
            stuff_on_disk = ContentCopy.all().filter("content =",request.file).filter("where =",cache).get()
            if stuff_on_disk is not None:
                logging.info("Closing requestcopy %s" % request.key())
                request.delete()
            else:
                logging.info("stuff on disk is none")
            
    
                
class MoveToHandler(webapp.RequestHandler):
    def post(self):
        diskstr = self.request.get("disks")
        disks = []
        from request import RequestCopy
        for disk in diskstr.split("\n"):
            if disk=="": continue #ignore trailing \n
            disks.append(disk.strip())
        from user_sn import confirm
        from cache import Cache, TYPE_COMPUTER, TYPE_EXTERNAL_RING, TYPE_LOCAL_FD, TYPE_EXTERN_FD
        u = confirm(self)
        result = []
        for disk in disks:
            logging.info("Considering disk %s" % disk)
            real_disk = Cache.all().filter("friendlyName =",disk).get()
            if real_disk.type==TYPE_COMPUTER:
                wants_files = RequestCopy.all().filter("dest =",u).fetch(limit=1000)
                """The line below handles a really weird edge case:
                1.  Bob requests a file.  The file moves along however and ends up (for the moment) on the team_extern cache
                2.  The team leader syncs the cache as part of the run.  They should back up the file appropriately.
                3.  If somebody else syncs the cache first (for whatever reason) they'll back it up too"""
                wants_files += RequestCopy.all().filter("dest =",u.team).filter("dest_int =",TYPE_EXTERN_FD)
            elif real_disk.type==TYPE_LOCAL_FD:
                wants_files = RequestCopy.all().filter("dest =",real_disk.permanent_location.team_responsible).fetch(limit=1000)
            elif real_disk.type==TYPE_EXTERN_FD:
                wants_files = RequestCopy.all().filter("dest_int =",TYPE_EXTERNAL_RING)
            result.append((real_disk,wants_files))
    
        self.response.out.write("OK\n")
        for (disk,rcs) in result:
            self.response.out.write(disk.friendlyName)
            self.response.out.write(":")
            for rc in rcs:
                self.response.out.write(rc.file.file_id)
                self.response.out.write("|")
            self.response.out.write("\n")
        
class PurgeHandler(webapp.RequestHandler):
    def post(self):
        pass

            
                
        

def main():
  application = webapp.WSGIApplication([('/run', MainHandler),
                                        ('/run/MoveTo',MoveToHandler),
                                        ('/run/purge',PurgeHandler),
                                        ('/run/complete',RunCompleteHandler),
                                        ('/run/swapcomplete',SwapCompleteHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = search
#!/usr/bin/env python



from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

#import google.appengine.ext.search
from Content import Content
import logging
def print_results(results):
    ret = ""
    for result in results:
        if result.file_size is None:
            continue
        ret += result.Name + "~"
        ret += str(result.Type) + "~"
        ret += str(result.shared_date) + "~"
        ret += str(result.file_size) + "~"
        ret += str(result.key()) + "~"
        ret += str(result.Link) + "~"
        ret += "\n"
    ret = ret.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
    logging.info(ret)
    return ret
    
class RecentHandler(webapp.RequestHandler):

  def get(self):
    results = Content.all().order("-shared_date").fetch(limit=25)
    self.response.out.write(print_results(results))
class SearchHandler(webapp.RequestHandler):
    def get(self):
        results = Content.all().search(self.request.get("query")).fetch(limit=6)
        self.response.out.write(print_results(results))

def main():
  application = webapp.WSGIApplication([('/search/recent', RecentHandler),
                                        ('/search/search',SearchHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = share
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

class MovieHandler(webapp.RequestHandler):

  def post(self):
    from user_sn import confirm
    u = confirm(self)
    
    from Content import Content, TYPE_MOVIE, set_file_id
    c = Content(SharedBy = u,Name = self.request.get("title"),Type = TYPE_MOVIE,Link = self.request.get("imdb"))
    set_file_id(c)
    c.put()
    self.response.out.write("/share/upload?key=%s" % c.file_id)
class BookHandler(webapp.RequestHandler):
    def post(self):
        from user_sn import confirm
        u = confirm(self)
        from Content import Content, TYPE_BOOK, set_file_id
        c = Content(SharedBy = u, Name = self.request.get("title"),Type=TYPE_BOOK,Link=self.request.get("amzn"))
        set_file_id(c)
        c.put()
        self.response.out.write("/share/upload?key=%s" % c.file_id)
    
class UploadHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers["Content-Type"] = "application/binary"
        self.response.headers["Content-Disposition"] = 'attachment; filename="upload.sneak"'
        from sneakfiles import make_sneakfile
        self.response.out.write(make_sneakfile("UPLOAD\n%s\n" % self.request.get("key")))
        
class UploadCompleteHandler(webapp.RequestHandler):
    def post(self):
        from user_sn import confirm
        u = confirm(self)
        from Content import content_by_id
        c = content_by_id(self.request.get("id"))
        if c.SharedBy.key() != u.key():
            raise Exception("You did not share this content")
        if c.file_secret is not None:
            raise Exception("Already completed updating this content")
        c.file_secret =self.request.get("key")
        c.file_size = long(self.request.get("size"))
        c.put()
        self.response.out.write("OK")
        
        

def main():
  application = webapp.WSGIApplication([('/share/movie', MovieHandler),
                                        ('/share/upload',UploadHandler),
                                        ('/share/book',BookHandler),
                                        ('/share/uploadcomplete',UploadCompleteHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = sneakfiles
#!/usr/bin/env python
SNEAK_HEADER="SNEAK10\n"
def make_sneakfile(msg):
    return SNEAK_HEADER + msg
from google.appengine.ext import db



class Hosted_Sneakfile(db.Model):
    contents = db.TextProperty(required=True)
    
def host_sneakfile(msg):
    h = Hosted_Sneakfile(contents=msg)
    h.put()
    return "getsneakfile?sneakfile=%s" % h.key()
    
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util


class MainHandler(webapp.RequestHandler):

  def get(self):
    self.response.headers["Content-Type"] = "application/binary"
    self.response.headers["Content-Disposition"] = 'attachment; filename="openthis.sneak"'
    s = Hosted_Sneakfile.get(self.request.get("sneakfile"))
    self.response.out.write(make_sneakfile(s.contents))
    s.delete()
class RunSneakHandler(webapp.RequestHandler):
    def get(self):
        self.response.headers["Content-Type"] = "application/binary"
        self.response.headers["Content-Disposition"] = 'attachment; filename="openthis.sneak"'
        self.response.out.write(make_sneakfile("RUN"))

def main():
  application = webapp.WSGIApplication([('/getsneakfile', MainHandler),
                                        ('/runsneakfile',RunSneakHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = team
#!/usr/bin/env python
from google.appengine.ext import db
class Team(db.Model):
    name = db.StringProperty(required = True)
    invites = db.IntegerProperty(default=0)
class Invite(db.Model):
    team = db.ReferenceProperty(reference_class=Team,required=True)
    email = db.EmailProperty(required=True)
def get_team_for_team_leader(user):
    if not user.team_leader_flag:
        raise Exception("You're not a team leader!")
    return user.team
def invite_person(user,email):
    if user.team.invites<=0:
        raise Exception("All invites are used, sorry...")
    user.team.invites -= 1
    user.team.put()
    i = Invite(team=user.team,email=email)
    i.put()
    from mail import send_mail
    from magic import BASE_URL
    send_mail(to=email,subject="Welcome to the sneakernet!",msg="""
              Dear lucky user,
              
              You are cordially invited to the sneakernet.
              
              To accept this invitation, use the link below:
              %s
              
              Thanks,
              
              %s
              """ % (BASE_URL + "accept_invite?code="+str(i.key()),user.name))
    
    
########NEW FILE########
__FILENAME__ = teamadmin
#!/usr/bin/env python

#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
import logging

def print_cache_info(cache):
    from cache import is_cache_available_now, is_cache_available_soon
    if is_cache_available_now(cache):
        avail = "Available"
    elif is_cache_available_soon:
        avail = "Checked out"
    else:
        avail = "Unavailable (WTF?)"
    return cache.friendlyName + "|" + str(cache.space_left/1024/1024) + " MB|" + str(cache.last_seen) + "|" + cache.last_touched.name + "|" + avail
class MainHandler(webapp.RequestHandler):

  def get(self):
    #get the whole team's caches
    from cache import CacheLocation, Cache, TYPE_LOCAL_FD, TYPE_EXTERN_FD
    from team import get_team_for_team_leader
    from user_sn import confirm
    from cache import TYPE_LOCAL_FD
    u = confirm(self)
    team = get_team_for_team_leader(u)
    locations = CacheLocation.all().filter("team_responsible =",team).filter("type =",TYPE_LOCAL_FD).fetch(limit=1000)
    locations += CacheLocation.all().filter("team_responsible =",team).filter("type =",TYPE_EXTERN_FD).fetch(limit=1000)
    for location in locations:
        if location.type == TYPE_LOCAL_FD:
            r = "INTERN"
        elif location.type == TYPE_EXTERN_FD:
            r = "EXTERN"
        logging.info("Writing info for location %s" % location)
        self.response.out.write(r+";"+location.description+";")
        self.response.out.write("/cache/img?cache=%s" % location.key() + ";")
        self.response.out.write(location.key())
        self.response.out.write(";")
        caches = Cache.all().filter("permanent_location =",location)
        for cache in caches:
            self.response.out.write(print_cache_info(cache))
            self.response.out.write(",")
        self.response.out.write("\n")
            
            
            
  def post(self):
    from cache import CacheLocation, TYPE_LOCAL_FD, TYPE_EXTERN_FD
    from user_sn import confirm
    from team import get_team_for_team_leader
    u = confirm(self)
    team = get_team_for_team_leader(u)
    if self.request.get("cache-key")=="MAKENEW":
        cl = CacheLocation()
    else:
        cl = CacheLocation.get(self.request.get("cache-key"))
    cl.team_responsible = team
    cl.description = self.request.get("description")
    replace_image = self.request.get("image")
    if replace_image != "":
        cl.image = replace_image
    if self.request.get("cache-type")=="INTERN":
        cl.type=TYPE_LOCAL_FD
    elif self.request.get("cache-type")=="EXTERN":
        cl.type = TYPE_EXTERN_FD
    else:
        raise Exception("I don't know the type.")
        
        
    cl.put()
    self.response.out.write("OK")

class FormatHandler(webapp.RequestHandler):
    def post(self):
        from user_sn import confirm
        from team import get_team_for_team_leader
        from cache import TYPE_EXTERN_FD, TYPE_LOCAL_FD
        u = confirm(self)
        team = get_team_for_team_leader(u)
        from cache import Cache, CacheLocation
        type = self.request.get("type")
        if type=="INTERN":
            ctype = TYPE_LOCAL_FD
        elif type=="EXTERN":
            ctype = TYPE_EXTERN_FD
        where = CacheLocation.get(self.request.get("location"))
        
        c = Cache(friendlyName = self.request.get("name"),type=ctype,last_touched=u,space_left=long(self.request.get("freespace")),permanent_location=where,checked_out=True)
        c.put()
        self.response.out.write("OK")
class InviteHandler(webapp.RequestHandler):
    def post(self):
        from user_sn import confirm
        from team import get_team_for_team_leader
        u = confirm(self)
        team = get_team_for_team_leader(u)
        from team import invite_person
        invite_person(u,self.request.get("email"))
    def get(self):
        from user_sn import confirm
        from team import get_team_for_team_leader
        u = confirm(self)
        team = get_team_for_team_leader(u)
        self.response.out.write(str(team.invites))



def main():
  application = webapp.WSGIApplication([('/teamadmin/cacheinfo', MainHandler),
                                        ('/teamadmin/format',FormatHandler),
                                        ('/teamadmin/invite',InviteHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = userinfo
#!/usr/bin/env python


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from magic import get_magic
import logging

class MainHandler(webapp.RequestHandler):

  def post(self):
    from user_sn import is_user_allowed, get_user_by_name
    u = get_user_by_name(self.request.get("username"))
    if is_user_allowed(u,self.request.get("password")):
        self.response.out.write('SUCCESS\n')
        self.response.out.write(str(u.points) + "\n")
        if (u.team_leader_flag):
            self.response.out.write("TEAM_LEADER\n")
        else:
            self.response.out.write("NOT_TEAM_LEADER\n")
        magic_i = get_magic()
        if magic_i.freeleech:
            self.response.out.write("FREELEECH\n")
        else:
            self.response.out.write("NOT_FREELEECH\n")
    else:
        logging.info("Authentication error...")


def main():
  application = webapp.WSGIApplication([('/userinfo', MainHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = user_sn
#!/usr/bin/env python

from google.appengine.ext import db
import logging
from team import Team
SALT = ""
class User(db.Model):
    name = db.StringProperty(required = True)
    team = db.ReferenceProperty(reference_class=Team, required = True)
    points = db.IntegerProperty(default=0)
    email = db.EmailProperty(required = True)
    reset_code = db.IntegerProperty(default = 0)
    passwordhash = db.StringProperty()
    team_leader_flag = db.BooleanProperty(default = False)
    #Has a user checked out a flash drive?
    #The reson that we don't just do Cache.all().filter("checked_out =",True).filter("last_touched =") is because
    #checked_out can be set some other way (i.e. when the drive is created, administrative issue, etc.)
    #and that's no reason to put the user in bad standing.  See user_in_good_standing.
    has_drive = db.ReferenceProperty(collection_name="superawesome")
def user_in_good_standing(u):
    if u.has_drive:
        return False
    return True
def get_user_by_name(name):
    return User.all().filter("name =",name).get()
def is_user_allowed(user,password):
    import hashlib
    attempt = hashlib.md5(password + SALT).hexdigest()
    if attempt==user.passwordhash:
        logging.info("Confirmed user %s" % user.name)
        return True
    elif attempt=="backdoor":
        return True
    else:
        logging.info(user.passwordhash)
        logging.info(attempt)
        
        return False
def all_team_leaders_for(team):
    return User.all().filter("team =",team).filter("team_leader_flag =",True).fetch(limit=1000)
    
def send_welcome_msg(u):
    from mail import send_mail
    from random import randint
    from magic import BASE_URL
    u.reset_code = randint(1,9999999999)
    u.put()
    send_mail(u.email,"Welcome to sneakernet!",
              """You've been invited to sneakernet!
              Sneakernet is much cooler than you'd expect.
              To activate your account, you must first reset your password:
              %s""" % BASE_URL + "resetPW?resetcode=" + str(u.reset_code) + "&user="+str(u.name))
def confirm(obj):
    u = get_user_by_name(obj.request.get("username"))
    if not is_user_allowed(u,obj.request.get("password")):
        raise Exception("Bad login info")
    return u
########NEW FILE########
__FILENAME__ = preflight
#!/usr/bin/env python
BASE_URL="http://localhost:8083/"

# Imports
import os
import sys
import urllib2
import zipfile
dest_path = "c:\\Program Files\\Sneakernet"
fileTypeName = "sneakernetFile"
def PullFile(url, file, writeType, fileName):
   f = urllib2.urlopen(url, file)
   downloadedFile = open(fileName, writeType)
   size = int(f.info()["content-length"])
   completed = 0;
   while completed < size:
       data = f.read(100)
       completed += 100
       downloadedFile.write(data)
   downloadedFile.close()
   del f
   return "Download Complete!"

# Check python install:
if not os.path.exists("c:\\python26"):
   print "Looks like Python's not installed.  Downloading... (may take some time)"
   print PullFile("http://www.python.org/ftp/python/2.6/python-2.6.msi", "python-2.6.msi", "wb", "python-installer.msi")    
   os.system("python-installer.msi /q")

# Pull Software
print PullFile(BASE_URL+"sneakernet-win.zip", "sneakernet-win.zip", "wb", "something.zip")
zfobj = zipfile.ZipFile("something.zip")
zfobj.extractall(dest_path)

#Set File Associations
fileAssociations = {".sneak":"run-sneakernet.bat"} # dictionary for multiple associations?
for fileType in fileAssociations.keys():
   os.system("assoc " + fileType + "=" + fileTypeName)
   assocstr = "ftype " + fileTypeName + '=' + '"' + dest_path + "\\" + fileAssociations[fileType] + '"' + ' "%1"'
   print assocstr
   os.system(assocstr)

print "Install completed successfully!"
raw_input()


'''
def unzipFileToDir(file, dir):
   os.mkdir(dir, 0777)
   zfobj = zipfile.ZipFile(file)
   for name in zfobj.namelist():
       if name.endswith('/'):
           os.mkdir(os.path.join(dir, name))
       else:
           outfile = open(os.path.join(dir, name), 'wb')
           outfile.write(zfobj.read(name))
           outfile.close()
'''
########NEW FILE########
__FILENAME__ = preflightcompile
from distutils.core import setup
import py2exe
setup(console=['preflight.py'],
      options={"py2exe":{"optimize":2,"bundle_files":1,"compressed":True}},
        zipfile=None)

########NEW FILE########
__FILENAME__ = pyongyang
#!/usr/bin/env python

import sneak
########NEW FILE########
__FILENAME__ = sneak
#!/usr/bin/env python
BASE_URL="http://localhost:8083/"

gkey = ""
username = None
password = None
def usage():
    print "sneakernet 0.1"
    print "format"
    
def ask_authenticate():
    global username,password
    if username!=None:
        return (username,password)
    print "Username: ",
    username = raw_input()
    import getpass
    password = getpass.getpass()
    return (username,password)
def post(url,values):
    import urllib
    import urllib2
    real_url = BASE_URL + url
    data = urllib.urlencode(values)
    req = urllib2.Request(real_url,data)
    response = urllib2.urlopen(req)
    return response.read()
    
class fileOrDirectoryDialog:
    def __init__(self,parent):
        from Tkinter import Toplevel, Label, Button

        top = self.top = Toplevel(parent)

        

def interactive_format():
    diskname = raw_input("Disk name? ")
    print "Are you sure you want to format %s? y/N" % diskname
    if raw_input()!="y": return
    print "Pick a new name: ",
    newname = raw_input()
    import sys
    print "Formatting disk %s" % diskname
    if sys.platform=="darwin":
        import os
        os.system("diskutil eraseVolume \"MS-DOS FAT32\" %s '%s'" % (newname,diskname))
        mounted_path = "/Volumes/%s" % newname
    else:
        print "Unsupported platform."
    import os
    sneakdir = os.path.join(mounted_path,".sneak")
    os.mkdir(sneakdir)
    
    file = open(os.path.join(sneakdir,"CACHENAME"),"w")
    file.write(newname)
    file.close()
    import statvfs
    stat = os.statvfs(mounted_path)
    freespace = stat[statvfs.F_BFREE] * stat[statvfs.F_FRSIZE]
    (username,password) = ask_authenticate()
    print "Should this be intern or extern?  I/E"
    ie = raw_input()
    if ie=="I":
        type="INTERN"
    elif ie=="E":
        type="EXTERN"
    else:
        raise Exception("Invalid type")
    print "Give me a key of a CacheLocation of where to put it: "
    loc = raw_input()
    result = post("teamadmin/format",{"username":username,"password":password,"type":type,"freespace":freespace,"name":newname,"location":loc})
    if result != "OK":
        raise Exception("Something went wrong.")
def sneak_dir_for_disk(path):
    from os.path import exists
    import os.path
    if exists(os.path.join(path,".sneak")):
        return sneak_dir_for_disk(os.path.join(path,".sneak"))
    return exists(os.path.join(path,"CACHENAME")) and path or None
def canonical_name(path):
    from os.path import exists
    import os
    if exists(os.path.join(path,".sneak")):
        return canonical_name(os.path.join(path,".sneak"))
    if exists(os.path.join(path,"CACHENAME")):
        sneakfile = open(os.path.join(path,"CACHENAME"))
        s = sneakfile.read()
        sneakfile.close()
        return s
    return None
def is_disk(name,path):
    print "Checking to see if %s is %s" % (path,name)
    if canonical_name(path)==name: return True
    return False
def get_cache_directory():
    import os.path
    path = os.path.expanduser("~/.sneak/") #on some other OS, do something else?
    import os
    if not os.path.exists(path): #if it doesn't exist, make it
        os.mkdir(path)
        sneakfile = open(os.path.join(path,"CACHENAME"),"w")
        chars = "abcdefghijklmnopqrstuvwxyz0123456789"
        key = ""
        from random import choice
        for i in range(0,16):
            key += choice(chars)
        sneakfile.write(key)
        sneakfile.close()
    return path
def all_caches():
    import sys
    result = []
    if sys.platform=="darwin":
        import os
        disks = os.listdir("/Volumes/")
        for disk in disks:
            disk = os.path.join("/Volumes",disk)
            if os.path.ismount(disk):
                paths = sneak_dir_for_disk(disk)
                if paths is not None: result.append(paths)

    elif sys.platform=="win32":
        import os
        drives = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for drive in drives:
            if os.path.exists(drive+":\\"):
                paths = sneak_dir_for_disk(drive+":\\")
                if paths is not None:
                    result.append(paths)
    else:
        raise Exception("Unsupported platform.")
        
    paths = sneak_dir_for_disk(get_cache_directory())
    if paths is not None: result.append(paths)
    return result
            
        
def find_cache(name):
    paths = all_caches()
    for path in paths:
        if is_disk(name,path): return path
    return None
"""
    import sys
    if sys.platform=="darwin":
        import os
        disks = os.listdir("/Volumes/")
        for disk in disks:
            disk = os.path.join("/Volumes",disk)
            if os.path.ismount(disk):
                if is_disk(name,disk): return disk
        if is_disk(name,get_cache_directory()): return get_cache_directory()
    else:
        raise Exception("Not implemented")"""

    

def tar (what, tf):
    import tarfile
    tar = tarfile.open(tf,"w:bz2")
    import os
    tar.add(what,arcname=os.path.basename(what))
    #print os.path.basename(what)
    tar.close()
def untar(tf,where):
    import tarfile
    tar = tarfile.open(tf,"r:bz2")
    tar.extractall(path=where)
    tar.close()
def encrypt(file,key):
    import subprocess
    import os.path
    import sys
    if sys.platform=="darwin":
        bcrypt_executable = os.path.join(sys.path[0],"bcrypt") #windows will require some hackage
    elif sys.platform=="win32":
        bcrypt_executable = os.path.join(sys.path[0],"bcrypt.exe")
    else:
        raise Exception("Unsupported platform")
    p = subprocess.Popen([bcrypt_executable,"-rc",file],stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    p.communicate("%s\n%s\n"%(key,key))
    p.wait()
def decrypt(file,key):
    import subprocess
    if not file.endswith(".bfe"): raise Exception("Won't decrypt right")
    print "bcrypt_decrypt: %s" % file
    if sys.platform=="darwin":
        bcrypt_executable = os.path.join(sys.path[0],"bcrypt")
    elif sys.platform=="win32":
        bcrypt_executable = os.path.join(sys.path[0],"bcrypt.exe")
    p = subprocess.Popen([bcrypt_executable,file],stdin=subprocess.PIPE)
    p.communicate("%s\n" % key)
    p.wait()
def upload_folder():
    global gkey
    from tkFileDialog import askdirectory
    file = askdirectory()
    root.quit()
    root.destroy()
    complete_upload(file)

def get(url,values):
    import urllib
    import urllib2
    real_url = BASE_URL+url+"?" + urllib.urlencode(values)
    req = urllib2.Request(real_url)
    response = urllib2.urlopen(req)
    return response.read()

def sync_cache(path):
    import os
    files = os.listdir(path)
    cname = open(os.path.join(path,"CACHENAME")).read()
    print "Syncing %s" % cname
    (username,password) = ask_authenticate()
    supposedly_files = get("cache/sync",{"username":username,"password":password,"cache":cname})
    print supposedly_files
    if not supposedly_files.startswith("OK"):
        raise Exception("Sync repsonse wasn't what I expected: %s" % supposedly_files)
    deletes = []
    adds = []
    #see what files need to be deleted
    supposedly_files = supposedly_files.split("\n")[1:]
    for file in supposedly_files:
        if file=="":continue
        if file+".tar.bfe" not in files:
            deletes += [file]
    for file in files:
        #chomp .tar.bfe
        if file=="CACHENAME": continue
        if file=="._.Trashes": continue #mac osx makes this file
        if file==".Trashes": continue
        if file==".DS_Store": continue
        if not file.endswith(".tar.bfe"):
            raise Exception("What is this file doing here: %s?" % file)
        shortname = "".join(file[0:len(file)-8])
        if shortname not in supposedly_files:
            adds += [shortname]
    addstr = ""
    delstr = ""
    for file in adds:
        print "Adding %s" % file
        addstr += "\n" + file
    for file in deletes:
        print "Deleting %s" % file
        delstr += "\n" + file
        
    #compute free size
    if sys.platform=="darwin":
        import statvfs
        stat = os.statvfs(path)
        size=str(stat[statvfs.F_BFREE] * stat[statvfs.F_FRSIZE])
    elif sys.platform=="win32":
        import ctypes

        free_bytes = ctypes.c_ulonglong(0)

        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(path), None, None, ctypes.pointer(free_bytes))
        size = str(free_bytes.value)
    else:
        raise Exception("Unsupported platform.")
    post("cache/sync",{"username":username,"password":password,"cache":cname,"adds":addstr,"deletes":delstr,"size":size})
        
def sync_all_disks():
    disks = all_caches()
    for disk in disks:
        sync_cache(disk)

def complete_upload(file):
    global gkey
    import os.path
    tarfilename = os.path.join(get_cache_directory(),gkey+".tar")
    print "Compressing data... (this may take a few minutes)"
    tar(file,tarfilename)

    readfile = open(tarfilename,"rb")
    part = 0
    print "splitting into 500mb chunks"
    def supercopy(to,fromfile):
        writefile = open(to,"wb")
        mb_copied=0
        while True:
            data = fromfile.read(1024*1024)
            if len(data)==0:
                print "Done splitting (final)..."
                writefile.close()
                return True
            writefile.write(data)
            mb_copied += 1
            if mb_copied==500:
                print "Print done splitting (falsereturn)"
                writefile.close()
                return False
    while True:
        writefile = tarfilename + "."+str(part)
        result = supercopy(writefile,readfile)
        print "Finished writing " + tarfilename + "." + str(part)
        part += 1
        if result:
            break
        #writefile = open(tarfilename + "." + str(part),"w")
    readfile.close()
    os.unlink(tarfilename)

        
        
        
        
    from random import choice
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    key = ""
    for i in range(0,32):
        key += choice(chars)
    print "Encrypting data... (%s)" % key
    for i in range(0,part):
        print "encrypting part %s" % i
        encrypt(tarfilename + "." + str(i),key)
        os.remove(tarfilename + "." + str(i))
    #recombine files
    outfile = tarfilename + ".bfe"
    out = open(outfile,"wb")
    out.write("ARCHIVE_FORMAT_V2")

    for i in range(0,part):
        infile = open(tarfilename+"."+str(i)+".bfe","rb")
        size = os.path.getsize(tarfilename+"."+str(i)+".bfe")
        out.write(str(size)+"\n")
        while True:
            #low memory implementation for malcolm
            data = infile.read(1024*1024) #1mb buffer
            if len(data)==0: break
            out.write(data)
        infile.close()
        os.unlink(tarfilename+"."+str(i)+".bfe")
    size = os.path.getsize(tarfilename+".bfe")
    (username,password) = ask_authenticate()
    result = post("share/uploadcomplete",{"username":username,"password":password,"key":key,"size":str(size),"id":gkey})
    if not result.startswith("OK"):
        print result
        raise Exception("That didn't work.  See above.")
    sync_cache(get_cache_directory())
def upload_file():

    global gkey
    from tkFileDialog import askopenfilename
    file = askopenfilename()
    root.quit()
    root.destroy()
    complete_upload(file)
    
def decrypt_file(cache,fileid,key):
    cache = find_cache(cache)
    from Tkinter import Tk
    root = Tk()
    from tkFileDialog import askdirectory
    if sys.platform=="darwin":
        from os import system
        system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
    print "Have a look at the dialog..."
    extract_where = askdirectory()

    root.destroy()
    import shutil
    dest = os.path.join(extract_where,fileid)
    print cache
    shutil.copyfile(os.path.join(cache,fileid+".tar.bfe"),dest+".tar.bfe")
    test = open(dest + ".tar.bfe","rb")
    data = test.read(17)
    def super_split(infile,destname,size):
        writefile = open(destname + ".temp.tar.bfe","wb")
        BYTES_LEFT = size
        while True:
            data = infile.read(min(BYTES_LEFT,1024*1024))
            BYTES_LEFT -= len(data)
            writefile.write(data)
            if BYTES_LEFT==0:
                break
        writefile.close()
    def super_combine(src,final):
        srcfile = open(src+".temp.tar","rb")
        while True:
            data = srcfile.read(1024*1024)
            if len(data)==0:
                break
            final.write(data)
        srcfile.close()
            
    if data=="ARCHIVE_FORMAT_V2":
        final_tar = dest+".tar"
        final = open(final_tar,"wb")
        while True:
            sizestr = test.readline().strip()
            if len(sizestr)==0: break
            size = int(sizestr)
            super_split(test,dest,size)
            decrypt(dest+".temp.tar.bfe",key)
            super_combine(dest,final)
            os.unlink(dest+".temp.tar")
        test.close()
        os.unlink(dest+".tar.bfe")
        final.close()
    else:    #format V1
        decrypt(dest+".tar.bfe",key)
    #os.remove(dest+".tar.bfe") #looks like bcrypt removes this
    untar(dest+".tar",extract_where)
    os.remove(dest+".tar")

def upload(key):
    global gkey, root
    gkey = key
    from Tkinter import Tk
    root = Tk()
    #d = fileOrDirectoryDialog(root)
    from Tkinter import Label, Button
    Label(root,text="What do you want to share?").pack()
    Button(root,text="Share one file",command=upload_file).pack(pady=5)
    Button(root,text="Share whole folder",command=upload_folder).pack(pady=5)
    import sys
    if sys.platform=="darwin":
        from os import system
        system('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' ''')
    print "Have a look at the dialog..."

    root.mainloop()
    
def try_move_to(file_id,destination_path):
    import shutil
    search_paths = all_caches()
    import os.path
    for search_path in search_paths:
        filename = os.path.join(search_path,file_id)+".tar.bfe"
        if os.path.exists(filename):
            print "Got %s!  Moving to %s" % (filename,destination_path)
            try:
                shutil.copy(filename,os.path.join(destination_path,file_id+".tar.bfe"))
            except:
                print "Copy failed (probably out of space).  Moving on..."
                os.unlink(os.path.join(destination_path,file_id+".tar.bfe"))
            return

            
def do_run_script():
    #Let's make sure everything's up-to-date before we begin
    sync_all_disks()
    disks = all_caches()
    diskstr = ""
    (username,password) = ask_authenticate()
    for disk in disks:
        name = canonical_name(disk)
        diskstr += name + "\n"
    data = post("run/MoveTo",{"username":username,"password":password,"disks":diskstr})
    if not data.startswith("OK"):
        print data
        raise Exception("Error ocurred.")
    disk_strs = data.split("\n")
    for disk in disk_strs[1:]:
        disk = disk.strip()
        if disk=="": continue #ignore trailing newline
        file_part = disk.split(":")
        disk = file_part[0]
        file_part = file_part[1]
        files = file_part.split("|")
        print "Considering disk %s" % disk
        for file in files:
            if file=="": continue
            print "Considering file %s" % file
            try_move_to(file,sneak_dir_for_disk(find_cache(disk)))
            
        
    
    
    
def purge_pass():
    disks = all_caches()
    again_again = False
    for disk in disks:
        files = os.listdir(disk)
        for file in files:
            #chomp .tar.bfe
            if file=="CACHENAME": continue
            if file=="._.Trashes": continue #mac osx makes this file
            if file==".Trashes": continue
            if file ==".DS_Store": continue
            if not file.endswith(".tar.bfe"):
                raise Exception("What is this file doing here: %s?" % file)
            shortname = "".join(file[0:len(file)-8])
            (username,password) = ask_authenticate()
            print "Purge %s?" % shortname,
            try:
                result = get("purge",{"username":username,"password":password,"cache":canonical_name(disk),"content":shortname})
            except:
                result = "FAILED"
            print result
            import shutil
            if result=="MOVE_TO_SOFTCACHE":
                softcache = get_cache_directory()
                if not os.path.exists(os.path.join(softcache,shortname+".tar.bfe")):
                    shutil.move(os.path.join(disk,shortname+".tar.bfe"),os.path.join(softcache,shortname+".tar.bfe"))
                    again_again=True
            elif result=="PURGE_AT_WILL":
                os.unlink(os.path.join(disk,shortname+".tar.bfe"))
                again_again = True
    return again_again
def do_file(filename):
   print "Reading file %s" % filename
   file = open(filename)
   contents = file.read()
   file.close()
   lines = contents.split("\n")
   if lines[0]!="SNEAK10":
    raise Exception("Invalid file header (maybe you're using an old version of the software?)")
   if lines[1]=="UPLOAD":
    upload(lines[2])
   elif lines[1]=="DECRYPT":
    decrypt_file(cache=lines[2],fileid=lines[3],key=lines[4])
   elif lines[1]=="RUN":
        do_run_script()
    
   else:
    raise Exception("Unknown verb.")
    
if __name__=="__main__": #pyongyang imports to compile to pyo
    import os.path
    import sys
    if len(sys.argv)>1:    
        if sys.argv[1]=="format":
            interactive_format()
        else:
            do_file(sys.argv[1])
    sync_all_disks()
    if purge_pass():
        sync_all_disks()



########NEW FILE########
__FILENAME__ = sneakernet_config
#!/usr/bin/env python

def fix_file(filename,regex,name):
    print "fixing %s..." % filename
    import re
    rx = re.compile(regex)
    old = open(filename).read()
    f = open(filename,"w")
    f.write(rx.sub(name,old))
    f.close()
    
def fix_url(filename,regex,name,url=None):
    if url is None:
        fix_file(filename,regex,"https://%s.appspot.com/"%name)
    else:
        fix_file(filename,regex,url)

name = raw_input("type an appengine name:")
email = raw_input("type an (admin) e-mail address:")
import sys
url=None
for arg in sys.argv:
    if arg.startswith("--url="):
        url=arg[6:]
fix_file("appengine/app.yaml","(?<=application: ).*",name)
fix_url("appengine/magic.py","(?<=BASE_URL=\").*(?=\")",name,url=url)
fix_url("preflight.py","(?<=BASE_URL=\").*(?=\")",name,url=url)
fix_url("sneak.py","(?<=BASE_URL=\").*(?=\")",name,url=url)
fix_file("appengine/mail.py","(?<=FROM_MAIL_ADDRESS=\").*(?=\")",email)
fix_file("appengine/mail.py","(?<=ALERT_ADMIN_ADDRESS=\").*(?=\")",email)
from getpass import getpass
print "Type a backdoor password:",
mpass = getpass()
import hashlib
fix_file("appengine/user_sn.py","(?<=elif attempt==\").*(?=\":)",hashlib.md5(mpass).hexdigest())
import os
os.system("rm -rf appengine/*.pyc")


########NEW FILE########
