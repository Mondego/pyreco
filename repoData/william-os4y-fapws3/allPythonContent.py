__FILENAME__ = base
# -*- coding: utf-8 -*-

#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import datetime
from Cookie import SimpleCookie, CookieError
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import sys
import string
import traceback
import time

import config
import httplib


def get_status(code):
    return "%s %s" % (code, httplib.responses[code])


class Environ(dict):
    def __init__(self, *arg, **kw):
        self['wsgi.version'] = (1, 0)
        self['wsgi.errors'] = StringIO.StringIO()
        self['wsgi.input'] = StringIO.StringIO()
        self['wsgi.multithread'] = False
        self['wsgi.multiprocess'] = True
        self['wsgi.run_once'] = False
        self['fapws.params'] = {}
    #here after some entry point before the Environ update

    def update_headers(self, data):
        dict.update(self, data)

    def update_uri(self, data):
        dict.update(self, data)

    def update_from_request(self, data):
        dict.update(self, data)


class Start_response:
    def __init__(self):
        self.status_code = "200"
        self.status_reasons = "OK"
        self.response_headers = {}
        self.exc_info = None
        self.cookies = None
        # NEW -- sent records whether or not the headers have been send to the
        # client
        self.sent = False

    def __call__(self, status, response_headers, exc_info=None):
        self.status_code, self.status_reasons = status.split(" ", 1)
        self.status_code = str(self.status_code)
        for key, val in response_headers:
            #if type(key)!=type(""):
            key = str(key)
            #if type(val)!=type(""):
            val = str(val)
            self.response_headers[key] = val
        self.exc_info = exc_info  # TODO: to implement

    def add_header(self, key, val):
        key = str(key)
        val = str(val)
        self.response_headers[key] = val

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/', domain=None, secure=None):
        if not self.cookies:
            self.cookies = SimpleCookie()
        self.cookies[key] = value
        if max_age:
            self.cookies[key]['max-age'] = max_age
        if expires:
            if isinstance(expires, str):
                self.cookies[key]['expires'] = expires
            elif isinstance(expires, datetime.datetime):
                expires = evwsgi.rfc1123_date(time.mktime(expires.timetuple()))
            else:
                raise CookieError('expires must be a datetime object or a string')
            self.cookies[key]['expires'] = expires
        if path:
            self.cookies[key]['path'] = path
        if domain:
            self.cookies[key]['domain'] = domain
        if secure:
            self.cookies[key]['secure'] = secure

    def delete_cookie(self, key):
        if self.cookies:
            self.cookies[key] = ''
        self.cookies[key]['max-age'] = "0"

    def __str__(self):
        res = "HTTP/1.0 %s %s\r\n" % (self.status_code, self.status_reasons)
        for key, val in self.response_headers.items():
            res += '%s: %s\r\n' % (key, val)
        if self.cookies:
            res += str(self.cookies) + "\r\n"
        res += "\r\n"
        return res


def redirectStdErr():
    """
    This methods allow use to redirect messages sent to stderr into a string
    Mandatory methods of the sys.stderr object are:
        write: to insert data
        getvalue; to retreive all data
    """
    sys.stderr = StringIO.StringIO()

supported_HTTP_command = ["GET", "POST", "HEAD", "OPTIONS"]


def split_len(seq, length):
    return [seq[i:i + length] for i in range(0, len(seq), length)]


def parse_cookies(environ):
    #transform the cookie environment into a SimpleCokkie object
    line = environ.get('HTTP_COOKIE', None)
    if line:
        cook = SimpleCookie()
        cook.load(line)
        return cook
    else:
        return None

########NEW FILE########
__FILENAME__ = config
#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
SERVER_IDENT = "fapws3/0.11"
send_traceback_to_browser = True
#in case of False for send_traceback_to_browser, send_traceback_short will be sent to the browser
send_traceback_short = "<h1>Error</h1>Please contact your administrator"
date_format = "%a, %d %b %Y %H:%M:%S GMT"

########NEW FILE########
__FILENAME__ = cgiapp
#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import os
import subprocess


class CGIApplication:
    def __init__(self, script):
        self.script = script
        self.dirname = os.path.dirname(script)
        self.cgi_environ = {}

    def _setup_cgi_environ(self, environ):
        for key, val in environ.items():
            if type(val) is str:
                self.cgi_environ[key] = val
        self.cgi_environ['REQUEST_URI'] = environ['fapws.uri']

    def _split_return(self, data):
        if '\n\n' in data:
            header, content = data.split('\n\n', 1)
        else:
            header = ""
            content = data
        return header, content

    def _split_header(self, header):
        i = 0
        headers = []
        firstline = "HTTP/1.1 200 OK"
        for line in header.split('\n'):
            if i == 0 and ':' not in line:
                firstline = line
            if ':' in line:
                name, value = line.split(':', 1)
                headers.append((name, value))
            i += 1
        status = " ".join(firstline.split()[1:])
        return status, headers

    def __call__(self, environ, start_response):
        self._setup_cgi_environ(environ)
        proc = subprocess.Popen(
                    [self.script],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=self.cgi_environ,
                    cwd=self.dirname,
                    )
        input_len = environ.get('CONTENT_LENGTH', 0)
        if input_len:
            cgi_input = environ['wsgi.input'].read(input_len)
        else:
            cgi_input = ""
        #print "cgi input", cgi_input
        stdout, stderr = proc.communicate(cgi_input)
        if stderr:
            return [stderr]
        header, content = self._split_return(stdout)
        status, headers = self._split_header(header)
        start_response(status, headers)
        return [content]

########NEW FILE########
__FILENAME__ = django_handler
#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
from django.core.handlers import wsgi
import django


djhand = wsgi.WSGIHandler()


def handler(environ, start_response):
    res = djhand(environ, start_response)
    if django.VERSION[0] == 0:
        for key, val in res.headers.items():
            start_response.response_headers[key] = val
    else:
        for key, val in res._headers.values():
            start_response.response_headers[key] = val
    start_response.cookies = res.cookies
    return res.content

########NEW FILE########
__FILENAME__ = headers
#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


def redirect(start_response, location, permanent=None):
    header = [('location', location), ('Content-Type', "text/plain")]
    if permanent:
        start_response('301 Moved Permanently', header)
    else:
        start_response('302 Moved Temporarily', header)
    return []

########NEW FILE########
__FILENAME__ = log
# -*- coding: utf-8 -*-
#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import time
import os
import sys


class Log:
    def __init__(self, output=sys.stdout):
        self.output = output

    def __call__(self, f):
        def func(environ, start_response):
            res = f(environ, start_response)
            tts = time.strftime("%d/%b/%Y:%H:%M:%S", time.gmtime())
            if type(res) is list:
                content = "".join(res)
                size = len(content)
            elif hasattr(res, "name"):
                #this is a filetype object
                size = os.path.getsize(res.name)
            else:
                size = "-"
            #this is provided by a proxy or direct
            remote_host = environ.get('HTTP_X_FORWARDED_FOR', environ['fapws.remote_addr'])
            self.output.write("%s %s - [%s GMT] \"%s %s %s\" %s %s \"%s\" \"%s\"\n" % (remote_host, environ['HTTP_HOST'], tts, environ['REQUEST_METHOD'], environ['fapws.uri'], environ['wsgi.url_scheme'],  start_response.status_code, size, environ.get("HTTP_REFERER", "-"), environ.get('HTTP_USER_AGENT', "-")))
            self.output.flush()
            return res
        return func

########NEW FILE########
__FILENAME__ = multipart
import os.path

class Storage(object):
    def __init__(self):
        self.fpath=None
    def open(self, attr):
        pass
    def write(self, data):
        pass
    def close(self):
        self.fpath=None #self.fpath allow us to know if the storage repository has to write some data or not

class DiskStorage(Storage):
    def open(self, fpath):
        self.fpath=fpath
        if self.fpath:
            self.fid=open(self.fpath,"wb")
        else:
            raise ValueError("fpath is not declared")
    def write(self, data):
        if self.fid:
            self.fid.write(data)
        else:
            raise ValueError("First open before writing")
    def close(self):
        self.fpath=None
        if self.fid:
            self.fid.close()
        
class DiskVersioning(DiskStorage):
    def _definefilename(self, fpath):
        "This method avoid the overwrite syndrome"
        if os.path.isfile(fpath):
            base,ext=os.path.splitext(fpath)
            res=base.rsplit('_',1)
            if len(res)==1:
                version="0"
                name=res[0]
            else:
                name,version=res
            return self._definefilename(name+"_"+str(int(version)+1)+ext)
        return fpath
    def open(self, fpath):
        self.fpath=self._definefilename(fpath)
        if self.fpath:
            self.fid=open(self.fpath,"wb")
        else:
            raise ValueError("fpath is not declared")

class GitStorage(Storage):
    "Still to develop"
    
    
class DBstorage(Storage):
    "still to develop"
    
    

