__FILENAME__ = common_dir_search
from burp import IBurpExtender
import jarray
import os

#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules/')
sys.path.insert(0, module_folder)
import webcommon

unique_list_of_urls=[]

class BurpExtender(IBurpExtender):
  def registerExtenderCallbacks(self,callbacks):
    list_of_urls=[]
    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()

    # set our extension name
    callbacks.setExtensionName("Common Directory Search")

    # Get proxy history
    proxyhistory=callbacks.getProxyHistory()

    #Read each request in proxy history
    for request in proxyhistory:
      request_byte_array=request.getRequest()
      requestInfo = self._helpers.analyzeRequest(request_byte_array)
      BurpExtender.fuzz_url(self,callbacks,request_byte_array,requestInfo)

  def fuzz_url(self,callbacks,request_byte_array,requestInfo):
    if requestInfo:
      request_headers=requestInfo.getHeaders()
      t0=request_headers[0].split(' ')
      t1=request_headers[1].split(': ')

      #Extract directories from every single request in proxy history
      directory=webcommon.extract_directory(self,callbacks,t0[1])

      if directory not in unique_list_of_urls:
        unique_list_of_urls.append(directory)
        request_string=self._helpers.bytesToString(request_byte_array)
        #String manipulation with a lot of temp variables t2,t3,t4 etc
        t2=request_string.split('\n')
        t3=t2[0].split(' ')
        t3[1]=directory+'/dummy'
        t4=' '.join(t3)
        t2[0]=t4
        request_string='\n'.join(t2)
        #String manipulation ends. Variable reuse possible.

        #Restore the manipulated string to the byte array so it can be reused.
        request_byte_array=self._helpers.stringToBytes(request_string)

        #Calculate correct offset here and send that request to Intruder to get fuzzed. Remember to configure the right payload set in Intruder
        #before running this extension
        callbacks.sendToIntruder(t1[1],443,1,request_byte_array,[jarray.array([request_string.find('/dummy')+1,request_string.find(' HTTP/1.1')], "i")])

########NEW FILE########
__FILENAME__ = csrf_token_detect
from burp import IBurpExtender
from burp import IHttpListener
from burp import IProxyListener
import re
import sys
import os

#This is where you put the name of the token that is being used in the application you are testing. It searches for __VIEWSTATE by default. The 
#extension will search for this token in every request and tell you which requests do NOT have a token, so you can manually explore.
anticsrf_token_name='securityRequestParameter'

excluded_file_extensions=['.jpg','.gif','.bmp','.png','.css','.js','.htc','.jpeg','.ico','.svg']
urls_in_scope=['blah.test.com']

#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules')
sys.path.insert(0, module_folder)
import webcommon

class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):
  def registerExtenderCallbacks(self,callbacks):
    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()

    # set our extension name
    callbacks.setExtensionName("CSRF Token Detector")

    # register ourselves as an HTTP listener
    callbacks.registerHttpListener(self)

    # register ourselves as a Proxy listener
    callbacks.registerProxyListener(self)

  def processProxyMessage(self,messageIsRequest,message):
    request_url = BurpExtender.detect_csrf_token(self,messageIsRequest,message)
    if request_url:
      print request_url

  def detect_csrf_token(self,messageIsRequest,message):
    #Only process requests as that's where the Token should be
    request_byte_array=message.getMessageInfo().getRequest()
    if messageIsRequest:
      t1=[]
      t2=[]
      flag=0

      requestInfo = self._helpers.analyzeRequest(request_byte_array)

      #Extract hostname from header
      hostname=webcommon.get_host_header_from_request(self,requestInfo)

      #Check if the URL is in scope. This is to eliminate stray traffic.
      if hostname and hostname[1] in urls_in_scope:
        csrf_token_value=self._helpers.getRequestParameter(request_byte_array,anticsrf_token_name)
        request_string=self._helpers.bytesToString(request_byte_array)
        urlpath=request_string.split("\n")
        tmp2=urlpath[0].split(' ')
 
      #If there's no token, check if it's an image, js or css file. In this case, a token isn't needed
        if not csrf_token_value:
          for tmp3 in excluded_file_extensions:
            #Search for file extension. If you want a more complex regex..remember to compile the regex. DO.NOT.FORGET :)
            tmp4=re.search(tmp3,tmp2[-2])
            if tmp4:
              flag=1
 
          #Not to be excluded and the request doesn't contain a token
          if flag != 1:
            return urlpath[0]

