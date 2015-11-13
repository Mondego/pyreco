__FILENAME__ = demo-cherrypy
#!/usr/local/bin/python
# -*- coding: utf-8 -*-
#############################################
## (C)opyright by Dirk Holtwick, 2008      ##
## All rights reserved                     ##
#############################################

import cherrypy as cp
import sx.pisa3 as pisa
import cStringIO as StringIO

try:
    import kid
except:
    kid = None

class PDFDemo(object):

    """
    Simple demo showing a form where you can enter some HTML code.
    After sending PISA is used to convert HTML to PDF and publish
    it directly.
    """

    @cp.expose
    def index(self):
        if kid:
            return file("demo-cherrypy.html","r").read()

        return """
        <html><body>
            Please enter some HTML code:
            <form action="download" method="post" enctype="multipart/form-data">
            <textarea name="data">Hello <strong>World</strong></textarea>
            <br />
            <input type="submit" value="Convert HTML to PDF" />
            </form>
        </body></html>
        """

    @cp.expose
    def download(self, data):

        if kid:
            data = """<?xml version="1.0" encoding="utf-8"?>
                <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
                  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
                <html xmlns="http://www.w3.org/1999/xhtml"
                      xmlns:py="http://purl.org/kid/ns#">
                  <head>
                    <title>PDF Demo</title>
                  </head>
                  <body>%s</body>
                </html>""" % data
            test = kid.Template(source=data)
            data = test.serialize(output='xhtml')

        result = StringIO.StringIO()
        pdf = pisa.CreatePDF(
            StringIO.StringIO(data),
            result
            )
        if pdf.err:
            return "We had some errors in HTML"
        else:
            cp.response.headers["content-type"] = "application/pdf"
            return result.getvalue()

cp.tree.mount(PDFDemo())

if __name__ == '__main__':
    import os.path
    cp.config.update(os.path.join(__file__.replace(".py", ".conf")))
    cp.server.quickstart()
    cp.engine.start()

########NEW FILE########
__FILENAME__ = django-admin
#!/usr/bin/env python
from django.core import management

if __name__ == "__main__":
    management.execute_from_command_line()

########NEW FILE########
__FILENAME__ = ezpdf
#! /usr/bin/python
# -*- encoding: utf-8 -*-

from django.template.loader import get_template
from django.template import Context
from django.http import HttpResponse
import cStringIO as StringIO
from sx.pisa3 import pisaDocument
import cgi

def render_to_pdf(template_src, context_dict):
    '''
    Renderiza el template con el contexto.
    Envía al cliente la Respuesta HTTP del contenido PDF para
    el template renderizado.
    '''
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context)
    result = StringIO.StringIO()
    pdf = pisaDocument(StringIO.StringIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), mimetype='application/pdf')
    return HttpResponse('We had some errors<pre>%s</pre>' % cgi.escape(html))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager

# Patch for Python 2.5

try:
    import sitecustomize
except:
    pass

# Set logging

import logging

try:
    logging.basicConfig(
        level=logging.WARN,
        format="%(levelname)s [%(name)s] %(pathname)s line %(lineno)d in %(funcName)s: %(message)s")
except:
    logging.basicConfig()

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for the example project.

import os
DEBUG = True
TEMPLATE_DEBUG = DEBUG
ROOT_URLCONF = 'djangoproject.urls'
TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
    (r'^$', 'djangoproject.views.index'),
    (r'^download', 'djangoproject.views.download'),
    (r'^ezpdf_sample', 'djangoproject.views.ezpdf_sample'),

)

########NEW FILE########
__FILENAME__ = views
#! /usr/bin/python
# -*- encoding: utf-8 -*-

from django import http
from django.shortcuts import render_to_response
from django.template.loader import get_template
from django.template import Context
import xhtml2pdf.pisa as pisa
import cStringIO as StringIO
import cgi

def index(request):
    return http.HttpResponse("""
        <html><body>
            <h1>Example 1</h1>
            Please enter some HTML code:
            <form action="/download/" method="post" enctype="multipart/form-data">
            <textarea name="data">Hello <strong>World</strong></textarea>
            <br />
            <input type="submit" value="Convert HTML to PDF" />
            </form>
            <hr>
            <h1>Example 2</h1>
            <p><a href="ezpdf_sample">Example with template</a>
        </body></html>
        """)

def download(request):
    if request.POST:
        result = StringIO.StringIO()
        pdf = pisa.CreatePDF(
            StringIO.StringIO(request.POST["data"]),
            result
            )

        if not pdf.err:
            return http.HttpResponse(
                result.getvalue(),
                mimetype='application/pdf')

    return http.HttpResponse('We had some errors')

def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    context = Context(context_dict)
    html  = template.render(context)
    result = StringIO.StringIO()
    pdf = pisa.pisaDocument(StringIO.StringIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return http.HttpResponse(result.getvalue(), mimetype='application/pdf')
    return http.HttpResponse('We had some errors<pre>%s</pre>' % cgi.escape(html))

def ezpdf_sample(request):
    blog_entries = []
    for i in range(1,10):
        blog_entries.append({
            'id': i,
            'title':'Playing with pisa 3.0.16 and dJango Template Engine',
            'body':'This is a simple example..'
            })
    return render_to_pdf('entries.html',{
        'pagesize':'A4',
        'title':'My amazing blog',
        'blog_entries':blog_entries})

########NEW FILE########
__FILENAME__ = start-tgpisa
#!C:\Python25\python.exe
# -*- coding: utf-8 -*-
"""Start script for the tgpisa TurboGears project.

This script is only needed during development for running from the project
directory. When the project is installed, easy_install will create a
proper start script.
"""

import sys

from tgpisa.commands import start, ConfigurationError

if __name__ == "__main__":
    try:
        start()
    except ConfigurationError, exc:
        sys.stderr.write(str(exc))
        sys.exit(1)

########NEW FILE########
__FILENAME__ = commands
# -*- coding: utf-8 -*-
"""This module contains functions called from console script entry points."""

import os
import sys

from os.path import dirname, exists, join

import pkg_resources
pkg_resources.require("TurboGears")

import turbogears
import cherrypy

cherrypy.lowercase_api = True

class ConfigurationError(Exception):
    pass

def start():
    """Start the CherryPy application server."""

    setupdir = dirname(dirname(__file__))
    curdir = os.getcwd()

    # First look on the command line for a desired config file,
    # if it's not on the command line, then look for 'setup.py'
    # in the current directory. If there, load configuration
    # from a file called 'dev.cfg'. If it's not there, the project
    # is probably installed and we'll look first for a file called
    # 'prod.cfg' in the current directory and then for a default
    # config file called 'default.cfg' packaged in the egg.
    if len(sys.argv) > 1:
        configfile = sys.argv[1]
    elif exists(join(setupdir, "setup.py")):
        configfile = join(setupdir, "dev.cfg")
    elif exists(join(curdir, "prod.cfg")):
        configfile = join(curdir, "prod.cfg")
    else:
        try:
            configfile = pkg_resources.resource_filename(
              pkg_resources.Requirement.parse("tgpisa"),
                "config/default.cfg")
        except pkg_resources.DistributionNotFound:
            raise ConfigurationError("Could not find default configuration.")

    turbogears.update_config(configfile=configfile,
        modulename="tgpisa.config")

    from tgpisa.controllers import Root

    turbogears.start_server(Root())

########NEW FILE########
__FILENAME__ = controllers
from turbogears import controllers, expose, flash
# from tgpisa import model
import pkg_resources
try:
    pkg_resources.require("SQLObject>=0.8,<=0.10.0")
except pkg_resources.DistributionNotFound:
    import sys
    print >> sys.stderr, """You are required to install SQLObject but appear not to have done so.
Please run your projects setup.py or run `easy_install SQLObject`.

"""
    sys.exit(1)
# import logging
# log = logging.getLogger("tgpisa.controllers")

from turbogears.decorator import weak_signature_decorator
import sx.pisa3 as pisa
import cStringIO as StringIO
import cherrypy

def pdf(filename=None, content_type="application/pdf"):
    def entangle(func):
        def decorated(func, *args, **kw):
            def kwpop(default, *names):
                for name in names:
                    if name in kw:
                        return kw.pop(name)
                return default

            # get the output from the decorated function
            output = func(*args, **kw)

            dst = StringIO.StringIO()
            result = pisa.CreatePDF(
                StringIO.StringIO(output),
                dst
                )

            # print cherrypy.url("index.html")
            if not result.err:
                cherrypy.response.headers["Content-Type"] = content_type
                if filename:
                    cherrypy.response.headers["Content-Disposition"] = "attachment; filename=" + filename
                output = dst.getvalue()

            return output
        return decorated
    return weak_signature_decorator(entangle)

class Root(controllers.RootController):

    @expose()
    def index(self):
        import time
        return """<a href="pdf">Open PDF...</a>"""

    @pdf(filename="test.pdf")
    @expose(template="tgpisa.templates.welcome")
    def pdf(self):
        import time
        # log.debug("Happy TurboGears Controller Responding For Duty")
        flash("Your application is now running")
        return dict(now=time.ctime())

########NEW FILE########
__FILENAME__ = json
# A JSON-based API(view) for your app.
# Most rules would look like:
# @jsonify.when("isinstance(obj, YourClass)")
# def jsonify_yourclass(obj):
#     return [obj.val1, obj.val2]
# @jsonify can convert your objects to following types:
# lists, dicts, numbers and strings

from turbojson.jsonify import jsonify


########NEW FILE########
__FILENAME__ = model
from turbogears.database import PackageHub
# import some basic SQLObject classes for declaring the data model
# (see http://www.sqlobject.org/SQLObject.html#declaring-the-class)
from sqlobject import SQLObject, SQLObjectNotFound, RelatedJoin
# import some datatypes for table columns from SQLObject
# (see http://www.sqlobject.org/SQLObject.html#column-types for more)
from sqlobject import StringCol, UnicodeCol, IntCol, DateTimeCol

__connection__ = hub = PackageHub('tgpisa')


# your data model


# class YourDataClass(SQLObject):
#     pass



########NEW FILE########
__FILENAME__ = release
# Release information about tgpisa

version = "1.0"

# description = "Your plan to rule the world"
# long_description = "More description about your plan"
# author = "Your Name Here"
# email = "YourEmail@YourDomain"
# copyright = "Vintage 2006 - a good year indeed"

# if it's open source, you might want to specify these
# url = "http://yourcool.site/"
# download_url = "http://yourcool.site/download"
# license = "MIT"

########NEW FILE########
__FILENAME__ = pisawsgidemo
#!/bin/python
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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
# Copyright 2010 Dirk Holtwick, holtwick.it
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


__version__ = "$Revision: 103 $"
__author__  = "$Author: holtwick $"
__date__    = "$Date: 2007-10-31 17:08:54 +0100 (Mi, 31 Okt 2007) $"
__svnid__   = "$Id: pisa.py 103 2007-10-31 16:08:54Z holtwick $"

from wsgiref.simple_server import make_server
import logging

from xhtml2pdf import wsgi

def SimpleApp(environ, start_response):

    # That's the magic!
    #
    # Set the environment variable "pisa.topdf" to the filename
    # you would like to have for the resulting PDF
    environ["pisa.topdf"] = "index.pdf"

    # Simple Hello World example
    start_response(
        '200 OK', [
        ('content-type', "text/html"),
        ])
    return ["Hello <strong>World</strong>"]

if __name__ == '__main__':

    HOST = ''
    PORT = 8080
    logging.basicConfig(level=logging.DEBUG)

    app = SimpleApp

    # Add PISA WSGI Middleware
    app = wsgi.PisaMiddleware(app)

    httpd = make_server(HOST, PORT, app)
    print "Serving HTTP on port %d..." % PORT
    httpd.serve_forever()

########NEW FILE########
__FILENAME__ = pisa
#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

__version__ = "$Revision: 221 $"
__author__ = "$Author: holtwick $"
__date__ = "$Date: 2008-05-31 18:56:27 +0200 (Sa, 31 Mai 2008) $"
__svnid__ = "$Id: pisa.py 221 2008-05-31 16:56:27Z holtwick $"

import xhtml2pdf.pisa as pisa


pisa.command()

########NEW FILE########
__FILENAME__ = cookbook
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

__version__ = "$Revision: 176 $"
__author__  = "$Author: holtwick $"
__date__    = "$Date: 2008-03-15 00:11:47 +0100 (Sa, 15 Mrz 2008) $"

"""
HTML/CSS to PDF converter

Most people know how to write a page with HTML and CSS. Why not using these skills to dynamically generate PDF documents using it? The "pisa" project http://www.htmltopdf.org enables you to to this quite simple.
"""

from xhtml2pdf import pisa
import cStringIO as StringIO

# Shortcut for dumping all logs to the screen
pisa.showLogging()

def HTML2PDF(data, filename, open=False):

    """
    Simple test showing how to create a PDF file from
    PML Source String. Also shows errors and tries to start
    the resulting PDF
    """

    pdf = pisa.CreatePDF(
        StringIO.StringIO(data),
        file(filename, "wb"))

    if open and (not pdf.err):
        pisa.startViewer(filename)

    return not pdf.err

if __name__=="__main__":
    HTMLTEST = """
    <html><body>
    <p>Hello <strong style="color: #f00;">World</strong>
    <hr>
    <table border="1" style="background: #eee; padding: 0.5em;">
        <tr>
            <td>Amount</td>
            <td>Description</td>
            <td>Total</td>
        </tr>
        <tr>
            <td>1</td>
            <td>Good weather</td>
            <td>0 EUR</td>
        </tr>
        <tr style="font-weight: bold">
            <td colspan="2" align="right">Sum</td>
            <td>0 EUR</td>
        </tr>
    </table>
    </body></html>
    """

    HTML2PDF(HTMLTEST, "test.pdf", open=False)

########NEW FILE########
__FILENAME__ = datauri
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

__version__ = "$Revision: 194 $"
__author__  = "$Author: holtwick $"
__date__    = "$Date: 2008-04-18 18:59:53 +0200 (Fr, 18 Apr 2008) $"

import ho.pisa as pisa
import os, os.path
import logging
log = logging.getLogger(__file__)

def helloWorld():
    filename = __file__ + ".pdf"
    datauri = pisa.makeDataURIFromFile('img/denker.png')
    bguri = os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir, "pdf/background-sample.pdf"))
    bguri = pisa.makeDataURIFromFile(bguri)
    html = u"""
            <style>
            @page {
                background: url("%s");
                @frame text {
                    top: 6cm;
                    left: 4cm;
                    right: 4cm;
                    bottom: 4cm;
                    -pdf-frame-border: 1;
                }
            }
            </style>

            <p>
            Hello <strong>World</strong>
            <p>
            <img src="%s">
        """ % (bguri, datauri)
    pdf = pisa.pisaDocument(
        html,
        file(filename, "wb"),
        path = __file__
        )
    if not pdf.err:
        pisa.startViewer(filename)

if __name__=="__main__":
    pisa.showLogging()
    helloWorld()

########NEW FILE########
__FILENAME__ = helloworld
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

__version__ = "$Revision: 194 $"
__author__  = "$Author: holtwick $"
__date__    = "$Date: 2008-04-18 18:59:53 +0200 (Fr, 18 Apr 2008) $"

import ho.pisa as pisa

def helloWorld():
    filename = __file__ + ".pdf"
    pdf = pisa.CreatePDF(
        u"Hello <strong>World</strong>",
        file(filename, "wb")
        )
    if not pdf.err:
        pisa.startViewer(filename)

if __name__=="__main__":
    pisa.showLogging()
    helloWorld()

########NEW FILE########
__FILENAME__ = linkloading
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

__version__ = "$Revision: 194 $"
__author__  = "$Author: holtwick $"
__date__    = "$Date: 2008-04-18 18:59:53 +0200 (Fr, 18 Apr 2008) $"

import ho.pisa as pisa

import logging
log = logging.getLogger(__file__)

def dummyLoader(name):
    return '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00F\x00\x00\x00\x89\x04\x03\x00\x00\x00c\xbeS\xd6\x00\x00\x000PLTE\x00\x00\x00\n\x06\x04\x18\x14\x0f-&\x1eLB6w`E\x8f\x80q\xb2\x9c\x82\xbe\xa1{\xc7\xb0\x96\xd1\xbd\xa9\xd9\xd0\xc6\xef\xeb\xe6\xf8\xf3\xef\xff\xfb\xf7\xff\xff\xffZ\x83\x0b|\x00\x00\x0c\xedIDATx^u\x97]l\x1bWv\xc7g\xe2`\x81\xbe\xcd%Gr\xd3\xa7P\x12e\xb7\x01\x8a\xd0")E\x01\x02\x8f\xf8!\x8bI\x17\x10\xc5!))5`\xf1C\xb4\xb25`S\xb2l\xb95\x90H\xa4.\xb9/u$K3\xe3\xa2\x80W\x12\xc59L\xf6a\xb3\x8dcN\xd6@\xb7\x1f\x01\x8a\x85\x16\x9b-\xfa\x81M\xb8@\x83l\xd1\xd8\xbc|)\xd0\x97\x82\xea\xb93\x92\xec"\xce\x11 \t3?\xfe\xcf\xff\x9e{\xce\x01(\x1c>7\x18\xfb\xc2\xfaE\xffk_\xb6\x18\xeb\x1e>\x8f\xe92d\xfe%T\xa8\x98\xfa\x07\x1f $<\x0f\xe1\x91\xabT\xc1\xacT\xf2\xbfd\xec\xbb\x98\xdfM\xeb\x86aYP\xfa\xd3\xd6\xf3\x98C[\xa6\xaaU\xa1a5\xe9\x1b\xad\xef\xd0i}\x91\xccy+\xc8X\xf5E\xf6]:\xff0\xd8\x97\xce7\xb9P\xf1\xd1\xb7\x98\xaec\xe7/\xd3\xa1\xeb\x81{\x96e5\xd7.\xb6\x85\xe7\x99aO\x94\xf1R(\xfeC\xce\xd4F\xbf\xc50\x1b\xfa\xefS\xa9\xb2\x12p\x98({\x8eN\x9b\xb1\xbf\xf5O\xa5\xd7\x0b\xb4\xc9\x0f\x96\xec<G\xa7\xc5\x1e\xbf\xfa\xe2b\x90\x16\xb2\x00\x96E\x93O\x9e\xe7\xe77\x8b\xd2@ \xa3\xa7\x96\xe6\r\xab\xb9\x97\xfc\xf6\xb90WV\x0e\x8d(\xa1\xa5dd*\x06PL\xa2\xe7g\xdfw\xba\xe8\xe6o\x06\xc6\xd5\x80\xc7\xe5s\xbb|\xbd\x91\xd2\xb9 \x13\x9e1\xc2\x13\xb5\xfeN\rn\xa5\xd5a\xc5+\xe7\xb7\xf5\xa2\xcbC\xde>a\x9c\xd2\xb5\xad\x07\xdbS\x0b\xb0\xa5z\xeb\x94\xd2y\x80kD\xee<e\x10h\x7fs]\xf4g\xa7\x01\xb6\x12\x91z\xa9P\x8a\\\xcfg\xfdQ\xf6\x0c\x83\xb1CD?\x05\x80\xf2\xa4;z)\xb8\x11\xf1\x11\xf7\xe5\x8b\x9d\xff\xcf\\\x92H\x846\x80f\x91Ys/\x11\xe2r\x85\xfe\x98u\x9e\xf5\xf3_\x1eB\xd2U\x00\x9a\xf3\xc9\xc92\xb9\xbc\xbc\xec\x93N?:\xce\xd59\xect\xdb\xec_\xbdC\xa4\x1f\x99\xb9\x81\x97\xddj\xb9g\x8c\xf4\xaf\xe8\x8f\xba\xc8\x1cwy\xbb\xd3\xb8\xab.\xfb\x0bU\xd03S\xa2\xac\x96\x03k\xe1\x02\xe4\x19\xbe\x12N\xcc|3<U\xd8O\x02\xd4iQ\x12\\j\x81R\x80\xbd\x14\x16\xed\x88\xc1\xfavw&\x02isj\xa2\xa9\xd1\x12\x91\xc4\xfe$\xa5\xe1\xbc\xf2f\xbbs\xcc \xc2\xb2\xc6\xcd\xec\xe8\xfe\xa2\x05\xb4F$A\x0c\x94\n\xee\x9b\xc5\xec_\xb3\xa7\x0c\xfb\xf7q\xad\xb2\xb6b5?h\xea\xe6$\x11\t\xe9\xebs\r\xbdv\xf5\xf6\t\xd3a\xec#5\xb8\x9c\x08\xdf\xb4\xc0J\xc1\x9a$\x11\x7f8\x1c\x01\xb8\xf4\x17\xec\xb0s\xe29\x93\x18\x08\xa5\xcc\xa4eA\xaep\xd7#\xca\xa0\xeb\xd7o\xd5\x8a\xb7\x19;a:.\x1f\x11\xdd7\x1b8R\xcb\x83\xf5\xac<\xbf\x1e.,\xce~<\xff\xe3N\x9b\x1d3m\x0f\xea\x8b\x85{\xd6\xa7\xd6\xc3\xf8e}\xd9\xdc C\xd1\xd9f\xfe\x9d\x16;f\xba\x7f/\x12A\x10\xce\xe2\x88[\xffT\x9a\x99\xc8\x0co\xf5\xf5\x05g\xad\xda\x0fX\xeb\xa4\xceqQ\x10$\xb1\xb7\xd2@\xa86x\x7f8>h._\x9dh4\x8d\xa7:\x8f#X\x13At\xdb3nF\xee\xc8\x19wV^\xf4\x1b\xd6\xdc\xed\x13\xe6w\x01I\x90\x90\xa1F\x05\x99\xdc}B\x88(\x87}\xb7\xac\xda\x99\x13\xe6\xa7\xa1\xf3\x02fs\xa5)\xbd\xd70\r\xceH"\x91\xc2\x15\xc8\x1e\x9f\xbd\xbd\x17\xf7\x8b\x04m\x07\xd2\xb4\x02\xc8 !\xcf\xe1\x83\x0b\xc6\x9d+\\\x87u;\xedl\xdc{^\x12\x05\x89$\x0b\xd40\xef\x12\tu\xd2\x99!\xec\xc4\xab\x17\x8f\x98\xc7/\xc6\x07\xc6$;\xc1YZ\xd1+\n\x11E\x12\xa0\xe0\x1b\x18G\xd3\x0e\xf3\xb57\xeeN\xbc,\x89\xa2@z\xd0\x12]\xc34C\x11d\xbct\x809\x0c\xfbU N"\x1eA\x92\xf0l\x03\xd8]\xeb\nq/\xc9\xb4\xe6\x91\x13\xf2\x97\xc8t\x1dF\xea#\xa2\xc0\xebH\x06)\x98\x8b\xc4\xbd\xd73\x12\x17e\xe5\x956g\xb0C~\x15P\x89(\t<\x08\xe9\xbda\xc0]\xcf\x1f\xed\x91\xbcBd\xe5\rv\xc4\xfc:\xac\xe2Qlf\xc8G\x82\x95\xc6\'\xf1\x18(><\xa6\xfb\xc0\xf6\x83\xcc\xe7\t\xd5G\x1c&\x8d\xc3E\x1b\x0fK\x00\x8a"\xc8\xd9\xde\x93\xfb\xfa\\U\xa7\x08\xcf\x85\x96\xd3\xf9\xb1\xf4\x0f\x9b\x9c\x11\xa4q_\xf8\xe0)3\xa5\x9e\x97\x1c;^\xbaU\xa8Z[1x\x9f\xbcX$3_v9\xd3\xedt?W\xe3^\x14r\xa04T\xc0\xfad\x14\xc6r\x83\xf7\xa5\xc4\x91\x1f\xc6\x90!r\x9fs0\xb1\xa76\xdd\xb0\x1e\xc66\xcf\\\x9ay\xf5\x85\xc4\xc1aW\xb0\x97\xd355A\x88,8AjA\x1d\x1b-S\x98Ly\xe4\xe4m\xe7\xec-\xe6WU\x82%\x94\x1cF\xed\xa1Uk/\xa2\xb9\xb3\xe4T\xee\r\xf6[dZ-\x16@F\xc2{w\x92\x05C#\xd4\x1a\x1f\xae\xcbe\x8f\xff\\\xaf\xe3\xa7\xfd\xf5\xd9\xb2:\x89wu\x14\xb2\xe2\xbeqO_\xa9\x0f\xaf\xfb\xfa\x06\xe7\xae\xb4m?\xff\xdc[\x8a\xa8\xca1$\x8a!\xf2Zc\x13\xea\x17\xd6\\I(\xcd\xb4\x84\xeea\x9b}\xe4\xce\x8f\x85\x13\xce\x8d\x89\xc8HR\x10\xb2P\xa7\x19w\x0c\xf6\x93\xbf\xe4L\xeb\x12\x89\x95\\\x11\xc5\xbe1" *\xca\xc6\x80Ik\xbe\xf0\x02\xd4s\x8f\xb8\x9fo|\xbd\x83\xda\x80+\xc7\xdbPD\x10\x8f\xf8\xc2B?\xadlD\x8b\x00\x943]\xf6?\xa9\xfe\x1e\xdc\xd6\x83\x08\t\xbc\x00\xc3\x8aH\xd2\xfd\x85\x8a_\x1b?a~\xb4\xb0\x99\xf1-g\xfc\x86\x11\x1a\x1a:\xd7G\x00\xce\x8b\xbd\xef\x176a\xed\xb5f\xb3\x9e{\x9b\xe7\xda\xbde\xc1^h\x1cj\x97s*\xc69\x80]B2\x05]\xcb.\x00\xd4\xcb\xafs\x9d\xfb\xef\xe0\x90\xefG\r\x8d\xaa\xe10\x9aA\x8eH\xee\x02-\xab^\x00\xd3f\xba\xbb\xc6\xa7V\xb3\xa9Uu]\xcf\x86\xb1\xda\xf6\x8c\xbe\x90,\xe4\x16]Q\xd08s\xd8\xde\xc5=\xd0\x040\xa0\x01e\x1f\x8e\xab\xcd\x90Hr\xdd\xf4yS\xb0\xc5\x99\xc71\x04@\xdf\x1c6\x00\xeeb\x89$\xde\xb5\xc4C\xfa\x01v\x86\xd2\xb0\x8f\x9e\xbb\xffV\x05\x93\x96\t\x99\x9b\x013DPG$R\xdf\xa9bx\x85\x7f\x12\xac\x07\x9c\xf9\xa4\n:\x8d\xe3h\xcfC.\xcb\xcbH\xdc\x03j\x90\xa2]\xdd\xc0\x9de\xfe\x00\x99T\x15\xa0\xe6!\x0159\x9f\xcf\xc7\t"I\x7f\xb9@\xab\x1a\xa5Z\xf5SK{\x13\x99\xf1*\xd4\xe7\xc8 \x8e\xf0\xe5\x89p\xde#{\xe3\xe9<\xb5\xa3R\xbfgY\x9a\x1f=GQg{\xfe\x06\xc5X\xd0\xebD.\xac\xf3\xff\xcb\xaa\x9a\xac\\\xc0\x9a\x94\\\x8e\x0e\x0f\xcd\xf9\xa4G.P\x8cuU\x8dxw\x0b\r0Koq\x86\x1aO!\x9a\x90\xd3\x1c\xc9*\x84\x8c\x16/7\xabu\xfa\xe7\xc8Di\xc5fL\x8a&\xe9v8\x89\x7fscD\x92\x17&W\x1e\xde\xd3J\xaf\xd8\x0c\xad\xd8\x14\xbe\x03C_T\xf3\xf9\\\xe2eB\xdc\xb1\x84F\xf5\xf0\x1a?{\x84[D\xa4\x01u\x8a\xbf\xf6T\x1e\xb83\xce\x04\xbd\xa6\xaa\xcd\xaf}\x88\xe7:?L\xb5\xfcM\'\x1b`(X*\xf5UQL-\xf5>\x18\xce\x8c$\x99\xc0\x98\x12\xa4tJ\xbd\xac\xeb<\x1bX\xcd\x1d{w\xf2\xae\x1d\xfeI\x94,q\xa6\xa3\x04\n\xebJ\x00\x97.\xcc\xeb\xb4\n\xf0>2|d%\x12\xfbI\xbe\'\x94\xecp\x9d@j]q\x0f\x8d\xd3\x9a?\xa6\x1b\x00\xef\x11I\xe0\xbb\x91\xb8\xa6wj\xd3\xc1 \xcf\xf5sY\xcdM\x11\x12(\x94\x88\\\xb1>K\xbf\xe7\x91\x88\xc8\xb5\xdc\xc9\xd0\xb5\xec\x99\xb78\xf3\xebS\xaa\x8a\x03\x88\x8c\x87\\\xf8\xf4\xfe\xcc5\xb4\x83\x86\x029\xf7\xd4\xe9\x9b\xa1\xa5/\xb9\x9f\xff\x15#jbh(\x92\xc6\x06\t6\xe6.\xfb\xb1\xc4\xfdb\x8fV\xf2\x89\xa2\x1c\xb9\xd2\xe6\xcc\x93\xc9\x80\x8a\x81\xf5\xc5d\xd5D\xed\x0f\xefr\xdd\x0b\xb4<\x89\xae\xc8\x15\xc6\x84\x0e\xeb~\x16Bh\x8a\xa8\xe5\xb0+Y\xd9\xdc\x9b\xb5,S!7hi\nG\x92\x1cp\xe6\xf0\xb7\x1fo\xf7\xf5\xf5\xbdL\x06K\x02\xb9P\x9d\xd8\xbbeY;\xa4\x07\xef,!\x89\xd2\xe9N\xf7\x10\x99v\x13\xee\xa0K\xd2["nZ\x81M\xec\xab;\x9e42\x93\x82$\xbe\xd29\xe4\xcc\x93\x18lp\xd5`\x89\x04\x0bU\x98Z\xb1\x9a\xfex\x9a\x96\xf9\xfa#\xb79\xc3\xba\xc8\x94\xf9|\xde(\x91\xe84@\xb2a}\x9c\x0c\xdb\xa9\x04\xe1\xd4#\x9ba\xc8`k\x89\xb2^"\x91\n\xec\xa7,kiKFF\xc1\x91\xc5m\x88\xcc!{2\x08\xb4\xe4\x11\'\x00sU\xeb\xc5\xd9fx\xa6&\xd3r\x02\'Q|\xb3c3\x87\xed\xbbP_#d\xc6\x98\x93\xd3\xd5\xd5\xc0\xec\xc3\x01(\xcbeu\n\x19r\x91ul\xa6\xb3\x07u\xac\xde\xeeK\x97\x08\xf6Vpv\'\x06\xef\x8e\xe4T\x85\x88\x92\xcc\x1c\xa6\xcb\x90YC\xe6\xb4B\xc2!wa=\x07\xf5w\xc7U,\x0e\x91\xfe\xa4\xd5:a\xcc\xb2O\xde\xed%\x18=t{\x06\xb4w\x83\t\x9f\x84%\xfbY\xf7(\x17\xdbY\x00\xaa\xc8\xbbI>\xea\x11\xdee\x9a\x12T\xb0b\xe2\xf7\x0eP\xc7\xf1|\x9f3$Q\xe4\xdb9J\rd\xce\xe5}\x9c\xf9\xb36;\xd6\xb9?\x83\x8c\x18\xbe\x86\x0c\x19__\x01s\xcd\xbd\xf8\x02\xf6*\x16\x87\xb5\x8f\xfc\xd8:b\xe2\x9a$H\xaedy\x01\xccLOv@\xb2\xdb\x82u\x1d\xa6\xbd\xb3b3s(\xe3N\xa1\x9fm_$\x11\x97D^c\xac\xa0\xe3g\x0f\x00\xeb<4\x87\x1f\x95SK\xbcX\xc3XA\xe9-4s\xc4t\x9f\xf8\x01\xd6\xf0H\xd8\xc7DNfM:\xd7sF\x9d\x12\xe5\x1f?\xcb\x8c\xa2K\x91\xb8\xe6DI\x94\xd3\xa3Z\x9ex\x83\x81\xb1\x84\xf7g\xfcP\xc7L\x8c\xdf\xa9\xf0\xa2\xffUQ\x08\xa4\xce\xe6|$\x91\x95U5\xf8\x08\x99\xae\xc3`\x8f\x99\x94*\x828\x91\x11p\x80\x06}\xe2)\xf5\xd2@^M\x7f\x88\x9e\x9f\xea\xd4)\x9d#\xe2BV\x10\x02\xd9~\\\x18\xd7\xc7\x92TM\xbf\xdd:a\x0e\xbf\x18EfU +\x8b\xc8d\xb0\xbe\xc1\xa4/J\xf37^G\xe4X\xe7q\xcc\x04Z&\xc2K\x0eC\\Y\x1a\xb8`,\x9a\xb7Z\xad\xa7\xb9Fu\x13u\xa4\x97\xb26#}\xcfK#\xd4\xd85W\xdb\xec\x19\xc6\x00\r\xeb\xfaR\xc9a\xc6F\xea\xab\x9aQ\x87U\xf6\x8cN\x0c\x1a\xday"\xfe\x9e\xc3\x90k#\xf52gJWX\x17\xef\xeb\x98\x01\x9a\xc7\xfa\x95\x88\xcd\xcc\x05\xa3U\xce\xd4\xdf\xc0+\xed:3\xf8x\x14\x99u\t\xbd\x12\x11\x19W1\xd0c\xd8\x8c\xcaX\x8b9\xf3\xf5\x1f1\xa8\xd3UIt\xe1p\xb8\xb3~Z\xf1\x91\r\xcd\xa85\xcc\xdc\x01k\x1f33\x00\xda\xaa\xe4\x0e/\x12\x89\xa4\xb1V\x8b\xbe\xa2\x06\xc5\x15(\xf1\x9b?\xb4\x99\xaf\x00\x80\xc6\xdd)\xc8\x12B\xfc\xcd\n\xad\x14s\xbay\x15\'|\x98\xb1\x13\x1d\x03h$U\x1b?\'\x86C\xa4\x01\x94\xee\x8e\xe8p\x15\x1b8\x8c\xd7\xeax\xfe\xeaF\xb5^\xd1k\xe7z\xb13\xae\xfb\x1aVS\xd39\x13\x03\x9ayttv\x16\xa2\x06\x98EQ\xec\x15"xo\xb8\xa1\x00Ftc\xaf\x17\x05\xdf\xec:\xf3\xce\xa2\x94\xc2&\x1f?\x92\xa6\xd5\xcd3M\x1d`\xa62\xbf\x13Df\x03\r\xd9~\xc2i\n\x97H8\xac\x88i\xdd0\x07,]\xdfZ\xd9^\xd9\xcf\x1b\x94\x96n\x1f1\xf7\xbdUXR)}\xcf\xfe\xa27`\x81V6\xf6rZn\x85\xd2\xf2\xf7\x8f\xcf%\xc3\x05\n\xf8@\xec\x1f1`\xee\x9df}j\xc5\xdc\x18Voit\xf5\xfb-\xc7\xf3\xcf\'\x8a\x7f\x00\x1a\xa5\xeb\xc4C&\xe0\xfdY\x0b&\x0bK\x99A\xafQ\xa7k\x07-\x9e\xab\xc3\xc6\xb6\x94\xd3\x00uZ\x96T%X\xd9\x8b!\x93t\'\x06\xaf\x83I\xd7o\xb7\x9c\\\x91\xc5p\xbfa\xeat]I\xff\xc8O\xf7\x83M\xc8\x10w\xc0\xbb\xb4b\xd2\xf2\xa8\xc3\xfc\xe7|\x94\xc6\xa7ML\x86_m\xb3\x14\x96\x8cz9G\xc8\xd9\xaca\x96\xe6C\x1fr\xa6\xf5@+\x18\xa5A\xd3\x04\x9a\xed\xd9\xc8j\xb0\x1f\xa6\xd4X"\xeei0\xd6\n\xea\x01g\xday\x8dB=~\x06\x1d\x95zV\xb7\xab`\xea\x1aB\xba\xc9\x1d\x06\xdf\xb6\xeb\xf3\x9b\n4\xf9N\xd8\xc6c(Y\xb3\x02{\xf3\x0f\n\x15@\xc3\x18\xfeN\xd7f(>\xc0\x9e\xbf3\x0e\x1a\xda\xd2\xa1\xe6\xc9O\xa0\xa8\x81H\xeeb\xdb\xd6\xf9G.\x0c\xb0zU\x9e\x81\xcd\xdf7\x00\x96<\xde( \xab\xd1l\xe0\xc0\xe9\xc3\x8f\x90G\xa9\xf8\xc6\xbc\x1fv\xe5J\xb5\xba\xd9#\'\x81K\xaf\xc5>hu\xed>\xfc)\xe5a\x8cm\xc2F\xcc\x1cZ\xde\xdc\x9f\x0ef\xd1\xf8:-\xfd\xd5\x01;\xea\xc3S\xd4\x8e\xdd\xe5\x19\x80\x86\x8fd\xca\x13\xd1\x1e\xa3\x9e\x0fEX\x1b\x7f\x1c\x1dU-\xd8\xd9F5t\x95 \xa1\xa5\x89\xa8:\xddTg\xf9N\xc5\xc9\xb1\x99\xc7J\xc4\x16\x9a\xd6\xd0\x95\x99 J4\xb5\x7f\xab\x85D\x8b\xffr\xf6<{\xb8\x1d\x0e\xf9\xa9\x13\xb0GnZ\xd6/Z\xfc%\xb3\x99\xae\xcd0f\xe1c\x1e\x9f\r\r\x05\xad\x16{&\x10\xc0\xf8?Z\n\xf1+\xfb\x81\xd5F\x00\x00\x00\x00IEND\xaeB`\x82'

class myLinkLoader:

    """
    This object is just a wrapper to track additional informations
    and handle temporary files after they are not needed any more.
    """

    def __init__(self, **kw):
        """
        The self.kw could be used in getFileName if you like
        """
        self.kw = kw
        self.tmpFileList = []

    def __del__(self):
        for path in self.tmpFileList:
            os.remove(path)
        self.tmpFileList = []

    def getFileName(self, path, relative=None):
        import os
        import tempfile

        log.info("myLinkLoader.getFileName: %r %r %r", path, relative, self.kw)
        try:
            if "." in path:
                new_suffix = "." + path.split(".")[-1].lower()
                if new_suffix in (".css", ".gif", ".jpg", ".png"):
                    suffix = new_suffix
            tmpPath = tempfile.mktemp(prefix="pisa-", suffix = suffix)
            tmpFile = file(tmpPath, "wb")
            try:
                # Here you may add your own stuff
                tmpFile.write(dummyLoader(path))
            finally:
                tmpFile.close()
            self.tmpFileList.append(tmpPath)
            return tmpPath
        except Exception, e:
            log.exception("myLinkLoader.getFileName")
        return None

def helloWorld():
    filename = __file__ + ".pdf"

    lc = myLinkLoader(database="some_name", port=666).getFileName

    pdf = pisa.CreatePDF(
        u"""
            <p>
            Hello <strong>World</strong>
            <p>
            <img src="apath/some.png">
        """,
        file(filename, "wb"),
        link_callback = lc,
        )
    if not pdf.err:
        pisa.startViewer(filename)

if __name__=="__main__":
    pisa.showLogging()
    helloWorld()

    # print repr(open("img/denker.png", "rb").read())

########NEW FILE########
__FILENAME__ = pdfjoiner
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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


__reversion__ = "$Revision: 20 $"
__author__    = "$Author: holtwick $"
__date__      = "$Date: 2007-10-09 12:58:24 +0200 (Di, 09 Okt 2007) $"

from sx.pisa3 import pisa
from sx.pisa3 import pisa_pdf

if __name__=="__main__":

    pdf = pisa_pdf.pisaPDF()

    subPdf = pisa.pisaDocument(
        u"""
            Hello <strong>World</strong>
        """)
    pdf.addDocument(subPdf)

    raw = open("test-loremipsum.pdf", "rb").read()
    pdf.addFromString(raw)

    pdf.addFromURI("test-loremipsum.pdf")

    pdf.addFromFile(open("test-loremipsum.pdf", "rb"))

    datauri = pisa.makeDataURIFromFile("test-loremipsum.pdf")
    pdf.addFromURI(datauri)

    # Write the result to a file and open it
    filename = __file__ + ".pdf"
    result = pdf.getvalue()
    open(filename, "wb").write(result)
    pisa.startViewer(filename)

########NEW FILE########
__FILENAME__ = simple
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

__version__ = "$Revision: 194 $"
__author__  = "$Author: holtwick $"
__date__    = "$Date: 2008-04-18 18:59:53 +0200 (Fr, 18 Apr 2008) $"

import os
import sys
import cgi
import cStringIO
import logging

import xhtml2pdf.pisa as pisa

# Shortcut for dumping all logs to the screen
pisa.showLogging()

def dumpErrors(pdf, showLog=True):
    #if showLog and pdf.log:
    #    for mode, line, msg, code in pdf.log:
    #        print "%s in line %d: %s" % (mode, line, msg)
    #if pdf.warn:
    #    print "*** %d WARNINGS OCCURED" % pdf.warn
    if pdf.err:
        print "*** %d ERRORS OCCURED" % pdf.err

def testSimple(
    data="""Hello <b>World</b><br/><img src="img/test.jpg"/>""",
    dest="test.pdf"):

    """
    Simple test showing how to create a PDF file from
    PML Source String. Also shows errors and tries to start
    the resulting PDF
    """

    pdf = pisa.CreatePDF(
        cStringIO.StringIO(data),
        file(dest, "wb")
        )

    if pdf.err:
        dumpErrors(pdf)
    else:
        pisa.startViewer(dest)

def testCGI(data="Hello <b>World</b>"):

    """
    This one shows, how to get the resulting PDF as a
    file object and then send it to STDOUT
    """

    result = cStringIO.StringIO()

    pdf = pisa.CreatePDF(
        cStringIO.StringIO(data),
        result
        )

    if pdf.err:
        print "Content-Type: text/plain"
        print
        dumpErrors(pdf)
    else:
        print "Content-Type: application/octet-stream"
        print
        sys.stdout.write(result.getvalue())

def testBackgroundAndImage(
    src="test-background.html",
    dest="test-background.pdf"):

    """
    Simple test showing how to create a PDF file from
    PML Source String. Also shows errors and tries to start
    the resulting PDF
    """

    pdf = pisa.CreatePDF(
        file(src, "r"),
        file(dest, "wb"),
        log_warn = 1,
        log_err = 1,
        path = os.path.join(os.getcwd(), src)
        )

    dumpErrors(pdf)
    if not pdf.err:
        pisa.startViewer(dest)

def testURL(
    url="http://www.htmltopdf.org",
    dest="test-website.pdf"):

    """
    Loading from an URL. We open a file like object for the URL by
    using 'urllib'. If there have to be loaded more data from the web,
    the pisaLinkLoader helper is passed as 'link_callback'. The
    pisaLinkLoader creates temporary files for everything it loads, because
    the Reportlab Toolkit needs real filenames for images and stuff. Then
    we also pass the url as 'path' for relative path calculations.
    """
    import urllib

    pdf = pisa.CreatePDF(
        urllib.urlopen(url),
        file(dest, "wb"),
        log_warn = 1,
        log_err = 1,
        path = url,
        link_callback = pisa.pisaLinkLoader(url).getFileName
        )

    dumpErrors(pdf)
    if not pdf.err:
        pisa.startViewer(dest)

if __name__=="__main__":

    testSimple()
    # testCGI()
    #testBackgroundAndImage()
    #testURL()

########NEW FILE########
__FILENAME__ = story2canvas
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

__version__ = "$Revision: 194 $"
__author__  = "$Author: holtwick $"
__date__    = "$Date: 2008-04-18 18:59:53 +0200 (Fr, 18 Apr 2008) $"

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch
from reportlab.platypus import Frame

import ho.pisa as pisa

def test(filename):

    # Convert HTML to "Reportlab Story" structure
    story = pisa.pisaStory("""
    <h1>Sample</h1>
    <p>Hello <b>World</b>!</p>
    """ * 20).story

    # Draw to Canvas
    c = Canvas(filename)
    f = Frame(inch, inch, 6*inch, 9*inch, showBoundary=1)
    f.addFromList(story,c)
    c.save()

    # Show PDF
    pisa.startViewer(filename)

if __name__=="__main__":
    test('story2canvas.pdf')

########NEW FILE########
__FILENAME__ = testBackground
# -*- coding: utf-8 -*-
#############################################
## (C)opyright by Dirk Holtwick            ##
## All rights reserved                     ##
#############################################

__version__ = "$Revision: 176 $"
__author__ = "$Author: kgrodzicki $"
__date__ = "$Date: 2011-01-15 10:11:47 +0100 (Fr, 15 July 2011) $"

"""
HTML/CSS to PDF converter
Test background image generation on the `portrait` and `landscape`
page.
"""

from cookbook import HTML2PDF

if __name__ == "__main__":
    xhtml = open('test-background-img.html')
    HTML2PDF(xhtml.read(), "testBackground.pdf")

########NEW FILE########
__FILENAME__ = testEvenOddPage
# -*- coding: utf-8 -*-
#############################################
## (C)opyright by Dirk Holtwick            ##
## All rights reserved                     ##
#############################################

__version__ = "$Revision: 176 $"
__author__ = "$Author: kgrodzicki $"
__date__ = "$Date: 2011-01-15 10:11:47 +0100 (Fr, 15 July 2011) $"

"""
HTML/CSS to PDF converter
Test for support left/right (even/odd) pages
"""

from cookbook import HTML2PDF

if __name__ == "__main__":
    xhtml = open('test-template-even-odd.html')
    HTML2PDF(xhtml.read(), "testEvenOdd.pdf")

########NEW FILE########
__FILENAME__ = visualdiff
# Copyright 2010 Dirk Holtwick, holtwick.it
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

import sys
import glob
import subprocess
import tempfile
import os
import os.path

CONVERT = r"C:\Programme\ImageMagick-6.3.8-Q16\convert.exe"
DIFF = "tortoiseidiff.exe"

__version__ = "0.1"

class VisualObject:

    def __init__(self):
        self.files = []
        self.files4del = []
        self.folder4del = None

    def __del__(self):
        for file in self.files4del:
            os.remove(file)
        self.files4del = []
        if self.folder4del:
            os.rmdir(self.folder4del)
        self.folder4del = None

    def execute(self, *a):
        print "EXECUTE", " ".join(a)
        return subprocess.Popen(a, stdout=subprocess.PIPE).communicate()[0]

    def getFiles(self, folder, pattern="*.*"):
        pattern = os.path.join(folder, pattern)
        self.files = [x for x in glob.glob(pattern) if not x.startswith(".")]
        self.files.sort()
        print "FILES", self.files
        return self.files

    def loadFile(self, file, folder=None, delete=True):
        if folder is None:
            folder = self.folder4del = tempfile.mkdtemp(prefix="visualdiff-tmp-")
            delete = True
        print "FOLDER", folder, "DELETE", delete
        source = os.path.abspath(file)
        destination = os.path.join(folder, "image.png")
        self.execute(CONVERT, source, destination)
        self.files4del = self.getFiles(folder, "*.png")
        return folder

    def compare(self, other, chunk=16 * 1024):
        if len(self.files) <> len(other.files):
            return False
        for i in range(len(self.files)):
            a = open(self.files[i], "rb")
            b = open(other.files[i], "rb")
            if a.read() <> b.read():
                return False
        return True

def getoptions():
    from optparse import OptionParser
    usage = "usage: %prog [options] arg"
    description = """
    Visual Differences
    """.strip()
    version = __version__
    parser = OptionParser(
        usage,
        description=description,
        version=version,
        )
    #parser.add_option(
    #    "-c", "--css",
    #    help="Path to default CSS file",
    #    dest="css",
    #    )
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")
    parser.set_defaults(
        # css=None,
        )
    (options, args) = parser.parse_args()

    #if not (0 < len(args) <= 2):
    #    parser.error("incorrect number of arguments")

    return options, args

def main():

    options, args = getoptions()

    print args

    a = VisualObject()
    b = VisualObject()

    a.loadFile("expected/test-loremipsum.pdf")
    b.files = a.files

    print a.compare(b)

if __name__=="__main__":
    main()

########NEW FILE########
__FILENAME__ = witherror
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

__version__ = "$Revision: 194 $"
__author__  = "$Author: holtwick $"
__date__    = "$Date: 2008-04-18 18:59:53 +0200 (Fr, 18 Apr 2008) $"

import ho.pisa as pisa

def helloWorld():
    filename = __file__ + ".pdf"
    pdf = pisa.CreatePDF(
        u"Hello <strong>World</strong> <img src='data:image/jpg;base64,?�*'>",
        file(filename, "wb"),
        show_error_as_pdf=True,
        )
    if not pdf.err:
        pisa.startViewer(filename)

if __name__=="__main__":
    pisa.showLogging()
    helloWorld()

########NEW FILE########
__FILENAME__ = testrender
#!/usr/bin/env python
import datetime
import os
import shutil
import sys
import glob
from optparse import OptionParser
from subprocess import Popen, PIPE

from xhtml2pdf import pisa


def render_pdf(filename, output_dir, options):
    if options.debug:
        print 'Rendering %s' % filename
    basename = os.path.basename(filename)
    outname = '%s.pdf' % os.path.splitext(basename)[0]
    outfile = os.path.join(output_dir, outname)

    input = open(filename, 'rb')
    output = open(outfile, 'wb')

    result = pisa.pisaDocument(input, output, path=filename)

    input.close()
    output.close()

    if result.err:
        print 'Error rendering %s: %s' % (filename, result.err)
        sys.exit(1)
    return outfile


def convert_to_png(infile, output_dir, options):
    if options.debug:
        print 'Converting %s to PNG' % infile
    basename = os.path.basename(infile)
    filename = os.path.splitext(basename)[0]
    outname = '%s.page%%0d.png' % filename
    globname = '%s.page*.png' % filename
    outfile = os.path.join(output_dir, outname)
    exec_cmd(options, options.convert_cmd, '-density', '150', infile, outfile)
    outfiles = glob.glob(os.path.join(output_dir, globname))
    outfiles.sort()
    return outfiles


def create_diff_image(srcfile1, srcfile2, output_dir, options):
    if options.debug:
        print 'Creating difference image for %s and %s' % (srcfile1, srcfile2)

    outname = '%s.diff%s' % os.path.splitext(srcfile1)
    outfile = os.path.join(output_dir, outname)
    _, result = exec_cmd(options, options.compare_cmd, '-metric', 'ae', srcfile1, srcfile2, '-lowlight-color', 'white', outfile)
    diff_value = int(result.strip())
    if diff_value > 0:
        if not options.quiet:
            print 'Image %s differs from reference, value is %i' % (srcfile1, diff_value)
    return outfile, diff_value


def copy_ref_image(srcname, output_dir, options):
    if options.debug:
        print 'Copying reference image %s ' % srcname
    dstname = os.path.basename(srcname)
    dstfile = os.path.join(output_dir, '%s.ref%s' % os.path.splitext(dstname))
    shutil.copyfile(srcname, dstfile)
    return dstfile


def create_thumbnail(filename, options):
    thumbfile = '%s.thumb%s' % os.path.splitext(filename)
    if options.debug:
        print 'Creating thumbnail of %s' % filename
    exec_cmd(options, options.convert_cmd, '-resize', '20%', filename, thumbfile)
    return thumbfile


def render_file(filename, output_dir, ref_dir, options):
    if not options.quiet:
        print 'Rendering %s' % filename
    pdf = render_pdf(filename, output_dir, options)
    pngs = convert_to_png(pdf, output_dir, options)
    if options.create_reference:
        return None, None, 0
    thumbs = [create_thumbnail(png, options) for png in pngs]
    pages = [{'png': p, 'png_thumb': thumbs[i]}
             for i,p in enumerate(pngs)]
    diff_count = 0
    if not options.no_compare:
        for page in pages:
            refsrc = os.path.join(ref_dir, os.path.basename(page['png']))
            if not os.path.isfile(refsrc):
                print 'Reference image for %s not found!' % page['png']
                continue
            page['ref'] = copy_ref_image(refsrc, output_dir, options)
            page['ref_thumb'] = create_thumbnail(page['ref'], options)
            page['diff'], page['diff_value'] = \
                    create_diff_image(page['png'], page['ref'],
                                      output_dir, options)
            page['diff_thumb'] = create_thumbnail(page['diff'], options)
            if page['diff_value']:
                diff_count += 1
    return pdf, pages, diff_count


def exec_cmd(options, *args):
    if options.debug:
        print 'Executing %s' % ' '.join(args)
    proc = Popen(args, stdout=PIPE, stderr=PIPE)
    result = proc.communicate()
    if options.debug:
        print result[0], result[1]
    if proc.returncode:
        print 'exec error (%i): %s' % (proc.returncode, result[1])
        sys.exit(1)
    return result[0], result[1]


def create_html_file(results, template_file, output_dir, options):
    html = []
    for pdf, pages, diff_count in results:
        if options.only_errors and not diff_count:
            continue
        pdfname = os.path.basename(pdf)
        html.append('<div class="result">\n'
                    '<h2><a href="%(pdf)s" class="pdf-file">%(pdf)s</a></h2>\n'
                    % {'pdf': pdfname})
        for i, page in enumerate(pages):
            vars = dict(((k, os.path.basename(v)) for k,v in page.items()
                         if k != 'diff_value'))
            vars['page'] = i+1
            if 'diff' in page:
                vars['diff_value'] = page['diff_value']
                if vars['diff_value']:
                    vars['class'] = 'result-page-diff error'
                else:
                    if options.only_errors:
                        continue
                    vars['class'] = 'result-page-diff'
                html.append('<div class="%(class)s">\n'
                            '<h3>Page %(page)i</h3>\n'

                            '<div class="result-img">\n'
                            '<div class="result-type">Difference '
                            '(Score %(diff_value)i)</div>\n'
                            '<a href="%(diff)s" class="diff-file">'
                            '<img src="%(diff_thumb)s"/></a>\n'
                            '</div>\n'

                            '<div class="result-img">\n'
                            '<div class="result-type">Rendered</div>\n'
                            '<a href="%(png)s" class="png-file">'
                            '<img src="%(png_thumb)s"/></a>\n'
                            '</div>\n'

                            '<div class="result-img">\n'
                            '<div class="result-type">Reference</div>\n'
                            '<a href="%(ref)s" class="ref-file">'
                            '<img src="%(ref_thumb)s"/></a>\n'
                            '</div>\n'

                            '</div>\n' % vars)
            else:
                html.append('<div class="result-page">\n'
                           '<h3>Page %(page)i</h3>\n'

                           '<div class="result-img">\n'
                           '<a href="%(png)s" class="png-file">'
                           '<img src="%(png_thumb)s"/></a>\n'
                           '</div>\n'

                           '</div>\n' % vars)
        html.append('</div>\n\n')

    now = datetime.datetime.now()
    title = 'xhtml2pdf Test Rendering Results, %s' % now.strftime('%c')
    template = open(template_file, 'rb').read()
    template = template.replace('%%TITLE%%', title)
    template = template.replace('%%RESULTS%%', '\n'.join(html))

    htmlfile = os.path.join(output_dir, 'index.html')
    outfile = open(htmlfile, 'wb')
    outfile.write(template)
    outfile.close()
    return htmlfile


def main():
    options, args = parser.parse_args()

    base_dir = os.path.abspath(os.path.join(__file__, os.pardir))
    source_dir = os.path.join(base_dir, options.source_dir)
    if options.create_reference is not None:
        output_dir = os.path.join(base_dir, options.create_reference)
    else:
        output_dir = os.path.join(base_dir, options.output_dir)
    template_file = os.path.join(base_dir, options.html_template)
    ref_dir = os.path.join(base_dir, options.ref_dir)

    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir)

    results = []
    diff_count = 0
    if len(args) == 0:
        files = glob.glob(os.path.join(source_dir, '*.html'))
    else:
        files = [os.path.join(source_dir, arg) for arg in args]
    for filename in files:
        pdf, pages, diff = render_file(filename, output_dir, ref_dir, options)
        diff_count += diff
        results.append((pdf, pages, diff))

    num = len(results)

    if options.create_reference is not None:
        print 'Created reference for %i file%s' % (num, '' if num == 1 else 's')
    else:
        htmlfile = create_html_file(results, template_file, output_dir, options)
        if not options.quiet:
            print 'Rendered %i file%s' % (num, '' if num == 1 else 's')
            print '%i file%s differ%s from reference' % \
                    (diff_count, diff_count != 1 and 's' or '',
                     diff_count == 1 and 's' or '')
            print 'Check %s for results' % htmlfile
        if diff_count:
            sys.exit(1)


parser = OptionParser(
    usage='rendertest.py [options] [source_file] [source_file] ...',
    description='Renders a single html source file or all files in the data '
    'directory, converts them to PNG format and prepares a result '
    'HTML file for comparing the output with an expected result')
parser.add_option('-s', '--source-dir', dest='source_dir', default='data/source',
                  help=('Path to directory containing the html source files'))
parser.add_option('-o', '--output-dir', dest='output_dir', default='output',
                  help='Path to directory for output files. CAREFUL: this '
                  'directory will be deleted and recreated before rendering!')
parser.add_option('-r', '--ref-dir', dest='ref_dir', default='data/reference',
                  help='Path to directory containing the reference images '
                  'to compare the result with')
parser.add_option('-t', '--template', dest='html_template',
                  default='data/template.html', help='Name of HTML template file')
parser.add_option('-e', '--only-errors', dest='only_errors', action='store_true',
                  default=False, help='Only include images in HTML file which '
                  'differ from reference')
parser.add_option('-q', '--quiet', dest='quiet', action='store_true',
                  default=False, help='Try to be quiet')
parser.add_option('--no-compare', dest='no_compare', action='store_true',
                  default=False, help='Do not compare with reference image, '
                  'only render to png')
parser.add_option('-c', '--create-reference', dest='create_reference',
                  metavar='DIR',
                  default=None, help='Do not output anything, render source to '
                  'specified directory for reference. CAREFUL: this directory '
                 'will be deleted and recreated before rendering!')
parser.add_option('--debug', dest='debug', action='store_true',
                  default=False, help='More output for debugging')
parser.add_option('--convert-cmd', dest='convert_cmd', default='/usr/bin/convert',
                  help='Path to ImageMagick "convert" tool')
parser.add_option('--compare-cmd', dest='compare_cmd', default='/usr/bin/compare',
                  help='Path to ImageMagick "compare" tool')

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = runtests
import sys
import os
import glob
import unittest

#Allow us to import the parent module
os.chdir(os.path.split(os.path.abspath(__file__))[0])
sys.path.insert(0, os.path.abspath(os.curdir))
sys.path.insert(0, os.path.abspath(os.pardir))
# sys.path.insert(0, os.path.join(os.path.abspath(os.pardir), "src"))

def buildTestSuite():
    suite = unittest.TestSuite()
    for testcase in glob.glob('test_*.py'):
        module = os.path.splitext(testcase)[0]
        suite.addTest(__import__(module).buildTestSuite())
    return suite

def main():
    results = unittest.TextTestRunner().run(buildTestSuite())
    return results

if __name__ == "__main__":
    results = main()
    if not results.wasSuccessful():
        sys.exit(1)

########NEW FILE########
__FILENAME__ = test_parser
import unittest
from xhtml2pdf.parser import pisaParser
from xhtml2pdf.context import pisaContext

_data = """
<!doctype html>
<html>
<title>TITLE</title>
<body>
BODY
</body>
</html>
"""

class TestCase(unittest.TestCase):

    def testParser(self):
        c = pisaContext(".")
        r = pisaParser(_data, c)
        self.assertEqual(c, r)

    def test_getFile(self):
        c = pisaContext(".")
        r = pisaParser(_data, c)
        self.assertEqual(c.getFile(None), None)

def buildTestSuite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)

def main():
    buildTestSuite()
    unittest.main()

if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = test_utils
#-*- coding: utf-8 -*-
from reportlab.lib.colors import Color
from unittest import TestCase
from xhtml2pdf.util import getCoords, getColor, getSize, getFrameDimensions, \
    getPos, getBox
from xhtml2pdf.tags import int_to_roman

class UtilsCoordTestCase(TestCase):

    def test_getCoords_simple(self):
        
        res = getCoords(1, 1, 10, 10, (10,10))
        self.assertEqual(res, (1, -1, 10, 10))
        
        # A second time - it's memoized!
        res = getCoords(1, 1, 10, 10, (10,10))
        self.assertEqual(res, (1, -1, 10, 10))
        
    def test_getCoords_x_lt_0(self):
        res = getCoords(-1, 1, 10, 10, (10,10))
        self.assertEqual(res, (9, -1, 10, 10))
        
    def test_getCoords_y_lt_0(self):
        res = getCoords(1, -1, 10, 10, (10,10))
        self.assertEqual(res, (1, -9, 10, 10))
        
    def test_getCoords_w_and_h_none(self):
        res = getCoords(1, 1, None, None, (10,10))
        self.assertEqual(res, (1, 9))
        
    def test_getCoords_w_lt_0(self):
        res = getCoords(1, 1, -1, 10, (10,10))
        self.assertEqual(res, (1, -1, 8, 10))
        
    def test_getCoords_h_lt_0(self):
        res = getCoords(1, 1, 10, -1, (10,10))
        self.assertEqual(res, (1, 1, 10, 8))

class UtilsColorTestCase(TestCase):
    
    def test_get_color_simple(self):
        res = getColor('red')
        self.assertEqual(res, Color(1,0,0,1))
        
        # Testing it being memoized properly
        res = getColor('red')
        self.assertEqual(res, Color(1,0,0,1))
        
    def test_get_color_from_color(self):
        # Noop if argument is already a color
        res = getColor(Color(1,0,0,1))
        self.assertEqual(res, Color(1,0,0,1))
        
    def test_get_transparent_color(self):
        res = getColor('transparent', default='TOKEN')
        self.assertEqual(res, 'TOKEN')
        
        res = getColor('none', default='TOKEN')
        self.assertEqual(res, 'TOKEN')
        
    def test_get_color_for_none(self):
        res = getColor(None, default='TOKEN')
        self.assertEqual(res, 'TOKEN')
        
    def test_get_color_for_RGB(self):
        res = getColor('#FF0000')
        self.assertEqual(res, Color(1,0,0,1))
    
    def test_get_color_for_RGB_with_len_4(self):
        res = getColor('#F00')
        self.assertEqual(res, Color(1,0,0,1))
    
    def test_get_color_for_CSS_RGB_function(self):
        # It's regexp based, let's try common cases.
        res = getColor('rgb(255,0,0)')
        self.assertEqual(res, Color(1,0,0,1))
        
        res = getColor('<css function: rgb(255,0,0)>')
        self.assertEqual(res, Color(1,0,0,1))
        
class UtilsGetSizeTestCase(TestCase):
    
    def test_get_size_simple(self):
        res = getSize('12pt')
        self.assertEqual(res, 12.00)
        
        # Memoized...
        res = getSize('12pt')
        self.assertEqual(res, 12.00)
    
    def test_get_size_for_none(self):
        res = getSize(None, relative='TOKEN')
        self.assertEqual(res, 'TOKEN')
        
    def test_get_size_for_float(self):
        res = getSize(12.00)
        self.assertEqual(res, 12.00)
        
    def test_get_size_for_tuple(self):
        # TODO: This is a really strange case. Probably should not work this way.
        res = getSize(("12", ".12"))
        self.assertEqual(res, 12.12)
        
    def test_get_size_for_cm(self):
        res = getSize("1cm")
        self.assertEqual(res, 28.346456692913385)
        
    def test_get_size_for_mm(self):
        res = getSize("1mm")
        self.assertEqual(res, 2.8346456692913385)
        
    def test_get_size_for_i(self):
        res = getSize("1i")
        self.assertEqual(res, 72.00)
        
    def test_get_size_for_in(self):
        res = getSize("1in")
        self.assertEqual(res, 72.00)
        
    def test_get_size_for_inch(self):
        res = getSize("1in")
        self.assertEqual(res, 72.00)
        
    def test_get_size_for_pc(self):
        res = getSize("1pc")
        self.assertEqual(res, 12.00)
        
    def test_get_size_for_none_str(self):
        res = getSize("none")
        self.assertEqual(res, 0.0)
        res = getSize("0")
        self.assertEqual(res, 0.0)
        res = getSize("auto") # Really?
        self.assertEqual(res, 0.0)
        
class PisaDimensionTestCase(TestCase):
        
    def test_FrameDimensions_left_top_width_height(self):
        #builder = pisaCSSBuilder(mediumSet=['all'])
        dims = {
            'left': '10pt',
            'top': '20pt',
            'width': '30pt',
            'height': '40pt',
        }
        expected = (10.0, 20.0, 30.0, 40.0)
        result = getFrameDimensions(dims, 100, 200)
        self.assertEquals(expected, result)
    
    def test_FrameDimensions_left_top_bottom_right(self):
        dims = {
            'left': '10pt',
            'top': '20pt',
            'bottom': '30pt',
            'right': '40pt',
        }
        expected = (10.0, 20.0, 50.0, 150.0)
        result = getFrameDimensions(dims, 100, 200)
        self.assertEquals(expected, result)

    def test_FrameDimensions_bottom_right_width_height(self):
        dims = {
            'bottom': '10pt',
            'right': '20pt',
            'width': '70pt',
            'height': '80pt',
        }
        expected = (10.0, 110.0, 70.0, 80.0)
        result = getFrameDimensions(dims, 100, 200)
        self.assertEquals(expected, result)
    
    def test_FrameDimensions_left_top_width_height_with_margin(self):
        dims = {
            'left': '10pt',
            'top': '20pt',
            'width': '70pt',
            'height': '80pt',
            'margin-top': '10pt',
            'margin-left': '15pt',
            'margin-bottom': '20pt',
            'margin-right': '25pt',
        }
        expected = (25.0, 30.0, 30.0, 50.0)
        result = getFrameDimensions(dims, 100, 200)
        self.assertEquals(expected, result)
    
    def test_FrameDimensions_bottom_right_width_height_with_margin(self):
        dims = {
            'bottom': '10pt',
            'right': '20pt',
            'width': '70pt',
            'height': '80pt',
            'margin-top': '10pt',
            'margin-left': '15pt',
            'margin-bottom': '20pt',
            'margin-right': '25pt',
        }
        expected = (25.0, 120.0, 30.0, 50.0)
        result = getFrameDimensions(dims, 100, 200)
        self.assertEquals(expected, result)
        
    def test_frame_dimensions_for_box_len_eq_4(self):
        dims = {
                '-pdf-frame-box': ['12pt','12,pt','12pt','12pt']
                }
        expected = [12.0, 12.0, 12.0, 12.0]
        result = getFrameDimensions(dims, 100, 200)
        self.assertEqual(result, expected)
        
    def test_trame_dimentions_for_height_without_top_or_bottom(self):
        dims = {
            'left': '10pt',
            #'top': '20pt',
            'width': '30pt',
            'height': '40pt',
        }
        expected = (10.0, 0.0, 30.0, 200.0)
        result = getFrameDimensions(dims, 100, 200)
        self.assertEquals(expected, result)
        
    def test_trame_dimentions_for_width_without_left_or_right(self):
        dims = {
            #'left': '10pt',
            'top': '20pt',
            'width': '30pt',
            'height': '40pt',
        }
        expected = (0.0, 20.0, 100.0, 40.0)
        result = getFrameDimensions(dims, 100, 200)
        self.assertEquals(expected, result)
        
class GetPosTestCase(TestCase):
    def test_get_pos_simple(self):
        res = getBox("1pt 1pt 10pt 10pt", (10,10))
        self.assertEqual(res,(1.0, -1.0, 10, 10))
        
    def test_get_pos_raising(self):
        raised = False
        try:
            getBox("1pt 1pt 10pt", (10,10))
        except Exception:
            raised = True
        self.assertTrue(raised)

class TestTagUtils(TestCase):
    def test_roman_numeral_conversion(self):
        self.assertEqual("I", int_to_roman(1))
        self.assertEqual("L", int_to_roman(50))
        self.assertEqual("XLII", int_to_roman(42))
        self.assertEqual("XXVI", int_to_roman(26))
        
########NEW FILE########
__FILENAME__ = context
# -*- coding: utf-8 -*-
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.frames import Frame, ShowBoundaryValue
from reportlab.platypus.paraparser import ParaFrag, ps2tt, tt2ps
from xhtml2pdf.util import getSize, getCoords, getFile, pisaFileObject, \
    getFrameDimensions, getColor
from xhtml2pdf.w3c import css
from xhtml2pdf.xhtml2pdf_reportlab import PmlPageTemplate, PmlTableOfContents, \
    PmlParagraph, PmlParagraphAndImage, PmlPageCount
import copy
import logging
import os
import re
import reportlab
import types
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import xhtml2pdf.default
import xhtml2pdf.parser

# Copyright 2010 Dirk Holtwick, holtwick.it
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

reportlab.rl_config.warnOnMissingFontGlyphs = 0

log = logging.getLogger("xhtml2pdf")

sizeDelta = 2       # amount to reduce font size by for super and sub script
subFraction = 0.4   # fraction of font size that a sub script should be lowered
superFraction = 0.4

NBSP = u"\u00a0"


def clone(self, **kwargs):
    n = ParaFrag(**self.__dict__)
    if kwargs:
        d = n.__dict__
        d.update(kwargs)
        # This else could cause trouble in Paragraphs with images etc.
        if "cbDefn" in d:
            del d["cbDefn"]
    n.bulletText = None
    return n


ParaFrag.clone = clone


def getParaFrag(style):
    frag = ParaFrag()
    frag.sub = 0
    frag.super = 0
    frag.rise = 0
    frag.underline = 0  # XXX Need to be able to set color to fit CSS tests
    frag.strike = 0
    frag.greek = 0
    frag.link = None
    frag.text = ""
    frag.fontName = "Times-Roman"
    frag.fontName, frag.bold, frag.italic = ps2tt(style.fontName)
    frag.fontSize = style.fontSize
    frag.textColor = style.textColor

    # Extras
    frag.leading = 0
    frag.letterSpacing = "normal"
    frag.leadingSource = "150%"
    frag.leadingSpace = 0
    frag.backColor = None
    frag.spaceBefore = 0
    frag.spaceAfter = 0
    frag.leftIndent = 0
    frag.rightIndent = 0
    frag.firstLineIndent = 0
    frag.keepWithNext = False
    frag.alignment = TA_LEFT
    frag.vAlign = None

    frag.borderWidth = 1
    frag.borderStyle = None
    frag.borderPadding = 0
    frag.borderColor = None

    frag.borderLeftWidth = frag.borderWidth
    frag.borderLeftColor = frag.borderColor
    frag.borderLeftStyle = frag.borderStyle
    frag.borderRightWidth = frag.borderWidth
    frag.borderRightColor = frag.borderColor
    frag.borderRightStyle = frag.borderStyle
    frag.borderTopWidth = frag.borderWidth
    frag.borderTopColor = frag.borderColor
    frag.borderTopStyle = frag.borderStyle
    frag.borderBottomWidth = frag.borderWidth
    frag.borderBottomColor = frag.borderColor
    frag.borderBottomStyle = frag.borderStyle

    frag.paddingLeft = 0
    frag.paddingRight = 0
    frag.paddingTop = 0
    frag.paddingBottom = 0

    frag.listStyleType = None
    frag.listStyleImage = None
    frag.whiteSpace = "normal"

    frag.wordWrap = None

    frag.pageNumber = False
    frag.pageCount = False
    frag.height = None
    frag.width = None

    frag.bulletIndent = 0
    frag.bulletText = None
    frag.bulletFontName = "Helvetica"

    frag.zoom = 1.0

    frag.outline = False
    frag.outlineLevel = 0
    frag.outlineOpen = False

    frag.insideStaticFrame = 0

    return frag


def getDirName(path):
    parts = urlparse.urlparse(path)
    if parts.scheme:
        return path
    else:
        return os.path.dirname(os.path.abspath(path))


class pisaCSSBuilder(css.CSSBuilder):
    def atFontFace(self, declarations):
        """
        Embed fonts
        """
        result = self.ruleset([self.selector('*')], declarations)
        data = result[0].values()[0]
        if "src" not in data:
            # invalid - source is required, ignore this specification
            return {}, {}
        names = data["font-family"]

        # Font weight
        fweight = str(data.get("font-weight", "normal")).lower()
        bold = fweight in ("bold", "bolder", "500", "600", "700", "800", "900")
        if not bold and fweight != "normal":
            log.warn(self.c.warning("@fontface, unknown value font-weight '%s'", fweight))

        # Font style
        italic = str(data.get("font-style", "")).lower() in ("italic", "oblique")

        src = self.c.getFile(data["src"], relative=self.c.cssParser.rootPath)
        self.c.loadFont(
            names,
            src,
            bold=bold,
            italic=italic)
        return {}, {}

    def _pisaAddFrame(self, name, data, first=False, border=None, size=(0, 0)):
        c = self.c
        if not name:
            name = "-pdf-frame-%d" % c.UID()
        if data.get('is_landscape', False):
            size = (size[1], size[0])
        x, y, w, h = getFrameDimensions(data, size[0], size[1])
        # print name, x, y, w, h
        #if not (w and h):
        #    return None
        if first:
            return name, None, data.get("-pdf-frame-border", border), x, y, w, h, data

        return (name, data.get("-pdf-frame-content", None),
                data.get("-pdf-frame-border", border), x, y, w, h, data)

    def _getFromData(self, data, attr, default=None, func=None):
        if not func:
            func = lambda x: x

        if type(attr) in (list, tuple):
            for a in attr:
                if a in data:
                    return func(data[a])
                return default
        else:
            if attr in data:
                return func(data[attr])
            return default

    def atPage(self, name, pseudopage, declarations):
        c = self.c
        data = {}
        name = name or "body"
        pageBorder = None

        if declarations:
            result = self.ruleset([self.selector('*')], declarations)

            if declarations:
                data = result[0].values()[0]
                pageBorder = data.get("-pdf-frame-border", None)

        if name in c.templateList:
            log.warn(self.c.warning("template '%s' has already been defined", name))

        if "-pdf-page-size" in data:
            c.pageSize = xhtml2pdf.default.PML_PAGESIZES.get(str(data["-pdf-page-size"]).lower(), c.pageSize)

        isLandscape = False
        if "size" in data:
            size = data["size"]
            if type(size) is not types.ListType:
                size = [size]
            sizeList = []
            for value in size:
                valueStr = str(value).lower()
                if type(value) is types.TupleType:
                    sizeList.append(getSize(value))
                elif valueStr == "landscape":
                    isLandscape = True
                elif valueStr in xhtml2pdf.default.PML_PAGESIZES:
                    c.pageSize = xhtml2pdf.default.PML_PAGESIZES[valueStr]
                else:
                    log.warn(c.warning("Unknown size value for @page"))

            if len(sizeList) == 2:
                c.pageSize = tuple(sizeList)
            if isLandscape:
                c.pageSize = landscape(c.pageSize)

        padding_top = self._getFromData(data, 'padding-top', 0, getSize)
        padding_left = self._getFromData(data, 'padding-left', 0, getSize)
        padding_right = self._getFromData(data, 'padding-right', 0, getSize)
        padding_bottom = self._getFromData(data, 'padding-bottom', 0, getSize)
        border_color = self._getFromData(data, ('border-top-color', 'border-bottom-color',\
                                                'border-left-color', 'border-right-color'), None, getColor)
        border_width = self._getFromData(data, ('border-top-width', 'border-bottom-width',\
                                                'border-left-width', 'border-right-width'), 0, getSize)

        for prop in ("margin-top", "margin-left", "margin-right", "margin-bottom",
                     "top", "left", "right", "bottom", "width", "height"):
            if prop in data:
                c.frameList.append(self._pisaAddFrame(name, data, first=True, border=pageBorder, size=c.pageSize))
                break

        # Frames have to be calculated after we know the pagesize
        frameList = []
        staticList = []
        for fname, static, border, x, y, w, h, fdata in c.frameList:
            fpadding_top = self._getFromData(fdata, 'padding-top', padding_top, getSize)
            fpadding_left = self._getFromData(fdata, 'padding-left', padding_left, getSize)
            fpadding_right = self._getFromData(fdata, 'padding-right', padding_right, getSize)
            fpadding_bottom = self._getFromData(fdata, 'padding-bottom', padding_bottom, getSize)
            fborder_color = self._getFromData(fdata, ('border-top-color', 'border-bottom-color',\
                                                      'border-left-color', 'border-right-color'), border_color, getColor)
            fborder_width = self._getFromData(fdata, ('border-top-width', 'border-bottom-width',\
                                                      'border-left-width', 'border-right-width'), border_width, getSize)

            if border or pageBorder:
                frame_border = ShowBoundaryValue()
            else:
                frame_border = ShowBoundaryValue(color=fborder_color, width=fborder_width)

            #fix frame sizing problem.
            if static:
                x, y, w, h = getFrameDimensions(fdata, c.pageSize[0], c.pageSize[1])
            x, y, w, h = getCoords(x, y, w, h, c.pageSize)
            if w <= 0 or h <= 0:
                log.warn(self.c.warning("Negative width or height of frame. Check @frame definitions."))

            frame = Frame(
                x, y, w, h,
                id=fname,
                leftPadding=fpadding_left,
                rightPadding=fpadding_right,
                bottomPadding=fpadding_bottom,
                topPadding=fpadding_top,
                showBoundary=frame_border)

            if static:
                frame.pisaStaticStory = []
                c.frameStatic[static] = [frame] + c.frameStatic.get(static, [])
                staticList.append(frame)
            else:
                frameList.append(frame)

        background = data.get("background-image", None)
        if background:
            #should be relative to the css file
            background = self.c.getFile(background, relative=self.c.cssParser.rootPath)

        if not frameList:
            log.warn(c.warning("missing explicit frame definition for content or just static frames"))
            fname, static, border, x, y, w, h, data = self._pisaAddFrame(name, data, first=True, border=pageBorder,
                                                                         size=c.pageSize)
            x, y, w, h = getCoords(x, y, w, h, c.pageSize)
            if w <= 0 or h <= 0:
                log.warn(c.warning("Negative width or height of frame. Check @page definitions."))

            if border or pageBorder:
                frame_border = ShowBoundaryValue()
            else:
                frame_border = ShowBoundaryValue(color=border_color, width=border_width)

            frameList.append(Frame(
                x, y, w, h,
                id=fname,
                leftPadding=padding_left,
                rightPadding=padding_right,
                bottomPadding=padding_bottom,
                topPadding=padding_top,
                showBoundary=frame_border))

        pt = PmlPageTemplate(
            id=name,
            frames=frameList,
            pagesize=c.pageSize,
        )
        pt.pisaStaticList = staticList
        pt.pisaBackground = background
        pt.pisaBackgroundList = c.pisaBackgroundList

        if isLandscape:
            pt.pageorientation = pt.LANDSCAPE

        c.templateList[name] = pt
        c.template = None
        c.frameList = []
        c.frameStaticList = []

        return {}, {}

    def atFrame(self, name, declarations):
        if declarations:
            result = self.ruleset([self.selector('*')], declarations)
            # print "@BOX", name, declarations, result

            data = result[0]
            if data:
                data = data.values()[0]
                self.c.frameList.append(
                    self._pisaAddFrame(name, data, size=self.c.pageSize))

        return {}, {} # TODO: It always returns empty dicts?


class pisaCSSParser(css.CSSParser):
    def parseExternal(self, cssResourceName):

        oldRootPath = self.rootPath
        cssFile = self.c.getFile(cssResourceName, relative=self.rootPath)
        if not cssFile:
            return None
        if self.rootPath and urlparse.urlparse(self.rootPath).scheme:
            self.rootPath = urlparse.urljoin(self.rootPath, cssResourceName)
        else:
            self.rootPath = getDirName(cssFile.uri)

        result = self.parse(cssFile.getData())
        self.rootPath = oldRootPath
        return result


class pisaContext(object):
    """
    Helper class for creation of reportlab story and container for
    various data.
    """

    def __init__(self, path, debug=0, capacity=-1):
        self.fontList = copy.copy(xhtml2pdf.default.DEFAULT_FONT)
        self.path = []
        self.capacity = capacity

        self.node = None
        self.toc = PmlTableOfContents()
        self.story = []
        self.indexing_story = None
        self.text = []
        self.log = []
        self.err = 0
        self.warn = 0
        self.text = u""
        self.uidctr = 0
        self.multiBuild = False

        self.pageSize = A4
        self.template = None
        self.templateList = {}

        self.frameList = []
        self.frameStatic = {}
        self.frameStaticList = []
        self.pisaBackgroundList = []

        self.keepInFrameIndex = None

        self.baseFontSize = getSize("12pt")

        self.anchorFrag = []
        self.anchorName = []

        self.tableData = None

        self.frag = self.fragBlock = getParaFrag(ParagraphStyle('default%d' % self.UID()))
        self.fragList = []
        self.fragAnchor = []
        self.fragStack = []
        self.fragStrip = True

        self.listCounter = 0

        self.cssText = ""
        self.cssDefaultText = ""

        self.image = None
        self.imageData = {}
        self.force = False

        self.pathCallback = None # External callback function for path calculations

        # Store path to document
        self.pathDocument = path or "__dummy__"
        parts = urlparse.urlparse(self.pathDocument)
        if not parts.scheme:
            self.pathDocument = os.path.abspath(self.pathDocument)
        self.pathDirectory = getDirName(self.pathDocument)

        self.meta = dict(
            author="",
            title="",
            subject="",
            keywords="",
            pagesize=A4,
        )

    def UID(self):
        self.uidctr += 1
        return self.uidctr

    # METHODS FOR CSS
    def addCSS(self, value):
        value = value.strip()
        if value.startswith("<![CDATA["):
            value = value[9: - 3]
        if value.startswith("<!--"):
            value = value[4: - 3]
        self.cssText += value.strip() + "\n"

    # METHODS FOR CSS
    def addDefaultCSS(self, value):
        value = value.strip()
        if value.startswith("<![CDATA["):
            value = value[9: - 3]
        if value.startswith("<!--"):
            value = value[4: - 3]
        self.cssDefaultText += value.strip() + "\n"

    def parseCSS(self):
        # This self-reference really should be refactored. But for now
        # we'll settle for using weak references. This avoids memory
        # leaks because the garbage collector (at least on cPython
        # 2.7.3) isn't aggressive enough.
        import weakref

        self.cssBuilder = pisaCSSBuilder(mediumSet=["all", "print", "pdf"])
        #self.cssBuilder.c = self
        self.cssBuilder._c = weakref.ref(self)
        pisaCSSBuilder.c = property(lambda self: self._c())

        self.cssParser = pisaCSSParser(self.cssBuilder)
        self.cssParser.rootPath = self.pathDirectory
        #self.cssParser.c = self
        self.cssParser._c = weakref.ref(self)
        pisaCSSParser.c = property(lambda self: self._c())

        self.css = self.cssParser.parse(self.cssText)
        self.cssDefault = self.cssParser.parse(self.cssDefaultText)
        self.cssCascade = css.CSSCascadeStrategy(userAgent=self.cssDefault, user=self.css)
        self.cssCascade.parser = self.cssParser

    # METHODS FOR STORY
    def addStory(self, data):
        self.story.append(data)

    def swapStory(self, story=[]):
        self.story, story = copy.copy(story), copy.copy(self.story)
        return story

    def toParagraphStyle(self, first):
        style = ParagraphStyle('default%d' % self.UID(), keepWithNext=first.keepWithNext)
        style.fontName = first.fontName
        style.fontSize = first.fontSize
        style.letterSpacing = first.letterSpacing
        style.leading = max(first.leading + first.leadingSpace, first.fontSize * 1.25)
        style.backColor = first.backColor
        style.spaceBefore = first.spaceBefore
        style.spaceAfter = first.spaceAfter
        style.leftIndent = first.leftIndent
        style.rightIndent = first.rightIndent
        style.firstLineIndent = first.firstLineIndent
        style.textColor = first.textColor
        style.alignment = first.alignment
        style.bulletFontName = first.bulletFontName or first.fontName
        style.bulletFontSize = first.fontSize
        style.bulletIndent = first.bulletIndent
        style.wordWrap = first.wordWrap

        # Border handling for Paragraph

        # Transfer the styles for each side of the border, *not* the whole
        # border values that reportlab supports. We'll draw them ourselves in
        # PmlParagraph.
        style.borderTopStyle = first.borderTopStyle
        style.borderTopWidth = first.borderTopWidth
        style.borderTopColor = first.borderTopColor
        style.borderBottomStyle = first.borderBottomStyle
        style.borderBottomWidth = first.borderBottomWidth
        style.borderBottomColor = first.borderBottomColor
        style.borderLeftStyle = first.borderLeftStyle
        style.borderLeftWidth = first.borderLeftWidth
        style.borderLeftColor = first.borderLeftColor
        style.borderRightStyle = first.borderRightStyle
        style.borderRightWidth = first.borderRightWidth
        style.borderRightColor = first.borderRightColor

        # If no border color is given, the text color is used (XXX Tables!)
        if (style.borderTopColor is None) and style.borderTopWidth:
            style.borderTopColor = first.textColor
        if (style.borderBottomColor is None) and style.borderBottomWidth:
            style.borderBottomColor = first.textColor
        if (style.borderLeftColor is None) and style.borderLeftWidth:
            style.borderLeftColor = first.textColor
        if (style.borderRightColor is None) and style.borderRightWidth:
            style.borderRightColor = first.textColor

        style.borderPadding = first.borderPadding

        style.paddingTop = first.paddingTop
        style.paddingBottom = first.paddingBottom
        style.paddingLeft = first.paddingLeft
        style.paddingRight = first.paddingRight
        style.fontName = tt2ps(first.fontName, first.bold, first.italic)

        return style

    def addTOC(self):
        styles = []
        for i in xrange(20):
            self.node.attributes["class"] = "pdftoclevel%d" % i
            self.cssAttr = xhtml2pdf.parser.CSSCollect(self.node, self)
            xhtml2pdf.parser.CSS2Frag(self, {
                "margin-top": 0,
                "margin-bottom": 0,
                "margin-left": 0,
                "margin-right": 0,
            }, True)
            pstyle = self.toParagraphStyle(self.frag)
            styles.append(pstyle)

        self.toc.levelStyles = styles
        self.addStory(self.toc)
        self.indexing_story = None

    def addPageCount(self):
        if not self.multiBuild:
            self.indexing_story = PmlPageCount()
            self.multiBuild = True

    def dumpPara(self, frags, style):
        return

    def addPara(self, force=False):

        force = (force or self.force)
        self.force = False

        # Cleanup the trail
        try:
            rfragList = reversed(self.fragList)
        except:
            # For Python 2.3 compatibility
            rfragList = copy.copy(self.fragList)
            rfragList.reverse()

        # Find maximum lead
        maxLeading = 0
        #fontSize = 0
        for frag in self.fragList:
            leading = getSize(frag.leadingSource, frag.fontSize) + frag.leadingSpace
            maxLeading = max(leading, frag.fontSize + frag.leadingSpace, maxLeading)
            frag.leading = leading

        if force or (self.text.strip() and self.fragList):

            # Update paragraph style by style of first fragment
            first = self.fragBlock
            style = self.toParagraphStyle(first)
            # style.leading = first.leading + first.leadingSpace
            if first.leadingSpace:
                style.leading = maxLeading
            else:
                style.leading = getSize(first.leadingSource, first.fontSize) + first.leadingSpace

            bulletText = copy.copy(first.bulletText)
            first.bulletText = None

            # Add paragraph to story
            if force or len(self.fragAnchor + self.fragList) > 0:

                # We need this empty fragment to work around problems in
                # Reportlab paragraphs regarding backGround etc.
                if self.fragList:
                    self.fragList.append(self.fragList[- 1].clone(text=''))
                else:
                    blank = self.frag.clone()
                    blank.fontName = "Helvetica"
                    blank.text = ''
                    self.fragList.append(blank)

                self.dumpPara(self.fragAnchor + self.fragList, style)
                para = PmlParagraph(
                    self.text,
                    style,
                    frags=self.fragAnchor + self.fragList,
                    bulletText=bulletText)

                para.outline = first.outline
                para.outlineLevel = first.outlineLevel
                para.outlineOpen = first.outlineOpen
                para.keepWithNext = first.keepWithNext
                para.autoLeading = "max"

                if self.image:
                    para = PmlParagraphAndImage(
                        para,
                        self.image,
                        side=self.imageData.get("align", "left"))

                self.addStory(para)

            self.fragAnchor = []
            first.bulletText = None

        # Reset data

        self.image = None
        self.imageData = {}

        self.clearFrag()

    # METHODS FOR FRAG
    def clearFrag(self):
        self.fragList = []
        self.fragStrip = True
        self.text = u""

    def copyFrag(self, **kw):
        return self.frag.clone(**kw)

    def newFrag(self, **kw):
        self.frag = self.frag.clone(**kw)
        return self.frag

    def _appendFrag(self, frag):
        if frag.link and frag.link.startswith("#"):
            self.anchorFrag.append((frag, frag.link[1:]))
        self.fragList.append(frag)

    # XXX Argument frag is useless!
    def addFrag(self, text="", frag=None):

        frag = baseFrag = self.frag.clone()

        # if sub and super are both on they will cancel each other out
        if frag.sub == 1 and frag.super == 1:
            frag.sub = 0
            frag.super = 0

        # XXX Has to be replaced by CSS styles like vertical-align and font-size
        if frag.sub:
            frag.rise = - frag.fontSize * subFraction
            frag.fontSize = max(frag.fontSize - sizeDelta, 3)
        elif frag.super:
            frag.rise = frag.fontSize * superFraction
            frag.fontSize = max(frag.fontSize - sizeDelta, 3)

       # bold, italic, and underline
        frag.fontName = frag.bulletFontName = tt2ps(frag.fontName, frag.bold, frag.italic)

        # Replace &shy; with empty and normalize NBSP
        text = (text
                .replace(u"\xad", u"")
                .replace(u"\xc2\xa0", NBSP)
                .replace(u"\xa0", NBSP))

        if frag.whiteSpace == "pre":

            # Handle by lines
            for text in re.split(r'(\r\n|\n|\r)', text):
                # This is an exceptionally expensive piece of code
                self.text += text
                if ("\n" in text) or ("\r" in text):
                    # If EOL insert a linebreak
                    frag = baseFrag.clone()
                    frag.text = ""
                    frag.lineBreak = 1
                    self._appendFrag(frag)
                else:
                    # Handle tabs in a simple way
                    text = text.replace(u"\t", 8 * u" ")
                    # Somehow for Reportlab NBSP have to be inserted
                    # as single character fragments
                    for text in re.split(r'(\ )', text):
                        frag = baseFrag.clone()
                        if text == " ":
                            text = NBSP
                        frag.text = text
                        self._appendFrag(frag)
        else:
            for text in re.split(u'(' + NBSP + u')', text):
                frag = baseFrag.clone()
                if text == NBSP:
                    self.force = True
                    frag.text = NBSP
                    self.text += text
                    self._appendFrag(frag)
                else:
                    frag.text = " ".join(("x" + text + "x").split())[1: - 1]
                    if self.fragStrip:
                        frag.text = frag.text.lstrip()
                        if frag.text:
                            self.fragStrip = False
                    self.text += frag.text
                    self._appendFrag(frag)

    def pushFrag(self):
        self.fragStack.append(self.frag)
        self.newFrag()

    def pullFrag(self):
        self.frag = self.fragStack.pop()

    # XXX
    def _getFragment(self, l=20):
        try:
            return repr(" ".join(self.node.toxml().split()[:l]))
        except:
            return ""

    def _getLineNumber(self):
        return 0

    def context(self, msg):
        return "%s\n%s" % (
            str(msg),
            self._getFragment(50))

    def warning(self, msg, *args):
        self.warn += 1
        self.log.append((xhtml2pdf.default.PML_WARNING, self._getLineNumber(), str(msg), self._getFragment(50)))
        try:
            return self.context(msg % args)
        except:
            return self.context(msg)

    def error(self, msg, *args):
        self.err += 1
        self.log.append((xhtml2pdf.default.PML_ERROR, self._getLineNumber(), str(msg), self._getFragment(50)))
        try:
            return self.context(msg % args)
        except:
            return self.context(msg)

    # UTILS
    def _getFileDeprecated(self, name, relative):
        try:
            path = relative or self.pathDirectory
            if name.startswith("data:"):
                return name
            if self.pathCallback is not None:
                nv = self.pathCallback(name, relative)
            else:
                if path is None:
                    log.warn("Could not find main directory for getting filename. Use CWD")
                    path = os.getcwd()
                nv = os.path.normpath(os.path.join(path, name))
                if not (nv and os.path.isfile(nv)):
                    nv = None
            if nv is None:
                log.warn(self.warning("File '%s' does not exist", name))
            return nv
        except:
            log.warn(self.warning("getFile %r %r %r", name, relative, path), exc_info=1)

    def getFile(self, name, relative=None):
        """
        Returns a file name or None
        """
        if self.pathCallback is not None:
            return getFile(self._getFileDeprecated(name, relative))
        return getFile(name, relative or self.pathDirectory)

    def getFontName(self, names, default="helvetica"):
        """
        Name of a font
        """
        # print names, self.fontList
        if type(names) is not types.ListType:
            if type(names) not in types.StringTypes:
                names = str(names)
            names = names.strip().split(",")
        for name in names:
            if type(name) not in types.StringTypes:
                name = str(name)
            font = self.fontList.get(name.strip().lower(), None)
            if font is not None:
                return font
        return self.fontList.get(default, None)

    def registerFont(self, fontname, alias=[]):
        self.fontList[str(fontname).lower()] = str(fontname)
        for a in alias:
            if type(fontname) not in types.StringTypes:
                fontname = str(fontname)
            self.fontList[str(a)] = fontname

    def loadFont(self, names, src, encoding="WinAnsiEncoding", bold=0, italic=0):

        # XXX Just works for local filenames!
        if names and src:

            file = src
            src = file.uri

            log.debug("Load font %r", src)

            if type(names) is types.ListType:
                fontAlias = names
            else:
                fontAlias = (x.lower().strip() for x in names.split(",") if x)

            # XXX Problems with unicode here
            fontAlias = [str(x) for x in fontAlias]

            fontName = fontAlias[0]
            parts = src.split(".")
            baseName, suffix = ".".join(parts[: - 1]), parts[- 1]
            suffix = suffix.lower()

            if suffix in ["ttc", "ttf"]:

                # determine full font name according to weight and style
                fullFontName = "%s_%d%d" % (fontName, bold, italic)

                # check if font has already been registered
                if fullFontName in self.fontList:
                    log.warn(self.warning("Repeated font embed for %s, skip new embed ", fullFontName))
                else:

                    # Register TTF font and special name
                    filename = file.getNamedFile()
                    pdfmetrics.registerFont(TTFont(fullFontName, filename))

                    # Add or replace missing styles
                    for bold in (0, 1):
                        for italic in (0, 1):
                            if ("%s_%d%d" % (fontName, bold, italic)) not in self.fontList:
                                addMapping(fontName, bold, italic, fullFontName)

                    # Register "normal" name and the place holder for style
                    self.registerFont(fontName, fontAlias + [fullFontName])

            elif suffix in ("afm", "pfb"):

                if suffix == "afm":
                    afm = file.getNamedFile()
                    tfile = pisaFileObject(baseName + ".pfb")
                    pfb = tfile.getNamedFile()
                else:
                    pfb = file.getNamedFile()
                    tfile = pisaFileObject(baseName + ".afm")
                    afm = tfile.getNamedFile()

                # determine full font name according to weight and style
                fullFontName = "%s_%d%d" % (fontName, bold, italic)

                # check if font has already been registered
                if fullFontName in self.fontList:
                    log.warn(self.warning("Repeated font embed for %s, skip new embed", fontName))
                else:

                    # Include font
                    face = pdfmetrics.EmbeddedType1Face(afm, pfb)
                    fontNameOriginal = face.name
                    pdfmetrics.registerTypeFace(face)
                    # print fontName, fontNameOriginal, fullFontName
                    justFont = pdfmetrics.Font(fullFontName, fontNameOriginal, encoding)
                    pdfmetrics.registerFont(justFont)

                    # Add or replace missing styles
                    for bold in (0, 1):
                        for italic in (0, 1):
                            if ("%s_%d%d" % (fontName, bold, italic)) not in self.fontList:
                                addMapping(fontName, bold, italic, fontNameOriginal)

                    # Register "normal" name and the place holder for style
                    self.registerFont(fontName, fontAlias + [fullFontName, fontNameOriginal])
            else:
                log.warning(self.warning("wrong attributes for <pdf:font>"))


########NEW FILE########
__FILENAME__ = default
# -*- coding: utf-8 -*-
from reportlab.lib.pagesizes import (A0, A1, A2, A3, A4, A5, A6, B0, B1, B2, B3,
                                     B4, B5, B6, LETTER, LEGAL, ELEVENSEVENTEEN)

# Copyright 2010 Dirk Holtwick, holtwick.it
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

PML_WARNING = "warning"
PML_ERROR = "error"
PML_EXCEPTION = "PML Exception"
PML_PREFIX = "pdf:"

#CLASS   = 1
BOOL = 2
FONT = 3
COLOR = 4
FILE = 5
SIZE = 6
INT = 7
STRING = 8
BOX = 9
POS = 10
#STYLE   = 11
MUST = 23

"""
Definition of all known tags. Also used for building the reference
"""

TAGS = {

    # FORMAT

    #"document": (1, {
    #    "format":               (["a0", "a1", "a2", "a3", "a4", "a5", "a6",
    #                              "b0", "b1", "b2", "b3", "b4", "b5", "b6",
    #                              "letter", "legal", "elevenseventeen"], "a4"),
    #    "orientation":          ["portrait", "landscape"],
    #    "fullscreen":           (BOOL, "0"),
    #    "author":               (STRING, ""),
    #    "subject":              (STRING, ""),
    #    "title":                (STRING, ""),
    #    "duration":             INT,
    #    "showoutline":          (BOOL, "0"),
    #    "outline":              INT,
    #    }),

    "pdftemplate": (1, {
        "name": (STRING, "body"),
        "format": (["a0", "a1", "a2", "a3", "a4", "a5", "a6",
                    "b0", "b1", "b2", "b3", "b4", "b5", "b6",
                    "letter", "legal", "elevenseventeen"], "a4"),
        "orientation": ["portrait", "landscape"],
        "background": FILE,
    }),

    "pdfframe": (0, {
        "name": (STRING, ""),
        "box": (BOX, MUST),
        "border": (BOOL, "0"),
        "static": (BOOL, "0"),
    }),

    #"static": (1, {
    #    "name":                 STRING,
    #    "box":                  (BOX, MUST),
    #    "border":               (BOOL, "0"),
    #    }),

    "pdfnexttemplate": (0, {
        "name": (STRING, "body"),
    }),

    "pdfnextpage": (0, {
        "name": (STRING, ""),
        # "background":           FILE,
    }),

    "pdfnextframe": (0, {}),

    "pdffont": (0, {
        "src": (FILE, MUST),
        "name": (STRING, MUST),
        # "print":                (BOOL, "0"),
        "encoding": (STRING, "WinAnsiEncoding"),
    }),

    "pdfdrawline": (0, {
        "from": (POS, MUST),
        "to": (POS, MUST),
        "color": (COLOR, "#000000"),
        "width": (SIZE, 1),
    }),

    "drawpoint": (0, {
        "pos": (POS, MUST),
        "color": (COLOR, "#000000"),
        "width": (SIZE, 1),
    }),

    "pdfdrawlines": (0, {
        "coords": (STRING, MUST),
        "color": (COLOR, "#000000"),
        "width": (SIZE, 1),
    }),

    "pdfdrawstring": (0, {
        "pos": (POS, MUST),
        "text": (STRING, MUST),
        "color": (COLOR, "#000000"),
        "align": (["left", "center", "right"], "right"),
        "valign": (["top", "middle", "bottom"], "bottom"),
        # "class":                CLASS,
        "rotate": (INT, "0"),
    }),

    "pdfdrawimg": (0, {
        "pos": (POS, MUST),
        "src": (FILE, MUST),
        "width": SIZE,
        "height": SIZE,
        "align": (["left", "center", "right"], "right"),
        "valign": (["top", "middle", "bottom"], "bottom"),
    }),

    "pdfspacer": (0, {
        "height": (SIZE, MUST),
    }),

    "pdfpagenumber": (0, {
        "example": (STRING, "0"),
    }),

    "pdfpagecount": (0, {
    }),

    "pdftoc": (0, {
    }),

    "pdfversion": (0, {
    }),

    "pdfkeeptogether": (1, {
    }),

    "pdfkeepinframe": (1, {
        "maxwidth": SIZE,
        "maxheight": SIZE,
        "mergespace": (INT, 1),
        "mode": (["error", "overflow", "shrink", "truncate"], "shrink"),
        "name": (STRING, "")
    }),

    # The chart example, see pml_charts
    "pdfchart": (1, {
        "type": (["spider", "bar"], "bar"),
        "strokecolor": (COLOR, "#000000"),
        "width": (SIZE, MUST),
        "height": (SIZE, MUST),
    }),

    "pdfchartdata": (0, {
        "set": (STRING, MUST),
        "value": (STRING),
        # "label":                (STRING),
        "strokecolor": (COLOR),
        "fillcolor": (COLOR),
        "strokewidth": (SIZE),
    }),

    "pdfchartlabel": (0, {
        "value": (STRING, MUST),
    }),

    "pdfbarcode": (0, {
        "value": (STRING, MUST),
        "type": (["i2of5", "itf",
                  "code39", "extendedcode39",
                  "code93", "extendedcode93",
                  "msi",
                  "codabar", "nw7",
                  "code11",
                  "fim",
                  "postnet",
                  "usps4s",
                  "code128",
                  "ean13", "ean8",
                  "qr",
                 ], "code128"),
        "humanreadable": (STRING, "0"),
        "vertical": (STRING, "0"),
        "checksum": (STRING, "1"),
        "barwidth": SIZE,
        "barheight": SIZE,
        "fontsize": SIZE,
        "align": (["baseline", "top", "middle", "bottom"], "baseline"),
    }),

    # ========================================================

    "link": (0, {
        "href": (STRING, MUST),
        "rel": (STRING, ""),
        "type": (STRING, ""),
        "media": (STRING, "all"),
        "charset": (STRING, "latin1"), # XXX Must be something else...
    }),

    "meta": (0, {
        "name": (STRING, ""),
        "content": (STRING, ""),
    }),

    "style": (0, {
        "type": (STRING, ""),
        "media": (STRING, "all"),
    }),

    "img": (0, {
        "src": (FILE, MUST),
        "width": SIZE,
        "height": SIZE,
        "align": ["top", "middle", "bottom", "left", "right",
                  "texttop", "absmiddle", "absbottom", "baseline"],
    }),

    "table": (1, {
        "align": (["left", "center", "right"], "left"),
        "valign": (["top", "bottom", "middle"], "middle"),
        "border": (SIZE, "0"),
        "bordercolor": (COLOR, "#000000"),
        "bgcolor": COLOR,
        "cellpadding": (SIZE, "0"),
        "cellspacing": (SIZE, "0"),
        "repeat": (INT, "0"), # XXX Remove this! Set to 0
        "width": STRING,
        #"keepmaxwidth":         SIZE,
        #"keepmaxheight":        SIZE,
        #"keepmergespace":       (INT, 1),
        #"keepmode":             (["error", "overflow", "shrink", "truncate"], "shrink"),
    }),

    "tr": (1, {
        "bgcolor": COLOR,
        "valign": ["top", "bottom", "middle"],
        "border": SIZE,
        "bordercolor": (COLOR, "#000000"),
    }),

    "td": (1, {
        "align": ["left", "center", "right", "justify"],
        "valign": ["top", "bottom", "middle"],
        "width": STRING,
        "bgcolor": COLOR,
        "border": SIZE,
        "bordercolor": (COLOR, "#000000"),
        "colspan": INT,
        "rowspan": INT,
    }),

    "th": (1, {
        "align": ["left", "center", "right", "justify"],
        "valign": ["top", "bottom", "middle"],
        "width": STRING,
        "bgcolor": COLOR,
        "border": SIZE,
        "bordercolor": (COLOR, "#000000"),
        "colspan": INT,
        "rowspan": INT,
    }),

    "dl": (1, {
    }),

    "dd": (1, {
    }),

    "dt": (1, {
    }),

    "ol": (1, {
        "type": (["1", "a", "A", "i", "I"], "1"),
    }),

    "ul": (1, {
        "type": (["circle", "disk", "square"], "disk"),
    }),

    "li": (1, {
    }),

    "hr": (0, {
        "color": (COLOR, "#000000"),
        "size": (SIZE, "1"),
        "width": STRING,
        "align": ["left", "center", "right", "justify"],
    }),

    "div": (1, {
        "align": ["left", "center", "right", "justify"],
    }),

    "p": (1, {
        "align": ["left", "center", "right", "justify"],
    }),

    "br": (0, {
    }),

    "h1": (1, {
        "outline": STRING,
        "closed": (INT, 0),
        "align": ["left", "center", "right", "justify"],
    }),

    "h2": (1, {
        "outline": STRING,
        "closed": (INT, 0),
        "align": ["left", "center", "right", "justify"],
    }),

    "h3": (1, {
        "outline": STRING,
        "closed": (INT, 0),
        "align": ["left", "center", "right", "justify"],
    }),

    "h4": (1, {
        "outline": STRING,
        "closed": (INT, 0),
        "align": ["left", "center", "right", "justify"],
    }),

    "h5": (1, {
        "outline": STRING,
        "closed": (INT, 0),
        "align": ["left", "center", "right", "justify"],
    }),

    "h6": (1, {
        "outline": STRING,
        "closed": (INT, 0),
        "align": ["left", "center", "right", "justify"],
    }),

    "font": (1, {
        "face": FONT,
        "color": COLOR,
        "size": STRING,
    }),

    "a": (1, {
        "href": STRING,
        "name": STRING,
    }),

    "input": (0, {
        "name": STRING,
        "value": STRING,
        "type": (["text", "hidden", "checkbox"], "text"),
    }),

    "textarea": (1, {
        "name": STRING,
    }),

    "select": (1, {
        "name": STRING,
        "value": STRING,
    }),

    "option": (0, {
        "value": STRING,
    }),
}

# XXX use "html" not "*" as default!
DEFAULT_CSS = """
html {
    font-family: Helvetica;
    font-size: 10px;
    font-weight: normal;
    color: #000000;
    background-color: transparent;
    margin: 0;
    padding: 0;
    line-height: 150%;
    border: 1px none;
    display: inline;
    width: auto;
    height: auto;
    white-space: normal;
}

b,
strong {
    font-weight: bold;
}

i,
em {
    font-style: italic;
}

u {
    text-decoration: underline;
}

s,
strike {
    text-decoration: line-through;
}

a {
    text-decoration: underline;
    color: blue;
}

ins {
    color: green;
    text-decoration: underline;
}
del {
    color: red;
    text-decoration: line-through;
}

pre,
code,
kbd,
samp,
tt {
    font-family: "Courier New";
}

h1,
h2,
h3,
h4,
h5,
h6 {
    font-weight:bold;
    -pdf-outline: true;
    -pdf-outline-open: false;
}

h1 {
    /*18px via YUI Fonts CSS foundation*/
    font-size:138.5%;
    -pdf-outline-level: 0;
}

h2 {
    /*16px via YUI Fonts CSS foundation*/
    font-size:123.1%;
    -pdf-outline-level: 1;
}

h3 {
    /*14px via YUI Fonts CSS foundation*/
    font-size:108%;
    -pdf-outline-level: 2;
}

h4 {
    -pdf-outline-level: 3;
}

h5 {
    -pdf-outline-level: 4;
}

h6 {
    -pdf-outline-level: 5;
}

h1,
h2,
h3,
h4,
h5,
h6,
p,
pre,
hr {
    margin:1em 0;
}

address,
blockquote,
body,
center,
dl,
dir,
div,
fieldset,
form,
h1,
h2,
h3,
h4,
h5,
h6,
hr,
isindex,
menu,
noframes,
noscript,
ol,
p,
pre,
table,
th,
tr,
td,
ul,
li,
dd,
dt,
pdftoc {
    display: block;
}

table {
}

tr,
th,
td {

    vertical-align: middle;
    width: auto;
}

th {
    text-align: center;
    font-weight: bold;
}

center {
    text-align: center;
}

big {
    font-size: 125%;
}

small {
    font-size: 75%;
}


ul {
    margin-left: 1.5em;
    list-style-type: disc;
}

ul ul {
    list-style-type: circle;
}

ul ul ul {
    list-style-type: square;
}

ol {
    list-style-type: decimal;
    margin-left: 1.5em;
}

pre {
    white-space: pre;
}

blockquote {
    margin-left: 1.5em;
    margin-right: 1.5em;
}

noscript {
    display: none;
}
"""

DEFAULT_FONT = {
    "courier": "Courier",
    "courier-bold": "Courier-Bold",
    "courier-boldoblique": "Courier-BoldOblique",
    "courier-oblique": "Courier-Oblique",
    "helvetica": "Helvetica",
    "helvetica-bold": "Helvetica-Bold",
    "helvetica-boldoblique": "Helvetica-BoldOblique",
    "helvetica-oblique": "Helvetica-Oblique",
    "times": "Times-Roman",
    "times-roman": "Times-Roman",
    "times-bold": "Times-Bold",
    "times-boldoblique": "Times-BoldOblique",
    "times-oblique": "Times-Oblique",
    "symbol": "Symbol",
    "zapfdingbats": "ZapfDingbats",
    "zapf-dingbats": "ZapfDingbats",

    # Alias
    "arial": "Helvetica",
    "times new roman": "Times-Roman",
    "georgia": "Times-Roman",
    'serif': 'Times-Roman',
    'sansserif': 'Helvetica',
    'sans': 'Helvetica',
    'monospaced': 'Courier',
    'monospace': 'Courier',
    'mono': 'Courier',
    'courier new': 'Courier',
    'verdana': 'Helvetica',
    'geneva': 'Helvetica',
}

PML_PAGESIZES = {
    "a0": A0,
    "a1": A1,
    "a2": A2,
    "a3": A3,
    "a4": A4,
    "a5": A5,
    "a6": A6,
    "b0": B0,
    "b1": B1,
    "b2": B2,
    "b3": B3,
    "b4": B4,
    "b5": B5,
    "b6": B6,
    "letter": LETTER,
    "legal": LEGAL,
    "ledger": ELEVENSEVENTEEN,
    "elevenseventeen": ELEVENSEVENTEEN,
}

########NEW FILE########
__FILENAME__ = document
# -*- coding: utf-8 -*-
from xhtml2pdf.context import pisaContext
from xhtml2pdf.default import DEFAULT_CSS
from xhtml2pdf.parser import pisaParser
from reportlab.platypus.flowables import Spacer
from reportlab.platypus.frames import Frame
from xhtml2pdf.xhtml2pdf_reportlab import PmlBaseDoc, PmlPageTemplate
from xhtml2pdf.util import pisaTempFile, getBox, PyPDF2
import cgi
import logging

# Copyright 2010 Dirk Holtwick, holtwick.it
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

log = logging.getLogger("xhtml2pdf")


def pisaErrorDocument(dest, c):
    out = pisaTempFile(capacity=c.capacity)
    out.write("<p style='background-color:red;'><strong>%d error(s) occured:</strong><p>" % c.err)
    for mode, line, msg, _ in c.log:
        if mode == "error":
            out.write("<pre>%s in line %d: %s</pre>" % (mode, line, cgi.escape(msg)))

    out.write("<p><strong>%d warning(s) occured:</strong><p>" % c.warn)
    for mode, line, msg, _ in c.log:
        if mode == "warning":
            out.write("<p>%s in line %d: %s</p>" % (mode, line, cgi.escape(msg)))

    return pisaDocument(out.getvalue(), dest, raise_exception=False)


def pisaStory(src, path=None, link_callback=None, debug=0, default_css=None,
              xhtml=False, encoding=None, context=None, xml_output=None,
              **kw):
    # Prepare Context
    if not context:
        context = pisaContext(path, debug=debug)
        context.pathCallback = link_callback

    # Use a default set of CSS definitions to get an expected output
    if default_css is None:
        default_css = DEFAULT_CSS

    # Parse and fill the story
    pisaParser(src, context, default_css, xhtml, encoding, xml_output)

    # Avoid empty documents
    if not context.story:
        context.story = [Spacer(1, 1)]

    if context.indexing_story:
        context.story.append(context.indexing_story)

    # Remove anchors if they do not exist (because of a bug in Reportlab)
    for frag, anchor in context.anchorFrag:
        if anchor not in context.anchorName:
            frag.link = None
    return context


def pisaDocument(src, dest=None, path=None, link_callback=None, debug=0,
                 default_css=None, xhtml=False, encoding=None, xml_output=None,
                 raise_exception=True, capacity=100 * 1024, **kw):
    log.debug("pisaDocument options:\n  src = %r\n  dest = %r\n  path = %r\n  link_callback = %r\n  xhtml = %r",
              src,
              dest,
              path,
              link_callback,
              xhtml)

    # Prepare simple context
    context = pisaContext(path, debug=debug, capacity=capacity)
    context.pathCallback = link_callback

    # Build story
    context = pisaStory(src, path, link_callback, debug, default_css, xhtml,
                        encoding, context=context, xml_output=xml_output)

    # Buffer PDF into memory
    out = pisaTempFile(capacity=context.capacity)

    doc = PmlBaseDoc(
        out,
        pagesize=context.pageSize,
        author=context.meta["author"].strip(),
        subject=context.meta["subject"].strip(),
        keywords=[x.strip() for x in
                  context.meta["keywords"].strip().split(",") if x],
        title=context.meta["title"].strip(),
        showBoundary=0,
        allowSplitting=1)

    # Prepare templates and their frames
    if "body" in context.templateList:
        body = context.templateList["body"]
        del context.templateList["body"]
    else:
        x, y, w, h = getBox("1cm 1cm -1cm -1cm", context.pageSize)
        body = PmlPageTemplate(
            id="body",
            frames=[
                Frame(x, y, w, h,
                      id="body",
                      leftPadding=0,
                      rightPadding=0,
                      bottomPadding=0,
                      topPadding=0)],
            pagesize=context.pageSize)

    doc.addPageTemplates([body] + context.templateList.values())

    # Use multibuild e.g. if a TOC has to be created
    if context.multiBuild:
        doc.multiBuild(context.story)
    else:
        doc.build(context.story)

    # Add watermarks
    if PyPDF2:
        for bgouter in context.pisaBackgroundList:
            # If we have at least one background, then lets do it
            if bgouter:
                istream = out

                output = PyPDF2.PdfFileWriter()
                input1 = PyPDF2.PdfFileReader(istream)
                ctr = 0
                # TODO: Why do we loop over the same list again?
                # see bgouter at line 137
                for bg in context.pisaBackgroundList:
                    page = input1.getPage(ctr)
                    if (bg and not bg.notFound()
                        and (bg.mimetype == "application/pdf")):
                        bginput = PyPDF2.PdfFileReader(bg.getFile())
                        pagebg = bginput.getPage(0)
                        pagebg.mergePage(page)
                        page = pagebg
                    else:
                        log.warn(context.warning(
                            "Background PDF %s doesn't exist.", bg))
                    output.addPage(page)
                    ctr += 1
                out = pisaTempFile(capacity=context.capacity)
                output.write(out)
                # data = sout.getvalue()
                # Found a background? So leave loop after first occurence
                break
    else:
        log.warn(context.warning("PyPDF2 not installed!"))

    # Get the resulting PDF and write it to the file object
    # passed from the caller

    if dest is None:
        # No output file was passed - Let's use a pisaTempFile
        dest = pisaTempFile(capacity=context.capacity)
    context.dest = dest

    data = out.getvalue()  # TODO: That load all the tempfile in RAM - Why bother with a swapping tempfile then?
    context.dest.write(data)  # TODO: context.dest is a tempfile as well...

    return context

########NEW FILE########
__FILENAME__ = paragraph
#!/bin/env/python
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

"""
A paragraph class to be used with ReportLab Platypus.

TODO
====

- Bullets
- Weblinks and internal links
- Borders and margins (Box)
- Underline, Background, Strike
- Images
- Hyphenation
+ Alignment
+ Breakline, empty lines
+ TextIndent
- Sub and super

"""

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import Color


class Style(dict):
    """
    Style.

    Single place for style definitions: Paragraphs and Fragments. The
    naming follows the convention of CSS written in camelCase letters.
    """

    DEFAULT = {
        "textAlign": TA_LEFT,
        "textIndent": 0.0,
        "width": None,
        "height": None,
        "fontName": "Times-Roman",
        "fontSize": 10.0,
        "color": Color(0, 0, 0),
        "lineHeight": 1.5,
        "lineHeightAbsolute": None,
        "pdfLineSpacing": 0,
        "link": None,
    }

    def __init__(self, **kw):
        self.update(self.DEFAULT)
        self.update(kw)
        self.spaceBefore = 0
        self.spaceAfter = 0
        self.keepWithNext = False


class Box(dict):
    """
    Box.

    Handles the following styles:

        backgroundColor, backgroundImage
        paddingLeft, paddingRight, paddingTop, paddingBottom
        marginLeft, marginRight, marginTop, marginBottom
        borderLeftColor, borderLeftWidth, borderLeftStyle
        borderRightColor, borderRightWidth, borderRightStyle
        borderTopColor, borderTopWidth, borderTopStyle
        borderBottomColor, borderBottomWidth, borderBottomStyle

    Not used in inline Elements:

        paddingTop, paddingBottom
        marginTop, marginBottom

    """

    name = "box"

    def drawBox(self, canvas, x, y, w, h):
        canvas.saveState()

        # Background
        bg = self.get("backgroundColor", None)
        if bg is not None:
            # draw a filled rectangle (with no stroke) using bg color
            canvas.setFillColor(bg)
            canvas.rect(x, y, w, h, fill=1, stroke=0)

        # Borders
        def _drawBorderLine(bstyle, width, color, x1, y1, x2, y2):
            # We need width and border style to be able to draw a border
            if width and bstyle:
                # If no color for border is given, the text color is used (like defined by W3C)
                if color is None:
                    color = self.get("textColor", Color(0, 0, 0))
                    # print "Border", bstyle, width, color
                if color is not None:
                    canvas.setStrokeColor(color)
                    canvas.setLineWidth(width)
                    canvas.line(x1, y1, x2, y2)

        _drawBorderLine(self.get("borderLeftStyle", None),
                        self.get("borderLeftWidth", None),
                        self.get("borderLeftColor", None),
                        x, y, x, y + h)
        _drawBorderLine(self.get("borderRightStyle", None),
                        self.get("borderRightWidth", None),
                        self.get("borderRightColor", None),
                        x + w, y, x + w, y + h)
        _drawBorderLine(self.get("borderTopStyle", None),
                        self.get("borderTopWidth", None),
                        self.get("borderTopColor", None),
                        x, y + h, x + w, y + h)
        _drawBorderLine(self.get("borderBottomStyle", None),
                        self.get("borderBottomWidth", None),
                        self.get("borderBottomColor", None),
                        x, y, x + w, y)

        canvas.restoreState()


class Fragment(Box):
    """
    Fragment.

    text:       String containing text
    fontName:
    fontSize:
    width:      Width of string
    height:     Height of string
    """

    name = "fragment"
    isSoft = False
    isText = False
    isLF = False


    def calc(self):
        self["width"] = 0


class Word(Fragment):
    """
    A single word.
    """

    name = "word"
    isText = True

    def calc(self):
        """
        XXX Cache stringWith if not accelerated?!
        """
        self["width"] = stringWidth(self["text"], self["fontName"], self["fontSize"])


class Space(Fragment):
    """
    A space between fragments that is the usual place for line breaking.
    """

    name = "space"
    isSoft = True

    def calc(self):
        self["width"] = stringWidth(" ", self["fontName"], self["fontSize"])


class LineBreak(Fragment):
    """
    Line break.
    """

    name = "br"
    isSoft = True
    isLF = True

    pass


class BoxBegin(Fragment):
    name = "begin"

    def calc(self):
        self["width"] = self.get("marginLeft", 0) + self.get("paddingLeft", 0) # + border if border

    def draw(self, canvas, y):
        # if not self["length"]:
        x = self.get("marginLeft", 0) + self["x"]
        w = self["length"] + self.get("paddingRight", 0)
        h = self["fontSize"]
        self.drawBox(canvas, x, y, w, h)


class BoxEnd(Fragment):
    name = "end"

    def calc(self):
        self["width"] = self.get("marginRight", 0) + self.get("paddingRight", 0) # + border


class Image(Fragment):
    name = "image"

    pass


class Line(list):
    """
    Container for line fragments.
    """

    LINEHEIGHT = 1.0

    def __init__(self, style):
        self.width = 0
        self.height = 0
        self.isLast = False
        self.style = style
        self.boxStack = []
        list.__init__(self)

    def doAlignment(self, width, alignment):
        # Apply alignment
        if alignment != TA_LEFT:
            lineWidth = self[- 1]["x"] + self[- 1]["width"]
            emptySpace = width - lineWidth
            if alignment == TA_RIGHT:
                for frag in self:
                    frag["x"] += emptySpace
            elif alignment == TA_CENTER:
                for frag in self:
                    frag["x"] += emptySpace / 2.0
            elif alignment == TA_JUSTIFY and not self.isLast: # XXX last line before split
                delta = emptySpace / (len(self) - 1)
                for i, frag in enumerate(self):
                    frag["x"] += i * delta

        # Boxes
        for frag in self:
            x = frag["x"] + frag["width"]
            # print "***", x, frag["x"]
            if isinstance(frag, BoxBegin):
                self.boxStack.append(frag)
            elif isinstance(frag, BoxEnd):
                if self.boxStack:
                    frag = self.boxStack.pop()
                    frag["length"] = x - frag["x"]

        # Handle the rest
        for frag in self.boxStack:
            # print "***", x, frag["x"]
            frag["length"] = x - frag["x"]

    def doLayout(self, width):
        """
        Align words in previous line.
        """

        # Calculate dimensions
        self.width = width
        self.height = self.lineHeight = max(frag.get("fontSize", 0) * self.LINEHEIGHT for frag in self)

        # Apply line height
        self.fontSize = max(frag.get("fontSize", 0) for frag in self)
        y = (self.lineHeight - self.fontSize) # / 2
        for frag in self:
            frag["y"] = y

        return self.height

    def dumpFragments(self):
        print ("Line", 40 * "-")
        for frag in self:
            print ("%s") % frag.get("text", frag.name.upper()),
        print()


class Text(list):
    """
    Container for text fragments.

    Helper functions for splitting text into lines and calculating sizes
    and positions.
    """

    def __init__(self, data=None, style=None):
        # Mutable arguments are a shit idea
        if data is None:
            data = []

        self.lines = []
        self.width = 0
        self.height = 0
        self.maxWidth = 0
        self.maxHeight = 0
        self.style = style
        list.__init__(self, data)

    def calc(self):
        """
        Calculate sizes of fragments.
        """
        for word in self:
            word.calc()

    def splitIntoLines(self, maxWidth, maxHeight, splitted=False):
        """
        Split text into lines and calculate X positions. If we need more
        space in height than available we return the rest of the text
        """
        self.lines = []
        self.height = 0
        self.maxWidth = self.width = maxWidth
        self.maxHeight = maxHeight
        boxStack = []

        style = self.style
        x = 0

        # Start with indent in first line of text
        if not splitted:
            x = style["textIndent"]

        lenText = len(self)
        pos = 0
        while pos < lenText:

            # Reset values for new line
            posBegin = pos
            line = Line(style)

            # Update boxes for next line
            for box in copy.copy(boxStack):
                box["x"] = 0
                line.append(BoxBegin(box))

            while pos < lenText:

                # Get fragment, its width and set X
                frag = self[pos]
                fragWidth = frag["width"]
                frag["x"] = x
                pos += 1

                # Keep in mind boxes for next lines
                if isinstance(frag, BoxBegin):
                    boxStack.append(frag)
                elif isinstance(frag, BoxEnd):
                    boxStack.pop()

                # If space or linebreak handle special way
                if frag.isSoft:
                    if frag.isLF:
                        line.append(frag)
                        break
                        # First element of line should not be a space
                    if x == 0:
                        continue
                        # Keep in mind last possible line break

                # The elements exceed the current line
                elif fragWidth + x > maxWidth:
                    break

                # Add fragment to line and update x
                x += fragWidth
                line.append(frag)

            # Remove trailing white spaces
            while line and line[-1].name in ("space", "br"):
                # print "Pop",
                line.pop()

            # Add line to list
            line.dumpFragments()
            # if line:
            self.height += line.doLayout(self.width)
            self.lines.append(line)

            # If not enough space for current line force to split
            if self.height > maxHeight:
                return posBegin

            # Reset variables
            x = 0

        # Apply alignment
        self.lines[- 1].isLast = True
        for line in self.lines:
            line.doAlignment(maxWidth, style["textAlign"])

        return None

    def dumpLines(self):
        """
        For debugging dump all line and their content
        """
        for i, line in enumerate(self.lines):
            print ("Line %d:") % i,
            line.dumpFragments()


class Paragraph(Flowable):
    """
    A simple Paragraph class respecting alignment.

    Does text without tags.

    Respects only the following global style attributes:
    fontName, fontSize, leading, firstLineIndent, leftIndent,
    rightIndent, textColor, alignment.
    (spaceBefore, spaceAfter are handled by the Platypus framework.)

    """
    def __init__(self, text, style, debug=False, splitted=False, **kwDict):

        Flowable.__init__(self)

        self.text = text
        self.text.calc()
        self.style = style
        self.text.style = style

        self.debug = debug
        self.splitted = splitted

        # More attributes
        for k, v in kwDict.iteritems():
            setattr(self, k, v)

        # set later...
        self.splitIndex = None

    # overwritten methods from Flowable class
    def wrap(self, availWidth, availHeight):
        """
        Determine the rectangle this paragraph really needs.
        """

        # memorize available space
        self.avWidth = availWidth
        self.avHeight = availHeight

        if self.debug:
            print ("*** wrap (%f, %f)") % (availWidth, availHeight)

        if not self.text:
            if self.debug:
                print ("*** wrap (%f, %f) needed") % (0, 0)
            return 0, 0

        # Split lines
        width = availWidth
        self.splitIndex = self.text.splitIntoLines(width, availHeight)

        self.width, self.height = availWidth, self.text.height

        if self.debug:
            print ("*** wrap (%f, %f) needed, splitIndex %r") % (self.width, self.height, self.splitIndex)

        return self.width, self.height

    def split(self, availWidth, availHeight):
        """
        Split ourself in two paragraphs.
        """

        if self.debug:
            print ("*** split (%f, %f)") % (availWidth, availHeight)

        splitted = []
        if self.splitIndex:
            text1 = self.text[:self.splitIndex]
            text2 = self.text[self.splitIndex:]
            p1 = Paragraph(Text(text1), self.style, debug=self.debug)
            p2 = Paragraph(Text(text2), self.style, debug=self.debug, splitted=True)
            splitted = [p1, p2]

            if self.debug:
                print ("*** text1 %s / text %s") % (len(text1), len(text2))

        if self.debug:
            print ('*** return %s') % self.splitted

        return splitted

    def draw(self):
        """
        Render the content of the paragraph.
        """

        if self.debug:
            print ("*** draw")

        if not self.text:
            return

        canvas = self.canv
        style = self.style

        canvas.saveState()

        # Draw box arround paragraph for debugging
        if self.debug:
            bw = 0.5
            bc = Color(1, 1, 0)
            bg = Color(0.9, 0.9, 0.9)
            canvas.setStrokeColor(bc)
            canvas.setLineWidth(bw)
            canvas.setFillColor(bg)
            canvas.rect(
                style.leftIndent,
                0,
                self.width,
                self.height,
                fill=1,
                stroke=1)

        y = 0
        dy = self.height
        for line in self.text.lines:
            y += line.height
            for frag in line:

                # Box
                if hasattr(frag, "draw"):
                    frag.draw(canvas, dy - y)

                # Text
                if frag.get("text", ""):
                    canvas.setFont(frag["fontName"], frag["fontSize"])
                    canvas.setFillColor(frag.get("color", style["color"]))
                    canvas.drawString(frag["x"], dy - y + frag["y"], frag["text"])

                # XXX LINK
                link = frag.get("link", None)
                if link:
                    _scheme_re = re.compile('^[a-zA-Z][-+a-zA-Z0-9]+$')
                    x, y, w, h = frag["x"], dy - y, frag["width"], frag["fontSize"]
                    rect = (x, y, w, h)
                    if isinstance(link, unicode):
                        link = link.encode('utf8')
                    parts = link.split(':', 1)
                    scheme = len(parts) == 2 and parts[0].lower() or ''
                    if _scheme_re.match(scheme) and scheme != 'document':
                        kind = scheme.lower() == 'pdf' and 'GoToR' or 'URI'
                        if kind == 'GoToR':
                            link = parts[1]

                        canvas.linkURL(link, rect, relative=1, kind=kind)
                    else:
                        if link[0] == '#':
                            link = link[1:]
                            scheme = ''
                        canvas.linkRect("", scheme != 'document' and link or parts[1], rect, relative=1)

        canvas.restoreState()


if __name__ == "__main__":
    # TODO: This should be a test, not a main!
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.styles import *
    from reportlab.rl_config import *
    from reportlab.lib.units import *

    import os
    import copy
    import re

    styles = getSampleStyleSheet()

    ALIGNMENTS = (TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY)

    TEXT = """
    Lörem ipsum dolor sit amet, consectetur adipisicing elit,
    sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
    Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi
    ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit
    in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
    Excepteur sint occaecat cupidatat non proident, sunt in culpa qui
    officia deserunt mollit anim id est laborum. Lorem ipsum dolor sit amet,
    consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore
    et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation
    ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure
    dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat
    nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt
    in culpa qui officia deserunt mollit anim id est laborum. Lorem ipsum
    dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor
    incididunt ut labore et dolore magna aliqua.
    """.strip()

    def textGenerator(data, fn, fs):
        i = 1
        for word in re.split('\s+', data):
            if word:
                yield Word(
                    text="[%d|%s]" % (i, word),
                    fontName=fn,
                    fontSize=fs
                )
                yield Space(
                    fontName=fn,
                    fontSize=fs
                )

    def createText(data, fn, fs):
        text = Text(list(textGenerator(data, fn, fs)))
        return text

    def makeBorder(width, style="solid", color=Color(1, 0, 0)):
        return dict(
            borderLeftColor=color,
            borderLeftWidth=width,
            borderLeftStyle=style,
            borderRightColor=color,
            borderRightWidth=width,
            borderRightStyle=style,
            borderTopColor=color,
            borderTopWidth=width,
            borderTopStyle=style,
            borderBottomColor=color,
            borderBottomWidth=width,
            borderBottomStyle=style
        )

    def test():
        doc = SimpleDocTemplate("test.pdf")
        story = []

        style = Style(fontName="Helvetica", textIndent=24.0)
        fn = style["fontName"]
        fs = style["fontSize"]
        sampleText1 = createText(TEXT[:100], fn, fs)
        sampleText2 = createText(TEXT[100:], fn, fs)

        text = Text(sampleText1 + [
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="TrennbarTrennbar",
                pairs=[("Trenn-", "barTrennbar")],
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Normal",
                color=Color(1, 0, 0),
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="gGrößer",
                fontName=fn,
                fontSize=fs * 1.5),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Bold",
                fontName="Times-Bold",
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="jItalic",
                fontName="Times-Italic",
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),

            # <span style="border: 1px solid red;">ipsum <span style="border: 1px solid green; padding: 4px; padding-left: 20px; background: yellow; margin-bottom: 8px; margin-left: 10px;">
            # Lo<font size="12pt">re</font>m</span> <span style="background:blue; height: 30px;">ipsum</span> Lorem</span>

            BoxBegin(
                fontName=fn,
                fontSize=fs,
                **makeBorder(0.5, "solid", Color(0, 1, 0))),
            Word(
                text="Lorem",
                fontName="Times-Bold",
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName="Times-Bold",
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            BoxBegin(
                fontName=fn,
                fontSize=fs,
                backgroundColor=Color(1, 1, 0),
                **makeBorder(1, "solid", Color(1, 0, 0))),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            BoxEnd(),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            BoxEnd(),

            LineBreak(
                fontName=fn,
                fontSize=fs),
            LineBreak(
                fontName=fn,
                fontSize=fs),
        ] + sampleText2)

        story.append(Paragraph(
            copy.copy(text),
            style,
            debug=0))

        for i in range(10):
            style = copy.deepcopy(style)
            style["textAlign"] = ALIGNMENTS[i % 4]
            text = createText(("(%d) " % i) + TEXT, fn, fs)
            story.append(Paragraph(
                copy.copy(text),
                style,
                debug=0))
        doc.build(story)

    test()
    os.system("start test.pdf")

    # FIXME: Useless line?
    # createText(TEXT, styles["Normal"].fontName, styles["Normal"].fontSize)

########NEW FILE########
__FILENAME__ = paragraph2
#!/bin/env/python
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

"""
A paragraph class to be used with ReportLab Platypus.

TODO
====

- Bullets
- Weblinks and internal links
- Borders and margins (Box)
- Underline, Background, Strike
- Images
- Hyphenation
+ Alignment
+ Breakline, empty lines
+ TextIndent
- Sub and super

"""

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import Color


WORD = 1
SPACE = 2
BR = 3
BEGIN = 4
END = 5
IMAGE = 6


class Style(dict):
    """
    Style.

    Single place for style definitions: Paragraphs and Fragments. The
    naming follows the convention of CSS written in camelCase letters.
    """

    DEFAULT = {
        "textAlign": TA_LEFT,
        "textIndent": 0.0,
        "width": None,
        "height": None,
        "fontName": "Times-Roman",
        "fontSize": 10.0,
        "color": Color(0, 0, 0),
        "lineHeight": 1.5,
        "lineHeightAbsolute": None,
        "pdfLineSpacing": 0,
        "link": None,
    }

    def __init__(self, **kw):
        self.update(self.DEFAULT)
        self.update(kw)
        self.spaceBefore = 0
        self.spaceAfter = 0
        self.keepWithNext = False


class Box(dict):
    """
    Box.

    Handles the following styles:

        # underline, underLineColor (?)
        # strike, strikeColor (?)

        backgroundColor, backgroundImage
        paddingLeft, paddingRight, paddingTop, paddingBottom
        marginLeft, marginRight, marginTop, marginBottom
        borderLeftColor, borderLeftWidth, borderLeftStyle
        borderRightColor, borderRightWidth, borderRightStyle
        borderTopColor, borderTopWidth, borderTopStyle
        borderBottomColor, borderBottomWidth, borderBottomStyle

    Not used in inline Elements:

        paddingTop, paddingBottom
        marginTop, marginBottom

    Needs also:

        fontName, fontSize, color

    """

    name = "box"

    def _drawBefore(self, canvas, x, y, w, h):
        canvas.saveState()

        textColor = self.get("color", Color(0, 0, 0))

        # Background
        bg = self.get("backgroundColor", None)
        if bg is not None:
            # draw a filled rectangle (with no stroke) using bg color
            canvas.setFillColor(bg)
            canvas.rect(x, y, w, h, fill=1, stroke=0)

        # Borders
        def _drawBorderLine(bstyle, width, color, x1, y1, x2, y2):
            # We need width and border style to be able to draw a border
            if width and bstyle:
                # If no color for border is given, the text color is used (like defined by W3C)
                if color is None:
                    color = textColor
                if color is not None:
                    canvas.setStrokeColor(color)
                    canvas.setLineWidth(width)
                    canvas.line(x1, y1, x2, y2)

        _drawBorderLine(self.get("borderLeftStyle", None),
                        self.get("borderLeftWidth", None),
                        self.get("borderLeftColor", None),
                        x, y, x, y + h)
        _drawBorderLine(self.get("borderRightStyle", None),
                        self.get("borderRightWidth", None),
                        self.get("borderRightColor", None),
                        x + w, y, x + w, y + h)
        _drawBorderLine(self.get("borderTopStyle", None),
                        self.get("borderTopWidth", None),
                        self.get("borderTopColor", None),
                        x, y + h, x + w, y + h)
        _drawBorderLine(self.get("borderBottomStyle", None),
                        self.get("borderBottomWidth", None),
                        self.get("borderBottomColor", None),
                        x, y, x + w, y)

        # Underline
        if self.get("underline", None):
            ff = 0.125 * self["fontSize"]
            yUnderline = y - 1.0 * ff
            canvas.setLineWidth(ff * 0.75)
            canvas.setStrokeColor(textColor)
            canvas.line(x, yUnderline, x + w, yUnderline)

        canvas.restoreState()

    def _drawAfter(self, canvas, x, y, w, h):

        # Strike
        if self.get("strike", None):
            ff = 0.125 * self["fontSize"]
            yStrike = y + 2.0 * ff
            textColor = self.get("color", Color(0, 0, 0))

            canvas.saveState()
            canvas.setLineWidth(ff * 0.75)
            canvas.setStrokeColor(textColor)
            canvas.line(x, yStrike, x + w, yStrike)
            canvas.restoreState()


class Fragment(Box):
    """
    Fragment.

    text:       String containing text
    fontName:
    fontSize:
    width:      Width of string
    height:     Height of string
    """

    name = "fragment"
    type = None

    isSoft = False
    isText = False
    isLF = False

    def calc(self):
        self["width"] = 0

    def __str__(self):
        if self.isText:
            return "'%s'" % self["text"]
        return "<%s>" % self.name.upper()


class BoxBegin(Fragment):
    name = "begin"
    type = BEGIN

    def calc(self):
        self["width"] = self.get("marginLeft", 0) + self.get("paddingLeft", 0) # + border if border

    def drawBefore(self, canvas, y):
        # print repr(self)
        x = self.get("marginLeft", 0) + self["x"]
        w = self["length"] + self.get("paddingRight", 0)
        h = self["fontSize"]
        self["box"] = (x, w, h)
        self._drawBefore(canvas, x, y, w, h)

    def drawAfter(self, canvas, y):
        x, w, h = self["box"]
        self._drawAfter(canvas, x, y, w, h)


class BoxEnd(Fragment):
    name = "end"
    type = END

    def calc(self):
        self["width"] = self.get("marginRight", 0) + self.get("paddingRight", 0) # + border


class Word(Fragment):
    """
    A single word.
    """

    name = "word"
    type = WORD

    isText = True

    def calc(self):
        """
        XXX Cache stringWith if not accelerated?!
        """
        self["width"] = stringWidth(self["text"], self["fontName"], self["fontSize"])


class Space(Fragment):
    """
    A space between fragments that is the usual place for line breaking.
    """

    name = "space"
    type = SPACE

    isSoft = True


    def calc(self):
        self["width"] = stringWidth(" ", self["fontName"], self["fontSize"])


class LineBreak(Fragment):
    " Line break. "

    name = "br"
    type = BR

    isSoft = True
    isLF = True

    pass


class Image(Fragment):
    name = "image"
    type = IMAGE

    isText = True

    pass


class Line(list):
    """
    Container for line fragments.
    """

    LINEHEIGHT = 1.0

    def __init__(self, style):
        self.width = 0
        self.height = 0
        self.isLast = False
        self.br = False
        self.style = style
        self.boxStack = []
        list.__init__(self)

    def doAlignment(self, width, alignment):
        # Apply alignment
        if alignment != TA_LEFT:
            lineWidth = self[- 1]["x"] + self[- 1]["width"]
            emptySpace = width - lineWidth
            if alignment == TA_RIGHT:
                for frag in self:
                    frag["x"] += emptySpace
            elif alignment == TA_CENTER:
                for frag in self:
                    frag["x"] += emptySpace / 2.0
            elif alignment == TA_JUSTIFY and not self.br: # XXX Just spaces! Currently divides also sticky fragments
                delta = emptySpace / (len(self) - 1)
                for i, frag in enumerate(self):
                    frag["x"] += i * delta

        # Boxes
        for frag in self:
            x = frag["x"] + frag["width"]
            if isinstance(frag, BoxBegin):
                self.boxStack.append(frag)
            elif isinstance(frag, BoxEnd):
                if self.boxStack:
                    frag = self.boxStack.pop()
                    frag["length"] = x - frag["x"]

        # Handle the rest
        for frag in self.boxStack:
            frag["length"] = x - frag["x"]

    def doLayout(self, width):
        "Align words in previous line."

        # Calculate dimensions
        self.width = width
        self.height = self.lineHeight = max(frag.get("fontSize", 0) * self.LINEHEIGHT for frag in self)

        # Apply line height
        self.fontSize = max(frag.get("fontSize", 0) for frag in self)
        y = (self.lineHeight - self.fontSize) # / 2
        for frag in self:
            frag["y"] = y

        return self.height

    def dumpFragments(self):
        print ("Line", 40 * "-")
        for frag in self:
            print ("%s") % frag.get("text", frag.name.upper()),
        print()


class Group(list):
    pass


class Text(list):
    """
    Container for text fragments.

    Helper functions for splitting text into lines and calculating sizes
    and positions.
    """

    def __init__(self, data=None, style=None):
        if data is None:
            data = []

        self.lines = []
        self.width = 0
        self.height = 0
        self.maxWidth = 0
        self.maxHeight = 0
        self.pos = 0
        self.oldSpace = None
        self.newSpace = None
        self.style = style
        list.__init__(self, data)

    def calc(self):
        """
        Calculate sizes of fragments.
        """
        for word in self:
            word.calc()

    def getGroup(self):
        self.oldSpace = self.newSpace # For Space recycing
        group = []
        width = 0
        br = False
        length = len(self)
        while self.pos < length:
            frag = self[self.pos]
            type_ = frag.type
            self.pos += 1
            if type_ == SPACE:
                self.newSpace = frag # For Space recycing
                if group:
                    break
                continue
            group.append(frag)
            width += frag.get("width", 0)
            if type_ == BR:
                br = True
                break
        return width, br, group

    def splitIntoLines(self, maxWidth, maxHeight, splitted=False):
        """
        Split text into lines and calculate X positions. If we need more
        space in height than available we return the rest of the text
        """

        self.lines = []
        self.pos = 0
        self.height = 0
        self.maxWidth = self.width = maxWidth
        self.maxHeight = maxHeight
        boxStack = []

        style = self.style
        x = 0

        # Start with indent in first line of text
        if not splitted:
            x = style["textIndent"]

        # Loop for each line
        while True:

            # Reset values for new line
            posBegin = self.pos
            line = Line(style)

            # Update boxes for next line
            for box in copy.deepcopy(boxStack):
                box["x"] = 0
                line.append(BoxBegin(box))

            # Loop for collecting line elements
            while True:

                # Get next group of unbreakable elements
                self.groupPos = self.pos
                groupWidth, br, group = self.getGroup()

                # No more groups? Leave line
                if not group:
                    break

                # To we fit the line? Reset cursor and finish line
                if groupWidth + x > maxWidth:
                    self.pos = self.groupPos
                    break

                # Space recycling
                if self.oldSpace:
                    group.insert(0, self.oldSpace)

                # Add fragments to line and update x
                for frag in group:

                    # Add fragment to line and update x
                    frag["x"] = x
                    x += frag["width"]
                    line.append(frag)

                    # Keep in mind boxes for next lines
                    if isinstance(frag, BoxBegin):
                        boxStack.append(frag)
                    elif isinstance(frag, BoxEnd):
                        boxStack.pop()

                # We got a new line forced
                if br:
                    line.br = True
                    break

            self.newSpace = None

            # Add line to list
            line.dumpFragments()

            if line:
                self.height += line.doLayout(self.width)
                self.lines.append(line)

            # If not enough space for current line force to split
            if self.height > maxHeight:
                return posBegin

            # Reached the end
            if not group:
                break

            # Reset variables
            x = 0

        # Apply alignment
        self.lines[- 1].br = True
        for line in self.lines:
            line.doAlignment(maxWidth, style["textAlign"])

        return None

    def dumpLines(self):
        """
        For debugging dump all line and their content
        """
        for i, line in enumerate(self.lines):
            print ("Line %d:") % i,
            line.dumpFragments()


class Paragraph(Flowable):
    """A simple Paragraph class respecting alignment.

    Does text without tags.

    Respects only the following global style attributes:
    fontName, fontSize, leading, firstLineIndent, leftIndent,
    rightIndent, textColor, alignment.
    (spaceBefore, spaceAfter are handled by the Platypus framework.)

    """

    def __init__(self, text, style, debug=False, splitted=False, **kwDict):

        Flowable.__init__(self)
        # self._showBoundary = True

        self.text = text
        self.text.calc()
        self.style = style
        self.text.style = style

        self.debug = debug
        self.splitted = splitted

        # More attributes
        for k, v in kwDict.iteritems():
            setattr(self, k, v)

        # set later...
        self.splitIndex = None

    # overwritten methods from Flowable class
    def wrap(self, availWidth, availHeight):
        """
        Determine the rectangle this paragraph really needs.
        """

        # memorize available space
        self.avWidth = availWidth
        self.avHeight = availHeight

        if self.debug:
            print ("*** wrap (%f, %f)") % (availWidth, availHeight)

        if not self.text:
            if self.debug:
                print ("*** wrap (%f, %f) needed") % (0, 0)
            return 0, 0

        # Split lines
        width = availWidth
        self.splitIndex = self.text.splitIntoLines(width, availHeight)

        self.width, self.height = availWidth, self.text.height

        if self.debug:
            print ("*** wrap (%f, %f) needed, splitIndex %r") % (self.width, self.height, self.splitIndex)

        return self.width, self.height

    def split(self, availWidth, availHeight):
        """
        Split ourself in two paragraphs.
        """

        if self.debug:
            print ("*** split (%f, %f)") % (availWidth, availHeight)

        splitted = []
        if self.splitIndex:
            text1 = self.text[:self.splitIndex]
            text2 = self.text[self.splitIndex:]
            p1 = Paragraph(Text(text1), self.style, debug=self.debug)
            p2 = Paragraph(Text(text2), self.style, debug=self.debug, splitted=True)
            splitted = [p1, p2]

            if self.debug:
                print ("*** text1 %s / text %s") % (len(text1), len(text2))

        if self.debug:
            print ('*** return %s') % self.splitted

        return splitted

    def draw(self):
        """
        Render the content of the paragraph.
        """

        if self.debug:
            print ("*** draw")

        if not self.text:
            return

        canvas = self.canv
        style = self.style

        canvas.saveState()

        # Draw box arround paragraph for debugging
        if self.debug:
            bw = 0.5
            bc = Color(1, 1, 0)
            bg = Color(0.9, 0.9, 0.9)
            canvas.setStrokeColor(bc)
            canvas.setLineWidth(bw)
            canvas.setFillColor(bg)
            canvas.rect(
                style.leftIndent,
                0,
                self.width,
                self.height,
                fill=1,
                stroke=1)

        y = 0
        dy = self.height
        for line in self.text.lines:
            y += line.height
            for frag in line:

                type_ = frag.type

                # Box
                if type_ == BEGIN:
                    frag.drawBefore(canvas, dy - y)

                # Text
                if type_ == WORD:
                    canvas.setFont(frag["fontName"], frag["fontSize"])
                    canvas.setFillColor(frag.get("color", style["color"]))
                    canvas.drawString(frag["x"], dy - y + frag["y"], frag["text"])

                # Box
                if type_ == BEGIN:
                    frag.drawAfter(canvas, dy - y)

                # XXX LINK
                link = frag.get("link", None)
                if link:
                    _scheme_re = re.compile('^[a-zA-Z][-+a-zA-Z0-9]+$')
                    x, y, w, h = frag["x"], dy - y, frag["width"], frag["fontSize"]
                    rect = (x, y, w, h)
                    if isinstance(link, unicode):
                        link = link.encode('utf8')
                    parts = link.split(':', 1)
                    scheme = len(parts) == 2 and parts[0].lower() or ''
                    if _scheme_re.match(scheme) and scheme != 'document':
                        kind = scheme.lower() == 'pdf' and 'GoToR' or 'URI'
                        if kind == 'GoToR': link = parts[1]
                        tx._canvas.linkURL(link, rect, relative=1, kind=kind)
                    else:
                        if link[0] == '#':
                            link = link[1:]
                            scheme = ''
                        canvas.linkRect("", scheme != 'document' and link or parts[1], rect, relative=1)

        canvas.restoreState()


if __name__ == "__main__":
    from reportlab.platypus import SimpleDocTemplate
    from reportlab.lib.styles import *
    from reportlab.rl_config import *
    from reportlab.lib.units import *

    import os
    import copy
    import re

    styles = getSampleStyleSheet()

    ALIGNMENTS = (TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY)

    TEXT = """
    Lörem ipsum dolor sit amet, consectetur adipisicing elit,
    sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
    Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi
    ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit
    in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
    Excepteur sint occaecat cupidatat non proident, sunt in culpa qui
    officia deserunt mollit anim id est laborum. Lorem ipsum dolor sit amet,
    consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore
    et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation
    ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure
    dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat
    nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt
    in culpa qui officia deserunt mollit anim id est laborum. Lorem ipsum
    dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor
    incididunt ut labore et dolore magna aliqua.
    """.strip()

    def textGenerator(data, fn, fs):
        i = 1
        for word in re.split('\s+', data):
            if word:
                yield Word(
                    text="[%d|%s]" % (i, word),
                    fontName=fn,
                    fontSize=fs
                )
                yield Space(
                    fontName=fn,
                    fontSize=fs
                )
                i += 1

    def createText(data, fn, fs):
        text = Text(list(textGenerator(data, fn, fs)))
        return text

    def makeBorder(width, style="solid", color=Color(1, 0, 0)):
        return dict(
            borderLeftColor=color,
            borderLeftWidth=width,
            borderLeftStyle=style,
            borderRightColor=color,
            borderRightWidth=width,
            borderRightStyle=style,
            borderTopColor=color,
            borderTopWidth=width,
            borderTopStyle=style,
            borderBottomColor=color,
            borderBottomWidth=width,
            borderBottomStyle=style
        )

    def makeSpecial(fn="Times-Roman", fs=10):
        return [
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="TrennbarTrennbar",
                pairs=[("Trenn-", "barTrennbar")],
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Normal",
                color=Color(1, 0, 0),
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            BoxBegin(
                fontName=fn,
                fontSize=fs,
                underline=True,
                strike=True),
            Word(
                text="gGrößer",
                fontName=fn,
                fontSize=fs * 1.5),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Bold",
                fontName="Times-Bold",
                fontSize=fs),
            BoxEnd(),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="jItalic",
                fontName="Times-Italic",
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),

            # <span style="border: 1px solid red;">ipsum <span style="border: 1px solid green; padding: 4px; padding-left: 20px; background: yellow; margin-bottom: 8px; margin-left: 10px;">
            # Lo<font size="12pt">re</font>m</span> <span style="background:blue; height: 30px;">ipsum</span> Lorem</span>

            BoxBegin(
                fontName=fn,
                fontSize=fs,
                **makeBorder(0.5, "solid", Color(0, 1, 0))),
            Word(
                text="Lorem",
                fontName="Times-Bold",
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName="Times-Bold",
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            BoxBegin(
                fontName=fn,
                fontSize=fs,
                backgroundColor=Color(1, 1, 0),
                **makeBorder(1, "solid", Color(1, 0, 0))),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            BoxEnd(),
            Space(
                fontName=fn,
                fontSize=fs),
            Word(
                text="Lorem",
                fontName=fn,
                fontSize=fs),
            Space(
                fontName=fn,
                fontSize=fs),
            BoxEnd(),

            LineBreak(
                fontName=fn,
                fontSize=fs),
            LineBreak(
                fontName=fn,
                fontSize=fs),
        ]

    def test():
        doc = SimpleDocTemplate("test.pdf")
        story = []

        style = Style(fontName="Helvetica", textIndent=24.0)
        fn = style["fontName"]
        fs = style["fontSize"]
        sampleText1 = createText(TEXT[:100], fn, fs)
        sampleText2 = createText(TEXT[100:], fn, fs)

        text = Text(sampleText1 + makeSpecial(fn, fs) + sampleText2)

        story.append(Paragraph(
            copy.copy(text),
            style,
            debug=0))

        if 0:  # FIXME: Why is this here?
            for i in range(10):
                style = copy.deepcopy(style)
                style["textAlign"] = ALIGNMENTS[i % 4]
                text = createText(("(%d) " % i) + TEXT, fn, fs)
                story.append(Paragraph(
                    copy.copy(text),
                    style,
                    debug=0))

        doc.build(story)

    def test2():
        # text = Text(list(textGenerator(TEXT, "Times-Roman", 10)))
        text = Text(makeSpecial())
        text.calc()
        print (text[1].type)
        while 1:
            width, br, group = text.getGroup()
            if not group:
                print ("ENDE", repr(group))
                break
            print (width, br, " ".join([str(x) for x in group]))

    # test2()
    if 1:  # FIXME: Again, why this? And the commented lines around here.
        test()
        os.system("start test.pdf")

        # createText(TEXT, styles["Normal"].fontName, styles["Normal"].fontSize)

########NEW FILE########
__FILENAME__ = parser
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

from html5lib import treebuilders, inputstream
from xhtml2pdf.default import TAGS, STRING, INT, BOOL, SIZE, COLOR, FILE
from xhtml2pdf.default import BOX, POS, MUST, FONT
from xhtml2pdf.util import getSize, getBool, toList, getColor, getAlign
from xhtml2pdf.util import getBox, getPos, pisaTempFile
from reportlab.platypus.doctemplate import NextPageTemplate, FrameBreak
from reportlab.platypus.flowables import PageBreak, KeepInFrame
from xhtml2pdf.xhtml2pdf_reportlab import PmlRightPageBreak, PmlLeftPageBreak
from xhtml2pdf.tags import * # TODO: Kill wild import!
from xhtml2pdf.tables import * # TODO: Kill wild import!
from xhtml2pdf.util import * # TODO: Kill wild import!
from xml.dom import Node
import copy
import html5lib
import logging
import re
import types
import xhtml2pdf.w3c.cssDOMElementInterface as cssDOMElementInterface
import xml.dom.minidom


CSSAttrCache = {}

log = logging.getLogger("xhtml2pdf")

rxhttpstrip = re.compile("https?://[^/]+(.*)", re.M | re.I)


class AttrContainer(dict):
    def __getattr__(self, name):
        try:
            return dict.__getattr__(self, name)
        except:
            return self[name]


def pisaGetAttributes(c, tag, attributes):
    global TAGS

    attrs = {}
    if attributes:
        for k, v in attributes.items():
            try:
                attrs[str(k)] = str(v)  # XXX no Unicode! Reportlab fails with template names
            except:
                attrs[k] = v

    nattrs = {}
    if tag in TAGS:
        block, adef = TAGS[tag]
        adef["id"] = STRING
        # print block, adef
        for k, v in adef.iteritems():
            nattrs[k] = None
            # print k, v
            # defaults, wenn vorhanden
            if type(v) == types.TupleType:
                if v[1] == MUST:
                    if k not in attrs:
                        log.warn(c.warning("Attribute '%s' must be set!", k))
                        nattrs[k] = None
                        continue
                nv = attrs.get(k, v[1])
                dfl = v[1]
                v = v[0]
            else:
                nv = attrs.get(k, None)
                dfl = None

            if nv is not None:
                if type(v) == types.ListType:
                    nv = nv.strip().lower()
                    if nv not in v:
                        #~ raise PML_EXCEPTION, "attribute '%s' of wrong value, allowed is one of: %s" % (k, repr(v))
                        log.warn(c.warning("Attribute '%s' of wrong value, allowed is one of: %s", k, repr(v)))
                        nv = dfl

                elif v == BOOL:
                    nv = nv.strip().lower()
                    nv = nv in ("1", "y", "yes", "true", str(k))

                elif v == SIZE:
                    try:
                        nv = getSize(nv)
                    except:
                        log.warn(c.warning("Attribute '%s' expects a size value", k))

                elif v == BOX:
                    nv = getBox(nv, c.pageSize)

                elif v == POS:
                    nv = getPos(nv, c.pageSize)

                elif v == INT:
                    nv = int(nv)

                elif v == COLOR:
                    nv = getColor(nv)

                elif v == FILE:
                    nv = c.getFile(nv)

                elif v == FONT:
                    nv = c.getFontName(nv)

                nattrs[k] = nv

    return AttrContainer(nattrs)


attrNames = '''
    color
    font-family
    font-size
    font-weight
    font-style
    text-decoration
    line-height
    letter-spacing
    background-color
    display
    margin-left
    margin-right
    margin-top
    margin-bottom
    padding-left
    padding-right
    padding-top
    padding-bottom
    border-top-color
    border-top-style
    border-top-width
    border-bottom-color
    border-bottom-style
    border-bottom-width
    border-left-color
    border-left-style
    border-left-width
    border-right-color
    border-right-style
    border-right-width
    text-align
    vertical-align
    width
    height
    zoom
    page-break-after
    page-break-before
    list-style-type
    list-style-image
    white-space
    text-indent
    -pdf-page-break
    -pdf-frame-break
    -pdf-next-page
    -pdf-keep-with-next
    -pdf-outline
    -pdf-outline-level
    -pdf-outline-open
    -pdf-line-spacing
    -pdf-keep-in-frame-mode
    -pdf-word-wrap
    '''.strip().split()


def getCSSAttr(self, cssCascade, attrName, default=NotImplemented):
    if attrName in self.cssAttrs:
        return self.cssAttrs[attrName]

    try:
        result = cssCascade.findStyleFor(self.cssElement, attrName, default)
    except LookupError:
        result = None

    # XXX Workaround for inline styles
    try:
        style = self.cssStyle
    except:
        style = self.cssStyle = cssCascade.parser.parseInline(self.cssElement.getStyleAttr() or '')[0]
    if attrName in style:
        result = style[attrName]

    if result == 'inherit':
        if hasattr(self.parentNode, 'getCSSAttr'):
            result = self.parentNode.getCSSAttr(cssCascade, attrName, default)
        elif default is not NotImplemented:
            return default
        raise LookupError("Could not find inherited CSS attribute value for '%s'" % (attrName,))

    if result is not None:
        self.cssAttrs[attrName] = result
    return result


#TODO: Monkeypatching standard lib should go away.
xml.dom.minidom.Element.getCSSAttr = getCSSAttr

# Create an aliasing system.  Many sources use non-standard tags, because browsers allow
# them to.  This allows us to map a nonstandard name to the standard one.
nonStandardAttrNames = {
    'bgcolor': 'background-color',
}

def mapNonStandardAttrs(c, n, attrList):
    for attr in nonStandardAttrNames:
        if attr in attrList and nonStandardAttrNames[attr] not in c:
            c[nonStandardAttrNames[attr]] = attrList[attr]
    return c

def getCSSAttrCacheKey(node):
    _cl = _id = _st = ''
    for k, v in node.attributes.items():
        if k == 'class':
            _cl = v
        elif k == 'id':
            _id = v
        elif k == 'style':
            _st = v
    return "%s#%s#%s#%s#%s" % (id(node.parentNode), node.tagName.lower(), _cl, _id, _st)

def CSSCollect(node, c):
    #node.cssAttrs = {}
    #return node.cssAttrs

    if c.css:

        _key = getCSSAttrCacheKey(node)

        if hasattr(node.parentNode, "tagName"):
            if node.parentNode.tagName.lower() != "html":
                CachedCSSAttr = CSSAttrCache.get(_key, None)
                if CachedCSSAttr is not None:
                    node.cssAttrs = CachedCSSAttr
                    return CachedCSSAttr

        node.cssElement = cssDOMElementInterface.CSSDOMElementInterface(node)
        node.cssAttrs = {}
        # node.cssElement.onCSSParserVisit(c.cssCascade.parser)
        cssAttrMap = {}
        for cssAttrName in attrNames:
            try:
                cssAttrMap[cssAttrName] = node.getCSSAttr(c.cssCascade, cssAttrName)
            #except LookupError:
            #    pass
            except Exception: # TODO: Kill this catch-all!
                log.debug("CSS error '%s'", cssAttrName, exc_info=1)

        CSSAttrCache[_key] = node.cssAttrs

    return node.cssAttrs

def CSS2Frag(c, kw, isBlock):
    # COLORS
    if "color" in c.cssAttr:
        c.frag.textColor = getColor(c.cssAttr["color"])
    if "background-color" in c.cssAttr:
        c.frag.backColor = getColor(c.cssAttr["background-color"])
        # FONT SIZE, STYLE, WEIGHT
    if "font-family" in c.cssAttr:
        c.frag.fontName = c.getFontName(c.cssAttr["font-family"])
    if "font-size" in c.cssAttr:
        # XXX inherit
        c.frag.fontSize = max(getSize("".join(c.cssAttr["font-size"]), c.frag.fontSize, c.baseFontSize), 1.0)
    if "line-height" in c.cssAttr:
        leading = "".join(c.cssAttr["line-height"])
        c.frag.leading = getSize(leading, c.frag.fontSize)
        c.frag.leadingSource = leading
    else:
        c.frag.leading = getSize(c.frag.leadingSource, c.frag.fontSize)
    if "letter-spacing" in c.cssAttr:
        c.frag.letterSpacing = c.cssAttr["letter-spacing"]
    if "-pdf-line-spacing" in c.cssAttr:
        c.frag.leadingSpace = getSize("".join(c.cssAttr["-pdf-line-spacing"]))
        # print "line-spacing", c.cssAttr["-pdf-line-spacing"], c.frag.leading
    if "font-weight" in c.cssAttr:
        value = c.cssAttr["font-weight"].lower()
        if value in ("bold", "bolder", "500", "600", "700", "800", "900"):
            c.frag.bold = 1
        else:
            c.frag.bold = 0
    for value in toList(c.cssAttr.get("text-decoration", "")):
        if "underline" in value:
            c.frag.underline = 1
        if "line-through" in value:
            c.frag.strike = 1
        if "none" in value:
            c.frag.underline = 0
            c.frag.strike = 0
    if "font-style" in c.cssAttr:
        value = c.cssAttr["font-style"].lower()
        if value in ("italic", "oblique"):
            c.frag.italic = 1
        else:
            c.frag.italic = 0
    if "white-space" in c.cssAttr:
        # normal | pre | nowrap
        c.frag.whiteSpace = str(c.cssAttr["white-space"]).lower()
        # ALIGN & VALIGN
    if "text-align" in c.cssAttr:
        c.frag.alignment = getAlign(c.cssAttr["text-align"])
    if "vertical-align" in c.cssAttr:
        c.frag.vAlign = c.cssAttr["vertical-align"]
        # HEIGHT & WIDTH
    if "height" in c.cssAttr:
        c.frag.height = "".join(toList(c.cssAttr["height"]))  # XXX Relative is not correct!
        if c.frag.height in ("auto",):
            c.frag.height = None
    if "width" in c.cssAttr:
        c.frag.width = "".join(toList(c.cssAttr["width"]))  # XXX Relative is not correct!
        if c.frag.width in ("auto",):
            c.frag.width = None
        # ZOOM
    if "zoom" in c.cssAttr:
        zoom = "".join(toList(c.cssAttr["zoom"]))  # XXX Relative is not correct!
        if zoom.endswith("%"):
            zoom = float(zoom[: - 1]) / 100.0
        c.frag.zoom = float(zoom)
        # MARGINS & LIST INDENT, STYLE
    if isBlock:
        if "margin-top" in c.cssAttr:
            c.frag.spaceBefore = getSize(c.cssAttr["margin-top"], c.frag.fontSize)
        if "margin-bottom" in c.cssAttr:
            c.frag.spaceAfter = getSize(c.cssAttr["margin-bottom"], c.frag.fontSize)
        if "margin-left" in c.cssAttr:
            c.frag.bulletIndent = kw["margin-left"]  # For lists
            kw["margin-left"] += getSize(c.cssAttr["margin-left"], c.frag.fontSize)
            c.frag.leftIndent = kw["margin-left"]
        if "margin-right" in c.cssAttr:
            kw["margin-right"] += getSize(c.cssAttr["margin-right"], c.frag.fontSize)
            c.frag.rightIndent = kw["margin-right"]
        if "text-indent" in c.cssAttr:
            c.frag.firstLineIndent = getSize(c.cssAttr["text-indent"], c.frag.fontSize)
        if "list-style-type" in c.cssAttr:
            c.frag.listStyleType = str(c.cssAttr["list-style-type"]).lower()
        if "list-style-image" in c.cssAttr:
            c.frag.listStyleImage = c.getFile(c.cssAttr["list-style-image"])
        # PADDINGS
    if isBlock:
        if "padding-top" in c.cssAttr:
            c.frag.paddingTop = getSize(c.cssAttr["padding-top"], c.frag.fontSize)
        if "padding-bottom" in c.cssAttr:
            c.frag.paddingBottom = getSize(c.cssAttr["padding-bottom"], c.frag.fontSize)
        if "padding-left" in c.cssAttr:
            c.frag.paddingLeft = getSize(c.cssAttr["padding-left"], c.frag.fontSize)
        if "padding-right" in c.cssAttr:
            c.frag.paddingRight = getSize(c.cssAttr["padding-right"], c.frag.fontSize)
        # BORDERS
    if isBlock:
        if "border-top-width" in c.cssAttr:
            c.frag.borderTopWidth = getSize(c.cssAttr["border-top-width"], c.frag.fontSize)
        if "border-bottom-width" in c.cssAttr:
            c.frag.borderBottomWidth = getSize(c.cssAttr["border-bottom-width"], c.frag.fontSize)
        if "border-left-width" in c.cssAttr:
            c.frag.borderLeftWidth = getSize(c.cssAttr["border-left-width"], c.frag.fontSize)
        if "border-right-width" in c.cssAttr:
            c.frag.borderRightWidth = getSize(c.cssAttr["border-right-width"], c.frag.fontSize)
        if "border-top-style" in c.cssAttr:
            c.frag.borderTopStyle = c.cssAttr["border-top-style"]
        if "border-bottom-style" in c.cssAttr:
            c.frag.borderBottomStyle = c.cssAttr["border-bottom-style"]
        if "border-left-style" in c.cssAttr:
            c.frag.borderLeftStyle = c.cssAttr["border-left-style"]
        if "border-right-style" in c.cssAttr:
            c.frag.borderRightStyle = c.cssAttr["border-right-style"]
        if "border-top-color" in c.cssAttr:
            c.frag.borderTopColor = getColor(c.cssAttr["border-top-color"])
        if "border-bottom-color" in c.cssAttr:
            c.frag.borderBottomColor = getColor(c.cssAttr["border-bottom-color"])
        if "border-left-color" in c.cssAttr:
            c.frag.borderLeftColor = getColor(c.cssAttr["border-left-color"])
        if "border-right-color" in c.cssAttr:
            c.frag.borderRightColor = getColor(c.cssAttr["border-right-color"])


def pisaPreLoop(node, context, collect=False):
    """
    Collect all CSS definitions
    """

    data = u""
    if node.nodeType == Node.TEXT_NODE and collect:
        data = node.data

    elif node.nodeType == Node.ELEMENT_NODE:
        name = node.tagName.lower()

        if name in ("style", "link"):
            attr = pisaGetAttributes(context, name, node.attributes)
            media = [x.strip() for x in attr.media.lower().split(",") if x.strip()]

            if attr.get("type", "").lower() in ("", "text/css") and \
                    (not media or "all" in media or "print" in media or "pdf" in media):

                if name == "style":
                    for node in node.childNodes:
                        data += pisaPreLoop(node, context, collect=True)
                    context.addCSS(data)
                    return u""

                if name == "link" and attr.href and attr.rel.lower() == "stylesheet":
                    # print "CSS LINK", attr
                    context.addCSS('\n@import "%s" %s;' % (attr.href, ",".join(media)))

    for node in node.childNodes:
        result = pisaPreLoop(node, context, collect=collect)
        if collect:
            data += result

    return data


def pisaLoop(node, context, path=None, **kw):

    if path is None:
        path = []

    # Initialize KW
    if not kw:
        kw = {
            "margin-top": 0,
            "margin-bottom": 0,
            "margin-left": 0,
            "margin-right": 0,
        }
    else:
        kw = copy.copy(kw)

    #indent = len(path) * "  " # only used for debug print statements

    # TEXT
    if node.nodeType == Node.TEXT_NODE:
        # print indent, "#", repr(node.data) #, context.frag
        context.addFrag(node.data)

        # context.text.append(node.value)

    # ELEMENT
    elif node.nodeType == Node.ELEMENT_NODE:

        node.tagName = node.tagName.replace(":", "").lower()

        if node.tagName in ("style", "script"):
            return

        path = copy.copy(path) + [node.tagName]

        # Prepare attributes
        attr = pisaGetAttributes(context, node.tagName, node.attributes)
        #log.debug(indent + "<%s %s>" % (node.tagName, attr) + repr(node.attributes.items())) #, path

        # Calculate styles
        context.cssAttr = CSSCollect(node, context)
        context.cssAttr = mapNonStandardAttrs(context.cssAttr, node, attr)
        context.node = node

        # Block?
        PAGE_BREAK = 1
        PAGE_BREAK_RIGHT = 2
        PAGE_BREAK_LEFT = 3

        pageBreakAfter = False
        frameBreakAfter = False
        display = context.cssAttr.get("display", "inline").lower()
        # print indent, node.tagName, display, context.cssAttr.get("background-color", None), attr
        isBlock = (display == "block")

        if isBlock:
            context.addPara()

            # Page break by CSS
            if "-pdf-next-page" in context.cssAttr:
                context.addStory(NextPageTemplate(str(context.cssAttr["-pdf-next-page"])))
            if "-pdf-page-break" in context.cssAttr:
                if str(context.cssAttr["-pdf-page-break"]).lower() == "before":
                    context.addStory(PageBreak())
            if "-pdf-frame-break" in context.cssAttr:
                if str(context.cssAttr["-pdf-frame-break"]).lower() == "before":
                    context.addStory(FrameBreak())
                if str(context.cssAttr["-pdf-frame-break"]).lower() == "after":
                    frameBreakAfter = True
            if "page-break-before" in context.cssAttr:
                if str(context.cssAttr["page-break-before"]).lower() == "always":
                    context.addStory(PageBreak())
                if str(context.cssAttr["page-break-before"]).lower() == "right":
                    context.addStory(PageBreak())
                    context.addStory(PmlRightPageBreak())
                if str(context.cssAttr["page-break-before"]).lower() == "left":
                    context.addStory(PageBreak())
                    context.addStory(PmlLeftPageBreak())
            if "page-break-after" in context.cssAttr:
                if str(context.cssAttr["page-break-after"]).lower() == "always":
                    pageBreakAfter = PAGE_BREAK
                if str(context.cssAttr["page-break-after"]).lower() == "right":
                    pageBreakAfter = PAGE_BREAK_RIGHT
                if str(context.cssAttr["page-break-after"]).lower() == "left":
                    pageBreakAfter = PAGE_BREAK_LEFT

        if display == "none":
            # print "none!"
            return

        # Translate CSS to frags

        # Save previous frag styles
        context.pushFrag()

        # Map styles to Reportlab fragment properties
        CSS2Frag(context, kw, isBlock)

        # EXTRAS
        if "-pdf-keep-with-next" in context.cssAttr:
            context.frag.keepWithNext = getBool(context.cssAttr["-pdf-keep-with-next"])
        if "-pdf-outline" in context.cssAttr:
            context.frag.outline = getBool(context.cssAttr["-pdf-outline"])
        if "-pdf-outline-level" in context.cssAttr:
            context.frag.outlineLevel = int(context.cssAttr["-pdf-outline-level"])
        if "-pdf-outline-open" in context.cssAttr:
            context.frag.outlineOpen = getBool(context.cssAttr["-pdf-outline-open"])
        if "-pdf-word-wrap" in context.cssAttr:
            context.frag.wordWrap = context.cssAttr["-pdf-word-wrap"]

        # handle keep-in-frame
        keepInFrameMode = None
        keepInFrameMaxWidth = 0
        keepInFrameMaxHeight = 0
        if "-pdf-keep-in-frame-mode" in context.cssAttr:
            value = str(context.cssAttr["-pdf-keep-in-frame-mode"]).strip().lower()
            if value in ("shrink", "error", "overflow", "truncate"):
                keepInFrameMode = value
        if "-pdf-keep-in-frame-max-width" in context.cssAttr:
            keepInFrameMaxWidth = getSize("".join(context.cssAttr["-pdf-keep-in-frame-max-width"]))
        if "-pdf-keep-in-frame-max-height" in context.cssAttr:
            keepInFrameMaxHeight = getSize("".join(context.cssAttr["-pdf-keep-in-frame-max-height"]))

        # ignore nested keep-in-frames, tables have their own KIF handling
        keepInFrame = keepInFrameMode is not None and context.keepInFrameIndex is None
        if keepInFrame:
            # keep track of current story index, so we can wrap everythink
            # added after this point in a KeepInFrame
            context.keepInFrameIndex = len(context.story)

        # BEGIN tag
        klass = globals().get("pisaTag%s" % node.tagName.replace(":", "").upper(), None)
        obj = None

        # Static block
        elementId = attr.get("id", None)
        staticFrame = context.frameStatic.get(elementId, None)
        if staticFrame:
            context.frag.insideStaticFrame += 1
            oldStory = context.swapStory()

        # Tag specific operations
        if klass is not None:
            obj = klass(node, attr)
            obj.start(context)

        # Visit child nodes
        context.fragBlock = fragBlock = copy.copy(context.frag)
        for nnode in node.childNodes:
            pisaLoop(nnode, context, path, **kw)
        context.fragBlock = fragBlock

        # END tag
        if obj:
            obj.end(context)

        # Block?
        if isBlock:
            context.addPara()

            # XXX Buggy!

            # Page break by CSS
            if pageBreakAfter:
                context.addStory(PageBreak())
                if pageBreakAfter == PAGE_BREAK_RIGHT:
                    context.addStory(PmlRightPageBreak())
                if pageBreakAfter == PAGE_BREAK_LEFT:
                    context.addStory(PmlLeftPageBreak())
            if frameBreakAfter:
                context.addStory(FrameBreak())

        if keepInFrame:
            # get all content added after start of -pdf-keep-in-frame and wrap
            # it in a KeepInFrame
            substory = context.story[context.keepInFrameIndex:]
            context.story = context.story[:context.keepInFrameIndex]
            context.story.append(
                KeepInFrame(
                    content=substory,
                    maxWidth=keepInFrameMaxWidth,
                    maxHeight=keepInFrameMaxHeight))
            context.keepInFrameIndex = None

        # Static block, END
        if staticFrame:
            context.addPara()
            for frame in staticFrame:
                frame.pisaStaticStory = context.story
            context.swapStory(oldStory)
            context.frag.insideStaticFrame -= 1

        # context.debug(1, indent, "</%s>" % (node.tagName))

        # Reset frag style
        context.pullFrag()

    # Unknown or not handled
    else:
        # context.debug(1, indent, "???", node, node.nodeType, repr(node))
        # Loop over children
        for node in node.childNodes:
            pisaLoop(node, context, path, **kw)


def pisaParser(src, context, default_css="", xhtml=False, encoding=None, xml_output=None):
    """
    - Parse HTML and get miniDOM
    - Extract CSS informations, add default CSS, parse CSS
    - Handle the document DOM itself and build reportlab story
    - Return Context object
    """

    global CSSAttrCache
    CSSAttrCache = {}

    if xhtml:
        #TODO: XHTMLParser doesn't see to exist...
        parser = html5lib.XHTMLParser(tree=treebuilders.getTreeBuilder("dom"))
    else:
        parser = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("dom"))

    if type(src) in types.StringTypes:
        if type(src) is types.UnicodeType:
            # If an encoding was provided, do not change it.
            if not encoding:
                encoding = "utf-8"
            src = src.encode(encoding)
        src = pisaTempFile(src, capacity=context.capacity)

    # Test for the restrictions of html5lib
    if encoding:
        # Workaround for html5lib<0.11.1
        if hasattr(inputstream, "isValidEncoding"):
            if encoding.strip().lower() == "utf8":
                encoding = "utf-8"
            if not inputstream.isValidEncoding(encoding):
                log.error("%r is not a valid encoding e.g. 'utf8' is not valid but 'utf-8' is!", encoding)
        else:
            if inputstream.codecName(encoding) is None:
                log.error("%r is not a valid encoding", encoding)
    document = parser.parse(
        src,
        encoding=encoding)

    if xml_output:
        if encoding:
            xml_output.write(document.toprettyxml(encoding=encoding))
        else:
            xml_output.write(document.toprettyxml(encoding="utf8"))


    if default_css:
        context.addDefaultCSS(default_css)

    pisaPreLoop(document, context)
    #try:
    context.parseCSS()
    #except:
    #    context.cssText = DEFAULT_CSS
    #    context.parseCSS()
    # context.debug(9, pprint.pformat(context.css))

    pisaLoop(document, context)
    return context


# Shortcuts

HTML2PDF = pisaParser


def XHTML2PDF(*a, **kw):
    kw["xhtml"] = True
    return HTML2PDF(*a, **kw)


XML2PDF = XHTML2PDF

########NEW FILE########
__FILENAME__ = pdf
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

from xhtml2pdf.util import pisaTempFile, getFile, PyPDF2

import logging


log = logging.getLogger("xhtml2pdf")


class pisaPDF:
    def __init__(self, capacity=-1):
        self.capacity = capacity
        self.files = []

    def addFromURI(self, url, basepath=None):
        obj = getFile(url, basepath)
        if obj and (not obj.notFound()):
            self.files.append(obj.getFile())

    addFromFileName = addFromURI

    def addFromFile(self, f):
        if hasattr(f, "read"):
            self.files.append(f)
        self.addFromURI(f)

    def addFromString(self, data):
        self.files.append(pisaTempFile(data, capacity=self.capacity))

    def addDocument(self, doc):
        if hasattr(doc.dest, "read"):
            self.files.append(doc.dest)

    def join(self, file=None):
        output = PyPDF2.PdfFileWriter()
        for pdffile in self.files:
            input = PyPDF2.PdfFileReader(pdffile)
            for pageNumber in xrange(input.getNumPages()):
                output.addPage(input.getPage(pageNumber))

        if file is not None:
            output.write(file)
            return file
        out = pisaTempFile(capacity=self.capacity)
        output.write(out)
        return out.getvalue()

    getvalue = join
    __str__ = join

########NEW FILE########
__FILENAME__ = pisa
# -*- coding: utf-8 -*-
from xhtml2pdf.default import DEFAULT_CSS
from xhtml2pdf.document import pisaDocument
from xhtml2pdf.util import getFile
from xhtml2pdf.version import VERSION, VERSION_STR
import getopt
import glob
import logging
import os
import sys
import tempfile
import urllib2
import urlparse

# Copyright 2010 Dirk Holtwick, holtwick.it
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

log = logging.getLogger("xhtml2pdf")

__version__ = VERSION

# Backward compatibility
CreatePDF = pisaDocument

USAGE = (VERSION_STR + """

USAGE: pisa [options] SRC [DEST]

SRC
  Name of a HTML file or a file pattern using * placeholder.
  If you want to read from stdin use "-" as file name.
  You may also load an URL over HTTP. Take care of putting
  the <src> in quotes if it contains characters like "?".

DEST
  Name of the generated PDF file or "-" if you like
  to send the result to stdout. Take care that the
  destination file is not already opened by an other
  application like the Adobe Reader. If the destination is
  not writeable a similar name will be calculated automatically.

[options]
  --base, -b:
    Specify a base path if input come via STDIN
  --css, -c:
    Path to default CSS file
  --css-dump:
    Dumps the default CSS definitions to STDOUT
  --debug, -d:
    Show debugging informations
  --encoding:
    the character encoding of SRC. If left empty (default) this
    information will be extracted from the HTML header data
  --help, -h:
    Show this help text
  --quiet, -q:
    Show no messages
  --start-viewer, -s:
    Start PDF default viewer on Windows and MacOSX
    (e.g. AcrobatReader)
  --version:
    Show version information
  --warn, -w:
    Show warnings
  --xml, --xhtml, -x:
    Force parsing in XML Mode
    (automatically used if file ends with ".xml")
  --html:
    Force parsing in HTML Mode (default)
""").strip()

COPYRIGHT = VERSION_STR

LOG_FORMAT = "%(levelname)s [%(name)s] %(message)s"
LOG_FORMAT_DEBUG = "%(levelname)s [%(name)s] %(pathname)s line %(lineno)d: %(message)s"


def usage():
    print (USAGE)


class pisaLinkLoader:
    """
    Helper to load page from an URL and load corresponding
    files to temporary files. If getFileName is called it
    returns the temporary filename and takes care to delete
    it when pisaLinkLoader is unloaded.
    """

    def __init__(self, src, quiet=True):
        self.quiet = quiet
        self.src = src
        self.tfileList = []

    def __del__(self):
        for path in self.tfileList:
            os.remove(path)

    def getFileName(self, name, relative=None):
        url = urlparse.urljoin(relative or self.src, name)
        path = urlparse.urlsplit(url)[2]
        suffix = ""
        if "." in path:
            new_suffix = "." + path.split(".")[-1].lower()
            if new_suffix in (".css", ".gif", ".jpg", ".png"):
                suffix = new_suffix
        path = tempfile.mktemp(prefix="pisa-", suffix=suffix)
        ufile = urllib2.urlopen(url)
        tfile = file(path, "wb")
        while True:
            data = ufile.read(1024)
            if not data:
                break
            tfile.write(data)
        ufile.close()
        tfile.close()
        self.tfileList.append(path)

        if not self.quiet:
            print ("  Loading", url, "to", path)

        return path


def command():
    if "--profile" in sys.argv:
        print ("*** PROFILING ENABLED")
        import cProfile as profile
        import pstats

        prof = profile.Profile()
        prof.runcall(execute)
        pstats.Stats(prof).strip_dirs().sort_stats('cumulative').print_stats()
    else:
        execute()


def execute():

    try:
        opts, args = getopt.getopt(sys.argv[1:], "dhqstwcxb", [
            "quiet",
            "help",
            "start-viewer",
            "start",
            "debug=",
            "copyright",
            "version",
            "warn",
            "tempdir=",
            "format=",
            "css=",
            "base=",
            "css-dump",
            "xml-dump",
            "xhtml",
            "xml",
            "html",
            "encoding=",
            "system",
            "profile",
        ])
    except getopt.GetoptError:
        usage()
        sys.exit(2)

    errors = 0
    startviewer = 0
    quiet = 0
    debug = 0
    tempdir = None
    format = "pdf"
    css = None
    xhtml = None
    encoding = None
    xml_output = None
    base_dir = None

    log_level = logging.ERROR
    log_format = LOG_FORMAT

    for o, a in opts:

        if o in ("-h", "--help"):
            # Hilfe anzeigen
            usage()
            sys.exit()

        if o in ("-s", "--start-viewer", "--start"):
            # Anzeigeprogramm starten
            startviewer = 1

        if o in ("-q", "--quiet"):
            # Output unterdr�cken
            quiet = 1

        if o in ("-w", "--warn"):
            # Warnings
            log_level = min(log_level, logging.WARN)  # If also -d ignore -w

        if o in ("-d", "--debug"):
            # Debug
            log_level = logging.DEBUG
            log_format = LOG_FORMAT_DEBUG

            if a:
                log_level = int(a)

        if o in ("--copyright", "--version"):
            print (COPYRIGHT)
            sys.exit(0)

        if o in ("--system",):
            print (COPYRIGHT)
            print ()
            print ("SYSTEM INFORMATIONS")
            print ("--------------------------------------------")
            print ("OS:                ", sys.platform)
            print ("Python:            ", sys.version)
            print ("html5lib:          ", "?")
            import reportlab

            print ("Reportlab:         ", reportlab.Version)
            sys.exit(0)

        if o in ("-t", "--format"):
            # Format XXX ???
            format = a

        if o in ("-b", "--base"):
            base_dir = a

        if o in ("--encoding",) and a:
            # Encoding
            encoding = a

        if o in ("-c", "--css"):
            # CSS
            css = file(a, "r").read()

        if o in ("--css-dump",):
            # CSS dump
            print (DEFAULT_CSS)
            return

        if o in ("--xml-dump",):
            xml_output = sys.stdout

        if o in ("-x", "--xml", "--xhtml"):
            xhtml = True
        elif o in ("--html",):
            xhtml = False

    if not quiet:
        try:
            logging.basicConfig(
                level=log_level,
                format=log_format)
        except:
            # XXX Logging doesn't work for Python 2.3
            logging.basicConfig()

    if len(args) not in (1, 2):
        usage()
        sys.exit(2)

    if len(args) == 2:
        a_src, a_dest = args
    else:
        a_src = args[0]
        a_dest = None

    if "*" in a_src:
        a_src = glob.glob(a_src)
        # print a_src
    else:
        a_src = [a_src]

    for src in a_src:

        # If not forced to parse in a special way have a look
        # at the filename suffix
        if xhtml is None:
            xhtml = src.lower().endswith(".xml")

        lc = None

        if src == "-" or base_dir is not None:
            # Output to console
            fsrc = sys.stdin
            wpath = os.getcwd()
            if base_dir:
                wpath = base_dir
        else:
            if src.startswith("http:") or src.startswith("https:"):
                wpath = src
                fsrc = getFile(src).getFile()
                src = "".join(urlparse.urlsplit(src)[1:3]).replace("/", "-")
            else:
                fsrc = wpath = os.path.abspath(src)
                fsrc = open(fsrc, "rb")

        if a_dest is None:
            dest_part = src
            if dest_part.lower().endswith(".html") or dest_part.lower().endswith(".htm"):
                dest_part = ".".join(src.split(".")[:-1])
            dest = dest_part + "." + format.lower()
            for i in xrange(10):
                try:
                    open(dest, "wb").close()
                    break
                except:
                    pass
                dest = dest_part + "-%d.%s" % (i, format.lower())
        else:
            dest = a_dest

        fdestclose = 0

        if dest == "-" or base_dir:
            if sys.platform == "win32":
                import msvcrt
                msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

            fdest = sys.stdout
            startviewer = 0
        else:
            dest = os.path.abspath(dest)
            try:
                open(dest, "wb").close()
            except:
                print ("File '%s' seems to be in use of another application.") % dest
                sys.exit(2)
            fdest = open(dest, "wb")
            fdestclose = 1

        if not quiet:
            print ("Converting %s to %s...") % (src, dest)

        pdf = pisaDocument(
            fsrc,
            fdest,
            debug=debug,
            path=wpath,
            errout=sys.stdout,
            tempdir=tempdir,
            format=format,
            link_callback=lc,
            default_css=css,
            xhtml=xhtml,
            encoding=encoding,
            xml_output=xml_output,
        )

        if xml_output:
            xml_output.getvalue()

        if fdestclose:
            fdest.close()

        if (not errors) and startviewer:
            if not quiet:
                print ("Open viewer for file %s") % dest
            startViewer(dest)


def startViewer(filename):
    """
    Helper for opening a PDF file
    """

    if filename:
        try:
            os.startfile(filename)
        except:
            # try to opan a la apple
            os.system('open "%s"' % filename)


def showLogging(debug=False):
    """
    Shortcut for enabling log dump
    """

    try:
        log_level = logging.WARN
        log_format = LOG_FORMAT_DEBUG
        if debug:
            log_level = logging.DEBUG
        logging.basicConfig(
            level=log_level,
            format=log_format)
    except:
        logging.basicConfig()


# Background informations in data URI here:
# http://en.wikipedia.org/wiki/Data_URI_scheme

def makeDataURI(data=None, mimetype=None, filename=None):
    import base64

    if not mimetype:
        if filename:
            import mimetypes


            mimetype = mimetypes.guess_type(filename)[0].split(";")[0]
        else:
            raise Exception("You need to provide a mimetype or a filename for makeDataURI")
    return "data:" + mimetype + ";base64," + "".join(base64.encodestring(data).split())


def makeDataURIFromFile(filename):
    data = open(filename, "rb").read()
    return makeDataURI(data, filename=filename)


if __name__ == "__main__":
    command()

########NEW FILE########
__FILENAME__ = reportlab_paragraph
# -*- coding: utf-8 -*-
# Copyright ReportLab Europe Ltd. 2000-2008
# see license.txt for license details
# history http://www.reportlab.co.uk/cgi-bin/viewcvs.cgi/public/reportlab/trunk/reportlab/platypus/paragraph.py
# Modifications by Dirk Holtwick, 2008
from string import join, whitespace
from operator import truth
from reportlab.pdfbase.pdfmetrics import stringWidth, getAscentDescent
from reportlab.platypus.paraparser import ParaParser
from reportlab.platypus.flowables import Flowable
from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.textsplit import ALL_CANNOT_START
from copy import deepcopy
from reportlab.lib.abag import ABag
import re


PARAGRAPH_DEBUG = False
LEADING_FACTOR = 1.0

_wsc_re_split = re.compile('[%s]+' % re.escape(''.join((
    u'\u0009',  # HORIZONTAL TABULATION
    u'\u000A',  # LINE FEED
    u'\u000B',  # VERTICAL TABULATION
    u'\u000C',  # FORM FEED
    u'\u000D',  # CARRIAGE RETURN
    u'\u001C',  # FILE SEPARATOR
    u'\u001D',  # GROUP SEPARATOR
    u'\u001E',  # RECORD SEPARATOR
    u'\u001F',  # UNIT SEPARATOR
    u'\u0020',  # SPACE
    u'\u0085',  # NEXT LINE
    #u'\u00A0', # NO-BREAK SPACE
    u'\u1680',  # OGHAM SPACE MARK
    u'\u2000',  # EN QUAD
    u'\u2001',  # EM QUAD
    u'\u2002',  # EN SPACE
    u'\u2003',  # EM SPACE
    u'\u2004',  # THREE-PER-EM SPACE
    u'\u2005',  # FOUR-PER-EM SPACE
    u'\u2006',  # SIX-PER-EM SPACE
    u'\u2007',  # FIGURE SPACE
    u'\u2008',  # PUNCTUATION SPACE
    u'\u2009',  # THIN SPACE
    u'\u200A',  # HAIR SPACE
    u'\u200B',  # ZERO WIDTH SPACE
    u'\u2028',  # LINE SEPARATOR
    u'\u2029',  # PARAGRAPH SEPARATOR
    u'\u202F',  # NARROW NO-BREAK SPACE
    u'\u205F',  # MEDIUM MATHEMATICAL SPACE
    u'\u3000',  # IDEOGRAPHIC SPACE
)))).split


def split(text, delim=None):
    if type(text) is str:
        text = text.decode('utf8')
    if type(delim) is str:
        delim = delim.decode('utf8')
    elif delim is None and u'\xa0' in text:
        return [uword.encode('utf8') for uword in _wsc_re_split(text)]
    return [uword.encode('utf8') for uword in text.split(delim)]


def strip(text):
    if type(text) is str:
        text = text.decode('utf8')
    return text.strip().encode('utf8')


class ParaLines(ABag):
    """
    class ParaLines contains the broken into lines representation of Paragraphs
        kind=0  Simple
        fontName, fontSize, textColor apply to whole Paragraph
        lines   [(extraSpace1,words1),....,(extraspaceN,wordsN)]

        kind==1 Complex
        lines   [FragLine1,...,FragLineN]
    """


class FragLine(ABag):
    """
    class FragLine contains a styled line (ie a line with more than one style)::

    extraSpace  unused space for justification only
    wordCount   1+spaces in line for justification purposes
    words       [ParaFrags] style text lumps to be concatenated together
    fontSize    maximum fontSize seen on the line; not used at present,
                but could be used for line spacing.
    """

#our one and only parser
# XXXXX if the parser has any internal state using only one is probably a BAD idea!
_parser = ParaParser()


def _lineClean(L):
    return join(filter(truth, split(strip(L))))


def cleanBlockQuotedText(text, joiner=' '):
    """This is an internal utility which takes triple-
    quoted text form within the document and returns
    (hopefully) the paragraph the user intended originally."""
    L = filter(truth, map(_lineClean, split(text, '\n')))
    return join(L, joiner)


def setXPos(tx, dx):
    if dx > 1e-6 or dx < -1e-6:
        tx.setXPos(dx)


def _leftDrawParaLine(tx, offset, extraspace, words, last=0):
    setXPos(tx, offset)
    tx._textOut(join(words), 1)
    setXPos(tx, -offset)
    return offset


def _centerDrawParaLine(tx, offset, extraspace, words, last=0):
    m = offset + 0.5 * extraspace
    setXPos(tx, m)
    tx._textOut(join(words), 1)
    setXPos(tx, -m)
    return m


def _rightDrawParaLine(tx, offset, extraspace, words, last=0):
    m = offset + extraspace
    setXPos(tx, m)
    tx._textOut(join(words), 1)
    setXPos(tx, -m)
    return m


def _justifyDrawParaLine(tx, offset, extraspace, words, last=0):
    setXPos(tx, offset)
    text = join(words)
    if last:
        #last one, left align
        tx._textOut(text, 1)
    else:
        nSpaces = len(words) - 1
        if nSpaces:
            tx.setWordSpace(extraspace / float(nSpaces))
            tx._textOut(text, 1)
            tx.setWordSpace(0)
        else:
            tx._textOut(text, 1)
    setXPos(tx, -offset)
    return offset


def imgVRange(h, va, fontSize):
    """
    return bottom,top offsets relative to baseline(0)
    """

    if va == 'baseline':
        iyo = 0
    elif va in ('text-top', 'top'):
        iyo = fontSize - h
    elif va == 'middle':
        iyo = fontSize - (1.2 * fontSize + h) * 0.5
    elif va in ('text-bottom', 'bottom'):
        iyo = fontSize - 1.2 * fontSize
    elif va == 'super':
        iyo = 0.5 * fontSize
    elif va == 'sub':
        iyo = -0.5 * fontSize
    elif hasattr(va, 'normalizedValue'):
        iyo = va.normalizedValue(fontSize)
    else:
        iyo = va
    return iyo, iyo + h


_56 = 5. / 6
_16 = 1. / 6


def _putFragLine(cur_x, tx, line):
    xs = tx.XtraState
    cur_y = xs.cur_y
    x0 = tx._x0
    autoLeading = xs.autoLeading
    leading = xs.leading
    cur_x += xs.leftIndent
    dal = autoLeading in ('min', 'max')
    if dal:
        if autoLeading == 'max':
            ascent = max(_56 * leading, line.ascent)
            descent = max(_16 * leading, -line.descent)
        else:
            ascent = line.ascent
            descent = -line.descent
        leading = ascent + descent
    if tx._leading != leading:
        tx.setLeading(leading)
    if dal:
        olb = tx._olb
        if olb is not None:
            xcy = olb - ascent
            if tx._oleading != leading:
                cur_y += leading - tx._oleading
            if abs(xcy - cur_y) > 1e-8:
                cur_y = xcy
                tx.setTextOrigin(x0, cur_y)
                xs.cur_y = cur_y
        tx._olb = cur_y - descent
        tx._oleading = leading

    # Letter spacing
    if xs.style.letterSpacing != 'normal':
        tx.setCharSpace(int(xs.style.letterSpacing))

    ws = getattr(tx, '_wordSpace', 0)
    nSpaces = 0
    words = line.words
    for f in words:
        if hasattr(f, 'cbDefn'):
            cbDefn = f.cbDefn
            kind = cbDefn.kind
            if kind == 'img':
                #draw image cbDefn,cur_y,cur_x
                w = cbDefn.width
                h = cbDefn.height
                txfs = tx._fontsize
                if txfs is None:
                    txfs = xs.style.fontSize
                iy0, iy1 = imgVRange(h, cbDefn.valign, txfs)
                cur_x_s = cur_x + nSpaces * ws
                tx._canvas.drawImage(cbDefn.image.getImage(), cur_x_s, cur_y + iy0, w, h, mask='auto')
                cur_x += w
                cur_x_s += w
                setXPos(tx, cur_x_s - tx._x0)
            elif kind == 'barcode':
                barcode = cbDefn.barcode
                w = cbDefn.width
                h = cbDefn.height
                txfs = tx._fontsize
                if txfs is None:
                    txfs = xs.style.fontSize
                iy0, iy1 = imgVRange(h, cbDefn.valign, txfs)
                cur_x_s = cur_x + nSpaces * ws
                barcode.draw(canvas=tx._canvas, xoffset=cur_x_s)
                cur_x += w
                cur_x_s += w
                setXPos(tx, cur_x_s - tx._x0)
            else:
                name = cbDefn.name
                if kind == 'anchor':
                    tx._canvas.bookmarkHorizontal(name, cur_x, cur_y + leading)
                else:
                    func = getattr(tx._canvas, name, None)
                    if not func:
                        raise AttributeError("Missing %s callback attribute '%s'" % (kind, name))
                    func(tx._canvas, kind, cbDefn.label)
            if f is words[-1]:
                if not tx._fontname:
                    tx.setFont(xs.style.fontName, xs.style.fontSize)
                    tx._textOut('', 1)
                elif kind == 'img':
                    tx._textOut('', 1)
        else:
            cur_x_s = cur_x + nSpaces * ws
            if (tx._fontname, tx._fontsize) != (f.fontName, f.fontSize):
                tx._setFont(f.fontName, f.fontSize)
            if xs.textColor != f.textColor:
                xs.textColor = f.textColor
                tx.setFillColor(f.textColor)
            if xs.rise != f.rise:
                xs.rise = f.rise
                tx.setRise(f.rise)
            text = f.text
            tx._textOut(text, f is words[-1])    # cheap textOut

            # XXX Modified for XHTML2PDF
            # Background colors (done like underline)
            if hasattr(f, "backColor"):
                if xs.backgroundColor != f.backColor or xs.backgroundFontSize != f.fontSize:
                    if xs.backgroundColor is not None:
                        xs.backgrounds.append((xs.background_x, cur_x_s, xs.backgroundColor, xs.backgroundFontSize))
                    xs.background_x = cur_x_s
                    xs.backgroundColor = f.backColor
                    xs.backgroundFontSize = f.fontSize

            # Underline
            if not xs.underline and f.underline:
                xs.underline = 1
                xs.underline_x = cur_x_s
                xs.underlineColor = f.textColor
            elif xs.underline:
                if not f.underline:
                    xs.underline = 0
                    xs.underlines.append((xs.underline_x, cur_x_s, xs.underlineColor))
                    xs.underlineColor = None
                elif xs.textColor != xs.underlineColor:
                    xs.underlines.append((xs.underline_x, cur_x_s, xs.underlineColor))
                    xs.underlineColor = xs.textColor
                    xs.underline_x = cur_x_s

            # Strike
            if not xs.strike and f.strike:
                xs.strike = 1
                xs.strike_x = cur_x_s
                xs.strikeColor = f.textColor
                # XXX Modified for XHTML2PDF
                xs.strikeFontSize = f.fontSize
            elif xs.strike:
                if not f.strike:
                    xs.strike = 0
                    # XXX Modified for XHTML2PDF
                    xs.strikes.append((xs.strike_x, cur_x_s, xs.strikeColor, xs.strikeFontSize))
                    xs.strikeColor = None
                    xs.strikeFontSize = None
                elif xs.textColor != xs.strikeColor:
                    xs.strikes.append((xs.strike_x, cur_x_s, xs.strikeColor, xs.strikeFontSize))
                    xs.strikeColor = xs.textColor
                    xs.strikeFontSize = f.fontSize
                    xs.strike_x = cur_x_s
            if f.link and not xs.link:
                if not xs.link:
                    xs.link = f.link
                    xs.link_x = cur_x_s
                    xs.linkColor = xs.textColor
            elif xs.link:
                if not f.link:
                    xs.links.append((xs.link_x, cur_x_s, xs.link, xs.linkColor))
                    xs.link = None
                    xs.linkColor = None
                elif f.link != xs.link or xs.textColor != xs.linkColor:
                    xs.links.append((xs.link_x, cur_x_s, xs.link, xs.linkColor))
                    xs.link = f.link
                    xs.link_x = cur_x_s
                    xs.linkColor = xs.textColor
            txtlen = tx._canvas.stringWidth(text, tx._fontname, tx._fontsize)
            cur_x += txtlen
            nSpaces += text.count(' ')
    cur_x_s = cur_x + (nSpaces - 1) * ws

    # XXX Modified for XHTML2PDF
    # Underline
    if xs.underline:
        xs.underlines.append((xs.underline_x, cur_x_s, xs.underlineColor))

    # XXX Modified for XHTML2PDF
    # Backcolor
    if hasattr(f, "backColor"):
        if xs.backgroundColor is not None:
            xs.backgrounds.append((xs.background_x, cur_x_s, xs.backgroundColor, xs.backgroundFontSize))

    # XXX Modified for XHTML2PDF
    # Strike
    if xs.strike:
        xs.strikes.append((xs.strike_x, cur_x_s, xs.strikeColor, xs.strikeFontSize))

    if xs.link:
        xs.links.append((xs.link_x, cur_x_s, xs.link, xs.linkColor))
    if tx._x0 != x0:
        setXPos(tx, x0 - tx._x0)


def _leftDrawParaLineX( tx, offset, line, last=0):
    setXPos(tx, offset)
    _putFragLine(offset, tx, line)
    setXPos(tx, -offset)


def _centerDrawParaLineX( tx, offset, line, last=0):
    m = offset + 0.5 * line.extraSpace
    setXPos(tx, m)
    _putFragLine(m, tx, line)
    setXPos(tx, -m)


def _rightDrawParaLineX( tx, offset, line, last=0):
    m = offset + line.extraSpace
    setXPos(tx, m)
    _putFragLine(m, tx, line)
    setXPos(tx, -m)


def _justifyDrawParaLineX( tx, offset, line, last=0):
    setXPos(tx, offset)
    extraSpace = line.extraSpace
    nSpaces = line.wordCount - 1
    if last or not nSpaces or abs(extraSpace) <= 1e-8 or line.lineBreak:
        _putFragLine(offset, tx, line)  # no space modification
    else:
        tx.setWordSpace(extraSpace / float(nSpaces))
        _putFragLine(offset, tx, line)
        tx.setWordSpace(0)
    setXPos(tx, -offset)


def _sameFrag(f, g):
    """
    returns 1 if two ParaFrags map out the same
    """

    if (hasattr(f, 'cbDefn') or hasattr(g, 'cbDefn')
        or hasattr(f, 'lineBreak') or hasattr(g, 'lineBreak')): return 0
    for a in ('fontName', 'fontSize', 'textColor', 'backColor', 'rise', 'underline', 'strike', 'link'):
        if getattr(f, a, None) != getattr(g, a, None): return 0
    return 1


def _getFragWords(frags):
    """
    given a Parafrag list return a list of fragwords
        [[size, (f00,w00), ..., (f0n,w0n)],....,[size, (fm0,wm0), ..., (f0n,wmn)]]
        each pair f,w represents a style and some string
        each sublist represents a word
    """
    R = []
    W = []
    n = 0
    hangingStrip = False
    for f in frags:
        text = f.text
        # of paragraphs
        if text != '':
            if hangingStrip:
                hangingStrip = False
                text = text.lstrip()

            S = split(text)
            if S == []:
                S = ['']
            if W != [] and text[0] in whitespace:
                W.insert(0, n)
                R.append(W)
                W = []
                n = 0

            for w in S[:-1]:
                W.append((f, w))
                n += stringWidth(w, f.fontName, f.fontSize)
                W.insert(0, n)
                R.append(W)
                W = []
                n = 0

            w = S[-1]
            W.append((f, w))
            n += stringWidth(w, f.fontName, f.fontSize)
            if text and text[-1] in whitespace:
                W.insert(0, n)
                R.append(W)
                W = []
                n = 0
        elif hasattr(f, 'cbDefn'):
            w = getattr(f.cbDefn, 'width', 0)
            if w:
                if W != []:
                    W.insert(0, n)
                    R.append(W)
                    W = []
                    n = 0
                R.append([w, (f, '')])
            else:
                W.append((f, ''))
        elif hasattr(f, 'lineBreak'):
            #pass the frag through.  The line breaker will scan for it.
            if W != []:
                W.insert(0, n)
                R.append(W)
                W = []
                n = 0
            R.append([0, (f, '')])
            hangingStrip = True

    if W != []:
        W.insert(0, n)
        R.append(W)

    return R


def _split_blParaSimple(blPara, start, stop):
    f = blPara.clone()
    for a in ('lines', 'kind', 'text'):
        if hasattr(f, a): delattr(f, a)

    f.words = []
    for l in blPara.lines[start:stop]:
        for w in l[1]:
            f.words.append(w)
    return [f]


def _split_blParaHard(blPara, start, stop):
    f = []
    lines = blPara.lines[start:stop]
    for l in lines:
        for w in l.words:
            f.append(w)
        if l is not lines[-1]:
            i = len(f) - 1
            while i >= 0 and hasattr(f[i], 'cbDefn') and not getattr(f[i].cbDefn, 'width', 0): i -= 1
            if i >= 0:
                g = f[i]
                if not g.text:
                    g.text = ' '
                elif g.text[-1] != ' ':
                    g.text += ' '
    return f


def _drawBullet(canvas, offset, cur_y, bulletText, style):
    """
    draw a bullet text could be a simple string or a frag list
    """

    tx2 = canvas.beginText(style.bulletIndent, cur_y + getattr(style, "bulletOffsetY", 0))
    tx2.setFont(style.bulletFontName, style.bulletFontSize)
    tx2.setFillColor(hasattr(style, 'bulletColor') and style.bulletColor or style.textColor)
    if isinstance(bulletText, basestring):
        tx2.textOut(bulletText)
    else:
        for f in bulletText:
            if hasattr(f, "image"):
                image = f.image
                width = image.drawWidth
                height = image.drawHeight
                gap = style.bulletFontSize * 0.25
                img = image.getImage()
                # print style.bulletIndent, offset, width
                canvas.drawImage(
                    img,
                    style.leftIndent - width - gap,
                    cur_y + getattr(style, "bulletOffsetY", 0),
                    width,
                    height)
            else:
                tx2.setFont(f.fontName, f.fontSize)
                tx2.setFillColor(f.textColor)
                tx2.textOut(f.text)
    canvas.drawText(tx2)
    #AR making definition lists a bit less ugly
    #bulletEnd = tx2.getX()
    bulletEnd = tx2.getX() + style.bulletFontSize * 0.6
    offset = max(offset, bulletEnd - style.leftIndent)
    return offset


def _handleBulletWidth(bulletText, style, maxWidths):
    """
    work out bullet width and adjust maxWidths[0] if neccessary
    """
    if bulletText:
        if isinstance(bulletText, basestring):
            bulletWidth = stringWidth(bulletText, style.bulletFontName, style.bulletFontSize)
        else:
            #it's a list of fragments
            bulletWidth = 0
            for f in bulletText:
                bulletWidth = bulletWidth + stringWidth(f.text, f.fontName, f.fontSize)
        bulletRight = style.bulletIndent + bulletWidth + 0.6 * style.bulletFontSize
        indent = style.leftIndent + style.firstLineIndent
        if bulletRight > indent:
            #..then it overruns, and we have less space available on line 1
            maxWidths[0] -= (bulletRight - indent)


def splitLines0(frags, widths):
    """
    given a list of ParaFrags we return a list of ParaLines

    each ParaLine has
    1)  ExtraSpace
    2)  blankCount
    3)  [textDefns....]
        each text definition is a (ParaFrag, start, limit) triplet
    """

    #initialise the algorithm
    lines = []
    lineNum = 0
    maxW = widths[lineNum]
    i = -1
    l = len(frags)
    lim = start = 0
    while 1:
        #find a non whitespace character
        while i < l:
            while start < lim and text[start] == ' ': start += 1
            if start == lim:
                i += 1
                if i == l: break
                start = 0
                f = frags[i]
                text = f.text
                lim = len(text)
            else:
                break   # we found one

        if start == lim: break    # if we didn't find one we are done

        #start of a line
        g = (None, None, None)
        line = []
        cLen = 0
        nSpaces = 0
        while cLen < maxW:
            j = text.find(' ', start)
            if j < 0:
                j == lim
            w = stringWidth(text[start:j], f.fontName, f.fontSize)
            cLen += w
            if cLen > maxW and line != []:
                cLen = cLen - w
                #this is the end of the line
                while g.text[lim] == ' ':
                    lim -= 1
                    nSpaces -= 1
                break
            if j < 0:
                j = lim
            if g[0] is f:
                g[2] = j  #extend
            else:
                g = (f, start, j)
                line.append(g)
            if j == lim:
                i += 1


def _do_under_line(i, t_off, ws, tx, lm=-0.125):
    y = tx.XtraState.cur_y - i * tx.XtraState.style.leading + lm * tx.XtraState.f.fontSize
    textlen = tx._canvas.stringWidth(join(tx.XtraState.lines[i][1]), tx._fontname, tx._fontsize)
    tx._canvas.line(t_off, y, t_off + textlen + ws, y)


_scheme_re = re.compile('^[a-zA-Z][-+a-zA-Z0-9]+$')


def _doLink(tx, link, rect):
    if isinstance(link, unicode):
        link = link.encode('utf8')
    parts = link.split(':', 1)
    scheme = len(parts) == 2 and parts[0].lower() or ''
    if _scheme_re.match(scheme) and scheme != 'document':
        kind = scheme.lower() == 'pdf' and 'GoToR' or 'URI'
        if kind == 'GoToR': link = parts[1]
        tx._canvas.linkURL(link, rect, relative=1, kind=kind)
    else:
        if link[0] == '#':
            link = link[1:]
            scheme = ''
        tx._canvas.linkRect("", scheme != 'document' and link or parts[1], rect, relative=1)


def _do_link_line(i, t_off, ws, tx):
    xs = tx.XtraState
    leading = xs.style.leading
    y = xs.cur_y - i * leading - xs.f.fontSize / 8.0 # 8.0 factor copied from para.py
    text = join(xs.lines[i][1])
    textlen = tx._canvas.stringWidth(text, tx._fontname, tx._fontsize)
    _doLink(tx, xs.link, (t_off, y, t_off + textlen + ws, y + leading))


# XXX Modified for XHTML2PDF
def _do_post_text(tx):
    """
    Try to find out what the variables mean:

    tx         A structure containing more informations about paragraph ???

    leading    Height of lines
    ff         1/8 of the font size
    y0         The "baseline" postion ???
    y          1/8 below the baseline
    """

    xs = tx.XtraState
    leading = xs.style.leading
    autoLeading = xs.autoLeading
    f = xs.f
    if autoLeading == 'max':
        # leading = max(leading, f.fontSize)
        leading = max(leading, LEADING_FACTOR * f.fontSize)
    elif autoLeading == 'min':
        leading = LEADING_FACTOR * f.fontSize
    ff = 0.125 * f.fontSize
    y0 = xs.cur_y
    y = y0 - ff

    # Background
    for x1, x2, c, fs in xs.backgrounds:
        inlineFF = fs * 0.125
        gap = inlineFF * 1.25
        tx._canvas.setFillColor(c)
        tx._canvas.rect(x1, y - gap, x2 - x1, fs + 1, fill=1, stroke=0)
    xs.backgrounds = []
    xs.background = 0
    xs.backgroundColor = None
    xs.backgroundFontSize = None

    # Underline
    yUnderline = y0 - 1.5 * ff
    tx._canvas.setLineWidth(ff * 0.75)
    csc = None
    for x1, x2, c in xs.underlines:
        if c != csc:
            tx._canvas.setStrokeColor(c)
            csc = c
        tx._canvas.line(x1, yUnderline, x2, yUnderline)
    xs.underlines = []
    xs.underline = 0
    xs.underlineColor = None

    # Strike
    for x1, x2, c, fs in xs.strikes:
        inlineFF = fs * 0.125
        ys = y0 + 2 * inlineFF
        if c != csc:
            tx._canvas.setStrokeColor(c)
            csc = c
        tx._canvas.setLineWidth(inlineFF * 0.75)
        tx._canvas.line(x1, ys, x2, ys)
    xs.strikes = []
    xs.strike = 0
    xs.strikeColor = None

    yl = y + leading
    for x1, x2, link, c in xs.links:
        # No automatic underlining for links, never!
        _doLink(tx, link, (x1, y, x2, yl))
    xs.links = []
    xs.link = None
    xs.linkColor = None
    xs.cur_y -= leading


def textTransformFrags(frags, style):
    tt = style.textTransform
    if tt:
        tt = tt.lower()
        if tt == 'lowercase':
            tt = unicode.lower
        elif tt == 'uppercase':
            tt = unicode.upper
        elif tt == 'capitalize':
            tt = unicode.title
        elif tt == 'none':
            return
        else:
            raise ValueError('ParaStyle.textTransform value %r is invalid' % style.textTransform)
        n = len(frags)
        if n == 1:
            #single fragment the easy case
            frags[0].text = tt(frags[0].text.decode('utf8')).encode('utf8')
        elif tt is unicode.title:
            pb = True
            for f in frags:
                t = f.text
                if not t: continue
                u = t.decode('utf8')
                if u.startswith(u' ') or pb:
                    u = tt(u)
                else:
                    i = u.find(u' ')
                    if i >= 0:
                        u = u[:i] + tt(u[i:])
                pb = u.endswith(u' ')
                f.text = u.encode('utf8')
        else:
            for f in frags:
                t = f.text
                if not t: continue
                f.text = tt(t.decode('utf8')).encode('utf8')


class cjkU(unicode):
    """
    simple class to hold the frag corresponding to a str
    """

    def __new__(cls, value, frag, encoding):
        self = unicode.__new__(cls, value)
        self._frag = frag
        if hasattr(frag, 'cbDefn'):
            w = getattr(frag.cbDefn, 'width', 0)
            self._width = w
        else:
            self._width = stringWidth(value, frag.fontName, frag.fontSize)
        return self

    frag = property(lambda self: self._frag)
    width = property(lambda self: self._width)


def makeCJKParaLine(U, extraSpace, calcBounds):
    words = []
    CW = []
    f0 = FragLine()
    maxSize = maxAscent = minDescent = 0
    for u in U:
        f = u.frag
        fontSize = f.fontSize
        if calcBounds:
            cbDefn = getattr(f, 'cbDefn', None)
            if getattr(cbDefn, 'width', 0):
                descent, ascent = imgVRange(cbDefn.height, cbDefn.valign, fontSize)
            else:
                ascent, descent = getAscentDescent(f.fontName, fontSize)
        else:
            ascent, descent = getAscentDescent(f.fontName, fontSize)
        maxSize = max(maxSize, fontSize)
        maxAscent = max(maxAscent, ascent)
        minDescent = min(minDescent, descent)
        if not _sameFrag(f0, f):
            f0 = f0.clone()
            f0.text = u''.join(CW)
            words.append(f0)
            CW = []
            f0 = f
        CW.append(u)
    if CW:
        f0 = f0.clone()
        f0.text = u''.join(CW)
        words.append(f0)
    return FragLine(kind=1, extraSpace=extraSpace, wordCount=1, words=words[1:], fontSize=maxSize, ascent=maxAscent,
                    descent=minDescent)


def cjkFragSplit(frags, maxWidths, calcBounds, encoding='utf8'):
    """
    This attempts to be wordSplit for frags using the dumb algorithm
    """

    from reportlab.rl_config import _FUZZ

    U = []  # get a list of single glyphs with their widths etc etc
    for f in frags:
        text = f.text
        if not isinstance(text, unicode):
            text = text.decode(encoding)
        if text:
            U.extend([cjkU(t, f, encoding) for t in text])
        else:
            U.append(cjkU(text, f, encoding))

    lines = []
    widthUsed = lineStartPos = 0
    maxWidth = maxWidths[0]

    for i, u in enumerate(U):
        w = u.width
        widthUsed += w
        lineBreak = hasattr(u.frag, 'lineBreak')
        endLine = (widthUsed > maxWidth + _FUZZ and widthUsed > 0) or lineBreak
        if endLine:
            if lineBreak: continue
            extraSpace = maxWidth - widthUsed + w
            #This is the most important of the Japanese typography rules.
            #if next character cannot start a line, wrap it up to this line so it hangs
            #in the right margin. We won't do two or more though - that's unlikely and
            #would result in growing ugliness.
            nextChar = U[i]
            if nextChar in ALL_CANNOT_START:
                extraSpace -= w
                i += 1
            lines.append(makeCJKParaLine(U[lineStartPos:i], extraSpace, calcBounds))
            try:
                maxWidth = maxWidths[len(lines)]
            except IndexError:
                maxWidth = maxWidths[-1]  # use the last one

            lineStartPos = i
            widthUsed = w
            i -= 1
        #any characters left?
    if widthUsed > 0:
        lines.append(makeCJKParaLine(U[lineStartPos:], maxWidth - widthUsed, calcBounds))

    return ParaLines(kind=1, lines=lines)


class Paragraph(Flowable):
    """
    Paragraph(text, style, bulletText=None, caseSensitive=1)
        text a string of stuff to go into the paragraph.
        style is a style definition as in reportlab.lib.styles.
        bulletText is an optional bullet defintion.
        caseSensitive set this to 0 if you want the markup tags and their attributes to be case-insensitive.

        This class is a flowable that can format a block of text
        into a paragraph with a given style.

        The paragraph Text can contain XML-like markup including the tags:
        <b> ... </b> - bold
        <i> ... </i> - italics
        <u> ... </u> - underline
        <strike> ... </strike> - strike through
        <super> ... </super> - superscript
        <sub> ... </sub> - subscript
        <font name=fontfamily/fontname color=colorname size=float>
        <onDraw name=callable label="a label">
        <link>link text</link>
            attributes of links
                size/fontSize=num
                name/face/fontName=name
                fg/textColor/color=color
                backcolor/backColor/bgcolor=color
                dest/destination/target/href/link=target
        <a>anchor text</a>
            attributes of anchors
                fontSize=num
                fontName=name
                fg/textColor/color=color
                backcolor/backColor/bgcolor=color
                href=href
        <a name="anchorpoint"/>
        <unichar name="unicode character name"/>
        <unichar value="unicode code point"/>
        <img src="path" width="1in" height="1in" valign="bottom"/>

        The whole may be surrounded by <para> </para> tags

        The <b> and <i> tags will work for the built-in fonts (Helvetica
        /Times / Courier).  For other fonts you need to register a family
        of 4 fonts using reportlab.pdfbase.pdfmetrics.registerFont; then
        use the addMapping function to tell the library that these 4 fonts
        form a family e.g.
            from reportlab.lib.fonts import addMapping
            addMapping('Vera', 0, 0, 'Vera')    #normal
            addMapping('Vera', 0, 1, 'Vera-Italic')    #italic
            addMapping('Vera', 1, 0, 'Vera-Bold')    #bold
            addMapping('Vera', 1, 1, 'Vera-BoldItalic')    #italic and bold

        It will also be able to handle any MathML specified Greek characters.
    """
    def __init__(self, text, style, bulletText=None, frags=None, caseSensitive=1, encoding='utf8'):
        self.caseSensitive = caseSensitive
        self.encoding = encoding
        self._setup(text, style, bulletText, frags, cleanBlockQuotedText)

    def __repr__(self):
        n = self.__class__.__name__
        L = [n + "("]
        keys = self.__dict__.keys()
        for k in keys:
            v = getattr(self, k)
            rk = repr(k)
            rv = repr(v)
            rk = "  " + rk.replace("\n", "\n  ")
            rv = "    " + rk.replace("\n", "\n    ")
            L.append(rk)
            L.append(rv)
        L.append(") #" + n)
        return '\n'.join(L)

    def _setup(self, text, style, bulletText, frags, cleaner):
        if frags is None:
            text = cleaner(text)
            _parser.caseSensitive = self.caseSensitive
            style, frags, bulletTextFrags = _parser.parse(text, style)
            if frags is None:
                raise ValueError("xml parser error (%s) in paragraph beginning\n'%s'" \
                                 % (_parser.errors[0], text[:min(30, len(text))]))
            textTransformFrags(frags, style)
            if bulletTextFrags: bulletText = bulletTextFrags

        #AR hack
        self.text = text
        self.frags = frags
        self.style = style
        self.bulletText = bulletText
        self.debug = PARAGRAPH_DEBUG  # turn this on to see a pretty one with all the margins etc.

    def wrap(self, availWidth, availHeight):

        if self.debug:
            print (id(self), "wrap")
            try:
                print (repr(self.getPlainText()[:80]))
            except:
                print ("???")

        # work out widths array for breaking
        self.width = availWidth
        style = self.style
        leftIndent = style.leftIndent
        first_line_width = availWidth - (leftIndent + style.firstLineIndent) - style.rightIndent
        later_widths = availWidth - leftIndent - style.rightIndent

        if style.wordWrap == 'CJK':
            #use Asian text wrap algorithm to break characters
            blPara = self.breakLinesCJK([first_line_width, later_widths])
        else:
            blPara = self.breakLines([first_line_width, later_widths])
        self.blPara = blPara
        autoLeading = getattr(self, 'autoLeading', getattr(style, 'autoLeading', ''))
        leading = style.leading
        if blPara.kind == 1 and autoLeading not in ('', 'off'):
            height = 0
            if autoLeading == 'max':
                for l in blPara.lines:
                    height += max(l.ascent - l.descent, leading)
            elif autoLeading == 'min':
                for l in blPara.lines:
                    height += l.ascent - l.descent
            else:
                raise ValueError('invalid autoLeading value %r' % autoLeading)
        else:
            if autoLeading == 'max':
                leading = max(leading, LEADING_FACTOR * style.fontSize)
            elif autoLeading == 'min':
                leading = LEADING_FACTOR * style.fontSize
            height = len(blPara.lines) * leading
        self.height = height

        return self.width, height

    def minWidth(self):
        """
        Attempt to determine a minimum sensible width
        """

        frags = self.frags
        nFrags = len(frags)
        if not nFrags: return 0
        if nFrags == 1:
            f = frags[0]
            fS = f.fontSize
            fN = f.fontName
            words = hasattr(f, 'text') and split(f.text, ' ') or f.words
            func = lambda w, fS=fS, fN=fN: stringWidth(w, fN, fS)
        else:
            words = _getFragWords(frags)
            func = lambda x: x[0]
        return max(map(func, words))

    def _get_split_blParaFunc(self):
        return self.blPara.kind == 0 and _split_blParaSimple or _split_blParaHard

    def split(self, availWidth, availHeight):

        if self.debug:
            print  (id(self), "split")

        if len(self.frags) <= 0: return []

        #the split information is all inside self.blPara
        if not hasattr(self, 'blPara'):
            self.wrap(availWidth, availHeight)

        blPara = self.blPara
        style = self.style
        autoLeading = getattr(self, 'autoLeading', getattr(style, 'autoLeading', ''))
        leading = style.leading
        lines = blPara.lines
        if blPara.kind == 1 and autoLeading not in ('', 'off'):
            s = height = 0
            if autoLeading == 'max':
                for i, l in enumerate(blPara.lines):
                    h = max(l.ascent - l.descent, leading)
                    n = height + h
                    if n > availHeight + 1e-8:
                        break
                    height = n
                    s = i + 1
            elif autoLeading == 'min':
                for i, l in enumerate(blPara.lines):
                    n = height + l.ascent - l.descent
                    if n > availHeight + 1e-8:
                        break
                    height = n
                    s = i + 1
            else:
                raise ValueError('invalid autoLeading value %r' % autoLeading)
        else:
            l = leading
            if autoLeading == 'max':
                l = max(leading, LEADING_FACTOR * style.fontSize)
            elif autoLeading == 'min':
                l = LEADING_FACTOR * style.fontSize
            s = int(availHeight / l)
            height = s * l

        n = len(lines)
        allowWidows = getattr(self, 'allowWidows', getattr(self, 'allowWidows', 1))
        allowOrphans = getattr(self, 'allowOrphans', getattr(self, 'allowOrphans', 0))
        if not allowOrphans:
            if s <= 1:    # orphan?
                del self.blPara
                return []
        if n <= s: return [self]
        if not allowWidows:
            if n == s + 1: # widow?
                if (allowOrphans and n == 3) or n > 3:
                    s -= 1  # give the widow some company
                else:
                    del self.blPara # no room for adjustment; force the whole para onwards
                    return []
        func = self._get_split_blParaFunc()

        P1 = self.__class__(None, style, bulletText=self.bulletText, frags=func(blPara, 0, s))
        #this is a major hack
        P1.blPara = ParaLines(kind=1, lines=blPara.lines[0:s], aH=availHeight, aW=availWidth)
        P1._JustifyLast = 1
        P1._splitpara = 1
        P1.height = height
        P1.width = availWidth
        if style.firstLineIndent != 0:
            style = deepcopy(style)
            style.firstLineIndent = 0
        P2 = self.__class__(None, style, bulletText=None, frags=func(blPara, s, n))
        for a in ('autoLeading',    # possible attributes that might be directly on self.
        ):
            if hasattr(self, a):
                setattr(P1, a, getattr(self, a))
                setattr(P2, a, getattr(self, a))
        return [P1, P2]

    def draw(self):
        #call another method for historical reasons.  Besides, I
        #suspect I will be playing with alternate drawing routines
        #so not doing it here makes it easier to switch.
        self.drawPara(self.debug)

    def breakLines(self, width):
        """
        Returns a broken line structure. There are two cases

        A) For the simple case of a single formatting input fragment the output is
            A fragment specifier with
                - kind = 0
                - fontName, fontSize, leading, textColor
                - lines=  A list of lines

                        Each line has two items.

                        1. unused width in points
                        2. word list

        B) When there is more than one input formatting fragment the output is
            A fragment specifier with
               - kind = 1
               - lines=  A list of fragments each having fields
                            - extraspace (needed for justified)
                            - fontSize
                            - words=word list
                                each word is itself a fragment with
                                various settings

        This structure can be used to easily draw paragraphs with the various alignments.
        You can supply either a single width or a list of widths; the latter will have its
        last item repeated until necessary. A 2-element list is useful when there is a
        different first line indent; a longer list could be created to facilitate custom wraps
        around irregular objects.
        """

        if self.debug:
            print (id(self), "breakLines")

        if not isinstance(width, (tuple, list)):
            maxWidths = [width]
        else:
            maxWidths = width
        lines = []
        lineno = 0
        style = self.style

        #for bullets, work out width and ensure we wrap the right amount onto line one
        _handleBulletWidth(self.bulletText, style, maxWidths)

        maxWidth = maxWidths[0]

        self.height = 0
        autoLeading = getattr(self, 'autoLeading', getattr(style, 'autoLeading', ''))
        calcBounds = autoLeading not in ('', 'off')
        frags = self.frags
        nFrags = len(frags)
        if nFrags == 1 and not hasattr(frags[0], 'cbDefn'):
            f = frags[0]
            fontSize = f.fontSize
            fontName = f.fontName
            ascent, descent = getAscentDescent(fontName, fontSize)
            words = hasattr(f, 'text') and split(f.text, ' ') or f.words
            spaceWidth = stringWidth(' ', fontName, fontSize, self.encoding)
            cLine = []
            currentWidth = -spaceWidth   # hack to get around extra space for word 1
            for word in words:
                #this underscores my feeling that Unicode throughout would be easier!
                wordWidth = stringWidth(word, fontName, fontSize, self.encoding)
                newWidth = currentWidth + spaceWidth + wordWidth
                if newWidth <= maxWidth or not len(cLine):
                    # fit one more on this line
                    cLine.append(word)
                    currentWidth = newWidth
                else:
                    if currentWidth > self.width: self.width = currentWidth
                    #end of line
                    lines.append((maxWidth - currentWidth, cLine))
                    cLine = [word]
                    currentWidth = wordWidth
                    lineno += 1
                    try:
                        maxWidth = maxWidths[lineno]
                    except IndexError:
                        maxWidth = maxWidths[-1]  # use the last one

            #deal with any leftovers on the final line
            if cLine != []:
                if currentWidth > self.width: self.width = currentWidth
                lines.append((maxWidth - currentWidth, cLine))

            return f.clone(kind=0, lines=lines, ascent=ascent, descent=descent, fontSize=fontSize)
        elif nFrags <= 0:
            return ParaLines(kind=0, fontSize=style.fontSize, fontName=style.fontName,
                             textColor=style.textColor, ascent=style.fontSize, descent=-0.2 * style.fontSize,
                             lines=[])
        else:
            if hasattr(self, 'blPara') and getattr(self, '_splitpara', 0):
                #NB this is an utter hack that awaits the proper information
                #preserving splitting algorithm
                return self.blPara
            n = 0
            words = []
            for w in _getFragWords(frags):
                f = w[-1][0]
                fontName = f.fontName
                fontSize = f.fontSize
                spaceWidth = stringWidth(' ', fontName, fontSize)

                if not words:
                    currentWidth = -spaceWidth   # hack to get around extra space for word 1
                    maxSize = fontSize
                    maxAscent, minDescent = getAscentDescent(fontName, fontSize)

                wordWidth = w[0]
                f = w[1][0]
                if wordWidth > 0:
                    newWidth = currentWidth + spaceWidth + wordWidth
                else:
                    newWidth = currentWidth

                #test to see if this frag is a line break. If it is we will only act on it
                #if the current width is non-negative or the previous thing was a deliberate lineBreak
                lineBreak = hasattr(f, 'lineBreak')
                endLine = (newWidth > maxWidth and n > 0) or lineBreak
                if not endLine:
                    if lineBreak: continue      #throw it away
                    nText = w[1][1]
                    if nText: n += 1
                    fontSize = f.fontSize
                    if calcBounds:
                        cbDefn = getattr(f, 'cbDefn', None)
                        if getattr(cbDefn, 'width', 0):
                            descent, ascent = imgVRange(cbDefn.height, cbDefn.valign, fontSize)
                        else:
                            ascent, descent = getAscentDescent(f.fontName, fontSize)
                    else:
                        ascent, descent = getAscentDescent(f.fontName, fontSize)
                    maxSize = max(maxSize, fontSize)
                    maxAscent = max(maxAscent, ascent)
                    minDescent = min(minDescent, descent)
                    if not words:
                        g = f.clone()
                        words = [g]
                        g.text = nText
                    elif not _sameFrag(g, f):
                        if currentWidth > 0 and ((nText != '' and nText[0] != ' ') or hasattr(f, 'cbDefn')):
                            if hasattr(g, 'cbDefn'):
                                i = len(words) - 1
                                while i >= 0:
                                    wi = words[i]
                                    cbDefn = getattr(wi, 'cbDefn', None)
                                    if cbDefn:
                                        if not getattr(cbDefn, 'width', 0):
                                            i -= 1
                                            continue
                                    if not wi.text.endswith(' '):
                                        wi.text += ' '
                                    break
                            else:
                                if not g.text.endswith(' '):
                                    g.text += ' '
                        g = f.clone()
                        words.append(g)
                        g.text = nText
                    else:
                        if nText != '' and nText[0] != ' ':
                            g.text += ' ' + nText

                    for i in w[2:]:
                        g = i[0].clone()
                        g.text = i[1]
                        words.append(g)
                        fontSize = g.fontSize
                        if calcBounds:
                            cbDefn = getattr(g, 'cbDefn', None)
                            if getattr(cbDefn, 'width', 0):
                                descent, ascent = imgVRange(cbDefn.height, cbDefn.valign, fontSize)
                            else:
                                ascent, descent = getAscentDescent(g.fontName, fontSize)
                        else:
                            ascent, descent = getAscentDescent(g.fontName, fontSize)
                        maxSize = max(maxSize, fontSize)
                        maxAscent = max(maxAscent, ascent)
                        minDescent = min(minDescent, descent)

                    currentWidth = newWidth
                else:  # either it won't fit, or it's a lineBreak tag
                    if lineBreak:
                        g = f.clone()
                        words.append(g)

                    if currentWidth > self.width: self.width = currentWidth
                    #end of line
                    lines.append(FragLine(extraSpace=maxWidth - currentWidth, wordCount=n,
                                          lineBreak=lineBreak, words=words, fontSize=maxSize, ascent=maxAscent,
                                          descent=minDescent))

                    #start new line
                    lineno += 1
                    try:
                        maxWidth = maxWidths[lineno]
                    except IndexError:
                        maxWidth = maxWidths[-1]  # use the last one

                    if lineBreak:
                        n = 0
                        words = []
                        continue

                    currentWidth = wordWidth
                    n = 1
                    g = f.clone()
                    maxSize = g.fontSize
                    if calcBounds:
                        cbDefn = getattr(g, 'cbDefn', None)
                        if getattr(cbDefn, 'width', 0):
                            minDescent, maxAscent = imgVRange(cbDefn.height, cbDefn.valign, maxSize)
                        else:
                            maxAscent, minDescent = getAscentDescent(g.fontName, maxSize)
                    else:
                        maxAscent, minDescent = getAscentDescent(g.fontName, maxSize)
                    words = [g]
                    g.text = w[1][1]

                    for i in w[2:]:
                        g = i[0].clone()
                        g.text = i[1]
                        words.append(g)
                        fontSize = g.fontSize
                        if calcBounds:
                            cbDefn = getattr(g, 'cbDefn', None)
                            if getattr(cbDefn, 'width', 0):
                                descent, ascent = imgVRange(cbDefn.height, cbDefn.valign, fontSize)
                            else:
                                ascent, descent = getAscentDescent(g.fontName, fontSize)
                        else:
                            ascent, descent = getAscentDescent(g.fontName, fontSize)
                        maxSize = max(maxSize, fontSize)
                        maxAscent = max(maxAscent, ascent)
                        minDescent = min(minDescent, descent)

            #deal with any leftovers on the final line
            if words != []:
                if currentWidth > self.width: self.width = currentWidth
                lines.append(ParaLines(extraSpace=(maxWidth - currentWidth), wordCount=n,
                                       words=words, fontSize=maxSize, ascent=maxAscent, descent=minDescent))
            return ParaLines(kind=1, lines=lines)

        return lines

    def breakLinesCJK(self, width):
        """Initially, the dumbest possible wrapping algorithm.
        Cannot handle font variations."""

        if self.debug:
            print (id(self), "breakLinesCJK")

        if not isinstance(width, (list, tuple)):
            maxWidths = [width]
        else:
            maxWidths = width
        style = self.style

        #for bullets, work out width and ensure we wrap the right amount onto line one
        _handleBulletWidth(self.bulletText, style, maxWidths)
        if len(self.frags) > 1:
            autoLeading = getattr(self, 'autoLeading', getattr(style, 'autoLeading', ''))
            calcBounds = autoLeading not in ('', 'off')
            return cjkFragSplit(self.frags, maxWidths, calcBounds, self.encoding)

        elif not len(self.frags):
            return ParaLines(kind=0, fontSize=style.fontSize, fontName=style.fontName,
                             textColor=style.textColor, lines=[], ascent=style.fontSize, descent=-0.2 * style.fontSize)
        f = self.frags[0]
        if 1 and hasattr(self, 'blPara') and getattr(self, '_splitpara', 0):
            #NB this is an utter hack that awaits the proper information
            #preserving splitting algorithm
            return f.clone(kind=0, lines=self.blPara.lines)
        lines = []
        lineno = 0

        self.height = 0

        f = self.frags[0]

        if hasattr(f, 'text'):
            text = f.text
        else:
            text = ''.join(getattr(f, 'words', []))

        from reportlab.lib.textsplit import wordSplit

        lines = wordSplit(text, maxWidths[0], f.fontName, f.fontSize)
        #the paragraph drawing routine assumes multiple frags per line, so we need an
        #extra list like this
        #  [space, [text]]
        #
        wrappedLines = [(sp, [line]) for (sp, line) in lines]
        return f.clone(kind=0, lines=wrappedLines, ascent=f.fontSize, descent=-0.2 * f.fontSize)

    def beginText(self, x, y):
        return self.canv.beginText(x, y)

    def drawPara(self, debug=0):
        """Draws a paragraph according to the given style.
        Returns the final y position at the bottom. Not safe for
        paragraphs without spaces e.g. Japanese; wrapping
        algorithm will go infinite."""

        if self.debug:
            print (id(self), "drawPara", self.blPara.kind)

        #stash the key facts locally for speed
        canvas = self.canv
        style = self.style
        blPara = self.blPara
        lines = blPara.lines
        leading = style.leading
        autoLeading = getattr(self, 'autoLeading', getattr(style, 'autoLeading', ''))

        #work out the origin for line 1
        leftIndent = style.leftIndent
        cur_x = leftIndent

        if debug:
            bw = 0.5
            bc = Color(1, 1, 0)
            bg = Color(0.9, 0.9, 0.9)
        else:
            bw = getattr(style, 'borderWidth', None)
            bc = getattr(style, 'borderColor', None)
            bg = style.backColor

        #if has a background or border, draw it
        if bg or (bc and bw):
            canvas.saveState()
            op = canvas.rect
            kwds = dict(fill=0, stroke=0)
            if bc and bw:
                canvas.setStrokeColor(bc)
                canvas.setLineWidth(bw)
                kwds['stroke'] = 1
                br = getattr(style, 'borderRadius', 0)
                if br and not debug:
                    op = canvas.roundRect
                    kwds['radius'] = br
            if bg:
                canvas.setFillColor(bg)
                kwds['fill'] = 1
            bp = getattr(style, 'borderPadding', 0)
            op(leftIndent - bp,
               -bp,
               self.width - (leftIndent + style.rightIndent) + 2 * bp,
               self.height + 2 * bp,
               **kwds)
            canvas.restoreState()

        nLines = len(lines)
        bulletText = self.bulletText
        if nLines > 0:
            _offsets = getattr(self, '_offsets', [0])
            _offsets += (nLines - len(_offsets)) * [_offsets[-1]]
            canvas.saveState()
            alignment = style.alignment
            offset = style.firstLineIndent + _offsets[0]
            lim = nLines - 1
            noJustifyLast = not (hasattr(self, '_JustifyLast') and self._JustifyLast)

            if blPara.kind == 0:
                if alignment == TA_LEFT:
                    dpl = _leftDrawParaLine
                elif alignment == TA_CENTER:
                    dpl = _centerDrawParaLine
                elif self.style.alignment == TA_RIGHT:
                    dpl = _rightDrawParaLine
                elif self.style.alignment == TA_JUSTIFY:
                    dpl = _justifyDrawParaLine
                f = blPara
                cur_y = self.height - getattr(f, 'ascent', f.fontSize)    # TODO fix XPreformatted to remove this hack
                if bulletText:
                    offset = _drawBullet(canvas, offset, cur_y, bulletText, style)

                #set up the font etc.
                canvas.setFillColor(f.textColor)

                tx = self.beginText(cur_x, cur_y)
                if autoLeading == 'max':
                    leading = max(leading, LEADING_FACTOR * f.fontSize)
                elif autoLeading == 'min':
                    leading = LEADING_FACTOR * f.fontSize

                #now the font for the rest of the paragraph
                tx.setFont(f.fontName, f.fontSize, leading)
                ws = getattr(tx, '_wordSpace', 0)  
                t_off = dpl(tx, offset, ws, lines[0][1], noJustifyLast and nLines == 1)
                if f.underline or f.link or f.strike:
                    xs = tx.XtraState = ABag()
                    xs.cur_y = cur_y
                    xs.f = f
                    xs.style = style
                    xs.lines = lines
                    xs.underlines = []
                    xs.underlineColor = None
                    # XXX Modified for XHTML2PDF
                    xs.backgrounds = []
                    xs.backgroundColor = None
                    xs.backgroundFontSize = None
                    xs.strikes = []
                    xs.strikeColor = None
                    # XXX Modified for XHTML2PDF
                    xs.strikeFontSize = None
                    xs.links = []
                    xs.link = f.link
                    canvas.setStrokeColor(f.textColor)
                    dx = t_off + leftIndent
                    if dpl != _justifyDrawParaLine: ws = 0
                    # XXX Never underline!
                    underline = f.underline
                    strike = f.strike
                    link = f.link
                    if underline:
                        _do_under_line(0, dx, ws, tx)
                    if strike:
                        _do_under_line(0, dx, ws, tx, lm=0.125)
                    if link: _do_link_line(0, dx, ws, tx)

                    #now the middle of the paragraph, aligned with the left margin which is our origin.
                    for i in xrange(1, nLines):
                        ws = lines[i][0]
                        t_off = dpl(tx, _offsets[i], ws, lines[i][1], noJustifyLast and i == lim)
                        if dpl != _justifyDrawParaLine: ws = 0
                        if underline: _do_under_line(i, t_off + leftIndent, ws, tx)
                        if strike: _do_under_line(i, t_off + leftIndent, ws, tx, lm=0.125)
                        if link: _do_link_line(i, t_off + leftIndent, ws, tx)
                else:
                    for i in xrange(1, nLines):
                        dpl(tx, _offsets[i], lines[i][0], lines[i][1], noJustifyLast and i == lim)
            else:
                f = lines[0]
                cur_y = self.height - getattr(f, 'ascent', f.fontSize)    # TODO fix XPreformatted to remove this hack
                # default?
                dpl = _leftDrawParaLineX
                if bulletText:
                    oo = offset
                    offset = _drawBullet(canvas, offset, cur_y, bulletText, style)
                if alignment == TA_LEFT:
                    dpl = _leftDrawParaLineX
                elif alignment == TA_CENTER:
                    dpl = _centerDrawParaLineX
                elif self.style.alignment == TA_RIGHT:
                    dpl = _rightDrawParaLineX
                elif self.style.alignment == TA_JUSTIFY:
                    dpl = _justifyDrawParaLineX
                else:
                    raise ValueError("bad align %s" % repr(alignment))

                #set up the font etc.
                tx = self.beginText(cur_x, cur_y)
                xs = tx.XtraState = ABag()
                xs.textColor = None
                # XXX Modified for XHTML2PDF
                xs.backColor = None
                xs.rise = 0
                xs.underline = 0
                xs.underlines = []
                xs.underlineColor = None
                # XXX Modified for XHTML2PDF
                xs.background = 0
                xs.backgrounds = []
                xs.backgroundColor = None
                xs.backgroundFontSize = None
                xs.strike = 0
                xs.strikes = []
                xs.strikeColor = None
                # XXX Modified for XHTML2PDF
                xs.strikeFontSize = None
                xs.links = []
                xs.link = None
                xs.leading = style.leading
                xs.leftIndent = leftIndent
                tx._leading = None
                tx._olb = None
                xs.cur_y = cur_y
                xs.f = f
                xs.style = style
                xs.autoLeading = autoLeading

                tx._fontname, tx._fontsize = None, None
                dpl(tx, offset, lines[0], noJustifyLast and nLines == 1)
                _do_post_text(tx)

                #now the middle of the paragraph, aligned with the left margin which is our origin.
                for i in xrange(1, nLines):
                    f = lines[i]
                    dpl(tx, _offsets[i], f, noJustifyLast and i == lim)
                    _do_post_text(tx)

            canvas.drawText(tx)
            canvas.restoreState()

    def getPlainText(self, identify=None):
        """
        Convenience function for templates which want access
        to the raw text, without XML tags.
        """

        frags = getattr(self, 'frags', None)
        if frags:
            plains = []
            for frag in frags:
                if hasattr(frag, 'text'):
                    plains.append(frag.text)
            return join(plains, '')
        elif identify:
            text = getattr(self, 'text', None)
            if text is None: text = repr(self)
            return text
        else:
            return ''

    def getActualLineWidths0(self):
        """
        Convenience function; tells you how wide each line
        actually is.  For justified styles, this will be
        the same as the wrap width; for others it might be
        useful for seeing if paragraphs will fit in spaces.
        """

        assert hasattr(self, 'width'), "Cannot call this method before wrap()"
        if self.blPara.kind:
            func = lambda frag, w=self.width: w - frag.extraSpace
        else:
            func = lambda frag, w=self.width: w - frag[0]
        return map(func, self.blPara.lines)


if __name__ == '__main__':    # NORUNTESTS
    def dumpParagraphLines(P):
        print ('dumpParagraphLines(<Paragraph @ %d>)') % id(P)
        lines = P.blPara.lines
        for l, line in enumerate(lines):
            line = lines[l]
            if hasattr(line, 'words'):
                words = line.words
            else:
                words = line[1]
            nwords = len(words)
            print ('line%d: %d(%s)\n  ') % (l, nwords, str(getattr(line, 'wordCount', 'Unknown'))),
            for w in xrange(nwords):
                print ("%d:'%s'") % (w, getattr(words[w], 'text', words[w])),
            print()

    def fragDump(w):
        R = ["'%s'" % w[1]]
        for a in ('fontName', 'fontSize', 'textColor', 'rise', 'underline', 'strike', 'link', 'cbDefn', 'lineBreak'):
            if hasattr(w[0], a):
                R.append('%s=%r' % (a, getattr(w[0], a)))
        return ', '.join(R)

    def dumpParagraphFrags(P):
        print ('dumpParagraphFrags(<Paragraph @ %d>) minWidth() = %.2f') % (id(P), P.minWidth())
        frags = P.frags
        n = len(frags)
        for l in xrange(n):
            print ("frag%d: '%s' %s") % (
            l, frags[l].text, ' '.join(['%s=%s' % (k, getattr(frags[l], k)) for k in frags[l].__dict__ if k != text]))

        l = 0
        cum = 0
        for W in _getFragWords(frags):
            cum += W[0]
            print ("fragword%d: cum=%3d size=%d") % (l, cum, W[0]),
            for w in W[1:]:
                print ('(%s)') % fragDump(w),
            print()
            l += 1

    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    import sys

    TESTS = sys.argv[1:]
    if TESTS == []:
        TESTS = ['4']

    def flagged(i, TESTS=TESTS):
        return 'all' in TESTS or '*' in TESTS or str(i) in TESTS

    styleSheet = getSampleStyleSheet()
    B = styleSheet['BodyText']
    style = ParagraphStyle("discussiontext", parent=B)
    style.fontName = 'Helvetica'
    if flagged(1):
        text = '''The <font name=courier color=green>CMYK</font> or subtractive method follows the way a printer
mixes three pigments (cyan, magenta, and yellow) to form colors.
Because mixing chemicals is more difficult than combining light there
is a fourth parameter for darkness.  For example a chemical
combination of the <font name=courier color=green>CMY</font> pigments generally never makes a perfect
black -- instead producing a muddy color -- so, to get black printers
don't use the <font name=courier color=green>CMY</font> pigments but use a direct black ink.  Because
<font name=courier color=green>CMYK</font> maps more directly to the way printer hardware works it may
be the case that &amp;| &amp; | colors specified in <font name=courier color=green>CMYK</font> will provide better fidelity
and better control when printed.
'''
        P = Paragraph(text, style)
        dumpParagraphFrags(P)
        aW, aH = 456.0, 42.8
        w, h = P.wrap(aW, aH)
        dumpParagraphLines(P)
        S = P.split(aW, aH)
        for s in S:
            s.wrap(aW, aH)
            dumpParagraphLines(s)
            aH = 500

    if flagged(2):
        P = Paragraph("""Price<super><font color="red">*</font></super>""", styleSheet['Normal'])
        dumpParagraphFrags(P)
        w, h = P.wrap(24, 200)
        dumpParagraphLines(P)

    if flagged(3):
        text = """Dieses Kapitel bietet eine schnelle <b><font color=red>Programme :: starten</font></b>
<onDraw name=myIndex label="Programme :: starten">
<b><font color=red>Eingabeaufforderung :: (&gt;&gt;&gt;)</font></b>
<onDraw name=myIndex label="Eingabeaufforderung :: (&gt;&gt;&gt;)">
<b><font color=red>&gt;&gt;&gt; (Eingabeaufforderung)</font></b>
<onDraw name=myIndex label="&gt;&gt;&gt; (Eingabeaufforderung)">
Einf&#xfc;hrung in Python <b><font color=red>Python :: Einf&#xfc;hrung</font></b>
<onDraw name=myIndex label="Python :: Einf&#xfc;hrung">.
Das Ziel ist, die grundlegenden Eigenschaften von Python darzustellen, ohne
sich zu sehr in speziellen Regeln oder Details zu verstricken. Dazu behandelt
dieses Kapitel kurz die wesentlichen Konzepte wie Variablen, Ausdr&#xfc;cke,
Kontrollfluss, Funktionen sowie Ein- und Ausgabe. Es erhebt nicht den Anspruch,
umfassend zu sein."""
        P = Paragraph(text, styleSheet['Code'])
        dumpParagraphFrags(P)
        w, h = P.wrap(6 * 72, 9.7 * 72)
        dumpParagraphLines(P)

    if flagged(4):
        text = '''Die eingebaute Funktion <font name=Courier>range(i, j [, stride])</font><onDraw name=myIndex label="eingebaute Funktionen::range()"><onDraw name=myIndex label="range() (Funktion)"><onDraw name=myIndex label="Funktionen::range()"> erzeugt eine Liste von Ganzzahlen und f&#xfc;llt sie mit Werten <font name=Courier>k</font>, f&#xfc;r die gilt: <font name=Courier>i &lt;= k &lt; j</font>. Man kann auch eine optionale Schrittweite angeben. Die eingebaute Funktion <font name=Courier>xrange()</font><onDraw name=myIndex label="eingebaute Funktionen::xrange()"><onDraw name=myIndex label="xrange() (Funktion)"><onDraw name=myIndex label="Funktionen::xrange()"> erf&#xfc;llt einen &#xe4;hnlichen Zweck, gibt aber eine unver&#xe4;nderliche Sequenz vom Typ <font name=Courier>XRangeType</font><onDraw name=myIndex label="XRangeType"> zur&#xfc;ck. Anstatt alle Werte in der Liste abzuspeichern, berechnet diese Liste ihre Werte, wann immer sie angefordert werden. Das ist sehr viel speicherschonender, wenn mit sehr langen Listen von Ganzzahlen gearbeitet wird. <font name=Courier>XRangeType</font> kennt eine einzige Methode, <font name=Courier>s.tolist()</font><onDraw name=myIndex label="XRangeType::tolist() (Methode)"><onDraw name=myIndex label="s.tolist() (Methode)"><onDraw name=myIndex label="Methoden::s.tolist()">, die seine Werte in eine Liste umwandelt.'''
        aW = 420
        aH = 64.4
        P = Paragraph(text, B)
        dumpParagraphFrags(P)
        w, h = P.wrap(aW, aH)
        print ('After initial wrap', w, h)
        dumpParagraphLines(P)
        S = P.split(aW, aH)
        dumpParagraphFrags(S[0])
        w0, h0 = S[0].wrap(aW, aH)
        print ('After split wrap', w0, h0)
        dumpParagraphLines(S[0])

    if flagged(5):
        text = '<para> %s <![CDATA[</font></b>& %s < >]]></para>' % (chr(163), chr(163))
        P = Paragraph(text, styleSheet['Code'])
        dumpParagraphFrags(P)
        w, h = P.wrap(6 * 72, 9.7 * 72)
        dumpParagraphLines(P)

    if flagged(6):
        for text in [
            '''Here comes <FONT FACE="Helvetica" SIZE="14pt">Helvetica 14</FONT> with <STRONG>strong</STRONG> <EM>emphasis</EM>.''',
            '''Here comes <font face="Helvetica" size="14pt">Helvetica 14</font> with <Strong>strong</Strong> <em>emphasis</em>.''',
            '''Here comes <font face="Courier" size="3cm">Courier 3cm</font> and normal again.''',
        ]:
            P = Paragraph(text, styleSheet['Normal'], caseSensitive=0)
            dumpParagraphFrags(P)
            w, h = P.wrap(6 * 72, 9.7 * 72)
            dumpParagraphLines(P)

    if flagged(7):
        text = """<para align="CENTER" fontSize="24" leading="30"><b>Generated by:</b>Dilbert</para>"""
        P = Paragraph(text, styleSheet['Code'])
        dumpParagraphFrags(P)
        w, h = P.wrap(6 * 72, 9.7 * 72)
        dumpParagraphLines(P)

    if flagged(8):
        text = """- bullet 0<br/>- bullet 1<br/>- bullet 2<br/>- bullet 3<br/>- bullet 4<br/>- bullet 5"""
        P = Paragraph(text, styleSheet['Normal'])
        dumpParagraphFrags(P)
        w, h = P.wrap(6 * 72, 9.7 * 72)
        dumpParagraphLines(P)
        S = P.split(6 * 72, h / 2.0)
        print (len(S))
        dumpParagraphLines(S[0])
        dumpParagraphLines(S[1])

    if flagged(9):
        text = """Furthermore, the fundamental error of
regarding <img src="../docs/images/testimg.gif" width="3" height="7"/> functional notions as
categorial delimits a general
convention regarding the forms of the<br/>
grammar. I suggested that these results
would follow from the assumption that"""
        P = Paragraph(text, ParagraphStyle('aaa', parent=styleSheet['Normal'], align=TA_JUSTIFY))
        dumpParagraphFrags(P)
        w, h = P.wrap(6 * cm - 12, 9.7 * 72)
        dumpParagraphLines(P)

    if flagged(10):
        text = """a b c\xc2\xa0d e f"""
        P = Paragraph(text, ParagraphStyle('aaa', parent=styleSheet['Normal'], align=TA_JUSTIFY))
        dumpParagraphFrags(P)
        w, h = P.wrap(6 * cm - 12, 9.7 * 72)
        dumpParagraphLines(P)

########NEW FILE########
__FILENAME__ = tables
# -*- coding: utf-8 -*-
from reportlab.platypus.tables import TableStyle
from xhtml2pdf.util import getSize, getBorderStyle, getAlign
from xhtml2pdf.tags import pisaTag
from xhtml2pdf.xhtml2pdf_reportlab import PmlTable, PmlKeepInFrame
import copy
import logging

# Copyright 2010 Dirk Holtwick, holtwick.it
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

log = logging.getLogger("xhtml2pdf")


def _width(value=None):
    if value is None:
        return None
    value = str(value)
    if value.endswith("%"):
        return value
    return getSize(value)


def _height(value=None):
    if value is None:
        return None
    value = str(value)
    if value.endswith("%"):
        return value
    return getSize(value)


class TableData:
    def __init__(self):
        self.data = []
        self.styles = []
        self.span = []
        self.mode = ""
        self.padding = 0
        self.col = 0

    def add_cell(self, data=None):
        self.col += 1
        self.data[len(self.data) - 1].append(data)

    def add_style(self, data):
        self.styles.append(copy.copy(data))

    def add_empty(self, x, y):
        self.span.append((x, y))

    def get_data(self):
        data = self.data
        for x, y in self.span:
            try:
                data[y].insert(x, '')
            except:
                pass
        return data

    def add_cell_styles(self, c, begin, end, mode="td"):
        def getColor(a, b):
            return a

        self.mode = mode.upper()
        if c.frag.backColor and mode != "tr": # XXX Stimmt das so?
            self.add_style(('BACKGROUND', begin, end, c.frag.backColor))

        if 0:
            log.debug("%r", (
                begin,
                end,
                c.frag.borderTopWidth,
                c.frag.borderTopStyle,
                c.frag.borderTopColor,
                c.frag.borderBottomWidth,
                c.frag.borderBottomStyle,
                c.frag.borderBottomColor,
                c.frag.borderLeftWidth,
                c.frag.borderLeftStyle,
                c.frag.borderLeftColor,
                c.frag.borderRightWidth,
                c.frag.borderRightStyle,
                c.frag.borderRightColor,
            ))
        if getBorderStyle(c.frag.borderTopStyle) and c.frag.borderTopWidth and c.frag.borderTopColor is not None:
            self.add_style(('LINEABOVE', begin, (end[0], begin[1]),
                            c.frag.borderTopWidth,
                            c.frag.borderTopColor,
                            "squared"))
        if getBorderStyle(c.frag.borderLeftStyle) and c.frag.borderLeftWidth and c.frag.borderLeftColor is not None:
            self.add_style(('LINEBEFORE', begin, (begin[0], end[1]),
                            c.frag.borderLeftWidth,
                            c.frag.borderLeftColor,
                            "squared"))
        if getBorderStyle(c.frag.borderRightStyle) and c.frag.borderRightWidth and c.frag.borderRightColor is not None:
            self.add_style(('LINEAFTER', (end[0], begin[1]), end,
                            c.frag.borderRightWidth,
                            c.frag.borderRightColor,
                            "squared"))
        if getBorderStyle(
                c.frag.borderBottomStyle) and c.frag.borderBottomWidth and c.frag.borderBottomColor is not None:
            self.add_style(('LINEBELOW', (begin[0], end[1]), end,
                            c.frag.borderBottomWidth,
                            c.frag.borderBottomColor,
                            "squared"))
        self.add_style(('LEFTPADDING', begin, end, c.frag.paddingLeft or self.padding))
        self.add_style(('RIGHTPADDING', begin, end, c.frag.paddingRight or self.padding))
        self.add_style(('TOPPADDING', begin, end, c.frag.paddingTop or self.padding))
        self.add_style(('BOTTOMPADDING', begin, end, c.frag.paddingBottom or self.padding))


class pisaTagTABLE(pisaTag):
    def start(self, c):
        c.addPara()

        attrs = self.attr

        # Swap table data
        c.tableData, self.tableData = TableData(), c.tableData
        tdata = c.tableData

        if attrs.border and attrs.bordercolor:
            frag = c.frag
            frag.borderLeftWidth = attrs.border
            frag.borderLeftColor = attrs.bordercolor
            frag.borderLeftStyle = "solid"
            frag.borderRightWidth = attrs.border
            frag.borderRightColor = attrs.bordercolor
            frag.borderRightStyle = "solid"
            frag.borderTopWidth = attrs.border
            frag.borderTopColor = attrs.bordercolor
            frag.borderTopStyle = "solid"
            frag.borderBottomWidth = attrs.border
            frag.borderBottomColor = attrs.bordercolor
            frag.borderBottomStyle = "solid"

        tdata.padding = attrs.cellpadding
        tdata.add_cell_styles(c, (0, 0), (-1, - 1), "table")
        tdata.align = attrs.align.upper()
        tdata.col = 0
        tdata.row = 0
        tdata.colw = []
        tdata.rowh = []
        tdata.repeat = attrs.repeat
        tdata.width = _width(attrs.width)

    def end(self, c):
        tdata = c.tableData
        data = tdata.get_data()

        # Add missing columns so that each row has the same count of columns
        # This prevents errors in Reportlab table

        try:
            maxcols = max([len(row) for row in data] or [0])
        except ValueError:
            log.warn(c.warning("<table> rows seem to be inconsistent"))
            maxcols = [0]

        for i, row in enumerate(data):
            data[i] += [''] * (maxcols - len(row))

        cols_with_no_width = len(filter(lambda col: col is None, tdata.colw))
        if cols_with_no_width:  # any col width not defined
            bad_cols = filter(lambda tup: tup[1] is None, enumerate(tdata.colw))
            fair_division = str(100 / float(cols_with_no_width)) + '%' # get fair %
            for i, _ in bad_cols:
                tdata.colw[i] = fair_division   # fix empty with fair %

        try:
            if tdata.data:
                # log.debug("Table styles %r", tdata.styles)
                t = PmlTable(
                    data,
                    colWidths=tdata.colw,
                    rowHeights=tdata.rowh,
                    # totalWidth = tdata.width,
                    splitByRow=1,
                    # repeatCols = 1,
                    repeatRows=tdata.repeat,
                    hAlign=tdata.align,
                    vAlign='TOP',
                    style=TableStyle(tdata.styles))
                t.totalWidth = _width(tdata.width)
                t.spaceBefore = c.frag.spaceBefore
                t.spaceAfter = c.frag.spaceAfter

                # XXX Maybe we need to copy some more properties?
                t.keepWithNext = c.frag.keepWithNext
                # t.hAlign = tdata.align
                c.addStory(t)
            else:
                log.warn(c.warning("<table> is empty"))
        except:
            log.warn(c.warning("<table>"), exc_info=1)

        # Cleanup and re-swap table data
        c.clearFrag()
        c.tableData, self.tableData = self.tableData, None


class pisaTagTR(pisaTag):
    def start(self, c):
        tdata = c.tableData
        row = tdata.row
        begin = (0, row)
        end = (-1, row)

        tdata.add_cell_styles(c, begin, end, "tr")
        c.frag.vAlign = self.attr.valign or c.frag.vAlign

        tdata.col = 0
        tdata.data.append([])

    def end(self, c):
        c.tableData.row += 1


class pisaTagTD(pisaTag):
    def start(self, c):

        if self.attr.align is not None:
            c.frag.alignment = getAlign(self.attr.align)

        c.clearFrag()
        self.story = c.swapStory()

        attrs = self.attr

        tdata = c.tableData

        cspan = attrs.colspan
        rspan = attrs.rowspan

        row = tdata.row
        col = tdata.col
        while 1:
            for x, y in tdata.span:
                if x == col and y == row:
                    col += 1
                    tdata.col += 1
            break

        begin = (col, row)
        end = (col, row)
        if cspan:
            end = (end[0] + cspan - 1, end[1])
        if rspan:
            end = (end[0], end[1] + rspan - 1)
        if begin != end:
            #~ print begin, end
            tdata.add_style(('SPAN', begin, end))
            for x in xrange(begin[0], end[0] + 1):
                for y in xrange(begin[1], end[1] + 1):
                    if x != begin[0] or y != begin[1]:
                        tdata.add_empty(x, y)

        # Set Border and padding styles
        tdata.add_cell_styles(c, begin, end, "td")

        # Calculate widths
        # Add empty placeholders for new columns
        if (col + 1) > len(tdata.colw):
            tdata.colw = tdata.colw + ((col + 1 - len(tdata.colw)) * [_width()])
            # Get value of with, if no spanning
        if not cspan:
            width = c.frag.width or self.attr.width
            # If is value, the set it in the right place in the arry
            if width is not None:
                tdata.colw[col] = _width(width)

        # Calculate heights
        if row + 1 > len(tdata.rowh):
            tdata.rowh = tdata.rowh + ((row + 1 - len(tdata.rowh)) * [_width()])
        if not rspan:
            height = None
            if height is not None:
                tdata.rowh[row] = _height(height)
                tdata.add_style(('FONTSIZE', begin, end, 1.0))
                tdata.add_style(('LEADING', begin, end, 1.0))

        # Vertical align
        valign = self.attr.valign or c.frag.vAlign
        if valign is not None:
            tdata.add_style(('VALIGN', begin, end, valign.upper()))

        # Reset border, otherwise the paragraph block will have borders too
        frag = c.frag
        frag.borderLeftWidth = 0
        frag.borderLeftColor = None
        frag.borderLeftStyle = None
        frag.borderRightWidth = 0
        frag.borderRightColor = None
        frag.borderRightStyle = None
        frag.borderTopWidth = 0
        frag.borderTopColor = None
        frag.borderTopStyle = None
        frag.borderBottomWidth = 0
        frag.borderBottomColor = None
        frag.borderBottomStyle = None

    def end(self, c):
        tdata = c.tableData

        c.addPara()
        cell = c.story

        # Keep in frame if needed since Reportlab does no split inside of cells
        if not c.frag.insideStaticFrame:
            # tdata.keepinframe["content"] = cell
            cell = PmlKeepInFrame(
                maxWidth=0,
                maxHeight=0,
                mode='shrink',
                content=cell)

        c.swapStory(self.story)

        tdata.add_cell(cell)


class pisaTagTH(pisaTagTD):
    pass

########NEW FILE########
__FILENAME__ = tags
# -*- coding: utf-8 -*-
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm
from reportlab.platypus.doctemplate import NextPageTemplate, FrameBreak
from reportlab.platypus.flowables import Spacer, HRFlowable, PageBreak, Flowable
from reportlab.platypus.frames import Frame
from reportlab.platypus.paraparser import tt2ps, ABag
from xhtml2pdf import xhtml2pdf_reportlab
from xhtml2pdf.util import getColor, getSize, getAlign, dpi96
from xhtml2pdf.xhtml2pdf_reportlab import PmlImage, PmlPageTemplate
import copy
import logging
import re
import warnings
import string

# Copyright 2010 Dirk Holtwick, holtwick.it
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

log = logging.getLogger("xhtml2pdf")


def deprecation(message):
    warnings.warn("<" + message + "> is deprecated!", DeprecationWarning, stacklevel=2)


class pisaTag:
    """
    The default class for a tag definition
    """

    def __init__(self, node, attr):
        self.node = node
        self.tag = node.tagName
        self.attr = attr

    def start(self, c):
        pass

    def end(self, c):
        pass


class pisaTagBODY(pisaTag):
    """
    We can also asume that there is a BODY tag because html5lib
    adds it for us. Here we take the base font size for later calculations
    in the FONT tag.
    """

    def start(self, c):
        c.baseFontSize = c.frag.fontSize
        # print "base font size", c.baseFontSize


class pisaTagTITLE(pisaTag):
    def end(self, c):
        c.meta["title"] = c.text
        c.clearFrag()


class pisaTagSTYLE(pisaTag):
    def start(self, c):
        c.addPara()


    def end(self, c):
        c.clearFrag()


class pisaTagMETA(pisaTag):
    def start(self, c):
        name = self.attr.name.lower()
        if name in ("author", "subject", "keywords"):
            c.meta[name] = self.attr.content


class pisaTagSUP(pisaTag):
    def start(self, c):
        c.frag.super = 1


class pisaTagSUB(pisaTag):
    def start(self, c):
        c.frag.sub = 1


class pisaTagA(pisaTag):
    rxLink = re.compile("^(#|[a-z]+\:).*")


    def start(self, c):
        attr = self.attr
        # XXX Also support attr.id ?
        if attr.name:
            # Important! Make sure that cbDefn is not inherited by other
            # fragments because of a bug in Reportlab!
            afrag = c.frag.clone()
            # These 3 lines are needed to fix an error with non internal fonts
            afrag.fontName = "Helvetica"
            afrag.bold = 0
            afrag.italic = 0
            afrag.cbDefn = ABag(
                kind="anchor",
                name=attr.name,
                label="anchor")
            c.fragAnchor.append(afrag)
            c.anchorName.append(attr.name)
        if attr.href and self.rxLink.match(attr.href):
            c.frag.link = attr.href

    def end(self, c):
        pass


class pisaTagFONT(pisaTag):
    # Source: http://www.w3.org/TR/CSS21/fonts.html#propdef-font-size

    def start(self, c):
        if self.attr["color"] is not None:
            c.frag.textColor = getColor(self.attr["color"])
        if self.attr["face"] is not None:
            c.frag.fontName = c.getFontName(self.attr["face"])
        if self.attr["size"] is not None:
            size = getSize(self.attr["size"], c.frag.fontSize, c.baseFontSize)
            c.frag.fontSize = max(size, 1.0)

    def end(self, c):
        pass


class pisaTagP(pisaTag):
    def start(self, c):
        # save the type of tag; it's used in PmlBaseDoc.afterFlowable()
        # to check if we need to add an outline-entry
        # c.frag.tag = self.tag
        if self.attr.align is not None:
            c.frag.alignment = getAlign(self.attr.align)


class pisaTagDIV(pisaTagP):
    pass


class pisaTagH1(pisaTagP):
    pass


class pisaTagH2(pisaTagP):
    pass


class pisaTagH3(pisaTagP):
    pass


class pisaTagH4(pisaTagP):
    pass


class pisaTagH5(pisaTagP):
    pass


class pisaTagH6(pisaTagP):
    pass


def listDecimal(c):
    c.listCounter += 1
    return unicode("%d." % c.listCounter)


roman_numeral_map = zip(
    (1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1),
    ('M', 'CM', 'D', 'CD', 'C', 'XC', 'L', 'XL', 'X', 'IX', 'V', 'IV', 'I')
)


def int_to_roman(i):
    result = []
    for integer, numeral in roman_numeral_map:
        count = int(i / integer)
        result.append(numeral * count)
        i -= integer * count
    return ''.join(result)


def listUpperRoman(c):
    c.listCounter += 1
    roman = int_to_roman(c.listCounter)
    return unicode("%s." % roman)


def listLowerRoman(c):
    return listUpperRoman(c).lower()


def listUpperAlpha(c):
    c.listCounter += 1
    index = c.listCounter - 1
    try:
        alpha = string.ascii_uppercase[index]
    except IndexError:
        # needs to start over and double the character
        # this will probably fail for anything past the 2nd time
        alpha = string.ascii_uppercase[index - 26]
        alpha *= 2
    return unicode("%s." % alpha)


def listLowerAlpha(c):
    return listUpperAlpha(c).lower()


_bullet = u"\u2022"
_list_style_type = {
    "none": u"",
    "disc": _bullet,
    "circle": _bullet,  # XXX PDF has no equivalent
    "square": _bullet,  # XXX PDF has no equivalent
    "decimal": listDecimal,
    "decimal-leading-zero": listDecimal,
    "lower-roman": listLowerRoman,
    "upper-roman": listUpperRoman,
    "hebrew": listDecimal,
    "georgian": listDecimal,
    "armenian": listDecimal,
    "cjk-ideographic": listDecimal,
    "hiragana": listDecimal,
    "katakana": listDecimal,
    "hiragana-iroha": listDecimal,
    "katakana-iroha": listDecimal,
    "lower-latin": listDecimal,
    "lower-alpha": listLowerAlpha,
    "upper-latin": listDecimal,
    "upper-alpha": listUpperAlpha,
    "lower-greek": listDecimal,
}


class pisaTagUL(pisaTagP):
    def start(self, c):
        self.counter, c.listCounter = c.listCounter, 0

    def end(self, c):
        c.addPara()
        # XXX Simulate margin for the moment
        c.addStory(Spacer(width=1, height=c.fragBlock.spaceAfter))
        c.listCounter = self.counter


class pisaTagOL(pisaTagUL):
    pass


class pisaTagLI(pisaTag):
    def start(self, c):
        lst = _list_style_type.get(c.frag.listStyleType or "disc", _bullet)
        frag = copy.copy(c.frag)

        self.offset = 0
        if frag.listStyleImage is not None:
            frag.text = u""
            f = frag.listStyleImage
            if f and (not f.notFound()):
                img = PmlImage(
                    f.getData(),
                    width=None,
                    height=None)
                img.drawHeight *= dpi96
                img.drawWidth *= dpi96
                img.pisaZoom = frag.zoom
                img.drawWidth *= img.pisaZoom
                img.drawHeight *= img.pisaZoom
                frag.image = img
                self.offset = max(0, img.drawHeight - c.frag.fontSize)
        else:
            if type(lst) == type(u""):
                frag.text = lst
            else:
                # XXX This should be the recent font, but it throws errors in Reportlab!
                frag.text = lst(c)

        # XXX This should usually be done in the context!!!
        frag.fontName = frag.bulletFontName = tt2ps(frag.fontName, frag.bold, frag.italic)
        c.frag.bulletText = [frag]

    def end(self, c):
        c.fragBlock.spaceBefore += self.offset


class pisaTagBR(pisaTag):
    def start(self, c):
        c.frag.lineBreak = 1
        c.addFrag()
        c.fragStrip = True
        del c.frag.lineBreak
        c.force = True


class pisaTagIMG(pisaTag):
    def start(self, c):
        attr = self.attr
        if attr.src and (not attr.src.notFound()):

            try:
                align = attr.align or c.frag.vAlign or "baseline"
                width = c.frag.width
                height = c.frag.height

                if attr.width:
                    width = attr.width * dpi96
                if attr.height:
                    height = attr.height * dpi96

                img = PmlImage(
                    attr.src.getData(),
                    width=None,
                    height=None)

                img.pisaZoom = c.frag.zoom

                img.drawHeight *= dpi96
                img.drawWidth *= dpi96

                if (width is None) and (height is not None):
                    factor = getSize(height) / img.drawHeight
                    img.drawWidth *= factor
                    img.drawHeight = getSize(height)
                elif (height is None) and (width is not None):
                    factor = getSize(width) / img.drawWidth
                    img.drawHeight *= factor
                    img.drawWidth = getSize(width)
                elif (width is not None) and (height is not None):
                    img.drawWidth = getSize(width)
                    img.drawHeight = getSize(height)

                img.drawWidth *= img.pisaZoom
                img.drawHeight *= img.pisaZoom

                img.spaceBefore = c.frag.spaceBefore
                img.spaceAfter = c.frag.spaceAfter

                # print "image", id(img), img.drawWidth, img.drawHeight

                '''
                TODO:

                - Apply styles
                - vspace etc.
                - Borders
                - Test inside tables
                '''

                c.force = True
                if align in ["left", "right"]:

                    c.image = img
                    c.imageData = dict(
                        align=align
                    )

                else:

                    # Important! Make sure that cbDefn is not inherited by other
                    # fragments because of a bug in Reportlab!
                    # afrag = c.frag.clone()

                    valign = align
                    if valign in ["texttop"]:
                        valign = "top"
                    elif valign in ["absmiddle"]:
                        valign = "middle"
                    elif valign in ["absbottom", "baseline"]:
                        valign = "bottom"

                    afrag = c.frag.clone()
                    afrag.text = ""
                    afrag.fontName = "Helvetica" # Fix for a nasty bug!!!
                    afrag.cbDefn = ABag(
                        kind="img",
                        image=img, # .getImage(), # XXX Inline?
                        valign=valign,
                        fontName="Helvetica",
                        fontSize=img.drawHeight,
                        width=img.drawWidth,
                        height=img.drawHeight)

                    c.fragList.append(afrag)
                    c.fontSize = img.drawHeight

            except Exception:  # TODO: Kill catch-all
                log.warn(c.warning("Error in handling image"), exc_info=1)
        else:
            log.warn(c.warning("Need a valid file name!"))


class pisaTagHR(pisaTag):
    def start(self, c):
        c.addPara()
        c.addStory(HRFlowable(
            color=self.attr.color,
            thickness=self.attr.size,
            width=self.attr.get('width', "100%") or "100%",
            spaceBefore=c.frag.spaceBefore,
            spaceAfter=c.frag.spaceAfter
        ))

# --- Forms


if 0:

    class pisaTagINPUT(pisaTag):

        def _render(self, c, attr):
            width = 10
            height = 10
            if attr.type == "text":
                width = 100
                height = 12
            c.addStory(xhtml2pdf_reportlab.PmlInput(attr.name,
                                                    type=attr.type,
                                                    default=attr.value,
                                                    width=width,
                                                    height=height,
            ))

        def end(self, c):
            c.addPara()
            attr = self.attr
            if attr.name:
                self._render(c, attr)
            c.addPara()

    class pisaTagTEXTAREA(pisaTagINPUT):

        def _render(self, c, attr):
            c.addStory(xhtml2pdf_reportlab.PmlInput(attr.name,
                                                    default="",
                                                    width=100,
                                                    height=100))

    class pisaTagSELECT(pisaTagINPUT):

        def start(self, c):
            c.select_options = ["One", "Two", "Three"]

        def _render(self, c, attr):
            c.addStory(xhtml2pdf_reportlab.PmlInput(attr.name,
                                                    type="select",
                                                    default=c.select_options[0],
                                                    options=c.select_options,
                                                    width=100,
                                                    height=40))
            c.select_options = None

    class pisaTagOPTION(pisaTag):

        pass


class pisaTagPDFNEXTPAGE(pisaTag):
    """
    <pdf:nextpage name="" />
    """

    def start(self, c):
        # deprecation("pdf:nextpage")
        c.addPara()
        if self.attr.name:
            c.addStory(NextPageTemplate(self.attr.name))
        c.addStory(PageBreak())


class pisaTagPDFNEXTTEMPLATE(pisaTag):
    """
    <pdf:nexttemplate name="" />
    """

    def start(self, c):
        # deprecation("pdf:frame")
        c.addStory(NextPageTemplate(self.attr["name"]))


class pisaTagPDFNEXTFRAME(pisaTag):
    """
    <pdf:nextframe name="" />
    """

    def start(self, c):
        c.addPara()
        c.addStory(FrameBreak())


class pisaTagPDFSPACER(pisaTag):
    """
    <pdf:spacer height="" />
    """

    def start(self, c):
        c.addPara()
        c.addStory(Spacer(1, self.attr.height))


class pisaTagPDFPAGENUMBER(pisaTag):
    """
    <pdf:pagenumber example="" />
    """

    def start(self, c):
        c.frag.pageNumber = True
        c.addFrag(self.attr.example)
        c.frag.pageNumber = False


class pisaTagPDFPAGECOUNT(pisaTag):
    """
    <pdf:pagecount />
    """

    def start(self, c):
        c.frag.pageCount = True
        c.addFrag()
        c.frag.pageCount = False

    def end(self, c):
        c.addPageCount()


class pisaTagPDFTOC(pisaTag):
    """
    <pdf:toc />
    """

    def end(self, c):
        c.multiBuild = True
        c.addTOC()


class pisaTagPDFFRAME(pisaTag):
    """
    <pdf:frame name="" static box="" />
    """

    def start(self, c):
        deprecation("pdf:frame")
        attrs = self.attr

        name = attrs["name"]
        if name is None:
            name = "frame%d" % c.UID()

        x, y, w, h = attrs.box
        self.frame = Frame(
            x, y, w, h,
            id=name,
            leftPadding=0,
            rightPadding=0,
            bottomPadding=0,
            topPadding=0,
            showBoundary=attrs.border)

        self.static = False
        if self.attr.static:
            self.static = True
            c.addPara()
            self.story = c.swapStory()
        else:
            c.frameList.append(self.frame)

    def end(self, c):
        if self.static:
            c.addPara()
            self.frame.pisaStaticStory = c.story
            c.frameStaticList.append(self.frame)
            c.swapStory(self.story)


class pisaTagPDFTEMPLATE(pisaTag):
    """
    <pdf:template name="" static box="" >
        <pdf:frame...>
    </pdf:template>
    """

    def start(self, c):
        deprecation("pdf:template")
        attrs = self.attr
        #print attrs
        name = attrs["name"]
        c.frameList = []
        c.frameStaticList = []
        if name in c.templateList:
            log.warn(c.warning("template '%s' has already been defined", name))

    def end(self, c):
        attrs = self.attr
        name = attrs["name"]
        if len(c.frameList) <= 0:
            log.warn(c.warning("missing frame definitions for template"))

        pt = PmlPageTemplate(
            id=name,
            frames=c.frameList,
            pagesize=A4,
        )
        pt.pisaStaticList = c.frameStaticList
        pt.pisaBackgroundList = c.pisaBackgroundList
        pt.pisaBackground = self.attr.background

        c.templateList[name] = pt
        c.template = None
        c.frameList = []
        c.frameStaticList = []


class pisaTagPDFFONT(pisaTag):
    """
    <pdf:fontembed name="" src="" />
    """

    def start(self, c):
        deprecation("pdf:font")
        c.loadFont(self.attr.name, self.attr.src, self.attr.encoding)


class pisaTagPDFBARCODE(pisaTag):
    _codeName = {
        "I2OF5": "I2of5",
        "ITF": "I2of5",
        "CODE39": "Standard39",
        "EXTENDEDCODE39": "Extended39",
        "CODE93": "Standard93",
        "EXTENDEDCODE93": "Extended93",
        "MSI": "MSI",
        "CODABAR": "Codabar",
        "NW7": "Codabar",
        "CODE11": "Code11",
        "FIM": "FIM",
        "POSTNET": "POSTNET",
        "USPS4S": "USPS_4State",
        "CODE128": "Code128",
        "EAN13": "EAN13",
        "EAN8": "EAN8",
        "QR": "QR",
    }

    class _barcodeWrapper(Flowable):
        """
        Wrapper for barcode widget
        """
        def __init__(self, codeName="Code128", value="", **kw):
            self.vertical = kw.get('vertical', 0)
            self.widget = createBarcodeDrawing(codeName, value=value, **kw)

        def draw(self, canvas, xoffset=0, **kw):
            # NOTE: 'canvas' is mutable, so canvas.restoreState() is a MUST.
            canvas.saveState()
            # NOTE: checking vertical value to rotate the barcode
            if self.vertical:
                width, height = self.wrap(0, 0)
                # Note: moving our canvas to the new origin
                canvas.translate(height, -width)
                canvas.rotate(90)
            else:
                canvas.translate(xoffset, 0)
            self.widget.canv = canvas
            self.widget.draw()
            canvas.restoreState()

        def wrap(self, aW, aH):
            return self.widget.wrap(aW, aH)

    def start(self, c):
        attr = self.attr
        codeName = attr.type or "Code128"
        codeName = pisaTagPDFBARCODE._codeName[codeName.upper().replace("-", "")]
        humanReadable = int(attr.humanreadable)
        vertical = int(attr.vertical)
        checksum = int(attr.checksum)
        barWidth = attr.barwidth or 0.01 * inch
        barHeight = attr.barheight or 0.5 * inch
        fontName = c.getFontName("OCRB10,OCR-B,OCR B,OCRB")  # or "Helvetica"
        fontSize = attr.fontsize or 2.75 * mm

        # Assure minimal size.
        if codeName in ("EAN13", "EAN8"):
            barWidth = max(barWidth, 0.264 * mm)
            fontSize = max(fontSize, 2.75 * mm)
        else:  # Code39 etc.
            barWidth = max(barWidth, 0.0075 * inch)

        barcode = pisaTagPDFBARCODE._barcodeWrapper(
            codeName=codeName,
            value=attr.value,
            barWidth=barWidth,
            barHeight=barHeight,
            humanReadable=humanReadable,
            vertical=vertical,
            checksum=checksum,
            fontName=fontName,
            fontSize=fontSize,
        )

        width, height = barcode.wrap(c.frag.width, c.frag.height)
        c.force = True

        valign = attr.align or c.frag.vAlign or "baseline"
        if valign in ["texttop"]:
            valign = "top"
        elif valign in ["absmiddle"]:
            valign = "middle"
        elif valign in ["absbottom", "baseline"]:
            valign = "bottom"

        afrag = c.frag.clone()
        afrag.text = ""
        afrag.fontName = fontName
        afrag.cbDefn = ABag(
            kind="barcode",
            barcode=barcode,
            width=width,
            height=height,
            valign=valign,
        )
        c.fragList.append(afrag)

########NEW FILE########
__FILENAME__ = turbogears
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

from turbogears.decorator import weak_signature_decorator
import xhtml2pdf.pisa as pisa
import StringIO
import cherrypy


def to_pdf(filename=None, content_type="application/pdf"):
    def entangle(func):
        def decorated(func, *args, **kw):
            output = func(*args, **kw)
            dst = StringIO.StringIO()
            result = pisa.CreatePDF(
                StringIO.StringIO(output),
                dst
            )
            if not result.err:
                cherrypy.response.headers["Content-Type"] = content_type
                if filename:
                    cherrypy.response.headers["Content-Disposition"] = "attachment; filename=" + filename
                output = dst.getvalue()
            return output

        return decorated

    return weak_signature_decorator(entangle)


topdf = to_pdf

########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
from reportlab.lib.colors import Color, toColor
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.units import inch, cm
import base64
try:
    import httplib
except ImportError:
    import http.client as httplib
import logging
import mimetypes
import os.path
import re
import reportlab
import shutil
import string
import sys
import tempfile
import types
import urllib
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

# Copyright 2010 Dirk Holtwick, holtwick.it
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

rgb_re = re.compile("^.*?rgb[(]([0-9]+).*?([0-9]+).*?([0-9]+)[)].*?[ ]*$")

_reportlab_version = tuple(map(int, reportlab.Version.split('.')))
if _reportlab_version < (2, 1):
    raise ImportError("Reportlab Version 2.1+ is needed!")

REPORTLAB22 = _reportlab_version >= (2, 2)
# print "***", reportlab.Version, REPORTLAB22, reportlab.__file__

log = logging.getLogger("xhtml2pdf")

try:
    import cStringIO as io
except:
    try:
        import StringIO as io
    except ImportError:
        import io

try:
    import PyPDF2
except:
    PyPDF2 = None

try:
    from reportlab.graphics import renderPM
except:
    renderPM = None

try:
    from reportlab.graphics import renderSVG
except:
    renderSVG = None


#=========================================================================
# Memoize decorator
#=========================================================================
class memoized(object):

    """
    A kwargs-aware memoizer, better than the one in python :)

    Don't pass in too large kwargs, since this turns them into a tuple of
    tuples. Also, avoid mutable types (as usual for memoizers)

    What this does is to create a dictionnary of {(*parameters):return value},
    and uses it as a cache for subsequent calls to the same method.
    It is especially useful for functions that don't rely on external variables
    and that are called often. It's a perfect match for our getSize etc...
    """

    def __init__(self, func):
        self.cache = {}
        self.func = func
        self.__doc__ = self.func.__doc__  # To avoid great confusion
        self.__name__ = self.func.__name__  # This also avoids great confusion

    def __call__(self, *args, **kwargs):
        # Make sure the following line is not actually slower than what you're
        # trying to memoize
        args_plus = tuple(kwargs.iteritems())
        key = (args, args_plus)
        try:
            if key not in self.cache:
                res = self.func(*args, **kwargs)
                self.cache[key] = res
            return self.cache[key]
        except TypeError:
            # happens if any of the parameters is a list
            return self.func(*args, **kwargs)


def ErrorMsg():
    """
    Helper to get a nice traceback as string
    """
    import traceback
    import sys

    type = value = tb = limit = None
    type, value, tb = sys.exc_info()
    list = traceback.format_tb(tb, limit) + \
        traceback.format_exception_only(type, value)
    return "Traceback (innermost last):\n" + "%-20s %s" % (
        string.join(list[: - 1], ""),
        list[- 1])


def toList(value):
    if type(value) not in (types.ListType, types.TupleType):
        return [value]
    return list(value)


@memoized
def getColor(value, default=None):
    """
    Convert to color value.
    This returns a Color object instance from a text bit.
    """

    if isinstance(value, Color):
        return value
    value = str(value).strip().lower()
    if value == "transparent" or value == "none":
        return default
    if value in COLOR_BY_NAME:
        return COLOR_BY_NAME[value]
    if value.startswith("#") and len(value) == 4:
        value = "#" + value[1] + value[1] + \
            value[2] + value[2] + value[3] + value[3]
    elif rgb_re.search(value):
        # e.g., value = "<css function: rgb(153, 51, 153)>", go figure:
        r, g, b = [int(x) for x in rgb_re.search(value).groups()]
        value = "#%02x%02x%02x" % (r, g, b)
    else:
        # Shrug
        pass

    return toColor(value, default)  # Calling the reportlab function


def getBorderStyle(value, default=None):
    # log.debug(value)
    if value and (str(value).lower() not in ("none", "hidden")):
        return value
    return default


mm = cm / 10.0
dpi96 = (1.0 / 96.0 * inch)

_absoluteSizeTable = {
    "1": 50.0 / 100.0,
    "xx-small": 50.0 / 100.0,
    "x-small": 50.0 / 100.0,
    "2": 75.0 / 100.0,
    "small": 75.0 / 100.0,
    "3": 100.0 / 100.0,
    "medium": 100.0 / 100.0,
    "4": 125.0 / 100.0,
    "large": 125.0 / 100.0,
    "5": 150.0 / 100.0,
    "x-large": 150.0 / 100.0,
    "6": 175.0 / 100.0,
    "xx-large": 175.0 / 100.0,
    "7": 200.0 / 100.0,
    "xxx-large": 200.0 / 100.0,
}

_relativeSizeTable = {
    "larger": 1.25,
    "smaller": 0.75,
    "+4": 200.0 / 100.0,
    "+3": 175.0 / 100.0,
    "+2": 150.0 / 100.0,
    "+1": 125.0 / 100.0,
    "-1": 75.0 / 100.0,
    "-2": 50.0 / 100.0,
    "-3": 25.0 / 100.0,
}

MIN_FONT_SIZE = 1.0


@memoized
def getSize(value, relative=0, base=None, default=0.0):
    """
    Converts strings to standard sizes.
    That is the function taking a string of CSS size ('12pt', '1cm' and so on)
    and converts it into a float in a standard unit (in our case, points).

    >>> getSize('12pt')
    12.0
    >>> getSize('1cm')
    28.346456692913385
    """
    try:
        original = value
        if value is None:
            return relative
        elif type(value) is types.FloatType:
            return value
        elif isinstance(value, int):
            return float(value)
        elif type(value) in (types.TupleType, types.ListType):
            value = "".join(value)
        value = str(value).strip().lower().replace(",", ".")
        if value[-2:] == 'cm':
            return float(value[:-2].strip()) * cm
        elif value[-2:] == 'mm':
            return float(value[:-2].strip()) * mm  # 1mm = 0.1cm
        elif value[-2:] == 'in':
            return float(value[:-2].strip()) * inch  # 1pt == 1/72inch
        elif value[-2:] == 'inch':
            return float(value[:-4].strip()) * inch  # 1pt == 1/72inch
        elif value[-2:] == 'pt':
            return float(value[:-2].strip())
        elif value[-2:] == 'pc':
            return float(value[:-2].strip()) * 12.0  # 1pc == 12pt
        elif value[-2:] == 'px':
            # XXX W3C says, use 96pdi
            # http://www.w3.org/TR/CSS21/syndata.html#length-units
            return float(value[:-2].strip()) * dpi96
        elif value[-1:] == 'i':  # 1pt == 1/72inch
            return float(value[:-1].strip()) * inch
        elif value in ("none", "0", "auto"):
            return 0.0
        elif relative:
            if value[-2:] == 'em':  # XXX
                # 1em = 1 * fontSize
                return float(value[:-2].strip()) * relative
            elif value[-2:] == 'ex':  # XXX
                # 1ex = 1/2 fontSize
                return float(value[:-2].strip()) * (relative / 2.0)
            elif value[-1:] == '%':
                # 1% = (fontSize * 1) / 100
                return (relative * float(value[:-1].strip())) / 100.0
            elif value in ("normal", "inherit"):
                return relative
            elif value in _relativeSizeTable:
                if base:
                    return max(MIN_FONT_SIZE, base * _relativeSizeTable[value])
                return max(MIN_FONT_SIZE, relative * _relativeSizeTable[value])
            elif value in _absoluteSizeTable:
                if base:
                    return max(MIN_FONT_SIZE, base * _absoluteSizeTable[value])
                return max(MIN_FONT_SIZE, relative * _absoluteSizeTable[value])
            else:
                return max(MIN_FONT_SIZE, relative * float(value))
        try:
            value = float(value)
        except:
            log.warn("getSize: Not a float %r", value)
            return default  # value = 0
        return max(0, value)
    except Exception:
        log.warn("getSize %r %r", original, relative, exc_info=1)
        return default


@memoized
def getCoords(x, y, w, h, pagesize):
    """
    As a stupid programmer I like to use the upper left
    corner of the document as the 0,0 coords therefore
    we need to do some fancy calculations
    """
    #~ print pagesize
    ax, ay = pagesize
    if x < 0:
        x = ax + x
    if y < 0:
        y = ay + y
    if w is not None and h is not None:
        if w <= 0:
            w = (ax - x + w)
        if h <= 0:
            h = (ay - y + h)
        return x, (ay - y - h), w, h
    return x, (ay - y)


@memoized
def getBox(box, pagesize):
    """
    Parse sizes by corners in the form:
    <X-Left> <Y-Upper> <Width> <Height>
    The last to values with negative values are interpreted as offsets form
    the right and lower border.
    """
    box = str(box).split()
    if len(box) != 4:
        raise Exception("box not defined right way")
    x, y, w, h = [getSize(pos) for pos in box]
    return getCoords(x, y, w, h, pagesize)


def getFrameDimensions(data, page_width, page_height):
    """Calculate dimensions of a frame

    Returns left, top, width and height of the frame in points.
    """
    box = data.get("-pdf-frame-box", [])
    if len(box) == 4:
        return [getSize(x) for x in box]
    top = getSize(data.get("top", 0))
    left = getSize(data.get("left", 0))
    bottom = getSize(data.get("bottom", 0))
    right = getSize(data.get("right", 0))
    if "height" in data:
        height = getSize(data["height"])
        if "top" in data:
            top = getSize(data["top"])
            bottom = page_height - (top + height)
        elif "bottom" in data:
            bottom = getSize(data["bottom"])
            top = page_height - (bottom + height)
    if "width" in data:
        width = getSize(data["width"])
        if "left" in data:
            left = getSize(data["left"])
            right = page_width - (left + width)
        elif "right" in data:
            right = getSize(data["right"])
            left = page_width - (right + width)
    top += getSize(data.get("margin-top", 0))
    left += getSize(data.get("margin-left", 0))
    bottom += getSize(data.get("margin-bottom", 0))
    right += getSize(data.get("margin-right", 0))

    width = page_width - (left + right)
    height = page_height - (top + bottom)
    return left, top, width, height


@memoized
def getPos(position, pagesize):
    """
    Pair of coordinates
    """
    position = str(position).split()
    if len(position) != 2:
        raise Exception("position not defined right way")
    x, y = [getSize(pos) for pos in position]
    return getCoords(x, y, None, None, pagesize)


def getBool(s):
    " Is it a boolean? "
    return str(s).lower() in ("y", "yes", "1", "true")


_uid = 0


def getUID():
    " Unique ID "
    global _uid
    _uid += 1
    return str(_uid)


_alignments = {
    "left": TA_LEFT,
    "center": TA_CENTER,
    "middle": TA_CENTER,
    "right": TA_RIGHT,
    "justify": TA_JUSTIFY,
}


def getAlign(value, default=TA_LEFT):
    return _alignments.get(str(value).lower(), default)

GAE = "google.appengine" in sys.modules

if GAE:
    STRATEGIES = (
        io.StringIO,
        io.StringIO)
else:
    STRATEGIES = (
        io.StringIO,
        tempfile.NamedTemporaryFile)


class pisaTempFile(object):

    """
    A temporary file implementation that uses memory unless
    either capacity is breached or fileno is requested, at which
    point a real temporary file will be created and the relevant
    details returned

    If capacity is -1 the second strategy will never be used.

    Inspired by:
    http://code.activestate.com/recipes/496744/
    """

    STRATEGIES = STRATEGIES

    CAPACITY = 10 * 1024

    def __init__(self, buffer="", capacity=CAPACITY):
        """Creates a TempFile object containing the specified buffer.
        If capacity is specified, we use a real temporary file once the
        file gets larger than that size.  Otherwise, the data is stored
        in memory.
        """

        self.capacity = capacity
        self.strategy = int(len(buffer) > self.capacity)
        try:
            self._delegate = self.STRATEGIES[self.strategy]()
        except:
            # Fallback for Google AppEnginge etc.
            self._delegate = self.STRATEGIES[0]()
        self.write(buffer)
        # we must set the file's position for preparing to read
        self.seek(0)

    def makeTempFile(self):
        """
        Switch to next startegy. If an error occured,
        stay with the first strategy
        """

        if self.strategy == 0:
            try:
                new_delegate = self.STRATEGIES[1]()
                new_delegate.write(self.getvalue())
                self._delegate = new_delegate
                self.strategy = 1
                log.warn("Created temporary file %s", self.name)
            except:
                self.capacity = - 1

    def getFileName(self):
        """
        Get a named temporary file
        """

        self.makeTempFile()
        return self.name

    def fileno(self):
        """
        Forces this buffer to use a temporary file as the underlying.
        object and returns the fileno associated with it.
        """
        self.makeTempFile()
        return self._delegate.fileno()

    def getvalue(self):
        """
        Get value of file. Work around for second strategy
        """

        if self.strategy == 0:
            return self._delegate.getvalue()
        self._delegate.flush()
        self._delegate.seek(0)
        return self._delegate.read()

    def write(self, value):
        """
        If capacity != -1 and length of file > capacity it is time to switch
        """

        if self.capacity > 0 and self.strategy == 0:
            len_value = len(value)
            if len_value >= self.capacity:
                needs_new_strategy = True
            else:
                self.seek(0, 2)  # find end of file
                needs_new_strategy = \
                    (self.tell() + len_value) >= self.capacity
            if needs_new_strategy:
                self.makeTempFile()
        self._delegate.write(value)

    def __getattr__(self, name):
        try:
            return getattr(self._delegate, name)
        except AttributeError:
            # hide the delegation
            e = "object '%s' has no attribute '%s'" \
                % (self.__class__.__name__, name)
            raise AttributeError(e)


_rx_datauri = re.compile(
    "^data:(?P<mime>[a-z]+/[a-z]+);base64,(?P<data>.*)$", re.M | re.DOTALL)


class pisaFileObject:

    """
    XXX
    """

    def __init__(self, uri, basepath=None):
        self.basepath = basepath
        self.mimetype = None
        self.file = None
        self.data = None
        self.uri = None
        self.local = None
        self.tmp_file = None
        uri = uri or str()
        uri = uri.encode('utf-8')
        log.debug("FileObject %r, Basepath: %r", uri, basepath)

        # Data URI
        if uri.startswith("data:"):
            m = _rx_datauri.match(uri)
            self.mimetype = m.group("mime")
            self.data = base64.decodestring(m.group("data"))

        else:
            # Check if we have an external scheme
            if basepath and not urlparse.urlparse(uri).scheme:
                urlParts = urlparse.urlparse(basepath)
            else:
                urlParts = urlparse.urlparse(uri)

            log.debug("URLParts: %r", urlParts)

            if urlParts.scheme == 'file':
                if basepath and uri.startswith('/'):
                    uri = urlparse.urljoin(basepath, uri[1:])
                urlResponse = urllib2.urlopen(uri)
                self.mimetype = urlResponse.info().get(
                    "Content-Type", '').split(";")[0]
                self.uri = urlResponse.geturl()
                self.file = urlResponse

            # Drive letters have len==1 but we are looking
            # for things like http:
            elif urlParts.scheme in ('http', 'https'):

                # External data
                if basepath:
                    uri = urlparse.urljoin(basepath, uri)

                #path = urlparse.urlsplit(url)[2]
                #mimetype = getMimeType(path)

                # Using HTTPLIB
                server, path = urllib.splithost(uri[uri.find("//"):])
                if uri.startswith("https://"):
                    conn = httplib.HTTPSConnection(server)
                else:
                    conn = httplib.HTTPConnection(server)
                conn.request("GET", path)
                r1 = conn.getresponse()
                # log.debug("HTTP %r %r %r %r", server, path, uri, r1)
                if (r1.status, r1.reason) == (200, "OK"):
                    self.mimetype = r1.getheader(
                        "Content-Type", '').split(";")[0]
                    self.uri = uri
                    if r1.getheader("content-encoding") == "gzip":
                        import gzip
                        try:
                            import cStringIO as io
                        except:
                            try:
                                import StringIO as io
                            except ImportError:
                                import io

                        self.file = gzip.GzipFile(
                            mode="rb", fileobj=io.StringIO(r1.read()))
                    else:
                        self.file = r1
                else:
                    try:
                        urlResponse = urllib2.urlopen(uri)
                    except urllib2.HTTPError:
                        return
                    self.mimetype = urlResponse.info().get(
                        "Content-Type", '').split(";")[0]
                    self.uri = urlResponse.geturl()
                    self.file = urlResponse

            else:

                # Local data
                if basepath:
                    uri = os.path.normpath(os.path.join(basepath, uri))

                if os.path.isfile(uri):
                    self.uri = uri
                    self.local = uri
                    self.setMimeTypeByName(uri)
                    self.file = open(uri, "rb")

    def getFile(self):
        if self.file is not None:
            return self.file
        if self.data is not None:
            return pisaTempFile(self.data)
        return None

    def getNamedFile(self):
        if self.notFound():
            return None
        if self.local:
            return str(self.local)
        if not self.tmp_file:
            self.tmp_file = tempfile.NamedTemporaryFile()
            if self.file:
                shutil.copyfileobj(self.file, self.tmp_file)
            else:
                self.tmp_file.write(self.getData())
            self.tmp_file.flush()
        return self.tmp_file.name

    def getData(self):
        if self.data is not None:
            return self.data
        if self.file is not None:
            self.data = self.file.read()
            return self.data
        return None

    def notFound(self):
        return (self.file is None) and (self.data is None)

    def setMimeTypeByName(self, name):
        " Guess the mime type "
        mimetype = mimetypes.guess_type(name)[0]
        if mimetype is not None:
            self.mimetype = mimetypes.guess_type(name)[0].split(";")[0]


def getFile(*a, **kw):
    file = pisaFileObject(*a, **kw)
    if file.notFound():
        return None
    return file


COLOR_BY_NAME = {
    'activeborder': Color(212, 208, 200),
    'activecaption': Color(10, 36, 106),
    'aliceblue': Color(.941176, .972549, 1),
    'antiquewhite': Color(.980392, .921569, .843137),
    'appworkspace': Color(128, 128, 128),
    'aqua': Color(0, 1, 1),
    'aquamarine': Color(.498039, 1, .831373),
    'azure': Color(.941176, 1, 1),
    'background': Color(58, 110, 165),
    'beige': Color(.960784, .960784, .862745),
    'bisque': Color(1, .894118, .768627),
    'black': Color(0, 0, 0),
    'blanchedalmond': Color(1, .921569, .803922),
    'blue': Color(0, 0, 1),
    'blueviolet': Color(.541176, .168627, .886275),
    'brown': Color(.647059, .164706, .164706),
    'burlywood': Color(.870588, .721569, .529412),
    'buttonface': Color(212, 208, 200),
    'buttonhighlight': Color(255, 255, 255),
    'buttonshadow': Color(128, 128, 128),
    'buttontext': Color(0, 0, 0),
    'cadetblue': Color(.372549, .619608, .627451),
    'captiontext': Color(255, 255, 255),
    'chartreuse': Color(.498039, 1, 0),
    'chocolate': Color(.823529, .411765, .117647),
    'coral': Color(1, .498039, .313725),
    'cornflowerblue': Color(.392157, .584314, .929412),
    'cornsilk': Color(1, .972549, .862745),
    'crimson': Color(.862745, .078431, .235294),
    'cyan': Color(0, 1, 1),
    'darkblue': Color(0, 0, .545098),
    'darkcyan': Color(0, .545098, .545098),
    'darkgoldenrod': Color(.721569, .52549, .043137),
    'darkgray': Color(.662745, .662745, .662745),
    'darkgreen': Color(0, .392157, 0),
    'darkgrey': Color(.662745, .662745, .662745),
    'darkkhaki': Color(.741176, .717647, .419608),
    'darkmagenta': Color(.545098, 0, .545098),
    'darkolivegreen': Color(.333333, .419608, .184314),
    'darkorange': Color(1, .54902, 0),
    'darkorchid': Color(.6, .196078, .8),
    'darkred': Color(.545098, 0, 0),
    'darksalmon': Color(.913725, .588235, .478431),
    'darkseagreen': Color(.560784, .737255, .560784),
    'darkslateblue': Color(.282353, .239216, .545098),
    'darkslategray': Color(.184314, .309804, .309804),
    'darkslategrey': Color(.184314, .309804, .309804),
    'darkturquoise': Color(0, .807843, .819608),
    'darkviolet': Color(.580392, 0, .827451),
    'deeppink': Color(1, .078431, .576471),
    'deepskyblue': Color(0, .74902, 1),
    'dimgray': Color(.411765, .411765, .411765),
    'dimgrey': Color(.411765, .411765, .411765),
    'dodgerblue': Color(.117647, .564706, 1),
    'firebrick': Color(.698039, .133333, .133333),
    'floralwhite': Color(1, .980392, .941176),
    'forestgreen': Color(.133333, .545098, .133333),
    'fuchsia': Color(1, 0, 1),
    'gainsboro': Color(.862745, .862745, .862745),
    'ghostwhite': Color(.972549, .972549, 1),
    'gold': Color(1, .843137, 0),
    'goldenrod': Color(.854902, .647059, .12549),
    'gray': Color(.501961, .501961, .501961),
    'graytext': Color(128, 128, 128),
    'green': Color(0, .501961, 0),
    'greenyellow': Color(.678431, 1, .184314),
    'grey': Color(.501961, .501961, .501961),
    'highlight': Color(10, 36, 106),
    'highlighttext': Color(255, 255, 255),
    'honeydew': Color(.941176, 1, .941176),
    'hotpink': Color(1, .411765, .705882),
    'inactiveborder': Color(212, 208, 200),
    'inactivecaption': Color(128, 128, 128),
    'inactivecaptiontext': Color(212, 208, 200),
    'indianred': Color(.803922, .360784, .360784),
    'indigo': Color(.294118, 0, .509804),
    'infobackground': Color(255, 255, 225),
    'infotext': Color(0, 0, 0),
    'ivory': Color(1, 1, .941176),
    'khaki': Color(.941176, .901961, .54902),
    'lavender': Color(.901961, .901961, .980392),
    'lavenderblush': Color(1, .941176, .960784),
    'lawngreen': Color(.486275, .988235, 0),
    'lemonchiffon': Color(1, .980392, .803922),
    'lightblue': Color(.678431, .847059, .901961),
    'lightcoral': Color(.941176, .501961, .501961),
    'lightcyan': Color(.878431, 1, 1),
    'lightgoldenrodyellow': Color(.980392, .980392, .823529),
    'lightgray': Color(.827451, .827451, .827451),
    'lightgreen': Color(.564706, .933333, .564706),
    'lightgrey': Color(.827451, .827451, .827451),
    'lightpink': Color(1, .713725, .756863),
    'lightsalmon': Color(1, .627451, .478431),
    'lightseagreen': Color(.12549, .698039, .666667),
    'lightskyblue': Color(.529412, .807843, .980392),
    'lightslategray': Color(.466667, .533333, .6),
    'lightslategrey': Color(.466667, .533333, .6),
    'lightsteelblue': Color(.690196, .768627, .870588),
    'lightyellow': Color(1, 1, .878431),
    'lime': Color(0, 1, 0),
    'limegreen': Color(.196078, .803922, .196078),
    'linen': Color(.980392, .941176, .901961),
    'magenta': Color(1, 0, 1),
    'maroon': Color(.501961, 0, 0),
    'mediumaquamarine': Color(.4, .803922, .666667),
    'mediumblue': Color(0, 0, .803922),
    'mediumorchid': Color(.729412, .333333, .827451),
    'mediumpurple': Color(.576471, .439216, .858824),
    'mediumseagreen': Color(.235294, .701961, .443137),
    'mediumslateblue': Color(.482353, .407843, .933333),
    'mediumspringgreen': Color(0, .980392, .603922),
    'mediumturquoise': Color(.282353, .819608, .8),
    'mediumvioletred': Color(.780392, .082353, .521569),
    'menu': Color(212, 208, 200),
    'menutext': Color(0, 0, 0),
    'midnightblue': Color(.098039, .098039, .439216),
    'mintcream': Color(.960784, 1, .980392),
    'mistyrose': Color(1, .894118, .882353),
    'moccasin': Color(1, .894118, .709804),
    'navajowhite': Color(1, .870588, .678431),
    'navy': Color(0, 0, .501961),
    'oldlace': Color(.992157, .960784, .901961),
    'olive': Color(.501961, .501961, 0),
    'olivedrab': Color(.419608, .556863, .137255),
    'orange': Color(1, .647059, 0),
    'orangered': Color(1, .270588, 0),
    'orchid': Color(.854902, .439216, .839216),
    'palegoldenrod': Color(.933333, .909804, .666667),
    'palegreen': Color(.596078, .984314, .596078),
    'paleturquoise': Color(.686275, .933333, .933333),
    'palevioletred': Color(.858824, .439216, .576471),
    'papayawhip': Color(1, .937255, .835294),
    'peachpuff': Color(1, .854902, .72549),
    'peru': Color(.803922, .521569, .247059),
    'pink': Color(1, .752941, .796078),
    'plum': Color(.866667, .627451, .866667),
    'powderblue': Color(.690196, .878431, .901961),
    'purple': Color(.501961, 0, .501961),
    'red': Color(1, 0, 0),
    'rosybrown': Color(.737255, .560784, .560784),
    'royalblue': Color(.254902, .411765, .882353),
    'saddlebrown': Color(.545098, .270588, .07451),
    'salmon': Color(.980392, .501961, .447059),
    'sandybrown': Color(.956863, .643137, .376471),
    'scrollbar': Color(212, 208, 200),
    'seagreen': Color(.180392, .545098, .341176),
    'seashell': Color(1, .960784, .933333),
    'sienna': Color(.627451, .321569, .176471),
    'silver': Color(.752941, .752941, .752941),
    'skyblue': Color(.529412, .807843, .921569),
    'slateblue': Color(.415686, .352941, .803922),
    'slategray': Color(.439216, .501961, .564706),
    'slategrey': Color(.439216, .501961, .564706),
    'snow': Color(1, .980392, .980392),
    'springgreen': Color(0, 1, .498039),
    'steelblue': Color(.27451, .509804, .705882),
    'tan': Color(.823529, .705882, .54902),
    'teal': Color(0, .501961, .501961),
    'thistle': Color(.847059, .74902, .847059),
    'threeddarkshadow': Color(64, 64, 64),
    'threedface': Color(212, 208, 200),
    'threedhighlight': Color(255, 255, 255),
    'threedlightshadow': Color(212, 208, 200),
    'threedshadow': Color(128, 128, 128),
    'tomato': Color(1, .388235, .278431),
    'turquoise': Color(.25098, .878431, .815686),
    'violet': Color(.933333, .509804, .933333),
    'wheat': Color(.960784, .870588, .701961),
    'white': Color(1, 1, 1),
    'whitesmoke': Color(.960784, .960784, .960784),
    'window': Color(255, 255, 255),
    'windowframe': Color(0, 0, 0),
    'windowtext': Color(0, 0, 0),
    'yellow': Color(1, 1, 0),
    'yellowgreen': Color(.603922, .803922, .196078)
}

########NEW FILE########
__FILENAME__ = version
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

__reversion__ = "$Revision: 247 $"
__author__ = "$Author: holtwick $"
__date__ = "$Date: 2008-08-15 13:37:57 +0200 (Fr, 15 Aug 2008) $"
__version__ = VERSION = "VERSION{3.0.33}VERSION"[8:-8]
__build__ = BUILD = "BUILD{2010-06-16}BUILD"[6:-6]

VERSION_STR = """XHTML2PDF/pisa %s (Build %s)
http://www.xhtml2pdf.com

Copyright 2010 Dirk Holtwick, holtwick.it

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.""" % (
    VERSION,
    BUILD,
)

########NEW FILE########
__FILENAME__ = css
#!/usr/bin/env python
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
##~ Copyright (C) 2002-2004  TechGame Networks, LLC.
##~
##~ This library is free software; you can redistribute it and/or
##~ modify it under the terms of the BSD style License as found in the
##~ LICENSE file included with this distribution.
##
##  Modified by Dirk Holtwick <holtwick@web.de>, 2007-2008
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""CSS-2.1 engine

Primary classes:
    * CSSElementInterfaceAbstract
        Provide a concrete implementation for the XML element model used.

    * CSSCascadeStrategy
        Implements the CSS-2.1 engine's attribute lookup rules.

    * CSSParser
        Parses CSS source forms into usable results using CSSBuilder and
        CSSMutableSelector.  You may want to override parseExternal()

    * CSSBuilder (and CSSMutableSelector)
        A concrete implementation for cssParser.CSSBuilderAbstract (and
        cssParser.CSSSelectorAbstract) to provide usable results to
        CSSParser requests.

Dependencies:
    python 2.3 (or greater)
    sets, cssParser, re (via cssParser)
"""

import sys

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ To replace any for with list comprehension
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


def stopIter(value):
    raise StopIteration(*value)


#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import copy


try:
    set
except NameError:
    from sets import Set as set
import cssParser
import cssSpecial

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Constants / Variables / Etc.
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

CSSParseError = cssParser.CSSParseError

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSElementInterfaceAbstract(object):
    def getAttr(self, name, default=NotImplemented):
        raise NotImplementedError('Subclass responsibility')


    def getIdAttr(self):
        return self.getAttr('id', '')


    def getClassAttr(self):
        return self.getAttr('class', '')


    def getInlineStyle(self):
        raise NotImplementedError('Subclass responsibility')


    def matchesNode(self):
        raise NotImplementedError('Subclass responsibility')


    def inPseudoState(self, name, params=()):
        raise NotImplementedError('Subclass responsibility')


    def iterXMLParents(self):
        """Results must be compatible with CSSElementInterfaceAbstract"""
        raise NotImplementedError('Subclass responsibility')


    def getPreviousSibling(self):
        raise NotImplementedError('Subclass responsibility')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSCascadeStrategy(object):
    author = None
    user = None
    userAgenr = None


    def __init__(self, author=None, user=None, userAgent=None):
        if author is not None:
            self.author = author
        if user is not None:
            self.user = user
        if userAgent is not None:
            self.userAgenr = userAgent

    def copyWithUpdate(self, author=None, user=None, userAgent=None):
        if author is None:
            author = self.author
        if user is None:
            user = self.user
        if userAgent is None:
            userAgent = self.userAgenr
        return self.__class__(author, user, userAgent)


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def iterCSSRulesets(self, inline=None):
        if self.userAgenr is not None:
            yield self.userAgenr[0]
            yield self.userAgenr[1]

        if self.user is not None:
            yield self.user[0]

        if self.author is not None:
            yield self.author[0]
            yield self.author[1]

        if inline:
            yield inline[0]
            yield inline[1]

        if self.user is not None:
            yield self.user[1]


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def findStyleFor(self, element, attrName, default=NotImplemented):
        """Attempts to find the style setting for attrName in the CSSRulesets.

        Note: This method does not attempt to resolve rules that return
        "inherited", "default", or values that have units (including "%").
        This is left up to the client app to re-query the CSS in order to
        implement these semantics.
        """
        rule = self.findCSSRulesFor(element, attrName)
        return self._extractStyleForRule(rule, attrName, default)


    def findStylesForEach(self, element, attrNames, default=NotImplemented):
        """Attempts to find the style setting for attrName in the CSSRulesets.

        Note: This method does not attempt to resolve rules that return
        "inherited", "default", or values that have units (including "%").
        This is left up to the client app to re-query the CSS in order to
        implement these semantics.
        """
        rules = self.findCSSRulesForEach(element, attrNames)
        return [(attrName, self._extractStyleForRule(rule, attrName, default))
                for attrName, rule in rules.iteritems()]


    def findCSSRulesFor(self, element, attrName):
        rules = []

        inline = element.getInlineStyle()

        # Generator are wonderfull but sometime slow...
        #for ruleset in self.iterCSSRulesets(inline):
        #    rules += ruleset.findCSSRuleFor(element, attrName)

        if self.userAgenr is not None:
            rules += self.userAgenr[0].findCSSRuleFor(element, attrName)
            rules += self.userAgenr[1].findCSSRuleFor(element, attrName)

        if self.user is not None:
            rules += self.user[0].findCSSRuleFor(element, attrName)

        if self.author is not None:
            rules += self.author[0].findCSSRuleFor(element, attrName)
            rules += self.author[1].findCSSRuleFor(element, attrName)

        if inline:
            rules += inline[0].findCSSRuleFor(element, attrName)
            rules += inline[1].findCSSRuleFor(element, attrName)

        if self.user is not None:
            rules += self.user[1].findCSSRuleFor(element, attrName)

        rules.sort()
        return rules


    def findCSSRulesForEach(self, element, attrNames):
        rules = dict((name, []) for name in attrNames)

        inline = element.getInlineStyle()
        for ruleset in self.iterCSSRulesets(inline):
            for attrName, attrRules in rules.iteritems():
                attrRules += ruleset.findCSSRuleFor(element, attrName)

        for attrRules in rules.itervalues():
            attrRules.sort()
        return rules


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _extractStyleForRule(self, rule, attrName, default=NotImplemented):
        if rule:
            # rule is packed in a list to differentiate from "no rule" vs "rule
            # whose value evalutates as False"
            style = rule[-1][1]
            return style[attrName]
        elif default is not NotImplemented:
            return default
        raise LookupError("Could not find style for '%s' in %r" % (attrName, rule))

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ CSS Selectors
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSSelectorBase(object):
    inline = False
    _hash = None
    _specificity = None


    def __init__(self, completeName='*'):
        if not isinstance(completeName, tuple):
            completeName = (None, '*', completeName)
        self.completeName = completeName


    def _updateHash(self):
        self._hash = hash((self.fullName, self.specificity(), self.qualifiers))


    def __hash__(self):
        if self._hash is None:
            return object.__hash__(self)
        return self._hash


    def getNSPrefix(self):
        return self.completeName[0]


    nsPrefix = property(getNSPrefix)


    def getName(self):
        return self.completeName[2]


    name = property(getName)


    def getNamespace(self):
        return self.completeName[1]


    namespace = property(getNamespace)


    def getFullName(self):
        return self.completeName[1:3]


    fullName = property(getFullName)


    def __repr__(self):
        strArgs = (self.__class__.__name__,) + self.specificity() + (self.asString(),)
        return '<%s %d:%d:%d:%d %s >' % strArgs


    def __str__(self):
        return self.asString()


    def __cmp__(self, other):
        result = cmp(self.specificity(), other.specificity())
        if result != 0:
            return result
        result = cmp(self.fullName, other.fullName)
        if result != 0:
            return result
        result = cmp(self.qualifiers, other.qualifiers)
        return result


    def specificity(self):
        if self._specificity is None:
            self._specificity = self._calcSpecificity()
        return self._specificity


    def _calcSpecificity(self):
        """from http://www.w3.org/TR/CSS21/cascade.html#specificity"""
        hashCount = 0
        qualifierCount = 0
        elementCount = int(self.name != '*')
        for q in self.qualifiers:
            if q.isHash():
                hashCount += 1
            elif q.isClass():
                qualifierCount += 1
            elif q.isAttr():
                qualifierCount += 1
            elif q.isPseudo():
                elementCount += 1
            elif q.isCombiner():
                i, h, q, e = q.selector.specificity()
                hashCount += h
                qualifierCount += q
                elementCount += e
        return self.inline, hashCount, qualifierCount, elementCount


    def matches(self, element=None):
        if element is None:
            return False

        # with  CSSDOMElementInterface.matchesNode(self, (namespace, tagName)) replacement:
        if self.fullName[1] not in ('*', element.domElement.tagName):
            return False
        if self.fullName[0] not in (None, '', '*') and self.fullName[0] != element.domElement.namespaceURI:
            return False

        for qualifier in self.qualifiers:
            if not qualifier.matches(element):
                return False
        else:
            return True


    def asString(self):
        result = []
        if self.nsPrefix is not None:
            result.append('%s|%s' % (self.nsPrefix, self.name))
        else:
            result.append(self.name)

        for q in self.qualifiers:
            if q.isCombiner():
                result.insert(0, q.asString())
            else:
                result.append(q.asString())
        return ''.join(result)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSInlineSelector(CSSSelectorBase):
    inline = True

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSMutableSelector(CSSSelectorBase, cssParser.CSSSelectorAbstract):
    qualifiers = []


    def asImmutable(self):
        return CSSImmutableSelector(self.completeName, [q.asImmutable() for q in self.qualifiers])


    def combineSelectors(klass, selectorA, op, selectorB):
        selectorB.addCombination(op, selectorA)
        return selectorB


    combineSelectors = classmethod(combineSelectors)


    def addCombination(self, op, other):
        self._addQualifier(CSSSelectorCombinationQualifier(op, other))


    def addHashId(self, hashId):
        self._addQualifier(CSSSelectorHashQualifier(hashId))


    def addClass(self, class_):
        self._addQualifier(CSSSelectorClassQualifier(class_))


    def addAttribute(self, attrName):
        self._addQualifier(CSSSelectorAttributeQualifier(attrName))


    def addAttributeOperation(self, attrName, op, attrValue):
        self._addQualifier(CSSSelectorAttributeQualifier(attrName, op, attrValue))


    def addPseudo(self, name):
        self._addQualifier(CSSSelectorPseudoQualifier(name))


    def addPseudoFunction(self, name, params):
        self._addQualifier(CSSSelectorPseudoQualifier(name, params))


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _addQualifier(self, qualifier):
        if self.qualifiers:
            self.qualifiers.append(qualifier)
        else:
            self.qualifiers = [qualifier]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSImmutableSelector(CSSSelectorBase):
    def __init__(self, completeName='*', qualifiers=()):
        # print completeName, qualifiers
        self.qualifiers = tuple(qualifiers)
        CSSSelectorBase.__init__(self, completeName)
        self._updateHash()


    def fromSelector(klass, selector):
        return klass(selector.completeName, selector.qualifiers)


    fromSelector = classmethod(fromSelector)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ CSS Selector Qualifiers -- see CSSImmutableSelector
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSSelectorQualifierBase(object):
    def isHash(self):
        return False


    def isClass(self):
        return False


    def isAttr(self):
        return False


    def isPseudo(self):
        return False


    def isCombiner(self):
        return False


    def asImmutable(self):
        return self


    def __str__(self):
        return self.asString()


class CSSSelectorHashQualifier(CSSSelectorQualifierBase):
    def __init__(self, hashId):
        self.hashId = hashId


    def isHash(self):
        return True


    def __hash__(self):
        return hash((self.hashId,))


    def asString(self):
        return '#' + self.hashId


    def matches(self, element):
        return element.getIdAttr() == self.hashId


class CSSSelectorClassQualifier(CSSSelectorQualifierBase):
    def __init__(self, classId):
        self.classId = classId


    def isClass(self):
        return True


    def __hash__(self):
        return hash((self.classId,))


    def asString(self):
        return '.' + self.classId


    def matches(self, element):
        #return self.classId in element.getClassAttr().split()
        attrValue = element.domElement.attributes.get('class')
        if attrValue is not None:
            return self.classId in attrValue.value.split()
        return False


class CSSSelectorAttributeQualifier(CSSSelectorQualifierBase):
    name, op, value = None, None, NotImplemented


    def __init__(self, attrName, op=None, attrValue=NotImplemented):
        self.name = attrName
        if op is not self.op:
            self.op = op
        if attrValue is not self.value:
            self.value = attrValue


    def isAttr(self):
        return True


    def __hash__(self):
        return hash((self.name, self.op, self.value))


    def asString(self):
        if self.value is NotImplemented:
            return '[%s]' % (self.name,)
        return '[%s%s%s]' % (self.name, self.op, self.value)


    def matches(self, element):
        if self.op is None:
            return element.getAttr(self.name, NotImplemented) != NotImplemented
        elif self.op == '=':
            return self.value == element.getAttr(self.name, NotImplemented)
        elif self.op == '~=':
            #return self.value in element.getAttr(self.name, '').split()
            attrValue = element.domElement.attributes.get(self.name)
            if attrValue is not None:
                return self.value in attrValue.value.split()
            return False
        elif self.op == '|=':
            #return self.value in element.getAttr(self.name, '').split('-')
            attrValue = element.domElement.attributes.get(self.name)
            if attrValue is not None:
                return self.value in attrValue.value.split('-')
            return False
        raise RuntimeError("Unknown operator %r for %r" % (self.op, self))


class CSSSelectorPseudoQualifier(CSSSelectorQualifierBase):
    def __init__(self, attrName, params=()):
        self.name = attrName
        self.params = tuple(params)


    def isPseudo(self):
        return True


    def __hash__(self):
        return hash((self.name, self.params))


    def asString(self):
        if self.params:
            return ':' + self.name
        else:
            return ':%s(%s)' % (self.name, self.params)


    def matches(self, element):
        return element.inPseudoState(self.name, self.params)


class CSSSelectorCombinationQualifier(CSSSelectorQualifierBase):
    def __init__(self, op, selector):
        self.op = op
        self.selector = selector


    def isCombiner(self):
        return True


    def __hash__(self):
        return hash((self.op, self.selector))


    def asImmutable(self):
        return self.__class__(self.op, self.selector.asImmutable())


    def asString(self):
        return '%s%s' % (self.selector.asString(), self.op)


    def matches(self, element):
        if self.op == ' ':
            if element is not None:
                if element.matchesNode(self.selector.fullName):
                    try:
                        for parent in element.iterXMLParents():
                            [None for qualifier in self.selector.qualifiers if
                             qualifier.matches(parent) and stopIter((None,))]
                    except StopIteration:
                        return True
            return False
        elif self.op == '>':
            if element is not None:
                if element.matchesNode(self.selector.fullName):
                    if self.selector.qualifiers[0].matches(element):
                        return True
            return False
        elif self.op == '+':
            return self.selector.matches(element.getPreviousSibling())

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ CSS Misc
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSTerminalFunction(object):
    def __init__(self, name, params):
        self.name = name
        self.params = params


    def __repr__(self):
        return '<CSS function: %s(%s)>' % (self.name, ', '.join(self.params))


class CSSTerminalOperator(tuple):
    def __new__(klass, *args):
        return tuple.__new__(klass, args)


    def __repr__(self):
        return 'op' + tuple.__repr__(self)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ CSS Objects
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSDeclarations(dict):
    pass


class CSSRuleset(dict):
    def findCSSRulesFor(self, element, attrName):
        ruleResults = [(nodeFilter, declarations) for nodeFilter, declarations in self.iteritems() if
                       (attrName in declarations) and (nodeFilter.matches(element))]
        ruleResults.sort()
        return ruleResults


    def findCSSRuleFor(self, element, attrName):
        # rule is packed in a list to differentiate from "no rule" vs "rule
        # whose value evalutates as False"
        return self.findCSSRulesFor(element, attrName)[-1:]


    def mergeStyles(self, styles):
        " XXX Bugfix for use in PISA "
        for k, v in styles.iteritems():
            if k in self and self[k]:
                self[k] = copy.copy(self[k])
                self[k].update(v)
            else:
                self[k] = v


class CSSInlineRuleset(CSSRuleset, CSSDeclarations):
    def findCSSRulesFor(self, element, attrName):
        if attrName in self:
            return [(CSSInlineSelector(), self)]
        return []


    def findCSSRuleFor(self, *args, **kw):
        # rule is packed in a list to differentiate from "no rule" vs "rule
        # whose value evalutates as False"
        return self.findCSSRulesFor(*args, **kw)[-1:]

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ CSS Builder
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSBuilder(cssParser.CSSBuilderAbstract):
    RulesetFactory = CSSRuleset
    SelectorFactory = CSSMutableSelector
    MediumSetFactory = set
    DeclarationsFactory = CSSDeclarations
    TermFunctionFactory = CSSTerminalFunction
    TermOperatorFactory = CSSTerminalOperator
    xmlnsSynonyms = {}
    mediumSet = None
    trackImportance = True
    charset = None


    def __init__(self, mediumSet=mediumSet, trackImportance=trackImportance):
        self.setMediumSet(mediumSet)
        self.setTrackImportance(trackImportance)


    def isValidMedium(self, mediums):
        if not mediums:
            return False
        if 'all' in mediums:
            return True

        mediums = self.MediumSetFactory(mediums)
        return bool(self.getMediumSet().intersection(mediums))


    def getMediumSet(self):
        return self.mediumSet


    def setMediumSet(self, mediumSet):
        self.mediumSet = self.MediumSetFactory(mediumSet)


    def updateMediumSet(self, mediumSet):
        self.getMediumSet().update(mediumSet)


    def getTrackImportance(self):
        return self.trackImportance


    def setTrackImportance(self, trackImportance=True):
        self.trackImportance = trackImportance


    #~ helpers ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _pushState(self):
        _restoreState = self.__dict__
        self.__dict__ = self.__dict__.copy()
        self._restoreState = _restoreState
        self.namespaces = {}


    def _popState(self):
        self.__dict__ = self._restoreState


    def _declarations(self, declarations, DeclarationsFactory=None):
        DeclarationsFactory = DeclarationsFactory or self.DeclarationsFactory
        if self.trackImportance:
            normal, important = [], []
            for d in declarations:
                if d[-1]:
                    important.append(d[:-1])
                else:
                    normal.append(d[:-1])
            return DeclarationsFactory(normal), DeclarationsFactory(important)
        else:
            return DeclarationsFactory(declarations)


    def _xmlnsGetSynonym(self, uri):
        # Don't forget to substitute our namespace synonyms!
        return self.xmlnsSynonyms.get(uri or None, uri) or None


    #~ css results ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def beginStylesheet(self):
        self._pushState()


    def endStylesheet(self):
        self._popState()


    def stylesheet(self, stylesheetElements, stylesheetImports):
        # XXX Updated for PISA
        if self.trackImportance:
            normal, important = self.RulesetFactory(), self.RulesetFactory()
            for normalStylesheet, importantStylesheet in stylesheetImports:
                normal.mergeStyles(normalStylesheet)
                important.mergeStyles(importantStylesheet)
            for normalStyleElement, importantStyleElement in stylesheetElements:
                normal.mergeStyles(normalStyleElement)
                important.mergeStyles(importantStyleElement)
            return normal, important
        else:
            result = self.RulesetFactory()
            for stylesheet in stylesheetImports:
                result.mergeStyles(stylesheet)

            for styleElement in stylesheetElements:
                result.mergeStyles(styleElement)
            return result


    def beginInline(self):
        self._pushState()


    def endInline(self):
        self._popState()


    def specialRules(self, declarations):
        return cssSpecial.parseSpecialRules(declarations)


    def inline(self, declarations):
        declarations = self.specialRules(declarations)
        return self._declarations(declarations, CSSInlineRuleset)


    def ruleset(self, selectors, declarations):

        # XXX Modified for pisa!
        declarations = self.specialRules(declarations)
        # XXX Modified for pisa!

        if self.trackImportance:
            normalDecl, importantDecl = self._declarations(declarations)
            normal, important = self.RulesetFactory(), self.RulesetFactory()
            for s in selectors:
                s = s.asImmutable()
                if normalDecl:
                    normal[s] = normalDecl
                if importantDecl:
                    important[s] = importantDecl
            return normal, important
        else:
            declarations = self._declarations(declarations)
            result = [(s.asImmutable(), declarations) for s in selectors]
            return self.RulesetFactory(result)


    #~ css namespaces ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def resolveNamespacePrefix(self, nsPrefix, name):
        if nsPrefix == '*':
            return (nsPrefix, '*', name)
        xmlns = self.namespaces.get(nsPrefix, None)
        xmlns = self._xmlnsGetSynonym(xmlns)
        return (nsPrefix, xmlns, name)


    #~ css @ directives ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def atCharset(self, charset):
        self.charset = charset


    def atImport(self, import_, mediums, cssParser):
        if self.isValidMedium(mediums):
            return cssParser.parseExternal(import_)
        return None


    def atNamespace(self, nsprefix, uri):
        self.namespaces[nsprefix] = uri


    def atMedia(self, mediums, ruleset):
        if self.isValidMedium(mediums):
            return ruleset
        return None


    def atPage(self, page, pseudopage, declarations):
        """
        This is overriden by xhtml2pdf.context.pisaCSSBuilder
        """
        return self.ruleset([self.selector('*')], declarations)


    def atFontFace(self, declarations):
        """
        This is overriden by xhtml2pdf.context.pisaCSSBuilder
        """
        return self.ruleset([self.selector('*')], declarations)


    def atIdent(self, atIdent, cssParser, src):
        return src, NotImplemented


    #~ css selectors ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def selector(self, name):
        return self.SelectorFactory(name)


    def combineSelectors(self, selectorA, op, selectorB):
        return self.SelectorFactory.combineSelectors(selectorA, op, selectorB)


    #~ css declarations ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def property(self, name, value, important=False):
        if self.trackImportance:
            return (name, value, important)
        return (name, value)


    def combineTerms(self, termA, op, termB):
        if op in (',', ' '):
            if isinstance(termA, list):
                termA.append(termB)
                return termA
            return [termA, termB]
        elif op is None and termB is None:
            return [termA]
        else:
            if isinstance(termA, list):
                # Bind these "closer" than the list operators -- i.e. work on
                # the (recursively) last element of the list
                termA[-1] = self.combineTerms(termA[-1], op, termB)
                return termA
            return self.TermOperatorFactory(termA, op, termB)


    def termIdent(self, value):
        return value


    def termNumber(self, value, units=None):
        if units:
            return value, units
        return value


    def termRGB(self, value):
        return value


    def termURI(self, value):
        return value


    def termString(self, value):
        return value


    def termUnicodeRange(self, value):
        return value


    def termFunction(self, name, value):
        return self.TermFunctionFactory(name, value)


    def termUnknown(self, src):
        return src, NotImplemented

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ CSS Parser -- finally!
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSParser(cssParser.CSSParser):
    CSSBuilderFactory = CSSBuilder


    def __init__(self, cssBuilder=None, create=True, **kw):
        if not cssBuilder and create:
            assert cssBuilder is None
            cssBuilder = self.createCSSBuilder(**kw)
        cssParser.CSSParser.__init__(self, cssBuilder)


    def createCSSBuilder(self, **kw):
        return self.CSSBuilderFactory(**kw)


    def parseExternal(self, cssResourceName):
        if os.path.isfile(cssResourceName):
            cssFile = file(cssResourceName, 'r')
            return self.parseFile(cssFile, True)
        raise RuntimeError("Cannot resolve external CSS file: \"%s\"" % cssResourceName)


########NEW FILE########
__FILENAME__ = cssDOMElementInterface
#!/usr/bin/env python
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
##~ Copyright (C) 2002-2004  TechGame Networks, LLC.
##~
##~ This library is free software; you can redistribute it and/or
##~ modify it under the terms of the BSD style License as found in the
##~ LICENSE file included with this distribution.
##
##  Modified by Dirk Holtwick <holtwick@web.de>, 2007-2008
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import css

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSDOMElementInterface(css.CSSElementInterfaceAbstract):
    """An implementation of css.CSSElementInterfaceAbstract for xml.dom Element Nodes"""

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Constants / Variables / Etc.
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    style = None

    _pseudoStateHandlerLookup = {
        'first-child':
            lambda self: not bool(self.getPreviousSibling()),
        'not-first-child':
            lambda self: bool(self.getPreviousSibling()),

        'last-child':
            lambda self: not bool(self.getNextSibling()),
        'not-last-child':
            lambda self: bool(self.getNextSibling()),

        'middle-child':
            lambda self: not bool(self.getPreviousSibling()) and not bool(self.getNextSibling()),
        'not-middle-child':
            lambda self: bool(self.getPreviousSibling()) or bool(self.getNextSibling()),

        # XXX 'first-line':

    }

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Definitions
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __init__(self, domElement, cssParser=None):
        self.domElement = domElement
        # print self.domElement.attributes
        if cssParser is not None:
            self.onCSSParserVisit(cssParser)


    def onCSSParserVisit(self, cssParser):
        styleSrc = self.getStyleAttr()
        if styleSrc:
            style = cssParser.parseInline(styleSrc)
            self.setInlineStyle(style)


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def matchesNode(self, namespace_tagName):
        namespace,tagName = namespace_tagName
        if tagName not in ('*', self.domElement.tagName):
            return False
        if namespace in (None, '', '*'):
            # matches any namespace
            return True
        else: # full compare
            return namespace == self.domElement.namespaceURI


    def getAttr(self, name, default=NotImplemented):
        attrValue = self.domElement.attributes.get(name)
        if attrValue is not None:
            return attrValue.value
        else:
            return default


    def getIdAttr(self):
        return self.getAttr('id', '')


    def getClassAttr(self):
        return self.getAttr('class', '')


    def getStyleAttr(self):
        return self.getAttr('style', None)


    def inPseudoState(self, name, params=()):
        handler = self._pseudoStateHandlerLookup.get(name, lambda self: False)
        return handler(self)


    def iterXMLParents(self, includeSelf=False):
        klass = self.__class__
        current = self.domElement
        if not includeSelf:
            current = current.parentNode
        while (current is not None) and (current.nodeType == current.ELEMENT_NODE):
            yield klass(current)
            current = current.parentNode


    def getPreviousSibling(self):
        sibling = self.domElement.previousSibling
        while sibling:
            if sibling.nodeType == sibling.ELEMENT_NODE:
                return sibling
            else:
                sibling = sibling.previousSibling
        return None


    def getNextSibling(self):
        sibling = self.domElement.nextSibling
        while sibling:
            if sibling.nodeType == sibling.ELEMENT_NODE:
                return sibling
            else:
                sibling = sibling.nextSibling
        return None


    def getInlineStyle(self):
        return self.style


    def setInlineStyle(self, style):
        self.style = style


########NEW FILE########
__FILENAME__ = cssParser
#!/usr/bin/env python
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
##~ Copyright (C) 2002-2004  TechGame Networks, LLC.
##~
##~ This library is free software; you can redistribute it and/or
##~ modify it under the terms of the BSD style License as found in the
##~ LICENSE file included with this distribution.
##
##  Modified by Dirk Holtwick <holtwick@web.de>, 2007-2008
##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

"""CSS-2.1 parser.

The CSS 2.1 Specification this parser was derived from can be found at http://www.w3.org/TR/CSS21/

Primary Classes:
    * CSSParser
        Parses CSS source forms into results using a Builder Pattern.  Must
        provide concrete implemenation of CSSBuilderAbstract.

    * CSSBuilderAbstract
        Outlines the interface between CSSParser and it's rule-builder.
        Compose CSSParser with a concrete implementation of the builder to get
        usable results from the CSS parser.

Dependencies:
    python 2.3 (or greater)
    re
"""

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Imports
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

import re
import cssSpecial

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ Definitions
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

def isAtRuleIdent(src, ident):
    return re.match(r'^@' + ident + r'\s*', src)


def stripAtRuleIdent(src):
    return re.sub(r'^@[a-z\-]+\s*', '', src)


class CSSSelectorAbstract(object):
    """Outlines the interface between CSSParser and it's rule-builder for selectors.

    CSSBuilderAbstract.selector and CSSBuilderAbstract.combineSelectors must
    return concrete implementations of this abstract.

    See css.CSSMutableSelector for an example implementation.
    """


    def addHashId(self, hashId):
        raise NotImplementedError('Subclass responsibility')


    def addClass(self, class_):
        raise NotImplementedError('Subclass responsibility')


    def addAttribute(self, attrName):
        raise NotImplementedError('Subclass responsibility')


    def addAttributeOperation(self, attrName, op, attrValue):
        raise NotImplementedError('Subclass responsibility')


    def addPseudo(self, name):
        raise NotImplementedError('Subclass responsibility')


    def addPseudoFunction(self, name, value):
        raise NotImplementedError('Subclass responsibility')


class CSSBuilderAbstract(object):
    """Outlines the interface between CSSParser and it's rule-builder.  Compose
    CSSParser with a concrete implementation of the builder to get usable
    results from the CSS parser.

    See css.CSSBuilder for an example implementation
    """


    def setCharset(self, charset):
        raise NotImplementedError('Subclass responsibility')


    #~ css results ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def beginStylesheet(self):
        raise NotImplementedError('Subclass responsibility')


    def stylesheet(self, elements):
        raise NotImplementedError('Subclass responsibility')


    def endStylesheet(self):
        raise NotImplementedError('Subclass responsibility')


    def beginInline(self):
        raise NotImplementedError('Subclass responsibility')


    def inline(self, declarations):
        raise NotImplementedError('Subclass responsibility')


    def endInline(self):
        raise NotImplementedError('Subclass responsibility')


    def ruleset(self, selectors, declarations):
        raise NotImplementedError('Subclass responsibility')


    #~ css namespaces ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def resolveNamespacePrefix(self, nsPrefix, name):
        raise NotImplementedError('Subclass responsibility')


    #~ css @ directives ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def atCharset(self, charset):
        raise NotImplementedError('Subclass responsibility')


    def atImport(self, import_, mediums, cssParser):
        raise NotImplementedError('Subclass responsibility')


    def atNamespace(self, nsPrefix, uri):
        raise NotImplementedError('Subclass responsibility')


    def atMedia(self, mediums, ruleset):
        raise NotImplementedError('Subclass responsibility')


    def atPage(self, page, pseudopage, declarations):
        raise NotImplementedError('Subclass responsibility')


    def atFontFace(self, declarations):
        raise NotImplementedError('Subclass responsibility')


    def atIdent(self, atIdent, cssParser, src):
        return src, NotImplemented


    #~ css selectors ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def combineSelectors(self, selectorA, combiner, selectorB):
        """Return value must implement CSSSelectorAbstract"""
        raise NotImplementedError('Subclass responsibility')


    def selector(self, name):
        """Return value must implement CSSSelectorAbstract"""
        raise NotImplementedError('Subclass responsibility')


    #~ css declarations ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def property(self, name, value, important=False):
        raise NotImplementedError('Subclass responsibility')


    def combineTerms(self, termA, combiner, termB):
        raise NotImplementedError('Subclass responsibility')


    def termIdent(self, value):
        raise NotImplementedError('Subclass responsibility')


    def termNumber(self, value, units=None):
        raise NotImplementedError('Subclass responsibility')


    def termRGB(self, value):
        raise NotImplementedError('Subclass responsibility')


    def termURI(self, value):
        raise NotImplementedError('Subclass responsibility')


    def termString(self, value):
        raise NotImplementedError('Subclass responsibility')


    def termUnicodeRange(self, value):
        raise NotImplementedError('Subclass responsibility')


    def termFunction(self, name, value):
        raise NotImplementedError('Subclass responsibility')


    def termUnknown(self, src):
        raise NotImplementedError('Subclass responsibility')

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#~ CSS Parser
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSParseError(Exception):
    src = None
    ctxsrc = None
    fullsrc = None
    inline = False
    srcCtxIdx = None
    srcFullIdx = None
    ctxsrcFullIdx = None


    def __init__(self, msg, src, ctxsrc=None):
        Exception.__init__(self, msg)
        self.src = src
        self.ctxsrc = ctxsrc or src
        if self.ctxsrc:
            self.srcCtxIdx = self.ctxsrc.find(self.src)
            if self.srcCtxIdx < 0:
                del self.srcCtxIdx


    def __str__(self):
        if self.ctxsrc:
            return Exception.__str__(self) + ':: (' + repr(self.ctxsrc[:self.srcCtxIdx]) + ', ' + repr(
                self.ctxsrc[self.srcCtxIdx:self.srcCtxIdx + 20]) + ')'
        else:
            return Exception.__str__(self) + ':: ' + repr(self.src[:40])


    def setFullCSSSource(self, fullsrc, inline=False):
        self.fullsrc = fullsrc
        if inline:
            self.inline = inline
        if self.fullsrc:
            self.srcFullIdx = self.fullsrc.find(self.src)
            if self.srcFullIdx < 0:
                del self.srcFullIdx
            self.ctxsrcFullIdx = self.fullsrc.find(self.ctxsrc)
            if self.ctxsrcFullIdx < 0:
                del self.ctxsrcFullIdx

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

class CSSParser(object):
    """CSS-2.1 parser dependent only upon the re module.

    Implemented directly from http://www.w3.org/TR/CSS21/grammar.html
    Tested with some existing CSS stylesheets for portability.

    CSS Parsing API:
        * setCSSBuilder()
            To set your concrete implementation of CSSBuilderAbstract

        * parseFile()
            Use to parse external stylesheets using a file-like object

            >>> cssFile = open('test.css', 'r')
            >>> stylesheets = myCSSParser.parseFile(cssFile)

        * parse()
            Use to parse embedded stylesheets using source string

            >>> cssSrc = '''
                body,body.body {
                    font: 110%, "Times New Roman", Arial, Verdana, Helvetica, serif;
                    background: White;
                    color: Black;
                }
                a {text-decoration: underline;}
            '''
            >>> stylesheets = myCSSParser.parse(cssSrc)

        * parseInline()
            Use to parse inline stylesheets using attribute source string

            >>> style = 'font: 110%, "Times New Roman", Arial, Verdana, Helvetica, serif; background: White; color: Black'
            >>> stylesheets = myCSSParser.parseInline(style)

        * parseAttributes()
            Use to parse attribute string values into inline stylesheets

            >>> stylesheets = myCSSParser.parseAttributes(
                    font='110%, "Times New Roman", Arial, Verdana, Helvetica, serif',
                    background='White',
                    color='Black')

        * parseSingleAttr()
            Use to parse a single string value into a CSS expression

            >>> fontValue = myCSSParser.parseSingleAttr('110%, "Times New Roman", Arial, Verdana, Helvetica, serif')
    """

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Constants / Variables / Etc.
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    ParseError = CSSParseError

    AttributeOperators = ['=', '~=', '|=', '&=', '^=', '!=', '<>']
    SelectorQualifiers = ('#', '.', '[', ':')
    SelectorCombiners = ['+', '>']
    ExpressionOperators = ('/', '+', ',')

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Regular expressions
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    if True: # makes the following code foldable
        _orRule = lambda *args: '|'.join(args)
        _reflags = re.I | re.M | re.U
        i_hex = '[0-9a-fA-F]'
        i_nonascii = u'[\200-\377]'
        i_unicode = '\\\\(?:%s){1,6}\s?' % i_hex
        i_escape = _orRule(i_unicode, u'\\\\[ -~\200-\377]')
        # i_nmstart = _orRule('[A-Za-z_]', i_nonascii, i_escape)
        i_nmstart = _orRule('\-[^0-9]|[A-Za-z_]', i_nonascii,
                            i_escape) # XXX Added hyphen, http://www.w3.org/TR/CSS21/syndata.html#value-def-identifier
        i_nmchar = _orRule('[-0-9A-Za-z_]', i_nonascii, i_escape)
        i_ident = '((?:%s)(?:%s)*)' % (i_nmstart, i_nmchar)
        re_ident = re.compile(i_ident, _reflags)
        # Caution: treats all characters above 0x7f as legal for an identifier.
        i_unicodeid = r'([^\u0000-\u007f]+)'
        re_unicodeid = re.compile(i_unicodeid, _reflags)
        i_element_name = '((?:%s)|\*)' % (i_ident[1:-1],)
        re_element_name = re.compile(i_element_name, _reflags)
        i_namespace_selector = '((?:%s)|\*|)\|(?!=)' % (i_ident[1:-1],)
        re_namespace_selector = re.compile(i_namespace_selector, _reflags)
        i_class = '\\.' + i_ident
        re_class = re.compile(i_class, _reflags)
        i_hash = '#((?:%s)+)' % i_nmchar
        re_hash = re.compile(i_hash, _reflags)
        i_rgbcolor = '(#%s{6}|#%s{3})' % (i_hex, i_hex)
        re_rgbcolor = re.compile(i_rgbcolor, _reflags)
        i_nl = u'\n|\r\n|\r|\f'
        i_escape_nl = u'\\\\(?:%s)' % i_nl
        i_string_content = _orRule(u'[\t !#$%&(-~]', i_escape_nl, i_nonascii, i_escape)
        i_string1 = u'\"((?:%s|\')*)\"' % i_string_content
        i_string2 = u'\'((?:%s|\")*)\'' % i_string_content
        i_string = _orRule(i_string1, i_string2)
        re_string = re.compile(i_string, _reflags)
        i_uri = (u'url\\(\s*(?:(?:%s)|((?:%s)+))\s*\\)'
                 % (i_string, _orRule('[!#$%&*-~]', i_nonascii, i_escape)))
        # XXX For now
        # i_uri = u'(url\\(.*?\\))'
        re_uri = re.compile(i_uri, _reflags)
        i_num = u'(([-+]?[0-9]+(?:\\.[0-9]+)?)|([-+]?\\.[0-9]+))' # XXX Added out paranthesis, because e.g. .5em was not parsed correctly
        re_num = re.compile(i_num, _reflags)
        i_unit = '(%%|%s)?' % i_ident
        re_unit = re.compile(i_unit, _reflags)
        i_function = i_ident + '\\('
        re_function = re.compile(i_function, _reflags)
        i_functionterm = u'[-+]?' + i_function
        re_functionterm = re.compile(i_functionterm, _reflags)
        i_unicoderange1 = "(?:U\\+%s{1,6}-%s{1,6})" % (i_hex, i_hex)
        i_unicoderange2 = "(?:U\\+\?{1,6}|{h}(\?{0,5}|{h}(\?{0,4}|{h}(\?{0,3}|{h}(\?{0,2}|{h}(\??|{h}))))))"
        i_unicoderange = i_unicoderange1 # u'(%s|%s)' % (i_unicoderange1, i_unicoderange2)
        re_unicoderange = re.compile(i_unicoderange, _reflags)

        # i_comment = u'(?:\/\*[^*]*\*+([^/*][^*]*\*+)*\/)|(?://.*)'
        # gabriel: only C convention for comments is allowed in CSS
        i_comment = u'(?:\/\*[^*]*\*+([^/*][^*]*\*+)*\/)'
        re_comment = re.compile(i_comment, _reflags)
        i_important = u'!\s*(important)'
        re_important = re.compile(i_important, _reflags)
        del _orRule

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Public
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def __init__(self, cssBuilder=None):
        self.setCSSBuilder(cssBuilder)


    #~ CSS Builder to delegate to ~~~~~~~~~~~~~~~~~~~~~~~~

    def getCSSBuilder(self):
        """A concrete instance implementing CSSBuilderAbstract"""
        return self._cssBuilder


    def setCSSBuilder(self, cssBuilder):
        """A concrete instance implementing CSSBuilderAbstract"""
        self._cssBuilder = cssBuilder


    cssBuilder = property(getCSSBuilder, setCSSBuilder)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Public CSS Parsing API
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def parseFile(self, srcFile, closeFile=False):
        """Parses CSS file-like objects using the current cssBuilder.
        Use for external stylesheets."""

        try:
            result = self.parse(srcFile.read())
        finally:
            if closeFile:
                srcFile.close()
        return result


    def parse(self, src):
        """Parses CSS string source using the current cssBuilder.
        Use for embedded stylesheets."""

        self.cssBuilder.beginStylesheet()
        try:

            # XXX Some simple preprocessing
            src = cssSpecial.cleanupCSS(src)

            try:
                src, stylesheet = self._parseStylesheet(src)
            except self.ParseError as err:
                err.setFullCSSSource(src)
                raise
        finally:
            self.cssBuilder.endStylesheet()
        return stylesheet


    def parseInline(self, src):
        """Parses CSS inline source string using the current cssBuilder.
        Use to parse a tag's 'sytle'-like attribute."""

        self.cssBuilder.beginInline()
        try:
            try:
                src, properties = self._parseDeclarationGroup(src.strip(), braces=False)
            except self.ParseError as err:
                err.setFullCSSSource(src, inline=True)
                raise

            result = self.cssBuilder.inline(properties)
        finally:
            self.cssBuilder.endInline()
        return result


    def parseAttributes(self, attributes={}, **kwAttributes):
        """Parses CSS attribute source strings, and return as an inline stylesheet.
        Use to parse a tag's highly CSS-based attributes like 'font'.

        See also: parseSingleAttr
        """
        if attributes:
            kwAttributes.update(attributes)

        self.cssBuilder.beginInline()
        try:
            properties = []
            try:
                for propertyName, src in kwAttributes.iteritems():
                    src, property = self._parseDeclarationProperty(src.strip(), propertyName)
                    properties.append(property)

            except self.ParseError as err:
                err.setFullCSSSource(src, inline=True)
                raise

            result = self.cssBuilder.inline(properties)
        finally:
            self.cssBuilder.endInline()
        return result


    def parseSingleAttr(self, attrValue):
        """Parse a single CSS attribute source string, and returns the built CSS expression.
        Use to parse a tag's highly CSS-based attributes like 'font'.

        See also: parseAttributes
        """

        results = self.parseAttributes(temp=attrValue)
        if 'temp' in results[1]:
            return results[1]['temp']
        else:
            return results[0]['temp']


    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #~ Internal _parse methods
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _parseStylesheet(self, src):
        """stylesheet
        : [ CHARSET_SYM S* STRING S* ';' ]?
            [S|CDO|CDC]* [ import [S|CDO|CDC]* ]*
            [ [ ruleset | media | page | font_face ] [S|CDO|CDC]* ]*
        ;
        """
        # Get rid of the comments
        src = self.re_comment.sub(u'', src)

        # [ CHARSET_SYM S* STRING S* ';' ]?
        src = self._parseAtCharset(src)

        # [S|CDO|CDC]*
        src = self._parseSCDOCDC(src)
        #  [ import [S|CDO|CDC]* ]*
        src, stylesheetImports = self._parseAtImports(src)

        # [ namespace [S|CDO|CDC]* ]*
        src = self._parseAtNamespace(src)

        stylesheetElements = []

        # [ [ ruleset | atkeywords ] [S|CDO|CDC]* ]*
        while src: # due to ending with ]*
            if src.startswith('@'):
                # @media, @page, @font-face
                src, atResults = self._parseAtKeyword(src)
                if atResults is not None:
                    stylesheetElements.extend(atResults)
            else:
                # ruleset
                src, ruleset = self._parseRuleset(src)
                stylesheetElements.append(ruleset)

            # [S|CDO|CDC]*
            src = self._parseSCDOCDC(src)

        stylesheet = self.cssBuilder.stylesheet(stylesheetElements, stylesheetImports)
        return src, stylesheet


    def _parseSCDOCDC(self, src):
        """[S|CDO|CDC]*"""
        while 1:
            src = src.lstrip()
            if src.startswith('<!--'):
                src = src[4:]
            elif src.startswith('-->'):
                src = src[3:]
            else:
                break
        return src


    #~ CSS @ directives ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _parseAtCharset(self, src):
        """[ CHARSET_SYM S* STRING S* ';' ]?"""
        if isAtRuleIdent(src, 'charset'):
            src = stripAtRuleIdent(src)
            charset, src = self._getString(src)
            src = src.lstrip()
            if src[:1] != ';':
                raise self.ParseError('@charset expected a terminating \';\'', src, ctxsrc)
            src = src[1:].lstrip()

            self.cssBuilder.atCharset(charset)
        return src


    def _parseAtImports(self, src):
        """[ import [S|CDO|CDC]* ]*"""
        result = []
        while isAtRuleIdent(src, 'import'):
            ctxsrc = src
            src = stripAtRuleIdent(src)

            import_, src = self._getStringOrURI(src)
            if import_ is None:
                raise self.ParseError('Import expecting string or url', src, ctxsrc)

            mediums = []
            medium, src = self._getIdent(src.lstrip())
            while medium is not None:
                mediums.append(medium)
                if src[:1] == ',':
                    src = src[1:].lstrip()
                    medium, src = self._getIdent(src)
                else:
                    break

            # XXX No medium inherits and then "all" is appropriate
            if not mediums:
                mediums = ["all"]

            if src[:1] != ';':
                raise self.ParseError('@import expected a terminating \';\'', src, ctxsrc)
            src = src[1:].lstrip()

            stylesheet = self.cssBuilder.atImport(import_, mediums, self)
            if stylesheet is not None:
                result.append(stylesheet)

            src = self._parseSCDOCDC(src)
        return src, result


    def _parseAtNamespace(self, src):
        """namespace :

        @namespace S* [IDENT S*]? [STRING|URI] S* ';' S*
        """

        src = self._parseSCDOCDC(src)
        while isAtRuleIdent(src, 'namespace'):
            ctxsrc = src
            src = stripAtRuleIdent(src)

            namespace, src = self._getStringOrURI(src)
            if namespace is None:
                nsPrefix, src = self._getIdent(src)
                if nsPrefix is None:
                    raise self.ParseError('@namespace expected an identifier or a URI', src, ctxsrc)
                namespace, src = self._getStringOrURI(src.lstrip())
                if namespace is None:
                    raise self.ParseError('@namespace expected a URI', src, ctxsrc)
            else:
                nsPrefix = None

            src = src.lstrip()
            if src[:1] != ';':
                raise self.ParseError('@namespace expected a terminating \';\'', src, ctxsrc)
            src = src[1:].lstrip()

            self.cssBuilder.atNamespace(nsPrefix, namespace)

            src = self._parseSCDOCDC(src)
        return src


    def _parseAtKeyword(self, src):
        """[media | page | font_face | unknown_keyword]"""
        ctxsrc = src
        if isAtRuleIdent(src, 'media'):
            src, result = self._parseAtMedia(src)
        elif isAtRuleIdent(src, 'page'):
            src, result = self._parseAtPage(src)
        elif isAtRuleIdent(src, 'font-face'):
            src, result = self._parseAtFontFace(src)
        # XXX added @import, was missing!
        elif isAtRuleIdent(src, 'import'):
            src, result = self._parseAtImports(src)
        elif isAtRuleIdent(src, 'frame'):
            src, result = self._parseAtFrame(src)
        elif src.startswith('@'):
            src, result = self._parseAtIdent(src)
        else:
            raise self.ParseError('Unknown state in atKeyword', src, ctxsrc)
        return src, result


    def _parseAtMedia(self, src):
        """media
        : MEDIA_SYM S* medium [ ',' S* medium ]* '{' S* ruleset* '}' S*
        ;
        """
        ctxsrc = src
        src = src[len('@media '):].lstrip()
        mediums = []
        while src and src[0] != '{':
            medium, src = self._getIdent(src)
            if medium is None:
                raise self.ParseError('@media rule expected media identifier', src, ctxsrc)
            # make "and ... {" work
            if medium == u'and':
                # strip up to curly bracket
                pattern = re.compile('.*({.*)')
                match = re.match(pattern, src)
                src = src[match.end()-1:]
                break
            mediums.append(medium)
            if src[0] == ',':
                src = src[1:].lstrip()
            else:
                src = src.lstrip()

        if not src.startswith('{'):
            raise self.ParseError('Ruleset opening \'{\' not found', src, ctxsrc)
        src = src[1:].lstrip()

        stylesheetElements = []
        #while src and not src.startswith('}'):
        #    src, ruleset = self._parseRuleset(src)
        #    stylesheetElements.append(ruleset)
        #    src = src.lstrip()

        # Containing @ where not found and parsed
        while src and not src.startswith('}'):
            if src.startswith('@'):
                # @media, @page, @font-face
                src, atResults = self._parseAtKeyword(src)
                if atResults is not None:
                    stylesheetElements.extend(atResults)
            else:
                # ruleset
                src, ruleset = self._parseRuleset(src)
                stylesheetElements.append(ruleset)
            src = src.lstrip()

        if not src.startswith('}'):
            raise self.ParseError('Ruleset closing \'}\' not found', src, ctxsrc)
        else:
            src = src[1:].lstrip()

        result = self.cssBuilder.atMedia(mediums, stylesheetElements)
        return src, result


    def _parseAtPage(self, src):
        """page
        : PAGE_SYM S* IDENT? pseudo_page? S*
            '{' S* declaration [ ';' S* declaration ]* '}' S*
        ;
        """
        ctxsrc = src
        src = src[len('@page '):].lstrip()
        page, src = self._getIdent(src)
        if src[:1] == ':':
            pseudopage, src = self._getIdent(src[1:])
            page = page + '_' + pseudopage
        else:
            pseudopage = None

        #src, properties = self._parseDeclarationGroup(src.lstrip())

        # Containing @ where not found and parsed
        stylesheetElements = []
        src = src.lstrip()
        properties = []

        # XXX Extended for PDF use
        if not src.startswith('{'):
            raise self.ParseError('Ruleset opening \'{\' not found', src, ctxsrc)
        else:
            src = src[1:].lstrip()

        while src and not src.startswith('}'):
            if src.startswith('@'):
                # @media, @page, @font-face
                src, atResults = self._parseAtKeyword(src)
                if atResults is not None:
                    stylesheetElements.extend(atResults)
            else:
                src, nproperties = self._parseDeclarationGroup(src.lstrip(), braces=False)
                properties += nproperties
            src = src.lstrip()

        result = [self.cssBuilder.atPage(page, pseudopage, properties)]

        return src[1:].lstrip(), result


    def _parseAtFrame(self, src):
        """
        XXX Proprietary for PDF
        """
        ctxsrc = src
        src = src[len('@frame '):].lstrip()
        box, src = self._getIdent(src)
        src, properties = self._parseDeclarationGroup(src.lstrip())
        result = [self.cssBuilder.atFrame(box, properties)]
        return src.lstrip(), result


    def _parseAtFontFace(self, src):
        ctxsrc = src
        src = src[len('@font-face '):].lstrip()
        src, properties = self._parseDeclarationGroup(src)
        result = [self.cssBuilder.atFontFace(properties)]
        return src, result


    def _parseAtIdent(self, src):
        ctxsrc = src
        atIdent, src = self._getIdent(src[1:])
        if atIdent is None:
            raise self.ParseError('At-rule expected an identifier for the rule', src, ctxsrc)

        src, result = self.cssBuilder.atIdent(atIdent, self, src)

        if result is NotImplemented:
            # An at-rule consists of everything up to and including the next semicolon (;) or the next block, whichever comes first

            semiIdx = src.find(';')
            if semiIdx < 0:
                semiIdx = None
            blockIdx = src[:semiIdx].find('{')
            if blockIdx < 0:
                blockIdx = None

            if semiIdx is not None and semiIdx < blockIdx:
                src = src[semiIdx + 1:].lstrip()
            elif blockIdx is None:
                # consume the rest of the content since we didn't find a block or a semicolon
                src = src[-1:-1]
            elif blockIdx is not None:
                # expecing a block...
                src = src[blockIdx:]
                try:
                    # try to parse it as a declarations block
                    src, declarations = self._parseDeclarationGroup(src)
                except self.ParseError:
                    # try to parse it as a stylesheet block
                    src, stylesheet = self._parseStylesheet(src)
            else:
                raise self.ParserError('Unable to ignore @-rule block', src, ctxsrc)

        return src.lstrip(), result


    #~ ruleset - see selector and declaration groups ~~~~

    def _parseRuleset(self, src):
        """ruleset
        : selector [ ',' S* selector ]*
            '{' S* declaration [ ';' S* declaration ]* '}' S*
        ;
        """
        src, selectors = self._parseSelectorGroup(src)
        src, properties = self._parseDeclarationGroup(src.lstrip())
        result = self.cssBuilder.ruleset(selectors, properties)
        return src, result


    #~ selector parsing ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _parseSelectorGroup(self, src):
        selectors = []
        while src[:1] not in ('{', '}', ']', '(', ')', ';', ''):
            src, selector = self._parseSelector(src)
            if selector is None:
                break
            selectors.append(selector)
            if src.startswith(','):
                src = src[1:].lstrip()
        return src, selectors


    def _parseSelector(self, src):
        """selector
        : simple_selector [ combinator simple_selector ]*
        ;
        """
        src, selector = self._parseSimpleSelector(src)
        srcLen = len(src) # XXX
        while src[:1] not in ('', ',', ';', '{', '}', '[', ']', '(', ')'):
            for combiner in self.SelectorCombiners:
                if src.startswith(combiner):
                    src = src[len(combiner):].lstrip()
                    break
            else:
                combiner = ' '
            src, selectorB = self._parseSimpleSelector(src)

            # XXX Fix a bug that occured here e.g. : .1 {...}
            if len(src) >= srcLen:
                src = src[1:]
                while src and (src[:1] not in ('', ',', ';', '{', '}', '[', ']', '(', ')')):
                    src = src[1:]
                return src.lstrip(), None

            selector = self.cssBuilder.combineSelectors(selector, combiner, selectorB)

        return src.lstrip(), selector


    def _parseSimpleSelector(self, src):
        """simple_selector
        : [ namespace_selector ]? element_name? [ HASH | class | attrib | pseudo ]* S*
        ;
        """
        ctxsrc = src.lstrip()
        nsPrefix, src = self._getMatchResult(self.re_namespace_selector, src)
        name, src = self._getMatchResult(self.re_element_name, src)
        if name:
            pass # already *successfully* assigned
        elif src[:1] in self.SelectorQualifiers:
            name = '*'
        else:
            raise self.ParseError('Selector name or qualifier expected', src, ctxsrc)

        name = self.cssBuilder.resolveNamespacePrefix(nsPrefix, name)
        selector = self.cssBuilder.selector(name)
        while src and src[:1] in self.SelectorQualifiers:
            hash_, src = self._getMatchResult(self.re_hash, src)
            if hash_ is not None:
                selector.addHashId(hash_)
                continue

            class_, src = self._getMatchResult(self.re_class, src)
            if class_ is not None:
                selector.addClass(class_)
                continue

            if src.startswith('['):
                src, selector = self._parseSelectorAttribute(src, selector)
            elif src.startswith(':'):
                src, selector = self._parseSelectorPseudo(src, selector)
            else:
                break

        return src.lstrip(), selector


    def _parseSelectorAttribute(self, src, selector):
        """attrib
        : '[' S* [ namespace_selector ]? IDENT S* [ [ '=' | INCLUDES | DASHMATCH ] S*
            [ IDENT | STRING ] S* ]? ']'
        ;
        """
        ctxsrc = src
        if not src.startswith('['):
            raise self.ParseError('Selector Attribute opening \'[\' not found', src, ctxsrc)
        src = src[1:].lstrip()

        nsPrefix, src = self._getMatchResult(self.re_namespace_selector, src)
        attrName, src = self._getIdent(src)

        src = src.lstrip()

        if attrName is None:
            raise self.ParseError('Expected a selector attribute name', src, ctxsrc)
        if nsPrefix is not None:
            attrName = self.cssBuilder.resolveNamespacePrefix(nsPrefix, attrName)

        for op in self.AttributeOperators:
            if src.startswith(op):
                break
        else:
            op = ''
        src = src[len(op):].lstrip()

        if op:
            attrValue, src = self._getIdent(src)
            if attrValue is None:
                attrValue, src = self._getString(src)
                if attrValue is None:
                    raise self.ParseError('Expected a selector attribute value', src, ctxsrc)
        else:
            attrValue = None

        if not src.startswith(']'):
            raise self.ParseError('Selector Attribute closing \']\' not found', src, ctxsrc)
        else:
            src = src[1:]

        if op:
            selector.addAttributeOperation(attrName, op, attrValue)
        else:
            selector.addAttribute(attrName)
        return src, selector


    def _parseSelectorPseudo(self, src, selector):
        """pseudo
        : ':' [ IDENT | function ]
        ;
        """
        ctxsrc = src
        if not src.startswith(':'):
            raise self.ParseError('Selector Pseudo \':\' not found', src, ctxsrc)
        src = re.search('^:{1,2}(.*)', src, re.M | re.S).group(1)

        name, src = self._getIdent(src)
        if not name:
            raise self.ParseError('Selector Pseudo identifier not found', src, ctxsrc)

        if src.startswith('('):
            # function
            src = src[1:].lstrip()
            src, term = self._parseExpression(src, True)
            if not src.startswith(')'):
                raise self.ParseError('Selector Pseudo Function closing \')\' not found', src, ctxsrc)
            src = src[1:]
            selector.addPseudoFunction(name, term)
        else:
            selector.addPseudo(name)

        return src, selector


    #~ declaration and expression parsing ~~~~~~~~~~~~~~~

    def _parseDeclarationGroup(self, src, braces=True):
        ctxsrc = src
        if src.startswith('{'):
            src, braces = src[1:], True
        elif braces:
            raise self.ParseError('Declaration group opening \'{\' not found', src, ctxsrc)

        properties = []
        src = src.lstrip()
        while src[:1] not in ('', ',', '{', '}', '[', ']', '(', ')', '@'): # XXX @?
            src, property = self._parseDeclaration(src)

            # XXX Workaround for styles like "*font: smaller"
            if src.startswith("*"):
                src = "-nothing-" + src[1:]
                continue

            if property is None:
                break
            properties.append(property)
            if src.startswith(';'):
                src = src[1:].lstrip()
            else:
                break

        if braces:
            if not src.startswith('}'):
                raise self.ParseError('Declaration group closing \'}\' not found', src, ctxsrc)
            src = src[1:]

        return src.lstrip(), properties


    def _parseDeclaration(self, src):
        """declaration
        : ident S* ':' S* expr prio?
        | /* empty */
        ;
        """
        # property
        propertyName, src = self._getIdent(src)

        if propertyName is not None:
            src = src.lstrip()
            # S* : S*
            if src[:1] in (':', '='):
                # Note: we are being fairly flexable here...  technically, the
                # ":" is *required*, but in the name of flexibility we
                # suppor a null transition, as well as an "=" transition
                src = src[1:].lstrip()

            src, property = self._parseDeclarationProperty(src, propertyName)
        else:
            property = None

        return src, property


    def _parseDeclarationProperty(self, src, propertyName):
        # expr
        src, expr = self._parseExpression(src)

        # prio?
        important, src = self._getMatchResult(self.re_important, src)
        src = src.lstrip()

        property = self.cssBuilder.property(propertyName, expr, important)
        return src, property


    def _parseExpression(self, src, returnList=False):
        """
        expr
        : term [ operator term ]*
        ;
        """
        src, term = self._parseExpressionTerm(src)
        operator = None
        while src[:1] not in ('', ';', '{', '}', '[', ']', ')'):
            for operator in self.ExpressionOperators:
                if src.startswith(operator):
                    src = src[len(operator):]
                    break
            else:
                operator = ' '
            src, term2 = self._parseExpressionTerm(src.lstrip())
            if term2 is NotImplemented:
                break
            else:
                term = self.cssBuilder.combineTerms(term, operator, term2)

        if operator is None and returnList:
            term = self.cssBuilder.combineTerms(term, None, None)
            return src, term
        else:
            return src, term


    def _parseExpressionTerm(self, src):
        """term
        : unary_operator?
            [ NUMBER S* | PERCENTAGE S* | LENGTH S* | EMS S* | EXS S* | ANGLE S* |
            TIME S* | FREQ S* | function ]
        | STRING S* | IDENT S* | URI S* | RGB S* | UNICODERANGE S* | hexcolor
        ;
        """
        ctxsrc = src

        result, src = self._getMatchResult(self.re_num, src)
        if result is not None:
            units, src = self._getMatchResult(self.re_unit, src)
            term = self.cssBuilder.termNumber(result, units)
            return src.lstrip(), term

        result, src = self._getString(src, self.re_uri)
        if result is not None:
            # XXX URL!!!!
            term = self.cssBuilder.termURI(result)
            return src.lstrip(), term

        result, src = self._getString(src)
        if result is not None:
            term = self.cssBuilder.termString(result)
            return src.lstrip(), term

        result, src = self._getMatchResult(self.re_functionterm, src)
        if result is not None:
            src, params = self._parseExpression(src, True)
            if src[0] != ')':
                raise self.ParseError('Terminal function expression expected closing \')\'', src, ctxsrc)
            src = src[1:].lstrip()
            term = self.cssBuilder.termFunction(result, params)
            return src, term

        result, src = self._getMatchResult(self.re_rgbcolor, src)
        if result is not None:
            term = self.cssBuilder.termRGB(result)
            return src.lstrip(), term

        result, src = self._getMatchResult(self.re_unicoderange, src)
        if result is not None:
            term = self.cssBuilder.termUnicodeRange(result)
            return src.lstrip(), term

        nsPrefix, src = self._getMatchResult(self.re_namespace_selector, src)
        result, src = self._getIdent(src)
        if result is not None:
            if nsPrefix is not None:
                result = self.cssBuilder.resolveNamespacePrefix(nsPrefix, result)
            term = self.cssBuilder.termIdent(result)
            return src.lstrip(), term

        result, src = self._getMatchResult(self.re_unicodeid, src)
        if result is not None:
            term = self.cssBuilder.termIdent(result)
            return src.lstrip(), term

        return self.cssBuilder.termUnknown(src)


    #~ utility methods ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    def _getIdent(self, src, default=None):
        return self._getMatchResult(self.re_ident, src, default)


    def _getString(self, src, rexpression=None, default=None):
        if rexpression is None:
            rexpression = self.re_string
        result = rexpression.match(src)
        if result:
            strres = filter(None, result.groups())
            if strres:
                strres = strres[0]
            else:
                strres = ''
            return strres, src[result.end():]
        else:
            return default, src


    def _getStringOrURI(self, src):
        result, src = self._getString(src, self.re_uri)
        if result is None:
            result, src = self._getString(src)
        return result, src


    def _getMatchResult(self, rexpression, src, default=None, group=1):
        result = rexpression.match(src)
        if result:
            return result.group(group), src[result.end():]
        else:
            return default, src


########NEW FILE########
__FILENAME__ = cssSpecial
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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
# Copyright 2010 Dirk Holtwick, holtwick.it
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


__reversion__ = "$Revision: 20 $"
__author__ = "$Author: holtwick $"
__date__ = "$Date: 2007-10-09 12:58:24 +0200 (Di, 09 Okt 2007) $"

"""
Helper for complex CSS definitons like font, margin, padding and border
Optimized for use with PISA
"""

import types
import logging


log = logging.getLogger("ho.css")


def toList(value):
    if type(value) != types.ListType:
        return [value]
    return value


_styleTable = {
    "normal": "",
    "italic": "",
    "oblique": "",
}

_variantTable = {
    "normal": None,
    "small-caps": None,
}

_weightTable = {
    "light": 300,
    "lighter": 300, # fake relativness for now
    "normal": 400,
    "bold": 700,
    "bolder": 700, # fake relativness for now

    "100": 100,
    "200": 200,
    "300": 300,
    "400": 400,
    "500": 500,
    "600": 600,
    "700": 700,
    "800": 800,
    "900": 900,

    #wx.LIGHT: 300,
    #wx.NORMAL: 400,
    #wx.BOLD: 700,
}

#_absSizeTable = {
#    "xx-small" : 3./5.,
#    "x-small": 3./4.,
#    "small": 8./9.,
#    "medium": 1./1.,
#    "large": 6./5.,
#    "x-large": 3./2.,
#    "xx-large": 2./1.,
#    "xxx-large": 3./1.,
#    "larger": 1.25,      # XXX Not totaly CSS conform:
#    "smaller": 0.75,     # http://www.w3.org/TR/CSS21/fonts.html#propdef-font-size
#    }

_borderStyleTable = {
    "none": 0,
    "hidden": 0,
    "dotted": 1,
    "dashed": 1,
    "solid": 1,
    "double": 1,
    "groove": 1,
    "ridge": 1,
    "inset": 1,
    "outset": 1,
}

'''
_relSizeTable = {
    'pt':
        # pt: absolute point size
        # Note: this is 1/72th of an inch
        (lambda value, pt: value),
    'px':
        # px: pixels, relative to the viewing device
        # Note: approximate at the size of a pt
        (lambda value, pt: value),
    'ex':
        # ex: proportional to the 'x-height' of the parent font
        # Note: can't seem to dervie this value from wx.Font methods,
        # so we'll approximate by calling it 1/2 a pt
        (lambda value, pt: 2 * value),
    'pc':
        # pc: 12:1 pica:point size
        # Note: this is 1/6th of an inch
        (lambda value, pt: 12*value),
    'in':
        # in: 72 inches per point
        (lambda value, pt: 72*value),
    'cm':
        # in: 72 inches per point, 2.54 cm per inch
        (lambda value, pt,_r=72./2.54: _r*value),
    'mm':
        # in: 72 inches per point, 25.4 mm per inch
        (lambda value, pt,_r=72./25.4: _r*value),
    '%':
        # %: percentage of the parent's pointSize
        (lambda value, pt: 0.01 * pt * value),
    'em':
        # em: proportional to the 'font-size' of the parent font
        (lambda value, pt: pt * value),
    }
'''


def getNextPart(parts):
    if parts:
        part = parts.pop(0)
    else:
        part = None
    return part


def isSize(value):
    return value and ((type(value) is types.TupleType) or value == "0")


def splitBorder(parts):
    """
    The order of the elements seems to be of no importance:

    http://www.w3.org/TR/CSS21/box.html#border-shorthand-properties
    """

    width = style = color = None
    copy_parts = parts[:]
    # part = getNextPart(parts)

    if len(parts) > 3:
        log.warn("To many elements for border style %r", parts)

    for part in parts:
        # Width
        if isSize(part):
            width = part
            # part = getNextPart(parts)

        # Style
        elif hasattr(part, 'lower') and part.lower() in _borderStyleTable:
            style = part
            # part = getNextPart(parts)

        # Color
        else:
            color = part

    # log.debug("Border styles: %r -> %r ", copy_parts, (width, style, color))

    return (width, style, color)


def parseSpecialRules(declarations, debug=0):
    # print selectors, declarations
    # CSS MODIFY!
    dd = []

    for d in declarations:

        if debug:
            log.debug("CSS special  IN: %r", d)

        name, parts, last = d
        oparts = parts
        parts = toList(parts)

        # FONT
        if name == "font":
            # [ [ <'font-style'> || <'font-variant'> || <'font-weight'> ]? <'font-size'> [ / <'line-height'> ]? <'font-family'> ] | inherit
            ddlen = len(dd)
            part = getNextPart(parts)
            # Style
            if part and part in _styleTable:
                dd.append(("font-style", part, last))
                part = getNextPart(parts)
                # Variant
            if part and part in _variantTable:
                dd.append(("font-variant", part, last))
                part = getNextPart(parts)
                # Weight
            if part and part in _weightTable:
                dd.append(("font-weight", part, last))
                part = getNextPart(parts)
                # Size and Line Height
            if isinstance(part, tuple) and len(part) == 3:
                fontSize, slash, lineHeight = part
                assert slash == '/'
                dd.append(("font-size", fontSize, last))
                dd.append(("line-height", lineHeight, last))
            else:
                dd.append(("font-size", part, last))
                # Face/ Family
            dd.append(("font-face", parts, last))

        # BACKGROUND
        elif name == "background":
            # [<'background-color'> || <'background-image'> || <'background-repeat'> || <'background-attachment'> || <'background-position'>] | inherit

            # XXX We do not receive url() and parts list, so we go for a dirty work arround
            part = getNextPart(parts) or oparts
            if part:

                if hasattr(part, '__iter__') and (type("." in part) or ("data:" in part)):
                    dd.append(("background-image", part, last))
                else:
                    dd.append(("background-color", part, last))

            if 0:
                part = getNextPart(parts) or oparts
                print ("~", part, parts, oparts, declarations)
                # Color
                if part and (not part.startswith("url")):
                    dd.append(("background-color", part, last))
                    part = getNextPart(parts)
                    # Background
                if part:
                    dd.append(("background-image", part, last))
                    # XXX Incomplete! Error in url()!

        # MARGIN
        elif name == "margin":
            if len(parts) == 1:
                top = bottom = left = right = parts[0]
            elif len(parts) == 2:
                top = bottom = parts[0]
                left = right = parts[1]
            elif len(parts) == 3:
                top = parts[0]
                left = right = parts[1]
                bottom = parts[2]
            elif len(parts) == 4:
                top = parts[0]
                right = parts[1]
                bottom = parts[2]
                left = parts[3]
            else:
                continue
            dd.append(("margin-left", left, last))
            dd.append(("margin-right", right, last))
            dd.append(("margin-top", top, last))
            dd.append(("margin-bottom", bottom, last))

        # PADDING
        elif name == "padding":
            if len(parts) == 1:
                top = bottom = left = right = parts[0]
            elif len(parts) == 2:
                top = bottom = parts[0]
                left = right = parts[1]
            elif len(parts) == 3:
                top = parts[0]
                left = right = parts[1]
                bottom = parts[2]
            elif len(parts) == 4:
                top = parts[0]
                right = parts[1]
                bottom = parts[2]
                left = parts[3]
            else:
                continue
            dd.append(("padding-left", left, last))
            dd.append(("padding-right", right, last))
            dd.append(("padding-top", top, last))
            dd.append(("padding-bottom", bottom, last))

        # BORDER WIDTH
        elif name == "border-width":
            if len(parts) == 1:
                top = bottom = left = right = parts[0]
            elif len(parts) == 2:
                top = bottom = parts[0]
                left = right = parts[1]
            elif len(parts) == 3:
                top = parts[0]
                left = right = parts[1]
                bottom = parts[2]
            elif len(parts) == 4:
                top = parts[0]
                right = parts[1]
                bottom = parts[2]
                left = parts[3]
            else:
                continue
            dd.append(("border-left-width", left, last))
            dd.append(("border-right-width", right, last))
            dd.append(("border-top-width", top, last))
            dd.append(("border-bottom-width", bottom, last))

        # BORDER COLOR
        elif name == "border-color":
            if len(parts) == 1:
                top = bottom = left = right = parts[0]
            elif len(parts) == 2:
                top = bottom = parts[0]
                left = right = parts[1]
            elif len(parts) == 3:
                top = parts[0]
                left = right = parts[1]
                bottom = parts[2]
            elif len(parts) == 4:
                top = parts[0]
                right = parts[1]
                bottom = parts[2]
                left = parts[3]
            else:
                continue
            dd.append(("border-left-color", left, last))
            dd.append(("border-right-color", right, last))
            dd.append(("border-top-color", top, last))
            dd.append(("border-bottom-color", bottom, last))

        # BORDER STYLE
        elif name == "border-style":
            if len(parts) == 1:
                top = bottom = left = right = parts[0]
            elif len(parts) == 2:
                top = bottom = parts[0]
                left = right = parts[1]
            elif len(parts) == 3:
                top = parts[0]
                left = right = parts[1]
                bottom = parts[2]
            elif len(parts) == 4:
                top = parts[0]
                right = parts[1]
                bottom = parts[2]
                left = parts[3]
            else:
                continue
            dd.append(("border-left-style", left, last))
            dd.append(("border-right-style", right, last))
            dd.append(("border-top-style", top, last))
            dd.append(("border-bottom-style", bottom, last))

        # BORDER
        elif name == "border":
            width, style, color = splitBorder(parts)
            if width is not None:
                dd.append(("border-left-width", width, last))
                dd.append(("border-right-width", width, last))
                dd.append(("border-top-width", width, last))
                dd.append(("border-bottom-width", width, last))
            if style is not None:
                dd.append(("border-left-style", style, last))
                dd.append(("border-right-style", style, last))
                dd.append(("border-top-style", style, last))
                dd.append(("border-bottom-style", style, last))
            if color is not None:
                dd.append(("border-left-color", color, last))
                dd.append(("border-right-color", color, last))
                dd.append(("border-top-color", color, last))
                dd.append(("border-bottom-color", color, last))

        # BORDER TOP, BOTTOM, LEFT, RIGHT
        elif name in ("border-top", "border-bottom", "border-left", "border-right"):
            direction = name[7:]
            width, style, color = splitBorder(parts)
            # print direction, width
            if width is not None:
                dd.append(("border-" + direction + "-width", width, last))
            if style is not None:
                dd.append(("border-" + direction + "-style", style, last))
            if color is not None:
                dd.append(("border-" + direction + "-color", color, last))

        # REST
        else:
            dd.append(d)

    if debug and dd:
        log.debug("CSS special OUT:\n%s", "\n".join([repr(d) for d in dd]))

    if 0: #declarations!=dd:
        print ("###", declarations)
        print ("#->", dd)
        # CSS MODIFY! END
    return dd


#import re
#_rxhttp = re.compile(r"url\([\'\"]?http\:\/\/[^\/]", re.IGNORECASE|re.DOTALL)

def cleanupCSS(src):
    # src = _rxhttp.sub('url(', src)
    return src

########NEW FILE########
__FILENAME__ = wsgi
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

import xhtml2pdf.pisa as pisa
import StringIO

import logging


log = logging.getLogger("xhtml2pdf.wsgi")


class Filter(object):
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('SCRIPT_NAME', '')
        path_info = environ.get('PATH_INFO', '')
        sent = []
        written_response = StringIO.StringIO()

        def replacement_start_response(status, headers, exc_info=None):
            if not self.should_filter(status, headers):
                return start_response(status, headers, exc_info)
            else:
                sent[:] = [status, headers, exc_info]
                return written_response.write

        app_iter = self.app(environ, replacement_start_response)
        if not sent:
            return app_iter
        status, headers, exc_info = sent
        try:
            for chunk in app_iter:
                written_response.write(chunk)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        body = written_response.getvalue()
        status, headers, body = self.filter(
            script_name, path_info, environ, status, headers, body)
        start_response(status, headers, exc_info)
        return [body]

    def should_filter(self, status, headers):
        print (headers)

    def filter(self, status, headers, body):
        raise NotImplementedError


class HTMLFilter(Filter):
    def should_filter(self, status, headers):
        if not status.startswith('200'):
            return False
        for name, value in headers:
            if name.lower() == 'content-type':
                return value.startswith('text/html')
        return False


class PisaMiddleware(HTMLFilter):
    def filter(self, script_name, path_info, environ, status, headers, body):
        topdf = environ.get("pisa.topdf", "")
        if topdf:
            dst = StringIO.StringIO()
            pisa.CreatePDF(body, dst, show_error_as_pdf=True)
            headers = [
                ("content-type", "application/pdf"),
                ("content-disposition", "attachment; filename=" + topdf)
            ]
            body = dst.getvalue()
        return status, headers, body

########NEW FILE########
__FILENAME__ = xhtml2pdf_reportlab
# -*- coding: utf-8 -*-

# Copyright 2010 Dirk Holtwick, holtwick.it
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

from hashlib import md5
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import flatten, open_for_read, getStringIO, \
    LazyImageReader, haveImages
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate, IndexingFlowable
from reportlab.platypus.flowables import Flowable, CondPageBreak, \
    KeepInFrame, ParagraphAndImage
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.tables import Table, TableStyle
from xhtml2pdf.reportlab_paragraph import Paragraph
from xhtml2pdf.util import getUID, getBorderStyle
from types import StringType, TupleType, ListType, IntType
import StringIO
import cgi
import copy
import logging
import reportlab.pdfbase.pdfform as pdfform
import sys


try:
    import PIL.Image as PILImage
except:
    try:
        import Image as PILImage
    except:
        PILImage = None

log = logging.getLogger("xhtml2pdf")

MAX_IMAGE_RATIO = 0.95


class PTCycle(list):
    def __init__(self):
        self._restart = 0
        self._idx = 0
        list.__init__(self)

    def cyclicIterator(self):
        while 1:
            yield self[self._idx]
            self._idx += 1
            if self._idx >= len(self):
                self._idx = self._restart


class PmlMaxHeightMixIn:
    def setMaxHeight(self, availHeight):
        self.availHeightValue = availHeight
        if availHeight < 70000:
            if hasattr(self, "canv"):
                if not hasattr(self.canv, "maxAvailHeightValue"):
                    self.canv.maxAvailHeightValue = 0
                self.availHeightValue = self.canv.maxAvailHeightValue = max(
                    availHeight,
                    self.canv.maxAvailHeightValue)
        else:
            self.availHeightValue = availHeight
        if not hasattr(self, "availHeightValue"):
            self.availHeightValue = 0
        return self.availHeightValue

    def getMaxHeight(self):
        if not hasattr(self, "availHeightValue"):
            return 0
        return self.availHeightValue


class PmlBaseDoc(BaseDocTemplate):
    """
    We use our own document template to get access to the canvas
    and set some informations once.
    """

    def beforePage(self):

        # Tricky way to set producer, because of not real privateness in Python
        info = "pisa HTML to PDF <http://www.htmltopdf.org>"
        self.canv._doc.info.producer = info

        '''
        # Convert to ASCII because there is a Bug in Reportlab not
        # supporting other than ASCII. Send to list on 23.1.2007

        author = toString(self.pml_data.get("author", "")).encode("ascii","ignore")
        subject = toString(self.pml_data.get("subject", "")).encode("ascii","ignore")
        title = toString(self.pml_data.get("title", "")).encode("ascii","ignore")
        # print repr((author,title,subject))

        self.canv.setAuthor(author)
        self.canv.setSubject(subject)
        self.canv.setTitle(title)

        if self.pml_data.get("fullscreen", 0):
            self.canv.showFullScreen0()

        if self.pml_data.get("showoutline", 0):
            self.canv.showOutline()

        if self.pml_data.get("duration", None) is not None:
            self.canv.setPageDuration(self.pml_data["duration"])
        '''

    def afterFlowable(self, flowable):
        # Does the flowable contain fragments?
        if getattr(flowable, "outline", False):
            self.notify('TOCEntry', (
                flowable.outlineLevel,
                cgi.escape(copy.deepcopy(flowable.text), 1),
                self.page))

    def handle_nextPageTemplate(self, pt):
        '''
        if pt has also templates for even and odd page convert it to list
        '''
        has_left_template = self._has_template_for_name(pt + '_left')
        has_right_template = self._has_template_for_name(pt + '_right')

        if has_left_template and has_right_template:
            pt = [pt + '_left', pt + '_right']

        '''On endPage change to the page template with name or index pt'''
        if type(pt) is StringType:
            if hasattr(self, '_nextPageTemplateCycle'):
                del self._nextPageTemplateCycle
            for t in self.pageTemplates:
                if t.id == pt:
                    self._nextPageTemplateIndex = self.pageTemplates.index(t)
                    return
            raise ValueError("can't find template('%s')" % pt)
        elif type(pt) is IntType:
            if hasattr(self, '_nextPageTemplateCycle'):
                del self._nextPageTemplateCycle
            self._nextPageTemplateIndex = pt
        elif type(pt) in (ListType, TupleType):
            #used for alternating left/right pages
            #collect the refs to the template objects, complain if any are bad
            c = PTCycle()
            for ptn in pt:
            #special case name used to short circuit the iteration
                if ptn == '*':
                    c._restart = len(c)
                    continue
                for t in self.pageTemplates:
                    if t.id == ptn.strip():
                        c.append(t)
                        break
            if not c:
                raise ValueError("No valid page templates in cycle")
            elif c._restart > len(c):
                raise ValueError("Invalid cycle restart position")

            #ensure we start on the first one$
            self._nextPageTemplateCycle = c.cyclicIterator()
        else:
            raise TypeError("Argument pt should be string or integer or list")

    def _has_template_for_name(self, name):
        for template in self.pageTemplates:
            if template.id == name.strip():
                return True
        return False


class PmlPageTemplate(PageTemplate):
    PORTRAIT = 'portrait'
    LANDSCAPE = 'landscape'
    # by default portrait
    pageorientation = PORTRAIT

    def __init__(self, **kw):
        self.pisaStaticList = []
        self.pisaBackgroundList = []
        self.pisaBackground = None
        PageTemplate.__init__(self, **kw)
        self._page_count = 0
        self._first_flow = True

    def isFirstFlow(self, canvas):
        if self._first_flow:
            if canvas.getPageNumber() <= self._page_count:
                self._first_flow = False
            else:
                self._page_count = canvas.getPageNumber()
                canvas._doctemplate._page_count = canvas.getPageNumber()
        return self._first_flow

    def isPortrait(self):
        return self.pageorientation == self.PORTRAIT

    def isLandscape(self):
        return self.pageorientation == self.LANDSCAPE

    def beforeDrawPage(self, canvas, doc):
        canvas.saveState()
        try:

            # Background
            pisaBackground = None
            if (self.isFirstFlow(canvas)
                and hasattr(self, "pisaBackground")
                and self.pisaBackground
                and (not self.pisaBackground.notFound())):

                # Is image not PDF
                if self.pisaBackground.mimetype.startswith("image/"):

                    try:
                        img = PmlImageReader(StringIO.StringIO(self.pisaBackground.getData()))
                        iw, ih = img.getSize()
                        pw, ph = canvas._pagesize

                        width = pw  # min(iw, pw) # max
                        wfactor = float(width) / iw
                        height = ph  # min(ih, ph) # max
                        hfactor = float(height) / ih
                        factor_min = min(wfactor, hfactor)

                        if self.isPortrait():
                            w = iw * factor_min
                            h = ih * factor_min
                            canvas.drawImage(img, 0, ph - h, w, h)
                        elif self.isLandscape():
                            factor_max = max(wfactor, hfactor)
                            w = ih * factor_max
                            h = iw * factor_min
                            canvas.drawImage(img, 0, 0, w, h)
                    except:
                        log.exception("Draw background")

                # PDF!
                else:
                    pisaBackground = self.pisaBackground

            if pisaBackground:
                self.pisaBackgroundList.append(pisaBackground)

            def pageNumbering(objList):
                for obj in flatten(objList):
                    if isinstance(obj, PmlParagraph):
                        for frag in obj.frags:
                            if frag.pageNumber:
                                frag.text = str(pagenumber)
                            elif frag.pageCount:
                                frag.text = str(canvas._doctemplate._page_count)

                    elif isinstance(obj, PmlTable):
                        # Flatten the cells ([[1,2], [3,4]] becomes [1,2,3,4])
                        flat_cells = [item for sublist in obj._cellvalues for item in sublist]
                        pageNumbering(flat_cells)

            try:

                # Paint static frames
                pagenumber = canvas.getPageNumber()
                for frame in self.pisaStaticList:
                    frame = copy.deepcopy(frame)
                    story = frame.pisaStaticStory
                    pageNumbering(story)

                    frame.addFromList(story, canvas)

            except Exception:  # TODO: Kill this!
                log.debug("PmlPageTemplate", exc_info=1)
        finally:
            canvas.restoreState()


_ctr = 1


class PmlImageReader(object):  # TODO We need a factory here, returning either a class for java or a class for PIL
    """
    Wraps up either PIL or Java to get data from bitmaps
    """
    _cache = {}

    def __init__(self, fileName):
        if isinstance(fileName, PmlImageReader):
            self.__dict__ = fileName.__dict__   # borgize
            return
            #start wih lots of null private fields, to be populated by
        #the relevant engine.
        self.fileName = fileName
        self._image = None
        self._width = None
        self._height = None
        self._transparent = None
        self._data = None
        imageReaderFlags = 0
        if PILImage and isinstance(fileName, PILImage.Image):
            self._image = fileName
            self.fp = getattr(fileName, 'fp', None)
            try:
                self.fileName = self._image.fileName
            except AttributeError:
                self.fileName = 'PILIMAGE_%d' % id(self)
        else:
            try:
                self.fp = open_for_read(fileName, 'b')
                if isinstance(self.fp, StringIO.StringIO().__class__):
                    imageReaderFlags = 0  # avoid messing with already internal files
                if imageReaderFlags > 0:  # interning
                    data = self.fp.read()
                    if imageReaderFlags & 2:  # autoclose
                        try:
                            self.fp.close()
                        except:
                            pass
                    if imageReaderFlags & 4:  # cache the data
                        if not self._cache:
                            from rl_config import register_reset
                            register_reset(self._cache.clear)

                        data = self._cache.setdefault(md5(data).digest(), data)
                    self.fp = getStringIO(data)
                elif imageReaderFlags == - 1 and isinstance(fileName, (str, unicode)):
                    #try Ralf Schmitt's re-opening technique of avoiding too many open files
                    self.fp.close()
                    del self.fp  # will become a property in the next statement
                    self.__class__ = LazyImageReader
                if haveImages:
                    #detect which library we are using and open the image
                    if not self._image:
                        self._image = self._read_image(self.fp)
                    if getattr(self._image, 'format', None) == 'JPEG':
                        self.jpeg_fh = self._jpeg_fh
                else:
                    from reportlab.pdfbase.pdfutils import readJPEGInfo

                    try:
                        self._width, self._height, c = readJPEGInfo(self.fp)
                    except:
                        raise RuntimeError('Imaging Library not available, unable to import bitmaps only jpegs')
                    self.jpeg_fh = self._jpeg_fh
                    self._data = self.fp.read()
                    self._dataA = None
                    self.fp.seek(0)
            except:  # TODO: Kill the catch-all
                et, ev, tb = sys.exc_info()
                if hasattr(ev, 'args'):
                    a = str(ev.args[- 1]) + (' fileName=%r' % fileName)
                    ev.args = ev.args[: - 1] + (a,)
                    raise et, ev, tb
                else:
                    raise

    def _read_image(self, fp):
        if sys.platform[0:4] == 'java':
            from javax.imageio import ImageIO
            from java.io import ByteArrayInputStream
            input_stream = ByteArrayInputStream(fp.read())
            return ImageIO.read(input_stream)
        elif PILImage:
            return PILImage.open(fp)

    def _jpeg_fh(self):
        fp = self.fp
        fp.seek(0)
        return fp

    def jpeg_fh(self):
        return None

    def getSize(self):
        if self._width is None or self._height is None:
            if sys.platform[0:4] == 'java':
                self._width = self._image.getWidth()
                self._height = self._image.getHeight()
            else:
                self._width, self._height = self._image.size
        return self._width, self._height

    def getRGBData(self):
        "Return byte array of RGB data as string"
        if self._data is None:
            self._dataA = None
            if sys.platform[0:4] == 'java':
                import jarray  # TODO: Move to top.
                from java.awt.image import PixelGrabber

                width, height = self.getSize()
                buffer = jarray.zeros(width * height, 'i')
                pg = PixelGrabber(self._image, 0, 0, width, height, buffer, 0, width)
                pg.grabPixels()
                # there must be a way to do this with a cast not a byte-level loop,
                # I just haven't found it yet...
                pixels = []
                a = pixels.append
                for rgb in buffer:
                    a(chr((rgb >> 16) & 0xff))
                    a(chr((rgb >> 8) & 0xff))
                    a(chr(rgb & 0xff))
                self._data = ''.join(pixels)
                self.mode = 'RGB'
            else:
                im = self._image
                mode = self.mode = im.mode
                if mode == 'RGBA':
                    im.load()
                    self._dataA = PmlImageReader(im.split()[3])
                    im = im.convert('RGB')
                    self.mode = 'RGB'
                elif mode not in ('L', 'RGB', 'CMYK'):
                    im = im.convert('RGB')
                    self.mode = 'RGB'
                if hasattr(im, 'tobytes'):
                    self._data = im.tobytes()
                else:
                    # PIL compatibility
                    self._data = im.tostring()
        return self._data

    def getImageData(self):
        width, height = self.getSize()
        return width, height, self.getRGBData()

    def getTransparent(self):
        if sys.platform[0:4] == 'java':
            return None
        elif "transparency" in self._image.info:
            transparency = self._image.info["transparency"] * 3
            palette = self._image.palette
            if hasattr(palette, 'palette'):
                palette = palette.palette
            elif hasattr(palette, 'data'):
                palette = palette.data
            else:
                return None

            # 8-bit PNGs could give an empty string as transparency value, so
            # we have to be careful here.
            try:
                return map(ord, palette[transparency:transparency + 3])
            except:
                return None
        else:
            return None

    def __str__(self):
        try:
            fn = self.fileName.read()
            if not fn:
                fn = id(self)
            return "PmlImageObject_%s" % hash(fn)
        except:
            fn = self.fileName
            if not fn:
                fn = id(self)
            return fn


class PmlImage(Flowable, PmlMaxHeightMixIn):

    def __init__(self, data, width=None, height=None, mask="auto", mimetype=None, **kw):
        self.kw = kw
        self.hAlign = 'CENTER'
        self._mask = mask
        self._imgdata = data
        # print "###", repr(data)
        self.mimetype = mimetype
        img = self.getImage()
        if img:
            self.imageWidth, self.imageHeight = img.getSize()
        self.drawWidth = width or self.imageWidth
        self.drawHeight = height or self.imageHeight

    def wrap(self, availWidth, availHeight):
        " This can be called more than once! Do not overwrite important data like drawWidth "
        availHeight = self.setMaxHeight(availHeight)
        # print "image wrap", id(self), availWidth, availHeight, self.drawWidth, self.drawHeight
        width = min(self.drawWidth, availWidth)
        wfactor = float(width) / self.drawWidth
        height = min(self.drawHeight, availHeight * MAX_IMAGE_RATIO)
        hfactor = float(height) / self.drawHeight
        factor = min(wfactor, hfactor)
        self.dWidth = self.drawWidth * factor
        self.dHeight = self.drawHeight * factor
        # print "imgage result", factor, self.dWidth, self.dHeight
        return self.dWidth, self.dHeight

    def getImage(self):
        img = PmlImageReader(StringIO.StringIO(self._imgdata))
        return img

    def draw(self):
        img = self.getImage()
        self.canv.drawImage(
            img,
            0, 0,
            self.dWidth,
            self.dHeight,
            mask=self._mask)

    def identity(self, maxLen=None):
        r = Flowable.identity(self, maxLen)
        return r


class PmlParagraphAndImage(ParagraphAndImage, PmlMaxHeightMixIn):
    def wrap(self, availWidth, availHeight):
        self.I.canv = self.canv
        result = ParagraphAndImage.wrap(self, availWidth, availHeight)
        del self.I.canv
        return result

    def split(self, availWidth, availHeight):
        # print "# split", id(self)
        if not hasattr(self, "wI"):
            self.wI, self.hI = self.I.wrap(availWidth, availHeight)  # drawWidth, self.I.drawHeight
        return ParagraphAndImage.split(self, availWidth, availHeight)


class PmlParagraph(Paragraph, PmlMaxHeightMixIn):
    def _calcImageMaxSizes(self, availWidth, availHeight):
        self.hasImages = False
        for frag in self.frags:
            if hasattr(frag, "cbDefn") and frag.cbDefn.kind == "img":
                img = frag.cbDefn
                if img.width > 0 and img.height > 0:
                    self.hasImages = True
                    width = min(img.width, availWidth)
                    wfactor = float(width) / img.width
                    height = min(img.height, availHeight * MAX_IMAGE_RATIO)  # XXX 99% because 100% do not work...
                    hfactor = float(height) / img.height
                    factor = min(wfactor, hfactor)
                    img.height *= factor
                    img.width *= factor

    def wrap(self, availWidth, availHeight):

        availHeight = self.setMaxHeight(availHeight)

        style = self.style

        self.deltaWidth = style.paddingLeft + style.paddingRight + style.borderLeftWidth + style.borderRightWidth
        self.deltaHeight = style.paddingTop + style.paddingBottom + style.borderTopWidth + style.borderBottomWidth

        # reduce the available width & height by the padding so the wrapping
        # will use the correct size
        availWidth -= self.deltaWidth
        availHeight -= self.deltaHeight

        # Modify maxium image sizes
        self._calcImageMaxSizes(availWidth, availHeight)

        # call the base class to do wrapping and calculate the size
        Paragraph.wrap(self, availWidth, availHeight)

        #self.height = max(1, self.height)
        #self.width = max(1, self.width)

        # increase the calculated size by the padding
        self.width = self.width + self.deltaWidth
        self.height = self.height + self.deltaHeight

        return self.width, self.height

    def split(self, availWidth, availHeight):

        if len(self.frags) <= 0:
            return []

        #the split information is all inside self.blPara
        if not hasattr(self, 'deltaWidth'):
            self.wrap(availWidth, availHeight)

        availWidth -= self.deltaWidth
        availHeight -= self.deltaHeight

        return Paragraph.split(self, availWidth, availHeight)

    def draw(self):

        # Create outline
        if getattr(self, "outline", False):

            # Check level and add all levels
            last = getattr(self.canv, "outlineLast", - 1) + 1
            while last < self.outlineLevel:
                # print "(OUTLINE",  last, self.text
                key = getUID()
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(
                    self.text,
                    key,
                    last,
                    not self.outlineOpen)
                last += 1
            self.canv.outlineLast = self.outlineLevel

            key = getUID()

            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(
                self.text,
                key,
                self.outlineLevel,
                not self.outlineOpen)
            last += 1

        # Draw the background and borders here before passing control on to
        # ReportLab. This is because ReportLab can't handle the individual
        # components of the border independently. This will also let us
        # support more border styles eventually.
        canvas = self.canv
        style = self.style
        bg = style.backColor
        leftIndent = style.leftIndent
        bp = 0  # style.borderPadding

        x = leftIndent - bp
        y = - bp
        w = self.width - (leftIndent + style.rightIndent) + 2 * bp
        h = self.height + 2 * bp

        if bg:
            # draw a filled rectangle (with no stroke) using bg color
            canvas.saveState()
            canvas.setFillColor(bg)
            canvas.rect(x, y, w, h, fill=1, stroke=0)
            canvas.restoreState()

        # we need to hide the bg color (if any) so Paragraph won't try to draw it again
        style.backColor = None

        # offset the origin to compensate for the padding
        canvas.saveState()
        canvas.translate(
            (style.paddingLeft + style.borderLeftWidth),
            -1 * (style.paddingTop + style.borderTopWidth))  # + (style.leading / 4)))

        # Call the base class draw method to finish up
        Paragraph.draw(self)
        canvas.restoreState()

        # Reset color because we need it again if we run 2-PASS like we
        # do when using TOC
        style.backColor = bg

        canvas.saveState()

        def _drawBorderLine(bstyle, width, color, x1, y1, x2, y2):
            # We need width and border style to be able to draw a border
            if width and getBorderStyle(bstyle):
                # If no color for border is given, the text color is used (like defined by W3C)
                if color is None:
                    color = style.textColor
                    # print "Border", bstyle, width, color
                if color is not None:
                    canvas.setStrokeColor(color)
                    canvas.setLineWidth(width)
                    canvas.line(x1, y1, x2, y2)

        _drawBorderLine(style.borderLeftStyle,
                        style.borderLeftWidth,
                        style.borderLeftColor,
                        x, y, x, y + h)
        _drawBorderLine(style.borderRightStyle,
                        style.borderRightWidth,
                        style.borderRightColor,
                        x + w, y, x + w, y + h)
        _drawBorderLine(style.borderTopStyle,
                        style.borderTopWidth,
                        style.borderTopColor,
                        x, y + h, x + w, y + h)
        _drawBorderLine(style.borderBottomStyle,
                        style.borderBottomWidth,
                        style.borderBottomColor,
                        x, y, x + w, y)

        canvas.restoreState()


class PmlKeepInFrame(KeepInFrame, PmlMaxHeightMixIn):
    def wrap(self, availWidth, availHeight):
        availWidth = max(availWidth, 1.0)
        availHeight = max(availHeight, 1.0)
        self.maxWidth = availWidth
        self.maxHeight = self.setMaxHeight(availHeight)
        return KeepInFrame.wrap(self, availWidth, availHeight)


class PmlTable(Table, PmlMaxHeightMixIn):
    def _normWidth(self, w, maxw):
        """
        Helper for calculating percentages
        """
        if type(w) == type(""):
            w = ((maxw / 100.0) * float(w[: - 1]))
        elif (w is None) or (w == "*"):
            w = maxw
        return min(w, maxw)

    def _listCellGeom(self, V, w, s, W=None, H=None, aH=72000):
        # print "#", self.availHeightValue
        if aH == 72000:
            aH = self.getMaxHeight() or aH
        return Table._listCellGeom(self, V, w, s, W=W, H=H, aH=aH)

    def wrap(self, availWidth, availHeight):

        self.setMaxHeight(availHeight)

        # Strange bug, sometime the totalWidth is not set !?
        try:
            self.totalWidth
        except:
            self.totalWidth = availWidth

        # Prepare values
        totalWidth = self._normWidth(self.totalWidth, availWidth)
        remainingWidth = totalWidth
        remainingCols = 0
        newColWidths = self._colWidths

        # Calculate widths that are fix
        # IMPORTANT!!! We can not substitute the private value
        # self._colWidths therefore we have to modify list in place
        for i, colWidth in enumerate(newColWidths):
            if (colWidth is not None) or (colWidth == '*'):
                colWidth = self._normWidth(colWidth, totalWidth)
                remainingWidth -= colWidth
            else:
                remainingCols += 1
                colWidth = None
            newColWidths[i] = colWidth

        # Distribute remaining space
        minCellWidth = totalWidth * 0.01
        if remainingCols > 0:
            for i, colWidth in enumerate(newColWidths):
                if colWidth is None:
                    newColWidths[i] = max(minCellWidth, remainingWidth / remainingCols)  # - 0.1

        # Bigger than totalWidth? Lets reduce the fix entries propotionally

        if sum(newColWidths) > totalWidth:
            quotient = totalWidth / sum(newColWidths)
            for i in range(len(newColWidths)):
                newColWidths[i] = newColWidths[i] * quotient

        # To avoid rounding errors adjust one col with the difference
        diff = sum(newColWidths) - totalWidth
        if diff > 0:
            newColWidths[0] -= diff

        return Table.wrap(self, availWidth, availHeight)


class PmlPageCount(IndexingFlowable):
    def __init__(self):
        IndexingFlowable.__init__(self)
        self.second_round = False

    def isSatisfied(self):
        s = self.second_round
        self.second_round = True
        return s

    def drawOn(self, canvas, x, y, _sW=0):
        pass


class PmlTableOfContents(TableOfContents):
    def wrap(self, availWidth, availHeight):
        """
        All table properties should be known by now.
        """

        widths = (availWidth - self.rightColumnWidth,
                  self.rightColumnWidth)

        # makes an internal table which does all the work.
        # we draw the LAST RUN's entries!  If there are
        # none, we make some dummy data to keep the table
        # from complaining
        if len(self._lastEntries) == 0:
            _tempEntries = [(0, 'Placeholder for table of contents', 0)]
        else:
            _tempEntries = self._lastEntries

        lastMargin = 0
        tableData = []
        tableStyle = [
            ('VALIGN', (0, 0), (- 1, - 1), 'TOP'),
            ('LEFTPADDING', (0, 0), (- 1, - 1), 0),
            ('RIGHTPADDING', (0, 0), (- 1, - 1), 0),
            ('TOPPADDING', (0, 0), (- 1, - 1), 0),
            ('BOTTOMPADDING', (0, 0), (- 1, - 1), 0),
        ]
        for i, entry in enumerate(_tempEntries):
            level, text, pageNum = entry[:3]
            leftColStyle = self.levelStyles[level]
            if i:  # Not for first element
                tableStyle.append((
                    'TOPPADDING',
                    (0, i), (- 1, i),
                    max(lastMargin, leftColStyle.spaceBefore)))
                # print leftColStyle.leftIndent
            lastMargin = leftColStyle.spaceAfter
            #right col style is right aligned
            rightColStyle = ParagraphStyle(name='leftColLevel%d' % level,
                                           parent=leftColStyle,
                                           leftIndent=0,
                                           alignment=TA_RIGHT)
            leftPara = Paragraph(text, leftColStyle)
            rightPara = Paragraph(str(pageNum), rightColStyle)
            tableData.append([leftPara, rightPara])

        self._table = Table(
            tableData,
            colWidths=widths,
            style=TableStyle(tableStyle))

        self.width, self.height = self._table.wrapOn(self.canv, availWidth, availHeight)
        return self.width, self.height


class PmlRightPageBreak(CondPageBreak):
    def __init__(self):
        pass

    def wrap(self, availWidth, availHeight):
        if not self.canv.getPageNumber() % 2:
            self.width = availWidth
            self.height = availHeight
            return availWidth, availHeight
        self.width = self.height = 0
        return 0, 0


class PmlLeftPageBreak(CondPageBreak):
    def __init__(self):
        pass

    def wrap(self, availWidth, availHeight):
        if self.canv.getPageNumber() % 2:
            self.width = availWidth
            self.height = availHeight
            return availWidth, availHeight
        self.width = self.height = 0
        return 0, 0

# --- Pdf Form


class PmlInput(Flowable):
    def __init__(self, name, type="text", width=10, height=10, default="", options=[]):
        self.width = width
        self.height = height
        self.type = type
        self.name = name
        self.default = default
        self.options = options

    def wrap(self, *args):
        return self.width, self.height

    def draw(self):
        c = self.canv

        c.saveState()
        c.setFont("Helvetica", 10)
        if self.type == "text":
            pdfform.textFieldRelative(c, self.name, 0, 0, self.width, self.height)
            c.rect(0, 0, self.width, self.height)
        elif self.type == "radio":
            c.rect(0, 0, self.width, self.height)
        elif self.type == "checkbox":
            if self.default:
                pdfform.buttonFieldRelative(c, self.name, "Yes", 0, 0)
            else:
                pdfform.buttonFieldRelative(c, self.name, "Off", 0, 0)
            c.rect(0, 0, self.width, self.height)
        elif self.type == "select":
            pdfform.selectFieldRelative(c, self.name, self.default, self.options, 0, 0, self.width, self.height)
            c.rect(0, 0, self.width, self.height)

        c.restoreState()

########NEW FILE########
