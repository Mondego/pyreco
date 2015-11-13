__FILENAME__ = main
#!/usr/bin/env python
import os, datetime, re, simplejson
import urllib, base64, uuid

import wsgiref.handlers
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from google.appengine.api.urlfetch import *
from google.appengine.api import memcache
from google.appengine.api import *

import openradar.api
import openradar.db
from openradar.models import *
from openradar.handlers import *

class IndexAction(Handler):
  def get(self):
    self.redirect("/page/1")
    
class OldIndexAction(Handler):
  def get(self):      
    biglist = memcache.get("biglist")
    if biglist is None:
      radars = db.GqlQuery("select * from Radar order by number_intvalue desc").fetch(100)
      path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'biglist.html'))
      biglist = template.render(path, {'radars':radars})
      memcache.add("biglist", biglist, 3600) # one hour, but we also invalidate on edits and adds
    self.respondWithTemplate('index.html', {"biglist": biglist})

PAGESIZE = 40
PAGE_PATTERN = re.compile("/page/([0-9]+)")

class RadarListByPageAction(Handler):
  def get(self):  
    m = PAGE_PATTERN.match(self.request.path)
    if m:
      number = m.group(1) 
      if (int(number) > 1):
        showprev = int(number)-1
      else: 
        showprev = None
      shownext = int(number)+1
      pagename = "page" + number
      biglist = memcache.get(pagename)
      if biglist is None:
        radars = db.GqlQuery("select * from Radar order by number_intvalue desc").fetch(PAGESIZE,(int(number)-1)*PAGESIZE)
        if len(radars) > 0:
          path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'biglist.html'))
          biglist = template.render(path, {'radars':radars})
          memcache.add(pagename, biglist, 3600) # one hour, but we also invalidate on edits and adds
        else:
          biglist = "<p>That's all.</p>"
      self.respondWithTemplate('page.html', {'pagenumber':number, 'shownext':shownext, 'showprev':showprev, "biglist": biglist})
    else:
      self.respondWithText('invalid page request')

class FAQAction(Handler):
  def get(self):    
    self.respondWithTemplate('faq.html', {})

class RadarAddAction(Handler):
  def get(self):    
    user = self.GetCurrentUser()
    if (not user):
      self.respondWithTemplate('please-sign-in.html', {'action': 'add Radars'})
    else:
      self.respondWithTemplate('radar-add.html', {})
  def post(self):
    user = self.GetCurrentUser()
    if (not user):
      self.respondWithTemplate('please-sign-in.html', {'action': 'add Radars'})
    else:
      title = self.request.get("title")
      number = self.request.get("number")
      status = self.request.get("status")
      description = self.request.get("description")
      resolved = self.request.get("resolved")
      product = self.request.get("product")
      classification = self.request.get("classification")
      reproducible = self.request.get("reproducible")
      product_version = self.request.get("product_version")
      originated = self.request.get("originated")
      radar = Radar(title=title,
                    number=number,
                    number_intvalue=int(number),
                    status=status,
                    user=user,
                    description=description,
                    resolved=resolved,
                    product=product,
                    classification=classification,
                    reproducible=reproducible,
                    product_version=product_version,
                    originated=originated,
                    created=datetime.datetime.now(),
                    modified=datetime.datetime.now())
      radar.put()
      memcache.flush_all()
      # tweet this.
      if 1:
        #tweet = ("[rdar://%s] %s: %s" % (number, radar.username(), title))
        tweet = ("http://openradar.me/%s %s: %s" % (number, radar.username(), title))
        tweet = tweet[0:140]
        secrets = db.GqlQuery("select * from Secret where name = :1", "retweet").fetch(1)
        if len(secrets) > 0:
          secret = secrets[0].value
          form_fields = {
            "message": tweet,
            "secret": secret
          }
          form_data = urllib.urlencode(form_fields)
          try:
            result = fetch("http://sulfur.neontology.com/retweet.php", payload=form_data, method=POST)
          except Exception:
            None # let's not worry about downstream problems
      self.redirect("/myradars")

RADAR_PATTERN = re.compile("/([0-9]+)")
class RadarViewByPathAction(Handler):
  def get(self):    
    user = users.GetCurrentUser()
    if not user:
        page = memcache.get(self.request.path)
        if page:
            self.respondWithText(page)
            return
    m = RADAR_PATTERN.match(self.request.path)
    if m:
      bare = self.request.get("bare")
      number = m.group(1) 
      radars = Radar.gql("WHERE number = :1", number).fetch(1)
      if len(radars) != 1:
        self.respondWithTemplate('radar-missing.html', {"number":number})
        return
      radar = radars[0]
      if (not radar):
        self.respondWithTemplate('radar-missing.html', {"number":number})
      else:	
        path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'radar-view.html'))        
        page = template.render(path, {"mine":(user == radar.user), "radar":radar, "radars":radar.children(), "comments": radar.comments(), "bare":bare})
        if not user:	    
            memcache.add(self.request.path, page, 3600) # one hour, but we also invalidate on edits and adds
        self.respondWithText(page)
      return

class RadarViewByIdOrNumberAction(Handler):
  def get(self):
    user = users.GetCurrentUser()
    # we keep request-by-id in case there are problems with the radar number (accidental duplicates, for example)
    id = self.request.get("id")
    if id:
      radar = Radar.get_by_id(int(id))
      if (not radar):
        self.respondWithText('Invalid Radar id')
      else:
        self.respondWithTemplate('radar-view.html', {"mine":(user == radar.user), "radar":radar, "radars":radar.children(), "comments": radar.comments()})
      return
    number = self.request.get("number")
    if number:
      self.redirect("/"+number)
      return
    else:
      self.respondWithText('Please specify a Radar by number or openradar id')
    
class RadarEditAction(Handler):
  def get(self):    
    user = users.GetCurrentUser()
    if (not user):
      self.respondWithTemplate('please-sign-in.html', {'action': 'edit Radars'})
    else:
      id = self.request.get("id")
      radar = Radar.get_by_id(int(id))
      if (not radar):
        self.respondWithText('Invalid Radar id')
      else:
        self.respondWithTemplate('radar-edit.html', {"radar":radar})

  def post(self):
    user = users.GetCurrentUser()
    if (not user):
      self.respondWithTemplate('please-sign-in.html', {'action': 'edit Radars'})
    else:
      id = self.request.get("id")
      radar = Radar.get_by_id(int(id))
      if not radar:
        self.respondWithText('Invalid Radar id')
      elif radar.user != user:
        self.respondWithText('Only the owner of a Radar can edit it')
      else:
        radar.title = self.request.get("title")
        radar.number = self.request.get("number")
        radar.number_intvalue = int(self.request.get("number"))
        radar.status = self.request.get("status")
        radar.description = self.request.get("description")
        radar.resolved = self.request.get("resolved")
        radar.product = self.request.get("product")
        radar.classification = self.request.get("classification")
        radar.reproducible = self.request.get("reproducible")
        radar.product_version = self.request.get("product_version")
        radar.originated = self.request.get("originated")
        radar.modified = datetime.datetime.now()
        radar.put()
        memcache.flush_all()
        self.redirect("/myradars")
  
class RadarFixNumberAction(Handler): 
  def post(self):
    id = self.request.get("id")
    radar = Radar.get_by_id(int(id))
    if not radar:
      self.respondWithText('Invalid Radar id')
    else:
      radar.number_intvalue = int(radar.number)      
      radar.put()
      memcache.flush_all()
      self.respondWithText('OK')
     
class RadarDeleteAction(Handler):
  def get(self):
    user = users.GetCurrentUser()
    id = self.request.get("id")
    radar = Radar.get_by_id(int(id))
    if (not user):
      self.respondWithTemplate('please-sign-in.html', {'action': 'delete Radars'})
    elif (not radar):
      self.respondWithText('Invalid Radar id')
    else:
      radar.delete()
      memcache.flush_all()
      self.redirect("/myradars")

class RadarListAction(Handler):
  def get(self):    
    user = users.GetCurrentUser()
    if (not user):
      self.respondWithTemplate('please-sign-in.html', {'action': 'view your Radars'})
    else:
      radars = db.GqlQuery("select * from Radar where user = :1 order by number_intvalue desc", user).fetch(1000)
      self.respondWithTemplate('radar-list.html', {"radars": radars})

class NotFoundAction(Handler):
  def get(self):
    self.response.out.write("<h1>Resource not found</h1>")
    self.response.out.write("<pre>")
    self.response.out.write(self.request)
    self.response.out.write("</pre>")

class RefreshAction(Handler):
  def get(self):
    memcache.flush_all()
    self.redirect("/")

class HelloAction(Handler):
  def get(self):
    user = users.get_current_user()
    if not user:
      # The user is not signed in.
      print "Hello"
    else:
      print "Hello, %s!" % user.nickname()

class APIKeyAction(Handler):
  def get(self):    
    user = users.GetCurrentUser()
    if (not user):
      self.respondWithTemplate('please-sign-in.html', {'action': 'view or regenerate your API key'})
    else:
      apikey = openradar.db.APIKey().fetchByUser(user)
      if not apikey:
        apikey = APIKey(user=user,
                        apikey=str(uuid.uuid1()),
                        created=datetime.datetime.now())
        apikey.put()
      self.respondWithTemplate('api-key.html', {'apikey': apikey})
  def post(self):
    user = users.GetCurrentUser()
    if (not user):
      self.respondWithTemplate('please-sign-in.html', {'action': 'regenerate your API key'})
    else:
      apikey = openradar.db.APIKey().fetchByUser(user)
      if apikey:
        apikey.delete()      
      self.redirect("/apikey")
      
    
class APIRadarsAction(Handler):
  def get(self):
    page = self.request.get("page")
    if page:
      page = int(page)
    else:
      page = 1
    apiresult = memcache.get("apiresult")
    if apiresult is None:
      radars = db.GqlQuery("select * from Radar order by number_intvalue desc").fetch(100,(page-1)*100)
      response = {"result":
                  [{"id":r.key().id(),
                    "title":r.title, 
                    "number":r.number, 
                    "user":r.user.email(),
                    "status":r.status, 
                    "description":r.description,
                    "resolved":r.resolved,
                    "product":r.product,
                    "classification":r.classification,
                    "reproducible":r.reproducible,
                    "product_version":r.product_version,
                    "originated":r.originated}
                   for r in radars]}
      apiresult = simplejson.dumps(response)
      #memcache.add("apiresult", apiresult, 600) # ten minutes, but we also invalidate on edits and adds
    self.respondWithText(apiresult)

class APICommentsAction(Handler):
  def get(self):
    page = self.request.get("page")
    if page:
      page = int(page)
    else:
      page = 1
    comments = db.GqlQuery("select * from Comment order by posted_at desc").fetch(100,(page-1)*100)
    result = []
    for c in comments:
      try:
        result.append({"id":c.key().id(),
                       "user":c.user.email(),
                       "subject":c.subject,
                       "body":c.body,
                       "radar":c.radar.number,
                       "is_reply_to":c.is_reply_to and c.is_reply_to.key().id() or ""})  
      except Exception:
        None
    response = {"result":result}
    apiresult = simplejson.dumps(response)
    self.respondWithText(apiresult)
    
class APIRadarsNumbersAction(Handler):
  def get(self):
    page = self.request.get("page")
    if page:
      page = int(page)
    else:
      page = 1
    apiresult = memcache.get("apiresult")
    if apiresult is None:
      radars = db.GqlQuery("select * from Radar order by number_intvalue desc").fetch(100,(page-1)*100)
      response = {"result":[r.number for r in radars]}
      apiresult = simplejson.dumps(response)
    self.respondWithText(apiresult)
      
class APIRadarsIDsAction(Handler):
  def get(self):
    page = self.request.get("page")
    if page:
      page = int(page)
    else:
      page = 1
    apiresult = memcache.get("apiresult")
    if apiresult is None:
      radars = db.GqlQuery("select * from Radar order by number desc").fetch(100,(page-1)*100)
      response = {"result":[r.key().id() for r in radars]}
      apiresult = simplejson.dumps(response)
    self.respondWithText(apiresult)
      
class APIAddRadarAction(Handler):
  def post(self):
    user = self.GetCurrentUser()
    if (not user):
      self.respondWithDictionaryAsJSON({"error":"you must authenticate to add radars"})
    else:
      title = self.request.get("title")
      number = self.request.get("number")
      status = self.request.get("status")
      description = self.request.get("description")
      resolved = self.request.get("resolved")
      product = self.request.get("product")
      classification = self.request.get("classification")
      reproducible = self.request.get("reproducible")
      product_version = self.request.get("product_version")
      originated = self.request.get("originated")
      radar = Radar(title=title,
                    number=number,
                    number_intvalue=int(number),
                    user=user,
                    status=status,
                    description=description,
                    resolved=resolved,
                    product=product,
                    classification=classification,
                    reproducible=reproducible,
                    product_version=product_version,
                    originated=originated,
                    created=datetime.datetime.now(),
                    modified=datetime.datetime.now())
      radar.put()
      memcache.flush_all()
      response = {"result":
                   {"title":title, 
                    "number":number, 
                    "status":status, 
                    "description":description}}
      self.respondWithDictionaryAsJSON(response)

class APISecretAction(Handler):
  def get(self):
    name = self.request.get("name")
    value = self.request.get("value")
    secret = Secret(name=name, value=value)
    secret.put()
    self.respondWithDictionaryAsJSON({"name":name, "value":value})


class CommentsAJAXFormAction(Handler):
  def _check(self):
    user = users.GetCurrentUser()
    if (not user):
      self.error(401)
      self.respondWithText("You must login to post a comment")
      return False, False, False
    
    radarKey = self.request.get("radar")
    radar = Radar.get(radarKey)
    
    if(not radar):
      self.error(400)
      self.respondWithText("Unknown radar key")
      return False, False, False
      
    
    replyKey = self.request.get("is_reply_to")
    replyTo = None
    if(replyKey):
      replyTo = Comment.get(replyKey)
    
    return user, radar, replyTo
    
  def get(self):
    
    # Edit
    commentKey = self.request.get("key")
    if(commentKey):
      comment = Comment.get(commentKey)
      if(not comment):
        self.error(400)
        self.respondWithText("Tried to edit a post that doesn't exist? Couldn't find post to edit.")
        return
      self.respondWithText(comment.form())
      return
      
    # New or reply
    user, radar, replyTo = self._check()
    if(not user): return
    
    args = {"radar": radar}
    
    if(replyTo):
      args["is_reply_to"] = replyTo
    
    self.respondWithText(Comment(**args).form())
    
    
  def post(self):
    user, radar, replyTo = self._check()
    if(not user): return
    
    commentKey = self.request.get("key")
    comment = None
    if(commentKey):
      comment = Comment.get(commentKey)
      if(not comment):
        self.error(400)
        self.respondWithText("Tried to edit a post that doesn't exist? Couldn't find post to edit.")
        return
    else:
      comment = Comment(user = user, radar = radar)
    
    if(not self.request.get("cancel")):
      comment.is_reply_to = replyTo
      comment.subject = self.request.get("subject")
      comment.body = self.request.get("body")
    comment.put()

    self.respondWithText(comment.draw(commentKey != ""))
    
class CommentsAJAXRemoveAction(Handler):
  def post(self):
    user = users.GetCurrentUser()
    if (not user):
      self.error(401)
      self.respondWithText("You must login to remove a comment")
      return
    
    commentKey = self.request.get("key")
    comment = Comment.get(commentKey)
    if(not comment):
      self.error(400)
      self.respondWithText("Tried to remove a post that doesn't exist? Couldn't find post to remove.")
      return
    
    if(not comment.editable_by_current_user()):
      self.error(401)
      self.respondWithText("You must be the comment's owner, or an admin, to remove this comment.")
      return
    
    if(comment.deleteOrBlank() == "blanked"):
      self.respondWithText(comment.html_body())
    else:
      self.respondWithText("REMOVED")
    
class CommentsRecentAction(Handler):
  def get(self):
    comments = db.GqlQuery("select * from Comment order by posted_at desc").fetch(20)
    self.respondWithTemplate('comments-recent.html', {"comments": comments})