########NEW FILE########
__FILENAME__ = csrf_valid_referer_detect
from burp import IBurpExtender
from burp import IHttpListener
from burp import IProxyListener
import os
import re
import sys

excluded_file_extensions=['.jpg','.gif','.bmp','.png','.css','.js','.htc']
urls_in_scope=['testblah.com']

referer_header_name='Referer'
referer_header_value='https://home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules.com/'

#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules/')
sys.path.insert(0, module_folder)
import webcommon

class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):
  def registerExtenderCallbacks(self,callbacks):
    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()

    # set our extension name
    callbacks.setExtensionName("CSRF Valid Referer Detector")

    # register ourselves as an HTTP listener
    callbacks.registerHttpListener(self)

    # register ourselves as a Proxy listener
    callbacks.registerProxyListener(self)

  def processProxyMessage(self,messageIsRequest,message):
    request_url = BurpExtender.detect_valid_referer(self,messageIsRequest,message)

  def detect_valid_referer(self,messageIsRequest,message):
    #Only process requests as that's where the valid Referer should be 
    request_http_service=message.getMessageInfo().getHttpService()
    request_byte_array=message.getMessageInfo().getRequest()
    requestInfo=self._helpers.analyzeRequest(request_http_service, request_byte_array)
    request_url=requestInfo.getUrl()

    if messageIsRequest:
      #Extract hostname from header
      hostname=webcommon.get_host_header_from_request(self,requestInfo)

      #Check if the URL is in scope. This is to eliminate stray traffic.
      if hostname and hostname[1] in urls_in_scope:
        #Extract referer. If it's not a referer from the same site - print it out and let the engineer decide if it is unsafe.
        referer=webcommon.get_referer_header_from_request(self,requestInfo)
        if not referer[1].startswith(referer_header_value):
          print str(request_url)+'\t\t'+str(referer[1])

########NEW FILE########
__FILENAME__ = direct_request
from burp import IBurpExtender
from burp import IHttpListener
from burp import IProxyListener
import re
import sys
import os

session_cookie_names = ['JSESSIONID','PHPSESSID']
urls_in_scope = ['blahtest.com']
remote_listening_port = 443
protocol = 'https'
hostname = []

#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules/')
sys.path.insert(0, module_folder)
import webcommon

class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):
  def registerExtenderCallbacks(self,callbacks):
    # Get a reference to the Burp helpers and the callbacks object. This is needed as you can't pass these as parameters to processProxymessage.
    self._helpers = callbacks.getHelpers()
    self._callbacks = callbacks

    # set our extension name
    callbacks.setExtensionName("Direct Request")

    # register ourselves as an HTTP listener
    callbacks.registerHttpListener(self)

    # register ourselves as a Proxy listener
    callbacks.registerProxyListener(self)

  def processProxyMessage(self,messageIsRequest,message):
    if messageIsRequest:
      request_byte_array = BurpExtender.remove_sessioncookie_from_request(self,messageIsRequest,message)
      BurpExtender.generate_request(self,request_byte_array)

  def remove_sessioncookie_from_request(self,messageIsRequest,message):
    request_byte_array=message.getMessageInfo().getRequest()
    requestInfo = self._helpers.analyzeRequest(request_byte_array)

    #Extract hostname from header
    global hostname
    hostname=webcommon.get_host_header_from_request(self,requestInfo)

    #Check if the URL is in scope. This is to eliminate stray traffic.
    if hostname and hostname[1] in urls_in_scope:
      request_string=self._helpers.bytesToString(request_byte_array)
      #Find and then remove all session cookies
      for cookie in session_cookie_names:
        regex=re.compile(r'(.*)(%s=\w+)(;*?)'%cookie,re.IGNORECASE|re.DOTALL)
        m1=regex.match(request_string)
        if m1:
          request_string=re.sub(m1.group(2),'',request_string)
          #Restore the manipulated string to the byte array so it can be reused.
          request_byte_array = self._helpers.stringToBytes(request_string)

    return request_byte_array

  def generate_request(self,request_byte_array):            
    if request_byte_array:
      http_service = self._helpers.buildHttpService(hostname[1],remote_listening_port,protocol)
      req_resp = self._callbacks.makeHttpRequest(http_service, request_byte_array)
      response_byte_array = req_resp.getResponse()
      response_object=self._helpers.analyzeResponse(response_byte_array)
      response_string = self._helpers.bytesToString(response_byte_array)
      request_object=self._helpers.analyzeRequest(http_service,request_byte_array)

      '''
      Print out the URL requested, the response code and the length of the response. The reason for doing this is so you can
      compare the lengths and see if all the requests are getting redirected to a login page or custom error page.
      '''
      print str(request_object.getUrl())+'\t'+str(response_object.getStatusCode())+'\t'+str(len(response_string))

