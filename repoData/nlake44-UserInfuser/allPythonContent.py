__FILENAME__ = dev_tester
# Copyright (C) 2011, CloudCaptive
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import sys
import inspect
from userinfuser.ui_api import *
from userinfuser.ui_constants import *
pwd = os.getcwd()
# Test to make sure it can read the API key from the env
prime_path = "http://localhost:8080/api/1/test"
delete_path = "http://localhost:8080/api/1/testcleanup"
IS_LOCAL = True
# ID settings for testing
account = "test@test.c"
testId = "testuserid"
testId2 = "anotheruser"
testId3 = "anotheruserxxxx"
badgeId1 = "music-1-private"
badgeId2 = "music-2-private"
badgeId3 = "music-3-private"
badgeId9 = "music-9-private"

testSecret = "8u8u9i9i"
# Set API key
apiKey = "ABCDEFGHI"
DEFAULT_DEBUG = True
# Turn this off/on to leave or delete data from the db 
cleanup = False
def __url_post(url, argsdic):
  import urllib
  import urllib2
  import socket
  socket.setdefaulttimeout(30) 
  if argsdic:
    url_values = urllib.urlencode(argsdic)

  req = urllib2.Request(url, url_values)
  response = urllib2.urlopen(req)
  output = response.read()

  return output  

""" Make sure what we received is what we expected """
def checkerr(line_num, received, expected):
  if expected != received:
    print "Failed for test at " + sys.argv[0] + ": " + str(line_num) + \
          " with a return of: " + str(received) + " while expecting: " + str(expected)
    exit(1)

""" Make sure the item is not what we received """
def notcheckerr(line_num, received, shouldnotbe):
  if shouldnotbe == received:
    print "Failed for test at " + sys.argv[0] + ": " + str(line_num) \
        + " with a return of: " + str(received) + \
        " while it should not be but was: " + str(shouldnotbe)
    exit(1)

""" See if the given string is contained in the response """
def checkstr(line_num, received, searchstr):
  if searchstr not in str(received):
    print "Failed for test at " + sys.argv[0] + ":" + str(line_num) \
        + " with a return of: " + str(received) + \
        " while searching for: " + searchstr
    exit(1)

""" See if the given string is not contained in the response """
def checknotstr(line_num, received, searchstr):
  if searchstr not in received:
    return
  else:
    print "Failed for test at " + sys.argv[0] + ":" + str(line_num) \
        + " with a return of: " + str(received) + \
        " while searching for: " + searchstr + " where it should not be"
    exit(1)
      
def lineno():
  return inspect.currentframe().f_back.f_lineno

ui_good = UserInfuser(account, apiKey, debug=DEFAULT_DEBUG, local=IS_LOCAL, sync_all=True)
ui_bad = UserInfuser(account, apiKey + "x", debug=DEFAULT_DEBUG, local=IS_LOCAL, sync_all=True)
badgetheme1 = "music"
badgetheme2 = "birds"

# Prime the DB with an account and badges
argsdict = {"apikey":apiKey,
           "accountid":account,
           "badgeid":badgeId1,
           "secret":testSecret,
           "user":testId,
           "theme":badgetheme1}

ret = __url_post(prime_path, argsdict)
checkstr(lineno(), ret, "success")
ret = __url_post(delete_path, argsdict)
checkstr(lineno(), ret, "success")
ret = __url_post(prime_path, argsdict)
checkstr(lineno(), ret, "success")

# ADD USER TESTS
start = time.time()
checkerr(lineno(), ui_good.update_user(testId, "Raaaaaaj", "http://facebook.com/nlake44", "http://imgur.com/AK9Fw"), True)
end = time.time()
sync_time = end - start
success = True
try:
  success = ui_bad.update_user(testId, "Heather", "http://www.facebook.com/profile.php?id=710661131", "http://profile.ak.fbcdn.net/hprofile-ak-snc4/203293_710661131_7132437_n.jpg")
except ui_errors.PermissionDenied:
  success = False
checkerr(lineno(), success, False)   

# Add a new field because we did not do it before
checkerr(lineno(), ui_good.update_user(testId, user_name="Raj", link_to_profile="http://facebook.com/nlake44", link_to_profile_img="http://profile.ak.fbcdn.net/hprofile-ak-snc4/203059_3610637_6604695_n.jpg"), True)
success = True
try:
  success = ui_bad.update_user(testId, user_name="Jack Smith", link_to_profile="http://test.com/a", link_to_profile_img="http://test.com/a/image")
except ui_errors.PermissionDenied:
  success = False
checkerr(lineno(), success, False)   

success = True
try:
  success = ui_good.update_user(testId2, user_name="Billy Gene", link_to_profile="http://www.facebook.com/isnotmylove", link_to_profile_img="http://cdn3.iconfinder.com/data/icons/faceavatars/PNG/J01.png")
except ui_errors.BadArgument:
  success = False
checkerr(lineno(), success, True)   


# AWARD BADGE TESTS
checkerr(lineno(), ui_good.award_badge(testId, badgeId1, reason="Star Power"), True)
success = True
try:
  success = ui_bad.award_badge(testId, badgeId1, reason="Star User")
except ui_errors.PermissionDenied:
  success = False
checkerr(lineno(), success, False)   
success = True
try:
  success = ui_good.award_badge(testId, "", reason="Promoter")
except ui_errors.BadArgument:
  success = False
checkerr(lineno(), success, False)   

success = True
try:
  success = ui_good.award_badge(testId, badgeId1 + "xxx", reason="Star Power")
except ui_errors.BadgeDoesNotExist:
  success = False
checkerr(lineno(), success, False)   


checkerr(lineno(), ui_good.award_badge(testId, badgeId2, reason='Maven'), True)
success = True
try:
  success =ui_bad.award_badge(testId, badgeId2, reason="For Fun")
except ui_errors.PermissionDenied:
  success = False
checkerr(lineno(), success, False)   

checkerr(lineno(), ui_good.remove_badge(testId, badgeId3), True)
checknotstr(lineno(), str(ui_good.get_user_data(testId)), badgeId3)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 10, 100, reason="Power User"), True)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 10, 100, reason="Power User"), True)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 10, 100, reason="Power User"), True)
checknotstr(lineno(), str(ui_good.get_user_data(testId)), badgeId3)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 70, 100, reason="Power User"), True)
checkstr(lineno(), str(ui_good.get_user_data(testId)), badgeId3)
success = True
try:
  success =ui_bad.award_badge(testId, badgeId2, reason="Shooting Star")
except ui_errors.PermissionDenied:
  success = False
checkerr(lineno(), success, False)   


# GET WIDGET TESTS
checkstr(lineno(), ui_good.get_widget(testId, "trophy_case"), "trophy_case")
checkstr(lineno(), ui_good.get_widget(testId, "milestones"), "milestones")
checkstr(lineno(), ui_good.get_widget(testId, "points"), "points")
checkstr(lineno(), ui_good.get_widget(testId, "rank"), "rank")
checkstr(lineno(), ui_good.get_widget(testId, "notifier"), "notifier")
checkstr(lineno(), ui_good.get_widget(testId, "leaderboard"), "leaderboard")

print ui_good.get_widget(testId, "trophy_case")
print ui_good.get_widget(testId, "points")
print ui_good.get_widget(testId, "rank")
print ui_good.get_widget(testId, "notifier")
print ui_good.get_widget(testId, "leaderboard")
success = True
try:
  success =ui_good.get_widget(testId, "doesnotexit")
except ui_errors.UnknownWidget:
  success = False
checkerr(lineno(), success, False)

# AWARD POINTS TESTS
checkerr(lineno(), ui_good.award_points(testId, 100, "just because"),True)
checkerr(lineno(), ui_good.award_points(testId, 100, "just because"),True)
success = True
try:
  success =ui_bad.award_points(testId, 100, "just because")
except ui_errors.PermissionDenied:
  success = False
checkerr(lineno(), success, False)   

success = True
try:
  success = ui_good.award_points(testId, "xxx", "just because")
except ui_errors.BadArgument:
  success = False
checkerr(lineno(), success, False)   

# GET USER DATA TESTS
# Verify badges are correctly being queried for
checkstr(lineno(), str(ui_good.get_user_data(testId)), badgeId1)
checkstr(lineno(), str(ui_good.get_user_data(testId)), badgeId2)
checkstr(lineno(), str(ui_good.get_user_data(testId)), testId)
# Check to see if points was incremented correctly
checkstr(lineno(), str(ui_good.get_user_data(testId)), "200")
success =  ui_bad.get_user_data(testId)
checkstr(lineno(), success, "failed")   

badUser = "blahblahblah___"
success =  ui_good.get_user_data(badUser)
checkstr(lineno(), success, "failed")

if cleanup:
  checkerr(lineno(), ui_good.remove_badge(testId, badgeId1), True)
  checkerr(lineno(), ui_good.remove_badge(testId, badgeId2), True)
  checkerr(lineno(), ui_good.remove_badge(testId, badgeId3), True)

success = True
try:
  success = ui_good.remove_badge(testId, "-x-x-x" + badgeId3 + "xxx" )
except ui_errors.BadgeDoesNotExist:
  success = False
checkerr(lineno(), success, False)   

#Delete the DB badges with an account and badges
ret = __url_post(delete_path, argsdict)
checkstr(lineno(), ret, "success")
###################################
# Async testing
###################################
ui_good = UserInfuser(account, apiKey, debug=DEFAULT_DEBUG, local=True)
ui_bad = UserInfuser(account, apiKey + "x", debug=DEFAULT_DEBUG, local=True)
ret = __url_post(delete_path, argsdict)
checkstr(lineno(), ret, "success")
ret = __url_post(prime_path, argsdict)
checkstr(lineno(), ret, "success")

# ADD USER TESTS
start = time.time()
checkerr(lineno(), ui_good.update_user(testId, user_name="Raj", link_to_profile="http://facebook.com/nlake44", link_to_profile_img="http://imgur.com/AK9Fw"), True)
end = time.time()
async_time = end - start
if async_time > sync_time:
  print "Async calls are slower than sync calls???"
  print "Async time: " + str(async_time)
  print "Sync time:" + str(sync_time)
  exit(1)
# async calls dont throw anything, always return true
success = ui_bad.update_user(testId, "a", "http://test.com/a", "http://test.com/a/image")
checkerr(lineno(), success, True)   

# Add a new field because we did not do it before
checkerr(lineno(), ui_good.update_user(testId, user_name="Jakob", link_to_profile="http://profile.ak.fbcdn.net/hprofile-ak-snc4/49299_669633666_9641_n.jpg", link_to_profile_img="http://profile.ak.fbcdn.net/hprofile-ak-snc4/49299_669633666_9641_n.jpg"), True)
# will return true
success = ui_bad.update_user(testId, user_name="Jack Smith", link_to_profile="http://test.com/a", link_to_profile_img="http://test.com/a/image")
checkerr(lineno(), success, True)

success = ui_good.update_user(testId2, user_name="Shan", link_to_profile="http://www.facebook.com/profile.php?id=3627076", link_to_profile_img="http://www.facebook.com/album.php?profile=1&id=3627076")
checkerr(lineno(), success, True)


# AWARD BADGE TESTS
# all calls should return true
checkerr(lineno(), ui_good.award_badge(testId, badgeId1, reason="Bright"), True)
success =  ui_bad.award_badge(testId, badgeId1, reason="For Fun")
checkerr(lineno(), success, True)
success = ui_good.award_badge(testId, "", reason="Star Power")
checkerr(lineno(), success, True)   

success = ui_good.award_badge(testId, badgeId1 + "xxx", reason="Celeb Status")
checkerr(lineno(), success, True)


success = ui_bad.award_badge(testId, badgeId2, reason="For fun")
checkerr(lineno(), success, True)

checkerr(lineno(), ui_good.remove_badge(testId, badgeId3), True)
# enough time to catch up
time.sleep(1)
checknotstr(lineno(), str(ui_good.get_user_data(testId)), badgeId3)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 10, 100, reason="Star Power"), True)
time.sleep(1)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 10, 100, reason="Star Power"), True)
time.sleep(1)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 10, 100, reason="Star Power"), True)
time.sleep(1)
checknotstr(lineno(), str(ui_good.get_user_data(testId)), badgeId3)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 70, 100, reason="Lobster Bisque mmmm"), True)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 70, 100, reason="ice cream sandwiches"), True)
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId3, 70, 100, reason="Good Times"), True)

# partial award
checkerr(lineno(), ui_good.award_badge_points(testId, badgeId9, 10, 100, reason="Almost there"), True)

time.sleep(2)
checkstr(lineno(), str(ui_good.get_user_data(testId)), badgeId3)
success = ui_bad.award_badge(testId, badgeId2, reason="For fun")
checkerr(lineno(), success, True)

checkerr(lineno(), ui_good.award_badge(testId, badgeId2, reason="Shooting High"), True)

# GET WIDGET TESTS
checkstr(lineno(), ui_good.get_widget(testId, "trophy_case"), "trophy_case")
checkstr(lineno(), ui_good.get_widget(testId, "milestones"), "milestones")
checkstr(lineno(), ui_good.get_widget(testId, "notifier"), "notifier")
checkstr(lineno(), ui_good.get_widget(testId, "points"), "points")
checkstr(lineno(), ui_good.get_widget(testId, "rank"), "rank")


# AWARD POINTS TESTS
checkerr(lineno(), ui_good.award_points(testId, 100, "just because"),True)
checkerr(lineno(), ui_good.award_points(testId, 100, "just because"),True)
success = ui_bad.award_points(testId, 100, "just because")
checkerr(lineno(), success, True)

success = ui_good.award_points(testId, "xxx", "just because")
checkerr(lineno(), success, True)

# GET USER DATA TESTS
# Verify badges are correctly being queried for
time.sleep(1)
checkstr(lineno(), str(ui_good.get_user_data(testId)), badgeId1)
checkstr(lineno(), str(ui_good.get_user_data(testId)), badgeId2)
checkstr(lineno(), str(ui_good.get_user_data(testId)), testId)
# Check to see if points was incremented correctly
checkstr(lineno(), str(ui_good.get_user_data(testId)), "200")

if cleanup:
  checkerr(lineno(), ui_good.remove_badge(testId, badgeId1), True)
  checkerr(lineno(), ui_good.remove_badge(testId, badgeId2), True)
  checkerr(lineno(), ui_good.remove_badge(testId, badgeId3), True)

success = ui_good.remove_badge("-x-x-x" + badgeId3 + "xxx", testId)
checkerr(lineno(), success, True)   
#ui_good.sync_all = True
success = ui_good.update_user(testId2, user_name="Raj", link_to_profile="http://www.facebook.com/nlake44", link_to_profile_img="http://profile.ak.fbcdn.net/hprofile-ak-snc4/203059_3610637_6604695_n.jpg")
checkstr(lineno(), ui_good.get_widget(testId2, "rank"), "rank")
ui_good.award_points(testId2, 10)
checkerr(lineno(), ui_good.update_user(testId3), True)
ui_good.create_badge("apple","oranges","fruit", "http://cdn1.iconfinder.com/data/icons/Futurosoft%20Icons%200.5.2/128x128/apps/limewire.png")
ui_good.award_badge("testuserid", "oranges-apple-private", reason="FRUIT!")
checkerr(lineno(), ui_good.award_badge_points(testId, "music-4-private", 10, 100, reason="Power User"), True)
time.sleep(1)

# award partial badge points 
#Delete the DB badges with an account and badges
if cleanup:
  ret = __url_post(delete_path, argsdict)
  checkstr(lineno(), ret, "success")
  # clear out the second user
  argsdict['user'] = testId2
  ret = __url_post(prime_path, argsdict)
  ret = __url_post(delete_path, argsdict)
  checkstr(lineno(), ret, "success")
  argsdict['user'] = testId3
  ret = __url_post(prime_path, argsdict)
  ret = __url_post(delete_path, argsdict)
  checkstr(lineno(), ret, "success")

print ui_good.get_widget(testId, "trophy_case")
print ui_good.get_widget(testId, "milestones")
print ui_good.get_widget(testId, "points")
print ui_good.get_widget(testId, "rank")
print ui_good.get_widget(testId, "notifier")
print ui_good.get_widget(testId, "leaderboard")
 
# Need to test awarding a badge via points
print "SUCESS" 
exit(0)


########NEW FILE########
__FILENAME__ = ui_api
# Copyright (C) 2011, CloudCaptive
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json
import os 
import hashlib
import ui_constants
import ui_errors
import threading
import urllib
import urllib2

try:
  # For GAE
  from google.appengine.api import urlfetch
  import logging
except:
  pass

def ui_threaded(callback=lambda *args, **kwargs: None, daemonic=True):
  """Decorate a function to run in its own thread and report the result
  by calling callback with it. Code yanked from stackoverflow.com"""
  def innerDecorator(func):
    def inner(*args, **kwargs):
      target = lambda: callback(func(*args, **kwargs))
      t = threading.Thread(target=target)
      t.setDaemon(daemonic)
      t.start()
    return inner
  return innerDecorator



class UserInfuser():
  def __init__(self, 
               account, # required 
               api_key, # required
               debug=False, 
               local=False, 
               encrypt=True,
               sync_all=False):
    """ 
      Constructor
      Required Arguments: 
                 account_email: The email you registered with
                 api_key: The key provided by UserInfuser
      Optional Arguments: 
                 encrypt: To Enable HTTPS (secure connections)
                 debug: For debugging information
                 local: Used for testing purposes
                 sync_all: Make all calls synchronous (slows your 
                           application down, only use it for testing)
      Exception: Tosses a BadConfiguration if required arguments are None
    """
    self.ui_url =  ui_constants.UI_PATH
    if encrypt:
      self.ui_url = ui_constants.UI_SPATH

    self.isGAE = False
    try:
      # There is no threading in Google App Engine
      from google.appengine.api import urlfetch
      self.isGAE = True
      # URL Fetch is not async in the dev server, force to sync
      if os.environ["SERVER_SOFTWARE"].find("Development") != -1:
        self.ui_url = ui_constants.LOCAL_TEST
        self.debug_log("Local testing enabled")
        self.raise_exceptions = True
    except:
      pass

    self.sync_all = sync_all

    self.debug = debug
    self.debug_log("debug is on, account: %s, apikey: %s"%(account, api_key))
    
    self.api_key = api_key
    if not account or not api_key:
      raise ui_errors.BadConfiguration()
    self.account = account

    self.raise_exceptions = ui_constants.RAISE_EXCEPTIONS
    if local:
      self.ui_url = ui_constants.LOCAL_TEST
      self.debug_log("Local testing enabled")
      self.raise_exceptions = True

    self.update_user_path = self.ui_url + ui_constants.API_VER + "/" + \
                         ui_constants.UPDATE_USER_PATH
    self.award_badge_path = self.ui_url + ui_constants.API_VER + "/" +\
                         ui_constants.AWARD_BADGE_PATH
    self.award_badge_points_path = self.ui_url + ui_constants.API_VER + "/"+\
                         ui_constants.AWARD_BADGE_POINTS_PATH
    self.award_points_path = self.ui_url + ui_constants.API_VER + "/"+\
                         ui_constants.AWARD_POINTS_PATH
    self.get_user_data_path = self.ui_url + ui_constants.API_VER + "/" + \
                         ui_constants.GET_USER_DATA_PATH
    self.remove_badge_path = self.ui_url + ui_constants.API_VER + "/" + \
                         ui_constants.REMOVE_BADGE_PATH
    self.widget_path = self.ui_url + ui_constants.API_VER + "/" + \
                         ui_constants.WIDGET_PATH
    self.create_badge_path = self.ui_url + ui_constants.API_VER + "/" + \
                         ui_constants.CREATE_BADGE_PATH
    
    self.timeout = 10 # seconds

  def get_user_data(self, user_id):
    """
     Function: get_user_data
     Arguments: user_id
                The user id is a unique identifier. It could be an email or 
                unique name. 
     Return value: Returns a dictionary of information about the user
           example:
           {"status": "success", 
            "is_enabled": "yes", 
            "points": 200, 
            "user_id": "nlake44@gmail.com", 
            "badges": ["muzaktheme-guitar-private", 
                       "muzaktheme-bass-private", 
                       "muzaktheme-drums-private"], 
            "profile_img": "http://test.com/images/raj.png",
            "profile_name": "Raj Chohan", 
            "profile_link": "http://test.com/nlake44", 
            "creation_date": "2011-02-26"} 
     Notes: This function is always synchronous. It will add latency into 
            your application/web site.
    """
    argsdict = {"apikey":self.api_key,
               "userid":user_id,
               "accountid":self.account}
    ret = '{"status":"failed"}'
    try:
      ret = self.__url_post(self.get_user_data_path, argsdict)
      self.debug_log("Received: %s"%ret)
    except:
      self.debug_log("Connection Error")
      if self.raise_exceptions:
        raise ui_errors.ConnectionError()

    try:
      ret = json.loads(ret) 
    except:
      self.debug_log("Unable to parse return message")
    return ret
  
  def update_user(self, user_id, user_name="", link_to_profile="", link_to_profile_img=""):
    """
     Function: update_user
     Description: To either add a new user, or update a user's information
     Required Arguments: user_id (unique user identifier)
     Optional Arguments: 
                user_name (The name that will show up in widgets, otherwise it
                           will use the user_id)
                link_to_profile (a URL to the user's profile)
                link_to_profile (a URL to a user's profile picture)
     Return value: True on success, False otherwise
    """
    argsdict = {"apikey":self.api_key,
               "userid":user_id,
               "accountid":self.account,
               "profile_name":user_name,
               "profile_link": link_to_profile,
               "profile_img":link_to_profile_img}
    ret = None
    try:
      if self.sync_all:
        ret = self.__url_post(self.update_user_path, argsdict)
      else: 
        self.__url_async_post(self.update_user_path, argsdict)
        return True
      self.debug_log("Received: %s"%ret)
    except:
      self.debug_log("Connection Error")
      if self.raise_exceptions:
        raise ui_errors.ConnectionError()
    return self.__parse_return(ret)


  def award_badge(self, user_id, badge_id, reason="", resource=""):
    """
     Function: award_badge
     Description: Award a badge to a user
     Required Arguments: user_id (unique user identifier)
                         badge_id (unique badge identifier from 
                                   UserInfuser website under badges tab of 
                                   control panel)
     Optional Arguments: reason (A short string that shows up in the user's 
                                 trophy case)
                         resource (A URL that the user goes to if the badge 
                                 is clicked) 
     Return value: True on success, False otherwise
    """
    argsdict = {"apikey":self.api_key,
               "accountid":self.account,
               "userid":user_id,
               "badgeid":badge_id,
               "resource": resource,
               "reason":reason}
    ret = None
    try:
      if self.sync_all:
        ret = self.__url_post(self.award_badge_path, argsdict)
      else: 
        self.__url_async_post(self.award_badge_path, argsdict)
        return True
      self.debug_log("Received: %s"%ret)
    except:
      self.debug_log("Connection Error")
      if self.raise_exceptions:
        raise ui_errors.ConnectionError()
    return self.__parse_return(ret)

  def remove_badge(self, user_id, badge_id):
    """
     Function: remove_badge
     Description: Remove a badge from a user
     Required Arguments: user_id (unique user identifier)
                         badge_id (unique badge identifier from 
                                   UserInfuser website under badges tab of 
                                   control panel)
     Return value: True on success, False otherwise
    """ 

    argsdict = {"apikey":self.api_key,
               "accountid":self.account,
               "userid":user_id,
               "badgeid":badge_id}
    ret = None
    try:
      if self.sync_all:
        ret = self.__url_post(self.remove_badge_path, argsdict)
      else: 
        self.__url_async_post(self.remove_badge_path, argsdict)
        return True
      self.debug_log("Received: %s"%ret)
    except:
      self.debug_log("Connection Error")
      if self.raise_exceptions:
        raise ui_errors.ConnectionError()
    return self.__parse_return(ret)

  def award_points(self, user_id, points_awarded, reason=""):
    """
     Function: award_points
     Description: Award points to a user
     Required Arguments: user_id (unique user identifier)
                         points_awarded 
     Optional Arguments: reason (Why they got points)
     Return value: True on success, False otherwise
    """ 
    argsdict = {"apikey":self.api_key,
               "accountid":self.account,
               "userid":user_id,
               "pointsawarded":points_awarded,
               "reason":reason}
    ret = None
    try:
      if self.sync_all:
        ret = self.__url_post(self.award_points_path, argsdict)
      else: 
        self.__url_async_post(self.award_points_path, argsdict)
        return True
      self.debug_log("Received: %s"%ret)
    except:
      self.debug_log("Connection Error")
      if self.raise_exceptions:
        raise ui_errors.ConnectionError()
    return self.__parse_return(ret)

  def award_badge_points(self, user_id, badge_id, points_awarded, points_required, reason="", resource=""):
    """
     Function: award_badge_points
     Description: Award badge points to a user. Badges can also be achieved
                  after a certain number of points are given towards an 
                  action. When that number is reached the badge is awarded to
                  the user. 
     Required Arguments: user_id (unique user identifier)
                         points_awarded 
                         badge_id (unique badge identifier from 
                                   UserInfuser website under badges tab of 
                                   control panel)
                         points_required (The total number of points a user must
                                   collect to get the badge)
     Optional Arguments: reason (Why they got the badge points)
                         resource (URL link to assign to badge)
     Return value: True on success, False otherwise
    """
    argsdict = {"apikey":self.api_key,
               "accountid":self.account,
               "userid":user_id,
               "badgeid":badge_id,
               "pointsawarded":points_awarded,
               "pointsrequired":points_required,
               "reason":reason, 
               "resource":resource}
    ret = None
    try:
      if self.sync_all:
        ret = self.__url_post(self.award_badge_points_path, argsdict)
      else: 
        self.__url_async_post(self.award_badge_points_path, argsdict)
        return True
      self.debug_log("Received: %s"%ret)
    except:
      self.debug_log("Connection Error")
      if self.raise_exceptions:
        raise ui_errors.ConnectionError()
      return False

    return self.__parse_return(ret)

 
  def get_widget(self, user_id, widget_type, height=500, width=300):
    """
     Function: get_widget
     Description: Retrieve the HTML 
     Required Arguments: user_id (unique user identifier)
                         widget_type (Check website for supported widgets)
     Optional Arguments: height and width. It is strongly recommended to tailor 
                         these values to your site rather than using the default
                         (500x300 pixels). Wigets like points and rank should
                         be much smaller.
     Return value: String to place into your website. The string will render an 
                   iframe of a set size. Customize your widgets on the
                   UserInfuser website.
    """
    if not user_id:
      user_id = ui_constants.ANONYMOUS
    if widget_type not in ui_constants.VALID_WIDGETS:
      raise ui_errors.UnknownWidget()
    userhash = hashlib.sha1(self.account + '---' + user_id).hexdigest()
    self.__prefetch_widget(widget_type, user_id)
    if widget_type != "notifier":
      return "<iframe border='0' z-index:9999; frameborder='0' height='"+str(height)+"px' width='"+str(width)+"px' allowtransparency='true' scrolling='no' src='" + self.widget_path + "?widget=" + widget_type + "&u=" + userhash + "&height=" +str(height) + "&width="+str(width)+"'>Sorry your browser does not support iframes!</iframe>"
    else:
      return "<div style='z-index:9999; overflow: hidden; position: fixed; bottom: 0px; right: 10px;'><iframe style='border:none;' allowtransparency='true' height='"+str(height)+"px' width='"+str(width)+"px' scrolling='no' src='" + self.widget_path + "?widget=" + widget_type + "&u=" + userhash + "&height=" +str(height) + "&width="+str(width)+"'>Sorry your browser does not support iframes!</iframe></div>"

  @ui_threaded()
  def __threaded_url_post(self, url, argsdic):
    self.__url_post(url, argsdic)  

  def __url_async_post(self, url, argsdic):
    if self.isGAE:
      # This will not work on the dev server for GAE, dev server must only use
      # synchronous calls
      rpc = urlfetch.create_rpc(deadline=10)
      try:
        urlfetch.make_fetch_call(rpc, url, payload=urllib.urlencode(argsdic), method=urlfetch.POST)
      except:
        self.debug_log("Unable to make fetch call to url: %s"%url)
    else:
      self.__threaded_url_post(url, argsdic)
 
  def __url_post(self, url, argsdic):
    try:
      import socket
      socket.setdefaulttimeout(self.timeout)
    except:
      pass  
    url_values = ""
    if argsdic:
      url_values = urllib.urlencode(argsdic)
  
    req = urllib2.Request(url, url_values)
    output = ""
    if self.isGAE:
      try:
        output = urlfetch.fetch(url=url, 
                                payload=url_values, 
                                method=urlfetch.POST,
                                deadline=10)
        output = output.content
      except:
        self.debug_log("Exception tossed when opening url: %s"%url)
        output =""
    else:
      try:
        response = urllib2.urlopen(req)
        output = response.read()
      except:
        self.debug_log("Exception tossed when opening url: %s"%url)
        output = "" 

    self.debug_log("urllib output %s"%output)
  
    return output  

  def __parse_return(self, ret):
    try:
      ret = json.loads(ret) 
    except:
      self.debug_log("Unable to parse return message")
      return False
    
    if ret['status'] == 'failed':
      self.debug_log(ret['error'])
      if self.raise_exceptions:
        error_code = int(ret['errcode'])
        raise ui_errors.ui_error_map[error_code]()
      return False
    return True

  def __prefetch_widget(self, widget_type, user_id):
    """ Prefetch the widget for the user """
    argsdict = {"apikey":self.api_key,
               "accountid":self.account,
               "userid":user_id,
               "widget":widget_type}
    try:
      self.__url_async_post(self, self.widget_path, argsdict)
    except:
      pass

  def create_badge(self, badge_name, badge_theme, description, link):
    """ Hidden Menu APIs """
    """ Badges should be created using the console """
    argsdict = {"apikey":self.api_key,
               "accountid":self.account,
               "name":badge_name,
               "theme":badge_theme,
               "description":description,
               "imagelink":link}
    ret = None
    try:
      ret = self.__url_post(self.create_badge_path, argsdict)
    except:
      self.debug_log("Connection Error")
      if self.raise_exceptions:
        raise ui_errors.ConnectionError()
    return self.__parse_return(ret)


  def debug_log(self, message):
    if not self.debug:
      return
    if self.isGAE:
      logging.info(message) 
    else:
      print(message)


########NEW FILE########
__FILENAME__ = ui_constants
# Copyright (C) 2011, CloudCaptive
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
APP_NAME = "cloudcaptive-userinfuser"
UI_SPATH = "https://"+ APP_NAME + ".appspot.com/api/"
UI_PATH = "http://" + APP_NAME +".appspot.com/api/"
LOCAL_TEST = "http://localhost:8080/api/"
API_VER = "1"
VALID_WIDGETS = ["trophy_case", "milestones", "notifier", "points", "rank", "availablebadges", "leaderboard"]
UPDATE_USER_PATH = "updateuser"
GET_USER_DATA_PATH = "getuserdata"
AWARD_BADGE_PATH = "awardbadge"
REMOVE_BADGE_PATH = "removebadge"
AWARD_BADGE_POINTS_PATH = "awardbadgepoints"
AWARD_POINTS_PATH = "awardpoints"
WIDGET_PATH = "getwidget"
CREATE_BADGE_PATH= "createbadge"
RAISE_EXCEPTIONS = False
ANONYMOUS = "__ui__anonymous__"

########NEW FILE########
__FILENAME__ = ui_errors
# Copyright (C) 2011, CloudCaptive
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

class Error(Exception):
  """ Base Error Type """

class InternalError(Error):
  """ Internal error within API """

class BadgeDoesNotExist(Error):
  """ The given badge id does not exist """

class UserDoesNotExist(Error):
  """ The given user id does not exist """

class ConnectionError(Error):
  """ Unable to make a connection to UI service """

class BadConfiguration(Error):
  """ Unable to find API key """

class PermissionDenied(Error):
  """ Check your api key or your account email """

class UnknownWidget(Error):
  """ Check valid widgets for the correct type """

class BadArgument(Error):
  """ Check your arguments and try again """

ui_error_map = {1: PermissionDenied,
                2: BadgeDoesNotExist,
                3: UserDoesNotExist,
                4: InternalError,
                5: BadArgument}

########NEW FILE########
__FILENAME__ = action
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

class FSMAction(object):
    """ Defines the interface for all user actions. """
    
    def execute(self, context, obj):
        """ Executes some action. The return value is ignored, _except_ for the main state action.
        
        @param context The FSMContext (i.e., machine). context.get() and context.put() can be used to get data
                       from/to the context.
        @param obj: An object which the action can operate on
        
        For the main state action, the return value should be a string representing the event to be dispatched.
        Actions performed should be careful to be idempotent: because of potential retry mechanisms 
        (notably with TaskQueueFSMContext), individual execute methods may get executed more than once with 
        exactly the same context.
        """
        raise NotImplementedError()
    
class ContinuationFSMAction(FSMAction):
    """ Defines the interface for all continuation actions. """
    
    def continuation(self, context, obj, token=None):
        """ Accepts a token (may be None) and returns the next token for the continutation. 
        
        @param token: the continuation token
        @param context The FSMContext (i.e., machine). context.get() and context.put() can be used to get data
                       from/to the context.
        @param obj: An object which the action can operate on
        """
        raise NotImplementedError()
    
class DatastoreContinuationFSMAction(ContinuationFSMAction):
    """ A datastore continuation. """
    
    def continuation(self, context, obj, token=None):
        """ Accepts a token (an optional cursor) and returns the next token for the continutation. 
        The results of the query are stored on obj.results.
        """
        # the continuation query comes
        query = self.getQuery(context, obj)
        cursor = token
        if cursor:
            query.with_cursor(cursor)
        limit = self.getBatchSize(context, obj)
        
        # place results on obj.results
        obj['results'] = query.fetch(limit)
        obj.results = obj['results'] # deprecated interface
        
        # add first obj.results item on obj.result - convenient for batch size 1
        if obj['results'] and len(obj['results']) > 0:
            obj['result'] = obj['results'][0]
        else:
            obj['result'] = None
        obj.result = obj['result'] # deprecated interface
            
        if len(obj['results']) == limit:
            return query.cursor()
        
    def getQuery(self, context, obj):
        """ Returns a GqlQuery """
        raise NotImplementedError()
    
    # W0613: 78:DatastoreContinuationFSMAction.getBatchSize: Unused argument 'obj'
    def getBatchSize(self, context, obj): # pylint: disable-msg=W0613
        """ Returns a batch size, default 1. Override for different values. """
        return 1

########NEW FILE########
__FILENAME__ = config
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import os
import yaml
import logging
import json
import datetime
from fantasm import exceptions, constants, utils

TASK_ATTRIBUTES = (
    (constants.TASK_RETRY_LIMIT_ATTRIBUTE, 'taskRetryLimit', constants.DEFAULT_TASK_RETRY_LIMIT, 
     exceptions.InvalidTaskRetryLimitError),
    (constants.MIN_BACKOFF_SECONDS_ATTRIBUTE, 'minBackoffSeconds', constants.DEFAULT_MIN_BACKOFF_SECONDS, 
     exceptions.InvalidMinBackoffSecondsError),
    (constants.MAX_BACKOFF_SECONDS_ATTRIBUTE, 'maxBackoffSeconds', constants.DEFAULT_MAX_BACKOFF_SECONDS, 
     exceptions.InvalidMaxBackoffSecondsError),
    (constants.TASK_AGE_LIMIT_ATTRIBUTE, 'taskAgeLimit', constants.DEFAULT_TASK_AGE_LIMIT, 
     exceptions.InvalidTaskAgeLimitError),
    (constants.MAX_DOUBLINGS_ATTRIBUTE, 'maxDoublings', constants.DEFAULT_MAX_DOUBLINGS, 
     exceptions.InvalidMaxDoublingsError),
)

_config = None

def currentConfiguration(filename=None):
    """ Retrieves the current configuration specified by the fsm.yaml file. """
    # W0603: 32:currentConfiguration: Using the global statement
    global _config # pylint: disable-msg=W0603
    
    # always reload the config for dev_appserver to grab recent dev changes
    if _config and not constants.DEV_APPSERVER:
        return _config
        
    _config = loadYaml(filename=filename)
    return _config

# following function is borrowed from mapreduce code
# ...
# N.B. Sadly, we currently don't have and ability to determine
# application root dir at run time. We need to walk up the directory structure
# to find it.
def _findYaml(yamlNames=constants.YAML_NAMES):
    """Traverse up from current directory and find fsm.yaml file.

    Returns:
      the path of fsm.yaml file or None if not found.
    """
    directory = os.path.dirname(__file__)
    while directory:
        for yamlName in yamlNames:
            yamlPath = os.path.join(directory, yamlName)
            if os.path.exists(yamlPath):
                return yamlPath
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None

def loadYaml(filename=None, importedAlready=None):
    """ Loads the YAML and constructs a configuration from it. """
    if not filename:
        filename = _findYaml()
    if not filename:
        raise exceptions.YamlFileNotFoundError('fsm.yaml')
      
    try:
        yamlFile = open(filename)
    except IOError:
        raise exceptions.YamlFileNotFoundError(filename)
    try:
        configDict = yaml.load(yamlFile.read())
    finally:
        yamlFile.close()
        
    return Configuration(configDict, importedAlready=importedAlready)
        
class Configuration(object):
    """ An overall configuration that corresponds to a fantasm.yaml file. """
    
    def __init__(self, configDict, importedAlready=None):
        """ Constructs the configuration from a dictionary of values. """
        
        importedAlready = importedAlready or []
        
        if constants.STATE_MACHINES_ATTRIBUTE not in configDict:
            raise exceptions.StateMachinesAttributeRequiredError()
        
        self.rootUrl = configDict.get(constants.ROOT_URL_ATTRIBUTE, constants.DEFAULT_ROOT_URL)
        if not self.rootUrl.endswith('/'):
            self.rootUrl += '/'
            
        self.machines = {}
        
        # import built-in machines
        self._importBuiltInMachines(importedAlready=importedAlready)
        
        for machineDict in configDict[constants.STATE_MACHINES_ATTRIBUTE]:
            
            # bring in all the imported machines
            if machineDict.get(constants.IMPORT_ATTRIBUTE):
                self._importYaml(machineDict[constants.IMPORT_ATTRIBUTE], importedAlready=importedAlready)
                continue
                
            machine = _MachineConfig(machineDict, rootUrl=self.rootUrl)
            if machine.name in self.machines:
                raise exceptions.MachineNameNotUniqueError(machine.name)
                
            # add the states
            for stateDict in machineDict.get(constants.MACHINE_STATES_ATTRIBUTE, []):
                machine.addState(stateDict)
                
            if not machine.initialState:
                raise exceptions.MachineHasNoInitialStateError(machine.name)
            
            if not machine.finalStates:
                raise exceptions.MachineHasNoFinalStateError(machine.name)
            
            # add the transitions (2-phase parsing :( )
            for stateDict in machineDict.get(constants.MACHINE_STATES_ATTRIBUTE, []):
                for transDict in stateDict.get(constants.STATE_TRANSITIONS_ATTRIBUTE, []):
                    machine.addTransition(transDict, stateDict[constants.STATE_NAME_ATTRIBUTE])
                
            self.machines[machine.name] = machine
            
    def __addMachinesFromImportedConfig(self, importedCofig):
        """ Adds new machines from an imported configuration. """
        for machineName, machine in importedCofig.machines.items():
            if machineName in self.machines:
                raise exceptions.MachineNameNotUniqueError(machineName)
            self.machines[machineName] = machine
            
    def _importYaml(self, importYamlFile, importedAlready=None):
        """ Imports a yaml file """
        yamlFile = _findYaml(yamlNames=[importYamlFile])
        if not yamlFile:
            raise exceptions.YamlFileNotFoundError(importYamlFile)
        if yamlFile in importedAlready:
            raise exceptions.YamlFileCircularImportError(importYamlFile)
        importedAlready.append(yamlFile)
        importedConfig = loadYaml(filename=yamlFile, importedAlready=importedAlready)
        self.__addMachinesFromImportedConfig(importedConfig)
            
    BUILTIN_MACHINES = (
        'scrubber.yaml',
    )
            
    def _importBuiltInMachines(self, importedAlready=None):
        """ Imports built-in machines. """
        directory = os.path.dirname(__file__)
        for key in self.BUILTIN_MACHINES:
            yamlFile = os.path.join(directory, key)
            if yamlFile in importedAlready:
                continue
            importedAlready.append(yamlFile)
            importedConfig = loadYaml(filename=yamlFile, importedAlready=importedAlready)
            self.__addMachinesFromImportedConfig(importedConfig)

def _resolveClass(className, namespace):
    """ Given a string representation of a class, locates and returns the class object. """
    
    # some shortcuts for context_types
    shortTypes = {
        'dict': json.loads,
        'int': int,
        'float': float,
        'bool': utils.boolConverter, 
        'long': long,
        'json': json.loads,
        'datetime': lambda x: datetime.datetime.utcfromtimestamp(int(x)),
    }
    if className in shortTypes:
        return shortTypes[className] # FIXME: is this valid with methods?
    
    if '.' in className:
        fullyQualifiedClass = className
    elif namespace:
        fullyQualifiedClass = '%s.%s' % (namespace, className)
    else:
        fullyQualifiedClass = className
    
    moduleName = fullyQualifiedClass[:fullyQualifiedClass.rfind('.')]
    className = fullyQualifiedClass[fullyQualifiedClass.rfind('.')+1:]
    
    try:
        module = __import__(moduleName, globals(), locals(), [className])
    except ImportError, e:
        raise exceptions.UnknownModuleError(moduleName, e)
        
    try:
        resolvedClass = getattr(module, className)
        return resolvedClass
    except AttributeError:
        raise exceptions.UnknownClassError(moduleName, className)
    
def _resolveObject(objectName, namespace, expectedType=basestring):
    """ Given a string name/path of a object, locates and returns the value of the object. 
    
    @param objectName: ie. MODULE_LEVEL_CONSTANT, ActionName.CLASS_LEVEL_CONSTANT
    @param namespace: ie. fully.qualified.python.module 
    """
    
    if '.' in objectName:
        classOrObjectName = objectName[:objectName.rfind('.')]
        objectName2 = objectName[objectName.rfind('.')+1:]
    else:
        classOrObjectName = objectName
        
    resolvedClassOrObject = _resolveClass(classOrObjectName, namespace)
    
    if isinstance(resolvedClassOrObject, expectedType):
        return resolvedClassOrObject
    
    try:
        resolvedObject = getattr(resolvedClassOrObject, objectName2)
    except AttributeError:
        raise exceptions.UnknownObjectError(objectName)
        
    if not isinstance(resolvedObject, expectedType):
        raise exceptions.UnexpectedObjectTypeError(objectName, expectedType)
        
    return resolvedObject
        
class _MachineConfig(object):
    """ Configuration of a machine. """
    
    def __init__(self, initDict, rootUrl=None):
        """ Configures the basic attributes of a machine. States and transitions are not handled
            here, but are added by an external client.
        """
        
        # machine name
        self.name = initDict.get(constants.MACHINE_NAME_ATTRIBUTE)
        if not self.name:
            raise exceptions.MachineNameRequiredError()
        if not constants.NAME_RE.match(self.name):
            raise exceptions.InvalidMachineNameError(self.name)
        
        # check for bad attributes
        badAttributes = set()
        for attribute in initDict.iterkeys():
            if attribute not in constants.VALID_MACHINE_ATTRIBUTES:
                badAttributes.add(attribute)
        if badAttributes:
            raise exceptions.InvalidMachineAttributeError(self.name, badAttributes)
            
        # machine queue, namespace
        self.queueName = initDict.get(constants.QUEUE_NAME_ATTRIBUTE, constants.DEFAULT_QUEUE_NAME)
        self.namespace = initDict.get(constants.NAMESPACE_ATTRIBUTE)
        
        # logging
        self.logging = initDict.get(constants.MACHINE_LOGGING_NAME_ATTRIBUTE, constants.LOGGING_DEFAULT)
        if self.logging not in constants.VALID_LOGGING_VALUES:
            raise exceptions.InvalidLoggingError(self.name, self.logging)
        
        # machine task_retry_limit, min_backoff_seconds, max_backoff_seconds, task_age_limit, max_doublings
        for (constant, attribute, default, exception) in TASK_ATTRIBUTES:
            setattr(self, attribute, default)
            if constant in initDict:
                setattr(self, attribute, initDict[constant])
                try:
                    i = int(getattr(self, attribute))
                    setattr(self, attribute, i)
                except ValueError:
                    raise exception(self.name, getattr(self, attribute))

        # if both max_retries and task_retry_limit specified, raise an exception
        if constants.MAX_RETRIES_ATTRIBUTE in initDict and constants.TASK_RETRY_LIMIT_ATTRIBUTE in initDict:
            raise exceptions.MaxRetriesAndTaskRetryLimitMutuallyExclusiveError(self.name)
        
        # machine max_retries - sets taskRetryLimit internally
        if constants.MAX_RETRIES_ATTRIBUTE in initDict:
            logging.warning('max_retries is deprecated. Use task_retry_limit instead.')
            self.taskRetryLimit = initDict[constants.MAX_RETRIES_ATTRIBUTE]
            try:
                self.taskRetryLimit = int(self.taskRetryLimit)
            except ValueError:
                raise exceptions.InvalidMaxRetriesError(self.name, self.taskRetryLimit)
                        
        self.states = {}
        self.transitions = {}
        self.initialState = None
        self.finalStates = []
        
        # context types
        self.contextTypes = initDict.get(constants.MACHINE_CONTEXT_TYPES_ATTRIBUTE, {})
        for contextName, contextType in self.contextTypes.iteritems():
            self.contextTypes[contextName] = _resolveClass(contextType, self.namespace)
        
        self.rootUrl = rootUrl
        if not self.rootUrl:
            self.rootUrl = constants.DEFAULT_ROOT_URL
        elif not rootUrl.endswith('/'):
            self.rootUrl += '/'
            
    @property
    def maxRetries(self):
        """ maxRetries is a synonym for taskRetryLimit """
        return self.taskRetryLimit
        
    def addState(self, stateDict):
        """ Adds a state to this machine (using a dictionary representation). """
        state = _StateConfig(stateDict, self)
        if state.name in self.states:
            raise exceptions.StateNameNotUniqueError(self.name, state.name)
        self.states[state.name] = state
        
        if state.initial:
            if self.initialState:
                raise exceptions.MachineHasMultipleInitialStatesError(self.name)
            self.initialState = state
        if state.final:
            self.finalStates.append(state)
        
        return state
        
    def addTransition(self, transDict, fromStateName):
        """ Adds a transition to this machine (using a dictionary representation). """
        transition = _TransitionConfig(transDict, self, fromStateName)
        if transition.name in self.transitions:
            raise exceptions.TransitionNameNotUniqueError(self.name, transition.name)
        self.transitions[transition.name] = transition
        
        return transition
        
    @property
    def url(self):
        """ Returns the url for this machine. """
        return '%sfsm/%s/' % (self.rootUrl, self.name)
        
class _StateConfig(object):
    """ Configuration of a state. """
    
    # R0912:268:_StateConfig.__init__: Too many branches (22/20)
    def __init__(self, stateDict, machine): # pylint: disable-msg=R0912
        """ Builds a _StateConfig from a dictionary representation. This state is not added to the machine. """
        
        self.machineName = machine.name
        
        # state name
        self.name = stateDict.get(constants.STATE_NAME_ATTRIBUTE)
        if not self.name:
            raise exceptions.StateNameRequiredError(self.machineName)
        if not constants.NAME_RE.match(self.name):
            raise exceptions.InvalidStateNameError(self.machineName, self.name)
            
        # check for bad attributes
        badAttributes = set()
        for attribute in stateDict.iterkeys():
            if attribute not in constants.VALID_STATE_ATTRIBUTES:
                badAttributes.add(attribute)
        if badAttributes:
            raise exceptions.InvalidStateAttributeError(self.machineName, self.name, badAttributes)
        
        self.final = bool(stateDict.get(constants.STATE_FINAL_ATTRIBUTE, False))

        # state action
        actionName = stateDict.get(constants.STATE_ACTION_ATTRIBUTE)
        if not actionName and not self.final:
            raise exceptions.StateActionRequired(self.machineName, self.name)
            
        # state namespace, initial state flag, final state flag, continuation flag
        self.namespace = stateDict.get(constants.NAMESPACE_ATTRIBUTE, machine.namespace)
        self.initial = bool(stateDict.get(constants.STATE_INITIAL_ATTRIBUTE, False))
        self.continuation = bool(stateDict.get(constants.STATE_CONTINUATION_ATTRIBUTE, False))
        
        # state fan_in
        self.fanInPeriod = stateDict.get(constants.STATE_FAN_IN_ATTRIBUTE, constants.NO_FAN_IN)
        try:
            self.fanInPeriod = int(self.fanInPeriod)
        except ValueError:
            raise exceptions.InvalidFanInError(self.machineName, self.name, self.fanInPeriod)
            
        # check that a state is not BOTH fan_in and continuation
        if self.continuation and self.fanInPeriod != constants.NO_FAN_IN:
            raise exceptions.FanInContinuationNotSupportedError(self.machineName, self.name)
        
        # state action
        if stateDict.get(constants.STATE_ACTION_ATTRIBUTE):
            self.action = _resolveClass(actionName, self.namespace)()
            if not hasattr(self.action, 'execute'):
                raise exceptions.InvalidActionInterfaceError(self.machineName, self.name)
        else:
            self.action = None
        
        if self.continuation:
            if not hasattr(self.action, 'continuation'):
                raise exceptions.InvalidContinuationInterfaceError(self.machineName, self.name)
        else:
            if hasattr(self.action, 'continuation'):
                logging.warning('State\'s action class has a continuation attribute, but the state is ' + 
                                'not marked as continuation=True. This continuation method will not be ' +
                                'executed. (Machine %s, State %s)', self.machineName, self.name)
            
        # state entry
        if stateDict.get(constants.STATE_ENTRY_ATTRIBUTE):
            self.entry = _resolveClass(stateDict[constants.STATE_ENTRY_ATTRIBUTE], self.namespace)()
            if not hasattr(self.entry, 'execute'):
                raise exceptions.InvalidEntryInterfaceError(self.machineName, self.name)
        else:
            self.entry = None
        
        # state exit
        if stateDict.get(constants.STATE_EXIT_ATTRIBUTE):
            self.exit = _resolveClass(stateDict[constants.STATE_EXIT_ATTRIBUTE], self.namespace)()
            if not hasattr(self.exit, 'execute'):
                raise exceptions.InvalidExitInterfaceError(self.machineName, self.name)
            if self.continuation:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.name,
                    'Exit actions on continuation states are not supported.'
                )
            if self.fanInPeriod != constants.NO_FAN_IN:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.name,
                    'Exit actions on fan_in states are not supported.'
                )
        else:
            self.exit = None

class _TransitionConfig(object):
    """ Configuration of a transition. """
    
    # R0912:326:_TransitionConfig.__init__: Too many branches (22/20)
    def __init__(self, transDict, machine, fromStateName): # pylint: disable-msg=R0912
        """ Builds a _TransitionConfig from a dictionary representation. 
            This transition is not added to the machine. """

        self.machineName = machine.name
        
        # check for bad attributes
        badAttributes = set()
        for attribute in transDict.iterkeys():
            if attribute not in constants.VALID_TRANS_ATTRIBUTES:
                badAttributes.add(attribute)
        if badAttributes:
            raise exceptions.InvalidTransitionAttributeError(self.machineName, fromStateName, badAttributes)

        # transition event
        event = transDict.get(constants.TRANS_EVENT_ATTRIBUTE)
        if not event:
            raise exceptions.TransitionEventRequiredError(machine.name, fromStateName)
        try:
            # attempt to import the value of the event
            self.event = _resolveObject(event, machine.namespace)
        except (exceptions.UnknownModuleError, exceptions.UnknownClassError, exceptions.UnknownObjectError):
            # otherwise just use the value from the yaml
            self.event = event
        if not constants.NAME_RE.match(self.event):
            raise exceptions.InvalidTransitionEventNameError(self.machineName, fromStateName, self.event)
            
        # transition name
        self.name = '%s--%s' % (fromStateName, self.event)
        if not self.name:
            raise exceptions.TransitionNameRequiredError(self.machineName)
        if not constants.NAME_RE.match(self.name):
            raise exceptions.InvalidTransitionNameError(self.machineName, self.name)

        # transition from state
        if not fromStateName:
            raise exceptions.TransitionFromRequiredError(self.machineName, self.name)
        if fromStateName not in machine.states:
            raise exceptions.TransitionUnknownFromStateError(self.machineName, self.name, fromStateName)
        self.fromState = machine.states[fromStateName]
        
        # transition to state
        toStateName = transDict.get(constants.TRANS_TO_ATTRIBUTE)
        if not toStateName:
            raise exceptions.TransitionToRequiredError(self.machineName, self.name)
        if toStateName not in machine.states:
            raise exceptions.TransitionUnknownToStateError(self.machineName, self.name, toStateName)
        self.toState = machine.states[toStateName]
        
        # transition namespace
        self.namespace = transDict.get(constants.NAMESPACE_ATTRIBUTE, machine.namespace)

        # transition task_retry_limit, min_backoff_seconds, max_backoff_seconds, task_age_limit, max_doublings
        # W0612:439:_TransitionConfig.__init__: Unused variable 'default'
        for (constant, attribute, default, exception) in TASK_ATTRIBUTES: # pylint: disable-msg=W0612
            setattr(self, attribute, getattr(machine, attribute)) # default from the machine
            if constant in transDict:
                setattr(self, attribute, transDict[constant])
                try:
                    i = int(getattr(self, attribute))
                    setattr(self, attribute, i)
                except ValueError:
                    raise exception(self.machineName, getattr(self, attribute))

        # if both max_retries and task_retry_limit specified, raise an exception
        if constants.MAX_RETRIES_ATTRIBUTE in transDict and constants.TASK_RETRY_LIMIT_ATTRIBUTE in transDict:
            raise exceptions.MaxRetriesAndTaskRetryLimitMutuallyExclusiveError(self.machineName)
            
        # transition maxRetries
        if constants.MAX_RETRIES_ATTRIBUTE in transDict:
            logging.warning('max_retries is deprecated. Use task_retry_limit instead.')
            self.taskRetryLimit = transDict[constants.MAX_RETRIES_ATTRIBUTE]
            try:
                self.taskRetryLimit = int(self.taskRetryLimit)
            except ValueError:
                raise exceptions.InvalidMaxRetriesError(self.name, self.taskRetryLimit)
            
        # transition countdown
        self.countdown = transDict.get(constants.TRANS_COUNTDOWN_ATTRIBUTE, constants.DEFAULT_COUNTDOWN)
        try:
            self.countdown = int(self.countdown)
        except ValueError:
            raise exceptions.InvalidCountdownError(self.countdown, self.machineName, self.fromState.name)
        if self.countdown and self.toState.fanInPeriod != constants.NO_FAN_IN:
            raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                'Countdown cannot be specified on a transition to a fan_in state.'
            )
            
        # transition specific queue
        self.queueName = transDict.get(constants.QUEUE_NAME_ATTRIBUTE, machine.queueName)

        # resolve the class for action, if specified
        if constants.TRANS_ACTION_ATTRIBUTE in transDict:
            self.action = _resolveClass(transDict[constants.TRANS_ACTION_ATTRIBUTE], self.namespace)()
            if self.fromState.continuation:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                    'Transition actions on transitions from continuation states are not supported.'
                )
            if self.toState.continuation:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                    'Transition actions on transitions to continuation states are not supported.'
                )
            if self.fromState.fanInPeriod != constants.NO_FAN_IN:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                    'Transition actions on transitions from fan_in states are not supported.'
                )
            if self.toState.fanInPeriod != constants.NO_FAN_IN:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                    'Transition actions on transitions to fan_in states are not supported.'
                )
        else:
            self.action = None
            
        # test for exit actions when transitions to a continuation or a fan_in
        if self.toState.continuation and self.fromState.exit:
            raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                'Exit actions on states with a transition to a continuation state are not supported.'
            )
        if self.toState.fanInPeriod != constants.NO_FAN_IN and self.fromState.exit:
            raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                'Exit actions on states with a transition to a fan_in state are not supported.'
            )

    @property
    def maxRetries(self):
        """ maxRetries is a synonym for taskRetryLimit """
        return self.taskRetryLimit

########NEW FILE########
__FILENAME__ = console
""" Views for the console. """
import webapp2
from fantasm import config

class Dashboard(webapp2.RequestHandler):
    """ The main dashboard. """
    
    def get(self):
        """ GET """
        
        self.response.out.write(self.generateDashboard())
        
        
    def generateDashboard(self):
        """ Generates the HTML for the dashboard. """
        
        currentConfig = config.currentConfiguration()
        
        s = """
<html>
<head>
  <title>Fantasm</title>
"""
        s += STYLESHEET
        s += """
</head>
<body>

<h1>Fantasm</h1>

<h4>Configured Machines</h4>

<table class='ae-table ae-table-striped' cellpadding='0' cellspacing='0'>
<thead>
  <tr>
    <th>Name</th>
    <th>Queue</th>
    <th>States</th>
    <th>Transitions</th>
    <th>Chart</th>
  </tr>
</thead>
<tbody>
"""
        even = True
        for machineKey in sorted(currentConfig.machines.keys()):
            machine = currentConfig.machines[machineKey]
            even = False if even else True
            s += """
  <tr class='%(class)s'>
    <td>%(machineName)s</td>
    <td>%(queueName)s</td>
    <td>%(numStates)d</td>
    <td>%(numTransitions)d</td>
    <td><a href='%(rootUrl)sgraphviz/%(machineName)s/'>view</a></td>
  </tr>
""" % {
    'class': 'ae-even' if even else '',
    'machineName': machine.name,
    'queueName': machine.queueName,
    'numStates': len(machine.states),
    'numTransitions': len(machine.transitions),
    'rootUrl': currentConfig.rootUrl,
}

        s += """
</tbody>
</table>

</body>
</html>
"""
        return s


STYLESHEET = """
<style>
html, body, div, h1, h2, h3, h4, h5, h6, p, img, dl, dt, dd, ol, ul, li, table, caption, tbody, tfoot, thead, tr, th, td, form, fieldset, embed, object, applet {
    border: 0px;
    margin: 0px;
    padding: 0px;
}
body {
  color: black;
  font-family: Arial, sans-serif;
  padding: 20px;
  font-size: 0.95em;
}
h4, h5, table {
    font-size: 0.95em;
}
table {
    border-collapse: separate;
}
table[cellspacing=0] {
    border-spacing: 0px 0px;
}
thead {
    border-color: inherit;
    display: table-header-group;
    vertical-align: middle;
}
tbody {
    border-color: inherit;
    display: table-row-group;
    vertical-align: middle;
}
tr {
    border-color: inherit;
    display: table-row;
    vertical-align: inherit;
}
th {
    font-weight: bold;
}
td, th {
    display: table-cell;
    vertical-align: inherit;
}
.ae-table {
    border: 1px solid #C5D7EF;
    border-collapse: collapse;
    width: 100%;
}
.ae-table thead th {
    background: #C5D7EF;
    font-weight: bold;
    text-align: left;
    vertical-align: bottom;
}
.ae-table th, .ae-table td {
    background-color: white;
    margin: 0px;
    padding: 0.35em 1em 0.25em 0.35em;
}
.ae-table td {
    border-bottom: 1px solid #C5D7EF;
    border-top: 1px solid #C5D7EF;
}
.ae-even td, .ae-even th, .ae-even-top td, .ae-even-tween td, .ae-even-bottom td, ol.ae-even {
    background-color: #E9E9E9;
    border-bottom: 1px solid #C5D7EF;
    border-top: 1px solid #C5D7EF;
}
</style>
"""

########NEW FILE########
__FILENAME__ = constants
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import os
import re
import json

# these parameters are not stored in the FSMContext, but are used to drive the fantasm task/event dispatching mechanism
STATE_PARAM = '__st__'
EVENT_PARAM = '__ev__'
INSTANCE_NAME_PARAM = '__in__'
TERMINATED_PARAM = '__tm__'
TASK_NAME_PARAM = '__tn__'
FAN_IN_RESULTS_PARAM = '__fi__'
RETRY_COUNT_PARAM = '__rc__'
FORKED_CONTEXTS_PARAM = '__fc__'
IMMEDIATE_MODE_PARAM = '__im__'
MESSAGES_PARAM = '__ms__'
NON_CONTEXT_PARAMS = (STATE_PARAM, EVENT_PARAM, INSTANCE_NAME_PARAM, TERMINATED_PARAM, TASK_NAME_PARAM,
                      FAN_IN_RESULTS_PARAM, RETRY_COUNT_PARAM, FORKED_CONTEXTS_PARAM, IMMEDIATE_MODE_PARAM,
                      MESSAGES_PARAM)


# these parameters are stored in the FSMContext, and used to drive the task naming machanism
STEPS_PARAM = '__step__' # tracks the number of steps executed in the machine so far
CONTINUATION_PARAM = '__ct__' # tracks the continuation token (for continuation states)
GEN_PARAM = '__ge__' # used to uniquify the machine instance names (for continuations and spawns)
INDEX_PARAM = '__ix__'
WORK_INDEX_PARAM = '__wix__'
FORK_PARAM = '__fk__'
STARTED_AT_PARAM = '__sa__'

# this dict is used for casting strings in HttpRequest.GET to the appropriate type to put into FSMContext
PARAM_TYPES = {
    STEPS_PARAM : int,
    GEN_PARAM : json.loads,
    INDEX_PARAM: int,
    FORK_PARAM: int,
    STARTED_AT_PARAM: float,
}

CHARS_FOR_RANDOM = 'BDGHJKLMNPQRTVWXYZ23456789' # no vowels or things that look like vowels - profanity-free!

REQUEST_LENGTH = 30

MAX_NAME_LENGTH = 50 # we need to combine a number of names into a task name, which has a 500 char limit
NAME_PATTERN = r'^[a-zA-Z0-9-]{1,%s}$' % MAX_NAME_LENGTH
NAME_RE = re.compile(NAME_PATTERN)

HTTP_REQUEST_HEADER_PREFIX = 'X-Fantasm-'
HTTP_ENVIRON_KEY_PREFIX = 'HTTP_X_FANTASM_'

DEFAULT_TASK_RETRY_LIMIT = None
DEFAULT_MIN_BACKOFF_SECONDS = None
DEFAULT_MAX_BACKOFF_SECONDS = None
DEFAULT_TASK_AGE_LIMIT = None
DEFAULT_MAX_DOUBLINGS = None
DEFAULT_QUEUE_NAME = 'default'
DEFAULT_LOG_QUEUE_NAME = DEFAULT_QUEUE_NAME
DEFAULT_CLEANUP_QUEUE_NAME = DEFAULT_QUEUE_NAME

NO_FAN_IN = -1
DEFAULT_FAN_IN_PERIOD = NO_FAN_IN # fan_in period (in seconds)
DATASTORE_ASYNCRONOUS_INDEX_WRITE_WAIT_TIME = 5.0 # seconds

DEFAULT_COUNTDOWN = 0

YAML_NAMES = ('fsm.yaml', 'fsm.yml', 'fantasm.yaml', 'fantasm.yml')

DEFAULT_ROOT_URL = '/fantasm/' # where all the fantasm handlers are mounted
DEFAULT_LOG_URL = '/fantasm/log/'
DEFAULT_CLEANUP_URL = '/fantasm/cleanup/'

### attribute names for YAML parsing

IMPORT_ATTRIBUTE = 'import'

NAMESPACE_ATTRIBUTE = 'namespace'
QUEUE_NAME_ATTRIBUTE = 'queue'
MAX_RETRIES_ATTRIBUTE = 'max_retries' # deprecated, use task_retry_limit instead
TASK_RETRY_LIMIT_ATTRIBUTE = 'task_retry_limit'
MIN_BACKOFF_SECONDS_ATTRIBUTE = 'min_backoff_seconds'
MAX_BACKOFF_SECONDS_ATTRIBUTE = 'max_backoff_seconds'
TASK_AGE_LIMIT_ATTRIBUTE = 'task_age_limit'
MAX_DOUBLINGS_ATTRIBUTE = 'max_doublings'

ROOT_URL_ATTRIBUTE = 'root_url'
STATE_MACHINES_ATTRIBUTE = 'state_machines'
                        
MACHINE_NAME_ATTRIBUTE = 'name'
MACHINE_STATES_ATTRIBUTE = 'states'
MACHINE_TRANSITIONS_ATTRIBUTE = 'transitions'
MACHINE_CONTEXT_TYPES_ATTRIBUTE = 'context_types'
MACHINE_LOGGING_NAME_ATTRIBUTE = 'logging'
VALID_MACHINE_ATTRIBUTES = (NAMESPACE_ATTRIBUTE, MAX_RETRIES_ATTRIBUTE, TASK_RETRY_LIMIT_ATTRIBUTE,
                            MIN_BACKOFF_SECONDS_ATTRIBUTE, MAX_BACKOFF_SECONDS_ATTRIBUTE,
                            TASK_AGE_LIMIT_ATTRIBUTE, MAX_DOUBLINGS_ATTRIBUTE,
                            MACHINE_NAME_ATTRIBUTE, QUEUE_NAME_ATTRIBUTE, 
                            MACHINE_STATES_ATTRIBUTE, MACHINE_CONTEXT_TYPES_ATTRIBUTE,
                            MACHINE_LOGGING_NAME_ATTRIBUTE)
                            # MACHINE_TRANSITIONS_ATTRIBUTE is intentionally not in this list;
                            # it is used internally only

LOGGING_DEFAULT = 'default'
LOGGING_PERSISTENT = 'persistent'
VALID_LOGGING_VALUES = (LOGGING_DEFAULT, LOGGING_PERSISTENT)

STATE_NAME_ATTRIBUTE = 'name'
STATE_ENTRY_ATTRIBUTE = 'entry'
STATE_EXIT_ATTRIBUTE = 'exit'
STATE_ACTION_ATTRIBUTE = 'action'
STATE_INITIAL_ATTRIBUTE = 'initial'
STATE_FINAL_ATTRIBUTE = 'final'
STATE_CONTINUATION_ATTRIBUTE = 'continuation'
STATE_FAN_IN_ATTRIBUTE = 'fan_in'
STATE_TRANSITIONS_ATTRIBUTE = 'transitions'
VALID_STATE_ATTRIBUTES = (NAMESPACE_ATTRIBUTE, STATE_NAME_ATTRIBUTE, STATE_ENTRY_ATTRIBUTE, STATE_EXIT_ATTRIBUTE,
                          STATE_ACTION_ATTRIBUTE, STATE_INITIAL_ATTRIBUTE, STATE_FINAL_ATTRIBUTE, 
                          STATE_CONTINUATION_ATTRIBUTE, STATE_FAN_IN_ATTRIBUTE, STATE_TRANSITIONS_ATTRIBUTE)
                        
TRANS_TO_ATTRIBUTE = 'to'
TRANS_EVENT_ATTRIBUTE = 'event'
TRANS_ACTION_ATTRIBUTE = 'action'
TRANS_COUNTDOWN_ATTRIBUTE = 'countdown'
VALID_TRANS_ATTRIBUTES = (NAMESPACE_ATTRIBUTE, MAX_RETRIES_ATTRIBUTE, TASK_RETRY_LIMIT_ATTRIBUTE,
                          MIN_BACKOFF_SECONDS_ATTRIBUTE, MAX_BACKOFF_SECONDS_ATTRIBUTE,
                          TASK_AGE_LIMIT_ATTRIBUTE, MAX_DOUBLINGS_ATTRIBUTE,
                          TRANS_TO_ATTRIBUTE, TRANS_EVENT_ATTRIBUTE, TRANS_ACTION_ATTRIBUTE,
                          TRANS_COUNTDOWN_ATTRIBUTE, QUEUE_NAME_ATTRIBUTE)

DEV_APPSERVER = 'SERVER_SOFTWARE' in os.environ and os.environ['SERVER_SOFTWARE'].find('Development') >= 0

########NEW FILE########
__FILENAME__ = exceptions
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from fantasm import constants

class FSMRuntimeError(Exception):
    """ The parent class of all Fantasm runtime errors. """
    pass
    
class UnknownMachineError(FSMRuntimeError):
    """ A machine could not be found. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Cannot find machine "%s".' % machineName
        super(UnknownMachineError, self).__init__(message)

class UnknownStateError(FSMRuntimeError):
    """ A state could not be found  """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = 'State "%s" is unknown. (Machine %s)' % (stateName, machineName)
        super(UnknownStateError, self).__init__(message)
    
class UnknownEventError(FSMRuntimeError):
    """ An event and the transition bound to it could not be found. """
    def __init__(self, event, machineName, stateName):
        """ Initialize exception """
        message = 'Cannot find transition for event "%s". (Machine %s, State %s)' % (event, machineName, stateName)
        super(UnknownEventError, self).__init__(message)
        
class InvalidEventNameRuntimeError(FSMRuntimeError):
    """ Event returned from dispatch is invalid (and would cause problems with task name restrictions). """
    def __init__(self, event, machineName, stateName, instanceName):
        """ Initialize exception """
        message = 'Event "%r" returned by state is invalid. It must be a string and match pattern "%s". ' \
                  '(Machine %s, State %s, Instance %s)' % \
                  (event, constants.NAME_PATTERN, machineName, stateName, instanceName)
        super(InvalidEventNameRuntimeError, self).__init__(message)
        
class InvalidFinalEventRuntimeError(FSMRuntimeError):
    """ Event returned when a final state action returns an event. """
    def __init__(self, event, machineName, stateName, instanceName):
        """ Initialize exception """
        message = 'Event "%r" returned by final state is invalid. ' \
                  '(Machine %s, State %s, Instance %s)' % \
                  (event, machineName, stateName, instanceName)
        super(InvalidFinalEventRuntimeError, self).__init__(message)
        
class FanInWriteLockFailureRuntimeError(FSMRuntimeError):
    """ Exception when fan-in writers are unable to acquire a lock. """
    def __init__(self, event, machineName, stateName, instanceName):
        """ Initialize exception """
        message = 'Event "%r" unable to to be fanned-in due to write lock failure. ' \
                  '(Machine %s, State %s, Instance %s)' % \
                  (event, machineName, stateName, instanceName)
        super(FanInWriteLockFailureRuntimeError, self).__init__(message)
        
class FanInReadLockFailureRuntimeError(FSMRuntimeError):
    """ Exception when fan-in readers are unable to acquire a lock. """
    def __init__(self, event, machineName, stateName, instanceName):
        """ Initialize exception """
        message = 'Event "%r" unable to to be fanned-in due to read lock failure. ' \
                  '(Machine %s, State %s, Instance %s)' % \
                  (event, machineName, stateName, instanceName)
        super(FanInReadLockFailureRuntimeError, self).__init__(message)
        
class RequiredServicesUnavailableRuntimeError(FSMRuntimeError):
    """ Some of the required API services are not available. """
    def __init__(self, unavailableServices):
        """ Initialize exception """
        message = 'The following services will not be available in the %d seconds: %s. This task will be retried.' % \
                  (constants.REQUEST_LENGTH, unavailableServices)
        super(RequiredServicesUnavailableRuntimeError, self).__init__(message)
        
class ConfigurationError(Exception):
    """ Parent class for all Fantasm configuration errors. """
    pass
    
class YamlFileNotFoundError(ConfigurationError):
    """ The Yaml file could not be found. """
    def __init__(self, filename):
        """ Initialize exception """
        message = 'Yaml configuration file "%s" not found.' % filename
        super(YamlFileNotFoundError, self).__init__(message)
        
class YamlFileCircularImportError(ConfigurationError):
    """ The Yaml is involved in a circular import. """
    def __init__(self, filename):
        """ Initialize exception """
        message = 'Yaml configuration file "%s" involved in a circular import.' % filename
        super(YamlFileCircularImportError, self).__init__(message)
    
class StateMachinesAttributeRequiredError(ConfigurationError):
    """ The YAML file requires a 'state_machines' attribute. """
    def __init__(self):
        """ Initialize exception """
        message = '"%s" is required attribute of yaml file.' % constants.STATE_MACHINES_ATTRIBUTE
        super(StateMachinesAttributeRequiredError, self).__init__(message)

class MachineNameRequiredError(ConfigurationError):
    """ Each machine requires a name. """
    def __init__(self):
        """ Initialize exception """
        message = '"%s" is required attribute of machine.' % constants.MACHINE_NAME_ATTRIBUTE
        super(MachineNameRequiredError, self).__init__(message)
        
class InvalidQueueNameError(ConfigurationError):
    """ The queue name was not valid. """
    def __init__(self, queueName, machineName):
        """ Initialize exception """
        message = 'Queue name "%s" must exist in queue.yaml. (Machine %s)' % (queueName, machineName)
        super(InvalidQueueNameError, self).__init__(message)

class InvalidMachineNameError(ConfigurationError):
    """ The machine name was not valid. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine name must match pattern "%s". (Machine %s)' % (constants.NAME_PATTERN, machineName)
        super(InvalidMachineNameError, self).__init__(message)

class MachineNameNotUniqueError(ConfigurationError):
    """ Each machine in a YAML file must have a unique name. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine names must be unique. (Machine %s)' % machineName
        super(MachineNameNotUniqueError, self).__init__(message)
        
class MachineHasMultipleInitialStatesError(ConfigurationError):
    """ Each machine must have exactly one initial state. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine has multiple initial states, but only one is allowed. (Machine %s)' % machineName
        super(MachineHasMultipleInitialStatesError, self).__init__(message)
        
class MachineHasNoInitialStateError(ConfigurationError):
    """ Each machine must have exactly one initial state. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine has no initial state, exactly one is required. (Machine %s)' % machineName
        super(MachineHasNoInitialStateError, self).__init__(message)
        
class MachineHasNoFinalStateError(ConfigurationError):
    """ Each machine must have at least one final state. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine has no final states, but at least one is required. (Machine %s)' % machineName
        super(MachineHasNoFinalStateError, self).__init__(message)

class StateNameRequiredError(ConfigurationError):
    """ Each state requires a name. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = '"%s" is required attribute of state. (Machine %s)' % (constants.STATE_NAME_ATTRIBUTE, machineName)
        super(StateNameRequiredError, self).__init__(message)

class InvalidStateNameError(ConfigurationError):
    """ The state name was not valid. """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = 'State name must match pattern "%s". (Machine %s, State %s)' % \
                  (constants.NAME_PATTERN, machineName, stateName)
        super(InvalidStateNameError, self).__init__(message)

class StateNameNotUniqueError(ConfigurationError):
    """ Each state within a machine must have a unique name. """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = 'State names within a machine must be unique. (Machine %s, State %s)' % \
                  (machineName, stateName)
        super(StateNameNotUniqueError, self).__init__(message)

class StateActionRequired(ConfigurationError):
    """ Each state requires an action. """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = '"%s" is required attribute of state. (Machine %s, State %s)' % \
                  (constants.STATE_ACTION_ATTRIBUTE, machineName, stateName)
        super(StateActionRequired, self).__init__(message)

class UnknownModuleError(ConfigurationError):
    """ When resolving actions, the module was not found. """
    def __init__(self, moduleName, importError):
        """ Initialize exception """
        message = 'Module "%s" cannot be imported due to "%s".' % (moduleName, importError)
        super(UnknownModuleError, self).__init__(message)

class UnknownClassError(ConfigurationError):
    """ When resolving actions, the class was not found. """
    def __init__(self, moduleName, className):
        """ Initialize exception """
        message = 'Class "%s" was not found in module "%s".' % (className, moduleName)
        super(UnknownClassError, self).__init__(message)
        
class UnknownObjectError(ConfigurationError):
    """ When resolving actions, the object was not found. """
    def __init__(self, objectName):
        """ Initialize exception """
        message = 'Object "%s" was not found.' % (objectName)
        super(UnknownObjectError, self).__init__(message)
        
class UnexpectedObjectTypeError(ConfigurationError):
    """ When resolving actions, the object was not found. """
    def __init__(self, objectName, expectedType):
        """ Initialize exception """
        message = 'Object "%s" is not of type "%s".' % (objectName, expectedType)
        super(UnexpectedObjectTypeError, self).__init__(message)
        
class InvalidMaxRetriesError(ConfigurationError):
    """ max_retries must be a positive integer. """
    def __init__(self, machineName, maxRetries):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.MAX_RETRIES_ATTRIBUTE, maxRetries, machineName)
        super(InvalidMaxRetriesError, self).__init__(message)

class InvalidTaskRetryLimitError(ConfigurationError):
    """ task_retry_limit must be a positive integer. """
    def __init__(self, machineName, taskRetryLimit):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.TASK_RETRY_LIMIT_ATTRIBUTE, taskRetryLimit, machineName)
        super(InvalidTaskRetryLimitError, self).__init__(message)

class InvalidMinBackoffSecondsError(ConfigurationError):
    """ min_backoff_seconds must be a positive integer. """
    def __init__(self, machineName, minBackoffSeconds):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.MIN_BACKOFF_SECONDS_ATTRIBUTE, minBackoffSeconds, machineName)
        super(InvalidMinBackoffSecondsError, self).__init__(message)
        
class InvalidMaxBackoffSecondsError(ConfigurationError):
    """ max_backoff_seconds must be a positive integer. """
    def __init__(self, machineName, maxBackoffSeconds):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.MAX_BACKOFF_SECONDS_ATTRIBUTE, maxBackoffSeconds, machineName)
        super(InvalidMaxBackoffSecondsError, self).__init__(message)
        
class InvalidTaskAgeLimitError(ConfigurationError):
    """ task_age_limit must be a positive integer. """
    def __init__(self, machineName, taskAgeLimit):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.TASK_AGE_LIMIT_ATTRIBUTE, taskAgeLimit, machineName)
        super(InvalidTaskAgeLimitError, self).__init__(message)
        
class InvalidMaxDoublingsError(ConfigurationError):
    """ max_doublings must be a positive integer. """
    def __init__(self, machineName, maxDoublings):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.MAX_DOUBLINGS_ATTRIBUTE, maxDoublings, machineName)
        super(InvalidMaxDoublingsError, self).__init__(message)
        
class MaxRetriesAndTaskRetryLimitMutuallyExclusiveError(ConfigurationError):
    """ max_retries and task_retry_limit cannot both be specified on a machine. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'max_retries and task_retry_limit cannot both be specified on a machine. (Machine %s)' % \
                  machineName
        super(MaxRetriesAndTaskRetryLimitMutuallyExclusiveError, self).__init__(message)
        
class InvalidLoggingError(ConfigurationError):
    """ The logging value was not valid. """
    def __init__(self, machineName, loggingValue):
        """ Initialize exception """
        message = 'logging attribute "%s" is invalid (must be one of "%s"). (Machine %s)' % \
                  (loggingValue, constants.VALID_LOGGING_VALUES, machineName)
        super(InvalidLoggingError, self).__init__(message)

class TransitionNameRequiredError(ConfigurationError):
    """ Each transition requires a name. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = '"%s" is required attribute of transition. (Machine %s)' % \
                  (constants.TRANS_NAME_ATTRIBUTE, machineName)
        super(TransitionNameRequiredError, self).__init__(message)

class InvalidTransitionNameError(ConfigurationError):
    """ The transition name was invalid. """
    def __init__(self, machineName, transitionName):
        """ Initialize exception """
        message = 'Transition name must match pattern "%s". (Machine %s, Transition %s)' % \
                  (constants.NAME_PATTERN, machineName, transitionName)
        super(InvalidTransitionNameError, self).__init__(message)

class TransitionNameNotUniqueError(ConfigurationError):
    """ Each transition within a machine must have a unique name. """
    def __init__(self, machineName, transitionName):
        """ Initialize exception """
        message = 'Transition names within a machine must be unique. (Machine %s, Transition %s)' % \
                  (machineName, transitionName)
        super(TransitionNameNotUniqueError, self).__init__(message)

class InvalidTransitionEventNameError(ConfigurationError):
    """ The transition's event name was invalid. """
    def __init__(self, machineName, fromStateName, eventName):
        """ Initialize exception """
        message = 'Transition event name must match pattern "%s". (Machine %s, State %s, Event %s)' % \
                  (constants.NAME_PATTERN, machineName, fromStateName, eventName)
        super(InvalidTransitionEventNameError, self).__init__(message)

class TransitionUnknownToStateError(ConfigurationError):
    """ Each transition must specify a to state. """
    def __init__(self, machineName, transitionName, toState):
        """ Initialize exception """
        message = 'Transition to state is undefined. (Machine %s, Transition %s, To %s)' % \
                  (machineName, transitionName, toState)
        super(TransitionUnknownToStateError, self).__init__(message)

class TransitionToRequiredError(ConfigurationError):
    """ The specified to state is unknown. """
    def __init__(self, machineName, transitionName):
        """ Initialize exception """
        message = '"%s" is required attribute of transition. (Machine %s, Transition %s)' % \
                  (constants.TRANS_TO_ATTRIBUTE, machineName, transitionName)
        super(TransitionToRequiredError, self).__init__(message)

class TransitionEventRequiredError(ConfigurationError):
    """ Each transition requires an event to be bound to. """
    def __init__(self, machineName, fromStateName):
        """ Initialize exception """
        message = '"%s" is required attribute of transition. (Machine %s, State %s)' % \
                  (constants.TRANS_EVENT_ATTRIBUTE, machineName, fromStateName)
        super(TransitionEventRequiredError, self).__init__(message)
        
class InvalidCountdownError(ConfigurationError):
    """ Countdown must be a positive integer. """
    def __init__(self, countdown, machineName, fromStateName):
        """ Initialize exception """
        message = 'Countdown "%s" must be a positive integer. (Machine %s, State %s)' % \
                  (countdown, machineName, fromStateName)
        super(InvalidCountdownError, self).__init__(message)

class InvalidMachineAttributeError(ConfigurationError):
    """ Unknown machine attributes were found. """
    def __init__(self, machineName, badAttributes):
        """ Initialize exception """
        message = 'The following are invalid attributes a machine: %s. (Machine %s)' % \
                  (badAttributes, machineName)
        super(InvalidMachineAttributeError, self).__init__(message)

class InvalidStateAttributeError(ConfigurationError):
    """ Unknown state attributes were found. """
    def __init__(self, machineName, stateName, badAttributes):
        """ Initialize exception """
        message = 'The following are invalid attributes a state: %s. (Machine %s, State %s)' % \
                  (badAttributes, machineName, stateName)
        super(InvalidStateAttributeError, self).__init__(message)

class InvalidTransitionAttributeError(ConfigurationError):
    """ Unknown transition attributes were found. """
    def __init__(self, machineName, fromStateName, badAttributes):
        """ Initialize exception """
        message = 'The following are invalid attributes a transition: %s. (Machine %s, State %s)' % \
                  (badAttributes, machineName, fromStateName)
        super(InvalidTransitionAttributeError, self).__init__(message)

class InvalidInterfaceError(ConfigurationError):
    """ Interface errors. """
    pass

class InvalidContinuationInterfaceError(InvalidInterfaceError):
    """ The specified state was denoted as a continuation, but it does not have a continuation method. """
    def __init__(self, machineName, stateName):
        message = 'The state was specified as continuation=True, but the action class does not have a ' + \
                  'continuation() method. (Machine %s, State %s)' % (machineName, stateName)
        super(InvalidContinuationInterfaceError, self).__init__(message)

class InvalidActionInterfaceError(InvalidInterfaceError):
    """ The specified state's action class does not have an execute() method. """
    def __init__(self, machineName, stateName):
        message = 'The state\'s action class does not have an execute() method. (Machine %s, State %s)' % \
                  (machineName, stateName)
        super(InvalidActionInterfaceError, self).__init__(message)

class InvalidEntryInterfaceError(InvalidInterfaceError):
    """ The specified state's entry class does not have an execute() method. """
    def __init__(self, machineName, stateName):
        message = 'The state\'s entry class does not have an execute() method. (Machine %s, State %s)' % \
                  (machineName, stateName)
        super(InvalidEntryInterfaceError, self).__init__(message)

class InvalidExitInterfaceError(InvalidInterfaceError):
    """ The specified state's exit class does not have an execute() method. """
    def __init__(self, machineName, stateName):
        message = 'The state\'s exit class does not have an execute() method. (Machine %s, State %s)' % \
                  (machineName, stateName)
        super(InvalidExitInterfaceError, self).__init__(message)

class InvalidFanInError(ConfigurationError):
    """ fan_in must be a positive integer. """
    def __init__(self, machineName, stateName, fanInPeriod):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s, State %s)' % \
                  (constants.STATE_FAN_IN_ATTRIBUTE, fanInPeriod, machineName, stateName)
        super(InvalidFanInError, self).__init__(message)

class FanInContinuationNotSupportedError(ConfigurationError):
    """ Cannot have fan_in and continuation on the same state, because it hurts our head at the moment. """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = '%s and %s are not supported on the same state. Maybe some day... (Machine %s, State %s)' % \
                  (constants.STATE_CONTINUATION_ATTRIBUTE, constants.STATE_FAN_IN_ATTRIBUTE,
                   machineName, stateName)
        super(FanInContinuationNotSupportedError, self).__init__(message)

class UnsupportedConfigurationError(ConfigurationError):
    """ Some exit and transition actions are not allowed near fan_in and continuation. At least not at the moment. """
    def __init__(self, machineName, stateName, message):
        """ Initialize exception """
        message = '%s (Machine %s, State %s)' % (message, machineName, stateName)
        super(UnsupportedConfigurationError, self).__init__(message)
########NEW FILE########
__FILENAME__ = fsm
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.



The FSM implementation is inspired by the paper:

[1] J. van Gurp, J. Bosch, "On the Implementation of Finite State Machines", in Proceedings of the 3rd Annual IASTED
    International Conference Software Engineering and Applications,IASTED/Acta Press, Anaheim, CA, pp. 172-178, 1999.
    (www.jillesvangurp.com/static/fsm-sea99.pdf)

The Fan-out / Fan-in implementation is modeled after the presentation:
    
[2] B. Slatkin, "Building high-throughput data pipelines with Google App Engine", Google IO 2010.
    http://code.google.com/events/io/2010/sessions/high-throughput-data-pipelines-appengine.html
"""

import datetime
import random
import copy
import time
import json
from google.appengine.api.taskqueue.taskqueue import Task, TaskAlreadyExistsError, TombstonedTaskError, \
                                                     TaskRetryOptions
from google.appengine.ext import db
from google.appengine.api import memcache
from fantasm import constants, config
from fantasm.log import Logger
from fantasm.state import State
from fantasm.transition import Transition
from fantasm.exceptions import UnknownEventError, UnknownStateError, UnknownMachineError
from fantasm.models import _FantasmFanIn, _FantasmInstance
from fantasm import models
from fantasm.utils import knuthHash
from fantasm.lock import ReadWriteLock, RunOnceSemaphore

class FSM(object):
    """ An FSMContext creation factory. This is primarily responsible for translating machine
    configuration information (config.currentConfiguration()) into singleton States and Transitions as per [1]
    """
    
    PSEUDO_INIT = 'pseudo-init'
    PSEUDO_FINAL = 'pseudo-final'
    
    _CURRENT_CONFIG = None
    _MACHINES = None
    _PSEUDO_INITS = None
    _PSEUDO_FINALS = None
    
    def __init__(self, currentConfig=None):
        """ Constructor which either initializes the module/class-level cache, or simply uses it 
        
        @param currentConfig: a config._Configuration instance (dependency injection). if None, 
            then the factory uses config.currentConfiguration()
        """
        currentConfig = currentConfig or config.currentConfiguration()
        
        # if the FSM is not using the currentConfig (.yaml was edited etc.)
        if not (FSM._CURRENT_CONFIG is currentConfig):
            self._init(currentConfig=currentConfig)
            FSM._CURRENT_CONFIG = self.config
            FSM._MACHINES = self.machines
            FSM._PSEUDO_INITS = self.pseudoInits
            FSM._PSEUDO_FINALS = self.pseudoFinals
            
        # otherwise simply use the cached currentConfig etc.
        else:
            self.config = FSM._CURRENT_CONFIG
            self.machines = FSM._MACHINES
            self.pseudoInits = FSM._PSEUDO_INITS
            self.pseudoFinals = FSM._PSEUDO_FINALS
    
    def _init(self, currentConfig=None):
        """ Constructs a group of singleton States and Transitions from the machineConfig 
        
        @param currentConfig: a config._Configuration instance (dependency injection). if None, 
            then the factory uses config.currentConfiguration()
        """
        import logging
        logging.info("Initializing FSM factory.")
        
        self.config = currentConfig or config.currentConfiguration()
        self.machines = {}
        self.pseudoInits, self.pseudoFinals = {}, {}
        for machineConfig in self.config.machines.values():
            self.machines[machineConfig.name] = {constants.MACHINE_STATES_ATTRIBUTE: {}, 
                                                 constants.MACHINE_TRANSITIONS_ATTRIBUTE: {}}
            machine = self.machines[machineConfig.name]
            
            # create a pseudo-init state for each machine that transitions to the initialState
            pseudoInit = State(FSM.PSEUDO_INIT, None, None, None)
            self.pseudoInits[machineConfig.name] = pseudoInit
            self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE][FSM.PSEUDO_INIT] = pseudoInit
            
            # create a pseudo-final state for each machine that transitions from the finalState(s)
            pseudoFinal = State(FSM.PSEUDO_FINAL, None, None, None, isFinalState=True)
            self.pseudoFinals[machineConfig.name] = pseudoFinal
            self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE][FSM.PSEUDO_FINAL] = pseudoFinal
            
            for stateConfig in machineConfig.states.values():
                state = self._getState(machineConfig, stateConfig)
                
                # add the transition from pseudo-init to initialState
                if state.isInitialState:
                    transition = Transition(FSM.PSEUDO_INIT, state, 
                                            retryOptions = self._buildRetryOptions(machineConfig),
                                            queueName=machineConfig.queueName)
                    self.pseudoInits[machineConfig.name].addTransition(transition, FSM.PSEUDO_INIT)
                    
                # add the transition from finalState to pseudo-final
                if state.isFinalState:
                    transition = Transition(FSM.PSEUDO_FINAL, pseudoFinal,
                                            retryOptions = self._buildRetryOptions(machineConfig),
                                            queueName=machineConfig.queueName)
                    state.addTransition(transition, FSM.PSEUDO_FINAL)
                    
                machine[constants.MACHINE_STATES_ATTRIBUTE][stateConfig.name] = state
                
            for transitionConfig in machineConfig.transitions.values():
                source = machine[constants.MACHINE_STATES_ATTRIBUTE][transitionConfig.fromState.name]
                transition = self._getTransition(machineConfig, transitionConfig)
                machine[constants.MACHINE_TRANSITIONS_ATTRIBUTE][transitionConfig.name] = transition
                event = transitionConfig.event
                source.addTransition(transition, event)
                
    def _buildRetryOptions(self, obj):
        """ Builds a TaskRetryOptions object. """
        return TaskRetryOptions(
            task_retry_limit = obj.taskRetryLimit,
            min_backoff_seconds = obj.minBackoffSeconds,
            max_backoff_seconds = obj.maxBackoffSeconds,
            task_age_limit = obj.taskAgeLimit,
            max_doublings = obj.maxDoublings)
                
    def _getState(self, machineConfig, stateConfig):
        """ Returns a State instance based on the machineConfig/stateConfig 
        
        @param machineConfig: a config._MachineConfig instance
        @param stateConfig: a config._StateConfig instance  
        @return: a State instance which is a singleton wrt. the FSM instance
        """
        
        if machineConfig.name in self.machines and \
           stateConfig.name in self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE]:
            return self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE][stateConfig.name]
        
        name = stateConfig.name
        entryAction = stateConfig.entry
        doAction = stateConfig.action
        exitAction = stateConfig.exit
        isInitialState = stateConfig.initial
        isFinalState = stateConfig.final
        isContinuation = stateConfig.continuation
        fanInPeriod = stateConfig.fanInPeriod
        
        return State(name, 
                     entryAction, 
                     doAction, 
                     exitAction, 
                     machineName=machineConfig.name,
                     isInitialState=isInitialState,
                     isFinalState=isFinalState,
                     isContinuation=isContinuation,
                     fanInPeriod=fanInPeriod)
            
    def _getTransition(self, machineConfig, transitionConfig):
        """ Returns a Transition instance based on the machineConfig/transitionConfig 
        
        @param machineConfig: a config._MachineConfig instance
        @param transitionConfig: a config._TransitionConfig instance  
        @return: a Transition instance which is a singleton wrt. the FSM instance
        """
        if machineConfig.name in self.machines and \
           transitionConfig.name in self.machines[machineConfig.name][constants.MACHINE_TRANSITIONS_ATTRIBUTE]:
            return self.machines[machineConfig.name][constants.MACHINE_TRANSITIONS_ATTRIBUTE][transitionConfig.name]
        
        target = self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE][transitionConfig.toState.name]
        retryOptions = self._buildRetryOptions(transitionConfig)
        countdown = transitionConfig.countdown
        queueName = transitionConfig.queueName
        
        return Transition(transitionConfig.name, target, action=transitionConfig.action,
                          countdown=countdown, retryOptions=retryOptions, queueName=queueName)
        
    def createFSMInstance(self, machineName, currentStateName=None, instanceName=None, data=None, method='GET',
                          obj=None, headers=None):
        """ Creates an FSMContext instance with non-initialized data 
        
        @param machineName: the name of FSMContext to instantiate, as defined in fsm.yaml 
        @param currentStateName: the name of the state to place the FSMContext into
        @param instanceName: the name of the current instance
        @param data: a dict or FSMContext
        @param method: 'GET' or 'POST'
        @param obj: an object that the FSMContext can operate on
        @param headers: a dict of X-Fantasm request headers to pass along in Tasks 
        @raise UnknownMachineError: if machineName is unknown
        @raise UnknownStateError: is currentState name is not None and unknown in machine with name machineName
        @return: an FSMContext instance
        """
        
        try:
            machineConfig = self.config.machines[machineName]
        except KeyError:
            raise UnknownMachineError(machineName)
        
        initialState = self.machines[machineName][constants.MACHINE_STATES_ATTRIBUTE][machineConfig.initialState.name]
        
        try:
            currentState = self.pseudoInits[machineName]
            if currentStateName:
                currentState = self.machines[machineName][constants.MACHINE_STATES_ATTRIBUTE][currentStateName]
        except KeyError:
            raise UnknownStateError(machineName, currentStateName)
                
        retryOptions = self._buildRetryOptions(machineConfig)
        url = machineConfig.url
        queueName = machineConfig.queueName
        
        return FSMContext(initialState, currentState=currentState, 
                          machineName=machineName, instanceName=instanceName,
                          retryOptions=retryOptions, url=url, queueName=queueName,
                          data=data, contextTypes=machineConfig.contextTypes,
                          method=method,
                          persistentLogging=(machineConfig.logging == constants.LOGGING_PERSISTENT),
                          obj=obj,
                          headers=headers)

class FSMContext(dict):
    """ A finite state machine context instance. """
    
    def __init__(self, initialState, currentState=None, machineName=None, instanceName=None,
                 retryOptions=None, url=None, queueName=None, data=None, contextTypes=None,
                 method='GET', persistentLogging=False, obj=None, headers=None):
        """ Constructor
        
        @param initialState: a State instance 
        @param currentState: a State instance
        @param machineName: the name of the fsm
        @param instanceName: the instance name of the fsm
        @param retryOptions: the TaskRetryOptions for the machine
        @param url: the url of the fsm  
        @param queueName: the name of the appengine task queue 
        @param headers: a dict of X-Fantasm request headers to pass along in Tasks 
        @param persistentLogging: if True, use persistent _FantasmLog model
        @param obj: an object that the FSMContext can operate on  
        """
        assert queueName
        
        super(FSMContext, self).__init__(data or {})
        self.initialState = initialState
        self.currentState = currentState
        self.currentAction = None
        if currentState:
            self.currentAction = currentState.exitAction 
        self.machineName = machineName
        self.instanceName = instanceName or self._generateUniqueInstanceName()
        self.queueName = queueName
        self.retryOptions = retryOptions
        self.url = url
        self.method = method
        self.startingEvent = None
        self.startingState = None
        self.contextTypes = constants.PARAM_TYPES.copy()
        if contextTypes:
            self.contextTypes.update(contextTypes)
        self.logger = Logger(self, obj=obj, persistentLogging=persistentLogging)
        self.__obj = obj
        self.headers = headers
        
        # the following is monkey-patched from handler.py for 'immediate mode'
        from google.appengine.api.taskqueue.taskqueue import Queue
        self.Queue = Queue # pylint: disable-msg=C0103
        
    def _generateUniqueInstanceName(self):
        """ Generates a unique instance name for this machine. 
        
        @return: a FSMContext instanceName that is (pretty darn likely to be) unique
        """
        utcnow = datetime.datetime.utcnow()
        dateStr = utcnow.strftime('%Y%m%d%H%M%S')
        randomStr = ''.join(random.sample(constants.CHARS_FOR_RANDOM, 6))
        return '%s-%s-%s' % (self.machineName, dateStr, randomStr)
        
    def putTypedValue(self, key, value):
        """ Sets a value on context[key], but casts the value according to self.contextTypes. """

        # cast the value to the appropriate type TODO: should this be in FSMContext?
        cast = self.contextTypes[key]
        kwargs = {}
        if cast is json.loads:
            kwargs = {'object_hook': models.decode}
        if isinstance(value, list):
            value = [cast(v, **kwargs) for v in value]
        else:
            value = cast(value, **kwargs)

        # update the context
        self[key] = value
        
    def generateInitializationTask(self, countdown=0, taskName=None):
        """ Generates a task for initializing the machine. """
        assert self.currentState.name == FSM.PSEUDO_INIT
        
        url = self.buildUrl(self.currentState, FSM.PSEUDO_INIT)
        params = self.buildParams(self.currentState, FSM.PSEUDO_INIT)
        taskName = taskName or self.getTaskName(FSM.PSEUDO_INIT)
        transition = self.currentState.getTransition(FSM.PSEUDO_INIT)
        task = Task(name=taskName, 
                    method=self.method, 
                    url=url, 
                    params=params, 
                    countdown=countdown, 
                    headers=self.headers, 
                    retry_options=transition.retryOptions)
        return task
    
    def fork(self, data=None):
        """ Forks the FSMContext. 
        
        When an FSMContext is forked, an identical copy of the finite state machine is generated
        that will have the same event dispatched to it as the machine that called .fork(). The data
        parameter is useful for allowing each forked instance to operate on a different bit of data.
        
        @param data: an option mapping of data to apply to the forked FSMContext 
        """
        obj = self.__obj
        if obj.get(constants.FORKED_CONTEXTS_PARAM) is None:
            obj[constants.FORKED_CONTEXTS_PARAM] = []
        forkedContexts = obj.get(constants.FORKED_CONTEXTS_PARAM)
        data = copy.copy(data) or {}
        data[constants.FORK_PARAM] = len(forkedContexts)
        forkedContexts.append(self.clone(data=data))
    
    def spawn(self, machineName, contexts, countdown=0, method='POST', 
              _currentConfig=None):
        """ Spawns new machines.
        
        @param machineName the machine to spawn
        @param contexts a list of contexts (dictionaries) to spawn the new machine(s) with; multiple contexts will spawn
                        multiple machines
        @param countdown the countdown (in seconds) to wait before spawning machines
        @param method the method ('GET' or 'POST') to invoke the machine with (default: POST)
        
        @param _currentConfig test injection for configuration
        """
        # using the current task name as a root to startStateMachine will make this idempotent
        taskName = self.__obj[constants.TASK_NAME_PARAM]
        startStateMachine(machineName, contexts, taskName=taskName, method=method, countdown=countdown, 
                          _currentConfig=_currentConfig, headers=self.headers)
    
    def initialize(self):
        """ Initializes the FSMContext. Queues a Task (so that we can benefit from auto-retry) to dispatch
        an event and take the machine from 'pseudo-init' into the state machine's initial state, as 
        defined in the fsm.yaml file.
        
        @param data: a dict of initial key, value pairs to stuff into the FSMContext
        @return: an event string to dispatch to the FSMContext to put it into the initialState 
        """
        self[constants.STEPS_PARAM] = 0
        task = self.generateInitializationTask()
        self.Queue(name=self.queueName).add(task)
        _FantasmInstance(key_name=self.instanceName, instanceName=self.instanceName).put()
        
        return FSM.PSEUDO_INIT
        
    def dispatch(self, event, obj):
        """ The main entry point to move the machine according to an event. 
        
        @param event: a string event to dispatch to the FSMContext
        @param obj: an object that the FSMContext can operate on  
        @return: an event string to dispatch to the FSMContext
        """
        
        self.__obj = self.__obj or obj # hold the obj object for use during this context

        # store the starting state and event for the handleEvent() method
        self.startingState = self.currentState
        self.startingEvent = event

        nextEvent = None
        try:
            nextEvent = self.currentState.dispatch(self, event, obj)
            
            if obj.get(constants.FORKED_CONTEXTS_PARAM):
                # pylint: disable-msg=W0212
                # - accessing the protected method is fine here, since it is an instance of the same class
                tasks = []
                for context in obj[constants.FORKED_CONTEXTS_PARAM]:
                    context[constants.STEPS_PARAM] = int(context.get(constants.STEPS_PARAM, '0')) + 1
                    task = context.queueDispatch(nextEvent, queue=False)
                    if task: # fan-in magic
                        if not task.was_enqueued: # fan-in always queues
                            tasks.append(task)
                
                try:
                    if tasks:
                        transition = self.currentState.getTransition(nextEvent)
                        _queueTasks(self.Queue, transition.queueName, tasks)
                
                except (TaskAlreadyExistsError, TombstonedTaskError):
                    # unlike a similar block in self.continutation, this is well off the happy path
                    self.logger.critical(
                                     'Unable to queue fork Tasks %s as it/they already exists. (Machine %s, State %s)',
                                     [task.name for task in tasks if not task.was_enqueued],
                                     self.machineName, 
                                     self.currentState.name)
                
            if nextEvent:
                self[constants.STEPS_PARAM] = int(self.get(constants.STEPS_PARAM, '0')) + 1
                
                try:
                    self.queueDispatch(nextEvent)
                    
                except (TaskAlreadyExistsError, TombstonedTaskError):
                    # unlike a similar block in self.continutation, this is well off the happy path
                    #
                    # FIXME: when this happens, it means there was failure shortly after queuing the Task, or
                    #        possibly even with queuing the Task. when this happens there is a chance that 
                    #        two states in the machine are executing simultaneously, which is may or may not
                    #        be a good thing, depending on what each state does. gracefully handling this 
                    #        exception at least means that this state will terminate.
                    self.logger.critical('Unable to queue next Task as it already exists. (Machine %s, State %s)',
                                     self.machineName, 
                                     self.currentState.name)
                    
            else:
                # if we're not in a final state, emit a log message
                # FIXME - somehow we should avoid this message if we're in the "last" step of a continuation...
                if not self.currentState.isFinalState and not obj.get(constants.TERMINATED_PARAM):
                    self.logger.critical('Non-final state did not emit an event. Machine has terminated in an ' +
                                     'unknown state. (Machine %s, State %s)' %
                                     (self.machineName, self.currentState.name))
                # if it is a final state, then dispatch the pseudo-final event to finalize the state machine
                elif self.currentState.isFinalState and self.currentState.exitAction:
                    self[constants.STEPS_PARAM] = int(self.get(constants.STEPS_PARAM, '0')) + 1
                    self.queueDispatch(FSM.PSEUDO_FINAL)
                    
        except Exception:
            self.logger.exception("FSMContext.dispatch is handling the following exception:")
            self._handleException(event, obj)
            
        return nextEvent
    
    def continuation(self, nextToken):
        """ Performs a continuation be re-queueing an FSMContext Task with a slightly modified continuation
        token. self.startingState and self.startingEvent are used in the re-queue, so this can be seen as a
        'fork' of the current context.
        
        @param nextToken: the next continuation token
        """
        assert not self.get(constants.INDEX_PARAM) # fan-out after fan-in is not allowed
        step = str(self[constants.STEPS_PARAM]) # needs to be a str key into a json dict
        
        # make a copy and set the currentState to the startingState of this context
        context = self.clone()
        context.currentState = self.startingState
        
        # update the generation and continuation params
        gen = context.get(constants.GEN_PARAM, {})
        gen[step] = gen.get(step, 0) + 1
        context[constants.GEN_PARAM] = gen
        context[constants.CONTINUATION_PARAM] = nextToken
        
        try:
            # pylint: disable-msg=W0212
            # - accessing the protected method is fine here, since it is an instance of the same class
            transition = self.startingState.getTransition(self.startingEvent)
            context._queueDispatchNormal(self.startingEvent, queue=True, queueName=transition.queueName)
            
        except (TaskAlreadyExistsError, TombstonedTaskError):
            # this can happen when currentState.dispatch() previously succeeded in queueing the continuation
            # Task, but failed with the doAction.execute() call in a _previous_ execution of this Task.
            # NOTE: this prevent the dreaded "fork bomb" 
            self.logger.info('Unable to queue continuation Task as it already exists. (Machine %s, State %s)',
                          self.machineName, 
                          self.currentState.name)
    
    def queueDispatch(self, nextEvent, queue=True):
        """ Queues a .dispatch(nextEvent) call in the appengine Task queue. 
        
        @param nextEvent: a string event 
        @param queue: a boolean indicating whether or not to queue a Task, or leave it to the caller 
        @return: a taskqueue.Task instance which may or may not have been queued already
        """
        assert nextEvent is not None
        
        # self.currentState is already transitioned away from self.startingState
        transition = self.currentState.getTransition(nextEvent)
        if transition.target.isFanIn:
            task = self._queueDispatchFanIn(nextEvent, fanInPeriod=transition.target.fanInPeriod,
                                            retryOptions=transition.retryOptions,
                                            queueName=transition.queueName)
        else:
            task = self._queueDispatchNormal(nextEvent, queue=queue, countdown=transition.countdown,
                                             retryOptions=transition.retryOptions,
                                             queueName=transition.queueName)
            
        return task
        
    def _queueDispatchNormal(self, nextEvent, queue=True, countdown=0, retryOptions=None, queueName=None):
        """ Queues a call to .dispatch(nextEvent) in the appengine Task queue. 
        
        @param nextEvent: a string event 
        @param queue: a boolean indicating whether or not to queue a Task, or leave it to the caller 
        @param countdown: the number of seconds to countdown before the queued task fires
        @param retryOptions: the RetryOptions for the task
        @param queueName: the queue name to Queue into 
        @return: a taskqueue.Task instance which may or may not have been queued already
        """
        assert nextEvent is not None
        assert queueName
        
        url = self.buildUrl(self.currentState, nextEvent)
        params = self.buildParams(self.currentState, nextEvent)
        taskName = self.getTaskName(nextEvent)
        
        task = Task(name=taskName, method=self.method, url=url, params=params, countdown=countdown,
                    retry_options=retryOptions, headers=self.headers)
        if queue:
            self.Queue(name=queueName).add(task)
        
        return task
    
    def _queueDispatchFanIn(self, nextEvent, fanInPeriod=0, retryOptions=None, queueName=None):
        """ Queues a call to .dispatch(nextEvent) in the task queue, or saves the context to the 
        datastore for processing by the queued .dispatch(nextEvent)
        
        @param nextEvent: a string event 
        @param fanInPeriod: the period of time between fan in Tasks 
        @param queueName: the queue name to Queue into 
        @return: a taskqueue.Task instance which may or may not have been queued already
        """
        assert nextEvent is not None
        assert not self.get(constants.INDEX_PARAM) # fan-in after fan-in is not allowed
        assert queueName
        
        # we pop this off here because we do not want the fan-out/continuation param as part of the
        # task name, otherwise we loose the fan-in - each fan-in gets one work unit.
        self.pop(constants.GEN_PARAM, None)
        fork = self.pop(constants.FORK_PARAM, None)
        
        taskNameBase = self.getTaskName(nextEvent, fanIn=True)
        rwlock = ReadWriteLock(taskNameBase, self)
        index = rwlock.currentIndex()
            
        # (***)
        #
        # grab the lock - memcache.incr()
        # 
        # on Task retry, multiple incr() calls are possible. possible ways to handle:
        #
        # 1. release the lock in a 'finally' clause, but then risk missing a work
        #    package because acquiring the read lock will succeed even though the
        #    work package was not written yet.
        #
        # 2. allow the lock to get too high. the fan-in logic attempts to wait for 
        #    work packages across multiple-retry attempts, so this seems like the 
        #    best option. we basically trade a bit of latency in fan-in for reliability.
        #    
        rwlock.acquireWriteLock(index, nextEvent=nextEvent)
        
        # insert the work package, which is simply a serialized FSMContext
        workIndex = '%s-%d' % (taskNameBase, knuthHash(index))
        
        # on retry, we want to ensure we get the same work index for this task
        actualTaskName = self.__obj[constants.TASK_NAME_PARAM]
        indexKeyName = 'workIndex-' + '-'.join([str(i) for i in [actualTaskName, fork] if i]) or None
        semaphore = RunOnceSemaphore(indexKeyName, self)
        
        # check if the workIndex changed during retry
        semaphoreWritten = False
        if self.__obj[constants.RETRY_COUNT_PARAM] > 0:
            # see comment (A) in self._queueDispatchFanIn(...)
            time.sleep(constants.DATASTORE_ASYNCRONOUS_INDEX_WRITE_WAIT_TIME)
            payload = semaphore.readRunOnceSemaphore(payload=workIndex, transactional=False)
            if payload:
                semaphoreWritten = True
                if payload != workIndex:
                    self.logger.info("Work index changed from '%s' to '%s' on retry.", payload, workIndex)
                    workIndex = payload
                
        # write down two models, one actual work package, one idempotency package
        keyName = '-'.join([str(i) for i in [actualTaskName, fork] if i]) or None
        work = _FantasmFanIn(context=self, workIndex=workIndex, key_name=keyName)
        
        # close enough to idempotent, but could still write only one of the entities
        # FIXME: could be made faster using a bulk put, but this interface is cleaner
        if not semaphoreWritten:
            semaphore.writeRunOnceSemaphore(payload=workIndex, transactional=False)
        
        # put the work item
        db.put(work)
        
        # (A) now the datastore is asynchronously writing the indices, so the work package may
        #     not show up in a query for a period of time. there is a corresponding time.sleep()
        #     in the fan-in of self.mergeJoinDispatch(...) 
            
        # release the lock - memcache.decr()
        rwlock.releaseWriteLock(index)
            
        try:
            
            # insert a task to run in the future and process a bunch of work packages
            now = time.time()
            self[constants.INDEX_PARAM] = index
            url = self.buildUrl(self.currentState, nextEvent)
            params = self.buildParams(self.currentState, nextEvent)
            task = Task(name='%s-%d' % (taskNameBase, index),
                        method=self.method,
                        url=url,
                        params=params,
                        eta=datetime.datetime.utcfromtimestamp(now) + datetime.timedelta(seconds=fanInPeriod),
                        headers=self.headers,
                        retry_options=retryOptions)
            self.Queue(name=queueName).add(task)
            return task
        
        except (TaskAlreadyExistsError, TombstonedTaskError):
            pass # Fan-in magic
                
            
    def mergeJoinDispatch(self, event, obj):
        """ Performs a merge join on the pending fan-in dispatches.
        
        @param event: an event that is being merge joined (destination state must be a fan in) 
        @return: a list (possibly empty) of FSMContext instances
        """
        # this assertion comes from _queueDispatchFanIn - we never want fan-out info in a fan-in context
        assert not self.get(constants.GEN_PARAM)
        assert not self.get(constants.FORK_PARAM)
        
        # the work package index is stored in the url of the Task/FSMContext
        index = self.get(constants.INDEX_PARAM)
        taskNameBase = self.getTaskName(event, fanIn=True)
        
        # see comment (***) in self._queueDispatchFanIn 
        # 
        # in the case of failing to acquire a read lock (due to failed release of write lock)
        # we have decided to keep retrying
        raiseOnFail = False
        if self._getTaskRetryLimit() is not None:
            raiseOnFail = (self._getTaskRetryLimit() > self.__obj[constants.RETRY_COUNT_PARAM])
            
        rwlock = ReadWriteLock(taskNameBase, self)
        rwlock.acquireReadLock(index, raiseOnFail=raiseOnFail)
        
        # and return the FSMContexts list
        class FSMContextList(list):
            """ A list that supports .logger.info(), .logger.warning() etc.for fan-in actions """
            def __init__(self, context, contexts):
                """ setup a self.logger for fan-in actions """
                super(FSMContextList, self).__init__(contexts)
                self.logger = Logger(context)
                self.instanceName = context.instanceName
                
        # see comment (A) in self._queueDispatchFanIn(...)
        time.sleep(constants.DATASTORE_ASYNCRONOUS_INDEX_WRITE_WAIT_TIME)
                
        # the following step ensure that fan-in only ever operates one time over a list of data
        # the entity is created in State.dispatch(...) _after_ all the actions have executed
        # successfully
        workIndex = '%s-%d' % (taskNameBase, knuthHash(index))
        if obj[constants.RETRY_COUNT_PARAM] > 0:
            semaphore = RunOnceSemaphore(workIndex, self)
            if semaphore.readRunOnceSemaphore(payload=self.__obj[constants.TASK_NAME_PARAM]):
                self.logger.info("Fan-in idempotency guard for workIndex '%s', not processing any work items.", 
                                 workIndex)
                return FSMContextList(self, []) # don't operate over the data again
            
        # fetch all the work packages in the current group for processing
        query = _FantasmFanIn.all() \
                             .filter('workIndex =', workIndex) \
                             .order('__key__')
                             
        # construct a list of FSMContexts
        contexts = [self.clone(data=r.context) for r in query]
        return FSMContextList(self, contexts)
        
    def _getTaskRetryLimit(self):
        """ Method that returns the maximum number of retries for this particular dispatch 
        
        @param obj: an object that the FSMContext can operate on  
        """
        # get task_retry_limit configuration
        try:
            transition = self.startingState.getTransition(self.startingEvent)
            taskRetryLimit = transition.retryOptions.task_retry_limit
        except UnknownEventError:
            # can't find the transition, use the machine-level default
            taskRetryLimit = self.retryOptions.task_retry_limit
        return taskRetryLimit
            
    def _handleException(self, event, obj):
        """ Method for child classes to override to handle exceptions. 
        
        @param event: a string event 
        @param obj: an object that the FSMContext can operate on  
        """
        retryCount = obj.get(constants.RETRY_COUNT_PARAM, 0)
        taskRetryLimit = self._getTaskRetryLimit()
        
        if taskRetryLimit and retryCount >= taskRetryLimit:
            # need to permanently fail
            self.logger.critical('Max-requeues reached. Machine has terminated in an unknown state. ' +
                             '(Machine %s, State %s, Event %s)',
                             self.machineName, self.startingState.name, event, exc_info=True)
            # re-raise, letting App Engine TaskRetryOptions kill the task
            raise
        else:
            # re-raise the exception
            self.logger.warning('Exception occurred processing event. Task will be retried. ' +
                            '(Machine %s, State %s)',
                            self.machineName, self.startingState.name, exc_info=True)
            
            # this line really just allows unit tests to work - the request is really dead at this point
            self.currentState = self.startingState
            
            raise
    
    def buildUrl(self, state, event):
        """ Builds the taskqueue url. 
        
        @param state: the State to dispatch to
        @param event: the event to dispatch
        @return: a url that can be used to build a taskqueue.Task instance to .dispatch(event)
        """
        assert state and event
        return self.url + '%s/%s/%s/' % (state.name, 
                                         event, 
                                         state.getTransition(event).target.name)
    
    def buildParams(self, state, event):
        """ Builds the taskqueue params. 
        
        @param state: the State to dispatch to
        @param event: the event to dispatch
        @return: a dict suitable to use in constructing a url (GET) or using as params (POST)
        """
        assert state and event
        params = {constants.STATE_PARAM: state.name, 
                  constants.EVENT_PARAM: event,
                  constants.INSTANCE_NAME_PARAM: self.instanceName}
        for key, value in self.items():
            if key not in constants.NON_CONTEXT_PARAMS:
                if self.contextTypes.get(key) is json.loads:
                    value = json.dumps(value, cls=models.Encoder)
                if isinstance(value, datetime.datetime):
                    value = str(int(time.mktime(value.utctimetuple())))
                if isinstance(value, dict):
                    # FIXME: should we issue a warning that they should update fsm.yaml?
                    value = json.dumps(value, cls=models.Encoder)
                if isinstance(value, list) and len(value) == 1:
                    key = key + '[]' # used to preserve lists of length=1 - see handler.py for inverse
                params[key] = value
        return params

    def getTaskName(self, nextEvent, instanceName=None, fanIn=False):
        """ Returns a task name that is unique for a specific dispatch 
        
        @param nextEvent: the event to dispatch
        @return: a task name that can be used to build a taskqueue.Task instance to .dispatch(nextEvent)
        """
        transition = self.currentState.getTransition(nextEvent)
        parts = []
        parts.append(instanceName or self.instanceName)
        
        if self.get(constants.GEN_PARAM):
            for (step, gen) in self[constants.GEN_PARAM].items():
                parts.append('continuation-%s-%s' % (step, gen))
        if self.get(constants.FORK_PARAM):
            parts.append('fork-' + str(self[constants.FORK_PARAM]))
        # post-fan-in we need to store the workIndex in the task name to avoid duplicates, since
        # we popped the generation off during fan-in
        # FIXME: maybe not pop the generation in fan-in?
        # FIXME: maybe store this in the instanceName?
        # FIXME: i wish this was easier to get right :-)
        if (not fanIn) and self.get(constants.INDEX_PARAM):
            parts.append('work-index-' + str(self[constants.INDEX_PARAM]))
        parts.append(self.currentState.name)
        parts.append(nextEvent)
        parts.append(transition.target.name)
        parts.append('step-' + str(self[constants.STEPS_PARAM]))
        return '--'.join(parts)
    
    def clone(self, instanceName=None, data=None):
        """ Returns a copy of the FSMContext.
        
        @param instanceName: the instance name to optionally apply to the clone
        @param data: a dict/mapping of data to optionally apply (.update()) to the clone
        @return: a new FSMContext instance
        """
        context = copy.deepcopy(self)
        if instanceName:
            context.instanceName = instanceName
        if data:
            context.update(data)
        return context
    
# pylint: disable-msg=C0103
def _queueTasks(Queue, queueName, tasks):
    """
    Add a list of Tasks to the supplied Queue/queueName
    
    @param Queue: taskqueue.Queue or other object with .add() method
    @param queueName: a queue name from queue.yaml
    @param tasks: a list of taskqueue.Tasks
    
    @raise TaskAlreadyExistsError: 
    @raise TombstonedTaskError: 
    """
    
    from google.appengine.api.taskqueue.taskqueue import MAX_TASKS_PER_ADD
    taskAlreadyExists, tombstonedTask = None, None

    # queue the Tasks in groups of MAX_TASKS_PER_ADD
    i = 0
    for i in xrange(len(tasks)):
        someTasks = tasks[i * MAX_TASKS_PER_ADD : (i+1) * MAX_TASKS_PER_ADD]
        if not someTasks:
            break
        
        # queue them up, and loop back for more, even if there are failures
        try:
            Queue(name=queueName).add(someTasks)
                
        except TaskAlreadyExistsError, e:
            taskAlreadyExists = e
            
        except TombstonedTaskError, e:
            tombstonedTask = e
            
    if taskAlreadyExists:
        # pylint: disable-msg=E0702
        raise taskAlreadyExists
    
    if tombstonedTask:
        # pylint: disable-msg=E0702
        raise tombstonedTask

def startStateMachine(machineName, contexts, taskName=None, method='POST', countdown=0,
                      _currentConfig=None, headers=None):
    """ Starts a new machine(s), by simply queuing a task. 
    
    @param machineName the name of the machine in the FSM to start
    @param contexts a list of contexts to start the machine with; a machine will be started for each context
    @param taskName used for idempotency; will become the root of the task name for the actual task queued
    @param method the HTTP methld (GET/POST) to run the machine with (default 'POST')
    @param countdown the number of seconds into the future to start the machine (default 0 - immediately)
                     or a list of sumber of seconds (must be same length as contexts)
    @param headers: a dict of X-Fantasm request headers to pass along in Tasks 
    
    @param _currentConfig used for test injection (default None - use fsm.yaml definitions)
    """
    if not contexts:
        return
    if not isinstance(contexts, list):
        contexts = [contexts]
    if not isinstance(countdown, list):
        countdown = [countdown] * len(contexts)
        
    # FIXME: I shouldn't have to do this.
    for context in contexts:
        context[constants.STEPS_PARAM] = 0
        
    fsm = FSM(currentConfig=_currentConfig) # loads the FSM definition
    
    instances = [fsm.createFSMInstance(machineName, data=context, method=method, headers=headers) 
                 for context in contexts]
    
    tasks = []
    for i, instance in enumerate(instances):
        tname = None
        if taskName:
            tname = '%s--startStateMachine-%d' % (taskName, i)
        task = instance.generateInitializationTask(countdown=countdown[i], taskName=tname)
        tasks.append(task)

    queueName = instances[0].queueName # same machineName, same queues
    try:
        from google.appengine.api.taskqueue.taskqueue import Queue
        _queueTasks(Queue, queueName, tasks)
    except (TaskAlreadyExistsError, TombstonedTaskError):
        # FIXME: what happens if _some_ of the tasks were previously enqueued?
        # normal result for idempotency
        import logging
        logging.info('Unable to queue new machine %s with taskName %s as it has been previously enqueued.',
                      machineName, taskName)

########NEW FILE########
__FILENAME__ = handlers
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import webapp2
import time
import logging
import json
from google.appengine.ext import deferred, db
from google.appengine.api.capabilities import CapabilitySet
from fantasm import config, constants
from fantasm.fsm import FSM
from fantasm.utils import NoOpQueue
from fantasm.constants import NON_CONTEXT_PARAMS, STATE_PARAM, EVENT_PARAM, INSTANCE_NAME_PARAM, TASK_NAME_PARAM, \
                              RETRY_COUNT_PARAM, STARTED_AT_PARAM, IMMEDIATE_MODE_PARAM, MESSAGES_PARAM, \
                              HTTP_REQUEST_HEADER_PREFIX
from fantasm.exceptions import UnknownMachineError, RequiredServicesUnavailableRuntimeError, FSMRuntimeError
from fantasm.models import _FantasmTaskSemaphore, Encoder, _FantasmFanIn
from fantasm.lock import RunOnceSemaphore

REQUIRED_SERVICES = ('memcache', 'datastore_v3', 'taskqueue')

class TemporaryStateObject(dict):
    """ A simple object that is passed throughout a machine dispatch that can hold temporary
        in-flight data.
    """
    pass
    
def getMachineNameFromRequest(request):
    """ Returns the machine name embedded in the request.
    
    @param request: an HttpRequest
    @return: the machineName (as a string)
    """    
    path = request.path
    
    # strip off the mount-point
    currentConfig = config.currentConfiguration()
    mountPoint = currentConfig.rootUrl # e.g., '/fantasm/'
    if not path.startswith(mountPoint):
        raise FSMRuntimeError("rootUrl '%s' must match app.yaml mapping." % mountPoint)
    path = path[len(mountPoint):]
    
    # split on '/', the second item will be the machine name
    parts = path.split('/')
    return parts[1] # 0-based index

def getMachineConfig(request):
    """ Returns the machine configuration specified by a URI in a HttpReuest
    
    @param request: an HttpRequest
    @return: a config._machineConfig instance
    """ 
    
    # parse out the machine-name from the path {mount-point}/fsm/{machine-name}/startState/event/endState/
    # NOTE: /startState/event/endState/ is optional
    machineName = getMachineNameFromRequest(request)
    
    # load the configuration, lookup the machine-specific configuration
    # FIXME: sort out a module level cache for the configuration - it must be sensitive to YAML file changes
    # for developer-time experience
    currentConfig = config.currentConfiguration()
    try:
        machineConfig = currentConfig.machines[machineName]
        return machineConfig
    except KeyError:
        raise UnknownMachineError(machineName)

class FSMLogHandler(webapp2.RequestHandler):
    """ The handler used for logging """
    def post(self):
        """ Runs the serialized function """
        deferred.run(self.request.body)
        
class FSMFanInCleanupHandler(webapp2.RequestHandler):
    """ The handler used for logging """
    def post(self):
        """ Runs the serialized function """
        q = _FantasmFanIn.all().filter('workIndex =', self.request.POST[constants.WORK_INDEX_PARAM])
        db.delete(q)

class FSMGraphvizHandler(webapp2.RequestHandler):
    """ The hander to output graphviz diagram of the finite state machine. """
    def get(self):
        """ Handles the GET request. """
        from fantasm.utils import outputMachineConfig
        machineConfig = getMachineConfig(self.request)
        content = outputMachineConfig(machineConfig, skipStateNames=[self.request.GET.get('skipStateName')])
        if self.request.GET.get('type', 'png') == 'png':
            self.response.out.write(
"""
<html>
<head></head>
<body onload="javascript:document.forms.chartform.submit();">
<form id='chartform' action='http://chart.apis.google.com/chart' method='POST'>
  <input type="hidden" name="cht" value="gv:dot"  />
  <input type="hidden" name="chl" value='%(chl)s'  />
  <input type="submit" value="Generate GraphViz .png" />
</form>
</body>
""" % {'chl': content.replace('\n', ' ')})
        else:
            self.response.out.write(content)
            
_fsm = None

def getCurrentFSM():
    """ Returns the current FSM singleton. """
    # W0603: 32:currentConfiguration: Using the global statement
    global _fsm # pylint: disable-msg=W0603
    
    # always reload the FSM for dev_appserver to grab recent dev changes
    if _fsm and not constants.DEV_APPSERVER:
        return _fsm
        
    currentConfig = config.currentConfiguration()
    _fsm = FSM(currentConfig=currentConfig)
    return _fsm
    
class FSMHandler(webapp2.RequestHandler):
    """ The main worker handler, used to process queued machine events. """

    def get(self):
        """ Handles the GET request. """
        self.get_or_post(method='GET')
        
    def post(self):
        """ Handles the POST request. """
        self.get_or_post(method='POST')
        
    def initialize(self, request, response):
        """Initializes this request handler with the given Request and Response."""
        super(FSMHandler, self).initialize(request, response)
        # pylint: disable-msg=W0201
        # - this is the preferred location to initialize the handler in the webapp framework
        self.fsm = None
        
    def handle_exception(self, exception, debug_mode): # pylint: disable-msg=C0103
        """ Delegates logging to the FSMContext logger """
        self.error(500)
        logger = logging
        if self.fsm:
            logger = self.fsm.logger
        logger.exception("FSMHandler caught Exception")
        if debug_mode:
            import traceback, sys, cgi
            lines = ''.join(traceback.format_exception(*sys.exc_info()))
            self.response.clear()
            self.response.out.write('<pre>%s</pre>' % (cgi.escape(lines, quote=True)))
        
    def get_or_post(self, method='POST'):
        """ Handles the GET/POST request. 
        
        FIXME: this is getting a touch long
        """
        
        # ensure that we have our services for the next 30s (length of a single request)
        unavailable = set()
        for service in REQUIRED_SERVICES:
            if not CapabilitySet(service).is_enabled():
                unavailable.add(service)
        if unavailable:
            raise RequiredServicesUnavailableRuntimeError(unavailable)
        
        # the case of headers is inconsistent on dev_appserver and appengine
        # ie 'X-AppEngine-TaskRetryCount' vs. 'X-AppEngine-Taskretrycount'
        lowerCaseHeaders = dict([(key.lower(), value) for key, value in self.request.headers.items()])

        taskName = lowerCaseHeaders.get('x-appengine-taskname')
        retryCount = int(lowerCaseHeaders.get('x-appengine-taskretrycount', 0))
        
        # Taskqueue can invoke multiple tasks of the same name occassionally. Here, we'll use
        # a datastore transaction as a semaphore to determine if we should actually execute this or not.
        if taskName:
            semaphoreKey = '%s--%s' % (taskName, retryCount)
            semaphore = RunOnceSemaphore(semaphoreKey, None)
            if not semaphore.writeRunOnceSemaphore(payload='fantasm')[0]:
                # we can simply return here, this is a duplicate fired task
                logging.info('A duplicate task "%s" has been queued by taskqueue infrastructure. Ignoring.', taskName)
                self.response.status_code = 200
                return
            
        # pull out X-Fantasm-* headers
        headers = None
        for key, value in self.request.headers.items():
            if key.startswith(HTTP_REQUEST_HEADER_PREFIX):
                headers = headers or {}
                if ',' in value:
                    headers[key] = [v.strip() for v in value.split(',')]
                else:
                    headers[key] = value.strip()
            
        requestData = {'POST': self.request.POST, 'GET': self.request.GET}[method]
        method = requestData.get('method') or method
        
        machineName = getMachineNameFromRequest(self.request)
        
        # get the incoming instance name, if any
        instanceName = requestData.get(INSTANCE_NAME_PARAM)
        
        # get the incoming state, if any
        fsmState = requestData.get(STATE_PARAM)
        
        # get the incoming event, if any
        fsmEvent = requestData.get(EVENT_PARAM)
        
        assert (fsmState and instanceName) or True # if we have a state, we should have an instanceName
        assert (fsmState and fsmEvent) or True # if we have a state, we should have an event
        
        obj = TemporaryStateObject()
        
        # make a copy, add the data
        fsm = getCurrentFSM().createFSMInstance(machineName, 
                                                currentStateName=fsmState, 
                                                instanceName=instanceName,
                                                method=method,
                                                obj=obj,
                                                headers=headers)
        
        # in "immediate mode" we try to execute as much as possible in the current request
        # for the time being, this does not include things like fork/spawn/contuniuations/fan-in
        immediateMode = IMMEDIATE_MODE_PARAM in requestData.keys()
        if immediateMode:
            obj[IMMEDIATE_MODE_PARAM] = immediateMode
            obj[MESSAGES_PARAM] = []
            fsm.Queue = NoOpQueue # don't queue anything else
        
        # pylint: disable-msg=W0201
        # - initialized outside of ctor is ok in this case
        self.fsm = fsm # used for logging in handle_exception
        
        # pull all the data off the url and stuff into the context
        for key, value in requestData.items():
            if key in NON_CONTEXT_PARAMS:
                continue # these are special, don't put them in the data
            
            # deal with ...a=1&a=2&a=3...
            value = requestData.get(key)
            valueList = requestData.getall(key)
            if len(valueList) > 1:
                value = valueList
                
            if key.endswith('[]'):
                key = key[:-2]
                value = [value]
                
            if key in fsm.contextTypes.keys():
                fsm.putTypedValue(key, value)
            else:
                fsm[key] = value
        
        if not (fsmState or fsmEvent):
            
            # just queue up a task to run the initial state transition using retries
            fsm[STARTED_AT_PARAM] = time.time()
            
            # initialize the fsm, which returns the 'pseudo-init' event
            fsmEvent = fsm.initialize()
            
        else:
            
            # add the retry counter into the machine context from the header
            obj[RETRY_COUNT_PARAM] = retryCount
            
            # add the actual task name to the context
            obj[TASK_NAME_PARAM] = taskName
            
            # dispatch and return the next event
            fsmEvent = fsm.dispatch(fsmEvent, obj)
            
        # loop and execute until there are no more events - any exceptions
        # will make it out to the user in the response - useful for debugging
        if immediateMode:
            while fsmEvent:
                fsmEvent = fsm.dispatch(fsmEvent, obj)
            self.response.headers['Content-Type'] = 'application/json'
            data = {
                'obj' : obj,
                'context': fsm,
            }
            self.response.out.write(json.dumps(data, cls=Encoder))

########NEW FILE########
__FILENAME__ = lock
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import random
import time
import logging

from google.appengine.api import memcache
from google.appengine.ext import db

from fantasm.models import _FantasmTaskSemaphore
from fantasm import constants
from fantasm.exceptions import FanInWriteLockFailureRuntimeError
from fantasm.exceptions import FanInReadLockFailureRuntimeError

# a variety of locking mechanisms to enforce idempotency (of the framework) in the face of retries

class ReadWriteLock( object ):
    """ A read/write lock that allows
    
    1. non-blocking write (for speed of fan-out)
    2. blocking read (speed not reqd in fan-in)
    """
    
    INDEX_PARAM = 'index'
    LOCK_PARAM = 'lock'
    
    # 20 iterations * 0.25s = 5s total wait time
    BUSY_WAIT_ITERS = 20
    BUSY_WAIT_ITER_SECS = 0.250
    
    def __init__(self, taskNameBase, context, obj=None):
        """ ctor 
        
        @param taskNameBase: the key for fan-in, based on the task name of the fan-out items
        @param logger: a logging module or object
        """
        self.taskNameBase = taskNameBase
        self.context = context
        self.obj = obj
        
    def indexKey(self):
        """ Returns the lock index key """
        return ReadWriteLock.INDEX_PARAM + '-' + self.taskNameBase
    
    def lockKey(self, index):
        """ Returns the lock key """
        return self.taskNameBase + '-' + ReadWriteLock.LOCK_PARAM + '-' + str(index)
        
    def currentIndex(self):
        """ Returns the current lock index from memcache, or sets it if it is missing
        
        @return: an int, the current index
        """
        indexKey = self.indexKey()
        index = memcache.get(indexKey)
        if index is None:
            # using 'random.randint' here instead of '1' helps when the index is ejected from memcache
            # instead of restarting at the same counter, we jump (likely) far way from existing task job
            # names. 
            memcache.add(indexKey, random.randint(1, 2**32))
            index = memcache.get(indexKey)
        return index
    
    def acquireWriteLock(self, index, nextEvent=None, raiseOnFail=True):
        """ Acquires the write lock 
        
        @param index: an int, the current index
        @raise FanInWriteLockFailureRuntimeError: 
        """
        acquired = True
        lockKey = self.lockKey(index)
        writers = memcache.incr(lockKey, initial_value=2**16)
        if writers < 2**16:
            self.context.logger.error("Gave up waiting for write lock '%s'.", lockKey)
            acquired = False
            if raiseOnFail:
                # this will escape as a 500 error and the Task will be re-tried by appengine
                raise FanInWriteLockFailureRuntimeError(nextEvent, 
                                                        self.context.machineName, 
                                                        self.context.currentState.name, 
                                                        self.context.instanceName)
        return acquired
            
    def releaseWriteLock(self, index):
        """ Acquires the write lock 
        
        @param index: an int, the current index
        """
        released = True
        
        lockKey = self.lockKey(index)
        memcache.decr(lockKey)
        
        return released
    
    def acquireReadLock(self, index, nextEvent=None, raiseOnFail=False):
        """ Acquires the read lock
        
        @param index: an int, the current index
        """
        acquired = True
        
        lockKey = self.lockKey(index)
        indexKey = self.indexKey()
        
        # tell writers to use another index
        memcache.incr(indexKey)
        
        # tell writers they missed the boat
        memcache.decr(lockKey, 2**15) 
        
        # busy wait for writers
        for i in xrange(ReadWriteLock.BUSY_WAIT_ITERS):
            counter = memcache.get(lockKey)
            # counter is None --> ejected from memcache, or no writers
            # int(counter) <= 2**15 --> writers have all called memcache.decr
            if counter is None or int(counter) <= 2**15:
                break
            time.sleep(ReadWriteLock.BUSY_WAIT_ITER_SECS)
            self.context.logger.debug("Tried to acquire read lock '%s' %d times...", lockKey, i + 1)
        
        # FIXME: is there anything else that can be done? will work packages be lost? maybe queue another task
        #        to sweep up later?
        if i >= (ReadWriteLock.BUSY_WAIT_ITERS - 1): # pylint: disable-msg=W0631
            self.context.logger.critical("Gave up waiting for all fan-in work items with read lock '%s'.", lockKey)
            acquired = False
            if raiseOnFail:
                raise FanInReadLockFailureRuntimeError(nextEvent, 
                                                       self.context.machineName, 
                                                       self.context.currentState.name, 
                                                       self.context.instanceName)
        
        return acquired
    
class RunOnceSemaphore( object ):
    """ A object used to enforce run-once semantics """
    
    def __init__(self, semaphoreKey, context, obj=None):
        """ ctor 
        
        @param logger: a logging module or object
        """
        self.semaphoreKey = semaphoreKey
        if context is None:
            self.logger = logging
        else:
            self.logger = context.logger
        self.obj = obj

    def writeRunOnceSemaphore(self, payload=None, transactional=True):
        """ Writes the semaphore
        
        @return: a tuple of (bool, obj) where the first arg is True if the semaphore was created and work 
                 can continue, or False if the semaphore was already created, and the caller should take action
                 the second arg is the payload used on initial creation.
        """
        assert payload # so that something is always injected into memcache
        
        # the semaphore is stored in two places, memcache and datastore
        # we use memcache for speed and datastore for 100% reliability
        # in case of memcache ejection
        
        # check memcache
        cached = memcache.get(self.semaphoreKey)
        if cached:
            if cached != payload:
                self.logger.critical("Run-once semaphore memcache payload write error.")
            return (False, cached)
        
        # check datastore
        def txn():
            """ lock in transaction to avoid races between Tasks """
            entity = _FantasmTaskSemaphore.get_by_key_name(self.semaphoreKey)
            if not entity:
                _FantasmTaskSemaphore(key_name=self.semaphoreKey, payload=payload).put()
                memcache.set(self.semaphoreKey, payload)
                return (True, payload)
            else:
                if entity.payload != payload:
                    self.logger.critical("Run-once semaphore datastore payload write error.")
                memcache.set(self.semaphoreKey, entity.payload) # maybe reduces chance of ejection???
                return (False, entity.payload)
                
        # and return whether or not the lock was written
        if transactional:
            return db.run_in_transaction(txn)
        else:
            return txn()
    
    def readRunOnceSemaphore(self, payload=None, transactional=True):
        """ Reads the semaphore
        
        @return: True if the semaphore exists
        """
        assert payload
        
        # check memcache
        cached = memcache.get(self.semaphoreKey)
        if cached:
            if cached != payload:
                self.logger.critical("Run-once semaphore memcache payload read error.")
            return cached
        
        # check datastore
        def txn():
            """ lock in transaction to avoid races between Tasks """
            entity = _FantasmTaskSemaphore.get_by_key_name(self.semaphoreKey)
            if entity:
                if entity.payload != payload:
                    self.logger.critical("Run-once semaphore datastore payload read error.")
                return entity.payload
            
        # return whether or not the lock was read 
        if transactional:
            return db.run_in_transaction(txn)
        else:
            return txn()
    
########NEW FILE########
__FILENAME__ = log
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import logging
import datetime
import traceback
import StringIO
from google.appengine.ext import deferred
from fantasm.models import _FantasmLog
from fantasm import constants
from google.appengine.api.taskqueue import taskqueue

LOG_ERROR_MESSAGE = 'Exception constructing log message. Please adjust your usage of context.logger.'

def _log(taskName, 
         instanceName, 
         machineName, stateName, actionName, transitionName,
         level, namespace, tags, message, stack, time, 
         *args, **kwargs): # pylint: disable-msg=W0613
    """ Creates a _FantasmLog that can be used for debugging 
    
    @param instanceName:
    @param machineName:
    @param stateName:
    @param actionName:
    @param transitionName: 
    @param level:
    @param namespace: 
    @param tags: 
    @param message:
    @param time:
    @param args:
    @param kwargs:
    """
    # logging.info etc. handle this like:
    #
    # import logging
    # >>> logging.critical('%s')
    # CRITICAL:root:%s
    #
    # so we will do the same thing here
    try:
        message = message % args
    except TypeError: # TypeError: not enough arguments for format string
        pass
    
    _FantasmLog(taskName=taskName,
                instanceName=instanceName, 
                machineName=machineName,
                stateName=stateName,
                actionName=actionName,
                transitionName=transitionName,
                level=level,
                namespace=namespace,
                tags=list(set(tags)) or [],
                message=message, 
                stack=stack,
                time=time).put()

class Logger( object ):
    """ A object that allows an FSMContext to have methods debug, info etc. similar to logging.debug/info etc. """
    
    _LOGGING_MAP = {
        logging.CRITICAL: logging.critical,
        logging.ERROR: logging.error,
        logging.WARNING: logging.warning,
        logging.INFO: logging.info,
        logging.DEBUG: logging.debug
    }
    
    def __init__(self, context, obj=None, persistentLogging=False):
        """ Constructor 
        
        @param context:
        @param obj:
        @param persistentLogging:
        """
        self.context = context
        self.level = logging.DEBUG
        self.maxLevel = logging.CRITICAL
        self.tags = []
        self.persistentLogging = persistentLogging
        self.__obj = obj
        
    def getLoggingMap(self):
        """ One layer of indirection to fetch self._LOGGING_MAP (required for minimock to work) """
        return self._LOGGING_MAP
    
    def _log(self, level, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        
        @param level:
        @param message:
        @param args:
        @param kwargs:   
        
        NOTE: we are not not using deferred module to reduce dependencies, but we are re-using the helper
              functions .serialize() and .run() - see handler.py
        """
        if not (self.level <= level <= self.maxLevel):
            return
        
        namespace = kwargs.pop('namespace', None)
        tags = kwargs.pop('tags', None)
        
        self.getLoggingMap()[level](message, *args, **kwargs)
        
        if not self.persistentLogging:
            return
        
        stack = None
        if 'exc_info' in kwargs:
            f = StringIO.StringIO()
            traceback.print_exc(25, f)
            stack = f.getvalue()
            
        # this _log method requires everything to be serializable, which is not the case for the logging
        # module. if message is not a basestring, then we simply cast it to a string to allow _something_
        # to be logged in the deferred task
        if not isinstance(message, basestring):
            try:
                message = str(message)
            except Exception:
                message = LOG_ERROR_MESSAGE
                if args:
                    args = []
                logging.warning(message, exc_info=True)
                
        taskName = (self.__obj or {}).get(constants.TASK_NAME_PARAM)
                
        stateName = None
        if self.context.currentState:
            stateName = self.context.currentState.name
            
        transitionName = None
        if self.context.startingState and self.context.startingEvent:
            transitionName = self.context.startingState.getTransition(self.context.startingEvent).name
            
        actionName = None
        if self.context.currentAction:
            actionName = self.context.currentAction.__class__.__name__
            
        # in immediateMode, tack the messages onto obj so that they can be returned
        # in the http response in handler.py
        if self.__obj is not None:
            if self.__obj.get(constants.IMMEDIATE_MODE_PARAM):
                try:
                    self.__obj[constants.MESSAGES_PARAM].append(message % args)
                except TypeError:
                    self.__obj[constants.MESSAGES_PARAM].append(message)
                
        serialized = deferred.serialize(_log,
                                        taskName,
                                        self.context.instanceName,
                                        self.context.machineName,
                                        stateName,
                                        actionName,
                                        transitionName,
                                        level,
                                        namespace,
                                        (self.tags or []) + (tags or []),
                                        message,
                                        stack,
                                        datetime.datetime.now(), # FIXME: called .utcnow() instead?
                                        *args,
                                        **kwargs)
        
        try:
            task = taskqueue.Task(url=constants.DEFAULT_LOG_URL, 
                                  payload=serialized, 
                                  retry_options=taskqueue.TaskRetryOptions(task_retry_limit=20))
            # FIXME: a batch add may be more optimal, but there are quite a few more corners to deal with
            taskqueue.Queue(name=constants.DEFAULT_LOG_QUEUE_NAME).add(task)
            
        except taskqueue.TaskTooLargeError:
            logging.warning("fantasm log message too large - skipping persistent storage")
            
        except taskqueue.Error:
            logging.warning("error queuing log message Task - skipping persistent storage", exc_info=True)
        
    def setLevel(self, level):
        """ Sets the minimum logging level to log 
        
        @param level: a log level (ie. logging.CRITICAL)
        """
        self.level = level
        
    def setMaxLevel(self, maxLevel):
        """ Sets the maximum logging level to log 
        
        @param maxLevel: a max log level (ie. logging.CRITICAL)
        """
        self.maxLevel = maxLevel
        
    def debug(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.DEBUG
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.DEBUG, message, *args, **kwargs)
        
    def info(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.INFO
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.INFO, message, *args, **kwargs)
        
    def warning(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.WARNING
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.WARNING, message, *args, **kwargs)
        
    warn = warning
        
    def error(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.ERROR
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.ERROR, message, *args, **kwargs)
        
    def critical(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.CRITICAL
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.CRITICAL, message, *args, **kwargs)
        
    # pylint: disable-msg=W0613
    # - kwargs is overridden in this case, and never used
    def exception(self, message, *args, **kwargs):
        """ Logs the message + stack dump to the normal logging module and also queues a Task to create an 
        _FantasmLog at level logging.ERROR
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.ERROR, message, *args, **{'exc_info': True})
        
########NEW FILE########
__FILENAME__ = main
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.



Main module for fantasm implementation.

This module should be specified as a handler for fantasm URLs in app.yaml:

  handlers:
  - url: /fantasm/.*
    login: admin
    script: fantasm/main.py
"""
import webapp2
from fantasm import handlers, console

def createApplication():
    """Create new WSGIApplication and register all handlers.

    Returns:
        an instance of webapp2.WSGIApplication with all fantasm handlers registered.
    """
    return webapp2.WSGIApplication([
        (r"^/[^\/]+/fsm/.+",       handlers.FSMHandler),
        (r"^/[^\/]+/cleanup/",     handlers.FSMFanInCleanupHandler),
        (r"^/[^\/]+/graphviz/.+",  handlers.FSMGraphvizHandler),
        (r"^/[^\/]+/log/",         handlers.FSMLogHandler),
        (r"^/[^\/]+/?",            console.Dashboard),
    ],
    debug=True)

APP = createApplication()



########NEW FILE########
__FILENAME__ = models
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from google.appengine.ext import db
from google.appengine.api import datastore_types
import json
import datetime

def decode(dct):
    """ Special handler for db.Key/datetime.datetime decoding """
    if '__set__' in dct:
        return set(dct['key'])
    if '__db.Key__' in dct:
        return db.Key(dct['key'])
    if '__db.Model__' in dct:
        return db.Key(dct['key']) # turns into a db.Key across serialization
    if '__datetime.datetime__' in dct:
        return datetime.datetime(**dct['datetime'])
    return dct

# W0232: 30:Encoder: Class has no __init__ method
class Encoder(json.JSONEncoder): # pylint: disable-msg=W0232
    """ A JSONEncoder that handles db.Key """
    # E0202: 36:Encoder.default: An attribute inherited from JSONEncoder hide this method
    def default(self, obj): # pylint: disable-msg=E0202
        """ see json.JSONEncoder.default """
        if isinstance(obj, set):
            return {'__set__': True, 'key': list(obj)}
        if isinstance(obj, db.Key):
            return {'__db.Key__': True, 'key': str(obj)}
        if isinstance(obj, db.Model):
            return {'__db.Model__': True, 'key': str(obj.key())} # turns into a db.Key across serialization
        if isinstance(obj, datetime.datetime) and \
           obj.tzinfo is None: # only UTC datetime objects are supported
            return {'__datetime.datetime__': True, 'datetime': {'year': obj.year,
                                                                'month': obj.month,
                                                                'day': obj.day,
                                                                'hour': obj.hour,
                                                                'minute': obj.minute,
                                                                'second': obj.second,
                                                                'microsecond': obj.microsecond}}
        return json.JSONEncoder.default(self, obj)

class JSONProperty(db.Property):
    """
    From Google appengine cookbook... a Property for storing dicts in the datastore
    """
    data_type = datastore_types.Text
    
    def get_value_for_datastore(self, modelInstance):
        """ see Property.get_value_for_datastore """
        value = super(JSONProperty, self).get_value_for_datastore(modelInstance)
        return db.Text(self._deflate(value))
    
    def validate(self, value):
        """ see Property.validate """
        return self._inflate(value)
    
    def make_value_from_datastore(self, value):
        """ see Property.make_value_from_datastore """
        return self._inflate(value)
    
    def _inflate(self, value):
        """ decodes string -> dict """
        if value is None:
            return {}
        if isinstance(value, unicode) or isinstance(value, str):
            return json.loads(value, object_hook=decode)
        return value
    
    def _deflate(self, value):
        """ encodes dict -> string """
        return json.dumps(value, cls=Encoder)
    
    
class _FantasmFanIn( db.Model ):
    """ A model used to store FSMContexts for fan in """
    workIndex = db.StringProperty()
    context = JSONProperty(indexed=False)
    # FIXME: createdTime only needed for scrubbing, but indexing might be a performance hit
    #        http://ikaisays.com/2011/01/25/app-engine-datastore-tip-monotonically-increasing-values-are-bad/
    createdTime = db.DateTimeProperty(auto_now_add=True)
    
class _FantasmInstance( db.Model ):
    """ A model used to to store FSMContext instances """
    instanceName = db.StringProperty()
    # FIXME: createdTime only needed for scrubbing, but indexing might be a performance hit
    #        http://ikaisays.com/2011/01/25/app-engine-datastore-tip-monotonically-increasing-values-are-bad/
    createdTime = db.DateTimeProperty(auto_now_add=True)
    
class _FantasmLog( db.Model ):
    """ A model used to store log messages """
    taskName = db.StringProperty()
    instanceName = db.StringProperty()
    machineName = db.StringProperty()
    stateName = db.StringProperty()
    actionName = db.StringProperty()
    transitionName = db.StringProperty()
    time = db.DateTimeProperty()
    level = db.IntegerProperty()
    message = db.TextProperty()
    stack = db.TextProperty()
    tags = db.StringListProperty()

class _FantasmTaskSemaphore( db.Model ):
    """ A model that simply stores the task name so that we can guarantee only-once semantics. """
    # FIXME: createdTime only needed for scrubbing, but indexing might be a performance hit
    #        http://ikaisays.com/2011/01/25/app-engine-datastore-tip-monotonically-increasing-values-are-bad/
    createdTime = db.DateTimeProperty(auto_now_add=True)
    payload = db.StringProperty(indexed=False)

########NEW FILE########
__FILENAME__ = scrubber
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import datetime
from google.appengine.ext import db
from fantasm.action import DatastoreContinuationFSMAction
# W0611: 23: Unused import _FantasmLog
# we're importing these here so that db has a chance to see them before we query them
from fantasm.models import _FantasmInstance, _FantasmLog, _FantasmTaskSemaphore # pylint: disable-msg=W0611

# W0613: Unused argument 'obj'
# implementing interfaces
# pylint: disable-msg=W0613

class InitalizeScrubber(object):
    """ Use current time to set up task names. """
    def execute(self, context, obj):
        """ Computes the before date and adds to context. """
        age = context.pop('age', 90)
        context['before'] = datetime.datetime.utcnow() - datetime.timedelta(days=age)
        return 'next'
        
class EnumerateFantasmModels(object):
    """ Kick off a continuation for each model. """
    
    FANTASM_MODELS = (
        ('_FantasmInstance', 'createdTime'), 
        ('_FantasmLog', 'time'), 
        ('_FantasmTaskSemaphore', 'createdTime'),
        ('_FantasmFanIn', 'createdTime')
    )
    
    def continuation(self, context, obj, token=None):
        """ Continue over each model. """
        if not token:
            obj['model'] = self.FANTASM_MODELS[0][0]
            obj['dateattr'] = self.FANTASM_MODELS[0][1]
            return self.FANTASM_MODELS[1][0] if len(self.FANTASM_MODELS) > 1 else None
        else:
            # find next in list
            for i in range(0, len(self.FANTASM_MODELS)):
                if self.FANTASM_MODELS[i][0] == token:
                    obj['model'] = self.FANTASM_MODELS[i][0]
                    obj['dateattr'] = self.FANTASM_MODELS[i][1]
                    return self.FANTASM_MODELS[i+1][0] if i < len(self.FANTASM_MODELS)-1 else None
        return None # this occurs if a token passed in is not found in list - shouldn't happen
        
    def execute(self, context, obj):
        """ Pass control to next state. """
        if not 'model' in obj or not 'dateattr' in obj:
            return None
        context['model'] = obj['model']
        context['dateattr'] = obj['dateattr']
        return 'next'
        
class DeleteOldEntities(DatastoreContinuationFSMAction):
    """ Deletes entities of a given model older than a given date. """
    
    def getQuery(self, context, obj):
        """ Query for all entities before a given datetime. """
        model = context['model']
        dateattr = context['dateattr']
        before = context['before']
        query = 'SELECT __key__ FROM %s WHERE %s < :1' % (model, dateattr)
        return db.GqlQuery(query, before)
        
    def getBatchSize(self, context, obj):
        """ Batch size. """
        return 100
        
    def execute(self, context, obj):
        """ Delete the rows. """
        if obj['results']:
            db.delete(obj['results'])

########NEW FILE########
__FILENAME__ = state
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
from google.appengine.ext import db
from google.appengine.api.taskqueue.taskqueue import Task, TaskAlreadyExistsError, TombstonedTaskError

from fantasm import constants
from fantasm.transition import Transition
from fantasm.exceptions import UnknownEventError, InvalidEventNameRuntimeError
from fantasm.utils import knuthHash
from fantasm.models import _FantasmFanIn
from fantasm.lock import RunOnceSemaphore

class State(object):
    """ A state object for a machine. """
    
    def __init__(self, name, entryAction, doAction, exitAction, machineName=None, 
                 isFinalState=False, isInitialState=False, isContinuation=False, fanInPeriod=constants.NO_FAN_IN):
        """
        @param name: the name of the State instance
        @param entryAction: an FSMAction instance
        @param doAction: an FSMAction instance
        @param exitAction: an FSMAction instance
        @param machineName: the name of the machine this State is associated with 
        @param isFinalState: a boolean indicating this is a terminal state
        @param isInitialState: a boolean indicating this is a starting state
        @param isContinuation: a boolean indicating this is a continuation State 
        @param fanInPeriod: integer (seconds) representing how long these states should collect before dispatching
        """
        assert not (exitAction and isContinuation) # TODO: revisit this with jcollins, we want to get it right
        assert not (exitAction and fanInPeriod > constants.NO_FAN_IN) # TODO: revisit this with jcollins
        
        self.name = name
        self.entryAction = entryAction
        self.doAction = doAction
        self.exitAction = exitAction
        self.machineName = machineName # is this really necessary? it is only for logging.
        self.isInitialState = isInitialState
        self.isFinalState = isFinalState
        self.isContinuation = isContinuation
        self.isFanIn = fanInPeriod != constants.NO_FAN_IN
        self.fanInPeriod = fanInPeriod
        self._eventToTransition = {}
        
    def addTransition(self, transition, event):
        """ Adds a transition for an event. 
        
        @param transition: a Transition instance
        @param event: a string event that results in the associated Transition to execute  
        """
        assert isinstance(transition, Transition)
        assert isinstance(event, basestring)
        
        assert not (self.exitAction and transition.target.isContinuation) # TODO: revisit this with jcollins
        assert not (self.exitAction and transition.target.isFanIn) # TODO: revisit
        
        self._eventToTransition[event] = transition
        
    def getTransition(self, event):
        """ Gets the Transition for a given event. 
        
        @param event: a string event
        @return: a Transition instance associated with the event
        @raise an UnknownEventError if event is unknown (i.e., no transition is bound to it).
        """
        try:
            return self._eventToTransition[event]
        except KeyError:
            import logging
            logging.critical('Cannot find transition for event "%s". (Machine %s, State %s)',
                             event, self.machineName, self.name)
            raise UnknownEventError(event, self.machineName, self.name)
        
    def dispatch(self, context, event, obj):
        """ Fires the transition and executes the next States's entry, do and exit actions.
            
        @param context: an FSMContext instance
        @param event: a string event to dispatch to the State
        @param obj: an object that the Transition can operate on  
        @return: the event returned from the next state's main action.
        """
        transition = self.getTransition(event)
        
        if context.currentState.exitAction:
            try:
                context.currentAction = context.currentState.exitAction
                context.currentState.exitAction.execute(context, obj)
            except Exception:
                context.logger.error('Error processing entry action for state. (Machine %s, State %s, exitAction %s)',
                              context.machineName, 
                              context.currentState.name, 
                              context.currentState.exitAction.__class__)
                raise
        
        # join the contexts of a fan-in
        contextOrContexts = context
        if transition.target.isFanIn:
            taskNameBase = context.getTaskName(event, fanIn=True)
            contextOrContexts = context.mergeJoinDispatch(event, obj)
            if not contextOrContexts:
                context.logger.info('Fan-in resulted in 0 contexts. Terminating machine. (Machine %s, State %s)',
                             context.machineName, 
                             context.currentState.name)
                obj[constants.TERMINATED_PARAM] = True
                
        transition.execute(context, obj)
        
        if context.currentState.entryAction:
            try:
                context.currentAction = context.currentState.entryAction
                context.currentState.entryAction.execute(contextOrContexts, obj)
            except Exception:
                context.logger.error('Error processing entry action for state. (Machine %s, State %s, entryAction %s)',
                              context.machineName, 
                              context.currentState.name, 
                              context.currentState.entryAction.__class__)
                raise
            
        if context.currentState.isContinuation:
            try:
                token = context.get(constants.CONTINUATION_PARAM, None)
                nextToken = context.currentState.doAction.continuation(contextOrContexts, obj, token=token)
                if nextToken:
                    context.continuation(nextToken)
                context.pop(constants.CONTINUATION_PARAM, None) # pop this off because it is really long
                
            except Exception:
                context.logger.error('Error processing continuation for state. (Machine %s, State %s, continuation %s)',
                              context.machineName, 
                              context.currentState.name, 
                              context.currentState.doAction.__class__)
                raise
            
        # either a fan-in resulted in no contexts, or a continuation was completed
        if obj.get(constants.TERMINATED_PARAM):
            return None
            
        nextEvent = None
        if context.currentState.doAction:
            try:
                context.currentAction = context.currentState.doAction
                nextEvent = context.currentState.doAction.execute(contextOrContexts, obj)
            except Exception:
                context.logger.error('Error processing action for state. (Machine %s, State %s, Action %s)',
                              context.machineName, 
                              context.currentState.name, 
                              context.currentState.doAction.__class__)
                raise
            
        if transition.target.isFanIn:
            
            # this prevents fan-in from re-counting the data if there is an Exception
            # or DeadlineExceeded _after_ doAction.execute(...) succeeds
            index = context.get(constants.INDEX_PARAM)
            workIndex = '%s-%d' % (taskNameBase, knuthHash(index))
            semaphore = RunOnceSemaphore(workIndex, context)
            semaphore.writeRunOnceSemaphore(payload=obj[constants.TASK_NAME_PARAM])
            
            try:
                # at this point we have processed the work items, delete them
                task = Task(name=obj[constants.TASK_NAME_PARAM] + '-cleanup', 
                            url=constants.DEFAULT_CLEANUP_URL, 
                            params={constants.WORK_INDEX_PARAM: workIndex})
                context.Queue(name=constants.DEFAULT_CLEANUP_QUEUE_NAME).add(task)
                
            except (TaskAlreadyExistsError, TombstonedTaskError):
                context.logger.info("Fan-in cleanup Task already exists.")
                
            if context.get('UNITTEST_RAISE_AFTER_FAN_IN'): # only way to generate this failure
                raise Exception()
                
        if nextEvent:
            if not isinstance(nextEvent, str) or not constants.NAME_RE.match(nextEvent):
                raise InvalidEventNameRuntimeError(nextEvent, context.machineName, context.currentState.name,
                                                   context.instanceName)
            
        return nextEvent

########NEW FILE########
__FILENAME__ = transition
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

class Transition(object):
    """ A transition object for a machine. """
    
    def __init__(self, name, target, action=None, countdown=0, retryOptions=None, queueName=None):
        """ Constructor 
        
        @param name: the name of the Transition instance
        @param target: a State instance
        @param action: the optional action for a state
        @param countdown: the number of seconds to wait before firing this transition. Default 0.
        @param retryOptions: the TaskRetryOptions for this transition
        @param queueName: the name of the queue to Queue into 
        """
        assert queueName
        
        self.target = target
        self.name = name
        self.action = action
        self.countdown = countdown
        self.retryOptions = retryOptions
        self.queueName = queueName
        
    # W0613:144:Transition.execute: Unused argument 'obj'
    # args are present for a future(?) transition action
    def execute(self, context, obj): # pylint: disable-msg=W0613
        """ Moves the machine to the next state. 
        
        @param context: an FSMContext instance
        @param obj: an object that the Transition can operate on  
        """
        if self.action:
            try:
                self.action.execute(context, obj)
            except Exception:
                context.logger.error('Error processing action for transition. (Machine %s, Transition %s, Action %s)',
                              context.machineName, 
                              self.name, 
                              self.action.__class__)
                raise
        context.currentState = self.target

########NEW FILE########
__FILENAME__ = utils
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
from fantasm import constants
from google.appengine.api.taskqueue.taskqueue import Queue

class NoOpQueue( Queue ):
    """ A Queue instance that does not Queue """
    
    def add(self, task, transactional=False):
        """ see taskqueue.Queue.add """
        pass
       
def knuthHash(number):
    """A decent hash function for integers."""
    return (number * 2654435761) % 2**32

def boolConverter(boolStr):
    """ A converter that maps some common bool string to True """
    return {'1': True, 'True': True, 'true': True}.get(boolStr, False)

def outputAction(action):
    """ Outputs the name of the action 
    
    @param action: an FSMAction instance 
    """
    if action:
        return str(action.__class__.__name__).split('.')[-1]

def outputTransitionConfig(transitionConfig):
    """ Outputs a GraphViz directed graph node
    
    @param transitionConfig: a config._TransitionConfig instance
    @return: a string
    """
    label = transitionConfig.event
    if transitionConfig.action:
        label += '/ ' + outputAction(transitionConfig.action)
    return '"%(fromState)s" -> "%(toState)s" [label="%(label)s"];' % \
            {'fromState': transitionConfig.fromState.name, 
             'toState': transitionConfig.toState.name, 
             'label': label}
            
def outputStateConfig(stateConfig, colorMap=None):
    """ Outputs a GraphViz directed graph node
    
    @param stateConfig: a config._StateConfig instance
    @return: a string
    """
    colorMap = colorMap or {}
    actions = []
    if stateConfig.entry:
        actions.append('entry/ %(entry)s' % {'entry': outputAction(stateConfig.entry)})
    if stateConfig.action:
        actions.append('do/ %(do)s' % {'do': outputAction(stateConfig.action)})
    if stateConfig.exit:
        actions.append('exit/ %(exit)s' % {'exit': outputAction(stateConfig.exit)})
    label = '%(stateName)s|%(actions)s' % {'stateName': stateConfig.name, 'actions': '\\l'.join(actions)}
    if stateConfig.continuation:
        label += '|continuation = True'
    if stateConfig.fanInPeriod != constants.NO_FAN_IN:
        label += '|fan in period = %(fanin)ds' % {'fanin': stateConfig.fanInPeriod}
    shape = 'Mrecord'
    if colorMap.get(stateConfig.name):
        return '"%(stateName)s" [style=filled,fillcolor="%(fillcolor)s",shape=%(shape)s,label="{%(label)s}"];' % \
               {'stateName': stateConfig.name,
                'fillcolor': colorMap.get(stateConfig.name, 'white'),
                'shape': shape,
                'label': label}
    else:
        return '"%(stateName)s" [shape=%(shape)s,label="{%(label)s}"];' % \
               {'stateName': stateConfig.name,
                'shape': shape,
                'label': label}

def outputMachineConfig(machineConfig, colorMap=None, skipStateNames=None):
    """ Outputs a GraphViz directed graph of the state machine 
    
    @param machineConfig: a config._MachineConfig instance
    @return: a string
    """
    skipStateNames = skipStateNames or ()
    lines = []
    lines.append('digraph G {')
    lines.append('label="%(machineName)s"' % {'machineName': machineConfig.name})
    lines.append('labelloc="t"')
    lines.append('"__start__" [label="start",shape=circle,style=filled,fillcolor=black,fontcolor=white,fontsize=9];')
    lines.append('"__end__" [label="end",shape=doublecircle,style=filled,fillcolor=black,fontcolor=white,fontsize=9];')
    for stateConfig in machineConfig.states.values():
        if stateConfig.name in skipStateNames:
            continue
        lines.append(outputStateConfig(stateConfig, colorMap=colorMap))
        if stateConfig.initial:
            lines.append('"__start__" -> "%(stateName)s"' % {'stateName': stateConfig.name})
        if stateConfig.final:
            lines.append('"%(stateName)s" -> "__end__"' % {'stateName': stateConfig.name})
    for transitionConfig in machineConfig.transitions.values():
        if transitionConfig.fromState.name in skipStateNames or \
           transitionConfig.toState.name in skipStateNames:
            continue
        lines.append(outputTransitionConfig(transitionConfig))
    lines.append('}')
    return '\n'.join(lines) 
########NEW FILE########
__FILENAME__ = accinfo
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from google.appengine.api import users
from google.appengine.ext import db
from serverside import constants
from serverside.dao import accounts_dao
from serverside.entities.counter import APICountBatch
import base64
import datetime
import httplib
import logging
import os
import json 
import urllib
import webapp2

class AppsAuthToken(db.Model):
  value = db.StringProperty()
  appname = db.StringProperty()
  enabled = db.BooleanProperty()
  
def get_x_apps_token():
  aset = AppsAuthToken.all().filter('appname =', 'xapps')
  if not aset or (aset and not aset.get()):
    logging.info('Creating new xappstoken')
    token = AppsAuthToken(value='----', appname = 'xapps', enabled= False)
    token.save()
    return token
  else:
    return aset.get()

def x_app_auth_required(method):
  def auth(self, *args):
    if users.is_current_user_admin():
      method(self,*args)
      return
    
    headers = self.request.headers
    tokenr = headers.get('xapp-token')
    
    if not tokenr:
      logging.info('No xapp token provided')
      self.error(400)
      self.response.out.write('Unable to authenticate!')
      return
    
    token = get_x_apps_token()
    
    if not token:
      logging.error('No token found.. weird...')
      self.error(400)
      self.response.out.write('Unable to authenticate!')
      return
    
    if not token.enabled:
      logging.info('Token disabled')
      self.error(400)
      self.response.out.write('Unable to authenticate!')
      return
    
    if tokenr == token.value and token.enabled:
      method(self,*args)
    else:
      logging.info('Token mismatch.. ' + tokenr + ' ' + token.value)
      self.error(400)
      self.response.out.write('Unable to authenticate!')
  return auth

class SendXAppToken(webapp2.RequestHandler):
  def get(self):
    if users.is_current_user_admin():
      location = self.request.get('location')
      path = self.request.get('path')
      
      conn = httplib.HTTPSConnection(location) # <---- needs to be HTTPS!!!!
      
      params = urllib.urlencode({'xapptoken': get_x_apps_token()})
      conn.request('POST', path, params)
      
      data = conn.getresponse().read()
      
      logging.critical('Sent XAppToken to ' + location + path + ' and this is the response: ' + data)
      
      conn.close()
  
class Authenticate(webapp2.RequestHandler):
  """
  Authenticates user and password combo
  """
  @x_app_auth_required
  def post(self):
    username = self.request.get('email')
    password = self.request.get('password')
    
    logging.info("Authentication attempt from: " + username)
    
    entity = accounts_dao.authenticate_web_account(username, password)
    if not entity:
      self.error(400)

class AccountUsage(webapp2.RequestHandler):
  def get(self):
    self.post()
  """
  Returns UserInfuser API usage for user. Only username required.
  """
  @x_app_auth_required
  def post(self):
    username = self.request.get('email')
    
    accounts = None
    if not username:
      accounts = accounts_dao.get_all_accounts()
    else:
      entity = accounts_dao.get(username)
      if not entity:
        self.error(400)
        return
      accounts = []
      accounts.append(entity)
    
    alldata = {'usage':[]}
    ''' retrieve all usage information summary (just API calls) '''
    for acc in accounts:
      q = APICountBatch.all().filter("account_key =", acc.key().name())
      values = {"success": "true", "email" : acc.email}
      res = q.fetch(1000) 
      values['total'] = q.count() or 1
      monthsdict = {}
      for ii in res:
        monthyear = ii.date.strftime('%Y-%m')
        curr=monthsdict.get(monthyear)
        if not curr:
          curr = 0
        curr += int(ii.counter)
        monthsdict[monthyear] = curr
      values['months'] = monthsdict
      alldata['usage'].append(values)
    
    self.response.out.write(json.dumps(alldata))

app = webapp2.WSGIApplication([
  ('/accinfo/auth', Authenticate),
  ('/accinfo/usage', AccountUsage)], debug=constants.DEBUG)


########NEW FILE########
__FILENAME__ = account
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Server side script for ajax calls
# Gives user info and other client side info

import wsgiref.handlers
import cgi
import webapp2
from google.appengine.ext import db
from entities.users import *
from tools.xss import XssCleaner
import json

class AccountInfo(webapp2.RequestHandler):
  def get(self):
    resp = {"success":"false","error":"User not logged in"}
    resp_json = json.dumps(resp)
    self.response.out.write(resp_json)
    return


########NEW FILE########
__FILENAME__ = analytics
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from serverside.dao import accounts_dao
from serverside.dao import badges_dao
from entities.accounts import Accounts
from entities.badges import *
from entities.users import *
from entities.logs import *
from entities.counter import *
from google.appengine.ext import db
import webapp2
from serverside import constants
from serverside.session import Session
from tools.utils import account_login_required
from tools.xss import XssCleaner, XssCleaner
from serverside.fantasm.action import FSMAction, DatastoreContinuationFSMAction
from serverside.fantasm import fsm
import cgi
import logging
import os
import wsgiref.handlers
import string
import datetime
import json

def stripMilSecs(d):
  return datetime.datetime(d.year, d.month, d.day, d.hour, d.minute, d.second)

def stripHours(d):
  return datetime.datetime(d.year, d.month, d.day)

class RunAnalytics(webapp2.RequestHandler):
  def get(self):
    now = datetime.datetime.now()
    a_day_ago = now - datetime.timedelta(days=1)

    context = {}
    context['start_time'] = str(stripMilSecs(a_day_ago))
    context['end_time'] = str(stripMilSecs(now))
    fsm.startStateMachine('CountAwardedBadges', [context])
    fsm.startStateMachine('CountAwardedPoints', [context])
    fsm.startStateMachine('CountAwardedBadgePoints', [context])
    fsm.startStateMachine('CountAPICalls', [context])

VALID_ANALYTICS = ["badges", "badgepoints", "points", "apicalls"]

class GetAnalytics(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    current_session = Session().get_current_session(self)
    acc = current_session.get_account_entity()
    a_type = self.request.get("type")
    if a_type not in VALID_ANALYTICS:
      return json.dumps({'success':'false'})

    values = getattr(self, a_type + "_values")(acc)
    self.response.out.write(json.dumps(values))


  @account_login_required
  def post(self):
    current_session = Session().get_current_session(self)
    acc = current_session.get_account_entity()
    a_type = self.request.get("type")
    if a_type not in VALID_ANALYTICS:
      return json.dumps({'success':'false'})

    values = getattr(self, a_type + "_values")(acc)
    self.response.out.write(json.dumps(values))

  def badges_values(self, acc):
    q = BadgeBatch.all().filter("account_key =", acc.key().name())
    values = {"success": "true"}
    res = q.fetch(1000) 
    values['total'] = q.count() or 1
    values['entry'] = []
    values['badges'] = []
    values['numbadges'] = 0
    badges = set()
    for ii in res:
      ent = {'date':ii.date.strftime("%Y-%m-%d"),
             'count':str(ii.counter),
             'badgeid':ii.badgeid}
      values['entry'].append(ent)
      badges.add(ii.badgeid)
    else:
      ent = {'date':datetime.datetime.now().strftime("%Y-%m-%d"),
             'count':"0",
             'badgeid':"none"}
      values['entry'].append(ent)
      badges.add("none")
             
    badges = list(badges)
    #badges = badges_dao.get_all_badges_for_account(acc)
    for ii in badges:
      values['badges'].append(ii)
      values['numbadges'] += 1
    return values

  def badgepoints_values(self, acc):
    q = BadgePointsBatch.all().filter("account_key =", acc.key().name())
    values = {"success": "true"}
    res = q.fetch(1000) 
    values['total'] = q.count() or 1
    values['entry'] = []
    values['badges'] = []
    values['numbadges'] = 0
    badges = set()
    for ii in res:
      ent = {'date':ii.date.strftime("%Y-%m-%d"),
             'count':str(ii.counter),
             'badgeid':ii.badgeid}
      values['entry'].append(ent)
      badges.add(ii.badgeid) 
    else:
      ent = {'date':datetime.datetime.now().strftime("%Y-%m-%d"),
             'count':"0",
             'badgeid':"none"}
      values['entry'].append(ent)
      badges.add("none")
 
    # = badges_dao.get_all_badges_for_account(acc)
    badges = list(badges)
    for ii in badges:
      values['badges'].append(ii)
      values['numbadges'] += 1
    return values

  def points_values(self, acc):
    q = PointBatch.all().filter("account_key =", acc.key().name())
    values = {"success": "true"}
    res = q.fetch(1000) 
    values['total'] = q.count() or 1
    values['entry'] = []
    for ii in res:
      ent = {'date':ii.date.strftime("%Y-%m-%d"),
             'count':str(ii.counter)}
      values['entry'].append(ent)
    else:
      ent = {'date':datetime.datetime.now().strftime("%Y-%m-%d"),
             'count':"0"}
      values['entry'].append(ent)
    return values

  def apicalls_values(self, acc):
    q = APICountBatch.all().filter("account_key =", acc.key().name())
    values = {"success": "true"}
    res = q.fetch(1000) 
    values['total'] = q.count() or 1
    values['entry'] = []
    for ii in res:
      ent = {'date':ii.date.strftime("%Y-%m-%d"),
             'count':str(ii.counter)}
      values['entry'].append(ent)
    else:
      ent = {'date':datetime.datetime.now().strftime("%Y-%m-%d"),
             'count':"0"}
      values['entry'].append(ent)
    return values


###############################################
# Start of State Machine 
# CountAwardedBadges
###############################################
"""
Badge Award Counting State Machine
This class starts a task for each account 
"""
class AllAccountsClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    return Accounts.all()

  def execute(self, context, obj):
    if not obj['result']:
      return None
    acc = obj['result']
    if acc: 
      context['account_key'] = acc.key().name()
      return "peraccount"

"""
Second state for each account's badges to count over
"""
class PerAccountClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    account_key = context['account_key']
    account_ref = accounts_dao.get(account_key)
    return Badges.all().filter('creator =', account_ref)
 
  def execute(self, context, obj):
    if not obj['result']:
      return None
    ii = obj['result']
    context['badgeid'] = ii.theme + '-' + ii.name + '-' + ii.permissions
    return "perbadge" 

"""
Awarded Badge Counting State Machine
"""
class PerBadgeClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    start_time = datetime.datetime.strptime(context['start_time'], "%Y-%m-%d %H:%M:%S")
    end_time = datetime.datetime.strptime(context['end_time'], "%Y-%m-%d %H:%M:%S")
    return Logs.all().filter("account =", context['account_key']).filter("badgeid =", context['badgeid']).filter("event =", "notify_badge").filter("date >", start_time).filter("date <", end_time)


  def execute(self, context, obj):
    # Create a counter initialized the count to 0
    # This way we'll at least know when its a sum of 0
    # rather than having nothing to signify that it ran
    def tx():
      batch_key = context['account_key'] + '-' + \
                  context['badgeid'] + '-' + \
                  context['end_time']

      batch = BadgeBatch.get_by_key_name(batch_key)
      if not batch:
        end_time = datetime.datetime.strptime(context['end_time'], "%Y-%m-%d %H:%M:%S")
        batch = BadgeBatch(key_name=batch_key,
                       badgeid=context['badgeid'],
                       account_key=context['account_key'],
                       date=end_time)
        batch.put()
    if not obj['result']:
      return None
    db.run_in_transaction(tx) 
    return "count"
   
"""
This class spawns a task for each log.
"""
class CountAwardedBadgesClass(FSMAction):
  def execute(self, context, obj):
    """Transactionally update our batch counter"""
    batch_key = context['account_key'] + '-' + \
                context['badgeid'] + '-' + \
                context['end_time']

    def tx():
      batch = BadgeBatch.get_by_key_name(batch_key)
      if not batch:
        # For whatever reason it was not already created in previous state
        end_time = datetime.datetime.strptime(context['end_time'], "%Y-%m-%d %H:%M:%S")
        batch = BadgeBatch(key_name=batch_key,
                       badgeid=context['badgeid'],
                       account_key=context['account_key'],
                       date=end_time)
        batch.put()
      batch.counter += 1
      batch.put()
    db.run_in_transaction(tx)

###############################################
# End of State Machine 
# CountAwardedBadges
###############################################
###############################################
###############################################
# Start of State Machine 
# CountAPICallsInitState
###############################################
"""
API Call Counting State Machine
This class starts a task for each account 
"""
class APICallsAllAccountsClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    return Accounts.all()

  def execute(self, context, obj):
    if not obj['result']:
      return None
    acc = obj['result']
    if acc: 
      context['account_key'] = acc.key().name()
      return "apicallsperaccount"

"""
Second state for each account's api calls for counting
"""
class APICallsPerAccountClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    start_time = datetime.datetime.strptime(context['start_time'], 
                                            "%Y-%m-%d %H:%M:%S")
    end_time = datetime.datetime.strptime(context['end_time'], 
                                            "%Y-%m-%d %H:%M:%S")
    return Logs.all().filter("account =", context['account_key']).filter("is_api =", "yes").filter("date >", start_time).filter("date <", end_time)

  def execute(self, context, obj):
    if not obj['result']:
      return None
    batch_key = context['account_key'] + '-' + \
                context['end_time']
    def tx():
      batch = APICountBatch.get_by_key_name(batch_key)
      if not batch:
        # Initialize counter
        end_time = datetime.datetime.strptime(context['end_time'], "%Y-%m-%d %H:%M:%S")
        batch = APICountBatch(key_name=batch_key,
                       account_key=context['account_key'],
                       date=end_time)
        batch.put()
 
    db.run_in_transaction(tx)
    return "count"
   
"""
This class fans in multiple logs
There may be failures in the computation
but its meant only for a rough estimate
"""
class CountAPICallsClass(FSMAction):
  def execute(self, contexts, obj):
    """Transactionally update our batch counter"""
    allcontext = {} 
    context_account = {}
    context_datetime = {}
    batch_key = None
    if len(contexts) < 1:
      return
    for index,ii in enumerate(contexts):
      batch_key = ii['account_key'] + '-' + \
                  ii['end_time']
      if batch_key in allcontext:
        allcontext[batch_key] += 1
      else:
        allcontext[batch_key] = 1
      context_account[batch_key] = ii['account_key']
      end_time = datetime.datetime.strptime(ii['end_time'], "%Y-%m-%d %H:%M:%S")
      context_datetime[batch_key] = end_time

    def tx(batch_key, count):
      batch = APICountBatch.get_by_key_name(batch_key)
      if not batch:
        batch = APICountBatch(key_name=batch_key,
                       account_key=context_account[batch_key],
                       date=context_datetime[batch_key])
        batch.put()
      batch.counter += count
      batch.put()

    # if a failure happens while in this loop, numbers will be inflated
    for ii in allcontext:
      db.run_in_transaction(tx, ii, allcontext[ii])
###############################################
# End of State Machine 
# CountAPICallsInitState
###############################################
###############################################
###############################################
# Start of State Machine 
# CountPointsInitState
###############################################
"""
Points Counting State Machine
This class starts a task for each account 
"""
class PointsAllAccountsClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    return Accounts.all()

  def execute(self, context, obj):
    if not obj['result']:
      return None
    acc = obj['result']
    if acc: 
      context['account_key'] = acc.key().name()
      return "pointsperaccount"

"""
Second state for each account's points awarded for counting
"""
class PointsPerAccountClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    start_time = datetime.datetime.strptime(context['start_time'], 
                                            "%Y-%m-%d %H:%M:%S")
    end_time = datetime.datetime.strptime(context['end_time'], 
                                            "%Y-%m-%d %H:%M:%S")
    return Logs.all().filter("account =", context['account_key']).filter("event =", "awardpoints").filter("date >", start_time).filter("date <", end_time).filter("success", "true")

  def execute(self, context, obj):
    if not obj['result']:
      return None
    batch_key = context['account_key'] + '-' + \
                context['end_time']
    end_time = datetime.datetime.strptime(context['end_time'], "%Y-%m-%d %H:%M:%S")

    context['points'] = obj['result'].points
    if not context['points']:
      context['points'] = 0

    def tx():
      batch = PointBatch.get_by_key_name(batch_key)
      if not batch:
        # Initialize counter
        batch = PointBatch(key_name=batch_key,
                       account_key=context['account_key'],
                       date=end_time)
        batch.put()
 
    db.run_in_transaction(tx)
    return "count"
   
"""
This class fans in multiple logs
If an error occurrs during this processing it is possible to have
inflated numbers.
"""
class CountPointsClass(FSMAction):
  def execute(self, contexts, obj):
    """Transactionally update our batch counter"""
    allcontext = {} 
    context_account = {}
    context_datetime = {}
    batch_key = None
    if len(contexts) < 1:
      return
    for index,ii in enumerate(contexts):
      batch_key = ii['account_key'] + '-' + \
                  ii['end_time']
      if batch_key in allcontext:
        allcontext[batch_key] += int(ii['points'])
      else:
        allcontext[batch_key] = int(ii['points'])
      context_account[batch_key] = ii['account_key']
      end_time = datetime.datetime.strptime(ii['end_time'], "%Y-%m-%d %H:%M:%S")
      context_datetime[batch_key] = end_time

    def tx(batch_key, count):
      batch = PointBatch.get_by_key_name(batch_key)
      if not batch:
        batch = PointBatch(key_name=batch_key,
                       account_key=context_account[batch_key],
                       date=context_datetime[batch_key])
        batch.put()
      batch.counter += int(count)
      batch.put()

    # if a failure happens while in this loop, numbers will be inflated
    for ii in allcontext:
      db.run_in_transaction(tx, ii, allcontext[ii])
###############################################
# End of State Machine 
# CountAPICallsInitState
###############################################
###############################################
# Start of State Machine 
# CountAwardedBadgePoints
###############################################
"""
Badge Point Award Counting State Machine
This class starts a task for each account 
"""
class BadgePointsAllAccountsClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    return Accounts.all()

  def execute(self, context, obj):
    if not obj['result']:
      return None
    acc = obj['result']
    if acc: 
      context['account_key'] = acc.key().name()
      return "peraccount"

"""
Second state for each account's badges to count over
"""
class BadgePointsPerAccountClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    account_key = context['account_key']
    account_ref = accounts_dao.get(account_key)
    return Badges.all().filter('creator =', account_ref)
 
  def execute(self, context, obj):
    if not obj['result']:
      return None
    ii = obj['result']
    context['badgeid'] = ii.theme + '-' + ii.name + '-' + ii.permissions
    return "perbadge" 

"""
Awarded Badge Counting State Machine
"""
class PerBadgePointsClass(DatastoreContinuationFSMAction):
  def getQuery(self, context, obj):
    start_time = datetime.datetime.strptime(context['start_time'], "%Y-%m-%d %H:%M:%S")
    end_time = datetime.datetime.strptime(context['end_time'], "%Y-%m-%d %H:%M:%S")
    return Logs.all().filter("account =", context['account_key']).filter("badgeid =", context['badgeid']).filter("api =", "award_badge_points").filter("date >", start_time).filter("date <", end_time)


  def execute(self, context, obj):
    # Create a counter initialized the count to 0
    # This way we'll at least know when its a sum of 0
    # rather than having nothing to signify that it ran
    end_time = datetime.datetime.strptime(context['end_time'], "%Y-%m-%d %H:%M:%S")
    def tx():
      batch_key = context['account_key'] + '-' + \
                  context['badgeid'] + '-' + \
                  context['end_time']

      batch = BadgePointsBatch.get_by_key_name(batch_key)
      if not batch:
        batch = BadgePointsBatch(key_name=batch_key,
                       badgeid=context['badgeid'],
                       account_key=context['account_key'],
                       date=end_time)
        batch.put()
    if not obj['result']:
      return None
    db.run_in_transaction(tx) 
    if obj['result'].success == "true":
      context['points'] = str(obj['result'].points)
      return "count"
    else:
      return None
   
"""
This class spawns a task for each log.
"""
class CountAwardedBadgePointsClass(FSMAction):
  def execute(self, context, obj):
    """Transactionally update our batch counter"""
    batch_key = context['account_key'] + '-' + \
                context['badgeid'] + '-' + \
                context['end_time']

    def tx():
      batch = BadgePointsBatch.get_by_key_name(batch_key)
      if not batch:
        end_time = datetime.datetime.strptime(context['end_time'], "%Y-%m-%d %H:%M:%S")
        batch = BadgePointsBatch(key_name=batch_key,
                       badgeid=context['badgeid'],
                       account_key=context['account_key'],
                       date=end_time)
        batch.put()
      batch.counter += int(context['points'])
      batch.put()
    db.run_in_transaction(tx)



########NEW FILE########
__FILENAME__ = api
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
""" Author: Navraj Chohan
    Description: The server side API implementation of UI.
"""
from __future__ import with_statement
  
import os
import wsgiref.handlers
import cgi
import locale
import webapp2
from serverside.entities.users import Users
from serverside.entities.accounts import Accounts
from serverside.entities.badges import Badges
from serverside.entities.badges import BadgeImage
from serverside.entities.badges import BadgeInstance
from serverside.entities.widgets import Leaderboard
from serverside.entities.widgets import Rank
from serverside.entities.widgets import Points
from serverside.entities.widgets import Notifier
from serverside.entities.widgets import TrophyCase
from serverside.entities.widgets import Milestones
from serverside.tools.utils import format_integer
from serverside.dao import badges_dao
from serverside.dao import accounts_dao
from serverside.dao import users_dao
from serverside.dao import widgets_dao
from serverside import environment
from serverside import notifier
from serverside import logs
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.ext.webapp import template
from google.appengine.api import channel
from google.appengine.api import files
from google.appengine.ext import blobstore
from serverside import constants 
from serverside.tools.xss import XssCleaner
import json

import hashlib
import time
import datetime
import logging
import traceback
DEBUG = constants.DEBUG
DISABLE_LOGGING = False
DISABLE_TIMING = True
"""
How keys are created for each type of entity:
User: sha1(account_id + '-' + user_id)
Badge: creatoremail + '-' badgename + '-' + badgetheme + '-' + permissions
BadgeInstance: user_id + '-' + badge_key
The dao interface should have a create key function for each
"""
def debug(msg):
  if DISABLE_LOGGING:
    return 
  if DEBUG:
    frame = traceback.extract_stack(limit=1)[0]
    filename, line_number, name, text = frame
    logging.info('DEBUG, File "%s", line %d, in %s: %s' % (filename, line_number, name, msg))
  
def error(msg):
  if DISABLE_LOGGING:
    return 
  frame = traceback.extract_stack(limit=1)[0]
  filename, line_number, name, text = frame
  logging.error('ERROR, File "%s", line %d, in %s: %s' % (filename, line_number, name, msg))

def timing(start):
  if DISABLE_TIMING:
    return 
  end = time.time()
  frame = traceback.extract_stack(limit=1)[0]
  filename, line_number, name, text = frame
  msg = str(start)
  msg += str("," + str(end) + "," + str(end - start))
  logging.info('TIMING, File "%s", line %d, in %s: %s' % (filename, line_number, name, msg))

def get_top_users(acc_ref):
  if not acc_ref:
    error("Unable to get users because of missing account ref") 
    return None
  result = db.GqlQuery("SELECT * FROM Users WHERE accountRef=:1 ORDER BY points DESC LIMIT " + constants.TOP_USERS, acc_ref)
  filtered = []
  for index,ii in enumerate(result):
    delete_index = -1
    try:
      if ii.profileImg == None or ii.profileImg == "":
        ii.profileImg = constants.IMAGE_PARAMS.USER_AVATAR
    except:
      ii.profileImg = constants.IMAGE_PARAMS.USER_AVATAR
    if ii.userid != constants.ANONYMOUS_USER:
      if not ii.profileName:
        ii.profileName = "Anonymous"
      filtered.append(ii) 
  return filtered

def calculate_rank(user_ref, acc_ref):
  rank = constants.NOT_RANKED
  if not user_ref or not acc_ref:
    #error("Unable to cal rank because of missing user or account ref")
    return rank

  if user_ref.rank:
    rank = user_ref.rank  

  last_ranking = user_ref.last_time_ranked
  current_time = datetime.datetime.now()
  recalculate = True
  if last_ranking:
    recalculate = (current_time - last_ranking) > datetime.timedelta(minutes=10)
     
  # Do not calculate rank unless its been 10 minutes since last time
  if recalculate:
    result = db.GqlQuery("SELECT __key__ FROM Users WHERE accountRef=:1 ORDER BY points DESC LIMIT " + constants.NUMBER_RANKED, acc_ref)
    counter = 1
    is_ranked = False
    for ii in result:
      if ii.name() == user_ref.key().name():
        is_ranked = True
        break 
      else:
        counter += 1
    if is_ranked:
      user_ref.rank = counter
      rank = counter
    else:
      user_ref.rank = constants.NOT_RANKED
    
    user_ref.last_time_ranked = current_time
    user_key = user_ref.key().name()
    try:
      users_dao.save_user(user_ref, user_key)
    except:
      error("Error getting user with key %s"%user_key)
  return rank

def success_ret():
  ret = {'status':'success'}
  ret = json.dumps(ret)
  return ret

def db_error():
  ret = {'status':'failed',
        'errcode':constants.API_ERROR_CODES.INTERNAL_ERROR,
        'error':'Database error'} 
  ret = json.dumps(ret)
  return ret 
    
def auth_error():
  ret = {'status':'failed',
         'errcode':constants.API_ERROR_CODES.NOT_AUTH,
         'error':'Permission denied'} 
  ret = json.dumps(ret)
  return ret 

def bad_args():
  ret = {'status':'failed',
         'errcode':constants.API_ERROR_CODES.BAD_ARGS,
         'error':'Number of points is not an integer'} 
  ret = json.dumps(ret)
  return ret 

def bad_user():
  ret = {'status':'failed',
         'errcode':constants.API_ERROR_CODES.BAD_USER,
         'error':'Invalid user provided'}
  ret = json.dumps(ret)
  return ret 

def badge_error():
  ret = {'status':'failed',
         'errcode':constants.API_ERROR_CODES.BADGE_NOT_FOUND,
         'error':'Check your badge id'} 
  ret = json.dumps(ret)
  return ret

def user_error():
  ret = {'status':'failed',
         'errcode':constants.API_ERROR_CODES.USER_NOT_FOUND,
         'error':'User was not found'} 
  ret = json.dumps(ret)
  return ret


class API_1_Status(webapp2.RequestHandler):
  def post(self):
    start = time.time()
    self.response.out.write(success_ret())
    timing(start)
  def get(self):
    start = time.time()
    self.response.out.write(success_ret())
    timing(start) 

class API_1_GetUserData(webapp2.RequestHandler):
  def post(self):
    start = time.time()
    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    user_id = self.request.get('userid')
    user_key = users_dao.get_user_key(account_id, user_id)
    acc = accounts_dao.authorize_api(account_id, api_key)

    logdiction = {'event':'getuserdata', 
                  'api': 'get_user_data',
                  'is_api':'yes',
                  'user':user_id,
                  'account':account_id,
                  'success':'true',
                  'ip':self.request.remote_addr}
    if not acc:
      logdiction['success'] = 'false'
      logdiction['details'] = auth_error()
      logs.create(logdiction)
      self.response.out.write(auth_error())
      return 

    user_ref = users_dao.get_user(account_id, user_id)
    if not user_ref:
      logdiction['success'] = 'false'
      logdiction['details'] = user_error()
      logs.create(logdiction)
      error("User for account %s, %s not found"%(account_id, user_id))
      self.response.out.write(user_error())
      return 

    badges = badges_dao.get_user_badges(user_ref)
    badge_keys = []
    badge_detail = []

    # get the badge image link
    for b in badges:
      if b.awarded == "yes":
        bid = badges_dao.get_badge_id_from_instance_key(b.key().name())
        badge_keys.append(bid)
        
        # add badge detail
        try:
          badgeobj = b.badgeRef
          badge_detail.append({'id':bid,
                               'name': badgeobj.name,
                               'description': badgeobj.description,
                               'theme': badgeobj.theme,
                               'awarded': str(b.awardDateTime),
                               'downloadlink' : b.downloadLink})
        except:
          logging.error('Failed to add badge detail. Badge id: ' + bid)
        
        
    ret = {"status":"success",
           "user_id":user_ref.userid,
           "is_enabled":user_ref.isEnabled,
           "creation_date":str(user_ref.creationDate),
           "points":user_ref.points,
           "profile_name": user_ref.profileName,
           "profile_link": user_ref.profileLink,
           "profile_img": user_ref.profileImg,
           "badges": badge_keys,
           "badges_detail":badge_detail}
    logs.create(logdiction)
    self.response.out.write(json.dumps(ret)) 
    timing(start) 

class API_1_UpdateUser(webapp2.RequestHandler):
  def post(self):
    start = time.time()
    clean = XssCleaner()
    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    new_user_id = self.request.get('userid')
    # Anything that can possibly be rended should be cleaned 
    profile_link = self.request.get('profile_link')
    if profile_link != "" and not profile_link.startswith('http://'):
      profile_link = "http://" + profile_link

    # We can't clean it because it will not render if embedded into a site
    # Be wary of doing any queries with this data
    #profile_link = clean.strip(profile_link)
    profile_img = self.request.get('profile_img') 
    if profile_img != "" and  not profile_img.startswith('http://'):
      profile_img = "http://" + profile_img

    #profile_img = clean.strip(profile_img)
    profile_name = self.request.get('profile_name')
    profile_name = clean.strip(profile_name)
    logdiction = {'event':'loginuser', 
                  'api': 'update_user',
                  'is_api':'yes',
                  'ip':self.request.remote_addr,
                  'user':new_user_id,
                  'account':account_id,
                  'success':'true'}
    if not account_id or not new_user_id or not api_key:
      self.response.out.write(bad_args())
      logdiction['success'] = 'false'
      logdiction['details'] = bad_args()
      logs.create(logdiction)
      return

    acc = accounts_dao.authorize_api(account_id, api_key)
    if not acc:
      self.response.out.write(auth_error())
      logdiction['success'] = 'false'
      logdiction['details'] = auth_error()
      logs.create(logdiction)
      return 

    # Create a new user
    user_key = users_dao.get_user_key(account_id, new_user_id)

    #Update
    user_ref = users_dao.get_user_with_key(user_key)
    if user_ref:
      dict = {}
      update = False
      if profile_link and profile_link != user_ref.profileLink: 
        dict["profileLink"] = profile_link
        update = True
      if profile_img and profile_img != user_ref.profileImg: 
        dict["profileImg"] = profile_img
        update = True
      if profile_name and profile_name != user_ref.profileName: 
        dict["profileName"] = profile_name
        update = True
      if update: 
        logdiction['event'] = 'updateuser'
        try:
          users_dao.update_user(user_key, dict, None)
        except:
          logdiction['success'] = 'false'
          logdiction['details'] = db_error()
          logs.create(logdiction)
          self.response.out.write(db_error())
          error("Error updating user with id %s"%new_user_id)
          return  

      logs.create(logdiction)

      self.response.out.write(success_ret())
      timing(start)
      return  

    if not profile_img:   
      profile_img = constants.IMAGE_PARAMS.USER_AVATAR

    new_user = Users(key_name=user_key,
                     userid=new_user_id,
                     isEnabled="yes",
                     accountRef=acc,
                     profileName=profile_name,
                     profileLink=profile_link,
                     profileImg=profile_img)
    logdiction['event'] = 'createuser'
    try:
      users_dao.save_user(new_user, user_key)
    except:
      logdiction['success'] = 'false'
      logdiction['details'] = db_error()
      logs.create(logdiction)
      self.response.out.write(db_error())
      error("Error getting user with key %s"%user_key)
      return  

    logs.create(logdiction)
    self.response.out.write(success_ret())
    timing(start)
    return 

  def get(self):
    self.redirect('/html/404.html')
    return 

class API_1_AwardBadgePoints(webapp2.RequestHandler):
  def post(self):
    start = time.time()

    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    user_id = self.request.get('userid')
    badge_ref_id = self.request.get('badgeid')
    how_to_get_badge = self.request.get('how')
    points = self.request.get('pointsawarded')
    points_needed = self.request.get('pointsrequired')
    reason = self.request.get('reason') 
    logdiction = {'event':'awardbadgepoints', 
                  'api':'award_badge_points',
                  'user':user_id,
                  'is_api':'yes',
                  'ip':self.request.remote_addr,
                  'account':account_id,
                  'badgeid':badge_ref_id,
                  'points':points,
                  'success':'true'}
    try:
      points = int(points)
      points_needed = int(points_needed)
    except:
      logdiction['success'] = 'false'
      logdiction['details'] = "The number of points was not a number"
      logs.create(logdiction)
      self.response.out.write(bad_args())
      error("Account %s -- Bad value for points awarded \
                    %s or points needed %s"\
                    %(account_id, points, points_needed ))
      return

    if not reason:
      reason = ""

    # Get the account 
    acc = accounts_dao.authorize_api(account_id, api_key)
    if not acc:
      logdiction['success'] = 'false'
      logdiction['details'] = auth_error()
      logs.create(logdiction)
      self.response.out.write(auth_error())
      return 

    # Get the Badge Type (used as a reference for the instances) 
    # Do this before getting/creating user
    badge_key = badges_dao.get_key_from_badge_id(account_id, badge_ref_id)
    if not badge_key:
      logdiction['success'] = 'false'
      logdiction['details'] = badge_error()
      logs.create(logdiction)
      self.response.out.write(badge_error())
      error("Badge not found with key %s"%badge_ref_id)
      return  

    # Get the user, create if it does not exist
    user_ref = users_dao.get_or_create_user(account_id, user_id, acc)
    if not user_ref:
      logdiction['success'] = 'false'
      logdiction['details'] = db_error()
      logs.create(logdiction)
      self.response.out.write(db_error())
      return  
  
    badge_ref = badges_dao.get_badge(badge_key) 
    if not badge_ref:
      logdiction['success'] = 'false'
      logdiction['details'] = badge_error()
      logs.create(logdiction)
      ret = badge_error()
      self.response.out.write(ret)
      return  

    badge_instance_key = badges_dao.get_badge_instance_key(badge_key, user_id)
    badge_instance_ref = badges_dao.get_badge_instance(badge_instance_key)

    if not reason:
      reason = badge_ref.description
    link = badge_ref.downloadLink

    if not badge_instance_ref:
      # Create a new badge with 0 points
      isawarded = "no"
      if points >= points_needed:
        isawarded = "yes" 
      perm = badges_dao.get_badge_key_permission(badge_ref_id)
      new_badge_instance = badges_dao.create_badge_instance(
                                       badge_instance_key,
                                       badge_ref,
                                       user_ref,
                                       isawarded,
                                       points,
                                       points_needed,
                                       perm,
                                       link,
                                       reason)
      if isawarded == "yes":
        notifier.user_badge_award(user_ref, "Badge Awarded", link, reason, acc, badge_ref_id)
        logdiction['event'] = 'badgeawarded'
    else: 
      isawarded = "no"
      points_thus_far = badge_instance_ref.pointsEarned
      if points:
        points_thus_far += points
      incr_args = {"pointsEarned":points}
      reg_args = {}
      # Update the following if its changed
      if badge_instance_ref.pointsRequired != points_needed:
        reg_args["pointsRequired"] = points_needed

      if badge_instance_ref.pointsEarned < points_needed and \
              points_thus_far >= points_needed:
        notifier.user_badge_award(user_ref, "Badge Awarded", link, reason, acc, badge_ref_id)
        logdiction['event'] = 'badgeawarded'

      if points_thus_far >= points_needed:
        reg_args["awarded"] = "yes"
        isawarded = "yes"
      try:
        ret = badges_dao.update_badge_instance(badge_instance_key, 
                                reg_args, incr_args)
        if not ret:
          raise
      except:
        error("Unable to update badge instance with key %s"%\
              badge_instance_key)
        self.response.out.write(db_error())
        return
    logs.create(logdiction)
    ret = {"status":"success",
           "badge_awarded":isawarded}
    self.response.out.write(json.dumps(ret))
    timing(start)
    return  

  def get(self):
    self.redirect('/html/404.html')


class API_1_AwardBadge(webapp2.RequestHandler):
  def post(self):
    start = time.time()
    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    user_id = self.request.get('userid')
    badge_ref_id = self.request.get('badgeid')
    reason = self.request.get('reason')

    clean = XssCleaner()
    reason = clean.strip(reason)
    logdiction = {'event':'awardbadge', 
                  'api':'award_badge',
                  'badgeid':badge_ref_id,
                  'is_api':'yes',
                  'ip':self.request.remote_addr,
                  'user':user_id,
                  'account':account_id,
                  'success':'true'}

    # Get the account 
    acc = accounts_dao.authorize_api(account_id, api_key)
    if not acc:
      logdiction['success'] = 'false'
      logdiction['details'] = auth_error()
      logs.create(logdiction)
      self.response.out.write(auth_error())
      return 

    if not user_id or not badge_ref_id:
      logdiction['success'] = 'false'
      logdiction['details'] = bad_args()
      logs.create(logdiction)
      self.response.out.write(bad_args())
      error("User id or badge id was not given")
      return  

    # Make sure we have a legit badge before getting/creating a user
    badge_key = badges_dao.get_key_from_badge_id(account_id, badge_ref_id)
    if not badge_key:
      logdiction['success'] = 'false'
      logdiction['details'] = badge_error()
      logs.create(logdiction)
      self.response.out.write(badge_error())
      return  
  
    # Get the user
    user_ref = users_dao.get_or_create_user(account_id, user_id, acc)
    if not user_ref:
      logdiction['success'] = 'false'
      logdiction['details'] = db_error()
      logs.create(logdiction)
      self.response.out.write(db_error())
      return 
 
    badge_instance_key = badges_dao.get_badge_instance_key(badge_key, user_id) 
    # If the user already has it, skip the award
    badge_ref = badges_dao.get_badge_instance(badge_instance_key)
    if badge_ref:
      if badge_ref.awarded == "yes":
        logs.create(logdiction)
        self.response.out.write(success_ret())
        timing(start)
        return  

    # Get the Badge Type (used as a reference for the instances) 
    badge_ref = badges_dao.get_badge(badge_key)
    if not badge_ref:
      self.response.out.write(badge_error())
      return  

    if not reason:
      reason = badge_ref.description

    link = badge_ref.downloadLink
    new_badge_instance = badges_dao.create_badge_instance(
                                    badge_instance_key,
                                    badge_ref,
                                    user_ref,
                                    "yes", #isawarded
                                    0, #points
                                    0, #points_needed
                                    "private",
                                    link,
                                    reason)
    name = badges_dao.get_badge_name_from_instance_key(badge_instance_key)
    notifier.user_badge_award(user_ref, "Badge Awarded", link, reason, acc, badge_ref_id)
    logs.create(logdiction)
    self.response.out.write(success_ret())
    timing(start)
    return  

  def get(self):
    self.redirect('/html/404.html')

class API_1_RemoveBadge(webapp2.RequestHandler):
  def post(self):
    start = time.time()
    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    user_id = self.request.get('userid')
    badge_ref_id = self.request.get('badgeid')
    logdiction = {'event':'removebadge', 
                  'api':'remove_badge',
                  'badgeid':badge_ref_id,
                  'is_api':'yes',
                  'ip':self.request.remote_addr,
                  'user':user_id,
                  'account':account_id,
                  'success':'true'}

    # Get the account 
    acc = accounts_dao.authorize_api(account_id, api_key)
    if not acc:
      logdiction['success'] = 'false'
      logdiction['details'] = auth_error()
      logs.create(logdiction)
      self.response.out.write(auth_error())
      return 

    if not user_id or not badge_ref_id:
      logdiction['success'] = 'false'
      logdiction['details'] = bad_args()
      logs.create(logdiction)
      self.response.out.write(bad_args())
      return  

    badge_key = badges_dao.get_key_from_badge_id(account_id, badge_ref_id)
    if not badge_key:
      logdiction['success'] = 'false'
      logdiction['details'] = badge_error()
      logs.create(logdiction)
      self.response.out.write(badge_error())
      return  
  
    # Get the user
    user_ref = users_dao.get_or_create_user(account_id, user_id, acc)
    if not user_ref:
      logdiction['success'] = 'false'
      logdiction['details'] = db_error()
      logs.create(logdiction)
      self.response.out.write(db_error())
      return 
 
    badge_instance_key = badges_dao.get_badge_instance_key(badge_key, user_id) 
    # Get the Badge Type (used as a reference for the instances) 
    badge_ref = badges_dao.get_badge(badge_key)
    if not badge_ref:
      logdiction['success'] = 'false'
      logdiction['details'] = badge_error()
      logs.create(logdiction)
      self.response.out.write(badge_error())
      return  

    try:
      new_badge_instance = badges_dao.delete_badge_instance(badge_instance_key)
    except:
      logdiction['success'] = 'false'
      logdiction['details'] = db_error()
      logs.create(logdiction)
      self.response.out.write(db_error())
      return 
    logs.create(logdiction)
    self.response.out.write(success_ret())
    timing(start)
    return  

  def get(self):
    self.redirect('/html/404.html')


class API_1_GetWidget(webapp2.RequestHandler):
  def post(self):
    """This post is for priming/prefetching, 
       not actually delivering the widget
    """
    start = time.time()
    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    user_id = self.request.get('userid')
    widget_type = self.request.get('widget')
    logdiction = {'event':'prefetchwidget', 
                  'api':'get_widget',
                  'user':user_id,
                  'is_api':'yes',
                  'ip':self.request.remote_addr,
                  'account':account_id,
                  'widget':widget_type,
                  'success':'true'}

    if widget_type not in constants.VALID_WIDGETS:
      logdiction['success'] = 'false'
      logdiction['details'] = "Using an invalid widget name"
      logs.create(logdiction)
      self.response.out.write(bad_args())
      return
 
    # Get the account 
    acc_ref = accounts_dao.authorize_api(account_id, api_key)
    if not acc_ref:
      logdiction['success'] = 'false'
      logdiction['details'] = auth_error()
      logs.create(logdiction)
      self.response.out.write(auth_error())
      return 

    if not user_id and widget_type in constants.WIDGETS_THAT_DONT_NEED_A_USER:
      user_id = constants.ANONYMOUS_USER

    if not user_id:
      logdiction['success'] = 'false'
      logdiction['details'] = bad_args()
      logs.create(logdiction)
      self.response.out.write(bad_args())
      return  

    user_ref = None
    if user_id: 
      user_ref = users_dao.get_user_with_key(user_id)

    if not user_ref and user_id == constants.ANONYMOUS_USER:
      users_dao.create_new_user(account_id, constants.ANONYMOUS_USER) 

    #acc_ref = users_dao.get_account_from_user(user_ref)
    # TODO Need to measure if there is an actual gain from this prefetching
    # or if it's causing unnecessary contention
    values = getattr(self, widget_type + "_values")(user_ref, acc_ref, 500, 300)
    logs.create(logdiction)
    return  
 
  
  def get(self):
    """ Users fetch their widgets from here """
    start = time.time()
    user_key = self.request.get('u')

    if not user_key:
      self.redirect('/html/404.html') 
      return 

    height = self.request.get('height')
    width = self.request.get('width')
    widget_type = self.request.get('widget')
    if widget_type not in constants.VALID_WIDGETS:
      self.redirect('/html/404.html')
      error("Fetching widget type " + str(widget_type))
      return
    
    # TODO make sure the account has permission to the type of widget
    # as of right now all widgets are enabled
    user_ref = users_dao.get_user_with_key(user_key)
    acc_ref = users_dao.get_account_from_user(user_ref)
    user_id = ""
    acc_id = ""
    if user_ref: user_id = user_ref.key().name()
    if acc_ref: acc_id = acc_ref.key().name()

    logdiction = {'event':'viewwidget', 
                  'api':'get_widget',
                  'user':user_id,
                  'is_api':'yes',
                  'ip':self.request.remote_addr,
                  'account':acc_id,
                  'widget':widget_type,
                  'success':'true'}

    values = getattr(self, widget_type + "_values")(user_ref, acc_ref, height, width)
    path = os.path.join(os.path.dirname(__file__), 'widgets/v1.0/' +
           widget_type + ".html")
    #TODO minify temp code, lots of white space right now
    temp = template.render(path, values)   

    logs.create(logdiction)
    self.response.out.write(temp)
    timing(start)
    return  

  def trophy_case_values(self, user_ref, acc_ref, height, width):
    badges = badges_dao.get_user_badges(user_ref)
    tcase_ref = None
    if not acc_ref:
      tcase_ref = TrophyCase()
    else:
      try:
        tcase_ref = acc_ref.trophyWidget
      except:
        tcase_ref = widgets_dao.add_trophy_case(acc_ref)

    awarded_badges= []
    for b in badges:
      if b.awarded == "yes":
        awarded_badges.append(b)
    # here we get the custom trophy case settings
    # Grab all the badge urls
    ret = {"status":"success"}
     
    for ii in tcase_ref.properties():
      ret[ii] = getattr(tcase_ref, ii)
    ret["badges"] = awarded_badges

    # Internal div's need to be slighy smaller than the iframe
    if width and height:
      try:
        width = int(width)
        height = int(height)
        # How did I get this equation? Trial and error.
        height = height - 2 *int(ret['borderThickness']) - 8
        width = width - 2 *int(ret['borderThickness']) - 8
        ret['height'] = height
        ret['width'] = width
      except:
        pass
    return ret 

  def notifier_values(self, user_ref, acc_ref, height, width):
    token = 0
    notifier_ref = None
    if not acc_ref:
      notifier_ref = Notifier()
    else:
      try:
        notifier_ref = acc_ref.notifierWidget
      except:
        notifier_ref = widgets_dao.add_notifier(acc_ref)

    token = notifier.get_channel_token(user_ref)

    ret = {"status":"success"}
    ret["token"] = token
    # here we get the custom settings
    for ii in notifier_ref.properties():
      ret[ii] = getattr(notifier_ref, ii)

    # Internal div's need to be slighy smaller than the iframe
    if width and height:
      try:
        width = int(width)
        height = int(height)
        # How did I get this equation? Trial and error.
        height = height - 2 *int(ret['borderThickness']) - 8
        width = width - 2 *int(ret['borderThickness']) - 16
        #height = height - 2 *int(ret['borderThickness']) - 8
        #width = width - 2 *int(ret['borderThickness']) - 8 
        ret['height'] = height
        ret['width'] = width
      except:
        pass
     
    return ret

  def milestones_values(self, user_ref, acc_ref, height, width):
    user_badges = badges_dao.get_user_badges(user_ref)
    acc_badges = badges_dao.get_rendereable_badgeset(acc_ref)
    mcase_ref = None
    if not acc_ref:
      mcase_ref = Milestones()
    else:
      try:
        mcase_ref = acc_ref.milestoneWidget
      except:
        mcase_ref = widgets_dao.add_milestones(acc_ref)

    if user_ref and user_ref.userid == constants.ANONYMOUS_USER:
      user_badges = []

    badge_count = 0
    display_badges = []
    for badge in user_badges:
      b = {}
      try:
        # In case the badge was removed, we'll skip it
        b["badgeRef"] = badge.badgeRef
      except Exception, e:
        continue
      if badge.awarded == "yes":
        b["awarded"] = True
      else:
        b["awarded"] = True
      b["id"] = badge_count 
      b["awarded"] = badge.awarded
      b["pointsRequired"] = badge.pointsRequired

      # backward compatibility
      if badge.pointsRequired == 9999999999:
        b["pointsRequired"] = 0
   
      if badge.pointsEarned > badge.pointsRequired:
        b["pointsEarned"] = badge.pointsRequired
      else:  
        b["pointsEarned"] = badge.pointsEarned
      b["resource"] = badge.resource
      b["reason"] = badge.reason
      b["downloadLink"] = badge.downloadLink
      b["id"] = badge_count
      badge_count += 1
      display_badges.append(b)
    # Put all badges that have not been awarded
    to_add = []
    for aa in acc_badges:
      is_there = False
      for dd in display_badges:
        if aa["key"] == dd["badgeRef"].key().name():
          is_there = True
      if not is_there:
        b = {}
        b["id"] = badge_count 
        b["awarded"] = False
        b["pointsEarned"] = 0
        b["pointsRequired"] = 0
        # This name should not have changed
        b["resource"] = ""
        b["reason"] = aa["description"]
        b["downloadLink"] = aa["downloadLink"]
        badge_count += 1
        to_add.append(b)
    display_badges.extend(to_add)
    ret = {"status":"success"}
     
    for ii in mcase_ref.properties():
      ret[ii] = getattr(mcase_ref, ii)
    ret["badges"] = display_badges

    # Internal div's need to be slighy smaller than the iframe
    if width and height:
      try:
        width = int(width)
        height = int(height)
        # How did I get this equation? Trial and error.
        height = height - 2 *int(ret['borderThickness']) - 8
        width = width - 2 *int(ret['borderThickness']) - 8
        ret['height'] = height
        ret['width'] = width
      except:
        pass
    ret['barSize'] = ret['imageSize']
    return ret 

  def leaderboard_values(self, user_ref, acc_ref, height, width):
    leader_ref = None
    if not acc_ref:
      leader_ref = Leaderboard()
    else: 
      try:
        leader_ref = acc_ref.leaderWidget
        if leader_ref == None:
          leader_ref = widgets_dao.add_leader(acc_ref)
      except:
        leader_ref = widgets_dao.add_leader(acc_ref)

    # here we get the custom rank settings
    ret = {"status":"success"}
    ret['users'] = get_top_users(acc_ref) 
    
    for ii in leader_ref.properties():
      ret[ii] = getattr(leader_ref, ii)

    # Internal div's need to be slighy smaller than the iframe
    if width and height:
      try:
        width = int(width)
        height = int(height)
        # How did I get this equation? Trial and error.
        height = height - 2 *int(ret['borderThickness']) - 8
        width = width - 2 *int(ret['borderThickness']) - 8
        ret['height'] = height
        ret['width'] = width
      except:
        pass
    
    return ret

  def points_values(self, user_ref, acc_ref, height, width):
    points = 0
    if user_ref:
      points = user_ref.points
    points_ref = None
    if not acc_ref:
      points_ref = Points()
    else:
      try:
        points_ref = acc_ref.pointsWidget
      except:
        points_ref = widgets_dao.add_points(acc_ref)
    ret = {"status":"success"}
     
    # here we get the custom points settings
    for ii in points_ref.properties():
      ret[ii] = getattr(points_ref, ii)
    points = format_integer(points) 
    ret['points'] = points
   
    # Internal div's need to be slighy smaller than the iframe
    if width and height:
      try:
        width = int(width)
        height = int(height)
        # How did I get this equation? Trial and error.
        height = height - 2 *int(ret['borderThickness']) - 8
        width = width - 2 *int(ret['borderThickness']) - 8
        ret['height'] = height
        ret['width'] = width
      except:
        pass
    return ret

  def rank_values(self, user_ref, acc_ref, height, width):
    rank = 0
    if user_ref:
      rank = user_ref.rank
    rank_ref = None
    if not acc_ref:
      rank_ref = Rank()
    else: 
      try:
        rank_ref = acc_ref.rankWidget
      except:
        rank_ref = widgets_dao.add_rank(acc_ref)

    # here we get the custom rank settings
    ret = {"status":"success"}
     
    for ii in rank_ref.properties():
      ret[ii] = getattr(rank_ref, ii)
    rank = calculate_rank(user_ref, acc_ref)
    if rank == constants.NOT_RANKED:
      ret['rank'] = "Unranked"
    else:
      ret['rank']= "&#35 " + format_integer(rank)
    # Internal div's need to be slighy smaller than the iframe
    if width and height:
      try:
        width = int(width)
        height = int(height)
        # How did I get this equation? Trial and error.
        height = height - 2 *int(ret['borderThickness']) - 8
        width = width - 2 *int(ret['borderThickness']) - 8
        ret['height'] = height
        ret['width'] = width
      except:
        pass
    
    return ret

class API_1_AwardPoints(webapp2.RequestHandler):
  def post(self):
    start = time.time()
    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    user_id = self.request.get('userid')
    newpoints = self.request.get('pointsawarded')
    reason = self.request.get('reason')
    logdiction = {'event':'awardpoints', 
                  'api':'award_points',
                  'points':newpoints,
                  'is_api':'yes',
                  'ip':self.request.remote_addr,
                  'user':user_id,
                  'account':account_id,
                  'success':'true'}

    clean = XssCleaner()
    if reason:
      reason = clean.strip(reason)
    else:
      reason = ""

    # Get the account 
    acc = accounts_dao.authorize_api(account_id, api_key)
    if not acc:
      logdiction['success'] = 'false'
      logdiction['details'] = auth_error()
      logs.create(logdiction)
      self.response.out.write(auth_error())
      return 

    try:
      newpoints = int(newpoints)
    except:
      logdiction['success'] = 'false'
      logdiction['details'] = "Points given was not a number"
      logs.create(logdiction)
      self.response.out.write(bad_args())
      error("Points given was not an integer")
      return  

    # Create the user if it doesnt exist
    user_ref = users_dao.get_or_create_user(account_id, user_id, acc)
    if not user_ref:
      logdiction['success'] = 'false'
      logdiction['details'] = db_error()
      logs.create(logdiction)
      self.response.out.write(db_error())
      return 

    incrArgs = {"points":newpoints}
    user_key = users_dao.get_user_key(account_id, user_id)
    dbret = users_dao.update_user(user_key, None, incrArgs)
    if not dbret:
      logdiction['success'] = 'false'
      logdiction['details'] = db_error()
      logs.create(logdiction)
      self.response.out.write(db_error())
      error("Unable to update points field account %s, user %s, key: %s"%\
            (account_id,user_id, user_key))
      return  
    if not reason:
      try:
        reason = acc.notifierWidget.title
      except:
        reason = "Points Awarded"
    notifier.user_points(user_ref, newpoints, reason, acc)
      
    logs.create(logdiction)
    self.response.out.write(success_ret())
    timing(start)
    return
   
  def get(self):
    self.redirect('/html/404.html')
    return 

class API_1_TestCleanup(webapp2.RequestHandler):
  def post(self):
    isLocal = os.environ['SERVER_SOFTWARE'].startswith('Dev')
    if not isLocal:
      return
    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    badge_id = self.request.get('badgeid')
    badge_theme = self.request.get('theme')
    user_id = self.request.get('user')
    if not badge_theme or not badge_id or not account_id or not api_key:
      ret = bad_args()
      self.response.out.write(ret)
      return

    user_key = users_dao.get_user_key(account_id, user_id)
    user_ref = users_dao.get_user(account_id, user_id)
    if user_ref:
      badge_instances = badges_dao.get_user_badges(user_ref)
      for b in badge_instances:
        badges_dao.delete_badge_instance(b.key().name())
      users_dao.delete_user(user_key)

    trophy_case_widget = TrophyCase(key_name=account_id)
    points_widget = Points(key_name=account_id)
    rank_widget = Rank(key_name=account_id)
    notifier_widget = Notifier(key_name=account_id)
    leader_widget = Leaderboard(key_name=account_id)
    milestones_widget = Milestones(key_name=account_id)
    acc = Accounts(key_name=account_id,
                   email=account_id,
                   password="xxxxxxxxx",
                   isEnabled=constants.ACCOUNT_STATUS.ENABLED, 
                   accountType="admin",
                   paymentType="free",
                   cookieKey="xxxxxxxxx", 
                   apiKey=api_key, 
                   trophyWidget=trophy_case_widget,
                   pointsWidget=points_widget,
                   rankWidget=rank_widget,
                   leaderWidget=leader_widget,
                   milestoneWidget=milestones_widget)

     # delete ten badges
    for ii in range(0,10):
      badgeKey = badges_dao.create_badge_key(account_id, badge_theme, str(ii), "private")
      badges_dao.delete_badge_image(badgeKey)
      badges_dao.delete_badge(badgeKey)

    widgets_dao.delete_widget(account_id, "TrophyCase")
    widgets_dao.delete_widget(account_id, "Points")
    widgets_dao.delete_widget(account_id, "Rank")
    widgets_dao.delete_widget(account_id, "Leaderboard")
    widgets_dao.delete_widget(account_id, "Notifier")
    widgets_dao.delete_widget(account_id, "Milestones")
    accounts_dao.delete_account(account_id)
    self.response.out.write(success_ret())
    return

  def  get(self):
    self.redirect('/html/404.html')
    return  

# Secret only valid for local testing
TOPSECRET = "8u8u9i9i"
class API_1_Test(webapp2.RequestHandler):
  def post(self):
    isLocal = os.environ['SERVER_SOFTWARE'].startswith('Dev')
    if not isLocal:
      return
    secret = self.request.get('secret')
    if secret != TOPSECRET:
      bad_args()  
      return
    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    badge_id = self.request.get('badgeid')
    badge_theme = self.request.get('theme')
    if not badge_theme or not badge_id or not account_id or not api_key:
      ret = bad_args()
      self.response.out.write(ret)
      return
    acc = accounts_dao.create_account(account_id, "xxx000xxx", enable=True)

    from serverside.entities import memcache_db
    acc.apiKey = "ABCDEFGHI"
    memcache_db.save_entity(acc, account_id)
    # remote paths are used because the SDK cannot fetch from itself 
    # because it is single threaded and would cause deadlock
    badge_list = ["http://cdn2.iconfinder.com/data/icons/crystalproject/128x128/apps/keditbookmarks.png",
                  "http://cdn4.iconfinder.com/data/icons/Merry_Christmas_by_jj_maxer/golden%20star.png",
                  "http://cdn1.iconfinder.com/data/icons/CrystalClear/128x128/actions/bookmark.png",
                  "http://cdn4.iconfinder.com/data/icons/token/Token,%20128x128,%20PNG/Star-Favorites.png",
                  "http://cdn4.iconfinder.com/data/icons/supermario/PNG/Star.png",
                  "http://cdn5.iconfinder.com/data/icons/SOPHISTIQUE/graphics/png/128/star.png",
                  "http://cdn3.iconfinder.com/data/icons/humano2/128x128/actions/bookmark-new.png",
                  "http://cdn2.iconfinder.com/data/icons/web2/Icons/Favorite_128x128.png",
                  "http://cdn5.iconfinder.com/data/icons/water_gaming_pack/128/star_wars_battlefront.png",
                  "http://cdn2.iconfinder.com/data/icons/spaceinvaders/blackhole.png"]
    # Create ten badges
    for ii in range(0,10):
      newbadge = badge_list[ii]

      try:
        result = urlfetch.fetch(url=newbadge)
      except:
        error("Is one of the badges no longer available? Check %s"%newbadge)
        return
 
      imgbuf = result.content
      if  len(imgbuf) == 0:
        error("One of the downloads did not work! url:%s"%newbadge)
        return
      badge_key = badges_dao.create_badge_key(account_id, badge_theme, str(ii), "private")
      # Create the file
      file_name = files.blobstore.create(mime_type='application/octet-stream')

      # Open the file and write to it
      with files.open(file_name, 'a') as f:
        f.write(imgbuf)

      # Finalize the file. Do this before attempting to read it.
      files.finalize(file_name)

      # Get the file's blob key
      blob_key = files.blobstore.get_blob_key(file_name)
      blob_info = blobstore.BlobInfo.get(blob_key)

      # TODO test with different types of images
      badges_dao.create_badge_type(badge_key,
                      str(ii),
                      "badge description",
                      acc,
                      badge_theme,
                      "png",
                      blob_info=blob_info)
      # End of for loop
    self.response.out.write(success_ret())
    return        
  def get(self):
    self.redirect('/html/404.html')
    return  

# Hidden menu APIs, badges should be created via console
class API_1_CreateBadge(webapp2.RequestHandler):
  def post(self):
    start = time.time()
    api_key = self.request.get('apikey')
    account_id = self.request.get('accountid')
    badge_name = self.request.get('name')
    theme = self.request.get('theme')
    description = self.request.get('description')
    imagelink = self.request.get('imagelink')
    acc = accounts_dao.authorize_api(account_id, api_key)
    logdiction = {'event':'createbadge', 
                  'ip':self.request.remote_addr,
                  'is_api':'yes',
                  'api':'createbadge',
                  'account':account_id,
                  'success':'true'}

    if not acc:
      logdiction['success'] = 'false'
      logdiction['details'] = auth_error()
      logs.create(logdiction)
      self.response.out.write(auth_error())
      return 

    if not imagelink or not badge_name or not theme or not description:
      logdiction['success'] = 'false'
      logdiction['details'] = bad_args()
      logs.create(logdiction)
      self.response.out.write(bad_args())
      return 
      
    badge_key = badges_dao.create_badge_key(account_id, theme, badge_name, "private")
    logdiction['details'] = badge_key + " " + imagelink
    result = ""
    try:
      result = urlfetch.fetch(url=imagelink)
    except:
      error("Unable to download badge")
      self.response.out.write(bad_args())
      return

    imgbuf = result.content
    if  len(imgbuf) == 0:
      error("One of the downloads did not work! url:%s"%imagelink)
      self.response.out.write(bad_args())
      return
    def get_file_ext(filename):
      ii = filename.rfind(".")
      if ii == -1:
        return "png"
      else:
        return filename[ii + 1:]

    file_name = files.blobstore.create(mime_type='image/'+ get_file_ext(imagelink))

    with files.open(file_name, 'a') as f:
      f.write(imgbuf)

    files.finalize(file_name)

    blob_key = files.blobstore.get_blob_key(file_name)
    blob_info = blobstore.BlobInfo.get(blob_key)
    badges_dao.create_badge_type(badge_key,
                    badge_name,
                    description,
                    acc,
                    theme,
                    get_file_ext(imagelink),
                    blob_info=blob_info)
    self.response.out.write(success_ret())
    return        
 

app = webapp2.WSGIApplication([
  ('/api/1/', API_1_Status),
  ('/api/1/updateuser', API_1_UpdateUser),
  ('/api/1/getuserdata', API_1_GetUserData),
  ('/api/1/awardbadge', API_1_AwardBadge),
  ('/api/1/removebadge', API_1_RemoveBadge),
  ('/api/1/awardbadgepoints', API_1_AwardBadgePoints),
  ('/api/1/awardpoints', API_1_AwardPoints),
  ('/api/1/test', API_1_Test),
  ('/api/1/testcleanup', API_1_TestCleanup),
  ('/api/1/getwidget', API_1_GetWidget),
  # Secret menu APIs 
  ('/api/1/createbadge', API_1_CreateBadge)
], debug=False)

"""
def main():
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()
"""

########NEW FILE########
__FILENAME__ = badge
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from serverside.dao import badges_dao
from entities.accounts import Accounts
from entities.badges import *
from entities.users import *
from google.appengine.ext import db
import webapp2
from google.appengine.ext.webapp import template
from serverside import constants
from serverside.constants import TEMPLATE_PATHS
from serverside.session import Session
from tools.utils import account_login_required
from tools.xss import XssCleaner, XssCleaner
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore
import google.appengine.api.images
import cgi
import logging
import os
import wsgiref.handlers
import string
import json

def delete_blob(blob_info):
  blob_key = blob_info.key()
  logging.info("Deleting blob " + str(blob_key))
  blobstore.delete(blob_key) 

def is_valid_image(filename, filecontents):
  return True 

def get_file_ext(filename):
  ii = filename.rfind(".")
  if ii == -1:
    # assume its png
    return "png"
  else:
    return filename[ii + 1:] 

class UploadBadge(blobstore_handlers.BlobstoreUploadHandler):
  @account_login_required
  def post(self):
    #TODO
    # IN the future we should try to move this logic to data access utility layer
    # and have the handler portion be in console.py
    current_session = Session().get_current_session(self)
    account = current_session.get_account_entity()
    if not account:
      self.response.out.write("Problem with your account. Please email support.")
      return  

    #TODO make sure badge name is not taken, or warn if overwritting
    badge_name = self.request.get("badgename")
    badge_name = string.replace(badge_name, " ", "_")
    badge_name = string.replace(badge_name, "-", "_")

    badge_theme = self.request.get("badgetheme")
    badge_theme= string.replace(badge_theme, "-", "_")
    badge_theme = string.replace(badge_theme, " ", "_")

    badge_des = self.request.get("badgedescription")

    upload_files = self.get_uploads('file')
    blob_info = upload_files[0]

    badge_file_name = blob_info.filename
    badge_ext = get_file_ext(badge_file_name)     
    if badge_ext not in constants.IMAGE_PARAMS.VALID_EXT_TYPES:
      delete_blob(blob_info)
      self.redirect('/adminconsole/badges?error=BadImageType')
      return 
      
    logging.info("File ext:"+badge_ext)
    if not badge_name:
      delete_blob(blob_info)
      self.redirect('/adminconsole/badges?error=NoNameGiven')
      return 
    if not badge_des:
      delete_blob(blob_info)
      self.redirect('/adminconsole/badges?error=NoDescriptionGiven')
      return 
    if not badge_theme: 
      delete_blob(blob_info)
      self.redirect('/adminconsole/badges?error=NoThemeGiven')
      return 
    if not blob_info:
      delete_blob(blob_info)
      self.redirect('/adminconsole/badges?error=InternalError')
      return 
    if blob_info.size > constants.MAX_BADGE_SIZE:
      delete_blob(blob_info)
      self.redirect('/adminconsole/badges?error=FileTooLarge')
      return 
    perm = "private"
    if account.email == constants.ADMIN_ACCOUNT:
      perm = "public" 

    badge_key = badges_dao.create_badge_key(account.email, badge_theme, badge_name, perm)

    badge = badges_dao.create_badge_type(badge_key,
                      badge_name,
                      badge_des,
                      account,
                      badge_theme,
                      badge_ext,
                      blob_info=blob_info)
    self.redirect('/adminconsole/badges')

  def get(self):
    self.redirect('/adminconsole/badges')

class DownloadBadge(webapp2.RequestHandler):
  def get(self):
    badge_id = self.request.get("bk")
    if not badge_id:
      self.redirect('/images/default.jpg')
      return 
    badge = badges_dao.get_badge_image(badge_id)
    if not badge:
      logging.error("Download badge: %s key not found"%badge_id) 
      self.redirect('/images/default.jpg')
      return 
    self.response.headers['Content-Type'] = "image/" + str(badge.imgType)
    self.response.out.write(badge.image)

class SeeTheme(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    clean = XssCleaner()
    badge_theme = self.request.get("theme")
    clean_badge_theme = clean.strip(badge_theme)
    if badge_theme != clean_badge_theme:
      logging.info("Cleaning: %s to %s"%(badge_theme, clean_badge_theme))
    badges = db.GqlQuery("SELECT * FROM Badges where theme=:1", 
                         clean_badge_theme)
    badgeset = []
    for b in badges:
      item = {"name": b.name, 
       "description": b.description, 
       "alt":b.altText, 
       "key":b.key().name(),
       "perm":b.permissions }
      badgeset.append(item)

    values = {"badgetheme":clean_badge_theme,
              "badges": badgeset}
    path = os.path.join(os.path.dirname(__file__), 'templates/badgetheme.html')
    # TODO fix this for when you hit refresh, dont go 404 on them
    self.response.out.write(template.render(path, values))
             

########NEW FILE########
__FILENAME__ = console
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Feb 1, 2011

@author: shan

Console class that will render the user console and provide additional functionality if needed.
'''
import webapp2
from google.appengine.ext.webapp import template
from google.appengine.api import mail
from google.appengine.ext import blobstore 

from serverside import constants
from serverside.session import Session
from serverside.tools.utils import account_login_required
from serverside.tools.utils import format_integer
from serverside.dao import widgets_dao
from serverside.dao import badges_dao
from serverside.dao import accounts_dao
from serverside import messages
from serverside import environment
from serverside.dao import users_dao
from serverside import notifier
from client_tools.python.userinfuser import ui_api 

# TODO This needs to be moved to users_dao
from serverside.entities.users import Users
import datetime
import hashlib
import logging
import wsgiref.handlers
import random
import json

def getErrorString(err):
  if err == "BadImageType":
    return "You may only have png, jpg, or gif image types"
  elif err == "FileTooLarge":
    return "Sorry, max image size allowed is " + str(constants.MAX_BADGE_SIZE) + " bytes"
  elif err == "InvalidID":
    return "Please check your values and try again"
  elif err == "BadBadge":
    return "Please check your badge id and try again"
  elif err == "NoUserID":
    return "A User ID was not provided, please try again"
  return err

class Console(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    """ Render dashboard """
    current_session = Session().get_current_session(self)
    
    account = current_session.get_account_entity()
    api_key = account.apiKey
    
    template_values = {'dashboard_main' : True,
                       'account_name': current_session.get_email(),
                       'api_key': api_key}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_DASHBOARD, template_values))

class ConsoleUsers(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    """ Render users template """
    current_session = Session().get_current_session(self)
    email = current_session.get_email()
    error = self.request.get("error")
    has_error = False
    if error:
      has_error = True 
      error = getErrorString(error)
    email = current_session.get_email()
    account = current_session.get_account_entity()
    badges = badges_dao.get_rendereable_badgeset(account)
    template_values = {'users_main': True,
                       'account_name': email,
                       'badges':badges,
                       'has_error': has_error,
                       'error': error}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_DASHBOARD, template_values))

class ConsoleBadges(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    current_session = Session().get_current_session(self)
    email = current_session.get_email()
    account = current_session.get_account_entity()
    error = self.request.get("error")
    has_error = False
    if error:
      has_error = True 
      error = getErrorString(error)
    badgeset = badges_dao.get_rendereable_badgeset(account)
    upload_url = blobstore.create_upload_url('/badge/u')
    template_values = {'badges_main': True,
                       'account_name': email,
                       'badges': badgeset,
                       'upload_url': upload_url,
                       'has_error': has_error,
                       'error': error}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_DASHBOARD, template_values))

class ConsoleEditUser(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    """
    Verify that specified user exists for given account
    """
    current_session = Session().get_current_session(self)
    email = current_session.get_email()
    edit_user = self.request.get("name")
    error = self.request.get("error")
    has_error = False
    if error:
      has_error = True 
      error = getErrorString(error)
    
    """ Generate links to see each widget for user """
    userhash = hashlib.sha1(email + '---' + edit_user).hexdigest()
    
    trophy_case_widget_url = "/api/1/getwidget?widget=trophy_case&u=" + userhash
    points_widget_url = "/api/1/getwidget?widget=points&u=" + userhash
    rank_widget_url = "/api/1/getwidget?widget=rank&u=" + userhash 
    milestones_widget_url = "/api/1/getwidget?widget=milestones&u=" + userhash 
    
    template_values = {'users_edit' : True,
                       'account_name' : current_session.get_email(),
                       'editusername': edit_user,
                       'view_trophy_case':trophy_case_widget_url,
                       'view_points':points_widget_url,
                       'view_rank':rank_widget_url,
                       'view_milestones':milestones_widget_url,
                       'error':error,
                       'has_error':has_error}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_DASHBOARD, template_values))

class ConsoleUsersFetch(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    """ Params page, limit """
    page = self.request.get("page")
    limit = self.request.get("limit")
    order_by = self.request.get("orderby")
    
    if page == None or page == "" or limit == None or page == "":
      self.response.out.write("Error")
      return
      
    try:
      page = int(page)
      limit = int(limit)
    except:
      self.response.out.write("Error, args must be ints. kthxbye!")
      return
      
    current_session = Session().get_current_session(self)
    
    asc = "ASC"
    if order_by == "points":
      asc = "DESC"
    
    offset = page*limit
    users = users_dao.get_users_by_page_by_order(current_session.get_account_entity(), offset, limit, order_by, asc)
    
    ret_json = "{ \"users\" : ["
    first = True
    for user in users:
      """ Do not send down anonymous user to be displayed """
      if user.userid == constants.ANONYMOUS_USER:
        continue
      
      if not first:
        ret_json += ","
      first = False
      ret_json += "{"
      ret_json += "\"userid\" : \"" + user.userid + "\","
      ret_json += "\"points\" : \"" + str(user.points) + "\","
      ret_json += "\"rank\" : \"" + str(user.rank) + "\""
      ret_json += "}"
    ret_json+= "]}"
    
    self.response.out.write(ret_json)
    
  
class ConsoleFeatures(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    current_session = Session().get_current_session(self)
    account = current_session.get_account_entity()
    email = current_session.get_email()
    
    """ Get widgets values """
    trophy_case_values = widgets_dao.get_trophy_case_properties_to_render(account)
    rank_values = widgets_dao.get_rank_properties_to_render(account)
    points_values = widgets_dao.get_points_properties_to_render(account)
    leaderboard_values = widgets_dao.get_leaderboard_properties_to_render(account)
    notifier_values = widgets_dao.get_notifier_properties_to_render(account)
    milestones_values = widgets_dao.get_milestones_properties_to_render(account)
    
    """ Preview urls """
    trophy_case_preview_url = ""
    rank_preview_url = ""
    points_preview_url = ""
    
    """ Notifier """
    if environment.is_dev():
      widget_path = constants.CONSOLE_GET_WIDGET_DEV
    else:
      widget_path = constants.CONSOLE_GET_WIDGET_PROD 
    widget_type = "notifier"
    userhash = hashlib.sha1(email + '---' + constants.ANONYMOUS_USER).hexdigest()
    notifier_str = "<div style='z-index:9999; overflow: hidden; position: fixed; bottom: 0px; right: 10px;'><iframe style='border:none;' allowtransparency='true' height='"+str(constants.NOTIFIER_SIZE_DEFAULT)+"px' width='"+str(constants.NOTIFIER_SIZE_DEFAULT)+"px' scrolling='no' src='" + widget_path + "?widget=" + widget_type + "&u=" + userhash + "&height=" +str(constants.NOTIFIER_SIZE_DEFAULT) + "&width="+str(constants.NOTIFIER_SIZE_DEFAULT)+"'>Sorry your browser does not support iframes!</iframe></div>"
    
    template_values = {'features_main' : True,
                       'account_name' : current_session.get_email(),
                       'trophy_case_values' : trophy_case_values,
                       'rank_values':rank_values,
                       'points_values':points_values,
                       'notifier_values': notifier_values,
                       'milestones_values': milestones_values,
                       'leaderboard_values':leaderboard_values,
                       'trophy_case_preview_url':trophy_case_preview_url,
                       'rank_preview_url':rank_preview_url,
                       'points_preview_url':points_preview_url,
                       'notifier': notifier_str}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_DASHBOARD, template_values))  

class ConsoleFeaturesUpdate(webapp2.RequestHandler):
  @account_login_required
  def post(self):
    """ Ajax call handler to save trophycase features """
    current_session = Session().get_current_session(self)
    
    property = self.request.get("property")
    new_value = self.request.get("propertyValue")
    entity_type = self.request.get("entityType")
    success = widgets_dao.update_widget_property(current_session.get_email(), entity_type, property, new_value)
    
    if success:
      self.response.out.write("Success")
    else:
      self.response.out.write("Failed")

class ConsoleFeaturesPreview(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    """ Ask for which widget, and then render that widget """
    widget = self.request.get("widget")
    current_session = Session().get_current_session(self)
    account = current_session.get_account_entity()
    
    if widget == "rank":
      widget_ref = account.rankWidget
      render_path = constants.TEMPLATE_PATHS.RENDER_RANK
    elif widget == "points":
      widget_ref = account.pointsWidget
      render_path = constants.TEMPLATE_PATHS.RENDER_POINTS
    elif widget == "leaderboard":
      widget_ref = account.leaderWidget
      render_path = constants.TEMPLATE_PATHS.RENDER_LEADERBOARD
    elif widget == "notifier":
      widget_ref = account.notifierWidget
      render_path = constants.TEMPLATE_PATHS.RENDER_NOTIFIER
    elif widget == "milestones":
      widget_ref = account.milestoneWidget
      render_path = constants.TEMPLATE_PATHS.RENDER_MILESTONES
    else:
      widget = "trophycase"
      widget_ref = account.trophyWidget
      render_path = constants.TEMPLATE_PATHS.RENDER_TROPHY_CASE  
      
    values = {"status":"success"}
    properties = widget_ref.properties()
    for property in properties:
      values[property] = getattr(widget_ref, property)
    
    
    show_with_data = self.request.get("withdata")
    if(show_with_data == "yes"):
      """ add appropriate dummy data """
      if widget == "trophycase":
        values["badges"] = self.getDummyBadges()
      elif widget == "rank":
        values["rank"] = str(format_integer(random.randint(1,1000)))
      elif widget == "points":
        values["points"] = str(format_integer(random.randint(1,10000)))
      elif widget == "leaderboard":
        pass
      elif widget == "notifier":
        pass
      elif widget == "milestones":
        pass  
      
    
    self.response.out.write(template.render(render_path, values))
  
  def getDummyBadges(self):
    """ Will return set of badges to be used for preview """
    badgeset = []
    for i in range(6):
      item = {"resource": "FakeResource-" + str(i),
              "downloadLink": "/images/badges/test"+str(i)+".png",
              "reason": "Reason" + str(i),
              "awardDate": datetime.datetime.now().strftime("%Y-%m-%d")}
      badgeset.append(item)
    return badgeset
  
class ConsoleFeaturesGetValue(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    """ Sleep here... on PROD we hare having race condition, try this out... """
    import time
    time.sleep(0.6)
    
    """ Look up value of "of" """
    current_session = Session().get_current_session(self)
    requested_value = self.request.get("of")
    entity_type = self.request.get("entityType")
    value = widgets_dao.get_single_widget_value(current_session.get_email(), entity_type, requested_value)
    self.response.out.write(value)
    

class ConsoleAnalytics(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    current_session = Session().get_current_session(self)
    template_values = {'analytics_main' : True,
                       'account_name' : current_session.get_email()}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_DASHBOARD, template_values))

class ConsoleDownloads(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    current_session = Session().get_current_session(self)
    template_values = {'downloads_main' : True,
                       'account_name' : current_session.get_email()}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_DASHBOARD, template_values))
    
class ConsolePreferences(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    """ handler for change password template """
    current_session = Session().get_current_session(self)
    template_values = {'preferences_main' : True,
                       'account_name' : current_session.get_email()}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_DASHBOARD, template_values))
    
  @account_login_required
  def post(self):
    """ will handle change of password request, will return success/fail """
    current_session = Session().get_current_session(self)
    email = current_session.get_email()
    
    old_password = self.request.get("oldpassword")
    new_password = self.request.get("newpassword")
    new_password_again = self.request.get("newpasswordagain")
    
    error_message = ""
    success = False
    if new_password != new_password_again:
      error_message = "Passwords do not match."
    else:
      """ Make sure that the account authenticates... this is a redundant check """
      if accounts_dao.authenticate_web_account(email, old_password):
        changed = accounts_dao.change_account_password(email, new_password)
        if changed:
          success = True
      else:
        error_message = "Old password incorrect."
  
    template_values = {"preferences_main" : True,
                       "password_change_attempted" : True,
                       'account_name' : email,
                       "error_message": error_message,
                       "password_changed" : success}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_DASHBOARD, template_values))

class ConsoleForgottenPassword(webapp2.RequestHandler):
  def get(self):
    """ handle forgotten password request """
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_FORGOTTEN_PASSWORD, None))

  def post(self):
    """ email posted, send a temporary password there """
    email = self.request.get("email")
    new_password = accounts_dao.reset_password(email)
    
    logging.info("Trying reset email to: " + str(email) + " temp password: " + str(new_password))
    success = False
    if new_password:
      """ send an email with new password """
      try:
        mail.send_mail(sender="UserInfuser <" + constants.APP_OWNER_EMAIL + ">",
                         to=email,
                         subject="UserInfuser Password Reset",
                         body= messages.get_forgotten_login_email(new_password))
        success = True
      except:
        logging.error("FAILED to send password reset email to: " + email)
        pass
    else:
      logging.error("Error for reset email to: " + str(email) + " temp password: " + str(new_password))
       
    values = {"success" : success,
              "response" : True}
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_FORGOTTEN_PASSWORD, values))
    
class ConsoleSignUp(webapp2.RequestHandler):
  def get(self):
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_SIGN_UP, None))
    
class ConsoleNotifierPreview(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    current_session = Session().get_current_session(self)
    account_entity = current_session.get_account_entity()
    email = account_entity.email
    
    """ notify anonymous account """
    
    userhash = hashlib.sha1(email + '---' + constants.ANONYMOUS_USER).hexdigest()
    user_ref = users_dao.get_user_with_key(userhash)
    
    notifier.user_badge_award(user_ref, "Preview Message", "/images/badges/test2.png", "Sample Title", account_entity, "anonymous_badge")
    self.response.out.write("done")

class ConsoleNewNotifierToken(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    current_session = Session().get_current_session(self)
    account_entity = current_session.get_account_entity()
    email = account_entity.email
    
    """ Notifier """
    if environment.is_dev():
      widget_path = constants.CONSOLE_GET_WIDGET_DEV
    else:
      widget_path = constants.CONSOLE_GET_WIDGET_PROD 
    widget_type = "notifier"
    userhash = hashlib.sha1(email + '---' + constants.ANONYMOUS_USER).hexdigest()
    notifier_str = "<div style='z-index:9999; overflow: hidden; position: fixed; bottom: 0px; right: 10px;'><iframe style='border:none;' allowtransparency='true' height='"+str(constants.NOTIFIER_SIZE_DEFAULT)+"px' width='"+str(constants.NOTIFIER_SIZE_DEFAULT)+"px' scrolling='no' src='" + widget_path + "?widget=" + widget_type + "&u=" + userhash + "&height=" +str(constants.NOTIFIER_SIZE_DEFAULT) + "&width="+str(constants.NOTIFIER_SIZE_DEFAULT)+"'>Sorry your browser does not support iframes!</iframe></div>"
    self.response.out.write(notifier_str)

class ReturnUserCount(webapp2.RequestHandler):
  def get(self):
    # TODO
    self.response.out.write("800")

class DeleteUser(webapp2.RequestHandler):
  @account_login_required
  def post(self):
    current_session = Session().get_current_session(self)
    account_entity = current_session.get_account_entity()
    email = account_entity.email
    user = self.request.get("id")
    if user == constants.ANONYMOUS_USER:
      json_ret = {"success":False,
                  "reason":"Sorry, you cannot delete this special user."}
      json_ret = json.dumps(json_ret)
      self.response.out.write(json_ret)
      return 
    json_ret = {'success':True,
                'reason':'Success. User has been deleted'}
    json_ret = json.dumps(json_ret)
    user_hash = hashlib.sha1(email + '---' + user).hexdigest()
    users_dao.delete_user(user_hash)
    self.response.out.write(json_ret)

class DeleteBadge(webapp2.RequestHandler):
  @account_login_required
  def post(self):
    current_session = Session().get_current_session(self)
    account_entity = current_session.get_account_entity()
    email = account_entity.email
    bk = self.request.get("bk")
    json_ret = {'success':True,
                'reason':'Success. Badge has been deleted'}
    json_ret = json.dumps(json_ret)
    try:
      bk = badges_dao.create_badge_key_with_id(email, bk)
      badges_dao.delete_badge(bk)
    except Exception, e:
      json_ret = {'success':False,
                'reason':'Unable to remove badge' + str(e)}
    self.response.out.write(json_ret)

class AddUser(webapp2.RequestHandler):
  @account_login_required
  def post(self):
    current_session = Session().get_current_session(self)
    account_entity = current_session.get_account_entity()
    email = account_entity.email
    new_user_id = self.request.get("id")
    if new_user_id == constants.ANONYMOUS_USER:
      self.redirect('/adminconsole/users?error=NoUserID')
      return 
    profile_name = self.request.get("name")
    profile_link = self.request.get("profile")
    profile_img = self.request.get("image")
    user_key = users_dao.get_user_key(email, new_user_id)
 
    new_user = Users(key_name=user_key,
                     userid=new_user_id,
                     isEnabled="yes",
                     accountRef=account_entity,
                     profileName=profile_name,
                     profileLink=profile_link,
                     profileImg=profile_img)
    users_dao.save_user(new_user, user_key)
    self.redirect('/adminconsole/users')

class AwardUser(webapp2.RequestHandler):
  @account_login_required
  def post(self):
    current_session = Session().get_current_session(self)
    account_entity = current_session.get_account_entity()
    email = account_entity.email
    ui = ui_api.UserInfuser(email, account_entity.apiKey, sync_all=True)

    user_id = self.request.get('userid')
    if not user_id:
      self.redirect('/adminconsole/users?error=NoUserID')
      return
    if user_id == constants.ANONYMOUS_USER:
      self.redirect('/adminconsole/users?error=InvalidID')
      return 
    if not users_dao.get_user(email, user_id):
      self.redirect('/adminconsole/users?error=InvalidID')
      return 
    award_type = self.request.get('awardtype')
    if award_type == 'awardbadge':
      badge_id = self.request.get("badgeid")
      if not badge_id:
        logging.error("Badge ID not provided %s"%email)
        self.redirect('/adminconsole/users?error=BadBadge')
      badge_key = badges_dao.get_key_from_badge_id(email, badge_id)
      if not badges_dao.get_badge(badge_key):
        logging.error("Badge ID does not exist for account %s"%email)
        self.redirect('/adminconsole/users?error=BadBadge')
      if not ui.award_badge(user_id, badge_id):
        self.redirect('/adminconsole/users?error=BadBadge')
        logging.error("Make sure the client code urls points to http://<app-id>.appspot.com if this is a custom deploy")
        logging.error("Account %s is unable to award badge %s to user %s"%(email, badge_id, user_id))
        self.redirect('/adminconsole/users?error=BadBadge')
    elif award_type == 'awardpoints': 
      points = self.request.get("points")
      try:
        points = int(points)
      except:
        points = 0
      if not ui.award_points(user_id, points):
        logging.error("Account %s is unable to award points %d to user %s"%(email, points, user_id))
        self.redirect('/adminconsole/users?error=InvalidID')
    else:
      logging.error("Received %s for console user award from account %s"%(award_type, email))
      self.redirect('/adminconsole/users?error=InvalidID')
      
    self.redirect('/adminconsole/users/edit?name=' + user_id)


app = webapp2.WSGIApplication([
  ('/adminconsole', Console),
  ('/adminconsole/users', ConsoleUsers),
  ('/adminconsole/users/edit', ConsoleEditUser),
  ('/adminconsole/users/count', ReturnUserCount),
  ('/adminconsole/users/fetch', ConsoleUsersFetch),
  ('/adminconsole/users/delete', DeleteUser),
  ('/adminconsole/users/award', AwardUser),
  ('/adminconsole/users/add', AddUser),
  ('/adminconsole/downloads', ConsoleDownloads),
  ('/adminconsole/features', ConsoleFeatures),
  ('/adminconsole/features/update', ConsoleFeaturesUpdate),
  ('/adminconsole/features/preview', ConsoleFeaturesPreview),
  ('/adminconsole/features/getvalue', ConsoleFeaturesGetValue),
  ('/adminconsole/badges', ConsoleBadges),
  ('/adminconsole/deletebadge', DeleteBadge),
  ('/adminconsole/preferences', ConsolePreferences),
  ('/adminconsole/forgot', ConsoleForgottenPassword),
  ('/adminconsole/signup', ConsoleSignUp),
  ('/adminconsole/analytics', ConsoleAnalytics),
  ('/adminconsole/notify', ConsoleNotifierPreview),
  ('/adminconsole/newnotifytoken', ConsoleNewNotifierToken)
], debug=constants.DEBUG)

"""
def main():
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
"""

########NEW FILE########
__FILENAME__ = constants
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os

# CHANGE THIS FOR CUSTOMER DEPLOYMENTS 
APP_NAME = "cloudcaptive-userinfuser" #os.environ['APPLICATION_ID']
APP_OWNER_EMAIL = "raj@cloudcaptive.com"

# Only valid for localhost testing
# Sign up twice with these accounts to get around the email validation
TEST_ACCOUNTS = ["raj@cloudcaptive.com","shanrandhawa@gmail.com","shan@cloudcaptive.com"]

ADMIN_ACCOUNT = "admin@" + APP_NAME + ".appspot.com"
DEBUG = True
ACCOUNT_TYPES = ["admin", "bronze", "silver", "gold", "platinum"]
PAYMENT_TYPES = ["free", "trial", "paid", "exempt"]
DEV_URL = "http://localhost:8080"
PRODUCTION_URL= "http://"+APP_NAME+".appspot.com"
SECURE_PRODUCTION_URL = "https://"+APP_NAME+".appspot.com"


"""
Use the following constants for generating widget previews on the admin console
These are API constants.
"""
CONSOLE_GET_WIDGET_DEV = "http://localhost:8080/api/1/getwidget"
CONSOLE_GET_WIDGET_PROD = "https://"+APP_NAME+".appspot.com/api/1/getwidget"


AES_ENCRYPTION_KEYNAME = "aes_encryption_key"
ENCRYPTION_KEYNAME = "encryption_key"

""" These are types which can not use the db methods directly and must
    use the memcache interface in serverside.entities.memcache_db. 
    These entities are used frequently and are thus memcached aggressively
    All others types may freely use the db.Model functions
"""
PROTECTED_DB_TYPES = ["Accounts", "Badges", "Users", "BadgeInstance", "BadgeImage", "TrophyCase", "Milestones", "Points", "Notifier", "Rank", "Leaderboard", "PassPhrase"]

class LOGGING:
  """ Logging events """
  CLIENT_EVENT = ["signin",
             "logout",
             "dropaccount",
             "startpayments",
             "upgrade",
             "downgrade",
             "dropuser",
             "addbadge",
             "removebadge",
             "error",
             "viewanalytics",
             "viewbadges",
             "signup",
             "test"]

  API_EVENT = ["awardpoints",
             "awardbadge",
             "awardbadgepoints",
             "badgeawarded", # if required badge points met
             "removebadge",
             "viewwidget",
             "prefetchwidget",
             "clickbadge",
             "updateuser",
             "loginuser",
             "createuser",
             "getuserdata",
             "notify_badge",
             "notify_points"]

  # Actual key is generated the first time the application is launched
  SECRET_KEYNAME = "secret_log_key"
  PATH = '/logevents'

class UPDATE:
  SECRET_KEYNAME = "secret_update_key"
  PATH = '/updateaccount'

class IMAGE_PARAMS:
  DEFAULT_SIZE = 150
  LEADER_SIZE = 90 
  VALID_EXT_TYPES = ['png','jpg','jpeg','gif','PNG','JPG','JPEG','GIF']
  # TODO Host these ourselves
  USER_AVATAR = "http://i.imgur.com/cXhDa.png"
  POINTS_IMAGE = "http://cdn1.iconfinder.com/data/icons/nuove/128x128/actions/edit_add.png"
  LOGIN_IMAGE = "http://www.iconfinder.com/icondetails/8794/128/cryptography_key_lock_log_in_login_password_security_icon" 

class API_ERROR_CODES:
  NOT_AUTH = 1 # Not authorized error, either bad account or api key
  BADGE_NOT_FOUND = 2
  USER_NOT_FOUND = 3
  INTERNAL_ERROR = 4 
  BAD_ARGS = 5
  BAD_USER = 6

class ACCOUNT_STATUS:
  """Enum(ish) of account status"""
  
  ENABLED = "enabled"
  PENDING_CREATE = "pending_create"
  DISABLED = "disabled"
  RANGE_OF_VALUES = [ENABLED,
                     PENDING_CREATE,
                     DISABLED]

class TEMPLATE_PATHS:
  CONSOLE_LOGIN = os.path.join(os.path.dirname(__file__), '../static/console_templates/login.html')
  CONSOLE_FORGOTTEN_PASSWORD = os.path.join(os.path.dirname(__file__), '../static/console_templates/forgot.html')
  CONSOLE_DASHBOARD =  os.path.join(os.path.dirname(__file__), '../static/console_templates/dashboard.html')
  CONSOLE_USERS =  os.path.join(os.path.dirname(__file__), '../static/console_templates/users.html')
  CONSOLE_SIGN_UP =  os.path.join(os.path.dirname(__file__), '../static/console_templates/signup_console.html')
  
  RENDER_TROPHY_CASE = os.path.join(os.path.dirname(__file__), 'api/widgets/v1.0/trophy_case.html')
  RENDER_NOTIFIER = os.path.join(os.path.dirname(__file__), 'api/widgets/v1.0/notifier.html')
  RENDER_MILESTONES = os.path.join(os.path.dirname(__file__), 'api/widgets/v1.0/milestones.html')
  RENDER_POINTS = os.path.join(os.path.dirname(__file__), 'api/widgets/v1.0/points.html')
  RENDER_RANK = os.path.join(os.path.dirname(__file__), 'api/widgets/v1.0/rank.html')
  RENDER_LEADERBOARD = os.path.join(os.path.dirname(__file__), 'api/widgets/v1.0/leaderboard.html')

class WEB_ADMIN_PARAMS:
  """Several standardized parameters used to keep track of authentication and sessions on web """
  COOKIE_EMAIL_PARAM = "key" # simply email, however, we don't want people their address is set in the cookie
  COOKIE_KEY_PARAM = "ssid" # same as the cookie_key param in our Accounts DB
  COOKIE_EXPIRATION = "esid" # expiration
  VALID_FOR_SECONDS = 86400 # make session valid for a day 

class WEB_SIGNUP_URLS:
  """Since we want to mask appspot from the URL we cannot have redirects to relative paths when deployed"""
  POST_DATA = ""
  ACTIVATE_URL = ""
  REDIRECT_SIGNUP_SUCCESS = ""
  REDIRECT_SIGNUP_FAIL = ""
  REDIRECT_ACTIVATE_SUCCESS = ""
  REDIRECT_ACTIVATE_FAIL = ""
  REDIRECT_HOME = ""
  REDIRECT_SIGNUP = ""
  
  if os.environ["SERVER_SOFTWARE"].find("Development") != -1:
    POST_DATA = "/signup"
    ACTIVATE_URL = "/signup"
    REDIRECT_SIGNUP_SUCCESS = "/html/signup_success.html"
    REDIRECT_SIGNUP_FAIL = "/html/signup_failed.html"
    REDIRECT_ACTIVATE_SUCCESS = "/html/activation_success.html"
    REDIRECT_ACTIVATE_FAIL = "/html/activation_fail.html"
    REDIRECT_HOME = "/html/index.html"
    REDIRECT_SIGNUP = "/html/signup.html"
  else:
    POST_DATA = SECURE_PRODUCTION_URL + "/signup" # need to use https URL for posting credentials
    ACTIVATE_URL = SECURE_PRODUCTION_URL + "/signup"
    REDIRECT_SIGNUP_SUCCESS = PRODUCTION_URL + "/html/signup_success.html"
    REDIRECT_SIGNUP_FAIL = PRODUCTION_URL + "/html/signup_failed.html"
    REDIRECT_ACTIVATE_SUCCESS = PRODUCTION_URL + "/html/activation_success.html"
    REDIRECT_ACTIVATE_FAIL = PRODUCTION_URL + "/html/activation_fail.html"
    REDIRECT_HOME = PRODUCTION_URL + "/html/index.html"
    REDIRECT_SIGNUP = PRODUCTION_URL + "/html/signup.html"
  
  

# This is only for localhost testing, not valid for production
ADMINPASSWD = "u8u8u9i9i"
ADMINKEY = "u8u89i9i"

VALID_WIDGETS = ["trophy_case", "notifier", "milestones", "points", "leaderboard", "rank"]
WIDGETS_THAT_DONT_NEED_A_USER = ["milestones", "leaderboard"]
ANONYMOUS_USER = "__ui__anonymous__"
LOCAL_URL = "http://localhost:8080/"
MAX_BADGE_SIZE = 2<<16 # 128k
NOTIFIER_SIZE_DEFAULT = 180
NOT_RANKED = -1 # For unranked users
NUMBER_RANKED = "10000" #Anyone not in the top 10k is not ranked
TOP_USERS = "10"


########NEW FILE########
__FILENAME__ = accounts_dao
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Feb 14, 2011

psuedo DAO methods

@author: shan
'''
from serverside.constants import ACCOUNT_STATUS
from serverside.entities import memcache_db
from serverside.entities.accounts import Accounts
from serverside.entities.widgets import TrophyCase, Points, Rank, Notifier, \
  Leaderboard, Milestones
from serverside import constants 
from serverside.tools import utils
from serverside.dao import users_dao
import hashlib
import logging
import uuid


def create_account(email, 
                   password, 
                   enable=False,
                   account_type="bronze",
                   payment_type="free"):
  """
  Creates an account with all the other needed dependencies properly initialized.
  """
  
  
  """
  Required:
  email = db.EmailProperty(required=True)
  password = db.StringProperty(required=True);
  isEnabled = db.StringProperty(required=True, choices=ACCOUNT_STATUS.RANGE_OF_VALUES)
  accountType = db.StringProperty(required=True, choices=set(ACCOUNT_TYPES)) 
  paymentType = db.StringProperty(required=True,choices=set(PAYMENT_TYPES))
  cookieKey = db.StringProperty(required=True)
  apiKey = db.StringProperty(required=True)
  trophyWidget = db.ReferenceProperty(required=True, reference_class=TrophyCase)
  pointsWidget = db.ReferenceProperty(required=True, reference_class=Points)
  rankWidget = db.ReferenceProperty(required=True, reference_class=Rank)
  """
  
  new_trophy_case = TrophyCase(key_name=email)
  memcache_db.save_entity(new_trophy_case, email)

  new_rank = Rank(key_name=email)
  memcache_db.save_entity(new_rank, email)

  new_points = Points(key_name=email)
  memcache_db.save_entity(new_points, email)

  new_notifier = Notifier(key_name=email)
  memcache_db.save_entity(new_notifier, email)
 
  new_leader = Leaderboard(key_name=email)
  memcache_db.save_entity(new_leader, email)
  
  new_milestones = Milestones(key_name=email)
  memcache_db.save_entity(new_milestones, email)
  
  """ Generate an API key """
  api_key = str(uuid.uuid4())
  
  """ Hash the password """
  hashed_password = hashlib.sha1(password).hexdigest()
  
  enable_account = ACCOUNT_STATUS.PENDING_CREATE
  if enable:
    enable_account = ACCOUNT_STATUS.ENABLED
  
  newacc = Accounts(key_name = email,
                      email = email,
                      password = hashed_password,
                      isEnabled = enable_account,
                      accountType = account_type,
                      paymentType = payment_type,
                      apiKey = api_key,
                      cookieKey = "xxxxxxxxxxxxxx",
                      trophyWidget = new_trophy_case,
                      pointsWidget = new_points,
                      rankWidget = new_rank,
                      notifierWidget = new_notifier,
                      leaderWidget = new_leader,
                      milestoneWidget = new_milestones)
  
  try:
    memcache_db.save_entity(newacc, email)
  except:
    logging.error("Failed to create account")
 
  users_dao.create_new_user(email, constants.ANONYMOUS_USER)
 
  return newacc


def authenticate_web_account(account_id, password):
  entity = memcache_db.get_entity(account_id, "Accounts")
  if entity != None and entity.password == hashlib.sha1(password).hexdigest() and entity.isEnabled == ACCOUNT_STATUS.ENABLED:
    return entity
  else:
    return None

def authenticate_web_account_hashed(account_id, hashedpassword):
  entity = memcache_db.get_entity(account_id, "Accounts")
  if entity != None and entity.password == hashedpassword and entity.isEnabled == ACCOUNT_STATUS.ENABLED:
    return entity
  else:
    return None   
  
def change_account_password(email, new_password):
  """ Change value in data store, also do hashing """
  values = {"password" : hashlib.sha1(new_password).hexdigest()}
  
  try:
    memcache_db.update_fields(email, "Accounts", values)
    return True
  except:
    logging.info("Password change failed.")
    return False
  
def reset_password(email):
  """
  Generates a random password for the account, and saves into account.
  Returns the new password.
  Returns None if account lookup/update fails
  """
  account_entity = memcache_db.get_entity(email, "Accounts")
  ret = None
  if account_entity:
    random_str = utils.generate_random_string(8)
    if change_account_password(email, random_str):
      ret = random_str
    else:
      logging.info("Unable to change password.")
  else:
    logging.info("Password cannot be reset, account was not located.")
      
  return ret

def authorize_api(account_id, api_key):
  """
  return the account on success, non on failure
  """
  acc = None
  try:
    acc = memcache_db.get_entity(account_id, "Accounts")
  except:
    logging.error("Error getting account with key %s"%account_id)
    return None
  if not acc:
    logging.error("Permission error with null  account")
    return None
  if acc.apiKey != api_key or acc.isEnabled != constants.ACCOUNT_STATUS.ENABLED:
    logging.error("Permission error with %s account with %s api key versus %s"\
                  %(account_id, api_key, acc.apiKey))
    return None
  return acc

def delete_account(acc_key):
  memcache_db.delete_entity_with_key(acc_key, "Leaderboard")
  memcache_db.delete_entity_with_key(acc_key, "TrophyCase")
  memcache_db.delete_entity_with_key(acc_key, "Points")
  memcache_db.delete_entity_with_key(acc_key, "Rank")
  return memcache_db.delete_entity_with_key(acc_key, "Accounts")

def save(acc_ref):
  memcache_db.save_entity(acc_ref, acc_ref.key().name())

def get_all_accounts():
  accounts = []
  aset = Accounts.all()
  for a in aset:
    accounts.append(get(a.email))
  return accounts
  

def get(acc_key):
  return memcache_db.get_entity(acc_key, "Accounts")

########NEW FILE########
__FILENAME__ = badges_dao
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Feb 28, 2011

psuedo DAO methods

@author: shan
'''
from serverside.entities.users import Users
from serverside.entities.badges import Badges
from serverside.entities.badges import BadgeInstance
from serverside.entities.badges import BadgeImage
from serverside.entities import memcache_db
from serverside import constants
from serverside import environment
from google.appengine.ext import db
from google.appengine.ext import blobstore
from google.appengine.api import images
import logging
import string
import hashlib
import datetime

def get_full_link(relative_path):
  """ 
  Returns the full link for a given badge (dev vs production)
  """
  
  if relative_path.startswith("http"):
    # already full
    return relative_path

  if environment.is_dev():
    return constants.LOCAL_URL + relative_path
  else:
    return constants.PRODUCTION_URL + relative_path

def get_all_badges_for_account(account):
  """
  Will return all badges per the account, ordered by theme
  """
  
  return Badges.gql("WHERE creator=:1 ORDER BY theme", account)

def create_badge_key(email, badge_theme, badge_name, permission):
  if permission == "public":
    email = constants.ADMIN_ACCOUNT
  emailHash = hashlib.sha1(email).hexdigest()
  badge_key = emailHash + "-" + badge_theme + "-" + badge_name + "-" + permission
  return badge_key

def create_badge_key_with_id(email, bk_id):
  emailHash = hashlib.sha1(email).hexdigest()
  badge_key = emailHash + "-" + bk_id
  return badge_key

def create_badge_type(badge_key, 
                      badge_name, 
                      badge_des, 
                      account, 
                      badge_theme, 
                      img_type,
                      imgbuf=None,
                      blob_info=None,
                      perm="private",
                      btype="free", 
                      stype="blob", 
                      is_enabled="yes"):
  """
  Storage is either using a BadgeImage or through the blobstore api for 
  faster and cheaper serving of images
  """
  blob_key = None
  storage_type = "blob"
  badge_image = None
  download_link = ""
  if imgbuf:
    storage_type = "db"
    badge_image = create_badge_image(badge_key, perm, account, imgbuf, img_type)
    download_link = get_full_link("badge/d?bk=" + badge_key)
  elif blob_info:
    storage_type = "blob"
    blob_key = blob_info.key()  
    download_link = images.get_serving_url(str(blob_key))
    logging.info("Badge serving url:" + str(download_link))
  else:
    logging.error("Create badge type error: No image to save for badge type") 
    raise

  badge = Badges(key_name=badge_key,
                 name=badge_name,
                 altText=badge_des,
                 description=badge_des,
                 setType=btype,
                 isEnabled=is_enabled,
                 creator=account,
                 permissions=perm,
                 storageType=storage_type,
                 imageKey=badge_image,
                 blobKey=blob_key,
                 downloadLink=download_link, 
                 theme=badge_theme)
  # Store it as a badge image
  memcache_db.save_entity(badge, badge_key)
  return badge

def create_badge_instance(badge_instance_key, 
                          badge_ref, 
                          user_ref,
                          isawarded, 
                          points, 
                          points_needed, 
                          perm, 
                          link,
                          reason,
                          expiration=None):
  if isawarded == "yes":
    date = datetime.date.today()
    datet = datetime.datetime.now()
  else:
    date = None
    datet = None
  if date:
    new_badge_instance = BadgeInstance(key_name=badge_instance_key,
                                       badgeRef=badge_ref,
                                       userRef=user_ref,
                                       awarded=isawarded,
                                       pointsEarned=points,
                                       pointsRequired=points_needed,
                                       permissions=perm,
                                       downloadLink=link,
                                       reason=reason,
                                       awardDate = date,
                                       awardDateTime = datet)
  else:
    new_badge_instance = BadgeInstance(key_name=badge_instance_key,
                                       badgeRef=badge_ref,
                                       userRef=user_ref,
                                       awarded=isawarded,
                                       pointsEarned=points,
                                       pointsRequired=points_needed,
                                       permissions=perm,
                                       downloadLink=link,
                                       reason=reason)

  memcache_db.save_entity(new_badge_instance, badge_instance_key)
              
  return new_badge_instance

def create_badge_image(badge_key, perm, acc, imgbuf, img_type):
  badge_img = BadgeImage(key_name=badge_key,
                        permissions = perm,
                        creator=acc,
                        image=imgbuf,
                        imgType = img_type) 
  memcache_db.save_entity(badge_img, badge_key)
  return badge_img

def update_badge_instance(badge_key, diction, incr_fields):
  # Get the old one, and if it was just now awarded set the date/time
  if 'awarded' in diction and diction['awarded'] == "yes":
    try:
      badge_ref = memcache_db.get_entity(badge_instance_key, "BadgeInstance")
      if badge_ref and badge_ref.awarded == "no":
        diction['awardDate'] = datetime.date.today()
        diction['awardDateTime'] = datetime.datetime.now()
    except:
      diction['awardDate'] = datetime.date.today()
      diction['awardDateTime'] = datetime.datetime.now()
  return memcache_db.update_fields(badge_key, "BadgeInstance",
                         fields=diction, increment_fields=incr_fields)

def get_rendereable_badgeset(account):
  """
  Will return a badgset as follows:
  theme
   -badgeset
    name
    description
    alt
    key
    perm(issions)
  """
  badges = get_all_badges_for_account(account)
  badgeset = []
  
  for b in badges:
    """ Badge id is theme-name-perm. spaces and " " become "-" """
    name_for_id = string.replace(b.name, " ", "_")
    name_for_id = string.replace(name_for_id, "-", "_")
    
    theme_for_id = string.replace(b.theme, " ", "_")
    theme_for_id = string.replace(theme_for_id, "-", "_")
    
    badge_id = theme_for_id + "-" + name_for_id + "-" + b.permissions 
  
    item = {"name": b.name,
            "description": b.description,
            "alt":b.altText,
            "key":b.key().name(),
            "perm":b.permissions,
            "theme" : b.theme,
            "id": badge_id,
            "downloadLink":b.downloadLink}
    badgeset.append(item)
  return badgeset
    
def get_themes(account):
  """
  Will return a list with all the themes for this account
  """
  
  all_themes = Badges.gql("WHERE creator=:1", account)
  
  """ Go through the list and remove redundancies """
  theme_set = []
  previous_theme = ""
  for theme in all_themes:
    if theme.theme != previous_theme:
      theme_set.append(theme.theme)
      previous_theme = theme.theme
  
def get_badge(badge_key):
  """
  Returns the reference to a badge, otherwise logs an error
  """
  badge_ref = None
  try:
    badge_ref = memcache_db.get_entity(badge_key, "Badges")
  except:
    logging.error("badges_dao: Error getting badge type with key %s"%badge_key)
  return badge_ref
 
def get_user_badges(user_ref):
  """
  Get a user's registered badges (both awarded and not awarded)
  """
  if user_ref:
    return db.GqlQuery("SELECT * FROM BadgeInstance WHERE userRef=:1", user_ref)
  else:
    return []

def get_badge_instance_key(badge_key, user_id):
  """
  Instance keys are like badge keys but have the user id prepended
  """
  return user_id + "-" + badge_key

def get_badge_instance(badge_instance_key):
  badge_ref = None
  try:
    badge_ref = memcache_db.get_entity(badge_instance_key, "BadgeInstance")
  except:
    logging.error("badges_dao: Error getting badge type with key %s"%badge_key)
    raise
  return badge_ref

def get_key_from_badge_id(account_id, badge_id):
  """ 
  Create a badge key from an account id and badgeref
  """
  tokens = badge_id.split('-')
  if len(tokens) != 3:
    logging.error("Incorrect number of tokens during parsing. %s, for account id %s for badge %s"%\
          (str(tokens), account_id, badge_id))
    return None
  badge_theme = tokens[0]
  badge_name = tokens[1]
  perm = tokens[2]
  if perm == "public":
    email = constants.ADMIN_ACCOUNT
  elif perm == "private":
    email = account_id
  else:
    logging.error("Perm of %s for account %s and badge id of %s"%(perm, account_id, badge_id))
    return None
  return create_badge_key(email, badge_theme, badge_name, perm)

def get_badge_key_permission(badge_key):
  """
  This function works for Badges and BadgeInstance types
  """
  tokens = badge_key.split('-')
  perm = tokens[-1]
  return perm

def get_badge_id_from_instance_key(instance_key):
  return instance_key.split('-',2)[2]

def get_badge_name_from_instance_key(instance_key):
  return instance_key.split('-')[2]

def get_badge_image(badge_key):
  return memcache_db.get_entity(badge_key, "BadgeImage")

def delete_badge(badge_key):
  return memcache_db.delete_entity_with_key(badge_key, "Badges")

def delete_badge_instance(badge_instance_key): 
  return memcache_db.delete_entity_with_key(badge_instance_key, "BadgeInstance")

def delete_badge_image(badge_image_key):
  return memcache_db.delete_entity_with_key(badge_image_key, "BadgeImage")

def delete_badge_blob(badge_key):
  badge = memcache_db.get_entity(badge_key, "Badges")
  if badge.blobKey:
    blob_key = badge.blobKey
    blob = BlobInfo.get(blob_key)
    blob.delete()

def add_resource_link(badge_key, url):
  diction = {'resourceLink':url}
  return memcache_db.update_fields(badge_key, "Badges",
                         fields=diction)
    
def add_expiration(badge_key, date):
  diction = {'expiration':date}
  return memcache_db.update_fields(badge_key, "Badges",
                         fields=diction)

########NEW FILE########
__FILENAME__ = logs_dao
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Feb 24, 2011

DAO methods for logging. Calls paths for logging events.

@author: Raj
'''
from serverside.entities.logs import Logs
from google.appengine.api import urlfetch

import logging
import random
import string
def gen_random(length):
  return ''.join(random.choice(string.letters) for i in xrange(length))

def save_log(diction):
  if "event" not in diction:
    logging.error("No event type in log")
    return
  key = gen_random(20)
  newlog = Logs(key_name=key, event=diction['event'])
  props = newlog.properties()
  for ii in diction:
    if ii in props:
       setattr(newlog, ii, diction[ii])
  newlog.put()

########NEW FILE########
__FILENAME__ = passphrase_dao
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on April 18, 2011

DAO methods for secrets. 
This way we generate secrets on startup and don't have to comb the code
when open sourcing it. It's a db read cost, but memcache should
amortize that cost. 

@author: Raj
'''
from serverside.entities import memcache_db
from serverside.entities.passphrase import PassPhrase
from serverside import constants
import logging
import string 
import random 
def gen_random(length):
  return ''.join(random.choice(string.letters) for i in xrange(length))
 
def get_log_secret():
  secret = memcache_db.get_entity(constants.LOGGING.SECRET_KEYNAME, "PassPhrase")
  if not secret: 
    phrase = gen_random(16)
    ent = PassPhrase(key_name=constants.LOGGING.SECRET_KEYNAME, secret=phrase)
    memcache_db.save_entity(ent, constants.LOGGING.SECRET_KEYNAME)
    return phrase
  else:
    return secret.secret

def get_update_secret():
  secret = memcache_db.get_entity(constants.UPDATE.SECRET_KEYNAME, "PassPhrase")
  if not secret: 
    phrase = gen_random(16)
    ent = PassPhrase(key_name=constants.UPDATE.SECRET_KEYNAME, secret=phrase)
    memcache_db.save_entity(ent, constants.UPDATE.SECRET_KEYNAME)
    return phrase
  else:
    return secret.secret


def get_encrypt_secret():
  secret = memcache_db.get_entity(constants.ENCRYPTION_KEYNAME, "PassPhrase")
  if not secret: 
    phrase = gen_random(8) #must be 8 characters long
    ent = PassPhrase(key_name=constants.ENCRYPTION_KEYNAME, secret=phrase)
    memcache_db.save_entity(ent, constants.ENCRYPTION_KEYNAME)
    return phrase
  else:
    return secret.secret

def get_aes_encrypt_secret():  
  secret = memcache_db.get_entity(constants.AES_ENCRYPTION_KEYNAME, "PassPhrase")
  if not secret: 
    phrase = gen_random(16) # must be 16 chars long
    ent = PassPhrase(key_name=constants.AES_ENCRYPTION_KEYNAME, secret=phrase)
    memcache_db.save_entity(ent, constants.AES_ENCRYPTION_KEYNAME)
    return phrase
  else:
    return secret.secret

########NEW FILE########
__FILENAME__ = pending_create_dao
'''
Created on May 8, 2011

@author: shan
'''
from serverside.entities.pending_create import Pending_Create

def get_id_by_email(email):
  return Pending_Create.gql("WHERE email = :1", email).get()

########NEW FILE########
__FILENAME__ = users_dao
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Feb 24, 2011

psuedo DAO methods

@author: shan
'''
from serverside.entities.users import Users
from serverside.entities.accounts import Accounts
from serverside.entities import memcache_db
from serverside import constants 
from serverside.dao import badges_dao
import logging
import hashlib 
class ORDER_BY:
  CREATION_DATE = 1
  POINTS = 2
  RANK = 3
  USER_ID = 4
  PROFILE_NAME = 5
  BADGE_COUNT = 6

def get_user(account_id, user_id):
  user_ref = None
  user_key = get_user_key(account_id, user_id)
  try:
    user_ref = memcache_db.get_entity(user_key, "Users")
  except:
    logging.error("Error getting key %s for user %s and account %s"%\
          (user_key, user_id, account_id))
    return None
  return user_ref 

def get_users_by_page_by_order(account, offset, limit, order_by, asc = "ASC"):
  """
  Retrieve chunks of users from users table by specifying offset
  """
  logging.info("Retrieving users for account: " + account.email + " and ordering by: " + order_by)
  users = Users.gql("WHERE accountRef = :1 ORDER BY " + order_by + " " + asc, account).fetch(limit, offset)
  
  return users

def get_users_by_page(account, offset, limit, order_by = "userid"):
  return get_users_by_page_by_order(account, offset, limit, order_by)


def create_new_user(account_id, user_id):
  """
  Create a new user entity and save
  Look up account with account_id and use in reference when creating new user 
  """
  account_entity = memcache_db.get_entity(account_id, "Accounts")
  
  user_key= get_user_key(account_id, user_id)
  new_user = Users(key_name=user_key,
                   userid=user_id,
                   isEnabled="yes",
                   accountRef=account_entity)
  
  try:
    memcache_db.save_entity(new_user, user_key)
  except:
    logging.error("Error saving new user entity")
    return  
  
def get_account_from_user(user_ref):
  acc = None
  if user_ref:
    try:
      if user_ref.accountRef:
        acc = user_ref.accountRef
        if not acc.isEnabled:
          logging.error("User accessing disabled account for %s"%acc.key().name())
    except:
      logging.error("User reference with key %s lacks an account"%user_ref.key().name())
  return acc

def get_user_key(account_id, user_id):
  """
  We have to have the user key so that when a widget request comes in
  the user and account info are not attainable from just the hash 
  """
  return hashlib.sha1(account_id + '---' + user_id).hexdigest()


def get_user_with_key(user_key):
  user_ref = None
  try:
    user_ref = memcache_db.get_entity(user_key, "Users")
  except:
    logging.error("Error getting key %s"%\
          (user_key))
    return None
  return user_ref

def get_or_create_user(account_id, user_id, acc_ref):
  """
  Create the user if it doesnt exist
  """
  user_ref = get_user(account_id, user_id)
  if not user_ref:
    # insert a new user, but lacking optional fields
    user_key= get_user_key(account_id, user_id)
    new_user = Users(key_name=user_key,
                     userid=user_id,
                     isEnabled="yes",
                     accountRef=acc_ref)
    try:
      memcache_db.save_entity(new_user, user_key)
    except:
      logging.error("Error saving user with key %s, userid %s for account %s"%\
             (user_key, user_id, account_id))
      return None
    user_ref = get_user(account_id, user_id)
    if not user_ref:
      logging.error("Error getting user with key %s, userid %s for account %s"%\
           (user_key, user_id, account_id))
      return None
  return user_ref

def save_user(user_ref, user_key):
  return memcache_db.save_entity(user_ref, user_key)

def update_user(user_key, dict, incr_fields):
  return memcache_db.update_fields(user_key, "Users", fields=dict, increment_fields=incr_fields)

def delete_user(user_key):
  user_ref = get_user_with_key(user_key)
  if not user_ref:
    logging.error("Unable to get user with key: " + str(user_key))
    return 

  badges = badges_dao.get_user_badges(user_ref)
  for b in badges:
    badges_dao.delete_badge_instance(b.key().name())

  return memcache_db.delete_entity_with_key(user_key, "Users")

def set_user_points(account_id, user_id, points):
  fields = {"points" : points}
  user_key = get_user_key(account_id, user_id)
  return memcache_db.update_fields(user_key, "Users", fields)
 

########NEW FILE########
__FILENAME__ = widgets_constants
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Feb 23, 2011

@author: shan
'''


COLOR_PROPERTY = "color"
BOOLEAN_PROPERTY = "boolean"
INT_PROPERTY = "int"
FONT_PROPERTY = "font"
FLOAT_PROPERTY = "float"
TEXT_PROPERTY = "text"
STYLE_PROPERTY = "style"

FONT_PROPERTY_RANGE = ["arial",
                       "arial black",
                       "comic sans ms",
                       "courier",
                       "courier new",
                       "georgia", 
                       "helvetica",
                       "impact",
                       "palatino",
                       "times new roman",
                       "trebuchet ms",
                       "verdana"]

FLOAT_PROPERTY_RANGE = ["left",
                       "right",
                       "none"]

STYLE_PROPERTY_RANGE = ["none",
                        "hidden",
                        "dotted",
                        "dashed",
                        "solid",
                        "double",
                        "groove",
                        "ridge",
                        "inset",
                        "outset"]

class PROPERTY_OF:
  """Enum(ish) of trophy case properties of properties"""
  
  backgroundColor = COLOR_PROPERTY
  borderThickness = INT_PROPERTY
  borderColor = COLOR_PROPERTY
  borderStyle = STYLE_PROPERTY
  height = INT_PROPERTY
  width = INT_PROPERTY
  hasRoundedCorners = BOOLEAN_PROPERTY
  titleBackgroundColor = COLOR_PROPERTY
  displayTitle = BOOLEAN_PROPERTY
  title = TEXT_PROPERTY
  titleColor = COLOR_PROPERTY
  titleSize = INT_PROPERTY
  titleFont = FONT_PROPERTY
  titleFloat = FLOAT_PROPERTY
  displayDate = BOOLEAN_PROPERTY
  dateColor = COLOR_PROPERTY
  dateSize = INT_PROPERTY
  dateFont = FONT_PROPERTY
  dateFloat = FLOAT_PROPERTY
  displayReason = BOOLEAN_PROPERTY
  reasonColor = COLOR_PROPERTY
  reasonSize = INT_PROPERTY
  reasonFont = FONT_PROPERTY
  reasonFloat = FLOAT_PROPERTY
  allowSorting = BOOLEAN_PROPERTY
  imageSize = INT_PROPERTY 
  scrollable = BOOLEAN_PROPERTY
  displayNoBadgesMessage = BOOLEAN_PROPERTY
  noBadgesMessage = TEXT_PROPERTY
  noBadgesFont = FONT_PROPERTY
  noBadgesSize = INT_PROPERTY
  noBadgesFloat = FLOAT_PROPERTY
  noBadgesColor = COLOR_PROPERTY

########NEW FILE########
__FILENAME__ = widgets_dao
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Feb 14, 2011

psuedo DAO methods and data access utilities

@author: shan
'''
from serverside.entities.widgets import TrophyCase
from serverside.entities.widgets import Rank
from serverside.entities.widgets import Points
from serverside.entities.widgets import Notifier
from serverside.entities.widgets import Leaderboard
from serverside.entities.widgets import Milestones
from serverside.entities import memcache_db
from serverside.dao import accounts_dao
from serverside.tools import utils
import logging


def get_trophy_case(key):
  """
  return corresponding trophy case entity
  
  This function seems unnecesary, but later we might need to do additional checking
  An effort to standardize data access
  """  
  logging.info("retrieving trophy case for account: " + key)
  return memcache_db.get_entity(key, "TrophyCase")

def update_widget_property(email, entity_name, property_name, property_value):
  """
  Saves desired property with new value for the specified entity type
  """
  
  """
  Check to see if the value string is a number or boolean
  """
  logging.info("Try to persist value, but first find out what it is!")
  try:
    value = long(property_value)
    update_fields = { property_name : value }
    memcache_db.update_fields(email, entity_name, update_fields)
    logging.info("Seems to be a number")
    return True
  except:
    try:
      bool_value = bool(property_value)
      if property_value == "True":
        update_fields = { property_name : True }
      else:
        update_fields = { property_name : False }
      memcache_db.update_fields(email, entity_name, update_fields)
      logging.info("Seems to be a boolean")
      return True
    except:
      try:
        update_fields = { property_name : property_value }
        memcache_db.update_fields(email, entity_name, update_fields)
        logging.info("Seems to be a string")
        return True
      except:
        return False
      
      

def update_trophy_property(email, property_name, property_value):
  """
  Saves desired property with new value
  """
  
  return update_widget_property(email, "TrophyCase", property_name, property_value)

def get_single_trophy_case_value(key, value_name):
  tcase_entity = get_trophy_case(key)
  if tcase_entity != None:
    value = str(tcase_entity.__getattribute__(str(value_name)))
    if value != None:
      return value
    else:
      return "Error"
  else:
    return "Error"


def get_single_widget_value(key, entity_name, value_name):
  widget_entity = memcache_db.get_entity(key, entity_name)
  if widget_entity != None:
    value = str(widget_entity.__getattribute__(str(value_name)))
    if value != None:
      return value
    else:
      return "Error"
  else:
    return "Error"
    

def get_trophy_case_properties_to_render(email):
  return get_values("TrophyCase", email, TrophyCase.properties())

def get_rank_properties_to_render(email):
  return get_values("Rank", email, Rank.properties())

def get_points_properties_to_render(email):
  return get_values("Points", email, Points.properties())
    
def get_notifier_properties_to_render(email):
  return get_values("Notifier", email, Notifier.properties())

def get_milestones_properties_to_render(email):
  return get_values("Milestones", email, Milestones.properties())

def get_leaderboard_properties_to_render(email):
  return get_values("Leaderboard", email, Leaderboard.properties())

def create_widget_for_account_by_email(widget_name, email):
  """
  Creates a new widget for the account, will return widget object if success, else it will return None
  """
  new_widget = None
  property_name = None
  if widget_name == "TrophyCase":
    new_widget = TrophyCase(key_name=email)
    property_name = "trophyWidget"
  elif widget_name == "Rank":
    new_widget = Rank(key_name=email)
    property_name = "rankWidget"
  elif widget_name == "Points":
    new_widget = Points(key_name=email)
    property_name = "pointsWidget"
  elif widget_name == "Notifier":
    new_widget = Notifier(key_name=email)
    property_name = "notifierWidget"
  elif widget_name == "Milestones":
    new_widget = Milestones(key_name=email)
    property_name = "milestoneWidget"
  elif widget_name == "Leaderboard":
    new_widget = Leaderboard(key_name=email)
    property_name = "leaderWidget"
    
  if new_widget!= None:
    memcache_db.save_entity(new_widget, email)
    update_fields = { property_name : new_widget }
    memcache_db.update_fields(email, "Accounts", update_fields)
  else:
    logging.info("Unable to create widget because widget type unknown: " + widget_name)
    
  return new_widget

def get_widget_for_account(account, widget_name):
  ret_widget = None
  if widget_name == "TrophyCase":
    ret_widget = account.trophyWidget
  elif widget_name == "Rank":
    ret_widget = account.rankWidget
  elif widget_name == "Points":
    ret_widget = account.pointsWidget
  elif widget_name == "Notifier":
    ret_widget = account.notifierWidget
  elif widget_name == "Milestones":
    ret_widget = account.milestoneWidget
  elif widget_name == "Leaderboard":
    ret_widget = account.leaderWidget
  return ret_widget
      
def get_values(widget_entity_name, account, properties):
  """
  Utility method to generate editable values dynamically.
  Using this method is pure laziness. If we want cool drop
  downs and color pickers we need to have a static mapping
  for all fields.
  """
  
  widget_entity = get_widget_for_account(account, widget_entity_name)
  email = account.email
  
  if widget_entity == None:
    """ create the required widget here """
    widget_entity = create_widget_for_account_by_email(widget_entity_name, email)
    if(widget_entity != None):
      logging.info("Created widget " + widget_entity_name + " dynamically for account: " + email + " because one did not already exist.")
  
  if widget_entity != None:
    widget_values=[]
    for property in properties:
      logging.debug(str(property))
      logging.debug("Value: " + str(widget_entity.__getattribute__(str(property))))
      
      property_name = str(property)
      property_value = str(widget_entity.__getattribute__(str(property)))
      
      new_widget_value = WidgetValue().new_widget_value(property_name, property_value, widget_entity_name)
      widget_values.append(new_widget_value)
      
    return widget_values
  else:
    return None
  
class WidgetValue:
  """
  ID,Value objects to make rendering neater... Contains several params used in rendering
  """
  def new_widget_value(self, id, value, entity_type):
    self.id = id
    self.name = utils.camelcase_to_friendly_str(id)
    self.value = value
    
    """ Other needed params """
    self.save_id = "save_" + id + entity_type
    self.action_id = "action_" + id + entity_type
    self.input_id = "input_" + id + entity_type
    self.td_id = "td_" + id + entity_type
    return self

def delete_widget(widget_key, wtype):
  return memcache_db.delete_entity_with_key(widget_key, wtype)

def add_notifier(acc_ref):
  logging.error("Had to add a Notifier widget to an account " + str(acc_ref.key().name()))
  new_notifier = Notifier(key_name=acc_ref.key().name())
  memcache_db.save_entity(new_notifier, acc_ref.key().name())
  acc_ref.notifierWidget = new_notifier
  accounts_dao.save(acc_ref)
  return new_notifier

def add_rank(acc_ref):
  logging.error("Had to add a Rank widget to an account " + str(acc_ref.key().name()))
  new_rank= Rank(key_name=acc_ref.key().name())
  memcache_db.save_entity(new_rank, acc_ref.key().name())
  acc_ref.rankWidget = new_rank
  accounts_dao.save(acc_ref)
  return new_rank

def add_points(acc_ref):
  logging.error("Had to add a Points widget to an account " + str(acc_ref.key().name()))
  new_points= Points(key_name=acc_ref.key().name())
  memcache_db.save_entity(new_points, acc_ref.key().name())
  acc_ref.pointsWidget = new_points
  accounts_dao.save(acc_ref)
  return new_points

def add_trophy_case(acc_ref):
  logging.error("Had to add a Trophy widget to an account " + str(acc_ref.key().name()))
  new_trophy_case= TrophyCase(key_name=acc_ref.key().name())
  memcache_db.save_entity(new_trophy_case, acc_ref.key().name())
  acc_ref.trophyWidget = new_trophy_case
  accounts_dao.save(acc_ref)
  return new_trophy_case

def add_leader(acc_ref):
  logging.error("Had to add a Leader widget to an account " + str(acc_ref.key().name()))
  new_leader= Leaderboard(key_name=acc_ref.key().name())
  memcache_db.save_entity(new_leader, acc_ref.key().name())
  acc_ref.leaderWidget = new_leader
  accounts_dao.save(acc_ref)
  return new_leader

def add_milestones(acc_ref):
  logging.error("Had to add a Milestones widget to an account " + str(acc_ref.key().name()))
  new_milestones = Milestones(key_name=acc_ref.key().name())
  memcache_db.save_entity(new_milestones, acc_ref.key().name())
  acc_ref.milestonesWidget = new_milestones
  accounts_dao.save(acc_ref)
  return new_milestones

 

########NEW FILE########
__FILENAME__ = accounts
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import logging
import hashlib
import datetime

from google.appengine.ext import db

import json
from serverside.constants import *
from serverside.entities.widgets import TrophyCase
from serverside.entities.widgets import Points
from serverside.entities.widgets import Rank
from serverside.entities.widgets import Milestones
from serverside.entities.widgets import Leaderboard
from serverside.entities.widgets import Notifier

"""
Class: 
  Account
Description:
  The accounts class is a primary user of the application.
  Email is required.
  The key to an account is always the email account
  The cookieKey is created at the time of creation.
  For proper scaling we must update the account as less as possible, given
  that writes max out at about 20/sec in GAE. We can do this via memcache.
  Do puts to logs/journals for login information. 
"""
class Accounts(db.Model):
  email = db.EmailProperty(required=True)
  password = db.StringProperty(required=True, indexed=False);
  isEnabled = db.StringProperty(required=True, choices=ACCOUNT_STATUS.RANGE_OF_VALUES)
  creationDate = db.DateTimeProperty(auto_now_add=True, indexed=False)
  modifiedDate = db.DateTimeProperty(auto_now=True, indexed=False)
  accountType = db.StringProperty(required=True, 
                                  choices=set(ACCOUNT_TYPES), indexed=False) 
  paymentType = db.StringProperty(required=True, 
                                  choices=set(PAYMENT_TYPES), indexed=False)
  cookieKey = db.StringProperty(required=True, indexed=False)
  apiKey = db.StringProperty(required=True)

  trophyWidget = db.ReferenceProperty(required=True, reference_class=TrophyCase)
  pointsWidget = db.ReferenceProperty(required=True, reference_class=Points)
  rankWidget = db.ReferenceProperty(required=True, reference_class=Rank)
  notifierWidget = db.ReferenceProperty(reference_class=Notifier)
  milestoneWidget = db.ReferenceProperty(reference_class=Milestones)
  leaderWidget = db.ReferenceProperty(reference_class=Leaderboard)

  lastPayment = db.StringProperty(indexed=False)
  firstName = db.StringProperty(indexed=False)
  lastName = db.StringProperty(indexed=False)
  address = db.StringProperty(indexed=False)
  city = db.StringProperty(indexed=False)
  phoneNumber = db.StringProperty(indexed=False)
  state = db.StringProperty(indexed=False)
  country = db.StringProperty(indexed=False)
  comments = db.TextProperty(indexed=False)
  receiveMarketEmails = db.BooleanProperty(indexed=False)
  receiveAnalysisEmails = db.BooleanProperty(indexed=False)
  pointsTrackingPeriod = db.StringProperty(choices=set(["daily","weekly", "monthly"] ), indexed=False)
  lastPointsReset = db.DateTimeProperty(indexed=False)
  notifyOnPoints = db.BooleanProperty(default=True, indexed=False)
  # TODO do not use iconfinder's CDN, serve it up locally
  pointsImage = db.StringProperty(default="http://cdn4.iconfinder.com/data/icons/prettyoffice/128/add1-.png", indexed=False)
  loginImage = db.StringProperty(default="http://cdn1.iconfinder.com/data/icons/Hosting_Icons/128/secure-server-px-png.png", indexed=False)

########NEW FILE########
__FILENAME__ = badges
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Author: Navraj Chohan
Description:
There are three badge types: The image, the template, and an instance
"""

import logging
import hashlib
import datetime
from accounts import Accounts
from users import Users

from google.appengine.ext import db
from google.appengine.ext.blobstore import blobstore

import json
BOOLEAN = ["yes", "no"]
TYPES = ["free", "basic", "premium"]
STYPE = ["blob", "db"]
PERMISSION = ["private", "public"]

"""
Class: BadgeImage
Description: Stores the image of the badge
Attributes:
  image: the image binary
  permissions: pub or private
  creator: Who created it 
Notes:This instance type is only for testing purposes. 
      Actual images are stored using blobstore
"""
class BadgeImage(db.Model): 
  image = db.BlobProperty(required=True)  
  permissions = db.StringProperty(required=True, choices=set(PERMISSION))
  creator = db.ReferenceProperty(reference_class=Accounts, required=True)
  imgType = db.StringProperty(required=True, choices=set(['jpg','gif','png', 'gif']), indexed=False)
  creationDate = db.DateTimeProperty(auto_now_add=True, indexed=False)
  modifiedDate = db.DateTimeProperty(auto_now=True, indexed=False)

"""
Class: Badges
Description: A badge type
Attributes:
  name: What the badge is called
  description: A brief explanation about the badge
  altText: The alt text you see in the browser
  setType: The pricing level
  isEnabled
  creationDate
  creator: A reference to the account who created this type
  tags: Tags by the owner (or everyone, if public)
  permissions: Permission, if we allow sharing
  blobKey: A reference to the image of this type
"""
class Badges(db.Model):
  name = db.StringProperty(required=True)
  description = db.TextProperty(required=True)
  altText = db.TextProperty(required=True)
  setType = db.TextProperty(required=True, choices=set(TYPES))
  isEnabled = db.StringProperty(required=True, choices=set(BOOLEAN))
  creationDate = db.DateTimeProperty(auto_now_add=True, indexed=False)
  modifiedDate = db.DateTimeProperty(auto_now=True, indexed=False)
  creator = db.ReferenceProperty(reference_class=Accounts, required=True)
  tags = db.StringProperty()
  permissions = db.StringProperty(required=True, choices=set(PERMISSION))
  storageType = db.StringProperty(required=True, choices=set(STYPE), indexed=False)
  # This if you want to make the badge clickable, and route to a resource
  # or secret link, etc
  resourceLink = db.LinkProperty(indexed=False)
  downloadLink = db.LinkProperty(indexed=False)
  # a reference key to the object stored into the blobstore
  blobKey =  blobstore.BlobReferenceProperty()
  imageKey = db.ReferenceProperty(reference_class=BadgeImage)
  # Uploaded files in static images of badges
  filePath = db.StringProperty(indexed=False)
  theme = db.StringProperty()
  
"""
Class: BadgeInstance
Description: An instance of a badge which has been given to a user
Attributes:
  badgeRef: A reference to the type of badge
"""
class BadgeInstance(db.Model): 
  badgeRef = db.ReferenceProperty(reference_class=Badges, required=True)
  userRef = db.ReferenceProperty(reference_class=Users, required=True)
  awarded = db.StringProperty(required=True, choices=set(BOOLEAN))
  permissions = db.StringProperty(required=True, choices=set(PERMISSION))
  creationDate = db.DateTimeProperty(auto_now_add=True, indexed=False)
  awardDateTime = db.DateTimeProperty(indexed=False)
  awardDate = db.DateProperty(indexed=False)
  modifiedDate = db.DateTimeProperty(auto_now=True, indexed=False)
  instanceRegistrationDate = db.DateTimeProperty(auto_now=True, indexed=False)
  pointsRequired = db.IntegerProperty(default=9999999999, indexed=False)
  pointsEarned = db.IntegerProperty(default=0, indexed=False)
  expirationDate = db.DateTimeProperty(indexed=False)
  resource = db.LinkProperty(indexed=False)
  reason = db.StringProperty(indexed=False)
  downloadLink = db.LinkProperty(indexed=False)

########NEW FILE########
__FILENAME__ = counter
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import datetime
from google.appengine.ext import db
from serverside import constants

class APICountBatch(db.Model):
  date = db.DateTimeProperty()
  account_key = db.StringProperty()
  counter = db.IntegerProperty(default=0, indexed=False)

class PointBatch(db.Model):
  date = db.DateTimeProperty()
  account_key = db.StringProperty()
  counter = db.IntegerProperty(default=0, indexed=False)

class BadgePointsBatch(db.Model):
  date = db.DateTimeProperty()
  account_key = db.StringProperty()
  badgeid = db.StringProperty()
  counter = db.IntegerProperty(default=0, indexed=False)

class BadgeBatch(db.Model):
  date = db.DateTimeProperty()
  account_key = db.StringProperty()
  badgeid = db.StringProperty()
  counter = db.IntegerProperty(default=0, indexed=False)

########NEW FILE########
__FILENAME__ = emails
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import datetime
from google.appengine.ext import db
class Email(db.Model):
  email = db.EmailProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)

########NEW FILE########
__FILENAME__ = logs
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import datetime
from google.appengine.ext import db
from serverside import constants

class Logs(db.Model):
  event = db.StringProperty(required=True)
  date = db.DateTimeProperty(auto_now_add=True)
  user = db.StringProperty()
  account = db.StringProperty()
  badgeid = db.StringProperty()
  details = db.StringProperty()
  points = db.StringProperty()
  widget = db.StringProperty()
  success = db.StringProperty()
  api = db.StringProperty()
  is_api = db.StringProperty()
  ip = db.StringProperty()

########NEW FILE########
__FILENAME__ = memcache_db
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
"""
Author: Navraj Chohan
This is an interface to the datastore which uses memcache as a cache for
faster access.
"""
from google.appengine.api import memcache
from google.appengine.ext import db
from google.appengine.datastore import entity_pb
from serverside import constants
from serverside.entities.accounts import Accounts
from serverside.entities.users import Users
from serverside.entities.badges import Badges
from serverside.entities.badges import BadgeInstance
from serverside.entities.badges import BadgeImage
from serverside.entities.widgets import TrophyCase
from serverside.entities.widgets import Notifier
from serverside.entities.widgets import Milestones 
from serverside.entities.widgets import Points
from serverside.entities.widgets import Leaderboard
from serverside.entities.widgets import Rank
from serverside.entities.passphrase import PassPhrase
import logging
"""
Function:
  get_entity
Args:
  key_name
Description:
  Uses memcache to access entities in string format. Then they are converted 
  to db.Model type. If not in memcache, get it from the datastore.
Returns:
  The db.Model of the entity
"""
def get_entity(key_name, ent_type):
  if ent_type not in constants.PROTECTED_DB_TYPES:
    raise Exception()
  e = memcache.get(key=key_name, namespace=ent_type)
  if e:
    try:
      e = deserialize(e)
    except:
      logging.error("Memcache_db: Unable to deserialize entity of type %s"%ent_type)
      e = None 

  if not e:
    memcache.delete(key=key_name, namespace=ent_type)
    if ent_type == "Accounts":
      e = Accounts.get_by_key_name(key_name)
    elif ent_type == "Badges":
      e = Badges.get_by_key_name(key_name)
    elif ent_type == "BadgeInstance":
      e = BadgeInstance.get_by_key_name(key_name)
    elif ent_type == "BadgeImage":
      e = BadgeImage.get_by_key_name(key_name)
    elif ent_type == "Users":
      e = Users.get_by_key_name(key_name)
    elif ent_type == "TrophyCase":
      e = TrophyCase.get_by_key_name(key_name)
    elif ent_type == "Points":
      e = Points.get_by_key_name(key_name)
    elif ent_type == "Notifier":
      e = Notifier.get_by_key_name(key_name)
    elif ent_type == "Rank":
      e = Rank.get_by_key_name(key_name)
    elif ent_type == "PassPhrase":
      e = PassPhrase.get_by_key_name(key_name)
    elif ent_type == "Milestones":
      e = Milestones.get_by_key_name(key_name)
    elif ent_type == "Leaderboard":
      e = Leaderboard.get_by_key_name(key_name)
    else:
      raise Exception()
    if e:
      memcache.add(key=key_name,value=str(serialize(e)),namespace=ent_type)
  return e

"""
TODO : Need to think if this is even possible. Can base it on a timeout, 
and it caches the last 1 minute or something...
"""
def __run_query(query, ent_type):
  return

"""
Function:
  batch_get_entity
Args:
  key_name list
Description:
  Uses memcache to access entities in string format. Then they are converted 
  to db.Model type. If not in memcache, get it from the datastore. This function
  gets a batch of keys at once, first from memcache, and the remaining from 
  the db in parallel. Only deals with one type.
Returns:
  List of db.Model of the entity

Experimental
TODO NEEDS TESTING
"""
def __batch_get_entity(key_names, ent_type):
  if ent_type not in constants.PROTECTED_DB_TYPES:
    raise Exception()
  es = memcache.get_multi(keys=key_names, namespace=ent_type)
  ents = []
  db_ents = {}
  for key in key_names:
    e = None
    if key in es:
      try:
        e = deserialize(e) 
        ents.append(e)
      except Exception, ex:
        logging.error("Memcache_db: Unable to deserialize entity of type %s with %s"%(ent_type, str(ex)))
        e = None
    if not e:
      # These puts are in a loop, making this function slow
      memcache.delete(key=key, namespace=ent_type)
      if ent_type == "Accounts":
        dbent = Accounts.get_by_key_name(key)
        ents.append(dbebt)
        db_ents[key] = serialize(dbent)
      elif ent_type == "Badges":
        dbent = Badges.get_by_key_name(key)
        ents.append(dbebt)
        db_ents[key] = serialize(dbent)
      elif ent_type == "BadgeInstance":
        dbent = BadgeInstance.get_by_key_name(key)
        ents.append(dbebt)
        db_ents[key] = serialize(dbent)
      elif ent_type == "BadgeImage":
        dbent = BadgeImage.get_by_key_name(key)
        ents.append(dbebt)
        db_ents[key] = serialize(dbent)
      elif ent_type == "Users":
        dbent = Users.get_by_key_name(key)
        ents.append(dbebt)
        db_ents[key] = serialize(dbent)
      elif ent_type == "TrophyCases":
        dbent = TrophyCases.get_by_key_name(key)
        ents.append(dbebt)
        db_ents[key] = serialize(dbent)
      else:
        raise Exception()
  memcache.set_multi(mapping=db_ents,namespace=ent_type)
  return ents

"""
Function
  update_fields
Args:
  fields: A dictionary of what to update
  key_name: the key to the entity 
  ent_type
  increment_fields: A dictionary but incremented by given ammount. 
                    This number can also be negative
Returns:
  The Key object of the entity
"""
def update_fields(key_name, ent_type, fields={}, increment_fields={}):
  if ent_type not in constants.PROTECTED_DB_TYPES:
    raise Exception()
  def _txn():
    entity = get_entity(key_name, ent_type)
    if not entity:
      raise Exception()
    if fields:
      for ii in fields:
        setattr(entity, ii, fields[ii])
    if increment_fields:
      for ii in increment_fields:
        prev_val = getattr(entity, ii) 
        if not prev_val: prev_val = 0
        setattr(entity, ii,  prev_val + increment_fields[ii])
    entity.key_name = key_name
    ret = entity.put()
    memcache.delete(key=key_name, namespace=ent_type)
    memcache.add(key=key_name,
                 value=str(serialize(entity)),
                 namespace=ent_type)
    return ret
  ret = db.run_in_transaction(_txn)
  return ret

"""
Function:
  save_entity 
Args:
  entity
  key_name
  ent_type
Description:
  For first time creation of an entity to be placed in memcache & DB
Returns:
  The Key object of the entity
"""
def save_entity(ent, key_name):
  if not ent:
    raise Exception()
  ent_type  = ent.__class__.__name__
  if ent_type not in constants.PROTECTED_DB_TYPES:
    logging.error("Memcache_db: Type %s not valid"%ent_type)
    raise Exception()
  def _txn():
    memcache.delete(key=key_name, namespace=ent_type)
    ent.key_name = key_name
    ret = ent.put()
    if ret:
      memcache.add(key=key_name , value=str(serialize(ent)), namespace=ent_type)
    return ret
  return db.run_in_transaction(_txn)

"""
Function:
  delete_entity 
Args:
  entity
  key_name
  ent_type
Raises:
  If deleting on a non-exiting ent, NotSavedError is raised   
"""
def delete_entity(ent, key_name):
  if not ent:
    raise Exception()
  ent_type = ent.__class__.__name__
  if ent_type not in constants.PROTECTED_DB_TYPES:
    raise Exception()
  memcache.delete(key=key_name, namespace=ent_type)
  ret = ent.delete() 
  return ret

"""
Function:
  delete_entity_with_key
Args:
  key_name
  ent_type
Raises:
  Nothing
"""
def delete_entity_with_key(key_name, ent_type):
  key = db.Key.from_path(ent_type, key_name)
  memcache.delete(key=key_name, namespace=ent_type)
  ret = db.delete(key) 
  return ret 

""" Serialization and deserialization of models """
def serialize(models):
  if models is None:
    return None
  elif isinstance(models, db.Model):
    # Just one instance
    return db.model_to_protobuf(models).Encode()
  else:
    # A list
    return [db.model_to_protobuf(x).Encode() for x in models]
 
def deserialize(data):
  if data is None:
    return None
  elif isinstance(data, str):
  # Just one instance
    return db.model_from_protobuf(entity_pb.EntityProto(data))
  else:
    return [db.model_from_protobuf(entity_pb.EntityProto(x)) for x in data]

def is_in_memcache(key_name, ent_type):
  e = memcache.get(key=key_name, namespace=ent_type)
  if e: return True
  else: return False

def is_in_db(key_name, ent_type):
  if ent_type not in constants.PROTECTED_DB_TYPES:
    raise Exception()
  e = None
  if ent_type == "Accounts":
    e = Accounts.get_by_key_name(key_name)
  elif ent_type == "Badges":
    e = Badges.get_by_key_name(key_name)
  elif ent_type == "BadgeInstance":
    e = BadgeInstance.get_by_key_name(key_name)
  elif ent_type == "BadgeImage":
    e = BadgeInstance.get_by_key_name(key_name)
  elif ent_type == "Users":
    e = Users.get_by_key_name(key_name)
  elif ent_type == "TrophyCases":
    e = TrophyCase.get_by_key_name(key_name)
  else:
    raise Exception()

  if e: return True
  else: return False

 

########NEW FILE########
__FILENAME__ = passphrase
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import datetime
from google.appengine.ext import db
class PassPhrase(db.Model):
  secret = db.StringProperty(required=True)
  creation_date = db.DateTimeProperty(auto_now_add=True)

########NEW FILE########
__FILENAME__ = pending_create
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from google.appengine.ext import db

class Pending_Create(db.Model):
  """This entity is used to store accounts that have signed up, but have not activated via email yet"""
  id = db.StringProperty(required=True)
  email = db.EmailProperty(required=True)

########NEW FILE########
__FILENAME__ = users
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import logging
import hashlib
import datetime
from google.appengine.ext import db
from serverside.entities.accounts import Accounts
from serverside import constants
import json
class Users(db.Model):
  userid = db.StringProperty(required=True)
  isEnabled = db.StringProperty(required=True, choices=set(["yes","no"]))
  creationDate = db.DateTimeProperty(auto_now_add=True, indexed=False)
  modifiedDate = db.DateTimeProperty(auto_now=True, indexed=False)
  accountRef = db.ReferenceProperty(reference_class=Accounts, required=True)
  points = db.IntegerProperty(default=0)
  rank = db.IntegerProperty(default=constants.NOT_RANKED)
  last_time_ranked = db.DateTimeProperty(indexed=False)
  profileName = db.StringProperty(default="Anonymous", indexed=False)
  profileLink = db.TextProperty(indexed=False)
  profileImg = db.TextProperty(default="http://i.imgur.com/hsDiZ.jpg", indexed=False)
  userNotes = db.TextProperty(indexed=False)
  tags = db.StringProperty()

########NEW FILE########
__FILENAME__ = widgets
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
""" Author: Navraj Chohan
    Description: Information about the way a widget should be rendered
"""
from google.appengine.ext import db
from serverside import constants
""" Class: TrophyCase
    Description: Settings for rendering TrophyCase
"""
class TrophyCase(db.Model):
  backgroundColor = db.StringProperty( default="#eeeeff", indexed=False)
  borderThickness = db.IntegerProperty( default=1, indexed=False)
  borderColor = db.StringProperty( default="#4488FF", indexed=False)
  borderStyle = db.StringProperty( default="solid", indexed=False)
  height = db.IntegerProperty( default=500, indexed=False)
  width = db.IntegerProperty( default=270, indexed=False)
  hasRoundedCorners = db.BooleanProperty(default=False, indexed=False)
  # Title
  titleBackgroundColor = db.StringProperty(default="#4488FF", indexed=False)
  displayTitle = db.BooleanProperty( default=True, indexed=False)
  title = db.StringProperty( default="Trophy Case", indexed=False)
  titleColor = db.StringProperty( default="white", indexed=False)
  titleSize = db.IntegerProperty( default=20, indexed=False)
  titleFont = db.StringProperty( default="Arial", indexed=False)
  titleFloat = db.StringProperty( default="center", indexed=False)
  # Date
  displayDate = db.BooleanProperty( default=True, indexed=False)
  dateColor = db.StringProperty( default="black", indexed=False)
  dateSize = db.IntegerProperty( default=8, indexed=False)
  dateFont = db.StringProperty( default="Arial", indexed=False)
  dateFloat = db.StringProperty( default="center", indexed=False)
  # Reason for getting badge
  displayReason = db.BooleanProperty( default=True, indexed=False)
  reasonColor = db.StringProperty( default="black", indexed=False)
  reasonSize = db.IntegerProperty( default=12, indexed=False)
  reasonFont = db.StringProperty( default="Arial", indexed=False)
  reasonFloat = db.StringProperty( default="center", indexed=False)

  # Random/Misc
  allowSorting = db.BooleanProperty( default=True, indexed=False)
  imageSize = db.IntegerProperty( default=100, indexed=False) 
  scrollable = db.BooleanProperty( default=False, indexed=False)

  # what to display if there is an empty case
  displayNoBadgesMessage = db.BooleanProperty( default=True, indexed=False)
  noBadgesMessage = db.StringProperty( default="Sorry, no badges yet!", indexed=False)
  noBadgesFont = db.StringProperty( default="Arial", indexed=False)
  noBadgesSize = db.IntegerProperty( default=12, indexed=False)
  noBadgesFloat = db.StringProperty( default="center", indexed=False)
  noBadgesColor = db.StringProperty( default="red", indexed=False)

class Notifier(db.Model):
  backgroundColor = db.StringProperty(default="#EEEEFF", indexed=False)
  borderThickness = db.IntegerProperty(default=1, indexed=False)
  borderColor = db.StringProperty( default="#4488FF", indexed=False)
  borderStyle = db.StringProperty( default="solid", indexed=False)
  height = db.IntegerProperty(default=160, indexed=False)
  width = db.IntegerProperty(default=150, indexed=False)
  hasRoundedCorners = db.BooleanProperty(default=False, indexed=False)
  # Title
  titleBackgroundColor = db.StringProperty(default="#4488FF", indexed=False)
  displayTitle = db.BooleanProperty( default=True, indexed=False)
  title = db.StringProperty( default="Congrats!", indexed=False)
  titleColor = db.StringProperty( default="white", indexed=False)
  titleSize = db.IntegerProperty( default=10, indexed=False)
  titleFont = db.StringProperty( default="Arial", indexed=False)
  titleFloat = db.StringProperty( default="center", indexed=False)

  """http://docs.jquery.com/UI/Effects for different types""" 
  """'blind', 'clip', 'drop', 'explode', 'fold', 'puff', 'slide', 'scale', 'size', 'pulsate'."""
  exitEffect = db.StringProperty(default="fold", indexed=False)
  """'blind', 'clip', 'drop', 'explode', 'fold', 'puff', 'slide', 'scale', 'size', 'pulsate'."""
  entryEffect = db.StringProperty(default="drop", indexed=False)
  imageSize = db.IntegerProperty(default=100, indexed=False)

  # Note
  noteColor = db.StringProperty(default="#4488FF", indexed=False)
  displayNote = db.BooleanProperty( default=True, indexed=False)
  noteColor = db.StringProperty( default="#4488FF", indexed=False)
  noteSize = db.IntegerProperty( default=14, indexed=False)
  noteFont = db.StringProperty( default="Arial", indexed=False)
  noteFloat = db.StringProperty( default="center", indexed=False)

class Leaderboard(db.Model):
  backgroundColor = db.StringProperty( default="#EEEEFF", indexed=False)
  alternateColor = db.StringProperty( default="#DDFFFF", indexed=False)
  borderThickness = db.IntegerProperty( default=1, indexed=False)
  borderColor = db.StringProperty( default="#4488FF", indexed=False)
  borderStyle = db.StringProperty( default="solid", indexed=False)
  height = db.IntegerProperty( default=1000, indexed=False)
  width = db.IntegerProperty( default=500, indexed=False)
  hasRoundedCorners = db.BooleanProperty(default=False, indexed=False)
  imageSize = db.IntegerProperty(default=constants.IMAGE_PARAMS.LEADER_SIZE, indexed=False)

  # Title
  titleBackgroundColor = db.StringProperty(default="#4488FF", indexed=False)
  displayTitle = db.BooleanProperty( default=True, indexed=False)
  title = db.StringProperty( default="Leaderboard", indexed=False)
  titleColor = db.StringProperty( default="white", indexed=False)
  titleSize = db.IntegerProperty( default=20, indexed=False)
  titleFont = db.StringProperty( default="Arial", indexed=False)
  titleFloat = db.StringProperty( default="center", indexed=False)

  # Header
  headerBackgroundColor = db.StringProperty(default="#EEEEFF", indexed=False)
  displayHeader = db.BooleanProperty( default=True, indexed=False)
  headerColor = db.StringProperty( default="black", indexed=False)
  headerSize = db.IntegerProperty( default=20, indexed=False)
  headerFont = db.StringProperty( default="Arial", indexed=False)

  #Rank 
  rankColor = db.StringProperty(default="#4488FF", indexed=False)
  displayRank = db.BooleanProperty( default=True, indexed=False)
  rankColor = db.StringProperty( default="black", indexed=False)
  rankSize = db.IntegerProperty( default=25, indexed=False)
  rankFont = db.StringProperty( default="Arial", indexed=False)

  #Name 
  nameColor = db.StringProperty(default="#4488FF", indexed=False)
  displayName = db.BooleanProperty( default=True, indexed=False)
  nameColor = db.StringProperty( default="#4488FF", indexed=False)
  nameSize = db.IntegerProperty( default=14, indexed=False)
  nameFont = db.StringProperty( default="Arial", indexed=False)

  # Points
  pointsColor = db.StringProperty(default="#4488FF", indexed=False)
  displayPoints = db.BooleanProperty( default=True, indexed=False)
  pointsColor = db.StringProperty( default="#4488FF", indexed=False)
  pointsSize = db.IntegerProperty( default=20, indexed=False)
  pointsFont = db.StringProperty( default="Arial", indexed=False)
  pointsFloat = db.StringProperty( default="center", indexed=False)

  # what to display if there is an empty case
  displayNoUserMessage = db.BooleanProperty( default=True, indexed=False)
  noUserMessage = db.StringProperty( default="Check Back Soon!", indexed=False)
  noUserFont = db.StringProperty( default="Arial", indexed=False)
  noUserSize = db.IntegerProperty( default=20, indexed=False)
  noUserFloat = db.StringProperty( default="center", indexed=False)
  noUserColor = db.StringProperty( default="#FFF000", indexed=False)

class Points(db.Model):
  backgroundColor = db.StringProperty( default="#EEEEFF", indexed=False)
  borderThickness = db.IntegerProperty( default=1, indexed=False)
  borderColor = db.StringProperty( default="#4488FF", indexed=False)
  borderStyle = db.StringProperty( default="solid", indexed=False)
  height = db.IntegerProperty( default=100, indexed=False)
  width = db.IntegerProperty( default=120, indexed=False)
  hasRoundedCorners = db.BooleanProperty(default=False, indexed=False)
  # Title
  titleBackgroundColor = db.StringProperty(default="#4488FF", indexed=False)
  displayTitle = db.BooleanProperty( default=True, indexed=False)
  title = db.StringProperty( default="Your Points", indexed=False)
  titleColor = db.StringProperty( default="white", indexed=False)
  titleSize = db.IntegerProperty( default=14, indexed=False)
  titleFont = db.StringProperty( default="Arial", indexed=False)
  titleFloat = db.StringProperty( default="center", indexed=False)

  #displayPoints = db.BooleanProperty( default=True)
  pointsColor = db.StringProperty( default="black", indexed=False)
  pointsSize = db.IntegerProperty( default=14, indexed=False)
  pointsFont = db.StringProperty( default="Arial", indexed=False)
  pointsFloat = db.StringProperty( default="center", indexed=False)

class Rank(db.Model):
  backgroundColor = db.StringProperty( default="#EEEEFF", indexed=False)
  borderThickness = db.IntegerProperty( default=1, indexed=False)
  borderColor = db.StringProperty( default="#4488FF", indexed=False)
  borderStyle = db.StringProperty( default="solid", indexed=False)
  height = db.IntegerProperty( default=100, indexed=False)
  width = db.IntegerProperty( default=120, indexed=False)
  hasRoundedCorners = db.BooleanProperty(default=False, indexed=False)
  # Title
  displayTitle = db.BooleanProperty( default=True, indexed=False)
  title = db.StringProperty( default="Your Ranking", indexed=False)
  titleBackgroundColor = db.StringProperty(default="#4488FF", indexed=False)
  titleColor = db.StringProperty( default="white", indexed=False)
  titleSize = db.IntegerProperty( default=14, indexed=False)
  titleFont = db.StringProperty( default="Arial", indexed=False)
  titleFloat = db.StringProperty( default="center", indexed=False)
  # Rank
  rankColor = db.StringProperty( default="black", indexed=False)
  rankSize = db.IntegerProperty( default=14, indexed=False)
  rankFont = db.StringProperty( default="Arial", indexed=False)
  rankFloat = db.StringProperty( default="center", indexed=False)

class Milestones(db.Model):
  backgroundColor = db.StringProperty( default="#eeeeff", indexed=False)
  borderThickness = db.IntegerProperty( default=1, indexed=False)
  borderColor = db.StringProperty( default="#4488FF", indexed=False)
  borderStyle = db.StringProperty( default="solid", indexed=False)
  height = db.IntegerProperty( default=500, indexed=False)
  width = db.IntegerProperty( default=270, indexed=False)
  hasRoundedCorners = db.BooleanProperty(default=False, indexed=False)
  # Title
  titleBackgroundColor = db.StringProperty(default="#4488FF", indexed=False)
  displayTitle = db.BooleanProperty( default=True, indexed=False)
  title = db.StringProperty( default="Badge Progress", indexed=False)
  titleColor = db.StringProperty( default="white", indexed=False)
  titleSize = db.IntegerProperty( default=20, indexed=False)
  titleFont = db.StringProperty( default="Arial", indexed=False)
  titleFloat = db.StringProperty( default="center", indexed=False)
  # Date
  displayDate = db.BooleanProperty( default=True, indexed=False)
  dateColor = db.StringProperty( default="black", indexed=False)
  dateSize = db.IntegerProperty( default=8, indexed=False)
  dateFont = db.StringProperty( default="Arial", indexed=False)
  dateFloat = db.StringProperty( default="center", indexed=False)
  # Reason for getting badge
  displayReason = db.BooleanProperty( default=True, indexed=False)
  reasonColor = db.StringProperty( default="black", indexed=False)
  reasonSize = db.IntegerProperty( default=12, indexed=False)
  reasonFont = db.StringProperty( default="Arial", indexed=False)
  reasonFloat = db.StringProperty( default="center", indexed=False)

  # Random/Misc
  allowSorting = db.BooleanProperty( default=True, indexed=False)
  imageSize = db.IntegerProperty( default=100, indexed=False) 
  scrollable = db.BooleanProperty( default=False, indexed=False)



########NEW FILE########
__FILENAME__ = environment
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Jan 25, 2011

@author: shan
'''
import os

"""Implement methods to identify environment """
  
def is_dev():
  if os.environ["SERVER_SOFTWARE"].find("Development") != -1:
    return True
  else:
    return False
    

########NEW FILE########
__FILENAME__ = action
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

class FSMAction(object):
    """ Defines the interface for all user actions. """
    
    def execute(self, context, obj):
        """ Executes some action. The return value is ignored, _except_ for the main state action.
        
        @param context The FSMContext (i.e., machine). context.get() and context.put() can be used to get data
                       from/to the context.
        @param obj: An object which the action can operate on
        
        For the main state action, the return value should be a string representing the event to be dispatched.
        Actions performed should be careful to be idempotent: because of potential retry mechanisms 
        (notably with TaskQueueFSMContext), individual execute methods may get executed more than once with 
        exactly the same context.
        """
        raise NotImplementedError()
    
class ContinuationFSMAction(FSMAction):
    """ Defines the interface for all continuation actions. """
    
    def continuation(self, context, obj, token=None):
        """ Accepts a token (may be None) and returns the next token for the continutation. 
        
        @param token: the continuation token
        @param context The FSMContext (i.e., machine). context.get() and context.put() can be used to get data
                       from/to the context.
        @param obj: An object which the action can operate on
        """
        raise NotImplementedError()
    
class DatastoreContinuationFSMAction(ContinuationFSMAction):
    """ A datastore continuation. """
    
    def continuation(self, context, obj, token=None):
        """ Accepts a token (an optional cursor) and returns the next token for the continutation. 
        The results of the query are stored on obj.results.
        """
        # the continuation query comes
        query = self.getQuery(context, obj)
        cursor = token
        if cursor:
            query.with_cursor(cursor)
        limit = self.getBatchSize(context, obj)
        
        # place results on obj.results
        obj['results'] = query.fetch(limit)
        obj.results = obj['results'] # deprecated interface
        
        # add first obj.results item on obj.result - convenient for batch size 1
        if obj['results'] and len(obj['results']) > 0:
            obj['result'] = obj['results'][0]
        else:
            obj['result'] = None
        obj.result = obj['result'] # deprecated interface
            
        if len(obj['results']) == limit:
            return query.cursor()
        
    def getQuery(self, context, obj):
        """ Returns a GqlQuery """
        raise NotImplementedError()
    
    # W0613: 78:DatastoreContinuationFSMAction.getBatchSize: Unused argument 'obj'
    def getBatchSize(self, context, obj): # pylint: disable-msg=W0613
        """ Returns a batch size, default 1. Override for different values. """
        return 1

########NEW FILE########
__FILENAME__ = config
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import os
import yaml
import logging
import json
import datetime
from fantasm import exceptions, constants, utils

TASK_ATTRIBUTES = (
    (constants.TASK_RETRY_LIMIT_ATTRIBUTE, 'taskRetryLimit', constants.DEFAULT_TASK_RETRY_LIMIT, 
     exceptions.InvalidTaskRetryLimitError),
    (constants.MIN_BACKOFF_SECONDS_ATTRIBUTE, 'minBackoffSeconds', constants.DEFAULT_MIN_BACKOFF_SECONDS, 
     exceptions.InvalidMinBackoffSecondsError),
    (constants.MAX_BACKOFF_SECONDS_ATTRIBUTE, 'maxBackoffSeconds', constants.DEFAULT_MAX_BACKOFF_SECONDS, 
     exceptions.InvalidMaxBackoffSecondsError),
    (constants.TASK_AGE_LIMIT_ATTRIBUTE, 'taskAgeLimit', constants.DEFAULT_TASK_AGE_LIMIT, 
     exceptions.InvalidTaskAgeLimitError),
    (constants.MAX_DOUBLINGS_ATTRIBUTE, 'maxDoublings', constants.DEFAULT_MAX_DOUBLINGS, 
     exceptions.InvalidMaxDoublingsError),
)

_config = None

def currentConfiguration(filename=None):
    """ Retrieves the current configuration specified by the fsm.yaml file. """
    # W0603: 32:currentConfiguration: Using the global statement
    global _config # pylint: disable-msg=W0603
    
    # always reload the config for dev_appserver to grab recent dev changes
    if _config and not constants.DEV_APPSERVER:
        return _config
        
    _config = loadYaml(filename=filename)
    return _config

# following function is borrowed from mapreduce code
# ...
# N.B. Sadly, we currently don't have and ability to determine
# application root dir at run time. We need to walk up the directory structure
# to find it.
def _findYaml(yamlNames=constants.YAML_NAMES):
    """Traverse up from current directory and find fsm.yaml file.

    Returns:
      the path of fsm.yaml file or None if not found.
    """
    directory = os.path.dirname(__file__)
    while directory:
        for yamlName in yamlNames:
            yamlPath = os.path.join(directory, yamlName)
            if os.path.exists(yamlPath):
                return yamlPath
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent
    return None

def loadYaml(filename=None, importedAlready=None):
    """ Loads the YAML and constructs a configuration from it. """
    if not filename:
        filename = _findYaml()
    if not filename:
        raise exceptions.YamlFileNotFoundError('fsm.yaml')
      
    try:
        yamlFile = open(filename)
    except IOError:
        raise exceptions.YamlFileNotFoundError(filename)
    try:
        configDict = yaml.load(yamlFile.read())
    finally:
        yamlFile.close()
        
    return Configuration(configDict, importedAlready=importedAlready)
        
class Configuration(object):
    """ An overall configuration that corresponds to a fantasm.yaml file. """
    
    def __init__(self, configDict, importedAlready=None):
        """ Constructs the configuration from a dictionary of values. """
        
        importedAlready = importedAlready or []
        
        if constants.STATE_MACHINES_ATTRIBUTE not in configDict:
            raise exceptions.StateMachinesAttributeRequiredError()
        
        self.rootUrl = configDict.get(constants.ROOT_URL_ATTRIBUTE, constants.DEFAULT_ROOT_URL)
        if not self.rootUrl.endswith('/'):
            self.rootUrl += '/'
            
        self.machines = {}
        
        # import built-in machines
        self._importBuiltInMachines(importedAlready=importedAlready)
        
        for machineDict in configDict[constants.STATE_MACHINES_ATTRIBUTE]:
            
            # bring in all the imported machines
            if machineDict.get(constants.IMPORT_ATTRIBUTE):
                self._importYaml(machineDict[constants.IMPORT_ATTRIBUTE], importedAlready=importedAlready)
                continue
                
            machine = _MachineConfig(machineDict, rootUrl=self.rootUrl)
            if machine.name in self.machines:
                raise exceptions.MachineNameNotUniqueError(machine.name)
                
            # add the states
            for stateDict in machineDict.get(constants.MACHINE_STATES_ATTRIBUTE, []):
                machine.addState(stateDict)
                
            if not machine.initialState:
                raise exceptions.MachineHasNoInitialStateError(machine.name)
            
            if not machine.finalStates:
                raise exceptions.MachineHasNoFinalStateError(machine.name)
            
            # add the transitions (2-phase parsing :( )
            for stateDict in machineDict.get(constants.MACHINE_STATES_ATTRIBUTE, []):
                for transDict in stateDict.get(constants.STATE_TRANSITIONS_ATTRIBUTE, []):
                    machine.addTransition(transDict, stateDict[constants.STATE_NAME_ATTRIBUTE])
                
            self.machines[machine.name] = machine
            
    def __addMachinesFromImportedConfig(self, importedCofig):
        """ Adds new machines from an imported configuration. """
        for machineName, machine in importedCofig.machines.items():
            if machineName in self.machines:
                raise exceptions.MachineNameNotUniqueError(machineName)
            self.machines[machineName] = machine
            
    def _importYaml(self, importYamlFile, importedAlready=None):
        """ Imports a yaml file """
        yamlFile = _findYaml(yamlNames=[importYamlFile])
        if not yamlFile:
            raise exceptions.YamlFileNotFoundError(importYamlFile)
        if yamlFile in importedAlready:
            raise exceptions.YamlFileCircularImportError(importYamlFile)
        importedAlready.append(yamlFile)
        importedConfig = loadYaml(filename=yamlFile, importedAlready=importedAlready)
        self.__addMachinesFromImportedConfig(importedConfig)
            
    BUILTIN_MACHINES = (
        'scrubber.yaml',
    )
            
    def _importBuiltInMachines(self, importedAlready=None):
        """ Imports built-in machines. """
        directory = os.path.dirname(__file__)
        for key in self.BUILTIN_MACHINES:
            yamlFile = os.path.join(directory, key)
            if yamlFile in importedAlready:
                continue
            importedAlready.append(yamlFile)
            importedConfig = loadYaml(filename=yamlFile, importedAlready=importedAlready)
            self.__addMachinesFromImportedConfig(importedConfig)

def _resolveClass(className, namespace):
    """ Given a string representation of a class, locates and returns the class object. """
    
    # some shortcuts for context_types
    shortTypes = {
        'dict': json.loads,
        'int': int,
        'float': float,
        'bool': utils.boolConverter, 
        'long': long,
        'json': json.loads,
        'datetime': lambda x: datetime.datetime.utcfromtimestamp(int(x)),
    }
    if className in shortTypes:
        return shortTypes[className] # FIXME: is this valid with methods?
    
    if '.' in className:
        fullyQualifiedClass = className
    elif namespace:
        fullyQualifiedClass = '%s.%s' % (namespace, className)
    else:
        fullyQualifiedClass = className
    
    moduleName = fullyQualifiedClass[:fullyQualifiedClass.rfind('.')]
    className = fullyQualifiedClass[fullyQualifiedClass.rfind('.')+1:]
    
    try:
        module = __import__(moduleName, globals(), locals(), [className])
    except ImportError, e:
        raise exceptions.UnknownModuleError(moduleName, e)
        
    try:
        resolvedClass = getattr(module, className)
        return resolvedClass
    except AttributeError:
        raise exceptions.UnknownClassError(moduleName, className)
    
def _resolveObject(objectName, namespace, expectedType=basestring):
    """ Given a string name/path of a object, locates and returns the value of the object. 
    
    @param objectName: ie. MODULE_LEVEL_CONSTANT, ActionName.CLASS_LEVEL_CONSTANT
    @param namespace: ie. fully.qualified.python.module 
    """
    
    if '.' in objectName:
        classOrObjectName = objectName[:objectName.rfind('.')]
        objectName2 = objectName[objectName.rfind('.')+1:]
    else:
        classOrObjectName = objectName
        
    resolvedClassOrObject = _resolveClass(classOrObjectName, namespace)
    
    if isinstance(resolvedClassOrObject, expectedType):
        return resolvedClassOrObject
    
    try:
        resolvedObject = getattr(resolvedClassOrObject, objectName2)
    except AttributeError:
        raise exceptions.UnknownObjectError(objectName)
        
    if not isinstance(resolvedObject, expectedType):
        raise exceptions.UnexpectedObjectTypeError(objectName, expectedType)
        
    return resolvedObject
        
class _MachineConfig(object):
    """ Configuration of a machine. """
    
    def __init__(self, initDict, rootUrl=None):
        """ Configures the basic attributes of a machine. States and transitions are not handled
            here, but are added by an external client.
        """
        
        # machine name
        self.name = initDict.get(constants.MACHINE_NAME_ATTRIBUTE)
        if not self.name:
            raise exceptions.MachineNameRequiredError()
        if not constants.NAME_RE.match(self.name):
            raise exceptions.InvalidMachineNameError(self.name)
        
        # check for bad attributes
        badAttributes = set()
        for attribute in initDict.iterkeys():
            if attribute not in constants.VALID_MACHINE_ATTRIBUTES:
                badAttributes.add(attribute)
        if badAttributes:
            raise exceptions.InvalidMachineAttributeError(self.name, badAttributes)
            
        # machine queue, namespace
        self.queueName = initDict.get(constants.QUEUE_NAME_ATTRIBUTE, constants.DEFAULT_QUEUE_NAME)
        self.namespace = initDict.get(constants.NAMESPACE_ATTRIBUTE)
        
        # logging
        self.logging = initDict.get(constants.MACHINE_LOGGING_NAME_ATTRIBUTE, constants.LOGGING_DEFAULT)
        if self.logging not in constants.VALID_LOGGING_VALUES:
            raise exceptions.InvalidLoggingError(self.name, self.logging)
        
        # machine task_retry_limit, min_backoff_seconds, max_backoff_seconds, task_age_limit, max_doublings
        for (constant, attribute, default, exception) in TASK_ATTRIBUTES:
            setattr(self, attribute, default)
            if constant in initDict:
                setattr(self, attribute, initDict[constant])
                try:
                    i = int(getattr(self, attribute))
                    setattr(self, attribute, i)
                except ValueError:
                    raise exception(self.name, getattr(self, attribute))

        # if both max_retries and task_retry_limit specified, raise an exception
        if constants.MAX_RETRIES_ATTRIBUTE in initDict and constants.TASK_RETRY_LIMIT_ATTRIBUTE in initDict:
            raise exceptions.MaxRetriesAndTaskRetryLimitMutuallyExclusiveError(self.name)
        
        # machine max_retries - sets taskRetryLimit internally
        if constants.MAX_RETRIES_ATTRIBUTE in initDict:
            logging.warning('max_retries is deprecated. Use task_retry_limit instead.')
            self.taskRetryLimit = initDict[constants.MAX_RETRIES_ATTRIBUTE]
            try:
                self.taskRetryLimit = int(self.taskRetryLimit)
            except ValueError:
                raise exceptions.InvalidMaxRetriesError(self.name, self.taskRetryLimit)
                        
        self.states = {}
        self.transitions = {}
        self.initialState = None
        self.finalStates = []
        
        # context types
        self.contextTypes = initDict.get(constants.MACHINE_CONTEXT_TYPES_ATTRIBUTE, {})
        for contextName, contextType in self.contextTypes.iteritems():
            self.contextTypes[contextName] = _resolveClass(contextType, self.namespace)
        
        self.rootUrl = rootUrl
        if not self.rootUrl:
            self.rootUrl = constants.DEFAULT_ROOT_URL
        elif not rootUrl.endswith('/'):
            self.rootUrl += '/'
            
    @property
    def maxRetries(self):
        """ maxRetries is a synonym for taskRetryLimit """
        return self.taskRetryLimit
        
    def addState(self, stateDict):
        """ Adds a state to this machine (using a dictionary representation). """
        state = _StateConfig(stateDict, self)
        if state.name in self.states:
            raise exceptions.StateNameNotUniqueError(self.name, state.name)
        self.states[state.name] = state
        
        if state.initial:
            if self.initialState:
                raise exceptions.MachineHasMultipleInitialStatesError(self.name)
            self.initialState = state
        if state.final:
            self.finalStates.append(state)
        
        return state
        
    def addTransition(self, transDict, fromStateName):
        """ Adds a transition to this machine (using a dictionary representation). """
        transition = _TransitionConfig(transDict, self, fromStateName)
        if transition.name in self.transitions:
            raise exceptions.TransitionNameNotUniqueError(self.name, transition.name)
        self.transitions[transition.name] = transition
        
        return transition
        
    @property
    def url(self):
        """ Returns the url for this machine. """
        return '%sfsm/%s/' % (self.rootUrl, self.name)
        
class _StateConfig(object):
    """ Configuration of a state. """
    
    # R0912:268:_StateConfig.__init__: Too many branches (22/20)
    def __init__(self, stateDict, machine): # pylint: disable-msg=R0912
        """ Builds a _StateConfig from a dictionary representation. This state is not added to the machine. """
        
        self.machineName = machine.name
        
        # state name
        self.name = stateDict.get(constants.STATE_NAME_ATTRIBUTE)
        if not self.name:
            raise exceptions.StateNameRequiredError(self.machineName)
        if not constants.NAME_RE.match(self.name):
            raise exceptions.InvalidStateNameError(self.machineName, self.name)
            
        # check for bad attributes
        badAttributes = set()
        for attribute in stateDict.iterkeys():
            if attribute not in constants.VALID_STATE_ATTRIBUTES:
                badAttributes.add(attribute)
        if badAttributes:
            raise exceptions.InvalidStateAttributeError(self.machineName, self.name, badAttributes)
        
        self.final = bool(stateDict.get(constants.STATE_FINAL_ATTRIBUTE, False))

        # state action
        actionName = stateDict.get(constants.STATE_ACTION_ATTRIBUTE)
        if not actionName and not self.final:
            raise exceptions.StateActionRequired(self.machineName, self.name)
            
        # state namespace, initial state flag, final state flag, continuation flag
        self.namespace = stateDict.get(constants.NAMESPACE_ATTRIBUTE, machine.namespace)
        self.initial = bool(stateDict.get(constants.STATE_INITIAL_ATTRIBUTE, False))
        self.continuation = bool(stateDict.get(constants.STATE_CONTINUATION_ATTRIBUTE, False))
        
        # state fan_in
        self.fanInPeriod = stateDict.get(constants.STATE_FAN_IN_ATTRIBUTE, constants.NO_FAN_IN)
        try:
            self.fanInPeriod = int(self.fanInPeriod)
        except ValueError:
            raise exceptions.InvalidFanInError(self.machineName, self.name, self.fanInPeriod)
            
        # check that a state is not BOTH fan_in and continuation
        if self.continuation and self.fanInPeriod != constants.NO_FAN_IN:
            raise exceptions.FanInContinuationNotSupportedError(self.machineName, self.name)
        
        # state action
        if stateDict.get(constants.STATE_ACTION_ATTRIBUTE):
            self.action = _resolveClass(actionName, self.namespace)()
            if not hasattr(self.action, 'execute'):
                raise exceptions.InvalidActionInterfaceError(self.machineName, self.name)
        else:
            self.action = None
        
        if self.continuation:
            if not hasattr(self.action, 'continuation'):
                raise exceptions.InvalidContinuationInterfaceError(self.machineName, self.name)
        else:
            if hasattr(self.action, 'continuation'):
                logging.warning('State\'s action class has a continuation attribute, but the state is ' + 
                                'not marked as continuation=True. This continuation method will not be ' +
                                'executed. (Machine %s, State %s)', self.machineName, self.name)
            
        # state entry
        if stateDict.get(constants.STATE_ENTRY_ATTRIBUTE):
            self.entry = _resolveClass(stateDict[constants.STATE_ENTRY_ATTRIBUTE], self.namespace)()
            if not hasattr(self.entry, 'execute'):
                raise exceptions.InvalidEntryInterfaceError(self.machineName, self.name)
        else:
            self.entry = None
        
        # state exit
        if stateDict.get(constants.STATE_EXIT_ATTRIBUTE):
            self.exit = _resolveClass(stateDict[constants.STATE_EXIT_ATTRIBUTE], self.namespace)()
            if not hasattr(self.exit, 'execute'):
                raise exceptions.InvalidExitInterfaceError(self.machineName, self.name)
            if self.continuation:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.name,
                    'Exit actions on continuation states are not supported.'
                )
            if self.fanInPeriod != constants.NO_FAN_IN:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.name,
                    'Exit actions on fan_in states are not supported.'
                )
        else:
            self.exit = None

class _TransitionConfig(object):
    """ Configuration of a transition. """
    
    # R0912:326:_TransitionConfig.__init__: Too many branches (22/20)
    def __init__(self, transDict, machine, fromStateName): # pylint: disable-msg=R0912
        """ Builds a _TransitionConfig from a dictionary representation. 
            This transition is not added to the machine. """

        self.machineName = machine.name
        
        # check for bad attributes
        badAttributes = set()
        for attribute in transDict.iterkeys():
            if attribute not in constants.VALID_TRANS_ATTRIBUTES:
                badAttributes.add(attribute)
        if badAttributes:
            raise exceptions.InvalidTransitionAttributeError(self.machineName, fromStateName, badAttributes)

        # transition event
        event = transDict.get(constants.TRANS_EVENT_ATTRIBUTE)
        if not event:
            raise exceptions.TransitionEventRequiredError(machine.name, fromStateName)
        try:
            # attempt to import the value of the event
            self.event = _resolveObject(event, machine.namespace)
        except (exceptions.UnknownModuleError, exceptions.UnknownClassError, exceptions.UnknownObjectError):
            # otherwise just use the value from the yaml
            self.event = event
        if not constants.NAME_RE.match(self.event):
            raise exceptions.InvalidTransitionEventNameError(self.machineName, fromStateName, self.event)
            
        # transition name
        self.name = '%s--%s' % (fromStateName, self.event)
        if not self.name:
            raise exceptions.TransitionNameRequiredError(self.machineName)
        if not constants.NAME_RE.match(self.name):
            raise exceptions.InvalidTransitionNameError(self.machineName, self.name)

        # transition from state
        if not fromStateName:
            raise exceptions.TransitionFromRequiredError(self.machineName, self.name)
        if fromStateName not in machine.states:
            raise exceptions.TransitionUnknownFromStateError(self.machineName, self.name, fromStateName)
        self.fromState = machine.states[fromStateName]
        
        # transition to state
        toStateName = transDict.get(constants.TRANS_TO_ATTRIBUTE)
        if not toStateName:
            raise exceptions.TransitionToRequiredError(self.machineName, self.name)
        if toStateName not in machine.states:
            raise exceptions.TransitionUnknownToStateError(self.machineName, self.name, toStateName)
        self.toState = machine.states[toStateName]
        
        # transition namespace
        self.namespace = transDict.get(constants.NAMESPACE_ATTRIBUTE, machine.namespace)

        # transition task_retry_limit, min_backoff_seconds, max_backoff_seconds, task_age_limit, max_doublings
        # W0612:439:_TransitionConfig.__init__: Unused variable 'default'
        for (constant, attribute, default, exception) in TASK_ATTRIBUTES: # pylint: disable-msg=W0612
            setattr(self, attribute, getattr(machine, attribute)) # default from the machine
            if constant in transDict:
                setattr(self, attribute, transDict[constant])
                try:
                    i = int(getattr(self, attribute))
                    setattr(self, attribute, i)
                except ValueError:
                    raise exception(self.machineName, getattr(self, attribute))

        # if both max_retries and task_retry_limit specified, raise an exception
        if constants.MAX_RETRIES_ATTRIBUTE in transDict and constants.TASK_RETRY_LIMIT_ATTRIBUTE in transDict:
            raise exceptions.MaxRetriesAndTaskRetryLimitMutuallyExclusiveError(self.machineName)
            
        # transition maxRetries
        if constants.MAX_RETRIES_ATTRIBUTE in transDict:
            logging.warning('max_retries is deprecated. Use task_retry_limit instead.')
            self.taskRetryLimit = transDict[constants.MAX_RETRIES_ATTRIBUTE]
            try:
                self.taskRetryLimit = int(self.taskRetryLimit)
            except ValueError:
                raise exceptions.InvalidMaxRetriesError(self.name, self.taskRetryLimit)
            
        # transition countdown
        self.countdown = transDict.get(constants.TRANS_COUNTDOWN_ATTRIBUTE, constants.DEFAULT_COUNTDOWN)
        try:
            self.countdown = int(self.countdown)
        except ValueError:
            raise exceptions.InvalidCountdownError(self.countdown, self.machineName, self.fromState.name)
        if self.countdown and self.toState.fanInPeriod != constants.NO_FAN_IN:
            raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                'Countdown cannot be specified on a transition to a fan_in state.'
            )
            
        # transition specific queue
        self.queueName = transDict.get(constants.QUEUE_NAME_ATTRIBUTE, machine.queueName)

        # resolve the class for action, if specified
        if constants.TRANS_ACTION_ATTRIBUTE in transDict:
            self.action = _resolveClass(transDict[constants.TRANS_ACTION_ATTRIBUTE], self.namespace)()
            if self.fromState.continuation:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                    'Transition actions on transitions from continuation states are not supported.'
                )
            if self.toState.continuation:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                    'Transition actions on transitions to continuation states are not supported.'
                )
            if self.fromState.fanInPeriod != constants.NO_FAN_IN:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                    'Transition actions on transitions from fan_in states are not supported.'
                )
            if self.toState.fanInPeriod != constants.NO_FAN_IN:
                raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                    'Transition actions on transitions to fan_in states are not supported.'
                )
        else:
            self.action = None
            
        # test for exit actions when transitions to a continuation or a fan_in
        if self.toState.continuation and self.fromState.exit:
            raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                'Exit actions on states with a transition to a continuation state are not supported.'
            )
        if self.toState.fanInPeriod != constants.NO_FAN_IN and self.fromState.exit:
            raise exceptions.UnsupportedConfigurationError(self.machineName, self.fromState.name,
                'Exit actions on states with a transition to a fan_in state are not supported.'
            )

    @property
    def maxRetries(self):
        """ maxRetries is a synonym for taskRetryLimit """
        return self.taskRetryLimit

########NEW FILE########
__FILENAME__ = console
""" Views for the console. """
import webapp2
from fantasm import config

class Dashboard(webapp2.RequestHandler):
    """ The main dashboard. """
    
    def get(self):
        """ GET """
        
        self.response.out.write(self.generateDashboard())
        
        
    def generateDashboard(self):
        """ Generates the HTML for the dashboard. """
        
        currentConfig = config.currentConfiguration()
        
        s = """
<html>
<head>
  <title>Fantasm</title>
"""
        s += STYLESHEET
        s += """
</head>
<body>

<h1>Fantasm</h1>

<h4>Configured Machines</h4>

<table class='ae-table ae-table-striped' cellpadding='0' cellspacing='0'>
<thead>
  <tr>
    <th>Name</th>
    <th>Queue</th>
    <th>States</th>
    <th>Transitions</th>
    <th>Chart</th>
  </tr>
</thead>
<tbody>
"""
        even = True
        for machineKey in sorted(currentConfig.machines.keys()):
            machine = currentConfig.machines[machineKey]
            even = False if even else True
            s += """
  <tr class='%(class)s'>
    <td>%(machineName)s</td>
    <td>%(queueName)s</td>
    <td>%(numStates)d</td>
    <td>%(numTransitions)d</td>
    <td><a href='%(rootUrl)sgraphviz/%(machineName)s/'>view</a></td>
  </tr>
""" % {
    'class': 'ae-even' if even else '',
    'machineName': machine.name,
    'queueName': machine.queueName,
    'numStates': len(machine.states),
    'numTransitions': len(machine.transitions),
    'rootUrl': currentConfig.rootUrl,
}

        s += """
</tbody>
</table>

</body>
</html>
"""
        return s


STYLESHEET = """
<style>
html, body, div, h1, h2, h3, h4, h5, h6, p, img, dl, dt, dd, ol, ul, li, table, caption, tbody, tfoot, thead, tr, th, td, form, fieldset, embed, object, applet {
    border: 0px;
    margin: 0px;
    padding: 0px;
}
body {
  color: black;
  font-family: Arial, sans-serif;
  padding: 20px;
  font-size: 0.95em;
}
h4, h5, table {
    font-size: 0.95em;
}
table {
    border-collapse: separate;
}
table[cellspacing=0] {
    border-spacing: 0px 0px;
}
thead {
    border-color: inherit;
    display: table-header-group;
    vertical-align: middle;
}
tbody {
    border-color: inherit;
    display: table-row-group;
    vertical-align: middle;
}
tr {
    border-color: inherit;
    display: table-row;
    vertical-align: inherit;
}
th {
    font-weight: bold;
}
td, th {
    display: table-cell;
    vertical-align: inherit;
}
.ae-table {
    border: 1px solid #C5D7EF;
    border-collapse: collapse;
    width: 100%;
}
.ae-table thead th {
    background: #C5D7EF;
    font-weight: bold;
    text-align: left;
    vertical-align: bottom;
}
.ae-table th, .ae-table td {
    background-color: white;
    margin: 0px;
    padding: 0.35em 1em 0.25em 0.35em;
}
.ae-table td {
    border-bottom: 1px solid #C5D7EF;
    border-top: 1px solid #C5D7EF;
}
.ae-even td, .ae-even th, .ae-even-top td, .ae-even-tween td, .ae-even-bottom td, ol.ae-even {
    background-color: #E9E9E9;
    border-bottom: 1px solid #C5D7EF;
    border-top: 1px solid #C5D7EF;
}
</style>
"""

########NEW FILE########
__FILENAME__ = constants
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import os
import re
import json

# these parameters are not stored in the FSMContext, but are used to drive the fantasm task/event dispatching mechanism
STATE_PARAM = '__st__'
EVENT_PARAM = '__ev__'
INSTANCE_NAME_PARAM = '__in__'
TERMINATED_PARAM = '__tm__'
TASK_NAME_PARAM = '__tn__'
FAN_IN_RESULTS_PARAM = '__fi__'
RETRY_COUNT_PARAM = '__rc__'
FORKED_CONTEXTS_PARAM = '__fc__'
IMMEDIATE_MODE_PARAM = '__im__'
MESSAGES_PARAM = '__ms__'
NON_CONTEXT_PARAMS = (STATE_PARAM, EVENT_PARAM, INSTANCE_NAME_PARAM, TERMINATED_PARAM, TASK_NAME_PARAM,
                      FAN_IN_RESULTS_PARAM, RETRY_COUNT_PARAM, FORKED_CONTEXTS_PARAM, IMMEDIATE_MODE_PARAM,
                      MESSAGES_PARAM)


# these parameters are stored in the FSMContext, and used to drive the task naming machanism
STEPS_PARAM = '__step__' # tracks the number of steps executed in the machine so far
CONTINUATION_PARAM = '__ct__' # tracks the continuation token (for continuation states)
GEN_PARAM = '__ge__' # used to uniquify the machine instance names (for continuations and spawns)
INDEX_PARAM = '__ix__'
WORK_INDEX_PARAM = '__wix__'
FORK_PARAM = '__fk__'
STARTED_AT_PARAM = '__sa__'

# this dict is used for casting strings in HttpRequest.GET to the appropriate type to put into FSMContext
PARAM_TYPES = {
    STEPS_PARAM : int,
    GEN_PARAM : json.loads,
    INDEX_PARAM: int,
    FORK_PARAM: int,
    STARTED_AT_PARAM: float,
}

CHARS_FOR_RANDOM = 'BDGHJKLMNPQRTVWXYZ23456789' # no vowels or things that look like vowels - profanity-free!

REQUEST_LENGTH = 30

MAX_NAME_LENGTH = 50 # we need to combine a number of names into a task name, which has a 500 char limit
NAME_PATTERN = r'^[a-zA-Z0-9-]{1,%s}$' % MAX_NAME_LENGTH
NAME_RE = re.compile(NAME_PATTERN)

HTTP_REQUEST_HEADER_PREFIX = 'X-Fantasm-'
HTTP_ENVIRON_KEY_PREFIX = 'HTTP_X_FANTASM_'

DEFAULT_TASK_RETRY_LIMIT = None
DEFAULT_MIN_BACKOFF_SECONDS = None
DEFAULT_MAX_BACKOFF_SECONDS = None
DEFAULT_TASK_AGE_LIMIT = None
DEFAULT_MAX_DOUBLINGS = None
DEFAULT_QUEUE_NAME = 'default'
DEFAULT_LOG_QUEUE_NAME = DEFAULT_QUEUE_NAME
DEFAULT_CLEANUP_QUEUE_NAME = DEFAULT_QUEUE_NAME

NO_FAN_IN = -1
DEFAULT_FAN_IN_PERIOD = NO_FAN_IN # fan_in period (in seconds)
DATASTORE_ASYNCRONOUS_INDEX_WRITE_WAIT_TIME = 5.0 # seconds

DEFAULT_COUNTDOWN = 0

YAML_NAMES = ('fsm.yaml', 'fsm.yml', 'fantasm.yaml', 'fantasm.yml')

DEFAULT_ROOT_URL = '/fantasm/' # where all the fantasm handlers are mounted
DEFAULT_LOG_URL = '/fantasm/log/'
DEFAULT_CLEANUP_URL = '/fantasm/cleanup/'

### attribute names for YAML parsing

IMPORT_ATTRIBUTE = 'import'

NAMESPACE_ATTRIBUTE = 'namespace'
QUEUE_NAME_ATTRIBUTE = 'queue'
MAX_RETRIES_ATTRIBUTE = 'max_retries' # deprecated, use task_retry_limit instead
TASK_RETRY_LIMIT_ATTRIBUTE = 'task_retry_limit'
MIN_BACKOFF_SECONDS_ATTRIBUTE = 'min_backoff_seconds'
MAX_BACKOFF_SECONDS_ATTRIBUTE = 'max_backoff_seconds'
TASK_AGE_LIMIT_ATTRIBUTE = 'task_age_limit'
MAX_DOUBLINGS_ATTRIBUTE = 'max_doublings'

ROOT_URL_ATTRIBUTE = 'root_url'
STATE_MACHINES_ATTRIBUTE = 'state_machines'
                        
MACHINE_NAME_ATTRIBUTE = 'name'
MACHINE_STATES_ATTRIBUTE = 'states'
MACHINE_TRANSITIONS_ATTRIBUTE = 'transitions'
MACHINE_CONTEXT_TYPES_ATTRIBUTE = 'context_types'
MACHINE_LOGGING_NAME_ATTRIBUTE = 'logging'
VALID_MACHINE_ATTRIBUTES = (NAMESPACE_ATTRIBUTE, MAX_RETRIES_ATTRIBUTE, TASK_RETRY_LIMIT_ATTRIBUTE,
                            MIN_BACKOFF_SECONDS_ATTRIBUTE, MAX_BACKOFF_SECONDS_ATTRIBUTE,
                            TASK_AGE_LIMIT_ATTRIBUTE, MAX_DOUBLINGS_ATTRIBUTE,
                            MACHINE_NAME_ATTRIBUTE, QUEUE_NAME_ATTRIBUTE, 
                            MACHINE_STATES_ATTRIBUTE, MACHINE_CONTEXT_TYPES_ATTRIBUTE,
                            MACHINE_LOGGING_NAME_ATTRIBUTE)
                            # MACHINE_TRANSITIONS_ATTRIBUTE is intentionally not in this list;
                            # it is used internally only

LOGGING_DEFAULT = 'default'
LOGGING_PERSISTENT = 'persistent'
VALID_LOGGING_VALUES = (LOGGING_DEFAULT, LOGGING_PERSISTENT)

STATE_NAME_ATTRIBUTE = 'name'
STATE_ENTRY_ATTRIBUTE = 'entry'
STATE_EXIT_ATTRIBUTE = 'exit'
STATE_ACTION_ATTRIBUTE = 'action'
STATE_INITIAL_ATTRIBUTE = 'initial'
STATE_FINAL_ATTRIBUTE = 'final'
STATE_CONTINUATION_ATTRIBUTE = 'continuation'
STATE_FAN_IN_ATTRIBUTE = 'fan_in'
STATE_TRANSITIONS_ATTRIBUTE = 'transitions'
VALID_STATE_ATTRIBUTES = (NAMESPACE_ATTRIBUTE, STATE_NAME_ATTRIBUTE, STATE_ENTRY_ATTRIBUTE, STATE_EXIT_ATTRIBUTE,
                          STATE_ACTION_ATTRIBUTE, STATE_INITIAL_ATTRIBUTE, STATE_FINAL_ATTRIBUTE, 
                          STATE_CONTINUATION_ATTRIBUTE, STATE_FAN_IN_ATTRIBUTE, STATE_TRANSITIONS_ATTRIBUTE)
                        
TRANS_TO_ATTRIBUTE = 'to'
TRANS_EVENT_ATTRIBUTE = 'event'
TRANS_ACTION_ATTRIBUTE = 'action'
TRANS_COUNTDOWN_ATTRIBUTE = 'countdown'
VALID_TRANS_ATTRIBUTES = (NAMESPACE_ATTRIBUTE, MAX_RETRIES_ATTRIBUTE, TASK_RETRY_LIMIT_ATTRIBUTE,
                          MIN_BACKOFF_SECONDS_ATTRIBUTE, MAX_BACKOFF_SECONDS_ATTRIBUTE,
                          TASK_AGE_LIMIT_ATTRIBUTE, MAX_DOUBLINGS_ATTRIBUTE,
                          TRANS_TO_ATTRIBUTE, TRANS_EVENT_ATTRIBUTE, TRANS_ACTION_ATTRIBUTE,
                          TRANS_COUNTDOWN_ATTRIBUTE, QUEUE_NAME_ATTRIBUTE)

DEV_APPSERVER = 'SERVER_SOFTWARE' in os.environ and os.environ['SERVER_SOFTWARE'].find('Development') >= 0

########NEW FILE########
__FILENAME__ = exceptions
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from fantasm import constants

class FSMRuntimeError(Exception):
    """ The parent class of all Fantasm runtime errors. """
    pass
    
class UnknownMachineError(FSMRuntimeError):
    """ A machine could not be found. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Cannot find machine "%s".' % machineName
        super(UnknownMachineError, self).__init__(message)

class UnknownStateError(FSMRuntimeError):
    """ A state could not be found  """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = 'State "%s" is unknown. (Machine %s)' % (stateName, machineName)
        super(UnknownStateError, self).__init__(message)
    
class UnknownEventError(FSMRuntimeError):
    """ An event and the transition bound to it could not be found. """
    def __init__(self, event, machineName, stateName):
        """ Initialize exception """
        message = 'Cannot find transition for event "%s". (Machine %s, State %s)' % (event, machineName, stateName)
        super(UnknownEventError, self).__init__(message)
        
class InvalidEventNameRuntimeError(FSMRuntimeError):
    """ Event returned from dispatch is invalid (and would cause problems with task name restrictions). """
    def __init__(self, event, machineName, stateName, instanceName):
        """ Initialize exception """
        message = 'Event "%r" returned by state is invalid. It must be a string and match pattern "%s". ' \
                  '(Machine %s, State %s, Instance %s)' % \
                  (event, constants.NAME_PATTERN, machineName, stateName, instanceName)
        super(InvalidEventNameRuntimeError, self).__init__(message)
        
class InvalidFinalEventRuntimeError(FSMRuntimeError):
    """ Event returned when a final state action returns an event. """
    def __init__(self, event, machineName, stateName, instanceName):
        """ Initialize exception """
        message = 'Event "%r" returned by final state is invalid. ' \
                  '(Machine %s, State %s, Instance %s)' % \
                  (event, machineName, stateName, instanceName)
        super(InvalidFinalEventRuntimeError, self).__init__(message)
        
class FanInWriteLockFailureRuntimeError(FSMRuntimeError):
    """ Exception when fan-in writers are unable to acquire a lock. """
    def __init__(self, event, machineName, stateName, instanceName):
        """ Initialize exception """
        message = 'Event "%r" unable to to be fanned-in due to write lock failure. ' \
                  '(Machine %s, State %s, Instance %s)' % \
                  (event, machineName, stateName, instanceName)
        super(FanInWriteLockFailureRuntimeError, self).__init__(message)
        
class FanInReadLockFailureRuntimeError(FSMRuntimeError):
    """ Exception when fan-in readers are unable to acquire a lock. """
    def __init__(self, event, machineName, stateName, instanceName):
        """ Initialize exception """
        message = 'Event "%r" unable to to be fanned-in due to read lock failure. ' \
                  '(Machine %s, State %s, Instance %s)' % \
                  (event, machineName, stateName, instanceName)
        super(FanInReadLockFailureRuntimeError, self).__init__(message)
        
class RequiredServicesUnavailableRuntimeError(FSMRuntimeError):
    """ Some of the required API services are not available. """
    def __init__(self, unavailableServices):
        """ Initialize exception """
        message = 'The following services will not be available in the %d seconds: %s. This task will be retried.' % \
                  (constants.REQUEST_LENGTH, unavailableServices)
        super(RequiredServicesUnavailableRuntimeError, self).__init__(message)
        
class ConfigurationError(Exception):
    """ Parent class for all Fantasm configuration errors. """
    pass
    
class YamlFileNotFoundError(ConfigurationError):
    """ The Yaml file could not be found. """
    def __init__(self, filename):
        """ Initialize exception """
        message = 'Yaml configuration file "%s" not found.' % filename
        super(YamlFileNotFoundError, self).__init__(message)
        
class YamlFileCircularImportError(ConfigurationError):
    """ The Yaml is involved in a circular import. """
    def __init__(self, filename):
        """ Initialize exception """
        message = 'Yaml configuration file "%s" involved in a circular import.' % filename
        super(YamlFileCircularImportError, self).__init__(message)
    
class StateMachinesAttributeRequiredError(ConfigurationError):
    """ The YAML file requires a 'state_machines' attribute. """
    def __init__(self):
        """ Initialize exception """
        message = '"%s" is required attribute of yaml file.' % constants.STATE_MACHINES_ATTRIBUTE
        super(StateMachinesAttributeRequiredError, self).__init__(message)

class MachineNameRequiredError(ConfigurationError):
    """ Each machine requires a name. """
    def __init__(self):
        """ Initialize exception """
        message = '"%s" is required attribute of machine.' % constants.MACHINE_NAME_ATTRIBUTE
        super(MachineNameRequiredError, self).__init__(message)
        
class InvalidQueueNameError(ConfigurationError):
    """ The queue name was not valid. """
    def __init__(self, queueName, machineName):
        """ Initialize exception """
        message = 'Queue name "%s" must exist in queue.yaml. (Machine %s)' % (queueName, machineName)
        super(InvalidQueueNameError, self).__init__(message)

class InvalidMachineNameError(ConfigurationError):
    """ The machine name was not valid. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine name must match pattern "%s". (Machine %s)' % (constants.NAME_PATTERN, machineName)
        super(InvalidMachineNameError, self).__init__(message)

class MachineNameNotUniqueError(ConfigurationError):
    """ Each machine in a YAML file must have a unique name. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine names must be unique. (Machine %s)' % machineName
        super(MachineNameNotUniqueError, self).__init__(message)
        
class MachineHasMultipleInitialStatesError(ConfigurationError):
    """ Each machine must have exactly one initial state. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine has multiple initial states, but only one is allowed. (Machine %s)' % machineName
        super(MachineHasMultipleInitialStatesError, self).__init__(message)
        
class MachineHasNoInitialStateError(ConfigurationError):
    """ Each machine must have exactly one initial state. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine has no initial state, exactly one is required. (Machine %s)' % machineName
        super(MachineHasNoInitialStateError, self).__init__(message)
        
class MachineHasNoFinalStateError(ConfigurationError):
    """ Each machine must have at least one final state. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'Machine has no final states, but at least one is required. (Machine %s)' % machineName
        super(MachineHasNoFinalStateError, self).__init__(message)

class StateNameRequiredError(ConfigurationError):
    """ Each state requires a name. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = '"%s" is required attribute of state. (Machine %s)' % (constants.STATE_NAME_ATTRIBUTE, machineName)
        super(StateNameRequiredError, self).__init__(message)

class InvalidStateNameError(ConfigurationError):
    """ The state name was not valid. """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = 'State name must match pattern "%s". (Machine %s, State %s)' % \
                  (constants.NAME_PATTERN, machineName, stateName)
        super(InvalidStateNameError, self).__init__(message)

class StateNameNotUniqueError(ConfigurationError):
    """ Each state within a machine must have a unique name. """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = 'State names within a machine must be unique. (Machine %s, State %s)' % \
                  (machineName, stateName)
        super(StateNameNotUniqueError, self).__init__(message)

class StateActionRequired(ConfigurationError):
    """ Each state requires an action. """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = '"%s" is required attribute of state. (Machine %s, State %s)' % \
                  (constants.STATE_ACTION_ATTRIBUTE, machineName, stateName)
        super(StateActionRequired, self).__init__(message)

class UnknownModuleError(ConfigurationError):
    """ When resolving actions, the module was not found. """
    def __init__(self, moduleName, importError):
        """ Initialize exception """
        message = 'Module "%s" cannot be imported due to "%s".' % (moduleName, importError)
        super(UnknownModuleError, self).__init__(message)

class UnknownClassError(ConfigurationError):
    """ When resolving actions, the class was not found. """
    def __init__(self, moduleName, className):
        """ Initialize exception """
        message = 'Class "%s" was not found in module "%s".' % (className, moduleName)
        super(UnknownClassError, self).__init__(message)
        
class UnknownObjectError(ConfigurationError):
    """ When resolving actions, the object was not found. """
    def __init__(self, objectName):
        """ Initialize exception """
        message = 'Object "%s" was not found.' % (objectName)
        super(UnknownObjectError, self).__init__(message)
        
class UnexpectedObjectTypeError(ConfigurationError):
    """ When resolving actions, the object was not found. """
    def __init__(self, objectName, expectedType):
        """ Initialize exception """
        message = 'Object "%s" is not of type "%s".' % (objectName, expectedType)
        super(UnexpectedObjectTypeError, self).__init__(message)
        
class InvalidMaxRetriesError(ConfigurationError):
    """ max_retries must be a positive integer. """
    def __init__(self, machineName, maxRetries):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.MAX_RETRIES_ATTRIBUTE, maxRetries, machineName)
        super(InvalidMaxRetriesError, self).__init__(message)

class InvalidTaskRetryLimitError(ConfigurationError):
    """ task_retry_limit must be a positive integer. """
    def __init__(self, machineName, taskRetryLimit):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.TASK_RETRY_LIMIT_ATTRIBUTE, taskRetryLimit, machineName)
        super(InvalidTaskRetryLimitError, self).__init__(message)

class InvalidMinBackoffSecondsError(ConfigurationError):
    """ min_backoff_seconds must be a positive integer. """
    def __init__(self, machineName, minBackoffSeconds):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.MIN_BACKOFF_SECONDS_ATTRIBUTE, minBackoffSeconds, machineName)
        super(InvalidMinBackoffSecondsError, self).__init__(message)
        
class InvalidMaxBackoffSecondsError(ConfigurationError):
    """ max_backoff_seconds must be a positive integer. """
    def __init__(self, machineName, maxBackoffSeconds):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.MAX_BACKOFF_SECONDS_ATTRIBUTE, maxBackoffSeconds, machineName)
        super(InvalidMaxBackoffSecondsError, self).__init__(message)
        
class InvalidTaskAgeLimitError(ConfigurationError):
    """ task_age_limit must be a positive integer. """
    def __init__(self, machineName, taskAgeLimit):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.TASK_AGE_LIMIT_ATTRIBUTE, taskAgeLimit, machineName)
        super(InvalidTaskAgeLimitError, self).__init__(message)
        
class InvalidMaxDoublingsError(ConfigurationError):
    """ max_doublings must be a positive integer. """
    def __init__(self, machineName, maxDoublings):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s)' % \
                  (constants.MAX_DOUBLINGS_ATTRIBUTE, maxDoublings, machineName)
        super(InvalidMaxDoublingsError, self).__init__(message)
        
class MaxRetriesAndTaskRetryLimitMutuallyExclusiveError(ConfigurationError):
    """ max_retries and task_retry_limit cannot both be specified on a machine. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = 'max_retries and task_retry_limit cannot both be specified on a machine. (Machine %s)' % \
                  machineName
        super(MaxRetriesAndTaskRetryLimitMutuallyExclusiveError, self).__init__(message)
        
class InvalidLoggingError(ConfigurationError):
    """ The logging value was not valid. """
    def __init__(self, machineName, loggingValue):
        """ Initialize exception """
        message = 'logging attribute "%s" is invalid (must be one of "%s"). (Machine %s)' % \
                  (loggingValue, constants.VALID_LOGGING_VALUES, machineName)
        super(InvalidLoggingError, self).__init__(message)

class TransitionNameRequiredError(ConfigurationError):
    """ Each transition requires a name. """
    def __init__(self, machineName):
        """ Initialize exception """
        message = '"%s" is required attribute of transition. (Machine %s)' % \
                  (constants.TRANS_NAME_ATTRIBUTE, machineName)
        super(TransitionNameRequiredError, self).__init__(message)

class InvalidTransitionNameError(ConfigurationError):
    """ The transition name was invalid. """
    def __init__(self, machineName, transitionName):
        """ Initialize exception """
        message = 'Transition name must match pattern "%s". (Machine %s, Transition %s)' % \
                  (constants.NAME_PATTERN, machineName, transitionName)
        super(InvalidTransitionNameError, self).__init__(message)

class TransitionNameNotUniqueError(ConfigurationError):
    """ Each transition within a machine must have a unique name. """
    def __init__(self, machineName, transitionName):
        """ Initialize exception """
        message = 'Transition names within a machine must be unique. (Machine %s, Transition %s)' % \
                  (machineName, transitionName)
        super(TransitionNameNotUniqueError, self).__init__(message)

class InvalidTransitionEventNameError(ConfigurationError):
    """ The transition's event name was invalid. """
    def __init__(self, machineName, fromStateName, eventName):
        """ Initialize exception """
        message = 'Transition event name must match pattern "%s". (Machine %s, State %s, Event %s)' % \
                  (constants.NAME_PATTERN, machineName, fromStateName, eventName)
        super(InvalidTransitionEventNameError, self).__init__(message)

class TransitionUnknownToStateError(ConfigurationError):
    """ Each transition must specify a to state. """
    def __init__(self, machineName, transitionName, toState):
        """ Initialize exception """
        message = 'Transition to state is undefined. (Machine %s, Transition %s, To %s)' % \
                  (machineName, transitionName, toState)
        super(TransitionUnknownToStateError, self).__init__(message)

class TransitionToRequiredError(ConfigurationError):
    """ The specified to state is unknown. """
    def __init__(self, machineName, transitionName):
        """ Initialize exception """
        message = '"%s" is required attribute of transition. (Machine %s, Transition %s)' % \
                  (constants.TRANS_TO_ATTRIBUTE, machineName, transitionName)
        super(TransitionToRequiredError, self).__init__(message)

class TransitionEventRequiredError(ConfigurationError):
    """ Each transition requires an event to be bound to. """
    def __init__(self, machineName, fromStateName):
        """ Initialize exception """
        message = '"%s" is required attribute of transition. (Machine %s, State %s)' % \
                  (constants.TRANS_EVENT_ATTRIBUTE, machineName, fromStateName)
        super(TransitionEventRequiredError, self).__init__(message)
        
class InvalidCountdownError(ConfigurationError):
    """ Countdown must be a positive integer. """
    def __init__(self, countdown, machineName, fromStateName):
        """ Initialize exception """
        message = 'Countdown "%s" must be a positive integer. (Machine %s, State %s)' % \
                  (countdown, machineName, fromStateName)
        super(InvalidCountdownError, self).__init__(message)

class InvalidMachineAttributeError(ConfigurationError):
    """ Unknown machine attributes were found. """
    def __init__(self, machineName, badAttributes):
        """ Initialize exception """
        message = 'The following are invalid attributes a machine: %s. (Machine %s)' % \
                  (badAttributes, machineName)
        super(InvalidMachineAttributeError, self).__init__(message)

class InvalidStateAttributeError(ConfigurationError):
    """ Unknown state attributes were found. """
    def __init__(self, machineName, stateName, badAttributes):
        """ Initialize exception """
        message = 'The following are invalid attributes a state: %s. (Machine %s, State %s)' % \
                  (badAttributes, machineName, stateName)
        super(InvalidStateAttributeError, self).__init__(message)

class InvalidTransitionAttributeError(ConfigurationError):
    """ Unknown transition attributes were found. """
    def __init__(self, machineName, fromStateName, badAttributes):
        """ Initialize exception """
        message = 'The following are invalid attributes a transition: %s. (Machine %s, State %s)' % \
                  (badAttributes, machineName, fromStateName)
        super(InvalidTransitionAttributeError, self).__init__(message)

class InvalidInterfaceError(ConfigurationError):
    """ Interface errors. """
    pass

class InvalidContinuationInterfaceError(InvalidInterfaceError):
    """ The specified state was denoted as a continuation, but it does not have a continuation method. """
    def __init__(self, machineName, stateName):
        message = 'The state was specified as continuation=True, but the action class does not have a ' + \
                  'continuation() method. (Machine %s, State %s)' % (machineName, stateName)
        super(InvalidContinuationInterfaceError, self).__init__(message)

class InvalidActionInterfaceError(InvalidInterfaceError):
    """ The specified state's action class does not have an execute() method. """
    def __init__(self, machineName, stateName):
        message = 'The state\'s action class does not have an execute() method. (Machine %s, State %s)' % \
                  (machineName, stateName)
        super(InvalidActionInterfaceError, self).__init__(message)

class InvalidEntryInterfaceError(InvalidInterfaceError):
    """ The specified state's entry class does not have an execute() method. """
    def __init__(self, machineName, stateName):
        message = 'The state\'s entry class does not have an execute() method. (Machine %s, State %s)' % \
                  (machineName, stateName)
        super(InvalidEntryInterfaceError, self).__init__(message)

class InvalidExitInterfaceError(InvalidInterfaceError):
    """ The specified state's exit class does not have an execute() method. """
    def __init__(self, machineName, stateName):
        message = 'The state\'s exit class does not have an execute() method. (Machine %s, State %s)' % \
                  (machineName, stateName)
        super(InvalidExitInterfaceError, self).__init__(message)

class InvalidFanInError(ConfigurationError):
    """ fan_in must be a positive integer. """
    def __init__(self, machineName, stateName, fanInPeriod):
        """ Initialize exception """
        message = '%s "%s" is invalid. Must be an integer. (Machine %s, State %s)' % \
                  (constants.STATE_FAN_IN_ATTRIBUTE, fanInPeriod, machineName, stateName)
        super(InvalidFanInError, self).__init__(message)

class FanInContinuationNotSupportedError(ConfigurationError):
    """ Cannot have fan_in and continuation on the same state, because it hurts our head at the moment. """
    def __init__(self, machineName, stateName):
        """ Initialize exception """
        message = '%s and %s are not supported on the same state. Maybe some day... (Machine %s, State %s)' % \
                  (constants.STATE_CONTINUATION_ATTRIBUTE, constants.STATE_FAN_IN_ATTRIBUTE,
                   machineName, stateName)
        super(FanInContinuationNotSupportedError, self).__init__(message)

class UnsupportedConfigurationError(ConfigurationError):
    """ Some exit and transition actions are not allowed near fan_in and continuation. At least not at the moment. """
    def __init__(self, machineName, stateName, message):
        """ Initialize exception """
        message = '%s (Machine %s, State %s)' % (message, machineName, stateName)
        super(UnsupportedConfigurationError, self).__init__(message)
########NEW FILE########
__FILENAME__ = fsm
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.



The FSM implementation is inspired by the paper:

[1] J. van Gurp, J. Bosch, "On the Implementation of Finite State Machines", in Proceedings of the 3rd Annual IASTED
    International Conference Software Engineering and Applications,IASTED/Acta Press, Anaheim, CA, pp. 172-178, 1999.
    (www.jillesvangurp.com/static/fsm-sea99.pdf)

The Fan-out / Fan-in implementation is modeled after the presentation:
    
[2] B. Slatkin, "Building high-throughput data pipelines with Google App Engine", Google IO 2010.
    http://code.google.com/events/io/2010/sessions/high-throughput-data-pipelines-appengine.html
"""

import datetime
import random
import copy
import time
import json
from google.appengine.api.taskqueue.taskqueue import Task, TaskAlreadyExistsError, TombstonedTaskError, \
                                                     TaskRetryOptions
from google.appengine.ext import db
from google.appengine.api import memcache
from fantasm import constants, config
from fantasm.log import Logger
from fantasm.state import State
from fantasm.transition import Transition
from fantasm.exceptions import UnknownEventError, UnknownStateError, UnknownMachineError
from fantasm.models import _FantasmFanIn, _FantasmInstance
from fantasm import models
from fantasm.utils import knuthHash
from fantasm.lock import ReadWriteLock, RunOnceSemaphore

class FSM(object):
    """ An FSMContext creation factory. This is primarily responsible for translating machine
    configuration information (config.currentConfiguration()) into singleton States and Transitions as per [1]
    """
    
    PSEUDO_INIT = 'pseudo-init'
    PSEUDO_FINAL = 'pseudo-final'
    
    _CURRENT_CONFIG = None
    _MACHINES = None
    _PSEUDO_INITS = None
    _PSEUDO_FINALS = None
    
    def __init__(self, currentConfig=None):
        """ Constructor which either initializes the module/class-level cache, or simply uses it 
        
        @param currentConfig: a config._Configuration instance (dependency injection). if None, 
            then the factory uses config.currentConfiguration()
        """
        currentConfig = currentConfig or config.currentConfiguration()
        
        # if the FSM is not using the currentConfig (.yaml was edited etc.)
        if not (FSM._CURRENT_CONFIG is currentConfig):
            self._init(currentConfig=currentConfig)
            FSM._CURRENT_CONFIG = self.config
            FSM._MACHINES = self.machines
            FSM._PSEUDO_INITS = self.pseudoInits
            FSM._PSEUDO_FINALS = self.pseudoFinals
            
        # otherwise simply use the cached currentConfig etc.
        else:
            self.config = FSM._CURRENT_CONFIG
            self.machines = FSM._MACHINES
            self.pseudoInits = FSM._PSEUDO_INITS
            self.pseudoFinals = FSM._PSEUDO_FINALS
    
    def _init(self, currentConfig=None):
        """ Constructs a group of singleton States and Transitions from the machineConfig 
        
        @param currentConfig: a config._Configuration instance (dependency injection). if None, 
            then the factory uses config.currentConfiguration()
        """
        import logging
        logging.info("Initializing FSM factory.")
        
        self.config = currentConfig or config.currentConfiguration()
        self.machines = {}
        self.pseudoInits, self.pseudoFinals = {}, {}
        for machineConfig in self.config.machines.values():
            self.machines[machineConfig.name] = {constants.MACHINE_STATES_ATTRIBUTE: {}, 
                                                 constants.MACHINE_TRANSITIONS_ATTRIBUTE: {}}
            machine = self.machines[machineConfig.name]
            
            # create a pseudo-init state for each machine that transitions to the initialState
            pseudoInit = State(FSM.PSEUDO_INIT, None, None, None)
            self.pseudoInits[machineConfig.name] = pseudoInit
            self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE][FSM.PSEUDO_INIT] = pseudoInit
            
            # create a pseudo-final state for each machine that transitions from the finalState(s)
            pseudoFinal = State(FSM.PSEUDO_FINAL, None, None, None, isFinalState=True)
            self.pseudoFinals[machineConfig.name] = pseudoFinal
            self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE][FSM.PSEUDO_FINAL] = pseudoFinal
            
            for stateConfig in machineConfig.states.values():
                state = self._getState(machineConfig, stateConfig)
                
                # add the transition from pseudo-init to initialState
                if state.isInitialState:
                    transition = Transition(FSM.PSEUDO_INIT, state, 
                                            retryOptions = self._buildRetryOptions(machineConfig),
                                            queueName=machineConfig.queueName)
                    self.pseudoInits[machineConfig.name].addTransition(transition, FSM.PSEUDO_INIT)
                    
                # add the transition from finalState to pseudo-final
                if state.isFinalState:
                    transition = Transition(FSM.PSEUDO_FINAL, pseudoFinal,
                                            retryOptions = self._buildRetryOptions(machineConfig),
                                            queueName=machineConfig.queueName)
                    state.addTransition(transition, FSM.PSEUDO_FINAL)
                    
                machine[constants.MACHINE_STATES_ATTRIBUTE][stateConfig.name] = state
                
            for transitionConfig in machineConfig.transitions.values():
                source = machine[constants.MACHINE_STATES_ATTRIBUTE][transitionConfig.fromState.name]
                transition = self._getTransition(machineConfig, transitionConfig)
                machine[constants.MACHINE_TRANSITIONS_ATTRIBUTE][transitionConfig.name] = transition
                event = transitionConfig.event
                source.addTransition(transition, event)
                
    def _buildRetryOptions(self, obj):
        """ Builds a TaskRetryOptions object. """
        return TaskRetryOptions(
            task_retry_limit = obj.taskRetryLimit,
            min_backoff_seconds = obj.minBackoffSeconds,
            max_backoff_seconds = obj.maxBackoffSeconds,
            task_age_limit = obj.taskAgeLimit,
            max_doublings = obj.maxDoublings)
                
    def _getState(self, machineConfig, stateConfig):
        """ Returns a State instance based on the machineConfig/stateConfig 
        
        @param machineConfig: a config._MachineConfig instance
        @param stateConfig: a config._StateConfig instance  
        @return: a State instance which is a singleton wrt. the FSM instance
        """
        
        if machineConfig.name in self.machines and \
           stateConfig.name in self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE]:
            return self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE][stateConfig.name]
        
        name = stateConfig.name
        entryAction = stateConfig.entry
        doAction = stateConfig.action
        exitAction = stateConfig.exit
        isInitialState = stateConfig.initial
        isFinalState = stateConfig.final
        isContinuation = stateConfig.continuation
        fanInPeriod = stateConfig.fanInPeriod
        
        return State(name, 
                     entryAction, 
                     doAction, 
                     exitAction, 
                     machineName=machineConfig.name,
                     isInitialState=isInitialState,
                     isFinalState=isFinalState,
                     isContinuation=isContinuation,
                     fanInPeriod=fanInPeriod)
            
    def _getTransition(self, machineConfig, transitionConfig):
        """ Returns a Transition instance based on the machineConfig/transitionConfig 
        
        @param machineConfig: a config._MachineConfig instance
        @param transitionConfig: a config._TransitionConfig instance  
        @return: a Transition instance which is a singleton wrt. the FSM instance
        """
        if machineConfig.name in self.machines and \
           transitionConfig.name in self.machines[machineConfig.name][constants.MACHINE_TRANSITIONS_ATTRIBUTE]:
            return self.machines[machineConfig.name][constants.MACHINE_TRANSITIONS_ATTRIBUTE][transitionConfig.name]
        
        target = self.machines[machineConfig.name][constants.MACHINE_STATES_ATTRIBUTE][transitionConfig.toState.name]
        retryOptions = self._buildRetryOptions(transitionConfig)
        countdown = transitionConfig.countdown
        queueName = transitionConfig.queueName
        
        return Transition(transitionConfig.name, target, action=transitionConfig.action,
                          countdown=countdown, retryOptions=retryOptions, queueName=queueName)
        
    def createFSMInstance(self, machineName, currentStateName=None, instanceName=None, data=None, method='GET',
                          obj=None, headers=None):
        """ Creates an FSMContext instance with non-initialized data 
        
        @param machineName: the name of FSMContext to instantiate, as defined in fsm.yaml 
        @param currentStateName: the name of the state to place the FSMContext into
        @param instanceName: the name of the current instance
        @param data: a dict or FSMContext
        @param method: 'GET' or 'POST'
        @param obj: an object that the FSMContext can operate on
        @param headers: a dict of X-Fantasm request headers to pass along in Tasks 
        @raise UnknownMachineError: if machineName is unknown
        @raise UnknownStateError: is currentState name is not None and unknown in machine with name machineName
        @return: an FSMContext instance
        """
        
        try:
            machineConfig = self.config.machines[machineName]
        except KeyError:
            raise UnknownMachineError(machineName)
        
        initialState = self.machines[machineName][constants.MACHINE_STATES_ATTRIBUTE][machineConfig.initialState.name]
        
        try:
            currentState = self.pseudoInits[machineName]
            if currentStateName:
                currentState = self.machines[machineName][constants.MACHINE_STATES_ATTRIBUTE][currentStateName]
        except KeyError:
            raise UnknownStateError(machineName, currentStateName)
                
        retryOptions = self._buildRetryOptions(machineConfig)
        url = machineConfig.url
        queueName = machineConfig.queueName
        
        return FSMContext(initialState, currentState=currentState, 
                          machineName=machineName, instanceName=instanceName,
                          retryOptions=retryOptions, url=url, queueName=queueName,
                          data=data, contextTypes=machineConfig.contextTypes,
                          method=method,
                          persistentLogging=(machineConfig.logging == constants.LOGGING_PERSISTENT),
                          obj=obj,
                          headers=headers)

class FSMContext(dict):
    """ A finite state machine context instance. """
    
    def __init__(self, initialState, currentState=None, machineName=None, instanceName=None,
                 retryOptions=None, url=None, queueName=None, data=None, contextTypes=None,
                 method='GET', persistentLogging=False, obj=None, headers=None):
        """ Constructor
        
        @param initialState: a State instance 
        @param currentState: a State instance
        @param machineName: the name of the fsm
        @param instanceName: the instance name of the fsm
        @param retryOptions: the TaskRetryOptions for the machine
        @param url: the url of the fsm  
        @param queueName: the name of the appengine task queue 
        @param headers: a dict of X-Fantasm request headers to pass along in Tasks 
        @param persistentLogging: if True, use persistent _FantasmLog model
        @param obj: an object that the FSMContext can operate on  
        """
        assert queueName
        
        super(FSMContext, self).__init__(data or {})
        self.initialState = initialState
        self.currentState = currentState
        self.currentAction = None
        if currentState:
            self.currentAction = currentState.exitAction 
        self.machineName = machineName
        self.instanceName = instanceName or self._generateUniqueInstanceName()
        self.queueName = queueName
        self.retryOptions = retryOptions
        self.url = url
        self.method = method
        self.startingEvent = None
        self.startingState = None
        self.contextTypes = constants.PARAM_TYPES.copy()
        if contextTypes:
            self.contextTypes.update(contextTypes)
        self.logger = Logger(self, obj=obj, persistentLogging=persistentLogging)
        self.__obj = obj
        self.headers = headers
        
        # the following is monkey-patched from handler.py for 'immediate mode'
        from google.appengine.api.taskqueue.taskqueue import Queue
        self.Queue = Queue # pylint: disable-msg=C0103
        
    def _generateUniqueInstanceName(self):
        """ Generates a unique instance name for this machine. 
        
        @return: a FSMContext instanceName that is (pretty darn likely to be) unique
        """
        utcnow = datetime.datetime.utcnow()
        dateStr = utcnow.strftime('%Y%m%d%H%M%S')
        randomStr = ''.join(random.sample(constants.CHARS_FOR_RANDOM, 6))
        return '%s-%s-%s' % (self.machineName, dateStr, randomStr)
        
    def putTypedValue(self, key, value):
        """ Sets a value on context[key], but casts the value according to self.contextTypes. """

        # cast the value to the appropriate type TODO: should this be in FSMContext?
        cast = self.contextTypes[key]
        kwargs = {}
        if cast is json.loads:
            kwargs = {'object_hook': models.decode}
        if isinstance(value, list):
            value = [cast(v, **kwargs) for v in value]
        else:
            value = cast(value, **kwargs)

        # update the context
        self[key] = value
        
    def generateInitializationTask(self, countdown=0, taskName=None):
        """ Generates a task for initializing the machine. """
        assert self.currentState.name == FSM.PSEUDO_INIT
        
        url = self.buildUrl(self.currentState, FSM.PSEUDO_INIT)
        params = self.buildParams(self.currentState, FSM.PSEUDO_INIT)
        taskName = taskName or self.getTaskName(FSM.PSEUDO_INIT)
        transition = self.currentState.getTransition(FSM.PSEUDO_INIT)
        task = Task(name=taskName, 
                    method=self.method, 
                    url=url, 
                    params=params, 
                    countdown=countdown, 
                    headers=self.headers, 
                    retry_options=transition.retryOptions)
        return task
    
    def fork(self, data=None):
        """ Forks the FSMContext. 
        
        When an FSMContext is forked, an identical copy of the finite state machine is generated
        that will have the same event dispatched to it as the machine that called .fork(). The data
        parameter is useful for allowing each forked instance to operate on a different bit of data.
        
        @param data: an option mapping of data to apply to the forked FSMContext 
        """
        obj = self.__obj
        if obj.get(constants.FORKED_CONTEXTS_PARAM) is None:
            obj[constants.FORKED_CONTEXTS_PARAM] = []
        forkedContexts = obj.get(constants.FORKED_CONTEXTS_PARAM)
        data = copy.copy(data) or {}
        data[constants.FORK_PARAM] = len(forkedContexts)
        forkedContexts.append(self.clone(data=data))
    
    def spawn(self, machineName, contexts, countdown=0, method='POST', 
              _currentConfig=None):
        """ Spawns new machines.
        
        @param machineName the machine to spawn
        @param contexts a list of contexts (dictionaries) to spawn the new machine(s) with; multiple contexts will spawn
                        multiple machines
        @param countdown the countdown (in seconds) to wait before spawning machines
        @param method the method ('GET' or 'POST') to invoke the machine with (default: POST)
        
        @param _currentConfig test injection for configuration
        """
        # using the current task name as a root to startStateMachine will make this idempotent
        taskName = self.__obj[constants.TASK_NAME_PARAM]
        startStateMachine(machineName, contexts, taskName=taskName, method=method, countdown=countdown, 
                          _currentConfig=_currentConfig, headers=self.headers)
    
    def initialize(self):
        """ Initializes the FSMContext. Queues a Task (so that we can benefit from auto-retry) to dispatch
        an event and take the machine from 'pseudo-init' into the state machine's initial state, as 
        defined in the fsm.yaml file.
        
        @param data: a dict of initial key, value pairs to stuff into the FSMContext
        @return: an event string to dispatch to the FSMContext to put it into the initialState 
        """
        self[constants.STEPS_PARAM] = 0
        task = self.generateInitializationTask()
        self.Queue(name=self.queueName).add(task)
        _FantasmInstance(key_name=self.instanceName, instanceName=self.instanceName).put()
        
        return FSM.PSEUDO_INIT
        
    def dispatch(self, event, obj):
        """ The main entry point to move the machine according to an event. 
        
        @param event: a string event to dispatch to the FSMContext
        @param obj: an object that the FSMContext can operate on  
        @return: an event string to dispatch to the FSMContext
        """
        
        self.__obj = self.__obj or obj # hold the obj object for use during this context

        # store the starting state and event for the handleEvent() method
        self.startingState = self.currentState
        self.startingEvent = event

        nextEvent = None
        try:
            nextEvent = self.currentState.dispatch(self, event, obj)
            
            if obj.get(constants.FORKED_CONTEXTS_PARAM):
                # pylint: disable-msg=W0212
                # - accessing the protected method is fine here, since it is an instance of the same class
                tasks = []
                for context in obj[constants.FORKED_CONTEXTS_PARAM]:
                    context[constants.STEPS_PARAM] = int(context.get(constants.STEPS_PARAM, '0')) + 1
                    task = context.queueDispatch(nextEvent, queue=False)
                    if task: # fan-in magic
                        if not task.was_enqueued: # fan-in always queues
                            tasks.append(task)
                
                try:
                    if tasks:
                        transition = self.currentState.getTransition(nextEvent)
                        _queueTasks(self.Queue, transition.queueName, tasks)
                
                except (TaskAlreadyExistsError, TombstonedTaskError):
                    # unlike a similar block in self.continutation, this is well off the happy path
                    self.logger.critical(
                                     'Unable to queue fork Tasks %s as it/they already exists. (Machine %s, State %s)',
                                     [task.name for task in tasks if not task.was_enqueued],
                                     self.machineName, 
                                     self.currentState.name)
                
            if nextEvent:
                self[constants.STEPS_PARAM] = int(self.get(constants.STEPS_PARAM, '0')) + 1
                
                try:
                    self.queueDispatch(nextEvent)
                    
                except (TaskAlreadyExistsError, TombstonedTaskError):
                    # unlike a similar block in self.continutation, this is well off the happy path
                    #
                    # FIXME: when this happens, it means there was failure shortly after queuing the Task, or
                    #        possibly even with queuing the Task. when this happens there is a chance that 
                    #        two states in the machine are executing simultaneously, which is may or may not
                    #        be a good thing, depending on what each state does. gracefully handling this 
                    #        exception at least means that this state will terminate.
                    self.logger.critical('Unable to queue next Task as it already exists. (Machine %s, State %s)',
                                     self.machineName, 
                                     self.currentState.name)
                    
            else:
                # if we're not in a final state, emit a log message
                # FIXME - somehow we should avoid this message if we're in the "last" step of a continuation...
                if not self.currentState.isFinalState and not obj.get(constants.TERMINATED_PARAM):
                    self.logger.critical('Non-final state did not emit an event. Machine has terminated in an ' +
                                     'unknown state. (Machine %s, State %s)' %
                                     (self.machineName, self.currentState.name))
                # if it is a final state, then dispatch the pseudo-final event to finalize the state machine
                elif self.currentState.isFinalState and self.currentState.exitAction:
                    self[constants.STEPS_PARAM] = int(self.get(constants.STEPS_PARAM, '0')) + 1
                    self.queueDispatch(FSM.PSEUDO_FINAL)
                    
        except Exception:
            self.logger.exception("FSMContext.dispatch is handling the following exception:")
            self._handleException(event, obj)
            
        return nextEvent
    
    def continuation(self, nextToken):
        """ Performs a continuation be re-queueing an FSMContext Task with a slightly modified continuation
        token. self.startingState and self.startingEvent are used in the re-queue, so this can be seen as a
        'fork' of the current context.
        
        @param nextToken: the next continuation token
        """
        assert not self.get(constants.INDEX_PARAM) # fan-out after fan-in is not allowed
        step = str(self[constants.STEPS_PARAM]) # needs to be a str key into a json dict
        
        # make a copy and set the currentState to the startingState of this context
        context = self.clone()
        context.currentState = self.startingState
        
        # update the generation and continuation params
        gen = context.get(constants.GEN_PARAM, {})
        gen[step] = gen.get(step, 0) + 1
        context[constants.GEN_PARAM] = gen
        context[constants.CONTINUATION_PARAM] = nextToken
        
        try:
            # pylint: disable-msg=W0212
            # - accessing the protected method is fine here, since it is an instance of the same class
            transition = self.startingState.getTransition(self.startingEvent)
            context._queueDispatchNormal(self.startingEvent, queue=True, queueName=transition.queueName)
            
        except (TaskAlreadyExistsError, TombstonedTaskError):
            # this can happen when currentState.dispatch() previously succeeded in queueing the continuation
            # Task, but failed with the doAction.execute() call in a _previous_ execution of this Task.
            # NOTE: this prevent the dreaded "fork bomb" 
            self.logger.info('Unable to queue continuation Task as it already exists. (Machine %s, State %s)',
                          self.machineName, 
                          self.currentState.name)
    
    def queueDispatch(self, nextEvent, queue=True):
        """ Queues a .dispatch(nextEvent) call in the appengine Task queue. 
        
        @param nextEvent: a string event 
        @param queue: a boolean indicating whether or not to queue a Task, or leave it to the caller 
        @return: a taskqueue.Task instance which may or may not have been queued already
        """
        assert nextEvent is not None
        
        # self.currentState is already transitioned away from self.startingState
        transition = self.currentState.getTransition(nextEvent)
        if transition.target.isFanIn:
            task = self._queueDispatchFanIn(nextEvent, fanInPeriod=transition.target.fanInPeriod,
                                            retryOptions=transition.retryOptions,
                                            queueName=transition.queueName)
        else:
            task = self._queueDispatchNormal(nextEvent, queue=queue, countdown=transition.countdown,
                                             retryOptions=transition.retryOptions,
                                             queueName=transition.queueName)
            
        return task
        
    def _queueDispatchNormal(self, nextEvent, queue=True, countdown=0, retryOptions=None, queueName=None):
        """ Queues a call to .dispatch(nextEvent) in the appengine Task queue. 
        
        @param nextEvent: a string event 
        @param queue: a boolean indicating whether or not to queue a Task, or leave it to the caller 
        @param countdown: the number of seconds to countdown before the queued task fires
        @param retryOptions: the RetryOptions for the task
        @param queueName: the queue name to Queue into 
        @return: a taskqueue.Task instance which may or may not have been queued already
        """
        assert nextEvent is not None
        assert queueName
        
        url = self.buildUrl(self.currentState, nextEvent)
        params = self.buildParams(self.currentState, nextEvent)
        taskName = self.getTaskName(nextEvent)
        
        task = Task(name=taskName, method=self.method, url=url, params=params, countdown=countdown,
                    retry_options=retryOptions, headers=self.headers)
        if queue:
            self.Queue(name=queueName).add(task)
        
        return task
    
    def _queueDispatchFanIn(self, nextEvent, fanInPeriod=0, retryOptions=None, queueName=None):
        """ Queues a call to .dispatch(nextEvent) in the task queue, or saves the context to the 
        datastore for processing by the queued .dispatch(nextEvent)
        
        @param nextEvent: a string event 
        @param fanInPeriod: the period of time between fan in Tasks 
        @param queueName: the queue name to Queue into 
        @return: a taskqueue.Task instance which may or may not have been queued already
        """
        assert nextEvent is not None
        assert not self.get(constants.INDEX_PARAM) # fan-in after fan-in is not allowed
        assert queueName
        
        # we pop this off here because we do not want the fan-out/continuation param as part of the
        # task name, otherwise we loose the fan-in - each fan-in gets one work unit.
        self.pop(constants.GEN_PARAM, None)
        fork = self.pop(constants.FORK_PARAM, None)
        
        taskNameBase = self.getTaskName(nextEvent, fanIn=True)
        rwlock = ReadWriteLock(taskNameBase, self)
        index = rwlock.currentIndex()
            
        # (***)
        #
        # grab the lock - memcache.incr()
        # 
        # on Task retry, multiple incr() calls are possible. possible ways to handle:
        #
        # 1. release the lock in a 'finally' clause, but then risk missing a work
        #    package because acquiring the read lock will succeed even though the
        #    work package was not written yet.
        #
        # 2. allow the lock to get too high. the fan-in logic attempts to wait for 
        #    work packages across multiple-retry attempts, so this seems like the 
        #    best option. we basically trade a bit of latency in fan-in for reliability.
        #    
        rwlock.acquireWriteLock(index, nextEvent=nextEvent)
        
        # insert the work package, which is simply a serialized FSMContext
        workIndex = '%s-%d' % (taskNameBase, knuthHash(index))
        
        # on retry, we want to ensure we get the same work index for this task
        actualTaskName = self.__obj[constants.TASK_NAME_PARAM]
        indexKeyName = 'workIndex-' + '-'.join([str(i) for i in [actualTaskName, fork] if i]) or None
        semaphore = RunOnceSemaphore(indexKeyName, self)
        
        # check if the workIndex changed during retry
        semaphoreWritten = False
        if self.__obj[constants.RETRY_COUNT_PARAM] > 0:
            # see comment (A) in self._queueDispatchFanIn(...)
            time.sleep(constants.DATASTORE_ASYNCRONOUS_INDEX_WRITE_WAIT_TIME)
            payload = semaphore.readRunOnceSemaphore(payload=workIndex, transactional=False)
            if payload:
                semaphoreWritten = True
                if payload != workIndex:
                    self.logger.info("Work index changed from '%s' to '%s' on retry.", payload, workIndex)
                    workIndex = payload
                
        # write down two models, one actual work package, one idempotency package
        keyName = '-'.join([str(i) for i in [actualTaskName, fork] if i]) or None
        work = _FantasmFanIn(context=self, workIndex=workIndex, key_name=keyName)
        
        # close enough to idempotent, but could still write only one of the entities
        # FIXME: could be made faster using a bulk put, but this interface is cleaner
        if not semaphoreWritten:
            semaphore.writeRunOnceSemaphore(payload=workIndex, transactional=False)
        
        # put the work item
        db.put(work)
        
        # (A) now the datastore is asynchronously writing the indices, so the work package may
        #     not show up in a query for a period of time. there is a corresponding time.sleep()
        #     in the fan-in of self.mergeJoinDispatch(...) 
            
        # release the lock - memcache.decr()
        rwlock.releaseWriteLock(index)
            
        try:
            
            # insert a task to run in the future and process a bunch of work packages
            now = time.time()
            self[constants.INDEX_PARAM] = index
            url = self.buildUrl(self.currentState, nextEvent)
            params = self.buildParams(self.currentState, nextEvent)
            task = Task(name='%s-%d' % (taskNameBase, index),
                        method=self.method,
                        url=url,
                        params=params,
                        eta=datetime.datetime.utcfromtimestamp(now) + datetime.timedelta(seconds=fanInPeriod),
                        headers=self.headers,
                        retry_options=retryOptions)
            self.Queue(name=queueName).add(task)
            return task
        
        except (TaskAlreadyExistsError, TombstonedTaskError):
            pass # Fan-in magic
                
            
    def mergeJoinDispatch(self, event, obj):
        """ Performs a merge join on the pending fan-in dispatches.
        
        @param event: an event that is being merge joined (destination state must be a fan in) 
        @return: a list (possibly empty) of FSMContext instances
        """
        # this assertion comes from _queueDispatchFanIn - we never want fan-out info in a fan-in context
        assert not self.get(constants.GEN_PARAM)
        assert not self.get(constants.FORK_PARAM)
        
        # the work package index is stored in the url of the Task/FSMContext
        index = self.get(constants.INDEX_PARAM)
        taskNameBase = self.getTaskName(event, fanIn=True)
        
        # see comment (***) in self._queueDispatchFanIn 
        # 
        # in the case of failing to acquire a read lock (due to failed release of write lock)
        # we have decided to keep retrying
        raiseOnFail = False
        if self._getTaskRetryLimit() is not None:
            raiseOnFail = (self._getTaskRetryLimit() > self.__obj[constants.RETRY_COUNT_PARAM])
            
        rwlock = ReadWriteLock(taskNameBase, self)
        rwlock.acquireReadLock(index, raiseOnFail=raiseOnFail)
        
        # and return the FSMContexts list
        class FSMContextList(list):
            """ A list that supports .logger.info(), .logger.warning() etc.for fan-in actions """
            def __init__(self, context, contexts):
                """ setup a self.logger for fan-in actions """
                super(FSMContextList, self).__init__(contexts)
                self.logger = Logger(context)
                self.instanceName = context.instanceName
                
        # see comment (A) in self._queueDispatchFanIn(...)
        time.sleep(constants.DATASTORE_ASYNCRONOUS_INDEX_WRITE_WAIT_TIME)
                
        # the following step ensure that fan-in only ever operates one time over a list of data
        # the entity is created in State.dispatch(...) _after_ all the actions have executed
        # successfully
        workIndex = '%s-%d' % (taskNameBase, knuthHash(index))
        if obj[constants.RETRY_COUNT_PARAM] > 0:
            semaphore = RunOnceSemaphore(workIndex, self)
            if semaphore.readRunOnceSemaphore(payload=self.__obj[constants.TASK_NAME_PARAM]):
                self.logger.info("Fan-in idempotency guard for workIndex '%s', not processing any work items.", 
                                 workIndex)
                return FSMContextList(self, []) # don't operate over the data again
            
        # fetch all the work packages in the current group for processing
        query = _FantasmFanIn.all() \
                             .filter('workIndex =', workIndex) \
                             .order('__key__')
                             
        # construct a list of FSMContexts
        contexts = [self.clone(data=r.context) for r in query]
        return FSMContextList(self, contexts)
        
    def _getTaskRetryLimit(self):
        """ Method that returns the maximum number of retries for this particular dispatch 
        
        @param obj: an object that the FSMContext can operate on  
        """
        # get task_retry_limit configuration
        try:
            transition = self.startingState.getTransition(self.startingEvent)
            taskRetryLimit = transition.retryOptions.task_retry_limit
        except UnknownEventError:
            # can't find the transition, use the machine-level default
            taskRetryLimit = self.retryOptions.task_retry_limit
        return taskRetryLimit
            
    def _handleException(self, event, obj):
        """ Method for child classes to override to handle exceptions. 
        
        @param event: a string event 
        @param obj: an object that the FSMContext can operate on  
        """
        retryCount = obj.get(constants.RETRY_COUNT_PARAM, 0)
        taskRetryLimit = self._getTaskRetryLimit()
        
        if taskRetryLimit and retryCount >= taskRetryLimit:
            # need to permanently fail
            self.logger.critical('Max-requeues reached. Machine has terminated in an unknown state. ' +
                             '(Machine %s, State %s, Event %s)',
                             self.machineName, self.startingState.name, event, exc_info=True)
            # re-raise, letting App Engine TaskRetryOptions kill the task
            raise
        else:
            # re-raise the exception
            self.logger.warning('Exception occurred processing event. Task will be retried. ' +
                            '(Machine %s, State %s)',
                            self.machineName, self.startingState.name, exc_info=True)
            
            # this line really just allows unit tests to work - the request is really dead at this point
            self.currentState = self.startingState
            
            raise
    
    def buildUrl(self, state, event):
        """ Builds the taskqueue url. 
        
        @param state: the State to dispatch to
        @param event: the event to dispatch
        @return: a url that can be used to build a taskqueue.Task instance to .dispatch(event)
        """
        assert state and event
        return self.url + '%s/%s/%s/' % (state.name, 
                                         event, 
                                         state.getTransition(event).target.name)
    
    def buildParams(self, state, event):
        """ Builds the taskqueue params. 
        
        @param state: the State to dispatch to
        @param event: the event to dispatch
        @return: a dict suitable to use in constructing a url (GET) or using as params (POST)
        """
        assert state and event
        params = {constants.STATE_PARAM: state.name, 
                  constants.EVENT_PARAM: event,
                  constants.INSTANCE_NAME_PARAM: self.instanceName}
        for key, value in self.items():
            if key not in constants.NON_CONTEXT_PARAMS:
                if self.contextTypes.get(key) is json.loads:
                    value = json.dumps(value, cls=models.Encoder)
                if isinstance(value, datetime.datetime):
                    value = str(int(time.mktime(value.utctimetuple())))
                if isinstance(value, dict):
                    # FIXME: should we issue a warning that they should update fsm.yaml?
                    value = json.dumps(value, cls=models.Encoder)
                if isinstance(value, list) and len(value) == 1:
                    key = key + '[]' # used to preserve lists of length=1 - see handler.py for inverse
                params[key] = value
        return params

    def getTaskName(self, nextEvent, instanceName=None, fanIn=False):
        """ Returns a task name that is unique for a specific dispatch 
        
        @param nextEvent: the event to dispatch
        @return: a task name that can be used to build a taskqueue.Task instance to .dispatch(nextEvent)
        """
        transition = self.currentState.getTransition(nextEvent)
        parts = []
        parts.append(instanceName or self.instanceName)
        
        if self.get(constants.GEN_PARAM):
            for (step, gen) in self[constants.GEN_PARAM].items():
                parts.append('continuation-%s-%s' % (step, gen))
        if self.get(constants.FORK_PARAM):
            parts.append('fork-' + str(self[constants.FORK_PARAM]))
        # post-fan-in we need to store the workIndex in the task name to avoid duplicates, since
        # we popped the generation off during fan-in
        # FIXME: maybe not pop the generation in fan-in?
        # FIXME: maybe store this in the instanceName?
        # FIXME: i wish this was easier to get right :-)
        if (not fanIn) and self.get(constants.INDEX_PARAM):
            parts.append('work-index-' + str(self[constants.INDEX_PARAM]))
        parts.append(self.currentState.name)
        parts.append(nextEvent)
        parts.append(transition.target.name)
        parts.append('step-' + str(self[constants.STEPS_PARAM]))
        return '--'.join(parts)
    
    def clone(self, instanceName=None, data=None):
        """ Returns a copy of the FSMContext.
        
        @param instanceName: the instance name to optionally apply to the clone
        @param data: a dict/mapping of data to optionally apply (.update()) to the clone
        @return: a new FSMContext instance
        """
        context = copy.deepcopy(self)
        if instanceName:
            context.instanceName = instanceName
        if data:
            context.update(data)
        return context
    
# pylint: disable-msg=C0103
def _queueTasks(Queue, queueName, tasks):
    """
    Add a list of Tasks to the supplied Queue/queueName
    
    @param Queue: taskqueue.Queue or other object with .add() method
    @param queueName: a queue name from queue.yaml
    @param tasks: a list of taskqueue.Tasks
    
    @raise TaskAlreadyExistsError: 
    @raise TombstonedTaskError: 
    """
    
    from google.appengine.api.taskqueue.taskqueue import MAX_TASKS_PER_ADD
    taskAlreadyExists, tombstonedTask = None, None

    # queue the Tasks in groups of MAX_TASKS_PER_ADD
    i = 0
    for i in xrange(len(tasks)):
        someTasks = tasks[i * MAX_TASKS_PER_ADD : (i+1) * MAX_TASKS_PER_ADD]
        if not someTasks:
            break
        
        # queue them up, and loop back for more, even if there are failures
        try:
            Queue(name=queueName).add(someTasks)
                
        except TaskAlreadyExistsError, e:
            taskAlreadyExists = e
            
        except TombstonedTaskError, e:
            tombstonedTask = e
            
    if taskAlreadyExists:
        # pylint: disable-msg=E0702
        raise taskAlreadyExists
    
    if tombstonedTask:
        # pylint: disable-msg=E0702
        raise tombstonedTask

def startStateMachine(machineName, contexts, taskName=None, method='POST', countdown=0,
                      _currentConfig=None, headers=None):
    """ Starts a new machine(s), by simply queuing a task. 
    
    @param machineName the name of the machine in the FSM to start
    @param contexts a list of contexts to start the machine with; a machine will be started for each context
    @param taskName used for idempotency; will become the root of the task name for the actual task queued
    @param method the HTTP methld (GET/POST) to run the machine with (default 'POST')
    @param countdown the number of seconds into the future to start the machine (default 0 - immediately)
                     or a list of sumber of seconds (must be same length as contexts)
    @param headers: a dict of X-Fantasm request headers to pass along in Tasks 
    
    @param _currentConfig used for test injection (default None - use fsm.yaml definitions)
    """
    if not contexts:
        return
    if not isinstance(contexts, list):
        contexts = [contexts]
    if not isinstance(countdown, list):
        countdown = [countdown] * len(contexts)
        
    # FIXME: I shouldn't have to do this.
    for context in contexts:
        context[constants.STEPS_PARAM] = 0
        
    fsm = FSM(currentConfig=_currentConfig) # loads the FSM definition
    
    instances = [fsm.createFSMInstance(machineName, data=context, method=method, headers=headers) 
                 for context in contexts]
    
    tasks = []
    for i, instance in enumerate(instances):
        tname = None
        if taskName:
            tname = '%s--startStateMachine-%d' % (taskName, i)
        task = instance.generateInitializationTask(countdown=countdown[i], taskName=tname)
        tasks.append(task)

    queueName = instances[0].queueName # same machineName, same queues
    try:
        from google.appengine.api.taskqueue.taskqueue import Queue
        _queueTasks(Queue, queueName, tasks)
    except (TaskAlreadyExistsError, TombstonedTaskError):
        # FIXME: what happens if _some_ of the tasks were previously enqueued?
        # normal result for idempotency
        import logging
        logging.info('Unable to queue new machine %s with taskName %s as it has been previously enqueued.',
                      machineName, taskName)

########NEW FILE########
__FILENAME__ = handlers
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import time
import logging
import json
import webapp2
from google.appengine.ext import deferred, db
from google.appengine.api.capabilities import CapabilitySet
from fantasm import config, constants
from fantasm.fsm import FSM
from fantasm.utils import NoOpQueue
from fantasm.constants import NON_CONTEXT_PARAMS, STATE_PARAM, EVENT_PARAM, INSTANCE_NAME_PARAM, TASK_NAME_PARAM, \
                              RETRY_COUNT_PARAM, STARTED_AT_PARAM, IMMEDIATE_MODE_PARAM, MESSAGES_PARAM, \
                              HTTP_REQUEST_HEADER_PREFIX
from fantasm.exceptions import UnknownMachineError, RequiredServicesUnavailableRuntimeError, FSMRuntimeError
from fantasm.models import _FantasmTaskSemaphore, Encoder, _FantasmFanIn
from fantasm.lock import RunOnceSemaphore

REQUIRED_SERVICES = ('memcache', 'datastore_v3', 'taskqueue')

class TemporaryStateObject(dict):
    """ A simple object that is passed throughout a machine dispatch that can hold temporary
        in-flight data.
    """
    pass
    
def getMachineNameFromRequest(request):
    """ Returns the machine name embedded in the request.
    
    @param request: an HttpRequest
    @return: the machineName (as a string)
    """    
    path = request.path
    
    # strip off the mount-point
    currentConfig = config.currentConfiguration()
    mountPoint = currentConfig.rootUrl # e.g., '/fantasm/'
    if not path.startswith(mountPoint):
        raise FSMRuntimeError("rootUrl '%s' must match app.yaml mapping." % mountPoint)
    path = path[len(mountPoint):]
    
    # split on '/', the second item will be the machine name
    parts = path.split('/')
    return parts[1] # 0-based index

def getMachineConfig(request):
    """ Returns the machine configuration specified by a URI in a HttpReuest
    
    @param request: an HttpRequest
    @return: a config._machineConfig instance
    """ 
    
    # parse out the machine-name from the path {mount-point}/fsm/{machine-name}/startState/event/endState/
    # NOTE: /startState/event/endState/ is optional
    machineName = getMachineNameFromRequest(request)
    
    # load the configuration, lookup the machine-specific configuration
    # FIXME: sort out a module level cache for the configuration - it must be sensitive to YAML file changes
    # for developer-time experience
    currentConfig = config.currentConfiguration()
    try:
        machineConfig = currentConfig.machines[machineName]
        return machineConfig
    except KeyError:
        raise UnknownMachineError(machineName)

class FSMLogHandler(webapp2.RequestHandler):
    """ The handler used for logging """
    def post(self):
        """ Runs the serialized function """
        deferred.run(self.request.body)
        
class FSMFanInCleanupHandler(webapp2.RequestHandler):
    """ The handler used for logging """
    def post(self):
        """ Runs the serialized function """
        q = _FantasmFanIn.all().filter('workIndex =', self.request.POST[constants.WORK_INDEX_PARAM])
        db.delete(q)

class FSMGraphvizHandler(webapp2.RequestHandler):
    """ The hander to output graphviz diagram of the finite state machine. """
    def get(self):
        """ Handles the GET request. """
        from fantasm.utils import outputMachineConfig
        machineConfig = getMachineConfig(self.request)
        content = outputMachineConfig(machineConfig, skipStateNames=[self.request.GET.get('skipStateName')])
        if self.request.GET.get('type', 'png') == 'png':
            self.response.out.write(
"""
<html>
<head></head>
<body onload="javascript:document.forms.chartform.submit();">
<form id='chartform' action='http://chart.apis.google.com/chart' method='POST'>
  <input type="hidden" name="cht" value="gv:dot"  />
  <input type="hidden" name="chl" value='%(chl)s'  />
  <input type="submit" value="Generate GraphViz .png" />
</form>
</body>
""" % {'chl': content.replace('\n', ' ')})
        else:
            self.response.out.write(content)
            
_fsm = None

def getCurrentFSM():
    """ Returns the current FSM singleton. """
    # W0603: 32:currentConfiguration: Using the global statement
    global _fsm # pylint: disable-msg=W0603
    
    # always reload the FSM for dev_appserver to grab recent dev changes
    if _fsm and not constants.DEV_APPSERVER:
        return _fsm
        
    currentConfig = config.currentConfiguration()
    _fsm = FSM(currentConfig=currentConfig)
    return _fsm
    
class FSMHandler(webapp2.RequestHandler):
    """ The main worker handler, used to process queued machine events. """

    def get(self):
        """ Handles the GET request. """
        self.get_or_post(method='GET')
        
    def post(self):
        """ Handles the POST request. """
        self.get_or_post(method='POST')
        
    def initialize(self, request, response):
        """Initializes this request handler with the given Request and Response."""
        super(FSMHandler, self).initialize(request, response)
        # pylint: disable-msg=W0201
        # - this is the preferred location to initialize the handler in the webapp framework
        self.fsm = None
        
    def handle_exception(self, exception, debug_mode): # pylint: disable-msg=C0103
        """ Delegates logging to the FSMContext logger """
        self.error(500)
        logger = logging
        if self.fsm:
            logger = self.fsm.logger
        logger.exception("FSMHandler caught Exception")
        if debug_mode:
            import traceback, sys, cgi
            lines = ''.join(traceback.format_exception(*sys.exc_info()))
            self.response.clear()
            self.response.out.write('<pre>%s</pre>' % (cgi.escape(lines, quote=True)))
        
    def get_or_post(self, method='POST'):
        """ Handles the GET/POST request. 
        
        FIXME: this is getting a touch long
        """
        
        # ensure that we have our services for the next 30s (length of a single request)
        unavailable = set()
        for service in REQUIRED_SERVICES:
            if not CapabilitySet(service).is_enabled():
                unavailable.add(service)
        if unavailable:
            raise RequiredServicesUnavailableRuntimeError(unavailable)
        
        # the case of headers is inconsistent on dev_appserver and appengine
        # ie 'X-AppEngine-TaskRetryCount' vs. 'X-AppEngine-Taskretrycount'
        lowerCaseHeaders = dict([(key.lower(), value) for key, value in self.request.headers.items()])

        taskName = lowerCaseHeaders.get('x-appengine-taskname')
        retryCount = int(lowerCaseHeaders.get('x-appengine-taskretrycount', 0))
        
        # Taskqueue can invoke multiple tasks of the same name occassionally. Here, we'll use
        # a datastore transaction as a semaphore to determine if we should actually execute this or not.
        if taskName:
            semaphoreKey = '%s--%s' % (taskName, retryCount)
            semaphore = RunOnceSemaphore(semaphoreKey, None)
            if not semaphore.writeRunOnceSemaphore(payload='fantasm')[0]:
                # we can simply return here, this is a duplicate fired task
                logging.info('A duplicate task "%s" has been queued by taskqueue infrastructure. Ignoring.', taskName)
                self.response.status_code = 200
                return
            
        # pull out X-Fantasm-* headers
        headers = None
        for key, value in self.request.headers.items():
            if key.startswith(HTTP_REQUEST_HEADER_PREFIX):
                headers = headers or {}
                if ',' in value:
                    headers[key] = [v.strip() for v in value.split(',')]
                else:
                    headers[key] = value.strip()
            
        requestData = {'POST': self.request.POST, 'GET': self.request.GET}[method]
        method = requestData.get('method') or method
        
        machineName = getMachineNameFromRequest(self.request)
        
        # get the incoming instance name, if any
        instanceName = requestData.get(INSTANCE_NAME_PARAM)
        
        # get the incoming state, if any
        fsmState = requestData.get(STATE_PARAM)
        
        # get the incoming event, if any
        fsmEvent = requestData.get(EVENT_PARAM)
        
        assert (fsmState and instanceName) or True # if we have a state, we should have an instanceName
        assert (fsmState and fsmEvent) or True # if we have a state, we should have an event
        
        obj = TemporaryStateObject()
        
        # make a copy, add the data
        fsm = getCurrentFSM().createFSMInstance(machineName, 
                                                currentStateName=fsmState, 
                                                instanceName=instanceName,
                                                method=method,
                                                obj=obj,
                                                headers=headers)
        
        # in "immediate mode" we try to execute as much as possible in the current request
        # for the time being, this does not include things like fork/spawn/contuniuations/fan-in
        immediateMode = IMMEDIATE_MODE_PARAM in requestData.keys()
        if immediateMode:
            obj[IMMEDIATE_MODE_PARAM] = immediateMode
            obj[MESSAGES_PARAM] = []
            fsm.Queue = NoOpQueue # don't queue anything else
        
        # pylint: disable-msg=W0201
        # - initialized outside of ctor is ok in this case
        self.fsm = fsm # used for logging in handle_exception
        
        # pull all the data off the url and stuff into the context
        for key, value in requestData.items():
            if key in NON_CONTEXT_PARAMS:
                continue # these are special, don't put them in the data
            
            # deal with ...a=1&a=2&a=3...
            value = requestData.get(key)
            valueList = requestData.getall(key)
            if len(valueList) > 1:
                value = valueList
                
            if key.endswith('[]'):
                key = key[:-2]
                value = [value]
                
            if key in fsm.contextTypes.keys():
                fsm.putTypedValue(key, value)
            else:
                fsm[key] = value
        
        if not (fsmState or fsmEvent):
            
            # just queue up a task to run the initial state transition using retries
            fsm[STARTED_AT_PARAM] = time.time()
            
            # initialize the fsm, which returns the 'pseudo-init' event
            fsmEvent = fsm.initialize()
            
        else:
            
            # add the retry counter into the machine context from the header
            obj[RETRY_COUNT_PARAM] = retryCount
            
            # add the actual task name to the context
            obj[TASK_NAME_PARAM] = taskName
            
            # dispatch and return the next event
            fsmEvent = fsm.dispatch(fsmEvent, obj)
            
        # loop and execute until there are no more events - any exceptions
        # will make it out to the user in the response - useful for debugging
        if immediateMode:
            while fsmEvent:
                fsmEvent = fsm.dispatch(fsmEvent, obj)
            self.response.headers['Content-Type'] = 'application/json'
            data = {
                'obj' : obj,
                'context': fsm,
            }
            self.response.out.write(json.dumps(data, cls=Encoder))

########NEW FILE########
__FILENAME__ = lock
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import random
import time
import logging

from google.appengine.api import memcache
from google.appengine.ext import db

from fantasm.models import _FantasmTaskSemaphore
from fantasm import constants
from fantasm.exceptions import FanInWriteLockFailureRuntimeError
from fantasm.exceptions import FanInReadLockFailureRuntimeError

# a variety of locking mechanisms to enforce idempotency (of the framework) in the face of retries

class ReadWriteLock( object ):
    """ A read/write lock that allows
    
    1. non-blocking write (for speed of fan-out)
    2. blocking read (speed not reqd in fan-in)
    """
    
    INDEX_PARAM = 'index'
    LOCK_PARAM = 'lock'
    
    # 20 iterations * 0.25s = 5s total wait time
    BUSY_WAIT_ITERS = 20
    BUSY_WAIT_ITER_SECS = 0.250
    
    def __init__(self, taskNameBase, context, obj=None):
        """ ctor 
        
        @param taskNameBase: the key for fan-in, based on the task name of the fan-out items
        @param logger: a logging module or object
        """
        self.taskNameBase = taskNameBase
        self.context = context
        self.obj = obj
        
    def indexKey(self):
        """ Returns the lock index key """
        return ReadWriteLock.INDEX_PARAM + '-' + self.taskNameBase
    
    def lockKey(self, index):
        """ Returns the lock key """
        return self.taskNameBase + '-' + ReadWriteLock.LOCK_PARAM + '-' + str(index)
        
    def currentIndex(self):
        """ Returns the current lock index from memcache, or sets it if it is missing
        
        @return: an int, the current index
        """
        indexKey = self.indexKey()
        index = memcache.get(indexKey)
        if index is None:
            # using 'random.randint' here instead of '1' helps when the index is ejected from memcache
            # instead of restarting at the same counter, we jump (likely) far way from existing task job
            # names. 
            memcache.add(indexKey, random.randint(1, 2**32))
            index = memcache.get(indexKey)
        return index
    
    def acquireWriteLock(self, index, nextEvent=None, raiseOnFail=True):
        """ Acquires the write lock 
        
        @param index: an int, the current index
        @raise FanInWriteLockFailureRuntimeError: 
        """
        acquired = True
        lockKey = self.lockKey(index)
        writers = memcache.incr(lockKey, initial_value=2**16)
        if writers < 2**16:
            self.context.logger.error("Gave up waiting for write lock '%s'.", lockKey)
            acquired = False
            if raiseOnFail:
                # this will escape as a 500 error and the Task will be re-tried by appengine
                raise FanInWriteLockFailureRuntimeError(nextEvent, 
                                                        self.context.machineName, 
                                                        self.context.currentState.name, 
                                                        self.context.instanceName)
        return acquired
            
    def releaseWriteLock(self, index):
        """ Acquires the write lock 
        
        @param index: an int, the current index
        """
        released = True
        
        lockKey = self.lockKey(index)
        memcache.decr(lockKey)
        
        return released
    
    def acquireReadLock(self, index, nextEvent=None, raiseOnFail=False):
        """ Acquires the read lock
        
        @param index: an int, the current index
        """
        acquired = True
        
        lockKey = self.lockKey(index)
        indexKey = self.indexKey()
        
        # tell writers to use another index
        memcache.incr(indexKey)
        
        # tell writers they missed the boat
        memcache.decr(lockKey, 2**15) 
        
        # busy wait for writers
        for i in xrange(ReadWriteLock.BUSY_WAIT_ITERS):
            counter = memcache.get(lockKey)
            # counter is None --> ejected from memcache, or no writers
            # int(counter) <= 2**15 --> writers have all called memcache.decr
            if counter is None or int(counter) <= 2**15:
                break
            time.sleep(ReadWriteLock.BUSY_WAIT_ITER_SECS)
            self.context.logger.debug("Tried to acquire read lock '%s' %d times...", lockKey, i + 1)
        
        # FIXME: is there anything else that can be done? will work packages be lost? maybe queue another task
        #        to sweep up later?
        if i >= (ReadWriteLock.BUSY_WAIT_ITERS - 1): # pylint: disable-msg=W0631
            self.context.logger.critical("Gave up waiting for all fan-in work items with read lock '%s'.", lockKey)
            acquired = False
            if raiseOnFail:
                raise FanInReadLockFailureRuntimeError(nextEvent, 
                                                       self.context.machineName, 
                                                       self.context.currentState.name, 
                                                       self.context.instanceName)
        
        return acquired
    
class RunOnceSemaphore( object ):
    """ A object used to enforce run-once semantics """
    
    def __init__(self, semaphoreKey, context, obj=None):
        """ ctor 
        
        @param logger: a logging module or object
        """
        self.semaphoreKey = semaphoreKey
        if context is None:
            self.logger = logging
        else:
            self.logger = context.logger
        self.obj = obj

    def writeRunOnceSemaphore(self, payload=None, transactional=True):
        """ Writes the semaphore
        
        @return: a tuple of (bool, obj) where the first arg is True if the semaphore was created and work 
                 can continue, or False if the semaphore was already created, and the caller should take action
                 the second arg is the payload used on initial creation.
        """
        assert payload # so that something is always injected into memcache
        
        # the semaphore is stored in two places, memcache and datastore
        # we use memcache for speed and datastore for 100% reliability
        # in case of memcache ejection
        
        # check memcache
        cached = memcache.get(self.semaphoreKey)
        if cached:
            if cached != payload:
                self.logger.critical("Run-once semaphore memcache payload write error.")
            return (False, cached)
        
        # check datastore
        def txn():
            """ lock in transaction to avoid races between Tasks """
            entity = _FantasmTaskSemaphore.get_by_key_name(self.semaphoreKey)
            if not entity:
                _FantasmTaskSemaphore(key_name=self.semaphoreKey, payload=payload).put()
                memcache.set(self.semaphoreKey, payload)
                return (True, payload)
            else:
                if entity.payload != payload:
                    self.logger.critical("Run-once semaphore datastore payload write error.")
                memcache.set(self.semaphoreKey, entity.payload) # maybe reduces chance of ejection???
                return (False, entity.payload)
                
        # and return whether or not the lock was written
        if transactional:
            return db.run_in_transaction(txn)
        else:
            return txn()
    
    def readRunOnceSemaphore(self, payload=None, transactional=True):
        """ Reads the semaphore
        
        @return: True if the semaphore exists
        """
        assert payload
        
        # check memcache
        cached = memcache.get(self.semaphoreKey)
        if cached:
            if cached != payload:
                self.logger.critical("Run-once semaphore memcache payload read error.")
            return cached
        
        # check datastore
        def txn():
            """ lock in transaction to avoid races between Tasks """
            entity = _FantasmTaskSemaphore.get_by_key_name(self.semaphoreKey)
            if entity:
                if entity.payload != payload:
                    self.logger.critical("Run-once semaphore datastore payload read error.")
                return entity.payload
            
        # return whether or not the lock was read 
        if transactional:
            return db.run_in_transaction(txn)
        else:
            return txn()
    
########NEW FILE########
__FILENAME__ = log
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import logging
import datetime
import traceback
import StringIO
from google.appengine.ext import deferred
from fantasm.models import _FantasmLog
from fantasm import constants
from google.appengine.api.taskqueue import taskqueue

LOG_ERROR_MESSAGE = 'Exception constructing log message. Please adjust your usage of context.logger.'

def _log(taskName, 
         instanceName, 
         machineName, stateName, actionName, transitionName,
         level, namespace, tags, message, stack, time, 
         *args, **kwargs): # pylint: disable-msg=W0613
    """ Creates a _FantasmLog that can be used for debugging 
    
    @param instanceName:
    @param machineName:
    @param stateName:
    @param actionName:
    @param transitionName: 
    @param level:
    @param namespace: 
    @param tags: 
    @param message:
    @param time:
    @param args:
    @param kwargs:
    """
    # logging.info etc. handle this like:
    #
    # import logging
    # >>> logging.critical('%s')
    # CRITICAL:root:%s
    #
    # so we will do the same thing here
    try:
        message = message % args
    except TypeError: # TypeError: not enough arguments for format string
        pass
    
    _FantasmLog(taskName=taskName,
                instanceName=instanceName, 
                machineName=machineName,
                stateName=stateName,
                actionName=actionName,
                transitionName=transitionName,
                level=level,
                namespace=namespace,
                tags=list(set(tags)) or [],
                message=message, 
                stack=stack,
                time=time).put()

class Logger( object ):
    """ A object that allows an FSMContext to have methods debug, info etc. similar to logging.debug/info etc. """
    
    _LOGGING_MAP = {
        logging.CRITICAL: logging.critical,
        logging.ERROR: logging.error,
        logging.WARNING: logging.warning,
        logging.INFO: logging.info,
        logging.DEBUG: logging.debug
    }
    
    def __init__(self, context, obj=None, persistentLogging=False):
        """ Constructor 
        
        @param context:
        @param obj:
        @param persistentLogging:
        """
        self.context = context
        self.level = logging.DEBUG
        self.maxLevel = logging.CRITICAL
        self.tags = []
        self.persistentLogging = persistentLogging
        self.__obj = obj
        
    def getLoggingMap(self):
        """ One layer of indirection to fetch self._LOGGING_MAP (required for minimock to work) """
        return self._LOGGING_MAP
    
    def _log(self, level, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        
        @param level:
        @param message:
        @param args:
        @param kwargs:   
        
        NOTE: we are not not using deferred module to reduce dependencies, but we are re-using the helper
              functions .serialize() and .run() - see handler.py
        """
        if not (self.level <= level <= self.maxLevel):
            return
        
        namespace = kwargs.pop('namespace', None)
        tags = kwargs.pop('tags', None)
        
        self.getLoggingMap()[level](message, *args, **kwargs)
        
        if not self.persistentLogging:
            return
        
        stack = None
        if 'exc_info' in kwargs:
            f = StringIO.StringIO()
            traceback.print_exc(25, f)
            stack = f.getvalue()
            
        # this _log method requires everything to be serializable, which is not the case for the logging
        # module. if message is not a basestring, then we simply cast it to a string to allow _something_
        # to be logged in the deferred task
        if not isinstance(message, basestring):
            try:
                message = str(message)
            except Exception:
                message = LOG_ERROR_MESSAGE
                if args:
                    args = []
                logging.warning(message, exc_info=True)
                
        taskName = (self.__obj or {}).get(constants.TASK_NAME_PARAM)
                
        stateName = None
        if self.context.currentState:
            stateName = self.context.currentState.name
            
        transitionName = None
        if self.context.startingState and self.context.startingEvent:
            transitionName = self.context.startingState.getTransition(self.context.startingEvent).name
            
        actionName = None
        if self.context.currentAction:
            actionName = self.context.currentAction.__class__.__name__
            
        # in immediateMode, tack the messages onto obj so that they can be returned
        # in the http response in handler.py
        if self.__obj is not None:
            if self.__obj.get(constants.IMMEDIATE_MODE_PARAM):
                try:
                    self.__obj[constants.MESSAGES_PARAM].append(message % args)
                except TypeError:
                    self.__obj[constants.MESSAGES_PARAM].append(message)
                
        serialized = deferred.serialize(_log,
                                        taskName,
                                        self.context.instanceName,
                                        self.context.machineName,
                                        stateName,
                                        actionName,
                                        transitionName,
                                        level,
                                        namespace,
                                        (self.tags or []) + (tags or []),
                                        message,
                                        stack,
                                        datetime.datetime.now(), # FIXME: called .utcnow() instead?
                                        *args,
                                        **kwargs)
        
        try:
            task = taskqueue.Task(url=constants.DEFAULT_LOG_URL, 
                                  payload=serialized, 
                                  retry_options=taskqueue.TaskRetryOptions(task_retry_limit=20))
            # FIXME: a batch add may be more optimal, but there are quite a few more corners to deal with
            taskqueue.Queue(name=constants.DEFAULT_LOG_QUEUE_NAME).add(task)
            
        except taskqueue.TaskTooLargeError:
            logging.warning("fantasm log message too large - skipping persistent storage")
            
        except taskqueue.Error:
            logging.warning("error queuing log message Task - skipping persistent storage", exc_info=True)
        
    def setLevel(self, level):
        """ Sets the minimum logging level to log 
        
        @param level: a log level (ie. logging.CRITICAL)
        """
        self.level = level
        
    def setMaxLevel(self, maxLevel):
        """ Sets the maximum logging level to log 
        
        @param maxLevel: a max log level (ie. logging.CRITICAL)
        """
        self.maxLevel = maxLevel
        
    def debug(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.DEBUG
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.DEBUG, message, *args, **kwargs)
        
    def info(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.INFO
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.INFO, message, *args, **kwargs)
        
    def warning(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.WARNING
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.WARNING, message, *args, **kwargs)
        
    warn = warning
        
    def error(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.ERROR
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.ERROR, message, *args, **kwargs)
        
    def critical(self, message, *args, **kwargs):
        """ Logs the message to the normal logging module and also queues a Task to create an _FantasmLog
        at level logging.CRITICAL
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.CRITICAL, message, *args, **kwargs)
        
    # pylint: disable-msg=W0613
    # - kwargs is overridden in this case, and never used
    def exception(self, message, *args, **kwargs):
        """ Logs the message + stack dump to the normal logging module and also queues a Task to create an 
        _FantasmLog at level logging.ERROR
        
        @param message:
        @param args:
        @param kwargs:   
        """
        self._log(logging.ERROR, message, *args, **{'exc_info': True})
        
########NEW FILE########
__FILENAME__ = main
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.



Main module for fantasm implementation.

This module should be specified as a handler for fantasm URLs in app.yaml:

  handlers:
  - url: /fantasm/.*
    login: admin
    script: fantasm/main.py
"""
import webapp2
from fantasm import handlers, console

def createApplication():
    """Create new WSGIApplication and register all handlers.

    Returns:
        an instance of webapp2.WSGIApplication with all fantasm handlers registered.
    """
    return webapp2.WSGIApplication([
        (r"^/[^\/]+/fsm/.+",       handlers.FSMHandler),
        (r"^/[^\/]+/cleanup/",     handlers.FSMFanInCleanupHandler),
        (r"^/[^\/]+/graphviz/.+",  handlers.FSMGraphvizHandler),
        (r"^/[^\/]+/log/",         handlers.FSMLogHandler),
        (r"^/[^\/]+/?",            console.Dashboard),
    ],
    debug=True)

APP = createApplication()


########NEW FILE########
__FILENAME__ = models
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from google.appengine.ext import db
from google.appengine.api import datastore_types
import json
import datetime

def decode(dct):
    """ Special handler for db.Key/datetime.datetime decoding """
    if '__set__' in dct:
        return set(dct['key'])
    if '__db.Key__' in dct:
        return db.Key(dct['key'])
    if '__db.Model__' in dct:
        return db.Key(dct['key']) # turns into a db.Key across serialization
    if '__datetime.datetime__' in dct:
        return datetime.datetime(**dct['datetime'])
    return dct

# W0232: 30:Encoder: Class has no __init__ method
class Encoder(json.JSONEncoder): # pylint: disable-msg=W0232
    """ A JSONEncoder that handles db.Key """
    # E0202: 36:Encoder.default: An attribute inherited from JSONEncoder hide this method
    def default(self, obj): # pylint: disable-msg=E0202
        """ see json.JSONEncoder.default """
        if isinstance(obj, set):
            return {'__set__': True, 'key': list(obj)}
        if isinstance(obj, db.Key):
            return {'__db.Key__': True, 'key': str(obj)}
        if isinstance(obj, db.Model):
            return {'__db.Model__': True, 'key': str(obj.key())} # turns into a db.Key across serialization
        if isinstance(obj, datetime.datetime) and \
           obj.tzinfo is None: # only UTC datetime objects are supported
            return {'__datetime.datetime__': True, 'datetime': {'year': obj.year,
                                                                'month': obj.month,
                                                                'day': obj.day,
                                                                'hour': obj.hour,
                                                                'minute': obj.minute,
                                                                'second': obj.second,
                                                                'microsecond': obj.microsecond}}
        return json.JSONEncoder.default(self, obj)

class JSONProperty(db.Property):
    """
    From Google appengine cookbook... a Property for storing dicts in the datastore
    """
    data_type = datastore_types.Text
    
    def get_value_for_datastore(self, modelInstance):
        """ see Property.get_value_for_datastore """
        value = super(JSONProperty, self).get_value_for_datastore(modelInstance)
        return db.Text(self._deflate(value))
    
    def validate(self, value):
        """ see Property.validate """
        return self._inflate(value)
    
    def make_value_from_datastore(self, value):
        """ see Property.make_value_from_datastore """
        return self._inflate(value)
    
    def _inflate(self, value):
        """ decodes string -> dict """
        if value is None:
            return {}
        if isinstance(value, unicode) or isinstance(value, str):
            return json.loads(value, object_hook=decode)
        return value
    
    def _deflate(self, value):
        """ encodes dict -> string """
        return json.dumps(value, cls=Encoder)
    
    
class _FantasmFanIn( db.Model ):
    """ A model used to store FSMContexts for fan in """
    workIndex = db.StringProperty()
    context = JSONProperty(indexed=False)
    # FIXME: createdTime only needed for scrubbing, but indexing might be a performance hit
    #        http://ikaisays.com/2011/01/25/app-engine-datastore-tip-monotonically-increasing-values-are-bad/
    createdTime = db.DateTimeProperty(auto_now_add=True)
    
class _FantasmInstance( db.Model ):
    """ A model used to to store FSMContext instances """
    instanceName = db.StringProperty()
    # FIXME: createdTime only needed for scrubbing, but indexing might be a performance hit
    #        http://ikaisays.com/2011/01/25/app-engine-datastore-tip-monotonically-increasing-values-are-bad/
    createdTime = db.DateTimeProperty(auto_now_add=True)
    
class _FantasmLog( db.Model ):
    """ A model used to store log messages """
    taskName = db.StringProperty()
    instanceName = db.StringProperty()
    machineName = db.StringProperty()
    stateName = db.StringProperty()
    actionName = db.StringProperty()
    transitionName = db.StringProperty()
    time = db.DateTimeProperty()
    level = db.IntegerProperty()
    message = db.TextProperty()
    stack = db.TextProperty()
    tags = db.StringListProperty()

class _FantasmTaskSemaphore( db.Model ):
    """ A model that simply stores the task name so that we can guarantee only-once semantics. """
    # FIXME: createdTime only needed for scrubbing, but indexing might be a performance hit
    #        http://ikaisays.com/2011/01/25/app-engine-datastore-tip-monotonically-increasing-values-are-bad/
    createdTime = db.DateTimeProperty(auto_now_add=True)
    payload = db.StringProperty(indexed=False)

########NEW FILE########
__FILENAME__ = scrubber
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import datetime
from google.appengine.ext import db
from fantasm.action import DatastoreContinuationFSMAction
# W0611: 23: Unused import _FantasmLog
# we're importing these here so that db has a chance to see them before we query them
from fantasm.models import _FantasmInstance, _FantasmLog, _FantasmTaskSemaphore # pylint: disable-msg=W0611

# W0613: Unused argument 'obj'
# implementing interfaces
# pylint: disable-msg=W0613

class InitalizeScrubber(object):
    """ Use current time to set up task names. """
    def execute(self, context, obj):
        """ Computes the before date and adds to context. """
        age = context.pop('age', 90)
        context['before'] = datetime.datetime.utcnow() - datetime.timedelta(days=age)
        return 'next'
        
class EnumerateFantasmModels(object):
    """ Kick off a continuation for each model. """
    
    FANTASM_MODELS = (
        ('_FantasmInstance', 'createdTime'), 
        ('_FantasmLog', 'time'), 
        ('_FantasmTaskSemaphore', 'createdTime'),
        ('_FantasmFanIn', 'createdTime')
    )
    
    def continuation(self, context, obj, token=None):
        """ Continue over each model. """
        if not token:
            obj['model'] = self.FANTASM_MODELS[0][0]
            obj['dateattr'] = self.FANTASM_MODELS[0][1]
            return self.FANTASM_MODELS[1][0] if len(self.FANTASM_MODELS) > 1 else None
        else:
            # find next in list
            for i in range(0, len(self.FANTASM_MODELS)):
                if self.FANTASM_MODELS[i][0] == token:
                    obj['model'] = self.FANTASM_MODELS[i][0]
                    obj['dateattr'] = self.FANTASM_MODELS[i][1]
                    return self.FANTASM_MODELS[i+1][0] if i < len(self.FANTASM_MODELS)-1 else None
        return None # this occurs if a token passed in is not found in list - shouldn't happen
        
    def execute(self, context, obj):
        """ Pass control to next state. """
        if not 'model' in obj or not 'dateattr' in obj:
            return None
        context['model'] = obj['model']
        context['dateattr'] = obj['dateattr']
        return 'next'
        
class DeleteOldEntities(DatastoreContinuationFSMAction):
    """ Deletes entities of a given model older than a given date. """
    
    def getQuery(self, context, obj):
        """ Query for all entities before a given datetime. """
        model = context['model']
        dateattr = context['dateattr']
        before = context['before']
        query = 'SELECT __key__ FROM %s WHERE %s < :1' % (model, dateattr)
        return db.GqlQuery(query, before)
        
    def getBatchSize(self, context, obj):
        """ Batch size. """
        return 100
        
    def execute(self, context, obj):
        """ Delete the rows. """
        if obj['results']:
            db.delete(obj['results'])

########NEW FILE########
__FILENAME__ = state
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
from google.appengine.ext import db
from google.appengine.api.taskqueue.taskqueue import Task, TaskAlreadyExistsError, TombstonedTaskError

from fantasm import constants
from fantasm.transition import Transition
from fantasm.exceptions import UnknownEventError, InvalidEventNameRuntimeError
from fantasm.utils import knuthHash
from fantasm.models import _FantasmFanIn
from fantasm.lock import RunOnceSemaphore

class State(object):
    """ A state object for a machine. """
    
    def __init__(self, name, entryAction, doAction, exitAction, machineName=None, 
                 isFinalState=False, isInitialState=False, isContinuation=False, fanInPeriod=constants.NO_FAN_IN):
        """
        @param name: the name of the State instance
        @param entryAction: an FSMAction instance
        @param doAction: an FSMAction instance
        @param exitAction: an FSMAction instance
        @param machineName: the name of the machine this State is associated with 
        @param isFinalState: a boolean indicating this is a terminal state
        @param isInitialState: a boolean indicating this is a starting state
        @param isContinuation: a boolean indicating this is a continuation State 
        @param fanInPeriod: integer (seconds) representing how long these states should collect before dispatching
        """
        assert not (exitAction and isContinuation) # TODO: revisit this with jcollins, we want to get it right
        assert not (exitAction and fanInPeriod > constants.NO_FAN_IN) # TODO: revisit this with jcollins
        
        self.name = name
        self.entryAction = entryAction
        self.doAction = doAction
        self.exitAction = exitAction
        self.machineName = machineName # is this really necessary? it is only for logging.
        self.isInitialState = isInitialState
        self.isFinalState = isFinalState
        self.isContinuation = isContinuation
        self.isFanIn = fanInPeriod != constants.NO_FAN_IN
        self.fanInPeriod = fanInPeriod
        self._eventToTransition = {}
        
    def addTransition(self, transition, event):
        """ Adds a transition for an event. 
        
        @param transition: a Transition instance
        @param event: a string event that results in the associated Transition to execute  
        """
        assert isinstance(transition, Transition)
        assert isinstance(event, basestring)
        
        assert not (self.exitAction and transition.target.isContinuation) # TODO: revisit this with jcollins
        assert not (self.exitAction and transition.target.isFanIn) # TODO: revisit
        
        self._eventToTransition[event] = transition
        
    def getTransition(self, event):
        """ Gets the Transition for a given event. 
        
        @param event: a string event
        @return: a Transition instance associated with the event
        @raise an UnknownEventError if event is unknown (i.e., no transition is bound to it).
        """
        try:
            return self._eventToTransition[event]
        except KeyError:
            import logging
            logging.critical('Cannot find transition for event "%s". (Machine %s, State %s)',
                             event, self.machineName, self.name)
            raise UnknownEventError(event, self.machineName, self.name)
        
    def dispatch(self, context, event, obj):
        """ Fires the transition and executes the next States's entry, do and exit actions.
            
        @param context: an FSMContext instance
        @param event: a string event to dispatch to the State
        @param obj: an object that the Transition can operate on  
        @return: the event returned from the next state's main action.
        """
        transition = self.getTransition(event)
        
        if context.currentState.exitAction:
            try:
                context.currentAction = context.currentState.exitAction
                context.currentState.exitAction.execute(context, obj)
            except Exception:
                context.logger.error('Error processing entry action for state. (Machine %s, State %s, exitAction %s)',
                              context.machineName, 
                              context.currentState.name, 
                              context.currentState.exitAction.__class__)
                raise
        
        # join the contexts of a fan-in
        contextOrContexts = context
        if transition.target.isFanIn:
            taskNameBase = context.getTaskName(event, fanIn=True)
            contextOrContexts = context.mergeJoinDispatch(event, obj)
            if not contextOrContexts:
                context.logger.info('Fan-in resulted in 0 contexts. Terminating machine. (Machine %s, State %s)',
                             context.machineName, 
                             context.currentState.name)
                obj[constants.TERMINATED_PARAM] = True
                
        transition.execute(context, obj)
        
        if context.currentState.entryAction:
            try:
                context.currentAction = context.currentState.entryAction
                context.currentState.entryAction.execute(contextOrContexts, obj)
            except Exception:
                context.logger.error('Error processing entry action for state. (Machine %s, State %s, entryAction %s)',
                              context.machineName, 
                              context.currentState.name, 
                              context.currentState.entryAction.__class__)
                raise
            
        if context.currentState.isContinuation:
            try:
                token = context.get(constants.CONTINUATION_PARAM, None)
                nextToken = context.currentState.doAction.continuation(contextOrContexts, obj, token=token)
                if nextToken:
                    context.continuation(nextToken)
                context.pop(constants.CONTINUATION_PARAM, None) # pop this off because it is really long
                
            except Exception:
                context.logger.error('Error processing continuation for state. (Machine %s, State %s, continuation %s)',
                              context.machineName, 
                              context.currentState.name, 
                              context.currentState.doAction.__class__)
                raise
            
        # either a fan-in resulted in no contexts, or a continuation was completed
        if obj.get(constants.TERMINATED_PARAM):
            return None
            
        nextEvent = None
        if context.currentState.doAction:
            try:
                context.currentAction = context.currentState.doAction
                nextEvent = context.currentState.doAction.execute(contextOrContexts, obj)
            except Exception:
                context.logger.error('Error processing action for state. (Machine %s, State %s, Action %s)',
                              context.machineName, 
                              context.currentState.name, 
                              context.currentState.doAction.__class__)
                raise
            
        if transition.target.isFanIn:
            
            # this prevents fan-in from re-counting the data if there is an Exception
            # or DeadlineExceeded _after_ doAction.execute(...) succeeds
            index = context.get(constants.INDEX_PARAM)
            workIndex = '%s-%d' % (taskNameBase, knuthHash(index))
            semaphore = RunOnceSemaphore(workIndex, context)
            semaphore.writeRunOnceSemaphore(payload=obj[constants.TASK_NAME_PARAM])
            
            try:
                # at this point we have processed the work items, delete them
                task = Task(name=obj[constants.TASK_NAME_PARAM] + '-cleanup', 
                            url=constants.DEFAULT_CLEANUP_URL, 
                            params={constants.WORK_INDEX_PARAM: workIndex})
                context.Queue(name=constants.DEFAULT_CLEANUP_QUEUE_NAME).add(task)
                
            except (TaskAlreadyExistsError, TombstonedTaskError):
                context.logger.info("Fan-in cleanup Task already exists.")
                
            if context.get('UNITTEST_RAISE_AFTER_FAN_IN'): # only way to generate this failure
                raise Exception()
                
        if nextEvent:
            if not isinstance(nextEvent, str) or not constants.NAME_RE.match(nextEvent):
                raise InvalidEventNameRuntimeError(nextEvent, context.machineName, context.currentState.name,
                                                   context.instanceName)
            
        return nextEvent

########NEW FILE########
__FILENAME__ = transition
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

class Transition(object):
    """ A transition object for a machine. """
    
    def __init__(self, name, target, action=None, countdown=0, retryOptions=None, queueName=None):
        """ Constructor 
        
        @param name: the name of the Transition instance
        @param target: a State instance
        @param action: the optional action for a state
        @param countdown: the number of seconds to wait before firing this transition. Default 0.
        @param retryOptions: the TaskRetryOptions for this transition
        @param queueName: the name of the queue to Queue into 
        """
        assert queueName
        
        self.target = target
        self.name = name
        self.action = action
        self.countdown = countdown
        self.retryOptions = retryOptions
        self.queueName = queueName
        
    # W0613:144:Transition.execute: Unused argument 'obj'
    # args are present for a future(?) transition action
    def execute(self, context, obj): # pylint: disable-msg=W0613
        """ Moves the machine to the next state. 
        
        @param context: an FSMContext instance
        @param obj: an object that the Transition can operate on  
        """
        if self.action:
            try:
                self.action.execute(context, obj)
            except Exception:
                context.logger.error('Error processing action for transition. (Machine %s, Transition %s, Action %s)',
                              context.machineName, 
                              self.name, 
                              self.action.__class__)
                raise
        context.currentState = self.target

########NEW FILE########
__FILENAME__ = utils
""" Fantasm: A taskqueue-based Finite State Machine for App Engine Python

Docs and examples: http://code.google.com/p/fantasm/

Copyright 2010 VendAsta Technologies Inc.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
from fantasm import constants
from google.appengine.api.taskqueue.taskqueue import Queue

class NoOpQueue( Queue ):
    """ A Queue instance that does not Queue """
    
    def add(self, task, transactional=False):
        """ see taskqueue.Queue.add """
        pass
       
def knuthHash(number):
    """A decent hash function for integers."""
    return (number * 2654435761) % 2**32

def boolConverter(boolStr):
    """ A converter that maps some common bool string to True """
    return {'1': True, 'True': True, 'true': True}.get(boolStr, False)

def outputAction(action):
    """ Outputs the name of the action 
    
    @param action: an FSMAction instance 
    """
    if action:
        return str(action.__class__.__name__).split('.')[-1]

def outputTransitionConfig(transitionConfig):
    """ Outputs a GraphViz directed graph node
    
    @param transitionConfig: a config._TransitionConfig instance
    @return: a string
    """
    label = transitionConfig.event
    if transitionConfig.action:
        label += '/ ' + outputAction(transitionConfig.action)
    return '"%(fromState)s" -> "%(toState)s" [label="%(label)s"];' % \
            {'fromState': transitionConfig.fromState.name, 
             'toState': transitionConfig.toState.name, 
             'label': label}
            
def outputStateConfig(stateConfig, colorMap=None):
    """ Outputs a GraphViz directed graph node
    
    @param stateConfig: a config._StateConfig instance
    @return: a string
    """
    colorMap = colorMap or {}
    actions = []
    if stateConfig.entry:
        actions.append('entry/ %(entry)s' % {'entry': outputAction(stateConfig.entry)})
    if stateConfig.action:
        actions.append('do/ %(do)s' % {'do': outputAction(stateConfig.action)})
    if stateConfig.exit:
        actions.append('exit/ %(exit)s' % {'exit': outputAction(stateConfig.exit)})
    label = '%(stateName)s|%(actions)s' % {'stateName': stateConfig.name, 'actions': '\\l'.join(actions)}
    if stateConfig.continuation:
        label += '|continuation = True'
    if stateConfig.fanInPeriod != constants.NO_FAN_IN:
        label += '|fan in period = %(fanin)ds' % {'fanin': stateConfig.fanInPeriod}
    shape = 'Mrecord'
    if colorMap.get(stateConfig.name):
        return '"%(stateName)s" [style=filled,fillcolor="%(fillcolor)s",shape=%(shape)s,label="{%(label)s}"];' % \
               {'stateName': stateConfig.name,
                'fillcolor': colorMap.get(stateConfig.name, 'white'),
                'shape': shape,
                'label': label}
    else:
        return '"%(stateName)s" [shape=%(shape)s,label="{%(label)s}"];' % \
               {'stateName': stateConfig.name,
                'shape': shape,
                'label': label}

def outputMachineConfig(machineConfig, colorMap=None, skipStateNames=None):
    """ Outputs a GraphViz directed graph of the state machine 
    
    @param machineConfig: a config._MachineConfig instance
    @return: a string
    """
    skipStateNames = skipStateNames or ()
    lines = []
    lines.append('digraph G {')
    lines.append('label="%(machineName)s"' % {'machineName': machineConfig.name})
    lines.append('labelloc="t"')
    lines.append('"__start__" [label="start",shape=circle,style=filled,fillcolor=black,fontcolor=white,fontsize=9];')
    lines.append('"__end__" [label="end",shape=doublecircle,style=filled,fillcolor=black,fontcolor=white,fontsize=9];')
    for stateConfig in machineConfig.states.values():
        if stateConfig.name in skipStateNames:
            continue
        lines.append(outputStateConfig(stateConfig, colorMap=colorMap))
        if stateConfig.initial:
            lines.append('"__start__" -> "%(stateName)s"' % {'stateName': stateConfig.name})
        if stateConfig.final:
            lines.append('"%(stateName)s" -> "__end__"' % {'stateName': stateConfig.name})
    for transitionConfig in machineConfig.transitions.values():
        if transitionConfig.fromState.name in skipStateNames or \
           transitionConfig.toState.name in skipStateNames:
            continue
        lines.append(outputTransitionConfig(transitionConfig))
    lines.append('}')
    return '\n'.join(lines) 
########NEW FILE########
__FILENAME__ = login
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import wsgiref.handlers
import cgi
import webapp2
from google.appengine.ext import db
import json

class LogIn(webapp2.RequestHandler):
  def get(self):
    ret = {"success":"true"}
    ret = json.dumps(ret)
    self.response.out.write(ret)
  def post(self):
    ret = {"success":"true"}
    ret = json.dumps(ret)
    self.response.out.write(ret)

########NEW FILE########
__FILENAME__ = logout
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from serverside.session import Session
import webapp2
class LogOut(webapp2.RequestHandler):
  def get(self):
    sess = Session().get_current_session(self)
    if(sess != None):
      sess.terminate()
    self.redirect("/adminconsole")

########NEW FILE########
__FILENAME__ = logs
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import cgi
import logging
import os
import wsgiref.handlers
import urllib
import webapp2
from google.appengine.api import urlfetch
from serverside import constants
from serverside import environment
from serverside.dao import logs_dao
from serverside.dao import passphrase_dao 
from google.appengine.api import taskqueue

class LogEvent(webapp2.RequestHandler):
  def post(self):
    logsecret = self.request.get('key') 
    official_log_secret = passphrase_dao.get_log_secret()    
    if logsecret != official_log_secret:
      logging.error("Logging: Bad logging secret: %s vs %s"%(logsecret, official_log_secret))
      return
    eventtype = self.request.get('event')
    if eventtype not in constants.LOGGING.CLIENT_EVENT and \
       eventtype not in constants.LOGGING.API_EVENT:
      logging.error("Unknown event type: %s"%eventtype)
      return
    diction = {}
    for args in self.request.arguments():
      diction[args] = self.request.get(args)
    logs_dao.save_log(diction)
    return 
    #logs_dao.save_log(newlog)
app = webapp2.WSGIApplication([
  (constants.LOGGING.PATH, LogEvent)
], debug=constants.DEBUG)

def __url_async_post(worker_url, argsdic):
  # This will not work on the dev server for GAE, dev server only uses
  # synchronous calls, unless the SDK is patched, or using AppScale
  #rpc = urlfetch.create_rpc(deadline=10)
  # Convert over to utf-8 for non-ascii (internationalization)
  for kk,vv in argsdic.items():
    if vv.__class__.__name__ in ['str', 'unicode']:
      argsdic[kk] = vv.encode('utf-8') 
  taskqueue.add(url=worker_url, params=argsdic)
  #urlfetch.make_fetch_call(rpc, url, payload=urllib.urlencode(argsdic), method=urlfetch.POST)

def full_path(relative_url):
  if environment.is_dev():
    return constants.DEV_URL + constants.LOGGING.PATH
  else:
    return constants.PRODUCTION_URL + constants.LOGGING.PATH

def create(diction):
  diction['key'] = passphrase_dao.get_log_secret()    
  assert ('event' in diction), "Logs must always have an event type"
  __url_async_post(constants.LOGGING.PATH, diction)

"""
def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
"""

########NEW FILE########
__FILENAME__ = main
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import wsgiref.handlers
import cgi
from google.appengine.ext.webapp import template
from serverside.console import Console
from serverside.entities.users import Users
from serverside.account import Accounts
from serverside.signup import NewsLetterSignUp
from serverside.signup import SignUp
from serverside.signin import SignIn
from serverside.logout import LogOut
from serverside.badge import UploadBadge
from serverside.badge import DownloadBadge 
from serverside.badge import SeeTheme
from serverside.analytics import GetAnalytics
from serverside.analytics import RunAnalytics
from serverside import constants
import webapp2
from google.appengine.ext import db
from google.appengine.api import users
import logging
import os
from serverside.analytics import *

class IndexPage(webapp2.RequestHandler):
  def get(self):
    self.redirect('/html/signup.html')

class HelloWorld(webapp2.RequestHandler):
  def get(self):
    self.response.out.write("hi!")

app = webapp2.WSGIApplication([
  ('/', IndexPage),
  ('/account', Accounts),
  ('/login', SignIn),
  ('/signup', SignUp),
  ('/logout', LogOut),
  ('/badge/u', UploadBadge),
  ('/badge/d', DownloadBadge),
  ('/badge/t', SeeTheme),
  ('/newslettersignup',NewsLetterSignUp),
  ('/hello', HelloWorld),
  ('/runanalytics', RunAnalytics),
  ('/getanalytics', GetAnalytics),
], debug=constants.DEBUG)

"""
def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
"""

########NEW FILE########
__FILENAME__ = messages
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Jan 9, 2011

@author: shan

This class shall hold messages that the server will be using for standard use, for example, email notifications.
'''


def get_activation_email(activation_url):
  """Get email message that goes out to customers when the sign up, for activation.
  
  activation_url is the url that will process the activation request. It will be embeded
  into the message.
  
  """
  
  message ="""  
Hello,
                      
Thank you for signing up for UserInfuser. Please click the following link to activate your account:
                      
""" + activation_url + """
                      
Thank you!
"""
  return message 



def get_forgotten_login_email(new_password):
  """
  Message formatted with a new password for forgotten login queries
  """
  
  message = """

You account password has been reset to the following: """ + new_password + """

Please login and change your password.

Thank you,

UserInfuser Team.
  
"""
  return message  

########NEW FILE########
__FILENAME__ = notifier
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from google.appengine.api import channel
from entities.accounts import Accounts
from entities.badges import *
from entities.users import *
from serverside import logs
from serverside import constants
from serverside.constants import TEMPLATE_PATHS
from serverside.session import Session
from tools.utils import account_login_required
from tools.xss import XssCleaner, XssCleaner
from serverside.dao import accounts_dao

import logging
import os
import json

def get_channel_token(user_ref):
  if not user_ref:
    return None
  token = channel.create_channel(user_ref.key().name())
  return token

def user_points(user_ref, points, title, acc):
  if not user_ref or not acc:
    return None
  try:
    image = acc.pointsImage
  except:
    acc.pointsImage = constants.IMAGE_PARAMS.POINTS_IMAGE
    accounts_dao.save(acc)
  diction = {'event':'notify_points',
             'user':user_ref.userid,
             'account':acc.key().name(),
             'points':points,
             'widget':'notifier',
             'is_api':'no',
             'details':"title: "+title,
             'success':'true'}
              
  message = {'note':"+" + str(points) + " Points", 'image': image, 'title': title}
  message = json.dumps(message)
  try:
    channel.send_message(user_ref.key().name(), message)
    logs.create(diction)  
  except channel.InvalidChannelClientIdError:
    diction['success'] = "false"
    logging.error("Bad Channel ID for acc %s and user %s"%(acc.key().name(), user_ref.key().name()))
    logs.create(diction)
    return  
  
def user_badge_award(user_ref, note, imglink, title, acc, badge_id):
  assert badge_id != None
  assert user_ref != None

  diction = {'event':'notify_badge',
             'user':user_ref.userid,
             'account':acc.key().name(),
             'badge':imglink,
             'widget':'notifier',
             'is_api':'no',
             'details':'note: '+note+", title: "+title,
             'badgeid': badge_id,
             'success':'true'}
  message = {'note':note, 'image': imglink, 'title': title}
  message = json.dumps(message)
  try:
    channel.send_message(user_ref.key().name(), message)
    logs.create(diction)
  except channel.InvalidChannelClientIdError:
    diction['success'] = "false"
    logging.error("Bad Channel ID for acc %s and user %s"%(acc.key().name(), user_ref.key().name()))
    logs.create(diction)
    return  

########NEW FILE########
__FILENAME__ = not_found
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import wsgiref.handlers
import cgi
import webapp2
import logging
from serverside import constants
class NotFound(webapp2.RequestHandler):
  def get(self):
    self.redirect('/html/404.html')

app = webapp2.WSGIApplication([
  ('/.*', NotFound),
], debug=constants.DEBUG)

"""
def main():
  wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
  main()
"""

########NEW FILE########
__FILENAME__ = session
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Feb 5, 2011

@author: shan
'''
from serverside.constants import WEB_ADMIN_PARAMS
from serverside.entities import memcache_db
from serverside.tools import encryption
import logging
import urllib
import time


class Session:
 
  """
  Class that contains class methods that are utils for account admin sessions. 
  Also, instance methods for tracking sessions when needed. This includes setting
  cookie params, or other params (in case we want to use other methods state
  tracking like GET requet params).
  """ 

  def create_session(self, request, email, ssid, expiration):
    """
    Encrypt parameters, set valid in DB, set cookie on client
    """
    account = memcache_db.get_entity(email, "Accounts")
    if account != None:
      update_fields = {"cookieKey" : ssid}
      memcache_db.update_fields(email, "Accounts", update_fields)
    
      email_enc = encryption.des_encrypt_str(email)
      ssid_enc = encryption.des_encrypt_str(ssid)
      exp_enc = encryption.des_encrypt_str(expiration)
      
      import base64
      import string
      email_encoded = string.rstrip(base64.encodestring(email_enc), "\n")
      ssid_encoded = string.rstrip(base64.encodestring(ssid_enc), "\n")
      exp_encoded = string.rstrip(base64.encodestring(exp_enc), "\n")
  
      # the email will be set as the key so we can use it to look up in the DB
      request.response.headers.add_header("Set-Cookie", WEB_ADMIN_PARAMS.COOKIE_EMAIL_PARAM + "=" + email_encoded)
      request.response.headers.add_header("Set-Cookie", WEB_ADMIN_PARAMS.COOKIE_KEY_PARAM + "=" + ssid_encoded)
      request.response.headers.add_header("Set-Cookie", WEB_ADMIN_PARAMS.COOKIE_EXPIRATION + "=" + exp_encoded)
      
      """ Create a new session object and return it """
      self.email = email
      self.ssid = ssid
      self.expiration = expiration
      self.account = account
    
      return self
    else:
      return None

  def get_current_session(self, request):
    """
    Returns a session object if a session can be detected given the HTTP request.
    This may include sifting through cookie values, or request params.
    
    Args:
    request
    
    Returns:
    Session or None
    """
    quoted_email = request.request.cookies.get(WEB_ADMIN_PARAMS.COOKIE_EMAIL_PARAM)
    quoted_ssid = request.request.cookies.get(WEB_ADMIN_PARAMS.COOKIE_KEY_PARAM)
    quoted_exp = request.request.cookies.get(WEB_ADMIN_PARAMS.COOKIE_EXPIRATION)
    
    if quoted_email == "" or quoted_ssid == "" or quoted_exp == "" or quoted_email == None or quoted_ssid == None or quoted_exp == None:
      return None
    else:
      import base64
      try: 
        unquoted_email = base64.decodestring(quoted_email)
        unquoted_ssid = base64.decodestring(quoted_ssid)
        unquoted_exp = base64.decodestring(quoted_exp)
      
        decrypted_email = encryption.des_decrypt_str(unquoted_email)
        decrypted_ssid = encryption.des_decrypt_str(unquoted_ssid)
        decrypted_exp = encryption.des_decrypt_str(unquoted_exp)
      except:
        logging.error("Error decoding sesssion: UnicodeDecodeError: 'ascii' codec can't decode byte: ordinal not in range(128)")
        return None 
      """ Make sure that the session has not expired """
      now = time.time()
      if not decrypted_exp:
        decrypted_exp = 0
      exp = float(decrypted_exp)
      if(now < exp):
        """ Make sure that the session is still valid """
        account = memcache_db.get_entity(decrypted_email, "Accounts")
        if account != None and account.cookieKey == decrypted_ssid:
          """ Create a new session object and return it """
          self.email = decrypted_email
          self.ssid = decrypted_ssid
          self.expiration = decrypted_exp
          self.account = account
        else:
          return None
      else:
        return None
      return self

  def terminate(self):
    """
    Remove cookie_key from datastore
    """
    email = self.email
    if email != None and email != "":
      account = memcache_db.get_entity(self.email, "Accounts")
      if account != None:
        update_fields = {"cookieKey" : "nada" }
        memcache_db.update_fields(email, "Accounts", update_fields)
  
  def get_email(self):
    return self.email
  
  def get_ssid(self):
    return self.ssid
  
  def get_expiration(self):
    return self.expiration
  
  def get_account_entity(self):
    return self.account

    

########NEW FILE########
__FILENAME__ = signin
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import webapp2
from google.appengine.ext.webapp import template
from serverside.constants import WEB_ADMIN_PARAMS, TEMPLATE_PATHS
from serverside.entities import memcache_db
from serverside.session import Session
from serverside.dao import accounts_dao
from serverside import update_account 
import logging
import time
import uuid


class SignIn(webapp2.RequestHandler):

  def post(self):
    """Get the username and password, hash password. Authenticate, make sure account is enabled then redirect to account page. """
    email = self.request.get("email")
    password = self.request.get("password")
    
    logging.info("Attempted log in attempt, email: " + email)
    
    template_values = {'error': "error"}
    if email != None and email != "" and password != None and password != "":
      entity = accounts_dao.authenticate_web_account(email, password)
      if entity:
        update_account.update_account(entity.key().name())
        Session().create_session(self, email, str(uuid.uuid4()), str(time.time() + WEB_ADMIN_PARAMS.VALID_FOR_SECONDS))
        self.redirect("/adminconsole")
      else:
        self.response.out.write(template.render(TEMPLATE_PATHS.CONSOLE_LOGIN, template_values))
    else:
      self.response.out.write(template.render(TEMPLATE_PATHS.CONSOLE_LOGIN, template_values))

########NEW FILE########
__FILENAME__ = signup
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from constants import ACCOUNT_STATUS
from entities import memcache_db
from entities.pending_create import Pending_Create
from google.appengine.api import mail
import webapp2
from google.appengine.ext.db import NotSavedError
from google.appengine.ext.webapp import template
from serverside.dao import accounts_dao, pending_create_dao
from serverside.entities.emails import Email
from tools import utils
from tools.xss import XssCleaner
import constants
import environment
import logging
import messages
import uuid


import json

class NewsLetterSignUp(webapp2.RequestHandler):
  def post(self):
    clean = XssCleaner()
    email = self.request.get('email')    
    email = clean.strip(email)
    newemail = Email(email=email)
    newemail.put()
    ret = {"success":"true"}
    ret = json.dumps(ret) 
    self.response.out.write(ret)



class SignUp(webapp2.RequestHandler):
  """
  get: is used to activate an account.
  post: is used to handle sign up requests coming from web form.
  """
  
  def get(self):
    """Account activation via email"""
    
    values = {'error_message' : "Activation not successful.",
              'error': True}
    
    id = self.request.get("activate")
    error_message = self.request.get("error_msg") 
    if id == None or id == "":
      if error_message:
        values['error_message'] = error_message
      logging.error("Activation attempted without ID")
    else:
      """Look up the account in pending creates table"""
      try:
        pending_entity = Pending_Create.get_by_key_name(id)
        account = None
        if pending_entity != None:
          """ Look up corresponding account entity """
          email = pending_entity.email
          account = memcache_db.get_entity(email, "Accounts")
        else:
          logging.error("Pending entity could not be looked up.")
          
        if account != None:
          if account.isEnabled == ACCOUNT_STATUS.PENDING_CREATE:
            update_fields = {"isEnabled" : ACCOUNT_STATUS.ENABLED }
            memcache_db.update_fields(email, "Accounts", update_fields)
            
            try:
              """ remove item from pending creates """
              pending_entity.delete()
            except NotSavedError:
              logging.error("Entity with id: " + id + " was not in data store...")
              
            values = {'activation' : True}
          else:
            logging.error("Account status is not pending create")
            
      except:
        logging.error("Activation tried and failed with ID: " + id)
    
    """ render with values set above """
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_LOGIN, values))
    
  def post(self):
    email = self.request.get("email")
    password = self.request.get("password")
    repeat_password = self.request.get('repeat_password')
    show_links = self.request.get("show_links")
    if not utils.validEmail(email):
      values = {"success" : False,
                "message" : "ERROR: You need to provide a valid email address."}
      if show_links == "yes":
        values['givelinks'] = True 
      self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_SIGN_UP, values))
      logging.error("Bad email %s"%email)
      return
    if password != repeat_password:
      values = {"success" : False,
                "message" : "ERROR: Passwords did not match."}
      if show_links == "yes":
        values['givelinks'] = True 
      logging.error("Bad passwords for email %s"%email)
      self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_SIGN_UP, values))
      return   
    ent_type = 'Accounts'
    existing_account = memcache_db.get_entity(email, ent_type)
    if existing_account != None:
      logging.error('An account already exists with that email: ' + existing_account.email)
 
      """ if the account is a test account, activate the account """
      if email in constants.TEST_ACCOUNTS and environment.is_dev():
        logging.debug("Account is a valid test account")
        
        memcache_db.delete_entity(existing_account, email)
        accounts_dao.create_account(email, password, True)
        
        message = "Your test account has been activated!"
        values = {"success" : True,
                "message" : message}
        if show_links == "yes":
          values['givelinks'] = True 
      elif existing_account.isEnabled == ACCOUNT_STATUS.PENDING_CREATE:
        """ REPEAT SIGN UP WITH UNACTIVATED ACCOUNT!!!!!!!!! """
        """ send the email again with the same activation ID """
        pc = pending_create_dao.get_id_by_email(email)
        activate_url = get_activate_url(pc.id)
        email_sent = send_email(email, activate_url)
        logging.info("Repeat sign up for account that was not activated yet. An email will be sent to with same activation link. Email: " + email + ", activation link: " + activate_url)
        message = ""
        if email_sent:
          message = "An email has been sent to you with a link to activate your account!"
        else:
          message = "There was an error during account creation. Please send an email to support@cloudcaptive.com"
        values = {"success" : True,
                  "message" : message}
        if show_links == "yes":
          values['givelinks'] = True 
        
      else:
        message = "ERROR: An account using this email address already exists. Contact support@cloudcaptive for support."
        values = {"success" : False,
                "message" : message}
        if show_links == "yes":
          values['givelinks'] = True 
    else:    
      """create an account and send an email for validation"""
      accounts_dao.create_account(email, password)
      
      """Add email to pending creates table"""
      id = str(uuid.uuid4())
      pending_create = Pending_Create(key_name=id, id=id, email=email)
      pending_create.put()
          
      
      """send an email to user to complete set up, get arguments in the string will be email and cookie ID"""
      activate_url = get_activate_url(id)
      logging.info("Activation URL for account: " + email + " is " + activate_url)
      email_sent = send_email(email, activate_url)
  
      message = ""
      if email_sent:
        message = "Sign up was a success. An activation link has been sent to your email address."
      else:
        message = "There was an error during account creation. Please send an email to support@cloudcaptive.com"
      values = {"success" : True,
                "message" : message}
      if show_links == "yes":
        values['givelinks'] = True 
    """ Render result with whatever values were filled in above """  
    self.response.out.write(template.render(constants.TEMPLATE_PATHS.CONSOLE_SIGN_UP, values))
      
def get_activate_url(id):
  return constants.WEB_SIGNUP_URLS.ACTIVATE_URL + "?activate=" + id

def send_email(email, activate_url):
  email_sent = False
  try:  
    mail.send_mail(sender="UserInfuser <" + constants.APP_OWNER_EMAIL + ">",
                   to=email,
                   subject="Welcome to UserInfuser!",
                   body= messages.get_activation_email(activate_url))
    email_sent = True
  except:
    email_sent = False
    logging.error("Error sending account activation email to account: " + email + ", activation url was: " + activate_url)
  return email_sent

########NEW FILE########
__FILENAME__ = dummydata
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Feb 24, 2011

@author: shan
'''
import webapp2

from serverside.dao import accounts_dao
from serverside.dao import users_dao
from serverside.entities.counter import *
import random

class CreateDummyAccountsAndUsers(webapp2.RequestHandler):
  def get(self):
    """
    Generate several accounts and users to test out stuff with
    """
    
    for i in range(10):
      """
      create 10 accounts
      """
      email = "user" + str(i) + "@infuser.com"
      account_entity = accounts_dao.create_account(email, "1111", True)
      
      for j in range(random.randint(40,100)):
        """
        create 40-100 users per account
        """
        user_id = "crazy" + str(i) + "crazy" + str(j) + "@someplaceelse" + str(i) + ".com"
        users_dao.create_new_user(email, user_id)
        users_dao.set_user_points(email, user_id, random.randint(5,200))
        
    self.response.out.write("Done. :-)")

class CreateDummyBatchData(webapp2.RequestHandler):
  def get(self):      
    # yesterday 
    import datetime
    import random
     
    today = datetime.datetime.now()
    yesterday = today - datetime.timedelta(days=1)
    tomorrow = today + datetime.timedelta(days=1) 
    account_key = "test@test.c"
    badges = ["theme-name-private", "theme2-name-private", "theme3-name-private"]
    for kk in range(365):
      for bid in badges:
        rand = random.randint(0,300)
        b = BadgePointsBatch(date=today + datetime.timedelta(days=kk),
                           badgeid=bid,
                           account_key=account_key,
                           counter=rand)
        b.put()
        rand = random.randint(0,300)
        b = BadgeBatch(date=today + datetime.timedelta(days=kk),
                           badgeid=bid,
                           account_key=account_key,
                           counter=rand)
        b.put()
    for kk in range(365):
      ii = 0
      rand = random.randint(0,300)
      b = APICountBatch(date=today + datetime.timedelta(days=kk),
                       account_key=account_key,
                       counter=rand)
      b.put()
      rand = random.randint(0,300)
      b = PointBatch(date=today + datetime.timedelta(days=kk),
                       account_key=account_key,
                       counter=rand)
      b.put()


    self.response.out.write("Done. :-)")

########NEW FILE########
__FILENAME__ = test
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
""" All paths here run unit tests
"""

import webapp2
from google.appengine.api import mail, memcache
from google.appengine.ext import db
from google.appengine.ext.db import *
from serverside import constants
from serverside.entities import memcache_db
from serverside.entities.accounts import *
from serverside.entities.badges import *
from serverside.entities.pending_create import *
from serverside.entities.users import *
from serverside.entities.widgets import *
from serverside.dao import accounts_dao
from serverside.session import Session
from serverside.tools.utils import account_login_required
from serverside import logs 
from serverside.entities.logs import Logs
from serverside.testing.dummydata import *
import cgi
import logging
import os
import time
import wsgiref.handlers
import random
class TestDB(webapp2.RequestHandler):
  def get(self):
   self.response.out.write("Test 1:" +self.test1() +"<br>")
   self.response.out.write("Test 2:" + self.test2() +"<br>")
   self.response.out.write("Test 3:" + self.test3() +"<br>")
   self.response.out.write("Test 4:" + self.test4() +"<br>")

  """ This test creates, updates, and deletes an Account """
  def test1(self):
    key = "test@test.com"
    ent_type = "Accounts"
    trophy_case_widget = TrophyCase(key_name=key)
    points_widget = Points(key_name=key)
    rank_widget = Rank(key_name=key)
    newacc = Accounts(key_name=key,
                     password="aaa",
                     email=key,
                     isEnabled="enabled",
                     accountType="bronze",
                     paymentType="free",
                     cookieKey="xxx",
                     apiKey="xxx",
                     trophyWidget=trophy_case_widget,
                     pointsWidget=points_widget,
                     rankWidget=rank_widget)
    try:
      memcache_db.delete_entity(newacc, key)
    except Exception:
      pass
    # Save and get saved ent
    ret = memcache_db.save_entity(newacc, key)
    sameent = memcache_db.get_entity(key, ent_type) 
    if sameent.email != key:
      return "Error getting same account. Subtest 1"

    # purge from memcache and get from db
    memcache.delete(key=key, namespace=ent_type)
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.email != key:
      return "Error getting same account from DB (no cache). Subtest 2"

    # Set and get new user name
    diction = {"email":"test2@test.com"}
    ret2 = memcache_db.update_fields(key, ent_type, diction)
    ret2 = sameent.put()
    if ret != ret2:
      self.response.out.write("Error getting key name")
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.email != "test2@test.com":
      return "Error getting same account after altering entity. Subtest 3"


    try:
      memcache_db.delete_entity(newacc, key)
    except Exception:
      return "Error deleting entity. Subtest 4"
      
    return "Success"

  """ This test creates, updates, and deletes a Badges entity"""
  def test2(self):
    account_key = "raj"
    trophy_case_widget = TrophyCase(key_name=account_key)
    points_widget = Points(key_name=account_key)
    rank_widget = Rank(key_name=account_key)
    newacc = Accounts(key_name=account_key,
                     password="aaa",
                     email="a@a.a",
                     isEnabled="enabled",
                     accountType="bronze",
                     paymentType="free",
                     apiKey="xxx",
                     cookieKey="xxx",
                     trophyWidget=trophy_case_widget,
                     pointsWidget=points_widget,
                     rankWidget=rank_widget)
    try:
      memcache_db.delete_entity(newacc, key)
    except Exception:
      pass

    # Save and get saved ent
    ret = memcache_db.save_entity(newacc, account_key)

    key = "testbadge1"
    ent_type = "Badges"
    newacc = Badges(key_name=key, 
                    name="badge1",
                    description=key,
                    altText="a really cool badge", 
                    setType="free",
                    isEnabled="yes",
                    creator=newacc,
                    permissions="private",
                    blobKey="xxxx",
                    storageType="blob") 
    try:
      memcache_db.delete_entity(newacc, key)
    except Exception:
      pass
    # Save and get saved ent
    ret = memcache_db.save_entity(newacc, key)
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.description != key:
      return "Error getting same account. Subtest 1"

    # purge from memcache and get from db
    memcache.delete(key=key, namespace=ent_type)
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.description != key:
      return "Error getting same account from DB (no cache). Subtest 2"

    # Set and get new user name
    diction = {"isEnabled":"no", "permissions":"public"}
    ret2 = memcache_db.update_fields(key, ent_type, diction)
    ret2 = sameent.put()
    if ret != ret2:
      self.response.out.write("Error getting key name")
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.isEnabled != "no" or sameent.permissions != "public":
      return "Error getting same account after altering entity. Subtest 3"

    try:
      memcache_db.delete_entity(sameent, key)
    except Exception:
      return "Error deleting entity. Subtest 4"

    try:
      memcache_db.delete_entity(newacc, account_key)
    except Exception:
      return "Error deleting account. Subtest 5"

    return "Success"

  """ This test creates, updates, and deletes User"""
  def test3(self):
    account_key = "a@a.a"
    trophy_case_widget = TrophyCase(key_name=account_key)
    points_widget = Points(key_name=account_key)
    rank_widget = Rank(key_name=account_key)
    newacc = Accounts(key_name=account_key,
                     password="aaa",
                     email="a@a.a",
                     isEnabled="enabled",
                     accountType="bronze",
                     paymentType="free",
                     apiKey="xxx",
                     cookieKey="xxx",
                     trophyWidget=trophy_case_widget,
                     pointsWidget=points_widget,
                     rankWidget=rank_widget)
    try:
      memcache_db.delete_entity(newacc, account_key)
    except Exception:
      pass

    # Save and get saved ent
    ret = memcache_db.save_entity(newacc, account_key)

    key = "testuser1"
    ent_type = "Users"
    newacc = Users(key_name=key,
                   userid=key,
                   isEnabled="yes",
                   accountRef=newacc,
                   tags = key)
    try:
      memcache_db.delete_entity(newacc, key)
    except Exception:
      pass
    # Save and get saved ent
    ret = memcache_db.save_entity(newacc, key)
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.tags != key:
      return "Error getting same entity. Subtest 1"

    # purge from memcache and get from db
    memcache.delete(key=key, namespace=ent_type)
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.tags != key:
      return "Error getting same entity from DB (no cache). Subtest 2"

    # Set and get new user name
    diction = {"tags":"goodbye:hello"}
    ret2 = memcache_db.update_fields(key, ent_type, diction)
    ret2 = sameent.put()
    if ret != ret2:
      self.response.out.write("Error getting key name")
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.tags != "goodbye:hello":
      return "Error getting same entity after altering entity. Subtest 3"


    try:
      memcache_db.delete_entity(newacc, account_key)
      memcache_db.delete_entity(sameent, key)
    except Exception:
      return "Error deleting entity. Subtest 4"
      
    return "Success"


  """ This test creates, updates, and deletes a BadgeInstance """
  def test4(self):
    account_key = "a@a.a"
    trophy_case_widget = TrophyCase(key_name=account_key)
    points_widget = Points(key_name=account_key)
    rank_widget = Rank(key_name=account_key)
    newacc = Accounts(key_name=account_key,
                     password="aaa",
                     email="a@a.a",
                     isEnabled="enabled",
                     accountType="bronze",
                     paymentType="free",
                     apiKey="xxx",
                     cookieKey="xxx",
                     trophyWidget=trophy_case_widget,
                     pointsWidget=points_widget, 
                     rankWidget=rank_widget)
    try:
      memcache_db.delete_entity(newacc, key)
    except Exception:
      pass

    # Save an account
    ret = memcache_db.save_entity(newacc, account_key)

    user_key = "testuser1"
    newuser = Users(key_name=user_key,
                   userid=user_key,
                   isEnabled="yes",
                   accountRef=newacc,
                   tags = user_key)
    try:
      memcache_db.delete_entity(newacc, user_key)
    except Exception:
      pass
    # Save a user
    ret = memcache_db.save_entity(newacc, user_key)

    # Create a Badge Type
    badge_key = "testbadge1"
    badgetype = Badges(key_name=badge_key,
                    name="badge1",
                    description=badge_key,
                    altText="a really cool badge", 
                    setType="free",
                    isEnabled="yes",
                    creator=newacc,
                    permissions="private",
                    storageType="blob",
                    blobKey="xxxx") 
    try:
      memcache_db.delete_entity(badgetype, badge_key)
    except Exception:
      pass
    # Save and get saved ent
    ret = memcache_db.save_entity(badgetype, badge_key)
 
    key = "testbadgeinstance1"
    ent_type = "BadgeInstance"
    badgeinstance = BadgeInstance(key_name=key,
                    awarded="no",
                    badgeRef=badgetype,
                    userRef=newuser,
                    pointRequired=10,
                    pointsEarned=0,
                    permissions="private") 
    try:
      memcache_db.delete_entity(badgeinstance, key)
    except Exception:
      pass
    # Save and get saved ent
    ret = memcache_db.save_entity(badgeinstance, key)
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.awarded != "no":
      return "Error getting same entity. Subtest 1"

    # purge from memcache and get from db
    memcache.delete(key=key, namespace=ent_type)
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.awarded != "no":
      return "Error getting same entity from DB (no cache). Subtest 2"

    # Set and get new user name
    diction = {"pointsRequired":11, "awarded":"no"}
    inc_diction = {"pointsEarned":5}
    ret2 = memcache_db.update_fields(key, ent_type, diction, inc_diction)
    ret2 = sameent.put()
    if ret != ret2:
      self.response.out.write("Error getting key name")
    sameent = memcache_db.get_entity(key, ent_type)
    if sameent.pointsRequired!= 11 \
          or sameent.pointsEarned != 5:
      return "Error getting same entity after altering entity. Subtest 3"


    # Cleanup
    try:
      memcache_db.delete_entity(badgeinstance, key)
    except Exception:
      return "Error deleting entity. Subtest 4"
    try:
      memcache_db.delete_entity(newacc, account_key)
    except Exception:
      return "Error deleting entity. Subtest 4"
    try:
      memcache_db.delete_entity(badgetype, badge_key)
    except Exception:
      return "Error deleting entity. Subtest 4"
    try:
      memcache_db.delete_entity(newuser, user_key)
    except Exception:
      return "Error deleting entity. Subtest 4"
       
    return "Success"

class TestPendingCreates(webapp2.RequestHandler):
  def get(self):
    """ Add to the db, get, and delete """
    
    id = "91658085309165808530"
    email = "shanrandhawa@gmail.com"
    
    pending_create = Pending_Create(key_name=id, id=id, email=email)
    key = pending_create.put()
    
    
    self.response.out.write("Wrote (put) entity. They returned key = " + str(key) + "<br/>")
    
    ret = Pending_Create.get_by_key_name(id)
    if ret == None:
      self.response.out.write("Not found in DB<br/>")
    else:
      self.response.out.write("Entity returned: email: " + ret.email + ", id: " + ret.id + "<br/>")
      self.response.out.write("Attempt to delete it...<br/>")
      
      try:
        ret.delete()
      except NotSavedError:
        self.response.out.write("The entity that u are trying to delte was not in the datastore<br/>")
        return
      self.response.out.write("Seems like the entity was deleted successfully...<br/>")
      
      self.response.out.write("Try to look it up again...<br/>")
      ret = Pending_Create.get_by_key_name(id)
      if ret == None:
        self.response.out.write("Nothing found... that's good.")
      else:
        self.response.out.write("Something found... not good.")
    
 
class TestEncryption(webapp2.RequestHandler):
  """Test encyption methods """
  def get(self):
    from serverside.tools import encryption
    """Do some simple encryption and show results """
    mystr = "hello, world"
    self.response.out.write("encrypt string: " + mystr + "<br/>")
    mystr_enc = encryption.des_encrypt_str("hello, world")
    self.response.out.write("encrypted: " + mystr_enc + "<br/>")
    mystr_dec = encryption.des_decrypt_str(mystr_enc)
    self.response.out.write("decrypted: " + mystr_dec + "<br/>")

    
class TestOSEnvironment(webapp2.RequestHandler):
  """Test method to see how environments are defined"""
  
  def get(self):
    print "OS: " + os.environ["SERVER_SOFTWARE"]
    self.response.out.write("OS server software: " + os.environ["SERVER_SOFTWARE"])
    
    """Try constants"""
    self.response.out.write("<br/>CONSTANT: " + constants.WEB_SIGNUP_URLS.POST_DATA)
    
  
  def post(self):
    pass   
class TestCreateSession(webapp2.RequestHandler):
  def get(self):
    self.response.out.write("Creating session and setting cookie")
    
    import uuid
    import time
    created_session = Session().create_session(self, "shanrandhawa@gmail.com", str(uuid.uuid4()), str(time.time() + WEB_ADMIN_PARAMS.VALID_FOR_SECONDS))
    if created_session == None:
      self.response.out.write("<br/>No session created")
    else:
      self.response.out.write("<br/>Session was created")
    
class TestViewLoggedIn(webapp2.RequestHandler):
  @account_login_required
  def get(self):
    self.response.out.write("<br/>If you reached here you are logged in!")
    
    sess = Session().get_current_session(self)
    if(sess == None):
      self.response.out.write("<br/>You are not logged in!!")
    else:
      self.response.out.write("<br/>You are logged in as:")
      email = sess.get_email()
      self.response.out.write("<br/>" + email)

class TestTerminateSession(webapp2.RequestHandler):
  def get(self):
    self.response.out.write("terminating the follow session:")
    sess = Session().get_current_session(self)
    if(sess == None):
      self.response.out.write("<br/>You are not logged in!!")
    else:
      self.response.out.write("<br/>You are logged in as:")
      email = sess.get_email()
      self.response.out.write("<br/>" + email)
      sess.terminate()

class TestViewLoggedOut(webapp2.RequestHandler):
  def get(self):
    self.response.out.write("You should be able to see this page, logged in or not...")
    sess = Session().get_current_session(self)
    if(sess == None):
      self.response.out.write("<br/>You are not logged in!!")
    else:
      self.response.out.write("<br/>You are logged in as:")
      email = sess.get_email()
      self.response.out.write("<br/>" + email)

class TestLogs(webapp2.RequestHandler):
  def get(self):
    log1 = {"account":"test@test.test",
            'event':'getuserdata',
            'api': 'get_user_data',
            'is_api':'yes',
            'user':"test_user",
            'success':'true',
            'ip':'127.0.0.1'}

    log1["details"] = u"HELLO 0"
    logs.create(log1)    
    log1["is_api"] = 'no'
    log1["details"] = u"HELLO 1"
    logs.create(log1)
    log1["is_api"] = 'yes'
    log1["details"] = u"HELLO 2"
    log1["points"] = 100
    logs.create(log1)
    log1["details"] = u"A BUNCH OF accent e's \xe9\xe9\xe9"
    logs.create(log1)

class TestLogsCheck(webapp2.RequestHandler):
  def get(self):
    q = Logs.all()
    q.filter("account = ", "test@test.test") 
    ents = q.fetch(10)
    count = 0
    for ii in ents:
      count += 1
      self.response.out.write(ii.details)
      self.response.out.write("<br/>")
    self.response.out.write("Number fetched " + str(count))

class TestAccount(webapp2.RequestHandler):
  def get(self):
    pass

class TestBadges(webapp2.RequestHandler):
  def get(self):
    pass

class TestUsers(webapp2.RequestHandler):
  def get(self):
    pass

class CreateDummyAPIAnalytics(webapp2.RequestHandler):
  def fill_with_api_logs(self, acc):
    today = datetime.datetime.now() 
    rand = random.randint(1, 100)
    batch = APICountBatch(date=today, account_key=acc.key().name(), counter=rand)
    batch.put()
    for ii in range(0, 10):
      rand = random.randint(1, 100) + 10*ii
      delta = datetime.timedelta(days=ii) 
      cur_date =  today - delta
      batch = APICountBatch(date=cur_date, account_key=acc.key().name(), counter=rand)
      batch.put()
      
  def get(self):
    created_logs = ""
    for ii in constants.TEST_ACCOUNTS:
      acc = accounts_dao.get(ii)
      if acc:
        self.fill_with_api_logs(acc) 
        created_logs = acc.key().name()
    if created_logs:
      self.response.out.write("Created logs for test account " + created_logs)
    else:
      self.response.out.write("Did not create any logs, create a test account first")
      

class CreateDummyBadgePointsAnalytics(webapp2.RequestHandler):
  def fill_with_api_logs(self, acc):
    today = datetime.datetime.now() 
    rand = random.randint(1, 100)
    batch = BadgePointsBatch(date=today, badgeid="badge1", account_key=acc.key().name(), counter=rand)
    batch.put()
    for ii in range(0, 10):
      rand = random.randint(1, 100) + 10*ii
      delta = datetime.timedelta(days=ii) 
      cur_date =  today - delta
      batch = BadgePointsBatch(date=cur_date, badgeid="badge1", account_key=acc.key().name(), counter=rand)
      batch.put()

    today = datetime.datetime.now() 
    rand = random.randint(1, 100)
    batch = BadgePointsBatch(date=today, badgeid="badge2", account_key=acc.key().name(), counter=rand)
    batch.put()
    for ii in range(0, 10):
      rand = random.randint(1, 100) + 10*ii
      delta = datetime.timedelta(days=ii) 
      cur_date =  today - delta
      batch = BadgePointsBatch(date=cur_date, badgeid="badge2", account_key=acc.key().name(), counter=rand)
      batch.put()
       
  def get(self):
    created_logs = ""
    for ii in constants.TEST_ACCOUNTS:
      acc = accounts_dao.get(ii)
      if acc:
        self.fill_with_api_logs(acc) 
        created_logs = acc.key().name()
    if created_logs:
      self.response.out.write("Created logs for test account " + created_logs)
    else:
      self.response.out.write("Did not create any logs, create a test account first")

class CreateDummyBadgeAnalytics(webapp2.RequestHandler):
  def fill_with_api_logs(self, acc):
    today = datetime.datetime.now() 
    rand = random.randint(1, 100)
    batch = BadgeBatch(date=today, badgeid="badge1", account_key=acc.key().name(), counter=rand)
    batch.put()
    for ii in range(0, 10):
      rand = random.randint(1, 100) + 10*ii
      delta = datetime.timedelta(days=ii) 
      cur_date =  today - delta
      batch = BadgeBatch(date=cur_date, badgeid="badge1", account_key=acc.key().name(), counter=rand)
      batch.put()

    today = datetime.datetime.now() 
    rand = random.randint(1, 100)
    batch = BadgeBatch(date=today, badgeid="badge2", account_key=acc.key().name(), counter=rand)
    batch.put()
    for ii in range(0, 10):
      rand = random.randint(1, 100) + 10*ii
      delta = datetime.timedelta(days=ii) 
      cur_date =  today - delta
      batch = BadgeBatch(date=cur_date, badgeid="badge2", account_key=acc.key().name(), counter=rand)
      batch.put()
       
  def get(self):
    created_logs = ""
    for ii in constants.TEST_ACCOUNTS:
      acc = accounts_dao.get(ii)
      if acc:
        self.fill_with_api_logs(acc) 
        created_logs = acc.key().name()
    if created_logs:
      self.response.out.write("Created logs for test account " + created_logs)
    else:
      self.response.out.write("Did not create any logs, create a test account first")


app = webapp2.WSGIApplication([
  ('/test/db', TestDB),
  ('/test/logscreate', TestLogs),
  ('/test/logscheck', TestLogsCheck),
  ('/test/accounts', TestAccount),
  ('/test/badges', TestBadges),
  ('/test/users', TestUsers),
  ('/test/encryption', TestEncryption),
  ('/test/environ', TestOSEnvironment),
  ('/test/createsession', TestCreateSession),
  ('/test/viewloggedin', TestViewLoggedIn),
  ('/test/terminatesession', TestTerminateSession),
  ('/test/viewloggedout', TestViewLoggedOut),
  ('/test/createdummyaccountsandusers', CreateDummyAccountsAndUsers),
  ('/test/createdummyapianalytics', CreateDummyAPIAnalytics),
  ('/test/createdummybadgepointsanalytics', CreateDummyBadgePointsAnalytics),
  ('/test/createdummybadgeanalytics', CreateDummyBadgeAnalytics),
  ('/test/createbatches', CreateDummyBatchData),
  ('/test/pendingcreates', TestPendingCreates)
], debug=True)


########NEW FILE########
__FILENAME__ = encryption
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Jan 21, 2011

@author: shan
'''

import urllib
import string
import logging
from serverside.dao import passphrase_dao

NO_ENCRYPT = True # For Mac OSX pycrypto issues
try:
  from Crypto.Cipher import DES
  NO_ENCRYPT = False
except:
  pass

def aes_encrypt_str(s):
  """ AES encryption using the pycrpyto lib """
  from Crypto.Cipher import AES
  
  for i in range(16-(len(s) % 16)):
    s += " "
  
  enc_obj = AES.new(passphrase_dao.get_aes_encrypt_secret(), AES.MODE_ECB)
  return enc_obj.encrypt(s)

def aes_decrypt_str(s):
  """ AES encryption using the pycrpyto lib """
  from Crypto.Cipher import AES
  enc_obj = AES.new(passphrase_dao.get_aes_encrypt_secret(), AES.MODE_ECB)
  return string.rstrip(enc_obj.decrypt(s))

def des_encrypt_str(str_to_encrypt):
  """DES encryption of string using PyCrypto lib"""
  if NO_ENCRYPT:
    return str_to_encrypt
  enc_obj = DES.new(passphrase_dao.get_encrypt_secret(), DES.MODE_ECB)
  
  logging.info("Input string, about to pad: " + str_to_encrypt + ". Str len: " + str(len(str_to_encrypt)))
  
  """ Convert to UTF-8 encoding """
  str_to_encrypt.encode("utf-8")
  logging.info("THE UTF-8 String: " + str_to_encrypt)
  
  for i in range(8-(len(str_to_encrypt) % 8)):
    str_to_encrypt += " "
  
  logging.info("Input string, padded: " + str_to_encrypt)
  
  return enc_obj.encrypt(str_to_encrypt)
  
  
def des_decrypt_str(str_to_decrypt):
  """DES decryption of string using PyCrypto lib"""
  if NO_ENCRYPT:
    return str_to_decrypt
  enc_obj = DES.new(passphrase_dao.get_encrypt_secret(), DES.MODE_ECB)
  dec_str = enc_obj.decrypt(str_to_decrypt)

  # ISSUE: This throws an unable to encode ascii codec exception
  try:
    dec_str.encode("ascii")
  except:
    logging.error("Unable to encode/decode ascii codec")
    return "" 

  return string.rstrip(dec_str)
  

def simple_encrypt_encode(s):
  """Very simple XOR encryption and url escaping"""
  
  s_xor = xor_str(s)
  return urllib.quote(s_xor, safe="")


def simple_decrpyt_decode(s):
  """Very simple XOR decryption and url unquoting"""
  
  s_unquoted = urllib.unquote(s)
  return xor_str(s_unquoted)

  
def xor_str(s, operand = 1):
  """XOR each element in the string with operand. Returns string"""
  
  b_array = bytearray(s)
  retval = ""
  for b in b_array:
    b = b ^ 1
    retval += str(chr(b))
  return retval

########NEW FILE########
__FILENAME__ = jsmin
#!/usr/bin/python

# This code is original from jsmin by Douglas Crockford, it was translated to
# Python by Baruch Even. The original code had the following copyright and
# license.
#
# /* jsmin.c
#    2007-05-22
#
# Copyright (c) 2002 Douglas Crockford  (www.crockford.com)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# The Software shall be used for Good, not Evil.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# */

from StringIO import StringIO

def jsmin(js):
    ins = StringIO(js)
    outs = StringIO()
    JavascriptMinify().minify(ins, outs)
    str = outs.getvalue()
    if len(str) > 0 and str[0] == '\n':
        str = str[1:]
    return str

def isAlphanum(c):
    """return true if the character is a letter, digit, underscore,
           dollar sign, or non-ASCII character.
    """
    return ((c >= 'a' and c <= 'z') or (c >= '0' and c <= '9') or
            (c >= 'A' and c <= 'Z') or c == '_' or c == '$' or c == '\\' or (c is not None and ord(c) > 126));

class UnterminatedComment(Exception):
    pass

class UnterminatedStringLiteral(Exception):
    pass

class UnterminatedRegularExpression(Exception):
    pass

class JavascriptMinify(object):

    def _outA(self):
        self.outstream.write(self.theA)
    def _outB(self):
        self.outstream.write(self.theB)

    def _get(self):
        """return the next character from stdin. Watch out for lookahead. If
           the character is a control character, translate it to a space or
           linefeed.
        """
        c = self.theLookahead
        self.theLookahead = None
        if c == None:
            c = self.instream.read(1)
        if c >= ' ' or c == '\n':
            return c
        if c == '': # EOF
            return '\000'
        if c == '\r':
            return '\n'
        return ' '

    def _peek(self):
        self.theLookahead = self._get()
        return self.theLookahead

    def _next(self):
        """get the next character, excluding comments. peek() is used to see
           if an unescaped '/' is followed by a '/' or '*'.
        """
        c = self._get()
        if c == '/' and self.theA != '\\':
            p = self._peek()
            if p == '/':
                c = self._get()
                while c > '\n':
                    c = self._get()
                return c
            if p == '*':
                c = self._get()
                while 1:
                    c = self._get()
                    if c == '*':
                        if self._peek() == '/':
                            self._get()
                            return ' '
                    if c == '\000':
                        raise UnterminatedComment()

        return c

    def _action(self, action):
        """do something! What you do is determined by the argument:
           1   Output A. Copy B to A. Get the next B.
           2   Copy B to A. Get the next B. (Delete A).
           3   Get the next B. (Delete B).
           action treats a string as a single character. Wow!
           action recognizes a regular expression if it is preceded by ( or , or =.
        """
        if action <= 1:
            self._outA()

        if action <= 2:
            self.theA = self.theB
            if self.theA == "'" or self.theA == '"':
                while 1:
                    self._outA()
                    self.theA = self._get()
                    if self.theA == self.theB:
                        break
                    if self.theA <= '\n':
                        raise UnterminatedStringLiteral()
                    if self.theA == '\\':
                        self._outA()
                        self.theA = self._get()


        if action <= 3:
            self.theB = self._next()
            if self.theB == '/' and (self.theA == '(' or self.theA == ',' or
                                     self.theA == '=' or self.theA == ':' or
                                     self.theA == '[' or self.theA == '?' or
                                     self.theA == '!' or self.theA == '&' or
                                     self.theA == '|' or self.theA == ';' or
                                     self.theA == '{' or self.theA == '}' or
                                     self.theA == '\n'):
                self._outA()
                self._outB()
                while 1:
                    self.theA = self._get()
                    if self.theA == '/':
                        break
                    elif self.theA == '\\':
                        self._outA()
                        self.theA = self._get()
                    elif self.theA <= '\n':
                        raise UnterminatedRegularExpression()
                    self._outA()
                self.theB = self._next()


    def _jsmin(self):
        """Copy the input to the output, deleting the characters which are
           insignificant to JavaScript. Comments will be removed. Tabs will be
           replaced with spaces. Carriage returns will be replaced with linefeeds.
           Most spaces and linefeeds will be removed.
        """
        self.theA = '\n'
        self._action(3)

        while self.theA != '\000':
            if self.theA == ' ':
                if isAlphanum(self.theB):
                    self._action(1)
                else:
                    self._action(2)
            elif self.theA == '\n':
                if self.theB in ['{', '[', '(', '+', '-']:
                    self._action(1)
                elif self.theB == ' ':
                    self._action(3)
                else:
                    if isAlphanum(self.theB):
                        self._action(1)
                    else:
                        self._action(2)
            else:
                if self.theB == ' ':
                    if isAlphanum(self.theA):
                        self._action(1)
                    else:
                        self._action(3)
                elif self.theB == '\n':
                    if self.theA in ['}', ']', ')', '+', '-', '"', '\'']:
                        self._action(1)
                    else:
                        if isAlphanum(self.theA):
                            self._action(1)
                        else:
                            self._action(3)
                else:
                    self._action(1)

    def minify(self, instream, outstream):
        self.instream = instream
        self.outstream = outstream
        self.theA = '\n'
        self.theB = None
        self.theLookahead = None

        self._jsmin()
        self.instream.close()

if __name__ == '__main__':
    import sys
    jsm = JavascriptMinify()
    jsm.minify(sys.stdin, sys.stdout)

########NEW FILE########
__FILENAME__ = utils
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
'''
Created on Jan 10, 2011

@author: shan
'''
from google.appengine.ext.webapp import template
from serverside.constants import TEMPLATE_PATHS
from serverside.session import Session
import re
import logging
import string
import random

def generate_random_string(length = 8):
  """ Will generate a random uppercase/number string for specified length """
  return ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(length))

def camelcase_to_friendly_str(s):
  """
  Utility to convert camelcase string to a friend string.
  For example, camelcase_to_friendly_str("helloWorld") would return "Hello World"
  """
  if s == None or len(s) < 1:
    return None
  
  ret_str = ""
  j=0
  for i in range(len(s)):
    if str(s[i]).isupper():
      ret_str += s[j:i] + " "
      j=i
  ret_str += s[j:]
  
  import string
  ret_str = string.capitalize(ret_str[0]) + ret_str[1:]
  return ret_str
  

def validEmail(email):
  """Check to see if the string is formatted as a valid email address.
  """
  
  if len(email) > 7:
    if re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", email) != None:
      return 1
    return 0

def account_login_required(handler_method):
  """
  Decorator to check if user is logged in. If user is not logged in they will be redirect to login screen.
  """

  def check_login(self, *args):
    if self.request.method != 'GET' and self.request.method != 'POST':
      self.response.out.write(template.render(TEMPLATE_PATHS.CONSOLE_LOGIN, None))
    else:
      user_session = Session().get_current_session(self)
      if user_session == None:
        self.response.out.write(template.render(TEMPLATE_PATHS.CONSOLE_LOGIN, None))  
      else:
        logging.info("LEGIT user session! Email: " + user_session.get_email())
        handler_method(self, *args)
        
  return check_login

def format_integer(number):
  s = '%d' % number
  groups = []
  while s and s[-1].isdigit():
      groups.append(s[-3:])
      s = s[:-3]
  return s + ','.join(reversed(groups))


########NEW FILE########
__FILENAME__ = xss
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from htmllib import HTMLParser
from cgi import escape
from urlparse import urlparse
from formatter import AbstractFormatter
from htmlentitydefs import entitydefs
from xml.sax.saxutils import quoteattr

def xssescape(text):
    """Gets rid of < and > and & and, for good measure, :"""
    return escape(text, quote=True).replace(':','&#58;')

class XssCleaner(HTMLParser):
    def __init__(self, fmt = AbstractFormatter):
        HTMLParser.__init__(self, fmt)
        self.result = ""
        self.open_tags = []
        # A list of the only tags allowed.  Be careful adding to this.  Adding
        # "script," for example, would not be smart.  'img' is out by default 
        # because of the danger of IMG embedded commands, and/or web bugs.
        self.permitted_tags = ['a', 'b', 'blockquote', 'br', 'i', 
                          'li', 'ol', 'ul', 'p', 'cite']

        # A list of tags that require no closing tag.
        self.requires_no_close = ['img', 'br']

        # A dictionary showing the only attributes allowed for particular tags.
        # If a tag is not listed here, it is allowed no attributes.  Adding
        # "on" tags, like "onhover," would not be smart.  Also be very careful
        # of "background" and "style."
        self.allowed_attributes = \
            {'a':['href','title'],
             'img':['src','alt'],
             'blockquote':['type']}

        # The only schemes allowed in URLs (for href and src attributes).
        # Adding "javascript" or "vbscript" to this list would not be smart.
        self.allowed_schemes = ['http','https','ftp']
    def handle_data(self, data):
        if data:
            self.result += xssescape(data)
    def handle_charref(self, ref):
        if len(ref) < 7 and ref.isdigit():
            self.result += '&#%s;' % ref
        else:
            self.result += xssescape('&#%s' % ref)
    def handle_entityref(self, ref):
        if ref in entitydefs:
            self.result += '&%s;' % ref
        else:
            self.result += xssescape('&%s' % ref)
    def handle_comment(self, comment):
        if comment:
            self.result += xssescape("<!--%s-->" % comment)

    def handle_starttag(self, tag, method, attrs):
        if tag not in self.permitted_tags:
            self.result += xssescape("<%s>" %  tag)
        else:
            bt = "<" + tag
            if tag in self.allowed_attributes:
                attrs = dict(attrs)
                self.allowed_attributes_here = \
                  [x for x in self.allowed_attributes[tag] if x in attrs \
                   and len(attrs[x]) > 0]
                for attribute in self.allowed_attributes_here:
                    if attribute in ['href', 'src', 'background']:
                        if self.url_is_acceptable(attrs[attribute]):
                            bt += ' %s="%s"' % (attribute, attrs[attribute])
                    else:
                        bt += ' %s=%s' % \
                           (xssescape(attribute), quoteattr(attrs[attribute]))
            if bt == "<a" or bt == "<img":
                return
            if tag in self.requires_no_close:
                bt += "/"
            bt += ">"                     
            self.result += bt
            self.open_tags.insert(0, tag)
            
    def handle_endtag(self, tag, attrs):
        bracketed = "</%s>" % tag
        if tag not in self.permitted_tags:
            self.result += xssescape(bracketed)
        elif tag in self.open_tags:
            self.result += bracketed
            self.open_tags.remove(tag)
            
    def unknown_starttag(self, tag, attributes):
        self.handle_starttag(tag, None, attributes)
    def unknown_endtag(self, tag):
        self.handle_endtag(tag, None)
    def url_is_acceptable(self,url):
        ### Requires all URLs to be "absolute."
        parsed = urlparse(url)
        return parsed[0] in self.allowed_schemes and '.' in parsed[1]
    def strip(self, rawstring):
        """Returns the argument stripped of potentially harmful HTML or Javascript code"""
        self.result = ""
        self.feed(rawstring)
        for endtag in self.open_tags:
            if endtag not in self.requires_no_close:
                self.result += "</%s>" % endtag
        return self.result
    def xtags(self):
        """Returns a printable string informing the user which tags are allowed"""
        self.permitted_tags.sort()
        tg = ""
        for x in self.permitted_tags:
            tg += "<" + x
            if x in self.allowed_attributes:
                for y in self.allowed_attributes[x]:
                    tg += ' %s=""' % y
            tg += "> "
        return xssescape(tg.strip())

########NEW FILE########
__FILENAME__ = update_account
# Copyright (C) 2011, CloudCaptive
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import cgi
import logging
import os
import wsgiref.handlers
import urllib
import webapp2
from google.appengine.api import urlfetch
from serverside import constants
from serverside import environment
from serverside.dao import passphrase_dao 
from serverside.dao import accounts_dao
from serverside.dao import users_dao
from serverside.dao import widgets_dao 
from google.appengine.api import taskqueue

def check_or_create_anonymous_user(acc_ref):
  """ Create an anonymous users if needed """
  return users_dao.get_or_create_user(acc_ref.key().name(), constants.ANONYMOUS_USER, acc_ref)

def has_milestone_widget(acc_ref):
  """ Adds a milestone widget if needed """
  widget = None
  try:
    widget = widgets_dao.get_widget_for_account(acc_ref, "Milestones")
  except:
    logging.error("Unable to get Milestone widget for account " + acc_ref.key().name() + " will have to create it")   
  if not widget:
    logging.error("No Milestone widget for account " + acc_ref.key().name() + " will have to create it")   
    widget = widgets_dao.add_milestones(acc_ref)
  return widget

def groom_account(email):
  """ 
      Check the account and make sure accounts are updated with newest 
      parameters, widgets, users, etc
  """
  acc = accounts_dao.get(email)
  if not acc:
    logging.error("Unable to locate account ref for " + str(email))
    return 

  if not check_or_create_anonymous_user(acc):
    logging.error("Unable to get/create anonymous user for " + str(email))
    return 

  if not has_milestone_widget(acc):
    logging.error("Unable to get/create milestone wildget for" + str(email))
    return 

class UpdateAccount(webapp2.RequestHandler):
  def post(self):
    email = self.request.get('email') 
    updatesecret = self.request.get('key') 
    official_update_secret = passphrase_dao.get_update_secret()    
    if updatesecret != official_update_secret:
      logging.error("Logging: Bad update secret: %s vs %s"%(updatesecret, official_update_secret))
      return
    groom_account(email)

app = webapp2.WSGIApplication([
  (constants.UPDATE.PATH, UpdateAccount)
], debug=constants.DEBUG)

def __url_async_post(url, argsdic):
  # This will not work on the dev server for GAE, dev server only uses
  # synchronous calls, unless the SDK is patched, or using AppScale
  #rpc = urlfetch.create_rpc(deadline=30)
  #urlfetch.make_fetch_call(rpc, url, payload=urllib.urlencode(argsdic), method=urlfetch.POST)
  taskqueue.add(url=url, params=argsdic)

def full_path(relative_url):
  if environment.is_dev():
    return constants.DEV_URL + constants.UPDATE.PATH
  else:
    return constants.PRODUCTION_URL + constants.UPDATE.PATH

def update_account(email):
  diction = {}
  diction['key'] = passphrase_dao.get_update_secret()    
  diction['email'] = email
  __url_async_post(constants.UPDATE.PATH, diction)

"""
def main():
  run_wsgi_app(application)

if __name__ == '__main__':
  main()
"""

########NEW FILE########
