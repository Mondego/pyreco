__FILENAME__ = admin
import app.basic
import tornado.web
import settings
from datetime import datetime, date
import logging
import json
import requests

from lib import companiesdb
from lib import hackpad
from lib import postsdb
from lib import userdb
from lib import disqus
from lib import emailsdb
from disqusapi import DisqusAPI

############################
# ADMIN NEWSLETTER
# /admin/newsletter
############################
class DailyEmail(app.basic.BaseHandler):
  def get(self):
    posts = postsdb.get_hot_posts()
    has_previewed = self.get_argument("preview", False)
    recipients = userdb.get_newsletter_recipients()
    #on this page, you'll choose from hot posts and POST the selections to the email form`
    self.render('admin/daily_email.html')
  
  def post(self):
    if not self.current_user_can('send_daily_email'):
      raise tornado.web.HTTPError(401)
      
    action = self.get_argument('action', None)
    
    if not action:
      return self.write("Select an action")
    
    if action == "setup_email":
      posts = postsdb.get_hot_posts_by_day(datetime.today())
      slugs = []
      for i, post in enumerate(posts):
        if i < 5:
          slugs.append(post['slug'])
      response1 = emailsdb.construct_daily_email(slugs)
      print response1
      
      response2 = emailsdb.setup_email_list()
      print response2
    
    if action == "add_list_to_email":
      response3 = emailsdb.add_list_to_email()
      print response3
    
    if action == "send_email":
      response4 = emailsdb.send_email()
      print response4

class DailyEmailHistory(app.basic.BaseHandler):
  def get(self):
    history = emailsdb.get_daily_email_log()
    self.render('admin/daily_email_history.html', history=history)
    
    
###########################
### ADMIN COMPANY
### /admin/company
###########################
class AdminCompany(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self):
    if self.current_user not in settings.get('staff'):
      self.redirect('/')
    else:
      slug = self.get_argument('slug', '')

      company = {
        'id':'', 'name':'', 'url':'', 'description':'', 'logo_filename':'',
        'locations':'', 'investment_series':'', 'investment_year':'', 'categories':'',
        'satus':'', 'slug':'', 'investment_post_slug':''
      }
      if slug != '':
        company = companiesdb.get_company_by_slug(slug)
        if not company:
          company = {
            'id':'', 'name':'', 'url':'', 'description':'', 'logo_filename':'',
            'locations':'', 'investment_series':'', 'investment_year':'', 'categories':'',
            'satus':'', 'slug':'', 'investment_post_slug':''
          }

      self.render('admin/admin_company.html', company=company)

  @tornado.web.authenticated
  def post(self):
    if self.current_user not in settings.get('staff'):
      self.redirect('/')
    else:
      company = {}
      company['id'] = self.get_argument('id', '')
      company['name'] = self.get_argument('name', '')
      company['url'] = self.get_argument('url', '')
      company['description'] = self.get_argument('description', '')
      company['logo_filename'] = self.get_argument('logo_filename', '')
      company['locations'] = self.get_argument('locations', '')
      company['investment_series'] = self.get_argument('investment_series', '')
      company['investment_year'] = self.get_argument('investment_year', '')
      company['categories'] = self.get_argument('categories', '')
      company['status'] = self.get_argument('status', '')
      company['slug'] = self.get_argument('slug', '')
      company['investment_post_slug'] = self.get_argument('investment_post_slug', '')

      # save the company details
      companiesdb.save_company(company)

      self.render('admin/admin_company.html', company=company)

###########################
### List the available admin tools
### /admin
###########################
class AdminHome(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self):
    if self.current_user not in settings.get('staff'):
      self.redirect('/')
    else:
      self.render('admin/admin_home.html')

###########################
### View system statistics
### /admin/stats
###########################
class AdminStats(app.basic.BaseHandler):
  def get(self):
    if self.current_user not in settings.get('staff'):
      self.redirect('/')
    else:
      total_posts = postsdb.get_post_count()
      total_users = userdb.get_user_count()

    self.render('admin/admin_stats.html', total_posts=total_posts, total_users=total_users)

###########################
### Add a user to the blacklist
### /users/(?P<username>[A-z-+0-9]+)/ban
###########################
class BanUser(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self, screen_name):
    if self.current_user in settings.get('staff'):
      user = userdb.get_user_by_screen_name(screen_name)
      if user:
        user['user']['is_blacklisted'] = True
        userdb.save_user(user)
    self.redirect('/')

###########################
### List posts that are marekd as deleted
### /admin/delete_user
###########################
class DeletedPosts(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self):
    if not self.current_user_can('delete_posts'):
      self.redirect('/')
    else:
      page = abs(int(self.get_argument('page', '1')))
      per_page = abs(int(self.get_argument('per_page', '10')))

      deleted_posts = postsdb.get_deleted_posts(per_page, page)
      total_count = postsdb.get_deleted_posts_count()

      self.render('admin/deleted_posts.html', deleted_posts=deleted_posts, total_count=total_count, page=page, per_page=per_page)

###########################
### Mark all shares by a user as 'deleted'
### /admin/deleted_posts
###########################
class DeleteUser(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self):
    if not self.current_user_can('delete_users'):
      self.redirect('/')
    else:
      msg = self.get_argument('msg', '')
      self.render('admin/delete_user.html', msg=msg)

  @tornado.web.authenticated
  def post(self):
    if not self.current_user_can('delete_users'):
      self.redirect('/')
    else:
      msg = self.get_argument('msg', '')
      post_slug = self.get_argument('post_slug', '')
      post = postsdb.get_post_by_slug(post_slug)
      if post:
        # get the author of this post
        screen_name = post['user']['screen_name']
        postsdb.delete_all_posts_by_user(screen_name)
      self.ender('admin/delete_user.html', msg=msg)

###########################
### Create a new hackpad
### /generate_hackpad/?
###########################
class GenerateNewHackpad(app.basic.BaseHandler):
  def get(self):
    if self.current_user not in settings.get('staff'):
      self.redirect('/')
    else:
      hackpads = hackpad.create_hackpad()
      self.api_response(hackpads)

###########################
### List all hackpads
### /list_hackpads
###########################
class ListAllHackpad(app.basic.BaseHandler):
  def get(self):
    if self.current_user not in settings.get('staff'):
      self.redirect('/')
    else:
      hackpads = hackpad.list_all()
      self.api_response(hackpads)

###########################
### Mute (hide) a post
### /posts/([^\/]+)/mute
###########################
class Mute(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self, slug):
    post = postsdb.get_post_by_slug(slug)

    if post and self.current_user_can('mute_posts'):
      post['muted'] = True
      postsdb.save_post(post)

    self.redirect('/?sort_by=hot')

###########################
### Recalc the sort socres (for hot list)
### /admin/sort_posts
###########################
class ReCalculateScores(app.basic.BaseHandler):
  def get(self):
    # set our config values up
    #staff_bonus = int(self.get_argument('staff_bonus', -3))
    staff_bonus = -3
    #time_penalty_multiplier = float(self.get_argument('time_penalty_multiplier', 2.0))
    time_penalty_multiplier = 2.0
    #grace_period = float(self.get_argument('grace_period', 6.0))
    grace_period = 12.0
    #comments_multiplier = float(self.get_argument('comments_multiplier', 3.0))
    comments_multiplier = 3.0
    #votes_multiplier = float(self.get_argument('votes_multiplier', 1.0))
    votes_multiplier = 1.0
    #min_votes = float(self.get_argument('min_votes', 2))
    min_votes = 2

    # get all the posts that have at least the 'min vote threshold'
    posts = postsdb.get_posts_with_min_votes(min_votes)

    data = []
    for post in posts:
      # determine how many hours have elapsed since this post was created
      tdelta = datetime.datetime.now() - post['date_created']
      hours_elapsed = tdelta.seconds/3600 + tdelta.days*24

      # determine the penalty for time decay
      time_penalty = 0
      if hours_elapsed > grace_period:
        time_penalty = hours_elapsed - grace_period
      if hours_elapsed > 12:
        time_penalty = time_penalty * 1.5
      if hours_elapsed > 18:
        time_penalty = time_penalty * 2

      # get our base score from downvotes
      #base_score = post['downvotes'] * -1
      base_score = 0

      # determine if we should assign a staff bonus or not
      if post['user']['username'] in settings.get('staff'):
        staff_bonus = staff_bonus
      else:
        staff_bonus = 0

      # determine how to weight votes
      votes_base_score = 0
      if post['votes'] == 1 and post['comment_count'] > 2:
        votes_base_score = -2
      if post['votes'] > 8 and post['comment_count'] == 0:
        votes_base_score = -2

      scores = {}
      # now actually calculate the score
      total_score = base_score
      
      scores['votes'] = (votes_base_score + post['votes'] * votes_multiplier)
      total_score += scores['votes']
      
      scores['comments'] = (post['comment_count'] * comments_multiplier)
      total_score += scores['comments']
      
      scores['time'] = (time_penalty * time_penalty_multiplier * -1)
      total_score += scores['time']
      
      total_score += staff_bonus
      post['scores'] = scores

      # and save the new score
      postsdb.update_post_score(post['slug'], total_score)

      data.append({
        'username': post['user']['username'],
        'title': post['title'],
        'slug': post['slug'],
        'date_created': post['date_created'],
        'hours_elapsed': hours_elapsed,
        'votes': post['votes'],
        'comment_count': post['comment_count'],
        'staff_bonus': staff_bonus,
        'time_penalty': time_penalty,
        'total_score': total_score,
        'scores': scores
      })
  
    data = sorted(data, key=lambda k: k['total_score'], reverse=True)

    self.render('admin/recalc_scores.html', data=data, staff_bonus=staff_bonus, time_penalty_multiplier=time_penalty_multiplier, grace_period=grace_period, comments_multiplier=comments_multiplier, votes_multiplier=votes_multiplier, min_votes=min_votes)

###########################
### Remove user from blacklist
### /users/(?P<username>[A-z-+0-9]+)/unban
###########################
class UnBanUser(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self, screen_name):
    if self.current_user in settings.get('staff'):
      user = userdb.get_user_by_screen_name(screen_name)
      if user:
        user['user']['is_blacklisted'] = False
        userdb.save_user(user)
    self.redirect('/')

###########################
### Manage Disqus Data
### /admin/disqus
###########################
class ManageDisqus(app.basic.BaseHandler):
  def get(self):
    if not self.current_user_can('manage_disqus'):
      return self.write("not authorized")
    
    from disqusapi import DisqusAPI
    disqus = DisqusAPI(settings.get('disqus_secret_key'), settings.get('disqus_public_key'))
    for result in disqus.trends.listThreads():
        self.write(result)
    #response = disqus.get_all_threads()
    #self.write(response)

###########################
### Get correspondence data
### /admin/gmail
###########################
class Gmail(app.basic.BaseHandler):
  def get(self):   
    if self.current_user not in settings.get('staff'):
      self.redirect('/')

    query = self.get_argument('q', '')
    accounts = gmaildb.get_all()
    usv_members = []
    for usv_member in accounts:
      usv_members.append(usv_member['name'])

    return self.render('admin/gmail.html', query=query, accounts=usv_members)


###########################
### API call for correspondence data from a single USVer
### /admin/gmailapi
###########################
class GmailAPI(app.basic.BaseHandler):
  def get(self):
    if self.current_user not in settings.get('staff'):
      self.write(json.dumps({'err': 'Not logged in'}))

    query = self.get_argument('q', '')
    name = self.get_argument('n','')
    if not query or not name:
      return
    try:
      usv_member = gmaildb.get_by_name(name)
      mail = self.email_login(usv_member['account'], usv_member['password'])
      total_emails_in, recent_email_in = self.search_mail(mail, "FROM " + query)
      total_emails_out, recent_email_out = self.search_mail(mail, "TO " + query)
      correspondence = {'name': usv_member['name'],
                        'account': usv_member['account'], 
                        'total_emails_in': total_emails_in, 
                        'total_emails_out': total_emails_out, 
                        'latest_email_in': recent_email_in.strftime('%b %d, %Y'), 
                        'latest_email_out': recent_email_out.strftime('%b %d, %Y')}
      self.write(json.dumps(correspondence))
    except:
        self.write(json.dumps({'name': name, 'err': 'None found'}))

  ''' Simple query to the inbox, returns how many emails match query and the date of the latest email.
      Query must be a single string, i.e. not "science exchange" '''
  def search_mail(self, mail, query):
      if not query:
        query = "ALL"
      result, data = mail.search(None, query) # data is a list, but there is only data[0]. data[0] is a string of all the email ids for the given query. ex: ['1 2 4']
      ids = data[0] # ids is a space separated string containing all the ids of email messages
      id_list = ids.split() # id_list is an array of all the ids of email messages

      # Get date of latest email
      if id_list:
        latest_id = id_list[-1]
        result, data = mail.fetch(latest_id, "(RFC822)") # fetch the email body (RFC822) for the given ID
        raw_email = data[0][1] # raw_email is the body, i.e. the raw text of the whole email including headers and alternate payloads     
        date = self.get_mail_date(raw_email)
      else:
        date = None
      return len(id_list), date

  ''' Login into an account '''
  def email_login(self, account, password):
    try:
      mail = imaplib.IMAP4_SSL('imap.gmail.com')
      result, message = mail.login(account, password)
      mail.select("[Gmail]/All Mail", readonly=True) #mark as unread 
      if result != 'OK':
        raise Exception
      print 'Logged in as ' + account
      return mail
    except:
      print "Failed to log into " + account
      return None

  ''' Parses raw email and returns date sent. Picks out dates of the form "26 Aug 2013" '''
  def get_mail_date(self, raw_email):
    if raw_email:
      #Date: Mon, 5 Nov 2012 17:45:38 -0500
      date_string = re.search(r'[0-3]*[0-9] [A-Z][a-z][a-z] 20[0-9][0-9]', raw_email)
      if date_string:
        time_obj = time.strptime(date_string.group(), "%d %b %Y")
        return date(time_obj.tm_year, time_obj.tm_mon, time_obj.tm_mday)
      else:
        return None
    else:
      raise Exception

########NEW FILE########
__FILENAME__ = api
import app.basic
import logging
import settings
import datetime

from lib import disqus
from lib import postsdb
from lib import userdb

#########################
### Alerting to share owner (and other subscribers) on new Disqus comments
### /api/incr_comment_count
#########################
class DisqusCallback(app.basic.BaseHandler):
  def get(self):
    comment = self.get_argument('comment', '')
    post_slug = self.get_argument('post', '')
    post = postsdb.get_post_by_slug(post_slug)

    if post:
      # increment the comment count for this post
      post['comment_count'] += 1
      postsdb.save_post(post)
      # determine if anyone is subscribed to this post (for email alerts)
      if len(post['subscribed']) > 0:
        # attempt to get the current user's email (we don't need to alert them)
        author_email = ''
        if self.current_user:
          author = userdb.get_user_by_screen_name(self.current_user)
          if author and 'email_address' in author.keys() and author['email_address'].strip() != '':
            author_email = author['email_address']
        # get the message details from Disqus
        message = disqus.get_post_details(comment)
        if message['message'].strip() != '':
          # send the emails with details
          logging.info(message)
          subject = 'New message on: %s' % post['title']
          text = 'The following comment was just added to your share on usv.com.\n\n%s\n\nYou can engaged in the conversation, and manage your alert settings for this share, at http://www.usv.com/posts/%s' % (message['message'], post['slug'])
          for email in post['subscribed']:
            # attempt to send to each of these subscribed people (don't send to author)
            if email.lower() != author_email.lower() and email.strip() != '':
              self.send_email('alerts@usv.com', email, subject, text)
    self.api_response('OK')

#########################
### Get a user's status
### /api/user_status
#########################
class GetUserStatus(app.basic.BaseHandler):
  def get(self):
    status = 'none'
    if self.current_user:
      if self.current_user in settings.get('staff'):
        status = 'staff'
      elif self.is_blacklisted(self.current_user):
        status = 'blacklisted'
      else:
        status = 'user'
    self.api_response(status)

#########################
### Get list of users who have voted on a post
### /api/voted_users/(.+)
#########################
class GetVotedUsers(app.basic.BaseHandler):
  def get(self, slug):
    voted_users = []
    post = postsdb.get_post_by_slug(slug)
    if post:
      voted_users = post['voted_users']
      for user in voted_users:
        if user.get('username') == post['user']['username']:
          voted_users.remove(user)
      self.render('post/voted_users.html', voted_users=voted_users)
    
#########################
### Check to see if we already have a post by url
### /api/check_for_url?url=foo
#########################
class CheckForUrl(app.basic.BaseHandler):
  def get(self, url):
    response = {
      "exists": False,
      "posts": []
    }
    posts = postsdb.get_post_by_url(url)
    if len(posts) > 0:
      response["exists"] = True
      response["posts"] = posts
    self.api_response(response)

############################
### Get a day's worth of posts
### /api/posts/get_day
############################
class PostsGetDay(app.basic.BaseHandler):
  def get(self):
    day = datetime.datetime.strptime(self.get_argument('day'), "%Y-%m-%d %H:%M:%S")
    yesterday = day - datetime.timedelta(days=1)
    posts = postsdb.get_hot_posts_by_day(day)
    html = self.render_string('post/daily_posts_list_snippet.html', today=day, yesterday=yesterday, posts=posts, current_user_can=self.current_user_can)
    response = {}
    response['html'] = html
    self.api_response(response)

########NEW FILE########
__FILENAME__ = basic
import tornado.web
import requests
import settings
import simplejson as json
import os
import httplib
import logging

from lib import userdb