########NEW FILE########
__FILENAME__ = download_all_js_files
from burp import IBurpExtender
from burp import IHttpListener
from burp import IProxyListener
import os
import re

urls_in_scope=['pagead2.googlesyndication.com']
download_path='/tmp'
#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules/')
sys.path.insert(0, module_folder)
import webcommon

class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):
  def registerExtenderCallbacks(self,callbacks):
    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()

    # set our extension name
    callbacks.setExtensionName("Download JS files")

    # register ourselves as an HTTP listener
    callbacks.registerHttpListener(self)

    # register ourselves as a Proxy listener
    callbacks.registerProxyListener(self)

  def processProxyMessage(self,messageIsRequest,message):
    BurpExtender.download_all_JS_files(self,messageIsRequest,message)

  def download_all_JS_files(self,messageIsRequest,message):
    request_byte_array=message.getMessageInfo().getRequest()
    if messageIsRequest:
      request_http_service=message.getMessageInfo().getHttpService()
      request_byte_array=message.getMessageInfo().getRequest()
      request_object=self._helpers.analyzeRequest(request_http_service, request_byte_array)

      #Extract hostname from header
      hostname=webcommon.get_host_header_from_request(self,request_object)

      #Check if the URL is in scope. This is to eliminate stray traffic.
      if hostname and hostname[1] in urls_in_scope:
        request_url=request_object.getUrl()
        if str(request_url).endswith('.js'):
          print request_url
          os.chdir(download_path)
          os.system("wget "+str(request_url))

########NEW FILE########
__FILENAME__ = http_method_test
from burp import IBurpExtender
import jarray
import os

#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules/')
sys.path.insert(0, module_folder)
import webcommon

protocol='http'
remote_listening_port = 80
unique_list_of_urls=[]
filename='/tmp/abc'
unique_list_of_urls=[]
hostname=''

class BurpExtender(IBurpExtender):
  def registerExtenderCallbacks(self,callbacks):
    global hostname
    list_of_urls=[]
    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()
    self._callbacks = callbacks

    # set our extension name
    callbacks.setExtensionName("HTTP method test")

    # Get proxy history
    proxyhistory=callbacks.getProxyHistory()

    #Read each request in proxy history
    for request in proxyhistory:
      request_byte_array=request.getRequest()
      requestInfo = self._helpers.analyzeRequest(request_byte_array)

      #Extract hostname from header
      hostname=webcommon.get_host_header_from_request(self,requestInfo)

      #Test PUT for each directory in the proxy history
      filepath=BurpExtender.test_put(self,callbacks,request_byte_array,hostname,requestInfo)

      #Get the file that you just PUT
      respcode=BurpExtender.check_file_existence_put(self,filepath)

      if respcode=='200':
        #Test DELETE for the file you uploaded
        BurpExtender.test_delete(self,filepath)

        #Get the file that you just DELETED. It should return a 404 if DELETE is enabled
        BurpExtender.check_file_existence_delete(self,filepath)


  def test_put(self,callbacks,request_byte_array,hostname,requestInfo):
    if requestInfo:
      request_headers=requestInfo.getHeaders()
      t0=request_headers[0].split(' ')
      respcode=request_headers[1].split(': ')

      #Extract directories from every single request in proxy history
      directory=webcommon.extract_directory(self,callbacks,t0[1])

      if directory not in unique_list_of_urls:
        unique_list_of_urls.append(directory)
        cmd="curl --upload-file "+filename+" "+protocol+'://'+hostname[1]+directory+'/'
        os.system(cmd)

      filepath=protocol+'://'+hostname[1]+directory+'/abc'
      return filepath

  def check_file_existence_put(self,filepath):            
    cmd='curl -s -w %{http_code} '+'"'+filepath+'"'+' -o /dev/null > /tmp/respcode'
    os.system(cmd)
    f=open('/tmp/respcode','rU')
    respcode=f.readline()
    f.close()

    if respcode=='200':
      print 'PUT succeeded - '+filepath
    elif respcode=='404':
      print 'PUT failed - '+filepath

    return respcode

  def test_delete(self,filepath):
    cmd='curl -X DELETE '+filepath
    os.system(cmd)

  def check_file_existence_delete(self,filepath):            
    cmd='curl -s -w %{http_code} '+'"'+filepath+'"'+' -o /dev/null > /tmp/respcode'
    os.system(cmd)
    f=open('/tmp/respcode','rU')
    respcode=f.readline()
    f.close()

    if respcode=='200':
      print 'DELETE failed - '+filepath
    elif respcode=='404':
      print 'DELETE succeeded - '+filepath