class MultipartFormData(object):
    """This class allow you to read, on the fly, the multipart elements we useually find in wsgi.input.
       file like objects are stored on the fly on disk, parameters are strored in .results dictionary
       For a specific parameter, and if required, an extra dictionary containing additinal info is appended.
       Feel free to adapt the self.definefilename. As default, we use the versioning. 
    """
    def __init__(self, basepath="./"):
        "Just porovide the directory path where the file objects must be stored" 
        self.basepath=basepath
        self.results={}
        self.boundary=None
        self._inheader=False
        self.filerepository=DiskVersioning() #per default we use the versioning method
    def write(self, data):
        #data can be chunk of the input data or all the input data
        line=""
        prevchar=""
        paramkey=""
        paramvalue=""
        paramattr={}
        content=""
        for char in data:
            line+=char
            if char=="\n" and prevchar=="\r":
                if self.boundary==None and line[:2]=="--":
                    #we have found a boudary. This will be used for the rest of the parser
                    self.boundary=line.strip()
                if self.boundary in line:
                    self._inheader=True
                    if content and not paramvalue:
                        paramvalue=content.strip()
                    if self.filerepository.fpath:
                        #we have to close the previous outputfid
                        self.filerepository.close()
                        paramattr['size']=os.path.getsize(paramvalue)
                    if paramkey:
                        self.results.setdefault(paramkey,[])
                        self.results[paramkey].append(paramvalue)
                        if paramattr:
                            self.results[paramkey].append(paramattr)
                    content=""
                    paramvalue=""
                    paramattr={}
                elif line.strip()=="" and self._inheader:
                    self._inheader=False
                elif self._inheader:
                    key,val=map(lambda x: x.strip(),  line.split(':'))
                    if key=="Content-Disposition" and val[0:10]=="form-data;":
                        for elem in val[11:].split(';'):
                            pkey,pval=map(lambda x: x.strip(),  elem.split('='))
                            if pval[0]=='"' and pval[-1]=='"':
                                pval=pval[1:-1]
                            if pkey=="filename":
                                if pval:
                                    self.filerepository.open(self.basepath+pval)
                                    paramvalue=self.filerepository.fpath
                            elif pkey=="name":
                                paramkey=pval
                            else:
                                paramattr[pkey]=pval
                    else:
                        paramattr[key]=val
                elif not self._inheader:
                    if self.filerepository.fpath:
                        self.filerepository.write(line)
                    else:
                        content+=line
                line=""
            prevchar=char
    def seek(self, position):
        #required for compatibility with file like object
        pass
    def getvalue(self):
        return self.results
    def get(self, key):
        return self.results.get(key, None)
    def keys(self):
        return self.results.keys()
    


########NEW FILE########
__FILENAME__ = sessions
#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import binascii
import datetime
try:
    import cPickle as pickle
except ImportError:
    import pickle
import os
import time


class Session:
    """
      This class will manage the session's data for you. Will take into account the expiration date, ... 
      Data can be any picklable object. 
      
      This object must be managed by a SessionMgr acting like this:
      class SessionMgr:
          #This sessionMgr is using sessdb with get and save methods.
	  def __init__(self, environ, start_response):
	      #we retreive the Session object from our Storage object
	      self.sessdb=None  
	      self._sessionid=None
	      self.start_response=start_response
	      cook=base.parse_cookies(environ)
	      if cook and cook.get('sessionid', None):
		  self._sessionid=cook['sessionid'].value
		  self.sessdb= ... # you retreive your sessdb dictionary from your Storage object (mysql, sqlite3, ...)
	      if not self.sessdb:
		  self.sessdb=... # your create an empty sessdb dictionary 
	  def get(self, key, default=None):
	      #To get a element of the data dictionary
	      sess=Session(self.sessdb)
	      data=sess.getdata() or {}         #this session manager use dictionary data
	      return data.get(key, default)
	  def set(self, key, value):
	      #to set a key/element in our dictionary
	      sess=Session(self.sessdb)
	      data=sess.getdata() or {}         #this session manager use dictionary data
	      data[key]=value
	      sess.setdata(data)      #This dumps data in our sess object, thus is our sessdb object
	      self.sessdb.save()      #If you sessdb object is a Storage object it should have asave method. 
	  def delete(self, key):
	      #to delete a key from our dictionary
	      sess=sessions.Session(self.sessdb)
	      data=sess.getdata() or {}
	      if data.has_key(key):
		  del data[key]
	      sess.setdata(data)
	      self.sessdb.save()

    """
    def __init__(self, sessiondb, max_age=10 * 86400, datetime_fmt="%Y-%m-%d %H:%M:%S", prepare_data=None):
        """
           sessiondb:   this is in fact a record of your sessionDB. This can be an empty record. 
           max_age:     the session duration. After expiration the associated date will be lost
           datetime_fmt: the time format are we have in the cookies
           prepare_date: method required to treat the data. Can be str, ... 
        """
        self.sessiondb = sessiondb  # must have a get method and return dictionary like object with sessionid, strdata and expiration_date
        self.datetime_fmt = datetime_fmt
        self.max_age = max_age
        self.prepare_data=prepare_data
        #we should always have a sessionid and an expiration date
        if not self.sessiondb.get('sessionid', None):
            self.newid()
        if not self.sessiondb.get('expiration_date', None):
            self.update_expdate()

    def getdata(self):
        "return the python objected associated or None in case of expiration"
        exp = self.sessiondb.get('expiration_date', None)
        if not exp:
            return None
        if type(exp) is datetime.datetime:
            expdate = exp
        elif type(exp) in (str, unicode):
            expdate = datetime.datetime.fromtimestamp(time.mktime(time.strptime(exp, self.datetime_fmt)))
        else:
            raise ValueError("expiration_Date must be a datetime object or a string (%s)" % self.datetime_fmt)
        if expdate < datetime.datetime.now():
            #expired
            return None
        else:
            if self.sessiondb['strdata']:
                strdata = str(self.sessiondb['strdata'])
                data = pickle.loads(strdata)
                return data
            else:
                return None

    def setdata(self, data):
        strdata = pickle.dumps(data)
        if self.prepare_data:
             strdata=self.prepare_data(strdata)
        self.sessiondb['strdata'] = strdata

    def newid(self):
        sessid = binascii.hexlify(os.urandom(12))
        self.sessiondb['sessionid'] = sessid

    def getid(self):
        return self.sessiondb.get('sessionid')

    def update_expdate(self):
        self.sessiondb['expiration_date'] = self._getexpdate()

    def _getexpdate(self):
        now = datetime.datetime.now()
        exp = now + datetime.timedelta(seconds=self.max_age)
        return exp.strftime(self.datetime_fmt)


if __name__ == "__main__":
    DB={}
    s=Session(DB, max_age=2) # we store data for 2 seconds
    s.newid() # we request an ID
    s.setdata({'test':'fapws values'}) # we set some values
    print "Our DB:", s.getdata()
    print "Those values will be stored for 2 seconds"
    print "now we sleep for 3 seconds"
    time.sleep(3)
    print "Our DB:", s.getdata()
    

########NEW FILE########
__FILENAME__ = forms
# -*- coding: utf-8 -*-
        
class FormFactory(type):
    """This is the factory required to gather every Form components"""
    def __init__(cls, name, bases, dct):
        cls.datas={}
        for k,v in dct.items():
            if k[0]!="_":
                cls.datas[k]=v
        return type.__init__(cls, name, bases, dct)
        
        
class Form(object):
    def __init__(self, action="", method="post", **kw):
        """You have to provide the form's action, the form's method and some additional parameters.
           You can put any type of form's parameter expect "class" which must be written "class_"
        """
        self.errors={}
        self.values={}
        self.action=action
        self.method=method
        self.parameters=""
        for k,v in kw.items():
            if k=="class_":
                self.parameters+=' class="%s"' % (v)
            else:
                self.parameters+=' %s="%s"' % (k, v)
        self.submit_text=""
    def submit(self, buttons):
        """Generate self.submit_text
        parameters must be a list of (value, name, params).
        params is here a string
        
        sample:
          <fieldset class="submit">
            <input type="submit" value="send" name="bt1"/>
            <input type="submit" value="cancel" name="bt1"/>
          <fieldset>
        """
        res='<fieldset class="submit">'
        for value, name, params in buttons:
            res+='<input type="submit" value="%s" name="%s" %s/>' % (value, name, params)
        res+="</fieldset>"
        self.submit_text=res
    def render_error(self, name):
        """generate a list of error messages.
        
        sample:
         <ul class="errorlist">
           <li><rong value</li>
         </ul>
        """
        err="""<ul class="errorlist">"""
        for error in self.errors[name]:
            err+="<li>%s</li>" % error
        err+="</ul>"
        return "<div>%s</div>" % err
    def render_form(self, form_fields):
        """Generate the html's form with all fields provided and the self.submit_text previously generated. 
        This is the main method to generate the form. 
        Parameter is a list of field's names you want to see in the form. 
        """
        res='<form action="%s" method="%s" %s>\n' % (self.action, self.method, self.parameters)
        res+="<fieldset>\n<ol>\n"
        for name in form_fields:
            obj=self.datas[name]
            if self.errors.has_key(name):
                res+= '<li class="error">'
                errormsg=self.render_error(name)+"\n"
            else:
                res+= "<li>"
                errormsg=None
            value=self.values.get(name, "")
            res+= obj.render(name, value)
            if errormsg:
                res+=errormsg
            res+= "</li>\n"
        res+="</ol>\n</fieldset>\n"
        res+=self.submit_text
        res+="</form>\n"
        return res
    def validate(self, input_values, form_fields):
        """Validate the data provided in the 1st parameter (a dictionary) agains the fields provided in the 2nd parameter (a list).
        and store the values in self.values
        
        This is an important medthod that allow you to generate self.values. 
        
        self.values is the actual result of the form. 
        """
        self.errors={}
        for name in form_fields:
            obj=self.datas[name]
            if input_values.has_key(name):
                data=input_values[name]
            else:
                data=""
            err=obj.isvalid(data)
            if err:
                self.errors[name]=err
            else:
                self.values[name]=data
    def render_list(self, records):
        """Generate a table with a list of possible values associated with this form.
        1st parameter must be a list of dictionary.
        
        The first column of the generated table will receive the hyperlink: /admin/edit/<table name>/<record id> to the real form
        """
        res="""<table class="tablesorter">\n<thead>\n<tr>"""
        for name in self._html_list:
            res+="<th>%s</th>" % name
        res+="</tr>\n</thead>\n<tbody>"
        i=1
        for data in records:
            if i%2==0:
                class_="odd"
            else:
                class_="even"
            res+='<tr class="%s">' % class_
            j=1
            for name in self._html_list:
                obj=self.datas[name]
                if j==1:
                    pk_path=[]
                    for key in self._dbkey:
                        pk_path.append(unicode(data[key]))
                    res+="""<td %s><a href="/admin/edit/%s/%s">%s</a></td>""" % (obj.list_attrs,self.__class__.__name__, "/".join(pk_path),unicode(data[name] or ""))
                else:
                    res+="<td %s>%s</td>" % (obj.list_attrs, unicode(data[name] or ""))
                j+=1
            res+="</tr>\n"
            i+=1
        res+="\n</tbody>\n</table>"
        return res

