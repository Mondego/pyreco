__FILENAME__ = models
#dummy model is needed for django app

########NEW FILE########
__FILENAME__ = tests
# -*- coding: utf-8 -*-
#
# Authors:
# Flávio Amieiro <amieiro.flavio@gmail.com>
# Henrique Bastos <henrique@bastos.net>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
import time
from subprocess import Popen, STDOUT, PIPE
from django.test import TestCase
from pyccuracy.core import PyccuracyCore
import selenium

"""
Path constants
You will need to configure the Path Constants according to your directory layout.

BASE_PATH
  Is Djangucacy's absolute path

APPLICATION_DIR
  Is the Django App directory (contains manage.py)

SELENIUM_DIR
  Is the directory of Selenium RC. We expect it contains the python driver and a lib subdirectory containing the RC Jar library.
"""
APPLICATION_DIR     = os.path.realpath(os.curdir)
SELENIUM_DIR        = os.path.dirname(selenium.__file__)

BASE_PATH           = os.path.dirname(os.path.realpath(__file__))
ACC_TESTS_DIR       = "%s/acceptance/" % BASE_PATH
CUSTOM_ACTIONS_DIR  = "%s/custom_actions/" % BASE_PATH
CUSTOM_PAGES_DIR    = "%s/custom_pages/" % BASE_PATH
LOG_SELENIUM        = "%s/selenium.log" % BASE_PATH
LOG_APPLICATION     = "%s/application.log" % BASE_PATH

class PyccuracyTestCase(TestCase):
    application_server = None
    selenium_server = None

    def runApplicationServer(self):
        """Starts Django Test Server"""
        logfile = open(LOG_APPLICATION, 'w')
        self.application_server = Popen(['python', 'manage.py', 'testserver'],
                stdout=logfile, stderr=STDOUT, cwd=APPLICATION_DIR)
        time.sleep(5) #FIXME: we need to wait for the server to be ready
        print "Started Django Test Server"

    def runSeleniumServer(self):
        """Starts Selenium RC server"""
        command = ["java", "-jar", "lib/selenium-server.jar"]
        logfile = open(LOG_SELENIUM, 'w')

        self.selenium_server = Popen(command, stdin=PIPE, 
              stdout=logfile, stderr=STDOUT, cwd=SELENIUM_DIR)

        #wait selenium rc to be ready
        with open(LOG_SELENIUM, 'r') as f:
           line = f.readline()
           while not "Started SocketListener on" in line:
              line = f.readline()
           print "Started Selenium RC Server"

    def setUp(self):
        """Starts Django Test Server and Selenium RC Server."""
        self.runApplicationServer()
        self.runSeleniumServer()

    def tearDown(self):
        """Stops Django Test Server and Selenium RC."""
        self.application_server.terminate()
        self.selenium_server.terminate()

    def testAcceptanceWithPyccuracy(self):
        """Execute acceptance tests running Pyccuracy Core"""
        core = PyccuracyCore()
        result = core.run_tests(
                #base_url="http://myserver/index",
                tests_dir=ACC_TESTS_DIR,
                custom_actions_dir=CUSTOM_ACTIONS_DIR,
                pages_dir=CUSTOM_PAGES_DIR,
                write_report=False,
                default_culture="pt-br",
                browser_to_run="firefox",
                browser_driver="selenium",
                should_throw="should_throw",
                workers=1,
                verbosity=2,)


########NEW FILE########
__FILENAME__ = checkbox_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyccuracy.page import PageRegistry, Page
from pyccuracy.actions import ActionBase
from pyccuracy.languages import LanguageItem

class CheckboxCheckAction(ActionBase):
    '''h3. Example

  * And I check the "book" checkbox

h3. Description

This action checks the given checkbox.'''
    __builtin__ = True
    regex = LanguageItem("checkbox_check_regex")
 
    def execute(self, context, checkbox_key):
        element_type = "checkbox"
        element_key = self.resolve_element_key(context, element_type, checkbox_key)

        error_message = context.language.format("element_is_visible_failure", element_type, checkbox_key)
        self.assert_element_is_visible(context, element_key, error_message)
        context.browser_driver.checkbox_check(element_key)

class CheckboxUncheckAction(ActionBase):
    '''h3. Example

  * And I uncheck the "book" checkbox

h3. Description

This action unchecks the given checkbox.'''
    __builtin__ = True
    regex = LanguageItem("checkbox_uncheck_regex")
 
    def execute(self, context, checkbox_key):
        element_type = "checkbox"
        element_key = self.resolve_element_key(context, element_type, checkbox_key)

        error_message = context.language.format("element_is_visible_failure", element_type, checkbox_key)
        self.assert_element_is_visible(context, element_key, error_message)
        context.browser_driver.checkbox_uncheck(element_key)

class CheckboxIsCheckedAction(ActionBase):
    '''h3. Example

  * And I see the "book" checkbox is checked

h3. Description

This action asserts that the given checkbox is checked.'''
    __builtin__ = True
    regex = LanguageItem("checkbox_is_checked_regex")

    def execute(self, context, checkbox_key):
        element_type = "checkbox"
        element_key = self.resolve_element_key(context, element_type, checkbox_key)

        error_messsage = context.language.format("element_is_visible_failure", element_type, checkbox_key)
        self.assert_element_is_visible(context, element_key, error_messsage)
        if not context.browser_driver.checkbox_is_checked(element_key):
            error_messsage = context.language.format("checkbox_is_checked_failure", checkbox_key)
            raise self.failed(error_messsage)

class CheckboxIsNotCheckedAction(ActionBase):
    '''h3. Example

  * And I see the "book" checkbox is not checked

h3. Description

This action asserts that the given checkbox is not checked.'''
    __builtin__ = True
    regex = LanguageItem("checkbox_is_not_checked_regex")

    def execute(self, context, checkbox_key):
        element_type = "checkbox"
        element_key = self.resolve_element_key(context, element_type, checkbox_key)

        error_messsage = context.language.format("element_is_visible_failure", element_type, checkbox_key)
        self.assert_element_is_visible(context, element_key, error_messsage)
        if context.browser_driver.checkbox_is_checked(element_key):
            error_messsage = context.language.format("checkbox_is_not_checked_failure", checkbox_key)
            raise self.failed(error_messsage)

########NEW FILE########
__FILENAME__ = element_actions
# -*- coding: utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

u'''
Element actions can be used for any registered element (more about registering elements at "[[Creating custom Pages]]" section). The majority of Pyccuracy's actions are in this category, like clicking elements or verifying that they contain a given style.

Whenever you see element_name, it means the name of the registered element or the attribute "name" or "id" of the given element.

Whenever you see [element_type|element_selector] what this means is that you have to use one of the following:

h3. en-us:
  * button
  * radio button
  * div 
  * link 
  * checkbox 
  * select 
  * textbox 
  * image 
  * paragraph 
  * ul 
  * li
  * table
  * element (only use this if none of the above apply)

h3. pt-br:
  * botão 
  * radio 
  * div 
  * link 
  * checkbox 
  * select 
  * caixa de texto 
  * imagem 
  * parágrafo 
  * ul 
  * li
  * tabela
  * elemento (só utilize este se nenhum dos outro se aplicar)
  '''

from pyccuracy.page import PageRegistry, Page
from pyccuracy.actions import ActionBase
from pyccuracy.languages import LanguageItem

def resolve_element_key(context, element_type, element_name, resolve_function):
    element_type = element_type.encode("utf-8")
    resolved = resolve_function(context, element_type, element_name)
    if resolved:
        return resolved

    element_category = context.language.get(element_type + "_category")
    return resolve_function(context, element_category, element_name)

class ElementDoesNotContainStyleAction(ActionBase):
    '''h3. Examples

  * And I see "some" textbox does not have "width" style
  * And I see "other" button does not have "visible" style

h3. Description

This action asserts that the given element does not have the given style with any value.'''
    __builtin__ = True
    regex = LanguageItem('element_does_not_contain_style_regex')

    def execute(self, context, element_type, element_name, style_name):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_style = context.browser_driver.get_class(element_key) or ""
        styles = current_style.split(" ")

        if style_name in styles:
            error_message = context.language.format("element_does_not_contain_style_failure", element_type, element_name, style_name)
            raise self.failed(error_message)

class ElementContainsStyleAction(ActionBase):
    '''h3. Examples

  * And I see "some" textbox has "width" style
  * And I see "other" button has "visible" style

h3. Description

This action asserts that the given element has the given style with any value.'''
    __builtin__ = True
    regex = LanguageItem('element_contains_style_regex')

    def execute(self, context, element_type, element_name, style_name):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_style = context.browser_driver.get_class(element_key) or ""
        styles = current_style.split(" ")

        if style_name not in styles:
            error_message = context.language.format("element_contains_style_failure", element_type, element_name, style_name)
            raise self.failed(error_message)

class ElementClickAction(ActionBase):
    '''h3. Examples

  * And I click "some" button
  * And I click "other" checkbox and wait

h3. Description

This action instructs the browser driver to click the given element. If the "and wait" suffix is used, a "Wait for page to load" action is executed after this one.'''
    __builtin__ = True
    regex = LanguageItem('element_click_regex')

    def execute(self, context, element_type, element_name, should_wait):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)
        context.browser_driver.click_element(element_key)

        if (should_wait):
            timeout = 30000
            try:
                context.browser_driver.wait_for_page(timeout=timeout)
            except Exception, error:
                if str(error) == "Timed out after %dms" % timeout:
                    raise self.failed(context.language.format("timeout_failure", timeout))
                else:
                    raise

class ElementIsVisibleAction(ActionBase):
    '''h3. Examples

  * And I see "some" button
  * And I see "other" checkbox

h3. Description

This action asserts that the given element is visible.'''
    __builtin__ = True
    regex = LanguageItem('element_is_visible_regex')

    def execute(self, context, element_type, element_name):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

class ElementIsNotVisibleAction(ActionBase):
    '''h3. Examples

  * And I do not see "some" button
  * And I do not see "other" checkbox

h3. Description

This action asserts that the given element is not visible.'''
    __builtin__ = True
    regex = LanguageItem('element_is_not_visible_regex')

    def execute(self, context, element_type, element_name):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_not_visible_failure", element_type, element_name)
        self.assert_element_is_not_visible(context, element_key, error_message)

class ElementIsEnabledAction(ActionBase):
    '''h3. Examples

  * And I see "some" button is enabled
  * And I see "other" textbox is enabled

h3. Description

This action asserts that the given element is enabled.'''
    __builtin__ = True
    regex = LanguageItem('element_is_enabled_regex')

    def execute(self, context, element_type, element_name):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        if not context.browser_driver.is_element_enabled(element_key):
            error_message = context.language.format("element_is_enabled_failure", element_type, element_name)
            raise self.failed(error_message)

class ElementIsDisabledAction(ActionBase):
    '''h3. Examples

  * And I see "some" button is disabled
  * And I see "other" textbox is disabled

h3. Description

This action asserts that the given element is disabled.'''
    __builtin__ = True
    regex = LanguageItem('element_is_disabled_regex')

    def execute(self, context, element_type, element_name):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        if context.browser_driver.is_element_enabled(element_key):
            error_message = context.language.format("element_is_disabled_failure", element_type, element_name)
            raise self.failed(error_message)

class ElementWaitForPresenceAction(ActionBase):
    '''h3. Examples

  * And I wait for "some" button element to be present
  * And I wait for "other" textbox element to be present for 5 seconds

h3. Description

Waits until a given element appears or times out.

This action is really useful when you have some processing done (maybe AJAX) before an element is dynamically created.
'''
    __builtin__ = True
    regex = LanguageItem("element_wait_for_presence_regex")

    def execute(self, context, element_type, element_name, timeout):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        if not timeout:
            timeout = 5
        timeout = int(timeout)

        if not context.browser_driver.wait_for_element_present(element_key, timeout):
            error_message = context.language.format("element_wait_for_presence_failure", element_type, element_name, timeout, element_key)
            raise self.failed(error_message)

class ElementWaitForDisappearAction(ActionBase):
    '''h3. Examples

  * And I wait for "some" button element to disappear
  * And I wait for "other" textbox element to disappear for 5 seconds

h3. Description

Waits until a given element disappears (or is not visible already) or times out.

This action is really useful when you have some processing done (maybe AJAX) before an element is dynamically removed or hidden.
    '''
    __builtin__ = True
    regex = LanguageItem("element_wait_for_disappear_regex")

    def execute(self, context, element_type, element_name, timeout):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        if not timeout:
            timeout = 5
        timeout = int(timeout)

        if not context.browser_driver.wait_for_element_to_disappear(element_key, timeout):
            error_message = context.language.format("element_wait_for_disappear_failure", element_type, element_name, timeout, element_key)
            raise self.failed(error_message)

class ElementDragAction(ActionBase):
    '''h3. Example

  * I drag the "from" div to the "target" div

h3. Description

This action instructs the browser driver to drag the "from" element to the "target" element.'''
    __builtin__ = True
    regex = LanguageItem("element_drag_drop_regex")

    def execute(self, context, from_element_type, from_element_name, to_element_type, to_element_name):
        from_element_key = resolve_element_key(context, from_element_type, from_element_name, self.resolve_element_key)
        to_element_key = resolve_element_key(context, to_element_type, to_element_name, self.resolve_element_key)

        error_message = context.language.get("element_is_not_visible_for_drag_failure")
        self.assert_element_is_visible(context, from_element_key, error_message % from_element_key)
        self.assert_element_is_visible(context, to_element_key, error_message % to_element_key)

        context.browser_driver.drag_element(from_element_key, to_element_key)

class ElementContainsTextAction(ActionBase):
    '''h3. Example

  * I see "username" textbox contains "polo"

h3. Description

This action asserts that the text for the given element contains the specified one.'''
    __builtin__ = True
    regex = LanguageItem("element_contains_text_regex")

    def execute(self, context, element_type, element_name, text):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_text = context.browser_driver.get_element_text(element_key)
        if (not current_text) or (not text in current_text):
            error_message = context.language.format("element_contains_text_failure", element_type, element_name, text, current_text)
            raise self.failed(error_message)

class ElementDoesNotContainTextAction(ActionBase):
    '''h3. Example

  * I see "username" textbox does not contain "polo"

h3. Description

This action asserts that the text for the given element does not contain the specified one.'''
    __builtin__ = True
    regex = LanguageItem("element_does_not_contain_text_regex")

    def execute(self, context, element_type, element_name, text):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_text = context.browser_driver.get_element_text(element_key)
        if current_text and text in current_text:
            error_message = context.language.format("element_does_not_contain_text_failure", element_type, element_name, text, current_text)
            raise self.failed(error_message)

class ElementMatchesTextAction(ActionBase):
    '''h3. Example

  * I see "username" textbox matches "polo"

h3. Description

This action asserts that the text for the given element matches exactly the specified one.'''
    __builtin__ = True
    regex = LanguageItem("element_matches_text_regex")

    def execute(self, context, element_type, element_name, text):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_text = context.browser_driver.get_element_text(element_key)
        if (not current_text) or (text.strip() != current_text.strip()):
            error_message = context.language.format("element_matches_text_failure", element_type, element_name, text, current_text)
            raise self.failed(error_message)

class ElementDoesNotMatchTextAction(ActionBase):
    '''h3. Example

  * I see "username" textbox matches "polo"

h3. Description

This action asserts that the text for the given element does not match exactly the specified one.'''
    __builtin__ = True
    regex = LanguageItem("element_does_not_match_text_regex")

    def execute(self, context, element_type, element_name, text):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_text = context.browser_driver.get_element_text(element_key)
        if current_text and text.strip() == current_text.strip():
            error_message = context.language.format("element_does_not_match_text_failure", element_type, element_name, text, current_text)
            raise self.failed(error_message)

class ElementContainsMarkupAction(ActionBase):
    '''h3. Example

  * I see "username" textbox contains "&lt;p&gt;polo&lt;/p&gt;" markup

h3. Description

This action asserts that the markup for the given element contains the specified one.'''
    __builtin__ = True
    regex = LanguageItem("element_contains_markup_regex")

    def execute(self, context, element_type, element_name, markup):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_markup = context.browser_driver.get_element_markup(element_key)
        if (not current_markup) or (not markup in current_markup):
            error_message = context.language.format("element_contains_markup_failure", element_type, element_name, markup, current_markup)
            raise self.failed(error_message)

class ElementDoesNotContainMarkupAction(ActionBase):
    '''h3. Example

  * I see "username" textbox does not contain "&lt;p&gt;polo&lt;/p&gt;" markup

h3. Description

This action asserts that the markup for the given element does not contain the specified one.'''
    __builtin__ = True
    regex = LanguageItem("element_does_not_contain_markup_regex")

    def execute(self, context, element_type, element_name, markup):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_markup = context.browser_driver.get_element_markup(element_key)
        if current_markup and markup in current_markup:
            error_message = context.language.format("element_does_not_contain_markup_failure", element_type, element_name, markup, current_markup)
            raise self.failed(error_message)

class ElementMatchesMarkupAction(ActionBase):
    '''h3. Example

  * I see "username" textbox matches "&lt;p&gt;polo&lt;/p&gt;" markup

h3. Description

This action asserts that the markup for the given element matches exactly the specified one.'''
    __builtin__ = True
    regex = LanguageItem("element_matches_markup_regex")

    def execute(self, context, element_type, element_name, markup):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_markup = context.browser_driver.get_element_markup(element_key)
        if (not current_markup) or (markup.strip() != current_markup.strip()):
            error_message = context.language.format("element_matches_markup_failure", element_type, element_name, markup, current_markup)
            raise self.failed(error_message)

class ElementDoesNotMatchMarkupAction(ActionBase):
    '''h3. Example

  * I see "username" textbox does not match "&lt;p&gt;polo&lt;/p&gt;" markup

h3. Description

This action asserts that the markup for the given element does not match exactly the specified one.'''
    __builtin__ = True
    regex = LanguageItem("element_does_not_match_markup_regex")

    def execute(self, context, element_type, element_name, markup):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)

        current_markup = context.browser_driver.get_element_markup(element_key)
        if current_markup and markup.strip() == current_markup.strip():
            error_message = context.language.format("element_does_not_match_markup_failure", element_type, element_name, markup, current_markup)
            raise self.failed(error_message)

class ElementMouseoverAction(ActionBase):
    '''h3. Example

  * And I mouseover "some" image

h3. Description

This action instructs the browser driver to mouse over the specified element.'''
    __builtin__ = True
    regex = LanguageItem("element_mouseover_regex")

    def execute(self, context, element_type, element_name):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)
        context.browser_driver.mouseover_element(element_key)

class ElementMouseOutAction(ActionBase):
    '''h3. Example

  * And I mouseout "some" image

h3. Description

This action instructs the browser driver to remove mouse focus from the specified element.'''
    __builtin__ = True
    regex = LanguageItem("element_mouseout_regex")

    def execute(self, context, element_type, element_name):
        element_key = resolve_element_key(context, element_type, element_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", element_type, element_name)
        self.assert_element_is_visible(context, element_key, error_message)
        context.browser_driver.mouseout_element(element_key)

########NEW FILE########
__FILENAME__ = image_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyccuracy.page import PageRegistry, Page
from pyccuracy.actions import ActionBase
from pyccuracy.languages import LanguageItem

class ImageHasSrcOfAction(ActionBase):
    '''h3. Example

  * And I see "logo" image has src of "images/logo.png"

h3. Description

This action asserts that an image has the given src attribute.'''
    __builtin__ = True
    regex = LanguageItem("image_has_src_regex")

    def execute(self, context, image_name, src):
        image = self.resolve_element_key(context, Page.Image, image_name)

        error_message = context.language.format("element_is_visible_failure", "image", image_name)
        self.assert_element_is_visible(context, image, error_message)
        
        current_src = context.browser_driver.get_image_src(image)
        if src.lower() != current_src.lower():
            error_message = self.language.format("image_has_src_failure", image_name, src, current_src)
            raise self.failed(error_message)

class ImageDoesNotHaveSrcOfAction(ActionBase):
    '''h3. Example

  * And I see "logo" image does not have src of "images/logo.png"

h3. Description

This action asserts that an image does not have the given src attribute.'''
    __builtin__ = True
    regex = LanguageItem("image_does_not_have_src_regex")

    def execute(self, context, image_name, src):
        image = self.resolve_element_key(context, Page.Image, image_name)

        error_message = context.language.format("element_is_visible_failure", "image", image_name)
        self.assert_element_is_visible(context, image, error_message)
        
        current_src = context.browser_driver.get_image_src(image)
        if src.lower() == current_src.lower():
            error_message = self.language.format("image_does_not_have_src_failure", image_name, src, current_src)
            raise self.failed(error_message)

########NEW FILE########
__FILENAME__ = link_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyccuracy.page import PageRegistry, Page
from pyccuracy.actions import ActionBase
from pyccuracy.languages import LanguageItem

class LinkHasHrefOfAction(ActionBase):
    '''h3. Example

  * And I see "logout" link has "/app/logout" href

h3. Description

This action asserts that a link has the given href attribute.'''
    __builtin__ = True
    regex = LanguageItem("link_has_href_regex")

    def execute(self, context, link_name, href):
        link = self.resolve_element_key(context, Page.Link, link_name)

        error_message = context.language.format("element_is_visible_failure", "link", link_name)
        self.assert_element_is_visible(context, link, error_message)

        current_href = context.browser_driver.get_link_href(link)

        if not current_href or current_href.lower().find(href.lower()) == -1:
            error_message = context.language.format("link_has_href_failure", link_name, href, current_href)
            raise self.failed(error_message)

########NEW FILE########
__FILENAME__ = page_actions
# -*- coding: utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Page actions are actions that have a specific impact in the browser, like navigating to a different page.

This is a *very important* category of actions, since almost any single test relies on navigating to a given page.'''

import re
import time

from pyccuracy.page import PageRegistry, Page
from pyccuracy.actions import ActionBase
from pyccuracy.languages import LanguageItem

class PageGoToAction(ActionBase):
    '''h3. Examples

  * And I go to My Custom Page
  * And I go to "http://www.google.com"

h3. Description

This action tells Pyccuracy that the current browser driver ([[Creating a custom Browser Driver]]) should navigate to the URL that's registered in the specified page. Other than that, it also changes that current page in Pyccuracy's context to the specified one. This means that Pyccuracy will start using the registered elements and url in the specified page. 

For more information on creating custom pages check the [[Creating custom Pages]] page.

If you specify an url directly, Pyccuracy sets the current page to None and you can't use registered elements. That might make sense for some scenarios, but is the least preferred way of using this action.

This action also issues automatically a wait for page to load action after navigating. This is important to make sure that the following actions work with a properly loaded page.'''
    __builtin__ = True
    regex = LanguageItem('page_go_to_regex')

    def execute(self, context, url):
        page, resolved_url = self.resolve_url(context, url)
        self.go_to_page(context, url, page, resolved_url)
    
    def resolve_url(self, context, url):
        return PageRegistry.resolve(context.settings, url.replace('"', ''), must_raise=False)
    
    def go_to_page(self, context, url, page, resolved_url):
        if not resolved_url or (not url.startswith('"') and not page):
            raise self.failed(context.language.format("page_go_to_failure", url))

        context.browser_driver.page_open(resolved_url)
        context.browser_driver.wait_for_page()
        context.url = resolved_url
        if page:
            # If the resolved page is the same as the current one, 
            # there's not need to override the context page, risking
            # losing all the re-registered elements of the users.
            if not isinstance(context.current_page, page):
                context.current_page = page()
                if hasattr(context.current_page, "register"):
                    context.current_page.register()

class PageGoToWithParametersAction(PageGoToAction):
    '''h3. Examples

  * And I go to Profile Page of user "name"
  * And I go to Config Page for user "name"
  * And I go to Search Page with query "apple", order "desc", page "10"

h3. Description

This action does the same thing as the *"I go to [page]"* but allows you to have variable URLs and pass parameters to be included in them. You can pass as many parameters as you want using commas.

For instance, the examples above will access pages with the following URLs (respectively):

  * url = "/&lt;user&gt;"
  * url = "/config/&lt;user&gt;"
  * url = "/search.php?q=&lt;query&gt;&order=&lt;order&gt;&p=&lt;page&gt;"

Parameters will be automatically included in the URL when you call these pages. For more information on creating custom pages check the [[Creating custom Pages]] page.
'''
    __builtin__ = True
    regex = LanguageItem('page_go_to_with_parameters_regex')

    def execute(self, context, url, parameters):
        page, resolved_url = self.resolve_url(context, url)
        params = self.parse_parameters(context, parameters)
        resolved_url = self.replace_url_paremeters(resolved_url, params)
        super(PageGoToWithParametersAction, self).go_to_page(context, url, page, resolved_url)
    
    def parse_parameters(self, context, parameters):
        params = {}
        pattern = re.compile(r'^(.+)\s\"(.+)\"$')
        for item in [param.strip() for param in parameters.split(',')]:
            match = pattern.match(item)
            if not match:
                raise self.failed(context.language.format("page_go_to_with_parameters_failure", parameters))
            params[match.group(1)] = match.group(2)
        return params
    
    def replace_url_paremeters(self, url, parameters):
        resolved_url = url
        for item in parameters.keys():
            resolved_url = resolved_url.replace('<%s>' % item, parameters[item])
        return resolved_url

class PageAmInAction(ActionBase):
    '''h3. Example

  * And I am in My Custom Page

h3. Description

This action tells Pyccuracy that it should change the current page (as far as registered elements and url go) to a given page.

The same rule for direct urls of Go to Page applies to this action.

Other than that, this action does not do anything. The main purpose of this action is responding to some client event or redirect that might have changed the current page without our direct action (like submitting a form that redirects us to a different page).'''
    __builtin__ = True
    regex = LanguageItem("page_am_in_regex")

    def execute(self, context, url):
        page, resolved_url = PageRegistry.resolve(context.settings, url, must_raise=False)

        if page:
            # If the resolved page is the same as the current one, 
            # there's not need to override the context page, risking
            # losing all the re-registered elements of the users.
            if not isinstance(context.current_page, page):
                context.current_page = page()
                if hasattr(context.current_page, "register"):
                    context.current_page.register()
            context.url = resolved_url
        else:
            raise self.failed(context.language.format("page_am_in_failure", url))

class PageSeeTitleAction(ActionBase):
    '''h3. Example

  * And I see "whatever" title

h3. Description

This action asserts that the currently loaded page's title (Browser title) is the specified one. '''
    __builtin__ = True
    regex = LanguageItem("page_see_title_regex")

    def execute(self, context, title):
        actual_title = context.browser_driver.get_title()
        if (actual_title != title):
            msg = context.language.format("page_see_title_failure", actual_title, title)
            raise self.failed(msg)

class PageCheckContainsMarkupAction(ActionBase):
    '''h3. Example

  * And I see that current page contains "&lt;p&gt;expected markup&lt;/p&gt;"

h3. Description

This action asserts that the currently loaded page's mark-up contains the given mark-up.'''
    __builtin__ = True
    regex = LanguageItem("page_check_contains_markup_regex")

    def execute(self, context, expected_markup):
        html = context.browser_driver.get_html_source()

        if expected_markup not in html:
            msg = context.language.format("page_check_contains_markup_failure", expected_markup)
            raise self.failed(msg)

class PageCheckDoesNotContainMarkupAction(ActionBase):
    '''h3. Example

  * And I see that current page does not contain "&lt;p&gt;expected markup&lt;/p&gt;"

h3. Description

This action asserts that the currently loaded page's mark-up *does not* contain the given mark-up.'''
    __builtin__ = True
    regex = LanguageItem("page_check_does_not_contain_markup_regex")

    def execute(self, context, expected_markup):
        html = context.browser_driver.get_html_source()

        if expected_markup in html:
            msg = context.language.format("page_check_does_not_contain_markup_failure", expected_markup)
            raise self.failed(msg)

class PageWaitForPageToLoadAction(ActionBase):
    '''h3. Examples

  * And I wait for the page to load
  * And I wait for the page to load for 5 seconds

h3. Description

This action instructs the browser driver to wait for a given number of seconds for the page to load. If it times out, the test fails.'''
    __builtin__ = True
    regex = LanguageItem("page_wait_for_page_to_load_regex")

    def execute(self, context, timeout):
        try:
            timeout = float(timeout)
        except Exception:
            timeout = None

        if timeout:
            context.browser_driver.wait_for_page(timeout * 1000)
        else:
            context.browser_driver.wait_for_page()

class PageWaitForSecondsAction(ActionBase):
    '''h3. Examples

  * And I wait for 5 seconds
  * And I wait for 1 second
  * And I wait for 3.5 seconds

h3. Description

This action is just a proxy to Python's time.sleep function. It just hangs for a given number of seconds.'''
    __builtin__ = True
    regex = LanguageItem("page_wait_for_seconds_regex")

    def execute(self, context, timeout):
        try:
            timeout = float(timeout)
        except ValueError:
            raise self.failed("The specified time cannot be parsed into a float number: %s" % timeout)

        time.sleep(timeout)


########NEW FILE########
__FILENAME__ = radio_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyccuracy.page import PageRegistry, Page
from pyccuracy.actions import ActionBase
from pyccuracy.languages import LanguageItem

class RadioCheckAction(ActionBase):
    '''h3. Example

  * And I check the "credit card" radio

h3. Description

This action marks the given radio button.'''
    __builtin__ = True
    regex = LanguageItem("radio_check_regex")

    def execute(self, context, radio_key):
        element_type = "radio"
        element_key = self.resolve_element_key(context, element_type, radio_key)

        error_message = context.language.format("element_is_visible_failure", element_type, radio_key)
        self.assert_element_is_visible(context, element_key, error_message)
        context.browser_driver.radio_check(element_key)

class RadioIsCheckedAction(ActionBase):
    '''h3. Example

  * And I see the "credit card" radio is checked

h3. Description

This action asserts that the given radio button is checked.'''
    __builtin__ = True
    regex = LanguageItem("radio_is_checked_regex")

    def execute(self, context, radio_key):
        element_type = "radio"
        element_key = self.resolve_element_key(context, element_type, radio_key)

        error_messsage = context.language.format("element_is_visible_failure", element_type, radio_key)
        self.assert_element_is_visible(context, element_key, error_messsage)
        if not context.browser_driver.radio_is_checked(element_key):
            error_messsage = context.language.format("radio_is_checked_failure", radio_key)
            raise self.failed(error_messsage)

class RadioIsNotCheckedAction(ActionBase):
    '''h3. Example

  * And I see the "credit card" radio is not checked

h3. Description

This action asserts that the given radio button is not checked.'''
    __builtin__ = True
    regex = LanguageItem("radio_is_not_checked_regex")

    def execute(self, context, radio_key):
        element_type = "radio"
        element_key = self.resolve_element_key(context, element_type, radio_key)

        error_messsage = context.language.format("element_is_visible_failure", element_type, radio_key)
        self.assert_element_is_visible(context, element_key, error_messsage)
        if context.browser_driver.radio_is_checked(element_key):
            error_messsage = context.language.format("radio_is_not_checked_failure", radio_key)
            raise self.failed(error_messsage)

########NEW FILE########
__FILENAME__ = select_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyccuracy.page import PageRegistry, Page
from pyccuracy.actions import ActionBase
from pyccuracy.languages import LanguageItem

def resolve_element_key(context, element_type, element_name, resolve_function):
    element_category = context.language.get(element_type.encode("utf-8") + "_category")
    return resolve_function(context, element_category, element_name)

class SelectOptionByValueAction(ActionBase):
    '''h3. Example

  * And I select the option with value of "1" in "sports" select

h3. Description

This action instructs the browser driver to select the option in the specified select that matches the specified value.'''

    __builtin__ = True
    regex = LanguageItem("select_option_by_value_regex")

    def execute(self, context, select_name, option_value):
        select_key = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)
        self.assert_element_is_visible(context, select_key, error_message)
        
        result = context.browser_driver.select_option_by_value(select_key, option_value)
        
        if not result:
            error_message = context.language.format("select_option_by_value_failure", select_name, option_value)
            raise self.failed(error_message)

class SelectHasSelectedValueAction(ActionBase):
    '''h3. Example

  * And I see "sports" select has selected value of "1"

h3. Description

This action asserts that the currently selected option in the specified select has the specified value.'''
    __builtin__ = True
    regex = LanguageItem("select_has_selected_value_regex")

    def execute(self, context, select_name, option_value):
        select = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)
        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)
        self.assert_element_is_visible(context, select, error_message)
        
        selected_value = context.browser_driver.get_selected_value(select)

        if (unicode(selected_value) != unicode(option_value)):
            error_message = context.language.format("select_has_selected_value_failure", select_name, option_value, selected_value)
            raise self.failed(error_message)

class SelectOptionByIndexAction(ActionBase):
    '''h3. Example

  * And I select the option with index of 1 in "sports" select

h3. Description

This action instructs the browser driver to select the option in the specified select with the specified index.'''
    __builtin__ = True
    regex = LanguageItem("select_option_by_index_regex")

    def execute(self, context, select_name, index):
        index = int(index)
        select_key = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)
        self.assert_element_is_visible(context, select_key, error_message)
        
        result = context.browser_driver.select_option_by_index(select_key, index)
        
        if not result:
            error_message = context.language.format("select_option_by_index_failure", select_name, index)
            raise self.failed(error_message)

class SelectHasSelectedIndexAction(ActionBase):
    '''h3. Example

  * And I see "sports" select has selected index of 1

h3. Description

This action asserts that the currently selected option in the specified select has the specified index.'''
    __builtin__ = True
    regex = LanguageItem("select_has_selected_index_regex")

    def execute(self, context, select_name, index):
        select = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)
        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)
        self.assert_element_is_visible(context, select, error_message)
        
        selected_index = context.browser_driver.get_selected_index(select)

        if (int(selected_index) != int(index)):
            error_message = context.language.format("select_has_selected_index_failure", select_name, index, selected_index)
            raise self.failed(error_message)

class SelectOptionByTextAction(ActionBase):
    '''h3. Example

  * And I select the option with text of "soccer" in "sports" select

h3. Description

This action instructs the browser driver to select the option in the specified select with the specified text.'''
    __builtin__ = True
    regex = LanguageItem("select_option_by_text_regex")

    def execute(self, context, select_name, text):
        select_key = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)
        self.assert_element_is_visible(context, select_key, error_message)
        
        result = context.browser_driver.select_option_by_text(select_key, text)
        
        if not result:
            error_message = context.language.format("select_option_by_text_failure", select_name, text)
            raise self.failed(error_message)

class SelectHasSelectedTextAction(ActionBase):
    '''h3. Example

  * And I see "sports" select has selected text of "soccer"

h3. Description

This action asserts that the currently selected option in the specified select has the specified text.'''
    __builtin__ = True
    regex = LanguageItem("select_has_selected_text_regex")

    def execute(self, context, select_name, text):
        select = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)
        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)
        self.assert_element_is_visible(context, select, error_message)

        selected_text = context.browser_driver.get_selected_text(select)

        if (selected_text != text):
            error_message = context.language.format("select_has_selected_text_failure", select_name, text, selected_text)
            raise self.failed(error_message)

class SelectDoesNotHaveSelectedIndexAction(ActionBase):
    '''h3. Example

  * And I see "sports" select does not have selected index of 1

h3. Description

This action asserts that the currently selected option in the specified select does not have the specified index.'''
    __builtin__ = True
    regex = LanguageItem("select_does_not_have_selected_index_regex")

    def execute(self, context, select_name, index):
        select = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)
        self.assert_element_is_visible(context, select, error_message)

        selected_index = context.browser_driver.get_selected_index(select)

        if (selected_index == index):
            error_message = context.language.format("select_does_not_have_selected_index_failure", select_name, index, selected_index)
            raise self.failed(error_message)

class SelectDoesNotHaveSelectedValueAction(ActionBase):
    '''h3. Example

  * And I see "sports" select does not have selected value of "1"

h3. Description

This action asserts that the currently selected option in the specified select does not have the specified value.'''
    __builtin__ = True
    regex = LanguageItem("select_does_not_have_selected_value_regex")

    def execute(self, context, select_name, value):
        select = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)
        self.assert_element_is_visible(context, select, error_message)

        selected_value = context.browser_driver.get_selected_value(select)

        if (selected_value == value):
            error_message = context.language.format("select_does_not_have_selected_value_failure", select_name, value, selected_value)
            raise self.failed(error_message)

class SelectDoesNotHaveSelectedTextAction(ActionBase):
    '''h3. Example

  * And I see "sports" select does not have selected text of "soccer"

h3. Description

This action asserts that the currently selected option in the specified select does not have the specified text.'''
    __builtin__ = True
    regex = LanguageItem("select_does_not_have_selected_text_regex")

    def execute(self, context, select_name, text):
        select = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)
        self.assert_element_is_visible(context, select, error_message)

        selected_text = context.browser_driver.get_selected_text(select)

        if (selected_text == text):
            error_message = context.language.format("select_does_not_have_selected_text_failure", select_name, text, selected_text)
            raise self.failed(error_message)

class SelectContainsOptionWithTextAction(ActionBase):
    '''h3. Example

  * And I see "sports" select contains an option with text "soccer"

h3. Description

This action asserts that the specified select contains at least one option with the specified text.'''
    __builtin__ = True
    regex = LanguageItem("select_contains_option_with_text_regex")

    def execute(self, context, select_name, text):
        select = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)

        self.assert_element_is_visible(context, select, error_message)

        options = context.browser_driver.get_select_options(select)

        found = text in options
        
        if not found:
            error_message = context.language.format("select_contains_option_with_text_failure", select_name, text)
            raise self.failed(error_message)

class SelectDoesNotContainOptionWithTextAction(ActionBase):
    '''h3. Example

  * And I see "sports" select does not contain an option with text "soccer"

h3. Description

This action asserts that the specified select does not contain any options with the specified text.'''
    __builtin__ = True
    regex = LanguageItem("select_does_not_contain_option_with_text_regex")

    def execute(self, context, select_name, text):
        select = resolve_element_key(context, Page.Select, select_name, self.resolve_element_key)

        error_message = context.language.format("element_is_visible_failure", Page.Select, select_name)

        self.assert_element_is_visible(context, select, error_message)

        options = context.browser_driver.get_select_options(select)

        found = text in options
        
        if found:
            error_message = context.language.format("select_does_not_contain_option_with_text_failure", select_name, text)
            raise self.failed(error_message)

########NEW FILE########
__FILENAME__ = table_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyccuracy.page import PageRegistry, Page
from pyccuracy.actions import ActionBase
from pyccuracy.languages import LanguageItem

def resolve_element_key(context, element_type, element_name, resolve_function):
    element_category = context.language.get(element_type.encode("utf-8") + "_category")
    return resolve_function(context, element_category, element_name)

class TableMatchAction(ActionBase):
    '''h3. Example

  * And I see "some" table as:
        | Name | Age | Sex  |
        | John | 28  | Male |
        | Paul | 30  | Male | 

h3. Description

This action asserts that the given table matches the one the user specified.'''
    __builtin__ = True
    regex = LanguageItem("table_match_regex")

    def execute(self, context, table_name, table):
        element_type = Page.Table
        element_key = self.resolve_element_key(context, element_type, table_name)

        error_message = context.language.format("element_is_visible_failure", "table", table_name)
        self.assert_element_is_visible(context, element_key, error_message)

        rows = context.browser_driver.get_table_rows(element_key)

        error_table_keys = " | ".join(table[0].keys())
        error_table_format = "\n".join([" | ".join(item.values()) for item in table])
        error_rows_format = [" | ".join(item) for item in rows]
        error_message = context.language.format(
                                            "table_invalid_data_failure", 
                                            table_name, 
                                            error_table_keys,
                                            error_table_format, 
                                            error_rows_format)
                
        if not rows or len(rows) <= len(table) :
            raise self.failed(error_message)
        
        actual_keys = rows[0]
        
        for row_index, row in enumerate(rows[1:]):
            if len(row) != len(actual_keys):
                raise self.failed(error_message)
                 
            for cell_index, cell in enumerate(row):
                if cell != table[row_index][actual_keys[cell_index]]:
                    raise self.failed(error_message)

########NEW FILE########
__FILENAME__ = textbox_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyccuracy.page import PageRegistry, Page
from pyccuracy.actions import ActionBase
from pyccuracy.languages import LanguageItem

class TextboxIsEmptyAction(ActionBase):
    '''h3. Example

  * And I see "username" textbox is empty

h3. Description

This action asserts that the given textbox is empty.'''
    __builtin__ = True
    regex = LanguageItem("textbox_is_empty_regex")

    def execute(self, context, textbox_name):
        element_type = Page.Textbox
        element_key = self.resolve_element_key(context, element_type, textbox_name)

        error_message = context.language.format("element_is_visible_failure", "textbox", textbox_name)
        self.assert_element_is_visible(context, element_key, error_message)

        is_empty = context.browser_driver.is_element_empty(element_key)

        if not is_empty:
            error_message = context.language.format("textbox_is_empty_failure", textbox_name)
            raise self.failed(error_message)

class TextboxIsNotEmptyAction(ActionBase):
    '''h3. Example

  * And I see "username" textbox is not empty

h3. Description

This action asserts that the given textbox is not empty.'''
    __builtin__ = True
    regex = LanguageItem("textbox_is_not_empty_regex")

    def execute(self, context, textbox_name):
        element_type = "textbox"
        element_key = self.resolve_element_key(context, element_type, textbox_name)

        error_message = context.language.format("element_is_visible_failure", "textbox", textbox_name)
        self.assert_element_is_visible(context, element_key, error_message)

        is_empty = context.browser_driver.is_element_empty(element_key)

        if is_empty:
            error_message = context.language.format("textbox_is_not_empty_failure", textbox_name)
            raise self.failed(error_message)

class TextboxTypeAction(ActionBase):
    '''h3. Example

  * And I fill "details" textbox with "text"

h3. Description

This action types the given text in the given textbox.'''
    __builtin__ = True
    regex = LanguageItem("textbox_type_regex")

    def execute(self, context, textbox_name, text):
        textbox_key = self.resolve_element_key(context, Page.Textbox, textbox_name)

        error_message = context.language.format("element_is_visible_failure", "textbox", textbox_name)
        self.assert_element_is_visible(context, textbox_key, error_message)
        context.browser_driver.type_text(textbox_key, text)

class TextboxTypeSlowlyAction(ActionBase):
    '''h3. Example

  * And I slowly fill "details" textbox with "text"

h3. Description

This action types the given text in the given textbox. The difference between "slowly" typing and the regular typing is that this action raises javascript "key" events (keyUp, keyDown, etc).'''
    __builtin__ = True
    regex = LanguageItem("textbox_type_keys_regex")

    def execute(self, context, textbox_name, text):
        if context.settings.browser_to_run == "safari":
            # Needed to work on Safari/Mac OS - Selenium bug?
            # I observed that it's only possible to type_keys after type_text once.
            TextboxTypeAction().execute(context, textbox_name, text)
        
        # now typyng slowly...
        textbox_key = self.resolve_element_key(context, Page.Textbox, textbox_name)
        context.browser_driver.type_keys(textbox_key, text)

class TextboxCleanAction(ActionBase):
    '''h3. Example

  * And I clean "details" textbox

h3. Description

This action cleans the given textbox (empties any text inside of it).'''
    __builtin__ = True
    regex = LanguageItem("textbox_clean_regex")

    def execute(self, context, textbox_name):
        textbox = self.resolve_element_key(context, Page.Textbox, textbox_name)

        error_message = context.language.format("element_is_visible_failure", "textbox", textbox_name)
        self.assert_element_is_visible(context, textbox, error_message)
        context.browser_driver.clean_input(textbox)

########NEW FILE########
__FILENAME__ = airspeed
#!/usr/bin/env python

# From http://dev.sanityinc.com/airspeed/wiki

import re, operator, os

import StringIO   # cStringIO has issues with unicode

__all__ = ['Template', 'TemplateError', 'TemplateSyntaxError', 'CachingFileLoader']


###############################################################################
# Compatibility for old Pythons & Jython
###############################################################################
try: True
except NameError:
    False, True = 0, 1
try: dict
except NameError:
    from UserDict import UserDict
    class dict(UserDict):
        def __init__(self): self.data = {}
try: operator.__gt__
except AttributeError:
    operator.__gt__ = lambda a, b: a > b
    operator.__lt__ = lambda a, b: a < b
    operator.__ge__ = lambda a, b: a >= b
    operator.__le__ = lambda a, b: a <= b
    operator.__eq__ = lambda a, b: a == b
    operator.__ne__ = lambda a, b: a != b
    operator.mod = lambda a, b: a % b
try:
    basestring
    def is_string(s): return isinstance(s, basestring)
except NameError:
    def is_string(s): return type(s) == type('')

###############################################################################
# Public interface
###############################################################################

def boolean_value(variable_value):
    if variable_value == False: return False
    return not (variable_value is None)


class Template:
    def __init__(self, content):
        self.content = content
        self.root_element = None

    def merge(self, namespace, loader=None):
        output = StoppableStream()
        self.merge_to(namespace, output, loader)
        return output.getvalue()

    def ensure_compiled(self):
        if not self.root_element:
            self.root_element = TemplateBody(self.content)

    def merge_to(self, namespace, fileobj, loader=None):
        if loader is None: loader = NullLoader()
        self.ensure_compiled()
        self.root_element.evaluate(fileobj, namespace, loader)


class TemplateError(Exception):
    pass


class TemplateSyntaxError(TemplateError):
    def __init__(self, element, expected):
        self.element = element
        self.text_understood = element.full_text()[:element.end]
        self.line = 1 + self.text_understood.count('\n')
        self.column = len(self.text_understood) - self.text_understood.rfind('\n')
        got = element.next_text()
        if len(got) > 40:
            got = got[:36] + ' ...'
        Exception.__init__(self, "line %d, column %d: expected %s in %s, got: %s ..." % (self.line, self.column, expected, self.element_name(), got))

    def get_position_strings(self):
        error_line_start = 1 + self.text_understood.rfind('\n')
        if '\n' in self.element.next_text():
            error_line_end = self.element.next_text().find('\n') + self.element.end
        else:
            error_line_end = len(self.element.full_text())
        error_line = self.element.full_text()[error_line_start:error_line_end]
        caret_pos = self.column
        return [error_line, ' ' * (caret_pos - 1) + '^']

    def element_name(self):
        return re.sub('([A-Z])', lambda m: ' ' + m.group(1).lower(), self.element.__class__.__name__).strip()


class NullLoader:
    def load_text(self, name):
        raise TemplateError("no loader available for '%s'" % name)

    def load_template(self, name):
        raise self.load_text(name)


class CachingFileLoader:
    def __init__(self, basedir, debugging=False):
        self.basedir = basedir
        self.known_templates = {} # name -> (template, file_mod_time)
        self.debugging = debugging
        if debugging: print "creating caching file loader with basedir:", basedir

    def filename_of(self, name):
        return os.path.join(self.basedir, name)

    def load_text(self, name):
        if self.debugging: print "Loading text from", self.basedir, name
        f = open(self.filename_of(name))
        try: return f.read()
        finally: f.close()

    def load_template(self, name):
        if self.debugging: print "Loading template...", name,
        mtime = os.path.getmtime(self.filename_of(name))
        if self.known_templates.has_key(name):
            template, prev_mtime = self.known_templates[name]
            if mtime <= prev_mtime:
                if self.debugging: print "loading parsed template from cache"
                return template
        if self.debugging: print "loading text from disk"
        template = Template(self.load_text(name))
        template.ensure_compiled()
        self.known_templates[name] = (template, mtime)
        return template


class StoppableStream(StringIO.StringIO):
    def __init__(self, buf=''):
        self.stop = False
        StringIO.StringIO.__init__(self, buf)

    def write(self, s):
        if not self.stop:
            StringIO.StringIO.write(self, s)


###############################################################################
# Internals
###############################################################################

WHITESPACE_TO_END_OF_LINE = re.compile(r'[ \t\r]*\n(.*)', re.S)

class NoMatch(Exception): pass


class LocalNamespace(dict):
    def __init__(self, parent):
        dict.__init__(self)
        self.parent = parent

    def __getitem__(self, key):
        try: return dict.__getitem__(self, key)
        except KeyError:
            parent_value = self.parent[key]
            self[key] = parent_value
            return parent_value

    def top(self):
        if hasattr(self.parent, "top"):
            return self.parent.top()
        return self.parent

    def __repr__(self):
        return dict.__repr__(self) + '->' + repr(self.parent)


class _Element:
    def __init__(self, text, start=0):
        self._full_text = text
        self.start = self.end = start
        self.parse()

    def next_text(self):
        return self._full_text[self.end:]

    def my_text(self):
        return self._full_text[self.start:self.end]

    def full_text(self):
        return self._full_text

    def syntax_error(self, expected):
        return TemplateSyntaxError(self, expected)

    def identity_match(self, pattern):
        m = pattern.match(self._full_text, self.end)
        if not m: raise NoMatch()
        self.end = m.start(pattern.groups)
        return m.groups()[:-1]

    def next_match(self, pattern):
        m = pattern.match(self._full_text, self.end)
        if not m: return False
        self.end = m.start(pattern.groups)
        return m.groups()[:-1]

    def optional_match(self, pattern):
        m = pattern.match(self._full_text, self.end)
        if not m: return False
        self.end = m.start(pattern.groups)
        return True

    def require_match(self, pattern, expected):
        m = pattern.match(self._full_text, self.end)
        if not m: raise self.syntax_error(expected)
        self.end = m.start(pattern.groups)
        return m.groups()[:-1]

    def next_element(self, element_spec):
        if callable(element_spec):
            element = element_spec(self._full_text, self.end)
            self.end = element.end
            return element
        else:
            for element_class in element_spec:
                try: element = element_class(self._full_text, self.end)
                except NoMatch: pass
                else:
                    self.end = element.end
                    return element
            raise NoMatch()

    def require_next_element(self, element_spec, expected):
        if callable(element_spec):
            try: element = element_spec(self._full_text, self.end)
            except NoMatch: raise self.syntax_error(expected)
            else:
                self.end = element.end
                return element
        else:
            for element_class in element_spec:
                try: element = element_class(self._full_text, self.end)
                except NoMatch: pass
                else:
                    self.end = element.end
                    return element
            expected = ', '.join([cls.__name__ for cls in element_spec])
            raise self.syntax_error('one of: ' + expected)


class Text(_Element):
    PLAIN = re.compile(r'((?:[^\\\$#]+|\\[\$#])+|\$[^!\{a-z0-9_]|\$$|#$|#[^\{\}a-zA-Z0-9#\*]+|\\.)(.*)$', re.S + re.I)
    ESCAPED_CHAR = re.compile(r'\\([\\\$#])')

    def parse(self):
        text, = self.identity_match(self.PLAIN)
        def unescape(match):
            return match.group(1)
        self.text = self.ESCAPED_CHAR.sub(unescape, text)

    def evaluate(self, stream, namespace, loader):
        stream.write(self.text)


class FallthroughHashText(_Element):
    """ Plain tex, starting a hash, but which wouldn't be matched
        by a directive or a macro earlier.
        The canonical example is an HTML color spec.
        Another good example, is in-document hypertext links
        (or the dummy versions thereof often used a href targets
        when javascript is used.
        Note that it MUST NOT match block-ending directives. """
    # because of earlier elements, this will always start with a hash
    PLAIN = re.compile(r'(\#+\{?[\d\w]*\}?)(.*)$', re.S)

    def parse(self):
        self.text, = self.identity_match(self.PLAIN)
        if self.text.startswith('#end') or self.text.startswith('#{end}') or self.text.startswith('#else') or self.text.startswith('#{else}') or self.text.startswith('#elseif') or self.text.startswith('#{elseif}'):
            raise NoMatch

    def evaluate(self, stream, namespace, loader):
        stream.write(self.text)


class IntegerLiteral(_Element):
    INTEGER = re.compile(r'(-?\d+)(.*)', re.S)

    def parse(self):
        self.value, = self.identity_match(self.INTEGER)
        self.value = int(self.value)

    def calculate(self, namespace, loader):
        return self.value


class FloatingPointLiteral(_Element):
    FLOAT = re.compile(r'(-?\d+\.\d+)(.*)', re.S)

    def parse(self):
        self.value, = self.identity_match(self.FLOAT)
        self.value = float(self.value)

    def calculate(self, namespace, loader):
        return self.value


class BooleanLiteral(_Element):
    BOOLEAN = re.compile(r'((?:true)|(?:false))(.*)', re.S | re.I)

    def parse(self):
        self.value, = self.identity_match(self.BOOLEAN)
        self.value = self.value.lower() == 'true'

    def calculate(self, namespace, loader):
        return self.value


class StringLiteral(_Element):
    STRING = re.compile(r"'((?:\\['nrbt\\\\\\$]|[^'\\])*)'(.*)", re.S)
    ESCAPED_CHAR = re.compile(r"\\([nrbt'\\])")

    def parse(self):
        value, = self.identity_match(self.STRING)
        def unescape(match):
            return {'n': '\n', 'r': '\r', 'b': '\b', 't': '\t', '"': '"', '\\': '\\', "'": "'"}.get(match.group(1), '\\' + match.group(1))
        self.value = self.ESCAPED_CHAR.sub(unescape, value)

    def calculate(self, namespace, loader):
        return self.value

class InterpolatedStringLiteral(StringLiteral):
    STRING = re.compile(r'"((?:\\["nrbt\\\\\\$]|[^"\\])*)"(.*)', re.S)
    ESCAPED_CHAR = re.compile(r'\\([nrbt"\\])')

    def parse(self):
        StringLiteral.parse(self)
        self.block = Block(self.value, 0)

    def calculate(self, namespace, loader):
        output = StoppableStream()
        self.block.evaluate(output, namespace, loader)
        return output.getvalue()


class Range(_Element):
    MIDDLE = re.compile(r'([ \t]*\.\.[ \t]*)(.*)$', re.S)

    def parse(self):
        self.value1 = self.next_element((FormalReference, IntegerLiteral))
        self.identity_match(self.MIDDLE)
        self.value2 = self.next_element((FormalReference, IntegerLiteral))

    def calculate(self, namespace, loader):
        value1 = self.value1.calculate(namespace, loader)
        value2 = self.value2.calculate(namespace, loader)
        if value2 < value1:
            return xrange(value1, value2 - 1, -1)
        return xrange(value1, value2 + 1)


class ValueList(_Element):
    COMMA = re.compile(r'\s*,\s*(.*)$', re.S)

    def parse(self):
        self.values = []
        try: value = self.next_element(Value)
        except NoMatch:
            pass
        else:
            self.values.append(value)
            while self.optional_match(self.COMMA):
                value = self.require_next_element(Value, 'value')
                self.values.append(value)

    def calculate(self, namespace, loader):
        return [value.calculate(namespace, loader) for value in self.values]


class _EmptyValues:
    def calculate(self, namespace, loader):
        return []


class ArrayLiteral(_Element):
    START = re.compile(r'\[[ \t]*(.*)$', re.S)
    END =   re.compile(r'[ \t]*\](.*)$', re.S)
    values = _EmptyValues()

    def parse(self):
        self.identity_match(self.START)
        try:
            self.values = self.next_element((Range, ValueList))
        except NoMatch:
            pass
        self.require_match(self.END, ']')
        self.calculate = self.values.calculate

class DictionaryLiteral(_Element):
    START = re.compile(r'{[ \t]*(.*)$', re.S)
    END =   re.compile(r'[ \t]*}(.*)$', re.S)
    KEYVALSEP = re.compile(r'[ \t]*:[[ \t]*(.*)$', re.S)
    PAIRSEP = re.compile(r'[ \t]*,[ \t]*(.*)$', re.S)

    def parse(self):
        self.identity_match(self.START)
        self.local_data = {}
        if self.optional_match(self.END):
            # it's an empty dictionary
            return
        while(True):
            key = self.next_element(Value)
            self.require_match(self.KEYVALSEP, ':')
            value = self.next_element(Value)
            self.local_data[key] = value
            if not self.optional_match(self.PAIRSEP): break
        self.require_match(self.END, '}')

    # Note that this delays calculation of values until it's used.
    # TODO confirm that that's correct.
    def calculate(self, namespace, loader):
        tmp = {}
        for (key,val) in self.local_data.items():
            tmp[key.calculate(namespace, loader)] = val.calculate(namespace, loader)
        return tmp


class Value(_Element):
    def parse(self):
        self.expression = self.next_element((FormalReference, FloatingPointLiteral, IntegerLiteral,
                                             StringLiteral, InterpolatedStringLiteral, ArrayLiteral,
                                             DictionaryLiteral, ParenthesizedExpression, UnaryOperatorValue,
                                             BooleanLiteral))

    def calculate(self, namespace, loader):
        return self.expression.calculate(namespace, loader)


class NameOrCall(_Element):
    NAME = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)(.*)$', re.S)
    parameters = None

    def parse(self):
        self.name, = self.identity_match(self.NAME)
        try: self.parameters = self.next_element(ParameterList)
        except NoMatch: pass

    def calculate(self, current_object, loader, top_namespace):
        look_in_dict = True
        if not isinstance(current_object, LocalNamespace):
            try:
                result = getattr(current_object, self.name)
                look_in_dict = False
            except AttributeError:
                pass
        if look_in_dict:
            try: result = current_object[self.name]
            except KeyError: result = None
            except TypeError: result = None
            except AttributeError: result = None
        if result is None:
            return None ## TODO: an explicit 'not found' exception?
        if self.parameters is not None:
            result = result(*self.parameters.calculate(top_namespace, loader))
        return result


class SubExpression(_Element):
    DOT = re.compile('\.(.*)', re.S)

    def parse(self):
        self.identity_match(self.DOT)
        self.expression = self.next_element(VariableExpression)

    def calculate(self, current_object, loader, global_namespace):
        return self.expression.calculate(current_object, loader, global_namespace)


class VariableExpression(_Element):
    subexpression = None

    def parse(self):
        self.part = self.next_element(NameOrCall)
        try: self.subexpression = self.next_element(SubExpression)
        except NoMatch: pass

    def calculate(self, namespace, loader, global_namespace=None):
        if global_namespace is None:
            global_namespace = namespace
        value = self.part.calculate(namespace, loader, global_namespace)
        if self.subexpression:
            value = self.subexpression.calculate(value, loader, global_namespace)
        return value


class ParameterList(_Element):
    START = re.compile(r'\(\s*(.*)$', re.S)
    COMMA = re.compile(r'\s*,\s*(.*)$', re.S)
    END = re.compile(r'\s*\)(.*)$', re.S)
    values = _EmptyValues()

    def parse(self):
        self.identity_match(self.START)
        try: self.values = self.next_element(ValueList)
        except NoMatch: pass
        self.require_match(self.END, ')')

    def calculate(self, namespace, loader):
        return self.values.calculate(namespace, loader)


class FormalReference(_Element):
    START = re.compile(r'\$(!?)(\{?)(.*)$', re.S)
    CLOSING_BRACE = re.compile(r'\}(.*)$', re.S)

    def parse(self):
        self.silent, braces = self.identity_match(self.START)
        self.expression = self.require_next_element(VariableExpression, 'expression')
        if braces: self.require_match(self.CLOSING_BRACE, '}')
        self.calculate = self.expression.calculate

    def evaluate(self, stream, namespace, loader):
        value = self.expression.calculate(namespace, loader)
        if value is None:
            if self.silent: value = ''
            else: value = self.my_text()
        if is_string(value):
            stream.write(value)
        elif isinstance(value, Exception):
            stream.write(unicode(value))
        else:
            stream.write(str(value))


class Null:
    def evaluate(self, stream, namespace, loader): pass


class Comment(_Element, Null):
    COMMENT = re.compile('#(?:#.*?(?:\n|$)|\*.*?\*#(?:[ \t]*\n)?)(.*)$', re.M + re.S)

    def parse(self):
        self.identity_match(self.COMMENT)


class BinaryOperator(_Element):
    BINARY_OP = re.compile(r'\s*(>=|<=|<|==|!=|>|%|\|\||&&|or|and|\+|\-|\*|\/|\%)\s*(.*)$', re.S)
    OPERATORS = {'>' : operator.gt, '>=': operator.ge,
                 '<' : operator.lt, '<=': operator.le,
                 '==': operator.eq, '!=': operator.ne,
                 '%' : operator.mod,
                 '||': lambda a,b : boolean_value(a) or boolean_value(b),
                 '&&': lambda a,b : boolean_value(a) and boolean_value(b),
                 'or': lambda a,b : boolean_value(a) or boolean_value(b),
                 'and': lambda a,b : boolean_value(a) and boolean_value(b),
                 '+' : operator.add,
                 '-' : operator.sub,
                 '*' : operator.mul,
                 '/' : operator.div}
    PRECEDENCE = { '>'  : 2, '<'  : 2, '==': 2, '>=' : 2, '<=' : 2, '!=': 2,
                   '||' : 1, '&&' : 1, 'or': 1, 'and': 1,
                   '+'  : 3, '-'  : 3, '*' : 3, '/'  : 3, '%': 3}

    # In velocity, if + is applied to one string and one numeric
    # argument, will convert the number into a string.
    # As far as I can tell, this is undocumented.
    # Note that this applies only to add, not to other operators

    def parse(self):
        op_string, = self.identity_match(self.BINARY_OP)
        self.apply_to = self.OPERATORS[op_string]
        self.precedence = self.PRECEDENCE[op_string]

    # This assumes that the self operator is "to the left"
    # of the argument, and thus gets higher precedence if they're
    # both boolean operators.
    # That is, the way this is used (see Expression.calculate)
    # it should return false if the two ops have the same precedence
    # that is, it's strictly greater than, not greater than or equal to
    # to get proper left-to-right evaluation, it should skew towards false.
    def greater_precedence_than(self, other):
        return self.precedence > other.precedence



class UnaryOperatorValue(_Element):
    UNARY_OP = re.compile(r'\s*(!)\s*(.*)$', re.S)
    OPERATORS = {'!': operator.__not__}
    def parse(self):
        op_string, = self.identity_match(self.UNARY_OP)
        self.value = self.next_element(Value)
        self.op = self.OPERATORS[op_string]

    def calculate(self, namespace, loader):
        return self.op(self.value.calculate(namespace, loader))


# Note: there appears to be no way to differentiate a variable or
# value from an expression, other than context.
class Expression(_Element):

    def parse(self):
        self.expression = [self.next_element(Value)]
        while(True):
            try:
                binary_operator = self.next_element(BinaryOperator)
                value = self.require_next_element(Value, 'value')
                self.expression.append(binary_operator)
                self.expression.append(value)
            except NoMatch:
                break

    def calculate(self, namespace, loader):
        if not self.expression or len(self.expression) == 0:
            return False
        #TODO: how does velocity deal with an empty condition expression?

        opstack = []
        valuestack = [self.expression[0]]
        terms = self.expression[1:]

        # use top of opstack on top 2 values of valuestack
        def stack_calculate(ops, values, namespace, loader):
            value2 = values.pop()
            if isinstance(value2, Value):
                value2 = value2.calculate(namespace, loader)
            value1 = values.pop()
            if isinstance(value1, Value):
                value1 = value1.calculate(namespace, loader)
            result = ops.pop().apply_to(value1, value2)
            # TODO this doesn't short circuit -- does velocity?
            # also note they're eval'd out of order
            values.append(result)

        while terms:
            # next is a binary operator
            if not opstack or terms[0].greater_precedence_than(opstack[-1]):
                opstack.append(terms[0])
                valuestack.append(terms[1])
                terms = terms[2:]
            else:
                stack_calculate(opstack, valuestack, namespace, loader)

        # now clean out the stacks
        while opstack:
            stack_calculate(opstack, valuestack, namespace, loader)

        if len(valuestack) != 1:
            print "evaluation of expression in Condition.calculate is messed up: final length of stack is not one"
            #TODO handle this officially

        result = valuestack[0]
        if isinstance(result, Value):
            result = result.calculate(namespace, loader)
        return result


class ParenthesizedExpression(_Element):
    START = re.compile(r'\(\s*(.*)$', re.S)
    END = re.compile(r'\s*\)(.*)$', re.S)

    def parse(self):
        self.identity_match(self.START)
        expression = self.next_element(Expression)
        self.require_match(self.END, ')')
        self.calculate = expression.calculate


class Condition(_Element):
    def parse(self):
        expression = self.next_element(ParenthesizedExpression)
        self.optional_match(WHITESPACE_TO_END_OF_LINE)
        self.calculate = expression.calculate
        # TODO do I need to do anything else here?


class End(_Element):
    END = re.compile(r'#(?:end|{end})(.*)', re.I + re.S)

    def parse(self):
        self.identity_match(self.END)
        self.optional_match(WHITESPACE_TO_END_OF_LINE)


class ElseBlock(_Element):
    START = re.compile(r'#(?:else|{else})(.*)$', re.S + re.I)

    def parse(self):
        self.identity_match(self.START)
        self.block = self.require_next_element(Block, 'block')
        self.evaluate = self.block.evaluate


class ElseifBlock(_Element):
    START = re.compile(r'#elseif\b\s*(.*)$', re.S + re.I)

    def parse(self):
        self.identity_match(self.START)
        self.condition = self.require_next_element(Condition, 'condition')
        self.block = self.require_next_element(Block, 'block')
        self.calculate = self.condition.calculate
        self.evaluate = self.block.evaluate


class IfDirective(_Element):
    START = re.compile(r'#if\b\s*(.*)$', re.S + re.I)
    else_block = Null()

    def parse(self):
        self.identity_match(self.START)
        self.condition = self.next_element(Condition)
        self.block = self.require_next_element(Block, "block")
        self.elseifs = []
        while True:
            try: self.elseifs.append(self.next_element(ElseifBlock))
            except NoMatch: break
        try: self.else_block = self.next_element(ElseBlock)
        except NoMatch: pass
        self.require_next_element(End, '#else, #elseif or #end')

    def evaluate(self, stream, namespace, loader):
        if self.condition.calculate(namespace, loader):
            self.block.evaluate(stream, namespace, loader)
        else:
            for elseif in self.elseifs:
                if elseif.calculate(namespace, loader):
                    elseif.evaluate(stream, namespace, loader)
                    return
            self.else_block.evaluate(stream, namespace, loader)


# This can't deal with assignments like
# #set($one.two().three = something)
# yet
class Assignment(_Element):
    START = re.compile(r'\s*\(\s*\$([a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)*)\s*=\s*(.*)$', re.S + re.I)
    END = re.compile(r'\s*\)(?:[ \t]*\r?\n)?(.*)$', re.S + re.M)

    def parse(self):
        var_name, = self.identity_match(self.START)
        self.terms = var_name.split('.')
        self.value = self.require_next_element(Expression, "expression")
        self.require_match(self.END, ')')

    def evaluate(self, stream, namespace, loader):
        thingy = namespace
        for term in self.terms[0:-1]:
            if thingy == None: return
            look_in_dict = True
            if not isinstance(thingy, LocalNamespace):
                try:
                    thingy = getattr(thingy, term)
                    look_in_dict = False
                except AttributeError:
                    pass
            if look_in_dict:
                try: 
                    thingy = thingy[term]
                except KeyError: thingy = None
                except TypeError: thingy = None
                except AttributeError: thingy = None
        if thingy is not None:
            thingy[self.terms[-1]] = self.value.calculate(namespace, loader)

class MacroDefinition(_Element):
    START = re.compile(r'#macro\b(.*)', re.S + re.I)
    OPEN_PAREN = re.compile(r'[ \t]*\(\s*(.*)$', re.S)
    NAME = re.compile(r'\s*([a-z][a-z_0-9]*)\b(.*)', re.S + re.I)
    CLOSE_PAREN = re.compile(r'[ \t]*\)(.*)$', re.S)
    ARG_NAME = re.compile(r'[, \t]+\$([a-z][a-z_0-9]*)(.*)$', re.S + re.I)
    RESERVED_NAMES = ('if', 'else', 'elseif', 'set', 'macro', 'foreach', 'parse', 'include', 'stop', 'end')
    def parse(self):
        self.identity_match(self.START)
        self.require_match(self.OPEN_PAREN, '(')
        self.macro_name, = self.require_match(self.NAME, 'macro name')
        if self.macro_name.lower() in self.RESERVED_NAMES:
            raise self.syntax_error('non-reserved name')
        self.arg_names = []
        while True:
            m = self.next_match(self.ARG_NAME)
            if not m: break
            self.arg_names.append(m[0])
        self.require_match(self.CLOSE_PAREN, ') or arg name')
        self.optional_match(WHITESPACE_TO_END_OF_LINE)
        self.block = self.require_next_element(Block, 'block')
        self.require_next_element(End, 'block')

    def evaluate(self, stream, namespace, loader):
        global_ns = namespace.top()
        macro_key = '#' + self.macro_name.lower()
        if global_ns.has_key(macro_key):
            raise Exception("cannot redefine macro")
        global_ns[macro_key] = self

    def execute_macro(self, stream, namespace, arg_value_elements, loader):
        if len(arg_value_elements) != len(self.arg_names):
            raise Exception("expected %d arguments, got %d" % (len(self.arg_names), len(arg_value_elements)))
        macro_namespace = LocalNamespace(namespace)
        for arg_name, arg_value in zip(self.arg_names, arg_value_elements):
            macro_namespace[arg_name] = arg_value.calculate(namespace, loader)
        self.block.evaluate(stream, macro_namespace, loader)


class MacroCall(_Element):
    START = re.compile(r'#([a-z][a-z_0-9]*)\b(.*)', re.S + re.I)
    OPEN_PAREN = re.compile(r'[ \t]*\(\s*(.*)$', re.S)
    CLOSE_PAREN = re.compile(r'[ \t]*\)(.*)$', re.S)
    SPACE_OR_COMMA = re.compile(r'[ \t]*(?:,|[ \t])[ \t]*(.*)$', re.S)

    def parse(self):
        macro_name, = self.identity_match(self.START)
        self.macro_name = macro_name.lower()
        self.args = []
        if self.macro_name in MacroDefinition.RESERVED_NAMES or self.macro_name.startswith('end'):
            raise NoMatch()
        if not self.optional_match(self.OPEN_PAREN):
            # It's not really a macro call,
            # it's just a spare pound sign with text after it,
            # the typical example being a color spec: "#ffffff"
            # call it not-a-match and then let another thing catch it
            raise NoMatch()
        while True:
            try: self.args.append(self.next_element(Value))
            except NoMatch: break
            if not self.optional_match(self.SPACE_OR_COMMA): break
        self.require_match(self.CLOSE_PAREN, 'argument value or )')

    def evaluate(self, stream, namespace, loader):
        try: macro = namespace['#' + self.macro_name]
        except KeyError: raise Exception('no such macro: ' + self.macro_name)
        macro.execute_macro(stream, namespace, self.args, loader)


class IncludeDirective(_Element):
    START = re.compile(r'#include\b(.*)', re.S + re.I)
    OPEN_PAREN = re.compile(r'[ \t]*\(\s*(.*)$', re.S)
    CLOSE_PAREN = re.compile(r'[ \t]*\)(.*)$', re.S)

    def parse(self):
        self.identity_match(self.START)
        self.require_match(self.OPEN_PAREN, '(')
        self.name = self.require_next_element((StringLiteral, InterpolatedStringLiteral, FormalReference), 'template name')
        self.require_match(self.CLOSE_PAREN, ')')

    def evaluate(self, stream, namespace, loader):
        stream.write(loader.load_text(self.name.calculate(namespace, loader)))


class ParseDirective(_Element):
    START = re.compile(r'#parse\b(.*)', re.S + re.I)
    OPEN_PAREN = re.compile(r'[ \t]*\(\s*(.*)$', re.S)
    CLOSE_PAREN = re.compile(r'[ \t]*\)(.*)$', re.S)

    def parse(self):
        self.identity_match(self.START)
        self.require_match(self.OPEN_PAREN, '(')
        self.name = self.require_next_element((StringLiteral, InterpolatedStringLiteral, FormalReference), 'template name')
        self.require_match(self.CLOSE_PAREN, ')')

    def evaluate(self, stream, namespace, loader):
        template = loader.load_template(self.name.calculate(namespace, loader))
        ## TODO: local namespace?
        template.merge_to(namespace, stream, loader=loader)


class StopDirective(_Element):
    STOP = re.compile(r'#stop\b(.*)', re.S + re.I)

    def parse(self):
        self.identity_match(self.STOP)

    def evaluate(self, stream, namespace, loader):
        if hasattr(stream, 'stop'):
            stream.stop = True


# Represents a SINGLE user-defined directive
class UserDefinedDirective(_Element):
    DIRECTIVES = []

    def parse(self):
        self.directive = self.next_element(self.DIRECTIVES)

    def evaluate(self, stream, namespace, loader):
        self.directive.evaluate(stream, namespace, loader)


class SetDirective(_Element):
    START = re.compile(r'#set\b(.*)', re.S + re.I)

    def parse(self):
        self.identity_match(self.START)
        self.assignment = self.require_next_element(Assignment, 'assignment')

    def evaluate(self, stream, namespace, loader):
        self.assignment.evaluate(stream, namespace, loader)


class ForeachDirective(_Element):
    START = re.compile(r'#foreach\b(.*)$', re.S + re.I)
    OPEN_PAREN = re.compile(r'[ \t]*\(\s*(.*)$', re.S)
    IN = re.compile(r'[ \t]+in[ \t]+(.*)$', re.S)
    LOOP_VAR_NAME = re.compile(r'\$([a-z_][a-z0-9_]*)(.*)$', re.S + re.I)
    CLOSE_PAREN = re.compile(r'[ \t]*\)(.*)$', re.S)

    def parse(self):
        ## Could be cleaner b/c syntax error if no '('
        self.identity_match(self.START)
        self.require_match(self.OPEN_PAREN, '(')
        self.loop_var_name, = self.require_match(self.LOOP_VAR_NAME, 'loop var name')
        self.require_match(self.IN, 'in')
        self.value = self.next_element(Value)
        self.require_match(self.CLOSE_PAREN, ')')
        self.block = self.next_element(Block)
        self.require_next_element(End, '#end')

    def evaluate(self, stream, namespace, loader):
        iterable = self.value.calculate(namespace, loader)
        counter = 1
        try:
            if iterable is None:
                return
            if hasattr(iterable, 'keys'): iterable = iterable.keys()
            if not hasattr(iterable, '__getitem__'):
                raise ValueError("value for $%s is not iterable in #foreach: %s" % (self.loop_var_name, iterable))
            for item in iterable:
                namespace = LocalNamespace(namespace)
                namespace['velocityCount'] = counter
                namespace[self.loop_var_name] = item
                self.block.evaluate(stream, namespace, loader)
                counter += 1
        except TypeError:
            raise


class TemplateBody(_Element):
    def parse(self):
        self.block = self.next_element(Block)
        if self.next_text():
            raise self.syntax_error('block element')

    def evaluate(self, stream, namespace, loader):
        namespace = LocalNamespace(namespace)
        self.block.evaluate(stream, namespace, loader)


class Block(_Element):
    def parse(self):
        self.children = []
        while True:
            try: self.children.append(self.next_element((Text, FormalReference, Comment, IfDirective, SetDirective,
                                                         ForeachDirective, IncludeDirective, ParseDirective,
                                                         MacroDefinition, StopDirective, UserDefinedDirective,
                                                         MacroCall, FallthroughHashText)))
            except NoMatch: break

    def evaluate(self, stream, namespace, loader):
        for child in self.children:
            child.evaluate(stream, namespace, loader)


########NEW FILE########
__FILENAME__ = colored_terminal
import sys, re

class TerminalController:
    """
    A class that can be used to portably generate formatted output to
    a terminal.

    `TerminalController` defines a set of instance variables whose
    values are initialized to the control sequence necessary to
    perform a given action.  These can be simply included in normal
    output to the terminal:

        >>> term = TerminalController()
        >>> print 'This is '+term.GREEN+'green'+term.NORMAL

    Alternatively, the `render()` method can used, which replaces
    '${action}' with the string required to perform 'action':

        >>> term = TerminalController()
        >>> print term.render('This is ${GREEN}green${NORMAL}')

    If the terminal doesn't support a given action, then the value of
    the corresponding instance variable will be set to ''.  As a
    result, the above code will still work on terminals that do not
    support color, except that their output will not be colored.
    Also, this means that you can test whether the terminal supports a
    given action by simply testing the truth value of the
    corresponding instance variable:

        >>> term = TerminalController()
        >>> if term.CLEAR_SCREEN:
        ...     print 'This terminal supports clearning the screen.'

    Finally, if the width and height of the terminal are known, then
    they will be stored in the `COLS` and `LINES` attributes.
    """
    # Cursor movement:
    BOL = ''             #: Move the cursor to the beginning of the line
    UP = ''              #: Move the cursor up one line
    DOWN = ''            #: Move the cursor down one line
    LEFT = ''            #: Move the cursor left one char
    RIGHT = ''           #: Move the cursor right one char

    # Deletion:
    CLEAR_SCREEN = ''    #: Clear the screen and move to home position
    CLEAR_EOL = ''       #: Clear to the end of the line.
    CLEAR_BOL = ''       #: Clear to the beginning of the line.
    CLEAR_EOS = ''       #: Clear to the end of the screen

    # Output modes:
    BOLD = ''            #: Turn on bold mode
    BLINK = ''           #: Turn on blink mode
    DIM = ''             #: Turn on half-bright mode
    REVERSE = ''         #: Turn on reverse-video mode
    NORMAL = ''          #: Turn off all modes

    # Cursor display:
    HIDE_CURSOR = ''     #: Make the cursor invisible
    SHOW_CURSOR = ''     #: Make the cursor visible

    # Terminal size:
    COLS = None          #: Width of the terminal (None for unknown)
    LINES = None         #: Height of the terminal (None for unknown)

    # Foreground colors:
    BLACK = BLUE = GREEN = CYAN = RED = MAGENTA = YELLOW = WHITE = ''

    # Background colors:
    BG_BLACK = BG_BLUE = BG_GREEN = BG_CYAN = ''
    BG_RED = BG_MAGENTA = BG_YELLOW = BG_WHITE = ''

    _STRING_CAPABILITIES = """
    BOL=cr UP=cuu1 DOWN=cud1 LEFT=cub1 RIGHT=cuf1
    CLEAR_SCREEN=clear CLEAR_EOL=el CLEAR_BOL=el1 CLEAR_EOS=ed BOLD=bold
    BLINK=blink DIM=dim REVERSE=rev UNDERLINE=smul NORMAL=sgr0
    HIDE_CURSOR=cinvis SHOW_CURSOR=cnorm""".split()
    _COLORS = """BLACK BLUE GREEN CYAN RED MAGENTA YELLOW WHITE""".split()
    _ANSICOLORS = "BLACK RED GREEN YELLOW BLUE MAGENTA CYAN WHITE".split()

    def __init__(self, term_stream=sys.stdout):
        """
        Create a `TerminalController` and initialize its attributes
        with appropriate values for the current terminal.
        `term_stream` is the stream that will be used for terminal
        output; if this stream is not a tty, then the terminal is
        assumed to be a dumb terminal (i.e., have no capabilities).
        """
        # Curses isn't available on all platforms
        try: import curses
        except: return

        # If the stream isn't a tty, then assume it has no capabilities.
        if not term_stream.isatty(): return

        # Check the terminal type.  If we fail, then assume that the
        # terminal has no capabilities.
        try: curses.setupterm()
        except: return

        # Look up numeric capabilities.
        self.COLS = curses.tigetnum('cols')
        self.LINES = curses.tigetnum('lines')

        # Look up string capabilities.
        for capability in self._STRING_CAPABILITIES:
            (attrib, cap_name) = capability.split('=')
            setattr(self, attrib, self._tigetstr(cap_name) or '')

        # Colors
        set_fg = self._tigetstr('setf')
        if set_fg:
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, color, curses.tparm(set_fg, i) or '')
        set_fg_ansi = self._tigetstr('setaf')
        if set_fg_ansi:
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, color, curses.tparm(set_fg_ansi, i) or '')
        set_bg = self._tigetstr('setb')
        if set_bg:
            for i,color in zip(range(len(self._COLORS)), self._COLORS):
                setattr(self, 'BG_'+color, curses.tparm(set_bg, i) or '')
        set_bg_ansi = self._tigetstr('setab')
        if set_bg_ansi:
            for i,color in zip(range(len(self._ANSICOLORS)), self._ANSICOLORS):
                setattr(self, 'BG_'+color, curses.tparm(set_bg_ansi, i) or '')

    def _tigetstr(self, cap_name):
        # String capabilities can include "delays" of the form "$<2>".
        # For any modern terminal, we should be able to just ignore
        # these, so strip them out.
        import curses
        cap = curses.tigetstr(cap_name) or ''
        return re.sub(r'\$<\d+>[/*]?', '', cap)

    def render(self, template):
        """
        Replace each $-substitutions in the given template string with
        the corresponding terminal control string (if it's defined) or
        '' (if it's not).
        """
        return re.sub(r'\$\$|\${\w+}', self._render_sub, template)

    def _render_sub(self, match):
        s = match.group()
        if s == '$$': return s
        else: return getattr(self, s[2:-1])

class ProgressBar:
    """
A 3-line progress bar, which looks like::
Header
20% [===========----------------------------------]
progress message
 
The progress bar is colored, if the terminal supports color
output; and adjusts to the width of the terminal.
"""
    BAR = '%3d%% ${GREEN}[${BOLD}%s%s${NORMAL}${GREEN}]${NORMAL}\n'
    RED_BAR = '%3d%% ${RED}[${BOLD}%s%s${NORMAL}${RED}]${NORMAL}\n'
    HEADER = '${BOLD}${CYAN}%s${NORMAL}\n\n'
        
    def __init__(self, header, verbosity, term=None):
        self.status = "SUCCESS"
        self.term = term or TerminalController()
        self.verbosity = verbosity
        self.display_dots = False
        if self.verbosity == 1 or not (self.term.CLEAR_EOL and self.term.UP and self.term.BOL):
            self.display_dots = True
            return
        self.width = self.term.COLS or 75
        self.bar = self.term.render(self.BAR)
        self.header = self.term.render(self.HEADER % header.center(self.width))
        self.cleared = 1 #: true if we haven't drawn the bar yet.
        self.update(0, '')

    def set_failed(self):
        self.bar = self.term.render(self.RED_BAR)
        self.status = "FAILED"

    def update(self, percent, message):
        if self.verbosity == 0:
            return
        if self.display_dots:
            print "[%06.2f%%] %s - %s" % (percent*100, self.status, message)
            return
        if self.cleared:
            sys.stdout.write(self.header)
            self.cleared = 0
        n = int((self.width-10)*percent)
        sys.stdout.write(
            self.term.BOL + self.term.UP + self.term.CLEAR_EOL +
            (self.bar % (100*percent, '='*n, '-'*(self.width-10-n))) +
            self.term.CLEAR_EOL + message.center(self.width))
 
    def clear(self):
        if not self.cleared:
            sys.stdout.write(self.term.BOL + self.term.CLEAR_EOL +
                             self.term.UP + self.term.CLEAR_EOL +
                             self.term.UP + self.term.CLEAR_EOL)
            self.cleared = 1

########NEW FILE########
__FILENAME__ = common
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import time
import fnmatch
import urllib2
from glob import glob

from os.path import abspath, join, dirname, exists

from pyccuracy.languages import *
from pyccuracy.drivers import *
from pyccuracy.actions import ActionRegistry

def get_curdir():
    return abspath(dirname(os.curdir))

class URLChecker(object):
    """
    Taken from dead-parrot:

    http://github.com/gabrielfalcao/dead-parrot
    deadparrot/models/fields.py
    """

    def __init__(self, lib=urllib2):
        self.lib = lib

    def set_url(self, url):
        self.url = url

    def is_valid(self):
        url_regex = re.compile(r'^(https?|file):[/]{2}([\w_.-]+)+[.]?\w{2,}([:]\d+)?([/]?.*)?')
        return url_regex.search(self.url) and True or False

    def exists(self):
        try:
            self.lib.urlopen(self.url)
            return True

        except urllib2.URLError:
            return False

class TimedItem(object):
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start_run(self):
        '''Starts a run for this story. This method just keeps track of the time this story started.'''
        self.start_time = time.time()

    def end_run(self):
        '''Finishes a run for this story. This method just keeps track of the time this story finished.'''
        self.end_time = time.time()

    def ellapsed(self):
        '''The number of milliseconds that this story took to run.'''
        if self.start_time is None:
            return 0

        if self.end_time is None:
            return time.time() - self.start_time

        return self.end_time - self.start_time

class Status:
    '''Possible statuses of a story, scenario or action.'''
    Unknown = "UNKNOWN"
    Failed = "FAILED"
    Successful = "SUCCESSFUL"

class StatusItem(object):
    def __init__(self, parent):
        self.status = Status.Unknown
        self.parent = parent
        self.error = None

    def mark_as_failed(self, error=None):
        '''Marks this story as failed.'''
        self.status = Status.Failed
        self.error = error
        if self.parent and isinstance(self.parent, StatusItem):
            self.parent.mark_as_failed()

    def mark_as_successful(self):
        '''Marks this story as successful only if it has not been marked failed before.'''
        if self.status != Status.Failed:
            self.status = Status.Successful
        if self.parent and isinstance(self.parent, StatusItem):
            self.parent.mark_as_successful()

class Settings(object):
    def __init__(self,
                 settings=None,
                 cur_dir=get_curdir(),
                 actions_dir=None,
                 abspath_func=abspath,
                 languages_dir=None):

        if not settings:
            settings = {}

        if not actions_dir:
            actions_dir = abspath_func(join(dirname(__file__), "actions"))

        if not languages_dir:
            languages_dir = abspath_func(join(dirname(__file__), "languages"))

        self.tests_dirs = [abspath_func(test_dir) for test_dir in self.get_setting(settings, "tests_dirs", [cur_dir])]

        self.actions_dir = self.get_setting(settings, "actions_dir", actions_dir)
        self.languages_dir = self.get_setting(settings, "languages_dir", languages_dir)
        
        self.hooks_dir = self.get_setting(settings, "hooks_dir", self.tests_dirs)
        if not self.hooks_dir:
            self.hooks_dir = self.tests_dirs
        
        self.pages_dir = self.get_setting(settings, "pages_dir", self.tests_dirs)
        if not self.pages_dir:
            self.pages_dir = self.tests_dirs
        
        self.custom_actions_dir = self.get_setting(settings, "custom_actions_dir", self.tests_dirs)
        if not self.custom_actions_dir:
            self.custom_actions_dir = self.tests_dirs

        self.file_pattern = self.get_setting(settings, "file_pattern", "*.acc")
        self.scenarios_to_run = self.get_setting(settings, "scenarios_to_run", [])
        if self.scenarios_to_run:
            self.scenarios_to_run = self.scenarios_to_run.replace(" ","").split(",")

        self.default_culture = self.get_setting(settings, "default_culture", "en-us")
        self.base_url = self.get_setting(settings, "base_url", None)
        self.should_throw = self.get_setting(settings, "should_throw", False)
        self.write_report = self.get_setting(settings, "write_report", True)
        self.report_file_dir = self.get_setting(settings, "report_file_dir", cur_dir)
        self.report_file_name = self.get_setting(settings, "report_file_name", "report.html")
        self.browser_to_run = self.get_setting(settings, "browser_to_run", "chrome")
        self.browser_driver = self.get_setting(settings, "browser_driver", "selenium")
        self.worker_threads = int(self.get_setting(settings, "workers", 1))
        self.extra_args = self.get_setting(settings, "extra_args", {})
        self.on_scenario_started = self.get_setting(settings, "on_scenario_started", None)
        self.on_scenario_completed = self.get_setting(settings, "on_scenario_completed", None)

        self.on_before_action = self.get_setting(settings, 'on_before_action', None)
        self.on_action_successful = self.get_setting(settings, 'on_action_successful', None)
        self.on_action_error = self.get_setting(settings, 'on_action_error', None)
        self.on_section_started = self.get_setting(settings, 'on_section_started', None)
        self.suppress_warnings = self.get_setting(settings, "suppress_warnings", False)

    def get_setting(self, settings, key, default):
        value = settings.get(key, None)

        if value is None:
            return default

        return value

class Context(object):
    def __init__(self, settings):
        self.settings = settings
        if not settings.default_culture in AVAILABLE_GETTERS:
            print "Invalid language %s. Available options are: %s. Defaulting to en-us." % (settings.default_culture, ", ".join(AVAILABLE_GETTERS.keys())) 
            settings.default_culture = "en-us"
        self.language = AVAILABLE_GETTERS[settings.default_culture]
        self.browser_driver = DriverRegistry.get(settings.browser_driver)(self)
        self.url = None
        self.current_page = None

def locate(pattern, root=os.curdir, recursive=True):
    root_path = os.path.abspath(root)

    if recursive:
        return_files = []
        for path, dirs, files in os.walk(root_path):
            for filename in fnmatch.filter(files, pattern):
                return_files.append(os.path.join(path, filename))
        return return_files
    else:
        return glob(join(root_path, pattern))

########NEW FILE########
__FILENAME__ = core
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
from os.path import join, split, splitext

from pyccuracy.airspeed import Template

from pyccuracy import Page, ActionBase
from pyccuracy.actions import MetaActionBase
from pyccuracy.common import Settings, Context, locate, Status
from pyccuracy.story_runner import *
from pyccuracy.parsers import FileParser, ActionNotFoundError
from pyccuracy.errors import *
from pyccuracy.languages.templates import *
from pyccuracy.drivers import DriverError
from pyccuracy.result import Result
from pyccuracy.colored_terminal import TerminalController
from pyccuracy.hooks import Hooks

class FSO(object):
    def add_to_import(self, path):
        sys.path.append(path)

    def remove_from_import(self, path):
        sys.path.remove(path)

    def locate(self, path, pattern):
        return locate(root=path, pattern=pattern, recursive=False)

    def import_file(self, filename):
        __import__(filename)

class PyccuracyCore(object):
    def __init__(self, parser=None, runner=None, hooks=None):
        self.parser = parser or FileParser()
        self.runner = runner
        sys.path.insert(0, os.getcwd())
        self.used_elements = {}
        self.hooks = hooks and hooks or Hooks

    def got_element(self, page, element_key, resolved_key):
        if page not in self.used_elements:
            self.used_elements[page] = []
        self.used_elements[page] = element_key

    def run_tests(self, context=None, fso=None, **kwargs):
        settings = Settings(kwargs)
        if not context:
            context = Context(settings)

        if not self.runner:
            self.runner = context.settings.worker_threads == 1 and StoryRunner() or ParallelStoryRunner(settings.worker_threads)

        for directory in context.settings.hooks_dir:
            self.import_extra_content(directory, fso=fso)
        
        for directory in context.settings.pages_dir:
            self.import_extra_content(directory, fso=fso)

        if context.settings.custom_actions_dir != context.settings.pages_dir:
            for directory in context.settings.custom_actions_dir:
                self.import_extra_content(directory, fso=fso)
        
        try:
            fixture = self.parser.get_stories(settings)
        except ActionNotFoundError, err:
            self.print_invalid_action(context.settings.default_culture, err)
            if settings.should_throw:
                raise TestFailedError("The test failed!")
            else:
                return None
        
        if fixture.no_story_header:
            self.print_no_story_header(fixture, context)
            if settings.should_throw:
                raise TestFailedError("The test failed!")
            else:
                return None

        if len(self.parser.used_actions) != len(ActionBase.all()):
            unused_actions = []
            for action in ActionBase.all():
                if hasattr(action, '__builtin__') and action.__builtin__:
                    continue
                if action not in self.parser.used_actions:
                    unused_actions.append(action.__name__)
            if unused_actions and not settings.suppress_warnings:
                self.print_unused_actions_warning(unused_actions)

        if not fixture.stories:
            results = Result(fixture)
            self.print_results(context.settings.default_culture, results)
            return results

        try:
            Page.subscribe_to_got_element(self.got_element)

            self.hooks.execute_before_tests()
            
            #running the tests
            results = self.runner.run_stories(settings=context.settings,
                                               fixture=fixture,
                                               context=context)

            if not settings.suppress_warnings:
                self.print_unused_elements_warning()

            self.print_results(context.settings.default_culture, results)

            if context.settings.write_report and results:
                try:
                    import lxml
                except ImportError:
                    self.print_lxml_import_error()
                else:
                    import report_parser as report
                    path = join(context.settings.report_file_dir, context.settings.report_file_name)
                    report.generate_report(path, results, context.language)

            self.hooks.execute_after_tests(results)
            
            if settings.should_throw and results and results.get_status() == Status.Failed:
                raise TestFailedError("The test failed!")
            
            return results
        except KeyboardInterrupt:
            results = Result(fixture)
            self.print_results(context.settings.default_culture, results)
            return results

    def print_no_story_header(self, fixture, context):
        val = { 
                "has_no_header_files":True,
                "no_header_files":fixture.no_story_header
              }
        template_loader = TemplateLoader(context.language.key)
        template_string = template_loader.load('noheader')
        template = Template(template_string)
        msg = template.merge(val)
        ctrl = TerminalController()
        print ctrl.render(msg)

    def print_unused_elements_warning(self):
        unused_elements = []
        
        for page_class in Page.all():
            page = page_class()
            if hasattr(page, "register"):
                page.register()
            if not page in self.used_elements:
                unused_elements.extend(page.registered_elements.keys())
            else:
                for element in page.registered_elements.keys():
                    element_key = '[%s] %s' % \
                                (page.__class__.__name__, element)
                                
                    if element not in self.used_elements.values() and \
                                element_key not in unused_elements:
                        unused_elements.append(element_key)

        if unused_elements:
            template = """${YELLOW}WARNING!
    ------------
    The following elements are registered but are never used: 

      *%s
    ------------
    ${NORMAL}
    """
            ctrl = TerminalController()
            print ctrl.render(template % "\n  *".join(unused_elements))

    def print_unused_actions_warning(self, unused_actions):
        template = """${YELLOW}WARNING!
------------
The following actions are never used: 

  *%s
------------
${NORMAL}
"""
        ctrl = TerminalController()
        print ctrl.render(template % "\n  *".join(unused_actions))

    def print_lxml_import_error(self):
        template = """${RED}REPORT ERROR
------------
Sorry, but you need to install lxml (python-lxml in aptitude or easy_install lxml)
before using the report feature in pyccuracy.
If you do not need a report use the -R=false parameter.
${NORMAL}
"""
        ctrl = TerminalController()
        print ctrl.render(template)

    def print_results(self, language, results):
        if not results:
            return
        ctrl = TerminalController()
        print ctrl.render("${NORMAL}")
        print ctrl.render(results.summary_for(language))
        print "\n"

    def print_invalid_action(self, language, err):
        ctrl = TerminalController()
        print ctrl.render("${NORMAL}")
        template_text = TemplateLoader(language).load("invalid_scenario")
        template = Template(template_text)

        values = {
                    "action_text":err.line,
                    "scenario":err.scenario,
                    "filename":err.filename
                 }

        print ctrl.render(template.merge(values))

    def import_extra_content(self, path, fso=None):
        '''Imports all the extra .py files in the tests dir so that pages, actions and other things get imported.'''
        pattern = "*.py"

        if not fso:
            fso = FSO()

        fso.add_to_import(path)
        files = fso.locate(path, pattern)

        for f in files:
            try:
                filename = splitext(split(f)[1])[0]
                fso.import_file(filename)
            except ImportError, e:
                import traceback
                err = traceback.format_exc(e)
                raise ExtraContentError("An error occurred while trying to import %s. Error: %s" % (f, err))

        fso.remove_from_import(path)

class ExtraContentError(Exception):
    pass

########NEW FILE########
__FILENAME__ = pyccuracy
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from os.path import abspath, dirname, join, exists
import warnings
from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings

from pyccuracy.pyccuracy_console import main as run_pyccuracy
from pyccuracy.common import locate

class Command(BaseCommand):
    help = "Runs pyccuracy tests for all apps (EXPERIMENTAL)"
    option_list = BaseCommand.option_list + (
        make_option("-s", "--scenario", dest=u"scenario", default=None, help=u"Number (index) for the scenario to be executed. Use commas for several scenarios. I.e.: -s 3,6,7 or --scenario=3,6,7."),
        make_option("-t", "--testfolder", dest=u"testfolder", default="tests/acceptance", help=u"Directory to look for tests (starting from each app)."),
        make_option("-l", "--loglevel", dest=u"loglevel", default=1, help=u"Verbosity: 1, 2 ou 3."),
        make_option("-u", "--baseurl", dest=u"baseurl", default=u"http://localhost:8000", help=u"Base Url for acceptance tests. Defaults to http://localhost:8000."),
        make_option("-p", "--pattern", dest=u"pattern", default=u"*.acc", help=u"Pattern (wildcard) to be used to find acceptance tests."),
        make_option("-b", "--browser", dest=u"browser", default=u"firefox", help=u"Browser that will be used to run the tests."),
        make_option("-w", "--workers", dest=u"workers", default=1, help=u"Number of tests to be run in parallel."),
        make_option("-c", "--language", dest=u"language", default='en-us', help=u"Language to run the tests in. Defaults to 'en-us'."),
        make_option("-a", "--app", dest=u"apps", default=None, help=u"Only run the specified apps - comma separated."),
        make_option("-n", "--supresswarning", action="store_true", dest=u"supress_warnings", default=False, help=u"Supress Pyccuracy warnings."),
    )

    def locate_resource_dirs(self, complement, pattern="*.*", recursive=True, apps=[]):
        dirs = []

        for app in settings.INSTALLED_APPS:
            fromlist = ""

            if len(app.split("."))>1:
                fromlist = ".".join(app.split(".")[1:])

            if app.startswith('django'):
                continue

            if apps and not app in apps:
                continue

            module = __import__(app, fromlist=fromlist)
            app_dir = abspath("/" + "/".join(module.__file__.split("/")[1:-1]))

            resource_dir = join(app_dir, complement)

            if exists(resource_dir) and locate(pattern, resource_dir, recursive):
                dirs.append(resource_dir)

        return dirs

    def handle(self, *args, **options):
        warnings.filterwarnings('ignore', '.*',)

        if args:
            selenium_host_and_port = args[0].split(':')
            if len(selenium_host_and_port) > 1:
                (seleniumn_host, selenium_port) = selenium_host_and_port
            else:
                selenium_host = selenium_host_and_port[0]
                selenium_port = 4444
        else:
            selenium_host = "localhost"
            selenium_port = 4444

        apps_to_look_for_tests = []
        if options['apps']:
            apps_to_look_for_tests = options['apps'].replace(' ', '').split(',')

        dir_template = "-d %s"
        action_template = "-A %s"
        page_template = "-P %s"

        pattern = options['pattern']

        testfolder = options['testfolder']

        dirs = self.locate_resource_dirs(testfolder, pattern, apps=apps_to_look_for_tests)

        action_pages_dirs = self.locate_resource_dirs(testfolder, "__init__.py")
        pages_templates = " ".join([page_template % dirname for dirname in action_pages_dirs])
        actions_templates = " ".join([action_template % dirname for dirname in action_pages_dirs])

        dir_templates = " ".join([dir_template % dirname for dirname in dirs])

        pyccuracy_arguments = []

        pyccuracy_arguments.append("-u")
        pyccuracy_arguments.append(options["baseurl"])
        pyccuracy_arguments.extend(dir_templates.split(" "))
        pyccuracy_arguments.extend(actions_templates.split(" "))
        pyccuracy_arguments.extend(pages_templates.split(" "))
        pyccuracy_arguments.append("-p")
        pyccuracy_arguments.append(options["pattern"])
        pyccuracy_arguments.append("-l")
        pyccuracy_arguments.append(options["language"])
        pyccuracy_arguments.append("-w")
        pyccuracy_arguments.append(options["workers"])
        pyccuracy_arguments.append("-v")
        pyccuracy_arguments.append(options["loglevel"])

        if options["supress_warnings"]:
            pyccuracy_arguments.append("--suppresswarnings")

        if options["scenario"]:
            pyccuracy_arguments.append("-s")
            pyccuracy_arguments.append(options["scenario"])

        pyccuracy_arguments.append("-b")
        pyccuracy_arguments.append(options["browser"])
        pyccuracy_arguments.append("selenium.server=%s" % selenium_host)
        pyccuracy_arguments.append("selenium.port=%s" % selenium_port)

        print u'***********************'
        print u'Running Pyccuracy Tests'
        print u'***********************'

        pyccuracy_arguments = [argument for argument in pyccuracy_arguments if argument != '' and argument is not None]

        ret_code = run_pyccuracy(pyccuracy_arguments)
        raise SystemExit(ret_code)

########NEW FILE########
__FILENAME__ = selenium_driver
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
from traceback import format_exc

selenium_available = True
try:
    from selenium import *
except ImportError:
    selenium_available = False

from pyccuracy.drivers import BaseDriver, DriverError
from selenium_element_selector import *

class SeleniumDriver(BaseDriver):
    backend = 'selenium'

    def __init__(self, context, selenium=None):
        self.context = context
        self.selenium = selenium

    def start_test(self, url=None):
        if not selenium_available:
            raise RuntimeError('You *MUST* have selenium installed to use the selenium browser driver')

        if not url:
            url = self.context.settings.base_url
        self.start_selenium(url)
        
    def start_selenium(self, url):
        host = self.context.settings.extra_args.get("selenium.server", "localhost")
        port = self.context.settings.extra_args.get("selenium.port", 4444)
        browser_to_run = self.context.settings.browser_to_run

        if not self.selenium:
            if not browser_to_run.startswith("*"):
                browser_to_run = "*%s" % browser_to_run
            self.selenium = selenium(host, port, browser_to_run, url)

        try:
            self.selenium.start()
        except Exception, e:
            raise DriverError("Error when starting selenium. Is it running?\n\n\n Error: %s\n" % format_exc(e))

    def stop_test(self):
        self.stop_selenium()
    
    def stop_selenium(self):
        self.selenium.stop()

    def resolve_element_key(self, context, element_type, element_key):
        if not context:
            return element_key
        return SeleniumElementSelector.element(element_type, element_key)

    def page_open(self, url):
        self.selenium.open(url)

    def wait_for_page(self, timeout=30000):
        self.selenium.wait_for_page_to_load(timeout)

    def click_element(self, element_selector):
        self.selenium.click(element_selector)

    def get_title(self):
        return self.selenium.get_title()

    def is_element_visible(self, element_selector):
        error_message = "ERROR: Element %s not found" % (element_selector)
        is_present = self.selenium.is_element_present(element_selector)
        if is_present:
            try:
                is_present = self.selenium.is_visible(element_selector)
            except Exception, error:
                if error.message == error_message:
                    is_present = False
                else:
                    raise
        return is_present

    def is_element_enabled(self, element):
        script = """this.page().findElement("%s").disabled;"""

        script_return = self.selenium.get_eval(script % element)
        if script_return == "null":
            is_disabled = self.__get_attribute_value(element, "disabled")
        else:
            is_disabled = script_return[0].upper()=="T" # is it 'True'?
        return not is_disabled

    def wait_for_element_present(self, element_selector, timeout):
        elapsed = 0
        interval = 0.5

        while (elapsed < timeout):
            elapsed += interval
            if self.is_element_visible(element_selector):
                return True
            time.sleep(interval)

        return False

    def wait_for_element_to_disappear(self, element_selector, timeout):
        elapsed = 0
        interval = 0.5

        while (elapsed < timeout):
            elapsed += interval
            if not self.is_element_visible(element_selector):
                return True
            time.sleep(interval)

        return False

    def get_element_text(self, element_selector):
        text = ""
        tag_name_script = """this.page().findElement("%s").tagName;"""
        # escaping the user-made selector quotes
        element_selector = element_selector.replace('"', r'\"')
        tag_name = self.selenium.get_eval(tag_name_script % element_selector).lower()

        properties = {
                        "input" : "value",
                        "textarea" : "value",
                        "div" : "innerHTML"
                     }

        script = """this.page().findElement("%s").%s;"""
        try:
            # if the element is not in the dict above, I'll assume that we need to use "innerHTML"
            script_return = self.selenium.get_eval(script % (element_selector, properties.get(tag_name, "innerHTML")))
        except KeyError, err:
            raise ValueError("The tag for element selector %s is %s and Pyccuracy only supports the following tags: %s",
                             (element_selector, tag_name, ", ".join(properties.keys)))

        if script_return != "null":
            text = script_return

        return text

    def get_element_markup(self, element_selector):
        script = """this.page().findElement("%s").innerHTML;"""
        script_return = self.selenium.get_eval(script % element_selector)
        return script_return != "null" and script_return or ""

    def drag_element(self, from_element_selector, to_element_selector):
        self.selenium.drag_and_drop_to_object(from_element_selector, to_element_selector)

    def mouseover_element(self, element_selector):
        self.selenium.mouse_over(element_selector)

    def mouseout_element(self, element_selector):
        self.selenium.mouse_out(element_selector)

    def checkbox_is_checked(self, checkbox_selector):
        return self.selenium.is_checked(checkbox_selector)

    def checkbox_check(self, checkbox_selector):
        self.selenium.check(checkbox_selector)

    def checkbox_uncheck(self, checkbox_selector):
        self.selenium.uncheck(checkbox_selector)

    def get_selected_index(self, element_selector):
        return int(self.selenium.get_selected_index(element_selector))

    def get_selected_value(self, element_selector):
        return self.selenium.get_selected_value(element_selector)

    def get_selected_text(self, element_selector):
        return self.selenium.get_selected_label(element_selector)

    def select_option_by_index(self, element_selector, index):
        return self.__select_option(element_selector, "index", index)

    def select_option_by_value(self, element_selector, value):
        return self.__select_option(element_selector, "value", value)

    def select_option_by_text(self, element_selector, text):
        return self.__select_option(element_selector, "label", text)

    def get_select_options(self, element_selector):
        options = self.selenium.get_select_options(element_selector)
        return options

    def __select_option(self, element_selector, option_selector, option_value):
        error_message = "Option with %s '%s' not found" % (option_selector, option_value)
        try:
            self.selenium.select(element_selector, "%s=%s" % (option_selector, option_value))
        except Exception, error:
            if error.message == error_message:
                return False
            else:
                raise
        return True

    def is_element_empty(self, element_selector):
        current_text = self.get_element_text(element_selector)
        return current_text == ""

    def get_image_src(self, image_selector):
        return self.__get_attribute_value(image_selector, "src")

    def type_text(self, input_selector, text):
        self.selenium.type(input_selector, text)

    def type_keys(self, input_selector, text):
        self.selenium.type_keys(input_selector, text)

    def exec_js(self, js):
        return self.selenium.get_eval(js)

    def clean_input(self, input_selector):
        self.selenium.type(input_selector, "")

    def get_link_href(self, link_selector):
        return self.__get_attribute_value(link_selector, "href")

    def get_html_source(self):
        return self.selenium.get_html_source()

    def get_class(self, name):
        klass = self.__get_attribute_value(name, 'class')
        return klass

    def get_xpath_count(self, xpath):
        return self.selenium.get_xpath_count(xpath)

    def __get_attribute_value(self, element, attribute):
        try:
            locator = element + "/@" + attribute
            attr_value = self.selenium.get_attribute(locator)
        except Exception, inst:
            if "Could not find element attribute" in str(inst):
                attr_value = None
            else:
                raise
        return attr_value

    def radio_is_checked(self, radio_selector):
        return self.selenium.is_checked(radio_selector)

    def radio_check(self, radio_selector):
        self.selenium.check(radio_selector)

    def radio_uncheck(self, radio_selector):
        self.selenium.uncheck(radio_selector)
        
    def get_table_rows(self, table_selector):
        rows = []
        row_count = int(self.get_xpath_count(table_selector + "/tbody/tr"))
        
        for row_index in range(row_count):
            row = []
            cell_count = int(self.get_xpath_count(table_selector + 
                                                "/tbody/tr[%d]/td" % \
                                                (row_index + 1)))
            for cell_index in range(cell_count):
                cell = self.selenium.get_table(table_selector + '.%d.%d' % (
                                                row_index,
                                                cell_index
                                              ))
                row.append(cell)
            rows.append(row)

        return rows
    
    def __str__(self):
        return self.__unicode__()
    
    def __unicode__(self):
        return "SeleniumDriver at '%s:%s' using '%s' browser." % (self.context.settings.extra_args.get("selenium.server", "localhost"),
                self.context.settings.extra_args.get("selenium.port", 4444),
                self.context.settings.browser_to_run)
########NEW FILE########
__FILENAME__ = selenium_element_selector
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class SeleniumElementSelector(object):
    @staticmethod
    def element(element_type, element_name):
        if element_type == "element":
            return SeleniumElementSelector.generic(element_name)
        method = getattr(SeleniumElementSelector, element_type, SeleniumElementSelector.generic)
        return method(element_name)

    @staticmethod
    def generic(element_name):
        '''
        Returns a xpath that matches a generic element
        '''
        return r"//*[(@name='%s' or @id='%s')]" % (element_name, element_name)

    @staticmethod
    def button(element_name):
        '''
        Returns an xpath that matches input type="button", input type="submit" or button tags with
        the specified argument as id or name.
        '''
        return r"//input[(@name='%s' or @id='%s') and (@type='button' or @type='submit')] | //button[@name='%s' or @id='%s']" % (element_name, element_name, element_name, element_name)

    @staticmethod
    def radio_button(element_name):
        '''
        Returns an xpath that matches input type="radio" with the specified argument as id or name.
        '''
        return r"//input[(@name='%s' or @id='%s') and @type='radio']" % (element_name, element_name)

    @staticmethod
    def div(element_name):
        '''
        Returns an xpath that matches div tags with
        the specified argument as id or name.
        '''
        return r"//div[(@name='%s' or @id='%s')]" % (element_name, element_name)

    @staticmethod
    def link(element_name):
        '''
        Returns an xpath that matches link(a) tags with
        the specified argument as id or name.
        '''
        return r"//a[(@name='%s' or @id='%s' or contains(., '%s'))]" % \
                            (element_name, element_name, element_name)
    @staticmethod
    def checkbox(element_name):
        '''
        Returns an xpath that matches input type="checkbox" tags with
        the specified argument as id or name.
        '''
        return r"//input[(@name='%s' or @id='%s') and @type='checkbox']" % (element_name, element_name)

    @staticmethod
    def select(element_name):
        '''
        Returns an xpath that matches Select tags with
        the specified argument as id or name.
        '''
        return r"//select[@name='%s' or @id='%s']" % (element_name, element_name)

    @staticmethod
    def textbox(element_name):
        '''
        Returns an xpath that matches input type="text", input without type attribute or textarea tags with
        the specified argument as id or name.
        '''
        return r"//input[(@name='%s' or @id='%s') and (@type='text' or @type='password' or not(@type))] | //textarea[@name='%s' or @id='%s']" % (element_name, element_name, element_name, element_name)

    @staticmethod
    def image(element_name):
        '''
        Returns an xpath that matches img tags with
        the specified argument as id or name.
        '''
        return r"//img[@name='%s' or @id='%s']" % (element_name, element_name)

    @staticmethod
    def table(element_name):
        '''
        Returns an xpath that matches table tags with
        the specified argument as id or name.
        '''
        return r"//table[@name='%s' or @id='%s']" % (element_name, element_name)
########NEW FILE########
__FILENAME__ = selenium_webdriver
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2011 Iraê Carvalho <irae@irae.pro.br>
# Copyright (C) 2011 Luiz Tadao Honda <lhonda@yahoo-inc.com>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import re

selenium_available = True
# try:
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.select import Select
from selenium.common.exceptions import NoSuchElementException
# except ImportError:
#     selenium_available = False

from pyccuracy.drivers import BaseDriver, DriverError
from selenium_element_selector import *

class SeleniumWebdriver(BaseDriver):
    backend = 'webdriver'

    def __init__(self, context):
        self.webdriver = None
        self.context = context
        if not selenium_available:
            raise RuntimeError('You *MUST* have selenium version 2+ installed to use the selenium webdriver')

    def start_driver(self):
        '''Create our driver instance'''
        host = self.context.settings.extra_args.get("selenium.server", "localhost")
        port = self.context.settings.extra_args.get("selenium.port", 4444)
        server_url = 'http://%s:%s/wd/hub' % (host, str(port))
        browser_to_run = self.context.settings.browser_to_run

        if hasattr(webdriver.DesiredCapabilities, browser_to_run.upper()):
            browser_to_run = getattr(webdriver.DesiredCapabilities, browser_to_run.upper())

        self.webdriver = webdriver.Remote(server_url, browser_to_run)


    def start_test(self, url=None):
        '''Start one task'''
        if not self.webdriver:
            self.start_driver()

        self.webdriver.get(url)

    def stop_test(self):
        '''Closes browser window.'''
        self.webdriver.quit()

    def exec_js(self, js):
        return self.webdriver.execute_script(js)

    def _get_element(self, element_selector):
        found_element = None
        if element_selector.startswith('//') or element_selector.startswith('xpath')  :
            found_element = self.webdriver.find_element_by_xpath(element_selector)
        else:
            found_element = self.webdriver.find_element_by_css_selector(element_selector)

        return found_element

    def resolve_element_key(self, context, element_type, element_key):
        return SeleniumElementSelector.element(element_type, element_key)

    def page_open(self, url):
        self.webdriver.get(url)

    def clean_input(self, input_selector):
        self._get_element(input_selector).clear()

    def type_text(self, input_selector, text):
        return self._get_element(input_selector).send_keys(text)

    def type_keys(self, input_selector, text):
        self.type_text(input_selector, text)

    def click_element(self, element_selector):
        return self._get_element(element_selector).click()

    def is_element_visible(self, element_selector):
        try:
            return self._get_element(element_selector).is_displayed()
        except NoSuchElementException:
            return False

    def wait_for_page(self, timeout=30000):
        pass
        # the new recomendation from selenium is to watch for an element only
        # present with the new situation, all wait functions were dropped

    def get_title(self):
        return self.webdriver.title

    def is_element_enabled(self, element):
        return self._get_element(element).is_enabled()

    def checkbox_is_checked(self, checkbox_selector):
        return self._get_element(checkbox_selector).is_selected()

    def checkbox_check(self, checkbox_selector):
        check = self._get_element(checkbox_selector)
        if not check.is_selected():
            check.click()

    def checkbox_uncheck(self, checkbox_selector):
        check = self._get_element(checkbox_selector)
        if check.is_selected():
            check.click()

    def radio_is_checked(self, radio_selector):
        return self.checkbox_is_checked(radio_selector)

    def radio_check(self, radio_selector):
        return self.checkbox_check(radio_selector)

    def radio_uncheck(self, radio_selector):
        return self.checkbox_uncheck(radio_selector)

    def _get_select(self, select_selector):
        return Select(self._get_element(select_selector))

    def get_selected_index(self, element_selector):
        text = self.get_selected_text(element_selector)
        options = self.get_select_options(element_selector)
        return options.index(text)

    def get_selected_value(self, element_selector):
        return self._get_select(element_selector).first_selected_option.get_attribute('value')

    def get_selected_text(self, element_selector):
        return self._get_select(element_selector).first_selected_option.text

    def get_select_options(self, select):
        return [x.text for x in self._get_select(select).options]

    def get_element_text(self, element_selector):
        element = self._get_element(element_selector)
        tagname = element.get_attribute('tagName').lower()
        if tagname == 'input' or tagname == 'textarea':
            return element.get_attribute('value')
        else:
            return element.text

    def get_class(self, element_selector):
        return self._get_element(element_selector).get_attribute('className')

    def get_element_markup(self, element_selector):
        got = self._get_element(element_selector).get_attribute('innerHTML')
        return got != "null" and got or ""

    def get_html_source(self):
        return self.webdriver.page_source

    def select_option_by_index(self, element_selector, index):
        try:
            self._get_select(element_selector).select_by_index(index)
        except:
            return False
        return True

    def select_option_by_value(self, element_selector, value):
        try:
            self._get_select(element_selector).select_by_value(value)
        except:
            return False
        return True

    def select_option_by_text(self, element_selector, text):
        try:
            self._get_select(element_selector).select_by_visible_text(text)
        except:
            return False
        return True

    def get_link_href(self, link_selector):
        return self._get_element(link_selector).get_attribute('href')

    def get_image_src(self, image_selector):
        full_src = self._get_element(image_selector).get_attribute('src')
        # must return only filename
        src = re.sub(r'.*/','', full_src)
        return src

    def get_link_text(self, link_selector):
        return self._get_element(link_selector).text

    def mouseover_element(self, element_selector):
        chain = ActionChains(self.webdriver)
        chain.move_to_element(self._get_element(element_selector))
        chain.perform()

    def mouseout_element(self, element_selector):
        chain = ActionChains(self.webdriver)
        chain.move_by_offset(-10000,-10000)
        chain.perform()

    def is_element_empty(self, element_selector):
        return self.get_element_text(element_selector) == ""

    def wait_for_element_present(self, element_selector, timeout):
        elapsed = 0
        interval = 0.5

        while (elapsed < timeout):
            elapsed += interval
            try:
                elem = self._get_element(element_selector)
                if elem.is_displayed():
                    return True
            except NoSuchElementException:
                pass
            time.sleep(interval)

        return False

    def wait_for_element_to_disappear(self, element_selector, timeout):
        elapsed = 0
        interval = 0.5

        while (elapsed < timeout):
            elapsed += interval
            try:
                elem = self._get_element(element_selector)
            except NoSuchElementException:
                return True
            if not elem.is_displayed():
                return True
            time.sleep(interval)

        return False

    def drag_element(self, from_element_selector, to_element_selector):
        chain = ActionChains(self.webdriver)
        chain.drag_and_drop(self._get_element(from_element_selector),self._get_element(to_element_selector))
        chain.perform()

    def get_table_rows(self, table_selector):
        table = self._get_element(table_selector)
        rows = []
        row_elems = table.find_elements_by_tag_name('tr')

        for row_elem in row_elems:
            row = []
            cel_elems = row_elem.find_elements_by_tag_name('td')

            for cell_elem in cel_elems:
                row.append(cell_elem.text)

            rows.append(row)

        return rows

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "SeleniumWebdriver at '%s:%s' using '%s' browser." % (self.context.settings.extra_args.get("selenium.server", "localhost"),
                self.context.settings.extra_args.get("selenium.port", 4444),
                self.context.settings.browser_to_run)
########NEW FILE########
__FILENAME__ = interface
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class DriverInterface(object):
    """ This class contains only, those methods that must be
    implemented by browser drivers"""

    def start_test(self, url=None):
        '''This method is responsible for starting a test, whether this means opening a browser window, connecting to some remote server or anything else.
        
This method is called before any scenarios begin.'''
        raise NotImplementedError

    def stop_test(self):
        '''This method is responsible for cleaning up after a test run. This method is calledo only once after all scenarios are run.'''
        raise NotImplementedError

    def resolve_element_key(self, context, element_type, element_key):
        '''This method is responsible for transforming the element key for the given element type in something that the browser driver understands.
        
        i.e.:
            resolve_element_key(context, 'some', 'textbox')
            this method call would go into context, get the current page, verify the xpath or css selector for the specified element and then return it.
        
        You are free to implement this any way you'd like, though. One could implement this to return elements like:
            element type.element name as css selector, so a div with name myDiv would return div.myDiv.
'''
        raise NotImplementedError

    def get_xpath_count(self, xpath):
        '''Returns the number of occurrences in the current document for the given xpath.'''        
        raise NotImplementedError

    def page_open(self, url):
        '''This method navigates the browser to the given url.'''
        raise NotImplementedError

    def clean_input(self, input_selector):
        '''This method wipes the text out of the given textbox'''
        raise NotImplementedError

    def type_text(self, input_selector, text):
        '''This method types (enter it) the given text in the specified input'''
        raise NotImplementedError

    def click_element(self, element_selector):
        '''This method clicks in the given element'''
        raise NotImplementedError

    def is_element_visible(self, element_selector):
        '''This method returns True if the element is visible. False otherwise.'''
        raise NotImplementedError

    def wait_for_page(self, timeout=0):
        '''This method waits until the page is loaded, or until it times out'''
        raise NotImplementedError

    def get_title(self):
        '''This method returns the title for the currently loaded document in the browser.'''
        raise NotImplementedError

    def is_element_enabled(self, element):
        '''This method returns whether the given element is enabled.'''
        raise NotImplementedError

    def checkbox_is_checked(self, checkbox_selector):
        '''This method returns whether the given checkbox is checked.'''
        raise NotImplementedError

    def checkbox_check(self, checkbox_selector):
        '''This method checks the specified checkbox.'''
        raise NotImplementedError

    def checkbox_uncheck(self, checkbox_selector):
        '''This method unchecks the specified checkbox.'''
        raise NotImplementedError

    def get_selected_index(self, element_selector):
        '''This method gets the selected index for the given select.'''
        raise NotImplementedError

    def get_selected_value(self, element_selector):
        '''This methid gets the value for the currently selected option in the given select.'''
        raise NotImplementedError

    def get_selected_text(self, element_selector):
        '''This methid gets the text for the currently selected option in the given select.'''
        raise NotImplementedError

    def get_element_text(self, element_selector):
        '''This method gets the text for the given element. This might mean different things for different element types (inner html for a div, value for a textbox, and so on).'''
        raise NotImplementedError

    def get_element_markup(self, element_selector):
        '''This method gets the given element markup.'''
        raise NotImplementedError

    def get_html_source(self):
        '''This method gets the whole source for the currently loaded document in the web browser.'''
        raise NotImplementedError

    def select_option_by_index(self, element_selector, index):
        '''This method selects an option in the given select by it's index.'''
        raise NotImplementedError

    def select_option_by_value(self, element_selector, value):
        '''This method selects the option that has the specified value in the given select.'''
        raise NotImplementedError

    def select_option_by_text(self, element_selector, text):
        '''This method selects the option that has the specified text in the given select.'''
        raise NotImplementedError

    def get_link_href(self, link_selector):
        '''This method returns the href attribute for the specified link.'''
        raise NotImplementedError

    def get_image_src(self, image_selector):
        '''This method returns the src attribute for the specified image.'''
        raise NotImplementedError

    def get_link_text(self, link_selector):
        '''This method gets the text for the specified link.'''
        raise NotImplementedError

    def mouseover_element(self, element_selector):
        '''This method triggers the mouse over event for the specified element.'''
        raise NotImplementedError

    def mouseout_element(self, element_selector):
        '''This method triggers the mouse out event for the specified element.'''
        raise NotImplementedError

    def is_element_empty(self, element_selector):
        '''This method returns whether the specified element has no text.'''
        raise NotImplementedError

    def wait_for_element_present(self, element_selector, timeout):
        '''This method waits for the given element to appear (become visible) or for the timeout. If it times out, the current scenario will fail.'''
        raise NotImplementedError

    def wait_for_element_to_disappear(self, element_selector, timeout):
        '''This method waits for the given element to disappear (become hidden or already be hidden) or for the timeout. If it times out, the current scenario will fail.'''
        raise NotImplementedError

    def drag_element(self, from_element_selector, to_element_selector):
        '''This method drags the from element to the to element.'''
        raise NotImplementedError

    def get_select_options(self, select):
        '''This method returns a list of options for the given select.'''
        raise NotImplementedError
    
    def get_table_rows(self, table_key):
        '''This method returns a list of rows for the given table.'''
        raise NotImplementedError
        
########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

class TestFailedError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return unicode(self.message)

class ActionFailedError(AssertionError):
    def __unicode__(self):
        return self.message

class InvalidScenarioError(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return unicode(self.message)

    def __unicode__(self):
        return self.message

class LanguageParseError(Exception):
    def __init__(self, culture, file_path, error_message = "The language file for %s could not be parsed at %s!"):
        self.culture = culture
        self.error_message = error_message
        self.file_path = file_path

    def __str__(self):
        return unicode(self.error_message) % (self.culture, self.file_path)

class SelectOptionError(Exception):
    def __init__(self, message):
        self.message = message
        print message

    def __str__(self):
        return unicode(self.message)

    def __unicode__(self):
        return self.message

class WrongArgumentsError(Exception):
    pass

class LanguageDoesNotResolveError(Exception):
    pass

########NEW FILE########
__FILENAME__ = fixture
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import operator

from pyccuracy.fixture_items import *
from pyccuracy.common import TimedItem, Status

class Fixture(TimedItem):
    def __init__(self):
        TimedItem.__init__(self)
        self.clear()

    def clear(self):
        self.invalid_test_files = []
        self.no_story_header = []
        self.stories = []

    def append_invalid_test_file(self, path, error):
        self.invalid_test_files.append((path, error))

    def append_no_story_header(self, path):
        self.no_story_header.append(path)

    def append_story(self, story):
        self.stories.append(story)
        return story

    def get_status(self):
        status = Status.Unknown
        for story in self.stories:
            if story.status == Status.Failed:
                return Status.Failed
            if story.status == Status.Successful:
                status = story.status
        return status

    def count_total_stories(self):
        return len(self.stories)

    def count_total_scenarios(self):
        return sum([len(story.scenarios) for story in self.stories])

    def count_successful_stories(self):
        return self.count_stories_by_status(Status.Successful)

    def count_failed_stories(self):
        return self.count_stories_by_status(Status.Failed)

    def count_stories_by_status(self, status):
        return len([story for story in self.stories if story.status == status])

    def count_successful_scenarios(self):
        return self.count_scenarios_by_status(Status.Successful)

    def count_failed_scenarios(self):
        return self.count_scenarios_by_status(Status.Failed)

    def count_scenarios_by_status(self, status):
        return len(self.get_scenarios_by_status(status))

    def get_successful_scenarios(self):
        return self.get_scenarios_by_status(Status.Successful)

    def get_failed_scenarios(self):
        return self.get_scenarios_by_status(Status.Failed)

    def get_scenarios_by_status(self, status):
        all_scenarios = []
        map(lambda item: all_scenarios.extend(item), [story.scenarios for story in self.stories])
        return [scenario for scenario in all_scenarios if scenario.status==status]

    def __str__(self):
        return self.get_results()

########NEW FILE########
__FILENAME__ = fixture_items
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import traceback

from pyccuracy.actions import ActionNotFoundError
from pyccuracy.errors import *
from pyccuracy.common import StatusItem, TimedItem, Status

class Story(StatusItem, TimedItem):
    '''Class that represents a story to be run by Pyccuracy.
    Contains zero or many scenarios to be run.'''
    def __init__(self, as_a, i_want_to, so_that, identity):
        StatusItem.__init__(self, parent=None)
        TimedItem.__init__(self)
        self.as_a = as_a
        self.i_want_to = i_want_to
        self.so_that = so_that
        self.identity = identity
        self.scenarios = []

    def append_scenario(self, index, title):
        scenario = Scenario(self, index, title)
        self.scenarios.append(scenario)
        return scenario

    def __unicode__(self):
        return "Story - As a %s I want to %s So that %s (%d scenarios) - %s" % \
                (self.as_a, self.i_want_to, self.so_that, len(self.scenarios), self.status)

    def __str__(self):
        return unicode(self)

class Scenario(StatusItem, TimedItem):
    def __init__(self, story, index, title):
        StatusItem.__init__(self, parent=story)
        TimedItem.__init__(self)

        self.story = story
        self.index = index
        self.title = title
        self.givens = []
        self.whens = []
        self.thens = []

    def add_given(self, action_description, execute_function, args, kwargs):
        action = Action(self, action_description, execute_function, args, kwargs)
        self.givens.append(action)
        return action

    def add_when(self, action_description, execute_function, args, kwargs):
        action = Action(self, action_description, execute_function, args, kwargs)
        self.whens.append(action)
        return action

    def add_then(self, action_description, execute_function, args, kwargs):
        action = Action(self, action_description, execute_function, args, kwargs)
        self.thens.append(action)
        return action

    def __unicode__(self):
        return "Scenario %s - %s (%d givens, %d whens, %d thens) - %s" % \
                (self.index, self.title, len(self.givens), len(self.whens), len(self.thens), self.status)
    def __str__(self):
        return unicode(self)

class Action(StatusItem, TimedItem):
    def __init__(self, scenario, description, execute_function, args, kwargs):
        StatusItem.__init__(self, parent=scenario)
        TimedItem.__init__(self)

        self.scenario = scenario
        self.description = description
        self.number_of_lines = len(description.split('\n'))
        self.execute_function = execute_function
        self.args = args
        self.kwargs = kwargs

    def execute(self, context):
        if context.settings.on_before_action:
            context.settings.on_before_action(context, self, self.args, self.kwargs)
        try:
            self.execute_function(context, *self.args, **self.kwargs)
            if context.settings.on_action_successful:
                context.settings.on_action_successful(context, self, self.args, self.kwargs)
        except ActionNotFoundError:
            raise
        except AssertionError, err:
            if context.settings.on_action_error:
                context.settings.on_action_error(context, self, self.args, self.kwargs, err)
            self.mark_as_failed(err)
            return False
        except Exception, err:
            if context.settings.on_action_error:
                context.settings.on_action_error(context, self, self.args, self.kwargs, err)
            self.mark_as_failed(ValueError("Error executing action %s - %s" % (self.execute_function, traceback.format_exc(err))))
            return False

        self.mark_as_successful()
        return True

    def __unicode__(self):
        return "Action %s - %s" % (self.description, self.status)
    def __str__(self):
        return unicode(self)


########NEW FILE########
__FILENAME__ = help
# coding: utf-8
import os
import re

CURR_DIR = os.path.dirname(__file__) or '.'

class LanguageViewer(object):
    ACTIONS = ['page', 'button', 'checkbox', 'div', 'image', 
            'link', 'radio', 'select', 'textbox', 'element', ]

    def __init__(self, language='en-us'):
        self.languages_dir = CURR_DIR + '/languages/data'
        self.language = language
        self.actions = {}
        self._set_all_actions()
    
    def _set_all_actions(self):
        language_filename = os.path.join(self.languages_dir, '%s.txt' % self.language)

        if not os.path.exists(language_filename):
            raise Exception, 'Language file not found: %s' % language_filename

        language_file = open(language_filename)

        possible_action_lines = []
        for line in language_file:
            line = line.strip()
            if not line.startswith('#') and '=' in line:
                values = line.split('=')
                left = values[0].strip()
                right = "=".join(values[1:]).strip()
                splitted_left_operand = left.split('_')
                if splitted_left_operand[-1] == 'regex' and splitted_left_operand[0] in self.ACTIONS:
                    action_name = '_'.join(splitted_left_operand[:-1])
                    new_right_value = self.make_it_readable(right)
                    self.actions[action_name] = new_right_value

        language_file.close()

    def make_it_readable(self, value):
        url_regex = "(?P<url>[\\\"](([\w:/._-]|\=|\?|\&|\\\"|\;|\%)+)[\\\"]|([\w\s_.-]+))$"
        value = value.replace(url_regex, '[page|"url"]') #replace urls
        value = value.replace('(?P<url>([\w\s_.-]+))', 'page')
        value = value.replace('(?P<parameters>.+)', 'parameters')
        value = re.sub(r'\(\?\P\<([\w\s]*)\>\<([\w\s]*)\>\)', r'[\1|\2]', value)
        value = re.sub(r'\(\?\P\<([\w\s]*)\>\[\^\"\]\+\)', r'\1', value)
        value = re.sub(r'\(\?\P\<([\w\s]*)\>\.\+\)', r'\1', value)
        value = re.sub(r'\(\?\P\<([\w\s]*)\>\\d\+\)', r'X', value)
        value = re.sub(r'\(\?\P\<\w\>(.*)\)', r'\1', value)
        value = re.sub(r'\(\?\P\<\w*\>\\d\+\(\[\.\]\\d\+\)\?\)', '[X|X.X]', value)
        value = re.sub(r'\P\<\w*\>', '', value)
        value = value.replace('[\\"]', '"') #replace quotes
        value = value.replace('(.+)', 'blah') #replace random text
        value = value.replace('\d+', 'X').replace('(X)', 'X') #replace digits
        value = value.replace('[\\\"\\\']', '"').replace('[\\\'\\\"]', '"') #replace quotes
        value = value.replace('X([.]X)?', '[X|X.X]')
        value = value.replace('?', '').replace('$', '').replace('^', '')
        value = value.replace('{1}', '')
        return value

    def get_actions(self, term):
        matches = {}
        for key in self.actions.keys():
            if term in key:
                matches[key] = self.actions.get(key)
            
        return matches

########NEW FILE########
__FILENAME__ = hooks
from pyccuracy.colored_terminal import TerminalController

HOOKS = {'after_tests':[], 'before_tests':[]}

class Hooks(object):
    
    #TODO: refactor - merge after & before methods
    @classmethod
    def execute_after_tests(cls, results):
        if len(HOOKS['after_tests']) > 0:
            ctrl = TerminalController()
            hooks_feedback = ctrl.render('${CYAN}')

            for hook in HOOKS['after_tests']:
                hook().execute(results)
                hooks_feedback += ctrl.render('[HOOKS] AfterTestsHook "%s" executed.\n' % hook)

            hooks_feedback += ctrl.render('${NORMAL}')
            hooks_feedback += "\n"

            print hooks_feedback

    @classmethod
    def execute_before_tests(cls):
        if len(HOOKS['before_tests']) > 0:
            ctrl = TerminalController()
            hooks_feedback = ctrl.render('${CYAN}')

            for hook in HOOKS['before_tests']:
                hook().execute()
                hooks_feedback += ctrl.render('[HOOKS] BeforeTestsHook "%s" executed.\n' % hook)

            hooks_feedback += ctrl.render('${NORMAL}')
            hooks_feedback += "\n"

            print hooks_feedback
    
    @classmethod
    def reset(cls):
        HOOKS['after_tests'] = []
        HOOKS['before_tests'] = []

class MetaHookBase(type):
    def __init__(cls, name, bases, attrs):
        if name not in ('AfterTestsHook', 'BeforeTestsHook' ):
            if 'execute' not in attrs:
                raise NotImplementedError("The hook %s does not implement the method execute()" % name)

            # registering
            if AfterTestsHook in bases:
                HOOKS['after_tests'].append(cls)
            
            if BeforeTestsHook in bases:
                HOOKS['before_tests'].append(cls)

        super(MetaHookBase, cls).__init__(name, bases, attrs)

class AfterTestsHook(object):
    __metaclass__ = MetaHookBase

class BeforeTestsHook(object):
    __metaclass__ = MetaHookBase
########NEW FILE########
__FILENAME__ = page
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os.path import abspath, exists
from urlparse import urljoin
lxml_available = True
try:
    from lxml import cssselect
except ImportError:
    lxml_available = False
from pyccuracy.common import Settings, URLChecker

NAME_DICT = {}
URL_DICT = {}
ALL_PAGES = []

class InvalidUrlError(Exception):
    pass

class ElementAlreadyRegisteredError(Exception):
    pass

class MetaPage(type):
    def __init__(cls, name, bases, attrs):
        if name not in ('MetaPage', 'Page'):

            if not attrs.has_key('url'):
                raise NotImplementedError('%r does not contain the attribute url' % cls)

            url = attrs['url']
            if not isinstance(url, basestring):
                raise TypeError('%s.url must be a string or unicode. Got %r(%r)' % (name, url.__class__, url))

            NAME_DICT[name] = cls
            if URL_DICT.has_key(url):
                URL_DICT[url].insert(0, cls)
            else:
                URL_DICT[url] = [cls]
            
            ALL_PAGES.append(cls)

        super(MetaPage, cls).__init__(name, bases, attrs)

class PageRegistry(object):
    @classmethod
    def get_by_name(cls, name):
        name = name.replace(" ", "")
        return NAME_DICT.get(name)

    @classmethod
    def get_by_url(cls, name):
        klass_list = cls.all_by_url(name)
        if klass_list:
            return klass_list[0]

    @classmethod
    def resolve(cls, settings, url, must_raise=True, abspath_func=abspath, exists_func=exists):
        """Resolves a url given a string and a settings. Raises
        TypeError when parameters are wrong, unless the must_raise
        parameter is False"""

        if not isinstance(settings, Settings):
            if must_raise:
                raise TypeError('PageRegistry.resolve takes a pyccuracy.common.Settings object first parameter. Got %r.' % settings)
            else:
                return None

        if not isinstance(url, basestring):
            if must_raise:
                raise TypeError('PageRegistry.resolve argument 2 must be a string. Got %r.' % url)
            else:
                return None

        klass_object = cls.get_by_name(url) or cls.get_by_url(url)
        if klass_object:
            url = klass_object.url

        url_pieces = []

        if not url.startswith("http"):
            if settings.base_url:
                url_pieces.append(settings.base_url)
            else:
                url_pieces.append(settings.tests_dirs[0]) #gotta think of a way to fix this
        
        if klass_object:
            url_pieces.append(klass_object.url)
            
            if hasattr(klass_object, 'port') and url_pieces[0].startswith("http"):
                url_pieces[0] = "%s:%d" % (url_pieces[0], klass_object.port)
        else:
            url_pieces.append(url)
        
        # if use os.path.join here, will not work on windows

        fix = lambda x: x.replace('//', '/').replace('http:/', 'http://').replace('https:/', 'https://')
        final_url = fix("/".join(url_pieces))

        if not "://" in final_url:
            almost_final_url = (final_url.startswith("/") and final_url) or "/%s" % final_url
            final_url = "file://%s" % abspath_func(almost_final_url)

        if final_url.startswith("/"):
            final_url = final_url[1:]

        checker = URLChecker()
        checker.set_url(final_url)
        if not checker.is_valid():
            error_message = "The url %r is not valid." % final_url
            if klass_object:
                error_message += " In class %s, path %r" % (klass_object.__name__, klass_object.__module__)

            if not final_url.startswith('file://'):
                raise InvalidUrlError(error_message)

        return klass_object, final_url

    @classmethod
    def all_by_url(cls, url):
        return URL_DICT.get(url)

class Page(object):
    '''Class that defines a page model.'''
    __metaclass__ = MetaPage

    got_element_event_handlers = []

    Button = "button"
    Checkbox = "checkbox"
    Div = "div"
    Image = "image"
    Link = "link"
    Page = "page"
    RadioButton = "radio_button"
    Select = "select"
    Textbox = "textbox"
    Table = "table"
    Element = '*'

    def __init__(self):
        '''Initializes the page with the given url.'''
        self.registered_elements = {}
        if hasattr(self, "register"):
            self.register()

    @classmethod
    def all(cls):
        return ALL_PAGES

    @classmethod
    def subscribe_to_got_element(cls, subscriber):
        cls.got_element_event_handlers.append(subscriber)

    def fire_got_element(self, element_key, resolved_key):
        for subscriber in self.got_element_event_handlers:
            subscriber(self, element_key, resolved_key)

    def get_registered_element(self, element_key):
        if not self.registered_elements.has_key(element_key):
            return None
        resolved_key = self.registered_elements[element_key]
        self.fire_got_element(element_key, resolved_key)
        return resolved_key

    def register_element(self, element_key, element_locator):
        if self.registered_elements.has_key(element_key) and self.get_registered_element(element_key) != element_locator:
            error_message = "You are trying to register an element with name '%s' in %s with locator '%s', but it is already registered with a different locator ('%s')." % (element_key, self.__class__, element_locator, self.get_registered_element(element_key))
            raise ElementAlreadyRegisteredError(error_message)
        self.registered_elements[element_key] = element_locator

    def quick_register(self, element_key, element_selector):
        if not lxml_available:
            raise RuntimeError("You can't use CSS selectors unless you install lxml. Installing it is pretty easy. Check our docs at http://www.pyccuracy.org to know more.")
        selector = cssselect.CSSSelector(element_selector)
        xpath = selector.path.replace("descendant-or-self::", "//")
        self.register_element(element_key, xpath)

########NEW FILE########
__FILENAME__ = parsers
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import os

from pyccuracy import ActionRegistry
from pyccuracy.actions import ActionNotFoundError
from pyccuracy.languages import LanguageGetter
from pyccuracy.common import locate
from pyccuracy.fixture import Fixture
from pyccuracy.fixture_items import Story, Action, Scenario

ident_re = re.compile(r'^(?P<ident>[ \t]*)')

class InvalidScenarioError(RuntimeError):
    pass

class FSO(object):
    '''Actual Filesystem'''
    def list_files(self, directories, pattern):
        files = []
        for directory in directories:
            files.extend(locate(root=directory, pattern=pattern))
        return files

    def read_file(self, file_path):
        return open(file_path).read().decode('utf-8')

class FileParser(object):
    def __init__(self, language=None, file_object=None, action_registry=None):
        self.file_object = file_object and file_object or FSO()
        self.action_registry = action_registry and action_registry or ActionRegistry
        self.language = language
        self.used_actions = []

    def get_stories(self, settings):
        if not self.language:
            self.language = LanguageGetter(settings.default_culture)

        fixture = Fixture()

        story_file_list = self.file_object.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
        story_file_list.sort()

        for story_file_path in story_file_list:
            try:
                parsed, error, story = self.parse_story_file(story_file_path, settings)
                if parsed:
                    fixture.append_story(story)
                else:
                    fixture.append_no_story_header(story_file_path)
            except IOError, err:
                fixture.append_invalid_test_file(story_file_path, err)
            except InvalidScenarioError, verr:
                fixture.append_no_story_header(story_file_path)
        return fixture

    def parse_story_file(self, story_file_path, settings):
        story_text = self.file_object.read_file(story_file_path)
        story_lines = [line for line in story_text.splitlines() if line.strip() != ""]

        headers = self.assert_header(story_lines, settings.default_culture)
        if not headers:
            return (False, self.language.get('no_header_failure'), None)

        as_a = headers[0]
        i_want_to = headers[1]
        so_that = headers[2]

        current_story = Story(as_a=as_a, i_want_to=i_want_to, so_that=so_that, identity=story_file_path)

        scenario_lines = story_lines[3:]

        current_scenario = None
        offset = 0
        for line_index, line in enumerate(scenario_lines):
            if offset > 0:
                offset -= 1
                continue
            offset = 0
            if self.is_scenario_starter_line(line):
                current_scenario = self.parse_scenario_line(current_story, line, settings)
                current_area = None
                continue

            if self.is_keyword(line, "given"):
                current_area = "given"
                continue
            if self.is_keyword(line, "when"):
                current_area = "when"
                continue
            if self.is_keyword(line, "then"):
                current_area = "then"
                continue

            if current_scenario is None:
                if settings.scenarios_to_run:
                    continue
                else:
                    raise InvalidScenarioError("NoScenario")

            if not current_area:
                raise InvalidScenarioError("NoGivenWhenThen")

            add_method = getattr(current_scenario, "add_%s" % current_area)

            if line.strip().startswith("#"):
                add_method(line, lambda context, *args, **kwargs: None, [], {})
                continue

            action, args, kwargs = self.action_registry.suitable_for(line.strip(), settings.default_culture)
            
            rows = []
            parsed_rows = []
            if line.strip().endswith(':'):
                if line_index >= len(scenario_lines):
                    self.raise_action_not_found_for_line(line, current_scenario, story_file_path)
                
                offset, rows, parsed_rows = self.parse_rows(line_index, 
                                                            line, 
                                                            scenario_lines)
                args=[]

            if not action:
                self.raise_action_not_found_for_line(line, current_scenario, story_file_path)
            
            if not action in self.used_actions:
                self.used_actions.append(action)

            instance = action()
            if kwargs:
                args = []
            instance.number_of_rows = 1
            
            parsed_line = line
            if parsed_rows:
                kwargs['table'] = parsed_rows
                
                for row in rows:
                    parsed_line = parsed_line + "\n%s%s" % ("  " * \
                                (self.get_line_identation(line) + 4),\
                                row)

            add_method(parsed_line, instance.execute, args, kwargs)

        return (True, None, current_story)

    def parse_rows(self, line_index, line, scenario_lines):
        line_identation = self.get_line_identation(line)

        offset = 1

        next_line_index = line_index + offset
        next_line = scenario_lines[next_line_index]
        next_line_identation = self.get_line_identation(next_line)
        
        rows = []
        parsed_rows = []
        keys = None

        while (next_line_identation > line_identation):
            rows.append(next_line)
            values = [cell.strip(' ') for cell 
                                      in next_line.split('|') 
                                      if cell.strip(' ')]
            
            if not keys:
                keys = values
            else:
                row = {}
                for cell_index, cell in enumerate(values):
                    row[keys[cell_index]] = cell
                parsed_rows.append(row)
            
            offset += 1
            next_line_index = line_index + offset

            if next_line_index == len(scenario_lines):
                break

            next_line = scenario_lines[next_line_index]
            next_line_identation = self.get_line_identation(next_line)
        
        return offset - 1, rows, parsed_rows

    def get_line_identation(self, line):
        ident = ident_re.match(line).groupdict()['ident']
        return len(ident)

    def assert_header(self, story_lines, culture):
        as_a = self.language.get('as_a')
        i_want_to = self.language.get('i_want_to')
        so_that = self.language.get('so_that')

        if len(story_lines) < 3:
            return []

        if not as_a in story_lines[0] \
           or not i_want_to in story_lines[1] \
           or not so_that in story_lines[2]:
            return []

        return [story_lines[0].replace(as_a, "").strip(),
                 story_lines[1].replace(i_want_to, "").strip(),
                 story_lines[2].replace(so_that, "").strip()]

    def is_scenario_starter_line(self, line):
        scenario_keyword = self.language.get('scenario')
        return line.strip().startswith(scenario_keyword)

    def is_keyword(self, line, keyword):
        keyword = self.language.get(keyword)
        return line.strip() == keyword

    def parse_scenario_line(self, current_story, line, settings):
        scenario_keyword = self.language.get('scenario')
        scenario_values = line.split(u'-', 1)
        index = scenario_values[0].replace(scenario_keyword,"").strip()
        title = scenario_values[1].strip()
        current_scenario = None
        if not settings.scenarios_to_run or index in settings.scenarios_to_run:
            current_scenario = current_story.append_scenario(index, title)
        return current_scenario

    def raise_action_not_found_for_line(self, line, scenario, filename):
        raise ActionNotFoundError(line, scenario, filename)

########NEW FILE########
__FILENAME__ = pyccuracy_console
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import codecs
import os
import textwrap
import sys, optparse
from pyccuracy.core import PyccuracyCore
from pyccuracy.common import Status
from pyccuracy.story_runner import StoryRunner, ParallelStoryRunner
from pyccuracy import Version, Release
from pyccuracy.colored_terminal import ProgressBar, TerminalController

__version_string__ = "pyccuracy %s (release '%s')" % (Version, Release)
__docformat__ = 'restructuredtext en'

# fixing print in non-utf8 terminals
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

no_progress = False
prg = None
scenarios_ran = 0
ctrl = TerminalController()

def position(level, message, offset=4):
    offset_message = (level * offset) * " "
    line = "%s%s" % (offset_message, message)
    return line

def section_started_handler(section):
    print ctrl.render("${YELLOW}%s${NORMAL}" % position(1, section))

def before_action(context, action, args, kwarg):
    print ctrl.render("${WHITE}%s${NORMAL}" % position(2, action.description))

def action_successful(context, action, args, kwarg):
    print ctrl.render((ctrl.BOL + ctrl.UP + ctrl.CLEAR_EOL) * action.number_of_lines + "${GREEN}%s${NORMAL}" % position(2, action.description))

def action_error(context, action, args, kwarg, error):
    print ctrl.render((ctrl.BOL + ctrl.UP + ctrl.CLEAR_EOL) * action.number_of_lines + "${RED}%s${NORMAL}" % position(2, action.description))

def scenario_started(fixture, scenario, scenario_index):
    global scenarios_ran

    total_scenarios = fixture.count_total_scenarios()
    scenario_message = "Scenario %d of %d <%.2f%%> - %s" % (scenarios_ran + 1, total_scenarios, (float(scenarios_ran) / float(total_scenarios) * 100), scenario.title)
    print
    print ctrl.render("${NORMAL}%s" % position(0, scenario_message))

def scenario_completed(fixture, scenario, scenario_index):
    global scenarios_ran

    scenarios_ran += 1

def create_progress(verbosity):
    global no_progress
    global prg
    global scenarios_ran

    if verbosity == 3:
        return

    scenarios_ran = 0
    if not no_progress:
        prg = ProgressBar("Pyccuracy - %s" % __version_string__, verbosity)
        prg.update(0, 'Running first test...')

def update_progress(fixture, scenario, scenario_index):
    global no_progress
    global prg
    global scenarios_ran
    
    if not scenarios_ran is None:
        scenarios_ran += 1
    if not no_progress:
        if scenario.status == Status.Failed:
            prg.set_failed()
        total_scenarios = fixture.count_total_scenarios()
        if total_scenarios == 0:
            return

        current_progress = float(scenarios_ran) / total_scenarios
        prg.update(current_progress, "[%s] Scenario %d of %d <%.2fs> - %s" % (scenario.status[0], scenarios_ran, total_scenarios, fixture.ellapsed(), scenario.title))

def main(arguments=sys.argv[1:]):
    """ Main function - parses args and runs action """
    global no_progress
    global scenarios_ran

    scenarios_ran = 0

    extra_browser_driver_arguments = "\n\nThe following extra browser driver arguments " \
                                     " are supported in the key=value format:\n\nSelenium Browser Driver:\n" \
                                     "* selenium.server=ip or name of selenium server or grid\n" \
                                     "* selenium.port=port of the given selenium server or grid\n"

    parser = optparse.OptionParser(usage="%prog or type %prog -h (--help) for help" + extra_browser_driver_arguments, description=__doc__, version=__version_string__)
    parser.add_option("-p", "--pattern", dest="pattern", default="*.acc", help="File pattern. Defines which files will get executed [default: %default].")
    parser.add_option("-s", "--scenarios", dest="scenarios_to_run", default=None, help="Run only the given scenarios, comma separated. I.e: --scenarios=1,4,9")
    parser.add_option("-l", "--language", dest="language", default="en-us", help="Language. Defines which language the dictionary will be loaded with  [default: %default].")
    parser.add_option("-L", "--languagesdir", dest="languages_dir", default=None, help="Languages Directory. Defines where Pyccuracy will search for language dictionaries  [default: %default].")
    parser.add_option("-d", "--dir", action="append", dest="dir", default=[], help="Tests directory. Defines where the tests to be executed are [default: %default]. Note: this is recursive, so all the tests under the current directory get executed.")
    parser.add_option("-a", "--actionsdir", action="append", dest="actions_dir", default=[], help="Actions directory. Defines where the Pyccuracy actions are. Chances are you don't need to change this parameter [default: %default].")
    parser.add_option("-A", "--customactionsdir", action="append", dest="custom_actions_dir", default=[], help="Custom Actions directory. Defines where the Pyccuracy custom actions are. If you don't change this parameter Pyccuracy will use the tests directory [default: %default].")
    parser.add_option("-P", "--pagesdir", action="append", dest="pages_dir", default=[], help="Pages directory. Defines where the Pyccuracy custom pages are. If you don't change this parameter Pyccuracy will use the tests directory [default: %default].")
    parser.add_option("-H", "--hooksdir", action="append", dest="hooks_dir", default=[], help="Hooks directory. Defines where Pyccuracy hooks are. If you don't change this parameter Pyccuracy will use the tests directory [default: %default].")
    parser.add_option("-u", "--url", dest="url", default=None, help="Base URL. Defines a base url against which the tests will get executed. For more details check the documentation [default: %default].")
    parser.add_option("-b", "--browser", dest="browser_to_run", default="firefox", help="Browser to run. Browser driver will use it to run tests [default: %default].")
    parser.add_option("-w", "--workers", dest="workers", default=1, help="Workers to run in parallel [default: %default].")

    #browser driver
    parser.add_option("-e", "--browserdriver", dest="browser_driver", default="selenium", help="Browser Driver to be used on tests. [default: %default].")

    #throws
    parser.add_option("-T", "--throws", dest="should_throw", default=False, help="Should Throw. Defines whether Pyccuracy console should throw an exception when tests fail. This is useful to set to True if you are running Pyccuracy inside unit tests [default: %default].")

    #reporter
    parser.add_option("-R", "--report", dest="write_report", default="true", help="Should write report. Defines if Pyccuracy should write an html report after each run [default: %default].")
    parser.add_option("-D", "--reportdir", dest="report_dir", default=os.curdir, help="Report directory. Defines the directory to write the report in [default: %default].")
    parser.add_option("-F", "--reportfile", dest="report_file_name", default="report.html", help="Report file. Defines the file name to write the report with [default: %default].")

    #verbosity
    parser.add_option("-v", "--verbosity", dest="verbosity", default="3", help="Verbosity. 0 - does not show any output, 1 - shows text progress, 2 - shows animated progress bar, 3 - shows action by action [default: %default].")
    parser.add_option("--suppresswarnings", action="store_true", dest="suppress_warnings", default=False, help="Suppress Pyccuracy warnings [default: %default].")

    options, args = parser.parse_args(arguments)

    workers = options.workers and int(options.workers) or None
    pyc = PyccuracyCore()

    if not options.dir:
        options.dir = [os.curdir]

    extra_args = {}
    if args:
        for arg in args:
            if not "=" in arg:
                raise ValueError("The specified extra argument should be in the form of key=value and not %s" % arg)
            key, value = arg.split('=')
            extra_args[key] = value

    verbosity = int(options.verbosity)

    create_progress(verbosity)

    on_before_action_handler = None
    on_action_successful_handler = None
    on_action_error_handler = None
    on_scenario_started_handler = None
    on_scenario_completed_handler = update_progress
    on_section_started = None

    if verbosity == 3:
        on_before_action_handler = before_action
        on_action_successful_handler = action_successful
        on_action_error_handler = action_error
        on_scenario_started_handler = scenario_started
        on_scenario_completed_handler = scenario_completed
        on_section_started = section_started_handler

    result = pyc.run_tests(actions_dir=options.actions_dir,
                           custom_actions_dir=options.custom_actions_dir,
                           pages_dir=options.pages_dir,
                           hooks_dir=options.hooks_dir,
                           languages_dir=options.languages_dir,
                           file_pattern=options.pattern,
                           scenarios_to_run=options.scenarios_to_run,
                           tests_dirs=options.dir,
                           base_url=options.url,
                           default_culture=options.language,
                           write_report=options.write_report.lower() == "true",
                           report_file_dir=options.report_dir,
                           report_file_name=options.report_file_name,
                           browser_to_run=options.browser_to_run,
                           browser_driver=options.browser_driver,
                           should_throw=options.should_throw,
                           workers=workers,
                           extra_args=extra_args,
                           on_scenario_started=on_scenario_started_handler,
                           on_scenario_completed=on_scenario_completed_handler,
                           on_before_action=on_before_action_handler,
                           on_action_successful=on_action_successful_handler,
                           on_action_error=on_action_error_handler,
                           on_section_started=on_section_started,
                           verbosity=int(options.verbosity),
                           suppress_warnings=options.suppress_warnings)

    if not result or result.get_status() != "SUCCESSFUL":
        return 1

    return 0

def console():
    # used by easy_install command line script - do not remove
    sys.exit(main(sys.argv[1:]))

if __name__ == "__main__":
    console()

########NEW FILE########
__FILENAME__ = pyccuracy_help
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import optparse
import sys

from help import LanguageViewer

def show_terms(term, language):
    viewer = LanguageViewer(language=language)
    actions = viewer.get_actions(term)
    print '\n----- Found %d results for "%s" -----\n' % (len(actions), term if term is not '' else '*')
    for name, value in actions.iteritems():
        print '%-35s = %s' % (name, value)
    print '\n----- Found %d results for "%s" -----\n' % (len(actions), term if term is not '' else '*')

def main(arguments=sys.argv[1:]):
    info = '''
--------------------------------------------------------------------------------------
Use %prog to get quick assistance on the expressions available for Pyccuracy.
--------------------------------------------------------------------------------------

Examples:

$ %prog --language en-us
    --> Shows all actions for english language.

$ %prog --term select
    --> Shows actions in english language for "select" elements.

$ %prog --language pt-br --term textboxes
    --> Shows actions in portuguese language for "textbox" elements.'''
    parser = optparse.OptionParser(info)

    parser.add_option('-t', '--term', dest='term', default='', help='Terms to search. It looks for terms that contains the informed words. [default: "%default"]')
    parser.add_option('-l', '--language', dest='language', default='en-us', help='Language to search for terms. [default: %default]')

    options, args = parser.parse_args()

    show_terms(options.term, options.language)

def console():
    sys.exit(main(sys.argv[1:]))

if __name__ == "__main__":
    console()
########NEW FILE########
__FILENAME__ = report_parser
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
from os import remove
from os import curdir

from datetime import datetime
from os.path import join, split, exists

from StringIO import StringIO

from lxml import etree
from lxml.etree import Element
from lxml.builder import E
from lxml import etree as ET

from pyccuracy import Version

def generate_report(file_path, test_result, language):
    xslt = open(join(split(__file__)[0], "xslt/AccuracyReport_%s.xslt" % language.key))
    xslt_doc = etree.parse(xslt)
    transform = etree.XSLT(xslt_doc)
    doc = generate_xml(test_result, language)
    result_tree = transform(doc)

    if exists(file_path):
        remove(file_path)

    html = open(file_path, "w")
    html.write(str(result_tree))
    html.close()

def generate_xml(test_result, language):
    total_stories = float(test_result.fixture.count_total_stories())
    total_scenarios = float(test_result.fixture.count_total_scenarios())
    successful_stories = test_result.fixture.count_successful_stories()
    successful_scenarios = test_result.fixture.count_successful_scenarios()
    failed_stories = test_result.fixture.count_failed_stories()
    failed_scenarios = test_result.fixture.count_failed_scenarios()
    percentage_successful_stories = (successful_stories / (total_stories or 1)) * 100
    percentage_failed_stories = (failed_stories / (total_stories or 1)) * 100
    percentage_successful_scenarios = (successful_scenarios / (total_scenarios or 1)) * 100
    percentage_failed_scenarios = (failed_scenarios / (total_scenarios or 1)) * 100

    index = 0
    stories = []
    for story in test_result.fixture.stories:
        index += 1
        stories.append(__generate_story(story, index, language))

    doc = E.report(
        E.header(
            {
                "date":datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            }
        ),
        E.footer(
            {
                "version":Version
            }
        ),
        E.summary(
            {
                "totalStories":"%.0f" % total_stories,
                "totalScenarios":"%.0f" % total_scenarios,
                "successfulScenarios":str(successful_scenarios),
                "failedScenarios":str(failed_scenarios),
                "percentageSuccessful": "%.2f" % percentage_successful_scenarios,
                "percentageFailed": "%.2f" % percentage_failed_scenarios
            }
        )
    )

    stories_doc = Element("stories")

    for story in stories:
        stories_doc.append(story)

    doc.append(stories_doc)

    #print etree.tostring(doc, pretty_print=True)
    return doc

def __generate_story(story, story_index, language):
    scenarios = []
    for scenario in story.scenarios:
        scenarios.append(__generate_scenario(scenario, language))

    story_doc = E.story(
                    {
                        "index":str(story_index),
                        "identity":story.identity,
                        "asA":"%s %s" % (language.get("as_a"), story.as_a),
                        "iWant":"%s %s" % (language.get("i_want_to"), story.i_want_to),
                        "soThat":"%s %s" % (language.get("so_that"), story.so_that),
                        "isSuccessful":(story.status == "SUCCESSFUL" and "true" or "false")
                    }
                )

    for scenario in scenarios:
        story_doc.append(scenario)

    return story_doc

def __generate_scenario(scenario, language):
    if scenario.status == "SUCCESSFUL":
        scenario_total_time = scenario.ellapsed()
        scenario_finish_time = time.asctime(time.localtime(scenario.end_time))
    else:
        scenario_total_time = 0.0
        scenario_finish_time = "FAILED"

    actions = []
    odd = True
    actions.append(__generate_given(language, odd))
    odd = not odd
    for action in scenario.givens:
        actions.append(__generate_action(action, language, odd))
        odd = not odd

    actions.append(__generate_when(language, odd))
    odd = not odd
    for action in scenario.whens:
        actions.append(__generate_action(action, language, odd))
        odd = not odd

    actions.append(__generate_then(language, odd))
    odd = not odd
    for action in scenario.thens:
        actions.append(__generate_action(action, language, odd))
        odd = not odd

    #action_text = "".join([etree.tostring(action, pretty_print=False) for action in actions]).replace('"', '&quot;')

    scenario_status = scenario.status == "SUCCESSFUL" and "true" or "false"

    scenario_doc = E.scenario(
                                {
                                    "index":str(scenario.index),
                                    "description":scenario.title,
                                    "totalTime": "%.2f" % scenario_total_time,
                                    "finishTime":scenario_finish_time,
                                    "isSuccessful":scenario_status
                                }
                           )

    for action in actions:
        scenario_doc.append(action)

    return scenario_doc

def __generate_given(language, odd):
    return __generate_condition(language.get("given"), odd)

def __generate_when(language, odd):
    return __generate_condition(language.get("when"), odd)

def __generate_then(language, odd):
    return __generate_condition(language.get("then"), odd)

def __generate_condition(condition_name, odd):
    condition_doc = E.action(
                            {
                                "type":"condition",
                                "description":condition_name,
                                "actionTime":"",
                                "oddOrEven":(odd and "odd" or "even")
                            }
                          )

    return condition_doc

def __generate_action(action, language, odd):
    description = action.description
    if action.status == "FAILED":
        description += " - %s" % unicode(action.error)

    actionTime = "Unknown"
    if action.status == "SUCCESSFUL" or action.status == "FAILED":
        actionTime = time.asctime(time.localtime(action.start_time))

    action_doc = E.action(
                        {
                            "type":"action",
                            "status":action.status,
                            "description": description,
                            "actionTime":actionTime,
                            "oddOrEven":(odd and "odd" or "even")
                        }
                 )
    return action_doc


########NEW FILE########
__FILENAME__ = result
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os.path import abspath, dirname, join
from pyccuracy.languages.templates import TemplateLoader
from pyccuracy.common import Status
from pyccuracy.airspeed import Template

class Result(object):
    def __init__(self, fixture, template_loader=None):
        self.fixture = fixture
        self.template_loader = template_loader

    def summary_for(self, language):
        template_string = self.get_summary_template_for(language)
        template = Template(template_string)
        return template.merge(self.summary_values())

    def get_summary_template_for(self, language):
        template_loader = self.template_loader or TemplateLoader(language)
        return template_loader.load("summary")

    def get_status(self):
        return self.fixture and self.fixture.get_status() or Status.Unknown

    def summary_values(self):
        val = {
                "run_status" : Status.Unknown,
                "total_stories" : 0,
                "total_scenarios" : 0,
                "successful_stories" : 0,
                "failed_stories" : 0,
                "successful_scenarios" : 0,
                "failed_scenarios" : 0,
                "has_failed_scenarios": False,
                "threshold":"0.00"
              }

        if self.fixture:
            val = {
                    "run_status" : self.fixture.get_status(),
                    "total_stories" : self.fixture.count_total_stories(),
                    "total_scenarios" : self.fixture.count_total_scenarios(),
                    "successful_stories" : self.fixture.count_successful_stories(),
                    "failed_stories" : self.fixture.count_failed_stories(),
                    "successful_scenarios" : self.fixture.count_successful_scenarios(),
                    "failed_scenarios" : self.fixture.count_failed_scenarios()
                  }
            total_test_time = float(self.fixture.ellapsed())
            if total_test_time == 0:
                val["threshold"] = 0
            else:
                val["threshold"] = "%.2f" % (val["total_scenarios"] / (total_test_time / 60))

            val["has_failed_scenarios"] = val["failed_scenarios"] > 0

        if val["has_failed_scenarios"]:
            val["failed_scenario_instances"] = self.fixture.get_failed_scenarios()

        no_stories = val["total_stories"] == 0
        no_scenarios = val["total_scenarios"] == 0

        val["successful_story_percentage"] = no_stories and "0.00" or "%.2f" % (float(val["successful_stories"]) / float(val["total_stories"]) * 100)
        val["failed_story_percentage"] = no_stories and "0.00" or "%.2f" % (float(val["failed_stories"]) / float(val["total_stories"]) * 100)
        val["successful_scenario_percentage"] = no_scenarios and "0.00" or "%.2f" % (float(val["successful_scenarios"]) / float(val["total_scenarios"]) * 100)
        val["failed_scenario_percentage"] = no_scenarios and "0.00" or "%.2f" % (float(val["failed_scenarios"]) / float(val["total_scenarios"]) * 100)

        if self.fixture.no_story_header:
            val["has_no_header_files"] = True
            val["no_header_files"] = self.fixture.no_story_header

        val["test_run_seconds"] = "%.2f" % total_test_time

        return val

    @classmethod
    def empty(cls):
        return Result(fixture=None)

########NEW FILE########
__FILENAME__ = story_runner
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import time
import traceback

from Queue import Queue
from threading import Thread, RLock

from pyccuracy.result import Result
from pyccuracy.common import Context
from pyccuracy.actions import ActionNotFoundError
from pyccuracy.errors import ActionFailedError
from pyccuracy.drivers import DriverError
from pyccuracy.languages.templates import TemplateLoader
from pyccuracy.airspeed import Template
from pyccuracy.colored_terminal import TerminalController

class StoryRunner(object):
    def run_stories(self, settings, fixture, context=None):
        if not context:
            context = self.create_context_for(settings)

        fixture.start_run()
        if settings.base_url:
            base_url = settings.base_url
        else:
            base_url = "http://localhost"

        try:
            context.browser_driver.start_test(base_url)
        except DriverError, err:
            ctrl = TerminalController()
            template_text = TemplateLoader(settings.default_culture).load("driver_error")
            template = Template(template_text)
            values = {"error": err, "browser_driver": context.browser_driver}
            print ctrl.render(template.merge(values))

            if settings.should_throw:
                raise TestFailedError("The test failed!")
            else:
                return None

        try:
            scenario_index = 0
            for story in fixture.stories:
                for scenario in story.scenarios:
                    if settings.on_scenario_started and callable(settings.on_scenario_started):
                        settings.on_scenario_started(fixture, scenario, scenario_index)
                    scenario_index += 1
                    if not context:
                        context = self.create_context_for(settings)
                    def execute_action(action):
                        try:
                            result = self.execute_action(context, action)
                            if not result:
                                return False
                        except ActionNotFoundError, error:
                            action.mark_as_failed(
                                ActionNotFoundError(error.line, 
                                                    scenario,
                                                    scenario.story.identity))
                            return False
                        return True

                    def on_section_started(section):
                        if settings.on_section_started and\
                        callable(settings.on_section_started):
                            settings.on_section_started(section)
                    
                    failed = False
                    on_section_started(context.language.get('given'))
                    for action in scenario.givens:
                        if not execute_action(action):
                            failed = True
                            break

                    if not failed:
                        on_section_started(context.language.get('when'))
                        for action in scenario.whens:
                            if not execute_action(action):
                                failed = True
                                break

                    if not failed:                    
                        on_section_started(context.language.get('then'))
                        for action in scenario.thens:
                            if not execute_action(action):
                                failed = True
                                break
                            
                    if settings.on_scenario_completed and callable(settings.on_scenario_completed):
                        settings.on_scenario_completed(fixture, scenario, scenario_index)

            fixture.end_run()
            return Result(fixture=fixture)
        finally:
            context.browser_driver.stop_test()

    def execute_action(self, context, action):
        return action.execute(context)

    def create_context_for(self, settings):
        return Context(settings)

class ParallelStoryRunner(StoryRunner):
    def __init__(self, number_of_threads):
        self.number_of_threads = number_of_threads
        self.test_queue = Queue()
        self.contexts = []
        self.available_context_queue = Queue()
        self.threads = []
        self.lock = RLock()
        self.aborted = False

    def run_stories(self, settings, fixture, context=None):
        if len(fixture.stories) == 0:
            return
        
        self.fill_queue(fixture, settings)
        self.fill_context_queue(settings)

        fixture.start_run()
        
        try:
            self.start_processes()

            try:
                time.sleep(2)
                while self.test_queue.unfinished_tasks:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.abort_run()
                
        finally:
            self.kill_context_queue()

        fixture.end_run()

        return Result(fixture=fixture)

    def start_processes(self):
        for i in range(self.number_of_threads):
            t = Thread(target=self.worker)
            t.setDaemon(True)
            t.start()
            self.threads.append(t)

    def fill_queue(self, fixture, settings):
        scenario_index = 0
        for story in fixture.stories:
            for scenario in story.scenarios:
                scenario_index += 1
                self.test_queue.put((fixture, scenario))
    
    def fill_context_queue(self, settings):
        starting_contexts = []
        for i in range(self.number_of_threads):
            context = self.create_context_for(settings)

            #start browser driver in background
            thread = Thread(target=self.start_context_test, kwargs={'context':context})
            thread.setDaemon(True)
            thread.start()
            starting_contexts.append(thread)

            self.available_context_queue.put(i)
            self.contexts.append(context)
        
        #waiting for threads to finish
        for thread in starting_contexts:
            if thread.isAlive():
                thread.join()
            else:
                del(thread)

    def start_context_test(self, context):
        context.browser_driver.start_test()

    def abort_run(self):
        self.aborted = True
        
        for context in self.contexts:
            context.settings.on_scenario_completed = None
    
    def kill_context_queue(self):
        sys.stdout.write("\nStopping workers, please wait (DO NOT CANCEL AGAIN)...\n")
        total = len(self.contexts)
        for index, context in enumerate(self.contexts):
            percent = (float(index + 1) / total) * 100
            sys.stdout.write("[%06.2f%%] Stopped worker %d of %d\n" % (percent, index + 1, total))
            try:
                context.browser_driver.stop_test()
            except Exception, e:
                pass #doesn't matter for the user, the execution MUST be stopped
                
        sys.stdout.write("Done.\n")

    def worker(self):
        while not self.aborted:
            fixture, scenario = self.test_queue.get()
            self.lock.acquire()
            context_index = self.available_context_queue.get()
            context = self.contexts[context_index]
            self.lock.release()

            scenario_index = fixture.count_successful_scenarios() + fixture.count_failed_scenarios() + 1

            if context.settings.on_scenario_started and callable(context.settings.on_scenario_started):
                context.settings.on_scenario_started(fixture, scenario, scenario_index)

            current_story = scenario.story
            if context.settings.base_url:
                base_url = context.settings.base_url
            else:
                base_url = "http://localhost"

            try:
                scenario.start_run()
                for action in scenario.givens + scenario.whens + scenario.thens:
                    result = self.execute_action(context, action)
                    if not result:
                        break
                scenario.end_run()
            except Exception, err:
                traceback.print_exc(err)
            finally:
                self.available_context_queue.put(context_index)
                self.test_queue.task_done()

                if context.settings.on_scenario_completed and callable(context.settings.on_scenario_completed):
                    context.settings.on_scenario_completed(fixture, scenario, scenario_index)
            

########NEW FILE########
__FILENAME__ = custom_action_with_table_parameter
#
from pyccuracy.actions import ActionBase
from pyccuracy.errors import *

class RegisterUsersAction(ActionBase):
    regex = r'^(And )?I have the following registered users:$'

    def execute(self, context, table):
        user = table[0]
        assert(user['username']=='admin')
        assert(user['email']=='a@dd.cc')
        assert(user['password']=='aidimin')
        
class ProductsSetupAction(ActionBase):
    regex = r'^(And )?I have the following products:$'

    def execute(self, context, table):
        apple = table[0]
        assert(apple['name']=='Apple')
        assert(apple['price']=='1.65')

        banana = table[1]
        assert(banana['name']=='Banana')
        assert(banana['price']=='0.99')
        

########NEW FILE########
__FILENAME__ = does_nothing_actions
from pyccuracy import ActionBase

class DoesNothingAction(ActionBase):
    regex = "^does nothing$"
    
    def execute(self):
        pass
########NEW FILE########
__FILENAME__ = pages
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyccuracy import Page

class TestCustomPage(Page):
    url = "page_tests.htm"

    def register(self):
        self.quick_register(u"custom wait for visible", "#divWaitForVisible")
        self.quick_register(u"custom wait for invisible", "#divWaitForInvisible")

class OtherPage(Page):
    url = "page_tests.html"

    def register(self):
        self.quick_register(u"text", "#divText3")

class GoogleSearch(Page):
    url = "http://www.google.com/"

    def register(self):
        self.register_element('query', '//input[@name="q"]')
        self.register_element('search', '//button')

class YahooSearch(Page):
    url = "http://search.yahoo.com/search?p=<query>"

    def register(self):
        self.register_element('search', '//input[@type="text"]')

class OtherYahooSearch(Page):
    url = "http://search.yahoo.com/search?p=<query>&b=<offset>"

    def register(self):
        self.register_element('search', '//input[@id="yschsp"]')
        self.register_element('page', '//div[@id="pg"]//strong')

########NEW FILE########
__FILENAME__ = some_more_pages
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pyccuracy import Page

class YetAnotherPage(Page):
    url = "page_tests.htm"

    def register(self):
        self.quick_register(u"text2", "#divText2")

########NEW FILE########
__FILENAME__ = django_extensions_test
#!/usr/bin/env python
# -*- coding: utf-8 -*-

########NEW FILE########
__FILENAME__ = test_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyccuracy import ActionRegistry, ActionBase
from pyccuracy.languages import LanguageItem
from pyccuracy.actions.core.page_actions import *

def test_get_suitable_action():
    Action, args, kw = ActionRegistry.suitable_for(u'I see "Welcome to Pyccuracy" title', 'en-us')
    assert Action, "Action cannot be None"
    assert issubclass(Action, ActionBase)
    assert isinstance(args, (list, tuple))
    assert isinstance(kw, dict)
    assert args[1] == u'Welcome to Pyccuracy'

def test_do_not_get_suitable_action():
    Action, args, kw = ActionRegistry.suitable_for(u'Blah bluh foo bar', 'en-us')
    assert Action is None
    assert args is None
    assert kw is None

def test_action_registry_suitable_for_returns_type_on_match():
    class FooTitleAction(ActionBase):
        regex = r'I see "foo" title'
        def execute(self, context, *args, **kwargs):
            pass

    Action, args, kwargs = ActionRegistry.suitable_for('I see "foo" title', 'en-us')
    assert isinstance(Action, type)

# Action-specific tests

def test_get_suitable_action_appropriately_for_page_actions_enus():
    Action, args, kw = ActionRegistry.suitable_for(u'I go to My Page', 'en-us')
    assert issubclass(Action, PageGoToAction)
    assert kw['url'] == u'My Page'
    
    Action, args, kw = ActionRegistry.suitable_for(u'I go to My Page for parameter "value"', 'en-us')
    assert issubclass(Action, PageGoToWithParametersAction)
    assert kw['url'] == u'My Page'
    assert kw['parameters'] == u'parameter "value"'

    Action, args, kw = ActionRegistry.suitable_for(u'I go to My Page of parameter "value"', 'en-us')
    assert issubclass(Action, PageGoToWithParametersAction)
    assert kw['url'] == u'My Page'
    assert kw['parameters'] == u'parameter "value"'
    
    Action, args, kw = ActionRegistry.suitable_for(u'I go to My Page with parameter1 "value1", parameter2 "value2"', 'en-us')
    assert issubclass(Action, PageGoToWithParametersAction)
    assert kw['url'] == u'My Page'
    assert kw['parameters'] == u'parameter1 "value1", parameter2 "value2"'

def test_get_suitable_action_appropriately_for_page_actions_ptbr():
    # Reset action regexes (this is necessary because pyccuracy was not built
    # to run 2 different languages in the same execution, then we do this to 
    # allow appropriate testing)
    PageGoToAction.regex = LanguageItem('page_go_to_regex')
    PageGoToWithParametersAction.regex = LanguageItem('page_go_to_with_parameters_regex')
    
    Action, args, kw = ActionRegistry.suitable_for(u'Eu navego para Uma Pagina', 'pt-br')
    assert issubclass(Action, PageGoToAction)
    assert kw['url'] == u'Uma Pagina'

    Action, args, kw = ActionRegistry.suitable_for(u'Eu navego para Pagina de Blog do usuario "nome"', 'pt-br')
    assert issubclass(Action, PageGoToWithParametersAction)
    assert kw['url'] == u'Pagina de Blog'
    assert kw['parameters'] == u'usuario "nome"'

    Action, args, kw = ActionRegistry.suitable_for(u'Eu navego para Pagina de Busca para query "palavra"', 'pt-br')
    assert issubclass(Action, PageGoToWithParametersAction)
    assert kw['url'] == u'Pagina de Busca'
    assert kw['parameters'] == u'query "palavra"'

    Action, args, kw = ActionRegistry.suitable_for(u'Eu navego para Pagina de Config com parameter1 "value1", parameter2 "value2"', 'pt-br')
    assert issubclass(Action, PageGoToWithParametersAction)
    assert kw['url'] == u'Pagina de Config'
    assert kw['parameters'] == u'parameter1 "value1", parameter2 "value2"'

########NEW FILE########
__FILENAME__ = test_drivers_registry
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pyccuracy import DriverRegistry
from pyccuracy.drivers import BaseDriver

def test_selenium_browser_driver_exists():
    SeleniumDriver = DriverRegistry.get('selenium')
    assert isinstance(SeleniumDriver, type)
    assert issubclass(SeleniumDriver, BaseDriver)

########NEW FILE########
__FILENAME__ = test_file_parser
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from os.path import join, dirname, abspath

from pyccuracy.common import Settings
from pyccuracy.parsers import FileParser
from pyccuracy.fixture import Fixture
from pyccuracy.fixture_items import Story
from pyccuracy import ActionBase

def assert_no_invalid_stories(fixture):
    if fixture.invalid_test_files:
        raise fixture.invalid_test_files[0][1]

def test_parsing_folder_with_no_stories_returns_empty_list():
    settings = Settings()
    settings.tests_dirs = [abspath(join(dirname(__file__), "no_stories_folder"))]
    parser = FileParser()

    fixture = parser.get_stories(settings=settings)
    assert len(fixture.stories) == 0

def test_parsing_files_with_empty_content_returns_no_story_header_list():
    settings = Settings()
    settings.tests_dirs = [abspath(join(dirname(__file__), "invalid_content_stories"))]
    settings.file_pattern = "empty_story.acc"

    parser = FileParser()

    fixture = parser.get_stories(settings=settings)

    assert len(fixture.no_story_header) == 1
    file_path = fixture.no_story_header[0]
    assert file_path.endswith("empty_story.acc")

def test_parsing_files_with_wrong_content_returns_no_story_header_list():
    settings = Settings()
    settings.tests_dirs = [abspath(join(dirname(__file__), "invalid_content_stories"))]
    settings.file_pattern = "invalid_story.acc"

    parser = FileParser()

    fixture = parser.get_stories(settings=settings)

    assert len(fixture.no_story_header) == 1
    file_path = fixture.no_story_header[0]
    assert file_path.endswith("invalid_story.acc")

def test_parsing_files_with_wrong_as_a_returns_no_story_header_list():
    settings = Settings()
    settings.tests_dirs = [abspath(join(dirname(__file__), "invalid_content_stories"))]
    settings.file_pattern = "invalid_as_a.acc"

    parser = FileParser()

    fixture = parser.get_stories(settings=settings)

    assert len(fixture.no_story_header) == 1
    file_path = fixture.no_story_header[0]
    assert file_path.endswith("invalid_as_a.acc")
    
def test_parsing_files_with_wrong_i_want_to_returns_no_story_header_list():
    settings = Settings()
    settings.tests_dirs = [abspath(join(dirname(__file__), "invalid_content_stories"))]
    settings.file_pattern = "invalid_i_want_to.acc"

    parser = FileParser()

    fixture = parser.get_stories(settings=settings)

    assert len(fixture.no_story_header) == 1
    file_path = fixture.no_story_header[0]
    assert file_path.endswith("invalid_i_want_to.acc")
    
def test_parsing_files_with_wrong_so_that_returns_no_story_header_list():
    settings = Settings()
    settings.tests_dirs = [abspath(join(dirname(__file__), "invalid_content_stories"))]
    settings.file_pattern = "invalid_so_that.acc"

    parser = FileParser()

    fixture = parser.get_stories(settings=settings)

    assert len(fixture.no_story_header) == 1
    file_path = fixture.no_story_header[0]
    assert file_path.endswith("invalid_so_that.acc")

def test_parsing_files_with_many_scenarios_returns_parsed_scenarios():
    class DoSomethingAction(ActionBase):
        regex = r'I do something$'
        def execute(context, *args, **kwargs):
            pass

    class DoSomethingElseAction(ActionBase):
        regex = r'I do something else$'
        def execute(context, *args, **kwargs):
            pass

    class DoYetAnotherThingAction(ActionBase):
        regex = r'I do yet another thing$'
        def execute(context, *args, **kwargs):
            pass

    settings = Settings()
    settings.tests_dirs = [abspath(dirname(__file__))]
    settings.file_pattern = "some_test.acc"

    parser = FileParser()

    fixture = parser.get_stories(settings=settings)

    assert_no_invalid_stories(fixture)

    assert len(fixture.stories) == 1, "Expected 1, Actual: %d" % len(fixture.stories)
    assert len(fixture.stories[0].scenarios) == 2
    assert "#some custom comment" in fixture.stories[0].scenarios[1].whens[0].description


########NEW FILE########
__FILENAME__ = test_language
# -*- coding: utf-8 -*-
import os
from nose.tools import raises, set_trace
from pyccuracy.languages import LanguageGetter, AVAILABLE_LANGUAGES

def test_pt_br_exists():
    lg = LanguageGetter('pt-br')
    assert os.path.exists(lg.language_path), "There is no language file for pt-br culture: %s" % lg.language_path

def test_pt_br_basic_items():
    lg = LanguageGetter('pt-br')
    assert lg.get('as_a')
    assert lg.get('i_want_to')
    assert lg.get('so_that')
    assert lg.get('scenario')
    assert lg.get('given')
    assert lg.get('when')
    assert lg.get('then')
    assert lg.get('invalid_test_files')
    assert lg.get('files_without_header')
    assert lg.get('story_status')

def test_en_us_exists():
    lg = LanguageGetter('en-us')
    assert os.path.exists(lg.language_path), "There is no language file for en-us culture: %s" % lg.language_path

def test_en_us_basic_items():
    lg = LanguageGetter('en-us')
    assert lg.get('as_a')
    assert lg.get('i_want_to')
    assert lg.get('so_that')
    assert lg.get('scenario')
    assert lg.get('given')
    assert lg.get('when')
    assert lg.get('then')
    assert lg.get('invalid_test_files')
    assert lg.get('files_without_header')
    assert lg.get('story_status')

def test_available_languages():
    assert 'pt-br' in AVAILABLE_LANGUAGES
    assert 'en-us' in AVAILABLE_LANGUAGES

########NEW FILE########
__FILENAME__ = test_pages
# -*- coding: utf-8 -*-
from pyccuracy import PageRegistry, Page
from pyccuracy.page import ElementAlreadyRegisteredError

class GoogleMainPage(Page):
    url = 'http://google.com'

class GoogleSearchPage(Page):
    url = 'http://google.com'

def test_get_by_name():
    page = PageRegistry.get_by_name(u'Google Main Page')
    assert issubclass(page, Page)

def test_get_all_by_url():
    pages = PageRegistry.all_by_url('http://google.com')
    for page in pages:
        assert issubclass(page, Page)

def test_register_element_registers_element_within_dict():
    class GloboPortal(Page):
        url = 'http://globo.com'
        def register(self):
            self.register_element('logo', u"div[contains(@class, 'marca-globo')]/a")


    p = GloboPortal()

    assert p.registered_elements.has_key('logo')
    assert p.registered_elements['logo'] == u"div[contains(@class, 'marca-globo')]/a"

def test_quick_register_registers_element_within_dict():
    class GloboPortal(Page):
        url = 'http://globo.com'
        def register(self):
            self.quick_register('logo', u"div.marca-globo > a")


    p = GloboPortal()
    expected_xpath = "//div[contains(concat(' ', normalize-space(@class), ' '), ' marca-globo ')]/a"
    assert p.registered_elements.has_key('logo')
    assert p.registered_elements['logo'] == expected_xpath

def test_should_not_allow_registering_two_elements_with_same_name():
    class GloboPortal(Page):
        url = 'http://globo.com'
        def register(self):
            self.register_element('my div', u"//div[1]")
            self.register_element('my div', u"//div[2]")

    try:
        p = GloboPortal()
        assert False, "Should not get here."
    except ElementAlreadyRegisteredError, e:
        pass

def test_should_allow_registering_two_elements_with_same_name_in_different_pages():
    class GloboPortal(Page):
        url = 'http://globo.com'
        def register(self):
            self.register_element('my div', u"//div[1]")

    class YahooPortal(Page):
        url = 'http://yahoo.com'
        def register(self):
            self.register_element('my div', u"//div[1]")

    try:
        g = GloboPortal()
        y = YahooPortal()
    except ElementAlreadyRegisteredError, e:
        assert False, "Should not get here."

########NEW FILE########
__FILENAME__ = test_result
#!/usr/bin/env python
#-*- coding:utf-8 -*-
import re
from pyccuracy.result import Result
from pyccuracy.common import Settings
from pyccuracy.fixture import Fixture
from pyccuracy.fixture_items import Story, Scenario, Action

def complete_scenario_with_then_action_returned():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="some file")
    scenario = story.append_scenario("1", "Something")
    given = scenario.add_given(action_description="I did something", execute_function=lambda: None, args=["s"], kwargs={"a":"bs"})
    when = scenario.add_when(action_description="I do something", execute_function=lambda: None, args=["s"], kwargs={"a":"b"})
    then = scenario.add_then(action_description="Something happens", execute_function=lambda: None, args=["s"], kwargs={"a":"b"})
    return then

def test_see_summary_for_fixture_returns_proper_failed_scenarios_string():
    expected = u"""================
Test Run Summary
================
Status: FAILED

Test Data Stats
---------------
Successful Stories......0 of 1 (0.00%)
Successful Scenarios....0 of 1 (0.00%)
Failed Stories..........1 of 1 (100.00%)
Failed Scenarios........1 of 1 (100.00%)

Total timing: 0.00 secs
Scenarios/Minute: 0 scenarios per minute


Failed Stories / Scenarios
--------------------------
Story..........As a Someone I want to Do Something So that I'm Happy
Story file.....some file
Scenario.......1 - Something
    Given
        I did something - UNKNOWN
    When
        I do something - UNKNOWN
    Then
        Something happens - FAILED - Something very bad happened
"""

    settings = Settings()
    fixture = Fixture()
    result = Result(fixture=fixture)
    action = complete_scenario_with_then_action_returned()
    fixture.append_story(action.scenario.story)
    action.mark_as_failed("Something very bad happened")

    summary = re.sub(r'[$][{][^}]+[}]', '', result.summary_for("en-us"))

    assert summary.strip() == expected.strip(), compare(summary.strip(), expected.strip())

def compare(str_a, str_b):

    for index in range(len(str_a)):
        if index > len(str_b):
            return  "Strings differ at position %d" % index

        char_a = str_a[index:index+1]
        char_b = str_b[index:index+1]
        if char_a != char_b:
            x =  "Strings differ at position %d\nString A: %s\nString B: %s\n" % (index, str_a[:index+1], str_b[:index+1])
            x += "The error is that  %r is different of %r\n" % (str_a[index], str_b[index])
            def diff(string, index):
                return "[%s]%s" % (string[index], string[index+1:index+10])

            x += "The difference is between %r and %r\n" % (diff(str_a, index), diff(str_b, index))
            return x


########NEW FILE########
__FILENAME__ = test_settings
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from os.path import join, abspath, dirname
from pyccuracy.common import Settings

cur_dir = abspath(dirname(os.curdir))
actions_dir = abspath(join(dirname(__file__), "../../pyccuracy/actions"))
languages_dir = abspath(join(dirname(__file__), "../../pyccuracy/languages"))

def test_settings_return_default_value_for_tests_dir():
    settings = Settings({})
    assert settings.tests_dirs == [cur_dir], "The tests dir should be %s but was %s." % (cur_dir, settings.tests_dir)

def test_settings_return_default_value_for_actions_dir():
    settings = Settings({})
    assert settings.actions_dir == actions_dir, "The actions_dir dir should be %s but was %s." % (actions_dir, settings.actions_dir)

def test_settings_return_default_value_for_languages_dir():
    settings = Settings({})
    assert settings.languages_dir == languages_dir, "The languages_dir dir should be %s but was %s." % (languages_dir, settings.languages_dir)

def test_settings_return_default_value_for_pages_dir():
    settings = Settings({})
    assert settings.pages_dir == [cur_dir], "The pages dir should be %s but was %s." % (cur_dir, settings.pages_dir)

def test_settings_return_default_value_for_custom_actions_dir():
    settings = Settings({})
    assert settings.custom_actions_dir == [cur_dir], "The custom actions dir should be %s but was %s." % (cur_dir, settings.custom_actions_dir)

########NEW FILE########
__FILENAME__ = test_element_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from re import compile as re_compile
from mocker import Mocker

from pyccuracy import Page
from pyccuracy.common import Settings
from pyccuracy.errors import ActionFailedError
from pyccuracy.actions.core.element_actions import *

from ..utils import assert_raises, Object

class FakeContext(object):
    def __init__(self, mocker):
        self.settings = Settings(cur_dir='/')
        self.browser_driver = mocker.mock()
        self.language = mocker.mock()
        self.current_page = None

def test_element_click_action_calls_the_right_browser_driver_methods():
    mocker = Mocker()
    
    context = FakeContext(mocker)
    
    context.browser_driver.resolve_element_key(context, "button", "some")
    mocker.result("btnSome")
    context.browser_driver.is_element_visible("btnSome")
    mocker.result(True)
    context.browser_driver.click_element("btnSome")
    
    context.language.format("element_is_visible_failure", "button", "some")
    mocker.result("button")
    context.language.get("button_category")
    mocker.count(min=0, max=None)
    mocker.result("button")
    
    with mocker:

        action = ElementClickAction()
    
        action.execute(context, element_name="some", element_type="button", should_wait=None)

########NEW FILE########
__FILENAME__ = test_page_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from re import compile as re_compile

from mocker import Mocker

from pyccuracy import Page
from pyccuracy.common import Settings
from pyccuracy.errors import ActionFailedError
from pyccuracy.actions.core.page_actions import *

from ..utils import assert_raises, Object

class FakeContext(object):
    def __init__(self, mocker):
        self.settings = Settings(cur_dir='/')
        self.browser_driver = mocker.mock()
        self.language = mocker.mock()
        self.current_page = None

#Go To Action

def test_page_go_to_action_calls_the_right_browser_driver_methods():
    
    mocker = Mocker()
    
    context = FakeContext(mocker)
    
    context.browser_driver.page_open("file:///some_url")
    context.browser_driver.wait_for_page()

    with mocker:
        action = PageGoToAction()
    
        action.execute(context, url='"some_url"')

def test_page_go_to_action_sets_context_current_url():
    mocker = Mocker()
    
    context = FakeContext(mocker)
    
    context.browser_driver.page_open("file:///some_url")
    context.browser_driver.wait_for_page()

    with mocker:
        action = PageGoToAction()

        action.execute(context, url='"some_url"')

    assert context.url == "file:///some_url"

def test_page_go_to_action_sets_page_if_page_is_supplied():
    class SomePage(Page):
        url = "some"
        
    mocker = Mocker()
    
    context = FakeContext(mocker)
    
    context.browser_driver.page_open("file:///some")
    context.browser_driver.wait_for_page()

    with mocker:
        action = PageGoToAction()

        action.execute(context, url="Some Page")

    assert isinstance(context.current_page, SomePage)

def test_page_go_to_action_raises_with_invalid_page():
        
    mocker = Mocker()
    
    context = FakeContext(mocker)
    
    context.language.format("page_go_to_failure", "http://www.google.com")
    mocker.result("Error Message")

    with mocker:
        action = PageGoToAction()
        assert_raises(ActionFailedError, action.execute, context=context, url="http://www.google.com",
                      exc_pattern=re_compile(r'^Error Message$'))

#End Go To Action

#Go To With Parameters Action

def test_page_go_to_with_parameters_action_raises_error_when_parameters_are_invalid():
        
    mocker = Mocker()
    
    action = PageGoToWithParametersAction()
    
    context = FakeContext(mocker)
    
    context.language.format('page_go_to_with_parameters_failure', 'Blah blahabla blah')
    mocker.result('Error Message')
    
    with mocker:
                    
        assert_raises(ActionFailedError, action.parse_parameters, context, 'Blah blahabla blah')

def test_page_go_to_with_parameters_action_parses_parameters():
        
    mocker = Mocker()
    
    action = PageGoToWithParametersAction()
    
    context = FakeContext(mocker)
    
    with mocker:
        params = action.parse_parameters(context, 'parameter1 "value1"')
        assert params == { 'parameter1':'value1' }
        
        params = action.parse_parameters(context, 'query_string "?another+value=x%20y%20z"')
        assert params == { 'query_string':'?another+value=x%20y%20z' }

def test_page_go_to_with_parameters_action_parses_many_parameters():
        
    mocker = Mocker()
    
    action = PageGoToWithParametersAction()
    
    context = FakeContext(mocker)
    
    with mocker:
        params = action.parse_parameters(context, 'parameter1 "value1", parameter2 "value2"')
        assert params == { 'parameter1':'value1', 'parameter2':'value2' }
    
        params = action.parse_parameters(context, 'query_string "?another+value=x%20y%20z", user "gchapiewski"')
        assert params == { 'query_string':'?another+value=x%20y%20z', 'user':'gchapiewski' }
        
        params = action.parse_parameters(context, 'parameter1 "value1", parameter2 "value2", param3 "value3"')
        assert params == { 'parameter1':'value1', 'parameter2':'value2', 'param3':'value3' }
    
def test_page_go_to_with_parameters_action_resolves_url_for_parameter():
    action = PageGoToWithParametersAction()
    url = '/user/<username>'
    params = {'username':'gchapiewski'}
    assert action.replace_url_paremeters(url, params) == '/user/gchapiewski'

def test_page_go_to_with_parameters_action_resolves_url_for_many_parameters():
    action = PageGoToWithParametersAction()
    url = '/search.php?q=<query>&order=<order>&p=<page>'
    params = {'query':'xpto', 'order':'desc', 'page':'10' }
    assert action.replace_url_paremeters(url, params) == '/search.php?q=xpto&order=desc&p=10'
    
#End Go To With Parameters Action

#Am In Action

def test_page_am_in_action_calls_the_right_browser_driver_methods():
        
    mocker = Mocker()
    
    class SomePage(Page):
        url = "http://www.somepage.com"

    context = FakeContext(mocker)

    with mocker:
        action = PageAmInAction()
    
        action.execute(context, url="http://www.somepage.com")
        assert isinstance(context.current_page, SomePage)
        assert context.url == "http://www.somepage.com"

def test_page_am_in_action_sets_page_if_page_is_supplied():
        
    mocker = Mocker()
    
    class SomePage1(Page):
        url = "http://www.somepage.com"

    context = FakeContext(mocker)

    with mocker:
        action = PageAmInAction()
    
        action.execute(context, url="Some Page 1")
        assert isinstance(context.current_page, SomePage1)
        assert context.url == "http://www.somepage.com"

def test_page_am_in_action_raises_if_no_page():
        
    mocker = Mocker()

    context = FakeContext(mocker)
    
    context.language.format("page_am_in_failure", "http://www.google.com")
    mocker.result("Error Message")
    
    with mocker:
        action = PageAmInAction()
    
        assert_raises(ActionFailedError, action.execute, context=context, url="http://www.google.com",
                      exc_pattern=re_compile(r'^Error Message$'))

#End Am In Action

# Page See Title Action

def test_page_see_title_action_calls_the_right_browser_driver_methods():
        
    mocker = Mocker()

    context = FakeContext(mocker)
    
    context.browser_driver.get_title()
    mocker.result("some title")
    
    with mocker:

        action = PageSeeTitleAction()
    
        action.execute(context, title="some title")

#End Page See Title Action

########NEW FILE########
__FILENAME__ = airspeed_test
#!/usr/bin/env python
# -*- coding: latin1 -*-

from unittest import TestCase, main
from pyccuracy import airspeed
import re

###############################################################################
# Compatibility for old Pythons & Jython
###############################################################################
try: True
except NameError:
    False, True = 0, 1


class TemplateTestCase(TestCase):

    def test_parser_returns_input_when_there_is_nothing_to_substitute(self):
        template = airspeed.Template("<html></html>")
        self.assertEquals("<html></html>", template.merge({}))

    def test_parser_substitutes_string_added_to_the_context(self):
        template = airspeed.Template("Hello $name")
        self.assertEquals("Hello Chris", template.merge({"name": "Chris"}))

    def test_dollar_left_untouched(self):
        template = airspeed.Template("Hello $ ")
        self.assertEquals("Hello $ ", template.merge({}))
        template = airspeed.Template("Hello $")
        self.assertEquals("Hello $", template.merge({}))

    def test_unmatched_name_does_not_get_substituted(self):
        template = airspeed.Template("Hello $name")
        self.assertEquals("Hello $name", template.merge({}))

    def test_silent_substitution_for_unmatched_values(self):
        template = airspeed.Template("Hello $!name")
        self.assertEquals("Hello world", template.merge({"name": "world"}))
        self.assertEquals("Hello ", template.merge({}))

    def test_formal_reference_in_an_if_condition(self):
        template = airspeed.Template("#if(${a.b.c})yes!#end")
        ## reference in an if statement used to be a problem
        self.assertEquals("yes!", template.merge({'a':{'b':{'c':'d'}}}))
        self.assertEquals("", template.merge({}))

    def test_silent_formal_reference_in_an_if_condition(self):
        # the silent modifier shouldn't make a difference here
        template = airspeed.Template("#if($!{a.b.c})yes!#end")
        self.assertEquals("yes!", template.merge({'a':{'b':{'c':'d'}}}))
        self.assertEquals("", template.merge({}))
        # with or without curly braces
        template = airspeed.Template("#if($!a.b.c)yes!#end")
        self.assertEquals("yes!", template.merge({'a':{'b':{'c':'d'}}}))
        self.assertEquals("", template.merge({}))

    def test_reference_function_calls_in_if_conditions(self):
        template = airspeed.Template("#if(${a.b.c('cheese')})yes!#end")
        self.assertEquals("yes!", template.merge({'a':{'b':{'c':lambda x: "hello %s" % x}}}))
        self.assertEquals("", template.merge({'a':{'b':{'c':lambda x: None}}}))
        self.assertEquals("", template.merge({}))

    def test_silent_reference_function_calls_in_if_conditions(self):
        # again, this shouldn't make any difference
        template = airspeed.Template("#if($!{a.b.c('cheese')})yes!#end")
        self.assertEquals("yes!", template.merge({'a':{'b':{'c':lambda x: "hello %s" % x}}}))
        self.assertEquals("", template.merge({'a':{'b':{'c':lambda x: None}}}))
        self.assertEquals("", template.merge({}))
        # with or without braces
        template = airspeed.Template("#if($!a.b.c('cheese'))yes!#end")
        self.assertEquals("yes!", template.merge({'a':{'b':{'c':lambda x: "hello %s" % x}}}))
        self.assertEquals("", template.merge({'a':{'b':{'c':lambda x: None}}}))
        self.assertEquals("", template.merge({}))

    def test_embed_substitution_value_in_braces_gets_handled(self):
        template = airspeed.Template("Hello ${name}.")
        self.assertEquals("Hello World.", template.merge({"name": "World"}))

    def test_unmatched_braces_raises_exception(self):
        template = airspeed.Template("Hello ${name.")
        self.assertRaises(airspeed.TemplateSyntaxError, template.merge, {})

    def test_unmatched_trailing_brace_preserved(self):
        template = airspeed.Template("Hello $name}.")
        self.assertEquals("Hello World}.", template.merge({"name": "World"}))

    def test_can_return_value_from_an_attribute_of_a_context_object(self):
        template = airspeed.Template("Hello $name.first_name")
        class MyObj: pass
        o = MyObj()
        o.first_name = 'Chris'
        self.assertEquals("Hello Chris", template.merge({"name": o}))

    def test_can_return_value_from_an_attribute_of_a_context_object(self):
        template = airspeed.Template("Hello $name.first_name")
        class MyObj: pass
        o = MyObj()
        o.first_name = 'Chris'
        self.assertEquals("Hello Chris", template.merge({"name": o}))

    def test_can_return_value_from_a_method_of_a_context_object(self):
        template = airspeed.Template("Hello $name.first_name()")
        class MyObj:
            def first_name(self): return "Chris"
        self.assertEquals("Hello Chris", template.merge({"name": MyObj()}))

    def test_when_if_statement_resolves_to_true_the_content_is_returned(self):
        template = airspeed.Template("Hello #if ($name)your name is ${name}#end Good to see you")
        self.assertEquals("Hello your name is Steve Good to see you", template.merge({"name": "Steve"}))

    def test_when_if_statement_resolves_to_false_the_content_is_skipped(self):
        template = airspeed.Template("Hello #if ($show_greeting)your name is ${name}#end Good to see you")
        self.assertEquals("Hello  Good to see you", template.merge({"name": "Steve", "show_greeting": False}))

    def test_when_if_statement_is_nested_inside_a_successful_enclosing_if_it_gets_evaluated(self):
        template = airspeed.Template("Hello #if ($show_greeting)your name is ${name}.#if ($is_birthday) Happy Birthday.#end#end Good to see you")
        namespace = {"name": "Steve", "show_greeting": False}
        self.assertEquals("Hello  Good to see you", template.merge(namespace))
        namespace["show_greeting"] = True
        self.assertEquals("Hello your name is Steve. Good to see you", template.merge(namespace))
        namespace["is_birthday"] = True
        self.assertEquals("Hello your name is Steve. Happy Birthday. Good to see you", template.merge(namespace))

    def test_if_statement_considers_None_to_be_false(self):
        template = airspeed.Template("#if ($some_value)hide me#end")
        self.assertEquals('', template.merge({}))
        self.assertEquals('', template.merge({'some_value': None}))

    def test_if_statement_honours_custom_truth_value_of_objects(self):
        class BooleanValue:
            def __init__(self, value): self.value = value
            def __nonzero__(self): return self.value
        template = airspeed.Template("#if ($v)yes#end")
        self.assertEquals('', template.merge({'v': BooleanValue(False)}))
        self.assertEquals('yes', template.merge({'v': BooleanValue(True)}))

    def test_understands_boolean_literal_true(self):
        template = airspeed.Template("#set ($v = true)$v")
        self.assertEquals('True', template.merge({}))

    def test_understands_boolean_literal_false(self):
        template = airspeed.Template("#set ($v = false)$v")
        self.assertEquals('False', template.merge({}))

    def test_new_lines_in_templates_are_permitted(self):
        template = airspeed.Template("hello #if ($show_greeting)${name}.\n#if($is_birthday)Happy Birthday\n#end.\n#endOff out later?")
        namespace = {"name": "Steve", "show_greeting": True, "is_birthday": True}
        self.assertEquals("hello Steve.\nHappy Birthday\n.\nOff out later?", template.merge(namespace))

    def test_foreach_with_plain_content_loops_correctly(self):
        template = airspeed.Template("#foreach ($name in $names)Hello you. #end")
        self.assertEquals("Hello you. Hello you. ", template.merge({"names": ["Chris", "Steve"]}))

    def test_foreach_skipped_when_nested_in_a_failing_if(self):
        template = airspeed.Template("#if ($false_value)#foreach ($name in $names)Hello you. #end#end")
        self.assertEquals("", template.merge({"false_value": False, "names": ["Chris", "Steve"]}))

    def test_foreach_with_expression_content_loops_correctly(self):
        template = airspeed.Template("#foreach ($name in $names)Hello $you. #end")
        self.assertEquals("Hello You. Hello You. ", template.merge({"you": "You", "names": ["Chris", "Steve"]}))

    def test_foreach_makes_loop_variable_accessible(self):
        template = airspeed.Template("#foreach ($name in $names)Hello $name. #end")
        self.assertEquals("Hello Chris. Hello Steve. ", template.merge({"names": ["Chris", "Steve"]}))

    def test_loop_variable_not_accessible_after_loop(self):
        template = airspeed.Template("#foreach ($name in $names)Hello $name. #end$name")
        self.assertEquals("Hello Chris. Hello Steve. $name", template.merge({"names": ["Chris", "Steve"]}))

    def test_loop_variables_do_not_clash_in_nested_loops(self):
        template = airspeed.Template("#foreach ($word in $greetings)$word to#foreach ($word in $names) $word#end. #end")
        namespace = {"greetings": ["Hello", "Goodbye"], "names": ["Chris", "Steve"]}
        self.assertEquals("Hello to Chris Steve. Goodbye to Chris Steve. ", template.merge(namespace))

    def test_loop_counter_variable_available_in_loops(self):
        template = airspeed.Template("#foreach ($word in $greetings)$velocityCount,#end")
        namespace = {"greetings": ["Hello", "Goodbye"]}
        self.assertEquals("1,2,", template.merge(namespace))

    def test_loop_counter_variables_do_not_clash_in_nested_loops(self):
        template = airspeed.Template("#foreach ($word in $greetings)Outer $velocityCount#foreach ($word in $names), inner $velocityCount#end. #end")
        namespace = {"greetings": ["Hello", "Goodbye"], "names": ["Chris", "Steve"]}
        self.assertEquals("Outer 1, inner 1, inner 2. Outer 2, inner 1, inner 2. ", template.merge(namespace))

    def test_can_use_an_integer_variable_defined_in_template(self):
        template = airspeed.Template("#set ($value = 10)$value")
        self.assertEquals("10", template.merge({}))

    def test_passed_in_namespace_not_modified_by_set(self):
        template = airspeed.Template("#set ($value = 10)$value")
        namespace = {}
        template.merge(namespace)
        self.assertEquals({}, namespace)

    def test_can_use_a_string_variable_defined_in_template(self):
        template = airspeed.Template('#set ($value = "Steve")$value')
        self.assertEquals("Steve", template.merge({}))

    def test_can_use_a_single_quoted_string_variable_defined_in_template(self):
        template = airspeed.Template("#set ($value = 'Steve')$value")
        self.assertEquals("Steve", template.merge({}))

    def test_single_line_comments_skipped(self):
        template = airspeed.Template('## comment\nStuff\nMore stuff## more comments $blah')
        self.assertEquals("Stuff\nMore stuff", template.merge({}))

    def test_multi_line_comments_skipped(self):
        template = airspeed.Template('Stuff#*\n more comments *#\n and more stuff')
        self.assertEquals("Stuff and more stuff", template.merge({}))

    def test_merge_to_stream(self):
        template = airspeed.Template('Hello $name!')
        from cStringIO import StringIO
        output = StringIO()
        template.merge_to({"name": "Chris"}, output)
        self.assertEquals('Hello Chris!', output.getvalue())

    def test_string_literal_can_contain_embedded_escaped_quotes(self):
        template = airspeed.Template('#set ($name = "\\"batman\\"")$name')
        self.assertEquals('"batman"', template.merge({}))

    def test_string_literal_can_contain_embedded_escaped_newlines(self):
        template = airspeed.Template('#set ($name = "\\\\batman\\nand robin")$name')
        self.assertEquals('\\batman\nand robin', template.merge({}))

    def test_else_block_evaluated_when_if_expression_false(self):
        template = airspeed.Template('#if ($value) true #else false #end')
        self.assertEquals(" false ", template.merge({}))

    def test_curly_else(self):
        template = airspeed.Template('#if($value)true#{else}false#end')
        self.assertEquals("false", template.merge({}))

    def test_curly_end(self):
        template = airspeed.Template('#if($value)true#{end}monkey')
        self.assertEquals("monkey", template.merge({}))

    def test_too_many_end_clauses_trigger_error(self):
        template = airspeed.Template('#if (1)true!#end #end ')
        self.assertRaises(airspeed.TemplateSyntaxError, template.merge, {})

    def test_can_call_function_with_one_parameter(self):
        def squared(number):
            return number * number
        template = airspeed.Template('$squared(8)')
        self.assertEquals("64", template.merge(locals()))
        some_var = 6
        template = airspeed.Template('$squared($some_var)')
        self.assertEquals("36", template.merge(locals()))
        template = airspeed.Template('$squared($squared($some_var))')
        self.assertEquals("1296", template.merge(locals()))

    def test_can_call_function_with_two_parameters(self):
        def multiply(number1, number2):
            return number1 * number2
        template = airspeed.Template('$multiply(2, 4)')
        self.assertEquals("8", template.merge(locals()))
        template = airspeed.Template('$multiply( 2 , 4 )')
        self.assertEquals("8", template.merge(locals()))
        value1, value2 = 4, 12
        template = airspeed.Template('$multiply($value1,$value2)')
        self.assertEquals("48", template.merge(locals()))

    def test_velocity_style_escaping(self): # example from Velocity docs
        template = airspeed.Template('''\
#set( $email = "foo" )
$email
\\$email
\\\\$email
\\\\\\$email''')
        self.assertEquals('''\
foo
$email
\\foo
\\$email''', template.merge({}))

#    def test_velocity_style_escaping_when_var_unset(self): # example from Velocity docs
#        template = airspeed.Template('''\
#$email
#\$email
#\\$email
#\\\$email''')
#        self.assertEquals('''\
#$email
#\$email
#\\$email
#\\\$email''', template.merge({}))

    def test_true_elseif_evaluated_when_if_is_false(self):
        template = airspeed.Template('#if ($value1) one #elseif ($value2) two #end')
        value1, value2 = False, True
        self.assertEquals(' two ', template.merge(locals()))

    def test_false_elseif_skipped_when_if_is_true(self):
        template = airspeed.Template('#if ($value1) one #elseif ($value2) two #end')
        value1, value2 = True, False
        self.assertEquals(' one ', template.merge(locals()))

    def test_first_true_elseif_evaluated_when_if_is_false(self):
        template = airspeed.Template('#if ($value1) one #elseif ($value2) two #elseif($value3) three #end')
        value1, value2, value3 = False, True, True
        self.assertEquals(' two ', template.merge(locals()))

    def test_illegal_to_have_elseif_after_else(self):
        template = airspeed.Template('#if ($value1) one #else two #elseif($value3) three #end')
        self.assertRaises(airspeed.TemplateSyntaxError, template.merge, {})

    def test_else_evaluated_when_if_and_elseif_are_false(self):
        template = airspeed.Template('#if ($value1) one #elseif ($value2) two #else three #end')
        value1, value2 = False, False
        self.assertEquals(' three ', template.merge(locals()))

    def test_syntax_error_contains_line_and_column_pos(self):
        try: airspeed.Template('#if ( $hello )\n\n#elseif blah').merge({})
        except airspeed.TemplateSyntaxError, e:
            self.assertEquals((3, 9), (e.line, e.column))
        else: self.fail('expected error')
        try: airspeed.Template('#else blah').merge({})
        except airspeed.TemplateSyntaxError, e:
            self.assertEquals((1, 1), (e.line, e.column))
        else: self.fail('expected error')

    def test_get_position_strings_in_syntax_error(self):
        try: airspeed.Template('#else whatever').merge({})
        except airspeed.TemplateSyntaxError, e:
            self.assertEquals(['#else whatever',
                               '^'], e.get_position_strings())
        else: self.fail('expected error')

    def test_get_position_strings_in_syntax_error_when_newline_after_error(self):
        try: airspeed.Template('#else whatever\n').merge({})
        except airspeed.TemplateSyntaxError, e:
            self.assertEquals(['#else whatever',
                               '^'], e.get_position_strings())
        else: self.fail('expected error')

    def test_get_position_strings_in_syntax_error_when_newline_before_error(self):
        try: airspeed.Template('foobar\n  #else whatever\n').merge({})
        except airspeed.TemplateSyntaxError, e:
            self.assertEquals(['  #else whatever',
                               '  ^'], e.get_position_strings())
        else: self.fail('expected error')

    def test_compare_greater_than_operator(self):
        template = airspeed.Template('#if ( $value > 1 )yes#end')
        self.assertEquals('', template.merge({'value': 0}))
        self.assertEquals('', template.merge({'value': 1}))
        self.assertEquals('yes', template.merge({'value': 2}))

    def test_compare_greater_than_or_equal_operator(self):
        template = airspeed.Template('#if ( $value >= 1 )yes#end')
        self.assertEquals('', template.merge({'value': 0}))
        self.assertEquals('yes', template.merge({'value': 1}))
        self.assertEquals('yes', template.merge({'value': 2}))

    def test_compare_less_than_operator(self):
        template = airspeed.Template('#if ( $value < 1 )yes#end')
        self.assertEquals('yes', template.merge({'value': 0}))
        self.assertEquals('', template.merge({'value': 1}))
        self.assertEquals('', template.merge({'value': 2}))

    def test_compare_less_than_or_equal_operator(self):
        template = airspeed.Template('#if ( $value <= 1 )yes#end')
        self.assertEquals('yes', template.merge({'value': 0}))
        self.assertEquals('yes', template.merge({'value': 1}))
        self.assertEquals('', template.merge({'value': 2}))

    def test_compare_equality_operator(self):
        template = airspeed.Template('#if ( $value == 1 )yes#end')
        self.assertEquals('', template.merge({'value': 0}))
        self.assertEquals('yes', template.merge({'value': 1}))
        self.assertEquals('', template.merge({'value': 2}))

    def test_or_operator(self):
        template = airspeed.Template('#if ( $value1 || $value2 )yes#end')
        self.assertEquals('', template.merge({'value1': False, 'value2': False}))
        self.assertEquals('yes', template.merge({'value1': True, 'value2': False}))
        self.assertEquals('yes', template.merge({'value1': False, 'value2': True}))

    def test_or_operator_otherform(self):
        template = airspeed.Template('#if ( $value1 or $value2 )yes#end')
        self.assertEquals('', template.merge({'value1': False, 'value2': False}))
        self.assertEquals('yes', template.merge({'value1': True, 'value2': False}))
        self.assertEquals('yes', template.merge({'value1': False, 'value2': True}))

    def test_or_operator_considers_not_None_values_true(self):
        class SomeClass: pass
        template = airspeed.Template('#if ( $value1 || $value2 )yes#end')
        self.assertEquals('', template.merge({'value1': None, 'value2': None}))
        self.assertEquals('yes', template.merge({'value1': SomeClass(), 'value2': False}))
        self.assertEquals('yes', template.merge({'value1': False, 'value2': SomeClass()}))

    def test_and_operator(self):
        template = airspeed.Template('#if ( $value1 && $value2 )yes#end')
        self.assertEquals('', template.merge({'value1': False, 'value2': False}))
        self.assertEquals('', template.merge({'value1': True, 'value2': False}))
        self.assertEquals('', template.merge({'value1': False, 'value2': True}))
        self.assertEquals('yes', template.merge({'value1': True, 'value2': True}))

    def test_and_operator_otherform(self):
        template = airspeed.Template('#if ( $value1 and $value2 )yes#end')
        self.assertEquals('', template.merge({'value1': False, 'value2': False}))
        self.assertEquals('', template.merge({'value1': True, 'value2': False}))
        self.assertEquals('', template.merge({'value1': False, 'value2': True}))
        self.assertEquals('yes', template.merge({'value1': True, 'value2': True}))

    def test_and_operator_considers_not_None_values_true(self):
        class SomeClass: pass
        template = airspeed.Template('#if ( $value1 && $value2 )yes#end')
        self.assertEquals('', template.merge({'value1': None, 'value2': None}))
        self.assertEquals('yes', template.merge({'value1': SomeClass(), 'value2': True}))
        self.assertEquals('yes', template.merge({'value1': True, 'value2': SomeClass()}))

    def test_parenthesised_value(self):
        template = airspeed.Template('#if ( ($value1 == 1) && ($value2 == 2) )yes#end')
        self.assertEquals('', template.merge({'value1': 0, 'value2': 1}))
        self.assertEquals('', template.merge({'value1': 1, 'value2': 1}))
        self.assertEquals('', template.merge({'value1': 0, 'value2': 2}))
        self.assertEquals('yes', template.merge({'value1': 1, 'value2': 2}))

    def test_multiterm_expression(self):
        template = airspeed.Template('#if ( $value1 == 1 && $value2 == 2 )yes#end')
        self.assertEquals('', template.merge({'value1': 0, 'value2': 1}))
        self.assertEquals('', template.merge({'value1': 1, 'value2': 1}))
        self.assertEquals('', template.merge({'value1': 0, 'value2': 2}))
        self.assertEquals('yes', template.merge({'value1': 1, 'value2': 2}))

    def test_compound_condition(self):
        template = airspeed.Template('#if ( ($value) )yes#end')
        self.assertEquals('', template.merge({'value': False}))
        self.assertEquals('yes', template.merge({'value': True}))

    def test_logical_negation_operator(self):
        template = airspeed.Template('#if ( !$value )yes#end')
        self.assertEquals('yes', template.merge({'value': False}))
        self.assertEquals('', template.merge({'value': True}))

    def test_logical_negation_operator_yields_true_for_None(self):
        template = airspeed.Template('#if ( !$value )yes#end')
        self.assertEquals('yes', template.merge({'value': None}))

    def test_logical_negation_operator_honours_custom_truth_values(self):
        class BooleanValue:
            def __init__(self, value): self.value = value
            def __nonzero__(self): return self.value
        template = airspeed.Template('#if ( !$v)yes#end')
        self.assertEquals('yes', template.merge({'v': BooleanValue(False)}))
        self.assertEquals('', template.merge({'v': BooleanValue(True)}))

    def test_compound_binary_and_unary_operators(self):
        template = airspeed.Template('#if ( !$value1 && !$value2 )yes#end')
        self.assertEquals('', template.merge({'value1': False, 'value2': True}))
        self.assertEquals('', template.merge({'value1': True, 'value2': False}))
        self.assertEquals('', template.merge({'value1': True, 'value2': True}))
        self.assertEquals('yes', template.merge({'value1': False, 'value2': False}))

    def test_cannot_define_macro_to_override_reserved_statements(self):
        for reserved in ('if', 'else', 'elseif', 'set', 'macro', 'foreach', 'parse', 'include', 'stop', 'end'):
            template = airspeed.Template('#macro ( %s $value) $value #end' % reserved)
            self.assertRaises(airspeed.TemplateSyntaxError, template.merge, {})

    def test_cannot_call_undefined_macro(self):
        template = airspeed.Template('#undefined()')
        self.assertRaises(Exception, template.merge, {})

    def test_define_and_use_macro_with_no_parameters(self):
        template = airspeed.Template('#macro ( hello)hi#end#hello ()#hello()')
        self.assertEquals('hihi', template.merge({'text': 'hello'}))

    def test_define_and_use_macro_with_one_parameter(self):
        template = airspeed.Template('#macro ( bold $value)<strong>$value</strong>#end#bold ($text)')
        self.assertEquals('<strong>hello</strong>', template.merge({'text': 'hello'}))

    def test_define_and_use_macro_with_two_parameters_no_comma(self):
        template = airspeed.Template('#macro ( bold $value $other)<strong>$value</strong>$other#end#bold ($text $monkey)')
        self.assertEquals('<strong>hello</strong>cheese', template.merge({'text': 'hello','monkey':'cheese'}))

    # we use commas with our macros and it seems to work
    # so it's correct behavior by definition; the real
    # question is whether using them w/o a comma is a legal variant
    # or not.  This should effect the above test; the following test
    # should be legal by defintion

    def test_define_and_use_macro_with_two_parameters_with_comma(self):
        template = airspeed.Template('#macro ( bold $value, $other)<strong>$value</strong>$other#end#bold ($text, $monkey)')
        self.assertEquals('<strong>hello</strong>cheese', template.merge({'text': 'hello','monkey':'cheese'}))

    def test_use_of_macro_name_is_case_insensitive(self):
        template = airspeed.Template('#macro ( bold $value)<strong>$value</strong>#end#BoLd ($text)')
        self.assertEquals('<strong>hello</strong>', template.merge({'text': 'hello'}))

    def test_define_and_use_macro_with_two_parameter(self):
        template = airspeed.Template('#macro (addition $value1 $value2 )$value1+$value2#end#addition (1 2)')
        self.assertEquals('1+2', template.merge({}))
        template = airspeed.Template('#macro (addition $value1 $value2 )$value1+$value2#end#addition( $one   $two )')
        self.assertEquals('ONE+TWO', template.merge({'one': 'ONE', 'two': 'TWO'}))

    def test_cannot_redefine_macro(self):
        template = airspeed.Template('#macro ( hello)hi#end#macro(hello)again#end')
        self.assertRaises(Exception, template.merge, {}) ## Should this be TemplateSyntaxError?

    def test_include_directive_gives_error_if_no_loader_provided(self):
        template = airspeed.Template('#include ("foo.tmpl")')
        self.assertRaises(airspeed.TemplateError, template.merge, {})

    def test_include_directive_yields_loader_error_if_included_content_not_found(self):
        class BrokenLoader:
            def load_text(self, name):
                raise IOError(name)
        template = airspeed.Template('#include ("foo.tmpl")')
        self.assertRaises(IOError, template.merge, {}, loader=BrokenLoader())

    def test_valid_include_directive_include_content(self):
        class WorkingLoader:
            def load_text(self, name):
                if name == 'foo.tmpl':
                    return "howdy"
        template = airspeed.Template('Message is: #include ("foo.tmpl")!')
        self.assertEquals('Message is: howdy!', template.merge({}, loader=WorkingLoader()))

    def test_parse_directive_gives_error_if_no_loader_provided(self):
        template = airspeed.Template('#parse ("foo.tmpl")')
        self.assertRaises(airspeed.TemplateError, template.merge, {})

    def test_parse_directive_yields_loader_error_if_parsed_content_not_found(self):
        class BrokenLoader:
            def load_template(self, name):
                raise IOError(name)
        template = airspeed.Template('#parse ("foo.tmpl")')
        self.assertRaises(IOError, template.merge, {}, loader=BrokenLoader())

    def test_valid_parse_directive_outputs_parsed_content(self):
        class WorkingLoader:
            def load_template(self, name):
                if name == 'foo.tmpl':
                    return airspeed.Template("$message")
        template = airspeed.Template('Message is: #parse ("foo.tmpl")!')
        self.assertEquals('Message is: hola!', template.merge({'message': 'hola'}, loader=WorkingLoader()))
        template = airspeed.Template('Message is: #parse ($foo)!')
        self.assertEquals('Message is: hola!', template.merge({'foo': 'foo.tmpl', 'message': 'hola'}, loader=WorkingLoader()))

    def test_assign_range_literal(self):
        template = airspeed.Template('#set($values = [1..5])#foreach($value in $values)$value,#end')
        self.assertEquals('1,2,3,4,5,', template.merge({}))
        template = airspeed.Template('#set($values = [2..-2])#foreach($value in $values)$value,#end')
        self.assertEquals('2,1,0,-1,-2,', template.merge({}))

    def test_local_namespace_methods_are_not_available_in_context(self):
        template = airspeed.Template('#macro(tryme)$values#end#tryme()')
        self.assertEquals('$values', template.merge({}))

    def test_array_literal(self):
        template = airspeed.Template('blah\n#set($valuesInList = ["Hello ", $person, ", your lucky number is ", 7])\n#foreach($value in $valuesInList)$value#end\n\nblah')
        self.assertEquals('blah\nHello Chris, your lucky number is 7\nblah', template.merge({'person': 'Chris'}))
        # NOTE: the original version of this test incorrectly preserved
        # the newline at the end of the #end line

    def test_dictionary_literal(self):
        template = airspeed.Template('#set($a = {"dog": "cat" , "horse":15})$a.dog')
        self.assertEquals('cat', template.merge({}))
        template = airspeed.Template('#set($a = {"dog": "$horse"})$a.dog')
        self.assertEquals('cow', template.merge({'horse':'cow'}))

    def test_dictionary_literal_as_parameter(self):
        template = airspeed.Template('$a({"color":"blue"})')
        ns = {'a':lambda x: x['color'] + ' food'}
        self.assertEquals('blue food', template.merge(ns))

    def test_nested_array_literals(self):
        template = airspeed.Template('#set($values = [["Hello ", "Steve"], ["Hello", " Chris"]])#foreach($pair in $values)#foreach($word in $pair)$word#end. #end')
        self.assertEquals('Hello Steve. Hello Chris. ', template.merge({}))

    def test_when_dictionary_does_not_contain_referenced_attribute_no_substitution_occurs(self):
        template = airspeed.Template(" $user.name ")
        self.assertEquals(" $user.name ", template.merge({'user':self}))

    def test_when_non_dictionary_object_does_not_contain_referenced_attribute_no_substitution_occurs(self):
        class MyObject: pass
        template = airspeed.Template(" $user.name ")
        self.assertEquals(" $user.name ", template.merge({'user':MyObject()}))

    def test_variables_expanded_in_double_quoted_strings(self):
        template = airspeed.Template('#set($hello="hello, $name is my name")$hello')
        self.assertEquals("hello, Steve is my name", template.merge({'name':'Steve'}))

    def test_escaped_variable_references_not_expanded_in_double_quoted_strings(self):
        template = airspeed.Template('#set($hello="hello, \\$name is my name")$hello')
        self.assertEquals("hello, $name is my name", template.merge({'name':'Steve'}))

    def test_macros_expanded_in_double_quoted_strings(self):
        template = airspeed.Template('#macro(hi $person)$person says hello#end#set($hello="#hi($name)")$hello')
        self.assertEquals("Steve says hello", template.merge({'name':'Steve'}))

    def test_color_spec(self):
        template = airspeed.Template('<span style="color: #13ff93">')
        self.assertEquals('<span style="color: #13ff93">', template.merge({}))

    # check for a plain hash outside of a context where it could be
    # confused with a directive or macro call.
    # this is useful for cases where someone put a hash in the target
    # of a link, which is typical when javascript is associated with the link

    def test_standalone_hashes(self):
        template = airspeed.Template('#')
        self.assertEquals('#', template.merge({}))
        template = airspeed.Template('"#"')
        self.assertEquals('"#"', template.merge({}))
        template = airspeed.Template('<a href="#">bob</a>')
        self.assertEquals('<a href="#">bob</a>', template.merge({}))

    def test_large_areas_of_text_handled_without_error(self):
        text = "qwerty uiop asdfgh jkl zxcvbnm. 1234" * 300
        template = airspeed.Template(text)
        self.assertEquals(text, template.merge({}))

    def test_foreach_with_unset_variable_expands_to_nothing(self):
        template = airspeed.Template('#foreach($value in $values)foo#end')
        self.assertEquals('', template.merge({}))

    def test_foreach_with_non_iterable_variable_raises_error(self):
        template = airspeed.Template('#foreach($value in $values)foo#end')
        self.assertRaises(ValueError, template.merge, {'values': 1})

    def test_correct_scope_for_parameters_of_method_calls(self):
        template = airspeed.Template('$obj.get_self().method($param)')
        class C:
            def get_self(self):
                return self
            def method(self, p):
                if p == 'bat': return 'monkey'
        value = template.merge({'obj': C(), 'param':'bat'})
        self.assertEquals('monkey', value)

    def test_preserves_unicode_strings(self):
        template = airspeed.Template('$value')
        value = unicode('Gr��e', 'latin1')
        self.assertEquals(value, template.merge(locals()))

    def test_can_define_macros_in_parsed_files(self):
        class Loader:
            def load_template(self, name):
                if name == 'foo.tmpl':
                    return airspeed.Template('#macro(themacro)works#end')
        template = airspeed.Template('#parse("foo.tmpl")#themacro()')
        self.assertEquals('works', template.merge({}, loader=Loader()))

    def test_modulus_operator(self):
        template = airspeed.Template('#set( $modulus = ($value % 2) )$modulus')
        self.assertEquals('1', template.merge({'value': 3}))

    def test_can_assign_empty_string(self):
        template = airspeed.Template('#set( $v = "" )#set( $y = \'\' ).$v.$y.')
        self.assertEquals('...', template.merge({}))

    def test_can_loop_over_numeric_ranges(self):
        ## Test for bug #15
        template = airspeed.Template('#foreach( $v in [1..5] )$v\n#end')
        self.assertEquals('1\n2\n3\n4\n5\n', template.merge({}))

    def test_can_loop_over_numeric_ranges_backwards(self):
        template = airspeed.Template('#foreach( $v in [5..-2] )$v,#end')
        self.assertEquals('5,4,3,2,1,0,-1,-2,', template.merge({}))

    def test_ranges_over_references(self):
        template = airspeed.Template("#set($start = 1)#set($end = 5)#foreach($i in [$start .. $end])$i-#end")
        self.assertEquals('1-2-3-4-5-', template.merge({}))

    def test_user_defined_directive(self):
        class DummyDirective(airspeed._Element):
            PLAIN = re.compile(r'#(monkey)man(.*)$', re.S + re.I)

            def parse(self):
                self.text, = self.identity_match(self.PLAIN)

            def evaluate(self, stream, namespace, loader):
                stream.write(self.text)

        airspeed.UserDefinedDirective.DIRECTIVES.append(DummyDirective)
        template = airspeed.Template("hello #monkeyman")
        self.assertEquals('hello monkey', template.merge({}))
        airspeed.UserDefinedDirective.DIRECTIVES.remove(DummyDirective)

    def test_stop_directive(self):
        template = airspeed.Template("hello #stop world")
        self.assertEquals('hello ', template.merge({}))


    def test_assignment_of_parenthesized_math_expression(self):
        template = airspeed.Template('#set($a = (5 + 4))$a')
        self.assertEquals('9', template.merge({}))

    def test_assignment_of_parenthesized_math_expression_with_reference(self):
        template = airspeed.Template('#set($b = 5)#set($a = ($b + 4))$a')
        self.assertEquals('9', template.merge({}))

    def test_recursive_macro(self):
        template = airspeed.Template('#macro ( recur $number)#if ($number > 0)#set($number = $number - 1)#recur($number)X#end#end#recur(5)')
        self.assertEquals('XXXXX', template.merge({}))

    def test_addition_has_higher_precedence_than_comparison(self):
        template = airspeed.Template('#set($a = 4 > 2 + 5)$a')
        self.assertEquals('False', template.merge({}))

    def test_parentheses_work(self):
        template = airspeed.Template('#set($a = (5 + 4) > 2)$a')
        self.assertEquals('True', template.merge({}))

    def test_addition_has_higher_precedence_than_comparison_other_direction(self):
        template = airspeed.Template('#set($a = 5 + 4 > 2)$a')
        self.assertEquals('True', template.merge({}))

    # Note: this template:
    # template = airspeed.Template('#set($a = (4 > 2) + 5)$a')
    # prints 6.  That's because Python automatically promotes True to 1
    # and False to 0.
    # This is weird, but I can't say it's wrong.

    def test_multiplication_has_higher_precedence_than_addition(self):
        template = airspeed.Template("#set($a = 5 * 4 - 2)$a")
        self.assertEquals('18', template.merge({}))

    def test_parse_empty_dictionary(self):
        template = airspeed.Template('#set($a = {})$a')
        self.assertEquals('{}', template.merge({}))

    def test_macro_whitespace_and_newlines_ignored(self):
        template = airspeed.Template('''#macro ( blah )
hello##
#end
#blah()''')
        self.assertEquals('hello', template.merge({}))

    def test_if_whitespace_and_newlines_ignored(self):
        template = airspeed.Template('''#if(true)
hello##
#end''')
        self.assertEquals('hello', template.merge({}))

    def test_subobject_assignment(self):
        template = airspeed.Template("#set($outer.inner = 'monkey')")
        x = {'outer':{}}
        template.merge(x)
        self.assertEquals('monkey', x['outer']['inner'])

    def test_expressions_with_numbers_with_fractions(self):
        template = airspeed.Template('#set($a = 100.0 / 50)$a')
        self.assertEquals('2.0', template.merge({}))
        # TODO: is that how Velocity would format a floating point?

    def test_multiline_arguments_to_function_calls(self):
        class Thing:
            def func(self, arg):
                return 'y'
        template = airspeed.Template('''$x.func("multi
line")''')
        self.assertEquals('y', template.merge({'x':Thing()}))


# TODO:
#
#  Report locations for template errors in strings
#  Gobbling up whitespace (see WHITESPACE_TO_END_OF_LINE above, but need to apply in more places)
#  Bind #macro calls at compile time?
#  Scope of #set across if/elseif/else?
#  there seems to be some confusion about the semantics of parameter passing to macros; an assignment in a macro body should persist past the macro call.  Confirm against Velocity.


if __name__ == '__main__':
    reload(airspeed)
    try: main()
    except SystemExit: pass

########NEW FILE########
__FILENAME__ = test_actions
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mocker import Mocker, ANY
from nose.tools import raises, set_trace

from pyccuracy import ActionBase, ActionRegistry
from pyccuracy.languages import LanguageItem
from pyccuracy.errors import LanguageDoesNotResolveError

from utils import Object

def test_construction():
    class DoNothingAction(ActionBase):
        regex = r'^My Regex$'
        def execute(self, context, *args, **kwargs):
            pass

    assert DoNothingAction.regex == r'^My Regex$'

@raises(NotImplementedError)
def test_construction_fails_without_implementing_execute():
    class DoNothingAction(ActionBase):
        regex = r'^My Regex$'

@raises(NotImplementedError)
def test_construction_fails_without_implementing_setting_regex():
    class DoNothingAction(ActionBase):
        def execute(self, context, *args, **kw):
            pass

@raises(NotImplementedError)
def test_construction_fails_without_implementing_basic_attrs():
    class DoNothingAction(ActionBase):
        pass

@raises(TypeError)
def test_construction_fails_if_regex_nonstring():
    class DoNothingAction(ActionBase):
        regex = range(10)
        def execute(self, context, *args, **kw):
            pass

def test_can_resolve_string():
    class DoSomethingAction(ActionBase):
        regex = r'^(And )?I do "(?P<what>\w+)"$'
        def execute(self, context, *args, **kwargs):
            pass

    assert DoSomethingAction.can_resolve('And I do "test"')
    assert DoSomethingAction.can_resolve('I do "test"')

def test_cannot_resolve_string():
    class DoSomethingAction(ActionBase):
        regex = r'^(And )?I do "(?P<what>\w+)"$'
        def execute(self, context, *args, **kwargs):
            pass

    assert not DoSomethingAction.can_resolve('Not for me')
    assert not DoSomethingAction.can_resolve('Foo Bar')

def test_action_registry_suitable_for_returns_my_action():
    
    mocker = Mocker()
    
    class MyAction(ActionBase):
        regex = LanguageItem('foo_bar_regex')
        def execute(self, context, *args, **kw):
            pass

    language_getter_mock = mocker.mock()
    language_getter_mock.get(LanguageItem('foo_bar_regex'))
    mocker.result('My regex .+')
    language_getter_mock.get(ANY)
    mocker.count(min=1, max=None)
    mocker.result('^$')
    

    with mocker:
        Action, args, kwargs = ActionRegistry.suitable_for('My regex baz', 'en-us', getter=language_getter_mock)
        assert Action is MyAction

def test_action_registry_suitable_for_returns_my_action_without_language_item():
    
    mocker = Mocker()
    
    class MyActionNoLanguage(ActionBase):
        regex = r'^I do (\w+)\s(\w+) so proudly$'
        def execute(self, context, *args, **kw):
            pass

    language_getter_mock = mocker.mock()
    language_getter_mock.get(ANY)
    mocker.count(min=1, max=None)
    mocker.result('^$')
    
    with mocker:
        Action, args, kwargs = ActionRegistry.suitable_for('I do unit test so proudly', 'en-us', getter=language_getter_mock)
        assert Action is MyActionNoLanguage

def test_action_registry_can_resolve_same_name_classes():
    
    mocker = Mocker()
    
    class MyActionSameName(ActionBase):
        regex = r'I do (\w+) very well'
        def execute(self, context, *args, **kw):
            pass
    Temp1 = MyActionSameName

    class MyActionSameName(ActionBase):
        regex = r'I do (\w+) very bad'
        def execute(self, context, *args, **kw):
            pass
    Temp2 = MyActionSameName

    language_getter_mock = mocker.mock()
    language_getter_mock.get(ANY)
    mocker.count(min=1, max=None)
    mocker.result('^$')

    with mocker:
        Action1, args1, kwargs1 = ActionRegistry.suitable_for('I do test very well', 'en-us', getter=language_getter_mock)
        Action2, args2, kwargs2 = ActionRegistry.suitable_for('I do test very bad', 'en-us', getter=language_getter_mock)
        assert Action1 is not MyActionSameName
        assert Action1 is not Temp2
        assert Action1 is Temp1
        assert Action2 is Temp2
        assert Action2 is MyActionSameName

@raises(LanguageDoesNotResolveError)
def test_action_registry_suitable_for_raises_when_language_getter_can_not_resolve():
    
    mocker = Mocker()
    
    class MyActionLanguage(ActionBase):
        regex = LanguageItem('foo_bar_regex1')
        def execute(self, context, *args, **kw):
            pass

    language_getter_mock = mocker.mock()
    language_getter_mock.get(LanguageItem('foo_bar_regex1'))
    mocker.result(None)
    language_getter_mock.get(ANY)
    mocker.count(min=1, max=None)
    mocker.result('^$')
    
    with mocker:
        Action, args, kwargs = ActionRegistry.suitable_for('Something blabla', 'en-us', getter=language_getter_mock)

@raises(RuntimeError) # A action can not execute itself for infinite recursion reasons :)
def test_execute_action_will_not_execute_itself():
    
    mocker = Mocker()
    
    class DoSomethingRecursiveAction(ActionBase):
        regex = r'^(And )?I do "(?P<what>\w+)" stuff$'
        def execute(self, context, getter_mock, *args, **kwargs):
            self.execute_action('And I do "recursive" stuff', context, getter=getter_mock)

    language_getter_mock = mocker.mock()
    language_getter_mock.get(ANY)
    mocker.count(min=1, max=None)
    mocker.result('^$')

    context_mock = Object(
        settings=mocker.mock()
    )
    context_mock.settings.default_culture
    mocker.result("en-us")

    with mocker:
        dosaction = DoSomethingRecursiveAction()
        args = []
        kwargs = dict(what='nothing')
    
        dosaction.execute(context_mock, getter_mock=language_getter_mock, *args, **kwargs)

def test_action_base_can_resolve_elements_in_a_given_page():
    
    mocker = Mocker()
    
    class DoOtherThingAction(ActionBase):
        regex="^Do other thing$"
        def execute(self, context, *args, **kwargs):
            self.element = self.resolve_element_key(context, "button", "Something")

    context_mock = Object(
        current_page=mocker.mock()
        )
    context_mock.current_page.get_registered_element("Something")
    mocker.result("btnSomething")

    with mocker:
        action = DoOtherThingAction()
        action.execute(context_mock)
        assert action.element == "btnSomething"

def test_action_base_can_resolve_elements_using_browser_driver():
    
    mocker = Mocker()
    
    class DoOneMoreThingAction(ActionBase):
        regex="^Do other thing$"
        def execute(self, context, *args, **kwargs):
            self.element = self.resolve_element_key(context, "button", "Something")

    context_mock = Object(
        browser_driver=mocker.mock(),
        current_page=None
        )
    context_mock.browser_driver.resolve_element_key(context_mock, "button", "Something")
    mocker.result("btnSomething")

    with mocker:
        action = DoOneMoreThingAction()
        action.execute(context_mock)
        assert action.element == "btnSomething"

########NEW FILE########
__FILENAME__ = test_base_driver
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from re import compile as re_compile

from utils import assert_raises
from pyccuracy.common import Settings
from pyccuracy.drivers import BaseDriver

def test_base_driver_instantiate_need_a_settings():
    def do_instantiate_fail():
        BaseDriver(None)

    assert_raises(TypeError, do_instantiate_fail, exc_pattern=re_compile('BaseDriver takes a pyccuracy.common.Settings object as construction parameter. Got None.'))

def test_base_driver_has_start_attr():
    assert hasattr(BaseDriver, 'start'), 'The BaseDriver should have the "start" attr'

def test_base_driver_start_attr_is_callable():
    assert callable(BaseDriver.start), 'The BaseDriver.start should be callable'

def test_base_driver_start_does_nothing():
    settings = Settings()
    assert BaseDriver(settings).start() is None

def test_base_driver_has_stop_attr():
    assert hasattr(BaseDriver, 'stop'), 'The BaseDriver should have the "stop" attr'

def test_base_driver_stop_attr_is_callable():
    assert callable(BaseDriver.stop), 'The BaseDriver.stop should be callable'

def test_base_driver_stop_does_nothing():
    settings = Settings()
    assert BaseDriver(settings).stop() is None

########NEW FILE########
__FILENAME__ = test_common
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mocker import Mocker

from pyccuracy.common import URLChecker

def test_url_checker():
    
    mocker = Mocker()
    
    urlmock = mocker.mock()

    urlmock.urlopen("http://foo.bar.com")
    mocker.result(None)

    with mocker:
        checker = URLChecker(lib=urlmock)
        checker.set_url("http://foo.bar.com")
    
        assert checker.url == "http://foo.bar.com"
        assert checker.is_valid()
        assert checker.exists()

def test_url_checker_with_port():
    
    mocker = Mocker()
    
    urlmock = mocker.mock()

    urlmock.urlopen("http://foo.bar.com:8080")
    mocker.result(None)

    with mocker:
        checker = URLChecker(lib=urlmock)
        checker.set_url("http://foo.bar.com:8080")
    
        assert checker.url == "http://foo.bar.com:8080"
        assert checker.is_valid()
        assert checker.exists()

def test_url_checker_with_port_with_sub_folder():
    
    mocker = Mocker()
    
    urlmock = mocker.mock()

    urlmock.urlopen("http://foo.bar.com:8080/login")
    mocker.result(None)

    with mocker:
        checker = URLChecker(lib=urlmock)
        checker.set_url("http://foo.bar.com:8080/login")
    
        assert checker.url == "http://foo.bar.com:8080/login"
        assert checker.is_valid()
        assert checker.exists()

def test_url_checker_with_port_with_sub_folder_in_localhost():
    
    mocker = Mocker()
    
    urlmock = mocker.mock()

    urlmock.urlopen("http://localhost:8080/login")
    mocker.result(None)

    with mocker:
        checker = URLChecker(lib=urlmock)
        checker.set_url("http://localhost:8080/login")
    
        assert checker.url == "http://localhost:8080/login"
        assert checker.is_valid()
        assert checker.exists()

########NEW FILE########
__FILENAME__ = test_core
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from os.path import join, abspath, dirname
from mocker import Mocker, ANY, ARGS, KWARGS
from nose.tools import *

from pyccuracy.core import PyccuracyCore
from pyccuracy.common import Settings, Status
from pyccuracy.errors import TestFailedError

from utils import Object

def test_pyccuracy_core_instantiation():
    class MyParser:
        pass

    class MyRunner:
        pass

    pc = PyccuracyCore(MyParser(), MyRunner())
    assert isinstance(pc, PyccuracyCore)
    assert isinstance(pc.parser, MyParser)
    assert isinstance(pc.runner, MyRunner)

def make_context_and_fso_mocks(mocker):
    
    hooks_dir = ["/hooks/dir/"]
    pages_dir = ["/pages/dir/"]
    custom_actions_dir = ["/custom/actions/dir/"]
    
    context_mock = Object()
    context_mock.browser_driver = mocker.mock()
    context_mock.settings = mocker.mock()
    context_mock.settings.hooks_dir
    mocker.count(min=1, max=None)
    mocker.result(hooks_dir)
    context_mock.settings.pages_dir
    mocker.count(min=1, max=None)
    mocker.result(pages_dir)
    context_mock.settings.custom_actions_dir
    mocker.count(min=1, max=None)
    mocker.result(custom_actions_dir)
    context_mock.settings.base_url
    mocker.count(min=0, max=None)
    mocker.result("http://localhost")
    context_mock.settings.default_culture
    mocker.count(min=1, max=None)
    mocker.result("en-us")

    files = ["/some/weird/file.py"]
    fso_mock = mocker.mock()
    fso_mock.add_to_import(hooks_dir[0])
    fso_mock.add_to_import(pages_dir[0])
    fso_mock.add_to_import(custom_actions_dir[0])
    fso_mock.locate(hooks_dir[0], '*.py')
    mocker.result(files)
    fso_mock.locate(pages_dir[0], '*.py')
    mocker.result(files)
    fso_mock.locate(custom_actions_dir[0], '*.py')
    mocker.result(files)
    fso_mock.import_file(ANY)
    mocker.count(min=1, max=None)
    fso_mock.remove_from_import(custom_actions_dir[0])
    mocker.count(min=1, max=None)
    fso_mock.remove_from_import(pages_dir[0])
    mocker.count(min=1, max=None)
    fso_mock.remove_from_import(hooks_dir[0])
    mocker.count(min=1, max=None)

    return context_mock, fso_mock

def test_pyccuracy_core_run_tests():
    mocker = Mocker()
    context_mock, fso_mock = make_context_and_fso_mocks(mocker)
    context_mock.settings.write_report
    mocker.result(False)

    suite_mock = mocker.mock()
    suite_mock.no_story_header
    mocker.result([])
    suite_mock.stories
    mocker.result(['some story'])

    runner_mock = mocker.mock()
    parser_mock = mocker.mock()
    parser_mock.used_actions
    mocker.count(min=1, max=None)
    mocker.result([])
    
    results_mock = mocker.mock()
    results_mock.summary_for('en-us')
    mocker.result('my results')
    
    parser_mock.get_stories(ANY)
    mocker.result(suite_mock)
    runner_mock.run_stories(KWARGS)
    mocker.result(results_mock)
    
    with mocker:
        pc = PyccuracyCore(parser_mock, runner_mock)
    
        #TODO: falha
        results = pc.run_tests(should_throw=False, context=context_mock, fso=fso_mock)
        assert results == results_mock, results

def test_pyccuracy_core_run_tests_works_when_None_Result_returned_from_story_runner():
    
    mocker = Mocker()
    
    context_mock, fso_mock = make_context_and_fso_mocks(mocker)
    context_mock.settings.write_report
    mocker.result(False)
        
    suite_mock = mocker.mock()
    suite_mock.no_story_header
    mocker.result([])
    suite_mock.stories
    mocker.result(['some story'])

    runner_mock = mocker.mock()
    parser_mock = mocker.mock()
    parser_mock.used_actions
    mocker.count(min=1, max=None)
    mocker.result([])

    parser_mock.get_stories(ANY)
    mocker.result(suite_mock)
    runner_mock.run_stories(KWARGS)
    mocker.result(None)

    with mocker:
        pc = PyccuracyCore(parser_mock, runner_mock)
    
        assert pc.run_tests(should_throw=False, context=context_mock, fso=fso_mock) == None

def test_pyccuracy_core_should_raise_TestFailedError_when_should_throw_is_true():
    def do_run_tests_should_throw():
        
        mocker = Mocker()
        
        context_mock, fso_mock = make_context_and_fso_mocks(mocker)
        context_mock.settings.write_report
        mocker.result(False)

        context_mock.language = mocker.mock()
        context_mock.language.key
        mocker.result("key")

        results_mock = mocker.mock()
        results_mock.summary_for('en-us')
        mocker.result('')
        results_mock.get_status()
        mocker.result(Status.Failed)
        
        suite_mock = mocker.mock()
        suite_mock.no_story_header
        mocker.result([])
        suite_mock.stories
        mocker.result(['some story'])

        runner_mock = mocker.mock()
        parser_mock = mocker.mock()
        parser_mock.used_actions
        mocker.count(min=1, max=None)
        mocker.result([])
    
        parser_mock.get_stories(ANY)
        mocker.result(suite_mock)
        runner_mock.run_stories(KWARGS)
        mocker.result(results_mock)

        with mocker:
            pc = PyccuracyCore(parser_mock, runner_mock)
            pc.run_tests(should_throw=True, context=context_mock, fso=fso_mock)

    assert_raises(TestFailedError, do_run_tests_should_throw)


########NEW FILE########
__FILENAME__ = test_drivers_registry
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from re import compile as re_compile
from nose.tools import *

from utils import assert_raises
from pyccuracy import DriverRegistry
from pyccuracy.drivers import BaseDriver, DriverDoesNotExistError, BackendNotFoundError

def test_drivers_registry_must_raise_when_does_not_exist():
    def do_get_must_fail():
        null_driver = DriverRegistry.get('spam_eggs')

    assert_raises(DriverDoesNotExistError, do_get_must_fail, exc_pattern=re_compile(u'^Driver not found "spam_eggs". Is the driver in a known path[?]$'))
    # maybe we should rename the exception to "NeedAGpsError" ? LOL

def test_drivers_registry_exception_must_have_backend_attribute():
    def do_get_must_fail():
        null_driver = DriverRegistry.get('spam_eggs')

    try:
        do_get_must_fail()
        assert False, "If you got here, something's amiss"

    except DriverDoesNotExistError, e:
        assert hasattr(e, 'backend')
        assert e.backend == 'spam_eggs'

def test_drivers_registry_get_custom_browser():
    class MyBrowserDriver1(BaseDriver):
        backend = 'my_backend'

    Driver = DriverRegistry.get('my_backend')
    assert Driver is MyBrowserDriver1

def test_drivers_registry_should_raise_when_no_backend_specified():
    def raise_my_stuff():
        class MyBrowserDriver2(BaseDriver):
            pass

    assert_raises(BackendNotFoundError, raise_my_stuff, exc_pattern=re_compile('^Backend not found in "MyBrowserDriver2" class. Did you forget to specify "backend" attribute[?]$'))

def test_drivers_registry_should_raise_and_exception_must_have_klass_attribute():
    def raise_my_stuff():
        class MyBrowserDriver3(BaseDriver):
            pass
    try:
        raise_my_stuff()
        assert False, "If you got here, something's amiss"

    except BackendNotFoundError, e:
        assert hasattr(e, 'klass')
        assert e.klass == 'MyBrowserDriver3'

########NEW FILE########
__FILENAME__ = test_file_parser
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mocker import Mocker
from nose.tools import raises

from pyccuracy.common import Settings
from pyccuracy.parsers import FileParser
from pyccuracy.fixture import Fixture
from pyccuracy.fixture_items import Story

def assert_no_invalid_stories(fixture):
    if fixture.invalid_test_files:
        raise fixture.invalid_test_files[0][1]

def test_can_create_file_parser():
    parser = FileParser()

    assert isinstance(parser, FileParser), "The created instance should be an instance of FileParser but was %s" % parser.__class__

def test_can_create_file_parser_with_mocked_filesystem():
    
    mocker = Mocker()
    
    filemock = mocker.mock()
    parser = FileParser(file_object=filemock)

    assert parser.file_object == filemock

def test_parsing_stories_returns_list():
    
    mocker = Mocker()
    
    settings = Settings()
    filemock = mocker.mock()
    filemock.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
    mocker.result([])
    
    with mocker:
        parser = FileParser(file_object=filemock)
    
        fixture = parser.get_stories(settings=settings)
        assert isinstance(fixture, Fixture)

def test_parsing_folder_with_no_stories_returns_empty_list():
    
    mocker = Mocker()
    
    settings = Settings()
    files = []
    filemock = mocker.mock()
    filemock.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
    mocker.result(files)

    with mocker:
        parser = FileParser(file_object=filemock)
    
        fixture = parser.get_stories(settings=settings)
        assert len(fixture.stories) == 0

def test_parsing_files_with_empty_content_returns_invalid_files_list():
    
    mocker = Mocker()
    
    settings = Settings()
    files = ["some path"]

    story_text = ""

    filemock = mocker.mock()
    filemock.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
    mocker.result(files)
    filemock.read_file(files[0])
    mocker.result(story_text)

    language_mock = mocker.mock()
    language_mock.get("as_a")
    mocker.result("As a")
    language_mock.get("i_want_to")
    mocker.result("I want to")
    language_mock.get("so_that")
    mocker.result("So that")
    language_mock.get("no_header_failure")
    mocker.result("No header found")

    with mocker:
        parser = FileParser(language=language_mock, file_object=filemock)
    
        fixture = parser.get_stories(settings=settings)
        assert len(fixture.no_story_header) == 1
        file_path = fixture.no_story_header[0]
        assert file_path == "some path"

def test_parsing_files_with_invalid_as_a_returns_invalid_files_list():
    
    mocker = Mocker()
    
    settings = Settings()
    files = ["some path"]
    
    story_text = """As someone
I want to do something
So that I'm happy"""

    filemock = mocker.mock()
    filemock.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
    mocker.result(files)
    filemock.read_file(files[0])
    mocker.result(story_text)

    language_mock = mocker.mock()
    language_mock.get("as_a")
    mocker.result("As a")
    language_mock.get("i_want_to")
    mocker.result("I want to")
    language_mock.get("so_that")
    mocker.result("So that")
    language_mock.get("no_header_failure")
    mocker.result("No header found")

    with mocker:
        parser = FileParser(language=language_mock, file_object=filemock)
    
        fixture = parser.get_stories(settings=settings)
        assert len(fixture.no_story_header) == 1
        file_path = fixture.no_story_header[0]
        assert file_path == "some path"

def test_parsing_files_with_invalid_i_want_to_returns_invalid_files_list():
    
    mocker = Mocker()
    
    settings = Settings()
    files = ["some path"]
    
    story_text = """As a someone
I want something
So that I'm happy"""

    filemock = mocker.mock()
    filemock.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
    mocker.result(files)
    filemock.read_file(files[0])
    mocker.result(story_text)

    language_mock = mocker.mock()
    language_mock.get("as_a")
    mocker.result("As a")
    language_mock.get("i_want_to")
    mocker.result("I want to")
    language_mock.get("so_that")
    mocker.result("So that")
    language_mock.get("no_header_failure")
    mocker.result("No header found")

    with mocker:
        parser = FileParser(language=language_mock, file_object=filemock)
    
        fixture = parser.get_stories(settings=settings)
        assert len(fixture.no_story_header) == 1
        file_path = fixture.no_story_header[0]
        assert file_path == "some path"

def test_parsing_files_with_invalid_so_that_returns_invalid_files_list():
    
    mocker = Mocker()
    
    settings = Settings()
    files = ["some path"]
    
    story_text = """As a someone
I want to do something
So I'm happy"""

    filemock = mocker.mock()
    filemock.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
    mocker.result(files)
    filemock.read_file(files[0])
    mocker.result(story_text)

    language_mock = mocker.mock()
    language_mock.get("as_a")
    mocker.result("As a")
    language_mock.get("i_want_to")
    mocker.result("I want to")
    language_mock.get("so_that")
    mocker.result("So that")
    language_mock.get("no_header_failure")
    mocker.result("No header found")

    with mocker:
        parser = FileParser(language=language_mock, file_object=filemock)
    
        fixture = parser.get_stories(settings=settings)
        assert len(fixture.no_story_header) == 1
        file_path = fixture.no_story_header[0]
        assert file_path == "some path"

def test_parsing_files_with_proper_header_returns_parsed_scenario():
    
    mocker = Mocker()
    
    settings = Settings()
    files = ["some path"]
    
    story_text = """As a someone
I want to do something
So that I'm happy"""

    filemock = mocker.mock()
    filemock.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
    mocker.result(files)
    filemock.read_file(files[0])
    mocker.result(story_text)

    language_mock = mocker.mock()
    language_mock.get("as_a")
    mocker.result("As a")
    language_mock.get("i_want_to")
    mocker.result("I want to")
    language_mock.get("so_that")
    mocker.result("So that")

    with mocker:
        parser = FileParser(language=language_mock, file_object=filemock)
    
        fixture = parser.get_stories(settings=settings)
        assert len(fixture.stories) == 1
        assert fixture.stories[0].as_a == "someone"
        assert fixture.stories[0].i_want_to == "do something"
        assert fixture.stories[0].so_that == "I'm happy"

def test_is_scenario_starter_line():
    
    mocker = Mocker()
    
    language_mock = mocker.mock()
    language_mock.get("scenario")
    mocker.result("Scenario")

    with mocker:
        parser = FileParser(language=language_mock, file_object=None)
        is_scenario_starter_line = parser.is_scenario_starter_line("Scenario bla")
        
        assert is_scenario_starter_line

def test_is_not_scenario_starter_line():
    
    mocker = Mocker()
    
    language_mock = mocker.mock()
    language_mock.get("scenario")
    mocker.result("Scenario")

    with mocker:
        parser = FileParser(language=language_mock, file_object=None)
        is_scenario_starter_line = parser.is_scenario_starter_line("Cenario bla")
        
        assert not is_scenario_starter_line

def test_parse_scenario_line():
    
    mocker = Mocker()
    
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="some file")

    settings_mock = mocker.mock()
    settings_mock.scenarios_to_run
    mocker.result([])
    
    language_mock = mocker.mock()
    language_mock.get("scenario")
    mocker.result("Scenario")

    with mocker:
        parser = FileParser(language=language_mock, file_object=None)
        scenario = parser.parse_scenario_line(story, "Scenario 1 - Doing something", settings_mock)
    
        assert scenario is not None
        assert scenario.index == "1", "Expected 1 actual %s" % scenario.index
        assert scenario.title == "Doing something"

def test_is_keyword():
    
    mocker = Mocker()
    
    language_mock = mocker.mock()
    language_mock.get("keyword")
    mocker.result("kw")

    with mocker:
        parser = FileParser(language=language_mock, file_object=None)
        is_keyword = parser.is_keyword("kw", "keyword")
    
        assert is_keyword

def test_is_not_keyword():
    
    mocker = Mocker()
    
    language_mock = mocker.mock()
    language_mock.get("keyword")
    mocker.result("kw")

    with mocker:
        parser = FileParser(language=language_mock, file_object=None)
        is_keyword = parser.is_keyword("other", "keyword")
    
        assert not is_keyword

def test_parsing_files_with_proper_scenario_returns_parsed_scenario():
    
    mocker = Mocker()
    
    class DoSomethingAction:
        def execute(context, *args, **kwargs):
            pass

    class DoSomethingElseAction:
        def execute(context, *args, **kwargs):
            pass
    class DoYetAnotherThingAction:
        def execute(context, *args, **kwargs):
            pass

    settings = Settings()
    files = ["some path"]
    
    story_text = """As a someone
I want to do something
So that I'm happy

Scenario 1 - Test Scenario
Given
    I do something
When
    I do something else
Then
    I do yet another thing"""

    filemock = mocker.mock()
    filemock.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
    mocker.result(files)
    filemock.read_file(files[0])
    mocker.result(story_text)

    language_mock = mocker.mock()
    language_mock.get("as_a")
    mocker.result("As a")
    language_mock.get("i_want_to")
    mocker.result("I want to")
    language_mock.get("so_that")
    mocker.result("So that")
    language_mock.get("given")
    mocker.result("Given")
    mocker.count(min=1, max=None)
    language_mock.get("when")
    mocker.result("When")
    mocker.count(min=1, max=None)
    language_mock.get("then")
    mocker.result("Then")
    mocker.count(min=1, max=None)
    language_mock.get("scenario")
    mocker.result("Scenario")
    mocker.count(min=1, max=None)

    action_registry_mock = mocker.mock()
    action_registry_mock.suitable_for("I do something", 'en-us')
    mocker.result((DoSomethingAction, [], {}))
    action_registry_mock.suitable_for("I do something else", 'en-us')
    mocker.result((DoSomethingElseAction, [], {}))
    action_registry_mock.suitable_for("I do yet another thing", 'en-us')
    mocker.result((DoYetAnotherThingAction, [], {}))

    with mocker:
        parser = FileParser(language=language_mock, file_object=filemock, action_registry=action_registry_mock)
    
        fixture = parser.get_stories(settings=settings)
    
        assert_no_invalid_stories(fixture)
    
        assert len(fixture.stories) == 1, "Expected 1, Actual: %d" % len(fixture.stories)
        assert len(fixture.stories[0].scenarios) == 1
        assert len(fixture.stories[0].scenarios[0].givens) == 1
        assert len(fixture.stories[0].scenarios[0].whens) == 1
        assert len(fixture.stories[0].scenarios[0].thens) == 1
    
        assert "I do something" in fixture.stories[0].scenarios[0].givens[0].description
        assert "I do something else" in fixture.stories[0].scenarios[0].whens[0].description
        assert "I do yet another thing" in fixture.stories[0].scenarios[0].thens[0].description

def test_parsing_files_with_many_scenarios_returns_parsed_scenarios():
    
    mocker = Mocker()
    
    class DoSomethingAction:
        def execute(context, *args, **kwargs):
            pass

    class DoSomethingElseAction:
        def execute(context, *args, **kwargs):
            pass
    class DoYetAnotherThingAction:
        def execute(context, *args, **kwargs):
            pass

    settings = Settings()
    files = ["some path"]
    
    story_text = """As a someone
I want to do something
So that I'm happy

Scenario 1 - Test Scenario
Given
    I do something
When
    I do something else
Then
    I do yet another thing

Scenario 2 - Test Scenario
Given
    I do something
When
    #some custom comment
Then
    I do yet another thing"""

    filemock = mocker.mock()
    filemock.list_files(directories=settings.tests_dirs, pattern=settings.file_pattern)
    mocker.result(files)
    filemock.read_file(files[0])
    mocker.result(story_text)

    language_mock = mocker.mock()
    language_mock.get("as_a")
    mocker.result("As a")
    language_mock.get("i_want_to")
    mocker.result("I want to")
    language_mock.get("so_that")
    mocker.result("So that")
    language_mock.get("given")
    mocker.result("Given")
    mocker.count(min=1, max=None)
    language_mock.get("when")
    mocker.result("When")
    mocker.count(min=1, max=None)
    language_mock.get("then")
    mocker.result("Then")
    mocker.count(min=1, max=None)
    language_mock.get("scenario")
    mocker.result("Scenario")
    mocker.count(min=1, max=None)

    action_registry_mock = mocker.mock()
    action_registry_mock.suitable_for("I do something", 'en-us')
    mocker.result((DoSomethingAction, [], {}))
    mocker.count(min=1, max=None)
    action_registry_mock.suitable_for("I do something else", 'en-us')
    mocker.result((DoSomethingElseAction, [], {}))
    mocker.count(min=1, max=None)
    action_registry_mock.suitable_for("I do yet another thing", 'en-us')
    mocker.result((DoYetAnotherThingAction, [], {}))
    mocker.count(min=1, max=None)

    with mocker:
        parser = FileParser(language=language_mock, file_object=filemock, action_registry=action_registry_mock)
    
        fixture = parser.get_stories(settings=settings)
    
        assert_no_invalid_stories(fixture)
    
        assert len(fixture.stories) == 1, "Expected 1, Actual: %d" % len(fixture.stories)
        assert len(fixture.stories[0].scenarios) == 2
        assert "#some custom comment" in fixture.stories[0].scenarios[1].whens[0].description, "Expected \"#some custom comment\", Actual: \"%s\"" % fixture.stories[0].scenarios[1].whens[0].description

########NEW FILE########
__FILENAME__ = test_fixture
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

from pyccuracy.fixture import Fixture
from pyccuracy.common import Status
from pyccuracy.fixture_items import Story, Scenario, Action

def some_action():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    scenario = story.append_scenario("1", "Something")
    return scenario.add_given(action_description="Some Action", execute_function=lambda: None, args=["s"], kwargs={"a":"b"})

def test_create_fixture_returns_fixture():
    fixture = Fixture()
    assert isinstance(fixture, Fixture)

def test_fixture_starts_with_empty_lists():
    fixture = Fixture()
    assert len(fixture.invalid_test_files) == 0
    assert len(fixture.no_story_header) == 0
    assert len(fixture.stories) == 0

def test_reset_clears_lists():
    fixture = Fixture()
    fixture.invalid_test_files.append("some")
    fixture.no_story_header.append("some")
    fixture.stories.append("some")

    fixture.clear()

    assert len(fixture.invalid_test_files) == 0
    assert len(fixture.no_story_header) == 0
    assert len(fixture.stories) == 0

def test_append_invalid_test_file():
    fixture = Fixture()
    fixture.append_invalid_test_file("some", "error")
    assert len(fixture.invalid_test_files) == 1

def test_append_invalid_test_file_keeps_file():
    fixture = Fixture()
    fixture.append_invalid_test_file("some", "error")
    assert fixture.invalid_test_files[0][0] == "some"
    assert fixture.invalid_test_files[0][1] == "error"

def test_append_no_story_header():
    fixture = Fixture()
    fixture.append_no_story_header("some")
    assert len(fixture.no_story_header) == 1

def test_append_no_story_header_keeps_file():
    fixture = Fixture()
    fixture.append_no_story_header("some")
    assert fixture.no_story_header[0] == "some"

def test_append_story():
    fixture = Fixture()
    story = Story("some","other","data", identity="Some File")
    fixture.append_story(story)
    assert len(fixture.stories) == 1

def test_append_story_keeps_data():
    fixture = Fixture()
    story = Story("some","other","data", identity="Some File")
    fixture.append_story(story)
    assert fixture.stories[0].as_a == "some"
    assert fixture.stories[0].i_want_to == "other"
    assert fixture.stories[0].so_that == "data"

def test_fixture_returns_unknown_status_if_no_stories():
    fixture = Fixture()
    assert fixture.get_status() == Status.Unknown

def test_fixture_returns_proper_status_if_action_failed():
    fixture = Fixture()
    action = some_action()
    fixture.append_story(action.scenario.story)
    action.mark_as_failed()

    assert fixture.get_status() == Status.Failed

def test_fixture_returns_proper_status_if_action_succeeded():
    fixture = Fixture()
    action = some_action()
    fixture.append_story(action.scenario.story)
    action.mark_as_successful()

    assert fixture.get_status() == Status.Successful

def test_fixture_returns_proper_status_with_two_scenarios():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_successful()
    other_action.mark_as_failed()

    assert fixture.get_status() == Status.Failed

def test_fixture_returns_proper_status_with_two_scenarios_with_failed_first():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_failed()
    other_action.mark_as_successful()

    assert fixture.get_status() == Status.Failed

def test_fixture_returns_proper_status_with_two_scenarios_with_both_successful():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_successful()
    other_action.mark_as_successful()

    assert fixture.get_status() == Status.Successful

def test_fixture_returns_total_number_of_stories():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_successful()
    other_action.mark_as_successful()

    assert fixture.count_total_stories() == 3

def test_fixture_returns_total_number_of_scenarios():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_successful()
    other_action.mark_as_successful()

    assert fixture.count_total_scenarios() == 3

def test_fixture_returns_total_successful_stories():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_successful()
    other_action.mark_as_failed()

    assert fixture.count_successful_stories() == 1

def test_fixture_returns_total_failed_stories():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_successful()
    other_action.mark_as_failed()

    assert fixture.count_failed_stories() == 1

def test_fixture_returns_total_successful_scenarios():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_successful()
    other_action.mark_as_successful()

    assert fixture.count_successful_scenarios() == 2

def test_fixture_returns_total_failed_scenarios():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_failed()
    other_action.mark_as_failed()

    assert fixture.count_failed_scenarios() == 2

def test_fixture_returns_successful_scenarios():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_successful()
    other_action.mark_as_successful()

    assert len(fixture.get_successful_scenarios()) == 2

def test_fixture_returns_failed_scenarios():
    fixture = Fixture()
    action = some_action()
    other_action = some_action()
    fixture.append_story(action.scenario.story)
    fixture.append_story(other_action.scenario.story)
    action.mark_as_failed()
    other_action.mark_as_failed()

    assert len(fixture.get_failed_scenarios()) == 2


########NEW FILE########
__FILENAME__ = test_fixture_items_action
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

from pyccuracy.fixture_items import Status, Story, Scenario, Action

def some_action():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    scenario = Scenario(index="1", title="Something", story=story)
    return Action(scenario=scenario, description="Some Action", execute_function=lambda: None, args=["s"], kwargs={"a":"b"})

def test_creating_an_action_returns_an_action():
    action = Action(scenario=None, description="bla", execute_function=None, args=None, kwargs=None)
    assert isinstance(action, Action)

def test_creating_an_action_keeps_description():
    expected = "1"
    action = Action(scenario=None, description=expected, execute_function=None, args=None, kwargs=None)
    assert action.description == expected, "Description should be %s but was %s" % (expected, action.description)

def test_creating_an_action_keeps_execute_function():
    func = lambda: None
    action = Action(scenario=None, description="bla", execute_function=func, args=None, kwargs=None)
    assert action.execute_function == func, "Execute function should be %s but was %s" % (func, action.execute_function)

def test_creating_an_action_keeps_args_and_kwargs():
    expected = ["a","b"]
    kwargs = {"a":"b"}
    action = Action(scenario=None, description="bla", execute_function=None, args=expected, kwargs=kwargs)
    assert action.args == expected, "Args should be %s but was %s" % (expected, action.args)
    assert action.kwargs == kwargs, "KWArgs should be %s but was %s" % (kwargs, action.kwargs)

def test_creating_an_action_starts_with_empty_times():
    action = some_action()
    assert action.start_time == None, "Action should start with no start time but was %s" % action.start_time
    assert action.end_time == None, "Action should start with no end time but was %s" % action.end_time

def test_creating_an_action_starts_with_unknown_status():
    action = some_action()
    assert action.status == Status.Unknown, "Action should start with Unknown status but was %s" % action.status

def test_story_returns_right_repr():
    action = some_action()
    expected = u"Action Some Action - UNKNOWN"
    assert unicode(action) == expected, "Unicode Expected: %s Actual: %s" % (expected, unicode(action))
    assert str(action) == expected, "Str Expected: %s Actual: %s" % (expected, str(action))

def test_mark_action_as_failed():
    action = some_action()
    action.mark_as_failed()
    assert action.status == Status.Failed, "The status should be %s but was %s" % (Status.Failed, action.status)

def test_mark_action_as_successful():
    action = some_action()
    action.mark_as_successful()
    assert action.status == Status.Successful, "The status should be %s but was %s" % (Status.Successful, action.status)

def test_mark_action_as_successful_after_failed_has_no_effect():
    action = some_action()
    action.mark_as_failed()
    action.mark_as_successful()
    assert action.status == Status.Failed, "The status should be %s but was %s" % (Status.Failed, action.status)

def test_marking_action_as_failed_also_marks_scenario_as_failed_if_scenario_exists():
    action = some_action()
    action.mark_as_failed()
    assert action.scenario.status == Status.Failed, "The status should be %s but was %s" % (Status.Failed, action.scenario.status)

def test_marking_action_as_successful_also_marks_scenario_as_successful_if_scenario_exists():
    action = some_action()
    action.mark_as_successful()
    assert action.scenario.status == Status.Successful, "The status should be %s but was %s" % (Status.Successful, action.scenario.status)

def test_action_start_run_marks_time():
    action = some_action()
    action.start_run()
    assert action.start_time is not None, "There should be some start time after start_run"

def test_action_end_run_marks_time():
    action = some_action()
    action.end_run()
    assert action.end_time is not None, "There should be some end time after end_run"

def test_action_ellapsed_returns_zero_for_non_started_actions():
    action = some_action()

    expected = 0
    ellapsed = int(action.ellapsed())
    assert ellapsed == expected, "The ellapsed time should be %d but was %d" % (expected, ellapsed)

def test_story_ellapsed_returns_zero_for_non_finished_stories():
    action = some_action()
    action.start_run()
    expected = 0
    ellapsed = int(action.ellapsed())
    assert ellapsed == expected, "The ellapsed time should be %d but was %d" % (expected, ellapsed)

def test_action_ellapsed_returns_seconds():
    action = some_action()
    action.start_run()
    time.sleep(0.1)
    action.end_run()

    expected = "0.1"
    ellapsed = "%.1f" % action.ellapsed()
    assert ellapsed == expected, "The ellapsed time should be %s but was %s" % (expected, ellapsed)
    

########NEW FILE########
__FILENAME__ = test_fixture_items_scenario
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

from pyccuracy.fixture_items import Status, Story, Scenario, Action

def test_creating_a_scenario_returns_a_scenario():
    scenario = Scenario(index=None, title=None, story=None)
    assert isinstance(scenario, Scenario)

def test_creating_a_scenario_keeps_index():
    expected = "1"
    scenario = Scenario(index=expected, title=None, story=None)
    assert scenario.index == expected, "Index should be %s but was %s" % (expected, scenario.index)

def test_creating_a_scenario_keeps_title():
    expected = "some title"
    scenario = Scenario(index=None, title=expected, story=None)
    assert scenario.title == expected, "title should be %s but was %s" % (expected, scenario.title)

def test_creating_a_scenario_keeps_the_story():
    story = Story(as_a="Someone", i_want_to="do something", so_that="something", identity="Some File")
    scenario = Scenario(index=None, title=None, story=story)
    assert str(story) == str(scenario.story), "story should be %s but was %s" % (str(story), str(scenario.story))

def test_creating_a_scenario_starts_with_empty_times():
    scenario = Scenario(index="1", title="Something", story=None)
    assert scenario.start_time == None, "Scenario should start with no start time but was %s" % scenario.start_time
    assert scenario.end_time == None, "Scenario should start with no end time but was %s" % scenario.end_time

def test_creating_a_scenario_starts_with_empty_givens():
    scenario = Scenario(index="1", title="Something", story=None)
    assert scenario.givens == [], "Scenario should start with no givens but was %s" % scenario.givens

def test_creating_a_scenario_starts_with_empty_whens():
    scenario = Scenario(index="1", title="Something", story=None)
    assert scenario.whens == [], "Scenario should start with no whens but was %s" % scenario.whens

def test_creating_a_scenario_starts_with_empty_thens():
    scenario = Scenario(index="1", title="Something", story=None)
    assert scenario.thens == [], "Scenario should start with no thens but was %s" % scenario.thens
    
def test_creating_a_scenario_starts_with_unknown_status():
    scenario = Scenario(index="1", title="Something", story=None)
    assert scenario.status == Status.Unknown, "Scenario should start with Unknown status but was %s" % scenario.status

def test_story_returns_right_repr():
    scenario = Scenario(index="1", title="Do Something", story=None)
    expected = u"Scenario 1 - Do Something (0 givens, 0 whens, 0 thens) - UNKNOWN"
    assert unicode(scenario) == expected, "Unicode Expected: %s Actual: %s" % (expected, unicode(scenario))
    assert str(scenario) == expected, "Str Expected: %s Actual: %s" % (expected, str(scenario))

def test_mark_scenario_as_failed():
    scenario = Scenario(index="1", title="Something", story=None)
    scenario.mark_as_failed()
    assert scenario.status == Status.Failed, "The status should be %s but was %s" % (Status.Failed, scenario.status)

def test_mark_scenario_as_successful():
    scenario = Scenario(index="1", title="Something", story=None)
    scenario.mark_as_successful()
    assert scenario.status == Status.Successful, "The status should be %s but was %s" % (Status.Successful, scenario.status)

def test_mark_scenario_as_successful_after_failed_has_no_effect():
    scenario = Scenario(index="1", title="Something", story=None)
    scenario.mark_as_failed()
    scenario.mark_as_successful()
    assert scenario.status == Status.Failed, "The status should be %s but was %s" % (Status.Failed, scenario.status)

def test_marking_scenario_as_failed_also_marks_story_as_failed_if_story_exists():
    story = Story(as_a="Someone", i_want_to="do something", so_that="something", identity="Some File")
    scenario = Scenario(index="1", title="Something", story=story)
    scenario.mark_as_failed()
    assert story.status == Status.Failed, "The status should be %s but was %s" % (Status.Failed, story.status)

def test_marking_scenario_as_successful_also_marks_story_as_failed_if_story_exists():
    story = Story(as_a="Someone", i_want_to="do something", so_that="something", identity="Some File")
    scenario = Scenario(index="1", title="Something", story=story)
    scenario.mark_as_successful()
    assert story.status == Status.Successful, "The status should be %s but was %s" % (Status.Successful, story.status)

def test_scenario_start_run_marks_time():
    scenario = Scenario(index="1", title="Something", story=None)
    scenario.start_run()
    assert scenario.start_time is not None, "There should be some start time after start_run"

def test_scenario_end_run_marks_time():
    scenario = Scenario(index="1", title="Something", story=None)
    scenario.end_run()
    assert scenario.end_time is not None, "There should be some end time after end_run"

def test_scenario_ellapsed_returns_zero_for_non_started_scenarios():
    scenario = Scenario(index="1", title="Something", story=None)

    expected = 0
    ellapsed = int(scenario.ellapsed())
    assert ellapsed == expected, "The ellapsed time should be %d but was %d" % (expected, ellapsed)

def test_story_ellapsed_returns_zero_for_non_finished_stories():
    scenario = Scenario(index="1", title="Something", story=None)
    scenario.start_run()
    expected = 0
    ellapsed = int(scenario.ellapsed())
    assert ellapsed == expected, "The ellapsed time should be %d but was %d" % (expected, ellapsed)

def test_scenario_ellapsed_returns_seconds():
    scenario = Scenario(index="1", title="Something", story=None)
    scenario.start_run()
    time.sleep(0.1)
    scenario.end_run()

    expected = "0.1"
    ellapsed = "%.1f" % scenario.ellapsed()
    assert ellapsed == expected, "The ellapsed time should be %s but was %s" % (expected, ellapsed)

def test_append_given_adds_to_givens_in_scenario():
    story = Story(as_a="Someone", i_want_to="do something", so_that="something", identity="Some File")
    scenario = Scenario(index="1", title="Something", story=story)
    args = ["a"]
    kwargs = {"extra_args":"something"}
    scenario.add_given("some action", lambda: None, args, kwargs)
    assert len(scenario.givens) == 1, "There should be one given in the scenario but there was %d" % len(scenario.givens)

def test_append_given_adds_right_class_to_givens_in_scenario():
    story = Story(as_a="Someone", i_want_to="do something", so_that="something", identity="Some File")
    scenario = Scenario(index="1", title="Something", story=story)
    args = ["a"]
    kwargs = {"extra_args":"something"}
    scenario.add_given("some action", lambda: None, args, kwargs)
    assert isinstance(scenario.givens[0], Action), "There should be one given of type Action in the scenario but there was %s" % scenario.givens[0].__class__

def test_append_when_adds_to_whens_in_scenario():
    story = Story(as_a="Someone", i_want_to="do something", so_that="something", identity="Some File")
    scenario = Scenario(index="1", title="Something", story=story)
    args = ["a"]
    kwargs = {"extra_args":"something"}
    scenario.add_when("some action", lambda: None, args, kwargs)
    assert len(scenario.whens) == 1, "There should be one when in the scenario but there was %d" % len(scenario.whens)

def test_append_when_adds_right_class_to_whens_in_scenario():
    story = Story(as_a="Someone", i_want_to="do something", so_that="something", identity="Some File")
    scenario = Scenario(index="1", title="Something", story=story)
    args = ["a"]
    kwargs = {"extra_args":"something"}
    scenario.add_when("some action", lambda: None, args, kwargs)
    assert isinstance(scenario.whens[0], Action), "There should be one when of type Action in the scenario but there was %s" % scenario.whens[0].__class__

def test_append_then_adds_to_thens_in_scenario():
    story = Story(as_a="Someone", i_want_to="do something", so_that="something", identity="Some File")
    scenario = Scenario(index="1", title="Something", story=story)
    args = ["a"]
    kwargs = {"extra_args":"something"}
    scenario.add_then("some action", lambda: None, args, kwargs)
    assert len(scenario.thens) == 1, "There should be one then in the scenario but there was %d" % len(scenario.thens)

def test_append_then_adds_right_class_to_thens_in_scenario():
    story = Story(as_a="Someone", i_want_to="do something", so_that="something", identity="Some File")
    scenario = Scenario(index="1", title="Something", story=story)
    args = ["a"]
    kwargs = {"extra_args":"something"}
    scenario.add_then("some action", lambda: None, args, kwargs)
    assert isinstance(scenario.thens[0], Action), "There should be one then of type Action in the scenario but there was %s" % scenario.thens[0].__class__


########NEW FILE########
__FILENAME__ = test_fixture_items_story
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

from pyccuracy.fixture_items import Status, Story, Scenario, TimedItem, StatusItem

def test_creating_a_story_returns_a_story():
    story = Story(as_a=None, i_want_to=None, so_that=None, identity="Some File")
    assert isinstance(story, Story)

def test_story_is_a_timed_item():
    story = Story(as_a=None, i_want_to=None, so_that=None, identity="Some File")
    assert isinstance(story, TimedItem)

def test_story_is_a_status_item():
    story = Story(as_a=None, i_want_to=None, so_that=None, identity="Some File")
    assert isinstance(story, StatusItem)

def test_creating_a_story_keeps_as_a():
    expected = "someone"
    story = Story(as_a=expected, i_want_to=None, so_that=None, identity="Some File")
    assert story.as_a == expected, "As_a should be %s but was %s" % (expected, story.as_a)

def test_creating_a_story_keeps_i_want_to():
    expected = "do"
    story = Story(as_a=None, i_want_to=expected, so_that=None, identity="Some File")
    assert story.i_want_to == expected, "i_want_to should be %s but was %s" % (expected, story.i_want_to)

def test_creating_a_story_keeps_so_that():
    expected = "so that"
    story = Story(as_a=None, i_want_to=None, so_that=expected, identity="Some File")
    assert story.so_that == expected, "so_that should be %s but was %s" % (expected, story.so_that)

def test_creating_a_story_keeps_an_identity():
    expected = "identity"
    story = Story(as_a=None, i_want_to=None, so_that=None, identity=expected)
    assert story.identity == expected, "identity should be %s but was %s" % (expected, story.identity)

def test_creating_a_story_starts_with_empty_times():
    story = Story(as_a=None, i_want_to=None, so_that=None, identity="Some File")
    assert story.start_time == None, "Story should start with no start time but was %s" % story.start_time
    assert story.end_time == None, "Story should start with no end time but was %s" % story.end_time

def test_creating_a_story_starts_with_empty_scenarios():
    story = Story(as_a=None, i_want_to=None, so_that=None, identity="Some File")
    assert story.scenarios == [], "Story should start with no scenarios but was %s" % story.scenarios

def test_creating_a_story_starts_with_unknown_status():
    story = Story(as_a=None, i_want_to=None, so_that=None, identity="Some File")
    assert story.status == Status.Unknown, "Story should start with Unknown status but was %s" % story.status

def test_story_returns_right_repr():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    expected = u"Story - As a Someone I want to Do Something So that I'm Happy (0 scenarios) - UNKNOWN"
    assert unicode(story) == expected, "Unicode Expected: %s Actual: %s" % (expected, unicode(story))
    assert str(story) == expected, "Str Expected: %s Actual: %s" % (expected, str(story))

def test_mark_story_as_failed():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.mark_as_failed()
    assert story.status == Status.Failed, "The status should be %s but was %s" % (Status.Failed, story.status)

def test_mark_story_as_successful():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.mark_as_successful()
    assert story.status == Status.Successful, "The status should be %s but was %s" % (Status.Successful, story.status)

def test_mark_story_as_successful_after_failed_has_no_effect():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.mark_as_failed()
    story.mark_as_successful()
    assert story.status == Status.Failed, "The status should be %s but was %s" % (Status.Failed, story.status)

def test_story_start_run_marks_time():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.start_run()
    assert story.start_time is not None, "There should be some start time after start_run"

def test_story_end_run_marks_time():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.end_run()
    assert story.end_time is not None, "There should be some end time after end_run"

def test_story_ellapsed_returns_zero_for_non_started_stories():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")

    expected = 0
    ellapsed = int(story.ellapsed())
    assert ellapsed == expected, "The ellapsed time should be %d but was %d" % (expected, ellapsed)

def test_story_ellapsed_returns_zero_for_non_finished_stories():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.start_run()
    expected = 0
    ellapsed = int(story.ellapsed())
    assert ellapsed == expected, "The ellapsed time should be %d but was %d" % (expected, ellapsed)

def test_story_ellapsed_returns_seconds():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.start_run()
    time.sleep(0.1)
    story.end_run()

    expected = "0.1"
    ellapsed = "%.1f" % story.ellapsed()
    assert ellapsed == expected, "The ellapsed time should be %s but was %s" % (expected, ellapsed)

def test_append_scenario_adds_to_scenarios_in_story():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.append_scenario(index="1", title="Test")
    assert len(story.scenarios) == 1, "There should be one scenario in the story but there was %d" % len(story.scenarios)

def test_append_scenario_adds_right_class_to_scenarios_in_story():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.append_scenario(index="1", title="Test")
    assert isinstance(story.scenarios[0], Scenario), "There should be an item of class Scenario in the story but there was %s" % story.scenarios[0].__class__

def test_append_scenario_adds_right_index_to_scenarios_in_story():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some File")
    story.append_scenario(index="1", title="Test")
    assert story.scenarios[0].index == "1", "There should be a scenario in the story with index 1 but there was %s" % story.scenarios[0].index


########NEW FILE########
__FILENAME__ = test_help
#-*- coding:utf-8 -*-
from pyccuracy.help import LanguageViewer

url_regex = r"(?P<url>[\"](([\w:/._-]|\=|\?|\&|\"|\;|\%)+)[\"]|([\w\s_.-]+))$"

def test_get_action():
    viewer = LanguageViewer(language='en-us')
    action = viewer.get_actions('select_does_not_have_selected_value')
    assert 'select_does_not_have_selected_value' in action
    assert action.get('select_does_not_have_selected_value') == '(And )I see "select_name" select does not have selected value of "value"'
    
    viewer = LanguageViewer(language='pt-br')
    action = viewer.get_actions('select_does_not_have_selected_value')
    assert 'select_does_not_have_selected_value' in action
    assert action.get('select_does_not_have_selected_value') == '(E )[eE]u vejo que o valor selecionado da select "select_name" não é "value"'

def test_make_regex_readable_for_pt_br():
    viewer = LanguageViewer()
    
    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a imagem [\"](?P<image_name>.+)[\"] tem src de [\"](?P<src>.+)[\"]$')\
            == '(E )[eE]u vejo que a imagem "image_name" tem src de "src"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a radio [\"](?P<radio_key>.+)[\"] está desmarcada$')\
            == '(E )[eE]u vejo que a radio "radio_key" está desmarcada'

    assert viewer.make_it_readable(r'^(E )?[eE]u preencho a caixa de texto [\"](?P<textbox_name>.+)[\"] com [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u preencho a caixa de texto "textbox_name" com "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u espero por (?P<timeout>\d+([.]\d+)?) segundo[s]?$')\
            == '(E )[eE]u espero por [X|X.X] segundo[s]'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que o link [\"](?P<link_name>.+)[\"] tem href [\"](?P<href>.+)[\"]$')\
            == '(E )[eE]u vejo que o link "link_name" tem href "href"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que o índice selecionado da select [\"](?P<select_name>.+)[\"] é (?P<index>\d+)$')\
            == '(E )[eE]u vejo que o índice selecionado da select "select_name" é X'

    assert viewer.make_it_readable(r'^(E )?[eE]u retiro o mouse d[oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"]$')\
            == '(E )[eE]u retiro o mouse d[oa] [element_type|element selector] "element_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a página atual contém [\"\'](?P<expected_markup>.+)[\'\"]$')\
            == '(E )[eE]u vejo que a página atual contém "expected_markup"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a checkbox [\"](?P<checkbox_key>.+)[\"] está marcada$')\
            == '(E )[eE]u vejo que a checkbox "checkbox_key" está marcada'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a página atual não contém [\"\'](?P<expected_markup>.+)[\'\"]$')\
            == '(E )[eE]u vejo que a página atual não contém "expected_markup"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a caixa de texto [\"](.+)[\"] não contém [\"](.+)[\"]$')\
            == '(E )[eE]u vejo que a caixa de texto "blah" não contém "blah"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a select [\"](?P<select_name>.+)[\"] contém uma opção com texto [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u vejo que a select "select_name" contém uma opção com texto "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u passo o mouse n[oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"]$')\
            == '(E )[eE]u passo o mouse n[oa] [element_type|element selector] "element_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [ao] (?P<element_type><element selector>) [\"](?P<element_name>.+)[\"] contém o estilo [\"](?P<style_name>.+)[\"]$')\
            == '(E )[eE]u vejo que [ao] [element_type|element selector] "element_name" contém o estilo "style_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que o valor selecionado da select [\"](?P<select_name>.+)[\"] é [\"](?P<option_value>.+)[\"]$')\
            == '(E )[eE]u vejo que o valor selecionado da select "select_name" é "option_value"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] está habilitad[oa]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" está habilitad[oa]'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] contém exatamente o markup [\"](?P<markup>.+)[\"]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" contém exatamente o markup "markup"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"]$')\
            == '(E )[eE]u vejo [oa] [element_type|element selector] "element_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] não contém o markup [\"](?P<markup>.+)[\"]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" não contém o markup "markup"'

    assert viewer.make_it_readable(r'^(E )?[eE]u seleciono o item com índice (?P<index>\d+) na select [\"](?P<select_name>.+)[\"]$')\
            == '(E )[eE]u seleciono o item com índice X na select "select_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u estou n[oa] %s' % url_regex)\
            == '(E )[eE]u estou n[oa] [page|"url"]', "result was: %s" % viewer.make_it_readable(r'^(E )?[eE]u estou n[oa] %s' % url_regex)

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a radio [\"](?P<radio_key>.+)[\"] está marcada$')\
            == '(E )[eE]u vejo que a radio "radio_key" está marcada'

    assert viewer.make_it_readable(r'^(E )?[eE]u marco a checkbox [\"](?P<checkbox_key>.+)[\"]$')\
            == '(E )[eE]u marco a checkbox "checkbox_key"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a caixa de texto [\"](?P<textbox_name>.+)[\"] está vazia$')\
            == '(E )[eE]u vejo que a caixa de texto "textbox_name" está vazia'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a caixa de texto [\"](.+)[\"] não contém exatamente [\"](.+)[\"]$')\
            == '(E )[eE]u vejo que a caixa de texto "blah" não contém exatamente "blah"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] não contém exatamente [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" não contém exatamente "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a imagem [\"](?P<image_name>.+)[\"] não tem src de [\"](?P<src>.+)[\"]$')\
            == '(E )[eE]u vejo que a imagem "image_name" não tem src de "src"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] não contém [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" não contém "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u marco a radio [\"](?P<radio_key>.+)[\"]$')\
            == '(E )[eE]u marco a radio "radio_key"'

    assert viewer.make_it_readable(r'^(E )?[eE]u seleciono o item com valor [\"](?P<option_value>.+)[\"] na select [\"](?P<select_name>.+)[\"]$')\
            == '(E )[eE]u seleciono o item com valor "option_value" na select "select_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] contém o markup [\"](?P<markup>.+)[\"]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" contém o markup "markup"'

    assert viewer.make_it_readable(r'^(E )?[eE]u seleciono o item com texto [\"](?P<text>.+)[\"] na select [\"](?P<select_name>.+)[\"]$')\
            == '(E )[eE]u seleciono o item com texto "text" na select "select_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo o título [\"](?P<title>.+)[\"]$')\
            == '(E )[eE]u vejo o título "title"'

    assert viewer.make_it_readable(r'^(E )?[eE]u não vejo [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"]$')\
            == '(E )[eE]u não vejo [oa] [element_type|element selector] "element_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a select [\"](?P<select_name>.+)[\"] não contém uma opção com texto [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u vejo que a select "select_name" não contém uma opção com texto "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que o índice selecionado da select [\"](?P<select_name>.+)[\"] não é (?P<index>\d+)$')\
            == '(E )[eE]u vejo que o índice selecionado da select "select_name" não é X'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a checkbox [\"](?P<checkbox_key>.+)[\"] está desmarcada$')\
            == '(E )[eE]u vejo que a checkbox "checkbox_key" está desmarcada'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [ao] (?P<element_type><element selector>) [\"](?P<element_name>.+)[\"] não contém o estilo [\"](?P<style_name>.+)[\"]$')\
            == '(E )[eE]u vejo que [ao] [element_type|element selector] "element_name" não contém o estilo "style_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que o link [\"](?P<link_name>.+)[\"] tem texto [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u vejo que o link "link_name" tem texto "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u desmarco a checkbox [\"](?P<checkbox_key>.+)[\"]$')\
            == '(E )[eE]u desmarco a checkbox "checkbox_key"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] contém exatamente [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" contém exatamente "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] não contém exatamente o markup [\"](?P<markup>.+)[\"]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" não contém exatamente o markup "markup"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a caixa de texto [\"](?P<textbox_name>.+)[\"] não está vazia$')\
            == '(E )[eE]u vejo que a caixa de texto "textbox_name" não está vazia'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] está desabilitad[oa]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" está desabilitad[oa]'

    assert viewer.make_it_readable(r'^(E )?[eE]u espero [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] desaparecer( por (?P<timeout>\d+) segundos)?$')\
            == '(E )[eE]u espero [oa] [element_type|element selector] "element_name" desaparecer( por X segundos)'

    assert viewer.make_it_readable(r'^(E )?[eE]u espero [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] aparecer( por (?P<timeout>\d+) segundos)?$')\
            == '(E )[eE]u espero [oa] [element_type|element selector] "element_name" aparecer( por X segundos)'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a caixa de texto [\"](.+)[\"] contém exatamente [\"](.+)[\"]$')\
            == '(E )[eE]u vejo que a caixa de texto "blah" contém exatamente "blah"'

    assert viewer.make_it_readable(r'^(E )?[eE]u espero a página ser carregada(?P<timeout> por (\d+) segundos)?$')\
            == '(E )[eE]u espero a página ser carregada( por X segundos)', "result was: %s" % viewer.make_it_readable(r'^(E )?[eE]u espero a página ser carregada(?P<timeout> por (\d+) segundos)?$')

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que o texto selecionado da select [\"](?P<select_name>.+)[\"] não é [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u vejo que o texto selecionado da select "select_name" não é "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que a caixa de texto [\"](.+)[\"] contém [\"](.+)[\"]$')\
            == '(E )[eE]u vejo que a caixa de texto "blah" contém "blah"'

    assert viewer.make_it_readable(r'^(E )?[eE]u preencho lentamente a caixa de texto [\"](?P<textbox_name>.+)[\"] com [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u preencho lentamente a caixa de texto "textbox_name" com "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que o texto selecionado da select [\"](?P<select_name>.+)[\"] é [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u vejo que o texto selecionado da select "select_name" é "text"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que o valor selecionado da select [\"](?P<select_name>.+)[\"] não é [\"](?P<value>.+)[\"]$')\
            == '(E )[eE]u vejo que o valor selecionado da select "select_name" não é "value"'

    assert viewer.make_it_readable(r'^(E )?[eE]u limpo a caixa de texto [\"](?P<textbox_name>.+)[\"]$')\
            == '(E )[eE]u limpo a caixa de texto "textbox_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u clico n[oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"](?P<should_wait> e espero)?$')\
            == '(E )[eE]u clico n[oa] [element_type|element selector] "element_name"( e espero)'

    assert viewer.make_it_readable(r'^(E )?[eE]u navego para %s' % url_regex)\
            == '(E )[eE]u navego para [page|"url"]'

    assert viewer.make_it_readable(r'^(E )?[eE]u arrasto [oa] (?P<from_element_type><element selector>) [\"](?P<from_element_name>.+)[\"] para [oa] (?P<to_element_type><element selector>) [\"](?P<to_element_name>[^"]+)[\"]?$')\
            == '(E )[eE]u arrasto [oa] [from_element_type|element selector] "from_element_name" para [oa] [to_element_type|element selector] "to_element_name"'

    assert viewer.make_it_readable(r'^(E )?[eE]u vejo que [oa] (?P<element_type><element selector>) [\"](?P<element_name>[^"]+)[\"] contém [\"](?P<text>.+)[\"]$')\
            == '(E )[eE]u vejo que [oa] [element_type|element selector] "element_name" contém "text"'

def test_make_regex_readable_for_en_us():
    viewer = LanguageViewer()

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<image_name>.+)[\"] image has src of [\"](?P<src>.+)[\"]$')\
            == '(And )I see "image_name" image has src of "src"'

    assert viewer.make_it_readable(r'^(And )?I see the [\"](?P<radio_key>.+)[\"] radio is not checked$')\
            == '(And )I see the "radio_key" radio is not checked'

    assert viewer.make_it_readable(r'^(And )?I fill [\"](?P<textbox_name>.+)[\"] textbox with [\"](?P<text>.+)[\"]$')\
            == '(And )I fill "textbox_name" textbox with "text"'

    assert viewer.make_it_readable(r'^(And )?I wait for (?P<timeout>\d+([.]\d+)?) second[s]?$')\
            == '(And )I wait for [X|X.X] second[s]', "result was: %s" % viewer.make_it_readable(r'^(And )?I wait for (?P<timeout>\d+([.]d+)?) second[s]?$')

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<link_name>.+)[\"] link has [\"](?P<href>.+)[\"] href$')\
            == '(And )I see "link_name" link has "href" href'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<select_name>.+)[\"] select has selected index of (?P<index>\d+)$')\
            == '(And )I see "select_name" select has selected index of X'

    assert viewer.make_it_readable(r'^(And )?I mouseout [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>)$')\
            == '(And )I mouseout "element_name" [element_type|element selector]'

    assert viewer.make_it_readable(r'^(And )?I see that current page contains [\"\'](?P<expected_markup>.+)[\'\"]$')\
            == '(And )I see that current page contains "expected_markup"'

    assert viewer.make_it_readable(r'^(And )?I see the [\"](?P<checkbox_key>.+)[\"] checkbox is checked$')\
            == '(And )I see the "checkbox_key" checkbox is checked'

    assert viewer.make_it_readable(r'^(And )?I see that current page does not contain [\"\'](?P<expected_markup>.+)[\'\"]$')\
            == '(And )I see that current page does not contain "expected_markup"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](.+)[\"] textbox does not contain [\"](.+)[\"]$')\
            == '(And )I see "blah" textbox does not contain "blah"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<select_name>.+)[\"] select contains an option with text [\"](?P<text>.+)[\"]$')\
            == '(And )I see "select_name" select contains an option with text "text"'

    assert viewer.make_it_readable(r'^(And )?I mouseover [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>)$')\
            == '(And )I mouseover "element_name" [element_type|element selector]'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>.+)[\"] (?P<element_type><element selector>) has [\"](?P<style_name>.+)[\"] style$')\
            == '(And )I see "element_name" [element_type|element selector] has "style_name" style'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<select_name>.+)[\"] select has selected value of [\"](?P<option_value>.+)[\"]$')\
            == '(And )I see "select_name" select has selected value of "option_value"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) is enabled$')\
            == '(And )I see "element_name" [element_type|element selector] is enabled'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) matches [\"](?P<markup>.+)[\"] markup$')\
            == '(And )I see "element_name" [element_type|element selector] matches "markup" markup'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>.+)[\"] (?P<element_type><element selector>)$')\
            == '(And )I see "element_name" [element_type|element selector]'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) does not contain [\"](?P<markup>.+)[\"] markup$')\
            == '(And )I see "element_name" [element_type|element selector] does not contain "markup" markup'

    assert viewer.make_it_readable(r'^(And )?I select the option with index of (?P<index>\d+) in [\"](?P<select_name>.+)[\"] select$')\
            == '(And )I select the option with index of X in "select_name" select'

    assert viewer.make_it_readable(r'^(And )?I am in the %s' % url_regex)\
            == '(And )I am in the [page|"url"]'

    assert viewer.make_it_readable(r'^(And )?I see the [\"](?P<radio_key>.+)[\"] radio is checked$')\
            == '(And )I see the "radio_key" radio is checked'

    assert viewer.make_it_readable(r'^(And )?I check the [\"](?P<checkbox_key>.+)[\"] checkbox$')\
            == '(And )I check the "checkbox_key" checkbox'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<textbox_name>.+)[\"] textbox is empty$')\
            == '(And )I see "textbox_name" textbox is empty'

    assert viewer.make_it_readable(r'^(And )?I see [\"](.+)[\"] textbox does not match [\"](.+)[\"]$')\
            == '(And )I see "blah" textbox does not match "blah"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) does not match [\"](?P<text>.+)[\"]$')\
            == '(And )I see "element_name" [element_type|element selector] does not match "text"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<image_name>.+)[\"] image does not have src of [\"](?P<src>.+)[\"]$')\
            == '(And )I see "image_name" image does not have src of "src"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) does not contain [\"](?P<text>.+)[\"]$')\
            == '(And )I see "element_name" [element_type|element selector] does not contain "text"'

    assert viewer.make_it_readable(r'^(And )?I check the [\"](?P<radio_key>.+)[\"] radio$')\
            == '(And )I check the "radio_key" radio'

    assert viewer.make_it_readable(r'^(And )?I select the option with value of [\"](?P<option_value>.+)[\"] in [\"](?P<select_name>.+)[\"] select$')\
            == '(And )I select the option with value of "option_value" in "select_name" select'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) contains [\"](?P<markup>.+)[\"] markup$')\
            == '(And )I see "element_name" [element_type|element selector] contains "markup" markup'

    assert viewer.make_it_readable(r'^(And )?I select the option with text of [\"](?P<text>.+)[\"] in [\"](?P<select_name>.+)[\"] select$')\
            == '(And )I select the option with text of "text" in "select_name" select'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<title>.+)[\"] title$')\
            == '(And )I see "title" title'

    assert viewer.make_it_readable(r'^(And )?I do not see [\"](?P<element_name>.+)[\"] (?P<element_type><element selector>)$')\
            == '(And )I do not see "element_name" [element_type|element selector]'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<select_name>.+)[\"] select does not contain an option with text [\"](?P<text>.+)[\"]$')\
            == '(And )I see "select_name" select does not contain an option with text "text"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<select_name>.+)[\"] select does not have selected index of (?P<index>\d+)$')\
            == '(And )I see "select_name" select does not have selected index of X'

    assert viewer.make_it_readable(r'^(And )?I see the [\"](?P<checkbox_key>.+)[\"] checkbox is not checked$')\
            == '(And )I see the "checkbox_key" checkbox is not checked'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>.+)[\"] (?P<element_type><element selector>) does not have [\"](?P<style_name>.+)[\"] style$')\
            == '(And )I see "element_name" [element_type|element selector] does not have "style_name" style'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<link_name>.+)[\"] link has [\"](?P<text>.+)[\"] text$')\
            == '(And )I see "link_name" link has "text" text'

    assert viewer.make_it_readable(r'^(And )?I uncheck the [\"](?P<checkbox_key>.+)[\"] checkbox$')\
            == '(And )I uncheck the "checkbox_key" checkbox'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) matches [\"](?P<text>.+)[\"]$')\
            == '(And )I see "element_name" [element_type|element selector] matches "text"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) does not match [\"](?P<markup>.+)[\"] markup$')\
            == '(And )I see "element_name" [element_type|element selector] does not match "markup" markup'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<textbox_name>.+)[\"] textbox is not empty$')\
            == '(And )I see "textbox_name" textbox is not empty'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) is disabled$')\
            == '(And )I see "element_name" [element_type|element selector] is disabled'

    assert viewer.make_it_readable(r'^(And )?I wait for [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) to disappear( for (?P<timeout>\d+) seconds)?$')\
            == '(And )I wait for "element_name" [element_type|element selector] to disappear( for X seconds)'

    assert viewer.make_it_readable(r'^(And )?I wait for [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) to be present( for (?P<timeout>\d+) seconds)?$')\
            == '(And )I wait for "element_name" [element_type|element selector] to be present( for X seconds)', "result was: %s" % viewer.make_it_readable(r'^(And )?I wait for [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) to be present( for (?P<timeout>\d+) seconds)?$')

    assert viewer.make_it_readable(r'^(And )?I see [\"](.+)[\"] textbox matches [\"](.+)[\"]$')\
            == '(And )I see "blah" textbox matches "blah"'

    assert viewer.make_it_readable(r'^(And )?I wait for the page to load( for (?P<timeout>\d+) seconds)?$')\
            == '(And )I wait for the page to load( for X seconds)'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<select_name>.+)[\"] select does not have selected text of [\"](?P<text>.+)[\"]$')\
            == '(And )I see "select_name" select does not have selected text of "text"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](.+)[\"] textbox contains [\"](.+)[\"]$')\
            == '(And )I see "blah" textbox contains "blah"'

    assert viewer.make_it_readable(r'^(And )?I slowly fill [\"](?P<textbox_name>.+)[\"] textbox with [\"](?P<text>.+)[\"]$')\
            == '(And )I slowly fill "textbox_name" textbox with "text"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<select_name>.+)[\"] select has selected text of [\"](?P<text>.+)[\"]$')\
            == '(And )I see "select_name" select has selected text of "text"'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<select_name>.+)[\"] select does not have selected value of [\"](?P<value>.+)[\"]$')\
            == '(And )I see "select_name" select does not have selected value of "value"'

    assert viewer.make_it_readable(r'^(And )?I clean [\"](?P<textbox_name>.+)[\"] textbox$')\
            == '(And )I clean "textbox_name" textbox'

    assert viewer.make_it_readable(r'^(And )?I click [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>)(?P<should_wait> and wait)?$')\
            == '(And )I click "element_name" [element_type|element selector]( and wait)'

    assert viewer.make_it_readable(r'^(And )?I go to %s' % url_regex)\
            == '(And )I go to [page|"url"]'

    assert viewer.make_it_readable(r'^(And )?I drag the [\"](?P<from_element_name>.+)[\"] (?P<from_element_type><element selector>) to the [\"](?P<to_element_name>.+)[\"] (?P<to_element_type><element selector>)?$')\
            == '(And )I drag the "from_element_name" [from_element_type|element selector] to the "to_element_name" [to_element_type|element selector]'

    assert viewer.make_it_readable(r'^(And )?I see [\"](?P<element_name>[^"]+)[\"] (?P<element_type><element selector>) contains [\"](?P<text>.+)[\"]$')\
            == '(And )I see "element_name" [element_type|element selector] contains "text"'

########NEW FILE########
__FILENAME__ = test_hooks

from time import sleep

from mocker import Mocker, ANY
from nose.tools import raises

from pyccuracy.hooks import *

@raises(NotImplementedError)
def test_construction_fails_without_implementing_execute_for_after_tests_hook():
    class DoNothing(AfterTestsHook):
        pass
    Hooks.reset()

@raises(NotImplementedError)
def test_construction_fails_without_implementing_execute_for_before_tests_hook():
    class DoNothing(BeforeTestsHook):
        pass
    Hooks.reset()

def test_will_register_after_tests_hook():
    class SomeHook(AfterTestsHook):
        def execute(self, result):
            pass

    assert SomeHook in HOOKS['after_tests']
    Hooks.reset()

def test_will_register_before_tests_hook():
    class SomeHook(BeforeTestsHook):
        def execute(self):
            pass

    assert SomeHook in HOOKS['before_tests']
    Hooks.reset()

def test_will_execute_after_tests_hook():
    
    mocker = Mocker()
    
    mock = mocker.mock()
    mock.a_method()
    
    with mocker:
        class MyHook(AfterTestsHook):
            def execute(self, result):
                MyHook.mock.a_method()
        
        MyHook.mock = mock
        Hooks.execute_after_tests(None)
        
    Hooks.reset()

def test_will_execute_before_tests_hook():
    
    mocker = Mocker()
    
    mock = mocker.mock()
    mock.a_method()

    with mocker:
        class MyHook(BeforeTestsHook):
            def execute(self):
                MyHook.mock.a_method()
    
        MyHook.mock = mock
        Hooks.execute_before_tests()
        
    Hooks.reset()

@raises(RuntimeError)
def test_user_exceptions_make_pyccuracy_raises_after_hook_error():
    class BrokenHook(AfterTestsHook):
        def execute(self, results):
            raise RuntimeError("user did stupid things")
    
    Hooks.execute_after_tests(None)
    Hooks.reset()

@raises(RuntimeError)
def test_user_exceptions_make_pyccuracy_raises_before_hook_error():
    class BrokenHook(BeforeTestsHook):
        def execute(self):
            raise RuntimeError("user did stupid things")

    Hooks.execute_before_tests()
    Hooks.reset()

def test_reset_hooks():
    Hooks.reset()
    class AHook(AfterTestsHook):
        def execute(self, results):
            pass
    class AnotherHook(BeforeTestsHook):
        def execute(self):
            pass
    assert len(HOOKS['after_tests']) == 1
    assert len(HOOKS['before_tests']) == 1
    assert AHook in HOOKS['after_tests']
    assert AnotherHook in HOOKS['before_tests']
    Hooks.reset()
    assert len(HOOKS['after_tests']) == 0
    assert len(HOOKS['before_tests']) == 0

########NEW FILE########
__FILENAME__ = test_language
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mocker import Mocker
from nose.tools import raises, set_trace

from pyccuracy.languages import LanguageGetter
from pyccuracy.errors import WrongArgumentsError

def test_language_getter_get():
    
    mocker = Mocker()
    
    language = 'data1 = something\n' \
               'data2 = something else'

    filemock = mocker.mock()
    filemock.read()
    mocker.result(language)

    with mocker:
        lg = LanguageGetter('en-us', file_object=filemock)
        lg.fill_data()
    
        assert lg.raw_data == language
        assert 'data' in lg.language_path
        assert lg.language_path.endswith('en-us.txt')
        assert lg.get('data1') == u'something'
        assert lg.get('data2') == u'something else'

def test_laguage_getter_format_args():
    
    mocker = Mocker()
    
    language = 'error_one_ok_args = you expected %s but got %s'

    filemock = mocker.mock()
    filemock.read()
    mocker.result(language)

    with mocker:
        lg = LanguageGetter('en-us', file_object=filemock)
        lg.fill_data()
    
        assert lg.format('error_one_ok_args', 'X', 'Y') == u'you expected X but got Y'

def test_laguage_getter_format():
    
    mocker = Mocker()
    
    language = 'error_one_ok_kwargs = you expected %(expected)s but got %(what_got)s'

    filemock = mocker.mock()
    filemock.read()
    mocker.result(language)

    with mocker:
        lg = LanguageGetter('en-us', file_object=filemock)
        lg.fill_data()
    
        assert lg.format('error_one_ok_kwargs', expected='Xabba', what_got='Yabba') == u'you expected Xabba but got Yabba'

def test_laguage_getter_format_raises_too_many_args():
    
    mocker = Mocker()
    
    language = 'error_two_too_many_args = impossible to check %s'

    filemock = mocker.mock()
    filemock.read()
    mocker.result(language)

    with mocker:
        lg = LanguageGetter('en-us', file_object=filemock)
        lg.fill_data()
    
        @raises(WrongArgumentsError)
        def format_wrong_too_many_args():
            assert lg.format('error_two_too_many_args', 'X', '!Y') != u'impossible to check X'
    
        format_wrong_too_many_args()

def test_laguage_getter_format_raises_not_enough_args():
    
    mocker = Mocker()
    
    language = 'error_three_not_enough_args = impossible to check %s in %s\n'

    filemock = mocker.mock()
    filemock.read()
    mocker.result(language)

    with mocker:
        lg = LanguageGetter('en-us', file_object=filemock)
        lg.fill_data()
    
        @raises(WrongArgumentsError)
        def format_wrong_not_enough_args():
            assert lg.format('error_three_not_enough_args', 'X') != u'impossible to check X in %s'
    
        format_wrong_not_enough_args()

def test_laguage_getter_format_raises_args_got_kwargs():
    
    mocker = Mocker()
    
    language = 'error_five_args_got_kwargs = impossible to check %s'

    filemock = mocker.mock()
    filemock.read()
    mocker.result(language)

    with mocker:
        lg = LanguageGetter('en-us', file_object=filemock)
        lg.fill_data()
    
        @raises(WrongArgumentsError)
        def format_wrong_args_got_kwargs():
            assert lg.format('error_five_args_got_kwargs', what='X') != u'impossible to check X in %s'
        format_wrong_args_got_kwargs()

def test_laguage_getter_format_raises_kwargs_got_args():
    
    mocker = Mocker()
    
    language = 'error_six_kwargs_got_args = impossible to check %(param)s'

    filemock = mocker.mock()
    filemock.read()
    mocker.result(language)

    with mocker:
        lg = LanguageGetter('en-us', file_object=filemock)
        lg.fill_data()
    
        @raises(WrongArgumentsError)
        def format_wrong_args_got_kwargs():
            assert lg.format('error_six_kwargs_got_args', 'X') != u'impossible to check X in %s'
        format_wrong_args_got_kwargs()


########NEW FILE########
__FILENAME__ = test_page_registry
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from re import compile as re_compile

from utils import assert_raises
from pyccuracy.common import Settings
from pyccuracy.page import PageRegistry, Page

fake_abs = (lambda x:x)

def test_page_registry_resolve_raises_with_wrong_none_settings():
    def do_resolve_fail():
        PageRegistry.resolve(None, 'http://google.com', exists_func=fake_abs)

    exc = 'PageRegistry.resolve takes a pyccuracy.common.Settings ' \
          'object first parameter. Got None.'
    assert_raises(TypeError, do_resolve_fail,
                  exc_pattern=re_compile(exc))

def test_page_registry_resolve_raises_with_wrong_none_settings_and_none_url():
    def do_resolve_fail():
        PageRegistry.resolve(None, None, exists_func=fake_abs)

    exc = 'PageRegistry.resolve takes a pyccuracy.common.Settings ' \
          'object first parameter. Got None.'
    assert_raises(TypeError, do_resolve_fail,
                  exc_pattern=re_compile(exc))

def test_page_registry_resolve_raises_with_wrong_none_url():
    def do_resolve_fail():
        PageRegistry.resolve(Settings(), None, exists_func=fake_abs)

    exc = 'PageRegistry.resolve argument 2 must be a string. Got None.'
    assert_raises(TypeError, do_resolve_fail,
                  exc_pattern=re_compile(exc))

def test_page_registry_does_not_raises_when_must_raise_is_false():
    assert PageRegistry.resolve(None, None, must_raise=False, exists_func=fake_abs) is None

def test_page_registry_resolve_by_page_class_name_get_right_class():
    class MyPage(Page):
        url = 'blabla'

    PageGot, url = PageRegistry.resolve(Settings(), 'My Page', exists_func=fake_abs)
    assert PageGot is MyPage, 'The page resolved by "My Page" should be a type class: MyPage. Got %r.' % PageGot

def test_page_registry_resolve_by_page_class_name_with_base_url_get_right_url():
    class MyPage(Page):
        url = 'blabla'

    PageGot, url = PageRegistry.resolve(Settings({'base_url': 'https://github.com/heynemann/pyccuracy/wiki'}), 'My Page', exists_func=fake_abs)
    assert PageGot is MyPage, 'The page resolved by "My Page" should be a type class: MyPage. Got %r.' % PageGot
    assert url == 'https://github.com/heynemann/pyccuracy/wiki/blabla', 'The url must be https://github.com/heynemann/pyccuracy/wiki concatenated with "/" and "blabla". Got "%s".' % url

def test_page_registry_resolve_by_page_class_name_with_base_url_get_right_url_without_slash():
    class MyPage(Page):
        url = 'blabla'

    PageGot, url = PageRegistry.resolve(Settings(cur_dir='/home'), 'My Page', exists_func=fake_abs)

    assert PageGot is MyPage, 'The page resolved by "My Page" should be a type class: MyPage. Got %r.' % PageGot
    assert url == 'file:///home/blabla', 'The url must be "file:///home" concatenated with "/" and "blabla". Got "%s".' % url

def test_page_registry_resolve_by_page_class_name_with_base_url_get_right_url_with_slash():
    class MyPage(Page):
        url = 'blabla'

    PageGot, url = PageRegistry.resolve(Settings(cur_dir='/home/'), 'My Page', exists_func=fake_abs)

    assert PageGot is MyPage, 'The page resolved by "My Page" should be a type class: MyPage. Got %r.' % PageGot
    assert url == 'file:///home/blabla', 'The url must be "file:///home" concatenated with "/" and "blabla". Got "%s".' % url

def test_page_registry_resolve_by_page_class_name_with_base_url_get_right_url_without_slash_both():
    class MyPage(Page):
        url = 'blabla'

    PageGot, url = PageRegistry.resolve(Settings(dict(tests_dir='home'), cur_dir='home', abspath_func=fake_abs), 'My Page', abspath_func=fake_abs, exists_func=fake_abs)

    assert PageGot is MyPage, 'The page resolved by "My Page" should be a type class: MyPage. Got %r.' % PageGot
    assert url == 'file:///home/blabla', 'The url must be "file:///home" concatenated with "/" and "blabla". Got "%s".' % url

def test_page_registry_resolve_by_page_class_name_with_base_url_get_right_url_without_slash_left():
    class MyPage(Page):
        url = 'blabla'

    PageGot, url = PageRegistry.resolve(Settings(dict(tests_dir='home'), cur_dir='home', abspath_func=fake_abs), 'My Page', abspath_func=fake_abs, exists_func=fake_abs)

    assert PageGot is MyPage, 'The page resolved by "My Page" should be a type class: MyPage. Got %r.' % PageGot
    assert url == 'file:///home/blabla', 'The url must be "file:///home" concatenated with "/" and "blabla". Got "%s".' % url

def test_page_registry_resolve_by_page_class_name_with_base_url_get_right_url_without_slash_right():
    class MyPage(Page):
        url = 'blabla'

    PageGot, url = PageRegistry.resolve(Settings(dict(tests_dir='home'), cur_dir='home', abspath_func=fake_abs), 'My Page', abspath_func=fake_abs, exists_func=fake_abs)

    assert PageGot is MyPage, 'The page resolved by "My Page" should be a type class: MyPage. Got %r.' % PageGot
    assert url == 'file:///home/blabla', 'The url must be "file:///home" concatenated with "/" and "blabla". Got "%s".' % url

def test_page_registry_resolve_page_by_url_with_base_url():
    PageGot, url = PageRegistry.resolve(Settings({'base_url': 'https://github.com/heynemann/pyccuracy/wiki'}), 'my_url', exists_func=fake_abs)

    assert PageGot is None, 'The page resolved by "my_url" should be a type class: MyPage. Got %r.' % PageGot
    assert url == 'https://github.com/heynemann/pyccuracy/wiki/my_url', 'The url must be "https://github.com/heynemann/pyccuracy/wiki/my_url". Got "%s".' % url

def test_page_registry_resolve_page_by_url_without_base_url_with_slash():
    PageGot, url = PageRegistry.resolve(Settings(dict(tests_dir='/test/'), cur_dir='/test/'), 'my_url', exists_func=fake_abs)

    assert PageGot is None, 'The page resolved by "my_url" should be a type class: MyPage. Got %r.' % PageGot
    assert url == 'file:///test/my_url', 'The url must be "file:///test/my_url". Got "%s".' % url

def test_page_registry_resolve_page_by_url_without_base_url_without_slash():
    PageGot, url = PageRegistry.resolve(Settings(dict(tests_dir='/test/'), cur_dir='/test'), 'my_url', exists_func=fake_abs)

    assert PageGot is None, 'The page resolved by "my_url" should be a type class: MyPage. Got %r.' % PageGot
    assert url == 'file:///test/my_url', 'The url must be "file:///test/my_url". Got "%s".' % url

def test_page_registry_resolve_by_url_without_base_url_without_page_with_slash():
    PageGot, url = PageRegistry.resolve(Settings(cur_dir='/test/'), 'file.html', exists_func=fake_abs)

    assert PageGot is None, 'The page resolved by "file.html" should be None. Got %r.' % PageGot
    assert url == 'file:///test/file.html', 'The url must be "file:///test/file.html". Got "%s".' % url

def test_page_registry_resolve_by_url_without_base_url_without_page_without_slash_right():
    PageGot, url = PageRegistry.resolve(Settings(cur_dir='/test'), 'file.html', exists_func=fake_abs)

    assert PageGot is None, 'The page resolved by "file.html" should be None. Got %r.' % PageGot
    assert url == 'file:///test/file.html', 'The url must be "file:///test/file.html". Got "%s".' % url

def test_page_registry_resolve_by_url_without_base_url_without_page_without_slash_left():
    PageGot, url = PageRegistry.resolve(Settings(cur_dir='test/', abspath_func=fake_abs), 'file.html', abspath_func=fake_abs, exists_func=fake_abs)

    assert PageGot is None, 'The page resolved by "file.html" should be None. Got %r.' % PageGot
    assert url == 'file:///test/file.html', 'The url must be "file:///test/file.html". Got "%s".' % url

def test_page_registry_resolve_by_url_without_base_url_without_page_without_slash_both():
    PageGot, url = PageRegistry.resolve(Settings(cur_dir='test', abspath_func=fake_abs), 'file.html', abspath_func=fake_abs, exists_func=fake_abs)

    assert PageGot is None, 'The page resolved by "file.html" should be None. Got %r.' % PageGot
    assert url == 'file:///test/file.html', 'The url must be "file:///test/file.html". Got "%s".' % url


########NEW FILE########
__FILENAME__ = test_parser
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mocker import Mocker
from nose.tools import *

from pyccuracy.parsers import FileParser

def test_parse_block_lines():
    parser = FileParser(None, None, None)
    
    line_index = 5
    line = "And I see table as:"
    scenario_lines = [
        'Line 1',
        'Line 2',
        'Line 3',
        'Scenario bla',
        'Given',
        '    And I see table as:',
        '        | Name | Age | Sex  |',
        '        | Paul | 28  | Male |',
        '        | John | 30  | Male |'
    ]
    offset, rows, parsed_rows = parser.parse_rows(line_index, line, scenario_lines)
    
    assert offset == 3
    assert rows == [
        '        | Name | Age | Sex  |',
        '        | Paul | 28  | Male |',
        '        | John | 30  | Male |'
    ]
    assert parsed_rows == [
                        {
                            'Name':'Paul',
                            'Age':'28',
                            'Sex':'Male'
                        },
                        {
                            'Name':'John',
                            'Age':'30',
                            'Sex':'Male'
                        }
                   ]

########NEW FILE########
__FILENAME__ = test_result
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mocker import Mocker

from pyccuracy.result import Result
from pyccuracy.common import Settings, Status
from pyccuracy.fixture import Fixture
from pyccuracy.fixture_items import Story, Scenario, Action

summary_template = """================
Test Run Summary
================

Status: $run_status

Test Data Stats
---------------
Successful Stories......$successful_stories/$total_stories ($successful_story_percentage%)
Failed Stories..........$failed_stories/$total_stories ($failed_story_percentage%)
Successful Scenarios....$successful_scenarios/$total_scenarios ($successful_scenario_percentage%)
Failed Scenarios........$failed_scenarios/$total_scenarios ($failed_scenario_percentage%)"""

summary_template_failed_stories = """#if($has_failed_scenarios)


Failed Stories / Scenarios
--------------------------
#foreach ($scenario in $failed_scenario_instances)Story..........As a $scenario.story.as_a I want to $scenario.story.i_want_to So that $scenario.story.so_that
Story file.....To be implemented.
Scenario.......$scenario.index - $scenario.title
    Given
#foreach ($action in $scenario.givens)#if($action.status != "FAILED")        $action.description - $action.status#end
#if($action.status == "FAILED")        $action.description - $action.status - $action.error#end#end

    When
#foreach ($action in $scenario.whens)#if($action.status != "FAILED")        $action.description - $action.status#end
#if($action.status == "FAILED")        $action.description - $action.status - $action.error#end#end

    Then
#foreach ($action in $scenario.thens)#if($action.status != "FAILED")        $action.description - $action.status#end
#if($action.status == "FAILED")        $action.description - $action.status - $action.error#end#end
#end
#end"""

def some_action():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some file")
    scenario = story.append_scenario("1", "Something")
    return scenario.add_given(action_description="Some Action", execute_function=lambda: None, args=["s"], kwargs={"a":"b"})

def complete_scenario_with_then_action_returned():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="Some file")
    scenario = story.append_scenario("1", "Something")
    given = scenario.add_given(action_description="I did something", execute_function=lambda: None, args=["s"], kwargs={"a":"b"})
    when = scenario.add_when(action_description="I do something", execute_function=lambda: None, args=["s"], kwargs={"a":"b"})
    then = scenario.add_then(action_description="Something happens", execute_function=lambda: None, args=["s"], kwargs={"a":"b"})
    return then

def test_empty_result_returns_result():
    result = Result.empty()
    assert result is not None

def test_empty_result_returns_none_fixture():
    result = Result.empty()
    assert result.fixture is None

def test_empty_result_returns_unknown_status():
    result = Result.empty()
    assert result.get_status() == Status.Unknown

def test_see_summary_for_fixture():
    
    mocker = Mocker()
    
    template_loader_mock = mocker.mock()
    template_loader_mock.load("summary")
    mocker.result(summary_template)
    
    with mocker:
        settings = Settings()
        fixture = Fixture()
        action = some_action()
        fixture.append_story(action.scenario.story)
        action.mark_as_successful()
        result = Result(fixture=fixture, template_loader=template_loader_mock)
    
        summary = result.summary_for(settings.default_culture)
        assert summary is not None

def test_see_summary_for_fixture_returns_proper_string():
    
    mocker = Mocker()
    
    expected = """================
Test Run Summary
================

Status: SUCCESSFUL

Test Data Stats
---------------
Successful Stories......1/1 (100.00%)
Failed Stories..........0/1 (0.00%)
Successful Scenarios....1/1 (100.00%)
Failed Scenarios........0/1 (0.00%)"""

    template_loader_mock = mocker.mock()
    template_loader_mock.load("summary")
    mocker.result(summary_template)
    
    with mocker:
        settings = Settings()
        fixture = Fixture()
        action = some_action()
        fixture.append_story(action.scenario.story)
        action.mark_as_successful()
        result = Result(fixture=fixture, template_loader=template_loader_mock)
    
        summary = result.summary_for(settings.default_culture)
        assert summary == expected

def test_see_summary_for_fixture_returns_proper_string_for_failed_tests():
    
    mocker = Mocker()
    
    expected = """================
Test Run Summary
================

Status: FAILED

Test Data Stats
---------------
Successful Stories......0/1 (0.00%)
Failed Stories..........1/1 (100.00%)
Successful Scenarios....0/1 (0.00%)
Failed Scenarios........1/1 (100.00%)"""

    template_loader_mock = mocker.mock()
    template_loader_mock.load("summary")
    mocker.result(summary_template)
    
    with mocker:
        settings = Settings()
        fixture = Fixture()
        action = some_action()
        fixture.append_story(action.scenario.story)
        action.mark_as_failed()
        result = Result(fixture=fixture, template_loader=template_loader_mock)
    
        summary = result.summary_for(settings.default_culture)
        assert summary == expected

def test_see_summary_for_fixture_returns_proper_string_for_no_tests():
    
    mocker = Mocker()
    
    expected = """================
Test Run Summary
================

Status: UNKNOWN

Test Data Stats
---------------
Successful Stories......0/0 (0.00%)
Failed Stories..........0/0 (0.00%)
Successful Scenarios....0/0 (0.00%)
Failed Scenarios........0/0 (0.00%)"""

    template_loader_mock = mocker.mock()
    template_loader_mock.load("summary")
    mocker.result(summary_template)
    
    with mocker:
        settings = Settings()
        fixture = Fixture()
        result = Result(fixture=fixture, template_loader=template_loader_mock)
    
        summary = result.summary_for(settings.default_culture)
        assert summary == expected

def test_see_summary_for_fixture_returns_proper_failed_scenarios_string():
    
    mocker = Mocker()
    
    expected = """================
Test Run Summary
================

Status: FAILED

Test Data Stats
---------------
Successful Stories......0/1 (0.00%)
Failed Stories..........1/1 (100.00%)
Successful Scenarios....0/1 (0.00%)
Failed Scenarios........1/1 (100.00%)

Failed Stories / Scenarios
--------------------------
Story..........As a Someone I want to Do Something So that I'm Happy
Story file.....To be implemented.
Scenario.......1 - Something
    Given
        I did something - UNKNOWN
    When
        I do something - UNKNOWN
    Then
        Something happens - FAILED - Something very bad happened
"""

    template_loader_mock = mocker.mock()
    template_loader_mock.load("summary")
    mocker.result(summary_template + summary_template_failed_stories)
    
    with mocker:
        settings = Settings()
        fixture = Fixture()
        result = Result(fixture=fixture, template_loader=template_loader_mock)
        action = complete_scenario_with_then_action_returned()
        fixture.append_story(action.scenario.story)
        action.mark_as_failed("Something very bad happened")
    
        summary = result.summary_for(settings.default_culture)
    
        assert summary.strip() == expected.strip()


########NEW FILE########
__FILENAME__ = test_selenium_browser_driver
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re

from mocker import Mocker

from pyccuracy.drivers.core.selenium_driver import SeleniumDriver
from pyccuracy.drivers import DriverError
from pyccuracy.common import Context, Settings
from utils import assert_raises

def test_can_create_selenium_browser_driver():
    context = Context(Settings())
    driver = SeleniumDriver(context)

    assert driver is not None

def test_selenium_driver_keeps_context():
    context = Context(Settings())
    driver = SeleniumDriver(context)

    assert driver.context == context

def test_selenium_driver_overrides_start_test_properly():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.start()

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
    
        driver.start_test("http://localhost")

def test_selenium_driver_overrides_start_test_properly_when_extra_args_specified():
    
    mocker = Mocker()
    
    context = Context(Settings())
    context.settings.extra_args = {
                                    "selenium.server":"localhost",
                                    "selenium.port":4444
                                  }
    selenium_mock = mocker.mock()
    selenium_mock.start()

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
    
        driver.start_test("http://localhost")

def test_selenium_driver_raises_on_start_test_when_selenium_cant_start():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.start()
    mocker.throw(DriverError("invalid usage"))

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
    
        assert_raises(DriverError, driver.start_test, url="http://localhost", \
                      exc_pattern=re.compile(r"Error when starting selenium. Is it running ?"))

def test_selenium_driver_calls_proper_selenese_on_stop_test():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.stop()

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
    
        driver.stop_test()

def test_selenium_driver_overrides_page_open_properly():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.open("http://localhost")

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
    
        driver.page_open("http://localhost")

def test_selenium_resolve_element_key_returns_element_key_for_null_context():
    driver = SeleniumDriver(None)
    assert driver.resolve_element_key(None, "button", "SomethingElse") == "SomethingElse"

def test_selenium_resolve_element_key_uses_SeleniumElementSelector_for_non_null_contexts():
    context = Context(Settings())
    driver = SeleniumDriver(context)
    key = driver.resolve_element_key(context, "Button", "SomethingElse")
    expected = "//*[(@name='SomethingElse' or @id='SomethingElse')]"
    assert key == expected, "Expected %s, Actual: %s" % (expected, key)

def test_selenium_driver_calls_proper_selenese_on_wait_for_page():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.wait_for_page_to_load(30000)

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
    
        driver.wait_for_page()

def test_selenium_driver_calls_proper_selenese_on_click_element():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.click("some")

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
    
        driver.click_element("some")

def test_selenium_driver_calls_proper_selenese_on_get_title():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.get_title()
    mocker.result("Some title")

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
    
        title = driver.get_title()
        assert title == "Some title"
    
def test_selenium_driver_calls_get_eval():
    
    mocker = Mocker()
    
    javascript = "some javascript"
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.get_eval(javascript)
    mocker.result("ok")
    
    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
        
        assert driver.exec_js(javascript) == "ok"

def test_selenium_driver_calls_type_keys():
    
    mocker = Mocker()
    
    input_selector = "//some_xpath"
    text = "text to type"
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.type_keys(input_selector, text)
    
    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
        driver.type_keys(input_selector, text)

def test_wait_for_presence():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.is_element_present('some element')
    mocker.result(True)
    selenium_mock.is_visible('some element')
    mocker.result(True)

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
        driver.wait_for_element_present("some element", 1)

def test_wait_for_presence_works_even_when_is_visible_raises():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.is_element_present('some element')
    mocker.count(min=1, max=None)
    mocker.result(True)
    
    with mocker.order():
        selenium_mock.is_visible('some element')
        mocker.throw(Exception("ERROR: Element some element not found"))
        selenium_mock.is_visible('some element')
        mocker.result(True)

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
        driver.wait_for_element_present("some element", 1)

def test_wait_for_disappear():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.is_element_present('some element')
    mocker.count(min=1, max=None)
    mocker.result(True)
    selenium_mock.is_visible('some element')
    mocker.count(min=1, max=None)
    mocker.result(True)

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
        driver.wait_for_element_to_disappear("some element", 1)

def test_wait_for_disappear_works_even_when_is_visible_raises():
    
    mocker = Mocker()
    
    context = Context(Settings())
    selenium_mock = mocker.mock()
    selenium_mock.is_element_present('some element')
    mocker.count(min=1, max=None)
    mocker.result(True)
    selenium_mock.is_visible('some element')
    mocker.throw(Exception("ERROR: Element some element not found"))

    with mocker:
        driver = SeleniumDriver(context, selenium=selenium_mock)
        driver.wait_for_element_to_disappear("some element", 1)


########NEW FILE########
__FILENAME__ = test_settings
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from os.path import join, abspath, dirname
from pyccuracy.common import Settings

def test_settings_return_default_value_for_tests_dirs():
    settings = Settings({}, cur_dir='/root')
    assert settings.tests_dirs[0] == '/root', "The tests dir should be %s but was %s." % ('/root', settings.tests_dirs[0])

def test_settings_return_default_value_for_actions_dir():
    settings = Settings({}, actions_dir='/actions')
    assert settings.actions_dir == '/actions', "The actions_dir dir should be %s but was %s." % ('/actions', settings.actions_dir)

def test_settings_return_default_value_for_languages_dir():
    settings = Settings({}, languages_dir)
    assert settings.languages_dir == '/languages', "The languages_dir dir should be %s but was %s." % ('/languages', settings.languages_dir)

def test_settings_return_default_value_for_pages_dir():
    settings = Settings({})
    assert settings.pages_dir == cur_dir, "The pages dir should be %s but was %s." % (cur_dir, settings.pages_dir)

def test_settings_return_default_value_for_custom_actions_dir():
    settings = Settings({})
    assert settings.custom_actions_dir == cur_dir, "The custom actions dir should be %s but was %s." % (cur_dir, settings.custom_actions_dir)

def test_settings_return_default_value_for_file_pattern():
    settings = Settings({})
    assert settings.file_pattern == "*.acc", "The pattern should be *.acc but was %s." % (settings.file_pattern)

def test_settings_return_default_value_for_scenarios_to_run():
    settings = Settings({})
    assert settings.scenarios_to_run == [], "The scenarios to run should be None but was %s." % (settings.scenarios_to_run)

def test_settings_return_default_value_for_default_culture():
    settings = Settings({})
    assert settings.default_culture == "en-us", "The default culture should be en-us but was %s." % (settings.default_culture)

def test_settings_return_default_value_for_base_url():
    settings = Settings({})
    assert settings.base_url is None, "The base url should be None but was %s." % (settings.base_url)

def test_settings_return_default_value_for_should_throw():
    settings = Settings({})
    assert not settings.should_throw, "The should_throw setting should be False but was %s." % (settings.should_throw)

def test_settings_return_default_value_for_write_report():
    settings = Settings({})
    assert settings.write_report, "The write_report setting should be True but was %s." % (settings.write_report)

def test_settings_return_default_value_for_report_file_dir():
    settings = Settings({})
    assert settings.report_file_dir == cur_dir, "The report_file_dir should be %s but was %s." % (cur_dir, settings.report_file_dir)

def test_settings_return_default_value_for_report_file_name():
    settings = Settings({})
    assert settings.report_file_name == "report.html", "The report_file_name should be report.html but was %s." % (settings.report_file_name)

def test_settings_return_default_value_for_browser_to_run():
    settings = Settings({})
    assert settings.browser_to_run == "chrome", "The browser_to_run should be chrome but was %s." % (settings.browser_to_run)

def test_settings_return_default_value_for_browser_driver():
    settings = Settings({})
    assert settings.browser_driver == "selenium", "The browser_driver should be selenium but was %s." % (settings.browser_driver)

def test_settings_return_default_value_for_extra_args():
    settings = Settings({})
    assert settings.extra_args == {}, "The extra_args should be an empty dict but was %s." % (settings.extra_args)

#Specified Values
def test_settings_return_custom_value_for_tests_dirs():
    settings = Settings({"tests_dirs":["a","b"]})
    expected = [abspath("a"), abspath("b")]
    assert settings.tests_dirs == expected, "The tests dir should be %s but was %s." % (expected, settings.tests_dirs)

def test_settings_return_default_value_for_actions_dir():
    settings = Settings({"actions_dir":"a"})
    assert settings.actions_dir == "a", "The actions_dir dir should be %s but was %s." % ("a", settings.actions_dir)

def test_settings_return_default_value_for_languages_dir():
    settings = Settings({"languages_dir":"a"})
    assert settings.languages_dir == "a", "The languages_dir dir should be %s but was %s." % ("a", settings.languages_dir)

def test_settings_return_default_value_for_pages_dir():
    settings = Settings({"pages_dir":"a"})
    assert settings.pages_dir == "a", "The pages dir should be %s but was %s." % ("a", settings.pages_dir)

def test_settings_return_default_value_for_custom_actions_dir():
    settings = Settings({"custom_actions_dir":"a"})
    assert settings.custom_actions_dir == "a", "The custom actions dir should be %s but was %s." % ("a", settings.custom_actions_dir)

def test_settings_return_default_value_for_file_pattern():
    settings = Settings({"file_pattern":"a"})
    assert settings.file_pattern == "a", "The pattern should be a but was %s." % (settings.file_pattern)

def test_settings_return_default_value_for_scenarios_to_run():
    settings = Settings({"scenarios_to_run":"a"})
    assert settings.scenarios_to_run == ["a"], "The scenarios to run should be 'a' but was %s." % (settings.scenarios_to_run)

def test_settings_return_default_value_for_default_culture():
    settings = Settings({"default_culture":"a"})
    assert settings.default_culture == "a", "The default culture should be 'a' but was %s." % (settings.default_culture)

def test_settings_return_default_value_for_base_url():
    settings = Settings({"base_url":"a"})
    assert settings.base_url == "a", "The base url should be 'a' but was %s." % (settings.base_url)

def test_settings_return_default_value_for_should_throw():
    settings = Settings({"should_throw":True})
    assert settings.should_throw, "The should_throw setting should be True but was %s." % (settings.should_throw)

def test_settings_return_default_value_for_write_report():
    settings = Settings({"write_report":False})
    assert not settings.write_report, "The write_report setting should be False but was %s." % (settings.write_report)

def test_settings_return_default_value_for_report_file_dir():
    settings = Settings({"report_file_dir":"a"})
    assert settings.report_file_dir == "a", "The report_file_dir should be %s but was %s." % ("a", settings.report_file_dir)

def test_settings_return_default_value_for_report_file_name():
    settings = Settings({"report_file_name":"a"})
    assert settings.report_file_name == "a", "The report_file_name should be 'a' but was %s." % (settings.report_file_name)

def test_settings_return_default_value_for_browser_to_run():
    settings = Settings({"browser_to_run":"a"})
    assert settings.browser_to_run == "a", "The browser_to_run should be 'a' but was %s." % (settings.browser_to_run)

def test_settings_return_default_value_for_browser_driver():
    settings = Settings({"browser_driver":"a"})
    assert settings.browser_driver == "a", "The browser_driver should be 'a' but was %s." % (settings.browser_driver)

def test_settings_return_default_value_for_extra_args():
    d = {"a":"b"}
    settings = Settings({"extra_args":d})
    assert settings.extra_args == {"a":"b"}, "The extra_args should be an %s but was %s." % (d, settings.extra_args)

########NEW FILE########
__FILENAME__ = test_story_runner
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2009 Bernardo Heynemann <heynemann@gmail.com>
# Copyright (C) 2009 Gabriel Falcão <gabriel@nacaolivre.org>
#
# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.opensource.org/licenses/osl-3.0.php
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mocker import Mocker

from pyccuracy.fixture import Fixture
from pyccuracy.fixture_items import Story, Scenario, Action
from pyccuracy.common import Context, Settings, Status
from pyccuracy.story_runner import StoryRunner
from pyccuracy.errors import ActionFailedError
from utils import Object

def some_action():
    story = Story(as_a="Someone", i_want_to="Do Something", so_that="I'm Happy", identity="some file")
    scenario = story.append_scenario("1", "Something")
    def execute_action(context, *args, **kwargs):
        return None
        
    return scenario.add_given(action_description="Some Action", \
                              execute_function=execute_action, \
                              args=["s"], \
                              kwargs={"a":"b"})

def test_story_runner_returns_a_result():
    
    mocker = Mocker()
    
    settings = Settings()
    fixture = Fixture()
    runner = StoryRunner()
    context = Object()
    context.browser_driver = mocker.mock()
    context.browser_driver.start_test("http://localhost")
    context.browser_driver.stop_test()

    with mocker:
        result = runner.run_stories(settings, fixture, context=context)
        assert result is not None

def test_story_runner_returns_a_result_with_a_Fixture():
    
    mocker = Mocker()
    
    settings = Settings()
    fixture = Fixture()
    action = some_action()
    fixture.append_story(action.scenario.story)
    runner = StoryRunner()

    context = Object()
    context.browser_driver = mocker.mock()
    context.browser_driver.start_test("http://localhost")
    context.browser_driver.stop_test()
    context.settings = mocker.mock()
    context.settings.on_before_action
    mocker.result(None)
    context.settings.on_action_successful
    mocker.result(None)
    
    context.language = mocker.mock()
    context.language.get('given')
    mocker.result('Given')
    context.language.get('when')
    mocker.result('When')
    context.language.get('then')
    mocker.result('Then')

    with mocker:
        result = runner.run_stories(settings, fixture, context=context)
    
        assert result.fixture is not None
        assert isinstance(result.fixture, Fixture)

def test_story_runner_returns_a_result_with_the_original_Fixture():
    
    mocker = Mocker()
    
    settings = Settings()
    fixture = Fixture()
    action = some_action()
    fixture.append_story(action.scenario.story)
    runner = StoryRunner()

    context = Object()
    context.browser_driver = mocker.mock()
    context.browser_driver.start_test("http://localhost")
    context.browser_driver.stop_test()
    context.settings = mocker.mock()
    context.settings.on_before_action
    mocker.result(None)
    context.settings.on_action_successful
    mocker.result(None)
    
    context.language = mocker.mock()
    context.language.get('given')
    mocker.result('Given')
    context.language.get('when')
    mocker.result('When')
    context.language.get('then')
    mocker.result('Then')

    with mocker:
        result = runner.run_stories(settings, fixture, context=context)
    
        assert result.fixture == fixture

def test_story_runner_returns_failed_story():
    
    mocker = Mocker()
    
    settings = Settings()
    fixture = Fixture()
    runner = StoryRunner()

    context = Object()
    context.browser_driver = mocker.mock()
    context.browser_driver.start_test("http://localhost")
    context.browser_driver.stop_test()

    with mocker:
        result = runner.run_stories(settings, fixture, context=context)
    
        assert result is not None

def test_create_context_for_returns_context():
    settings = Settings()
    runner = StoryRunner()
    context = runner.create_context_for(settings)

    assert context is not None

def test_should_execute_scenarios_successfully():
    
    mocker = Mocker()
    
    settings = Settings()
    runner = StoryRunner()
    fixture = Fixture()
    fixture.append_story(some_action().scenario.story)

    context = Object()
    context.browser_driver = mocker.mock()
    context.browser_driver.start_test("http://localhost")
    context.browser_driver.stop_test()
    context.settings = mocker.mock()
    context.settings.on_before_action
    mocker.result(None)
    context.settings.on_action_successful
    mocker.result(None)
    
    context.language = mocker.mock()
    context.language.get('given')
    mocker.result('Given')
    context.language.get('when')
    mocker.result('When')
    context.language.get('then')
    mocker.result('Then')

    with mocker:
        result = runner.run_stories(settings=settings, fixture=fixture, context=context)
    
        assert fixture.get_status() == Status.Successful

def test_should_handle_action_errors_successfully():
    
    mocker = Mocker()
    
    def action_failed_method(context, *args, **kwargs):
        raise ActionFailedError("bla")
    settings = Settings()
    runner = StoryRunner()
    fixture = Fixture()
    action = some_action()
    fixture.append_story(action.scenario.story)
    action.execute_function = action_failed_method

    context = Object()
    context.browser_driver = mocker.mock()
    context.browser_driver.start_test("http://localhost")
    context.browser_driver.stop_test()
    context.settings = mocker.mock()
    context.settings.on_before_action
    mocker.result(None)
    context.settings.on_action_error
    mocker.result(None)
    context.language = mocker.mock()
    context.language.get('given')
    mocker.result('Given')

    with mocker:
        result = runner.run_stories(settings=settings, fixture=fixture, context=context)
    
        assert fixture.get_status() == Status.Failed

def test_should_record_errors_correctly():
    
    mocker = Mocker()
    
    def action_failed_method(context, *args, **kwargs):
        raise ActionFailedError("bla")
    settings = Settings()
    runner = StoryRunner()
    fixture = Fixture()
    action = some_action()
    fixture.append_story(action.scenario.story)
    action.execute_function = action_failed_method

    context = Object()
    context.browser_driver = mocker.mock()
    context.browser_driver.start_test("http://localhost")
    context.browser_driver.stop_test()
    context.settings = mocker.mock()
    context.settings.on_before_action
    mocker.result(None)
    context.settings.on_action_error
    mocker.result(None)
    
    context.language = mocker.mock()
    context.language.get('given')
    mocker.result('Given')

    with mocker:
        result = runner.run_stories(settings=settings, fixture=fixture, context=context)
    
        assert isinstance(action.error, ActionFailedError)
        assert action.error.message == "bla"

def test_should_catch_assertion_error():
    
    mocker = Mocker()
    
    def action_failed_method(context, *args, **kwargs):
        assert False, "bla"
    settings = Settings()
    runner = StoryRunner()
    fixture = Fixture()
    action = some_action()
    fixture.append_story(action.scenario.story)
    action.execute_function = action_failed_method

    context = Object()
    context.browser_driver = mocker.mock()
    context.browser_driver.start_test("http://localhost")
    context.browser_driver.stop_test()
    context.settings = mocker.mock()
    context.settings.on_before_action
    mocker.result(None)
    context.settings.on_action_error
    mocker.result(None)
    context.language = mocker.mock()
    context.language.get('given')
    mocker.result('Given')

    with mocker:
        result = runner.run_stories(settings=settings, fixture=fixture, context=context)
    
        assert isinstance(action.error, AssertionError)
        assert action.error.message == "bla"


########NEW FILE########
__FILENAME__ = test_utils
#!/usr/bin/env python
#-*- coding:utf-8 -*-

from utils import Object

def test_object():
    
    foo = Object(
        bar='bar',
        baz=(1, 2, 3),
        foo1=Object(
            bar='BAR',
            baz={
                'one': 1,
                'two': 2
                }
            )
        )
    
    assert foo.bar == 'bar'
    assert foo.baz == (1, 2, 3)
    assert foo.foo1.bar == 'BAR'
    assert foo.foo1.baz['one'] == 1
########NEW FILE########
__FILENAME__ = utils
#!/usr/bin/env python
#-*- coding:utf-8 -*-

# Licensed under the Open Software License ("OSL") v. 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.opensource.org/licenses/osl-3.0.php

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Discussion
#    assert_raises() adds two optional arguments: "exc_args"
#    and "exc_pattern". "exc_args" is a tuple that is expected
#    to match the .args attribute of the raised exception.
#    "exc_pattern" is a compiled regular expression that the
#    stringified raised exception is expected to match.
#
# Original url: http://code.activestate.com/recipes/307970/
# Author: Trent Mick
#
# Usage: assert_raises(ExceptionType, method_to_execute,
#                       arguments_to_method, kwargs_to_method,
#                       exc_pattern=r'^.+$')
# Please note that exc_pattern is not required, but if passed
# matches the exception message.
#
# Fail Conditions
# Fails on exception not raised, wrong exception type or
# invalid exception message.

import sys

def assert_raises(exception, callable, *args, **kwargs):
    if "exc_args" in kwargs:
        exc_args = kwargs["exc_args"]
        del kwargs["exc_args"]
    else:
        exc_args = None
    if "exc_pattern" in kwargs:
        exc_pattern = kwargs["exc_pattern"]
        del kwargs["exc_pattern"]
    else:
        exc_pattern = None

    argv = [repr(a) for a in args]\
           + ["%s=%r" % (k,v)  for k,v in kwargs.items()]
    callsig = "%s(%s)" % (callable.__name__, ", ".join(argv))

    try:
        callable(*args, **kwargs)
    except exception, exc:
        if exc_args is not None:
            assert exc.args != exc_args, \
                        "%s raised %s with unexpected args: "\
                        "expected=%r, actual=%r"\
                        % (callsig, exc.__class__, exc_args, exc.args)
        if exc_pattern is not None:
            assert exc_pattern.search(str(exc)), \
                            "%s raised %s, but the exception "\
                            "does not match '%s': %r"\
                            % (callsig, exc.__class__, exc_pattern.pattern,
                               str(exc))
    except:
        exc_info = sys.exc_info()
        print exc_info
        assert False, "%s raised an unexpected exception type: "\
                  "expected=%s, actual=%s"\
                  % (callsig, exception, exc_info[0])
    else:
        assert False, "%s did not raise %s" % (callsig, exception)

class Object(object):
    
    def __init__(self, **properties):
        
        for key in properties:
            self.__setattr__(key, properties[key])
########NEW FILE########