########NEW FILE########
__FILENAME__ = webcommon
import re

def get_host_header_from_request(self,requestInfo):
  t1 = requestInfo.getHeaders()
  header_name='Host:'

  regex=re.compile('^.*%s.*'%header_name,re.IGNORECASE)
  for i in t1:
    #Search for the Host header
    m1=regex.match(i)
  
    #Extract and store the Host header
    if m1:
      t2=i.split(': ')
  
  return t2

def extract_directory(self,callbacks,url):
  t0=url.split('/')
  if len(t0) > 1:
    t0.pop(-1)
  i=0
  t1=''
  while i<len(t0):
    t1=t1+'/'+t0[i]
    i+=1

  return t1[1:]

def extract_urls(self,callbacks,url):
  t0=url.split('/')
  i=0
  t1=''
  while i<len(t0):
    t1=t1+'/'+t0[i]
    i+=1

  return t1[1:]

def get_referer_header_from_request(self,requestInfo):
  t1 = requestInfo.getHeaders()
  header_name='Referer:'

  regex=re.compile('^.*%s.*'%header_name,re.IGNORECASE)
  for i in t1:
    #Search for the Referer header
    m1=regex.match(i)

    #Extract and store the Referer header
    if m1:
      t2=i.split(': ')
      return t2

def get_setcookie_from_header(self,responseInfo):
  t1 = responseInfo.getHeaders()
  header_name='Set-Cookie:'

  #Search for the Set Cookie header
  regex=re.compile('^.*%s.*'%header_name,re.IGNORECASE)

  for i in t1:
    m1=regex.match(i)
    #Extract and store the Set Cookie header
    if m1:
      t2=i.split(': ')
      return t2

def get_response_code_from_headers(self,responseInfo):
  t1 = responseInfo.getHeaders()
  return t1

def get_location_from_headers(self,responseInfo):
  t1 = responseInfo.getHeaders()
  header_name='Location:'

  #Search for the Location header
  regex=re.compile('^.*%s.*'%header_name,re.IGNORECASE)
  for i in t1:
    m1=regex.match(i)
    #Extract and store the Location header
    if m1:
      t2=i.split(': ')
      return t2

def get_response_body(self,response_byte_array,responseInfo):
  responseBody=response_byte_array[responseInfo.getBodyOffset():]
  return responseBody

def get_banner_from_response(self,responseInfo):
  t1 = responseInfo.getHeaders()
  #header_name='Server:'
  header_name=['Server:','X-AspNet-Version:','X-AspNetMvc-Version:','X-Powered-By:','X-Requested-With:','X-UA-Compatible:','Via:']
 
  for h1 in header_name:
    regex=re.compile('^.*%s.*'%h1,re.IGNORECASE)
    for i in t1:
      #Search for the Server header
      m1=regex.match(i)

      #Extract and store the Server header
      if m1:
        return i

########NEW FILE########
__FILENAME__ = record_set_cookie_headers
from burp import IBurpExtender
from burp import IHttpListener
from burp import IProxyListener
import re
import os
import sys

urls_in_scope=['test.blah.com']
#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules')
sys.path.insert(0, module_folder)
import webcommon