class BaseHandler(tornado.web.RequestHandler):
  def __init__(self, *args, **kwargs):
    super(BaseHandler, self).__init__(*args, **kwargs)
    #user = self.get_current_user()
    #css_file = "%s/css/threatvector.css" % settings.tornado_config['static_path']
    #css_modified_time = os.path.getmtime(css_file)
      
    self.vars = {
      #'user': user,
      #'css_modified_time': css_modified_time
    }
                
  def render(self, template, **kwargs):
  
    # add any variables we want available to all templates
    kwargs['user_obj'] = None
    kwargs['user_obj'] = userdb.get_user_by_screen_name(self.current_user)
    kwargs['current_user_can'] = self.current_user_can 
    kwargs['settings'] = settings 
    kwargs['body_location_class'] = ""
    kwargs['current_path'] = self.request.uri
    #kwargs['request_path'] = self.request
    
    if self.request.path == "/":
      kwargs['body_location_class'] = "home"
  
    super(BaseHandler, self).render(template, **kwargs)
    
  def get_current_user(self):
    return self.get_secure_cookie("username")

  def send_email(self, from_user, to_user, subject, text):
    if settings.get('environment') != "prod":
      logging.info("If this were prod, we would have sent email to %s" % to_user)
      return
    else:
      return requests.post(
        "https://sendgrid.com/api/mail.send.json",
        data={
          "api_user":settings.get('sendgrid_user'),
          "api_key":settings.get('sendgrid_secret'),
          "from": from_user,
          "to": to_user,
          "subject": subject,
          "text": text
        },
        verify=False
      )
      
    
  def is_blacklisted(self, screen_name):
    u = userdb.get_user_by_screen_name(screen_name)
    if u and 'user' in u.keys() and 'is_blacklisted' in u['user'].keys() and u['user']['is_blacklisted']:
      return True
    return False

  def current_user_can(self, capability):
    """
    Tests whether a user can do a certain thing.
    """
    result = False
    u = userdb.get_user_by_screen_name(self.current_user)
    if u and 'role' in u.keys():
      try:
        if capability in settings.get('%s_capabilities' % u['role']):
          result = True
      except:
        result = False
    return result

  def api_response(self, data):
    # return an api response in the proper output format with status_code == 200
    self.write_api_response(data, 200, "OK")

  def error(self, status_code, status_txt, data=None):
    # return an api error in the proper output format
    self.write_api_response(status_code=status_code, status_txt=status_txt, data=data)

  def write_api_response(self, data, status_code, status_txt):
    # return an api error based on the appropriate request format (ie: json)
    format = self.get_argument('format', 'json')
    callback = self.get_argument('callback', None)
    if format not in ["json"]:
      status_code = 500
      status_txt = "INVALID_ARG_FORMAT"
      data = None
      format = "json"
    response = {'status_code':status_code, 'status_txt':status_txt, 'data':data}

    if format == "json":
      data = json.dumps(response)
      if callback:
        self.set_header("Content-Type", "application/javascript; charset=utf-8")
        self.write('%s(%s)' % (callback, data))
      else:
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.write(data)
      self.finish()
  
  def write_error(self, status_code, **kwargs):
    self.require_setting("static_path")
    if status_code in [404, 500, 503, 403]:
        filename = os.path.join(self.settings['static_path'], '%d.html' % status_code)
        if os.path.exists(filename):
            f = open(filename, 'r')
            data = f.read()
            f.close()
            return self.write(data)
    return self.write("<html><title>%(code)d: %(message)s</title>" \
            "<body class='bodyErrorPage'>%(code)d: %(message)s</body></html>" % {
        "code": status_code,
        "message": httplib.responses[status_code],
    })

########NEW FILE########
__FILENAME__ = disqus
import urllib2
import urllib
import simplejson as json
import tornado.web
import logging
import settings
import app.basic
from datetime import datetime

from lib import userdb
from lib import postsdb
from lib import disqus

class Auth(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self):
    req_host = self.request.headers['host']
    client_id = settings.get('disqus_public_key')
    redirect_url = 'https://disqus.com/api/oauth/2.0/authorize/?client_id=%s&scope=read,write&response_type=code&redirect_uri=http://%s/disqus'  % (client_id, req_host)
    self.redirect(redirect_url)

class Disqus(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self):
    code = self.get_argument('code','')
    req_host = self.request.headers['host']
    api_key = settings.get('disqus_public_key')
    api_secret = settings.get('disqus_secret_key')

    link = 'https://disqus.com/api/oauth/2.0/access_token/'
    data = {
      'grant_type':'authorization_code',
      'client_id':api_key,
      'client_secret':api_secret,
      'redirect_uri': 'http://%s/disqus' % req_host,
      'code' : code
    }
    try:
      account = userdb.get_user_by_screen_name(self.current_user)
      if account:
        response = urllib2.urlopen(link, urllib.urlencode(data))
        #  access_token should look like access_token=111122828977539|98f28d8b5b8ed787b585e69b.1-537252399|1bKwe6ghzXyS9vPDyeB9b1fHLRc
        user_data = json.loads(response.read())
        # refresh the user token details
        disqus_obj = {}
        disqus_obj['username'] = user_data['username']
        disqus_obj['user_id'] = user_data['user_id']
        disqus_obj['access_token'] = user_data['access_token']
        disqus_obj['expires_in'] = user_data['expires_in']
        disqus_obj['refresh_token'] = user_data['refresh_token']
        disqus_obj['token_type'] = user_data['token_type']
        disqus_obj['token_startdate'] = datetime.now()
        account['disqus'] = disqus_obj
        if 'disqus_username' in account.keys(): del account['disqus_username']
        if 'disqus_user_id' in account.keys(): del account['disqus_user_id']
        if 'disqus_access_token' in account.keys(): del account['disqus_access_token']
        if 'disqus_expires_in' in account.keys(): del account['disqus_expires_in']
        if 'disqus_refresh_token' in account.keys(): del account['disqus_refresh_token']
        if 'disqus_token_type' in account.keys(): del account['disqus_token_type']
        userdb.save_user(account)
        
        # subscribe user to all previous threads they've written
        disqus.subscribe_to_all_your_threads(self.current_user)
        
    except Exception, e:
      logging.info(e)
      # trouble logging in
      data = {}
    self.redirect('/user/%s/settings?msg=updated' % self.current_user)

class Remove(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self):
    # remove twitter from this account
    account = userdb.get_user_by_screen_name(self.current_user)
    if account:
      del account['disqus']
      userdb.save_user(account)

    self.redirect('/user/%s/settings?msg=updated' % self.current_user)

########NEW FILE########
__FILENAME__ = error
import os
import httplib
import tornado.web

class ErrorHandler(tornado.web.RequestHandler):
	"""Generates an error response with status_code for all requests."""
	def __init__(self, application, request, status_code):
		tornado.web.RequestHandler.__init__(self, application, request)
		self.set_status(status_code)

	def get_error_html(self, status_code, **kwargs):
		self.require_setting("static_path")
		if status_code in [404, 500, 503, 403]:
			filename = os.path.join(self.settings['static_path'], '%d.html' % status_code)
			if os.path.exists(filename):
				f = open(filename, 'r')
				data = f.read()
				f.close()
				return data
		return "<html><title>%(code)d: %(message)s</title>" \
				"<body class='bodyErrorPage'>%(code)d: %(message)s</body></html>" % {
			"code": status_code,
			"message": httplib.responses[status_code],
		}

	def prepare(self):
		raise tornado.web.HTTPError(self._status_code)

## override the tornado.web.ErrorHandler with our default ErrorHandler
tornado.web.ErrorHandler = ErrorHandler
########NEW FILE########
__FILENAME__ = general
import app.basic

from lib import postsdb

#############
### ABOUT USV
### /about
#############
class About(app.basic.BaseHandler):
  def get(self):
    # get the last 6 posts tagged thesis (and published by staff)
    related_posts = postsdb.get_latest_staff_posts_by_tag('thesis', 6)
    self.render('general/about.html', related_posts=related_posts)
########NEW FILE########
__FILENAME__ = posts
#-*- coding:utf-8 -*-
import app.basic

import logging
import re
import settings
import tornado.web
import tornado.options
import urllib

from datetime import datetime
from datetime import timedelta
from datetime import date
from lib import datetime_overrider

import time
from urlparse import urlparse
from lib import bitly
from lib import google
from lib import mentionsdb
from lib import postsdb
from lib import sanitize
from lib import tagsdb
from lib import userdb
from lib import disqus
from lib import template_helpers

###############
### New Post
### /posts
###############
class NewPost(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self):
    post = {}
    post['title'] = self.get_argument('title', '')
    post['url'] = self.get_argument('url', '')
    is_bookmarklet = False
    if self.request.path.find('/bookmarklet') == 0:
      is_bookmarklet = True
      
    self.render('post/new_post.html', post=post, is_bookmarklet=is_bookmarklet)

###############
### EDIT A POST
### /posts/([^\/]+)/edit
###############
class EditPost(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self, slug):
    post = postsdb.get_post_by_slug(slug)
    if post and post['user']['screen_name'] == self.current_user or self.current_user_can('edit_posts'):
      # available to edit this post
      self.render('post/edit_post.html', post=post)
    else:
      # not available to edit right now
      self.redirect('/posts/%s' % slug)

##################
### FEATURED POSTS
### /featured.*$
##################
class FeaturedPosts(app.basic.BaseHandler):
  def get(self, tag=None):
    featured_posts = postsdb.get_featured_posts(1000, 1)
    tags_alpha = tagsdb.get_all_tags(sort="alpha")
    tags_count = tagsdb.get_all_tags(sort="count")

    self.render('search/search_results.html', tag=tag, tags_alpha=tags_alpha, tags_count=tags_count, posts=featured_posts, total_count=len(featured_posts), query="featured_posts")

##############
### FEED
### /feed
##############
class Feed(app.basic.BaseHandler):
  def get(self, feed_type="hot"):
    #action = self.get_argument('action', '')
    page = abs(int(self.get_argument('page', '1')))
    per_page = abs(int(self.get_argument('per_page', '9')))

    posts = []
    if feed_type == 'new':
      # show the newest posts
      posts = postsdb.get_new_posts(per_page, page)
    elif feed_type == 'sad':
      # show the sad posts
      posts = postsdb.get_sad_posts(per_page, page)
    elif feed_type == 'hot':
      # show the sad posts
      posts = postsdb.get_daily_posts_by_sort_score(8)
    elif feed_type == 'superhot':
      # show the sad posts
      posts = postsdb.get_daily_posts_by_sort_score(20)
    elif feed_type == 'superduperhot':
      # show the sad posts
      posts = postsdb.get_daily_posts_by_sort_score(50)
    elif feed_type == 'today':
      posts = postsdb.get_hot_posts_by_day()
    else:
      posts = postsdb.get_hot_posts_by_day()

    self.render('post/feed.xml', posts=posts)

##############
### LIST POSTS and SHARE POST
### /
##############
class ListPosts(app.basic.BaseHandler):
  def get(self, day="today", page=1, sort_by="hot"):
    view = "list"
    sort_by = self.get_argument('sort_by', sort_by)
    page = abs(int(self.get_argument('page', page)))
    per_page = abs(int(self.get_argument('per_page', '20')))
    msg = self.get_argument('msg', '')
    slug = self.get_argument('slug', '')
    new_post = None
    if slug:
      new_post = postsdb.get_post_by_slug(slug)
      
    featured_posts = postsdb.get_featured_posts(1)
    posts = []
    post = {}
    hot_tags = tagsdb.get_hot_tags()
    
    is_today = False
    if day == "today":
      is_today = True
      day = datetime.today()
    else:
      day = datetime.strptime(day, "%Y-%m-%d")
    previous_day = day - timedelta(days=1)
    two_days_ago = previous_day - timedelta(days=1)
    
    day_str = str(date(day.year, day.month, day.day))
    previous_day_str = str(date(previous_day.year, previous_day.month, previous_day.day))
    two_days_ago_str = str(date(two_days_ago.year, two_days_ago.month, two_days_ago.day))
    
    show_day_permalink = True
    infinite_scroll = False
    if self.request.path == ('/'):
      show_day_permalink = False
      infinite_scroll = True
    
    is_blacklisted = False
    if self.current_user:
      is_blacklisted = self.is_blacklisted(self.current_user)

    posts = postsdb.get_hot_posts_by_day(day)
    #posts = postsdb.get_hot_posts_24hr()
    previous_day_posts = postsdb.get_hot_posts_by_day(previous_day)
    
    
    #midpoint = (len(posts) - 1) / 2
    # midpoint determines where post list breaks from size=md to size=sm
    midpoint = 7
    hot_posts_past_week = postsdb.get_hot_posts_past_week()

    self.vars.update({
      'is_today': is_today,
      'view': view,
      'msg': msg,
      'posts': posts,
      'previous_day_posts': previous_day_posts,
      'hot_posts_past_week': hot_posts_past_week,
      'featured_posts': featured_posts,
      'post': post,
      #'featured_posts': featured_posts,
      'is_blacklisted': is_blacklisted,
      'tags': hot_tags,
      'day': day,
      'day_str': day_str,      
      'previous_day': previous_day,
      'previous_day_str': previous_day_str,
      'two_days_ago': two_days_ago,
      'two_days_ago_str': two_days_ago_str,
      'show_day_permalink': show_day_permalink,
      'infinite_scroll': infinite_scroll,
      'midpoint': midpoint,
      'new_post': new_post,
      'datetime': datetime
    })
    self.render('post/lists_posts.html', **self.vars)

  @tornado.web.authenticated
  def post(self):
    sort_by = self.get_argument('sort_by', 'hot')
    page = abs(int(self.get_argument('page', '1')))
    per_page = abs(int(self.get_argument('per_page', '9')))
    is_blacklisted = False
    msg = 'success'
    if self.current_user:
      is_blacklisted = self.is_blacklisted(self.current_user)
    
    post = {}
    post['slug'] = self.get_argument('slug', None)
    post['title'] = self.get_argument('title', '')
    post['url'] = self.get_argument('url', '')
    post['body_raw'] = self.get_argument('body_raw', '')
    post['tags'] = self.get_argument('tags', '').split(',')
    post['featured'] = self.get_argument('featured', '')
    post['has_hackpad'] = self.get_argument('has_hackpad', '')
    post['slug'] = self.get_argument('slug', '')
    post['sort_score'] = 0
    post['daily_sort_score'] = 0
    if post['has_hackpad'] != '':
      post['has_hackpad'] = True
    else:
      post['has_hackpad'] = False

    deleted = self.get_argument('deleted', '')
    if deleted != '':
      post['deleted'] = True
      post['date_deleted'] = datetime.now()

    bypass_dup_check = self.get_argument('bypass_dup_check', '')
    is_edit = False
    if post['slug']:
      bypass_dup_check = "true"
      is_edit = True

    dups = []

    # make sure user isn't blacklisted
    if not self.is_blacklisted(self.current_user):
      # check if there is an existing URL
      if post['url'] != '':
        url = urlparse(post['url'])
        netloc = url.netloc.split('.')
        if netloc[0] == 'www':
          del netloc[0]
        path = url.path
        if path and path[-1] == '/':
          path = path[:-1]
        url = '%s%s' % ('.'.join(netloc), path)
        post['normalized_url'] = url

        long_url = post['url']
        if long_url.find('goo.gl') > -1:
          long_url = google.expand_url(post['url'])
        if long_url.find('bit.ly') > -1 or long_url.find('bitly.com') > -1:
          long_url = bitly.expand_url(post['url'].replace('http://bitly.com','').replace('http://bit.ly',''))
        post['domain'] = urlparse(long_url).netloc

      ok_to_post = True
      dups = postsdb.get_posts_by_normalized_url(post.get('normalized_url', ""), 1)
      if post['url'] != '' and len(dups) > 0 and bypass_dup_check != "true":
        ## 
        ## If there are dupes, kick them back to the post add form
        ##
        return (self.render('post/new_post.html', post=post, dups=dups))
        
      # Handle tags
      post['tags'] = [t.strip().lower() for t in post['tags']]
      post['tags'] = [t for t in post['tags'] if t]
      userdb.add_tags_to_user(self.current_user, post['tags'])
      for tag in post['tags']:
        tagsdb.save_tag(tag)

      # format the content as needed
      post['body_html'] = sanitize.html_sanitize(post['body_raw'], media=self.current_user_can('post_rich_media'))
      post['body_text'] = sanitize.html_to_text(post['body_html'])
      post['body_truncated'] = sanitize.truncate(post['body_text'], 500)

      # determine if this should be a featured post or not
      if self.current_user_can('feature_posts') and post['featured'] != '':
        post['featured'] = True
        post['date_featured'] = datetime.now()
      else:
        post['featured'] = False
        post['date_featured'] = None

      user = userdb.get_user_by_screen_name(self.current_user)

      if not post['slug']:
        # No slug -- this is a new post.
        # initiate fields that are new
        post['disqus_shortname'] = settings.get('disqus_short_code')
        post['muted'] = False
        post['comment_count'] = 0
        post['disqus_thread_id_str'] = ''
        post['sort_score'] = 0.0
        post['downvotes'] = 0
        post['hackpad_url'] = ''
        post['date_created'] = datetime.now()
        post['user_id_str'] = user['user']['id_str']
        post['username'] = self.current_user
        post['user'] = user['user']
        post['votes'] = 1
        post['voted_users'] = [user['user']]
        #save it
        post['slug'] = postsdb.insert_post(post)
        msg = 'success'
      else:
        # this is an existing post.
        # attempt to edit the post (make sure they are the author)
        saved_post = postsdb.get_post_by_slug(post['slug'])
        if saved_post and self.current_user == saved_post['user']['screen_name']:
          # looks good - let's update the saved_post values to new values
          for key in post.keys():
            saved_post[key] = post[key]
          # finally let's save the updates
          postsdb.save_post(saved_post)
          msg = 'success'

      # log any @ mentions in the post
      mentions = re.findall(r'@([^\s]+)', post['body_raw'])
      for mention in mentions:
        mentionsdb.add_mention(mention.lower(), post['slug'])

    # Send email to USVers if OP is staff
    if self.current_user in settings.get('staff'):
      subject = 'USV.com: %s posted "%s"' % (self.current_user, post['title'])
      if 'url' in post and post['url']: # post.url is the link to external content (if any)
        post_link = 'External Link: %s \n\n' % post['url']
      else:
        post_link = ''
      post_url = "http://%s/posts/%s" % (settings.get('base_url'), post['slug'])
      text = '"%s" ( %s ) posted by %s. \n\n %s %s' % (post['title'].encode('ascii', errors='ignore'), post_url, self.current_user, post_link, post.get('body_text', ""))
      # now attempt to actually send the emails
      for u in settings.get('staff'):
        if u != self.current_user:
          acc = userdb.get_user_by_screen_name(u)
          if acc:
            self.send_email('web@usv.com', acc['email_address'], subject, text)
  
    # Subscribe to Disqus
    # Attempt to create the post's thread
    acc = userdb.get_user_by_screen_name(self.current_user)
    thread_id = 0
    try:
      # Attempt to create the thread.
      thread_details = disqus.create_thread(post, acc['disqus']['access_token'])
      thread_id = thread_details['response']['id']
    except:
      try:
        # trouble creating the thread, try to just get the thread via the slug
        thread_details = disqus.get_thread_details(post)
        thread_id = thread_details['response']['id']
      except:
        thread_id = 0
    if thread_id != 0:
      # Subscribe a user to the thread specified in response
      disqus.subscribe_to_thread(thread_id, acc['disqus']['access_token'])
      # update the thread with the disqus_thread_id_str
      saved_post = postsdb.get_post_by_slug(post['slug'])
      saved_post['disqus_thread_id_str'] = thread_id
      postsdb.save_post(saved_post)

    if is_edit:
      self.redirect('/posts/%s?msg=updated' % post['slug'])
    else:
      self.redirect('/?msg=success&slug=%s' % post['slug'])