########NEW FILE########
__FILENAME__ = widgets
# -*- coding: utf-8 -*-


import string

#TODO: manage multiple values in isvalid

def makeid(name):
    """
    >>> t=u"this is oéké\t"
    >>> makeid(t)
    'thisisok'
    >>> 
    """
    #turn it to a real string
    res=name.encode('ascii','ignore')
    #remove all unneeded char
    res=res.translate(None, string.punctuation+' \t\n\r')
    return res

class Widget(object):
    """This is the metaclass from which all from's element will come from
    self.label is the label of the associate html's  input (must be unicode)
    If self.required is True the label's class with receive "required".
    self.default contains the default value of your html input
    Other parameters can be provided and will be added to the input's form (class, must be written class_)
    You can provide additonal label's parameter by extending the dictionary label_attr
    """
    def __init__(self, label, required=False, default="", **kw):
        self.base=""
        self.list_attrs=""
        self.params=kw
        self.label=unicode(label)
        self.required=required
        self.default=default
        self.label_attr={'class':"table"}
    def getlabel(self, name):
        """Generate the label in html
        """
        if not self.label:
            return u""
        lid=makeid(name)
        if self.required and "required" not in self.label_attr.get('class',''):
            self.label_attr['class']+=" required"
        attrs=""
        for key,val in self.label_attr.items():
            attrs+='%s="%s" ' % (key, val)
        return u"""<label for="%s" %s>%s</label>""" % (lid, attrs, self.label)
    def _manage_class(self):
        if self.params.has_key("class_"):
            self.params["class"]=self.params["class_"]
            del self.params["class_"]

    def render(self, name, value):
        """This is the main method of this object, and will generated the whole html (lable and input element). 
        This method receiv 2 parameters: the input's name and input's value
        """
        #the 2 following lines must aways be present
        self._manage_class()
        parameters=" ".join(['%s="%s"' % (k,v) for k,v in self.params.items()])
        res=self.getlabel(name)
        if not value:
            value=self.default
        res+="""<%s name="%s" value="%s" %s/>""" % (self.base, name, unicode(value), parameters)
        return res
    def isrequired(self, value):
        """Intern method to return an error message in case the value is not provided"""
        res=[]
        if self.required and value in [None, ""]:
            res.append("Value cannot be empty")
        return res
    def isvalid(self, value):
        """Method that the forms.validate will call to assure the data provided are correct"""
        #the following line must always be present
        return self.isrequired(value)
    

class Text(Widget):
    """
    >>> t=Text("label")
    >>> t.render("name","val")
    u'<label for="name" class="table" >label</label><input name="name" value="val" type="text"/>'
    >>> t.isvalid("value")
    []
    >>> 
    >>> t=Text(u"label", required=True, id="text", class_="input")
    >>> t.render("name","val")
    u'<label for="name" class="table required" >label</label><input name="name" value="val" type="text" id="text" class="input"/>'
    >>> t.isvalid("value")
    []
    >>> t.isvalid("")
    ['Value cannot be empty']
    >>> 
    >>> t=Text("label")
    >>> t.label_attr['id']='input'
    >>> t.render("name","val")
    u'<label for="name" class="table" id="input" >label</label><input name="name" value="val" type="text"/>'
    >>> 
    >>> t=Text("label", default="why not")
    >>> t.render("name","value")
    u'<label for="name" class="table" >label</label><input name="name" value="value" type="text"/>'
    >>> t.render("name","")
    u'<label for="name" class="table" >label</label><input name="name" value="why not" type="text"/>'
    >>> 

    """
    def __init__(self, *lw, **kw):
        super(Text, self).__init__(*lw, **kw)
        self.params['type']='text'
        self.base="input"

class ReadonlyText(Text):
    """
    >>> r=ReadonlyText("label")
    >>> r.render("name","value")
    u'<label for="name" class="table" >label</label><input name="name" value="value" readonly="1" type="text"/>'
    >>> 
    """
    def __init__(self, *lw, **kw):
        super(ReadonlyText, self).__init__(*lw, **kw)
        self.params['readonly']="1"

class Hidden(Widget):
    """
    >>> h=Hidden("")
    >>> h.render("name","value")
    u'<input name="name" value="value" type="hidden"/>'
    >>> 
    """
    def __init__(self, *lw, **kw):
        super(Hidden, self).__init__(*lw, **kw)
        self.params['type']='hidden'
        self.base="input"
    
class Integer(Widget):
    """
    >>> i=Integer("label")
    >>> i.render("name","value")
    u'<label for="name" class="table" >label</label><input name="name" value="value" type="text" size="5"/>'
    >>> i.isvalid("value")
    ['Value is not an integer']
    >>> i.isvalid(12)
    []
    """
    def __init__(self, *lw, **kw):
        super(Integer, self).__init__(*lw, **kw)
        self.params['type']='text'
        self.params['size']=5
        self.base="input"
        self.list_attrs='class="nowrap"'
    def isvalid(self, value):
        res=super(Integer, self).isvalid(value)
        if not self.required and not value:
            return []
        try:
            val=int(value)
        except:
            res.append("Value is not an integer")
        return res

class Area(Widget):
    """
    >>> a=Area("label", cols="100")
    >>> a.render("name","value")
    u'<label for="name" class="bellow" >label</label><textarea name="name" rows="10" cols="100">value</textarea>'
    >>> a.isvalid("value")
    []
    """
    def __init__(self, *lw, **kw):
        super(Area, self).__init__(*lw, **kw)
        if not kw.has_key('cols'):
            self.params['cols']=40
        if not kw.has_key('rows'):
            self.params['rows']=10
        self.base="textarea"
        self.label_attr['class']='bellow'
    def render(self, name, content):
        self._manage_class()
        parameters=" ".join(['%s="%s"' % (k,v) for k,v in self.params.items()])
        res=self.getlabel(name)
        if not content:
            content=self.default
        res+= """<%(base)s name="%(name)s" %(args)s>%(content)s</%(base)s>""" % {'name':name, 'base': self.base, 'args': parameters, 'content':content}
        return res
        

class Check(Widget):
    """
    >>> c=Check("label", required=True)
    >>> c.render("name","value")
    u'<label for="name" class="table required" >label</label><input name="name" value="1" checked="checked" type="checkbox"/>'
    >>> c.render("name","")
    u'<label for="name" class="table required" >label</label><input name="name" value="1" type="checkbox"/>'
    >>> c.isvalid("")
    []
    >>> c=Check("label", default="1")
    >>> c.render("name","value")
    u'<label for="name" class="table" >label</label><input name="name" value="1" checked="checked" type="checkbox"/>'
    >>> c.render("name","")
    u'<label for="name" class="table" >label</label><input name="name" value="1" checked="checked" type="checkbox"/>'
    >>> 
    """
    def __init__(self, *lw, **kw):
        super(Check, self).__init__(*lw, **kw)
        self.params['type']='checkbox'
        self.base="input"
    
    def render(self, name, value):
        self._manage_class()
        if self.default or value:
            self.params['checked']="checked"
        else:
            if self.params.has_key('checked'):
                del self.params['checked']
        parameters=" ".join(['%s="%s"' % (k,v) for k,v in self.params.items()])
        res=self.getlabel(name)
        res+="""<%s name="%s" value="1" %s/>""" % (self.base, name, parameters)
        return res
    def isvalid(self, value):
        #in this case no need to verify the isrequired
        return []

class Boolean(Check):
    """
    >>> b=Boolean("label")
    >>> b.render("name","value")
    u'<label for="name" class="table" >label</label><input name="name" value="1" checked="checked" type="checkbox"/>'
    >>> 
    """
    pass

class Password(Text):
    """
    >>> p=Password("label")
    >>> p.render("name","value")
    u'<label for="name" class="table" >label</label><input name="name" value="value" type="password"/>'
    >>> p.isvalid("value")
    []
    >>> p.isvalid("")
    []
    >>> 
    """
    def __init__(self, *lw, **kw):
        super(Password, self).__init__(*lw, **kw)
        self.params['type']='password'