class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):
  def registerExtenderCallbacks(self,callbacks):
    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()

    # set our extension name
    callbacks.setExtensionName("Record Set Cookie Headers")

    # register ourselves as an HTTP listener
    callbacks.registerHttpListener(self)

    # register ourselves as a Proxy listener
    callbacks.registerProxyListener(self)

  def processProxyMessage(self,messageIsRequest,message):
    request_byte_array=message.getMessageInfo().getRequest()
    requestInfo = self._helpers.analyzeRequest(request_byte_array)
    setcookie_header=BurpExtender.record_setcookie_headers(self,messageIsRequest,message)

  def record_setcookie_headers(self,messageIsRequest,message):
    if not messageIsRequest:
      response_byte_array=message.getMessageInfo().getResponse()
      responseInfo = self._helpers.analyzeResponse(response_byte_array)
      setcookie_header=webcommon.get_setcookie_from_header(self,responseInfo)
      if setcookie_header:
        for cookie in setcookie_header:
          print cookie

########NEW FILE########
__FILENAME__ = sslyze_scan
from burp import IBurpExtender
import os
result_dir='/tmp/'
result_file='sslscan_result'

#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules/')
sys.path.insert(0, module_folder)
import webcommon

class BurpExtender(IBurpExtender):
  def registerExtenderCallbacks(self,callbacks):
    global hostname

    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()
    self._callbacks = callbacks

    # set our extension name
    callbacks.setExtensionName("SSlyze Scan")
    unique_list_of_urls=BurpExtender.get_all_hosts(self)
    list_ssl_urls=BurpExtender.extract_ssl_hosts(self,unique_list_of_urls)
    BurpExtender.scan_ssl(self,list_ssl_urls)

  def get_all_hosts(self):
    unique_list_of_urls=[]
    # Get proxy history
    proxyhistory=self._callbacks.getProxyHistory()

    #Read each request in proxy history
    for request in proxyhistory:
      request_byte_array=request.getRequest()
      request_http_service=request.getHttpService()
      requestInfo = self._helpers.analyzeRequest(request_http_service,request_byte_array)

      t1=str(requestInfo.getUrl())
      t2=t1.split('/')
      url=t2[0]+'//'+t2[2]

      #Extract hostname from header
      hostname=webcommon.get_host_header_from_request(self,requestInfo)
      if url not in unique_list_of_urls:
        unique_list_of_urls.append(url)

    return unique_list_of_urls

  def extract_ssl_hosts(self,unique_list_of_urls):
    list_ssl_urls=[]
    for url in unique_list_of_urls:
      if url.startswith('https'):
        list_ssl_urls.append(url)

    return list_ssl_urls

  def scan_ssl(self,list_ssl_urls):
    for url in list_ssl_urls:
      print "Processing url "+url
      dest=url.split(':')
      full_path=result_dir+dest[1][2:]+'_'+result_file
      cmd='python /media/9f576cb3-3236-42c7-b9bf-869b455b2d87/Installations/sslyze/sslyze-0.6_src/sslyze.py --sslv2 --sslv3 --tlsv1 --tlsv1_1 --tlsv1_2 --hide_rejected_ciphers --reneg --certinfo=basic '+dest[1][2:]+' '+dest[2]+'>'+full_path
      print cmd
      os.system(cmd)

########NEW FILE########
__FILENAME__ = third_party_referer_record
from burp import IBurpExtender
from burp import IHttpListener
from burp import IProxyListener
import re
import sys
import os

urls_in_scope=['testblah.com','qa.ooboob.com']
#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules/')
sys.path.insert(0, module_folder)
import webcommon

class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):
  def registerExtenderCallbacks(self,callbacks):
    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()

    # set our extension name
    callbacks.setExtensionName("Third Party Referer")

    # register ourselves as an HTTP listener
    callbacks.registerHttpListener(self)

    # register ourselves as a Proxy listener
    callbacks.registerProxyListener(self)

  def processProxyMessage(self,messageIsRequest,message):
    request_http_service=message.getMessageInfo().getHttpService()
    request_byte_array=message.getMessageInfo().getRequest()
    request_object=self._helpers.analyzeRequest(request_http_service, request_byte_array)

    #Extract hostname from header
    hostname=webcommon.get_host_header_from_request(self,request_object)

    #Check if the URL is NOT in scope. We want to look at referers for the requests that are made to OTHER domains.
    if (hostname) and (hostname[1] not in urls_in_scope):
      #Extract referer from header
      referer=webcommon.get_referer_header_from_request(self,request_object)
      if referer:
        t1=referer[1].split('/')
        if t1[2] in urls_in_scope:
          print referer[1]

