__FILENAME__ = cli
import sys
import argparse

from lettuce.bin import main as lettuce_main
from lettuce import world
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

BROWSER_CHOICES = [browser.lower()
                   for browser in DesiredCapabilities.__dict__.keys()
                   if not browser.startswith('_')]
BROWSER_CHOICES.append('zope.testbrowser')
BROWSER_CHOICES.sort()
DEFAULT_BROWSER = 'firefox'


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(prog="Salad", description='BDD browswer-automation made tasty.')

    parser.add_argument('--browser', default=DEFAULT_BROWSER,
                        metavar='BROWSER', choices=BROWSER_CHOICES,
                        help=('Browser to use. Options: %s Default is %s.' %
                              (BROWSER_CHOICES, DEFAULT_BROWSER)))
    parser.add_argument('--remote-url',
                        help='Selenium server url for remote browsers')
    parser.add_argument('args', nargs=argparse.REMAINDER)

    parsed_args = parser.parse_args()
    world.drivers = [parsed_args.browser]
    world.remote_url = parsed_args.remote_url
    lettuce_main(args=parsed_args.args)

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = salad_steps
# Imports and SALAD_PATH just for testing within salad.
from os.path import abspath, join, dirname
from sys import path

SALAD_ROOT = abspath(join(dirname(__file__), "../", "../"))
path.insert(0, SALAD_ROOT)

from salad.steps.everything import *
from salad.tests import TEST_SERVER_PORT


@step(r'visit the salad test url "(.*)"')
def go_to_the_salad_test_url(step, url):
    try:
        go_to_the_url(step, "http://localhost:%s/%s" % (TEST_SERVER_PORT, url))
    except:
        go_to_the_url(step, "http://localhost:%s/%s" % (TEST_SERVER_PORT, url))

########NEW FILE########
__FILENAME__ = salad_terrains
import time
from os import remove
from os.path import abspath, join, dirname
from subprocess import Popen
from sys import path

# Imports and SALAD_PATH just for testing within salad.
SALAD_ROOT = abspath(join(dirname(__file__), "../", "../"))
path.insert(0, SALAD_ROOT)

from lettuce import before, world, after
from salad.tests import TEST_SERVER_PORT
from salad.terrains.everything import *
from salad.logger import logger


@before.all
def setup_subprocesses():
    world.subprocesses = []


@before.all
def setup_test_server():
    file_server_command = "python -m SimpleHTTPServer %s" % (TEST_SERVER_PORT)
    test_dir = abspath(join(SALAD_ROOT, "salad", "tests", "html"))
    world.silent_output = file('/dev/null', 'a+')
    world.tempfile = file('/dev/null', 'a+')

    world.subprocesses.append(Popen(file_server_command,
                                    shell=True,
                                    cwd=test_dir,
                                    stderr=world.silent_output,
                                    stdout=world.silent_output
                                ))
    time.sleep(3)  # Wait for server to spin up


@after.all
def teardown_test_server(total):
    world.silent_output.close()
    for s in world.subprocesses:
        try:
            s.terminate()
        except:
            try:
                s.kill()
            except OSError:
                # Ignore an exception for process already killed.
                pass


@before.all
def create_tempfile():
    world.tempfile = file('/tmp/temp_lettuce_test', 'a+')
    world.tempfile.close()


@after.all
def remove_tempfile(total):
    remove("/tmp/temp_lettuce_test")

########NEW FILE########
__FILENAME__ = logger
import logging

logger = logging.getLogger("salad")
# logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
# ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

########NEW FILE########
__FILENAME__ = alerts
from lettuce import step, world
from salad.tests.util import assert_with_negate


def _get_alert_or_none():
    try:
        alert = world.browser.get_alert()
    except:
        alert = None
    return alert


@step(r'should( not)? see an alert$')
def should_see_alert(step, negate):
    alert = _get_alert_or_none()
    assert_with_negate(alert is not None, negate)
    if alert:
        alert.accept()


@step(r'should( not)? see an alert (?:with the text|that says) "(.*)"')
def should_see_alert_with_text(step, negate, text):
    alert = _get_alert_or_none()
    assert_with_negate(alert is not None and alert.text == text, negate)
    if alert:
        alert.accept()