class RadarsByUserAction(Handler):
  def get(self):
    username = self.request.get("user")
    user = users.User(username)
    if user:
      query = db.GqlQuery("select * from Radar where user = :1 order by number_intvalue desc", user)
      radars = query.fetch(100)
      if len(radars) == 0:
        searchlist = '<p>No matching results found.</p>'
      else:
        path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'biglist.html'))
        searchlist = template.render(path, {'radars':radars})
      self.respondWithTemplate('byuser.html', {"radarlist": searchlist})
    else:
      self.respondWithText('unknown user')

class SearchAction(Handler):
  def get(self):
    querystring = self.request.get("query")
    keywords = querystring.split(" ")
    keyword = keywords[0]
    try:
      query = Radar.all().search(keyword).order("-number")
      radars = query.fetch(100)
    except Exception:
      self.respondWithTemplate('search.html', {"query":keyword, "searchlist":"<p>No matching results found.</p>"})
      return
    if len(radars) == 0:
      searchlist = '<p>No matching results found.</p>'
    else:
      path = os.path.join(os.path.dirname(__file__), os.path.join('templates', 'biglist.html'))
      searchlist = template.render(path, {'radars':radars})
    self.respondWithTemplate('search.html', {"query":keyword, "searchlist": searchlist})

class RePutAction(Handler):
  def get(self):
    offset = self.request.get("offset")
    if offset:
      offset = int(offset)
    else:
      offset = 0
    radars = Radar.all().fetch(50,offset)
    for radar in radars:
      radar.put()
    self.respondWithText("done")

class LoginAction(webapp.RequestHandler):
  def get(self):
    self.response.out.write(users.create_login_url("/"))

def main():
  application = webapp.WSGIApplication([
    ('/', IndexAction),
    ('/[0-9]+', RadarViewByPathAction),
    ('/api/comment', openradar.api.Comment),
    ('/api/comment/count', openradar.api.CommentCount),
    ('/api/comments', APICommentsAction),
    ('/api/radar', openradar.api.Radar),
    ('/api/radar/count', openradar.api.RadarCount),
    ('/api/radars', APIRadarsAction),
    ('/api/radars/add', APIAddRadarAction),
    ('/api/radars/numbers', APIRadarsNumbersAction),
    ('/api/radars/ids', APIRadarsIDsAction),
    ('/api/search', openradar.api.Search),
    ('/api/test', openradar.api.Test),
    ('/api/test_authentication', openradar.api.TestAuthentication),
    ('/comment', CommentsAJAXFormAction),
    ('/comment/remove', CommentsAJAXRemoveAction),
    ('/comments', CommentsRecentAction),
    ('/faq', FAQAction),
    ('/hello', HelloAction),
    ('/loginurl', LoginAction),
    ('/myradars', RadarListAction),
    ('/myradars/add', RadarAddAction),
    ('/myradars/edit', RadarEditAction),
    ('/myradars/delete', RadarDeleteAction),
    ('/page/[0-9]+', RadarListByPageAction),
    ('/radar', RadarViewByIdOrNumberAction),
    ('/radarsby', RadarsByUserAction),
    ('/rdar', RadarViewByIdOrNumberAction),
    ('/refresh', RefreshAction),
    ('/search', SearchAction),
    ('/fixnumber', RadarFixNumberAction),
    ('/apikey', APIKeyAction),
    # intentially disabled 
    # ('/api/secret', APISecretAction),
    # ('/reput', RePutAction),
    ('.*', NotFoundAction)
  ], debug=True)
  wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = markdown
#!/usr/bin/env python

version = "1.7"
version_info = (1,7,0,"rc-2")
__revision__ = "$Rev: 72 $"

"""
Python-Markdown
===============

Converts Markdown to HTML.  Basic usage as a module:

    import markdown
    md = Markdown()
    html = md.convert(your_text_string)

See http://www.freewisdom.org/projects/python-markdown/ for more
information and instructions on how to extend the functionality of the
script.  (You might want to read that before you try modifying this
file.)

Started by [Manfred Stienstra](http://www.dwerg.net/).  Continued and
maintained  by [Yuri Takhteyev](http://www.freewisdom.org) and [Waylan
Limberg](http://achinghead.com/).

Contact: yuri [at] freewisdom.org
         waylan [at] gmail.com

License: GPL 2 (http://www.gnu.org/copyleft/gpl.html) or BSD

"""


import re, sys, codecs

from logging import getLogger, StreamHandler, Formatter, \
                    DEBUG, INFO, WARN, ERROR, CRITICAL


MESSAGE_THRESHOLD = CRITICAL


# Configure debug message logger (the hard way - to support python 2.3)
logger = getLogger('MARKDOWN')
logger.setLevel(DEBUG) # This is restricted by handlers later
console_hndlr = StreamHandler()
formatter = Formatter('%(name)s-%(levelname)s: "%(message)s"')
console_hndlr.setFormatter(formatter)
console_hndlr.setLevel(MESSAGE_THRESHOLD)
logger.addHandler(console_hndlr)


def message(level, text):
    ''' A wrapper method for logging debug messages. '''
    logger.log(level, text)


# --------------- CONSTANTS YOU MIGHT WANT TO MODIFY -----------------

TAB_LENGTH = 4            # expand tabs to this many spaces
ENABLE_ATTRIBUTES = True  # @id = xyz -> <... id="xyz">
SMART_EMPHASIS = 1        # this_or_that does not become this<i>or</i>that
HTML_REMOVED_TEXT = "[HTML_REMOVED]" # text used instead of HTML in safe mode

RTL_BIDI_RANGES = ( (u'\u0590', u'\u07FF'),
                    # from Hebrew to Nko (includes Arabic, Syriac and Thaana)
                    (u'\u2D30', u'\u2D7F'),
                    # Tifinagh
                    )

# Unicode Reference Table:
# 0590-05FF - Hebrew
# 0600-06FF - Arabic
# 0700-074F - Syriac
# 0750-077F - Arabic Supplement
# 0780-07BF - Thaana
# 07C0-07FF - Nko

BOMS = { 'utf-8': (codecs.BOM_UTF8, ),
         'utf-16': (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE),
         #'utf-32': (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)
         }

def removeBOM(text, encoding):
    convert = isinstance(text, unicode)
    for bom in BOMS[encoding]:
        bom = convert and bom.decode(encoding) or bom
        if text.startswith(bom):
            return text.lstrip(bom)
    return text

# The following constant specifies the name used in the usage
# statement displayed for python versions lower than 2.3.  (With
# python2.3 and higher the usage statement is generated by optparse
# and uses the actual name of the executable called.)

EXECUTABLE_NAME_FOR_USAGE = "python markdown.py"
                    

# --------------- CONSTANTS YOU _SHOULD NOT_ HAVE TO CHANGE ----------

# a template for html placeholders
HTML_PLACEHOLDER_PREFIX = "qaodmasdkwaspemas"
HTML_PLACEHOLDER = HTML_PLACEHOLDER_PREFIX + "%dajkqlsmdqpakldnzsdfls"

BLOCK_LEVEL_ELEMENTS = ['p', 'div', 'blockquote', 'pre', 'table',
                        'dl', 'ol', 'ul', 'script', 'noscript',
                        'form', 'fieldset', 'iframe', 'math', 'ins',
                        'del', 'hr', 'hr/', 'style']

def isBlockLevel (tag):
    return ( (tag in BLOCK_LEVEL_ELEMENTS) or
             (tag[0] == 'h' and tag[1] in "0123456789") )

"""
======================================================================
========================== NANODOM ===================================
======================================================================

The three classes below implement some of the most basic DOM
methods.  I use this instead of minidom because I need a simpler
functionality and do not want to require additional libraries.

Importantly, NanoDom does not do normalization, which is what we
want. It also adds extra white space when converting DOM to string
"""

ENTITY_NORMALIZATION_EXPRESSIONS = [ (re.compile("&"), "&amp;"),
                                     (re.compile("<"), "&lt;"),
                                     (re.compile(">"), "&gt;")]

ENTITY_NORMALIZATION_EXPRESSIONS_SOFT = [ (re.compile("&(?!\#)"), "&amp;"),
                                     (re.compile("<"), "&lt;"),
                                     (re.compile(">"), "&gt;"),
                                     (re.compile("\""), "&quot;")]


def getBidiType(text):

    if not text: return None

    ch = text[0]

    if not isinstance(ch, unicode) or not ch.isalpha():
        return None

    else:

        for min, max in RTL_BIDI_RANGES:
            if ( ch >= min and ch <= max ):
                return "rtl"
        else:
            return "ltr"


class Document:

    def __init__ (self):
        self.bidi = "ltr"

    def appendChild(self, child):
        self.documentElement = child
        child.isDocumentElement = True
        child.parent = self
        self.entities = {}

    def setBidi(self, bidi):
        if bidi:
            self.bidi = bidi

    def createElement(self, tag, textNode=None):
        el = Element(tag)
        el.doc = self
        if textNode:
            el.appendChild(self.createTextNode(textNode))
        return el

    def createTextNode(self, text):
        node = TextNode(text)
        node.doc = self
        return node

    def createEntityReference(self, entity):
        if entity not in self.entities:
            self.entities[entity] = EntityReference(entity)
        return self.entities[entity]

    def createCDATA(self, text):
        node = CDATA(text)
        node.doc = self
        return node

    def toxml (self):
        return self.documentElement.toxml()

    def normalizeEntities(self, text, avoidDoubleNormalizing=False):

        if avoidDoubleNormalizing:
            regexps = ENTITY_NORMALIZATION_EXPRESSIONS_SOFT
        else:
            regexps = ENTITY_NORMALIZATION_EXPRESSIONS

        for regexp, substitution in regexps:
            text = regexp.sub(substitution, text)
        return text

    def find(self, test):
        return self.documentElement.find(test)

    def unlink(self):
        self.documentElement.unlink()
        self.documentElement = None


class CDATA:

    type = "cdata"

    def __init__ (self, text):
        self.text = text

    def handleAttributes(self):
        pass

    def toxml (self):
        return "<![CDATA[" + self.text + "]]>"