########NEW FILE########
__FILENAME__ = url_in_parameter_detect
from burp import IBurpExtender
from burp import IHttpListener
from burp import IProxyListener
import re
import sys
import urllib
import os

param_constant_type_mapping = {'0':'PARAM_URL','1':'PARAM_BODY','2':'PARAM_COOKIE','3':'PARAM_XML','4':'PARAM_XML_ATTR','5':'PARAM_MULTIPART_ATTR','6':'PARAM_JSON'}
url_patterns=['http','https','://','/','\w\.\w+$','\\\\','%5c','%2f','%3a']
excluded_url_patterns=['\d+/\d+/\d+','\d+%2f\d+%2f\d+']
urls_in_scope=['testblah.com','qa.blah.com','qa.ooboob.com']

#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules/')
sys.path.insert(0, module_folder)
import webcommon

class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):
  def registerExtenderCallbacks(self,callbacks):
    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()

    # set our extension name
    callbacks.setExtensionName("URL in Parameter Detector")

    # register ourselves as an HTTP listener
    callbacks.registerHttpListener(self)

    # register ourselves as a Proxy listener
    callbacks.registerProxyListener(self)

  def processProxyMessage(self,messageIsRequest,message):
    request_urls = BurpExtender.detect_urls_in_parameters(self,messageIsRequest,message)
    if request_urls:
      print request_urls

  def detect_urls_in_parameters(self,messageIsRequest,message):
    #Only process requests
    if messageIsRequest:
      request_http_service=message.getMessageInfo().getHttpService()
      request_byte_array=message.getMessageInfo().getRequest()
      request_object=self._helpers.analyzeRequest(request_http_service, request_byte_array)

      #Extract hostname from header
      hostname=webcommon.get_host_header_from_request(self,request_object)

      #Check if the URL is in scope. This is to eliminate stray traffic.
      if hostname and hostname[1] in urls_in_scope:
        request_url=request_object.getUrl()
        request_parameters=request_object.getParameters()

        #Check if the value of each parameter matches a whitelist or a blacklist. Both lists are defined above as global variables.
        for param in request_parameters:
          blacklist=0
          whitelist=0
          for excluded_pattern in excluded_url_patterns:
            regex=re.compile('.*%s.*'%excluded_pattern,re.IGNORECASE)
            m2=regex.match(str(param.getValue()))
            #m3=regex.match(urllib.quote(str(param.getValue())))
            if m2:# or m3:
              blacklist=1

          #If it doesn't match a blacklist
          if blacklist == 0:
            for pattern in url_patterns:
              regex=re.compile('.*%s.*'%pattern,re.IGNORECASE)
              m1=regex.match(str(param.getValue()))
              #m4=regex.match(urllib.quote_plus(str(param.getValue())))
              if m1:# or m4:
                whitelist=1

          #If the value for the URL parameter matches a pattern print it out
          if whitelist==1:
            #The moment you detect that a URL matches a pattern you also want to fuzz it. Hence you do the following:
            # -- Check if you already sent it to Intruder
            # -- If not, mark the positions that you want scanned
            # -- Set the payload list, set any other Intruder customizations up
            # -- Send the URL to be fuzzed to Intruder
            # -- Probably fuzz it as well and save the Intruder results to be imported later
            print str(request_url)+"\t\t"+str(param_constant_type_mapping[str(param.getType())])+"\t\t"+str(param.getName())+"\t\t"+str(param.getValue())
    else:
      response_byte_array=message.getMessageInfo().getResponse()
      responseInfo = self._helpers.analyzeResponse(response_byte_array)

      responseCode=webcommon.get_response_code_from_headers(self,responseInfo)
      location=webcommon.get_location_from_headers(self,responseInfo)
      if location:
        print str(responseCode[0])+'\t\t'+str(location[1])

########NEW FILE########
__FILENAME__ = version_detect
#Get server header from every response and dump it into a file
#Search response bodies for a set of common versions