@step(r'should( not)? see a prompt.?$')
def should_see_prompt(step, negate):
    world.prompt = _get_alert_or_none()
    assert_with_negate(world.prompt is not None, negate)
    if world.prompt:
        world.prompt.accept()


@step(r'should( not)? see a prompt (?:with the text|that says) "(.*)"')
def should_see_prompt_with_text(step, negate, text):
    world.prompt = _get_alert_or_none()
    assert_with_negate(world.prompt is not None and world.prompt.text == text, negate)
    if world.prompt:
        world.prompt.accept()


@step(r'cancel the prompt')
def cancel_prompt(step):
    if not hasattr(world, "prompt") or not world.prompt:
        world.prompt = _get_alert_or_none()
    # for some reason, world.prompt.dismiss() doesn't work.
    world.prompt._alert.dismiss()


@step(r'enter "(.*)" into the prompt')
def enter_into_the_prompt(step, text):
    if not hasattr(world, "prompt") or not world.prompt:
        world.prompt = _get_alert_or_none()

    world.prompt.fill_with(text)
    world.prompt.accept()

########NEW FILE########
__FILENAME__ = browsers
from lettuce import step, world
from salad.terrains.browser import setup_browser

# Choose which browser to use


@step(r'am using (.*)')
def using_alternative_browser(step, browser_name):
    driver = browser_name.lower().replace(' ', '')
    if driver == 'zope':
        driver = 'zope.testbrowser'
    world.browsers.append(setup_browser(driver))
    world.browser = world.browsers[-1]

########NEW FILE########
__FILENAME__ = elements
from lettuce import step, world
from salad.tests.util import assert_equals_with_negate, assert_with_negate, parsed_negator
from salad.steps.browser.finders import ELEMENT_FINDERS, ELEMENT_THING_STRING, _get_element
from splinter.exceptions import ElementDoesNotExist

# Find and verify that elements exist, have the expected content and attributes (text, classes, ids)


@step(r'should( not)? see "(.*)" (?:somewhere|anywhere) in (?:the|this) page')
def should_see_in_the_page(step, negate, text):
    assert_with_negate(text in world.browser.html, negate)


@step(r'should( not)? see (?:the|a) link (?:called|with the text) "(.*)"')
def should_see_a_link_called(step, negate, text):
    assert_with_negate(len(world.browser.find_link_by_text(text)) > 0, negate)


@step(r'should( not)? see (?:the|a) link to "(.*)"')
def should_see_a_link_to(step, negate, link):
    assert_with_negate(len(world.browser.find_link_by_href(link)) > 0, negate)

for finder_string, finder_function in ELEMENT_FINDERS.iteritems():
    def _visible_generator(finder_string, finder_function):
        @step(r'should( not)? see (?:the|a|an)( first)?( last)? %s %s' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, negate, first, last, find_pattern):
            try:
                _get_element(finder_function, first, last, find_pattern, expect_not_to_find=True)
            except ElementDoesNotExist:
                assert parsed_negator(negate)

        return _this_step

    globals()["form_visible_%s" % (finder_function,)] = _visible_generator(finder_string, finder_function)

    def _contains_generator(finder_string, finder_function):
        @step(r'should( not)? see that the( first)?( last)? %s %s contains? "(.*)"' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, negate, first, last, find_pattern, content):
            ele = _get_element(finder_function, first, last, find_pattern)
            assert_with_negate(content in ele.text, negate)

        return _this_step

    globals()["form_contains_%s" % (finder_function,)] = _contains_generator(finder_string, finder_function)

    def _is_exactly_generator(finder_string, finder_function):
        @step(r'should( not)? see that the( first)?( last)? %s %s (?:is|contains) exactly "(.*)"' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, negate, first, last, find_pattern, content):
            ele = _get_element(finder_function, first, last, find_pattern)
            assert_equals_with_negate(ele.text, content, negate)

        return _this_step

    globals()["form_exactly_%s" % (finder_function,)] = _is_exactly_generator(finder_string, finder_function)

    def _attribute_value_generator(finder_string, finder_function):
        @step(r'should( not)? see that the( first)?( last)? %s %s has (?:an|the) attribute (?:of|named|called) "(.*)" with(?: the)? value "(.*)"' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, negate, first, last, find_pattern, attr_name, attr_value):
            ele = _get_element(finder_function, first, last, find_pattern)
            assert_equals_with_negate("%s" % ele[attr_name], attr_value, negate)

        return _this_step

    globals()["form_attribute_value_%s" % (finder_function,)] = _attribute_value_generator(finder_string, finder_function)

    def _attribute_generator(finder_string, finder_function):
        @step(r'should( not)? see that the( first)?( last)? %s %s has (?:an|the) attribute (?:of|named|called) "(\w*)"$' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, negate, first, last, find_pattern, attr_name):
            ele = _get_element(finder_function, first, last, find_pattern)
            assert_with_negate(ele[attr_name] != None, negate)

        return _this_step

    globals()["form_attribute_%s" % (finder_function,)] = _attribute_generator(finder_string, finder_function)