class Element:

    type = "element"

    def __init__ (self, tag):

        self.nodeName = tag
        self.attributes = []
        self.attribute_values = {}
        self.childNodes = []
        self.bidi = None
        self.isDocumentElement = False

    def setBidi(self, bidi):

        if bidi:

            orig_bidi = self.bidi

            if not self.bidi or self.isDocumentElement:
                # Once the bidi is set don't change it (except for doc element)
                self.bidi = bidi
                self.parent.setBidi(bidi)


    def unlink(self):
        for child in self.childNodes:
            if child.type == "element":
                child.unlink()
        self.childNodes = None

    def setAttribute(self, attr, value):
        if not attr in self.attributes:
            self.attributes.append(attr)

        self.attribute_values[attr] = value

    def insertChild(self, position, child):
        self.childNodes.insert(position, child)
        child.parent = self

    def removeChild(self, child):
        self.childNodes.remove(child)

    def replaceChild(self, oldChild, newChild):
        position = self.childNodes.index(oldChild)
        self.removeChild(oldChild)
        self.insertChild(position, newChild)

    def appendChild(self, child):
        self.childNodes.append(child)
        child.parent = self

    def handleAttributes(self):
        pass

    def find(self, test, depth=0):
        """ Returns a list of descendants that pass the test function """
        matched_nodes = []
        for child in self.childNodes:
            if test(child):
                matched_nodes.append(child)
            if child.type == "element":
                matched_nodes += child.find(test, depth+1)
        return matched_nodes

    def toxml(self):
        if ENABLE_ATTRIBUTES:
            for child in self.childNodes:
                child.handleAttributes()

        buffer = ""
        if self.nodeName in ['h1', 'h2', 'h3', 'h4']:
            buffer += "\n"
        elif self.nodeName in ['li']:
            buffer += "\n "

        # Process children FIRST, then do the attributes

        childBuffer = ""

        if self.childNodes or self.nodeName in ['blockquote']:
            childBuffer += ">"
            for child in self.childNodes:
                childBuffer += child.toxml()
            if self.nodeName == 'p':
                childBuffer += "\n"
            elif self.nodeName == 'li':
                childBuffer += "\n "
            childBuffer += "</%s>" % self.nodeName
        else:
            childBuffer += "/>"


            
        buffer += "<" + self.nodeName

        if self.nodeName in ['p', 'li', 'ul', 'ol',
                             'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:

            if not self.attribute_values.has_key("dir"):
                if self.bidi:
                    bidi = self.bidi
                else:
                    bidi = self.doc.bidi
                    
                if bidi=="rtl":
                    self.setAttribute("dir", "rtl")
        
        for attr in self.attributes:
            value = self.attribute_values[attr]
            value = self.doc.normalizeEntities(value,
                                               avoidDoubleNormalizing=True)
            buffer += ' %s="%s"' % (attr, value)


        # Now let's actually append the children

        buffer += childBuffer

        if self.nodeName in ['p', 'br ', 'li', 'ul', 'ol',
                             'h1', 'h2', 'h3', 'h4'] :
            buffer += "\n"

        return buffer


class TextNode:

    type = "text"
    attrRegExp = re.compile(r'\{@([^\}]*)=([^\}]*)}') # {@id=123}

    def __init__ (self, text):
        self.value = text        

    def attributeCallback(self, match):

        self.parent.setAttribute(match.group(1), match.group(2))

    def handleAttributes(self):
        self.value = self.attrRegExp.sub(self.attributeCallback, self.value)

    def toxml(self):

        text = self.value

        self.parent.setBidi(getBidiType(text))
        
        if not text.startswith(HTML_PLACEHOLDER_PREFIX):
            if self.parent.nodeName == "p":
                text = text.replace("\n", "\n   ")
            elif (self.parent.nodeName == "li"
                  and self.parent.childNodes[0]==self):
                text = "\n     " + text.replace("\n", "\n     ")
        text = self.doc.normalizeEntities(text)
        return text


class EntityReference:

    type = "entity_ref"

    def __init__(self, entity):
        self.entity = entity

    def handleAttributes(self):
        pass

    def toxml(self):
        return "&" + self.entity + ";"


"""
======================================================================
========================== PRE-PROCESSORS ============================
======================================================================

Preprocessors munge source text before we start doing anything too
complicated.

There are two types of preprocessors: TextPreprocessor and Preprocessor.

"""


class TextPreprocessor:
    '''
    TextPreprocessors are run before the text is broken into lines.
    
    Each TextPreprocessor implements a "run" method that takes a pointer to a
    text string of the document, modifies it as necessary and returns
    either the same pointer or a pointer to a new string.  
    
    TextPreprocessors must extend markdown.TextPreprocessor.
    '''

    def run(self, text):
        pass


class Preprocessor:
    '''
    Preprocessors are run after the text is broken into lines.

    Each preprocessor implements a "run" method that takes a pointer to a
    list of lines of the document, modifies it as necessary and returns
    either the same pointer or a pointer to a new list.  
    
    Preprocessors must extend markdown.Preprocessor.
    '''

    def run(self, lines):
        pass
 

class HtmlBlockPreprocessor(TextPreprocessor):
    """Removes html blocks from the source text and stores it."""
    
    def _get_left_tag(self, block):
        return block[1:].replace(">", " ", 1).split()[0].lower()


    def _get_right_tag(self, left_tag, block):
        return block.rstrip()[-len(left_tag)-2:-1].lower()

    def _equal_tags(self, left_tag, right_tag):
        
        if left_tag == 'div' or left_tag[0] in ['?', '@', '%']: # handle PHP, etc.
            return True
        if ("/" + left_tag) == right_tag:
            return True
        if (right_tag == "--" and left_tag == "--"):
            return True
        elif left_tag == right_tag[1:] \
            and right_tag[0] != "<":
            return True
        else:
            return False

    def _is_oneliner(self, tag):
        return (tag in ['hr', 'hr/'])

    
    def run(self, text):

        new_blocks = []
        text = text.split("\n\n")
        
        items = []
        left_tag = ''
        right_tag = ''
        in_tag = False # flag
        
        for block in text:
            if block.startswith("\n"):
                block = block[1:]

            if not in_tag:

                if block.startswith("<"):
                    
                    left_tag = self._get_left_tag(block)
                    right_tag = self._get_right_tag(left_tag, block)

                    if not (isBlockLevel(left_tag) \
                        or block[1] in ["!", "?", "@", "%"]):
                        new_blocks.append(block)
                        continue

                    if self._is_oneliner(left_tag):
                        new_blocks.append(block.strip())
                        continue
                        
                    if block[1] == "!":
                        # is a comment block
                        left_tag = "--"
                        right_tag = self._get_right_tag(left_tag, block)
                        # keep checking conditions below and maybe just append
                        
                    if block.rstrip().endswith(">") \
                        and self._equal_tags(left_tag, right_tag):
                        new_blocks.append(
                            self.stash.store(block.strip()))
                        continue
                    else: #if not block[1] == "!":
                        # if is block level tag and is not complete
                        items.append(block.strip())
                        in_tag = True
                        continue

                new_blocks.append(block)

            else:
                items.append(block.strip())
                
                right_tag = self._get_right_tag(left_tag, block)
                
                if self._equal_tags(left_tag, right_tag):
                    # if find closing tag
                    in_tag = False
                    new_blocks.append(
                        self.stash.store('\n\n'.join(items)))
                    items = []

        if items:
            new_blocks.append(self.stash.store('\n\n'.join(items)))
            new_blocks.append('\n')
            
        return "\n\n".join(new_blocks)

HTML_BLOCK_PREPROCESSOR = HtmlBlockPreprocessor()


class HeaderPreprocessor(Preprocessor):

    """
       Replaces underlined headers with hashed headers to avoid
       the nead for lookahead later.
    """

    def run (self, lines):

        i = -1
        while i+1 < len(lines):
            i = i+1
            if not lines[i].strip():
                continue

            if lines[i].startswith("#"):
                lines.insert(i+1, "\n")

            if (i+1 <= len(lines)
                  and lines[i+1]
                  and lines[i+1][0] in ['-', '=']):

                underline = lines[i+1].strip()

                if underline == "="*len(underline):
                    lines[i] = "# " + lines[i].strip()
                    lines[i+1] = ""
                elif underline == "-"*len(underline):
                    lines[i] = "## " + lines[i].strip()
                    lines[i+1] = ""

        return lines

HEADER_PREPROCESSOR = HeaderPreprocessor()


class LinePreprocessor(Preprocessor):
    """Deals with HR lines (needs to be done before processing lists)"""

    blockquote_re = re.compile(r'^(> )+')

    def run (self, lines):
        for i in range(len(lines)):
            prefix = ''
            m = self.blockquote_re.search(lines[i])
            if m : prefix = m.group(0)
            if self._isLine(lines[i][len(prefix):]):
                lines[i] = prefix + self.stash.store("<hr />", safe=True)
        return lines

    def _isLine(self, block):
        """Determines if a block should be replaced with an <HR>"""
        if block.startswith("    "): return 0  # a code block
        text = "".join([x for x in block if not x.isspace()])
        if len(text) <= 2:
            return 0
        for pattern in ['isline1', 'isline2', 'isline3']:
            m = RE.regExp[pattern].match(text)
            if (m and m.group(1)):
                return 1
        else:
            return 0

LINE_PREPROCESSOR = LinePreprocessor()


class ReferencePreprocessor(Preprocessor):
    ''' 
    Removes reference definitions from the text and stores them for later use.
    '''

    def run (self, lines):

        new_text = [];
        for line in lines:
            m = RE.regExp['reference-def'].match(line)
            if m:
                id = m.group(2).strip().lower()
                t = m.group(4).strip()  # potential title
                if not t:
                    self.references[id] = (m.group(3), t)
                elif (len(t) >= 2
                      and (t[0] == t[-1] == "\""
                           or t[0] == t[-1] == "\'"
                           or (t[0] == "(" and t[-1] == ")") ) ):
                    self.references[id] = (m.group(3), t[1:-1])
                else:
                    new_text.append(line)
            else:
                new_text.append(line)

        return new_text #+ "\n"

REFERENCE_PREPROCESSOR = ReferencePreprocessor()

"""
======================================================================
========================== INLINE PATTERNS ===========================
======================================================================

Inline patterns such as *emphasis* are handled by means of auxiliary
objects, one per pattern.  Pattern objects must be instances of classes
that extend markdown.Pattern.  Each pattern object uses a single regular
expression and needs support the following methods:

  pattern.getCompiledRegExp() - returns a regular expression

  pattern.handleMatch(m, doc) - takes a match object and returns
                                a NanoDom node (as a part of the provided
                                doc) or None

All of python markdown's built-in patterns subclass from Patter,
but you can add additional patterns that don't.

Also note that all the regular expressions used by inline must
capture the whole block.  For this reason, they all start with
'^(.*)' and end with '(.*)!'.  In case with built-in expression
Pattern takes care of adding the "^(.*)" and "(.*)!".

Finally, the order in which regular expressions are applied is very
important - e.g. if we first replace http://.../ links with <a> tags
and _then_ try to replace inline html, we would end up with a mess.
So, we apply the expressions in the following order:

       * escape and backticks have to go before everything else, so
         that we can preempt any markdown patterns by escaping them.

       * then we handle auto-links (must be done before inline html)

       * then we handle inline HTML.  At this point we will simply
         replace all inline HTML strings with a placeholder and add
         the actual HTML to a hash.

       * then inline images (must be done before links)

       * then bracketed links, first regular then reference-style

       * finally we apply strong and emphasis
"""

NOBRACKET = r'[^\]\[]*'
BRK = ( r'\[('
        + (NOBRACKET + r'(\[')*6
        + (NOBRACKET+ r'\])*')*6
        + NOBRACKET + r')\]' )
NOIMG = r'(?<!\!)'

BACKTICK_RE = r'\`([^\`]*)\`'                    # `e= m*c^2`
DOUBLE_BACKTICK_RE =  r'\`\`(.*)\`\`'            # ``e=f("`")``
ESCAPE_RE = r'\\(.)'                             # \<
EMPHASIS_RE = r'\*([^\*]*)\*'                    # *emphasis*
STRONG_RE = r'\*\*(.*)\*\*'                      # **strong**
STRONG_EM_RE = r'\*\*\*([^_]*)\*\*\*'            # ***strong***

if SMART_EMPHASIS:
    EMPHASIS_2_RE = r'(?<!\S)_(\S[^_]*)_'        # _emphasis_
else:
    EMPHASIS_2_RE = r'_([^_]*)_'                 # _emphasis_

STRONG_2_RE = r'__([^_]*)__'                     # __strong__
STRONG_EM_2_RE = r'___([^_]*)___'                # ___strong___

LINK_RE = NOIMG + BRK + r'\s*\(([^\)]*)\)'               # [text](url)
LINK_ANGLED_RE = NOIMG + BRK + r'\s*\(<([^\)]*)>\)'      # [text](<url>)
IMAGE_LINK_RE = r'\!' + BRK + r'\s*\(([^\)]*)\)' # ![alttxt](http://x.com/)
REFERENCE_RE = NOIMG + BRK+ r'\s*\[([^\]]*)\]'           # [Google][3]
IMAGE_REFERENCE_RE = r'\!' + BRK + '\s*\[([^\]]*)\]' # ![alt text][2]
NOT_STRONG_RE = r'( \* )'                        # stand-alone * or _
AUTOLINK_RE = r'<(http://[^>]*)>'                # <http://www.123.com>
AUTOMAIL_RE = r'<([^> \!]*@[^> ]*)>'               # <me@example.com>
#HTML_RE = r'(\<[^\>]*\>)'                        # <...>
HTML_RE = r'(\<[a-zA-Z/][^\>]*\>)'               # <...>
ENTITY_RE = r'(&[\#a-zA-Z0-9]*;)'                # &amp;
LINE_BREAK_RE = r'  \n'                     # two spaces at end of line
LINE_BREAK_2_RE = r'  $'                    # two spaces at end of text

class Pattern:

    def __init__ (self, pattern):
        self.pattern = pattern
        self.compiled_re = re.compile("^(.*)%s(.*)$" % pattern, re.DOTALL)

    def getCompiledRegExp (self):
        return self.compiled_re

BasePattern = Pattern # for backward compatibility

class SimpleTextPattern (Pattern):

    def handleMatch(self, m, doc):
        return doc.createTextNode(m.group(2))

class SimpleTagPattern (Pattern):

    def __init__ (self, pattern, tag):
        Pattern.__init__(self, pattern)
        self.tag = tag

    def handleMatch(self, m, doc):
        el = doc.createElement(self.tag)
        el.appendChild(doc.createTextNode(m.group(2)))
        return el

class SubstituteTagPattern (SimpleTagPattern):

    def handleMatch (self, m, doc):
        return doc.createElement(self.tag)

class BacktickPattern (Pattern):

    def __init__ (self, pattern):
        Pattern.__init__(self, pattern)
        self.tag = "code"

    def handleMatch(self, m, doc):
        el = doc.createElement(self.tag)
        text = m.group(2).strip()
        #text = text.replace("&", "&amp;")
        el.appendChild(doc.createTextNode(text))
        return el


class DoubleTagPattern (SimpleTagPattern): 

    def handleMatch(self, m, doc):
        tag1, tag2 = self.tag.split(",")
        el1 = doc.createElement(tag1)
        el2 = doc.createElement(tag2)
        el1.appendChild(el2)
        el2.appendChild(doc.createTextNode(m.group(2)))
        return el1


class HtmlPattern (Pattern):

    def handleMatch (self, m, doc):
        rawhtml = m.group(2)
        inline = True
        place_holder = self.stash.store(rawhtml)
        return doc.createTextNode(place_holder)


class LinkPattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('a')
        el.appendChild(doc.createTextNode(m.group(2)))
        parts = m.group(9).split('"')
        # We should now have [], [href], or [href, title]
        if parts:
            el.setAttribute('href', parts[0].strip())
        else:
            el.setAttribute('href', "")
        if len(parts) > 1:
            # we also got a title
            title = '"' + '"'.join(parts[1:]).strip()
            title = dequote(title) #.replace('"', "&quot;")
            el.setAttribute('title', title)
        return el


class ImagePattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('img')
        src_parts = m.group(9).split()
        if src_parts:
            el.setAttribute('src', src_parts[0])
        else:
            el.setAttribute('src', "")
        if len(src_parts) > 1:
            el.setAttribute('title', dequote(" ".join(src_parts[1:])))
        if ENABLE_ATTRIBUTES:
            text = doc.createTextNode(m.group(2))
            el.appendChild(text)
            text.handleAttributes()
            truealt = text.value
            el.childNodes.remove(text)
        else:
            truealt = m.group(2)
        el.setAttribute('alt', truealt)
        return el

class ReferencePattern (Pattern):

    def handleMatch(self, m, doc):

        if m.group(9):
            id = m.group(9).lower()
        else:
            # if we got something like "[Google][]"
            # we'll use "google" as the id
            id = m.group(2).lower()

        if not self.references.has_key(id): # ignore undefined refs
            return None
        href, title = self.references[id]
        text = m.group(2)
        return self.makeTag(href, title, text, doc)

    def makeTag(self, href, title, text, doc):
        el = doc.createElement('a')
        el.setAttribute('href', href)
        if title:
            el.setAttribute('title', title)
        el.appendChild(doc.createTextNode(text))
        return el


class ImageReferencePattern (ReferencePattern):

    def makeTag(self, href, title, text, doc):
        el = doc.createElement('img')
        el.setAttribute('src', href)
        if title:
            el.setAttribute('title', title)
        el.setAttribute('alt', text)
        return el


class AutolinkPattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('a')
        el.setAttribute('href', m.group(2))
        el.appendChild(doc.createTextNode(m.group(2)))
        return el

class AutomailPattern (Pattern):

    def handleMatch(self, m, doc):
        el = doc.createElement('a')
        email = m.group(2)
        if email.startswith("mailto:"):
            email = email[len("mailto:"):]
        for letter in email:
            entity = doc.createEntityReference("#%d" % ord(letter))
            el.appendChild(entity)
        mailto = "mailto:" + email
        mailto = "".join(['&#%d;' % ord(letter) for letter in mailto])
        el.setAttribute('href', mailto)
        return el

ESCAPE_PATTERN          = SimpleTextPattern(ESCAPE_RE)
NOT_STRONG_PATTERN      = SimpleTextPattern(NOT_STRONG_RE)

BACKTICK_PATTERN        = BacktickPattern(BACKTICK_RE)
DOUBLE_BACKTICK_PATTERN = BacktickPattern(DOUBLE_BACKTICK_RE)
STRONG_PATTERN          = SimpleTagPattern(STRONG_RE, 'strong')
STRONG_PATTERN_2        = SimpleTagPattern(STRONG_2_RE, 'strong')
EMPHASIS_PATTERN        = SimpleTagPattern(EMPHASIS_RE, 'em')
EMPHASIS_PATTERN_2      = SimpleTagPattern(EMPHASIS_2_RE, 'em')

STRONG_EM_PATTERN       = DoubleTagPattern(STRONG_EM_RE, 'strong,em')
STRONG_EM_PATTERN_2     = DoubleTagPattern(STRONG_EM_2_RE, 'strong,em')

LINE_BREAK_PATTERN      = SubstituteTagPattern(LINE_BREAK_RE, 'br ')
LINE_BREAK_PATTERN_2    = SubstituteTagPattern(LINE_BREAK_2_RE, 'br ')

LINK_PATTERN            = LinkPattern(LINK_RE)
LINK_ANGLED_PATTERN     = LinkPattern(LINK_ANGLED_RE)
IMAGE_LINK_PATTERN      = ImagePattern(IMAGE_LINK_RE)
IMAGE_REFERENCE_PATTERN = ImageReferencePattern(IMAGE_REFERENCE_RE)
REFERENCE_PATTERN       = ReferencePattern(REFERENCE_RE)

HTML_PATTERN            = HtmlPattern(HTML_RE)
ENTITY_PATTERN          = HtmlPattern(ENTITY_RE)

AUTOLINK_PATTERN        = AutolinkPattern(AUTOLINK_RE)
AUTOMAIL_PATTERN        = AutomailPattern(AUTOMAIL_RE)


"""
======================================================================
========================== POST-PROCESSORS ===========================
======================================================================

Markdown also allows post-processors, which are similar to
preprocessors in that they need to implement a "run" method. However,
they are run after core processing.

There are two types of post-processors: Postprocessor and TextPostprocessor
"""


class Postprocessor:
    '''
    Postprocessors are run before the dom it converted back into text.
    
    Each Postprocessor implements a "run" method that takes a pointer to a
    NanoDom document, modifies it as necessary and returns a NanoDom 
    document.
    
    Postprocessors must extend markdown.Postprocessor.

    There are currently no standard post-processors, but the footnote
    extension uses one.
    '''

    def run(self, dom):
        pass



class TextPostprocessor:
    '''
    TextPostprocessors are run after the dom it converted back into text.
    
    Each TextPostprocessor implements a "run" method that takes a pointer to a
    text string, modifies it as necessary and returns a text string.
    
    TextPostprocessors must extend markdown.TextPostprocessor.
    '''

    def run(self, text):
        pass


class RawHtmlTextPostprocessor(TextPostprocessor):

    def __init__(self):
        pass

    def run(self, text):
        for i in range(self.stash.html_counter):
            html, safe  = self.stash.rawHtmlBlocks[i]
            if self.safeMode and not safe:
                if str(self.safeMode).lower() == 'escape':
                    html = self.escape(html)
                elif str(self.safeMode).lower() == 'remove':
                    html = ''
                else:
                    html = HTML_REMOVED_TEXT
                                   
            text = text.replace("<p>%s\n</p>" % (HTML_PLACEHOLDER % i),
                              html + "\n")
            text =  text.replace(HTML_PLACEHOLDER % i, html)
        return text

    def escape(self, html):
        ''' Basic html escaping '''
        html = html.replace('&', '&amp;')
        html = html.replace('<', '&lt;')
        html = html.replace('>', '&gt;')
        return html.replace('"', '&quot;')

RAWHTMLTEXTPOSTPROCESSOR = RawHtmlTextPostprocessor()

"""
======================================================================
========================== MISC AUXILIARY CLASSES ====================
======================================================================
"""

class HtmlStash:
    """This class is used for stashing HTML objects that we extract
        in the beginning and replace with place-holders."""

    def __init__ (self):
        self.html_counter = 0 # for counting inline html segments
        self.rawHtmlBlocks=[]

    def store(self, html, safe=False):
        """Saves an HTML segment for later reinsertion.  Returns a
           placeholder string that needs to be inserted into the
           document.

           @param html: an html segment
           @param safe: label an html segment as safe for safemode
           @param inline: label a segmant as inline html
           @returns : a placeholder string """
        self.rawHtmlBlocks.append((html, safe))
        placeholder = HTML_PLACEHOLDER % self.html_counter
        self.html_counter += 1
        return placeholder


class BlockGuru:

    def _findHead(self, lines, fn, allowBlank=0):

        """Functional magic to help determine boundaries of indented
           blocks.

           @param lines: an array of strings
           @param fn: a function that returns a substring of a string
                      if the string matches the necessary criteria
           @param allowBlank: specifies whether it's ok to have blank
                      lines between matching functions
           @returns: a list of post processes items and the unused
                      remainder of the original list"""

        items = []
        item = -1

        i = 0 # to keep track of where we are

        for line in lines:

            if not line.strip() and not allowBlank:
                return items, lines[i:]

            if not line.strip() and allowBlank:
                # If we see a blank line, this _might_ be the end
                i += 1

                # Find the next non-blank line
                for j in range(i, len(lines)):
                    if lines[j].strip():
                        next = lines[j]
                        break
                else:
                    # There is no more text => this is the end
                    break

                # Check if the next non-blank line is still a part of the list

                part = fn(next)

                if part:
                    items.append("")
                    continue
                else:
                    break # found end of the list

            part = fn(line)

            if part:
                items.append(part)
                i += 1
                continue
            else:
                return items, lines[i:]
        else:
            i += 1

        return items, lines[i:]


    def detabbed_fn(self, line):
        """ An auxiliary method to be passed to _findHead """
        m = RE.regExp['tabbed'].match(line)
        if m:
            return m.group(4)
        else:
            return None


    def detectTabbed(self, lines):

        return self._findHead(lines, self.detabbed_fn,
                              allowBlank = 1)


def print_error(string):
    """Print an error string to stderr"""
    sys.stderr.write(string +'\n')


def dequote(string):
    """ Removes quotes from around a string """
    if ( ( string.startswith('"') and string.endswith('"'))
         or (string.startswith("'") and string.endswith("'")) ):
        return string[1:-1]
    else:
        return string

"""
======================================================================
========================== CORE MARKDOWN =============================
======================================================================

This stuff is ugly, so if you are thinking of extending the syntax,
see first if you can do it via pre-processors, post-processors,
inline patterns or a combination of the three.
"""

class CorePatterns:
    """This class is scheduled for removal as part of a refactoring
        effort."""

    patterns = {
        'header':          r'(#*)([^#]*)(#*)', # # A title
        'reference-def':   r'(\ ?\ ?\ ?)\[([^\]]*)\]:\s*([^ ]*)(.*)',
                           # [Google]: http://www.google.com/
        'containsline':    r'([-]*)$|^([=]*)', # -----, =====, etc.
        'ol':              r'[ ]{0,3}[\d]*\.\s+(.*)', # 1. text
        'ul':              r'[ ]{0,3}[*+-]\s+(.*)', # "* text"
        'isline1':         r'(\**)', # ***
        'isline2':         r'(\-*)', # ---
        'isline3':         r'(\_*)', # ___
        'tabbed':          r'((\t)|(    ))(.*)', # an indented line
        'quoted':          r'> ?(.*)', # a quoted block ("> ...")
    }

    def __init__ (self):

        self.regExp = {}
        for key in self.patterns.keys():
            self.regExp[key] = re.compile("^%s$" % self.patterns[key],
                                          re.DOTALL)

        self.regExp['containsline'] = re.compile(r'^([-]*)$|^([=]*)$', re.M)

RE = CorePatterns()


class Markdown:
    """ Markdown formatter class for creating an html document from
        Markdown text """


    def __init__(self, source=None,  # depreciated
                 extensions=[],
                 extension_configs=None,
                 safe_mode = False):
        """Creates a new Markdown instance.

           @param source: The text in Markdown format. Depreciated!
           @param extensions: A list if extensions.
           @param extension-configs: Configuration setting for extensions.
           @param safe_mode: Disallow raw html. """

        self.source = source
        if source is not None:
            message(WARN, "The `source` arg of Markdown.__init__() is depreciated and will be removed in the future. Use `instance.convert(source)` instead.")
        self.safeMode = safe_mode
        self.blockGuru = BlockGuru()
        self.registeredExtensions = []
        self.stripTopLevelTags = 1
        self.docType = ""

        self.textPreprocessors = [HTML_BLOCK_PREPROCESSOR]

        self.preprocessors = [HEADER_PREPROCESSOR,
                              LINE_PREPROCESSOR,
                              # A footnote preprocessor will
                              # get inserted here
                              REFERENCE_PREPROCESSOR]


        self.postprocessors = [] # a footnote postprocessor will get
                                 # inserted later

        self.textPostprocessors = [# a footnote postprocessor will get
                                   # inserted here
                                   RAWHTMLTEXTPOSTPROCESSOR]

        self.prePatterns = []
        

        self.inlinePatterns = [DOUBLE_BACKTICK_PATTERN,
                               BACKTICK_PATTERN,
                               ESCAPE_PATTERN,
                               REFERENCE_PATTERN,
                               LINK_ANGLED_PATTERN,
                               LINK_PATTERN,
                               IMAGE_LINK_PATTERN,
			                   IMAGE_REFERENCE_PATTERN,
			                   AUTOLINK_PATTERN,
                               AUTOMAIL_PATTERN,
                               LINE_BREAK_PATTERN_2,
                               LINE_BREAK_PATTERN,
                               HTML_PATTERN,
                               ENTITY_PATTERN,
                               NOT_STRONG_PATTERN,
                               STRONG_EM_PATTERN,
                               STRONG_EM_PATTERN_2,
                               STRONG_PATTERN,
                               STRONG_PATTERN_2,
                               EMPHASIS_PATTERN,
                               EMPHASIS_PATTERN_2
                               # The order of the handlers matters!!!
                               ]

        self.registerExtensions(extensions = extensions,
                                configs = extension_configs)

        self.reset()


    def registerExtensions(self, extensions, configs):

        if not configs:
            configs = {}

        for ext in extensions:

            extension_module_name = "mdx_" + ext

            try:
                module = __import__(extension_module_name)

            except:
                message(CRITICAL,
                        "couldn't load extension %s (looking for %s module)"
                        % (ext, extension_module_name) )
            else:

                if configs.has_key(ext):
                    configs_for_ext = configs[ext]
                else:
                    configs_for_ext = []
                extension = module.makeExtension(configs_for_ext)    
                extension.extendMarkdown(self, globals())




    def registerExtension(self, extension):
        """ This gets called by the extension """
        self.registeredExtensions.append(extension)

    def reset(self):
        """Resets all state variables so that we can start
            with a new text."""
        self.references={}
        self.htmlStash = HtmlStash()

        HTML_BLOCK_PREPROCESSOR.stash = self.htmlStash
        LINE_PREPROCESSOR.stash = self.htmlStash
        REFERENCE_PREPROCESSOR.references = self.references
        HTML_PATTERN.stash = self.htmlStash
        ENTITY_PATTERN.stash = self.htmlStash
        REFERENCE_PATTERN.references = self.references
        IMAGE_REFERENCE_PATTERN.references = self.references
        RAWHTMLTEXTPOSTPROCESSOR.stash = self.htmlStash
        RAWHTMLTEXTPOSTPROCESSOR.safeMode = self.safeMode

        for extension in self.registeredExtensions:
            extension.reset()


    def _transform(self):
        """Transforms the Markdown text into a XHTML body document

           @returns: A NanoDom Document """

        # Setup the document

        self.doc = Document()
        self.top_element = self.doc.createElement("span")
        self.top_element.appendChild(self.doc.createTextNode('\n'))
        self.top_element.setAttribute('class', 'markdown')
        self.doc.appendChild(self.top_element)

        # Fixup the source text
        text = self.source
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text += "\n\n"
        text = text.expandtabs(TAB_LENGTH)

        # Split into lines and run the preprocessors that will work with
        # self.lines

        self.lines = text.split("\n")

        # Run the pre-processors on the lines
        for prep in self.preprocessors :
            self.lines = prep.run(self.lines)

        # Create a NanoDom tree from the lines and attach it to Document


        buffer = []
        for line in self.lines:
            if line.startswith("#"):
                self._processSection(self.top_element, buffer)
                buffer = [line]
            else:
                buffer.append(line)
        self._processSection(self.top_element, buffer)
        
        #self._processSection(self.top_element, self.lines)

        # Not sure why I put this in but let's leave it for now.
        self.top_element.appendChild(self.doc.createTextNode('\n'))

        # Run the post-processors
        for postprocessor in self.postprocessors:
            postprocessor.run(self.doc)

        return self.doc


    def _processSection(self, parent_elem, lines,
                        inList = 0, looseList = 0):

        """Process a section of a source document, looking for high
           level structural elements like lists, block quotes, code
           segments, html blocks, etc.  Some those then get stripped
           of their high level markup (e.g. get unindented) and the
           lower-level markup is processed recursively.

           @param parent_elem: A NanoDom element to which the content
                               will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None"""

        # Loop through lines until none left.
        while lines:

            # Check if this section starts with a list, a blockquote or
            # a code block

            processFn = { 'ul':     self._processUList,
                          'ol':     self._processOList,
                          'quoted': self._processQuote,
                          'tabbed': self._processCodeBlock}

            for regexp in ['ul', 'ol', 'quoted', 'tabbed']:
                m = RE.regExp[regexp].match(lines[0])
                if m:
                    processFn[regexp](parent_elem, lines, inList)
                    return

            # We are NOT looking at one of the high-level structures like
            # lists or blockquotes.  So, it's just a regular paragraph
            # (though perhaps nested inside a list or something else).  If
            # we are NOT inside a list, we just need to look for a blank
            # line to find the end of the block.  If we ARE inside a
            # list, however, we need to consider that a sublist does not
            # need to be separated by a blank line.  Rather, the following
            # markup is legal:
            #
            # * The top level list item
            #
            #     Another paragraph of the list.  This is where we are now.
            #     * Underneath we might have a sublist.
            #

            if inList:

                start, lines  = self._linesUntil(lines, (lambda line:
                                 RE.regExp['ul'].match(line)
                                 or RE.regExp['ol'].match(line)
                                                  or not line.strip()))

                self._processSection(parent_elem, start,
                                     inList - 1, looseList = looseList)
                inList = inList-1

            else: # Ok, so it's just a simple block

                paragraph, lines = self._linesUntil(lines, lambda line:
                                                     not line.strip())

                if len(paragraph) and paragraph[0].startswith('#'):
                    self._processHeader(parent_elem, paragraph)

                elif paragraph:
                    self._processParagraph(parent_elem, paragraph,
                                          inList, looseList)

            if lines and not lines[0].strip():
                lines = lines[1:]  # skip the first (blank) line


    def _processHeader(self, parent_elem, paragraph):
        m = RE.regExp['header'].match(paragraph[0])
        if m:
            level = len(m.group(1))
            h = self.doc.createElement("h%d" % level)
            parent_elem.appendChild(h)
            for item in self._handleInline(m.group(2).strip()):
                h.appendChild(item)
        else:
            message(CRITICAL, "We've got a problem header!")


    def _processParagraph(self, parent_elem, paragraph, inList, looseList):
        list = self._handleInline("\n".join(paragraph))

        if ( parent_elem.nodeName == 'li'
                and not (looseList or parent_elem.childNodes)):

            # If this is the first paragraph inside "li", don't
            # put <p> around it - append the paragraph bits directly
            # onto parent_elem
            el = parent_elem
        else:
            # Otherwise make a "p" element
            el = self.doc.createElement("p")
            parent_elem.appendChild(el)

        for item in list:
            el.appendChild(item)
 

    def _processUList(self, parent_elem, lines, inList):
        self._processList(parent_elem, lines, inList,
                         listexpr='ul', tag = 'ul')

    def _processOList(self, parent_elem, lines, inList):
        self._processList(parent_elem, lines, inList,
                         listexpr='ol', tag = 'ol')


    def _processList(self, parent_elem, lines, inList, listexpr, tag):
        """Given a list of document lines starting with a list item,
           finds the end of the list, breaks it up, and recursively
           processes each list item and the remainder of the text file.

           @param parent_elem: A dom element to which the content will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None"""

        ul = self.doc.createElement(tag)  # ul might actually be '<ol>'
        parent_elem.appendChild(ul)

        looseList = 0

        # Make a list of list items
        items = []
        item = -1

        i = 0  # a counter to keep track of where we are

        for line in lines: 

            loose = 0
            if not line.strip():
                # If we see a blank line, this _might_ be the end of the list
                i += 1
                loose = 1

                # Find the next non-blank line
                for j in range(i, len(lines)):
                    if lines[j].strip():
                        next = lines[j]
                        break
                else:
                    # There is no more text => end of the list
                    break

                # Check if the next non-blank line is still a part of the list
                if ( RE.regExp['ul'].match(next) or
                     RE.regExp['ol'].match(next) or 
                     RE.regExp['tabbed'].match(next) ):
                    # get rid of any white space in the line
                    items[item].append(line.strip())
                    looseList = loose or looseList
                    continue
                else:
                    break # found end of the list

            # Now we need to detect list items (at the current level)
            # while also detabing child elements if necessary

            for expr in ['ul', 'ol', 'tabbed']:

                m = RE.regExp[expr].match(line)
                if m:
                    if expr in ['ul', 'ol']:  # We are looking at a new item
                        #if m.group(1) :
                        # Removed the check to allow for a blank line
                        # at the beginning of the list item
                        items.append([m.group(1)])
                        item += 1
                    elif expr == 'tabbed':  # This line needs to be detabbed
                        items[item].append(m.group(4)) #after the 'tab'

                    i += 1
                    break
            else:
                items[item].append(line)  # Just regular continuation
                i += 1 # added on 2006.02.25
        else:
            i += 1

        # Add the dom elements
        for item in items:
            li = self.doc.createElement("li")
            ul.appendChild(li)

            self._processSection(li, item, inList + 1, looseList = looseList)

        # Process the remaining part of the section

        self._processSection(parent_elem, lines[i:], inList)


    def _linesUntil(self, lines, condition):
        """ A utility function to break a list of lines upon the
            first line that satisfied a condition.  The condition
            argument should be a predicate function.
            """

        i = -1
        for line in lines:
            i += 1
            if condition(line): break
        else:
            i += 1
        return lines[:i], lines[i:]

    def _processQuote(self, parent_elem, lines, inList):
        """Given a list of document lines starting with a quote finds
           the end of the quote, unindents it and recursively
           processes the body of the quote and the remainder of the
           text file.

           @param parent_elem: DOM element to which the content will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None """

        dequoted = []
        i = 0
        blank_line = False # allow one blank line between paragraphs
        for line in lines:
            m = RE.regExp['quoted'].match(line)
            if m:
                dequoted.append(m.group(1))
                i += 1
                blank_line = False
            elif not blank_line and line.strip() != '':
                dequoted.append(line)
                i += 1
            elif not blank_line and line.strip() == '':
                dequoted.append(line)
                i += 1
                blank_line = True
            else:
                break

        blockquote = self.doc.createElement('blockquote')
        parent_elem.appendChild(blockquote)

        self._processSection(blockquote, dequoted, inList)
        self._processSection(parent_elem, lines[i:], inList)




    def _processCodeBlock(self, parent_elem, lines, inList):
        """Given a list of document lines starting with a code block
           finds the end of the block, puts it into the dom verbatim
           wrapped in ("<pre><code>") and recursively processes the
           the remainder of the text file.

           @param parent_elem: DOM element to which the content will be added
           @param lines: a list of lines
           @param inList: a level
           @returns: None"""

        detabbed, theRest = self.blockGuru.detectTabbed(lines)

        pre = self.doc.createElement('pre')
        code = self.doc.createElement('code')
        parent_elem.appendChild(pre)
        pre.appendChild(code)
        text = "\n".join(detabbed).rstrip()+"\n"
        #text = text.replace("&", "&amp;")
        code.appendChild(self.doc.createTextNode(text))
        self._processSection(parent_elem, theRest, inList)



    def _handleInline (self, line, patternIndex=0):
        """Transform a Markdown line with inline elements to an XHTML
        fragment.

        This function uses auxiliary objects called inline patterns.
        See notes on inline patterns above.

        @param line: A line of Markdown text
        @param patternIndex: The index of the inlinePattern to start with
        @return: A list of NanoDom nodes """


        parts = [line]

        while patternIndex < len(self.inlinePatterns):

            i = 0

            while i < len(parts):
                
                x = parts[i]

                if isinstance(x, (str, unicode)):
                    result = self._applyPattern(x, \
                                self.inlinePatterns[patternIndex], \
                                patternIndex)

                    if result:
                        i -= 1
                        parts.remove(x)
                        for y in result:
                            parts.insert(i+1,y)

                i += 1
            patternIndex += 1

        for i in range(len(parts)):
            x = parts[i]
            if isinstance(x, (str, unicode)):
                parts[i] = self.doc.createTextNode(x)

        return parts
        

    def _applyPattern(self, line, pattern, patternIndex):

        """ Given a pattern name, this function checks if the line
        fits the pattern, creates the necessary elements, and returns
        back a list consisting of NanoDom elements and/or strings.
        
        @param line: the text to be processed
        @param pattern: the pattern to be checked

        @returns: the appropriate newly created NanoDom element if the
                  pattern matches, None otherwise.
        """

        # match the line to pattern's pre-compiled reg exp.
        # if no match, move on.



        m = pattern.getCompiledRegExp().match(line)
        if not m:
            return None

        # if we got a match let the pattern make us a NanoDom node
        # if it doesn't, move on
        node = pattern.handleMatch(m, self.doc)

        # check if any of this nodes have children that need processing

        if isinstance(node, Element):

            if not node.nodeName in ["code", "pre"]:
                for child in node.childNodes:
                    if isinstance(child, TextNode):
                        
                        result = self._handleInline(child.value, patternIndex+1)
                        
                        if result:

                            if result == [child]:
                                continue
                                
                            result.reverse()
                            #to make insertion easier

                            position = node.childNodes.index(child)
                            
                            node.removeChild(child)

                            for item in result:

                                if isinstance(item, (str, unicode)):
                                    if len(item) > 0:
                                        node.insertChild(position,
                                             self.doc.createTextNode(item))
                                else:
                                    node.insertChild(position, item)
                



        if node:
            # Those are in the reverse order!
            return ( m.groups()[-1], # the string to the left
                     node,           # the new node
                     m.group(1))     # the string to the right of the match

        else:
            return None

    def convert (self, source = None):
        """Return the document in XHTML format.

        @returns: A serialized XHTML body."""

        if source is not None: #Allow blank string
            self.source = source

        if not self.source:
            return u""

        try:
            self.source = unicode(self.source)
        except UnicodeDecodeError:
            message(CRITICAL, 'UnicodeDecodeError: Markdown only accepts unicode or ascii  input.')
            return u""

        for pp in self.textPreprocessors:
            self.source = pp.run(self.source)

        doc = self._transform()
        xml = doc.toxml()


        # Return everything but the top level tag

        if self.stripTopLevelTags:
            xml = xml.strip()[23:-7] + "\n"

        for pp in self.textPostprocessors:
            xml = pp.run(xml)

        return (self.docType + xml).strip()


    def __str__(self):
        ''' Report info about instance. Markdown always returns unicode. '''
        if self.source is None:
            status = 'in which no source text has been assinged.'
        else:
            status = 'which contains %d chars and %d line(s) of source.'%\
                     (len(self.source), self.source.count('\n')+1)
        return 'An instance of "%s" %s'% (self.__class__, status)

    __unicode__ = convert # markdown should always return a unicode string





# ====================================================================

def markdownFromFile(input = None,
                     output = None,
                     extensions = [],
                     encoding = None,
                     message_threshold = CRITICAL,
                     safe = False):

    global console_hndlr
    console_hndlr.setLevel(message_threshold)

    message(DEBUG, "input file: %s" % input)

    if not encoding:
        encoding = "utf-8"

    input_file = codecs.open(input, mode="r", encoding=encoding)
    text = input_file.read()
    input_file.close()

    text = removeBOM(text, encoding)

    new_text = markdown(text, extensions, safe_mode = safe)

    if output:
        output_file = codecs.open(output, "w", encoding=encoding)
        output_file.write(new_text)
        output_file.close()

    else:
        sys.stdout.write(new_text.encode(encoding))

def markdown(text,
             extensions = [],
             safe_mode = False):
    
    message(DEBUG, "in markdown.markdown(), received text:\n%s" % text)

    extension_names = []
    extension_configs = {}
    
    for ext in extensions:
        pos = ext.find("(") 
        if pos == -1:
            extension_names.append(ext)
        else:
            name = ext[:pos]
            extension_names.append(name)
            pairs = [x.split("=") for x in ext[pos+1:-1].split(",")]
            configs = [(x.strip(), y.strip()) for (x, y) in pairs]
            extension_configs[name] = configs

    md = Markdown(extensions=extension_names,
                  extension_configs=extension_configs,
                  safe_mode = safe_mode)

    return md.convert(text)
        

class Extension:

    def __init__(self, configs = {}):
        self.config = configs

    def getConfig(self, key):
        if self.config.has_key(key):
            return self.config[key][0]
        else:
            return ""

    def getConfigInfo(self):
        return [(key, self.config[key][1]) for key in self.config.keys()]

    def setConfig(self, key, value):
        self.config[key][0] = value


OPTPARSE_WARNING = """
Python 2.3 or higher required for advanced command line options.
For lower versions of Python use:

      %s INPUT_FILE > OUTPUT_FILE
    
""" % EXECUTABLE_NAME_FOR_USAGE

def parse_options():

    try:
        optparse = __import__("optparse")
    except:
        if len(sys.argv) == 2:
            return {'input': sys.argv[1],
                    'output': None,
                    'message_threshold': CRITICAL,
                    'safe': False,
                    'extensions': [],
                    'encoding': None }

        else:
            print OPTPARSE_WARNING
            return None

    parser = optparse.OptionParser(usage="%prog INPUTFILE [options]")

    parser.add_option("-f", "--file", dest="filename",
                      help="write output to OUTPUT_FILE",
                      metavar="OUTPUT_FILE")
    parser.add_option("-e", "--encoding", dest="encoding",
                      help="encoding for input and output files",)
    parser.add_option("-q", "--quiet", default = CRITICAL,
                      action="store_const", const=60, dest="verbose",
                      help="suppress all messages")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=INFO, dest="verbose",
                      help="print info messages")
    parser.add_option("-s", "--safe", dest="safe", default=False,
                      metavar="SAFE_MODE",
                      help="same mode ('replace', 'remove' or 'escape'  user's HTML tag)")
    
    parser.add_option("--noisy",
                      action="store_const", const=DEBUG, dest="verbose",
                      help="print debug messages")
    parser.add_option("-x", "--extension", action="append", dest="extensions",
                      help = "load extension EXTENSION", metavar="EXTENSION")

    (options, args) = parser.parse_args()

    if not len(args) == 1:
        parser.print_help()
        return None
    else:
        input_file = args[0]

    if not options.extensions:
        options.extensions = []

    return {'input': input_file,
            'output': options.filename,
            'message_threshold': options.verbose,
            'safe': options.safe,
            'extensions': options.extensions,
            'encoding': options.encoding }

