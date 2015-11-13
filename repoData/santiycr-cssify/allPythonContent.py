__FILENAME__ = cssify
#!/usr/bin/python

import re
import sys
from optparse import OptionParser

sub_regexes = {
    "tag": "([a-zA-Z][a-zA-Z0-9]{0,10}|\*)",
    "attribute": "[.a-zA-Z_:][-\w:.]*(\(\))?)",
    "value": "\s*[\w/:][-/\w\s,:;.]*"
}

validation_re = (
    "(?P<node>"
      "("
        "^id\([\"\']?(?P<idvalue>%(value)s)[\"\']?\)" # special case! id(idValue)
      "|"
        "(?P<nav>//?)(?P<tag>%(tag)s)" # //div
        "(\[("
          "(?P<matched>(?P<mattr>@?%(attribute)s=[\"\'](?P<mvalue>%(value)s))[\"\']" # [@id="bleh"] and [text()="meh"]
        "|"
          "(?P<contained>contains\((?P<cattr>@?%(attribute)s,\s*[\"\'](?P<cvalue>%(value)s)[\"\']\))" # [contains(text(), "bleh")] or [contains(@id, "bleh")]
        ")\])?"
        "(\[(?P<nth>\d)\])?"
      ")"
    ")" % sub_regexes
)

prog = re.compile(validation_re)


class XpathException(Exception):
    pass


def cssify(xpath):
    """
    Get your XPATHs translated to css automatically! (don't go to crazy on what
    you want to translate, this script is smart but won't do your breakfast).
    """

    css = ""
    position = 0

    while position < len(xpath):
        node = prog.match(xpath[position:])
        if node is None:
            raise XpathException("Invalid or unsupported Xpath: %s" % xpath)
        log("node found: %s" % node)
        match = node.groupdict()
        log("broke node down to: %s" % match)

        if position != 0:
            nav = " " if match['nav'] == "//" else " > "
        else:
            nav = ""

        tag = "" if match['tag'] == "*" else match['tag'] or ""

        if match['idvalue']:
            attr = "#%s" % match['idvalue'].replace(" ", "#")
        elif match['matched']:
            if match['mattr'] == "@id":
                attr = "#%s" % match['mvalue'].replace(" ", "#")
            elif match['mattr'] == "@class":
                attr = ".%s" % match['mvalue'].replace(" ", ".")
            elif match['mattr'] in ["text()", "."]:
                attr = ":contains(^%s$)" % match['mvalue']
            elif match['mattr']:
                if match["mvalue"].find(" ") != -1:
                    match["mvalue"] = "\"%s\"" % match["mvalue"]
                attr = "[%s=%s]" % (match['mattr'].replace("@", ""),
                                    match['mvalue'])
        elif match['contained']:
            if match['cattr'].startswith("@"):
                attr = "[%s*=%s]" % (match['cattr'].replace("@", ""),
                                     match['cvalue'])
            elif match['cattr'] == "text()":
                attr = ":contains(%s)" % match['cvalue']
        else:
            attr = ""

        if match['nth']:
            nth = ":nth-of-type(%s)" % match['nth']
        else:
            nth = ""

        node_css = nav + tag + attr + nth

        log("final node css: %s" % node_css)

        css += node_css
        position += node.end()
    else:
        css = css.strip()
        return css

if __name__ == "__main__":
    usage = "usage: %prog [options] XPATH"
    parser = OptionParser(usage)
    parser.add_option("-v", "--verbose",
                      action="store_true", dest="verbose", default=False,
                      help="print status messages to stdout")

    (options, args) = parser.parse_args()

    if options.verbose:
        def log(msg):
            print "> %s" % msg
    else:
        def log(msg):
            pass

    if len(args) != 1:
        parser.error("incorrect number of arguments")
    try:
        print cssify(args[0])
    except XpathException, e:
        print e
        sys.exit(1)
else:
    def log(msg):
        pass

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
import webapp2
from cssify import cssify, XpathException
import json


class MainHandler(webapp2.RequestHandler):
    def post(self):
        xpath = self.request.get('xpath')
        if xpath:
            self.response.headers['Content-Type'] = 'application/json'
            try:
                css = cssify(xpath)
            except XpathException, e:
                self.response.out.write(json.dumps({'status': 'fail',
                                                    'response': str(e)}))
            else:
                self.response.out.write(json.dumps({'status': 'pass',
                                                    'response': css}))
        else:
            self.response.out.write("Send your xpath via POST under the xpath param")

    def get(self):
        self.response.out.write("Send your xpath via POST under the xpath param")


app = webapp2.WSGIApplication([('/cssify', MainHandler)])

########NEW FILE########
__FILENAME__ = test_cssify
#!/usr/bin/env python

from test_data import SUPPORTED, UNSUPPORTED
import os
import sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)
import cssify
import unittest


class CssifyTest(unittest.TestCase):
    def test_supported(self):
        for path, cssified in SUPPORTED:
            self.assertEqual(cssify.cssify(path), cssified)

    def test_unsupported(self):
        for path in UNSUPPORTED:
            self.assertRaises(cssify.XpathException, cssify.cssify, (path))

########NEW FILE########
__FILENAME__ = test_cssify_web
#!/usr/bin/python

import os
import sys
import new
from random import randint
import base64
import json
import httplib
import unittest
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

from test_data import SUPPORTED, UNSUPPORTED