########NEW FILE########
__FILENAME__ = finders
from lettuce import world
from salad.logger import logger
from splinter.exceptions import ElementDoesNotExist

ELEMENT_FINDERS = {
    'named "(.*)"': "find_by_name",
    'with(?: the)? id "(.*)"': "find_by_id",
    'with(?: the)? css selector "(.*)"': "find_by_css",
    'with(?: the)? value (.*)': "find_by_value",
}

LINK_FINDERS = {
    'to "(.*)"': "find_link_by_href",
    'to a url that contains "(.*)"': "find_link_by_partial_href",
    'with(?: the)? text "(.*)"': "find_link_by_text",
    'with text that contains "(.*)"': "find_link_by_partial_text",
}

ELEMENT_THING_STRING = "(?:element|thing|field|textarea|radio button|button|checkbox|label)"
LINK_THING_STRING = "link"


def _get_element(finder_function, first, last, pattern, expect_not_to_find=False, leave_in_list=False):

    ele = world.browser.__getattribute__(finder_function)(pattern)

    try:
        if first:
            ele = ele.first
        if last:
            ele = ele.last

        if not "WebDriverElement" in "%s" % type(ele):
            if len(ele) > 1:
                logger.warn("More than one element found when looking for %s for %s.  Using the first one. " % (finder_function, pattern))

            if not leave_in_list:
                ele = ele.first

    except ElementDoesNotExist:
            if not expect_not_to_find:
                logger.error("Element not found: %s for %s" % (finder_function, pattern))
            raise ElementDoesNotExist

    world.current_element = ele
    return ele


def _convert_pattern_to_css(finder_function, first, last, find_pattern, tag=""):
    pattern = ""
    if finder_function == "find_by_name":
        pattern += "%s[name='%s']" % (tag, find_pattern, )
    elif finder_function == "find_by_id":
        pattern += "#%s" % (find_pattern, )
    elif finder_function == "find_by_css":
        pattern += "%s" % (find_pattern, )
    elif finder_function == "find_by_value":
        pattern += "%s[value='%s']" % (tag, find_pattern, )  # makes no sense, but consistent.
    else:
        raise Exception("Unknown pattern.")

    if first:
        pattern += ":first"

    if last:
        pattern += ":last"

    return pattern

########NEW FILE########
__FILENAME__ = forms
from lettuce import step, world
from splinter.driver.webdriver import TypeIterator
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.errorhandler import StaleElementReferenceException
from salad.steps.browser.finders import ELEMENT_FINDERS, ELEMENT_THING_STRING, _get_element, _convert_pattern_to_css
from salad.tests.util import assert_equals_with_negate

# What's happening here? We're generating steps for every possible permuation of the element finder