if __name__ == '__main__':
    """ Run Markdown from the command line. """

    options = parse_options()

    #if os.access(inFile, os.R_OK):

    if not options:
        sys.exit(0)
    
    markdownFromFile(**options)











########NEW FILE########
__FILENAME__ = api
"""@package docstring
Provides the web service API.
"""

import google.appengine.api.memcache
import google.appengine.api.users
import datetime
import simplejson
import db
import handlers
import models

class Comment(handlers.Handler):
    """Provides web service methods that handle requests to /api/comment."""
    
    def get(self):
        """Returns one or more comments.
        
        Parameters:
        
        count (optional): The number of results to return. Default is 100.
        page (optional): The page of results. Default is 1.
        user (optional): The email address of the comment submitter.
        
        Errors:
        
        400 Bad Request
        """
        result = {}
        count = self.request.get("count")
        if (count):
            count = int(count)
        else:
            count = 100
        page = self.request.get("page")
        if (page):
            page = int(page)
        else:
            page = 1
        user = google.appengine.api.users.User(self.request.get("user"))
        if (user):
            comments = db.Comment().fetchByUser(user, page, count)
            if (comments):
                result = [comment.toDictionary() for comment in comments]
        
        # Return the result
        self.respondWithDictionaryAsJSON({"result": result})
        
    def post(self):
        pass
        