class Dropdown(Widget):
    """
    >>> d=Dropdown("label")
    >>> d.options=[("-1","-----"),("1","value")]
    >>> len(d.render("name","1"))
    164
    >>> len(d.render("name",""))
    144
    >>> d.isvalid("1")
    []
    >>> d=Dropdown("label", required=True)
    >>> d.options=[("-1","-----"),("1","value")]
    >>> d.isvalid("1")
    []
    >>> d.isvalid("2")
    ['Value not in the list']
    >>> d.isvalid("-1")
    ['Not a valid value']
    >>> 
    """
    def __init__(self, *lw, **kw):
        super(Dropdown, self).__init__(*lw, **kw)
        self.base='select'
    
    def render(self, name, value_selected):
        self._manage_class()
        res=self.getlabel(name)
        parameters=" ".join(['%s="%s"' % (k,v) for k,v in self.params.items()])
        res+='<%s name="%s" %s>\n' % (self.base, name, parameters) 
        if not value_selected:
            value_selected=self.default
        for oval, oname in self.options:
            if unicode(oval) == unicode(value_selected):
                res+='<option value="%s" selected="selected">%s</option>\n' % (oval,oname)
            else:
                res+='<option value="%s">%s</option>\n' % (oval,oname)
        res+="</select>"
        return res
    def isvalid(self, value):
        res=super(Dropdown, self).isvalid(unicode(value))
        if self.required:        
            if unicode(value) not in [unicode(k) for k,e in self.options]:
                res.append("Value not in the list")
            if unicode(value)=="-1":
                res.append("Not a valid value")
        return res

class Foreignkey(Dropdown):
    """
    >>> f=Foreignkey("label")
    >>> f.options=[("-1","-----"),("1","value")]
    >>> len(f.render("name","1"))
    164
    >>> len(f.render("name",""))
    144
    >>> f.url_other_table="/admin/tablea/add"
    >>> len(f.render("name","1"))
    346
    >>> 
    """
    def __init__(self, *lw, **kw):
        super(Foreignkey, self).__init__(*lw, **kw)
        self.url_other_table=""
    def render(self, name, value):
        res=super(Foreignkey,self).render(name, value)
        if self.url_other_table:
            res+="""<a href="#" onClick="window.open('%s?_open=popup','mywindow','width=900,height=600,scrollbars=yes,resizable=yes')"> <img src="/static/images/add.png" height="12"/></a>""" % self.url_other_table
        return res

    

class Date(Widget):
    """
    >>> d=Date("label")
    >>> d.render("name","2011-01-01")
    u'<label for="name" class="table" >label</label><input name="name" value="2011-01-01" type="text"/>'
    >>> d.isvalid("2011-01-01")
    []
    >>> d.isvalid("2011-011-01")
    ['Date must have the format yyyy-mm-dd']
    >>> 
    """
    def __init__(self, *lw, **kw):
        super(Date, self).__init__(*lw, **kw)
        self.params['type']='text'
        self.base="input"
    def isvalid(self, value):
        res=super(Date, self).isvalid(value)
        if (self.required and value) or value:
            if (len(value)!= 10) or (value[4]!="-" and value[7]!="-"):
                res.append("Date must have the format yyyy-mm-dd")
        return res

class DateTime(Widget):
    """
    >>> dt=DateTime("label")
    >>> dt.render("name","2011-01-01 10:10:10")
    u'<label for="name" class="table" >label</label><input name="name" value="2011-01-01 10:10:10" type="text"/>'
    >>> dt.isvalid("2011-01-01 10:10:10")
    []
    >>> dt.isvalid("2011-01-01 10:10")
    ['Date must have the format yyyy-mm-dd HH:MM:SS']
    >>> 

    """
    def __init__(self, *lw, **kw):
        super(DateTime, self).__init__(*lw, **kw)
        self.params['type']='text'
        self.base="input"
    def isvalid(self, value):
        res=super(DateTime, self).isvalid(value)
        if (self.required and value) or value:
            if (len(value)!= 19) or (value[4]!="-" and value[7]!="-" and value[13]!=":" and value[16]!=":"):
                res.append("Date must have the format yyyy-mm-dd HH:MM:SS")
        return res

class File(Widget):
    """
    >>> f=File("label")
    >>> f.render("name","")
    u'<label for="name" class="table" >label</label><input name="name" value="" type="file"/>'
    >>> f.render("name","value")
    u'<label for="name" class="table" >label</label><input name="name" value="value" type="file"/>'
    >>> 
    """
    def __init__(self, *lw, **kw):
        super(File, self).__init__(*lw, **kw)
        self.params['type']='file'
        self.base="input"


class jFile(File):
    """
    >>> f=jFile("label")
    >>> f.render("name","value")
    u'<label for="name" class="table" >label</label><input name="name" value="value" type="text"/><a id="em"><img src="/static/images/add.png" height="15"/></a> '
    >>> 
    This is a File object to use with jquery fileupload
    """
    def __init__(self, *lw, **kw):
        super(jFile, self).__init__(*lw, **kw)
        self.params['type']='text'
        self.base="input"
    def render(self, name, value):
        #the 2 following lines must aways be present
        self._manage_class()
        parameters=" ".join(['%s="%s"' % (k,v) for k,v in self.params.items()])
        res=self.getlabel(name)
        if not value:
            value=self.default
        res+="""<%s name="%s" value="%s" %s/><a id="em"><img src="/static/images/add.png" height="15"/></a> """ % (self.base, name, unicode(value), parameters)
        return res





if __name__=="__main__":
    import doctest
    doctest.testmod()

########NEW FILE########
__FILENAME__ = views
#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import mimetypes
import os
import time


class Staticfile:
    """ Generic class that you can use to dispatch static files
    You must use it like this:
      static=Staticfile("/rootpath/")
      evhttp.http_cb("/static/",static)
    NOTE: you must be consistent between /rootpath/ and /static/ concerning the ending "/"
    """
    def __init__(self, rootpath="", maxage=None):
        self.rootpath = rootpath
        self.maxage = maxage

    def __call__(self, environ, start_response):
        fpath = self.rootpath + environ['PATH_INFO']
        try:
            f = open(fpath, "rb")
        except:
            print "ERROR in Staticfile: file %s not existing" % (fpath)
            start_response('404 File not found', [])
            return []
        fmtime = os.path.getmtime(fpath)
        if environ.get('HTTP_IF_NONE_MATCH', 'NONE') != str(fmtime):
            headers = []
            if self.maxage:
                headers.append(('Cache-control', 'max-age=%s' % int(self.maxage + time.time())))
            #print "NEW", environ['fapws.uri']
            ftype = mimetypes.guess_type(fpath)[0]
            headers.append(('Content-Type', ftype))
            headers.append(('ETag', fmtime))
            headers.append(('Content-Length', os.path.getsize(fpath)))
            start_response('200 OK', headers)
            return f
        else:
            #print "SAME", environ['fapws.uri']
            start_response('304 Not Modified', [])
            return []

########NEW FILE########
__FILENAME__ = zip
#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
try:
    import cStringIO as StringIO
except:
    import StringIO
import gzip


class Gzip:
    #wsgi gzip middelware
    def __call__(self, f):
        def func(environ, start_response):
            content = f(environ, start_response)
            if 'gzip' in environ.get('HTTP_ACCEPT_ENCODING', ''):
                if type(content) is list:
                    content = "".join(content)
                else:
                    #this is a stream
                    content = content.read()
                sio = StringIO.StringIO()
                comp_file = gzip.GzipFile(mode='wb', compresslevel=6, fileobj=sio)
                comp_file.write(content)
                comp_file.close()
                start_response.add_header('Content-Encoding', 'gzip')
                res = sio.getvalue()
                start_response.add_header('Content-Length', len(res))
                return [res]
            else:
                return content
        return func

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python

import fapws._evwsgi as evwsgi
from fapws import base
import time
import sys
sys.setcheckinterval(100000) # since we don't use threads, internal checks are no more required

from fapws.contrib import views, cgiapp

def start():
    evwsgi.start("0.0.0.0", "8080")
    
    evwsgi.set_base_module(base)
    
    hello=cgiapp.CGIApplication("./test.cgi")
    evwsgi.wsgi_cb(("/hellocgi",hello))
    testphp=cgiapp.CGIApplication("/tmp/test.php")
    evwsgi.wsgi_cb(("/testphp",testphp))
    
        
    evwsgi.run()
    

if __name__=="__main__":
    start()

########NEW FILE########
__FILENAME__ = create
# -*- coding: utf-8 -*-
import sqlite3

con=sqlite3.connect('database.db')
c=con.cursor()
c.execute("""create table names(
          page text primary key,
          text text,
          display int)""")

temp_text="""Lorem ipsum dolor sit amet, consectetur adipiscing elit. Etiam sed ipsum purus, a tincidunt elit. Fusce id lectus et elit varius suscipit. Duis accumsan varius orci ac auctor. Quisque at feugiat mauris. Vestibulum velit lectus, lacinia ac cursus id, volutpat id justo. Quisque varius mauris eu mauris tempus venenatis. Vivamus pretium lacinia pretium. Praesent sed elit tortor. Phasellus eu turpis in metus commodo dapibus volutpat quis metus. Nulla egestas aliquam commodo. Etiam dictum consequat pharetra. Phasellus molestie pellentesque velit, in pretium velit interdum nec. Quisque egestas ipsum in nisi hendrerit dapibus. Vivamus aliquam enim ut diam laoreet sit amet tristique neque viverra. Cras felis dolor, tempor a tristique ac, lacinia ut neque."""