for finder_string, finder_function in ELEMENT_FINDERS.iteritems():

    def _fill_generator(finder_string, finder_function):
        @step(r'fill in the( first)?( last)? %s %s with "(.*)"' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, first, last, find_pattern, text):
            ele = _get_element(finder_function, first, last, find_pattern)
            try:
                ele.value = text
            except:
                ele._control.value = text

        return _this_step

    globals()["form_fill_%s" % (finder_function,)] = _fill_generator(finder_string, finder_function)

    def _type_generator(finder_string, finder_function):
        @step(r'(slowly )?type "(.*)" into the( first)?( last)? %s %s' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, slowly, text, first, last, find_pattern):
            css = _convert_pattern_to_css(finder_function, first, last, find_pattern)

            driver_ele = world.browser.driver.find_element_by_css_selector(css)
            slowly = False
            if slowly and slowly != "":
                TypeIterator(driver_ele, text)
            else:
                driver_ele.send_keys(text)

        return _this_step

    globals()["form_type_%s" % (finder_function,)] = _type_generator(finder_string, finder_function)

    def _attach_generator(finder_string, finder_function):
        @step(r'attach "(.*)" onto the( first)?( last)? %s %s' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, file_name, first, last, find_pattern):
            ele = _get_element(finder_function, first, last, find_pattern)
            try:
                ele.value = file_name
            except:  # Zope
                ele._control.value = file_name

        return _this_step

    globals()["form_attach_%s" % (finder_function,)] = _attach_generator(finder_string, finder_function)

    def _select_generator(finder_string, finder_function):
        @step(r'select the option (named|with the value)? "(.*)" (?:from|in) the( first)?( last)? %s %s' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, named_or_with_value, field_value, first, last, find_pattern):
            css = _convert_pattern_to_css(finder_function, first, last, find_pattern, tag="select")

            if named_or_with_value == "with the value":
                css += " option[value='%s']" % (field_value,)
                ele = world.browser.find_by_css(css).first
            else:
                ele = world.browser.find_option_by_text(field_value)

            ele.click()

        return _this_step

    globals()["form_select_%s" % (finder_function,)] = _select_generator(finder_string, finder_function)

    def _focus_generator(finder_string, finder_function):
        @step(r'focus on the( first)?( last)? %s %s' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, first, last, find_pattern):
            ele = _get_element(finder_function, first, last, find_pattern)
            ele.focus()

        return _this_step

    globals()["form_focus_%s" % (finder_function,)] = _focus_generator(finder_string, finder_function)

    def _blur_generator(finder_string, finder_function):
        @step(r'(?:blur|move) from the( first)?( last)? %s %s' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, first, last, find_pattern):
            ele = _get_element(finder_function, first, last, find_pattern)
            ele.blur()

        return _this_step

    globals()["form_blur_%s" % (finder_function,)] = _blur_generator(finder_string, finder_function)

    def _value_generator(finder_string, finder_function):
        @step(r'(?:should see that the)? value of the( first)?( last)? %s %s is( not)? "(.*)"' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, first, last, find_pattern, negate, value):
            ele = _get_element(finder_function, first, last, find_pattern)
            assert_equals_with_negate(ele.value, value, negate)

        return _this_step

    globals()["form_value_%s" % (finder_function,)] = _value_generator(finder_string, finder_function)

    def _key_generator(finder_string, finder_function):
        @step(r'hit the (.*) key in the ( first)?( last)? %s %s' % (ELEMENT_THING_STRING, finder_string))
        def _this_step(step, first, last, find_pattern):
            key = transform_key_string(key_string)
            ele = _get_element(finder_function, first, last, find_pattern)
            ele.type(key)

        return _this_step

    globals()["form_key_%s" % (finder_function,)] = _key_generator(finder_string, finder_function)


@step(r'hit the (.*) key')
def hit_key(step, key_string):
    key = transform_key_string(key_string)
    try:
        world.browser.driver.switch_to_active_element().send_keys(key)
    except StaleElementReferenceException:
        world.browser.find_by_css("body").type(key)

def transform_key_string(key_string):
    key_string = key_string.upper().replace(' ', '_')
    if key_string == 'BACKSPACE':
        key_string = 'BACK_SPACE'
    elif key_string == 'SPACEBAR':
        key_string = 'SPACE'
    key = Keys.__getattribute__(Keys, key_string)
    return key

########NEW FILE########
__FILENAME__ = javascript
from lettuce import step, world
from salad.tests.util import assert_equals_with_negate
from salad.logger import logger

# Execute JS and verify results


@step(r'run the javascript "(.*)"')
def run_the_javascript(step, script):
    try:
        world.browser.execute_script(script)
    except NotImplementedError:
        logger.info("Attempted to run javascript in a javascript-disabled browser. Moving along.")


@step(r'should( not)? see that running the javascript "(.*)" returns "(.*)"')
def evaluate_the_javascript(step, negate, script, value):
    try:
        assert_equals_with_negate("%s" % world.browser.evaluate_script(script), value, negate)
    except NotImplementedError:
        logger.info("Attempted to run javascript in a javascript-disabled browser. Moving along.")