##############
### List all New Posts
### /new
##############
class ListPostsNew(app.basic.BaseHandler):
  def get(self, page=1):
    page = abs(int(self.get_argument('page', page)))
    per_page = abs(int(self.get_argument('per_page', '100')))

    featured_posts = postsdb.get_featured_posts(5, 1)
    posts = []
    post = {}
    hot_tags = tagsdb.get_hot_tags()

    is_blacklisted = False
    if self.current_user:
      is_blacklisted = self.is_blacklisted(self.current_user)

    posts = postsdb.get_new_posts(per_page=per_page, page=page)

    self.vars.update({
      'posts': posts,
      'featured_posts': featured_posts,
      #'featured_posts': featured_posts,
      'is_blacklisted': is_blacklisted,
      'tags': hot_tags,
    })
    self.render('post/list_new_posts.html', **self.vars)

 
      
##########################
### Bump Up A SPECIFIC POST
### /posts/([^\/]+)/bump
##########################
class Bump(app.basic.BaseHandler):
  def get(self, slug):
    # user must be logged in
    msg = {}
    if not self.current_user:
      msg = {'error': 'You must be logged in to bump.', 'redirect': True}
    else:
      post = postsdb.get_post_by_slug(slug)
      if post:
        can_vote = True
        for u in post['voted_users']:
          if u['username'] == self.current_user:
            can_vote = False
        if not can_vote:
          msg = {'error': 'You have already upvoted this post.'}
        else:
          user = userdb.get_user_by_screen_name(self.current_user)
          
          # Increment the vote count
          post['votes'] += 1
          post['voted_users'].append(user['user'])
          postsdb.save_post(post)
          msg = {'votes': post['votes']}
          
          # send email notification to post author
          author = userdb.get_user_by_screen_name(post['user']['username'])
          if 'email_address' in author.keys():
            subject = "[#usvconversation] @%s just bumped up your post: %s" % (self.current_user, post['title'])
            text = "Woo!\n\n%s" % template_helpers.post_permalink(post)
            logging.info('sent email to %s' % author['email_address'])
            self.send_email('web@usv.com', author['email_address'], subject, text)
          
    self.api_response(msg)

##########################
### Super Upvote
### /posts/([^\/]+)/superupvote
##########################
class SuperUpVote(app.basic.BaseHandler):
  def get(self, slug):
    # user must be logged in
    msg = {}
    if not self.current_user:
      msg = {'error': 'You must be logged in to super upvote.', 'redirect': True}
    elif not self.current_user_can('super_upvote'):
      msg = {'error': 'You are not authorized to super upvote', 'redirect': True}
    else:
      post = postsdb.get_post_by_slug(slug)
      if post:
          # Increment the vote count
          super_upvotes = post.get('super_upvotes') or 0
          super_upvotes += 1
          post['super_upvotes'] = super_upvotes
          postsdb.save_post(post)
          msg = {'supervotes': post['super_upvotes']}

    self.api_response(msg)

##########################
### Super DownVote
### /posts/([^\/]+)/superdownvote
##########################
class SuperDownVote(app.basic.BaseHandler):
  def get(self, slug):
    # user must be logged in
    msg = {}
    if not self.current_user:
      msg = {'error': 'You must be logged in to super downvote.', 'redirect': True}
    elif not self.current_user_can('super_downvote'):
      msg = {'error': 'You are not authorized to super downvote', 'redirect': True}
    else:
      post = postsdb.get_post_by_slug(slug)
      if post:
          # Increment the vote count
          super_downvotes = post.get('super_downvotes') or 0
          super_downvotes += 1
          post['super_downvotes'] = super_downvotes
          postsdb.save_post(post)
          msg = {'supervotes': post['super_downvotes']}

    self.api_response(msg)
    
##########################
### Un-Bump A SPECIFIC POST
### /posts/([^\/]+)/unbump
##########################
class UnBump(app.basic.BaseHandler):
  def get(self, slug):
    # user must be logged in
    msg = {}
    if not self.current_user:
      msg = {'error': 'You must be logged in to bump.', 'redirect': True}
    else:
      post = postsdb.get_post_by_slug(slug)
      if post:
        can_vote = True
        for u in post['voted_users']:
          if u['username'] == self.current_user:
            can_unbump = True
        if not can_unbump:
          msg = {'error': "You can't unbump this post!"}
        else:
          user = userdb.get_user_by_screen_name(self.current_user)
          post['votes'] -= 1
          post['voted_users'].remove(user['user'])
          postsdb.save_post(post)
          msg = {'votes': post['votes']}

    self.api_response(msg)

########################
### VIEW A SPECIFIC POST
### /posts/(.+)
########################
class ViewPost(app.basic.BaseHandler):
  def get(self, slug):
    post = postsdb.get_post_by_slug(slug)
    if not post:
      raise tornado.web.HTTPError(404)  
    
    tag_posts = []
    all_keeper_posts = []
    if 'tags' in post.keys() and len(post['tags']) > 0:
      for t in post['tags']:
        posts = postsdb.get_related_posts_by_tag(t)
        tag_keeper_posts = []
        for p in posts:
          if p['slug'] != slug and p not in all_keeper_posts:
            tag_keeper_posts.append(p)
            all_keeper_posts.append(p)
        obj = {
          'tag': t,
          'posts': tag_keeper_posts
        }
        tag_posts.append(obj)
    
    msg = self.get_argument('msg', None)  
    
    user = None
    if self.current_user:
      user = userdb.get_user_by_screen_name(self.current_user)
    
    # remove dupes from voted_users
    voted_users = []
    for i in post['voted_users']:
      if i not in voted_users:
        voted_users.append(i)
    post['voted_users'] = voted_users
    
    hot_posts_past_week = postsdb.get_hot_posts_past_week()
    featured_posts = {}
    
    view = "single"
    
    self.render('post/view_post.html', user_obj=user, post=post, msg=msg, tag_posts=tag_posts, hot_posts_past_week=hot_posts_past_week, featured_posts=featured_posts, view=view)

#############
### WIDGET
### /widget.*?
#############
class Widget(app.basic.BaseHandler):
  def get(self, extra_path=''):
    view = self.get_argument('view', 'sidebar')
    if extra_path != '':
      self.render('post/widget_demo.html')
    else:
      # list posts
      #action = self.get_argument('action', '')
      page = abs(int(self.get_argument('page', '1')))
      per_page = abs(int(self.get_argument('per_page', '9')))
      num_posts = abs(int(self.get_argument('num_posts', '5')))

      if view == "sidebar":
        # get the current hot posts
        posts = postsdb.get_hot_posts(per_page, page)
        self.render('post/widget.js', posts=posts, num_posts=num_posts)
      else: 
        posts = postsdb.get_hot_posts_by_day()
        self.render('post/widget_inline.js', posts=posts, num_posts=3)

###################
### WIDGET DEMO
### /widget/demo.*?
###################
class WidgetDemo(app.basic.BaseHandler):
  def get(self, extra_path=''):
    self.render('post/widget_demo.html')


########NEW FILE########
__FILENAME__ = search
import app.basic
import urllib

from lib import postsdb
from lib import tagsdb

################
### SEARCH POSTS
### /search
################
class Search(app.basic.BaseHandler):
  def get(self):
    query = self.get_argument('query', '')
    page = abs(int(self.get_argument('page', '1')))
    per_page = abs(int(self.get_argument('per_page', '10000')))

    # get posts based on query
    posts = postsdb.get_posts_by_query(query, per_page, page)
    total_count = postsdb.get_post_count_by_query(query)
    
    tags_alpha = tagsdb.get_all_tags(sort="alpha")
    tags_count = tagsdb.get_all_tags(sort="count")
    tag = ""

    self.render('search/search_results.html', posts=posts, tag=tag, tags_alpha=tags_alpha, tags_count=tags_count, total_count=total_count, page=page, per_page=per_page, query=query)

#####################
### VIEW POSTS BY TAG
### /tagged/(.+)
#####################
class ViewByTag(app.basic.BaseHandler):
  def get(self, tag=None):
    if tag:
        tag = urllib.unquote(tag.strip().replace('+',' ')).decode('utf8')
        posts = postsdb.get_posts_by_tag(tag)
        total_count = postsdb.get_post_count_by_tag(tag)
    else:
        posts = None
        total_count = 0
    
    featured_posts = postsdb.get_featured_posts(5, 1)
    tags_alpha = tagsdb.get_all_tags(sort="alpha")
    tags_count = tagsdb.get_all_tags(sort="count")
    
    self.render('search/search_results.html', tag=tag, tags_alpha=tags_alpha, tags_count=tags_count, posts=posts, total_count=total_count, query=tag)


########NEW FILE########
__FILENAME__ = stats
import app.basic

from datetime import datetime, timedelta

from lib import postsdb

######################
### WEEKLY STATS
### /stats/shares/weekly
######################
class WeeklyShareStats(app.basic.BaseHandler):
  def get(self):
    # get the stats based on the past 7 days
    today = datetime.today()
    week_ago = today + timedelta(days=-7)

    single_post_count = 0
    unique_posters = postsdb.get_unique_posters(week_ago, today)
    for user in unique_posters:
      if user['count'] == 1:
        single_post_count += 1

    stats = []
    stats.append({'name':'total','link':'','count':postsdb.get_post_count_for_range(week_ago, today)})
    stats.append({'name':'unique posters', 'link':'','count':len(unique_posters)})
    stats.append({'name':'single post count', 'link':'','count':single_post_count})

    self.render('stats/share_stats.html', stats=stats)


########NEW FILE########
__FILENAME__ = twitter
import tweepy
import app.basic
import settings

from lib import userdb

####################
### AUTH VIA TWITTER
### /auth/twitter
####################
class Auth(app.basic.BaseHandler):
  def get(self):
    consumer_key = settings.get('twitter_consumer_key')
    consumer_secret = settings.get('twitter_consumer_secret')
    callback_host = 'http://%s/twitter' % self.request.headers['host']
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, callback_host, secure=True)
    auth_url = auth.get_authorization_url(True)
    self.set_secure_cookie("request_token_key", auth.request_token.key)
    self.set_secure_cookie("request_token_secret", auth.request_token.secret)
    redirect = self.get_argument('next', '/')
    self.set_secure_cookie("twitter_auth_redirect", redirect)
    self.redirect(auth_url)

##############################
### RESPONSE FROM TWITTER AUTH
### /twitter
##############################
class Twitter(app.basic.BaseHandler):
  def get(self):
    oauth_verifier = self.get_argument('oauth_verifier', '')
    consumer_key = settings.get('twitter_consumer_key')
    consumer_secret = settings.get('twitter_consumer_secret')
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
    auth.set_request_token(self.get_secure_cookie('request_token_key'), self.get_secure_cookie('request_token_secret'))
    auth.get_access_token(oauth_verifier)
    screen_name = auth.get_username()
    bounce_to = self.get_secure_cookie('twitter_auth_redirect') or '/'

    access_token = {
      'secret': auth.access_token.secret,
      'user_id': '',
      'screen_name': '',
      'key': auth.access_token.key
    }

    # check if we have this user already or not in the system
    user = userdb.get_user_by_screen_name(screen_name)
    if user:
      # set the cookies based on account details
      self.set_secure_cookie("user_id_str", user['user']['id_str'])
      self.set_secure_cookie("username", user['user']['screen_name'])
      if 'email_address' not in user or ('email_address' in user and user['email_address'] == ''):
        bounce_to = '/user/%s/settings?1' % screen_name
    else:
      # need to create the account (so get more details from Twitter)
      auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
      api = tweepy.API(auth)
      user = api.get_user(screen_name)
      access_token['user_id'] = user.id
      access_token['screen_name'] = user.screen_name
      user_data = {
        'auth_type': 'twitter',
        'id_str': user.id_str,
        'username': user.screen_name,
        'fullname': user.name,
        'screen_name': user.screen_name,
        'profile_image_url': user.profile_image_url,
        'profile_image_url_https': user.profile_image_url_https,
      }
      # now save to mongo
      userdb.create_new_user(user_data, access_token)
      # and set our cookies
      self.set_secure_cookie("user_id_str", user.id_str)
      self.set_secure_cookie("username", user.screen_name)
      bounce_to = '/user/%s/settings?msg=twitter-thanks' % screen_name

    # let's save the screen_name to a cookie as well so we can use it for restricted bounces if need be
    self.set_secure_cookie('screen_name', screen_name, expires_days=30)

    # bounce to account
    self.redirect(bounce_to)

########NEW FILE########
__FILENAME__ = user
import tornado.web
import app.basic

from lib import disqus
from lib import mentionsdb
from lib import postsdb
from lib import tagsdb
from lib import userdb

###########################
### EMAIL SETTINGS
### /auth/email/?
###########################
class EmailSettings(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self):
    next_page = self.get_argument('next', '')
    subscribe_to = self.get_argument('subscribe_to', '')
    error = ''
    email = ''
    status = 'enter_email'

    # get the current user's email value
    user = userdb.get_user_by_screen_name(self.current_user)
    if user:
      email = user['email_address']

    self.render('user/email_subscribe.html', email=email, error=error, next_page=next_page, subscribe_to=subscribe_to, status=status)

  @tornado.web.authenticated
  def post(self):
    next_page = self.get_argument('next', '')
    next_page += "&finished=true"
    close_popup = self.get_argument('close_popup', '')
    email = self.get_argument('email', '')
    subscribe_to = self.get_argument('subscribe_to', '')
    error = ''
    status = ''
    slug = ''
    if close_popup != '':
      status = 'close_popup'

    # get the current user's email value
    user = userdb.get_user_by_screen_name(self.current_user)
    if user:
      # Clear the existing email address
      if email == '':
        if subscribe_to == '':
          user['email_address'] = ''
          self.set_secure_cookie('email_address', '')
          userdb.save_user(user)
          error = 'Your email address has been cleared.'
      else:
        # make sure someone else isn't already using this email
        existing = userdb.get_user_by_email(email)
        if existing and existing['user']['id_str'] != user['user']['id_str']:
          error = 'This email address is already in use.'
        else:
          # OK to save as user's email
          user['email_address'] = email
          userdb.save_user(user)
          self.set_secure_cookie('email_address', email)

          if subscribe_to != '':
            post = postsdb.get_post_by_slug(subscribe_to)
            if post:
              slug = post['slug']
              
            # Attempt to create the post's thread
            thread_id = 0
            try:
              # Attempt to create the thread.
              thread_details = disqus.create_thread(post, user['disqus_access_token'])
              thread_id = thread_details['response']['id']
            except:
              try:
                # trouble creating the thread, try to just get the thread via the slug
                thread_details = disqus.get_thread_details(post)
                thread_id = thread_details['response']['id']
              except:
                thread_id = 0

            if thread_id != 0:
              # Subscribe a user to the thread specified in response
              disqus.subscribe_to_thread(thread_id, user['disqus_access_token'])
    
    #save email prefs
    user['wants_daily_email'] = self.get_argument('wants_daily_email', False)
    if user['wants_daily_email'] == "on":
      user['wants_daily_email'] = True
    
    user['wants_email_alerts'] = self.get_argument('wants_email_alerts', False)
    if user['wants_email_alerts'] == "on":
      user['wants_email_alerts'] = True
              
    userdb.save_user(user)
    
    self.redirect("/user/%s/settings?msg=updated" % user['user']['screen_name'])

###########################
### LOG USER OUT OF ACCOUNT
### /auth/logout
###########################
class LogOut(app.basic.BaseHandler):
  def get(self):
    self.clear_all_cookies()
    self.redirect(self.get_argument('next', '/'))

