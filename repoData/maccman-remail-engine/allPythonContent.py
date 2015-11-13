__FILENAME__ = inbound
import logging, email, yaml
from django.utils import simplejson as json
from google.appengine.ext import webapp, deferred
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.api.urlfetch import fetch
from google.appengine.api.urlfetch import Error as FetchError

settings = yaml.load(open('settings.yaml'))

def callback(raw):
  result = {'email': {'raw': raw}}
  
  response = fetch(settings['outbound_url'], 
              payload=json.dumps(result), 
              method="POST", 
              headers={
                'Authorization': settings['api_key'],
                'Content-Type': 'application/json'
              },
              deadline=10
             )
  logging.info(response.status_code)
  if response.status_code != 200:
    raise FetchError()

class InboundHandler(InboundMailHandler):
    def receive(self, message):
      logging.info("Received a message from: " + message.sender)
      deferred.defer(callback, message.original.as_string(True), _queue='inbound')
########NEW FILE########
__FILENAME__ = main
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from outbound import OutboundHandler
from inbound import InboundHandler

def main():
  application = webapp.WSGIApplication([
                                         ('/emails(\.json)*', OutboundHandler), 
                                         InboundHandler.mapping()
                                       ],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()

########NEW FILE########
__FILENAME__ = outbound
import logging, yaml
from django.utils import simplejson as json
from google.appengine.ext import webapp, deferred
from google.appengine.api import mail

settings = yaml.load(open('settings.yaml'))

def safe_dict(d): 
  """
    Recursively clone json structure with UTF-8 dictionary keys
    http://bugs.python.org/issue2646
  """ 
  if isinstance(d, dict): 
    return dict([(k.encode('utf-8'), safe_dict(v)) for k,v in d.iteritems()]) 
  elif isinstance(d, list): 
    return [safe_dict(x) for x in d] 
  else: 
    return d
    
def email(body):
  email = json.loads(body)
  mail.EmailMessage(**safe_dict(email)).send()

class OutboundHandler(webapp.RequestHandler):

  def post(self, *args):
    api_key = self.request.headers.get('Authorization')
    
    if api_key != settings['api_key']:
      logging.error("Invalid API key: " + str(api_key))
      self.error(401)
      return
    
    deferred.defer(email, self.request.body, _queue='outbound')
########NEW FILE########