for i in range(1000):
   name="page%s" %i
   c.execute("insert into names values (?,?,?)", (name, temp_text,0))

con.commit()
con.close()

########NEW FILE########
__FILENAME__ = run
# -*- coding: utf-8 -*-
#You have to install mako
from mako.lookup import TemplateLookup
import fapws._evwsgi as evwsgi
from fapws import base
#you have to install one of my other code: simple sqlite data mapper
from ssdm import ssdm

i=0

lookup = TemplateLookup(directories=['templates',], filesystem_checks=True, module_directory='./modules')
#Thanks to assure the database will first be created (create.py)
con=ssdm.connect('database.db')
db=ssdm.scan_db(con)

import time

def commit(v):
    global count
    con.commit()
    time.sleep(0.1)
    #print "commit"


def names(environ, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    name=environ['PATH_INFO']
    rec=db.names.select("page='%s'" % name)
    template=lookup.get_template('names.html')
    if rec:
        rec=rec[0]
        ndisp=rec.display+1
        rec.set({'display':ndisp})
        rec.save()
        #We defere the commit and allow the combine
        #defer(<python call back>, <argumtent>, <combined them>)
        #The argument is unique and mandatory. 
        #If combined is True, then Fapws will add it in the queue if it's not yet present. 
        evwsgi.defer(commit, None, True)
        #commit(True)
        return [template.render(**{"name":rec.name,"text":rec.text,"display":ndisp})]
    else:
        return["Name not found"]

def qsize():
    print "defer queue size:",evwsgi.defer_queue_size()

evwsgi.start("0.0.0.0", "8080")
evwsgi.set_base_module(base)  
evwsgi.wsgi_cb(("/names/", names))
evwsgi.add_timer(2, qsize)
evwsgi.set_debug(0)    
evwsgi.run()
  
con.close()


########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-
import fapws._evwsgi as evwsgi
from fapws import base

import time

count=0

def toto(v):
    global count
    time.sleep(v)
    count+=1
    print "defer sleep %s, counter %s, %s" % (v,count,evwsgi.defer_queue_size())

def application(environ, start_response):
    response_headers = [('Content-type', 'text/plain')]
    start_response('200 OK', response_headers)
    print "before defer", time.time()
    evwsgi.defer(toto, 0.2, False)
    #evwsgi.defer(toto, 1, True)
    print "after defer", time.time()
    return ["hello word!!"]
    
if __name__=="__main__":

    evwsgi.start("0.0.0.0", "8080")
    evwsgi.set_base_module(base)
    evwsgi.wsgi_cb(("/", application))
    evwsgi.set_debug(0)
    evwsgi.run()

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python
from optparse import OptionParser
parser = OptionParser()
parser.set_defaults(
    port='8000',
    host='127.0.0.1',
    settings='settings',
)

parser.add_option('--port', dest='port')
parser.add_option('--host', dest='host')
parser.add_option('--settings', dest='settings')
parser.add_option('--pythonpath', dest='pythonpath')

options, args = parser.parse_args()

import os
os.environ['DJANGO_SETTINGS_MODULE'] = options.settings

import fapws._evwsgi as evwsgi
from fapws import base
import time
import sys
sys.setcheckinterval=100000 # since we don't use threads, internal checks are no more required

if options.pythonpath:
    sys.path.insert(1, options.pythonpath)

from fapws.contrib import django_handler, views
import django

print 'start on', (options.host, options.port)
evwsgi.start(options.host, options.port)
evwsgi.set_base_module(base)

def generic(environ, start_response):
    res=django_handler.handler(environ, start_response)
    return [res]

evwsgi.wsgi_cb(('',generic))
evwsgi.set_debug(0)
evwsgi.run()

########NEW FILE########
__FILENAME__ = hello_world
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fapws._evwsgi as evwsgi
from fapws import base

def start():
    evwsgi.start("0.0.0.0", "8080")
    evwsgi.set_base_module(base)
    
    def hello(environ, start_response):
        start_response('200 OK', [('Content-Type','text/html')])
        return ["hello world!!"]

    def iteration(environ, start_response):
        start_response('200 OK', [('Content-Type','text/plain')])
        yield "hello"
        yield " "
        yield "world!!"

    
    evwsgi.wsgi_cb(("/hello", hello))
    evwsgi.wsgi_cb(("/iterhello", iteration))

    evwsgi.set_debug(0)    
    evwsgi.run()
    

if __name__=="__main__":
    start()

########NEW FILE########
__FILENAME__ = hello_world
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fapws._evwsgi as evwsgi
from fapws import base

def start():
    evwsgi.start("/tmp/hello_unix.sock", "unix")
    evwsgi.set_base_module(base)
    
    def hello(environ, start_response):
        start_response('200 OK', [('Content-Type','text/html')])
        return ["hello world!!"]

    def iteration(environ, start_response):
        start_response('200 OK', [('Content-Type','text/plain')])
        yield "hello"
        yield " "
        yield "world!!"

    
    evwsgi.wsgi_cb(("/hello", hello))
    evwsgi.wsgi_cb(("/iterhello", iteration))

    evwsgi.set_debug(0)    
    evwsgi.run()
    

if __name__=="__main__":
    start()

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python

import fapws._evwsgi as evwsgi
from fapws import base
import time
import sys
from fapws.contrib import views, zip, log

import trace

base.supported_HTTP_command.append("TRACE")
def start():
    evwsgi.start("0.0.0.0", "8080")
    evwsgi.set_base_module(base)
    
    @trace.Trace()
    def hello(environ, start_response):
        start_response('200 OK', [('Content-Type','text/html')])
        return ["hello world!!"]

    evwsgi.wsgi_cb(("/hello", hello))

    evwsgi.set_debug(0)    
    evwsgi.run()
    

if __name__=="__main__":
    start()

########NEW FILE########
__FILENAME__ = trace

import time
import os.path
import sys

class Trace:
    def __init__(self):
        self.pp=4
    def __call__(self, f):
        def func(environ, start_response):
            res=f(environ, start_response)
            if environ['REQUEST_METHOD']=="TRACE":
                res=[]
                for elem in environ.keys():
                    res.append("%s: %s\r\n" % (elem, str(environ[elem])))
            return res

        return func
    

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-

import time


def application(environ, start_response):
    status = '404 Not Found'
    output = 'Pong!'

    response_headers = [('Content-type', 'text/plain')]
    #response_headers = [('Content-type', 'text/plain'),
    #                    ('Content-Length', str(len(output)))]

    start_response(status, response_headers)
    # return [output] # <- works OK
    yield output # <- does not convey 404 status to client
    time.sleep(5)
    yield "and"
    time.sleep(5)
    yield "Ping!!!"

if __name__=="__main__":
    import fapws._evwsgi as evwsgi
    from fapws import base

    evwsgi.start("0.0.0.0", "8080")
    evwsgi.set_base_module(base)
    evwsgi.wsgi_cb(("/", application))
    evwsgi.set_debug(1)
    evwsgi.run()

########NEW FILE########
__FILENAME__ = run
# -*- coding: utf-8 -*-

#This is just an example of proxy with Fapws. 
#Just start it and add his adress (host:port) to the proxy parameter of your browser
#I've test it successfully with FireFox-3.6
#WARNING: does not work with Youtueb videos


import fapws._evwsgi as evwsgi
import fapws
import fapws.base
import fapws.contrib
import fapws.contrib.views
import sys
import httplib


TIMEOUT=20


def get_header(head):
    headers={}
    lines=head.split("\n")
    lines.pop(0)
    for line in lines:
        line=line.strip()
        if line and ":" in line:
            key,val=line.split(":",1)
            headers[key.strip()]=val.strip()
    return headers



def generic(environ, start_response):
    if ":" in environ["HTTP_HOST"]:
        host,port=environ["HTTP_HOST"].split(":")
    else:
        host=environ["HTTP_HOST"]
        port=80
    con=httplib.HTTPConnection(host,port, timeout=TIMEOUT)
    print environ["fapws.uri"]
    path=environ["fapws.uri"][len(host)+len(environ["wsgi.url_scheme"])+3:]
    params=environ["wsgi.input"].read()
    headers=get_header(environ['fapws.raw_header'])
    #print "path             ", path
    #print "PARAMS           ", params
    #print "HEADERS          ", headers
    con.connect()
    con.request(environ["REQUEST_METHOD"],path, params, headers)
    res=con.getresponse()
    content=res.read()
    resp_headers={}
    blocked=False
    for key,val in res.getheaders():
        resp_headers[key.upper()]=val
    if resp_headers.get('CONTENT-TYPE','').lower().startswith("text/html") and res.status==200:
        if "sex" in content: #we just block the page if the bad word is in it. It will not block compressed pages
            blocked=True
    if blocked:
        content="Page blocked"
    else:
        #we send back headers has we have received them
        start_response.status_code=res.status
        start_response.status_reasons=res.reason
        for key, val in resp_headers.items():
            start_response.add_header(key,val)
    con.close()
    return [content]
    

def start():
    evwsgi.start("0.0.0.0", "8080")
    evwsgi.set_base_module(fapws.base)
    evwsgi.wsgi_cb(("",generic))
    evwsgi.set_debug(0)    
    print "libev ABI version:%i.%i" % evwsgi.libev_version()
    evwsgi.run()


if __name__=="__main__":
    start()


########NEW FILE########
__FILENAME__ = run
import os
import os.path
import paste.deploy
import fapws._evwsgi as evwsgi
from fapws import base
import sys
sys.setcheckinterval(100000) # since we don't use threads, internal checks are no more required

config_path = os.path.abspath(os.path.dirname(_args[0]))
path = '%s/%s' % (config_path, 'development.ini')
wsgi_app = paste.deploy.loadapp('config:%s' % path)

def start():
    evwsgi.start("0.0.0.0", "5000")
    evwsgi.set_base_module(base)
    
    def app(environ, start_response):
        environ['wsgi.multiprocess'] = False
        return wsgi_app(environ, start_response)

    evwsgi.wsgi_cb(('',app))
    evwsgi.run()

if __name__=="__main__": 
    start()

########NEW FILE########
__FILENAME__ = create
# -*- coding: utf-8 -*-
import sqlite3

con=sqlite3.connect('database.db')
c=con.cursor()
c.execute("""create table names(
          page text primary key,
          text text,
          display int)""")

temp_text="""Lorem ipsum dolor sit amet, consectetur adipiscing elit. Etiam sed ipsum purus, a tincidunt elit. Fusce id lectus et elit varius suscipit. Duis accumsan varius orci ac auctor. Quisque at feugiat mauris. Vestibulum velit lectus, lacinia ac cursus id, volutpat id justo. Quisque varius mauris eu mauris tempus venenatis. Vivamus pretium lacinia pretium. Praesent sed elit tortor. Phasellus eu turpis in metus commodo dapibus volutpat quis metus. Nulla egestas aliquam commodo. Etiam dictum consequat pharetra. Phasellus molestie pellentesque velit, in pretium velit interdum nec. Quisque egestas ipsum in nisi hendrerit dapibus. Vivamus aliquam enim ut diam laoreet sit amet tristique neque viverra. Cras felis dolor, tempor a tristique ac, lacinia ut neque."""

for i in range(1000):
   name="page%s" %i
   c.execute("insert into names values (?,?,?)", (name, temp_text,0))

con.commit()
con.close()

########NEW FILE########
__FILENAME__ = run
# -*- coding: utf-8 -*-
#You have to install mako
from mako.lookup import TemplateLookup
import fapws._evwsgi as evwsgi
from fapws import base
#you have to install one of my other code: simple sqlite data mapper
from ssdm import ssdm

i=0

lookup = TemplateLookup(directories=['templates',], filesystem_checks=True, module_directory='./modules')
#Thanks to assure the database will first be created (create.py)
con=ssdm.connect('database.db')
db=ssdm.scan_db(con)

evwsgi.start("0.0.0.0", "8080")
evwsgi.set_base_module(base)
    
def names(environ, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    name=environ['PATH_INFO']
    rec=db.names.select("page='%s'" % name)
    template=lookup.get_template('names.html')
    if rec:
        rec=rec[0]
        ndisp=rec.display+1
        rec.set({'display':ndisp})
        rec.save()
        #uncomment the following to force a commit for each request
        #db.names.commit()
        return [template.render(**{"name":rec.name,"text":rec.text,"display":ndisp})]
    else:
        return["Name not found"]

def commit():
    con.commit()
    print "commit"

    
#he following trigger a commit every 2 seconds    
evwsgi.add_timer(2,commit)
evwsgi.wsgi_cb(("/names/", names))
evwsgi.set_debug(0)    
evwsgi.run()
  
con.close()

########NEW FILE########
__FILENAME__ = run
#!/usr/bin/env python

import fapws._evwsgi as evwsgi
import fapws
import fapws.base
import fapws.contrib
import fapws.contrib.views
import sys
sys.setcheckinterval(100000) # since we don't use threads, internal checks are no more required

import views

def start():
    evwsgi.start("0.0.0.0", "8085")
    
    evwsgi.set_base_module(fapws.base)
    
    #def generic(environ, start_response):
    #    return ["page not found"]
    
    def index(environ, start_response):
        print "GET:", environ['fapws.uri']
        return views.index(environ, start_response)
    
    def display(environ, start_response):
        print "GET:", environ['fapws.uri']
        return views.display(environ, start_response)
    def edit(environ, start_response):
        #print environ['fapws.params']
        print "GET:", environ['fapws.uri']
        r=views.Edit()
        return r(environ, start_response)
    favicon=fapws.contrib.views.Staticfile("static/img/favicon.ico")
    def mystatic(environ, start_response):
        print "GET:", environ['fapws.uri']
        s=fapws.contrib.views.Staticfile("static/")
        return s(environ, start_response)
    evwsgi.wsgi_cb(("/display/",display))
    evwsgi.wsgi_cb(("/edit", edit))
    evwsgi.wsgi_cb(("/new", edit))
    evwsgi.wsgi_cb(("/static/",mystatic))
    #evwsgi.wsgi_cb(('/favicon.ico',favicon)),

    evwsgi.wsgi_cb(("/", index))
    #evhttp.gen_http_cb(generic)
    evwsgi.set_debug(0)    
    print "libev ABI version:%i.%i" % evwsgi.libev_version()
    evwsgi.run()
    

if __name__=="__main__":
    start()

########NEW FILE########
__FILENAME__ = views
import os.path
import string
import time
from cgi import parse_qs
import urllib
import httplib

from fapws.contrib.headers import redirect

repository = "repository"
menu = """<a href="/index"><img border="0" src="/static/img/house.png" title="Back to home page"/></a>"""
def get_status(code):
    return "%s %s" % (code, httplib.responses[code])



def display(environ, start_response):
    page = os.path.normpath(environ['PATH_INFO'].replace('..',''))
    if page[0] not in string.letters:
        errormsg = "Error: the asked page does not exist"
        #put message in a session
        print errormsg
        return redirect(start_response, '/')
    filepage = os.path.join(repository,page)
    if not os.path.isfile(filepage):
        return redirect(start_response, '/edit?page=%s' % page)
    content = open(filepage).read()
    mnu = menu + """, <a href="/edit?page=%s"><img border="0" src="/static/img/application_edit.png"title="Edit this page"/></a>""" % page
    tmpl = string.Template(open('template/display.html').read()).safe_substitute({'content':content,'page':page,'menu':mnu})
    start_response(get_status(200), [('Content-Type','text/html')])
    return [tmpl]

class Edit:
    def __call__(self, environ, start_response):
        self.start_response = start_response
        self.environ = environ
        if environ['REQUEST_METHOD'] == "POST":
            params=environ['fapws.params']
            page = params.get('page', [''])[0]
            content = params.get('content', [''])[0]
            return self.POST(page,content)
        else:
            page = environ['fapws.params'].get('page', [''])[0]
            return self.GET(page)
    def POST(self, page="", content=""):
        if page.strip() == "":
            msg = "ERROR!! Page cannot be empty"
            print "ERROR PAGE empty"
            return self.GET(page,msg)
        else:
            if content.strip() == "":
                if os.path.isfile(os.path.join(repository, page)):
                    os.unlink(os.path.join(repository,page))
                return redirect(self.start_response, "/")
            else:
                try:
                    f = open(os.path.join(repository,page),"w").write(content)
                except:
                    msg = "Error, wrong page name"
                    return self.GET(page,msg)
                return redirect(self.start_response, "/display/%s" % page)
    def GET(self, page="",msg=""):
        mnu = menu
        if page:
            mnu += """, <a href="/display/%s"><img border="0" src="/static/img/cancel.png" title="Cancel the editing" /></a>""" % page
        content = ""
        if page and os.path.isfile(os.path.join(repository,page)):
            content = open(os.path.join(repository,page)).read()
        else:
            msg = "This page does not exist, do you want to create it?"
        tmpl = string.Template(open('template/edit.html').read()).safe_substitute({'menu':mnu,'content':content,'page':page,'msg':msg})
        self.start_response(get_status(200), [('Content-Type','text/html')])    
        return [tmpl]

def index(environ, start_response):
    mnu = menu+ """, <a href="/new"><img border="0" src="/static/img/add.png" title="Add a new page"/></a>"""
    elems = ""
    for e in os.listdir(repository):
        if os.path.isfile(os.path.join(repository,e)):
            elems += """<li><a href="/display/%s">%s</a></li>""" % (e,e)
    tmpl = string.Template(open('template/index.html').read()).safe_substitute({'elems':elems,'menu':mnu})
    start_response(get_status(200), [('Content-Type','text/html')])
    return [tmpl]


########NEW FILE########
__FILENAME__ = slow_client
"""The sample slow + fast client.

The client can work fine if server is localhost.  Otherwise time_request
client usually takes the same time as long_request.
"""

import sys
import socket
import time
import threading

if len(sys.argv) > 2:
    print "usage: %s [host[:port]]" % sys.argv[0]
    sys.exit(1)

hostname = 'localhost'
port = 8080
if len(sys.argv) == 2:
    if ':' in sys.argv[1]:
        hostname, port = sys.argv[1].split(':')
        port = int(port)
    else:
        hostname = sys.argv[1]
headers = '\r\nHost: %s\r\n\r\n' % hostname

def timed(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            print '%s took %.2f sec' % (repr(func), time.time() - start)
    return wrapper

lock = threading.Lock()
@timed
def long_request():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))
    s.send('GET /file HTTP/1.0' + headers)
    for i in range(1):
        s.recv(80)
        time.sleep(1)
    lock.release()
    print 'release'
    for i in range(10):
        s.recv(80)
        time.sleep(1)
    s.close()

@timed
def time_request():
    lock.acquire()
    print 'acquire'
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((hostname, port))
    s.send('GET /time HTTP/1.0' + headers)
    s.recv(900)
    s.close()

lock.acquire()
fl = threading.Thread(target=long_request)
tl = threading.Thread(target=time_request)
fl.start()
tl.start()
tl.join()
fl.join()

########NEW FILE########
__FILENAME__ = test
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from time import time
import fapws._evwsgi as evwsgi
from fapws import base

def start():
    evwsgi.start("0.0.0.0", "8080")
    evwsgi.set_base_module(base)

    def return_file(environ, start_response):
        start_response('200 OK', [('Content-Type','text/html')])
        return open('big-file')

    def return_tuple(environ, start_response):
        start_response('200 OK', [('Content-Type','text/plain')])
        return ('Hello,', " it's me ", 'Bob!')

    def return_rfc_time(environ, start_response):
        start_response('200 OK', [('Content-Type','text/plain')])
        return [evwsgi.rfc1123_date(time())]

    evwsgi.wsgi_cb(("/file", return_file))
    evwsgi.wsgi_cb(("/tuple", return_tuple))
    evwsgi.wsgi_cb(("/time", return_rfc_time))

    evwsgi.run()

if __name__=="__main__":
    try:
        open('big-file')
    except IOError:
        open('big-file', 'w').write('\n'.join('x'*1024 for i in range(1024)))
    start()

########NEW FILE########
__FILENAME__ = mybase
# -*- coding: utf-8 -*-

#    Copyright (C) 2009 William.os4y@gmail.com
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, version 2 of the License.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
import datetime
from Cookie import SimpleCookie, CookieError
try:
    import cStringIO as StringIO
except ImportError:
    import StringIO
import sys
import string
import traceback
import time
import httplib

from fapws import config
from fapws.contrib import multipart


def get_status(code):
    return "%s %s" % (code, httplib.responses[code])


class Environ(dict):
    def __init__(self, *arg, **kw):
        self['wsgi.version'] = (1, 0)
        self['wsgi.errors'] = StringIO.StringIO()
        self['wsgi.input'] = multipart.MultipartFormData("/tmp/")
        self['wsgi.multithread'] = False
        self['wsgi.multiprocess'] = True
        self['wsgi.run_once'] = False
        self['fapws.params'] = {}
    #here after some entry point before the Environ update

    def update_headers(self, data):
        dict.update(self, data)

    def update_uri(self, data):
        dict.update(self, data)

    def update_from_request(self, data):
        dict.update(self, data)


class Start_response:
    def __init__(self):
        self.status_code = "200"
        self.status_reasons = "OK"
        self.response_headers = {}
        self.exc_info = None
        self.cookies = None
        # NEW -- sent records whether or not the headers have been send to the
        # client
        self.sent = False

    def __call__(self, status, response_headers, exc_info=None):
        self.status_code, self.status_reasons = status.split(" ", 1)
        self.status_code = str(self.status_code)
        for key, val in response_headers:
            #if type(key)!=type(""):
            key = str(key)
            #if type(val)!=type(""):
            val = str(val)
            self.response_headers[key] = val
        self.exc_info = exc_info  # TODO: to implement

    def add_header(self, key, val):
        key = str(key)
        val = str(val)
        self.response_headers[key] = val

    def set_cookie(self, key, value='', max_age=None, expires=None, path='/', domain=None, secure=None):
        if not self.cookies:
            self.cookies = SimpleCookie()
        self.cookies[key] = value
        if max_age:
            self.cookies[key]['max-age'] = max_age
        if expires:
            if isinstance(expires, str):
                self.cookies[key]['expires'] = expires
            elif isinstance(expires, datetime.datetime):
                expires = evwsgi.rfc1123_date(time.mktime(expires.timetuple()))
            else:
                raise CookieError('expires must be a datetime object or a string')
            self.cookies[key]['expires'] = expires
        if path:
            self.cookies[key]['path'] = path
        if domain:
            self.cookies[key]['domain'] = domain
        if secure:
            self.cookies[key]['secure'] = secure

    def delete_cookie(self, key):
        if self.cookies:
            self.cookies[key] = ''
        self.cookies[key]['max-age'] = "0"

    def __str__(self):
        res = "HTTP/1.0 %s %s\r\n" % (self.status_code, self.status_reasons)
        for key, val in self.response_headers.items():
            res += '%s: %s\r\n' % (key, val)
        if self.cookies:
            res += str(self.cookies) + "\r\n"
        res += "\r\n"
        return res


def redirectStdErr():
    """
    This methods allow use to redirect messages sent to stderr into a string
    Mandatory methods of the sys.stderr object are:
        write: to insert data
        getvalue; to retreive all data
    """
    sys.stderr = StringIO.StringIO()

supported_HTTP_command = ["GET", "POST", "HEAD", "OPTIONS"]


def split_len(seq, length):
    return [seq[i:i + length] for i in range(0, len(seq), length)]


def parse_cookies(environ):
    #transform the cookie environment into a SimpleCokkie object
    line = environ.get('HTTP_COOKIE', None)
    if line:
        cook = SimpleCookie()
        cook.load(line)
        return cook
    else:
        return None

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import fapws._evwsgi as evwsgi
from fapws import base
import time
import sys
from fapws.contrib import views, zip, log
import mybase

if len(sys.argv)>1 and sys.argv[1]=="socket":
  import socket
  socket_server = True
else:
  socket_server = False


def env(environ, start_response):
    print environ
    start_response('200 OK', [('Content-Type','text/html')])
    res=[]
    for key,val in environ.items():
        val=str(val).replace('\r','\\r')
        val=val.replace('\n','\\n')
        res.append("%s:%s\n" % (key,val))
    return res

def hello(environ, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    return ["Hello"," world!!"]

class helloclass(object):
    def __init__(self, txt=None):
        self.content = ["Hello from class %s" % txt]
    def __call__(self, environ, start_response):
        start_response('200 OK', [('Content-Type','text/html')])
        return self.content

def iteration(environ, start_response):
    start_response('200 OK', [('Content-Type','text/plain')])
    yield "Hello"
    yield " "
    yield "world!!"

def tuplehello(environ, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    return ("Hello"," world!!")

@log.Log()
def staticlong(environ, start_response):
    try:
        f=open("long.txt", "rb")
    except:
        f=["Page not found"]
    start_response('200 OK', [('Content-Type','text/html')])
    return f

def embedlong(environ, start_response):
    try:
        c=open("long.txt", "rb").read()
    except:
        c=["Page not found"]
    start_response('200 OK', [('Content-Type','text/html')])
    return base.split_len(c,32768)

def staticshort(environ, start_response):
    f=open("short.txt", "rb")
    start_response('200 OK', [('Content-Type','text/html')])
    return f

def testpost(environ, start_response):
    print environ
    if "multipart/form-data" in environ['HTTP_CONTENT_TYPE']:
        res=environ["wsgi.input"].getvalue()
    elif "application/x-www-form-urlencoded" in environ['HTTP_CONTENT_TYPE']:
        res=environ["fapws.params"]
    else:
        res={}
    return ["OK. params are:%s" % (res)]

@zip.Gzip()    
def staticlongzipped(environ, start_response):
    try:
        f=open("long.txt", "rb")
    except:
        f=["Page not found"]
    start_response('200 OK', [('Content-Type','text/html')])
    return f

def badscript(environ, start_response):
    start_reponse('200 OK', [('Content-Type','text/html')])
    return ["Hello world!!"]

def returnnone(environ, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    return None

def returnnull(environ, start_response):
    start_response('200 OK', [('Content-Type','text/html')])

def returniternull(environ, start_response):
    start_response('200 OK', [('Content-Type','text/html')])
    yield "start"
    yield None
    yield "tt"




def start():
    if socket_server:
        evwsgi.start("\0/org/fapws3/server", "unix")
    else:
        evwsgi.start("0.0.0.0", "8080")
    evwsgi.set_base_module(mybase)
    
 
    evwsgi.wsgi_cb(("/env", env))
    evwsgi.wsgi_cb(("/helloclass", helloclass("!!!")))
    evwsgi.wsgi_cb(("/hello", hello))
    evwsgi.wsgi_cb(("/tuplehello", tuplehello))
    evwsgi.wsgi_cb(("/iterhello", iteration))
    evwsgi.wsgi_cb(("/longzipped", staticlongzipped))
    evwsgi.wsgi_cb(("/long", staticlong))
    evwsgi.wsgi_cb(("/elong", embedlong))
    evwsgi.wsgi_cb(("/short", staticshort))
    staticform=views.Staticfile("test.html")
    evwsgi.wsgi_cb(("/staticform", staticform))
    evwsgi.wsgi_cb(("/testpost", testpost))
    evwsgi.wsgi_cb(("/badscript", badscript))
    evwsgi.wsgi_cb(("/returnnone", returnnone))
    evwsgi.wsgi_cb(("/returnnull", returnnull))
    evwsgi.wsgi_cb(("/returniternull", returniternull))

    evwsgi.set_debug(0)    
    evwsgi.run()
    

if __name__=="__main__":
    start()

########NEW FILE########
__FILENAME__ = test
# -*- coding: utf-8 -*-
import httplib
import urllib
import os.path

import os
import sys

import _raw_send

if len(sys.argv)>1 and sys.argv[1]=="socket":
  import socket
  socket_server = True
else:
  socket_server = False

successes=0
failures=0


def test(search, test, data):
    global successes, failures
    if not test:
        print "TEST PROBLEM"
        failures+=1
    elif search not in data:
        print """RESPONSE PROBLEM, we don't find "%s" """ % search
        print data
        failures+=1
    else:
        print "SUCCESS"
        successes+=1

class UHTTPConnection(httplib.HTTPConnection):
    """Subclass of Python library HTTPConnection that
       uses a unix-domain socket.
       borrowed from http://7bits.nl/blog/2007/08/15/http-on-unix-sockets-with-python
    """
 
    def __init__(self, path):
        httplib.HTTPConnection.__init__(self, 'localhost')
        self.path = path
 
    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.path)
        self.sock = sock

if socket_server:
    con = UHTTPConnection("\0/org/fapws3/server")
else:
    con = httplib.HTTPConnection("127.0.0.1:8080")
    
if 1:
  print "=== Normal get ==="
  con.request("GET", "/env/param?key=val")
  response=con.getresponse()
  content=response.read()
  test("SCRIPT_NAME:/env",response.status==200,content) 
  test("PATH_INFO:/param",response.status==200,content)
  test("REQUEST_METHOD:GET",response.status==200,content) 
  test("SERVER_PROTOCOL:HTTP/1.1",response.status==200,content) 
  test("wsgi.url_scheme:HTTP",response.status==200,content) 
  test("QUERY_STRING:key=val",response.status==200,content) 
  test("fapws.params:{'key': ['val']}",response.status==200,content) 

  print "=== URL not found ==="
  con.request("GET", "/wrongpage")
  response=con.getresponse()
  content=response.read()
  test("Page not found", response.status==500, content)

  print "=== Get Hello world ==="
  con.request("GET", "/hello")
  response=con.getresponse()
  content=response.read()
  test("Hello world!!", response.status==200, content)

  print "=== Get Iter Hello world ==="
  con.request("GET", "/iterhello")
  response=con.getresponse()
  content=response.read()
  test("Hello world!!", response.status==200, content)

  print "=== Get tuple Hello world ==="
  con.request("GET", "/tuplehello")
  response=con.getresponse()
  content=response.read()
  test("Hello world!!", response.status==200, content)

  print "=== Get Class Hello world ==="
  con.request("GET", "/helloclass")
  response=con.getresponse()
  content=response.read()
  test("Hello from class !!!", response.status==200, content)

  print "=== Get long file ==="
  con.request("GET", "/long")
  response=con.getresponse()
  content=response.read()
  test("azerty", len(content)==os.path.getsize("long.txt"), content)

  print "=== Get long file zipped ==="
  headers={"Accept-Encoding":"gzip"}
  con.request("GET", "/longzipped", "", headers)
  response=con.getresponse()
  content=response.read()
  header=response.getheader('content-encoding')
  test("azerty", header=="gzip", "azerty")

  print "=== Get split long file ==="
  con.request("GET", "/elong")
  response=con.getresponse()
  content=response.read()
  test("azerty", len(content)==os.path.getsize("long.txt"), content)

  print "=== Get cached file ==="
  headers={"if-None-Match":str(os.path.getmtime('test.html'))}
  con.request("GET", "/staticform", "", headers)
  response=con.getresponse()
  test("304", response.status==304, "304")

  print "=== Post without length ==="
  params = urllib.urlencode({'var1': 'value1', 'var2': 'value2'})
  con.request("POST", "/testpost")
  response=con.getresponse()
  content=response.read()
  test("Length Required", response.status==411, content)

  print "=== Post with length ==="
  params = urllib.urlencode({'var1': 'value1', 'var2': 'value2'})
  headers = {"Content-type": "application/x-www-form-urlencoded", 
            "Accept": "text/plain"}
  con.request("POST", "/testpost", params, headers) #in this case httplib send automatically the content-length header
  response=con.getresponse()
  content=response.read()
  test("OK. params are:{'var1': ['value1'], 'var2': ['value2']}", response.status==200, content)

  if socket_server == True:
    print "=== Post multipart is skipped on Socket server ==="
  else:
    print "=== Post with multipart ==="
    try:
      os.remove('/tmp/short.txt')
    except:
      pass
    data = """POST /testpost HTTP/1.1\r
Host: 127.0.0.1:8080\r
Accept: */*\r
Content-Length: 333\r
Content-Type: multipart/form-data; boundary=----------------------------6b72468f07eb\r
\r
------------------------------6b72468f07eb\r
Content-Disposition: form-data; name="field1"\r
\r
this is a test using httppost & stuff\r
------------------------------6b72468f07eb\r
Content-Disposition: form-data; name="field2"; filename="short.txt"\r
Content-Type: text/plain\r
\r
Hello world
\r
------------------------------6b72468f07eb--\r\n"""  
    response = _raw_send.send(data)
    print "response", response
    test("OK. params are:{'field2': ['/tmp/short.txt', {'Content-Type': 'text/plain', 'size': 14L}], 'field1': ['this is a test using httppost & stuff']}", 1==1, response)

  print "=== Options ==="
  con.request("OPTIONS", "/")
  response=con.getresponse()
  content=response.read()
  resp_allow=response.getheader('allow', None)
  test("Options", response.status==200 and resp_allow[:3]=='GET', "Options")

  print "=== Bad header: 2 semi-column ==="
  headers={'Badkey:': "Value"}
  con.request("GET", "/env", "", headers)
  response=con.getresponse()
  content=response.read()
  test("HTTP_BADKEY:: Value", response.status==200 , content)

  print "=== Bad header: key with CR  ==="
  headers={'Bad\nkey': "Value"}
  con.request("GET", "/env", "", headers)
  response=con.getresponse()
  content=response.read()
  test("KEY:Value", response.status==200 , content)

  print "=== Bad header: value with CR  ==="
  headers={'Badkey': "Val\nue"}
  con.request("GET", "/env", "", headers)
  response=con.getresponse()
  content=response.read()
  test("HTTP_BADKEY:Val", response.status==200 , content)

  print "=== Bad header: value with CRLF  ==="
  headers={'Badkey': "Val\r\nue"}
  con.request("GET", "/env", "", headers)
  response=con.getresponse()
  content=response.read()
  test("HTTP_BADKEY:Val", response.status==200 , content)

  print "=== Bad command  ==="
  con.request("GIT", "/env")
  response=con.getresponse()
  content=response.read()
  test("Not Implemented", response.status==501 , content)

  print "=== Bad first line  ==="
  con.request("GET", "/env\r\n")
  response=con.getresponse()
  content=response.read()
  test("SCRIPT_NAME:/env", response.status==200 , content)

  print "=== Bad script  ==="
  con.request("GET", "/badscript")
  response=con.getresponse()
  content=response.read()
  test("Traceback", response.status==500 , content)

  print "=== Bad command ==="
  con.request("!çàù","")
  response=con.getresponse()
  content=response.read()
  test("Not Implemented", response.status==501 , content)
  
  print("=== Very long GET ===")
  url = "/env?var=" + "to"*2056
  con.request("GET", url)
  response=con.getresponse()
  content=response.read()
  test("tototototo", response.status==200 , content)

  print("=== Return Null ===")
  con.request("GET", "/returnnull")
  response=con.getresponse()
  content=response.read()
  test("", response.status==200 , content)

  print("=== Return None ===")
  con.request("GET", "/returnnone")
  response=con.getresponse()
  content=response.read()
  test("", response.status==200 , content)

  print("=== Return Iter None ===")
  con.request("GET", "/returniternull")
  response=con.getresponse()
  content=response.read()
  test("start", response.status==200 , content)

print "=================="
print "TOTAL successes:", successes
print "TOTAL failures:", failures
print 
print 



########NEW FILE########
__FILENAME__ = testforms
from fapws.contrib.siforms import widgets, forms 

class myform(forms.Form):
    __metaclass__ = forms.FormFactory
    name = widgets.Text("First name", required=True)
    personid = widgets.Integer("Person ID", required=True)
    personcode = widgets.Dropdown("Person's code")
    _add_html_form=['name', 'personid', 'personcode']
    _edit_html_form=['name', 'personid', 'personcode']
    _html_list=['name','personid', 'personcode']



m=myform(id="test", class_="test")
m.personcode.options=[(0,"-----"),(1,"master"),(2,"intermediate")]
print m.render_form(m._add_html_form)
print "="*15
m.validate({'personcode':1,'personid':4,'name':'rrr'},m._add_html_form)
print m.render_form(m._add_html_form)


import doctest 
print doctest.testmod(widgets, verbose=True)







    
            
        
         

########NEW FILE########
__FILENAME__ = _raw_send
import socket
import time

def send(post_data, port=8080, host='127.0.0.1'):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.send(post_data)
    time.sleep(0.1) # we just let the sercer having time to build the answer
    res = s.recv(1024)
    s.close()
    return res


if __name__ ==  "__main__":
    data = """POST /testpost HTTP/1.1\r
Host: 127.0.0.1:8080\r
Accept: */*\r
Content-Length: 333\r
Content-Type: multipart/form-data; boundary=----------------------------6b72468f07eb\r
\r
------------------------------6b72468f07eb\r
Content-Disposition: form-data; name="field1"\r
\r
this is a test using httppost & stuff\r
------------------------------6b72468f07eb\r
Content-Disposition: form-data; name="field2"; filename="short.txt"\r
Content-Type: text/plain\r
\r
Hello world
\r
------------------------------6b72468f07eb--\r\n"""
    res = send(data)
    print(res)

########NEW FILE########