##########################
### USER PROFILE
### /user/(.+)
##########################
class Profile(app.basic.BaseHandler):
  def get(self, screen_name, section="shares"):
    user = userdb.get_user_by_screen_name(screen_name)
    if not user:
      raise tornado.web.HTTPError(404)
    
    view = "profile"
    #section = self.get_argument('section', 'shares')
    tag = self.get_argument('tag', '')
    per_page = int(self.get_argument('per_page', 10))
    page = int(self.get_argument('page',1))
    if section == 'mentions':
      # get the @ mention list for this user
      posts = mentionsdb.get_mentions_by_user(screen_name.lower(), per_page, page)
    elif section =='bumps':
      posts = postsdb.get_posts_by_bumps(screen_name, per_page, page)
    else:
      if tag == '':
        posts = postsdb.get_posts_by_screen_name(screen_name, per_page, page)
      else:
        posts = postsdb.get_posts_by_screen_name_and_tag(screen_name, tag, per_page, page)

    # also get the list of tags this user has put in
    tags = tagsdb.get_user_tags(screen_name)

    self.render('user/profile.html', user=user, screen_name=screen_name, posts=posts, section=section, page=page, per_page=per_page, tags=tags, tag=tag, msg=None, view=view)

###########################
### USER SETTINGS
### /user/settings/?
###########################
class UserSettings(app.basic.BaseHandler):
  @tornado.web.authenticated
  def get(self, username=None):
    if username is None and self.current_user:
      username = self.current_user
    if username != self.current_user:
      raise tornado.web.HTTPError(401)
    
    if self.request.path.find("/user/settings") >= 0:
      self.redirect('/user/%s/settings' % username)
      
    msg = self.get_argument("msg", None)
    user = userdb.get_user_by_screen_name(self.current_user)
    if not user:
      raise tornado.web.HTTPError(404)
    
    user['wants_daily_email'] = user.get('wants_daily_email', False)
    user['wants_email_alerts'] = user.get('wants_email_alerts', True)
      
    #self.render('user/settings.html', user=user, msg=msg)
    self.render('user/profile.html', user=user, screen_name=self.current_user, posts=None, section="settings", page=None, per_page=None, tags=None, tag=None, msg=msg)

########NEW FILE########
__FILENAME__ = bitly
import bitly_api
import settings

def shorten_url(url):
  access_token = settings.get('bitly_access_token')
  c = bitly_api.Connection(access_token=access_token)
  return c.shorten(url)

def expand_url(hash_val):
  access_token = settings.get('bitly_access_token')
  c = bitly_api.Connection(access_token=access_token)
  return c.expand(hash_val)

########NEW FILE########
__FILENAME__ = companiesdb
import pymongo
from mongo import db

"""
{
  'id': 0
  'name': ''
  'url': ''
  'description': ''
  'logo_filename': ''
  'locations': ''
  'investment_series': ''
  'investment_year': ''
  'categories': ''
  'status': ''
  'slug': ''
  'investment_post_slug': ''
}
"""

def get_companies_by_status(status):
  # order by name
  return list(db.company.find({'status':status}, sort=[('name', pymongo.ASCENDING)]))

def get_company_by_slug(slug):
  return db.company.find_one({'slug':slug})

def save_company(company):
  if 'id' not in company.keys() or company['id'] == '':
    # need to create a new company id
    company['id'] = db.company.count() + 1

  company['id'] = int(company['id'])
  return db.company.update({'slug':company['slug']}, company, upsert=True)


########NEW FILE########
__FILENAME__ = datetime_overrider
from datetime import datetime
import settings

class datetime(datetime):
	def today(self):
		if settings.get('ENVIRONMENT') == "dev":
			return datetime.date('2014-02-01')
		else:
			return datetime.today()
########NEW FILE########
__FILENAME__ = disqus
import base64
import hashlib
import hmac
import json
import re
import requests
import settings
import time

from lib import postsdb
from lib import userdb
from lib import template_helpers

import logging

def check_for_thread(short_code, link):
  api_link = 'https://disqus.com/api/3.0/threads/details.json?api_key=%s&thread:link=%s&forum=%s' % (settings.get('disqus_public_key'), link, short_code)
  return do_api_request(api_link, 'GET')

def create_thread(post, access_token):
  api_link = 'https://disqus.com/api/3.0/threads/create.json'
  url = template_helpers.post_permalink(post)
  thread_info = {
    'forum': settings.get('disqus_short_code'),
    'title': post['title'].encode('utf-8'),
    'identifier':post['slug'],
    'url': url,
    'api_secret':settings.get('disqus_secret_key'),
    'api_key': settings.get('disqus_public_key'),
    'access_token': access_token
  }
  return do_api_request(api_link, 'POST', thread_info)

def get_post_details(post_id):
  message = {'id':'','message':'','author':{'username':'', 'email':''}}
  api_link = 'https://disqus.com/api/3.0/posts/details.json'
  api_key = settings.get('disqus_public_key')
  api_link = 'https://disqus.com/api/3.0/posts/details.json?api_key=%s&post=%s' % (api_key, post_id)
  disqus = do_api_request(api_link)
  if 'response' in disqus.keys():
    if 'id' in disqus['response'].keys():
      message['id'] = disqus['response']['id']
      message['message'] = disqus['response']['message']
      message['author']['username'] = disqus['response']['author']['username']
      if 'email' in disqus['response']['author'].keys():
        message['author']['email'] = disqus['response']['author']['email']
  return message

def get_thread_details(post):
  api_link = 'https://disqus.com/api/3.0/threads/details.json'
  info = {
    'api_key': settings.get('disqus_public_key'),
    'thread:link': template_helpers.post_permalink(post),
    'forum': settings.get('disqus_short_code'),
  }
  return do_api_request(api_link, 'GET', info)

def grep_short_code(link):
  # attempt to get the disqus short code out of a given page
  # http://continuations.disqus.com/embed.js vs. http://disqus.com/forums/avc/embed.js
  short_code = ''
  r = requests.get(link, verify=False)
  html = r.text
  m = re.search(r'http:\/\/disqus\.com\/forums\/([^/]+)', html)
  if m:
    short_code = m.group(1).strip()

  if short_code == '':
    m = re.search(r'http:\/\/([^.]+)\.disqus\.com', html)
    if m:
      short_code = m.group(1).strip()

  return short_code

#
# Subscribe to a thread
#
def subscribe_to_thread(thread_id, access_token):
  api_link = 'https://disqus.com/api/3.0/threads/subscribe.json'
  info = {
    'api_secret': settings.get('disqus_secret_key'),
    'api_key': settings.get('disqus_public_key'),
    'access_token': access_token,
    'thread': thread_id,
  }
  return do_api_request(api_link, 'POST', info)

#
# Subscribe to all your threads
#
def subscribe_to_all_your_threads(username):
  account = userdb.get_user_by_screen_name(username)
  # todo: get disqus_user_id
  # temp: nick's ID
  if 'disqus' not in account:
    print 'ERROR: no disqus user ID'
    return
  print 'subscribing to disqus threads for user %s' % username
  
  #make sure all your threads are registered w disqus
  posts = postsdb.get_posts_by_screen_name(username, per_page=25, page=1)
  for post in posts:
    print template_helpers.post_permalink(post)
    if 'disqus_thread_id_str' not in post.keys() or post.get('disqus_thread_id_str') == "":
      thread_details = create_thread(post, account['disqus']['access_token'])
      try:
        thread_id = thread_details['response']['id']
      except:
        thread = get_thread_details(post)
        thread_id = thread['response']['id']

      post['disqus_thread_id_str'] = thread_id
      postsdb.save_post(post)
    subscribe_to_thread(post.get('disqus_thread_id_str'), account['disqus']['access_token'])
  
  '''
  threads = get_all_threads(account['disqus']['user_id'])['response']
  my_threads = []
  for thread in threads:
    if 'link' not in thread or thread['link'] is None:
      continue
    if thread['link'].find('http://localhost') >= 0:
      continue
    my_threads.append(thread)
  if 'disqus' in account:
    for thread in my_threads:
      subscribe_to_thread(thread['id'], account['disqus']['access_token'])
      print 'subscribed to thread: %s' % thread['title']
  return
  '''
  return
  

def remove_all_your_threads(username):
  #account = userdb.get_user_by_screen_name(username)
  #get posts from disqus
  threads = get_all_threads(851030)
  for i, thread in enumerate(threads['response']):
    if thread['link'].find('http://localhost') == 0:
      print thread['link']
      print "----%s" % thread['identifiers']
      print "----%s" % thread['author']
      print "----%s" % thread['id']
      #print remove_thread(thread['id'])

def user_details(api_key, access_token, api_secret, user_id):
  api_link = 'https://disqus.com/api/3.0/users/details.json?access_token=%s&api_key=%s&api_secret=%s&user=%s' % (access_token, api_key, api_secret, int(user_id))
  return do_api_request(api_link)

#
# Get Threads
#
def get_all_threads(disqus_user_id=None):
  api_link = 'https://disqus.com/api/3.0/threads/list.json'
  info = {
    'api_secret': settings.get('disqus_secret_key'),
    'forum': settings.get('disqus_short_code'),
    'limit': 100
  }
  if disqus_user_id:
    info.update({
      'author': disqus_user_id
    })
  return do_api_request(api_link, 'GET', info)

def remove_thread(thread_id=None):
  if not thread_id:
    return
  api_link = 'https://disqus.com/api/3.0/threads/remove.json'
  info = {
    'api_secret': settings.get('disqus_secret_key'),
    'forum': settings.get('disqus_short_code'),
    'thread': thread_id,
    'access_token': "0a75d127c53f4a99bd853d721166af14"
  }
  return do_api_request(api_link, 'POST', info)


#####################################################
#### ACTUALLY HANDLE THE REQUESTS/RESPOSNE TO THE API
#####################################################
def do_api_request(api_link, method='GET', params={}):
  try:
    if method.upper() == 'GET':
      if len(params.keys()) > 0:
        r = requests.get(
          api_link,
          params=params,
          verify=False
        )
      else:
        r = requests.get(
          api_link,
          verify=False
        )
    else:
      r = requests.post(
        api_link,
        params=params,
        verify=False
      )
    disqus = r.json()
    print api_link
    print json.dumps(disqus, indent=4)
  except:
    disqus = {}
  return disqus

########NEW FILE########
__FILENAME__ = emailsdb
from mongo import db
import pymongo
import json
import logging
from datetime import datetime

from lib import postsdb, userdb

import settings
import urllib2
import requests

# track emails sent to users

"""
{
	_id: ...,
	timestamp: Date(),
	subject: "",
	body: "",
	recipients: []
}

"""
db.user_info.ensure_index('wants_daily_email')
	
#
# Construct a daily email
#
def construct_daily_email(slugs):
	from_email = "web@usv.com"
	subject = "Top USV.com posts for %s" % datetime.today().strftime("%a %b %d, %Y")
	body_html = "<p>Here are the posts with the mosts for today:</p><hr />"
	email_name = "Daily %s" % datetime.today().strftime("%a %b %d, %Y")
	
	posts = []
	for slug in slugs:
		post = postsdb.get_post_by_slug(slug)
		posts.append(post)
	
	for post in posts:
		post['url'] = post.get('url', '')
		source = post.get('domain', '')
		body_html += "<p><b><a href='%s'>%s</a></b></p>" % (post['url'], post['title'])
		body_html += "<p>posted by @<a href='http://%s/user/%s'>%s</a> | %s comments | %s &uarr;</p>" % (settings.get('base_url'), post['user']['username'], post['user']['username'], post['comment_count'], post['votes'])
		body_html += "<p>%s</p>" % post['body_html']
		body_html += "<p>discussion: <a href='http://%s/posts/%s'>http://%s/posts/%s</a></p>" % (settings.get('base_url'), post['slug'], settings.get('base_url'), post['slug'])
		body_html += "<hr />"
	body_html += "Want to unsubscribe? Visit http://%s/user/settings" % settings.get('base_url')
	
	email = {
		'from': from_email,
		'subject': subject,
		'body_html': body_html
	}
	
	# create the email
	# POST https://api.sendgrid.com/api/newsletter/add.json
	# @identity (created in advance == the sender's identity), @name (of email), @subject, @text, @html
	api_link = 'https://api.sendgrid.com/api/newsletter/add.json'
	params = {
		'identity': settings.get('sendgrid_sender_identity'),
		'name': email_name,
		'subject': email['subject'],
		'text': '', #to do get text version,
		'html': email['body_html']
	}
	result = do_api_request(api_link, method="POST", params=params)
	
	return result
	
#
# Setup Email List
#
def setup_email_list():
	email_sent = False
	recipients = userdb.get_newsletter_recipients()
	email_name = "Daily %s" % datetime.today().strftime("%a %b %d, %Y")

	# =====
	# 1) create a "list" for today's email	
	# POST https://api.sendgrid.com/api/newsletter/lists/add.json
	# @list (list name)
	api_link = 'https://api.sendgrid.com/api/newsletter/lists/add.json'
	params = {
		'list': email_name
	}
	result = do_api_request(api_link, method='POST', params=params)

	# 4) add everyone from our recipients list to the sendgrid list
	# POST https://api.sendgrid.com/api/newsletter/lists/email/add.json
	# list=ListName  data[]={ 'email': '', 'name': '' } & data[]={ 'email': '', 'name': '' }
	api_link = 'https://api.sendgrid.com/api/newsletter/lists/email/add.json'

	num_groups = int(math.ceil(len(recipients) / 50))
	recipient_groups = split_seq(recipients, num_groups) 

	for i, group in enumerate(recipient_groups):
		# sendgrid needs list add requests to be < 100 peole
		users = MultiDict()	
		for i, user in enumerate(group):
			if user.get('user').get('username') != "" and user.get('email_address') != "":
				users.add('data', '{"name":"%s","email":"%s"}' % (user.get('user').get('username'), user.get('email_address')))

		params = {
			'list': email_name,
			'data': users.getlist('data')
		}

		result = do_api_request(api_link, method='POST', params=params)

#
# Add the newly created list to the email
#
def add_list_to_email():
	email_name = "Daily %s" % datetime.today().strftime("%a %b %d, %Y")
	# 3) Add your list to the email
	# POST https://api.sendgrid.com/api/newsletter/recipients/add.json
	# @list (name of the list to assign to this email) @name (name of the email)
	api_link = 'https://api.sendgrid.com/api/newsletter/recipients/add.json'
	params = {
		'list': email_name,
		'name': email_name,
	}
	result = do_api_request(api_link, method="POST", params=params)
	print result

#
# Actually Send it
#
def send_email():
	email_name = "Daily %s" % datetime.today().strftime("%a %b %d, %Y")
	# 5) send the email
	# POST https://api.sendgrid.com/api/newsletter/schedule/add.json
	# @email (created in step 3)
	api_link = 'https://api.sendgrid.com/api/newsletter/schedule/add.json'
	params = {
		'email': email,
		'name': "Daily %s" % datetime.datetime.today().strftime("%a %b %d, %Y")
	}
	result = do_api_request(api_link, 'POST', params=params)
	return result

#
# Add a daily email to the log
#
def log_daily_email(email, recipient_usernames):
	data = {
		'timestamp': datetime.now(),
		'subject': email['subject'],
		'body': email['body_html'],
		'recipients': recipient_usernames
	}
	db.email.daily.insert(data)
	
#
# Get log of daily emails
#
def get_daily_email_log():
	return list(db.email.daily.find({}, sort=[('timestamp', pymongo.DESCENDING)]))
	

#####################################################
#### ACTUALLY HANDLE THE REQUESTS/RESPOSNE TO THE API
#####################################################
def do_api_request(api_link, method='GET', params={}):
	# add sendgrid user & api key
	params.update({
		'api_user': settings.get('sendgrid_user'),
		'api_key': settings.get('sendgrid_secret')
	})
	try:
		if method.upper() == 'GET':
			if len(params.keys()) > 0:
				r = requests.get(
					api_link,
					params=params,
					verify=False
				)
			else:
				r = requests.get(
					api_link,
					verify=False
				)
		else:
			r = requests.post(
				api_link,
				params=params,
				verify=False
			)
		response = r.json()
	except:
		response = {}
	if settings.get('environment') == "dev":
		logging.info("=================")
		logging.info( api_link)
		logging.info( json.dumps(params, indent=4))
		logging.info( response)
		logging.info( "=================")
	return response
########NEW FILE########
__FILENAME__ = google
# -*- coding: utf-8 -*-

"""
Basic google link shortener api handler - https://developers.google.com/url-shortener/v1/getting_started
"""

import requests
import simplejson as json
import settings

def shorten_url(url):
  goo_key = settings.get('google_api_key')
  r = requests.post(
    'https://www.googleapis.com/urlshortener/v1/url?key=%s' % goo_key,
    data=json.dumps({'longUrl': url}),
    headers={'Content-Type': 'application/json; charset=UTF-8'},
    verify=False
  )
  return json.loads(r.text)

def expand_url(url):
  r = requests.get(
    'https://www.googleapis.com/urlshortener/v1/url?shortUrl=%s' % url,
    verify=False
  )
  return json.loads(r.text)


########NEW FILE########
__FILENAME__ = hackpad
from tornado import escape
from tornado.auth import _oauth10a_signature
import urllib
from urlparse import urljoin
import requests
import settings
import time
import binascii
import uuid
import logging
import sys

"""
Hackpad API. Documentation: https://hackpad.com/Public-Hackpad-API-Draft-nGhsrCJFlP7
"""

# Returns all of the pad IDs
def list_all():
  return do_api_request('pads/all', 'GET')

# Creates and returns the new pad ID
def create_hackpad():
  return do_api_request('pad/create', 'POST', {}, 'Hackpad Title\nHackpad contents.')