from burp import IBurpExtender
from burp import IHttpListener
from burp import IProxyListener
import re
import sys
import os

unique_banners={}
list_of_platforms=['iis','apache','tomcat','weblogic','websphere','jetty','gws','ibm','oracle','nginx','bigip']
urls_in_scope=['test.blah.com']

#Adding directory to the path where Python searches for modules
module_folder = os.path.dirname('/home/arvind/Documents/Me/My_Projects/Git/WebAppsec/BurpExtensions/modules/')
sys.path.insert(0, module_folder)
import webcommon

class BurpExtender(IBurpExtender, IHttpListener, IProxyListener):
  def registerExtenderCallbacks(self,callbacks):
    # Get a reference to the Burp helpers object
    self._helpers = callbacks.getHelpers()

    # set our extension name
    callbacks.setExtensionName("Platform Information Extractor")

    # register ourselves as an HTTP listener
    callbacks.registerHttpListener(self)

    # register ourselves as a Proxy listener
    callbacks.registerProxyListener(self)

  def processProxyMessage(self,messageIsRequest,message):
    response_byte_array=message.getMessageInfo().getResponse()

    request_http_service=message.getMessageInfo().getHttpService()
    request_byte_array=message.getMessageInfo().getRequest()
    request_object=self._helpers.analyzeRequest(request_http_service, request_byte_array)

    #Extract hostname from header
    hostname=webcommon.get_host_header_from_request(self,request_object)
    #hostname=BurpExtender.get_host_header_from_request(self,request_object)

    #Check if the URL is in scope. This is to eliminate stray traffic.
    if hostname and hostname[1] in urls_in_scope:
       if not messageIsRequest:
         responseInfo = self._helpers.analyzeResponse(response_byte_array)

         #Extract banner from response
         banner=webcommon.get_banner_from_response(self,responseInfo)
         if banner not in unique_banners.keys():
           unique_banners[banner]=''
           print banner

         #Extract platform specific content from response
         responseBody=webcommon.get_response_body(self,response_byte_array,responseInfo)
         responseBody_string=self._helpers.bytesToString(responseBody)

         for platform_name in list_of_platforms:
           regex=re.compile('.{30}%s.{30}'%platform_name,re.IGNORECASE|re.DOTALL)
           m2=regex.search(responseBody_string)
           if m2:
             print m2.group(0)+'\n'+'-'*30+'\n'

########NEW FILE########
__FILENAME__ = force_http_req_threaded
#http://stackoverflow.com/questions/110498/is-there-an-easy-way-to-request-a-url-in-python-and-not-follow-redirects
#http://kentsjohnson.com/kk/00010.html
#http://stackoverflow.com/questions/4560288/python-try-except-showing-the-cause-of-the-error-after-displaying-my-variables
#http://nocivus.posterous.com/way-to-wait-for-all-threads-to

import sys
import re
import urllib2
import traceback
import threading
import os
import time

urldir='URLs/'; requests='https_urls'; report='report'
urls_accessible_http=[]

def main():
  #The number of URLs you initially copy can be huge. This results in too many threads spawning and the stupid code crashing :). So we split.
  split_into_multiple_files()
  #Run code for every file in the directory.
  all_requests=os.listdir(urldir)
  for i in all_requests:
    #Does not start with a new file; unless all the threads processing the previous file are done.
    while threading.activeCount() > 1:
      time.sleep(0.01)
    print 'Processing file '+i
    #Uses simple regex to convert all the https URLs into http
    list_of_requests=read_https_urls(urldir+i)
    #Request every URL over HTTP
    request_over_http(list_of_requests)
    #This sleep is super important; as funny race conditions occur without it. May look at a better way later; for now this will do :)
    time.sleep(10)
    #Writes report to file
    create_report(i,urls_accessible_http)
    #Multiple instances written to file for some stupid reason; got to extract unique URLs only
    get_unique_urls(report)

#Uses Linux system commands to split. Is there a more 'platform independent' way of doing this? Probably.
def split_into_multiple_files():
  os.system('rm '+urldir+'*')
  os.system('cp '+requests+' '+urldir)
  os.system('split -l 50 '+urldir+requests+' url_')
  os.system('mv url_* URLs/')
  os.system('rm '+urldir+requests)
  os.system('rm '+report)
  