class CommentCount(handlers.Handler):
    """Provides web service methods that handle requests to api/comment/count."""
    
    def get(self):
        """Returns the number of comments.
        
        Parameters:
        
        Errors:
        
        400 Bad Request
        """
        result = db.Comment().fetchCount()
        # Return the result
        self.respondWithDictionaryAsJSON({"result": result})
        
class Radar(handlers.Handler):
    """Provides web service methods that handle requests to /api/radar."""
    
    def get(self):
        """Returns one or more radars.
        
        Parameters:
        
        count (optional): The number of results to return. Default is 100.
        page (optional): The page of results. Default is 1.
        id (optional): The radar identifier.
        number (optional): The radar number.
        user (optional): The email address of the radar submitter.
        
        Errors:
        
        400 Bad Request
        """
        result = {}
        count = self.request.get("count", None)
        if (count):
            count = int(count)
        else:
            count = 100
        page = self.request.get("page", None)
        if (page):
            page = int(page)
        else:
            page = 1
        parameters = [];
        radarId = self.request.get("id")
        if (radarId):
            parameters.append(radarId)
            radar = db.Radar().fetchById(int(radarId))
            if (radar):
                result = radar.toDictionary()
        if (not result):
            radarNumber = self.request.get("number")
            if radarNumber:
                parameters.append(radarNumber)
                radar = db.Radar().fetchByNumber(radarNumber)
                if (radar):
                    result = radar.toDictionary()
        if (not result):
            userName = self.request.get("user")
            if (userName):
                parameters.append(userName)
                user = google.appengine.api.users.User(userName)
                if (user):
                    radars = db.Radar().fetchByUser(user, page, count)
                    if (radars):
                        result = [radar.toDictionary() for radar in radars]
        if (not result and not parameters):
            radars = db.Radar().fetchAll(page, count)
            if (radars):
                result = [radar.toDictionary() for radar in radars]
        
        # Return the result
        self.respondWithDictionaryAsJSON({"result": result})
        
    def post(self):
        """Add a radar.
        
        Parameters:
        
        number (required):
        classification (optional):
        description (optional):
        originated (optional):
        product (optional):
        product_version (optional):
        reproducible (optional):
        status (optional):
        title (optional):
        
        Errors:
        
        400 Bad Request
        401 Unauthorized
        
        Authentication:
        
        This service requires authentication.
        """
        result = {}
        
        currentUser = google.appengine.api.users.GetCurrentUser()
        if (not currentUser):
            # Unauthorized
            self.error(401)
            self.respondWithDictionaryAsJSON({"error": "Authentication required."})
            return
        
        radar = models.Radar(
            created = datetime.datetime.now(),
            modified = datetime.datetime.now())
        
        # Required
        radar.number = self.request.get("number", None)
        if (radar.number == None):
            # Bad Request
            self.error(400)
            self.respondWithDictionaryAsJSON({"error": "Missing required parameter."})
            return;
        radar.user = currentUser;
        
        # Optional
        radar.classification = self.request.get("classification", None)
        radar.description = self.request.get("description", None)
        radar.originated = self.request.get("originated", None)
        radar.product = self.request.get("product", None)
        radar.product_version = self.request.get("product_version", None)
        # radar.resolved = self.request.get("resolved", None)
        radar.reproducible = self.request.get("reproducible", None)
        radar.status = self.request.get("status", None)
        radar.title = self.request.get("title", None)
        
        # Save
        radar.put()
        
        if (radar.key() != None):
            result = radar.toDictionary();
        
        google.appengine.api.memcache.flush_all()
        
        # Return the result
        self.respondWithDictionaryAsJSON({"result": result})
        
class RadarCount(handlers.Handler):
    """Provides web service methods that handle requests to api/radar/count."""
    
    def get(self):
        """Returns the number of radars.
        
        Parameters:
        
        Errors:
        
        400 Bad Request
        """
        result = db.Radar().fetchCount()
        # Return the result
        self.respondWithDictionaryAsJSON({"result": result})
        
class Search(handlers.Handler):
    """Provides web service methods that handle requests to api/search."""
    
    def get(self):
        result = {}
        radars = None
        
        count = self.request.get("count")
        if (count):
            count = int(count)
        else:
            count = 100
        
        page = self.request.get("page")
        if (page):
            page = int(page)
        else:
            page = 1
        
        scope = self.request.get("scope")
        if (not scope):
            scope = "all"
        
        searchQuery = self.request.get("q")
        keywords = searchQuery.split(" ")
        keyword = keywords[0]
        
        try:
            if (scope == "number"):
                radars = db.Radar().fetchByNumbers(keywords, page, count)
            elif (scope == "user"):
                users = []
                for userName in keywords:
                    user = google.appengine.api.users.User(userName)
                    if user:
                        users.append(user)
                radars = db.Radar().fetchByUsers(users, page, count);
            else:
                radars = models.Radar.all().search(keyword).order("-number").fetch(count, (page - 1) * count)
        except Exception:
            radars = None
        
        if (radars and len(radars) > 0):
            result = [radar.toDictionary() for radar in radars]
        
        # Return the result
        self.respondWithDictionaryAsJSON({"result": result})
        
class Test(handlers.Handler):
    def get(self):
        result = {"foo":[1, 2, 3, {"bar": [4, 5, 6]}]}
        self.respondWithDictionaryAsJSON(result)

class TestAuthentication(handlers.Handler):
    def get(self):
        user = self.GetCurrentUser()
        if user:
          result = {"user":user.nickname(), "foo":[1, 2, 3, {"bar": [4, 5, 6]}]}
          self.respondWithDictionaryAsJSON(result)
        else:
          self.error(401)
          self.respondWithDictionaryAsJSON({"error": "Authentication required."})

########NEW FILE########
__FILENAME__ = db
import models

class Radar():
    def fetchAll(self, page = 1, count = 100):
        return models.Radar.gql("ORDER BY number DESC").fetch(count, (page - 1) * count)
        
    def fetchCount(self):
        return models.Radar.all().count()
        
    def fetchById(self, id):
        return models.Radar.get_by_id(id)
        
    def fetchByNumber(self, number):
        return models.Radar.gql("WHERE number = :1", number).get()
        
    def fetchByNumbers(self, numbers, page = 1, count = 100):
        return models.Radar.gql("WHERE number IN :1", numbers).fetch(count, (page - 1) * count)
        
    def fetchByUser(self, user, page = 1, count = 100):
        return models.Radar.gql("WHERE user = :1 ORDER BY number DESC", user).fetch(count, (page - 1) * count)
        
    def fetchByUsers(self, users, page = 1, count = 100):
        return models.Radar.gql("WHERE user IN :1 ORDER BY number DESC", users).fetch(count, (page - 1) * count)
        
class Comment():
    def fetchAll(self, page = 1, count = 100):
        return models.Comment.gql("ORDER BY posted_at DESC").fetch(count, (page - 1) * count)
        
    def fetchCount(self):
        return models.Comment.all().count()
        
    def fetchByUser(self, user, page = 1, count = 100):
        return models.Comment.gql("WHERE user = :1 ORDER BY posted_at DESC", user).fetch(count, (page - 1) * count)
        
class APIKey():
    def fetchByUser(self, user):
        return models.APIKey.gql("WHERE user = :1", user).get()

    def fetchByAPIKey(self, apikey):
        return models.APIKey.gql("WHERE apikey = :1", apikey).get()
    

########NEW FILE########
__FILENAME__ = handlers
import wsgiref.handlers
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required

import openradar.db

import datetime
import os
import simplejson

class Handler(webapp.RequestHandler):

  def respondWithDictionaryAsJSON(self, d):
    self.response.out.write(simplejson.dumps(d) + "\n")
      
  def respondWithText(self, text):
    self.response.out.write(text)
    self.response.out.write("\n")
    
  """Supplies a common template generation function.
  When you call generate(), we augment the template variables supplied with
  the current user in the 'user' variable and the current webapp request
  in the 'request' variable.
  """
  def respondWithTemplate(self, template_name, template_values={}):
    values = {
      'request': self.request,
      'debug': self.request.get('debug'),
      'application_name': 'Open Radar',
      'user': users.GetCurrentUser(),
      'login_url': users.CreateLoginURL(self.request.uri),
      'logout_url': users.CreateLogoutURL('http://' + self.request.host + '/'),
    }
    values.update(template_values)
    directory = os.path.dirname(__file__)
    path = os.path.join(directory, os.path.join('../templates', template_name))
    self.response.out.write(template.render(path, values))

  def GetCurrentUser(self):
    if 'Authorization' in self.request.headers: 
        auth = self.request.headers['Authorization']
        if auth:
            apikey = openradar.db.APIKey().fetchByAPIKey(auth)
            if apikey:
                return apikey.user
    return users.GetCurrentUser()

    