def do_api_request(path, method, post_data={}, body=''):
  try:
    url = urljoin('https://%s.hackpad.com/api/1.0/' % settings.get('hackpad_domain'), path)
    args = dict(
      oauth_consumer_key=escape.to_basestring(settings.get('hackpad_oauth_client_id')),
      oauth_signature_method='HMAC-SHA1',
      oauth_timestamp=str(int(time.time())),
      oauth_nonce=escape.to_basestring(binascii.b2a_hex(uuid.uuid4().bytes)),
      oauth_version='1.0a',
    )
    signature = _oauth10a_signature(
      {
        'key':settings.get('hackpad_oauth_client_id'),
        'secret':settings.get('hackpad_oauth_secret')
      },
      method,
      url,
      args
    )
    args['oauth_signature'] = signature
    api_link = url + '?' + urllib.urlencode(args)
    logging.info(api_link)

    hackpad = {}
    if method.lower() == 'post':
      r = requests.post(
        api_link,
        data=body,
        headers={'Content-Type': 'text/plain'},
        verify=False
      )
      hackpad = r.json
    else:
      r = requests.get(
        api_link,
        headers={'Content-Type': 'text/plain'},
        verify=False
      )
      hackpad = r.json
  except:
    logging.info(sys.exc_info()[0])
    hackpad = {}

  return hackpad

########NEW FILE########
__FILENAME__ = mentionsdb
import pymongo

from datetime import datetime
from mongo import db

"""
{
  'screen_name': '',
  'slug': '',
  'date_created': new Date()
}
"""

def add_mention(screen_name, slug):
  return db.mentions.update({'screen_name': screen_name, 'slug': slug}, {'screen_name': screen_name, 'slug': slug, 'date_created': datetime.utcnow()}, upsert=True)

