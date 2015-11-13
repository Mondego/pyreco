__FILENAME__ = main
#!/usr/bin/env python
#
# Copyright 2008 Adam Stiles
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy 
# of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required 
# by applicable law or agreed to in writing, software distributed under the 
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS 
# OF ANY KIND, either express or implied. See the License for the specific 
# language governing permissions and limitations under the License.
#

"""A url-shortener built on Google App Engine."""
__author__ = 'Adam Stiles'

""" 
All Urly records in the database have an id and an href. We base62 that
integer id to create a short code that represents that Urly.

Format options are: json, xml, html, and txt

/{code}                     Redirect user to urly with this code
/{code}(.format)            Show user formatted urly with this code
/new(.format)?href={href}   Create a new urly with this href or
                            return existing one if it already exists
                            Note special handling for 'new' code
                            when we have a href GET parameter 'cause
                            'new' by itself looks like a code
"""
import wsgiref.handlers
import re, os, logging
from google.appengine.ext import webapp
from google.appengine.ext import db
from urly import Urly
from view import MainView

class MainHandler(webapp.RequestHandler):
    """All non-static requests go through this handler.
    The code and format parameters are pre-populated by
    our routing regex... see main() below.
    """
    def get(self, code, format):
        if (code is None):
            MainView.render(self, 200, None, format)
            return
        
        href = self.request.get('href').strip().encode('utf-8')
        title = self.request.get('title').strip().encode('utf-8')
        if (code == 'new') and (href is not None):
            try:
                u = Urly.find_or_create_by_href(href)
                if u is not None:
                    MainView.render(self, 200, u, format, href, title)
                else:
                    logging.error("Error creating urly by href: %s", str(href))
                    MainView.render(self, 400, None, format, href)
            except db.BadValueError:
                # href parameter is bad
                MainView.render(self, 400, None, format, href)
        else:
            u = Urly.find_by_code(str(code))
            if u is not None:
                MainView.render(self, 200, u, format)
            else:
                MainView.render(self, 404, None, format)
    
    def head(self, code, format):
        if (code is None):
            self.error(400)
        else:
            u = Urly.find_by_code(str(code))
            if u is not None:
                self.redirect(u.href)
            else:
                self.error(404)

def main():
    application = webapp.WSGIApplication([
        ('/([a-zA-Z0-9]{1,6})?(.xml|.json|.html|.txt)?', MainHandler)
    ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = urly
# Copyright 2008 Adam Stiles
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy 
# of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required 
# by applicable law or agreed to in writing, software distributed under the 
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS 
# OF ANY KIND, either express or implied. See the License for the specific 
# language governing permissions and limitations under the License.

from google.appengine.ext import db
from google.appengine.api import memcache
import cgi
import logging

class Urly(db.Model):
    """Our one-and-only model"""  
    href = db.LinkProperty(required=True)
    created_at = db.DateTimeProperty(auto_now_add=True)

    KEY_BASE = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    BASE = 62

    def code(self):
        """Return our code, our base-62 encoded id"""
        if not self.is_saved():
            return None
        nid = self.key().id()
        s = []
        while nid:
            nid, c = divmod(nid, Urly.BASE)
            s.append(Urly.KEY_BASE[c])
        s.reverse()
        return "".join(s)
        
    def to_json(self):
        """JSON is so simple that we won't worry about a template at this point"""
        return "{\"code\":\"%s\",\"href\":\"%s\"}\n" % (self.code(), self.href);
    
    def to_xml(self):
        """Like JSON, XML is simple enough that we won't template now"""
        msg = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        msg += "<urly code=\"%s\" href=\"%s\" />\n" % (self.code(), cgi.escape(self.href))
        return msg

    def to_text(self):
        return "http://ur.ly/%s" % self.code()

    def save_in_cache(self):
        """We don't really care if this fails"""
        memcache.set(self.code(), self)

    @staticmethod
    def find_or_create_by_href(href):
        query = db.Query(Urly)
        query.filter('href =', href)
        u = query.get()
        if not u:
            u = Urly(href=href)
            u.put()
            u.save_in_cache()
        return u

    @staticmethod
    def code_to_id(code):
        aid = 0L
        for c in code:
            aid *= Urly.BASE 
            aid += Urly.KEY_BASE.index(c)
        return aid
    
    @staticmethod
    def find_by_code(code):
        try:
            u = memcache.get(code)
        except:
            # http://code.google.com/p/googleappengine/issues/detail?id=417
            logging.error("Urly.find_by_code() memcached error")
            u = None
        
        if u is not None:
            logging.info("Urly.find_by_code() cache HIT: %s", str(code))
            return u        

        logging.info("Urly.find_by_code() cache MISS: %s", str(code))
        aid = Urly.code_to_id(code)
        try:
            u = Urly.get_by_id(int(aid))
            if u is not None:
                u.save_in_cache()
            return u
        except db.BadValueError:
            return None
########NEW FILE########
__FILENAME__ = view
# Copyright 2008 Adam Stiles
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy 
# of the License at http://www.apache.org/licenses/LICENSE-2.0 Unless required 
# by applicable law or agreed to in writing, software distributed under the 
# License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS 
# OF ANY KIND, either express or implied. See the License for the specific 
# language governing permissions and limitations under the License.

import os
from google.appengine.ext.webapp import template

class MainView():
    """Helper method for our one-and-only template. All display goes through here"""
    @staticmethod
    def render(handler, status, urly, format, href=None, title=None):
        """Lovin my delphi-like inner functions"""
        def render_raw(handler, content_type, body):
            handler.response.headers["Content-Type"] = content_type
            handler.response.out.write(body)

        def render_main(handler, values=None):
            path = os.path.join(os.path.dirname(__file__), 'main.html')
            handler.response.out.write(template.render(path, values))

        """ We never have an error if we have an urly to show """
        if (urly is not None):
            if (format is None):
                handler.redirect(urly.href)
            elif (format == '.json'):
                render_raw(handler, "application/json", urly.to_json())
            elif (format == '.xml'):
                render_raw(handler, "application/xml", urly.to_xml())
            elif (format == '.txt'):
                render_raw(handler, "text/plain", urly.to_text())
            else:
                render_main(handler, { 'urly': urly, 'title': title })
        elif (status == 400):
            handler.error(status)
            if (format != '.json') and (format != '.xml'): 
                vals = { 'error_href': True, 'default_href': href }
                render_main(handler, vals)
        elif (status == 404):
            handler.error(404)
            if (format != '.json') and (format != '.xml'): 
                vals = { 'error_404': True }
                render_main(handler, vals)
        else:
            render_main(handler)

########NEW FILE########