########NEW FILE########
__FILENAME__ = mouse
from lettuce import step
from salad.steps.browser.finders import ELEMENT_FINDERS, LINK_FINDERS, ELEMENT_THING_STRING, LINK_THING_STRING, _get_element


# Click on things, mouse over, move the mouse around.

# General syntax:
# <action> the (first|last) <thing> <find clause>
#
# <action> can be:
# click on
# mouse over / mouseover
# mouse out / mouseout
# (double click / double-click / doubleclick) on
# (right click / right-click / rightclick) on
#
# <thing> can be:
# element
# link (searches for <A hrefs>)
# thing
#
# <find clause> for any page element can be:
# named "foo"
# with the id "foo"
# with the css selector ""
#
# <find clause> for links can be
# to "http://www.google.com"
# to a url that contains ".google.com"
# with the text "foo"
# with text that contains "foo"


# What's happening here? We're generating steps for every possible permutation
# of the actions and the finders below.

actions = {
    "click(?: on)?": "click",
    "(?: mouse over|mouse-over|mouseover)": "mouse_over",
    "(?: mouse out|mouse-out|mouseout)": "mouse_out",
    "(?: double click|double-click|doubleclick)": "double_click",
    "(?: right click|right-click|rightclick)": "right_click",
}


def step_generator(action_string, action_function, thing_string, finder_string, finder_function):

    @step(r'%s (?:a|the)( first)?( last)? %s %s' % (action_string, thing_string, finder_string))
    def _this_step(step, first, last, find_pattern):
        ele = _get_element(finder_function, first, last, find_pattern)

        ele.__getattribute__(action_function)()

    return _this_step


def drag_and_drop_generator(thing_string, finder_string, finder_function):

    @step(r'drag the( first)?( last)? %s %s and drop it on the( first)?( last)? %s %s' % (thing_string, finder_string, thing_string, finder_string))
    def _this_step(step, first_hander, last_handler, drag_handler_pattern, first_target, last_target, drag_target_pattern):
        handler = _get_element(finder_function, first_hander, last_handler, drag_handler_pattern)
        target = _get_element(finder_function, first_target, last_target, drag_target_pattern)

        handler.drag_and_drop(target)

    return _this_step


for action_string, action_function in actions.iteritems():
    for finder_string, finder_function in ELEMENT_FINDERS.iteritems():
        globals()["element_%s_%s" % (action_function, finder_function)] = step_generator(action_string,
                                                                                        action_function,
                                                                                        ELEMENT_THING_STRING,
                                                                                        finder_string,
                                                                                        finder_function
                                                                                        )

    for finder_string, finder_function in LINK_FINDERS.iteritems():
        globals()["link_%s_%s" % (action_function, finder_function)] = step_generator(action_string,
                                                                                        action_function,
                                                                                        LINK_THING_STRING,
                                                                                        finder_string,
                                                                                        finder_function
                                                                                        )

for finder_string, finder_function in ELEMENT_FINDERS.iteritems():
    globals()["element_drag_%s" % (finder_function)] = drag_and_drop_generator(ELEMENT_THING_STRING,
                                                                                    finder_string,
                                                                                    finder_function
                                                                                    )

########NEW FILE########
__FILENAME__ = navigation
from lettuce import step, world

# Browse from page to page


@step(r'(?:visit|access|open) the url "(.*)"')
def go_to_the_url(step, url):
    world.response = world.browser.visit(url)


@step(r'go back(?: a page)?')
def go_back(step):
    world.browser.back()


@step(r'go forward(?: a page)?')
def go_forward(step):
    world.browser.forward()


@step(r'(?:reload|refresh)(?: the page)?')
def reload(step):
    world.browser.reload()

########NEW FILE########
__FILENAME__ = page
from lettuce import step, world
from salad.tests.util import assert_equals_with_negate

# Verify page-level attributes (title, size, etc)


@step(r'should( not)? see that the page is titled "(.*)"')
def should_be_titled(step, negate, title):
    assert_equals_with_negate(world.browser.title, title, negate)


@step(r'should( not)? see that the url is "(.*)"')
def should_have_the_url(step, negate, url):
    assert_equals_with_negate(world.browser.url, url, negate)