def get_mentions_by_user(screen_name, per_page, page):
  mentions = list(db.mentions.find({'screen_name': screen_name}, sort=[('date_created', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))
  posts = []
  for mention in mentions:
    posts.append(db.post.find_one({'slug':mention['slug']}))
  return posts

########NEW FILE########
__FILENAME__ = mongo
import logging
import pymongo
import settings


class Proxy(object):
  _db = None
  def __getattr__(self, name):
    if Proxy._db == None:
      # lazily connect to the db so we pickup the right environment settings
      mongo_database = settings.get('mongo_database')
      logging.info("connecting to mongo at %s:%d/%s" % (mongo_database['host'], mongo_database['port'], mongo_database['db']))
      connection = pymongo.MongoClient(mongo_database['host'], mongo_database['port'], connectTimeoutMS=5000, max_pool_size=200)
      Proxy._db = connection[mongo_database['db']]

    return getattr(self._db, name)

db = Proxy()
########NEW FILE########
__FILENAME__ = postsdb
import pymongo
import re
import settings
import json
from datetime import datetime
from datetime import date
from datetime import timedelta

from mongo import db
from slugify import slugify

"""
{
  'date_created':new Date(),
  'title': '',
  'slugs': [],
  'slug': '',
  'user': { 'id_str':'', 'auth_type': '', 'username': '', 'fullname': '', 'screen_name': '', 'profile_image_url_https': '', 'profile_image_url': '', 'is_blacklisted': False },
  'tags': [],
  'votes': 0,
  'voted_users': [{ 'id_str':'', 'auth_type': '', 'username': '', 'fullname': '', 'screen_name': '', 'profile_image_url_https': '', 'profile_image_url': '', 'is_blacklisted': False }],
  'deleted': False,
  'date_deleted': new Date(),
  'featured': False
  'date_featured': new Date(),
  'url': '',
  'normalized_url': '',
  'hackpad_url': '',
  'has_hackpad': False,
  'body_raw': '',
  'body_html': '',
  'body_truncated': '',
  'body_text': '',
  'disqus_shortname': 'usvbeta2',
  'muted': False,
  'comment_count': 0,
  'disqus_thread_id_str': '',
  'sort_score': 0.0,
  'downvotes': 0,
  'super_upvotes': 0,
  'super_downvotes': 0,
  'subscribed':[]
}
"""

###########################
### GET A SPECIFIC POST
###########################
def get_post_by_slug(slug):
  return db.post.find_one({'slug':slug})

  
def get_all():
  return list(db.post.find(sort=[('date_created', pymongo.DESCENDING)]))

###########################
### GET PAGED LISTING OF POSTS
###########################
def get_posts_by_bumps(screen_name, per_page, page):
  return list(db.post.find({'voted_users.screen_name':screen_name, 'user.screen_name':{'$ne':screen_name}}, sort=[('date_created', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))

def get_posts_by_query(query, per_page=10, page=1):
  query_regex = re.compile('%s[\s$]' % query, re.I)
  return list(db.post.find({'$or':[{'title':query_regex}, {'body_raw':query_regex}]}, sort=[('date_created', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))

def get_posts_by_tag(tag):
  return list(db.post.find({'deleted': { "$ne": True }, 'tags':tag}, sort=[('date_created', pymongo.DESCENDING)]))

def get_posts_by_screen_name(screen_name, per_page=10, page=1):
  return list(db.post.find({'deleted': { "$ne": True }, 'user.screen_name':screen_name}, sort=[('date_created', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))

def get_posts_by_screen_name_and_tag(screen_name, tag, per_page=10, page=1):
  return list(db.post.find({'deleted': { "$ne": True }, 'user.screen_name':screen_name, 'tags':tag}, sort=[('date_created', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))

def get_featured_posts(per_page=10, page=1):
  return list(db.post.find({'deleted': { "$ne": True }, 'featured':True}, sort=[('date_created', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))

def get_new_posts(per_page=50, page=1):
  return list(db.post.find({"deleted": { "$ne": True }}, sort=[('_id', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))

def get_hot_posts(per_page=50, page=1):
  return list(db.post.find({"votes": { "$gte" : 2 }, "deleted": { "$ne": True }}, sort=[('sort_score', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))
  
def get_hot_posts_by_day(day=date.today()):
  day = datetime.combine(day, datetime.min.time())
  day_plus_one = day + timedelta(days=1)
  return list(db.post.find({"deleted": { "$ne": True }, 'date_created': {'$gte': day, '$lte': day_plus_one}}, sort=[('daily_sort_score', pymongo.DESCENDING)]))

def get_daily_posts_by_sort_score(min_score=8):
  day=date.today()
  day = datetime.combine(day, datetime.min.time())
  day_plus_one = day + timedelta(days=1)
  return list(db.post.find({'daily_sort_score': {"$gte" : min_score }, "deleted": { "$ne": True }, 'date_created': {'$gte': day, '$lte': day_plus_one}}, sort=[('daily_sort_score', pymongo.DESCENDING)]))

def get_hot_posts_24hr():
  now = datetime.now()
  then = now - timedelta(hours=24)
  return list(db.post.find({"deleted": { "$ne": True }, 'date_created': {'$gte': then }}, sort=[('daily_sort_score', pymongo.DESCENDING)]))

def get_sad_posts(per_page=50, page=1):
  return list(db.post.find({'date_created':{'$gt': datetime.datetime.strptime("10/12/13", "%m/%d/%y")}, 'votes':1, 'comment_count':0, 'deleted': { "$ne": True } , 'featured': False}, sort=[('date_created', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))

def get_deleted_posts(per_page=50, page=1):
  return list(db.post.find({'deleted':True}, sort=[('date_deleted', pymongo.DESCENDING)]).skip((page-1)*per_page).limit(per_page))

###########################
### AGGREGATE QUERIES
###########################
def get_unique_posters(start_date, end_date):
  return db.post.group(["user.screen_name"], {'date_created':{'$gte': start_date, '$lte': end_date}}, {"count":0}, "function(o, p){p.count++}" )

###########################
### GET POST COUNTS
###########################
def get_featured_posts_count():
  return len(list(db.post.find({'featured':True})))

def get_post_count_by_query(query):
  query_regex = re.compile('%s[\s$]' % query, re.I)
  return len(list(db.post.find({'$or':[{'title':query_regex}, {'body_raw':query_regex}]})))

def get_post_count():
  return len(list(db.post.find({'date_created':{'$gt': datetime.datetime.strptime("10/12/13", "%m/%d/%y")}})))

def get_post_count_for_range(start_date, end_date):
  return len(list(db.post.find({'date_created':{'$gte': start_date, '$lte': end_date}})))

def get_delete_posts_count():
  return len(list(db.post.find({'deleted':True})))

def get_post_count_by_tag(tag):
  return len(list(db.post.find({'tags':tag})))

###########################
### GET LIST OF POSTS BY CRITERIA
###########################
def get_latest_staff_posts_by_tag(tag, limit=10):
  staff = settings.get('staff')
  return list(db.post.find({'deleted': { "$ne": True }, 'user.username': {'$in': staff}, 'tags':tag}, sort=[('date_featured', pymongo.DESCENDING)]).limit(limit))

def get_posts_by_normalized_url(normalized_url, limit):
  return list(db.post.find({'normalized_url':normalized_url, 'deleted': { "$ne": True }}, sort=[('_id', pymongo.DESCENDING)]).limit(limit))

def get_posts_with_min_votes(min_votes):
  return list(db.post.find({'deleted': { "$ne": True }, 'votes':{'$gte':min_votes}}, sort=[('date_created', pymongo.DESCENDING)]))
  
def get_hot_posts_past_week():
  yesterday = datetime.today() - timedelta(days=1)
  week_ago = datetime.today() - timedelta(days=5)
  return list(db.post.find({'deleted': { "$ne": True }, 'date_created':{'$lte':yesterday, '$gte': week_ago}}, sort=[('daily_sort_score', pymongo.DESCENDING)]).limit(5))

def get_related_posts_by_tag(tag):
  return list(db.post.find({'deleted': { "$ne": True }, 'tags':tag}, sort=[('daily_sort_score', pymongo.DESCENDING)]).limit(2))

###########################
### UPDATE POST DETAIL
###########################
def add_subscriber_to_post(slug, email):
  return db.post.update({'slug':slug}, {'$addToSet': {'subscribed': email}})

def remove_subscriber_from_post(slug, email):
  return db.post.update({'slug':slug}, {'$pull': {'subscribed': email}})

def save_post(post):
  return db.post.update({'_id':post['_id']}, post)

def update_post_score(slug, score, scores):
  return db.post.update({'slug':slug}, {'$set':{'daily_sort_score': score, 'scores': scores}})

def delete_all_posts_by_user(screen_name):
  db.post.update({'user.screen_name':screen_name}, {'$set':{'deleted':True, 'date_delated': datetime.datetime.utcnow()}}, multi=True)

###########################
### ADD A NEW POST
###########################
def insert_post(post):
  slug = slugify(post['title'])
  slug_count = len(list(db.post.find({'slug':slug})))
  if slug_count > 0:
    slug = '%s-%i' % (slug, slug_count)
  post['slug'] = slug
  post['slugs'] = [slug]
  if 'subscribed' not in post.keys():
    post['subscribed'] = []
  db.post.update({'url':post['slug'], 'user.screen_name':post['user']['screen_name']}, post, upsert=True)
  return post['slug']

###########################
### SORT ALL POSTS
### RUN BY HEROKU SCHEDULER EVERY 5 MIN
### VIA SCRIPTS/SORT_POSTS.PY
###########################
def sort_posts(day="all"):
  # set our config values up
  staff_bonus = -3
  comments_multiplier = 3.0
  votes_multiplier = 1.0
  super_upvotes_multiplier = 3.0
  super_downvotes_multiplier = 3.0

  if day == "all":
    posts = get_all()
  else:
    posts = get_hot_posts_by_day(day)

  for post in posts:
    # determine if we should assign a staff bonus or not
    if post['user']['username'] in settings.get('staff'):
      staff_bonus = staff_bonus
    else:
      staff_bonus = 0

    # determine how to weight votes
    votes_base_score = 0
    if post['votes'] == 1 and post['comment_count'] > 2:
      votes_base_score = -2
    if post['votes'] > 8 and post['comment_count'] == 0:
      votes_base_score = -2

    if 'super_upvotes' in post.keys():
      super_upvotes = post['super_upvotes']
    else:
      super_upvotes = 0
    #super_upvotes = post.get('super_upvotes', 0)
    super_downvotes = post.get('super_downvotes', 0)

    # calculate the sub-scores
    scores = {}
    scores['votes'] = (votes_base_score + post['votes'] * votes_multiplier)
    scores['super_upvotes'] = (super_upvotes * super_upvotes_multiplier)
    scores['super_downvotes'] = (super_downvotes * super_downvotes_multiplier * -1)
    scores['comments'] = (post['comment_count'] * comments_multiplier)

    # add up the scores
    total_score = 0
    total_score += staff_bonus
    for score in scores:
      total_score += scores[score]

    # and save the new score
    post['scores'] = scores
    update_post_score(post['slug'], total_score, scores)
    print post['slug']
    print "-- %s" % total_score
    print "---- %s" % json.dumps(scores, indent=4)

  print "All posts sorted!"
########NEW FILE########
__FILENAME__ = sanitize
import bleach
from bs4 import BeautifulSoup

allowed_tags = ['a', 'b', 'p', 'i', 'blockquote', 'span', 'ul', 'li', 'ol',
  'strong', 'pre', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'br', 'span']
allowed_attrs = {
  'a': ['href', 'rel'],
}

allowed_tags_media = list(allowed_tags)
allowed_tags_media += ['iframe', 'object', 'embed', 'img']
allowed_attrs_media = dict(allowed_attrs)
allowed_attrs_media.update({
  'iframe': ['src', 'frameborder', 'width', 'height'],
  'img': ['src', 'alt', 'width', 'height'],
  'embed': ['src', 'type', 'width', 'height'],
  'object': ['data', 'type', 'width', 'height'],
})

allowed_styles = ['text-decoration']

# This is exposed to templates as a template method.
# See ui/template_methods.py
def tinymce_valid_elements(media=True):
  if media:
    tags = allowed_tags_media
    attrs = allowed_attrs_media
  else:
    tags = allowed_tags
    attrs = allowed_attrs
  valid_list = []
  for tag in tags:
    elem_attrs = attrs.get(tag)
    if elem_attrs:
      tag += '[%s]' % '|'.join(elem_attrs)
    valid_list.append(tag)
  return ','.join(valid_list)

def linkify(input):
  return bleach.linkify(input)

def html_sanitize(input, media=True):
  if media:
    tags = allowed_tags_media
    attrs = allowed_attrs_media
  else:
    tags = allowed_tags
    attrs = allowed_attrs
  text = bleach.clean(input, tags=tags, attributes=attrs, styles=allowed_styles)
  return text

def html_sanitize_preview(input):
  return bleach.clean(input, tags=[], attributes=[], styles=[], strip=True)

def html_to_text(text):
  soup = BeautifulSoup(text)
  for br in soup.find_all('br'):
    br.string = ' '
  text = soup.get_text()
  return text

def truncate(text, length, ellipsis=True):
  truncated = text[:length]
  if ellipsis and len(text) > length:
    truncated += '...'
  return truncated

########NEW FILE########
__FILENAME__ = statsdb
from mongo import db
import postsdb

import settings
import urllib2
import datetime

# For stats, we have two collections:
# "daily" and "weekly"
# a document in each collection is a day or a week
# each collection looks like:

"""
{
	_id: ...,
	timestamp: Date(),
	metric1: 0
}

"""

def insert_stat(stat="foo", value="Bar", timescale="day"):
	#
	# We expect that stats will be added on a daily basis
	# Via a cron job, at 12:01 am
	#
	
	# handle time -- create timestamp for start of preceding day at 12:00am
	now = datetime.datetime.now()
	today = datetime.datetime(now.year, now.month, now.day)
	yesterday = today - datetime.timedelta(days=1) 
	
	# calculate the appropriate monday -- for week beginning that monday
	dow = yesterday.weekday()
	monday = yesterday - datetime.timedelta(days=dow)
	
	# setup daystats object
	daystats = db.stats.daily.find_one({'timestamp': yesterday})
	if daystats:
		daystats[stat] = value
	else:
		daystats = {
			'timestamp': yesterday,
			stat: value
		}
	
	# upsert the daily document
	db.stats.daily.update({'timestamp': yesterday }, daystats, upsert=True)
	
	# upsert the weekly document. 
	sumkey = "%s.sum" % stat
	countkey = "%s.count" % stat
	db.stats.weekly.update( { 'timestamp': monday }, { '$inc': { sumkey : value, countkey : 1 } }, upsert=True )
########NEW FILE########
__FILENAME__ = tagsdb
from bson.son import SON
from mongo import db
from datetime import timedelta
from datetime import datetime

def get_user_tags(screen_name):
  tags = db.post.aggregate([
    {'$unwind':'$tags'},
    {'$match': {'user.screen_name':screen_name}},
    {'$group': {'_id': '$tags', 'count': {'$sum': 1}}},
    {"$sort": SON([("count", -1), ("_id", -1)])}
  ])
  return tags

def get_all_tags(sort=None):
  if not sort or sort == "count":
    sort = SON([("count", -1), ("_id", -1)])
  if sort == "alpha":
    sort = SON([("_id", 1)])
  
  tags = db.post.aggregate([
    {'$unwind':'$tags'},
    {'$group': {'_id': '$tags', 'count': {'$sum': 1}}},
    {"$sort": sort}
  ])
  return tags

def get_hot_tags():
  today = datetime.today()
  two_weeks_ago = today + timedelta(days=-14)
  tags = db.post.aggregate([
    {'$unwind':'$tags'},
    {'$match': {'date_created':{'$gte':two_weeks_ago}}},
    {'$group': {'_id': '$tags', 'count': {'$sum': 1}}},
    {"$sort": SON([("count", -1), ("_id", -1)])},
    {"$limit": 24}
  ])
  return tags

def get_user_tags(screen_name):
  tags = db.post.aggregate([
    {'$unwind':'$tags'},
    {'$match': {'user.screen_name':screen_name}},
    {'$group': {'_id': '$tags', 'count': {'$sum': 1}}},
    {"$sort": SON([("count", -1), ("_id", -1)])}
  ])
  return tags

def save_tag(tag):
  return db.tag.update({'name':tag}, {'name':tag}, upsert=True)

########NEW FILE########
__FILENAME__ = template_helpers
from lib.sanitize import tinymce_valid_elements
import datetime
import settings

def tinymce_valid_elements_wrapper(media=True):
  return tinymce_valid_elements(media=media)

# Twitter URLs are stored as their 'normal' size
# eg. http://a0.twimg.com/profile_images/3428823565/9c49c693a9b7527b3fb7e36f6bba627f_normal.png
def twitter_avatar_size(url, size):
  if size == 'original':
    url = url.replace('_normal', '')
  else:
    url = url.replace('_normal', '_%s' % size)
  return url

# Adapted from http://bit.ly/17wpDuh
def pretty_date(d):
  diff = datetime.datetime.now() - d
  s = diff.seconds
  if diff.days != 0:
    return d.strftime('%b %d, %Y')
  elif s <= 1:
    return 'just now'
  elif s < 60:
    return '{} seconds ago'.format(s)
  elif s < 120:
    return '1 minute ago'
  elif s < 3600:
    return '{} minutes ago'.format(s/60)
  elif s < 7200:
    return '1 hour ago'
  else:
    return '{} hours ago'.format(s/3600)
  
# display a permalink to a post
def post_permalink(p):
  return 'http://' + settings.get('base_url') + "/posts/" + p['slug']

########NEW FILE########
__FILENAME__ = userdb
from mongo import db
import postsdb

# For update_twitter
import tweepy
import settings
import urllib2

"""
{
  'user': { 'id_str':'', 'auth_type': '', 'username': '', 'fullname': '', 'screen_name': '', 'profile_image_url_https': '', 'profile_image_url': '', 'is_blacklisted': False }
  'access_token': { 'secret': '', 'user_id': '', 'screen_name': '', 'key': '' },
  'email_address': '',
  'role': '',
  'tags':[]
}

"""
#db.user_info.ensure_index('user.screen_name')

def get_all():
  return list(db.user_info.find({}))

def get_user_by_id_str(id_str):
  return db.user_info.find_one({'user.id_str': id_str})

def get_user_by_screen_name(screen_name):
  return db.user_info.find_one({'user.screen_name': screen_name})

def get_user_by_email(email_address):
  return db.user_info.find_one({'email_address':email_address})
  
def get_disqus_users():
  return db.user_info.find({'disqus': { '$exists': 'true' }})
  
def get_newsletter_recipients():
  return list(db.user_info.find({'wants_daily_email': True}))

def create_new_user(user, access_token):
  return db.user_info.update({'user.id_str': user['id_str']}, {'user':user, 'access_token':access_token, 'email_address':'', 'role':''}, upsert=True)

def save_user(user):
  return db.user_info.update({'user.id_str': user['user']['id_str']}, user)

def get_user_count():
  return db.user_info.count()

def add_tags_to_user(screen_name, tags=[]):
  return db.user_info.update({'user.screen_name':screen_name}, {'$addToSet':{'tags':{'$each':tags}}})

###########################
### SCRIPT FUNCTIONS
###########################
''' Updates twitter account of id id_str, or else updates all twitter accounts.
    Updating all accounts will probably cause API to puke from too many requests '''
def update_twitter(id_str=None, api=None):
  if not api:
    consumer_key = settings.get('twitter_consumer_key')
    consumer_secret = settings.get('twitter_consumer_secret')
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
    api = tweepy.API(auth) 

  if id_str:
    users = [get_user_by_id_str(id_str)]
  else:
    users = get_all()

  for user in users:
    id_str = user['user']['id_str']
    twitter_user = api.get_user(id=id_str)
    if id_str != twitter_user.id_str:
      raise Exception

    user_data = {
      'auth_type': 'twitter',
      'id_str': twitter_user.id_str,
      'username': twitter_user.screen_name,
      'fullname': twitter_user.name,
      'screen_name': twitter_user.screen_name,
      'profile_image_url': twitter_user.profile_image_url,
      'profile_image_url_https': twitter_user.profile_image_url_https,
    }

    updated_user = {'access_token': user['access_token'], 'user': user_data}
    save_user(updated_user)
    print "++ Updated user @%s" % user['user']['username']
    user_posts = postsdb.get_posts_by_screen_name(twitter_user.screen_name, per_page=100, page=1)
    for p in user_posts:
      p['user'] = user_data
      postsdb.save_post(p)
      print "++++ Updated %s info for %s" % (p['user']['screen_name'], p['title'])

''' Only updates a user if their twitter profile image URL returns a 404 '''
def update_twitter_profile_images():
  consumer_key = settings.get('twitter_consumer_key')
  consumer_secret = settings.get('twitter_consumer_secret')
  auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
  api = tweepy.API(auth) 

  for user in get_all():
    print "Checking user %s" % user['user']['screen_name']
    try:
        response= urllib2.urlopen(user['user']['profile_image_url_https'])
    except urllib2.HTTPError, e:
        if e.code == 404:
          update_twitter(id_str=user['user']['id_str'], api=api)
      

''' Update all account info from twitter, i.e. profile pic 
    This currently times out for making too many API calls '''
'''
def update_twitter_all():
  consumer_key = settings.get('twitter_consumer_key')
  consumer_secret = settings.get('twitter_consumer_secret')
  auth = tweepy.OAuthHandler(consumer_key, consumer_secret, secure=True)
  api = tweepy.API(auth) 

  for user in get_all():
    id_str = user['user']['id_str']
    twitter_user = api.get_user(id=id_str)
    if id_str != twitter_user.id_str:
      raise Exception

    user_data = {
      'auth_type': 'twitter',
      'id_str': twitter_user.id_str,
      'username': twitter_user.screen_name,
      'fullname': twitter_user.name,
      'screen_name': twitter_user.screen_name,
      'profile_image_url': twitter_user.profile_image_url,
      'profile_image_url_https': twitter_user.profile_image_url_https,
    }

    updated_user = {'access_token': user['access_token'], 'user': user_data}
    save_user(updated_user)
    print "Updated user @%s" % user['user']['username']
'''
########NEW FILE########
__FILENAME__ = voted_users
import sys
sys.path.insert(0, '/Users/nick/dev/conversation')
import settings
from lib import postsdb
from lib import userdb
from mongo import db
import logging

#
# MIGRATES from the old voted users format
# to the new one.
# meant to be run by hand from the command line, e.g. python voted_users.py
# Update the path above to whatever path is right on your machine (root of this app)
#


posts = postsdb.get_posts_by_query("", 3000)

for post in posts:
	voted_users = []
	for v in post['voted_users']:
		# OLD FORMAT
		if '_id' in v:
			user_info = userdb.get_user_by_id_str(v['_id'])
			if user_info:
				voted_users.append(user_info['user'])
		# NEW FORMAT
		if 'id_str' in v:
			user_info = userdb.get_user_by_id_str(v['id_str'])
			if user_info:
				voted_users.append(user_info['user'])
				
	if db.post.update({'_id':post['_id']}, {'$set': {'voted_users': voted_users, 'votes': len(voted_users)}}):
		print('saved post: [%s votes] %s' % (str(len(voted_users)), post['title']))
########NEW FILE########
__FILENAME__ = daily_newsletter

########NEW FILE########
__FILENAME__ = disqus_subscribe_to_existing
# Run by Heroku scheduler every night
# If running locally, uncomment below imports
import sys
try:
	sys.path.insert(0, '/Users/nick/dev/usv/usv.com')
except:
	pass
import settings
import requests
import logging
from lib import postsdb
from lib import disqus
from lib import userdb

# =================================================================
# This script finds all users that have authenticated with Disqus
# and then sweeps back through their disqus threads
# and make sure they are subscribed to all of them.
# =================================================================

#
# Find all users who have disqus_user_ids
#
disqus_users = userdb.get_disqus_users()

#
# for each user, subscribe them to all of their threads
#
for u in disqus_users:
	print u['user']['username']
	print "-- %s" % u['disqus']['user_id']
	disqus.subscribe_to_all_your_threads(u['user']['username'])
########NEW FILE########
__FILENAME__ = mongo
import logging
import pymongo

class Proxy(object):
  _db = None
  def __getattr__(self, name):
    if Proxy._db == None:
      # lazily connect to the db so we pickup the right environment settings
      logging.info("connecting to mongo at %s:%d/%s" % ('localhost', 27017, 'usv'))
      connection = pymongo.MongoClient('localhost', 27017, connectTimeoutMS=5000, max_pool_size=200)
      Proxy._db = connection['usv']

    return getattr(self._db, name)

db = Proxy()
########NEW FILE########
__FILENAME__ = populate_old_features
import requests
import re
import slugify
import sanitize

from datetime import datetime
from mongo import db

old_posts = {
  "/2005/09/is-bill-gates-t.php": "/posts/is-bill-gates-the-cat-with-nine-lives",
  "/2005/10/location-locati.php": "/posts/location-location-location",
  "/2005/10/the-problem-wit.php": "/posts/the-problem-with-podcasts",
  "/2005/10/wikis.php": "/posts/wikis",
  "/2005/10/inspiration.php": "/posts/inspiration",
  "/2005/10/downturns.php": "/posts/downturns",
  "/2005/10/impact-media.php": "/posts/impact-media",
  "/2005/10/a-new-dimension.php": "/posts/a-new-dimension",
  "/2005/10/indeed.php": "/posts/indeed",
  "/2005/10/delicious.php": "/posts/delicious",
  "/2005/10/audience-manage.php": "/posts/audience-management",
  "/2005/09/union-square-ve.php": "/posts/union-square-ventures",
  "/2005/10/10-steps-to-a-h.php": "/posts/10-steps-to-a-hugely-successful-web-20-company",
  "/2005/10/founders.php": "/posts/founders",
  "/2005/10/hello-world.php": "/posts/hello-world",
  "/2005/10/web-services-ar.php": "/posts/web-services-are-different",
  "/2005/10/metrics.php": "/posts/metrics",
  "/2005/10/management-case.php": "/posts/management-case-base-case-and-worst-case",
  "/2005/10/usv-sessions-1.php": "/posts/union-square-sessions-1-peer-production",
  "/2005/10/usv-sessions-1-1.php": "/posts/union-square-sessions-1-photos",
  "/2005/10/union-square-se.php": "/posts/union-square-sessions-1-transcript",
  "/2005/10/peer-production.php": "/posts/peer-production-in-action",
  "/2005/10/we-dont-get-it.php": "/posts/we-dont-get-it",
  "/2005/10/vc-cliche-of-th.php": "/posts/vc-cliche-of-the-week",
  "/2005/10/seeking-a-super.php": "/posts/seeking-a-super-talented-productdesign-person",
  "/2005/10/sessions-top-te.php": "/posts/sessions-top-ten-insights-one",
  "/2005/10/post.php": "/posts/sessions-top-ten-insights-two",
  "/2005/11/sessions-top-te-2.php": "/posts/sessions-top-ten-insights-three",
  "/2005/11/vc-cliche-of-th-1.php": "/posts/vc-cliche-of-the-week-2",
  "/2005/11/sessions-top-te-1.php": "/posts/sessions-top-ten-insights-four",
  "/2005/11/will-live-kill.php": "/posts/will-live-kill",
  "/2005/11/sessions-top-te-3.php": "/posts/sessions-top-ten-insights-five",
  "/2005/11/vc-cliche-of-th-2.php": "/posts/vc-cliche-of-the-week-3",
  "/2005/11/are-reputations.php": "/posts/sessions-top-ten-insights-six-reputations-are-not-portable",
  "/2005/11/our-customer-is.php": "/posts/our-customer-is-the-entrepreneur",
  "/2005/11/sessions-top-te-5.php": "/posts/sessions-top-ten-insights-seven-less-control-can-create-more-value",
  "/2005/11/cliche-of-the-w.php": "/posts/cliche-of-the-week",
  "/2005/11/sessions-top-te-4.php": "/posts/sessions-top-ten-insights-eight-putting-a-string-on-data",
  "/2005/11/evolution-vs-in.php": "/posts/evolution-vs-intelligent-design",
  "/2005/11/cliche-of-the-w-1.php": "/posts/cliche-of-the-week-2",
  "/2005/11/powered-by.php": "/posts/powered-by",
  "/2005/11/cliche-of-the-w-2.php": "/posts/cliche-of-the-week-3",
  "/2005/12/cliche-of-the-w-3.php": "/posts/cliche-of-the-week-4",
  "/2005/12/a-delicious-eig-1.php": "/posts/a-delicious-eight-months",
  "/2005/12/cliche-of-the-w-4.php": "/posts/cliche-of-the-week-5",
  "/2005/12/cliche-of-the-w-5.php": "/posts/cliche-of-the-week-6",
  "/2006/01/vc-cliche-of-th-3.php": "/posts/cliche-of-the-week-7",
  "/2006/01/cliche-of-the-w-6.php": "/posts/cliche-of-the-week-8",
  "/2006/01/web-services-in.php": "/posts/web-services-in-the-mist",
  "/2006/01/rich-media-real.php": "/posts/rich-media-realities",
  "/2006/01/advertising-out.php": "/posts/advertising-out-of-context",
  "/2006/01/instant-job-boa.php": "/posts/instant-job-board",
  "/2006/01/indeed-job-data-1.php": "/posts/indeed-job-data",
  "/2006/01/physics-the-sec.php": "/posts/physics-the-second-law-of-thermodynamics",
  "/2006/02/web-20-is-an-ox.php": "/posts/web-20-is-an-oxymoron",
  "/2006/02/post-1.php": "/posts/mathematics-how-much-is-enough",
  "/2006/02/feedburner.php": "/posts/feedburner",
  "/2006/02/why-we-invested.php": "/posts/why-we-invested-in-feedburner",
  "/2006/02/research-and-de.php": "/posts/research-and-development",
  "/2006/02/advisory-capita.php": "/posts/advisory-capital",
  "/2006/02/web-services-an.php": "/posts/web-services-and-devices",
  "/2006/03/tacoda-raises-1.php": "/posts/tacoda-raises-12-million",
  "/2006/03/looking-ahead.php": "/posts/looking-ahead",
  "/2006/03/will-computing-1.php": "/posts/will-computing-ever-be-as-invisible-as-electricity",
  "/2006/03/yes-but.php": "/posts/yes-but",
  "/2006/04/taking-web-serv.php": "/posts/taking-web-services-to-the-office",
  "/2006/04/why-has-the-flo.php": "/posts/why-has-the-flow-of-technology-reversed",
  "/2006/05/a-stray-thought-1.php": "/posts/a-stray-thought-on-the-micro-chunking-of-media",
  "/2006/05/user-tagging-is-1.php": "/posts/user-tagging-is-fundamental",
  "/2006/05/on-influence-1.php": "/posts/on-influence",
  "/2006/05/introducing-bug.php": "/posts/introducing-bug-labs",
  "/2006/05/advertising-to.php": "/posts/advertising-to-job-seekers",
  "/2006/05/what-else-are-y.php": "/posts/what-else-are-you-interested-in",
  "/2006/05/replicating-sil.php": "/posts/replicating-silicon-valley",
  "/2006/06/how-does-indeed-1.php": "/posts/how-does-indeed-make-money",
  "/2006/06/etsy-1.php": "/posts/etsy",
  "/2006/06/why-we-admire-c.php": "/posts/why-we-admire-craigslist",
  "/2006/06/oddcast.php": "/posts/oddcast",
  "/2006/06/union-square-se-1.php": "/posts/union-square-sessions-2-public-policy-and-innovation",
  "/2006/06/sessions.php": "/posts/sessions",
  "/2006/07/a-bittersweet-m.php": "/posts/a-bittersweet-moment",
  "/2006/07/through-the-loo-1.php": "/posts/through-the-looking-glass-into-the-net-neutrality-debate",
  "/2006/07/sessions-patent.php": "/posts/do-patents-encourage-or-stifle-innovation",
  "/2010/01/we-need-an-independent-invention-defense-to-minimize-the-damage-of-aggressive-patent-trolls.php": "/posts/we-need-an-independent-invention-defense-to-minimize-the-damage-of-aggressive-patent-trolls",
  "/2006/07/looking-for-the.php": "/posts/looking-for-the-right-person",
  "/2006/08/our-focus.php": "/posts/our-focus",
  "/2006/08/potential-to-ch-1.php": "/posts/potential-to-change-the-structure-of-markets",
  "/2006/08/information-tec.php": "/posts/information-technology-leverage",
  "/2006/08/defensibility.php": "/posts/defensibility",
  "/2006/08/scalability.php": "/posts/scalability",
  "/2006/08/business-develo.php": "/posts/business-development-20",
  "/2006/08/welcome-andrew-1.php": "/posts/welcome-andrew-parker",
  "/2006/09/other-things-we.php": "/posts/other-things-we-look-for",
  "/2006/09/history-doesnt-1.php": "/posts/history-doesnt-repeat-itself-but-it-does-rhyme",
  "/2006/09/early-stage-inv.php": "/posts/early-stage-investing",
  "/2006/09/traction.php": "/posts/traction",
  "/2006/10/lead-investor.php": "/posts/lead-investor",
  "/2006/10/deal-size-1.php": "/posts/deal-size",
  "/2006/11/customer-servic.php": "/posts/customer-service-is-the-new-marketing",
  "/2006/11/geography-1.php": "/posts/geography",
  "/2007/01/founders-and-ma.php": "/posts/founders-and-management",
  "/2007/01/why-we-dont-inv.php": "/posts/why-we-dont-invest-in-competitive-businesses",
  "/2007/01/whats-next.php": "/posts/whats-next",
  "/2007/01/siaa-preview-ke-1.php": "/posts/siaa-preview-keynote",
  "/2007/02/adaptiveblue.php": "/posts/adaptiveblue",
  "/2007/02/outsidein.php": "/posts/outsidein",
  "/2007/04/targetspot-1.php": "/posts/targetspot",
  "/2007/04/reserves.php": "/posts/reserves",
  "/2007/04/cash-flow-forec-1.php": "/posts/cash-flow-forecasting-isnt-what-it-used-to-be",
  "/2007/05/job-board.php": "/posts/job-board",
  "/2007/05/who-do-you-trus.php": "/posts/who-do-you-trust-to-edit-your-news",
  "/2007/05/dick-costolo-on.php": "/posts/dick-costolo-on-wallstrip",
  "/2007/05/feedburner-is-a.php": "/posts/feedburner-is-acquired-by-google",
  "/2007/06/wesabe-is-more.php": "/posts/wesabe-is-more-than-a-personal-financial-service",
  "/2007/06/introducing-alb.php": "/posts/introducing-albert-wenger",
  "/2007/07/clickable.php": "/posts/clickable",
  "/2007/07/twitter.php": "/posts/twitter",
  "/2007/07/aoltime-warner-1.php": "/posts/aoltime-warner-buys-tacoda",
  "/2007/08/hiring-a-vp-of.php": "/posts/hiring-a-vp-of-engineering-or-cto-for-non-techie-first-time-founders",
  "/2007/09/what-i-want-fro-1.php": "/posts/what-i-want-from-bug-labs",
  "/2007/09/post-2.php": "/posts/there-are-no-open-web-services",
  "/2007/09/i-want-a-new-pl.php": "/posts/i-want-a-new-platform",
  "/2007/09/union-square-se-2.php": "/posts/union-square-sessions-3-hacking-philanthropy",
  "/2007/10/hacking-philant.php": "/posts/hacking-philanthropy-the-transcript",
  "/2010/02/twilio.php": "/posts/twilio",
  "/2007/10/markets-and-phi.php": "/posts/markets-and-philanthropy",
  "/2007/10/tumblr.php": "/posts/tumblr",
  "/2007/11/why-past-perfor.php": "/posts/why-past-performance-is-a-good-predictor-of-future-returns-in-the-venture-capital-asset-class",
  "/2007/11/failure-rates-i.php": "/posts/failure-rates-in-early-stage-venture-deals",
  "/2007/11/why-early-stage.php": "/posts/why-early-stage-venture-investments-fail",
  "/2008/01/zynga-game-netw.php": "/posts/zynga-game-network",
  "/2007/12/googles-data-as.php": "/posts/googles-data-asset",
  "/2008/01/etsys-new-finan.php": "/posts/etsys-new-financing-and-what-they-are-going-to-do-with-it",
  "/2008/02/were-hiring.php": "/posts/were-hiring",
  "/2008/03/new-fund-same-f.php": "/posts/new-fund-same-focus",
  "/2008/03/targetspot-rais.php": "/posts/targetspot-raises-series-b-round",
  "/2008/03/disqus.php": "/posts/disqus",
  "/2008/03/structural-chan.php": "/posts/structural-change-and-marketplaces",
  "/2008/04/covestor.php": "/posts/covestor",
  "/2008/04/i-may-have-a-ne.php": "/posts/i-may-have-a-new-platform",
  "/2008/04/this-is-nuts.php": "/posts/this-is-nuts",
  "/2008/04/ab-meta.php": "/posts/ab-meta",
  "/2008/04/wesabe-steps-ou.php": "/posts/wesabe-steps-out",
  "/2008/05/outsidein-steps.php": "/posts/outsidein-steps-it-up",
  "/2008/05/losing-jason.php": "/posts/losing-jason",
  "/2008/05/pinch-media-inv.php": "/posts/pinch-media-investing-on-a-new-platform",
  "/2008/06/the-spooky-econ.php": "/posts/the-weird-economics-of-information",
  "/2008/06/and-then-there-1.php": "/posts/and-then-there-were-five",
  "/2008/06/call-for-topics.php": "/posts/call-for-topics",
  "/2008/06/internet-for-ev.php": "/posts/internet-for-everyone",
  "/2008/06/twitter-raises.php": "/posts/twitter-raises-a-second-round-of-funding",
  "/2008/07/twitter-acquire.php": "/posts/twitter-acquires-summize",
  "/2008/07/10gen.php": "/posts/10gen",
  "/2008/07/meetup-the-orig.php": "/posts/meetup-the-original-web-meets-world-company",
  "/2008/07/zynga-announces.php": "/posts/zynga-announces-new-investment-from-kleiner-perkins-and-ivp",
  "/2008/09/zemanta-1.php": "/posts/zemanta",
  "/2008/09/power-to-the-pe-1.php": "/posts/power-to-the-people",
  "/2008/09/why-the-flow-of.php": "/posts/why-the-flow-of-innovation-has-reversed",
  "/2008/10/return-path.php": "/posts/return-path",
  "/2008/11/boxee.php": "/posts/boxee",
  "/2008/12/amee.php": "/posts/amee",
  "/2009/01/arguing-from-fi.php": "/posts/arguing-from-first-principles",
  "/2009/02/twitter-fills-t.php": "/posts/twitter-fills-the-tank",
  "/2009/02/pinch-medias-ip.php": "/posts/pinch-medias-iphone-app-store-secrets",
  "/2009/03/dave-morgan-lau.php": "/posts/welcome-back-dave",
  "/2009/03/hacking-educati.php": "/posts/hacking-education",
  "/2009/04/open-spectrum-i.php": "/posts/open-spectrum-is-good-policy",
  "/2009/05/hacking-education.php": "/posts/hacking-education-2",
  "/2009/05/heyzap.php": "/posts/heyzap",
  "/2009/06/bring-the-world.php": "/posts/bring-the-world-to-your-event",
  "/2009/06/the-mobile-chal.php": "/posts/the-mobile-challenge",
  "/2009/08/chris-and-malco.php": "/posts/chris-and-malcolm-are-both-wrong",
  "/2009/09/foursquare.php": "/posts/foursquare",
  "/2009/10/introducing-tra.php": "/posts/introducing-trackedcom",
  "/2012/06/duolingo.php": "/posts/duolingo",
  "/2009/08/our-focus-intro.php": "/posts/our-focus-intro",
  "/2010/04/hiring-update.php": "/posts/hiring-update",
  "/2010/02/software-patents-are-the-problem-not-the-answer.php": "/posts/software-patents-are-the-problem-not-the-answer",
  "/2010/03/communicator-done-replicator-next-the-future-of-making-stuff.php": "/posts/communicator-done-replicator-next-the-future-of-making-stuff",
  "/2010/03/bidding-goodbye-to-andrew.php": "/posts/bidding-goodbye-to-andrew",
  "/2010/04/usv-is-hiring.php": "/posts/we-are-hiring",
  "/2010/04/hiring-update-2.php": "/posts/hiring-update-2",
  "/2010/04/hiring-update-3.php": "/posts/hiring-update-3",
  "/2010/05/stackoverflow.php": "/posts/stack-overflow",
  "/2010/05/hiring-update-4.php": "/posts/hiring-update-4",
  "/2010/06/final-hiring-update.php": "/posts/final-hiring-update",
  "/2010/06/a-new-analyst-at-usv.php": "/posts/a-new-member-of-the-usv-team",
  "/2010/06/web-services-as-governments.php": "/posts/web-services-as-governments",
  "/2010/06/work-market.php": "/posts/work-market",
  "/2013/01/hi-im-brittany-laughlin-im.php": "/posts/joining-union-square-ventures",
  "/2010/06/getting-started.php": "/posts/getting-started",
  "/2010/07/policies-to-encourage-startup-innovation.php": "/posts/policies-to-encourage-startup-innovation",
  "/2010/08/a-threat-to-startups.php": "/posts/a-threat-to-startups",
  "/2010/08/internet-architecture-and-innovation.php": "/posts/internet-architecture-and-innovation",
  "/2010/09/shapeways.php": "/posts/shapeways",
  "/2010/11/tasty-labs.php": "/posts/tasty-labs",
  "/2010/12/10gen-fills-the-tank.php": "/posts/10gen-fills-the-tank",
  "/2010/12/edmodo.php": "/posts/edmodo",
  "/2010/12/an-applications-agnostic-approach.php": "/posts/internet-access-should-be-application-agnostic",
  "/2013/05/circle-up.php": "/posts/circleup",
  "/2011/01/soundcloud.php": "/posts/soundcloud",
  "/2011/01/the-opportunity-fund.php": "/posts/the-opportunity-fund",
  "/2011/03/kik.php": "/posts/kik",
  "/2011/03/innovation-in-education.php": "/posts/innovation-in-education",
  "/2011/03/stack-overflow-becomes-stack-exchange.php": "/posts/stack-overflow-becomes-stack-exchange",
  "/2011/03/kickstarter.php": "/posts/kickstarter",
  "/2011/06/canvas.php": "/posts/canvas",
  "/2011/06/the-protect-ip-act-will-slow-start-up-innovation.php": "/posts/the-protect-ip-act-will-slow-start-up-innovation",
  "/2011/08/lending-club-1.php": "/posts/lending-club",
  "/2011/08/skillshare.php": "/posts/skillshare",
  "/2011/09/jig---when-you-need-a-little-help.php": "/posts/jig-when-you-need-a-little-help",
  "/2011/09/wattpad.php": "/posts/wattpad",
  "/2012/06/wattpads-continued-re-imagining-of-the-book.php": "/posts/wattpads-continued-re-imagining-of-the-book",
  "/2011/09/turntable.php": "/posts/turntable",
  "/2011/09/were-hiring-1.php": "/posts/were-hiring-2",
  "/2011/10/analyst-hiring-update.php": "/posts/analyst-hiring-update",
  "/2011/10/duck-duck-go.php": "/posts/duck-duck-go",
  "/2011/10/my-back-pages.php": "/posts/my-back-pages",
  "/2011/10/codecademy.php": "/posts/codecademy",
  "/2011/10/analyst-hiring-update-2.php": "/posts/analyst-hiring-update-2",
  "/2011/11/help-protect-internet-innovation.php": "/posts/help-protect-internet-innovation",
  "/2011/11/what-comes-next.php": "/posts/what-comes-next",
  "/2012/02/dwolla.php": "/posts/dwolla",
  "/2012/03/the-freedom-to-innovate.php": "/posts/the-freedom-to-innovate",
  "/2012/04/funding-circle.php": "/posts/funding-circle",
  "/2012/04/the-twitter-patent-hack.php": "/posts/the-twitter-patent-hack",
  "/2012/04/hacking-society.php": "/posts/hacking-society",
  "/2012/05/b-corporation.php": "/posts/b-corporation",
  "/2012/05/behance.php": "/posts/behance",
  "/2012/05/investment-thesis-usv.php": "/posts/investment-thesis-usv",
  "/2012/06/internet-presence-usv.php": "/posts/the-next-stage-of-usvcom",
  "/2012/06/and-then-there-were-nine.php": "/posts/and-then-there-were-nine",
  "/2012/06/hello-world-1.php": "/posts/hello-world-2",
  "/2012/06/joining-usv.php": "/posts/joining-usv",
  "/2012/07/brewster.php": "/posts/brewster",
  "/2012/08/networks-and-the-enterprise.php": "/posts/networks-and-the-enterprise",
  "/2012/09/pollenware.php": "/posts/pollenware",
  "/2012/10/researching-online-education.php": "/posts/researching-online-education",
  "/2012/10/looking-for-design-talent.php": "/posts/looking-for-design-talent",
  "/2012/11/visualizing-our-investments.php": "/posts/visualizing-our-investments",
  "/2012/12/behance-joins-adobe-to-scale-creative-network.php": "/posts/behance-joins-adobe-to-scale-creative-network",
  "/2013/02/hailo.php": "/posts/hailo",
  "/2013/03/sift-science.php": "/posts/sift-science",
  "/2013/04/kitchensurfing.php": "/posts/kitchensurfing",
  "/2013/04/foursquare-checks-in.php": "/posts/foursquare-checks-in",
  "/2013/04/shapeways-restocks.php": "/posts/shapeways-restocks",
  "/2013/04/science-exchange.php": "/posts/science-exchange",
  "/2013/05/coinbase.php": "/posts/coinbase",
  "/2013/05/the-patent-quality-improvement-act.php": "/posts/the-patent-quality-improvement-act",
  "/2013/05/yahoo-acquires-tumblr.php": "/posts/yahoo-acquires-tumblr",
  "/2013/06/auxmoney-1.php": "/posts/auxmoney",
  "/2013/06/firebase.php": "/posts/firebase",
  "/2013/07/sigfig.php": "/posts/sigfig",
  "/2013/07/transparency-in-government-surveillance.php": "/posts/transparency-in-government-surveillance",
  "/2013/10/splice.php": "/posts/splice",
  "/2013/08/vhx.php": "/posts/vhx"
}

users = [
  {'id_str':'14202841', 'auth_type':'staff', 'username':'_zachary', 'fullname':'Zach Cimafonte', 'screen_name':'_zachary', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/378800000265819635/0dd348de38d14502ee97d418dacab8ca_normal.jpeg', 'profile_image_url':'http://pbs.twimg.com/profile_images/378800000265819635/0dd348de38d14502ee97d418dacab8ca_normal.jpeg', 'is_blacklisted': False},
  {'id_str':'3021344974', 'auth_type':'staff', 'username':'alexandermpease', 'fullname':'Alexander Pease', 'screen_name':'alexandermpease', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/2425968860/zg9wdsxlfgecxog9lkwz_normal.png', 'profile_image_url':'http://pbs.twimg.com/profile_images/2425968860/zg9wdsxlfgecxog9lkwz_normal.png', 'is_blacklisted': False},
  {'id_str':'18500786', 'auth_type':'staff', 'username':'bwats', 'fullname':'Brian Watson', 'screen_name':'bwats', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/378800000426206820/2f6d04c6b302bf60423190f62b4005ce_normal.jpeg', 'profile_image_url':'http://pbs.twimg.com/profile_images/378800000426206820/2f6d04c6b302bf60423190f62b4005ce_normal.jpeg', 'is_blacklisted': False},
  {'id_str':'1374411', 'auth_type':'staff', 'username':'aweissman', 'fullname':'Andrew Weissman', 'screen_name':'aweissman', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/344513261581924513/b3735cda4529be5530c9d29b6f8e148e_normal.jpeg', 'profile_image_url':'http://pbs.twimg.com/profile_images/344513261581924513/b3735cda4529be5530c9d29b6f8e148e_normal.jpeg', 'is_blacklisted': False},
  {'id_str':'1000591', 'auth_type':'staff', 'username':'fredwilson', 'fullname':'Fred Wilson', 'screen_name':'fredwilson', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/3580641456/82c873940343750638b7caa04b4652fe_normal.jpeg', 'profile_image_url':'http://pbs.twimg.com/profile_images/3580641456/82c873940343750638b7caa04b4652fe_normal.jpeg', 'is_blacklisted': False},
  {'id_str':'7015112', 'auth_type':'staff', 'username':'albertwenger', 'fullname':'Albert Wenger', 'screen_name':'albertwenger', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/1773890030/aew_artistic_normal.gif', 'profile_image_url':'http://pbs.twimg.com/profile_images/1773890030/aew_artistic_normal.gif', 'is_blacklisted': False},
  {'id_str':'7410742', 'auth_type':'staff', 'username':'bradusv', 'fullname':'Brad Burnham', 'screen_name':'bradusv', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/52435733/bio_brad_normal.jpg', 'profile_image_url':'http://pbs.twimg.com/profile_images/52435733/bio_brad_normal.jpg', 'is_blacklisted': False},
  {'id_str':'14375609', 'auth_type':'staff', 'username':'nickgrossman', 'fullname':'Nick Grossman', 'screen_name':'nickgrossman', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/3608605926/71036b2e9d4deff52fdacd8196c40ce5_normal.png', 'profile_image_url':'http://pbs.twimg.com/profile_images/3608605926/71036b2e9d4deff52fdacd8196c40ce5_normal.png', 'is_blacklisted': False},
  {'id_str':'45452822', 'auth_type':'staff', 'username':'br_ttany', 'fullname':'Brittany Laughlin', 'screen_name':'br_ttany', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/1217456552/theoffice_normal.JPG', 'profile_image_url':'http://pbs.twimg.com/profile_images/1217456552/theoffice_normal.JPG', 'is_blacklisted': False},
  {'id_str':'314817239', 'auth_type':'staff', 'username':'johnbuttrick', 'fullname':'John Buttrick', 'screen_name':'johnbuttrick', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/378800000598260826/94bdf40ab10196dea98aff13b7d30565_normal.jpeg', 'profile_image_url':'http://pbs.twimg.com/profile_images/378800000598260826/94bdf40ab10196dea98aff13b7d30565_normal.jpeg', 'is_blacklisted': False},
  {'id_str':'29294520', 'auth_type':'staff', 'username':'christinacaci', 'fullname':'Christina Cacioppo', 'screen_name':'christinacaci', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/1043543563/temp_normal.jpg', 'profile_image_url':'http://pbs.twimg.com/profile_images/1043543563/temp_normal.jpg', 'is_blacklisted': False},
  {'id_str':'29058287', 'auth_type':'staff', 'username':'garychou', 'fullname':'Gary Chou', 'screen_name':'garychou', 'profile_image_url_https':'https://pbs.twimg.com/profile_images/3292748896/a94514170806ebf29c2f481023217967_normal.jpeg', 'profile_image_url':'http://pbs.twimg.com/profile_images/3292748896/a94514170806ebf29c2f481023217967_normal.jpeg', 'is_blacklisted': False}
]

for key, val in old_posts.iteritems():
  api_link = 'http://www.usv.com%s' % val
  r = requests.get(
    api_link,
    verify=False
  )
  html = r.text
  html = re.sub(r'\n', ' ', html)

  post = {
    'date_created':datetime.utcnow(),
    'title':'',
    'slugs':[],
    'slug':'',
    'user':{},
    'tags':[],
    'votes':0,
    'voted_users':[],
    'deleted':False,
    'date_deleted':'',
    'featured':True,
    'date_featured':'',
    'url':'',
    'normalized_url':'',
    'hackpad_url':'',
    'has_hackpad':False,
    'body_raw':'',
    'body_html':'',
    'body_truncated':'',
    'body_text':'',
    'disqus_shortname':'usvbeta2',
    'muted':False,
    'comment_count':0,
    'disqus_thread_id_str':'',
    'sort_score':0.0,
    'downvotes':0,
    'subscribed':[]
  }

  m = re.search(r'http://www.twitter.com/([^"]+)"', html)
  if m:
    username = m.group(1).strip()
    for user in users:
      if user['screen_name'] == username:
        post['user'] = user

  #m = re.search(r'<span class="post-date">([^<]+)<', html)
  #if m:
  #  post['date_created'] = m.group(1).strip()

  m = re.search(r'(\d+) vote', html)
  if m:
    post['votes'] = int(m.group(1).strip())

  m = re.search(r'<title>([^|]+)', html)
  if m:
    post['title'] = m.group(1).strip()

  post['slug'] = slugify.slugify(post['title'])
  post['slugs'] = [post['slug']]

  start = html.find('<div class="post-body">') + 23
  stop = html.find('</div><!--end of post-body-->')
  post['body_raw'] = html[start:stop].strip()
  post['body_html'] = sanitize.html_sanitize(post['body_raw'], media=False)
  post['body_text'] = sanitize.html_to_text(post['body_html'])
  post['body_truncated'] = sanitize.truncate(post['body_text'], 500)

  start = html.find('<div class="col-xs-6 tags">') + 27
  stop = html.find('</div>', start)
  raw_tags = html[start:stop].strip().split(', ')
  for t in raw_tags:
    m = re.search(r'#([^<]+)', t.replace('<span class="post-tags">','').replace('</span>','').strip())
    if m:
      post['tags'].append(m.group(1).strip())

  if 'user' in post.keys() and 'username' in post['user'].keys():
    db.post.update({'slug':post['slug']}, post, upsert=True)
    print "added %s" % post['slug']

########NEW FILE########
__FILENAME__ = repop_domains_for_posts
# repopulate the domain value for each post

import bitly_api
import requests
import simplejson as json
import urlparse
from mongo import db

def expand_bitly_url(hash_val):
  access_token = ''
  c = bitly_api.Connection(access_token=access_token)
  return c.expand(hash_val)['long_url']

def expand_google_url(url):
  r = requests.get(
    'https://www.googleapis.com/urlshortener/v1/url?shortUrl=%s' % url,
    verify=False
  )
  return json.loads(r.text)['longUrl']

# get all the existing posts
posts = list(db.post.find())
for post in posts:
  long_url = post['url']
  if long_url.find('goo.gl') > -1:
    long_url = expand_google_url(post['url'])
  if long_url.find('bit.ly') > -1 or long_url.find('bitly.com') > -1:
    long_url = expand_bitly_url(post['url'].replace('http://bitly.com','').replace('http://bit.ly',''))
  domain = urlparse(long_url).netloc
  post['domain'] = domain
  db.post.update({'_id':post['_id']}, {'$set':{'domain':domain}})
  print "updated %s" % post['slug']


########NEW FILE########
__FILENAME__ = sanitize
import bleach
from bs4 import BeautifulSoup

allowed_tags = ['a', 'b', 'p', 'i', 'blockquote', 'span', 'ul', 'li', 'ol',
  'strong', 'pre', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'br', 'span']
allowed_attrs = {
  'a': ['href', 'rel'],
}

allowed_tags_media = list(allowed_tags)
allowed_tags_media += ['iframe', 'object', 'embed', 'img']
allowed_attrs_media = dict(allowed_attrs)
allowed_attrs_media.update({
  'iframe': ['src', 'frameborder', 'width', 'height'],
  'img': ['src', 'alt', 'width', 'height'],
  'embed': ['src', 'type', 'width', 'height'],
  'object': ['data', 'type', 'width', 'height'],
})

allowed_styles = ['text-decoration']

# This is exposed to templates as a template method.
# See ui/template_methods.py
def tinymce_valid_elements(media=True):
  if media:
    tags = allowed_tags_media
    attrs = allowed_attrs_media
  else:
    tags = allowed_tags
    attrs = allowed_attrs
  valid_list = []
  for tag in tags:
    elem_attrs = attrs.get(tag)
    if elem_attrs:
      tag += '[%s]' % '|'.join(elem_attrs)
    valid_list.append(tag)
  return ','.join(valid_list)

def linkify(input):
  return bleach.linkify(input)

def html_sanitize(input, media=True):
  if media:
    tags = allowed_tags_media
    attrs = allowed_attrs_media
  else:
    tags = allowed_tags
    attrs = allowed_attrs
  text = bleach.clean(input, tags=tags, attributes=attrs, styles=allowed_styles)
  return text

def html_sanitize_preview(input):
  return bleach.clean(input, tags=[], attributes=[], styles=[], strip=True)

def html_to_text(text):
  soup = BeautifulSoup(text)
  for br in soup.find_all('br'):
    br.string = ' '
  text = soup.get_text()
  return text

def truncate(text, length, ellipsis=True):
  truncated = text[:length]
  if ellipsis and len(text) > length:
    truncated += '...'
  return truncated

########NEW FILE########
__FILENAME__ = sanitize_user_data
import sys
try:
	sys.path.insert(0, '/Users/nick/dev/theconversation')
except:
	pass

from lib import userdb

users = userdb.get_all()

for user in users:
	user['email_address'] = ""
	user['disqus'] = {}
	user['access_token'] = {}
	userdb.save_user(user)
	print "saved user %s" % user['user']['username']
########NEW FILE########
__FILENAME__ = sort_posts
# Run by Heroku Scheduler every 10min
from datetime import datetime, timedelta
try:
	import sys
	sys.path.insert(0, '/Users/nick/dev/theconversation')
except:
	print "could not import -- must be running on heroku"

from lib import postsdb

postsdb.sort_posts(datetime.today())
########NEW FILE########
__FILENAME__ = stats
import sys
sys.path.insert(0, '/Users/nick/dev/conversation')
import settings
import logging
from datetime import datetime, timedelta
import optparse
from lib import statsdb, postsdb

parser = optparse.OptionParser()
parser.add_option('-s', '--start',
	action="store", dest="start_date",
	help="start date", default="today")
options, args = parser.parse_args()

if options.start_date == "today":
	options.start_date = datetime.today()

start_date_str = options.start_date
start_date = datetime.strptime(start_date_str, "%m-%d-%Y")
end_date = start_date + timedelta(days=7)
count = postsdb.get_post_count_for_range(start_date, end_date)
unique_posters = postsdb.get_unique_posters(start_date, end_date)
single_post_count = 0
for user in unique_posters:
	if user['count'] == 1:
		single_post_count += 1


print "Week starting %s" % start_date_str
print "+++ %s posts" % count 
print "+++ %s unique posters" % len(unique_posters)
print "+++ %s one-time posters" % single_post_count

########NEW FILE########
__FILENAME__ = update_disqus_thread_data
# Run by Heroku scheduler every night
# If running locally, uncomment below imports
import sys
sys.path.insert(0, '/Users/nick/dev/conversation')
import settings

from lib import postsdb
from lib import disqus
from mongo import db

#users = db.user_info.find({"lastname" : {"$exists" : true, "$ne" : ""}})
threads = disqus.get_all_threads()

for thread in threads['response']:
	print(thread)
	#for key in thread['response'].keys():
	#	logging.info(key + ": " + thread[key])
########NEW FILE########
__FILENAME__ = update_users
# Run by Heroku scheduler every night
# If running locally, uncomment below imports
import sys
#sys.path.insert(0, '/<path-to-your-codebase>')
import settings

from lib import userdb

userdb.update_twitter_profile_images() 

########NEW FILE########
__FILENAME__ = settings
import os
import tornado.options

# Environmenal settings for heroku#
# If you are developing for heroku and want to set your settings as environmental vars
# create settings_local_environ.py in the root folder and use:
# os.environ['KEY'] = 'value'
# to simulate using heroku config vars
# this is better than using a .env file and foreman
# since it still allows you to see logging.info() output
try:
  import settings_local_environ
except:
  pass

tornado.options.define("environment", default="dev", help="environment")
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__)))

options = {
  'dev' : {
    'mongo_database' : {'host' : os.environ.get('MONGODB_URL'), 'port' : 27017, 'db' : os.environ.get('DB_NAME')},
    'base_url' : os.environ.get('BASE_URL'),
  },
  'test' : {
    'mongo_database' : {'host' : os.environ.get('MONGODB_URL'), 'port' : 27017, 'db' : os.environ.get('DB_NAME')},
    'base_url' : os.environ.get('BASE_URL'),
  },
  'prod' : {
    'mongo_database' : {'host' : os.environ.get('MONGODB_URL'), 'port' : 27017, 'db' : os.environ.get('DB_NAME')},
    'base_url' : os.environ.get('BASE_URL'),
  }
}

default_options = {
  'active_theme': "default",
  'site_title': "The Conversation",
  'site_intro': "This is a website where people talk",
  
  'project_root': os.path.abspath(os.path.join(os.path.dirname(__file__))),

  # twiter details
  'twitter_consumer_key' : '',
  'twitter_consumer_secret' : '',

  # disqus details
  'disqus_public_key': '',
  'disqus_secret_key': '',
  'disqus_short_code': '',

  # sendgrid details
  'sendgrid_user': '',
  'sendgrid_secret': '',

  # hackpad details
  'hackpad_oauth_client_id':'', 
  'hackpad_oauth_secret':'', 
  'hackpad_domain':'',

  # google api key
  'google_api_key': '',

  # bitly access token
  'bitly_access_token': '',

  # other control variables
  'tinymce_valid_elements': '',
  'post_char_limit': 1000,
  'sticky': None,
  'read_only' : False,
  'max_simultaneous_connections' : 10,
  'hot_post_set_count': 200,
  'staff':[ 'nickgrossman'],

  # define the various roles and what capabilities they support
  'staff_capabilities': [
    'send_daily_email',
    'see_admin_link',
    'delete_users',
    'delete_posts',
    'post_rich_media',
    'feature_posts',
    'edit_posts',
    'super_upvote',
    'super_downvote',
    'downvote_posts',
    'manage_disqus',
    'view_post_sort_score'
  ],
  'user_capabilities': [], 
  
  'module_dir': os.path.join(PROJECT_ROOT, 'templates/modules')
}

def get(key):
  # check for an environmental variable (used w Heroku) first
  if os.environ.get('ENVIRONMENT'):
    env = os.environ.get('ENVIRONMENT')
  else:
    env = tornado.options.options.environment

  if env not in options:
    raise Exception("Invalid Environment (%s)" % env)

  if key == 'environment':
    return env

  v = options.get(env).get(key) or os.environ.get(key.upper()) or default_options.get(key)

  if callable(v):
    return v

  if v is not None:
    return v

  return default_options.get(key)


########NEW FILE########
__FILENAME__ = template_modules
import os
import sys
from tornado.web import UIModule
import logging

sys.path.append('../')
import settings

"""
		Iterate through the modules folder, creating UIModules for each module.

		- JavaScript for each module is externally bundled and loaded into the page.
		- The embedded_javascript method of BaseUIModule is called when a module is
		used in a template. It provides additional JavaScript for the page to
		contain. Modules with JavaScript will invoke their externally bundled
		JavaScript by injecting a call to it into the parent template.
"""

class BaseUIModule(UIModule):
		name = ''
		wrap_javascript = False

		def __init__(self, *args, **kwargs):
				super(BaseUIModule, self).__init__(*args, **kwargs)

		def embedded_javascript(self):
				if self.has_javascript:
						return "%s();\n" % self.name

		def render(self, *args, **kwargs):
				relpath = "{name}/main.html".format(name=self.name)
				filepath = os.path.join(settings.get('module_dir'), relpath)
				return self.render_string(filepath, *args, **kwargs)

# Create modules using the folder name as the module name
def template_modules():
		modules = {}
		for filename in os.listdir(settings.get('module_dir')):
				path = os.path.join(settings.get('module_dir'), filename)
				if not os.path.isdir(path):
						continue

				# Open JS file, check for contents
				js_file = os.path.join(path, "main.js")
				has_javascript = False
				try:
						f = open(js_file, 'r')
						if f.read().strip():
								has_javascript = True
						f.close()
				except IOError:
						pass

				# Create a UIModule object for this module
				modules[filename] = type("UI_%s" % filename, (BaseUIModule,), {
						'name': filename,
						'has_javascript': has_javascript
				})
		return modules


########NEW FILE########
__FILENAME__ = tests
from splinter import Browser

browser = Browser('phantomjs')

browser.visit('http://dev.usv.com')
if browser.status_code == 200:
	print("success")
########NEW FILE########
__FILENAME__ = tornado_server
import os
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.options
import tornado.web

import logging

# settings is required/used to set our environment
import settings 

import app.user
import app.admin
import app.api
import app.basic
import app.disqus
import app.general
import app.posts
import app.search
import app.stats
import app.twitter
import app.error
import templates

class Application(tornado.web.Application):
  def __init__(self):

    debug = (settings.get('environment') == "dev")

    app_settings = {
      "cookie_secret" : "change_me",
      "login_url": "/auth/twitter",
      "debug": debug,
      "static_path" : os.path.join(os.path.dirname(__file__), "static"),
      "template_path" : os.path.join(os.path.dirname(__file__), "templates"),
    }

    handlers = [    
      # account stuff
      (r"/auth/email/?", app.user.EmailSettings),
      (r"/auth/logout/?", app.user.LogOut),
      (r"/user/(?P<username>[A-z-+0-9]+)/settings/?", app.user.UserSettings),
      (r"/user/settings?", app.user.UserSettings),
      (r"/user/(?P<screen_name>[A-z-+0-9]+)", app.user.Profile),
      (r"/user/(?P<screen_name>[A-z-+0-9]+)/(?P<section>[A-z]+)", app.user.Profile),

      # admin stuff
      (r"/admin", app.admin.AdminHome),
      (r"/admin/delete_user", app.admin.DeleteUser),
      (r"/admin/deleted_posts", app.admin.DeletedPosts),
      (r"/admin/sort_posts", app.admin.ReCalculateScores),
      (r"/admin/stats", app.admin.AdminStats),
      (r"/admin/disqus", app.admin.ManageDisqus),
      (r"/admin/daily_email", app.admin.DailyEmail),
      (r"/admin/daily_email/history", app.admin.DailyEmailHistory),
      (r"/generate_hackpad/?", app.admin.GenerateNewHackpad),
      (r"/list_hackpads", app.admin.ListAllHackpad),
      (r"/posts/([^\/]+)/mute", app.admin.Mute),
      (r"/users/(?P<username>[A-z-+0-9]+)/ban", app.admin.BanUser),
      (r"/users/(?P<username>[A-z-+0-9]+)/unban", app.admin.UnBanUser),
      
      # api stuff
      (r"/api/incr_comment_count", app.api.DisqusCallback),
      (r"/api/user_status", app.api.GetUserStatus),
      (r"/api/voted_users/(.+)", app.api.GetVotedUsers),
      (r"/api/check_for_url", app.api.CheckForUrl),
      (r"/api/posts/get_day", app.api.PostsGetDay),

      # disqus stuff
      (r"/auth/disqus", app.disqus.Auth),
      (r"/remove/disqus", app.disqus.Remove),
      (r"/disqus", app.disqus.Disqus),

      # search stuff
      (r"/search", app.search.Search),
      (r"/tagged/(.+)", app.search.ViewByTag),
      (r"/tags", app.search.ViewByTag),

      # stats stuff
      (r"/stats/shares/weekly", app.stats.WeeklyShareStats),

      # twitter stuff
      (r"/auth/twitter/?", app.twitter.Auth),
      (r"/twitter", app.twitter.Twitter),

      # post stuff
      (r"/featured.*$", app.posts.FeaturedPosts),
      (r"/feed/(?P<feed_type>[A-z-+0-9]+)$", app.posts.Feed),
      (r"/feed$", app.posts.Feed),
      (r"/posts/new$", app.posts.NewPost),
      (r"/bookmarklet$", app.posts.NewPost),
      (r"/(?P<sort_by>hot)$", app.posts.ListPosts),
      (r"/(?P<sort_by>new)$", app.posts.ListPostsNew),
      (r"/(?P<sort_by>sad)$", app.posts.ListPosts),
      (r"/(?P<sort_by>[^\/]+)/page/(?P<page>[0-9]+)$", app.posts.ListPosts),
      (r"/posts/([^\/]+)/upvote", app.posts.Bump),
      (r"/posts/([^\/]+)/bump", app.posts.Bump),
      (r"/posts/([^\/]+)/unbump", app.posts.UnBump),
      (r"/posts/([^\/]+)/superupvote", app.posts.SuperUpVote),
      (r"/posts/([^\/]+)/superdownvote", app.posts.SuperDownVote),
      (r"/posts/([^\/]+)/edit", app.posts.EditPost),
      (r"/day/(?P<day>[A-z-+0-9]+)$", app.posts.ListPosts),
      (r"/posts/(.+)", app.posts.ViewPost),
      (r"/posts$", app.posts.ListPosts),
      (r"/widget/demo.*?", app.posts.WidgetDemo),
      (r"/widget.*?", app.posts.Widget),
      (r'/$', app.posts.ListPosts),
    ]
    
    app_settings.update({
      'ui_modules': templates.template_modules()
    })

    tornado.web.Application.__init__(self, handlers, **app_settings)

def main():
  tornado.options.define("port", default=8001, help="Listen on port", type=int)
  tornado.options.parse_command_line()
  logging.info("starting tornado_server on 0.0.0.0:%d" % tornado.options.options.port)
  http_server = tornado.httpserver.HTTPServer(request_callback=Application(), xheaders=True)
  http_server.listen(tornado.options.options.port)
  tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
  main()

########NEW FILE########