########NEW FILE########
__FILENAME__ = models
from google.appengine.ext import db
from google.appengine.ext import search
import datetime
import markdown

class Secret(db.Model):
    name = db.StringProperty()
    value = db.StringProperty()

class Radar(search.SearchableModel):
    # This first set of properties are user-specified.
    # For flexibility and robustness, we represent them all as strings.
    # The Radar Problem ID (we need an int form of this)
    number = db.StringProperty()
    number_intvalue = db.IntegerProperty()
    
    # The radar number this radar duplicates
    parent_number = db.StringProperty()
    title = db.StringProperty()
    # Radar state
    status = db.StringProperty()
    resolved = db.StringProperty()
    # App Engine user who created this entry
    user = db.UserProperty()
    product = db.StringProperty()
    classification = db.StringProperty()
    reproducible = db.StringProperty()
    product_version = db.StringProperty()
    # problem description plus anything else.
    description = db.TextProperty()
    # when the Radar was filed
    originated = db.StringProperty()
    # when the OpenRadar object was created
    created = db.DateTimeProperty()
    # These remaining properties are managed by the OpenRadar web app.
    # They are automatically set when put() is called.
    # We will add more as needed to allow better performance or to simplify
    # sorting and querying.
    # when the OpenRadar object was last modified
    modified = db.DateTimeProperty()
    
    def username(self):
        return self.user.nickname().split("@")[0]
    
    def put(self):
        self.modified = datetime.datetime.now()
        # Sanitize the data before storing
        self.sanitize()
        return db.Model.put(self)
    
    def comments(self):
        return Comment.gql("WHERE radar = :1 AND is_reply_to = :2", self, None)
    
    def children(self):
        gqlQuery = Radar.gql("WHERE parent_number = :1 ORDER BY number ASC", self.number)
        
        return gqlQuery.fetch(gqlQuery.count())
    
    def parent(self):
        return Radar.gql("WHERE number = :1", self.parent_number).get()
    
    def sanitize(self):
        if (self.classification):
            self.classification = self.classification.strip()
        if (self.description):
            self.description = self.description.strip()
        if (self.number):
            self.number = self.number.strip()
        if (self.originated):
            self.originated = self.originated.strip()
        if (self.product):
            self.product = self.product.strip()
        if (self.product_version):
            self.product_version = self.product_version.strip()
        if (self.resolved):
            self.resolved = self.resolved.strip()
        if (self.reproducible):
            self.reproducible = self.reproducible.strip()
        
        # The most common format for duplicates is "Duplicate/<radar_number>"
        # If that format is found, extract the included radar number and store
        # it in self.parent_number
        if (self.status):
            current_status = self.status.strip()
            status_words = current_status.split("/")
            if (len(status_words) == 2):
                # Trim any leading or trailing whitespace from the status type
                status_type = status_words[0].strip()
                # Determine whether status_type equals "duplicate", ignore
                # case sensitivity
                if (status_type.lower() == "duplicate"):
                    status_type = "Duplicate"
                    parent_radar_number = status_words[1].strip()
                    if (parent_radar_number.isdigit()):
                        self.parent_number = parent_radar_number
                    # Put the components back together
                    current_status = status_type + "/" + parent_radar_number
            # Update self.status with the sanitized status
            self.status = current_status;
        
        if (self.title):
            self.title = self.title.strip()
    
    def toDictionary(self):
        return {
            "id":self.key().id(),
            "title":self.title,
            "number":self.number,
            "user":self.user.email(),
            "status":self.status,
            "description":self.description,
            "resolved":self.resolved,
            "product":self.product,
            "classification":self.classification,
            "reproducible":self.reproducible,
            "product_version":self.product_version,
            "originated":self.originated}
    

md = markdown.Markdown()

class Comment(search.SearchableModel):
  user = db.UserProperty() # App Engine user who wrote the comment
  subject = db.StringProperty()
  body = db.TextProperty() # as markdown
  posted_at = db.DateTimeProperty()
  radar = db.ReferenceProperty(Radar)
  is_reply_to = db.SelfReferenceProperty()
  
  def __init__(self, *args, **kwargs):
    super(Comment, self).__init__(*args, **kwargs)
    if(not self.posted_at): self.posted_at = datetime.datetime.now()
    if(not self.body): self.body = ""
    if(not self.subject): self.subject = ""
    
  def username(self):
    return self.user.nickname().split("@")[0]
      
  def radar_exists(self):
    try:
      return self.radar != None 
    except db.Error:
      return False

  def radarnumber(self):
    return self.radar_exists() and self.radar.number or "Deleted"

  def radartitle(self):
    return self.radar_exists() and self.radar.title or "Deleted"

  def replies(self):
    return Comment.gql("WHERE is_reply_to = :1", self)
  
  # I know this is a bad place to put it, but my only other idea is custom django template tags, and I just couldn't get those to work
  def draw(self, onlyInner = False):
    from google.appengine.ext.webapp import template
    import os
    directory = os.path.dirname(__file__)
    path = os.path.join(directory, os.path.join('../templates', "comment.html"))
    
    return template.render(path, {"comment": self, "onlyInner": onlyInner})
  
  def form(self):
    from google.appengine.ext.webapp import template
    import os
    directory = os.path.dirname(__file__)
    path = os.path.join(directory, os.path.join('../templates', "comment-form.html"))
    
    return template.render(path, {"comment": self})
  
  def html_body(self):
    return md.convert(self.body)

  def editable_by_current_user(self):
    from google.appengine.api import users
    user = users.GetCurrentUser()
    return user == self.user or users.is_current_user_admin()
    
  def deleteOrBlank(self):
    if self.replies().count() > 0:
      self.subject = "(Removed)"
      self.body = "*This comment has been removed by its author or a moderator.*"
      self.put()
      return "blanked"
    else:
      self.delete()
      return "deleted"
    
  def toDictionary(self):
    return {
      "id":self.key().id(),
      "user":self.user.email(), 
      "subject":self.subject,
      "body":self.body,
      "radar":self.radar.number,
      "is_reply_to":self.is_reply_to and self.is_reply_to.key().id() or ""
    }
    

class Profile(db.Model):
  name = db.StringProperty()            # screen name
  twitter = db.StringProperty()         # twitter id
  user = db.UserProperty()
  radar_count = db.IntegerProperty()
  
class Bump(db.Model):
  radar = db.ReferenceProperty(Radar)   # users can bump radars to raise their profile
  user = db.UserProperty()              # the bumping user
  created = db.DateTimeProperty()	      # when the bump was added

class APIKey(db.Model):
  user = db.UserProperty()
  created = db.DateTimeProperty()
  apikey = db.StringProperty()

########NEW FILE########
__FILENAME__ = decoder
"""Implementation of JSONDecoder
"""
import re
import sys
import struct

from simplejson.scanner import make_scanner
try:
    from simplejson._speedups import scanstring as c_scanstring
except ImportError:
    c_scanstring = None

__all__ = ['JSONDecoder']

FLAGS = re.VERBOSE | re.MULTILINE | re.DOTALL

def _floatconstants():
    _BYTES = '7FF80000000000007FF0000000000000'.decode('hex')
    if sys.byteorder != 'big':
        _BYTES = _BYTES[:8][::-1] + _BYTES[8:][::-1]
    nan, inf = struct.unpack('dd', _BYTES)
    return nan, inf, -inf

NaN, PosInf, NegInf = _floatconstants()


def linecol(doc, pos):
    lineno = doc.count('\n', 0, pos) + 1
    if lineno == 1:
        colno = pos
    else:
        colno = pos - doc.rindex('\n', 0, pos)
    return lineno, colno


def errmsg(msg, doc, pos, end=None):
    # Note that this function is called from _speedups
    lineno, colno = linecol(doc, pos)
    if end is None:
        return '%s: line %d column %d (char %d)' % (msg, lineno, colno, pos)
    endlineno, endcolno = linecol(doc, end)
    return '%s: line %d column %d - line %d column %d (char %d - %d)' % (
        msg, lineno, colno, endlineno, endcolno, pos, end)


_CONSTANTS = {
    '-Infinity': NegInf,
    'Infinity': PosInf,
    'NaN': NaN,
}

STRINGCHUNK = re.compile(r'(.*?)(["\\\x00-\x1f])', FLAGS)
BACKSLASH = {
    '"': u'"', '\\': u'\\', '/': u'/',
    'b': u'\b', 'f': u'\f', 'n': u'\n', 'r': u'\r', 't': u'\t',
}

DEFAULT_ENCODING = "utf-8"

def py_scanstring(s, end, encoding=None, strict=True, _b=BACKSLASH, _m=STRINGCHUNK.match):
    if encoding is None:
        encoding = DEFAULT_ENCODING
    chunks = []
    _append = chunks.append
    begin = end - 1
    while 1:
        chunk = _m(s, end)
        if chunk is None:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        end = chunk.end()
        content, terminator = chunk.groups()
        if content:
            if not isinstance(content, unicode):
                content = unicode(content, encoding)
            _append(content)
        if terminator == '"':
            break
        elif terminator != '\\':
            if strict:
                raise ValueError(errmsg("Invalid control character %r at", s, end))
            else:
                _append(terminator)
                continue
        try:
            esc = s[end]
        except IndexError:
            raise ValueError(
                errmsg("Unterminated string starting at", s, begin))
        if esc != 'u':
            try:
                m = _b[esc]
            except KeyError:
                raise ValueError(
                    errmsg("Invalid \\escape: %r" % (esc,), s, end))
            end += 1
        else:
            esc = s[end + 1:end + 5]
            next_end = end + 5
            msg = "Invalid \\uXXXX escape"
            try:
                if len(esc) != 4:
                    raise ValueError
                uni = int(esc, 16)
                if 0xd800 <= uni <= 0xdbff and sys.maxunicode > 65535:
                    msg = "Invalid \\uXXXX\\uXXXX surrogate pair"
                    if not s[end + 5:end + 7] == '\\u':
                        raise ValueError
                    esc2 = s[end + 7:end + 11]
                    if len(esc2) != 4:
                        raise ValueError
                    uni2 = int(esc2, 16)
                    uni = 0x10000 + (((uni - 0xd800) << 10) | (uni2 - 0xdc00))
                    next_end += 6
                m = unichr(uni)
            except ValueError:
                raise ValueError(errmsg(msg, s, end))
            end = next_end
        _append(m)
    return u''.join(chunks), end


# Use speedup if available
scanstring = c_scanstring or py_scanstring

WHITESPACE = re.compile(r'[ \t\n\r]*', FLAGS)
WHITESPACE_STR = ' \t\n\r'

def JSONObject((s, end), encoding, strict, scan_once, object_hook, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    pairs = {}
    nextchar = s[end:end + 1]
    # Normally we expect nextchar == '"'
    if nextchar != '"':
        if nextchar in _ws:
            end = _w(s, end).end()
            nextchar = s[end:end + 1]
        # Trivial empty object
        if nextchar == '}':
            return pairs, end + 1
        elif nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end))
    end += 1
    while True:
        key, end = scanstring(s, end, encoding, strict)

        # To skip some function call overhead we optimize the fast paths where
        # the JSON key separator is ": " or just ":".
        if s[end:end + 1] != ':':
            end = _w(s, end).end()
            if s[end:end + 1] != ':':
                raise ValueError(errmsg("Expecting : delimiter", s, end))

        end += 1

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        pairs[key] = value

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end = _w(s, end + 1).end()
                nextchar = s[end]
        except IndexError:
            nextchar = ''
        end += 1

        if nextchar == '}':
            break
        elif nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end - 1))

        try:
            nextchar = s[end]
            if nextchar in _ws:
                end += 1
                nextchar = s[end]
                if nextchar in _ws:
                    end = _w(s, end + 1).end()
                    nextchar = s[end]
        except IndexError:
            nextchar = ''

        end += 1
        if nextchar != '"':
            raise ValueError(errmsg("Expecting property name", s, end - 1))

    if object_hook is not None:
        pairs = object_hook(pairs)
    return pairs, end

def JSONArray((s, end), scan_once, _w=WHITESPACE.match, _ws=WHITESPACE_STR):
    values = []
    nextchar = s[end:end + 1]
    if nextchar in _ws:
        end = _w(s, end + 1).end()
        nextchar = s[end:end + 1]
    # Look-ahead for trivial empty array
    if nextchar == ']':
        return values, end + 1
    _append = values.append
    while True:
        try:
            value, end = scan_once(s, end)
        except StopIteration:
            raise ValueError(errmsg("Expecting object", s, end))
        _append(value)
        nextchar = s[end:end + 1]
        if nextchar in _ws:
            end = _w(s, end + 1).end()
            nextchar = s[end:end + 1]
        end += 1
        if nextchar == ']':
            break
        elif nextchar != ',':
            raise ValueError(errmsg("Expecting , delimiter", s, end))

        try:
            if s[end] in _ws:
                end += 1
                if s[end] in _ws:
                    end = _w(s, end + 1).end()
        except IndexError:
            pass

    return values, end

class JSONDecoder(object):
    """Simple JSON <http://json.org> decoder

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | JSON          | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | unicode           |
    +---------------+-------------------+
    | number (int)  | int, long         |
    +---------------+-------------------+
    | number (real) | float             |
    +---------------+-------------------+
    | true          | True              |
    +---------------+-------------------+
    | false         | False             |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+

    It also understands ``NaN``, ``Infinity``, and ``-Infinity`` as
    their corresponding ``float`` values, which is outside the JSON spec.

    """

    def __init__(self, encoding=None, object_hook=None, parse_float=None,
            parse_int=None, parse_constant=None, strict=True):
        """``encoding`` determines the encoding used to interpret any ``str``
        objects decoded by this instance (utf-8 by default).  It has no
        effect when decoding ``unicode`` objects.

        Note that currently only encodings that are a superset of ASCII work,
        strings of other encodings should be passed in as ``unicode``.

        ``object_hook``, if specified, will be called with the result
        of every JSON object decoded and its return value will be used in
        place of the given ``dict``.  This can be used to provide custom
        deserializations (e.g. to support JSON-RPC class hinting).

        ``parse_float``, if specified, will be called with the string
        of every JSON float to be decoded. By default this is equivalent to
        float(num_str). This can be used to use another datatype or parser
        for JSON floats (e.g. decimal.Decimal).

        ``parse_int``, if specified, will be called with the string
        of every JSON int to be decoded. By default this is equivalent to
        int(num_str). This can be used to use another datatype or parser
        for JSON integers (e.g. float).

        ``parse_constant``, if specified, will be called with one of the
        following strings: -Infinity, Infinity, NaN.
        This can be used to raise an exception if invalid JSON numbers
        are encountered.

        """
        self.encoding = encoding
        self.object_hook = object_hook
        self.parse_float = parse_float or float
        self.parse_int = parse_int or int
        self.parse_constant = parse_constant or _CONSTANTS.__getitem__
        self.strict = strict
        self.parse_object = JSONObject
        self.parse_array = JSONArray
        self.parse_string = scanstring
        self.scan_once = make_scanner(self)

    def decode(self, s, _w=WHITESPACE.match):
        """Return the Python representation of ``s`` (a ``str`` or ``unicode``
        instance containing a JSON document)

        """
        obj, end = self.raw_decode(s, idx=_w(s, 0).end())
        end = _w(s, end).end()
        if end != len(s):
            raise ValueError(errmsg("Extra data", s, end, len(s)))
        return obj

    def raw_decode(self, s, idx=0):
        """Decode a JSON document from ``s`` (a ``str`` or ``unicode`` beginning
        with a JSON document) and return a 2-tuple of the Python
        representation and the index in ``s`` where the document ended.

        This can be used to decode a JSON document from a string that may
        have extraneous data at the end.

        """
        try:
            obj, end = self.scan_once(s, idx)
        except StopIteration:
            raise ValueError("No JSON object could be decoded")
        return obj, end