class CssifyWebTest(unittest.TestCase):
    __test__ = False

    def setUp(self):
        self.caps['name'] = 'Testing cssify'
        if (os.environ.get('TRAVIS') and
            os.environ.get('HAS_JOSH_K_SEAL_OF_APPROVAL')):
            self.caps['tunnel-identifier'] = os.environ['TRAVIS_JOB_NUMBER']
            self.caps['build'] = os.environ['TRAVIS_BUILD_NUMBER']
            self.caps['tags'] = [os.environ['TRAVIS_PYTHON_VERSION'], 'CI']
        self.url = 'http://localhost:8080/'

        self.username = os.environ['SAUCE_USERNAME']
        self.key = os.environ['SAUCE_ACCESS_KEY']
        hub_url = "%s:%s@ondemand.saucelabs.com:80" % (self.username, self.key)
        self.driver = webdriver.Remote(desired_capabilities=self.caps,
                                       command_executor="http://%s/wd/hub" % hub_url)
        self.jobid = self.driver.session_id
        print "Sauce Labs job: https://saucelabs.com/jobs/%s" % self.jobid
        self.driver.implicitly_wait(30)

    def report_test_result(self):
        base64string = base64.encodestring('%s:%s'
                                           % (self.username, self.key))[:-1]
        result = json.dumps({'passed': sys.exc_info() == (None, None, None)})
        connection = httplib.HTTPConnection("saucelabs.com")
        connection.request('PUT',
                           '/rest/v1/%s/jobs/%s' % (self.username, self.jobid),
                           result,
                           headers={"Authorization": "Basic %s" % base64string})
        result = connection.getresponse()
        return result.status == 200

    def test_supported_cssify(self):
        for path, cssified in SUPPORTED:
            self.driver.get(self.url)
            xpath = self.driver.find_element_by_id('xpath')
            xpath.send_keys(path)
            xpath.submit()
            css = WebDriverWait(self.driver, 30).until(
                lambda driver: driver.find_element_by_id("css"))
            self.assertEqual(css.get_attribute("value"), cssified)

    def test_unsupported_cssify(self):
        for path in UNSUPPORTED:
            self.driver.get(self.url)
            self.assertTrue("cssify" in self.driver.title)
            xpath = self.driver.find_element_by_id('xpath')
            xpath.send_keys(path)
            xpath.submit()
            fail = WebDriverWait(self.driver, 30).until(
                lambda driver: driver.find_element_by_class_name("fail"))
            self.assertEqual("Invalid or unsupported Xpath: %s" % path,
                             fail.text)

    def tearDown(self):
        self.driver.quit()
        self.report_test_result()


PLATFORMS = [
    {'browserName': 'firefox',
     'version': '19',
     'platform': 'LINUX',
     },
    {'browserName': 'firefox',
     'version': '19',
     'platform': 'XP',
     },
    {'browserName': 'chrome',
     'platform': 'LINUX',
     },
    {'browserName': 'chrome',
     'platform': 'XP',
     },
    {'browserName': 'internet explorer',
     'version': '10',
     'platform': 'WIN8',
     },
    {'browserName': 'internet explorer',
     'version': '9',
     'platform': 'VISTA',
     },
    {'browserName': 'internet explorer',
     'version': '8',
     'platform': 'XP',
     },
]

classes = {}
for platform in PLATFORMS:
    d = dict(CssifyWebTest.__dict__)
    name = "%s_%s_%s_%s" % (CssifyWebTest.__name__,
                            platform['browserName'],
                            platform.get('platform', 'ANY'),
                            randint(0, 999))
    name = name.replace(" ", "").replace(".", "")
    d.update({'__test__': True,
              'caps': platform,
              })
    classes[name] = new.classobj(name, (CssifyWebTest,), d)

globals().update(classes)

########NEW FILE########
__FILENAME__ = test_data
#!/usr/bin/python

SUPPORTED = [
    ('//a', 'a'),
    ('//a[2]', 'a:nth-of-type(2)'),
    ('/html/body/h1', 'html > body > h1'),
    ('//a[@id="myId"]', 'a#myId'),
    ("//a[@id='myId']", 'a#myId'),
    ('//a[@id="myId"][4]', 'a#myId:nth-of-type(4)'),
    ('//*[@id="myId"]', '#myId'),
    ('id(myId)', '#myId'),
    ('id("myId")/a', '#myId > a'),
    ('//a[@class="myClass"]', 'a.myClass'),
    ('//*[@class="myClass"]', '.myClass'),
    ('//a[@class="multiple classes"]', 'a.multiple.classes'),
    ('//a[@href="bleh"]', 'a[href=bleh]'),
    ('//a[@href="bleh bar"]', 'a[href="bleh bar"]'),
    ('//a[@href="/bleh"]', 'a[href=/bleh]'),
    ('//a[@class="class-bleh"]', 'a.class-bleh'),
    ('//a[.="my text"]', 'a:contains(^my text$)'),
    ('//a[text()="my text"]', 'a:contains(^my text$)'),
    ('//a[contains(@id, "bleh")]', 'a[id*=bleh]'),
    ('//a[contains(text(), "bleh")]', 'a:contains(bleh)'),
    ('//div[@id="myId"]/span[@class="myClass"]//a[contains(text(), "bleh")]//img',
     'div#myId > span.myClass a:contains(bleh) img'),
]

UNSUPPORTED = [
    'fail',
    'a[[]]',
    '(//a)[2]',
]

########NEW FILE########