@step(r'should( not)? see that the page html is "(.*)"')
def should_have_html(step, negate, html):
    assert_equals_with_negate(world.browser.html, html, negate)


@step(r'switch(?: back) to the parent frame')
def back_to_the_parent_frame(step):
    world.browser.driver.switch_to_frame(None)


@step(r'switch to the iframe "(.*)"')
def switch_to_iframe(step, iframe_id):
    world.browser.driver.switch_to_frame(iframe_id)

########NEW FILE########
__FILENAME__ = common
import time

from lettuce import step


@step(r'look around')
def look_around(step):
    pass


@step(r'wait (\d+) seconds?')
def wait(step, seconds):
    time.sleep(float(seconds))


@step(r'should fail because "(.*)"')
def should_fail(step, because):
    assert because == True

########NEW FILE########
__FILENAME__ = djangoify
from lettuce import step, world
from salad.logger import logger

try:
    from lettuce.django import django_url

    @step(r'(?:visit|access|open) the django url "(.*)"')
    def go_to_the_url(step, url):
        world.response = world.browser.visit(django_url(url))
except:
    try:
        # Only complain if it seems likely that using django was intended.
        import django
        logger.warn("Django steps not imported.")
    except:
        pass

########NEW FILE########
__FILENAME__ = everything
from salad.steps.common import *
from salad.steps.browser import *
from salad.steps.djangoify import *

########NEW FILE########
__FILENAME__ = browser
from lettuce import before, world, after
from splinter.browser import Browser
from salad.logger import logger


@before.all
def setup_master_browser():
    try:
        browser = world.drivers[0]
        remote_url = world.remote_url
    except AttributeError, IndexError:
        browser = 'firefox'
        remote_url = None

    world.master_browser = setup_browser(browser, remote_url)
    world.browser = world.master_browser


def setup_browser(browser, url=None):
    logger.info("Setting up browser %s..." % browser)
    try:
        if url:
            browser = Browser('remote', url=url,
                    browser=browser)
        else:
            browser = Browser(browser)
    except Exception as e:
        logger.warn("Error starting up %s: %s" % (browser, e))
        raise
    return browser


@before.each_scenario
def clear_alternative_browsers(step):
    world.browser = world.master_browser
    world.browsers = []


@after.each_scenario
def reset_to_parent_frame(step):
    if hasattr(world, "parent_browser"):
        world.browser = world.parent_browser


@after.each_scenario
def restore_browser(step):
    for browser in world.browsers:
        teardown_browser(browser)


@after.all
def teardown_master_browser(total):
    teardown_browser(world.master_browser)

def teardown_browser(browser):
    name = browser.driver_name
    logger.info("Tearing down browser %s..." % name)
    try:
        browser.quit()
    except Exception as e:
        logger.warn("Error tearing down %s: %s" % (name, e))

########NEW FILE########
__FILENAME__ = common

########NEW FILE########
__FILENAME__ = djangoify
from lettuce import before
from salad.logger import logger

logger.info("Loading the terrain file...")
try:
    from django.core import mail
    from django.core.management import call_command

    @before.each_scenario
    def reset_data(scenario):
        # Clean up django.
        logger.info("Flushing the test database...")
        call_command('flush', interactive=False, verbosity=0)
        call_command('loaddata', 'all', verbosity=0)

    @before.each_feature
    def empty_outbox(scenario):
        logger.info("Emptying outbox...")
        mail.outbox = []

except:
    try:
        # Only complain if it seems likely that using django was intended.
        import django
        logger.info("Django terrains not imported.")
    except:
        pass

########NEW FILE########
__FILENAME__ = everything
from salad.terrains.common import *
from salad.terrains.browser import *
from salad.terrains.djangoify import *

########NEW FILE########
__FILENAME__ = util
from nose.tools import assert_equals, assert_not_equals


def parsed_negator(negator):
    return negator and (negator == True or negator != "")


def assert_equals_with_negate(a, b, negator=None):
    if parsed_negator(negator):
        assert_not_equals(a, b)
    else:
        assert_equals(a, b)


def assert_with_negate(assertion, negator=None):
    if parsed_negator(negator):
        assert not assertion
    else:
        assert assertion

########NEW FILE########