########NEW FILE########
__FILENAME__ = encoder
"""Implementation of JSONEncoder
"""
import re

try:
    from simplejson._speedups import encode_basestring_ascii as c_encode_basestring_ascii
except ImportError:
    c_encode_basestring_ascii = None
try:
    from simplejson._speedups import make_encoder as c_make_encoder
except ImportError:
    c_make_encoder = None

ESCAPE = re.compile(r'[\x00-\x1f\\"\b\f\n\r\t]')
ESCAPE_ASCII = re.compile(r'([\\"]|[^\ -~])')
HAS_UTF8 = re.compile(r'[\x80-\xff]')
ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}
for i in range(0x20):
    ESCAPE_DCT.setdefault(chr(i), '\\u%04x' % (i,))

# Assume this produces an infinity on all machines (probably not guaranteed)
INFINITY = float('1e66666')
FLOAT_REPR = repr

def encode_basestring(s):
    """Return a JSON representation of a Python string

    """
    def replace(match):
        return ESCAPE_DCT[match.group(0)]
    return '"' + ESCAPE.sub(replace, s) + '"'


def py_encode_basestring_ascii(s):
    if isinstance(s, str) and HAS_UTF8.search(s) is not None:
        s = s.decode('utf-8')
    def replace(match):
        s = match.group(0)
        try:
            return ESCAPE_DCT[s]
        except KeyError:
            n = ord(s)
            if n < 0x10000:
                return '\\u%04x' % (n,)
            else:
                # surrogate pair
                n -= 0x10000
                s1 = 0xd800 | ((n >> 10) & 0x3ff)
                s2 = 0xdc00 | (n & 0x3ff)
                return '\\u%04x\\u%04x' % (s1, s2)
    return '"' + str(ESCAPE_ASCII.sub(replace, s)) + '"'


encode_basestring_ascii = c_encode_basestring_ascii or py_encode_basestring_ascii

class JSONEncoder(object):
    """Extensible JSON <http://json.org> encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | JSON          |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list, tuple       | array         |
    +-------------------+---------------+
    | str, unicode      | string        |
    +-------------------+---------------+
    | int, long, float  | number        |
    +-------------------+---------------+
    | True              | true          |
    +-------------------+---------------+
    | False             | false         |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+

    To extend this to recognize other objects, subclass and implement a
    ``.default()`` method with another method that returns a serializable
    object for ``o`` if possible, otherwise it should call the superclass
    implementation (to raise ``TypeError``).

    """
    item_separator = ', '
    key_separator = ': '
    def __init__(self, skipkeys=False, ensure_ascii=True,
            check_circular=True, allow_nan=True, sort_keys=False,
            indent=None, separators=None, encoding='utf-8', default=None):
        """Constructor for JSONEncoder, with sensible defaults.

        If skipkeys is False, then it is a TypeError to attempt
        encoding of keys that are not str, int, long, float or None.  If
        skipkeys is True, such items are simply skipped.

        If ensure_ascii is True, the output is guaranteed to be str
        objects with all incoming unicode characters escaped.  If
        ensure_ascii is false, the output will be unicode object.

        If check_circular is True, then lists, dicts, and custom encoded
        objects will be checked for circular references during encoding to
        prevent an infinite recursion (which would cause an OverflowError).
        Otherwise, no such check takes place.

        If allow_nan is True, then NaN, Infinity, and -Infinity will be
        encoded as such.  This behavior is not JSON specification compliant,
        but is consistent with most JavaScript based encoders and decoders.
        Otherwise, it will be a ValueError to encode such floats.

        If sort_keys is True, then the output of dictionaries will be
        sorted by key; this is useful for regression tests to ensure
        that JSON serializations can be compared on a day-to-day basis.

        If indent is a non-negative integer, then JSON array
        elements and object members will be pretty-printed with that
        indent level.  An indent level of 0 will only insert newlines.
        None is the most compact representation.

        If specified, separators should be a (item_separator, key_separator)
        tuple.  The default is (', ', ': ').  To get the most compact JSON
        representation you should specify (',', ':') to eliminate whitespace.

        If specified, default is a function that gets called for objects
        that can't otherwise be serialized.  It should return a JSON encodable
        version of the object or raise a ``TypeError``.

        If encoding is not None, then all input strings will be
        transformed into unicode using that encoding prior to JSON-encoding.
        The default is UTF-8.

        """

        self.skipkeys = skipkeys
        self.ensure_ascii = ensure_ascii
        self.check_circular = check_circular
        self.allow_nan = allow_nan
        self.sort_keys = sort_keys
        self.indent = indent
        if separators is not None:
            self.item_separator, self.key_separator = separators
        if default is not None:
            self.default = default
        self.encoding = encoding

    def default(self, o):
        """Implement this method in a subclass such that it returns
        a serializable object for ``o``, or calls the base implementation
        (to raise a ``TypeError``).

        For example, to support arbitrary iterators, you could
        implement default like this::

            def default(self, o):
                try:
                    iterable = iter(o)
                except TypeError:
                    pass
                else:
                    return list(iterable)
                return JSONEncoder.default(self, o)

        """
        raise TypeError("%r is not JSON serializable" % (o,))

    def encode(self, o):
        """Return a JSON string representation of a Python data structure.

        >>> JSONEncoder().encode({"foo": ["bar", "baz"]})
        '{"foo": ["bar", "baz"]}'

        """
        # This is for extremely simple cases and benchmarks.
        if isinstance(o, basestring):
            if isinstance(o, str):
                _encoding = self.encoding
                if (_encoding is not None
                        and not (_encoding == 'utf-8')):
                    o = o.decode(_encoding)
            if self.ensure_ascii:
                return encode_basestring_ascii(o)
            else:
                return encode_basestring(o)
        # This doesn't pass the iterator directly to ''.join() because the
        # exceptions aren't as detailed.  The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        chunks = self.iterencode(o, _one_shot=True)
        if not isinstance(chunks, (list, tuple)):
            chunks = list(chunks)
        return ''.join(chunks)

    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None
        if self.ensure_ascii:
            _encoder = encode_basestring_ascii
        else:
            _encoder = encode_basestring
        if self.encoding != 'utf-8':
            def _encoder(o, _orig_encoder=_encoder, _encoding=self.encoding):
                if isinstance(o, str):
                    o = o.decode(_encoding)
                return _orig_encoder(o)

        def floatstr(o, allow_nan=self.allow_nan, _repr=FLOAT_REPR, _inf=INFINITY, _neginf=-INFINITY):
            # Check for specials.  Note that this type of test is processor- and/or
            # platform-specific, so do tests which don't depend on the internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError("Out of range float values are not JSON compliant: %r"
                    % (o,))

            return text


        if _one_shot and c_make_encoder is not None and not self.indent and not self.sort_keys:
            _iterencode = c_make_encoder(
                markers, self.default, _encoder, self.indent,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, self.allow_nan)
        else:
            _iterencode = _make_iterencode(
                markers, self.default, _encoder, self.indent, floatstr,
                self.key_separator, self.item_separator, self.sort_keys,
                self.skipkeys, _one_shot)
        return _iterencode(o, 0)