#Read BURP site map HTTPS Urls
def read_https_urls(requests):
  list_of_requests=[]
  try:
    f=open(requests,'r')
  except:
    print 'Could not open file containing requests'
  for url in f:
    url=re.sub(r'^https',r'http',url)
    list_of_requests.append(url)
  f.close()
  return list_of_requests

#Request all converted URLs over HTTP
def request_over_http(list_of_requests):
  threads=[]
  #This is each split file getting read. Some nice threading done here :)
  for url in list_of_requests:
    url=re.sub(r'\s+$',r'',url)
    url=re.sub(r'^\s+',r'',url)
    t = threading.Thread(target=thread_request_over_http, args=(url,))
    threads.append(t)
    t.start()

  return urls_accessible_http

#Callback function for thread which does all the grunt work
def thread_request_over_http(url):
  try:
    f = urllib2.urlopen(url)
    t1=f.geturl().split(':')
    if t1[0] != 'https':
      urls_accessible_http.append(url)
  except Exception:
    pass

#Create a report after requests are made
def create_report(filename,urls_accessible_http):
  try:
    f=open(report,'a')
  except:
    print 'Cannot open file to write report'
    traceback.print_exc(file=sys.stdout)

  if len(urls_accessible_http) > 0:
    f.write(filename+'\n\n')
    for url in urls_accessible_http:
      f.write('-----------')
      f.write('\n'+url+'\n')
    f.write('-----------')
  else:
    f.write(filename+' --- None of the URLs can be accessed over HTTP.\n')

  f.close()

#Get only unique URLs from the report
def get_unique_urls(report):
  unique_urls=[]
  try:
    f=open(report,'rU')
  except:
    print 'Cannot open generated report'
  t1=f.read()
  f.close()

  t2=t1.split('\n')
  for i in t2:
    if i not in unique_urls:
      unique_urls.append(i)

  os.system('rm -rf '+report)
  try:
    f=open(report,'w')
  except:
    print 'Cannot write report with unique files'
  for i in unique_urls:
    if i != '':
      f.write(i+'\n') 
  f.close()

#Code starts here
main()

########NEW FILE########
__FILENAME__ = numeric_fuzz_lists
import random
import sys

#Generate  a random large integer
print random.randrange(0,100000000000000000000000000000)

#Generate a random large float with and without a random large decimal
print random.uniform(0.0,39873285793487643.29357)
print random.uniform(0.0,39873285793487643.2935743967439860376894768945)

#Generate a large negative integer
print random.randrange(-1,-324235436436346353543646,-1)

#Generate a large negative float
print random.uniform(-1.0,-39873285793487643.274809)

#Generate a random hexadecimal number
lst=[random.choice('0123456789abcdef') for i in xrange(30)]
x=''.join(lst)
x='0x'+x
print x

#Largest Python integer
print sys.maxint
print sys.maxint+1

#Smallest Python integer
print -sys.maxsize-2

#Largest Python Float
print sys.float_info.max
print sys.float_info.max+1

#Integer rep of float in memory (This one's by Max)
print int('0'+'1'*8+'0'*23,2)

#Smallest Python float
print sys.float_info.min

#Explicit 'L' and explicit 'B' tagged on at the end
print '79228162514264337593543950336L'
print '79228162514264337593543950336l'
print '79228162514264337593543950336B'

#Different types of infinity :)
print float('inf')
print 'Infinity'
print '-Infinity'

#Not a number
print 'NaN'

#Largest unsigned integers - 8,16,32 and 64 bit
print '255\n65535\n4294967295\n18446744073709551615\n'

#Largest unsigned integers - 8,16,32 and 64 bit PLUS 1
print '256\n65536\n4294967296\n18446744073709551616\n'

#Largest signed integers - 8,16,32 and 64 bit
print '127\n32767\n2147483647\n9223372036854775807\n'

#Largest signed integers - 8,16,32 and 64 bit PLUS 1
print '128\n32768\n2147483648\n9223372036854775808\n'

#Smallest signed integers - 8,16,32 and 64 bit
print '-128\n-32768\n-2147483648\n-9223372036854775808\n'

#Smallest signed integers - 8,16,32 and 64 bit PLUS 1
print '-129\n-32769\n-2147483649\n-9223372036854775809\n'

########NEW FILE########