def _make_iterencode(markers, _default, _encoder, _indent, _floatstr, _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
        ## HACK: hand-optimized bytecode; turn globals into locals
        False=False,
        True=True,
        ValueError=ValueError,
        basestring=basestring,
        dict=dict,
        float=float,
        id=id,
        int=int,
        isinstance=isinstance,
        list=list,
        long=long,
        str=str,
        tuple=tuple,
    ):

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '[]'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '['
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, basestring):
                yield buf + _encoder(value)
            elif value is None:
                yield buf + 'null'
            elif value is True:
                yield buf + 'true'
            elif value is False:
                yield buf + 'false'
            elif isinstance(value, (int, long)):
                yield buf + str(value)
            elif isinstance(value, float):
                yield buf + _floatstr(value)
            else:
                yield buf
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (' ' * (_indent * _current_indent_level))
        yield ']'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
            item_separator = _item_separator + newline_indent
            yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _sort_keys:
            items = dct.items()
            items.sort(key=lambda kv: kv[0])
        else:
            items = dct.iteritems()
        for key, value in items:
            if isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = _floatstr(key)
            elif isinstance(key, (int, long)):
                key = str(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif _skipkeys:
                continue
            else:
                raise TypeError("key %r is not a string" % (key,))
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            yield _key_separator
            if isinstance(value, basestring):
                yield _encoder(value)
            elif value is None:
                yield 'null'
            elif value is True:
                yield 'true'
            elif value is False:
                yield 'false'
            elif isinstance(value, (int, long)):
                yield str(value)
            elif isinstance(value, float):
                yield _floatstr(value)
            else:
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (' ' * (_indent * _current_indent_level))
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance(o, basestring):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield _floatstr(o)
        elif isinstance(o, (list, tuple)):
            for chunk in _iterencode_list(o, _current_indent_level):
                yield chunk
        elif isinstance(o, dict):
            for chunk in _iterencode_dict(o, _current_indent_level):
                yield chunk
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            o = _default(o)
            for chunk in _iterencode(o, _current_indent_level):
                yield chunk
            if markers is not None:
                del markers[markerid]

    return _iterencode

########NEW FILE########
__FILENAME__ = scanner
"""JSON token scanner
"""
import re
try:
    from simplejson._speedups import make_scanner as c_make_scanner
except ImportError:
    c_make_scanner = None

__all__ = ['make_scanner']

NUMBER_RE = re.compile(
    r'(-?(?:0|[1-9]\d*))(\.\d+)?([eE][-+]?\d+)?',
    (re.VERBOSE | re.MULTILINE | re.DOTALL))

def py_make_scanner(context):
    parse_object = context.parse_object
    parse_array = context.parse_array
    parse_string = context.parse_string
    match_number = NUMBER_RE.match
    encoding = context.encoding
    strict = context.strict
    parse_float = context.parse_float
    parse_int = context.parse_int
    parse_constant = context.parse_constant
    object_hook = context.object_hook

    def _scan_once(string, idx):
        try:
            nextchar = string[idx]
        except IndexError:
            raise StopIteration

        if nextchar == '"':
            return parse_string(string, idx + 1, encoding, strict)
        elif nextchar == '{':
            return parse_object((string, idx + 1), encoding, strict, _scan_once, object_hook)
        elif nextchar == '[':
            return parse_array((string, idx + 1), _scan_once)
        elif nextchar == 'n' and string[idx:idx + 4] == 'null':
            return None, idx + 4
        elif nextchar == 't' and string[idx:idx + 4] == 'true':
            return True, idx + 4
        elif nextchar == 'f' and string[idx:idx + 5] == 'false':
            return False, idx + 5

        m = match_number(string, idx)
        if m is not None:
            integer, frac, exp = m.groups()
            if frac or exp:
                res = parse_float(integer + (frac or '') + (exp or ''))
            else:
                res = parse_int(integer)
            return res, m.end()
        elif nextchar == 'N' and string[idx:idx + 3] == 'NaN':
            return parse_constant('NaN'), idx + 3
        elif nextchar == 'I' and string[idx:idx + 8] == 'Infinity':
            return parse_constant('Infinity'), idx + 8
        elif nextchar == '-' and string[idx:idx + 9] == '-Infinity':
            return parse_constant('-Infinity'), idx + 9
        else:
            raise StopIteration

    return _scan_once

make_scanner = c_make_scanner or py_make_scanner

########NEW FILE########
__FILENAME__ = test_decode
import decimal
from unittest import TestCase

import simplejson as S

class TestDecode(TestCase):
    def test_decimal(self):
        rval = S.loads('1.1', parse_float=decimal.Decimal)
        self.assert_(isinstance(rval, decimal.Decimal))
        self.assertEquals(rval, decimal.Decimal('1.1'))

    def test_float(self):
        rval = S.loads('1', parse_int=float)
        self.assert_(isinstance(rval, float))
        self.assertEquals(rval, 1.0)

    def test_decoder_optimizations(self):
        # Several optimizations were made that skip over calls to
        # the whitespace regex, so this test is designed to try and
        # exercise the uncommon cases. The array cases are already covered.
        rval = S.loads('{   "key"    :    "value"    ,  "k":"v"    }')
        self.assertEquals(rval, {"key":"value", "k":"v"})

########NEW FILE########
__FILENAME__ = test_default
from unittest import TestCase

import simplejson as S

class TestDefault(TestCase):
    def test_default(self):
        self.assertEquals(
            S.dumps(type, default=repr),
            S.dumps(repr(type)))

########NEW FILE########
__FILENAME__ = test_dump
from unittest import TestCase
from cStringIO import StringIO

import simplejson as S

class TestDump(TestCase):
    def test_dump(self):
        sio = StringIO()
        S.dump({}, sio)
        self.assertEquals(sio.getvalue(), '{}')

    def test_dumps(self):
        self.assertEquals(S.dumps({}), '{}')

########NEW FILE########
__FILENAME__ = test_encode_basestring_ascii
from unittest import TestCase

import simplejson.encoder

CASES = [
    (u'/\\"\ucafe\ubabe\uab98\ufcde\ubcda\uef4a\x08\x0c\n\r\t`1~!@#$%^&*()_+-=[]{}|;:\',./<>?', '"/\\\\\\"\\ucafe\\ubabe\\uab98\\ufcde\\ubcda\\uef4a\\b\\f\\n\\r\\t`1~!@#$%^&*()_+-=[]{}|;:\',./<>?"'),
    (u'\u0123\u4567\u89ab\ucdef\uabcd\uef4a', '"\\u0123\\u4567\\u89ab\\ucdef\\uabcd\\uef4a"'),
    (u'controls', '"controls"'),
    (u'\x08\x0c\n\r\t', '"\\b\\f\\n\\r\\t"'),
    (u'{"object with 1 member":["array with 1 element"]}', '"{\\"object with 1 member\\":[\\"array with 1 element\\"]}"'),
    (u' s p a c e d ', '" s p a c e d "'),
    (u'\U0001d120', '"\\ud834\\udd20"'),
    (u'\u03b1\u03a9', '"\\u03b1\\u03a9"'),
    ('\xce\xb1\xce\xa9', '"\\u03b1\\u03a9"'),
    (u'\u03b1\u03a9', '"\\u03b1\\u03a9"'),
    ('\xce\xb1\xce\xa9', '"\\u03b1\\u03a9"'),
    (u'\u03b1\u03a9', '"\\u03b1\\u03a9"'),
    (u'\u03b1\u03a9', '"\\u03b1\\u03a9"'),
    (u"`1~!@#$%^&*()_+-={':[,]}|;.</>?", '"`1~!@#$%^&*()_+-={\':[,]}|;.</>?"'),
    (u'\x08\x0c\n\r\t', '"\\b\\f\\n\\r\\t"'),
    (u'\u0123\u4567\u89ab\ucdef\uabcd\uef4a', '"\\u0123\\u4567\\u89ab\\ucdef\\uabcd\\uef4a"'),
]

class TestEncodeBaseStringAscii(TestCase):
    def test_py_encode_basestring_ascii(self):
        self._test_encode_basestring_ascii(simplejson.encoder.py_encode_basestring_ascii)

    def test_c_encode_basestring_ascii(self):
        if not simplejson.encoder.c_encode_basestring_ascii:
            return
        self._test_encode_basestring_ascii(simplejson.encoder.c_encode_basestring_ascii)

    def _test_encode_basestring_ascii(self, encode_basestring_ascii):
        fname = encode_basestring_ascii.__name__
        for input_string, expect in CASES:
            result = encode_basestring_ascii(input_string)
            self.assertEquals(result, expect,
                '%r != %r for %s(%r)' % (result, expect, fname, input_string))

########NEW FILE########
__FILENAME__ = test_fail
from unittest import TestCase

import simplejson as S

# Fri Dec 30 18:57:26 2005
JSONDOCS = [
    # http://json.org/JSON_checker/test/fail1.json
    '"A JSON payload should be an object or array, not a string."',
    # http://json.org/JSON_checker/test/fail2.json
    '["Unclosed array"',
    # http://json.org/JSON_checker/test/fail3.json
    '{unquoted_key: "keys must be quoted}',
    # http://json.org/JSON_checker/test/fail4.json
    '["extra comma",]',
    # http://json.org/JSON_checker/test/fail5.json
    '["double extra comma",,]',
    # http://json.org/JSON_checker/test/fail6.json
    '[   , "<-- missing value"]',
    # http://json.org/JSON_checker/test/fail7.json
    '["Comma after the close"],',
    # http://json.org/JSON_checker/test/fail8.json
    '["Extra close"]]',
    # http://json.org/JSON_checker/test/fail9.json
    '{"Extra comma": true,}',
    # http://json.org/JSON_checker/test/fail10.json
    '{"Extra value after close": true} "misplaced quoted value"',
    # http://json.org/JSON_checker/test/fail11.json
    '{"Illegal expression": 1 + 2}',
    # http://json.org/JSON_checker/test/fail12.json
    '{"Illegal invocation": alert()}',
    # http://json.org/JSON_checker/test/fail13.json
    '{"Numbers cannot have leading zeroes": 013}',
    # http://json.org/JSON_checker/test/fail14.json
    '{"Numbers cannot be hex": 0x14}',
    # http://json.org/JSON_checker/test/fail15.json
    '["Illegal backslash escape: \\x15"]',
    # http://json.org/JSON_checker/test/fail16.json
    '["Illegal backslash escape: \\\'"]',
    # http://json.org/JSON_checker/test/fail17.json
    '["Illegal backslash escape: \\017"]',
    # http://json.org/JSON_checker/test/fail18.json
    '[[[[[[[[[[[[[[[[[[[["Too deep"]]]]]]]]]]]]]]]]]]]]',
    # http://json.org/JSON_checker/test/fail19.json
    '{"Missing colon" null}',
    # http://json.org/JSON_checker/test/fail20.json
    '{"Double colon":: null}',
    # http://json.org/JSON_checker/test/fail21.json
    '{"Comma instead of colon", null}',
    # http://json.org/JSON_checker/test/fail22.json
    '["Colon instead of comma": false]',
    # http://json.org/JSON_checker/test/fail23.json
    '["Bad value", truth]',
    # http://json.org/JSON_checker/test/fail24.json
    "['single quote']",
    # http://code.google.com/p/simplejson/issues/detail?id=3
    u'["A\u001FZ control characters in string"]',
]

SKIPS = {
    1: "why not have a string payload?",
    18: "spec doesn't specify any nesting limitations",
}

class TestFail(TestCase):
    def test_failures(self):
        for idx, doc in enumerate(JSONDOCS):
            idx = idx + 1
            if idx in SKIPS:
                S.loads(doc)
                continue
            try:
                S.loads(doc)
            except ValueError:
                pass
            else:
                self.fail("Expected failure for fail%d.json: %r" % (idx, doc))

########NEW FILE########
__FILENAME__ = test_float
import math
from unittest import TestCase

import simplejson as S

class TestFloat(TestCase):
    def test_floats(self):
        for num in [1617161771.7650001, math.pi, math.pi**100, math.pi**-100, 3.1]:
            self.assertEquals(float(S.dumps(num)), num)
            self.assertEquals(S.loads(S.dumps(num)), num)

    def test_ints(self):
        for num in [1, 1L, 1<<32, 1<<64]:
            self.assertEquals(S.dumps(num), str(num))
            self.assertEquals(int(S.dumps(num)), num)

########NEW FILE########
__FILENAME__ = test_indent
from unittest import TestCase

import simplejson as S
import textwrap

class TestIndent(TestCase):
    def test_indent(self):
        h = [['blorpie'], ['whoops'], [], 'd-shtaeou', 'd-nthiouh', 'i-vhbjkhnth',
             {'nifty': 87}, {'field': 'yes', 'morefield': False} ]

        expect = textwrap.dedent("""\
        [
          [
            "blorpie"
          ],
          [
            "whoops"
          ],
          [],
          "d-shtaeou",
          "d-nthiouh",
          "i-vhbjkhnth",
          {
            "nifty": 87
          },
          {
            "field": "yes",
            "morefield": false
          }
        ]""")


        d1 = S.dumps(h)
        d2 = S.dumps(h, indent=2, sort_keys=True, separators=(',', ': '))

        h1 = S.loads(d1)
        h2 = S.loads(d2)

        self.assertEquals(h1, h)
        self.assertEquals(h2, h)
        self.assertEquals(d2, expect)

########NEW FILE########
__FILENAME__ = test_pass1
from unittest import TestCase

import simplejson as S

# from http://json.org/JSON_checker/test/pass1.json
JSON = r'''
[
    "JSON Test Pattern pass1",
    {"object with 1 member":["array with 1 element"]},
    {},
    [],
    -42,
    true,
    false,
    null,
    {
        "integer": 1234567890,
        "real": -9876.543210,
        "e": 0.123456789e-12,
        "E": 1.234567890E+34,
        "":  23456789012E666,
        "zero": 0,
        "one": 1,
        "space": " ",
        "quote": "\"",
        "backslash": "\\",
        "controls": "\b\f\n\r\t",
        "slash": "/ & \/",
        "alpha": "abcdefghijklmnopqrstuvwyz",
        "ALPHA": "ABCDEFGHIJKLMNOPQRSTUVWYZ",
        "digit": "0123456789",
        "special": "`1~!@#$%^&*()_+-={':[,]}|;.</>?",
        "hex": "\u0123\u4567\u89AB\uCDEF\uabcd\uef4A",
        "true": true,
        "false": false,
        "null": null,
        "array":[  ],
        "object":{  },
        "address": "50 St. James Street",
        "url": "http://www.JSON.org/",
        "comment": "// /* <!-- --",
        "# -- --> */": " ",
        " s p a c e d " :[1,2 , 3

,

4 , 5        ,          6           ,7        ],
        "compact": [1,2,3,4,5,6,7],
        "jsontext": "{\"object with 1 member\":[\"array with 1 element\"]}",
        "quotes": "&#34; \u0022 %22 0x22 034 &#x22;",
        "\/\\\"\uCAFE\uBABE\uAB98\uFCDE\ubcda\uef4A\b\f\n\r\t`1~!@#$%^&*()_+-=[]{}|;:',./<>?"
: "A key can be any string"
    },
    0.5 ,98.6
,
99.44
,

1066


,"rosebud"]
'''

class TestPass1(TestCase):
    def test_parse(self):
        # test in/out equivalence and parsing
        res = S.loads(JSON)
        out = S.dumps(res)
        self.assertEquals(res, S.loads(out))
        try:
            S.dumps(res, allow_nan=False)
        except ValueError:
            pass
        else:
            self.fail("23456789012E666 should be out of range")

########NEW FILE########
__FILENAME__ = test_pass2
from unittest import TestCase
import simplejson as S

# from http://json.org/JSON_checker/test/pass2.json
JSON = r'''
[[[[[[[[[[[[[[[[[[["Not too deep"]]]]]]]]]]]]]]]]]]]
'''

class TestPass2(TestCase):
    def test_parse(self):
        # test in/out equivalence and parsing
        res = S.loads(JSON)
        out = S.dumps(res)
        self.assertEquals(res, S.loads(out))

########NEW FILE########
__FILENAME__ = test_pass3
from unittest import TestCase

import simplejson as S

# from http://json.org/JSON_checker/test/pass3.json
JSON = r'''
{
    "JSON Test Pattern pass3": {
        "The outermost value": "must be an object or array.",
        "In this test": "It is an object."
    }
}
'''

class TestPass3(TestCase):
    def test_parse(self):
        # test in/out equivalence and parsing
        res = S.loads(JSON)
        out = S.dumps(res)
        self.assertEquals(res, S.loads(out))

########NEW FILE########
__FILENAME__ = test_recursion
from unittest import TestCase

import simplejson as S

class JSONTestObject:
    pass

class RecursiveJSONEncoder(S.JSONEncoder):
    recurse = False
    def default(self, o):
        if o is JSONTestObject:
            if self.recurse:
                return [JSONTestObject]
            else:
                return 'JSONTestObject'
        return S.JSONEncoder.default(o)

class TestRecursion(TestCase):
    def test_listrecursion(self):
        x = []
        x.append(x)
        try:
            S.dumps(x)
        except ValueError:
            pass
        else:
            self.fail("didn't raise ValueError on list recursion")
        x = []
        y = [x]
        x.append(y)
        try:
            S.dumps(x)
        except ValueError:
            pass
        else:
            self.fail("didn't raise ValueError on alternating list recursion")
        y = []
        x = [y, y]
        # ensure that the marker is cleared
        S.dumps(x)

    def test_dictrecursion(self):
        x = {}
        x["test"] = x
        try:
            S.dumps(x)
        except ValueError:
            pass
        else:
            self.fail("didn't raise ValueError on dict recursion")
        x = {}
        y = {"a": x, "b": x}
        # ensure that the marker is cleared
        S.dumps(x)

    def test_defaultrecursion(self):
        enc = RecursiveJSONEncoder()
        self.assertEquals(enc.encode(JSONTestObject), '"JSONTestObject"')
        enc.recurse = True
        try:
            enc.encode(JSONTestObject)
        except ValueError:
            pass
        else:
            self.fail("didn't raise ValueError on default recursion")

########NEW FILE########
__FILENAME__ = test_scanstring
import sys
import decimal
from unittest import TestCase

import simplejson.decoder

class TestScanString(TestCase):
    def test_py_scanstring(self):
        self._test_scanstring(simplejson.decoder.py_scanstring)

    def test_c_scanstring(self):
        if not simplejson.decoder.c_scanstring:
            return
        self._test_scanstring(simplejson.decoder.c_scanstring)

    def _test_scanstring(self, scanstring):
        self.assertEquals(
            scanstring('"z\\ud834\\udd20x"', 1, None, True),
            (u'z\U0001d120x', 16))

        if sys.maxunicode == 65535:
            self.assertEquals(
                scanstring(u'"z\U0001d120x"', 1, None, True),
                (u'z\U0001d120x', 6))
        else:
            self.assertEquals(
                scanstring(u'"z\U0001d120x"', 1, None, True),
                (u'z\U0001d120x', 5))

        self.assertEquals(
            scanstring('"\\u007b"', 1, None, True),
            (u'{', 8))

        self.assertEquals(
            scanstring('"A JSON payload should be an object or array, not a string."', 1, None, True),
            (u'A JSON payload should be an object or array, not a string.', 60))

        self.assertEquals(
            scanstring('["Unclosed array"', 2, None, True),
            (u'Unclosed array', 17))

        self.assertEquals(
            scanstring('["extra comma",]', 2, None, True),
            (u'extra comma', 14))

        self.assertEquals(
            scanstring('["double extra comma",,]', 2, None, True),
            (u'double extra comma', 21))

        self.assertEquals(
            scanstring('["Comma after the close"],', 2, None, True),
            (u'Comma after the close', 24))

        self.assertEquals(
            scanstring('["Extra close"]]', 2, None, True),
            (u'Extra close', 14))

        self.assertEquals(
            scanstring('{"Extra comma": true,}', 2, None, True),
            (u'Extra comma', 14))

        self.assertEquals(
            scanstring('{"Extra value after close": true} "misplaced quoted value"', 2, None, True),
            (u'Extra value after close', 26))

        self.assertEquals(
            scanstring('{"Illegal expression": 1 + 2}', 2, None, True),
            (u'Illegal expression', 21))

        self.assertEquals(
            scanstring('{"Illegal invocation": alert()}', 2, None, True),
            (u'Illegal invocation', 21))

        self.assertEquals(
            scanstring('{"Numbers cannot have leading zeroes": 013}', 2, None, True),
            (u'Numbers cannot have leading zeroes', 37))

        self.assertEquals(
            scanstring('{"Numbers cannot be hex": 0x14}', 2, None, True),
            (u'Numbers cannot be hex', 24))

        self.assertEquals(
            scanstring('[[[[[[[[[[[[[[[[[[[["Too deep"]]]]]]]]]]]]]]]]]]]]', 21, None, True),
            (u'Too deep', 30))

        self.assertEquals(
            scanstring('{"Missing colon" null}', 2, None, True),
            (u'Missing colon', 16))

        self.assertEquals(
            scanstring('{"Double colon":: null}', 2, None, True),
            (u'Double colon', 15))

        self.assertEquals(
            scanstring('{"Comma instead of colon", null}', 2, None, True),
            (u'Comma instead of colon', 25))

        self.assertEquals(
            scanstring('["Colon instead of comma": false]', 2, None, True),
            (u'Colon instead of comma', 25))

        self.assertEquals(
            scanstring('["Bad value", truth]', 2, None, True),
            (u'Bad value', 12))

########NEW FILE########
__FILENAME__ = test_separators
import textwrap
from unittest import TestCase

import simplejson as S


class TestSeparators(TestCase):
    def test_separators(self):
        h = [['blorpie'], ['whoops'], [], 'd-shtaeou', 'd-nthiouh', 'i-vhbjkhnth',
             {'nifty': 87}, {'field': 'yes', 'morefield': False} ]

        expect = textwrap.dedent("""\
        [
          [
            "blorpie"
          ] ,
          [
            "whoops"
          ] ,
          [] ,
          "d-shtaeou" ,
          "d-nthiouh" ,
          "i-vhbjkhnth" ,
          {
            "nifty" : 87
          } ,
          {
            "field" : "yes" ,
            "morefield" : false
          }
        ]""")


        d1 = S.dumps(h)
        d2 = S.dumps(h, indent=2, sort_keys=True, separators=(' ,', ' : '))

        h1 = S.loads(d1)
        h2 = S.loads(d2)

        self.assertEquals(h1, h)
        self.assertEquals(h2, h)
        self.assertEquals(d2, expect)

########NEW FILE########
__FILENAME__ = test_unicode
from unittest import TestCase

import simplejson as S

class TestUnicode(TestCase):
    def test_encoding1(self):
        encoder = S.JSONEncoder(encoding='utf-8')
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        s = u.encode('utf-8')
        ju = encoder.encode(u)
        js = encoder.encode(s)
        self.assertEquals(ju, js)

    def test_encoding2(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        s = u.encode('utf-8')
        ju = S.dumps(u, encoding='utf-8')
        js = S.dumps(s, encoding='utf-8')
        self.assertEquals(ju, js)

    def test_encoding3(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        j = S.dumps(u)
        self.assertEquals(j, '"\\u03b1\\u03a9"')

    def test_encoding4(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        j = S.dumps([u])
        self.assertEquals(j, '["\\u03b1\\u03a9"]')

    def test_encoding5(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        j = S.dumps(u, ensure_ascii=False)
        self.assertEquals(j, u'"%s"' % (u,))

    def test_encoding6(self):
        u = u'\N{GREEK SMALL LETTER ALPHA}\N{GREEK CAPITAL LETTER OMEGA}'
        j = S.dumps([u], ensure_ascii=False)
        self.assertEquals(j, u'["%s"]' % (u,))

    def test_big_unicode_encode(self):
        u = u'\U0001d120'
        self.assertEquals(S.dumps(u), '"\\ud834\\udd20"')
        self.assertEquals(S.dumps(u, ensure_ascii=False), u'"\U0001d120"')

    def test_big_unicode_decode(self):
        u = u'z\U0001d120x'
        self.assertEquals(S.loads('"' + u + '"'), u)
        self.assertEquals(S.loads('"z\\ud834\\udd20x"'), u)

    def test_unicode_decode(self):
        for i in range(0, 0xd7ff):
            u = unichr(i)
            json = '"\\u%04x"' % (i,)
            self.assertEquals(S.loads(json), u)

    def test_default_encoding(self):
        self.assertEquals(S.loads(u'{"a": "\xe9"}'.encode('utf-8')),
            {'a': u'\xe9'})

########NEW FILE########
__FILENAME__ = tool
r"""Using simplejson from the shell to validate and
pretty-print::

    $ echo '{"json":"obj"}' | python -msimplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -msimplejson.tool
    Expecting property name: line 1 column 2 (char 2)
"""
import simplejson

def main():
    import sys
    if len(sys.argv) == 1:
        infile = sys.stdin
        outfile = sys.stdout
    elif len(sys.argv) == 2:
        infile = open(sys.argv[1], 'rb')
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        infile = open(sys.argv[1], 'rb')
        outfile = open(sys.argv[2], 'wb')
    else:
        raise SystemExit("%s [infile [outfile]]" % (sys.argv[0],))
    try:
        obj = simplejson.load(infile)
    except ValueError, e:
        raise SystemExit(e)
    simplejson.dump(obj, outfile, sort_keys=True, indent=4)
    outfile.write('\n')


if __name__ == '__main__':
    main()

########NEW FILE########
